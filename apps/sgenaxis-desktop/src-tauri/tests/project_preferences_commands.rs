#[path = "../src/dispatch.rs"] mod dispatch;
#[path = "../src/dto.rs"] mod dto;
#[path = "../src/git_index_commit.rs"] mod git_index_commit;
use dispatch::DispatchHost;
use sgenaxis_adapters::FakeFileSystem;
use sgenaxis_ports::FileSystemPort;
#[test]
fn presets_and_import_preview_reuse_validated_schema_without_writing() {
 let fs=FakeFileSystem::new();let presets=DispatchHost::project_policy_presets().unwrap();
 assert_eq!(presets["balanced"]["batch"]["maxTasks"],4);
 let bytes=serde_json::to_vec(&presets["balanced"]).unwrap();fs.write_atomic("/selected.json",&bytes).unwrap();let writes=fs.write_count();
 let preview=DispatchHost::project_policy_import(&fs,"/selected.json").unwrap();assert_eq!(preview["status"],"ok");assert_eq!(fs.write_count(),writes);assert_eq!(fs.read("/selected.json").unwrap(),bytes);
}
#[test]
fn imported_secret_field_is_rejected_without_source_mutation() {
 let fs=FakeFileSystem::new();let mut value=DispatchHost::project_policy_presets().unwrap()["balanced"].clone();value["token"]=serde_json::json!("fixture-secret");let bytes=serde_json::to_vec(&value).unwrap();fs.write_atomic("/invalid.json",&bytes).unwrap();let writes=fs.write_count();
 assert!(DispatchHost::project_policy_import(&fs,"/invalid.json").is_err());assert_eq!(fs.write_count(),writes);assert_eq!(fs.read("/invalid.json").unwrap(),bytes);
}
#[test]
fn unbound_or_stale_project_is_rejected_before_any_write() {
 let fs=FakeFileSystem::new();
 assert!(DispatchHost::project_policy_load(&fs,""," ").is_err());
 assert!(DispatchHost::project_policy_save(&fs,"/B","/A",None,b"{}").is_err());assert_eq!(fs.write_count(),0);
}
#[test]
fn current_project_load_save_and_stale_digest() {
 let fs=FakeFileSystem::new();let draft=serde_json::to_vec(&sgenaxis_spec::project_preferences::preset("balanced").unwrap()).unwrap();
 assert_eq!(DispatchHost::project_policy_load(&fs,"/A","/A").unwrap()["configured"],false);
 let saved=DispatchHost::project_policy_save(&fs,"/A","/A",None,&draft).unwrap();
 assert_eq!(saved["preferences"]["batch"]["maxTasks"],4);
 assert_eq!(DispatchHost::project_policy_load(&fs,"/A","/A").unwrap(),saved);
 assert!(DispatchHost::project_policy_save(&fs,"/A","/A",Some("stale"),&draft).is_err());
}
// Owner-approved migration: original success obligations remain archived and BLOCKED
// at docs/ci/wizard-contract-alignment; rejection is not wizard success coverage.
struct CreationFileSystemSpy {
    inner: FakeFileSystem,
    calls: std::sync::Mutex<Vec<&'static str>>,
}

impl CreationFileSystemSpy {
    fn seeded() -> Self {
        let inner = FakeFileSystem::new();
        inner.seed("/projects/existing/keep.txt", b"original fixture content");
        Self { inner, calls: std::sync::Mutex::new(Vec::new()) }
    }

    fn record(&self, operation: &'static str) {
        self.calls.lock().unwrap().push(operation);
    }

    fn assert_untouched(&self, name: &str) {
        // Inspect the call log before using the inner fake for verification reads.
        assert!(self.calls.lock().unwrap().is_empty(), "even filesystem reads are forbidden");
        assert_eq!(self.inner.write_count(), 0);
        assert_eq!(self.inner.mkdir_count(), 0);
        assert_eq!(self.inner.read("/projects/existing/keep.txt").unwrap(), b"original fixture content");
        assert!(!self.inner.exists(&format!("/projects/{name}")).unwrap());
        assert!(!self.inner.exists(&format!("/projects/{name}/.sgenaxis/preferences.json")).unwrap());
    }
}

impl FileSystemPort for CreationFileSystemSpy {
    fn exists(&self, path: &str) -> Result<bool, sgenaxis_ports::PortError> {
        self.record("exists"); self.inner.exists(path)
    }
    fn is_file(&self, path: &str) -> Result<bool, sgenaxis_ports::PortError> {
        self.record("is_file"); self.inner.is_file(path)
    }
    fn read(&self, path: &str) -> Result<Vec<u8>, sgenaxis_ports::PortError> {
        self.record("read"); self.inner.read(path)
    }
    fn read_to_string(&self, path: &str) -> Result<String, sgenaxis_ports::PortError> {
        self.record("read_to_string"); self.inner.read_to_string(path)
    }
    fn write_atomic(&self, path: &str, bytes: &[u8]) -> Result<(), sgenaxis_ports::PortError> {
        self.record("write_atomic"); self.inner.write_atomic(path, bytes)
    }
    fn create_dir_all(&self, path: &str) -> Result<(), sgenaxis_ports::PortError> {
        self.record("create_dir_all"); self.inner.create_dir_all(path)
    }
    fn remove_file(&self, path: &str) -> Result<(), sgenaxis_ports::PortError> {
        self.record("remove_file"); self.inner.remove_file(path)
    }
}

#[test]
fn legacy_skip_requires_wizard_before_any_fs_access() {
    let fs = CreationFileSystemSpy::seeded();
    let result = DispatchHost::project_policy_create(&fs, "/projects", "skip", None, None);
    assert_eq!(result.unwrap_err(), "WizardRequired");
    fs.assert_untouched("skip");
}

#[test]
fn legacy_preset_requires_wizard_before_any_fs_access() {
    let fs = CreationFileSystemSpy::seeded();
    let result = DispatchHost::project_policy_create(&fs, "/projects", "preset", Some("balanced"), None);
    assert_eq!(result.unwrap_err(), "WizardRequired");
    fs.assert_untouched("preset");
}

#[test]
fn legacy_conflicting_choices_reject_before_any_fs_access() {
    let fs = CreationFileSystemSpy::seeded();
    let result = DispatchHost::project_policy_create(&fs, "/projects", "bad", Some("balanced"), Some("{}"));
    assert_eq!(result.unwrap_err(), "CHOOSE_PRESET_OR_IMPORT");
    fs.assert_untouched("bad");
    assert!(!fs.inner.exists("/projects/bad").unwrap());
}
