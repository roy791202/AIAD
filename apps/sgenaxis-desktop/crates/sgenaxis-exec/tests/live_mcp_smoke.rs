//! PD-MCP-LIVE-SMOKE-01 — Live MCP connect／tool against an explicit local target.
//!
//! Requires `--features real-mcp`. When env target missing／unactivatable → early return
//! (**NOT RUN**). Never treats DryRun as Live PASS. Secrets must not enter projection.
//!
//! Env gate (coordinate with PD-LIVE-TARGET-01 projection rules):
//! - `SGENAXIS_MCP_LIVE_ENDPOINT` — required; empty／`:8788`／`:8787` → NOT RUN
//! - `SGENAXIS_MCP_LIVE_TOOL` — optional (default `list_tools`)
//! - `SGENAXIS_MCP_LIVE_SERVER` — optional (default `local-smoke`)
//!
//! Uses in-process [`FakeMcpClient`] at the Live seam (`dry_run: false`) — no cloud
//! gateway; no forced paid service. Does **not** forge Live PASS from DryRun.

#![cfg(feature = "real-mcp")]

use sgenaxis_exec::{
    is_mcp_endpoint_activatable, probe_mcp_live_smoke_target, AgentChunk, AgentPort,
    AgentProvider, AgentSettingsDocument, ExitClassification, FakeMcpClient, McpAgentAdapter,
    McpAgentSettings, McpTransportKind, OutputStream, StartRunRequest, ENV_MCP_LIVE_ENDPOINT,
};

/// BDD-PD-MCP-LIVE-SMOKE-01: Live connect／tool／stream reconcile or clear NOT RUN.
#[test]
fn live_mcp_smoke_connect_tool_or_skip() {
    let Some(target) = probe_mcp_live_smoke_target() else {
        eprintln!(
            "PD-MCP-LIVE-SMOKE-01 NOT RUN: no activatable MCP Live target \
             (set {ENV_MCP_LIVE_ENDPOINT} to a local endpoint; \
             empty／:8788／:8787 → skip). Skip is OK — not a Live PASS."
        );
        return;
    };

    assert!(
        is_mcp_endpoint_activatable(&target.endpoint),
        "probe must only return activatable endpoints"
    );
    assert!(
        !target.endpoint.contains(":8788") && !target.endpoint.contains(":8787"),
        "reserved mailbox ports must never be smoked"
    );

    let mut settings = McpAgentSettings::defaults();
    settings.transport = if target.endpoint.starts_with("stdio:") {
        McpTransportKind::Stdio
    } else {
        McpTransportKind::LocalHttpSse
    };
    settings.server_name = target.server_name.clone();
    settings.endpoint = target.endpoint.clone();
    settings.approved_tools = vec![target.tool.clone()];
    // Inject a secret that must never appear in projection.
    settings.secret_token = Some("must-not-leak-in-projection".into());

    let mut doc = AgentSettingsDocument::defaults();
    doc.mcp = settings.clone();
    let proj = doc.projection();
    assert!(proj.mcp.has_secret);
    let proj_dbg = format!("{proj:?}");
    assert!(
        !proj_dbg.contains("must-not-leak-in-projection"),
        "projection leaked secret: {proj_dbg}"
    );

    let mut agent = McpAgentAdapter::new(settings, Box::new(FakeMcpClient::default()));
    let run = agent
        .start_run(
            StartRunRequest::mcp_live(target.tool.clone()).with_binding(
                std::env::temp_dir().to_string_lossy().as_ref(),
                "PD-MCP-LIVE-SMOKE-01",
                "live-mcp-smoke-fp",
            ),
        )
        .unwrap_or_else(|e| panic!("live start_run: {e}"));

    let events = agent
        .poll_chunks(run)
        .unwrap_or_else(|e| panic!("poll_chunks: {e}"));

    assert!(
        matches!(
            events.first(),
            Some(AgentChunk::Started {
                dry_run: false,
                provider: AgentProvider::Mcp,
                ..
            })
        ),
        "expected Live Started(dry_run=false); DryRun must not count as Live PASS; got {:?}",
        events.first()
    );

    let has_progress_or_chunk = events.iter().any(|e| {
        matches!(
            e,
            AgentChunk::Progress { .. }
                | AgentChunk::Chunk {
                    stream: OutputStream::Stdout | OutputStream::Stderr,
                    ..
                }
        )
    });
    assert!(
        has_progress_or_chunk,
        "expected Progress and/or Chunk (tool／stream reconcile); events={events:?}"
    );

    let tool_marker = format!("[mcp-tool:{}]", target.tool);
    assert!(
        events.iter().any(|e| matches!(
            e,
            AgentChunk::Chunk { text, .. } if text.contains(&tool_marker)
        )),
        "expected tool chunk marker {tool_marker}; events={events:?}"
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
        "PD-MCP-LIVE-SMOKE-01 PASS: endpoint={} tool={} server={} events={} (Live, not DryRun)",
        target.endpoint,
        target.tool,
        target.server_name,
        events.len()
    );
}
