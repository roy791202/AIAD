//! SGenAxis **EXEC** — Agent Providers A (CLI) + B (local MCP) per PRODUCT-DEVELOPMENT §6.3.
//!
//! ```text
//! start_run { provider: Cli | Mcp, dry_run, project_root, work_item_id, worktree_fingerprint }
//!   → require_run_binding (PD-EXEC-BIND-01)
//!   → AgentRouter
//!        ├─ CliAgentAdapter
//!        │     ├─ DryRun  → simulated AgentChunk (no ProcessPort spawn)
//!        │     └─ live (real-spawn + live_approved) → ProcessPort
//!        │           stdout／stderr → AgentChunk::Chunk; exit via try_wait
//!        └─ McpAgentAdapter
//!              ├─ DryRun  → simulated AgentChunk (no network)
//!              └─ real-mcp feature → McpClientPort (stdio / local HTTP／SSE)
//! ```
//!
//! MCP connects **only** to user-explicit local targets; never `:8788`／`:8787`.
//! Secrets stay in [`McpAgentSettings`]; use [`McpSettingsProjection`] for UI.
//!
//! PD-LIVE-TARGET-01: [`probe_live_cli_targets`] detects PATH／settings CLIs without spawning;
//! empty → explicit `NOT RUN` for PD-LIVE-CLI-SMOKE-01.
//!
//! PD-MCP-LIVE-SMOKE-01: [`probe_mcp_live_smoke_target`] reads env-gated MCP endpoint;
//! missing／unactivatable → explicit `NOT RUN` (never forge Live PASS from DryRun).

#![forbid(unsafe_code)]

mod bind;
mod cli;
mod error;
mod events;
mod host_settings;
mod live_target;
mod mcp;
mod mcp_client;
mod mcp_live_target;
mod port;
mod router;
mod settings;

pub use bind::{assert_lease_root_consistent, require_run_binding, RunBinding};
pub use cli::{drain_until_terminal, CliAgentAdapter};
pub use error::ExecError;
pub use events::{AgentChunk, ExitClassification, OutputStream};
pub use host_settings::HostSettingsStore;
pub use live_target::{
    lookup_on_path, probe_from_cli_settings, probe_live_cli_targets, LiveCliTargetHit,
    LiveTargetProbeResult, LiveTargetSettingsProjection, LiveTargetSource,
    LIVE_TARGET_STATUS_NOT_RUN, LIVE_TARGET_STATUS_PASS,
};
pub use mcp::McpAgentAdapter;
pub use mcp_client::{FakeMcpClient, McpClientPort, McpSessionId, StubMcpClient};
pub use mcp_live_target::{
    probe_mcp_live_smoke_target, McpLiveSmokeTarget, ENV_MCP_LIVE_ENDPOINT, ENV_MCP_LIVE_SERVER,
    ENV_MCP_LIVE_TOOL,
};
pub use port::{
    AgentPort, AgentProvider, RunId, StartRunRequest, DEMO_PROJECT_ROOT, DEMO_WORK_ITEM_ID,
    DEMO_WORKTREE_FINGERPRINT,
};
pub use router::AgentRouter;
pub use settings::{
    is_cli_path_activatable, is_mcp_endpoint_activatable, AgentSettingsDocument,
    AgentSettingsProjection, CliAgentSettings, CliSettingsProjection, CliToolConfig, CliToolKind,
    McpAgentSettings, McpSettingsProjection, McpTransportKind, SettingsError,
};
