//! AgentPort — EXEC Provider surface (mode A/B share this shape).

use crate::error::ExecError;
use crate::events::AgentChunk;

/// Opaque run handle.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct RunId(pub u64);

/// Provider kind selected by UI／FLOW (`Cli` | `Mcp`).
///
/// Leaf adapters accept one kind; [`crate::AgentRouter`] switches on `start_run`.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AgentProvider {
    Cli,
    Mcp,
}

/// Demo binding used by DryRun helpers (tests／docs). Production callers must pass real values.
pub const DEMO_PROJECT_ROOT: &str = "/demo/root";
pub const DEMO_WORK_ITEM_ID: &str = "demo-work";
pub const DEMO_WORKTREE_FINGERPRINT: &str = "demo-fingerprint";

/// `start_run` request — **must** bind project root／work item／worktree fingerprint
/// (PD-EXEC-BIND-01 / PRODUCT-DEVELOPMENT §6.2).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StartRunRequest {
    pub provider: AgentProvider,
    pub dry_run: bool,
    pub project_root: String,
    pub work_item_id: String,
    pub worktree_fingerprint: String,
    /// MCP live tool name (PD-MCP-LIVE-01). Ignored for CLI／DryRun.
    /// When `None` on live MCP, adapter uses the first approved tool if any.
    pub mcp_tool: Option<String>,
    /// Optional JSON args for [`Self::mcp_tool`] (live MCP only).
    pub mcp_tool_args: Option<String>,
}

impl StartRunRequest {
    fn with_demo_binding(provider: AgentProvider, dry_run: bool) -> Self {
        Self {
            provider,
            dry_run,
            project_root: DEMO_PROJECT_ROOT.into(),
            work_item_id: DEMO_WORK_ITEM_ID.into(),
            worktree_fingerprint: DEMO_WORKTREE_FINGERPRINT.into(),
            mcp_tool: None,
            mcp_tool_args: None,
        }
    }

    pub fn cli_dry_run() -> Self {
        Self::with_demo_binding(AgentProvider::Cli, true)
    }

    /// Live CLI via ProcessPort — requires approved settings + feature `real-spawn`.
    pub fn cli_live() -> Self {
        Self::with_demo_binding(AgentProvider::Cli, false)
    }

    pub fn mcp_dry_run() -> Self {
        Self::with_demo_binding(AgentProvider::Mcp, true)
    }

    /// Live MCP run requesting an approved tool (requires feature `real-mcp`).
    pub fn mcp_live(tool: impl Into<String>) -> Self {
        Self {
            mcp_tool: Some(tool.into()),
            ..Self::with_demo_binding(AgentProvider::Mcp, false)
        }
    }

    /// Attach／override Run binding fields (PD-EXEC-BIND-01).
    pub fn with_binding(
        mut self,
        project_root: impl Into<String>,
        work_item_id: impl Into<String>,
        worktree_fingerprint: impl Into<String>,
    ) -> Self {
        self.project_root = project_root.into();
        self.work_item_id = work_item_id.into();
        self.worktree_fingerprint = worktree_fingerprint.into();
        self
    }
}

/// Agent EXEC port: start, stream chunks, cancel, exit classification via events.
pub trait AgentPort: Send {
    /// Start a run. On success, subsequent [`poll_chunks`] yield the event stream.
    ///
    /// Rejects when project root／work item／fingerprint are missing (PD-EXEC-BIND-01).
    fn start_run(&mut self, req: StartRunRequest) -> Result<RunId, ExecError>;

    /// Non-blocking drain of queued [`AgentChunk`] events for `run`.
    fn poll_chunks(&mut self, run: RunId) -> Result<Vec<AgentChunk>, ExecError>;

    /// Request cancel. Emits `Exited { Cancelled }` (or Failed) when drained.
    fn cancel(&mut self, run: RunId) -> Result<(), ExecError>;
}
