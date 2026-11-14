//! CLI path／args + MCP settings (PRODUCT-DEVELOPMENT §6.3 — settings page keys).
//!
//! PD-SET-01: CLI／MCP partitions; invalid path not activatable; secrets omitted from projection.

use std::fmt;

use sgenaxis_ports::FileSystemPort;

/// Config keys／labels for known Agent CLIs (path + args only; no secrets).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum CliToolKind {
    Claude,
    CursorAgent,
    Codex,
    Antigravity,
}

impl CliToolKind {
    /// Stable settings／config key string.
    pub fn config_key(self) -> &'static str {
        match self {
            CliToolKind::Claude => "claude",
            CliToolKind::CursorAgent => "cursor-agent",
            CliToolKind::Codex => "codex",
            CliToolKind::Antigravity => "antigravity",
        }
    }

    /// Human-facing label (UI).
    pub fn label(self) -> &'static str {
        match self {
            CliToolKind::Claude => "Claude",
            CliToolKind::CursorAgent => "cursor-agent",
            CliToolKind::Codex => "Codex",
            CliToolKind::Antigravity => "Antigravity",
        }
    }
}

/// Path + argv for one CLI tool.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct CliToolConfig {
    pub path: String,
    pub args: Vec<String>,
}

impl CliToolConfig {
    pub fn new(path: impl Into<String>, args: impl IntoIterator<Item = impl Into<String>>) -> Self {
        Self {
            path: path.into(),
            args: args.into_iter().map(Into::into).collect(),
        }
    }
}

/// Settings store for Provider A (CLI). Separate from MCP settings (`PD-EXEC-MCP`).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct CliAgentSettings {
    pub selected: CliToolKind,
    pub claude: CliToolConfig,
    pub cursor_agent: CliToolConfig,
    pub codex: CliToolConfig,
    pub antigravity: CliToolConfig,
    /// Host／settings gate for true ProcessPort spawn (PD-EXEC-LIVE-01).
    /// Mirrored from host `agent_active` when wired; default false keeps DryRun-only.
    #[serde(default)]
    pub live_approved: bool,
}

impl Default for CliAgentSettings {
    fn default() -> Self {
        Self::defaults()
    }
}

impl CliAgentSettings {
    /// Sensible empty／placeholder defaults (user fills paths in settings UI later).
    pub fn defaults() -> Self {
        Self {
            selected: CliToolKind::Claude,
            claude: CliToolConfig::new("claude", ["--print"]),
            cursor_agent: CliToolConfig::new("cursor-agent", [] as [&str; 0]),
            codex: CliToolConfig::new("codex", ["exec"]),
            antigravity: CliToolConfig::new("antigravity", [] as [&str; 0]),
            live_approved: false,
        }
    }

    /// Approve live CLI spawn once the selected path is activatable on `fs`.
    pub fn approve_live(&mut self, fs: &dyn FileSystemPort) -> Result<(), SettingsError> {
        let path = self.selected_config().path.clone();
        if !is_cli_path_activatable(&path, fs) {
            return Err(SettingsError::InvalidPathNotActivatable(path));
        }
        self.live_approved = true;
        Ok(())
    }

    /// Revoke live approval — DryRun remains available.
    pub fn revoke_live(&mut self) {
        self.live_approved = false;
    }

    pub fn selected_config(&self) -> &CliToolConfig {
        match self.selected {
            CliToolKind::Claude => &self.claude,
            CliToolKind::CursorAgent => &self.cursor_agent,
            CliToolKind::Codex => &self.codex,
            CliToolKind::Antigravity => &self.antigravity,
        }
    }

    pub fn config_mut(&mut self, kind: CliToolKind) -> &mut CliToolConfig {
        match kind {
            CliToolKind::Claude => &mut self.claude,
            CliToolKind::CursorAgent => &mut self.cursor_agent,
            CliToolKind::Codex => &mut self.codex,
            CliToolKind::Antigravity => &mut self.antigravity,
        }
    }

    /// Activate `kind` as selected only when its path exists on `fs`.
    pub fn try_activate(
        &mut self,
        kind: CliToolKind,
        fs: &dyn FileSystemPort,
    ) -> Result<(), SettingsError> {
        let path = self.config_mut(kind).path.clone();
        if !is_cli_path_activatable(&path, fs) {
            return Err(SettingsError::InvalidPathNotActivatable(path));
        }
        self.selected = kind;
        Ok(())
    }

    /// UI projection for the CLI partition (no secrets — CLI has none).
    pub fn projection(&self) -> CliSettingsProjection {
        CliSettingsProjection {
            selected: self.selected,
            claude_path: self.claude.path.clone(),
            cursor_agent_path: self.cursor_agent.path.clone(),
            codex_path: self.codex.path.clone(),
            antigravity_path: self.antigravity.path.clone(),
            claude_args: self.claude.args.clone(),
            cursor_agent_args: self.cursor_agent.args.clone(),
            codex_args: self.codex.args.clone(),
            antigravity_args: self.antigravity.args.clone(),
        }
    }
}

/// How the MCP client reaches a **user-explicit local** target (PRODUCT-DEVELOPMENT §6.3 mode B).
///
/// Prefer **stdio** (spawn local MCP server process) or **local HTTP／SSE** (loopback only).
/// Never treat this as a cloud arbitrary gateway. Do **not** use HoneyBadger `:8788` or
/// reserved `:8787`. Live connection is opt-in (`real-mcp`); default tests use DryRun only.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, serde::Serialize, serde::Deserialize)]
pub enum McpTransportKind {
    /// Local stdio MCP server (command + args supplied by user later; DryRun ignores).
    Stdio,
    /// Loopback HTTP／SSE endpoint the user named (e.g. `http://127.0.0.1:<user-port>/sse`).
    LocalHttpSse,
}

impl McpTransportKind {
    pub fn config_key(self) -> &'static str {
        match self {
            McpTransportKind::Stdio => "stdio",
            McpTransportKind::LocalHttpSse => "local-http-sse",
        }
    }
}

/// Full MCP settings store (may hold secrets for live connect — **never** project these).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct McpAgentSettings {
    pub transport: McpTransportKind,
    /// Server display／registry name (user-chosen).
    pub server_name: String,
    /// Endpoint for LocalHttpSse, or stdio command path placeholder for Stdio.
    /// Must be a user-explicit local target when live; DryRun does not dial.
    pub endpoint: String,
    /// Approved tool name allowlist (empty = deny-all for live; DryRun still simulates).
    pub approved_tools: Vec<String>,
    /// Optional auth material for live MCP — **excluded** from [`McpSettingsProjection`].
    pub secret_token: Option<String>,
}

impl Default for McpAgentSettings {
    fn default() -> Self {
        Self::defaults()
    }
}

impl McpAgentSettings {
    /// Safe placeholders — no live dial; no default secret.
    pub fn defaults() -> Self {
        Self {
            transport: McpTransportKind::Stdio,
            server_name: "local-agent".into(),
            // Placeholder only; live path must use an endpoint the user set explicitly.
            endpoint: "stdio://local-agent".into(),
            approved_tools: vec!["list_tools".into()],
            secret_token: None,
        }
    }

    /// UI／Dirty projection DTO — **no** `secret_token` or other secrets.
    pub fn projection(&self) -> McpSettingsProjection {
        McpSettingsProjection {
            transport: self.transport,
            server_name: self.server_name.clone(),
            endpoint: self.endpoint.clone(),
            approved_tools: self.approved_tools.clone(),
            has_secret: self.secret_token.as_ref().is_some_and(|s| !s.is_empty()),
        }
    }

    pub fn is_tool_approved(&self, tool: &str) -> bool {
        self.approved_tools.iter().any(|t| t == tool)
    }
}

/// Projection DTO for settings UI／Run log — secrets must not appear here.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct McpSettingsProjection {
    pub transport: McpTransportKind,
    pub server_name: String,
    pub endpoint: String,
    pub approved_tools: Vec<String>,
    /// Whether a secret is configured — never the secret value itself.
    pub has_secret: bool,
}

/// CLI partition projection for settings UI.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CliSettingsProjection {
    pub selected: CliToolKind,
    pub claude_path: String,
    pub cursor_agent_path: String,
    pub codex_path: String,
    pub antigravity_path: String,
    pub claude_args: Vec<String>,
    pub cursor_agent_args: Vec<String>,
    pub codex_args: Vec<String>,
    pub antigravity_args: Vec<String>,
}

/// Combined CLI + MCP settings document (PD-SET-01 partitions).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct AgentSettingsDocument {
    pub cli: CliAgentSettings,
    pub mcp: McpAgentSettings,
}

impl Default for AgentSettingsDocument {
    fn default() -> Self {
        Self::defaults()
    }
}

impl AgentSettingsDocument {
    pub fn defaults() -> Self {
        Self {
            cli: CliAgentSettings::defaults(),
            mcp: McpAgentSettings::defaults(),
        }
    }

    /// Combined projection — **never** includes `secret_token` values.
    pub fn projection(&self) -> AgentSettingsProjection {
        AgentSettingsProjection {
            cli: self.cli.projection(),
            mcp: self.mcp.projection(),
        }
    }

    pub fn to_json(&self) -> Result<String, SettingsError> {
        serde_json::to_string_pretty(self).map_err(|e| SettingsError::Io(e.to_string()))
    }

    pub fn from_json(raw: &str) -> Result<Self, SettingsError> {
        serde_json::from_str(raw).map_err(|e| SettingsError::Io(e.to_string()))
    }
}

/// Combined projection for UI／Dirty — secrets omitted.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgentSettingsProjection {
    pub cli: CliSettingsProjection,
    pub mcp: McpSettingsProjection,
}

/// Settings validation／persist errors (PD-SET-01).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SettingsError {
    /// Path／endpoint cannot be stored or selected as the active configuration.
    InvalidPathNotActivatable(String),
    Io(String),
}

impl fmt::Display for SettingsError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            SettingsError::InvalidPathNotActivatable(p) => {
                write!(f, "invalid path not activatable: {p}")
            }
            SettingsError::Io(s) => write!(f, "settings io: {s}"),
        }
    }
}

impl std::error::Error for SettingsError {}

/// CLI path is activatable iff non-empty (trimmed) and `fs.exists(path)`.
pub fn is_cli_path_activatable(path: &str, fs: &dyn FileSystemPort) -> bool {
    let t = path.trim();
    if t.is_empty() {
        return false;
    }
    fs.exists(t).unwrap_or(false)
}

/// MCP endpoint activatable iff non-empty and not reserved `:8788`／`:8787`.
pub fn is_mcp_endpoint_activatable(endpoint: &str) -> bool {
    let t = endpoint.trim();
    if t.is_empty() {
        return false;
    }
    // Never activate HoneyBadger／reserved mailbox ports.
    if t.contains(":8788") || t.contains(":8787") {
        return false;
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::fake::FakeFileSystem;

    #[test]
    fn document_has_cli_and_mcp_partitions() {
        let doc = AgentSettingsDocument::defaults();
        let p = doc.projection();
        assert_eq!(p.cli.selected, CliToolKind::Claude);
        assert_eq!(p.mcp.server_name, "local-agent");
        assert!(!p.mcp.has_secret);
        // Distinct partitions
        assert!(!p.cli.claude_path.is_empty());
        assert!(!p.mcp.endpoint.is_empty());
    }

    #[test]
    fn empty_cli_path_not_activatable() {
        let fs = FakeFileSystem::new();
        assert!(!is_cli_path_activatable("", &fs));
        assert!(!is_cli_path_activatable("   ", &fs));
    }

    #[test]
    fn missing_cli_path_not_activatable() {
        let fs = FakeFileSystem::new();
        assert!(!is_cli_path_activatable("/no/such/tool", &fs));
    }

    #[test]
    fn existing_cli_path_activatable() {
        let fs = FakeFileSystem::new();
        fs.seed("/bin/claude", b"");
        assert!(is_cli_path_activatable("/bin/claude", &fs));
    }

    #[test]
    fn try_activate_rejects_invalid_keeps_selected() {
        let fs = FakeFileSystem::new();
        let mut cli = CliAgentSettings::defaults();
        cli.selected = CliToolKind::Claude;
        cli.codex.path = "/missing/codex".into();
        let err = cli
            .try_activate(CliToolKind::Codex, &fs)
            .expect_err("must fail");
        assert!(matches!(err, SettingsError::InvalidPathNotActivatable(_)));
        assert_eq!(cli.selected, CliToolKind::Claude);
    }

    #[test]
    fn try_activate_accepts_existing_path() {
        let fs = FakeFileSystem::new();
        fs.seed("/bin/codex", b"");
        let mut cli = CliAgentSettings::defaults();
        cli.codex.path = "/bin/codex".into();
        cli.try_activate(CliToolKind::Codex, &fs).expect("ok");
        assert_eq!(cli.selected, CliToolKind::Codex);
    }

    #[test]
    fn projection_omits_secret_token_value() {
        let mut doc = AgentSettingsDocument::defaults();
        doc.mcp.secret_token = Some("super-secret-token".into());
        let p = doc.projection();
        assert!(p.mcp.has_secret);
        let debug = format!("{p:?}");
        assert!(!debug.contains("super-secret-token"));
        // Field must not exist on projection type — only has_secret flag.
        assert_eq!(p.mcp.endpoint, doc.mcp.endpoint);
    }

    #[test]
    fn mcp_reserved_ports_not_activatable() {
        assert!(!is_mcp_endpoint_activatable("http://127.0.0.1:8788/sse"));
        assert!(!is_mcp_endpoint_activatable("http://127.0.0.1:8787/events"));
        assert!(is_mcp_endpoint_activatable("http://127.0.0.1:3920/sse"));
        assert!(is_mcp_endpoint_activatable("stdio://local-agent"));
        assert!(!is_mcp_endpoint_activatable(""));
    }
}
