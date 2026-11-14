//! PD-LIVE-CLI-SMOKE-01 — Live start→chunk→exit against an explicit local Agent CLI.
//!
//! Requires `--features real-spawn`. When no CLI is on PATH → early return (NOT RUN).
//! Uses `--version` only (no interactive prompt; no cloud gateway; no secrets in projection).
//!
//! Coordinate: PATH probe shared with PD-LIVE-TARGET-01 via `sgenaxis_adapters::probe_agent_cli`.

#![cfg(feature = "real-spawn")]

use std::thread;
use std::time::{Duration, Instant};

use sgenaxis_adapters::{probe_agent_cli, StdFileSystem, StdProcess};
use sgenaxis_exec::{
    AgentChunk, AgentPort, AgentProvider, AgentSettingsDocument, CliAgentAdapter, CliAgentSettings,
    CliToolConfig, CliToolKind, ExitClassification, OutputStream, StartRunRequest,
};

fn kind_for_key(key: &str) -> Option<CliToolKind> {
    match key {
        "claude" => Some(CliToolKind::Claude),
        "cursor-agent" => Some(CliToolKind::CursorAgent),
        "codex" => Some(CliToolKind::Codex),
        "antigravity" => Some(CliToolKind::Antigravity),
        _ => None,
    }
}

fn drain_live_with_timeout(
    agent: &mut dyn AgentPort,
    run: sgenaxis_exec::RunId,
    timeout: Duration,
) -> Result<Vec<AgentChunk>, String> {
    let deadline = Instant::now() + timeout;
    let mut all = Vec::new();
    while Instant::now() < deadline {
        let batch = agent
            .poll_chunks(run)
            .map_err(|e| format!("poll_chunks: {e}"))?;
        let done = batch
            .iter()
            .any(|e| matches!(e, AgentChunk::Exited { .. } | AgentChunk::Failed { .. }));
        all.extend(batch);
        if done {
            return Ok(all);
        }
        thread::sleep(Duration::from_millis(40));
    }
    Err(format!(
        "run did not terminate within {:?}; events so far: {all:?}",
        timeout
    ))
}

/// BDD-PD-LIVE-CLI-SMOKE-01: Live start→chunk→exit or clear NOT RUN skip.
#[test]
fn live_cli_smoke_start_chunk_exit_or_skip() {
    let Some(probed) = probe_agent_cli() else {
        eprintln!(
            "PD-LIVE-CLI-SMOKE-01 NOT RUN: no Agent CLI on PATH \
             (probed claude｜cursor-agent｜codex｜antigravity). Skip is OK."
        );
        return;
    };

    let kind = kind_for_key(&probed.key).expect("known key");
    let path_str = probed
        .path
        .to_str()
        .expect("utf-8 cli path")
        .to_string();

    let fs = StdFileSystem::new();
    let mut settings = CliAgentSettings::defaults();
    settings.selected = kind;
    *settings.config_mut(kind) = CliToolConfig::new(path_str.clone(), ["--version"]);
    settings
        .approve_live(&fs)
        .unwrap_or_else(|e| panic!("approve_live for {path_str}: {e}"));
    assert!(settings.live_approved);

    // Secrets must never appear in projection (MCP partition may hold a token).
    let mut doc = AgentSettingsDocument::defaults();
    doc.cli = settings.clone();
    doc.mcp.secret_token = Some("must-not-leak-in-projection".into());
    let proj = doc.projection();
    assert!(proj.mcp.has_secret);
    let proj_dbg = format!("{proj:?}");
    assert!(
        !proj_dbg.contains("must-not-leak-in-projection"),
        "projection leaked secret: {proj_dbg}"
    );

    let mut agent = CliAgentAdapter::new(settings, Box::new(StdProcess::new()));
    let run = agent
        .start_run(
            StartRunRequest::cli_live().with_binding(
                std::env::temp_dir().to_string_lossy().as_ref(),
                "PD-LIVE-CLI-SMOKE-01",
                "live-cli-smoke-fp",
            ),
        )
        .unwrap_or_else(|e| panic!("live start_run: {e}"));

    let events = drain_live_with_timeout(&mut agent, run, Duration::from_secs(30))
        .expect("live drain");

    assert!(
        matches!(
            events.first(),
            Some(AgentChunk::Started {
                dry_run: false,
                provider: AgentProvider::Cli,
                ..
            })
        ),
        "expected Started(dry_run=false); got {:?}",
        events.first()
    );

    let has_chunk_or_progress = events.iter().any(|e| {
        matches!(
            e,
            AgentChunk::Chunk {
                stream: OutputStream::Stdout | OutputStream::Stderr,
                ..
            } | AgentChunk::Progress { .. }
        )
    });
    assert!(
        has_chunk_or_progress,
        "expected Chunk and/or Progress before exit; events={events:?}"
    );

    let exited = events
        .iter()
        .rev()
        .find(|e| matches!(e, AgentChunk::Exited { .. }));
    assert!(
        matches!(
            exited,
            Some(AgentChunk::Exited {
                classification: ExitClassification::Success,
                exit_code: Some(0),
                ..
            })
        ),
        "expected Exited(Success, 0); got {exited:?}; all={events:?}"
    );

    eprintln!(
        "PD-LIVE-CLI-SMOKE-01 PASS: key={} path={} events={}",
        probed.key,
        path_str,
        events.len()
    );
}
