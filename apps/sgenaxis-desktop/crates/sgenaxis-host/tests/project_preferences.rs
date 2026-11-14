use sgenaxis_adapters::FakeFileSystem;
use sgenaxis_host::project_preferences::*;
use sgenaxis_ports::{FileSystemPort, PortError};
use sgenaxis_spec::packet::source_sha256;
use sgenaxis_spec::project_preferences::{preset, PreferenceError};
use std::sync::atomic::{AtomicBool, Ordering};
#[test]
fn missing_file_stays_unconfigured_and_does_not_write_defaults() {
    let fs = FakeFileSystem::new();
    assert_eq!(load_project_preferences(&fs, "/projects/a"), Ok(None));
    assert_eq!(fs.write_count(), 0);
}
#[test]
fn save_reopen_and_project_isolation_use_exact_digest() {
    let fs = FakeFileSystem::new();
    let a =
        save_project_preferences(&fs, "/projects/a", None, &preset("balanced").unwrap()).unwrap();
    let b =
        save_project_preferences(&fs, "/projects/b", None, &preset("throughput").unwrap()).unwrap();
    assert_eq!(
        load_project_preferences(&fs, "/projects/a").unwrap(),
        Some(a.clone())
    );
    assert_eq!(
        load_project_preferences(&fs, "/projects/b").unwrap(),
        Some(b)
    );
    assert_eq!(
        a.digest,
        source_sha256(&fs.read("/projects/a/.sgenaxis/preferences.json").unwrap())
    );
}
#[test]
fn stale_and_missing_digests_never_overwrite_existing_policy() {
    let fs = FakeFileSystem::new();
    let a = save_project_preferences(&fs, "/a", None, &preset("balanced").unwrap()).unwrap();
    let before = fs.read("/a/.sgenaxis/preferences.json").unwrap();
    for expected in [None, Some("wrong")] {
        assert_eq!(
            save_project_preferences(&fs, "/a", expected, &preset("throughput").unwrap()),
            Err(ProjectPreferenceError::Conflict)
        );
    }
    assert_eq!(fs.read("/a/.sgenaxis/preferences.json").unwrap(), before);
    let next =
        save_project_preferences(&fs, "/a", Some(&a.digest), &preset("conservative").unwrap())
            .unwrap();
    assert_eq!(next.preferences.batch.max_tasks, 1);
}
#[test]
fn externally_reformatted_bytes_invalidate_draft() {
    let fs = FakeFileSystem::new();
    let a = save_project_preferences(&fs, "/a", None, &preset("balanced").unwrap()).unwrap();
    let mut bytes = fs.read("/a/.sgenaxis/preferences.json").unwrap();
    bytes.push(b'\n');
    fs.write_atomic("/a/.sgenaxis/preferences.json", &bytes)
        .unwrap();
    assert_eq!(
        save_project_preferences(&fs, "/a", Some(&a.digest), &a.preferences),
        Err(ProjectPreferenceError::Conflict)
    );
    assert_eq!(fs.read("/a/.sgenaxis/preferences.json").unwrap(), bytes);
}
#[test]
fn invalid_root_and_invalid_draft_have_zero_writes() {
    let fs = FakeFileSystem::new();
    for root in ["", " ", "https://example.invalid/project", "/demo/root"] {
        assert_eq!(
            load_project_preferences(&fs, root),
            Err(ProjectPreferenceError::InvalidRoot)
        );
    }
    let mut bad = preset("balanced").unwrap();
    bad.batch.max_tasks = 0;
    assert_eq!(
        save_project_preferences(&fs, "/a", None, &bad),
        Err(ProjectPreferenceError::Policy(
            PreferenceError::InvalidPolicy
        ))
    );
    assert_eq!(fs.write_count(), 0);
}
#[test]
fn malformed_existing_preferences_are_not_reset_or_overwritten() {
    let fs = FakeFileSystem::new();
    fs.write_atomic("/a/.sgenaxis/preferences.json", b"broken")
        .unwrap();
    assert!(matches!(
        load_project_preferences(&fs, "/a"),
        Err(ProjectPreferenceError::Policy(_))
    ));
    assert!(matches!(
        save_project_preferences(&fs, "/a", None, &preset("balanced").unwrap()),
        Err(ProjectPreferenceError::Policy(_))
    ));
    assert_eq!(fs.read("/a/.sgenaxis/preferences.json").unwrap(), b"broken");
    assert_eq!(fs.write_count(), 1);
}
struct FailWrite {
    fs: FakeFileSystem,
    deny_read: bool,
}
impl FileSystemPort for FailWrite {
    fn read(&self, p: &str) -> Result<Vec<u8>, PortError> {
        if self.deny_read {
            Err(PortError::PermissionDenied("read".into()))
        } else {
            self.fs.read(p)
        }
    }
    fn exists(&self, p: &str) -> Result<bool, PortError> {
        self.fs.exists(p)
    }
    fn is_file(&self, p: &str) -> Result<bool, PortError> {
        self.fs.is_file(p)
    }
    fn read_to_string(&self, p: &str) -> Result<String, PortError> {
        self.fs.read_to_string(p)
    }
    fn write_atomic(&self, _: &str, _: &[u8]) -> Result<(), PortError> {
        Err(PortError::PermissionDenied("write".into()))
    }
    fn create_dir_all(&self, p: &str) -> Result<(), PortError> {
        self.fs.create_dir_all(p)
    }
    fn remove_file(&self, _: &str) -> Result<(), PortError> {
        panic!("must not remove source")
    }
}
#[test]
fn permission_read_failure_is_explicit_not_unconfigured() {
    let fs = FailWrite {
        fs: FakeFileSystem::new(),
        deny_read: true,
    };
    assert!(matches!(
        load_project_preferences(&fs, "/a"),
        Err(ProjectPreferenceError::Storage(
            PortError::PermissionDenied(_)
        ))
    ));
}
#[test]
fn write_failure_preserves_prior_valid_document() {
    let inner = FakeFileSystem::new();
    let old = save_project_preferences(&inner, "/a", None, &preset("balanced").unwrap()).unwrap();
    let fs = FailWrite {
        fs: inner,
        deny_read: false,
    };
    let bytes = fs.fs.read("/a/.sgenaxis/preferences.json").unwrap();
    assert!(matches!(
        save_project_preferences(&fs, "/a", Some(&old.digest), &preset("throughput").unwrap()),
        Err(ProjectPreferenceError::Storage(
            PortError::PermissionDenied(_)
        ))
    ));
    assert_eq!(fs.fs.read("/a/.sgenaxis/preferences.json").unwrap(), bytes);
}

#[derive(Clone, Copy)]
enum ReadbackFaultMode {
    MismatchedBytes,
    ReadFailure,
}

struct PostWriteReadbackFault {
    fs: FakeFileSystem,
    mode: ReadbackFaultMode,
    wrote: AtomicBool,
}

impl FileSystemPort for PostWriteReadbackFault {
    fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
        if self.wrote.load(Ordering::SeqCst) {
            return match self.mode {
                ReadbackFaultMode::MismatchedBytes => Ok(b"different bytes".to_vec()),
                ReadbackFaultMode::ReadFailure => {
                    Err(PortError::PermissionDenied("post-write readback".into()))
                }
            };
        }
        self.fs.read(path)
    }

    fn exists(&self, path: &str) -> Result<bool, PortError> {
        self.fs.exists(path)
    }

    fn is_file(&self, path: &str) -> Result<bool, PortError> {
        self.fs.is_file(path)
    }

    fn read_to_string(&self, path: &str) -> Result<String, PortError> {
        self.fs.read_to_string(path)
    }

    fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError> {
        self.fs.write_atomic(path, contents)?;
        self.wrote.store(true, Ordering::SeqCst);
        Ok(())
    }

    fn create_dir_all(&self, path: &str) -> Result<(), PortError> {
        self.fs.create_dir_all(path)
    }

    fn remove_file(&self, path: &str) -> Result<(), PortError> {
        self.fs.remove_file(path)
    }
}

#[test]
fn successful_write_with_mismatched_readback_returns_conflict() {
    let fs = PostWriteReadbackFault {
        fs: FakeFileSystem::new(),
        mode: ReadbackFaultMode::MismatchedBytes,
        wrote: AtomicBool::new(false),
    };

    assert_eq!(
        save_project_preferences(&fs, "/a", None, &preset("balanced").unwrap()),
        Err(ProjectPreferenceError::Conflict)
    );
}

#[test]
fn successful_write_with_readback_failure_returns_storage_error() {
    let fs = PostWriteReadbackFault {
        fs: FakeFileSystem::new(),
        mode: ReadbackFaultMode::ReadFailure,
        wrote: AtomicBool::new(false),
    };

    assert!(matches!(
        save_project_preferences(&fs, "/a", None, &preset("balanced").unwrap()),
        Err(ProjectPreferenceError::Storage(PortError::PermissionDenied(message)))
            if message == "post-write readback"
    ));
}
