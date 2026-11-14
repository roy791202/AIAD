//! Persistent host settings store — config only; no WORK／FLOW business state.
//!
//! PD-SET-01: embeds CLI／MCP [`AgentSettingsDocument`]; invalid paths cannot be
//! stored as active; projections omit secrets.

use serde::{Deserialize, Serialize};
use sgenaxis_exec::{
    is_cli_path_activatable, is_mcp_endpoint_activatable, probe_live_cli_targets,
    AgentSettingsDocument, AgentSettingsProjection, CliAgentAdapter, CliAgentSettings,
    LiveTargetProbeResult, LiveTargetSettingsProjection,
};
use sgenaxis_ports::{FileSystemPort, ProcessPort};

use crate::error::HostError;

/// Schema version for forward-compatible migrations.
pub const HOST_SETTINGS_VERSION: u32 = 4;

/// Default relative filename under the app config dir.
pub const HOST_SETTINGS_FILE: &str = "host-settings.json";

/// Default relative board path suggestion (repo-root relative; not an HTTP URL).
pub const DEFAULT_BOARD_PATH_HINT: &str = "docs/PROJECT-BOARD.html";

/// Host-level preferences (PD-HOST-01 + PD-SET-01 + PD-BOARD-LIVE-01 + PD-WIRE-ROOT-01).
/// Not project／task／run state.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct HostSettings {
    pub version: u32,
    /// `system`｜`light`｜`dark`
    pub ui_theme: String,
    pub locale: String,
    /// Bound project root directory (PD-WIRE-OPEN-01／PD-WIRE-ROOT-01).
    /// Empty = unbound. Never a success default of `/demo/root`.
    #[serde(default)]
    pub project_root: String,
    /// Local PROJECT-BOARD.html (or JSON) path for read-only lamp projection.
    /// Empty = not configured. Never a `:8788`／`:28789` URL.
    /// Relative paths resolve under [`Self::project_root`] when bound.
    #[serde(default)]
    pub board_path: String,
    /// CLI＋MCP partitions (PD-SET-01). May hold draft paths; see [`Self::agent_active`].
    #[serde(default)]
    pub agent: AgentSettingsDocument,
    /// When true, selected CLI path + MCP endpoint must be activatable to persist.
    #[serde(default)]
    pub agent_active: bool,
}

impl Default for HostSettings {
    fn default() -> Self {
        Self::defaults()
    }
}

impl HostSettings {
    pub fn defaults() -> Self {
        Self {
            version: HOST_SETTINGS_VERSION,
            ui_theme: "system".into(),
            locale: "en".into(),
            project_root: String::new(),
            board_path: String::new(),
            agent: AgentSettingsDocument::defaults(),
            agent_active: false,
        }
    }

    /// Trimmed bound root, or `None` when unbound (PD-WIRE-ROOT-01).
    pub fn bound_project_root(&self) -> Option<&str> {
        let r = self.project_root.trim();
        if r.is_empty() {
            None
        } else {
            Some(r)
        }
    }

    pub fn validate(&self) -> Result<(), HostError> {
        match self.ui_theme.as_str() {
            "system" | "light" | "dark" => {}
            other => {
                return Err(HostError::Settings(format!("invalid ui_theme: {other}")));
            }
        }
        if self.locale.trim().is_empty() {
            return Err(HostError::Settings("locale must not be empty".into()));
        }
        // board_path may be empty (not configured). Reject URL／mailbox schemes.
        let bp = self.board_path.trim();
        if bp.starts_with("http://")
            || bp.starts_with("https://")
            || bp.contains(":8788")
            || bp.contains(":8787")
        {
            return Err(HostError::Settings(
                "board_path must be a local file path (not http / :8788 / :8787)".into(),
            ));
        }
        // project_root may be empty (未綁定). Reject URL／mailbox／cloud schemes.
        let pr = self.project_root.trim();
        if pr.starts_with("http://")
            || pr.starts_with("https://")
            || pr.contains("://")
            || pr.contains(":8788")
            || pr.contains(":8787")
        {
            return Err(HostError::Settings(
                "project_root must be a local directory path (not URL / cloud)".into(),
            ));
        }
        Ok(())
    }

    /// Theme／locale always; when `agent_active`, CLI path + MCP endpoint must be activatable.
    pub fn validate_with_fs(&self, fs: &dyn FileSystemPort) -> Result<(), HostError> {
        self.validate()?;
        if self.agent_active {
            let path = &self.agent.cli.selected_config().path;
            if !is_cli_path_activatable(path, fs) {
                return Err(HostError::Settings(format!(
                    "invalid path not activatable: {path}"
                )));
            }
            if !is_mcp_endpoint_activatable(&self.agent.mcp.endpoint) {
                return Err(HostError::Settings(format!(
                    "invalid path not activatable: {}",
                    self.agent.mcp.endpoint
                )));
            }
        }
        Ok(())
    }

    /// Activate agent settings only when paths／endpoints are valid (BDD-PD-SET-01).
    /// Also mirrors `agent_active` → CLI `live_approved` for PD-EXEC-LIVE-01.
    pub fn try_activate_agent(&mut self, fs: &dyn FileSystemPort) -> Result<(), HostError> {
        let path = &self.agent.cli.selected_config().path;
        if !is_cli_path_activatable(path, fs) {
            return Err(HostError::Settings(format!(
                "invalid path not activatable: {path}"
            )));
        }
        if !is_mcp_endpoint_activatable(&self.agent.mcp.endpoint) {
            return Err(HostError::Settings(format!(
                "invalid path not activatable: {}",
                self.agent.mcp.endpoint
            )));
        }
        self.agent_active = true;
        self.agent.cli.live_approved = true;
        Ok(())
    }

    /// Revoke live Agent approval — DryRun remains available (PD-EXEC-LIVE-01).
    pub fn revoke_agent_live(&mut self) {
        self.agent_active = false;
        self.agent.cli.live_approved = false;
    }

    /// CLI settings for EXEC with `live_approved` mirrored from `agent_active`.
    pub fn cli_settings_for_exec(&self) -> CliAgentSettings {
        let mut cli = self.agent.cli.clone();
        cli.live_approved = self.agent_active;
        cli
    }

    /// Compose [`CliAgentAdapter`] from host settings + ProcessPort (live gate wired).
    pub fn make_cli_adapter(&self, process: Box<dyn ProcessPort>) -> CliAgentAdapter {
        CliAgentAdapter::new(self.cli_settings_for_exec(), process)
    }

    /// UI／Dirty projection — **never** includes secret token values.
    pub fn agent_projection(&self) -> AgentSettingsProjection {
        self.agent.projection()
    }

    /// PD-LIVE-TARGET-01: probe PATH＋configured CLI paths; no spawn.
    /// Empty → `status=NOT RUN`. Projection omits secrets for PD-LIVE-CLI-SMOKE-01.
    pub fn probe_live_cli_targets(
        &self,
        fs: &dyn FileSystemPort,
        path_env: &str,
        path_sep: char,
        windows_exts: bool,
    ) -> LiveTargetProbeResult {
        let proj = LiveTargetSettingsProjection::from_agent(&self.agent_projection());
        probe_live_cli_targets(fs, &self.agent.cli, path_env, path_sep, windows_exts, proj)
    }
}

/// Load／save [`HostSettings`] through [`FileSystemPort`] (Fake or Std).
#[derive(Debug, Clone)]
pub struct SettingsStore {
    path: String,
    settings: HostSettings,
}

impl SettingsStore {
    pub fn path(&self) -> &str {
        &self.path
    }

    pub fn settings(&self) -> &HostSettings {
        &self.settings
    }

    pub fn settings_mut(&mut self) -> &mut HostSettings {
        &mut self.settings
    }

    /// Load from disk／fake FS, or create defaults if missing.
    pub fn load_or_default(
        fs: &dyn FileSystemPort,
        path: impl Into<String>,
    ) -> Result<Self, HostError> {
        let path = path.into();
        if !fs.exists(&path)? {
            let store = Self {
                path,
                settings: HostSettings::defaults(),
            };
            store.save(fs)?;
            return Ok(store);
        }
        let raw = fs.read_to_string(&path)?;
        let settings: HostSettings =
            serde_json::from_str(&raw).map_err(|e| HostError::Settings(format!("parse: {e}")))?;
        settings.validate_with_fs(fs)?;
        Ok(Self { path, settings })
    }

    pub fn save(&self, fs: &dyn FileSystemPort) -> Result<(), HostError> {
        self.settings.validate_with_fs(fs)?;
        if let Some((dir, _)) = split_parent(&self.path) {
            fs.create_dir_all(dir)?;
        }
        let json = serde_json::to_vec_pretty(&self.settings)
            .map_err(|e| HostError::Settings(format!("serialize: {e}")))?;
        fs.write_atomic(&self.path, &json)?;
        Ok(())
    }

    pub fn update_and_save(
        &mut self,
        fs: &dyn FileSystemPort,
        next: HostSettings,
    ) -> Result<(), HostError> {
        next.validate_with_fs(fs)?;
        self.settings = next;
        self.save(fs)
    }
}

fn split_parent(path: &str) -> Option<(&str, &str)> {
    let normalized = path.replace('\\', "/");
    let idx = normalized.rfind('/')?;
    if idx == 0 {
        return None;
    }
    // Use original slice bounds carefully — for Fake FS paths with `/` this is fine.
    let parent = &path[..idx];
    let name = &path[idx + 1..];
    if parent.is_empty() {
        None
    } else {
        Some((parent, name))
    }
}

#[cfg(test)]
mod tests {
    use sgenaxis_adapters::FakeFileSystem;
    use sgenaxis_exec::CliToolKind;

    use super::*;

    #[test]
    fn load_or_default_creates_and_persists() {
        let fs = FakeFileSystem::new();
        let path = "/fake/config/sgenaxis/host-settings.json";
        let store = SettingsStore::load_or_default(&fs, path).expect("load");
        assert_eq!(store.settings().ui_theme, "system");
        assert!(fs.exists(path).unwrap());
        assert!(!store.settings().agent_active);
        assert_eq!(store.settings().agent.cli.selected, CliToolKind::Claude);
    }

    #[test]
    fn roundtrip_persists_theme_change() {
        let fs = FakeFileSystem::new();
        let path = "/fake/config/sgenaxis/host-settings.json";
        let mut store = SettingsStore::load_or_default(&fs, path).unwrap();
        let mut next = store.settings().clone();
        next.ui_theme = "dark".into();
        next.locale = "zh-TW".into();
        store.update_and_save(&fs, next).unwrap();

        let reloaded = SettingsStore::load_or_default(&fs, path).unwrap();
        assert_eq!(reloaded.settings().ui_theme, "dark");
        assert_eq!(reloaded.settings().locale, "zh-TW");
    }

    #[test]
    fn rejects_invalid_theme() {
        let bad = HostSettings {
            version: 4,
            ui_theme: "neon".into(),
            locale: "en".into(),
            project_root: String::new(),
            board_path: String::new(),
            agent: AgentSettingsDocument::defaults(),
            agent_active: false,
        };
        assert!(bad.validate().is_err());
    }

    #[test]
    fn project_root_roundtrips_via_host_settings() {
        let fs = FakeFileSystem::new();
        let path = "/fake/config/sgenaxis/host-settings.json";
        let mut store = SettingsStore::load_or_default(&fs, path).unwrap();
        let mut next = store.settings().clone();
        next.project_root = "/work/real-repo".into();
        next.board_path = "docs/PROJECT-BOARD.html".into();
        store.update_and_save(&fs, next).unwrap();

        let reloaded = SettingsStore::load_or_default(&fs, path).unwrap();
        assert_eq!(
            reloaded.settings().bound_project_root(),
            Some("/work/real-repo")
        );
        assert_eq!(reloaded.settings().board_path, "docs/PROJECT-BOARD.html");
    }

    #[test]
    fn rejects_board_path_http_or_mailbox() {
        let mut s = HostSettings::defaults();
        s.board_path = "http://127.0.0.1:8788/".into();
        assert!(s.validate().is_err());
        s.board_path = "docs/PROJECT-BOARD.html".into();
        assert!(s.validate().is_ok());
    }

    #[test]
    fn cli_mcp_partitions_persist_via_host_settings() {
        let fs = FakeFileSystem::new();
        let path = "/fake/config/sgenaxis/host-settings.json";
        let mut store = SettingsStore::load_or_default(&fs, path).unwrap();
        let mut next = store.settings().clone();
        next.agent.cli.claude.path = "/tools/claude.exe".into();
        next.agent.mcp.server_name = "local-x".into();
        next.agent.mcp.endpoint = "http://127.0.0.1:3920/sse".into();
        next.agent.mcp.approved_tools = vec!["a".into(), "b".into()];
        next.agent.mcp.secret_token = Some("host-secret".into());
        next.agent_active = false; // draft ok
        store.update_and_save(&fs, next).unwrap();

        let reloaded = SettingsStore::load_or_default(&fs, path).unwrap();
        assert_eq!(
            reloaded.settings().agent.cli.claude.path,
            "/tools/claude.exe"
        );
        assert_eq!(reloaded.settings().agent.mcp.server_name, "local-x");
        assert_eq!(reloaded.settings().agent.mcp.approved_tools, vec!["a", "b"]);
        assert_eq!(
            reloaded.settings().agent.mcp.secret_token.as_deref(),
            Some("host-secret")
        );
    }

    #[test]
    fn invalid_path_not_persisted_as_active() {
        let fs = FakeFileSystem::new();
        let path = "/fake/config/sgenaxis/host-settings.json";
        let mut store = SettingsStore::load_or_default(&fs, path).unwrap();
        let mut next = store.settings().clone();
        next.agent.cli.claude.path = "/missing/bin".into();
        next.agent_active = true;
        let err = store.update_and_save(&fs, next).expect_err("must refuse");
        assert!(err.to_string().contains("not activatable"));
    }

    #[test]
    fn valid_path_persisted_as_active() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let path = "/fake/config/sgenaxis/host-settings.json";
        let mut store = SettingsStore::load_or_default(&fs, path).unwrap();
        let mut next = store.settings().clone();
        next.agent.cli.claude.path = "/tools/claude.exe".into();
        next.agent.mcp.endpoint = "stdio://local-agent".into();
        next.try_activate_agent(&fs).unwrap();
        store.update_and_save(&fs, next).unwrap();
        assert!(store.settings().agent_active);
        assert!(store.settings().agent.cli.live_approved);
    }

    #[test]
    fn activate_wires_cli_live_approved_and_dry_run_revocable() {
        use sgenaxis_adapters::FakeProcess;
        use sgenaxis_exec::{AgentPort, StartRunRequest};

        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let mut host = HostSettings::defaults();
        host.agent.cli.claude.path = "/tools/claude.exe".into();
        host.agent.mcp.endpoint = "stdio://local-agent".into();
        host.try_activate_agent(&fs).expect("activate");

        let cli = host.cli_settings_for_exec();
        assert!(cli.live_approved);

        let adapter = host.make_cli_adapter(Box::new(FakeProcess::new()));
        assert!(adapter.settings().live_approved);

        // DryRun still available under approved live settings.
        let mut adapter = host.make_cli_adapter(Box::new(FakeProcess::new()));
        let run = adapter
            .start_run(StartRunRequest::cli_dry_run())
            .expect("dry");
        let ev = adapter.poll_chunks(run).expect("poll");
        assert!(matches!(
            &ev[0],
            sgenaxis_exec::AgentChunk::Started { dry_run: true, .. }
        ));

        host.revoke_agent_live();
        assert!(!host.cli_settings_for_exec().live_approved);
    }

    #[test]
    fn agent_projection_omits_secret() {
        let mut s = HostSettings::defaults();
        s.agent.mcp.secret_token = Some("never-in-projection".into());
        let p = s.agent_projection();
        assert!(p.mcp.has_secret);
        let debug = format!("{p:?}");
        assert!(!debug.contains("never-in-projection"));
        // Partitions present
        assert_eq!(p.cli.selected, CliToolKind::Claude);
        assert_eq!(p.mcp.server_name, "local-agent");
    }

    #[test]
    fn probe_live_cli_targets_not_run_when_empty() {
        let fs = FakeFileSystem::new();
        let host = HostSettings::defaults();
        let r = host.probe_live_cli_targets(&fs, "", ':', false);
        assert_eq!(r.status, sgenaxis_exec::LIVE_TARGET_STATUS_NOT_RUN);
        assert!(r.targets.is_empty());
    }

    #[test]
    fn probe_live_cli_targets_from_settings_omits_secret() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let mut host = HostSettings::defaults();
        host.agent.cli.claude.path = "/tools/claude.exe".into();
        host.agent.mcp.secret_token = Some("host-live-secret".into());
        let r = host.probe_live_cli_targets(&fs, "", ':', false);
        assert_eq!(r.status, sgenaxis_exec::LIVE_TARGET_STATUS_PASS);
        assert_eq!(r.targets[0].tool, "claude");
        assert!(r.settings.mcp_has_secret);
        let json = r.to_json_pretty().expect("json");
        assert!(!json.contains("host-live-secret"));
        assert!(!json.contains("secret_token"));
    }

    #[test]
    fn reserved_mcp_port_not_activatable() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let mut s = HostSettings::defaults();
        s.agent.cli.claude.path = "/tools/claude.exe".into();
        s.agent.mcp.endpoint = "http://127.0.0.1:8788/sse".into();
        assert!(s.try_activate_agent(&fs).is_err());
    }
}
