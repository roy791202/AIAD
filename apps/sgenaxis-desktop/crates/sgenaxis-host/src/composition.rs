//! Composition root — wires Ports + settings + lifecycle at boot.
//!
//! HOST does **not** own WORK／FLOW／EXEC business state here.

use sgenaxis_adapters::compose::{boxed_deploy_fake, ensure_app_config_dir};
use sgenaxis_adapters::BoxedPorts;
use sgenaxis_ports::{DeployPort, FileSystemPort, GitPort, GitWritePort, PathPort, PortError};

use crate::deploy::{
    check_view, default_workspace_root, find_workspace_root, focus_platform, list_artifact_views,
    status_view, DeployArtifactView, DeployCheckView, DeployStatusView,
};
use crate::error::HostError;
use crate::lifecycle::{AppLifecycle, LifecyclePhase};
use crate::ports_view::{project_ports_status, PortAdapterLabels, PortsStatusView};
use crate::settings::{HostSettings, SettingsStore, HOST_SETTINGS_FILE};

/// App name used for config／cache path resolution.
pub const APP_NAME: &str = "sgenaxis";

/// Boot-time host bundle. Swap Fake ↔ Std via [`BoxedPorts`].
pub struct CompositionRoot {
    pub lifecycle: AppLifecycle,
    pub settings: SettingsStore,
    pub ports: BoxedPorts,
    /// PD-DEPLOY-PORT-01 — query-only DeployPort (Fake／Std).
    pub deploy: Box<dyn DeployPort>,
    /// PD-GIT-WRITE-UI-01: `true` when write adapter accepts granted approval.
    /// Default-deny GatedGitWrite keeps this `false`.
    pub git_writes_enabled: bool,
    /// PD-REMAIN-PORTS-UI-01: adapter labels for Ports panel projection (no OS enum).
    pub port_labels: Option<PortAdapterLabels>,
}

impl CompositionRoot {
    /// Unit-test／DryRun boot: all-fake ports, settings under fake config dir.
    pub fn boot_fake() -> Result<Self, HostError> {
        let ports = BoxedPorts::fake();
        Self::boot_with_ports_deploy_labels(
            ports,
            boxed_deploy_fake(),
            false,
            Some(PortAdapterLabels::FAKE),
        )
    }

    /// Test／DryRun boot with approving [`FakeGitWrite`] (still needs per-call approval).
    pub fn boot_fake_with_approving_git_write() -> Result<Self, HostError> {
        let ports = BoxedPorts::fake_with_approving_git_write();
        Self::boot_with_ports_deploy_labels(
            ports,
            boxed_deploy_fake(),
            true,
            Some(PortAdapterLabels::FAKE_APPROVING_WRITE),
        )
    }

    /// Production-style: Std FS／Path／Process + StdGit + approving StdGitWrite + StdDeploy.
    #[cfg(feature = "std-adapters")]
    pub fn boot_std() -> Result<Self, HostError> {
        let ports = BoxedPorts::std_with_approving_git_write();
        let cwd = default_workspace_root();
        let root = find_workspace_root(ports.fs.as_ref(), ports.path.as_ref(), &cwd).unwrap_or(cwd);
        let deploy = sgenaxis_adapters::boxed_deploy_std(root);
        Self::boot_with_ports_deploy_labels(
            ports,
            deploy,
            true,
            Some(PortAdapterLabels::STD_APPROVING),
        )
    }

    /// Wire ports, ensure config dir, load settings, mark Ready.
    /// Uses Fake deploy when std-adapters off; otherwise StdDeploy at discovered root.
    /// Write gate stays default-deny (`git_writes_enabled = false`) unless ports already
    /// carry an approving write adapter (callers should prefer explicit boot helpers).
    pub fn boot_with_ports(ports: BoxedPorts) -> Result<Self, HostError> {
        #[cfg(feature = "std-adapters")]
        {
            let cwd = default_workspace_root();
            let root =
                find_workspace_root(ports.fs.as_ref(), ports.path.as_ref(), &cwd).unwrap_or(cwd);
            let deploy = sgenaxis_adapters::boxed_deploy_std(root);
            return Self::boot_with_ports_deploy_labels(
                ports,
                deploy,
                false,
                Some(PortAdapterLabels::STD_GATED_WRITE),
            );
        }
        #[cfg(not(feature = "std-adapters"))]
        {
            Self::boot_with_ports_deploy_labels(
                ports,
                boxed_deploy_fake(),
                false,
                Some(PortAdapterLabels::FAKE),
            )
        }
    }

    /// Wire ports + explicit DeployPort (tests／adapter swap). Labels unknown → empty ok.
    pub fn boot_with_ports_and_deploy(
        ports: BoxedPorts,
        deploy: Box<dyn DeployPort>,
        git_writes_enabled: bool,
    ) -> Result<Self, HostError> {
        Self::boot_with_ports_deploy_labels(ports, deploy, git_writes_enabled, None)
    }

    /// Wire ports + deploy + explicit adapter labels for Ports UI projection.
    pub fn boot_with_ports_deploy_labels(
        ports: BoxedPorts,
        deploy: Box<dyn DeployPort>,
        git_writes_enabled: bool,
        port_labels: Option<PortAdapterLabels>,
    ) -> Result<Self, HostError> {
        let mut lifecycle = AppLifecycle::new();
        assert_eq!(lifecycle.phase(), LifecyclePhase::Booting);

        let config_dir = ensure_app_config_dir(ports.path.as_ref(), ports.fs.as_ref(), APP_NAME)?;
        let settings_path = join_path(ports.path.as_ref(), &config_dir, HOST_SETTINGS_FILE)?;
        let settings = SettingsStore::load_or_default(ports.fs.as_ref(), settings_path)?;

        lifecycle.mark_ready()?;
        Ok(Self {
            lifecycle,
            settings,
            ports,
            deploy,
            git_writes_enabled,
            port_labels,
        })
    }

    pub fn phase(&self) -> LifecyclePhase {
        self.lifecycle.phase()
    }

    pub fn host_settings(&self) -> &HostSettings {
        self.settings.settings()
    }

    pub fn set_host_settings(&mut self, next: HostSettings) -> Result<(), HostError> {
        if !self.lifecycle.is_ready() {
            return Err(HostError::Lifecycle(
                "settings mutation requires Ready phase".into(),
            ));
        }
        self.settings.update_and_save(self.ports.fs.as_ref(), next)
    }

    /// Graceful close: Ready → ShuttingDown → Stopped.
    pub fn shutdown(&mut self) -> Result<(), HostError> {
        self.lifecycle.request_shutdown()?;
        // Persist settings on exit (best-effort already saved on mutate).
        self.settings.save(self.ports.fs.as_ref())?;
        self.lifecycle.mark_stopped()?;
        Ok(())
    }

    pub fn fs(&self) -> &dyn FileSystemPort {
        self.ports.fs.as_ref()
    }

    /// Read-only Git port (PD-GIT-01 / PD-GIT-UI-01).
    pub fn git(&self) -> &dyn GitPort {
        self.ports.git.as_ref()
    }

    /// Write port — PD-GIT-02 approval gate; UI must pass GitWriteApproval per call.
    pub fn git_write(&self) -> &dyn GitWritePort {
        self.ports.git_write.as_ref()
    }

    /// Whether UI may offer commit／push (still requires explicit approval per mutation).
    pub fn git_writes_enabled(&self) -> bool {
        self.git_writes_enabled
    }

    /// PD-DEPLOY-PORT-01 DeployPort (query only).
    pub fn deploy_port(&self) -> &dyn DeployPort {
        self.deploy.as_ref()
    }

    pub fn deploy_status(&self) -> Result<DeployStatusView, PortError> {
        status_view(self.deploy.as_ref(), focus_platform())
    }

    pub fn deploy_check(&self) -> Result<DeployCheckView, PortError> {
        check_view(self.deploy.as_ref(), focus_platform())
    }

    pub fn list_artifacts(&self) -> Result<Vec<DeployArtifactView>, PortError> {
        list_artifact_views(self.deploy.as_ref(), focus_platform())
    }

    /// PD-REMAIN-PORTS-UI-01: registered Port／adapter status projection (empty ok).
    pub fn ports_status(&self) -> PortsStatusView {
        project_ports_status(self.port_labels.as_ref(), self.git_writes_enabled)
    }
}

fn join_path(path: &dyn PathPort, dir: &str, file: &str) -> Result<String, HostError> {
    Ok(path.join(dir, &[file]))
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::ipc::{authorize, is_allowed};

    #[test]
    fn boot_fake_reaches_ready_with_persisted_settings() {
        let root = CompositionRoot::boot_fake().expect("boot");
        assert_eq!(root.phase(), LifecyclePhase::Ready);
        assert_eq!(root.host_settings().ui_theme, "system");
        let path = root.settings.path().to_string();
        assert!(root.fs().exists(&path).unwrap());
    }

    #[test]
    fn shutdown_stops_cleanly() {
        let mut root = CompositionRoot::boot_fake().unwrap();
        root.shutdown().unwrap();
        assert!(root.lifecycle.is_stopped());
    }

    #[test]
    fn settings_update_persists_across_reboot() {
        let mut root = CompositionRoot::boot_fake().unwrap();
        let path = root.settings.path().to_string();
        let mut next = root.host_settings().clone();
        next.ui_theme = "light".into();
        root.set_host_settings(next).unwrap();

        // Simulate new process: same fake FS still holds bytes if we reuse ports —
        // here reload via SettingsStore on the same FS handle.
        let reloaded = SettingsStore::load_or_default(root.fs(), path).expect("reload");
        assert_eq!(reloaded.settings().ui_theme, "light");
    }

    #[test]
    fn composition_does_not_expose_shell_ipc() {
        assert!(!is_allowed("shell_execute"));
        assert!(authorize("shell_execute").is_err());
        assert!(authorize("host_get_phase").is_ok());
    }

    #[test]
    fn boot_fake_exposes_read_only_deploy_commands() {
        let root = CompositionRoot::boot_fake().unwrap();
        let st = root.deploy_status().unwrap();
        assert!(!st.elevated_qn_auto);
        // Windows focus → supported; non-Windows focus → unsupported (still observable).
        let check = root.deploy_check().unwrap();
        assert!(!check.message.is_empty());
        let arts = root.list_artifacts().unwrap();
        assert!(!arts.is_empty());
        assert!(authorize("deploy_status").is_ok());
        assert!(authorize("deploy_check").is_ok());
        assert!(authorize("list_artifacts").is_ok());
        assert!(authorize("deploy_install").is_err());
        let _ = (st, check);
    }

    /// BDD-PD-REMAIN-PORTS-UI-01: composition projects registered ports; empty ok.
    #[test]
    fn boot_fake_ports_status_lists_registered_adapters() {
        let root = CompositionRoot::boot_fake().unwrap();
        let v = root.ports_status();
        assert_eq!(v.status, "ok");
        assert_eq!(v.entry_count, 6);
        assert!(v
            .entries
            .iter()
            .any(|e| e.port == "FileSystemPort" && e.adapter == "FakeFileSystem"));
        assert!(v
            .entries
            .iter()
            .any(|e| e.port == "GitWritePort" && e.status == "gated"));
        assert!(authorize("ports_status").is_ok());
    }

    #[test]
    fn unlabeled_boot_ports_status_is_empty_ok() {
        let root = CompositionRoot::boot_with_ports_and_deploy(
            BoxedPorts::fake(),
            boxed_deploy_fake(),
            false,
        )
        .unwrap();
        let v = root.ports_status();
        assert_eq!(v.status, "empty");
        assert_eq!(v.entry_count, 0);
    }
}
