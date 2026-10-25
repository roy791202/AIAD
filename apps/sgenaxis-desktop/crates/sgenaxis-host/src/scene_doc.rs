//! Project-scoped scene files under `scene/` (`.ess` XML／`.es`／`.esml`／`.esui`).
//! Writes only relative paths inside the bound project — no arbitrary FS paths from UI.
//! Legacy `.sgs`／`.sg`／`.sgml`／`.sgui` remain readable for migration.

use sgenaxis_ports::FileSystemPort;

use crate::error::HostError;
use crate::uidesign_doc::join_project_rel;

pub const SCENE_DIR: &str = "scene";
pub const DEFAULT_SGS_REL: &str = "scene/default.ess";
pub const DEFAULT_SG_REL: &str = "scene/default.es";
pub const DEFAULT_SGML_REL: &str = "scene/default.esml";
pub const DEFAULT_SGUI_REL: &str = "scene/default.esui";

const ALLOWED_EXT: &[&str] = &[
    ".ess", ".es", ".esml", ".esui", ".sgs", ".sg", ".sgml", ".sgui", ".xml",
];

fn assert_scene_rel(rel: &str) -> Result<(), HostError> {
    let rel = rel.trim().trim_start_matches(['/', '\\']).replace('\\', "/");
    if rel.is_empty() {
        return Err(HostError::Settings("scene relative path empty".into()));
    }
    if !rel.starts_with("scene/") {
        return Err(HostError::Settings(
            "scene path must be under scene/ (project-scoped only)".into(),
        ));
    }
    if rel.contains("..") {
        return Err(HostError::Settings(
            "scene path must not contain ..".into(),
        ));
    }
    let lower = rel.to_ascii_lowercase();
    if !ALLOWED_EXT.iter().any(|ext| lower.ends_with(ext)) {
        return Err(HostError::Settings(format!(
            "scene extension not allowed (use {} )",
            ALLOWED_EXT.join("／")
        )));
    }
    Ok(())
}

pub fn normalize_scene_rel(rel: Option<&str>, default_rel: &str) -> Result<String, HostError> {
    let raw = rel
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or(default_rel);
    if raw.starts_with(['/', '\\']) {
        return Err(HostError::Settings("scene path must be project-relative".into()));
    }
    let norm = raw.replace('\\', "/");
    assert_scene_rel(&norm)?;
    Ok(norm)
}

pub fn save_scene_text(
    fs: &dyn FileSystemPort,
    project_root: &str,
    rel_path: &str,
    text: &str,
) -> Result<String, HostError> {
    let rel = normalize_scene_rel(Some(rel_path), DEFAULT_SGS_REL)?;
    let path = join_project_rel(project_root, &rel)?;
    if let Some(parent) = std::path::Path::new(&path).parent() {
        let parent_s = parent.to_string_lossy();
        if !parent_s.is_empty() {
            fs.create_dir_all(&parent_s).map_err(|e| {
                HostError::Settings(format!("mkdir for scene save: {e}"))
            })?;
        }
    }
    fs.write_atomic(&path, text.as_bytes())
        .map_err(|e| HostError::Settings(format!("write scene file: {e}")))?;
    Ok(path)
}

pub fn load_scene_text(
    fs: &dyn FileSystemPort,
    project_root: &str,
    rel_path: &str,
) -> Result<(String, String), HostError> {
    let rel = normalize_scene_rel(Some(rel_path), DEFAULT_SGS_REL)?;
    let path = join_project_rel(project_root, &rel)?;
    let raw = fs
        .read_to_string(&path)
        .map_err(|e| HostError::Settings(format!("read scene file: {e}")))?;
    Ok((raw, path))
}

pub fn scene_file_exists(
    fs: &dyn FileSystemPort,
    project_root: &str,
    rel_path: &str,
) -> Result<bool, HostError> {
    let rel = normalize_scene_rel(Some(rel_path), DEFAULT_SGS_REL)?;
    let path = join_project_rel(project_root, &rel)?;
    Ok(fs.exists(&path).unwrap_or(false))
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::fake::FakeFileSystem;

    #[test]
    fn rejects_outside_scene_dir() {
        let err = normalize_scene_rel(Some("design/main.ess"), DEFAULT_SGS_REL).unwrap_err();
        assert!(err.to_string().contains("scene/"));
    }

    #[test]
    fn roundtrip_ess_text() {
        let fs = FakeFileSystem::new();
        let root = "/work/proj";
        fs.create_dir_all(root).unwrap();
        let path = save_scene_text(&fs, root, DEFAULT_SGS_REL, "<eluslotScene/>\n").unwrap();
        assert!(path.replace('\\', "/").ends_with("scene/default.ess"));
        let (text, _) = load_scene_text(&fs, root, DEFAULT_SGS_REL).unwrap();
        assert!(text.contains("eluslotScene"));
    }

    #[test]
    fn allows_legacy_sgs_extension() {
        let rel = normalize_scene_rel(Some("scene/default.sgs"), DEFAULT_SGS_REL).unwrap();
        assert_eq!(rel, "scene/default.sgs");
    }

    #[test]
    fn invalid_scene_paths_preserve_existing_document() {
        let fs = FakeFileSystem::new();
        let root = "C:/work/project";
        let original = save_scene_text(&fs, root, DEFAULT_SGS_REL, "original").unwrap();
        for rel in ["scene/C:/outside.ess", "scene/C:outside.ess", "/scene/outside.ess", r"\scene\outside.ess", "scene/../outside.ess", "scene/main.ess:stream.ess"] {
            assert!(save_scene_text(&fs, root, rel, "replacement").is_err(), "accepted {rel:?}");
            assert!(load_scene_text(&fs, root, rel).is_err(), "read accepted {rel:?}");
            assert!(scene_file_exists(&fs, root, rel).is_err(), "exists accepted {rel:?}");
            assert_eq!(fs.read_to_string(&original).unwrap(), "original");
        }
    }
}
