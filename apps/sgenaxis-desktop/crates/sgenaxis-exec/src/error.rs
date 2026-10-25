//! EXEC errors — no OS error types leaked.

use std::fmt;

/// Failure from AgentPort / CliAgentAdapter / McpAgentAdapter.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExecError {
    UnsupportedProvider(String),
    RealSpawnDisabled,
    /// Live CLI spawn refused — settings not approved (`live_approved`／host `agent_active`).
    LiveNotApproved,
    /// Live MCP client disabled — enable feature `real-mcp` or use `dry_run: true`.
    RealMcpDisabled,
    /// Endpoint not activatable (empty or reserved `:8788`／`:8787`) — must not connect.
    EndpointNotApproved(String),
    /// Tool not on the approved allowlist — must not call.
    ToolNotApproved(String),
    /// PD-EXEC-BIND-01: `start_run` missing project root／work item／fingerprint.
    MissingBinding(String),
    /// PD-EXEC-BIND-01: request root ≠ active WORK lease bound root.
    LeaseRootMismatch {
        expected: String,
        got: String,
    },
    RunNotFound(String),
    Busy(String),
    Process(String),
    /// Live MCP client／session failure (no OS types).
    Mcp(String),
    Cancelled(String),
    Other(String),
}

impl fmt::Display for ExecError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ExecError::UnsupportedProvider(s) => write!(f, "unsupported provider: {s}"),
            ExecError::RealSpawnDisabled => write!(
                f,
                "real CLI spawn disabled (enable feature `real-spawn` or use dry_run)"
            ),
            ExecError::LiveNotApproved => write!(
                f,
                "live CLI spawn not approved (activate settings / set live_approved)"
            ),
            ExecError::RealMcpDisabled => write!(
                f,
                "real MCP client disabled (enable feature `real-mcp` or use dry_run)"
            ),
            ExecError::EndpointNotApproved(s) => {
                write!(f, "mcp endpoint not approved (must not connect): {s}")
            }
            ExecError::ToolNotApproved(s) => {
                write!(f, "mcp tool not approved (must not call): {s}")
            }
            ExecError::MissingBinding(field) => {
                write!(f, "start_run missing binding field: {field}")
            }
            ExecError::LeaseRootMismatch { expected, got } => write!(
                f,
                "start_run root mismatch vs WORK lease (expected={expected}, got={got})"
            ),
            ExecError::RunNotFound(s) => write!(f, "run not found: {s}"),
            ExecError::Busy(s) => write!(f, "busy: {s}"),
            ExecError::Process(s) => write!(f, "process: {s}"),
            ExecError::Mcp(s) => write!(f, "mcp: {s}"),
            ExecError::Cancelled(s) => write!(f, "cancelled: {s}"),
            ExecError::Other(s) => write!(f, "{s}"),
        }
    }
}

impl std::error::Error for ExecError {}
