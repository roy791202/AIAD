//! Std [`DeployPort`] — Windows WiX/MSI path conventions; macOS/Linux Unsupported.
//!
//! Query / probe only: **never** runs elevated install or `msiexec`.

use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};

use sgenaxis_ports::{
    unsupported_platform_reason, windows_wix_artifact_relpath, windows_wix_supported,
    DeployCapability, DeployPlatform, DeployPort, DeploySupport, PortError,
    WINDOWS_WIX_PRODUCT_VERSION,
};

/// Real-ish deploy adapter: capability from channel policy; optional MSI probe under repo root.
#[derive(Debug, Clone)]
pub struct StdDeploy {
    repo_root: Option<String>,
    version: String,
    /// Explicit override (tests / host); otherwise probe under `repo_root`.
    last_override: Arc<Mutex<Option<String>>>,
}

impl Default for StdDeploy {
    fn default() -> Self {
        Self::new()
    }
}

impl StdDeploy {
    pub fn new() -> Self {
        Self {
            repo_root: None,
            version: WINDOWS_WIX_PRODUCT_VERSION.into(),
            last_override: Arc::new(Mutex::new(None)),
        }
    }

    /// Bind a repository root so [`DeployPort::last_artifact_path`] can probe the WiX `out/` MSI.
    pub fn with_repo_root(repo_root: impl Into<String>) -> Self {
        Self {
            repo_root: Some(repo_root.into()),
            version: WINDOWS_WIX_PRODUCT_VERSION.into(),
            last_override: Arc::new(Mutex::new(None)),
        }
    }

    pub fn with_version(mut self, version: impl Into<String>) -> Self {
        self.version = version.into();
        self
    }

    /// Record a last artifact path without installing (host / tests).
    pub fn set_last_artifact_path(&self, path: Option<String>) -> Result<(), PortError> {
        let mut g = self
            .last_override
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        *g = path;
        Ok(())
    }

    fn windows_support(&self) -> DeploySupport {
        windows_wix_supported(&self.version)
    }

    fn probe_msi(&self) -> Option<String> {
        let root = self.repo_root.as_ref()?;
        let rel = windows_wix_artifact_relpath(&self.version);
        let joined: PathBuf = Path::new(root).join(rel.replace('/', std::path::MAIN_SEPARATOR_STR));
        if joined.is_file() {
            Some(joined.to_string_lossy().into_owned())
        } else {
            None
        }
    }
}

impl DeployPort for StdDeploy {
    fn capability(&self, platform: DeployPlatform) -> Result<DeployCapability, PortError> {
        let support = match platform {
            DeployPlatform::Windows => self.windows_support(),
            DeployPlatform::MacOs | DeployPlatform::Linux => DeploySupport::Unsupported {
                reason: unsupported_platform_reason(platform),
            },
        };
        Ok(DeployCapability { platform, support })
    }

    fn last_artifact_path(&self) -> Result<Option<String>, PortError> {
        let override_path = self
            .last_override
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?
            .clone();
        if override_path.is_some() {
            return Ok(override_path);
        }
        Ok(self.probe_msi())
    }
}
