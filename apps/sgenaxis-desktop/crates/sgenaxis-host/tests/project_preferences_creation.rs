//! M01-S2 migration of the existing native preference roundtrip.
//! Original source is retained in planning/s2-exact-design/legacy-history.
//! Seven other original creation tests retain their names and full behavior in
//! phase1_project_definition.rs; see migration-map.json. This is real native IO.
//!
//! StdFileCommit is a Windows-only adapter (uses std::os::windows::fs) and is
//! only exported under cfg(all(windows, feature = "std-adapters")), so this
//! whole native-IO test compiles on Windows only. Matches the guard on
//! adapters/tests/phase1_file_commit.rs. On Linux CI the test binary is empty.
#![cfg(all(windows, feature = "std-adapters"))]
use sgenaxis_host::project_definition::*;
use sgenaxis_host::project_preferences::*;
use sgenaxis_ports::FileSystemPort;
use sgenaxis_spec::project_preferences::preset;
use sgenaxis_work::project_definition::*;

struct OwnedFixture {
    base: std::path::PathBuf,
}
impl Drop for OwnedFixture {
    fn drop(&mut self) {
        // Never recursively delete or remove unknown files. Only named fixture
        // artifacts beneath the exclusively created private parent are eligible.
        let root = self.base.join("Project-A");
        if self.base.join("fixture-owner").is_file() {
            for relative in [
                ".sgenaxis/project-definition.json",
                ".sgenaxis/preferences.json",
                ".sgenaxis/project-definition.json.eluslot-lock",
                ".sgenaxis/preferences.json.eluslot-lock",
            ] {
                let path = root.join(relative);
                if path.is_file() {
                    if relative.ends_with(".eluslot-lock")
                        && std::fs::read(&path).map(|b| !b.is_empty()).unwrap_or(true)
                    {
                        continue;
                    }
                    let _ = std::fs::remove_file(&path);
                }
            }
            // IO owns its own sidecars. Leftover/uncertain evidence is retained;
            // remove_dir intentionally fails rather than erasing unknown files.
            let _ = std::fs::remove_dir(root.join(".sgenaxis"));
            let _ = std::fs::remove_dir(root);
            if std::fs::read_dir(&self.base)
                .map(|mut x| x.by_ref().count() == 1)
                .unwrap_or(false)
            {
                let _ = std::fs::remove_file(self.base.join("fixture-owner"));
                let _ = std::fs::remove_dir(&self.base);
            }
        }
    }
}
#[test]
fn real_filesystem_project_preference_roundtrip() {
    let base = std::env::temp_dir().join(format!(
        "sgenaxis-definition-fixture-{}-{}",
        std::process::id(),
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos()
    ));
    // Exclusive native fixture setup; no user project or shared directory.
    std::fs::create_dir(&base).unwrap();
    std::fs::write(base.join("fixture-owner"), b"M01-S2-owned-fixture").unwrap();
    let fixture = OwnedFixture {
        base: std::fs::canonicalize(&base).unwrap(),
    };
    let parent = fixture.base.to_str().unwrap();
    let root = fixture.base.join("Project-A");
    assert!(!root.exists());
    let fs = sgenaxis_adapters::StdFileSystem::new();
    let commit = sgenaxis_adapters::StdFileCommit::new();
    let context = DefinitionAuthorityContext {
        selection_id: "native-test-selection".into(),
        session_id: "native-test-session".into(),
        owner_window: "test".into(),
    };
    let prepared = prepare_definition_preferences(PreferenceChoice::Preset("balanced"));
    assert!(prepared.is_ok(), "prepare public boundary: {prepared:?}");
    let definition = ProjectDefinition {
        project_uuid: PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),
        definition_revision: DefinitionRevision(0),
        mode: DefinitionMode::Draft,
        approval_refs: vec![],
        legacy_root_keys: vec!["proj_legacy_A".into()],
        draft: DefinitionDraft {
            name: "Local Design".into(),
            purpose: "先保存需求草稿".into(),
            last_saved_step: WizardStep::Delivery,
            delivery_targets: vec![],
            topology: FieldState::Unresolved,
            requirements: vec![],
            preference_source: PreferenceSource::Preset,
            template: None,
            open_decisions: vec!["delivery.form".into(), "technology.framework".into()],
            extensions: match ExtensionValue::Object([].into_iter().collect()) {
                ExtensionValue::Object(o) => o,
                _ => unreachable!(),
            },
        },
    };
    let binding = bind_definition(
        &fs,
        context,
        DefinitionLocation::NewProject {
            canonical_parent: parent.into(),
            single_name: "Project-A".into(),
        },
        definition.project_uuid.clone(),
        DefinitionBaseline::Absent,
        prepared.unwrap(),
        &[],
    );
    assert!(binding.is_ok(), "native fixture binding: {binding:?}");
    let result = save_definition(&fs, &commit, &binding.unwrap(), None, &definition);
    assert!(
        result.is_ok(),
        "native explicit definition creation: {result:?}"
    );
    let receipt = result.unwrap();
    assert!(receipt.creation.root_created);
    assert!(matches!(
        receipt.preferences,
        PreferenceCommitStatus::Committed { .. }
    ));
    // Existing preference editor uses Win32 paths, not verbatim mixed separators.
    // Keep its old path convention while S2 receipts retain canonical identity.
    let native_path = root.to_str().unwrap();
    let path = native_path.strip_prefix(r"\\?\").unwrap_or(native_path);
    assert_eq!(std::fs::canonicalize(path).unwrap(), root);
    let view = load_project_preferences(&fs, path)
        .unwrap()
        .expect("persisted preferences");
    assert_eq!(view.preferences, preset("balanced").unwrap());
    let bytes = fs
        .read(
            &root
                .join(".sgenaxis/project-definition.json")
                .to_string_lossy(),
        )
        .unwrap();
    assert_eq!(decode_definition(&bytes), Ok(definition));
    let next = save_project_preferences(
        &fs,
        path,
        Some(&view.digest),
        &preset("throughput").unwrap(),
    )
    .unwrap();
    assert_eq!(load_project_preferences(&fs, path).unwrap(), Some(next));
    drop(fixture);
    assert!(
        !base.exists(),
        "native cleanup retained unexpected sidecars; investigate, do not recursively delete"
    );
}
