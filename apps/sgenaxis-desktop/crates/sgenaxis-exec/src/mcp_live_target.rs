//! MCP Live smoke target probe (PD-MCP-LIVE-SMOKE-01) — env gate only; **never** dials.
//!
//! BDD-PD-MCP-LIVE-SMOKE-01: under approval, Live connect／tool against an **explicit**
//! local MCP endpoint from env, or clear `NOT RUN` when unset／unactivatable.
//! Secrets never enter the probe DTO (coordinate with PD-LIVE-TARGET-01 projection rules).

use crate::settings::is_mcp_endpoint_activatable;

/// Env: explicit local MCP endpoint for Live smoke (required to leave NOT RUN).
pub const ENV_MCP_LIVE_ENDPOINT: &str = "SGENAXIS_MCP_LIVE_ENDPOINT";
/// Env: approved tool name (default `list_tools`).
pub const ENV_MCP_LIVE_TOOL: &str = "SGENAXIS_MCP_LIVE_TOOL";
/// Env: server display name (default `local-smoke`).
pub const ENV_MCP_LIVE_SERVER: &str = "SGENAXIS_MCP_LIVE_SERVER";

/// Secret-free MCP Live smoke target (endpoint／tool／server only).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct McpLiveSmokeTarget {
    pub endpoint: String,
    pub tool: String,
    pub server_name: String,
}

/// Probe env for an activatable MCP Live smoke target.
///
/// - Missing／empty endpoint → `None` (caller must treat as **NOT RUN**, never Live PASS).
/// - Reserved `:8788`／`:8787` or otherwise unactivatable → `None` (NOT RUN; never dial).
/// - Never reads or returns secrets／tokens.
pub fn probe_mcp_live_smoke_target() -> Option<McpLiveSmokeTarget> {
    let endpoint = std::env::var(ENV_MCP_LIVE_ENDPOINT).ok()?;
    let endpoint = endpoint.trim().to_string();
    if endpoint.is_empty() || !is_mcp_endpoint_activatable(&endpoint) {
        return None;
    }
    let tool = std::env::var(ENV_MCP_LIVE_TOOL)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "list_tools".into());
    let server_name = std::env::var(ENV_MCP_LIVE_SERVER)
        .ok()
        .map(|s| s.trim().to_string())
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| "local-smoke".into());
    Some(McpLiveSmokeTarget {
        endpoint,
        tool,
        server_name,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    /// Serialize env mutations across tests in this module.
    static ENV_LOCK: Mutex<()> = Mutex::new(());

    fn clear_mcp_live_env() {
        std::env::remove_var(ENV_MCP_LIVE_ENDPOINT);
        std::env::remove_var(ENV_MCP_LIVE_TOOL);
        std::env::remove_var(ENV_MCP_LIVE_SERVER);
    }

    #[test]
    fn missing_endpoint_is_none_not_run() {
        let _g = ENV_LOCK.lock().expect("env lock");
        clear_mcp_live_env();
        assert!(probe_mcp_live_smoke_target().is_none());
    }

    #[test]
    fn reserved_8788_is_none_not_run() {
        let _g = ENV_LOCK.lock().expect("env lock");
        clear_mcp_live_env();
        std::env::set_var(ENV_MCP_LIVE_ENDPOINT, "http://127.0.0.1:8788/sse");
        assert!(probe_mcp_live_smoke_target().is_none());
        clear_mcp_live_env();
    }

    #[test]
    fn activatable_endpoint_returns_target_without_secret() {
        let _g = ENV_LOCK.lock().expect("env lock");
        clear_mcp_live_env();
        std::env::set_var(ENV_MCP_LIVE_ENDPOINT, "http://127.0.0.1:3920/sse");
        std::env::set_var(ENV_MCP_LIVE_TOOL, "list_tools");
        std::env::set_var(ENV_MCP_LIVE_SERVER, "smoke-srv");
        let t = probe_mcp_live_smoke_target().expect("target");
        assert_eq!(t.endpoint, "http://127.0.0.1:3920/sse");
        assert_eq!(t.tool, "list_tools");
        assert_eq!(t.server_name, "smoke-srv");
        let dbg = format!("{t:?}");
        assert!(!dbg.to_lowercase().contains("secret"));
        clear_mcp_live_env();
    }
}
