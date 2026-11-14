//! Deploy Port — capability / last artifact path / unsupported platforms (PD-DEPLOY-PORT-01).
//!
//! Query-only: no elevated install, no packager invocation. Paths are `String`
//! (no `PathBuf` on the public surface).

use crate::PortError;

/// Target OS family for packaging / deploy queries.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum DeployPlatform {
    Windows,
    MacOs,
    Linux,
}

/// Whether a platform can be packaged with the current release channel.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DeploySupport {
    /// Supported packager + artifact format + path convention (relative to repo root).
    Supported {
        /// e.g. `"wix"`
        packager: String,
        /// e.g. `"msi"`
        format: String,
        /// Repo-relative convention, e.g. `packaging/windows/wix/out/SGenAxis-0.1.0-windows-x64.msi`
        artifact_path_convention: String,
    },
    /// Not in scope for this milestone (adapters must surface this — not panic).
    Unsupported {
        reason: String,
    },
}

/// Capability snapshot for one platform.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeployCapability {
    pub platform: DeployPlatform,
    pub support: DeploySupport,
}

/// Status = capability for a focus platform + optional last artifact path.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeployStatus {
    pub platform: DeployPlatform,
    pub support: DeploySupport,
    pub last_artifact_path: Option<String>,
}

/// Default Windows product version used in WiX artifact naming (PD-REL-01/02).
pub const WINDOWS_WIX_PRODUCT_VERSION: &str = "0.1.0";

/// Primary Windows packager id.
pub const WINDOWS_WIX_PACKAGER: &str = "wix";

/// Windows artifact format.
pub const WINDOWS_WIX_FORMAT: &str = "msi";

/// Repo-relative MSI path convention under `packaging/windows/wix/out/`.
pub fn windows_wix_artifact_relpath(version: &str) -> String {
    format!("packaging/windows/wix/out/SGenAxis-{version}-windows-x64.msi")
}

/// Build the Supported arm for Windows WiX/MSI (shared by Fake / Std).
pub fn windows_wix_supported(version: &str) -> DeploySupport {
    DeploySupport::Supported {
        packager: WINDOWS_WIX_PACKAGER.into(),
        format: WINDOWS_WIX_FORMAT.into(),
        artifact_path_convention: windows_wix_artifact_relpath(version),
    }
}

/// M3/M4 reason string for non-Windows platforms.
pub fn unsupported_platform_reason(platform: DeployPlatform) -> String {
    match platform {
        DeployPlatform::Windows => {
            // Caller should not use this for Windows when WiX is the channel.
            "windows packaging unexpected unsupported".into()
        }
        DeployPlatform::MacOs => "M4 — macOS packager out of scope (not WiX)".into(),
        DeployPlatform::Linux => "M4 — Linux packager out of scope (not WiX)".into(),
    }
}

/// Deploy / packaging boundary — capability + last artifact; Fake ↔ Std swappable.
///
/// Object-safe. Implementations must **not** run elevated `msiexec` / install.
pub trait DeployPort: Send + Sync {
    /// Query deploy capability for `platform` (Supported or Unsupported).
    fn capability(&self, platform: DeployPlatform) -> Result<DeployCapability, PortError>;

    /// Last known artifact path string, if the adapter has recorded / discovered one.
    fn last_artifact_path(&self) -> Result<Option<String>, PortError>;

    /// Combined status for `platform` plus [`Self::last_artifact_path`].
    fn status(&self, platform: DeployPlatform) -> Result<DeployStatus, PortError> {
        let cap = self.capability(platform)?;
        Ok(DeployStatus {
            platform: cap.platform,
            support: cap.support,
            last_artifact_path: self.last_artifact_path()?,
        })
    }
}
