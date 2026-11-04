//! Project policy storage. Callers serialize same-process mutation through HOST.
//! Digest checks detect stale drafts, not cross-process atomic compare-and-swap.
use sgenaxis_ports::{FileSystemPort, PortError};
use sgenaxis_spec::packet::source_sha256;
use sgenaxis_spec::project_preferences::{
    parse_project_preferences, validate, PreferenceError, ProjectPreferences, PREFERENCES_PATH,
};
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PreferenceView {
    pub project_root: String,
    pub preferences: ProjectPreferences,
    pub digest: String,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectPreferenceError {
    /// Deprecated creation entry requires the six-step wizard.
    WizardRequired,
    InvalidRoot,
    Conflict,
    Policy(PreferenceError),
    Storage(PortError),
    ExistingTarget,
}

pub enum PreferenceChoice<'a> {
    Skip,
    Preset(&'a str),
    Imported(&'a [u8]),
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreationOutcome {
    Created {
        project_root: String,
        preferences: Option<PreferenceView>,
    },
    DirectoryCreatedPreferencesFailed {
        project_root: String,
        error: ProjectPreferenceError,
    },
}
/// Does not bind HOST settings or delete any source, file or directory.
pub fn create_project_with_preferences(
    fs: &dyn FileSystemPort,
    root: &str,
    choice: PreferenceChoice<'_>,
) -> Result<CreationOutcome, ProjectPreferenceError> {
    let _ = (fs, choice);
    root_path(root)?;
    Err(ProjectPreferenceError::WizardRequired)
}

fn root_path(root: &str) -> Result<(String, String), ProjectPreferenceError> {
    if root.contains('\0') {
        return Err(ProjectPreferenceError::InvalidRoot);
    }
    let root = crate::project_new::normalize_new_project_path(root)
        .map_err(|_| ProjectPreferenceError::InvalidRoot)?;
    let path = format!(
        "{}/{}",
        root.trim_end_matches(['/', '\\']),
        PREFERENCES_PATH
    );
    Ok((root, path))
}
pub fn load_project_preferences(
    fs: &dyn FileSystemPort,
    root: &str,
) -> Result<Option<PreferenceView>, ProjectPreferenceError> {
    let (root, path) = root_path(root)?;
    let bytes = match fs.read(&path) {
        Ok(bytes) => bytes,
        Err(PortError::NotFound(_)) => return Ok(None),
        Err(e) => return Err(ProjectPreferenceError::Storage(e)),
    };
    let preferences = parse_project_preferences(&bytes).map_err(ProjectPreferenceError::Policy)?;
    Ok(Some(PreferenceView {
        project_root: root,
        preferences,
        digest: source_sha256(&bytes),
    }))
}
pub fn save_project_preferences(
    fs: &dyn FileSystemPort,
    root: &str,
    expected_digest: Option<&str>,
    draft: &ProjectPreferences,
) -> Result<PreferenceView, ProjectPreferenceError> {
    let (root, path) = root_path(root)?;
    validate(draft).map_err(ProjectPreferenceError::Policy)?;
    let current = load_project_preferences(fs, &root)?;
    if current.as_ref().map(|v| v.digest.as_str()) != expected_digest {
        return Err(ProjectPreferenceError::Conflict);
    }
    let bytes = serde_json::to_vec_pretty(draft)
        .map_err(|_| ProjectPreferenceError::Policy(PreferenceError::InvalidDocument))?;
    fs.create_dir_all(&format!("{}/.sgenaxis", root.trim_end_matches(['/', '\\'])))
        .map_err(ProjectPreferenceError::Storage)?;
    // Recheck after directory preparation. This is still not an OS-level CAS.
    let latest = load_project_preferences(fs, &root)?;
    if latest.as_ref().map(|v| v.digest.as_str()) != expected_digest {
        return Err(ProjectPreferenceError::Conflict);
    }
    fs.write_atomic(&path, &bytes)
        .map_err(ProjectPreferenceError::Storage)?;
    let readback = fs.read(&path).map_err(ProjectPreferenceError::Storage)?;
    if readback != bytes {
        return Err(ProjectPreferenceError::Conflict);
    }
    let preferences =
        parse_project_preferences(&readback).map_err(ProjectPreferenceError::Policy)?;
    Ok(PreferenceView {
        project_root: root,
        preferences,
        digest: source_sha256(&readback),
    })
}
