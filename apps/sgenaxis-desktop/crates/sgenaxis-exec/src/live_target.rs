//! Live CLI target probe (PD-LIVE-TARGET-01) — PATH／host settings only; **never** spawns.
//!
//! BDD-PD-LIVE-TARGET-01: detect usable local CLIs (`claude`｜`cursor-agent`｜`codex`｜…)
//! or read host／agent settings; if none → explicit `NOT RUN`. Secrets never enter the
//! probe projection (for PD-LIVE-CLI-SMOKE-01 consumption).

use sgenaxis_ports::FileSystemPort;

use crate::settings::{
    is_cli_path_activatable, AgentSettingsProjection, CliAgentSettings, CliToolKind,
    McpSettingsProjection,
};

/// Status vocabulary for the probe artifact (never forge PASS when empty).
pub const LIVE_TARGET_STATUS_PASS: &str = "PASS";
pub const LIVE_TARGET_STATUS_NOT_RUN: &str = "NOT RUN";

/// Where a hit was discovered.
#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LiveTargetSource {
    /// Resolved via `PATH` (or equivalent env walk).
    Path,
    /// Configured path from host／agent settings that exists on `FileSystemPort`.
    HostSettings,
}

impl LiveTargetSource {
    pub fn as_str(self) -> &'static str {
        match self {
            LiveTargetSource::Path => "path",
            LiveTargetSource::HostSettings => "host_settings",
        }
    }
}

/// One detected CLI target (path only — no argv secrets／tokens).
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct LiveCliTargetHit {
    /// Stable tool key (`claude`, `cursor-agent`, …).
    pub tool: String,
    /// Absolute or resolvable path string (never a secret).
    pub path: String,
    pub source: LiveTargetSource,
}

/// Secret-free projection fragment for smoke／UI consumers.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct LiveTargetSettingsProjection {
    pub cli_selected: String,
    pub claude_path: String,
    pub cursor_agent_path: String,
    pub codex_path: String,
    pub antigravity_path: String,
    pub mcp_server_name: String,
    pub mcp_endpoint: String,
    /// Whether a secret is configured — **never** the secret value.
    pub mcp_has_secret: bool,
}

impl LiveTargetSettingsProjection {
    pub fn from_agent(p: &AgentSettingsProjection) -> Self {
        Self {
            cli_selected: p.cli.selected.config_key().to_string(),
            claude_path: p.cli.claude_path.clone(),
            cursor_agent_path: p.cli.cursor_agent_path.clone(),
            codex_path: p.cli.codex_path.clone(),
            antigravity_path: p.cli.antigravity_path.clone(),
            mcp_server_name: p.mcp.server_name.clone(),
            mcp_endpoint: p.mcp.endpoint.clone(),
            mcp_has_secret: p.mcp.has_secret,
        }
    }

    pub fn from_cli_and_mcp(cli: &CliAgentSettings, mcp: &McpSettingsProjection) -> Self {
        let cp = cli.projection();
        Self {
            cli_selected: cp.selected.config_key().to_string(),
            claude_path: cp.claude_path,
            cursor_agent_path: cp.cursor_agent_path,
            codex_path: cp.codex_path,
            antigravity_path: cp.antigravity_path,
            mcp_server_name: mcp.server_name.clone(),
            mcp_endpoint: mcp.endpoint.clone(),
            mcp_has_secret: mcp.has_secret,
        }
    }
}

/// Probe result for PD-LIVE-CLI-SMOKE-01 / reports.
#[derive(Debug, Clone, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub struct LiveTargetProbeResult {
    pub card: String,
    /// `PASS` when ≥1 target; `NOT RUN` when none (explicit — not FAIL).
    pub status: String,
    pub targets: Vec<LiveCliTargetHit>,
    pub settings: LiveTargetSettingsProjection,
    pub detail: String,
}

impl LiveTargetProbeResult {
    pub fn is_not_run(&self) -> bool {
        self.status == LIVE_TARGET_STATUS_NOT_RUN
    }

    pub fn is_pass(&self) -> bool {
        self.status == LIVE_TARGET_STATUS_PASS
    }

    pub fn to_json_pretty(&self) -> Result<String, String> {
        serde_json::to_string_pretty(self).map_err(|e| e.to_string())
    }
}

const KNOWN_TOOLS: [CliToolKind; 4] = [
    CliToolKind::Claude,
    CliToolKind::CursorAgent,
    CliToolKind::Codex,
    CliToolKind::Antigravity,
];

/// Walk `path_env` for `name` (+ Windows extensions when `windows_exts`).
/// Does **not** spawn processes — only `FileSystemPort::exists`.
pub fn lookup_on_path(
    name: &str,
    path_env: &str,
    path_sep: char,
    windows_exts: bool,
    fs: &dyn FileSystemPort,
) -> Option<String> {
    let name = name.trim();
    if name.is_empty() {
        return None;
    }
    // Absolute／relative path with separators: existence only.
    if name.contains('/') || name.contains('\\') {
        return if is_cli_path_activatable(name, fs) {
            Some(name.to_string())
        } else {
            None
        };
    }

    let candidates = path_candidates(name, windows_exts);
    for dir in path_env.split(path_sep) {
        let dir = dir.trim().trim_end_matches(['/', '\\']);
        if dir.is_empty() {
            continue;
        }
        let sep = if dir.contains('\\') && !dir.contains('/') {
            '\\'
        } else if windows_exts {
            '\\'
        } else {
            '/'
        };
        for cand in &candidates {
            let full = format!("{dir}{sep}{cand}");
            if fs.exists(&full).unwrap_or(false) {
                return Some(full);
            }
        }
    }
    None
}

fn path_candidates(name: &str, windows_exts: bool) -> Vec<String> {
    if !windows_exts {
        return vec![name.to_string()];
    }
    let lower = name.to_ascii_lowercase();
    if lower.ends_with(".exe") || lower.ends_with(".cmd") || lower.ends_with(".bat") {
        return vec![name.to_string()];
    }
    vec![
        name.to_string(),
        format!("{name}.exe"),
        format!("{name}.cmd"),
        format!("{name}.bat"),
    ]
}

fn config_for(cli: &CliAgentSettings, kind: CliToolKind) -> &crate::settings::CliToolConfig {
    match kind {
        CliToolKind::Claude => &cli.claude,
        CliToolKind::CursorAgent => &cli.cursor_agent,
        CliToolKind::Codex => &cli.codex,
        CliToolKind::Antigravity => &cli.antigravity,
    }
}

/// Probe host／agent CLI settings + optional `PATH` walk. Never spawns a CLI.
pub fn probe_live_cli_targets(
    fs: &dyn FileSystemPort,
    cli: &CliAgentSettings,
    path_env: &str,
    path_sep: char,
    windows_exts: bool,
    settings_proj: LiveTargetSettingsProjection,
) -> LiveTargetProbeResult {
    let mut targets: Vec<LiveCliTargetHit> = Vec::new();

    for kind in KNOWN_TOOLS {
        let key = kind.config_key().to_string();
        let cfg = config_for(cli, kind);
        let mut hit: Option<LiveCliTargetHit> = None;

        // 1) Configured path exists on FS → host_settings.
        if is_cli_path_activatable(&cfg.path, fs) {
            hit = Some(LiveCliTargetHit {
                tool: key.clone(),
                path: cfg.path.trim().to_string(),
                source: LiveTargetSource::HostSettings,
            });
        } else {
            // 2) Bare configured name on PATH.
            let lookup_name = {
                let t = cfg.path.trim();
                if t.is_empty() || t.contains('/') || t.contains('\\') {
                    kind.config_key()
                } else {
                    t
                }
            };
            if let Some(p) = lookup_on_path(lookup_name, path_env, path_sep, windows_exts, fs) {
                hit = Some(LiveCliTargetHit {
                    tool: key.clone(),
                    path: p,
                    source: LiveTargetSource::Path,
                });
            } else if lookup_name != kind.config_key() {
                // 3) Canonical tool key on PATH.
                if let Some(p) =
                    lookup_on_path(kind.config_key(), path_env, path_sep, windows_exts, fs)
                {
                    hit = Some(LiveCliTargetHit {
                        tool: key.clone(),
                        path: p,
                        source: LiveTargetSource::Path,
                    });
                }
            }
        }

        if let Some(h) = hit {
            targets.push(h);
        }
    }

    let (status, detail) = if targets.is_empty() {
        (
            LIVE_TARGET_STATUS_NOT_RUN.to_string(),
            "no usable CLI on PATH or in host settings — NOT RUN (never forged PASS)".into(),
        )
    } else {
        (
            LIVE_TARGET_STATUS_PASS.to_string(),
            format!("{} CLI target(s) detected for live smoke", targets.len()),
        )
    };

    LiveTargetProbeResult {
        card: "PD-LIVE-TARGET-01".into(),
        status,
        targets,
        settings: settings_proj,
        detail,
    }
}

/// Convenience: probe from CLI settings alone (MCP projection flags default empty／false).
pub fn probe_from_cli_settings(
    fs: &dyn FileSystemPort,
    cli: &CliAgentSettings,
    path_env: &str,
    path_sep: char,
    windows_exts: bool,
) -> LiveTargetProbeResult {
    let empty_mcp = McpSettingsProjection {
        transport: crate::settings::McpTransportKind::Stdio,
        server_name: String::new(),
        endpoint: String::new(),
        approved_tools: vec![],
        has_secret: false,
    };
    let proj = LiveTargetSettingsProjection::from_cli_and_mcp(cli, &empty_mcp);
    probe_live_cli_targets(fs, cli, path_env, path_sep, windows_exts, proj)
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::fake::FakeFileSystem;

    use crate::settings::{AgentSettingsDocument, McpAgentSettings};

    #[test]
    fn none_found_is_not_run_not_pass() {
        let fs = FakeFileSystem::new();
        let cli = CliAgentSettings::defaults();
        let r = probe_from_cli_settings(&fs, &cli, "", ':', false);
        assert!(r.is_not_run());
        assert!(!r.is_pass());
        assert_eq!(r.status, LIVE_TARGET_STATUS_NOT_RUN);
        assert!(r.targets.is_empty());
        assert!(r.detail.contains("NOT RUN"));
    }

    #[test]
    fn host_settings_path_detected() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude", b"");
        let mut cli = CliAgentSettings::defaults();
        cli.claude.path = "/tools/claude".into();
        let r = probe_from_cli_settings(&fs, &cli, "", ':', false);
        assert!(r.is_pass());
        assert_eq!(r.targets.len(), 1);
        assert_eq!(r.targets[0].tool, "claude");
        assert_eq!(r.targets[0].source, LiveTargetSource::HostSettings);
        assert_eq!(r.targets[0].path, "/tools/claude");
    }

    #[test]
    fn path_env_detects_bare_name() {
        let fs = FakeFileSystem::new();
        fs.seed("/opt/bin/cursor-agent", b"");
        let cli = CliAgentSettings::defaults();
        let r = probe_from_cli_settings(&fs, &cli, "/opt/bin", ':', false);
        assert!(r.is_pass());
        let hit = r
            .targets
            .iter()
            .find(|t| t.tool == "cursor-agent")
            .expect("cursor-agent");
        assert_eq!(hit.source, LiveTargetSource::Path);
        assert_eq!(hit.path, "/opt/bin/cursor-agent");
    }

    #[test]
    fn windows_ext_lookup() {
        let fs = FakeFileSystem::new();
        fs.seed(r"C:\Tools\codex.exe", b"");
        let cli = CliAgentSettings::defaults();
        let r = probe_from_cli_settings(&fs, &cli, r"C:\Tools", ';', true);
        assert!(r.is_pass());
        let hit = r.targets.iter().find(|t| t.tool == "codex").expect("codex");
        assert_eq!(hit.path, r"C:\Tools\codex.exe");
        assert_eq!(hit.source, LiveTargetSource::Path);
    }

    #[test]
    fn projection_omits_secret_token() {
        let fs = FakeFileSystem::new();
        fs.seed("/bin/claude", b"");
        let mut doc = AgentSettingsDocument::defaults();
        doc.cli.claude.path = "/bin/claude".into();
        doc.mcp.secret_token = Some("super-secret-token-xyz".into());
        let proj = LiveTargetSettingsProjection::from_agent(&doc.projection());
        assert!(proj.mcp_has_secret);
        let r = probe_live_cli_targets(&fs, &doc.cli, "", ':', false, proj);
        let json = r.to_json_pretty().expect("json");
        assert!(!json.contains("super-secret-token-xyz"));
        assert!(json.contains("\"mcp_has_secret\": true") || json.contains("\"mcp_has_secret\":true"));
        // Ensure secret field name from settings never appears as a value carrier.
        assert!(!json.contains("secret_token"));
        let _ = McpAgentSettings::defaults();
    }

    #[test]
    fn json_roundtrip_status_vocab() {
        let fs = FakeFileSystem::new();
        let r = probe_from_cli_settings(&fs, &CliAgentSettings::defaults(), "", ':', false);
        let raw = r.to_json_pretty().unwrap();
        let back: LiveTargetProbeResult = serde_json::from_str(&raw).unwrap();
        assert_eq!(back.status, LIVE_TARGET_STATUS_NOT_RUN);
        assert_eq!(back.card, "PD-LIVE-TARGET-01");
    }
}
