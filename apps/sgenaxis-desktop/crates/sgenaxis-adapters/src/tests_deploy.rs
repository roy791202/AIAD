//! PD-DEPLOY-PORT-01 — capability / last path / Unsupported / Fake↔Std swap.

use sgenaxis_ports::{
    windows_wix_artifact_relpath, DeployPlatform, DeployPort, DeploySupport,
    WINDOWS_WIX_FORMAT, WINDOWS_WIX_PACKAGER, WINDOWS_WIX_PRODUCT_VERSION,
};

use crate::fake::FakeDeploy;
use crate::StdDeploy;

fn assert_windows_wix_supported(port: &dyn DeployPort) {
    let cap = port.capability(DeployPlatform::Windows).expect("windows cap");
    assert_eq!(cap.platform, DeployPlatform::Windows);
    match cap.support {
        DeploySupport::Supported {
            packager,
            format,
            artifact_path_convention,
        } => {
            assert_eq!(packager, WINDOWS_WIX_PACKAGER);
            assert_eq!(format, WINDOWS_WIX_FORMAT);
            assert_eq!(
                artifact_path_convention,
                windows_wix_artifact_relpath(WINDOWS_WIX_PRODUCT_VERSION)
            );
            assert!(artifact_path_convention.contains("packaging/windows/wix/out"));
            assert!(artifact_path_convention.ends_with(".msi"));
        }
        DeploySupport::Unsupported { reason } => {
            panic!("Windows must be Supported, got Unsupported: {reason}");
        }
    }
}

fn assert_unsupported(port: &dyn DeployPort, platform: DeployPlatform) {
    let cap = port.capability(platform).expect("cap");
    match cap.support {
        DeploySupport::Unsupported { reason } => {
            assert!(!reason.is_empty(), "unsupported reason must be non-empty");
            assert!(
                reason.contains("M4") || reason.to_lowercase().contains("out of scope"),
                "unexpected reason: {reason}"
            );
        }
        DeploySupport::Supported { .. } => panic!("{platform:?} must be Unsupported"),
    }
}

#[test]
fn fake_deploy_windows_wix_and_unsupported_platforms() {
    let fake = FakeDeploy::m3_defaults();
    assert_windows_wix_supported(&fake);
    assert_unsupported(&fake, DeployPlatform::MacOs);
    assert_unsupported(&fake, DeployPlatform::Linux);
    assert_eq!(fake.last_artifact_path().unwrap(), None);
}

#[test]
fn fake_deploy_last_artifact_path_settable() {
    let fake = FakeDeploy::m3_defaults();
    let path = r"D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi";
    fake.set_last_artifact_path(Some(path.into())).unwrap();
    assert_eq!(fake.last_artifact_path().unwrap().as_deref(), Some(path));

    let st = fake.status(DeployPlatform::Windows).unwrap();
    assert_eq!(st.last_artifact_path.as_deref(), Some(path));
    match st.support {
        DeploySupport::Supported { packager, .. } => assert_eq!(packager, "wix"),
        DeploySupport::Unsupported { .. } => panic!("expected Supported"),
    }
}

#[test]
fn std_deploy_windows_wix_macos_linux_unsupported() {
    let std = StdDeploy::new();
    assert_windows_wix_supported(&std);
    assert_unsupported(&std, DeployPlatform::MacOs);
    assert_unsupported(&std, DeployPlatform::Linux);
}

#[test]
fn std_deploy_probes_msi_under_repo_root() {
    // Prefer live AIAD tree when present; otherwise last path is None.
    let repo = aiad_repo_root();
    let port = StdDeploy::with_repo_root(&repo);
    let last = port.last_artifact_path().unwrap();
    let expected_rel = windows_wix_artifact_relpath(WINDOWS_WIX_PRODUCT_VERSION);
    let expected = std::path::Path::new(&repo).join(expected_rel.replace('/', std::path::MAIN_SEPARATOR_STR));
    if expected.is_file() {
        let got = last.expect("MSI exists → last path Some");
        assert!(
            got.replace('/', "\\")
                .ends_with(r"packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi")
                || got.ends_with("SGenAxis-0.1.0-windows-x64.msi"),
            "unexpected last path: {got}"
        );
    } else {
        assert_eq!(last, None, "missing MSI → last path None");
    }
}

#[test]
fn swap_fake_and_std_behind_dyn_deploy_port() {
    let mut port: Box<dyn DeployPort> = Box::new(FakeDeploy::m3_defaults());
    assert_windows_wix_supported(port.as_ref());
    assert_unsupported(port.as_ref(), DeployPlatform::MacOs);

    port = Box::new(StdDeploy::with_repo_root(aiad_repo_root()));
    assert_windows_wix_supported(port.as_ref());
    assert_unsupported(port.as_ref(), DeployPlatform::Linux);

    // Same dyn slot accepts Fake again (swap).
    let again = FakeDeploy::m3_defaults();
    again
        .set_last_artifact_path(Some("/fake/out/SGenAxis-0.1.0-windows-x64.msi".into()))
        .unwrap();
    port = Box::new(again);
    assert_eq!(
        port.last_artifact_path().unwrap().as_deref(),
        Some("/fake/out/SGenAxis-0.1.0-windows-x64.msi")
    );
}

#[test]
fn status_surfaces_unsupported_without_error() {
    let port: &dyn DeployPort = &FakeDeploy::m3_defaults();
    let st = port.status(DeployPlatform::MacOs).unwrap();
    assert!(matches!(st.support, DeploySupport::Unsupported { .. }));
}

/// Resolve AIAD repo root from this crate path (…/crates/sgenaxis-adapters → repo).
fn aiad_repo_root() -> String {
    let manifest = env!("CARGO_MANIFEST_DIR");
    // crates/sgenaxis-adapters → apps/sgenaxis-desktop → apps → repo
    let root = std::path::Path::new(manifest)
        .join("../../..")
        .canonicalize()
        .unwrap_or_else(|_| std::path::PathBuf::from(manifest).join("../../.."));
    root.to_string_lossy().into_owned()
}
