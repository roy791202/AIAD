//! PD-M2-E2E-LOOP-01 — M2 closed-loop integration (board＋git＋Provider DryRun).
//!
//! BDD-PD-M2-E2E-LOOP-01: re-runnable chain of `load_board_file` (or equivalent)＋
//! `summarize_worktree`＋Cli｜Mcp DryRun `start_run`→chunk／exit events.
//! Missing OS deps (git binary／board file) → explicit skip／NOT RUN.
//! This test **never** implies full Live PASS — DryRun only; no DCC.

use sgenaxis_adapters::fake::status_with_modified;
use sgenaxis_adapters::{
    summarize_worktree, FakeFileSystem, FakeGit, FakeProcess, StdFileSystem, StdGit,
};
use sgenaxis_exec::{
    drain_until_terminal, AgentChunk, AgentPort, AgentProvider, AgentRouter, CliAgentAdapter,
    ExitClassification, McpAgentAdapter, StartRunRequest, StubMcpClient,
};
use sgenaxis_host::load_board_file;
use sgenaxis_ports::{GitCommit, GitPort};

const BOARD_PATH: &str = "/fixture/docs/PROJECT-BOARD.html";
const REPO: &str = "/fixture/repo";
const MINI_BOARD: &str = r#"<!DOCTYPE html><html><body>
<script type="application/json" id="board-snapshot">
{
  "asOf": "2026-10-24T13:00:00+08:00",
  "version": "m2-e2e",
  "tasks": [
    {"id": "PD-M2-E2E-LOOP-01", "title": "M2 loop", "zone": "yellow"},
    {"id": "PD-BOARD-LIVE-01", "title": "board", "zone": "green"}
  ]
}
</script>
</body></html>"#;

fn dry_router() -> AgentRouter {
    AgentRouter::new(
        CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),
        McpAgentAdapter::with_defaults(Box::new(StubMcpClient)),
    )
}

fn assert_dry_run_chain(events: &[AgentChunk], provider: AgentProvider) {
    assert!(
        !events.is_empty(),
        "expected DryRun events for {provider:?}"
    );
    assert!(
        matches!(
            &events[0],
            AgentChunk::Started {
                provider: p,
                dry_run: true,
                ..
            } if *p == provider
        ),
        "first event must be Started dry_run=true for {provider:?}: {:?}",
        events[0]
    );
    let has_body = events.iter().any(|e| {
        matches!(
            e,
            AgentChunk::Chunk { .. } | AgentChunk::Progress { .. }
        )
    });
    assert!(
        has_body,
        "expected chunk and/or progress before exit for {provider:?}: {events:?}"
    );
    assert!(
        matches!(
            events.last(),
            Some(AgentChunk::Exited {
                classification: ExitClassification::Success,
                ..
            })
        ),
        "terminal must be Exited Success (DryRun) for {provider:?}: {events:?}"
    );
}

/// Core closed loop on Fake ports — always runnable (no Live／no DCC).
#[test]
fn m2_e2e_loop_board_git_cli_mcp_dryrun_chain() {
    // ── 1) Board load (PD-BOARD-LIVE-01 API) ───────────────────────────────
    let fs = FakeFileSystem::new();
    fs.seed(BOARD_PATH, MINI_BOARD.as_bytes());
    let snap = load_board_file(&fs, BOARD_PATH).expect("load_board_file");
    assert!(
        snap.tasks.iter().any(|t| t.id == "PD-M2-E2E-LOOP-01"),
        "board must contain PD-M2-E2E-LOOP-01: {:?}",
        snap.tasks
    );

    // ── 2) Git summarize (PD-GIT-01 FakeGit) ───────────────────────────────
    let git = FakeGit::new();
    git.set_status(REPO, status_with_modified("m2-e2e", "crates/sgenaxis-host/tests/m2_e2e_loop.rs"));
    git.set_log(
        REPO,
        vec![GitCommit {
            hash: "abc1234".into(),
            subject: "PD-M2-E2E-LOOP-01 fixture".into(),
        }],
    );
    git.set_diff(REPO, "diff --git a/fixture b/fixture\n");
    let summary = summarize_worktree(&git, REPO, 5).expect("summarize_worktree FakeGit");
    assert_eq!(summary.repo, REPO);
    assert_eq!(summary.branch.as_deref(), Some("m2-e2e"));
    assert_eq!(summary.entry_count, 1);
    assert!(!summary.writes_enabled, "summarize is read-only");

    // ── 3) Cli DryRun start→chunk／exit (PD-EXEC-CLI) ──────────────────────
    let mut exec = dry_router();
    let cli_run = exec
        .start_run(StartRunRequest::cli_dry_run().with_binding(
            REPO,
            "PD-M2-E2E-LOOP-01",
            "m2-e2e-fp",
        ))
        .expect("cli dry start_run");
    let cli_events = drain_until_terminal(&mut exec, cli_run, 8).expect("cli drain");
    assert_dry_run_chain(&cli_events, AgentProvider::Cli);

    // ── 4) Mcp DryRun start→chunk／exit (PD-EXEC-MCP) ──────────────────────
    let mcp_run = exec
        .start_run(StartRunRequest::mcp_dry_run().with_binding(
            REPO,
            "PD-M2-E2E-LOOP-01",
            "m2-e2e-fp",
        ))
        .expect("mcp dry start_run");
    let mcp_events = drain_until_terminal(&mut exec, mcp_run, 8).expect("mcp drain");
    assert_dry_run_chain(&mcp_events, AgentProvider::Mcp);

    eprintln!(
        "PD-M2-E2E-LOOP-01 PASS (DryRun chain only): board＋FakeGit＋Cli｜Mcp \
         start→chunk／exit. NOT a full Live PASS — Live／DCC intentionally not forced."
    );
}

/// Optional StdGit summarize against the real workspace — skip／NOT RUN if git missing.
#[test]
fn m2_e2e_std_git_summarize_or_not_run() {
    let repo = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../..")
        .canonicalize()
        .unwrap_or_else(|_| {
            std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("../../..")
                .to_path_buf()
        });
    let repo_str = repo.to_string_lossy().to_string();

    let git = StdGit::new();
    match git.status(&repo_str) {
        Ok(_) => {
            let summary = summarize_worktree(&git as &dyn GitPort, &repo_str, 3)
                .expect("StdGit summarize_worktree");
            assert_eq!(summary.repo, repo_str);
            assert!(!summary.writes_enabled);
            eprintln!(
                "PD-M2-E2E-LOOP-01 StdGit summarize OK (read-only); still DryRun-only for EXEC."
            );
        }
        Err(e) => {
            eprintln!(
                "PD-M2-E2E-LOOP-01 NOT RUN (StdGit): git unavailable or not a repo — {e}. \
                 FakeGit path remains the mandatory DryRun chain."
            );
            // Explicit skip semantics: do not fail the suite.
        }
    }
}

/// Optional real board file via StdFileSystem — skip／NOT RUN if path absent.
#[test]
fn m2_e2e_std_board_load_or_not_run() {
    let board = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("../../../../docs/PROJECT-BOARD.html");
    let fs = StdFileSystem::new();
    let path = board.to_string_lossy();
    match load_board_file(&fs, path.as_ref()) {
        Ok(snap) => {
            assert!(
                !snap.tasks.is_empty(),
                "real board loaded but tasks empty"
            );
            eprintln!(
                "PD-M2-E2E-LOOP-01 Std board load OK ({} tasks); write-back not exercised here.",
                snap.tasks.len()
            );
        }
        Err(e) => {
            eprintln!(
                "PD-M2-E2E-LOOP-01 NOT RUN (Std board): {e}. \
                 FakeFileSystem load_board_file remains the mandatory path."
            );
        }
    }
}
