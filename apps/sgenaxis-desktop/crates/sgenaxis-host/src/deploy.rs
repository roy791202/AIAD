//! PD-DEPLOY-CMD-01 — HOST façade over [`sgenaxis_ports::DeployPort`].
//!
//! Tauri invokes `deploy_status`／`deploy_check`／`list_artifacts` (read-only).
//! No arbitrary shell; no elevated `/qn` auto. Failures map to observable
//! `Result`／structured check status.
//!
//! Depends on **PD-DEPLOY-PORT-01** (`sgenaxis-ports`／`sgenaxis-adapters`).

use serde::{Deserialize, Serialize};
use sgenaxis_ports::{
    windows_wix_artifact_relpath, DeployPlatform, DeployPort, DeploySupport, FileSystemPort,
    PathPort, PortError, WINDOWS_WIX_PRODUCT_VERSION,
};

/// Read-only status DTO for IPC (policy fields beyond the Port).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DeployStatusView {
    pub supported: bool,
    pub platform: String,
    pub packaging: String,
    pub format: String,
    pub message: String,
    /// Policy: always `false` — HOST never auto-runs elevated `/qn`.
    pub elevated_qn_auto: bool,
    pub artifact_convention: Option<String>,
    pub last_artifact_path: Option<String>,
}

/// Read-only check DTO (presence／capability; never installs).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DeployCheckView {
    /// `ok`／`warn`／`error`／`unsupported`
    pub status: String,
    pub ok: bool,
    pub issues: Vec<String>,
    /// Artifact present → operator must run elevated `/qn` manually.
    pub needs_manual_elevated: bool,
    pub message: String,
}

/// One packaging artifact row for UI listing.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DeployArtifactView {
    pub kind: String,
    pub path: String,
    pub exists: bool,
    pub sha256: Option<String>,
}

/// Focus platform for this host process.
pub fn focus_platform() -> DeployPlatform {
    if cfg!(windows) {
        DeployPlatform::Windows
    } else if cfg!(target_os = "macos") {
        DeployPlatform::MacOs
    } else {
        DeployPlatform::Linux
    }
}

pub fn platform_label(p: DeployPlatform) -> &'static str {
    match p {
        DeployPlatform::Windows => "windows",
        DeployPlatform::MacOs => "macos",
        DeployPlatform::Linux => "linux",
    }
}

/// Map Port status → IPC view (`elevated_qn_auto` always false).
pub fn status_view(
    deploy: &dyn DeployPort,
    platform: DeployPlatform,
) -> Result<DeployStatusView, PortError> {
    let st = deploy.status(platform)?;
    match st.support {
        DeploySupport::Supported {
            packager,
            format,
            artifact_path_convention,
        } => Ok(DeployStatusView {
            supported: true,
            platform: platform_label(st.platform).into(),
            packaging: packager,
            format,
            message: "deploy capability Supported (read-only; no elevated /qn auto)".into(),
            elevated_qn_auto: false,
            artifact_convention: Some(artifact_path_convention),
            last_artifact_path: st.last_artifact_path,
        }),
        DeploySupport::Unsupported { reason } => Ok(DeployStatusView {
            supported: false,
            platform: platform_label(st.platform).into(),
            packaging: "none".into(),
            format: "none".into(),
            message: reason,
            elevated_qn_auto: false,
            artifact_convention: None,
            last_artifact_path: st.last_artifact_path,
        }),
    }
}

/// Capability + artifact presence check (no msiexec／shell).
pub fn check_view(
    deploy: &dyn DeployPort,
    platform: DeployPlatform,
) -> Result<DeployCheckView, PortError> {
    let st = deploy.status(platform)?;
    match st.support {
        DeploySupport::Unsupported { reason } => Ok(DeployCheckView {
            status: "unsupported".into(),
            ok: false,
            issues: vec![reason.clone()],
            needs_manual_elevated: false,
            message: reason,
        }),
        DeploySupport::Supported {
            packager,
            format,
            artifact_path_convention,
        } => {
            let mut issues = Vec::new();
            let has = st.last_artifact_path.is_some();
            if !has {
                issues.push(format!(
                    "no last artifact yet (convention: {artifact_path_convention})"
                ));
            }
            let (status, ok) = if issues.is_empty() {
                ("ok".into(), true)
            } else {
                ("warn".into(), false)
            };
            Ok(DeployCheckView {
                status,
                ok,
                needs_manual_elevated: has,
                message: if has {
                    format!(
                        "{packager}/{format} artifact present; elevated /qn install is manual only"
                    )
                } else {
                    format!("{packager}/{format} supported; artifact not discovered yet")
                },
                issues,
            })
        }
    }
}

/// List convention + last artifact rows (existence from Port last path).
pub fn list_artifact_views(
    deploy: &dyn DeployPort,
    platform: DeployPlatform,
) -> Result<Vec<DeployArtifactView>, PortError> {
    let st = deploy.status(platform)?;
    let mut out = Vec::new();
    match &st.support {
        DeploySupport::Supported {
            format,
            artifact_path_convention,
            ..
        } => {
            let exists = st.last_artifact_path.is_some();
            out.push(DeployArtifactView {
                kind: format.clone(),
                path: artifact_path_convention.clone(),
                exists,
                sha256: None,
            });
            if let Some(last) = &st.last_artifact_path {
                if !path_matches_convention(last, artifact_path_convention) {
                    out.push(DeployArtifactView {
                        kind: "last_artifact".into(),
                        path: last.clone(),
                        exists: true,
                        sha256: None,
                    });
                }
            }
        }
        DeploySupport::Unsupported { reason } => {
            out.push(DeployArtifactView {
                kind: "unsupported".into(),
                path: String::new(),
                exists: false,
                sha256: Some(reason.clone()),
            });
        }
    }
    // Always surface the well-known Windows convention row for UI emptiness／docs,
    // even when focus platform is non-Windows (read-only catalogue).
    if platform != DeployPlatform::Windows {
        let conv = windows_wix_artifact_relpath(WINDOWS_WIX_PRODUCT_VERSION);
        out.push(DeployArtifactView {
            kind: "msi_convention".into(),
            path: conv,
            exists: false,
            sha256: None,
        });
    }
    Ok(out)
}

fn path_matches_convention(abs_or_rel: &str, convention: &str) -> bool {
    let a = abs_or_rel.replace('\\', "/");
    let c = convention.replace('\\', "/");
    a.ends_with(&c) || a.ends_with(c.rsplit('/').next().unwrap_or(c.as_str()))
}

/// Walk up from `start` looking for WiX packaging root or desktop app marker.
pub fn find_workspace_root(fs: &dyn FileSystemPort, path: &dyn PathPort, start: &str) -> Option<String> {
    let mut cur = start.to_string();
    for _ in 0..12 {
        let marker = path.join(&cur, &["packaging", "windows", "wix", "SGenAxis.wxs"]);
        if fs.exists(&marker).ok()? {
            return Some(cur);
        }
        let desktop = path.join(&cur, &["apps", "sgenaxis-desktop", "Cargo.toml"]);
        if fs.exists(&desktop).ok()? {
            return Some(cur);
        }
        let parent = parent_dir(&cur)?;
        if parent == cur {
            break;
        }
        cur = parent;
    }
    None
}

fn parent_dir(p: &str) -> Option<String> {
    let normalized = p.replace('\\', "/");
    let trimmed = normalized.trim_end_matches('/');
    let idx = trimmed.rfind('/')?;
    if idx == 0 {
        return Some("/".into());
    }
    let parent = &trimmed[..idx];
    if parent.is_empty() {
        return None;
    }
    if p.contains('\\') {
        Some(parent.replace('/', "\\"))
    } else {
        Some(parent.to_string())
    }
}

/// Default workspace root for boot (cwd). Empty if unavailable.
pub fn default_workspace_root() -> String {
    std::env::current_dir()
        .map(|p| p.to_string_lossy().into_owned())
        .unwrap_or_default()
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::fake::FakeDeploy;

    #[test]
    fn status_view_qn_auto_always_false() {
        let fake = FakeDeploy::m3_defaults();
        let v = status_view(&fake, DeployPlatform::Windows).unwrap();
        assert!(v.supported);
        assert!(!v.elevated_qn_auto);
        assert_eq!(v.packaging, "wix");
    }

    #[test]
    fn check_warns_without_artifact_manual_when_present() {
        let fake = FakeDeploy::m3_defaults();
        let c = check_view(&fake, DeployPlatform::Windows).unwrap();
        assert_eq!(c.status, "warn");
        assert!(!c.needs_manual_elevated);

        fake
            .set_last_artifact_path(Some(
                r"D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi".into(),
            ))
            .unwrap();
        let c2 = check_view(&fake, DeployPlatform::Windows).unwrap();
        assert!(c2.ok);
        assert!(c2.needs_manual_elevated);
        assert!(c2.message.contains("manual"));
    }

    #[test]
    fn unsupported_platform_observable() {
        let fake = FakeDeploy::m3_defaults();
        let v = status_view(&fake, DeployPlatform::MacOs).unwrap();
        assert!(!v.supported);
        let c = check_view(&fake, DeployPlatform::MacOs).unwrap();
        assert_eq!(c.status, "unsupported");
        assert!(!c.ok);
    }

    #[test]
    fn list_artifacts_includes_convention() {
        let fake = FakeDeploy::m3_defaults();
        let arts = list_artifact_views(&fake, DeployPlatform::Windows).unwrap();
        assert!(!arts.is_empty());
        assert_eq!(arts[0].kind, "msi");
        assert!(!arts[0].exists);
    }
}
