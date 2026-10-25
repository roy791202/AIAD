//! MCP client port — trait-based seam for live MCP (feature `real-mcp`).
//!
//! Transport notes (PRODUCT-DEVELOPMENT §6.3 mode B):
//! - Prefer **stdio** (local MCP server subprocess) or **local HTTP／SSE** (loopback).
//! - Connect **only** to user-explicit local targets from settings (`endpoint`／`server_name`).
//! - Do **not** dial HoneyBadger mailbox `:8788` or reserved `:8787`.
//! - Tool calls go through [`McpClientPort::call_tool`]; adapter enforces `approved_tools`.
//! - Default unit tests never dial; [`McpAgentAdapter`](crate::McpAgentAdapter) DryRun
//!   simulates `AgentChunk` without network. Live tests use [`FakeMcpClient`].

use crate::error::ExecError;
use crate::settings::McpAgentSettings;

/// Opaque session handle for a live MCP connection (adapter-owned).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct McpSessionId(pub u64);

/// Minimal MCP client surface. Real protocol (initialize／tools／notifications) is
/// behind feature `real-mcp`; without the feature the adapter returns
/// [`ExecError::RealMcpDisabled`] before calling the client (after approval gates).
pub trait McpClientPort: Send {
    /// Open a session to the configured **local** target. Must not be used in DryRun.
    /// Caller (adapter) must already have rejected unapproved endpoints.
    fn connect(&mut self, settings: &McpAgentSettings) -> Result<McpSessionId, ExecError>;

    /// Invoke an approved tool on an open session. Returns textual／JSON result payload.
    fn call_tool(
        &mut self,
        session: McpSessionId,
        tool: &str,
        args_json: &str,
    ) -> Result<String, ExecError>;

    /// Best-effort cancel／close. No force-kill of unrelated processes.
    fn disconnect(&mut self, session: McpSessionId) -> Result<(), ExecError>;
}

/// Refuses live connect — safe default when `real-mcp` is off or host wants no dial.
#[derive(Debug, Default)]
pub struct StubMcpClient;

impl McpClientPort for StubMcpClient {
    fn connect(&mut self, _settings: &McpAgentSettings) -> Result<McpSessionId, ExecError> {
        Err(ExecError::RealMcpDisabled)
    }

    fn call_tool(
        &mut self,
        _session: McpSessionId,
        _tool: &str,
        _args_json: &str,
    ) -> Result<String, ExecError> {
        Err(ExecError::RealMcpDisabled)
    }

    fn disconnect(&mut self, _session: McpSessionId) -> Result<(), ExecError> {
        Ok(())
    }
}

/// In-process fake for `real-mcp` tests — does **not** open sockets or spawn MCP servers.
///
/// Still requires settings to name a user-explicit local target; the values are recorded
/// only for assertions, never dialed.
#[derive(Debug, Default)]
pub struct FakeMcpClient {
    next: u64,
    pub last_endpoint: Option<String>,
    pub last_server_name: Option<String>,
    pub connect_count: u64,
    pub last_tool: Option<String>,
    pub last_tool_args: Option<String>,
    pub call_tool_count: u64,
    /// When set, `connect` returns this error (observable failure).
    pub fail_connect: Option<String>,
    /// When set, `call_tool` returns this error (observable failure).
    pub fail_call_tool: Option<String>,
}

impl McpClientPort for FakeMcpClient {
    fn connect(&mut self, settings: &McpAgentSettings) -> Result<McpSessionId, ExecError> {
        if let Some(msg) = &self.fail_connect {
            return Err(ExecError::Mcp(msg.clone()));
        }
        self.last_endpoint = Some(settings.endpoint.clone());
        self.last_server_name = Some(settings.server_name.clone());
        self.connect_count = self.connect_count.saturating_add(1);
        self.next = self.next.saturating_add(1);
        Ok(McpSessionId(self.next))
    }

    fn call_tool(
        &mut self,
        session: McpSessionId,
        tool: &str,
        args_json: &str,
    ) -> Result<String, ExecError> {
        if session.0 == 0 || session.0 > self.next {
            return Err(ExecError::Mcp(format!("unknown session {}", session.0)));
        }
        if let Some(msg) = &self.fail_call_tool {
            return Err(ExecError::Mcp(msg.clone()));
        }
        self.last_tool = Some(tool.to_string());
        self.last_tool_args = Some(args_json.to_string());
        self.call_tool_count = self.call_tool_count.saturating_add(1);
        Ok(format!(
            "{{\"ok\":true,\"tool\":\"{tool}\",\"args\":{args_json}}}"
        ))
    }

    fn disconnect(&mut self, _session: McpSessionId) -> Result<(), ExecError> {
        Ok(())
    }
}
