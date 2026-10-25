//! Host settings persistence (PD-SET-01) — config dir via PathPort + FileSystemPort.
//!
//! Secrets may be stored on disk for live MCP; they are **never** returned by
//! [`crate::settings::AgentSettingsDocument::projection`].
//!
//! PD-EXEC-LIVE-01: live CLI also requires [`crate::settings::CliAgentSettings::live_approved`]
//! (host mirrors `agent_active` → `live_approved` when wiring [`crate::CliAgentAdapter`]).

use sgenaxis_ports::{FileSystemPort, PathPort, PortError};

use crate::settings::{
    is_cli_path_activatable, is_mcp_endpoint_activatable, AgentSettingsDocument, AgentSettingsProjection,
    SettingsError,
};

const APP_NAME: &str = "SGenAxis";
const SETTINGS_FILE: &str = "agent-settings.json";

/// Persist／load [`AgentSettingsDocument`] under the host config directory.
pub struct HostSettingsStore<'a> {
    fs: &'a dyn FileSystemPort,
    path: &'a dyn PathPort,
}

impl<'a> HostSettingsStore<'a> {
    pub fn new(fs: &'a dyn FileSystemPort, path: &'a dyn PathPort) -> Self {
        Self { fs, path }
    }

    /// Absolute path to the settings JSON file.
    pub fn settings_file_path(&self) -> Result<String, SettingsError> {
        let dir = self
            .path
            .config_dir(APP_NAME)
            .map_err(map_port)?;
        Ok(self.path.join(&dir, &[SETTINGS_FILE]))
    }

    /// Load document or defaults when missing.
    pub fn load(&self) -> Result<AgentSettingsDocument, SettingsError> {
        let file = self.settings_file_path()?;
        match self.fs.read_to_string(&file) {
            Ok(raw) => AgentSettingsDocument::from_json(&raw),
            Err(PortError::NotFound(_)) => Ok(AgentSettingsDocument::defaults()),
            Err(e) => Err(map_port(e)),
        }
    }

    /// Persist the full document (drafts allowed). Does **not** require activatable paths.
    pub fn save_document(&self, doc: &AgentSettingsDocument) -> Result<(), SettingsError> {
        let file = self.settings_file_path()?;
        let dir = self
            .path
            .config_dir(APP_NAME)
            .map_err(map_port)?;
        self.fs.create_dir_all(&dir).map_err(map_port)?;
        let json = doc.to_json()?;
        self.fs
            .write_atomic(&file, json.as_bytes())
            .map_err(map_port)
    }

    /// Persist only when the selected CLI path and MCP endpoint are activatable.
    /// BDD-PD-SET-01: invalid path cannot be stored as active.
    pub fn save_as_active(&self, doc: &AgentSettingsDocument) -> Result<(), SettingsError> {
        let cli_path = &doc.cli.selected_config().path;
        if !is_cli_path_activatable(cli_path, self.fs) {
            return Err(SettingsError::InvalidPathNotActivatable(cli_path.clone()));
        }
        if !is_mcp_endpoint_activatable(&doc.mcp.endpoint) {
            return Err(SettingsError::InvalidPathNotActivatable(doc.mcp.endpoint.clone()));
        }
        self.save_document(doc)
    }

    /// Load then project — secrets never appear in the DTO.
    pub fn load_projection(&self) -> Result<AgentSettingsProjection, SettingsError> {
        Ok(self.load()?.projection())
    }
}

fn map_port(e: PortError) -> SettingsError {
    SettingsError::Io(e.to_string())
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::fake::{FakeFileSystem, FakePath};

    use crate::settings::{CliToolKind, McpTransportKind};

    #[test]
    fn partitions_persist_roundtrip_cli_and_mcp() {
        let fs = FakeFileSystem::new();
        let path = FakePath::new();
        let store = HostSettingsStore::new(&fs, &path);

        let mut doc = AgentSettingsDocument::defaults();
        doc.cli.claude.path = "/tools/claude.exe".into();
        doc.cli.selected = CliToolKind::Claude;
        doc.mcp.server_name = "my-local".into();
        doc.mcp.endpoint = "http://127.0.0.1:3920/sse".into();
        doc.mcp.approved_tools = vec!["read".into(), "write".into()];
        doc.mcp.secret_token = Some("tok-secret-xyz".into());
        doc.mcp.transport = McpTransportKind::LocalHttpSse;

        store.save_document(&doc).expect("save draft");
        let loaded = store.load().expect("load");
        assert_eq!(loaded.cli.claude.path, "/tools/claude.exe");
        assert_eq!(loaded.mcp.server_name, "my-local");
        assert_eq!(loaded.mcp.approved_tools, vec!["read", "write"]);
        assert_eq!(loaded.mcp.secret_token.as_deref(), Some("tok-secret-xyz"));
    }

    #[test]
    fn invalid_cli_path_not_saved_as_active() {
        let fs = FakeFileSystem::new();
        let path = FakePath::new();
        let store = HostSettingsStore::new(&fs, &path);

        let mut doc = AgentSettingsDocument::defaults();
        doc.cli.claude.path = "/missing/claude.exe".into();
        // path does not exist on FakeFS
        let err = store.save_as_active(&doc).expect_err("must refuse");
        assert!(matches!(err, SettingsError::InvalidPathNotActivatable(_)));
        // nothing written as active file content for missing path
        let file = store.settings_file_path().unwrap();
        assert!(!fs.exists(&file).unwrap());
    }

    #[test]
    fn valid_cli_path_saved_as_active() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let path = FakePath::new();
        let store = HostSettingsStore::new(&fs, &path);

        let mut doc = AgentSettingsDocument::defaults();
        doc.cli.claude.path = "/tools/claude.exe".into();
        doc.mcp.endpoint = "stdio://local-agent".into();
        store.save_as_active(&doc).expect("save active");
        let loaded = store.load().expect("load");
        assert_eq!(loaded.cli.claude.path, "/tools/claude.exe");
    }

    #[test]
    fn projection_omits_secrets_after_persist() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let path = FakePath::new();
        let store = HostSettingsStore::new(&fs, &path);

        let mut doc = AgentSettingsDocument::defaults();
        doc.cli.claude.path = "/tools/claude.exe".into();
        doc.mcp.secret_token = Some("never-project-me".into());
        store.save_document(&doc).expect("save");

        let proj = store.load_projection().expect("proj");
        assert!(proj.mcp.has_secret);
        let debug = format!("{proj:?}");
        assert!(!debug.contains("never-project-me"));
        // CLI partition present
        assert_eq!(proj.cli.selected, CliToolKind::Claude);
        assert_eq!(proj.cli.claude_path, "/tools/claude.exe");
        // MCP partition present
        assert_eq!(proj.mcp.server_name, "local-agent");
    }

    #[test]
    fn reserved_mcp_ports_not_activatable_for_save() {
        let fs = FakeFileSystem::new();
        fs.seed("/tools/claude.exe", b"");
        let path = FakePath::new();
        let store = HostSettingsStore::new(&fs, &path);

        let mut doc = AgentSettingsDocument::defaults();
        doc.cli.claude.path = "/tools/claude.exe".into();
        doc.mcp.endpoint = "http://127.0.0.1:8788/sse".into();
        let err = store.save_as_active(&doc).expect_err("8788 blocked");
        assert!(matches!(err, SettingsError::InvalidPathNotActivatable(_)));
    }
}
