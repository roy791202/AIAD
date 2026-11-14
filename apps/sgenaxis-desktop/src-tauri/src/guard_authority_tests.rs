//! GUARD-S1 formal authority tests — production-bound seams in `dispatch.rs`.
//! Frozen assertions from owner-approved envelope; intended RED (behavior NotReady).
//! Doubles／fixture facts here are NOT Native／ACL／ConPTY／capture-producer PASS.

use super::{
    guard_qualify_red, guard_require_main_local, guard_validate_manifest, GuardApproval,
    GuardApprovalStatus, GuardAuthorityError, GuardCaptureFacts, GuardHostIntent,
    GuardManifestEntry, GuardNativeObservation, GuardPending, GuardSessionState, GuardSnapshot,
};

fn snapshot() -> GuardSnapshot {
    GuardSnapshot {
        task: "T1".into(),
        module: "M1".into(),
        project: "P1".into(),
        root: "D:/fixture".into(),
        input_fp: "fp1".into(),
        architecture: "a1".into(),
        bdd: "b1".into(),
        skeleton: "s1".into(),
        envelope: "e1".into(),
        red_id: "R1".into(),
        test_manifest: "tests1".into(),
    }
}

fn state() -> GuardSessionState {
    GuardSessionState {
        boot: 1,
        approval: Some(GuardApproval {
            session: 1,
            id: 11,
            binding: snapshot(),
            status: GuardApprovalStatus::Approved,
        }),
        pending: None,
    }
}

fn facts() -> GuardCaptureFacts {
    GuardCaptureFacts {
        host_owned: true,
        build_ok: true,
        case_id: "case1".into(),
        expected_case_id: "case1".into(),
        case_executed: true,
        case_ignored: false,
        case_failed: true,
        exit_code: 101,
        dual_eof: true,
        stream_error: false,
        same_snapshot: true,
        owner_qualifies: true,
    }
}

#[test]
fn gr01_exact_binding_consumes_before_execution() {
    let mut s = state();
    assert_eq!(
        s.authorize_start(GuardHostIntent::Implementation, 11, &snapshot()),
        Ok(())
    );
    assert_eq!(s.approval.unwrap().status, GuardApprovalStatus::Consumed);
}

#[test]
fn gr02_generic_cannot_bypass_implementation_reference() {
    let mut s = state();
    assert_eq!(
        s.authorize_start(GuardHostIntent::Unknown, 11, &snapshot()),
        Err(GuardAuthorityError::IntentUnknown)
    );
}

#[test]
fn gr03_every_changed_binding_rejects_field() {
    let names = [
        "task",
        "module",
        "project",
        "root",
        "input_fp",
        "architecture",
        "bdd",
        "skeleton",
        "envelope",
        "red_id",
        "test_manifest",
    ];
    for (n, name) in names.iter().enumerate() {
        let mut x = snapshot();
        match n {
            0 => x.task.push('x'),
            1 => x.module.push('x'),
            2 => x.project.push('x'),
            3 => x.root.push('x'),
            4 => x.input_fp.push('x'),
            5 => x.architecture.push('x'),
            6 => x.bdd.push('x'),
            7 => x.skeleton.push('x'),
            8 => x.envelope.push('x'),
            9 => x.red_id.push('x'),
            _ => x.test_manifest.push('x'),
        }
        let mut s = state();
        assert_eq!(
            s.authorize_start(GuardHostIntent::Implementation, 11, &x),
            Err(GuardAuthorityError::Stale(name)),
            "field {name}"
        );
        assert_eq!(s.approval.unwrap().status, GuardApprovalStatus::Approved);
    }
}

#[test]
fn gr04_consumed_replay_rejected() {
    let mut s = state();
    s.approval.as_mut().unwrap().status = GuardApprovalStatus::Consumed;
    assert_eq!(
        s.authorize_start(GuardHostIntent::Implementation, 11, &snapshot()),
        Err(GuardAuthorityError::Consumed)
    );
}

#[test]
fn gr05_revoked_rejected() {
    let mut s = state();
    s.approval.as_mut().unwrap().status = GuardApprovalStatus::Revoked;
    assert_eq!(
        s.authorize_start(GuardHostIntent::Implementation, 11, &snapshot()),
        Err(GuardAuthorityError::Revoked)
    );
}

#[test]
fn gr06_other_boot_reference_unknown() {
    let mut s = state();
    s.boot = 2;
    assert_eq!(
        s.authorize_start(GuardHostIntent::Implementation, 11, &snapshot()),
        Err(GuardAuthorityError::MissingRecord)
    );
}

#[test]
fn gr07_missing_reference_rejected() {
    let mut s = state();
    assert_eq!(
        s.authorize_start(GuardHostIntent::Implementation, 99, &snapshot()),
        Err(GuardAuthorityError::MissingRecord)
    );
}

#[test]
fn gr08_valid_capture_requires_both_provenances() {
    assert_eq!(guard_qualify_red(&facts()), Ok(()));
}

#[test]
fn gr09_negative_capture_matrix_cannot_be_overridden_by_yes() {
    for i in 0..10 {
        let mut x = facts();
        match i {
            0 => x.host_owned = false,
            1 => x.build_ok = false,
            2 => x.case_executed = false,
            3 => x.case_ignored = true,
            4 => x.case_failed = false,
            5 => x.exit_code = 0,
            6 => x.dual_eof = false,
            7 => x.stream_error = true,
            8 => x.same_snapshot = false,
            _ => x.case_id = "other".into(),
        }
        assert_eq!(
            guard_qualify_red(&x),
            Err(GuardAuthorityError::RedUnqualified),
            "negative capture {i}"
        );
    }
}

#[test]
fn gr10_valid_red_without_owner_qualification_rejected() {
    let mut x = facts();
    x.owner_qualifies = false;
    assert_eq!(
        guard_qualify_red(&x),
        Err(GuardAuthorityError::RedUnqualified)
    );
}

#[test]
fn gr11_manifest_valid_exact_paths() {
    let x = vec![GuardManifestEntry {
        relative_path: "src/a.rs".into(),
        sha256: "a".repeat(64),
    }];
    assert_eq!(guard_validate_manifest(&x), Ok(()));
}

#[test]
fn gr12_manifest_missing_duplicate_unsafe_or_bad_hash_rejected() {
    let make = |p: &str, h: &str| GuardManifestEntry {
        relative_path: p.into(),
        sha256: h.into(),
    };
    let hash = "a".repeat(64);
    let cases = vec![
        vec![],
        vec![make("../escape", &hash)],
        vec![make("D:/other", &hash)],
        vec![make("src/a", &hash), make("src/a", &hash)],
        vec![make("src/a", "bad")],
    ];
    for x in cases {
        assert_eq!(
            guard_validate_manifest(&x),
            Err(GuardAuthorityError::InvalidManifest)
        );
    }
}

#[test]
fn gr13_main_local_only_predicate() {
    assert_eq!(guard_require_main_local("main", true), Ok(()));
    for (label, local) in [
        ("ui-editor", true),
        ("ui-viewer", true),
        ("main", false),
        ("unknown", true),
    ] {
        assert_eq!(
            guard_require_main_local(label, local),
            Err(GuardAuthorityError::AuthorityDenied)
        );
    }
}

#[test]
fn gr14_native_cancel_creates_no_approval() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: Some(GuardPending {
            nonce: 8,
            binding: snapshot(),
            revoked: false,
        }),
    };
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::Cancel, &snapshot()),
        Err(GuardAuthorityError::NativeDeclined)
    );
    assert!(s.approval.is_none());
}

#[test]
fn gr15_native_yes_commits_exact_snapshot() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: Some(GuardPending {
            nonce: 8,
            binding: snapshot(),
            revoked: false,
        }),
    };
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::Yes, &snapshot()),
        Ok(())
    );
    assert_eq!(s.approval.as_ref().unwrap().binding, snapshot());
    assert!(s.pending.is_none());
}

#[test]
fn gr16_native_yes_after_bytes_changed_rejects() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: Some(GuardPending {
            nonce: 8,
            binding: snapshot(),
            revoked: false,
        }),
    };
    let mut x = snapshot();
    x.input_fp = "changed".into();
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::Yes, &x),
        Err(GuardAuthorityError::Stale("input_fp"))
    );
    assert!(s.approval.is_none());
}

#[test]
fn gr17_revoke_idempotent_prevents_start() {
    let mut s = state();
    assert_eq!(s.revoke(11), Ok(()));
    assert_eq!(s.revoke(11), Ok(()));
    assert_eq!(
        s.authorize_start(GuardHostIntent::Implementation, 11, &snapshot()),
        Err(GuardAuthorityError::Revoked)
    );
}

#[test]
fn gr18_generic_route_checks_host_owned_intent() {
    let s = state();
    assert_eq!(
        s.authorize_generic(GuardHostIntent::Implementation),
        Err(GuardAuthorityError::RequiresApproval)
    );
    assert_eq!(
        s.authorize_generic(GuardHostIntent::Unknown),
        Err(GuardAuthorityError::IntentUnknown)
    );
    assert_eq!(s.authorize_generic(GuardHostIntent::Generic), Ok(()));
}

#[test]
fn gr19_native_no_creates_no_approval() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: Some(GuardPending {
            nonce: 8,
            binding: snapshot(),
            revoked: false,
        }),
    };
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::No, &snapshot()),
        Err(GuardAuthorityError::NativeDeclined)
    );
    assert!(s.approval.is_none());
}

#[test]
fn gr20_repeated_nonce_cannot_commit_again() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: None,
    };
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::Yes, &snapshot()),
        Err(GuardAuthorityError::MissingRecord)
    );
    assert!(s.approval.is_none());
}

#[test]
fn gr21_project_switch_while_prompt_rejects() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: Some(GuardPending {
            nonce: 8,
            binding: snapshot(),
            revoked: false,
        }),
    };
    let mut x = snapshot();
    x.project = "P2".into();
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::Yes, &x),
        Err(GuardAuthorityError::Stale("project"))
    );
    assert!(s.approval.is_none());
}

#[test]
fn gr22_revoke_pending_prompt_wins_yes() {
    let mut s = GuardSessionState {
        boot: 1,
        approval: None,
        pending: Some(GuardPending {
            nonce: 8,
            binding: snapshot(),
            revoked: true,
        }),
    };
    assert_eq!(
        s.commit_native_observation(8, GuardNativeObservation::Yes, &snapshot()),
        Err(GuardAuthorityError::Revoked)
    );
    assert!(s.approval.is_none());
}

#[cfg(test)]
mod guard_fingerprint_tests {
    use super::super::{guard_current_byte_snapshot, GuardCurrentByteSnapshot, GuardInputManifest, GuardReadFailureCategory, GuardSnapshotProducerError};
    use sgenaxis_ports::{FileSystemPort, PortError};
    use std::collections::BTreeMap;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::sync::Mutex;

#[derive(Default)]
struct SnapshotFs {
    files: Mutex<BTreeMap<String, Vec<u8>>>,
    read_error: Mutex<Option<PortError>>,
    path_error: Mutex<Option<(String, PortError)>>,
    reads: AtomicUsize,
}

impl SnapshotFs {
    fn seed(&self, path: &str, bytes: &[u8]) {
        self.files.lock().unwrap().insert(path.into(), bytes.into());
    }

    fn fail_reads_with(&self, error: PortError) {
        *self.read_error.lock().unwrap() = Some(error);
    }

    fn fail_path_with(&self, path: &str, error: PortError) {
        *self.path_error.lock().unwrap() = Some((path.into(), error));
    }
}

impl FileSystemPort for SnapshotFs {
    fn exists(&self, path: &str) -> Result<bool, PortError> {
        Ok(self.files.lock().unwrap().contains_key(path))
    }

    fn read_to_string(&self, path: &str) -> Result<String, PortError> {
        String::from_utf8(self.read(path)?).map_err(|error| PortError::Io(error.to_string()))
    }

    fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
        self.reads.fetch_add(1, Ordering::SeqCst);
        if let Some((failed_path, error)) = self.path_error.lock().unwrap().clone() {
            if failed_path == path {
                return Err(error);
            }
        }
        if let Some(error) = self.read_error.lock().unwrap().clone() {
            return Err(error);
        }
        self.files
            .lock()
            .unwrap()
            .get(path)
            .cloned()
            .ok_or_else(|| PortError::NotFound(path.into()))
    }

    fn write_atomic(&self, _path: &str, _contents: &[u8]) -> Result<(), PortError> {
        Err(PortError::Other("write forbidden in snapshot test".into()))
    }

    fn create_dir_all(&self, _path: &str) -> Result<(), PortError> {
        Err(PortError::Other("mkdir forbidden in snapshot test".into()))
    }

    fn is_file(&self, path: &str) -> Result<bool, PortError> {
        self.exists(path)
    }

    fn remove_file(&self, _path: &str) -> Result<(), PortError> {
        Err(PortError::Other("remove forbidden in snapshot test".into()))
    }
}

fn input_manifest(inputs: &[&str]) -> GuardInputManifest {
    let paths = inputs.iter().map(|path| (*path).into()).collect::<Vec<_>>();
    GuardInputManifest {
        revision: "manifest-v1".into(),
        inputs: paths.clone(),
        architecture: paths.clone(),
        bdd: paths.clone(),
        skeleton: paths.clone(),
        tests: paths,
    }
}

fn snapshot_result(fs: &dyn FileSystemPort, manifest: &GuardInputManifest) -> Result<GuardCurrentByteSnapshot, GuardSnapshotProducerError> {
    guard_current_byte_snapshot(fs, "D:/fixture", manifest)
}

#[test]
fn guard_fingerprint_exact_bytes_include_invalid_utf8_and_comments() {
    let fs = SnapshotFs::default();
    let raw = [0xff, 0x00, b'/', b'/', b' ', b'n', b'o', b't', b'e'];
    fs.seed("D:/fixture/src/a.rs", &raw);
    let result = snapshot_result(&fs, &input_manifest(&["src/a.rs"])).unwrap();
    assert_eq!(result.entries[0].sha256, "60323a59e89e6848f6132f90e19922a2e79857643f6524907b4006840ba023d2");
    let before = result.manifest_fingerprint;
    fs.seed("D:/fixture/src/a.rs", &[0xff, 0x00, b'/', b'/', b' ', b'n', b'o', b't', b'e', b'!']);
    let after = snapshot_result(&fs, &input_manifest(&["src/a.rs"])).unwrap();
    assert_ne!(before, after.manifest_fingerprint);
}

#[test]
fn guard_fingerprint_is_deterministic_and_utf8_path_order_independent() {
    let fs = SnapshotFs::default();
    fs.seed("D:/fixture/z.rs", b"z");
    fs.seed("D:/fixture/é.rs", b"unicode");
    fs.seed("D:/fixture/a.rs", b"a");
    let a = input_manifest(&["z.rs", "é.rs", "a.rs"]);
    let b = input_manifest(&["a.rs", "z.rs", "é.rs"]);
    let first = snapshot_result(&fs, &a).unwrap();
    for _ in 0..100 {
        let next = snapshot_result(&fs, &b).unwrap();
        assert_eq!(first.manifest_fingerprint, next.manifest_fingerprint);
        assert_eq!(first.entries, next.entries);
    }
    assert_eq!(first.entries.iter().map(|entry| entry.relative_path.as_str()).collect::<Vec<_>>(), vec!["a.rs", "z.rs", "é.rs"]);
}

#[test]
fn guard_fingerprint_rejects_empty_duplicate_and_malformed_paths_before_reads() {
    let invalid = ["", "/absolute", "C:/drive", "src//empty", "src/./dot", "src/../escape", "src\\backslash"];
    for path in invalid {
        let fs = SnapshotFs::default();
        assert_eq!(snapshot_result(&fs, &input_manifest(&[path])), Err(GuardSnapshotProducerError::InvalidManifest), "path={path:?}");
        assert_eq!(fs.reads.load(Ordering::SeqCst), 0, "read occurred for {path:?}");
    }
    let fs = SnapshotFs::default();
    assert_eq!(snapshot_result(&fs, &input_manifest(&[])), Err(GuardSnapshotProducerError::InvalidManifest));
    assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
    let fs = SnapshotFs::default();
    assert_eq!(snapshot_result(&fs, &input_manifest(&["src/a", "src/a"])), Err(GuardSnapshotProducerError::InvalidManifest));
    assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
}

#[test]
fn guard_fingerprint_missing_and_read_errors_return_no_snapshot() {
    let missing = SnapshotFs::default();
    assert_eq!(snapshot_result(&missing, &input_manifest(&["src/missing"])), Err(GuardSnapshotProducerError::ReadFailure { relative_path: "src/missing".into(), category: GuardReadFailureCategory::NotFound }));
    let denied = SnapshotFs::default();
    denied.fail_reads_with(PortError::PermissionDenied("private".into()));
    assert_eq!(snapshot_result(&denied, &input_manifest(&["src/denied"])), Err(GuardSnapshotProducerError::ReadFailure { relative_path: "src/denied".into(), category: GuardReadFailureCategory::PermissionDenied }));
}

#[test]
fn guard_fingerprint_rejects_invalid_category_membership() {
    let fs = SnapshotFs::default();
    fs.seed("D:/fixture/src/a.rs", b"a");
    let mut empty_required = input_manifest(&["src/a.rs"]);
    empty_required.architecture.clear();
    assert_eq!(snapshot_result(&fs, &empty_required), Err(GuardSnapshotProducerError::InvalidManifest));
    assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
    let mut undeclared = input_manifest(&["src/a.rs"]);
    undeclared.bdd = vec!["src/other.rs".into()];
    assert_eq!(snapshot_result(&fs, &undeclared), Err(GuardSnapshotProducerError::InvalidManifest));
    assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
}

#[test]
fn guard_fingerprint_category_digest_changes_when_member_bytes_change() {
    let fs = SnapshotFs::default();
    fs.seed("D:/fixture/src/a.rs", b"// before\n");
    let manifest = input_manifest(&["src/a.rs"]);
    let before = snapshot_result(&fs, &manifest).unwrap();
    fs.seed("D:/fixture/src/a.rs", b"// after\n");
    let after = snapshot_result(&fs, &manifest).unwrap();
    assert_ne!(before.artifact_digests, after.artifact_digests);
}

#[test]
fn guard_fingerprint_golden_canonical_digest() {
    let fs = SnapshotFs::default();
    fs.seed("D:/fixture/src/a.rs", b"// before\n");
    let before = snapshot_result(&fs, &input_manifest(&["src/a.rs"])).unwrap();
    assert_eq!(before.artifact_digests["architecture"], "3acb99393b77f8aabce216208fd7fc6f93cc3a6e479aca693b80923f36c9e70a");
    // Private aggregate schema includes the exact HOST-resolved logical root.
    assert_eq!(before.manifest_fingerprint, "f35af625ad3167428935830a144af4ce702e6cdeec794e8443c1094b8064a9a7");
}

#[test]
fn guard_fingerprint_categories_are_isolated_and_revision_is_bound() {
    let fs = SnapshotFs::default();
    for (path, bytes) in [("a.rs", b"a".as_slice()), ("b.feature", b"b"), ("c.json", b"c"), ("d.rs", b"d")] {
        fs.seed(&format!("D:/fixture/{path}"), bytes);
    }
    let mut manifest = GuardInputManifest {
        revision: "r1".into(),
        inputs: vec!["a.rs".into(), "b.feature".into(), "c.json".into(), "d.rs".into()],
        architecture: vec!["a.rs".into()],
        bdd: vec!["b.feature".into()],
        skeleton: vec!["c.json".into()],
        tests: vec!["d.rs".into()],
    };
    let before = snapshot_result(&fs, &manifest).unwrap();
    fs.seed("D:/fixture/b.feature", b"b changed");
    let changed_bdd = snapshot_result(&fs, &manifest).unwrap();
    assert_ne!(before.artifact_digests["bdd"], changed_bdd.artifact_digests["bdd"]);
    for name in ["architecture", "skeleton", "tests"] {
        assert_eq!(before.artifact_digests[name], changed_bdd.artifact_digests[name]);
    }
    manifest.revision = "r2".into();
    let changed_revision = snapshot_result(&fs, &manifest).unwrap();
    assert_ne!(changed_bdd.manifest_fingerprint, changed_revision.manifest_fingerprint);
}

#[test]
fn guard_fingerprint_binds_the_host_resolved_logical_root() {
    let fs = SnapshotFs::default();
    fs.seed("D:/fixture/src/a.rs", b"same bytes");
    fs.seed("E:/fixture/src/a.rs", b"same bytes");
    let manifest = input_manifest(&["src/a.rs"]);
    let first = snapshot_result(&fs, &manifest).unwrap();
    let second = guard_current_byte_snapshot(&fs, "E:/fixture", &manifest).unwrap();
    assert_ne!(first.manifest_fingerprint, second.manifest_fingerprint);
}

#[test]
fn guard_fingerprint_requires_all_four_categories_as_declared_nonempty_subsets() {
    let cases = [
        GuardInputManifest { architecture: vec![], ..input_manifest(&["a"]) },
        GuardInputManifest { bdd: vec![], ..input_manifest(&["a"]) },
        GuardInputManifest { skeleton: vec![], ..input_manifest(&["a"]) },
        GuardInputManifest { tests: vec![], ..input_manifest(&["a"]) },
        GuardInputManifest { architecture: vec!["outside".into()], ..input_manifest(&["a"]) },
        GuardInputManifest { bdd: vec!["outside".into()], ..input_manifest(&["a"]) },
        GuardInputManifest { skeleton: vec!["outside".into()], ..input_manifest(&["a"]) },
        GuardInputManifest { tests: vec!["outside".into()], ..input_manifest(&["a"]) },
    ];
    for manifest in cases {
        let fs = SnapshotFs::default();
        assert_eq!(snapshot_result(&fs, &manifest), Err(GuardSnapshotProducerError::InvalidManifest));
        assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
    }
}

#[test]
fn guard_fingerprint_rejects_nul_and_colon_paths_before_reads() {
    for path in ["src/with\0nul", "src/name:stream"] {
        let fs = SnapshotFs::default();
        assert_eq!(snapshot_result(&fs, &input_manifest(&[path])), Err(GuardSnapshotProducerError::InvalidManifest));
        assert_eq!(fs.reads.load(Ordering::SeqCst), 0);
    }
}

#[test]
fn guard_fingerprint_reads_each_path_once_and_maps_late_io_failure_portably() {
    let fs = SnapshotFs::default();
    fs.seed("D:/fixture/a.rs", b"a");
    fs.seed("D:/fixture/b.rs", b"b");
    let result = snapshot_result(&fs, &input_manifest(&["a.rs", "b.rs"])).unwrap();
    assert_eq!(result.entries.len(), 2);
    assert_eq!(fs.reads.load(Ordering::SeqCst), 2);

    let failing = SnapshotFs::default();
    failing.seed("D:/fixture/a.rs", b"a");
    failing.seed("D:/fixture/b.rs", b"b");
    failing.fail_path_with("D:/fixture/b.rs", PortError::Io("machine-specific detail".into()));
    assert_eq!(
        snapshot_result(&failing, &input_manifest(&["a.rs", "b.rs"])),
        Err(GuardSnapshotProducerError::ReadFailure {
            relative_path: "b.rs".into(),
            category: GuardReadFailureCategory::Io,
        })
    );
    assert_eq!(failing.reads.load(Ordering::SeqCst), 2);
}

}

#[cfg(test)]
mod guard_host_fs_tests {
    use super::super::{
        DispatchHost, GuardCurrentByteSnapshot, GuardInputManifest, GuardProjectSnapshotError,
        GuardReadFailureCategory, GuardSnapshotProducerError,
    };
    use sgenaxis_ports::{FileSystemPort, PortError};
    use sgenaxis_work::{ProjectId, RegisterOutcome};
    use std::collections::BTreeMap;
    use std::sync::Mutex;

    #[derive(Default)]
    struct ControlledFakeFs {
        files: Mutex<BTreeMap<String, Vec<u8>>>,
        failed: Mutex<BTreeMap<String, PortError>>,
        reads: Mutex<Vec<String>>,
    }

    impl ControlledFakeFs {
        fn seed(&self, path: &str, bytes: &[u8]) {
            self.files.lock().unwrap().insert(path.into(), bytes.into());
        }

        fn fail(&self, path: &str, error: PortError) {
            self.failed.lock().unwrap().insert(path.into(), error);
        }

        fn read_paths(&self) -> Vec<String> {
            self.reads.lock().unwrap().clone()
        }
    }

    impl FileSystemPort for ControlledFakeFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> {
            Ok(self.files.lock().unwrap().contains_key(path))
        }

        fn read_to_string(&self, path: &str) -> Result<String, PortError> {
            String::from_utf8(self.read(path)?).map_err(|error| PortError::Other(error.to_string()))
        }

        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
            self.reads.lock().unwrap().push(path.into());
            if let Some(error) = self.failed.lock().unwrap().get(path).cloned() {
                return Err(error);
            }
            self.files
                .lock()
                .unwrap()
                .get(path)
                .cloned()
                .ok_or_else(|| PortError::NotFound(path.into()))
        }

        fn write_atomic(&self, _path: &str, _contents: &[u8]) -> Result<(), PortError> {
            Err(PortError::Other("write disabled in guard test".into()))
        }

        fn create_dir_all(&self, _path: &str) -> Result<(), PortError> {
            Err(PortError::Other("filesystem mutation disabled in guard test".into()))
        }

        fn is_file(&self, path: &str) -> Result<bool, PortError> {
            self.exists(path)
        }

        fn remove_file(&self, _path: &str) -> Result<(), PortError> {
            Err(PortError::Other("filesystem mutation disabled in guard test".into()))
        }
    }

    fn host_with_fake_fs() -> (DispatchHost, std::sync::Arc<ControlledFakeFs>) {
        let mut host = DispatchHost::new();
        let fs = std::sync::Arc::new(ControlledFakeFs::default());
        host.guard_input_fs = Box::new(SharedFakeFs(fs.clone()));
        (host, fs)
    }

    struct SharedFakeFs(std::sync::Arc<ControlledFakeFs>);

    impl FileSystemPort for SharedFakeFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> { self.0.exists(path) }
        fn read_to_string(&self, path: &str) -> Result<String, PortError> { self.0.read_to_string(path) }
        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> { self.0.read(path) }
        fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError> { self.0.write_atomic(path, contents) }
        fn create_dir_all(&self, path: &str) -> Result<(), PortError> { self.0.create_dir_all(path) }
        fn is_file(&self, path: &str) -> Result<bool, PortError> { self.0.is_file(path) }
        fn remove_file(&self, path: &str) -> Result<(), PortError> { self.0.remove_file(path) }
    }

    fn register(host: &mut DispatchHost, root: &str) -> ProjectId {
        match host.work.register(root).unwrap() {
            RegisterOutcome::Created(project) | RegisterOutcome::Existing(project) => project.id,
        }
    }

    fn manifest(paths: &[&str]) -> GuardInputManifest {
        let inputs = paths.iter().map(|path| (*path).to_string()).collect::<Vec<_>>();
        GuardInputManifest {
            revision: "guard-host-fs-v1".into(),
            architecture: vec![inputs[0].clone()],
            bdd: vec![inputs[0].clone()],
            skeleton: vec![inputs[0].clone()],
            tests: vec![inputs[0].clone()],
            inputs,
        }
    }

    fn snapshot(host: &DispatchHost, id: &ProjectId, manifest: &GuardInputManifest) -> Result<GuardCurrentByteSnapshot, GuardProjectSnapshotError> {
        host.guard_project_input_snapshot(id, manifest)
    }

    #[test]
    fn guard_host_fs_reads_same_filename_from_each_registered_root() {
        let (mut host, fs) = host_with_fake_fs();
        let first = register(&mut host, "D:/guard/first");
        let second = register(&mut host, "D:/guard/second");
        fs.seed("D:/guard/first/input.feature", b"first");
        fs.seed("D:/guard/second/input.feature", b"second");

        let first_result = snapshot(&host, &first, &manifest(&["input.feature"])).unwrap();
        let second_result = snapshot(&host, &second, &manifest(&["input.feature"])).unwrap();
        assert_ne!(first_result.entries[0].sha256, second_result.entries[0].sha256);
        assert_eq!(fs.read_paths(), ["D:/guard/first/input.feature", "D:/guard/second/input.feature"]);
    }

    #[test]
    fn guard_host_fs_unknown_project_fails_without_reads() {
        let (host, fs) = host_with_fake_fs();
        let unknown = ProjectId::new("not-registered");
        assert_eq!(
            snapshot(&host, &unknown, &manifest(&["input.feature"])),
            Err(GuardProjectSnapshotError::ProjectNotFound)
        );
        assert!(fs.read_paths().is_empty());
    }

    #[test]
    fn guard_host_fs_rebind_and_byte_change_recompute_snapshot() {
        let (mut host, fs) = host_with_fake_fs();
        let id = register(&mut host, "D:/guard/before");
        fs.seed("D:/guard/before/input.feature", b"v1");
        fs.seed("D:/guard/after/input.feature", b"v2");
        let declaration = manifest(&["input.feature"]);
        let before = snapshot(&host, &id, &declaration).unwrap();

        fs.seed("D:/guard/before/input.feature", b"changed");
        let changed_bytes = snapshot(&host, &id, &declaration).unwrap();
        assert_ne!(before.manifest_fingerprint, changed_bytes.manifest_fingerprint);
        host.work.rebind_root(&id, "D:/guard/after").unwrap();
        let rebound = snapshot(&host, &id, &declaration).unwrap();
        assert_ne!(changed_bytes.manifest_fingerprint, rebound.manifest_fingerprint);
        assert_eq!(fs.read_paths(), [
            "D:/guard/before/input.feature",
            "D:/guard/before/input.feature",
            "D:/guard/after/input.feature",
        ]);
    }

    #[test]
    fn guard_host_fs_read_failure_returns_no_snapshot_or_authority_mutation() {
        let (mut host, fs) = host_with_fake_fs();
        let id = register(&mut host, "D:/guard/read-error");
        fs.seed("D:/guard/read-error/a.feature", b"available");
        fs.fail("D:/guard/read-error/b.feature", PortError::PermissionDenied("private".into()));
        let declaration = manifest(&["a.feature", "b.feature"]);
        let authority_before = host.guard_authority.clone();

        assert_eq!(
            snapshot(&host, &id, &declaration),
            Err(GuardProjectSnapshotError::Snapshot(GuardSnapshotProducerError::ReadFailure {
                relative_path: "b.feature".into(),
                category: GuardReadFailureCategory::PermissionDenied,
            }))
        );
        assert_eq!(host.guard_authority.boot, authority_before.boot);
        assert_eq!(host.guard_authority.pending.as_ref().map(|p| p.nonce), authority_before.pending.as_ref().map(|p| p.nonce));
        assert_eq!(host.guard_authority.approval.as_ref().map(|a| &a.binding), authority_before.approval.as_ref().map(|a| &a.binding));
    }

    #[test]
    fn guard_host_fs_explicit_project_id_ignores_selected_project() {
        let (mut host, fs) = host_with_fake_fs();
        let requested = register(&mut host, "D:/guard/requested");
        let _selected = register(&mut host, "D:/guard/selected");
        fs.seed("D:/guard/requested/input.feature", b"requested");
        fs.seed("D:/guard/selected/input.feature", b"selected");

        snapshot(&host, &requested, &manifest(&["input.feature"])).unwrap();
        assert_eq!(fs.read_paths(), ["D:/guard/requested/input.feature"]);
    }
}

#[cfg(test)]
mod guard_host_fs_boundary_tests {
    use super::super::{
        DispatchHost, GuardApproval, GuardApprovalStatus, GuardInputManifest,
        GuardProjectSnapshotError, GuardSessionState, GuardSnapshotProducerError,
        GuardPending,
    };
    use sgenaxis_ports::{FileSystemPort, PortError};
    use sgenaxis_work::{ProjectId, RegisterOutcome};
    use std::collections::BTreeMap;
    use std::sync::{Arc, Mutex};

    #[derive(Default)]
    struct FakeFs {
        files: Mutex<BTreeMap<String, Vec<u8>>>,
        failed: Mutex<BTreeMap<String, PortError>>,
        reads: Mutex<Vec<String>>,
    }

    impl FakeFs {
        fn seed(&self, path: &str, bytes: &[u8]) { self.files.lock().unwrap().insert(path.into(), bytes.into()); }
        fn fail(&self, path: &str) { self.failed.lock().unwrap().insert(path.into(), PortError::PermissionDenied(path.into())); }
        fn reads(&self) -> Vec<String> { self.reads.lock().unwrap().clone() }
    }

    impl FileSystemPort for FakeFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> { Ok(self.files.lock().unwrap().contains_key(path)) }
        fn read_to_string(&self, path: &str) -> Result<String, PortError> {
            String::from_utf8(self.read(path)?).map_err(|error| PortError::Other(error.to_string()))
        }
        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
            self.reads.lock().unwrap().push(path.into());
            if let Some(error) = self.failed.lock().unwrap().get(path).cloned() { return Err(error); }
            self.files.lock().unwrap().get(path).cloned().ok_or_else(|| PortError::NotFound(path.into()))
        }
        fn write_atomic(&self, _path: &str, _contents: &[u8]) -> Result<(), PortError> { Err(PortError::Other("disabled".into())) }
        fn create_dir_all(&self, _path: &str) -> Result<(), PortError> { Err(PortError::Other("disabled".into())) }
        fn is_file(&self, path: &str) -> Result<bool, PortError> { self.exists(path) }
        fn remove_file(&self, _path: &str) -> Result<(), PortError> { Err(PortError::Other("disabled".into())) }
    }

    struct SharedFs(Arc<FakeFs>);
    impl FileSystemPort for SharedFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> { self.0.exists(path) }
        fn read_to_string(&self, path: &str) -> Result<String, PortError> { self.0.read_to_string(path) }
        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> { self.0.read(path) }
        fn write_atomic(&self, path: &str, bytes: &[u8]) -> Result<(), PortError> { self.0.write_atomic(path, bytes) }
        fn create_dir_all(&self, path: &str) -> Result<(), PortError> { self.0.create_dir_all(path) }
        fn is_file(&self, path: &str) -> Result<bool, PortError> { self.0.is_file(path) }
        fn remove_file(&self, path: &str) -> Result<(), PortError> { self.0.remove_file(path) }
    }

    fn setup(root: &str) -> (DispatchHost, Arc<FakeFs>, ProjectId) {
        let mut host = DispatchHost::new();
        let fs = Arc::new(FakeFs::default());
        host.guard_input_fs = Box::new(SharedFs(fs.clone()));
        let id = match host.work.register(root).unwrap() {
            RegisterOutcome::Created(project) | RegisterOutcome::Existing(project) => project.id,
        };
        (host, fs, id)
    }

    fn one_input(path: &str) -> GuardInputManifest {
        GuardInputManifest {
            revision: "guard-host-fs-boundary-v1".into(),
            inputs: vec![path.into()],
            architecture: vec![path.into()],
            bdd: vec![path.into()],
            skeleton: vec![path.into()],
            tests: vec![path.into()],
        }
    }

    fn assert_nonempty_authority_unchanged(host: &DispatchHost, expected: &GuardSessionState) {
        assert_eq!(host.guard_authority.boot, expected.boot);
        let actual = host.guard_authority.approval.as_ref().unwrap();
        let prior = expected.approval.as_ref().unwrap();
        assert_eq!((actual.session, actual.id, &actual.status, &actual.binding), (prior.session, prior.id, &prior.status, &prior.binding));
        let actual = host.guard_authority.pending.as_ref().unwrap();
        let prior = expected.pending.as_ref().unwrap();
        assert_eq!((actual.nonce, &actual.binding, actual.revoked), (prior.nonce, &prior.binding, prior.revoked));
    }

    fn seed_nonempty_authority(host: &mut DispatchHost) -> GuardSessionState {
        let binding = super::snapshot();
        let prior = GuardSessionState {
            boot: 41,
            approval: Some(GuardApproval { session: 41, id: 43, binding: binding.clone(), status: GuardApprovalStatus::Approved }),
            pending: Some(GuardPending { nonce: 47, binding, revoked: false }),
        };
        host.guard_authority = prior.clone();
        prior
    }

    #[test]
    fn guard_host_fs_success_and_failure_preserve_existing_authority_records() {
        let (mut success_host, success_fs, success_id) = setup("D:/guard/state-success");
        success_fs.seed("D:/guard/state-success/input.feature", b"current");
        let success_prior = seed_nonempty_authority(&mut success_host);
        assert!(success_host.guard_project_input_snapshot(&success_id, &one_input("input.feature")).is_ok());
        assert_nonempty_authority_unchanged(&success_host, &success_prior);

        let (mut failed_host, failed_fs, failed_id) = setup("D:/guard/state-failure");
        failed_fs.fail("D:/guard/state-failure/input.feature");
        let failed_prior = seed_nonempty_authority(&mut failed_host);
        assert!(matches!(
            failed_host.guard_project_input_snapshot(&failed_id, &one_input("input.feature")),
            Err(GuardProjectSnapshotError::Snapshot(GuardSnapshotProducerError::ReadFailure { .. }))
        ));
        assert_nonempty_authority_unchanged(&failed_host, &failed_prior);
    }

    #[test]
    fn guard_host_fs_invalid_manifest_rejects_before_reads() {
        let (host, fs, project_id) = setup("D:/guard/invalid-manifest");
        assert_eq!(
            host.guard_project_input_snapshot(&project_id, &one_input("../escape.feature")),
            Err(GuardProjectSnapshotError::Snapshot(GuardSnapshotProducerError::InvalidManifest))
        );
        assert!(fs.reads().is_empty());
    }
}

#[cfg(test)]
mod guard_candidate_producer_tests {
    use super::super::{
        DispatchHost, GuardAuthorityError, GuardCandidateError, GuardCaptureError,
        GuardNativeObservation,
    };
    use crate::dto::{CandidateDraft, EnvelopeDraft, RedJobDraft};
    use sgenaxis_core::Zone;
    use sgenaxis_ports::{FileSystemPort, PortError, ProcessId, ProcessOutput, ProcessPort, StreamCompletion};
    use sgenaxis_work::{ProjectId, RegisterOutcome};
    use std::collections::{BTreeMap, BTreeSet, VecDeque};
    use std::sync::{Arc, Mutex};
    use std::time::Instant;

    #[derive(Clone, Debug, PartialEq, Eq)]
    struct ProcessCall {
        program: String,
        args: Vec<String>,
        cwd: Option<String>,
    }

    struct ProcessScript {
        exit: Option<i32>,
        output: Option<ProcessOutput>,
        completion_after_read: (StreamCompletion, StreamCompletion),
        completion_sequence: VecDeque<(StreamCompletion, StreamCompletion)>,
        wait_error: bool,
        read_error: bool,
        cancel_finishes: bool,
        cancels: usize,
        mutation_on_start: Option<(Arc<Fs>, String, Vec<u8>)>,
    }

    impl ProcessScript {
        fn completed(exit: i32, output: ProcessOutput) -> Self {
            let completion_after_read = (output.stdout_completion.clone(), output.stderr_completion.clone());
            Self { exit: Some(exit), output: Some(output), completion_after_read, completion_sequence: VecDeque::new(), wait_error: false, read_error: false, cancel_finishes: true, cancels: 0, mutation_on_start: None }
        }

        fn running(output: ProcessOutput, cancel_finishes: bool) -> Self {
            let completion_after_read = (output.stdout_completion.clone(), output.stderr_completion.clone());
            Self { exit: None, output: Some(output), completion_after_read, completion_sequence: VecDeque::new(), wait_error: false, read_error: false, cancel_finishes, cancels: 0, mutation_on_start: None }
        }

        fn mutate_on_start(mut self, fs: Arc<Fs>, path: &str, bytes: &[u8]) -> Self {
            self.mutation_on_start = Some((fs, path.into(), bytes.into()));
            self
        }
    }

    #[derive(Default)]
    struct ProcessState {
        calls: Vec<ProcessCall>,
        scripts: VecDeque<ProcessScript>,
        active: BTreeMap<u64, ProcessScript>,
        next_id: u64,
    }

    #[derive(Clone, Default)]
    struct RecordingProcess(Arc<Mutex<ProcessState>>);

    impl RecordingProcess {
        fn scripted(scripts: impl IntoIterator<Item = ProcessScript>) -> Self {
            Self(Arc::new(Mutex::new(ProcessState { scripts: scripts.into_iter().collect(), next_id: 40, ..ProcessState::default() })))
        }

        fn calls(&self) -> Vec<ProcessCall> { self.0.lock().unwrap().calls.clone() }
        fn cancel_count(&self, id: ProcessId) -> usize { self.0.lock().unwrap().active.get(&id.0).map(|script| script.cancels).unwrap_or(0) }
    }

    impl ProcessPort for RecordingProcess {
        fn start(&mut self, program: &str, args: &[&str], cwd: Option<&str>) -> Result<ProcessId, PortError> {
            let mut state = self.0.lock().unwrap();
            state.calls.push(ProcessCall { program: program.into(), args: args.iter().map(|arg| (*arg).into()).collect(), cwd: cwd.map(str::to_owned) });
            let script = state.scripts.pop_front().ok_or_else(|| PortError::Process("no scripted process".into()))?;
            let mutation = script.mutation_on_start.clone();
            state.next_id += 1;
            let id = state.next_id;
            state.active.insert(id, script);
            drop(state);
            if let Some((fs, path, bytes)) = mutation { fs.seed(&path, &bytes); }
            Ok(ProcessId(id))
        }

        fn try_wait(&mut self, id: ProcessId) -> Result<Option<i32>, PortError> {
            let state = self.0.lock().unwrap();
            let script = state.active.get(&id.0).ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
            if script.wait_error { Err(PortError::Process("scripted wait failure".into())) } else { Ok(script.exit) }
        }

        fn cancel(&mut self, id: ProcessId) -> Result<(), PortError> {
            let mut state = self.0.lock().unwrap();
            let script = state.active.get_mut(&id.0).ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
            script.cancels += 1;
            if script.cancel_finishes { script.exit = Some(-1); }
            Ok(())
        }

        fn try_read(&mut self, id: ProcessId) -> Result<ProcessOutput, PortError> {
            let mut state = self.0.lock().unwrap();
            let script = state.active.get_mut(&id.0).ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
            if script.read_error { return Err(PortError::Process("scripted read failure".into())); }
            if let Some(output) = script.output.take() { return Ok(output); }
            let (stdout_completion, stderr_completion) = script.completion_sequence.pop_front()
                .unwrap_or_else(|| script.completion_after_read.clone());
            Ok(ProcessOutput { stdout_completion, stderr_completion, ..ProcessOutput::default() })
        }
    }

    fn completed_output(stdout: &str, stderr: &str) -> ProcessOutput {
        ProcessOutput { stdout: stdout.into(), stderr: stderr.into(), stdout_completion: StreamCompletion::Eof, stderr_completion: StreamCompletion::Eof }
    }

    fn capture_candidate(project_id: &str) -> CandidateDraft {
        let mut draft = candidate(project_id);
        draft.red_job.build_argv = vec!["test".into(), "--no-run".into(), "--message-format=json".into(), "--lib".into()];
        draft.red_job.test_target = "sgenaxis_desktop_lib".into();
        draft
    }

    fn cargo_artifact_message(path: &str, target: &str) -> String {
        serde_json::json!({
            "reason": "compiler-artifact",
            "package_id": "path+file:///D:/candidate#candidate@0.1.0",
            "target": {"kind": ["lib"], "name": target, "src_path": "D:/candidate/src/lib.rs", "edition": "2021", "test": true},
            "profile": {"test": true},
            "filenames": [path],
            "executable": path,
            "fresh": false
        }).to_string()
    }

    fn confirmed_capture_host() -> (DispatchHost, Arc<Fs>, ProjectId, u64) {
        let (mut host, fs, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &capture_candidate(project.as_str())).expect("candidate prepared");
        host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes).expect("candidate classified");
        (host, fs, project, reference)
    }

    fn captured_red_host() -> (DispatchHost, Arc<Fs>, ProjectId, u64, super::super::GuardMechanicalCapture) {
        let (mut host, fs, project) = setup();
        fs.seed("D:/candidate/bdd.feature", b"Feature: approved behavior\nScenario: red is expected\n");
        let reference = host.guard_prepare_candidate("TASK-A", &capture_candidate(project.as_str())).expect("candidate prepared");
        host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes).expect("candidate classified");
        let (path, _) = seed_capture_artifact(&fs);
        host.guard_red_process = Box::new(RecordingProcess::scripted(successful_capture_processes(path)));
        let capture = host.guard_capture_red(reference, GuardNativeObservation::Yes).expect("mechanical RED captured");
        (host, fs, project, reference, capture)
    }

    fn seed_pending_qualification(
        host: &mut DispatchHost,
        reference: u64,
        capture: &super::super::GuardMechanicalCapture,
    ) {
        let record = host.guard_candidates.get_mut(&reference).unwrap();
        let bdd_id = record.draft.as_ref().unwrap().red_job.bdd_id.clone();
        record.pending_qualification = Some(super::super::GuardPendingQualification {
            producer_id: capture.producer_id,
            binding: record.binding.clone(),
            artifact_sha256: capture.artifact_sha256.clone(),
            test_id: capture.test_id.clone(),
            bdd_id,
        });
    }

    #[derive(Default)]
    struct Fs {
        files: Mutex<BTreeMap<String, Vec<u8>>>,
        reads: Mutex<Vec<String>>,
        failed: Mutex<BTreeSet<String>>,
    }
    impl Fs {
        fn seed(&self, path: &str, value: &[u8]) { self.files.lock().unwrap().insert(path.into(), value.into()); }
        fn fail(&self, path: &str) { self.failed.lock().unwrap().insert(path.into()); }
        fn reads(&self) -> Vec<String> { self.reads.lock().unwrap().clone() }
    }
    struct Shared(Arc<Fs>);
    impl FileSystemPort for Shared {
        fn exists(&self, p: &str) -> Result<bool, PortError> { Ok(self.0.files.lock().unwrap().contains_key(p)) }
        fn read_to_string(&self, p: &str) -> Result<String, PortError> { String::from_utf8(self.read(p)?).map_err(|e| PortError::Other(e.to_string())) }
        fn read(&self, p: &str) -> Result<Vec<u8>, PortError> {
            self.0.reads.lock().unwrap().push(p.into());
            if self.0.failed.lock().unwrap().contains(p) { return Err(PortError::PermissionDenied(p.into())); }
            self.0.files.lock().unwrap().get(p).cloned().ok_or_else(|| PortError::NotFound(p.into()))
        }
        fn write_atomic(&self, _: &str, _: &[u8]) -> Result<(), PortError> { Err(PortError::Other("read only".into())) }
        fn create_dir_all(&self, _: &str) -> Result<(), PortError> { Err(PortError::Other("read only".into())) }
        fn is_file(&self, p: &str) -> Result<bool, PortError> { self.exists(p) }
        fn remove_file(&self, _: &str) -> Result<(), PortError> { Err(PortError::Other("read only".into())) }
    }

    fn candidate(project_id: &str) -> CandidateDraft {
        CandidateDraft {
            module_id: "MOD-A".into(),
            project_id: project_id.into(),
            manifest_revision: "rev-7".into(),
            input_paths: vec!["arch.json".into(), "bdd.feature".into(), "skeleton.rs".into(), "test.rs".into()],
            architecture_paths: vec!["arch.json".into()],
            bdd_paths: vec!["bdd.feature".into()],
            skeleton_paths: vec!["skeleton.rs".into()],
            test_paths: vec!["test.rs".into()],
            envelope: EnvelopeDraft { primary_module: "MOD-A".into(), integration_modules: vec![], allowed_patterns: vec!["src/**".into()], protected_patterns: vec![], module_prefixes: BTreeMap::new() },
            red_job: RedJobDraft { program: "D:/tools/cargo.exe".into(), build_argv: vec!["test".into(), "--no-run".into()], cwd_ref: "D:/candidate".into(), test_target: "lib".into(), test_id: "mod_a::red_case".into(), bdd_id: "BDD-01".into(), timeout_ms: 120_000 },
        }
    }

    fn setup() -> (DispatchHost, Arc<Fs>, ProjectId) {
        let mut host = DispatchHost::new();
        let fs = Arc::new(Fs::default());
        host.guard_input_fs = Box::new(Shared(fs.clone()));
        let project = match host.work.register("D:/candidate").unwrap() {
            RegisterOutcome::Created(p) | RegisterOutcome::Existing(p) => p.id,
        };
        host.engine.upsert_task("TASK-A", "Candidate task", Zone::Gray);
        for (path, bytes) in [("arch.json", b"arch".as_slice()), ("bdd.feature", b"bdd"), ("skeleton.rs", b"skel"), ("test.rs", b"test")] {
            fs.seed(&format!("D:/candidate/{path}"), bytes);
        }
        (host, fs, project)
    }

    #[test]
    fn gc_candidate_prepare_reads_exact_host_project_bytes_and_binds_owner_candidate() {
        let (mut host, fs, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared");
        assert!(reference > 0);
        assert_eq!(fs.reads().len(), 4);
        assert_eq!(host.guard_authority.pending.as_ref().map(|p| p.nonce), Some(reference));
        assert_eq!(host.guard_candidates.get(&reference).unwrap().task_id, "TASK-A");
        assert_eq!(host.guard_candidates.get(&reference).unwrap().binding.project, project.as_str());
        assert!(host.guard_authority.approval.is_none());
    }

    #[test]
    fn gc_candidate_unknown_task_fails_before_source_reads() {
        let (mut host, fs, project) = setup();
        assert_eq!(host.guard_prepare_candidate("unknown-task", &candidate(project.as_str())), Err(GuardCandidateError::UnknownTask));
        assert!(fs.reads().is_empty());
        assert!(host.guard_authority.pending.is_none());
    }

    #[test]
    fn gc_candidate_references_are_session_scoped_across_dispatch_hosts() {
        let (mut first, _, first_project) = setup();
        let (mut second, _, second_project) = setup();
        let a = first.guard_prepare_candidate("TASK-A", &candidate(first_project.as_str())).unwrap();
        let b = second.guard_prepare_candidate("TASK-A", &candidate(second_project.as_str())).unwrap();
        assert_ne!(first.guard_authority.boot, second.guard_authority.boot);
        assert_ne!(a, b, "candidate references are session-seeded opaque u64 values");
        assert!(second.guard_candidates.get(&a).is_none(), "foreign-session reference is unknown");
        assert_eq!(second.guard_complete_candidate_confirmation(a, GuardNativeObservation::Yes), Err(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord)));
    }

    #[test]
    fn gc_candidate_reference_is_json_number_safe_and_roundtrips_exactly() {
        const MAX_SAFE_JSON_INTEGER: u64 = (1u64 << 53) - 1;
        let (mut host, _, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).unwrap();
        assert!(reference <= MAX_SAFE_JSON_INTEGER, "u64 refs crossing Tauri JSON must remain exactly representable by JS Number");
        let encoded = serde_json::to_string(&reference).unwrap();
        let decoded: u64 = serde_json::from_str(&encoded).unwrap();
        assert_eq!(decoded, reference);
        let js_number = serde_json::from_str::<f64>(&encoded).unwrap();
        assert_eq!(js_number as u64, reference);
    }

    #[test]
    fn gc_candidate_reference_exhaustion_rejects_without_mutation() {
        const MAX_SAFE_JSON_INTEGER: u64 = (1u64 << 53) - 1;
        let (mut host, fs, project) = setup();
        host.guard_next_candidate = MAX_SAFE_JSON_INTEGER;
        assert!(host.guard_authority.pending.is_none());
        assert_eq!(host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())), Err(GuardCandidateError::InvalidCandidate));
        assert_eq!(host.guard_next_candidate, MAX_SAFE_JSON_INTEGER);
        assert!(host.guard_authority.pending.is_none());
        assert!(fs.reads().is_empty(), "exhaustion is rejected before reading bound inputs");
    }

    #[test]
    fn gc_candidate_unknown_project_fails_before_any_source_read() {
        let (mut host, fs, _) = setup();
        let mut draft = candidate("missing-project");
        draft.project_id = "missing-project".into();
        assert_eq!(host.guard_prepare_candidate("TASK-A", &draft), Err(GuardCandidateError::ProjectNotFound));
        assert!(fs.reads().is_empty());
        assert!(host.guard_authority.pending.is_none());
    }

    #[test]
    fn gc_candidate_invalid_draft_fails_before_read_or_pending_mutation() {
        let (mut host, fs, project) = setup();
        let mut draft = candidate(project.as_str());
        draft.input_paths[0] = "../outside".into();
        assert_eq!(host.guard_prepare_candidate("TASK-A", &draft), Err(GuardCandidateError::Snapshot(super::super::GuardSnapshotProducerError::InvalidManifest)));
        assert!(fs.reads().is_empty());
        assert!(host.guard_authority.pending.is_none());
    }

    #[test]
    fn guard_confirmation_native_no_and_cancel_never_create_approval() {
        for observation in [GuardNativeObservation::No, GuardNativeObservation::Cancel] {
            let (mut host, _, project) = setup();
            let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared");
            assert_eq!(host.guard_complete_candidate_confirmation(reference, observation), Err(GuardCandidateError::Authority(GuardAuthorityError::NativeDeclined)));
            assert!(host.guard_authority.approval.is_none());
            assert!(host.guard_authority.pending.is_none());
        }
    }

    #[test]
    fn guard_confirmation_denial_clears_pending_even_if_source_read_would_fail() {
        let (mut host, fs, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared");
        fs.fail("D:/candidate/bdd.feature");
        assert_eq!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::No), Err(GuardCandidateError::Authority(GuardAuthorityError::NativeDeclined)));
        assert!(host.guard_authority.pending.is_none());
        assert!(host.guard_authority.approval.is_none());
        assert!(host.guard_candidates.get(&reference).is_none());
    }

    #[test]
    fn guard_confirmation_yes_read_failure_invalidates_nonce_and_fails_closed() {
        let (mut host, fs, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared");
        fs.fail("D:/candidate/bdd.feature");
        assert!(matches!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes), Err(GuardCandidateError::Snapshot(super::super::GuardSnapshotProducerError::ReadFailure { .. }))));
        assert!(host.guard_authority.pending.is_none());
        assert!(host.guard_authority.approval.is_none());
        assert!(host.guard_candidates.get(&reference).is_none());
        assert_eq!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes), Err(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord)));
    }

    #[test]
    fn guard_confirmation_yes_rechecks_exact_bytes_and_replay_cannot_create_approval() {
        let (mut host, fs, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared");
        fs.seed("D:/candidate/bdd.feature", b"changed after prompt");
        assert_eq!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes), Err(GuardCandidateError::Authority(GuardAuthorityError::Stale("input_fp"))));
        assert!(host.guard_authority.approval.is_none());
        assert_eq!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes), Err(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord)));

        let (mut host, _, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared");
        host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes).expect("committed");
        assert!(host.guard_authority.approval.is_none(), "classification is not final execution approval");
        assert!(host.guard_candidates.get(&reference).unwrap().confirmed);
        assert_eq!(host.guard_intents.get("TASK-A"), Some(&super::super::GuardHostIntent::Implementation));
        assert_eq!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes), Err(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord)));
    }

    fn seed_capture_artifact(fs: &Fs) -> (&'static str, Vec<u8>) {
        let path = "D:/candidate/target/debug/deps/sgenaxis_desktop_lib-abc.exe";
        let bytes = b"fake test executable bytes".to_vec();
        fs.seed(path, &bytes);
        (path, bytes)
    }

    fn successful_capture_processes(path: &str) -> Vec<ProcessScript> {
        let build = completed_output(&format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")), "");
        let test = completed_output(
            "running 1 test\ntest mod_a::red_case ... FAILED\npanicked at src\\test.rs:7:3: expected failure\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 42 filtered out\n",
            "",
        );
        vec![ProcessScript::completed(0, build), ProcessScript::completed(101, test)]
    }

    fn deterministic_drain_clock() -> impl FnMut() -> Instant {
        let base = Instant::now();
        let mut tick = 0u32;
        move || {
            let now = base + std::time::Duration::from_millis(u64::from(tick) * 250);
            tick += 1;
            now
        }
    }

    #[test]
    fn guard_capture_red_records_exact_build_artifact_test_case_and_dual_eof() {
        let (mut host, fs, project, reference) = confirmed_capture_host();
        let (path, bytes) = seed_capture_artifact(&fs);
        let process = RecordingProcess::scripted(successful_capture_processes(path));
        host.guard_red_process = Box::new(process.clone());

        let captured = host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock())
            .expect("bounded fake process evidence should be captured");

        assert_eq!(captured.test_id, "mod_a::red_case");
        assert_eq!(captured.target, "sgenaxis_desktop_lib");
        assert_eq!(captured.test_exit_code, 101);
        assert!(captured.dual_eof);
        assert_eq!(captured.observed_case_line.as_deref(), Some("test mod_a::red_case ... FAILED"));
        assert_eq!(captured.failure_summary_line.as_deref(), Some("test result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 42 filtered out"));
        assert_eq!(captured.input_fingerprint, host.guard_candidates.get(&reference).unwrap().binding.input_fp);
        assert!(captured.raw_test_stdout.contains("panicked at src\\test.rs:7:3"));
        assert_eq!(captured.build_stdout_sha256.len(), 64);
        assert_eq!(captured.build_stderr_sha256.len(), 64);
        assert_eq!(captured.artifact_path, path);
        assert_eq!(captured.selected_artifact_record, cargo_artifact_message(path, "sgenaxis_desktop_lib"));
        let expected_hash = sgenaxis_spec::packet::source_sha256(&bytes);
        assert_eq!(captured.artifact_sha256, expected_hash);
        assert_eq!(process.calls().len(), 2);
        assert_eq!(process.calls()[0].program, "D:/tools/cargo.exe");
        assert_eq!(process.calls()[0].cwd.as_deref(), Some("D:/candidate"));
        assert_eq!(process.calls()[1].program, path);
        assert!(process.calls()[1].args.windows(2).any(|args| args == ["--exact", "mod_a::red_case"]));
        assert_eq!(host.guard_candidates.get(&reference).unwrap().binding.project, project.as_str());
        assert!(host.guard_authority.approval.is_none(), "mechanical capture is not final RED qualification");
    }

    #[test]
    fn guard_red_qualification_prompt_contains_exact_capture_and_declared_bdd() {
        let (mut host, _fs, _, reference, capture) = captured_red_host();
        let prompt = host.guard_prepare_red_qualification(reference).expect("qualification prompt");
        assert_eq!(prompt.candidate_ref, reference);
        assert_eq!(prompt.producer_id, capture.producer_id);
        assert_eq!(prompt.test_id, capture.test_id);
        assert_eq!(prompt.bdd_id, "BDD-01");
        assert_eq!(prompt.artifact_sha256, capture.artifact_sha256);
        assert_eq!(prompt.observed_case_line, "test mod_a::red_case ... FAILED");
        assert!(prompt.failure_summary_line.contains("0 passed; 1 failed; 0 ignored"));
        assert!(prompt.bdd_text.contains("Scenario: red is expected"));
        assert!(host.guard_authority.approval.is_none());
    }

    #[test]
    fn guard_red_qualification_callback_is_bound_to_producer_and_never_final_approval() {
        let (mut host, _, _, reference, capture) = captured_red_host();
        seed_pending_qualification(&mut host, reference, &capture);
        let qualified = host.guard_complete_red_qualification(reference, capture.producer_id, GuardNativeObservation::Yes)
            .expect("exact capture qualified");
        assert_eq!(qualified.id, capture.producer_id);
        assert_eq!(qualified.producer_id, capture.producer_id);
        assert_eq!(qualified.artifact_sha256, capture.artifact_sha256);
        assert_eq!(qualified.test_id, "mod_a::red_case");
        assert_eq!(qualified.bdd_id, "BDD-01");
        assert_eq!(qualified.binding.red_id, capture.producer_id.to_string());
        assert_eq!(host.guard_qualified_red_for_approval(reference), Ok(qualified));
        assert!(host.guard_authority.approval.is_none(), "BDD qualification is not final approval");
    }

    #[test]
    fn guard_red_qualification_rejects_replaced_producer_after_prompt() {
        let (mut host, _, _, reference, capture) = captured_red_host();
        seed_pending_qualification(&mut host, reference, &capture);
        let replacement = host.guard_candidates.get_mut(&reference).unwrap().mechanical_capture.as_mut().unwrap();
        replacement.producer_id += 1;
        assert_eq!(
            host.guard_complete_red_qualification(reference, capture.producer_id, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified))
        );
        assert!(host.guard_qualified_red_for_approval(reference).is_err());
    }

    #[test]
    fn guard_red_qualification_rechecks_task_and_source_after_native_wait() {
        for remove_task in [false, true] {
            let (mut host, fs, _, reference, capture) = captured_red_host();
            seed_pending_qualification(&mut host, reference, &capture);
            if remove_task {
                host.replace_projection_tasks(Vec::new());
            } else {
                fs.seed("D:/candidate/bdd.feature", b"changed while qualification dialog was open");
            }
            assert!(host.guard_complete_red_qualification(reference, capture.producer_id, GuardNativeObservation::Yes).is_err());
            assert!(host.guard_qualified_red_for_approval(reference).is_err());
        }
    }

    #[test]
    fn guard_red_qualification_no_or_cancel_creates_no_qualified_record() {
        for observation in [GuardNativeObservation::No, GuardNativeObservation::Cancel] {
            let (mut host, _, _, reference, capture) = captured_red_host();
            seed_pending_qualification(&mut host, reference, &capture);
            assert_eq!(
                host.guard_complete_red_qualification(reference, capture.producer_id, observation),
                Err(GuardCandidateError::Authority(GuardAuthorityError::NativeDeclined))
            );
            assert!(host.guard_qualified_red_for_approval(reference).is_err());
            assert!(host.guard_authority.approval.is_none());
        }
    }

    #[test]
    fn guard_red_qualification_pending_prompt_is_single_use_and_read_failure_clears_it() {
        let (mut host, fs, _, reference, capture) = captured_red_host();
        let prompt = host.guard_prepare_red_qualification(reference).expect("first prompt prepared");
        assert_eq!(prompt.producer_id, capture.producer_id);
        assert!(host.guard_prepare_red_qualification(reference).is_err(), "a second prompt cannot replace the producer-bound pending record");
        fs.fail("D:/candidate/arch.json");
        assert!(host.guard_complete_red_qualification(reference, capture.producer_id, GuardNativeObservation::Yes).is_err());
        let record = host.guard_candidates.get(&reference).unwrap();
        assert!(record.pending_qualification.is_none(), "unavailable evidence consumes and clears the callback state");
        assert!(record.qualified_red.is_none());
    }

    #[test]
    fn guard_red_qualification_new_capture_attempt_clears_old_proof_before_failure() {
        let (mut host, fs, _, reference, capture) = captured_red_host();
        host.guard_prepare_red_qualification(reference).expect("prompt prepared");
        host.guard_complete_red_qualification(reference, capture.producer_id, GuardNativeObservation::Yes)
            .expect("qualified");
        assert!(host.guard_qualified_red_for_approval(reference).is_ok());

        host.guard_red_process = Box::new(RecordingProcess::scripted([
            ProcessScript::completed(101, completed_output("", "failed build")),
        ]));
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Capture(GuardCaptureError::BuildFailed))
        );
        let record = host.guard_candidates.get(&reference).unwrap();
        assert!(record.mechanical_capture.is_none());
        assert!(record.qualified_red.is_none());
        assert!(record.pending_qualification.is_none());
        assert!(host.guard_qualified_red_for_approval(reference).is_err());
        assert!(fs.reads().len() > 4);
    }

    #[test]
    fn guard_capture_red_declined_consent_never_starts_a_process() {
        let (mut host, _, _, reference) = confirmed_capture_host();
        let process = RecordingProcess::scripted([]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Cancel),
            Err(GuardCandidateError::Capture(GuardCaptureError::ConsentDeclined))
        );
        assert!(process.calls().is_empty());
        assert!(host.guard_authority.approval.is_none());
    }

    #[test]
    fn guard_capture_red_requires_a_confirmed_host_candidate() {
        let (mut host, _, project) = setup();
        let reference = host.guard_prepare_candidate("TASK-A", &capture_candidate(project.as_str())).unwrap();
        let process = RecordingProcess::scripted([]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Capture(GuardCaptureError::CandidateNotConfirmed))
        );
        assert!(process.calls().is_empty());
    }

    #[test]
    fn guard_candidate_accepts_owner_declared_fixture_cwd_inside_bound_root() {
        let (mut host, fs, project) = setup();
        let mut draft = capture_candidate(project.as_str());
        draft.red_job.cwd_ref = "D:/candidate/fixtures/red-case".into();
        let reference = host.guard_prepare_candidate("TASK-A", &draft)
            .expect("the approved exact fixture cwd beneath the HOST root is allowed");
        host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes).expect("confirmed");
        assert_eq!(host.guard_candidates.get(&reference).unwrap().draft.as_ref().unwrap().red_job.cwd_ref, "D:/candidate/fixtures/red-case");
        assert_eq!(fs.reads().len(), 8, "only declared source files are read; no fixture directory probe");
    }

    #[test]
    fn guard_candidate_rejects_fixture_cwd_outside_bound_root_before_reads() {
        let (mut host, fs, project) = setup();
        let mut draft = capture_candidate(project.as_str());
        draft.red_job.cwd_ref = "D:/outside/fixture".into();
        assert_eq!(host.guard_prepare_candidate("TASK-A", &draft), Err(GuardCandidateError::InvalidCandidate));
        assert!(fs.reads().is_empty());
    }

    #[test]
    fn guard_capture_runs_exact_case_from_declared_fixture_cwd() {
        let (mut host, fs, project) = setup();
        let fixture_cwd = "D:/candidate/fixtures/red-case";
        let mut draft = capture_candidate(project.as_str());
        draft.red_job.cwd_ref = fixture_cwd.into();
        let reference = host.guard_prepare_candidate("TASK-A", &draft).expect("candidate prepared");
        host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes).expect("confirmed");
        let (path, _) = seed_capture_artifact(&fs);
        let process = RecordingProcess::scripted(successful_capture_processes(path));
        host.guard_red_process = Box::new(process.clone());
        assert!(host.guard_capture_red(reference, GuardNativeObservation::Yes).is_ok());
        assert!(process.calls().iter().all(|call| call.cwd.as_deref() == Some(fixture_cwd)));
    }

    #[test]
    fn guard_capture_red_rechecks_current_input_before_starting_build() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        fs.seed("D:/candidate/test.rs", b"changed after candidate confirmation");
        let process = RecordingProcess::scripted([]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock()),
            Err(GuardCandidateError::Capture(GuardCaptureError::InputStale))
        );
        assert!(process.calls().is_empty());
    }

    #[test]
    fn guard_capture_red_preflight_that_consumes_absolute_budget_never_starts_process() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let process = RecordingProcess::scripted([]);
        host.guard_red_process = Box::new(process.clone());
        let start = Instant::now();
        let initial_reads = fs.reads().len();
        let result = host.guard_capture_red_at(reference, GuardNativeObservation::Yes, || {
            if fs.reads().len() > initial_reads { start + std::time::Duration::from_secs(120) } else { start }
        });
        assert_eq!(result, Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut)));
        assert!(process.calls().is_empty(), "an exhausted preflight budget must be checked before ProcessPort::start");
    }

    #[test]
    fn guard_capture_red_rejects_build_failure_without_running_test_binary() {
        let (mut host, _, _, reference) = confirmed_capture_host();
        let process = RecordingProcess::scripted([ProcessScript::completed(101, completed_output("", "build failed"))]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Capture(GuardCaptureError::BuildFailed))
        );
        assert_eq!(process.calls().len(), 1, "failed build must not execute a test binary");
        assert!(host.guard_authority.approval.is_none());
    }

    #[test]
    fn guard_capture_red_rejects_ambiguous_target_artifacts() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let first = "D:/candidate/target/debug/deps/sgenaxis_desktop_lib-abc.exe";
        let second = "D:/candidate/target/debug/deps/sgenaxis_desktop_lib-def.exe";
        fs.seed(first, b"first");
        fs.seed(second, b"second");
        let mut build = cargo_artifact_message(first, "sgenaxis_desktop_lib");
        build.push('\n');
        build.push_str(&cargo_artifact_message(second, "sgenaxis_desktop_lib"));
        let process = RecordingProcess::scripted([ProcessScript::completed(0, completed_output(&build, ""))]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactAmbiguous))
        );
        assert_eq!(process.calls().len(), 1);
    }

    #[test]
    fn guard_capture_red_rejects_non_failed_or_unobserved_exact_case() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let build = ProcessScript::completed(0, completed_output(&format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")), ""));
        let pass = ProcessScript::completed(0, completed_output("running 1 test\ntest mod_a::red_case ... ok\ntest result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 42 filtered out\n", ""));
        let process = RecordingProcess::scripted([build, pass]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Capture(GuardCaptureError::CaseNotObserved))
        );
        assert_eq!(process.calls().len(), 2);
    }

    #[test]
    fn guard_capture_red_requires_dual_eof_before_advancing_from_build() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let output = ProcessOutput {
            stdout: format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")),
            stdout_completion: StreamCompletion::Eof,
            stderr_completion: StreamCompletion::Open,
            ..ProcessOutput::default()
        };
        let process = RecordingProcess::scripted([ProcessScript::completed(0, output)]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock()),
            Err(GuardCandidateError::Capture(GuardCaptureError::StreamIncomplete))
        );
        assert_eq!(process.calls().len(), 1, "test binary cannot start before build streams reach EOF");
    }

    #[test]
    fn guard_capture_red_accepts_late_eof_within_the_existing_drain_window() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let mut build_output = completed_output(&format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")), "");
        build_output.stdout_completion = StreamCompletion::Open;
        build_output.stderr_completion = StreamCompletion::Open;
        let mut build = ProcessScript::completed(0, build_output);
        build.completion_sequence.push_back((StreamCompletion::Eof, StreamCompletion::Eof));
        let test = ProcessScript::completed(101, completed_output(
            "running 1 test\ntest mod_a::red_case ... FAILED\npanicked at src\\test.rs:7:3: expected failure\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 42 filtered out\n", ""));
        let process = RecordingProcess::scripted([build, test]);
        host.guard_red_process = Box::new(process.clone());
        let captured = host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock())
            .expect("late EOF before the approved drain deadline remains observable");
        assert!(captured.dual_eof);
        assert_eq!(process.calls().len(), 2);
    }

    #[test]
    fn guard_capture_red_absolute_deadline_retains_unresolved_process_and_blocks_retry() {
        let (mut host, _, _, reference) = confirmed_capture_host();
        let process = RecordingProcess::scripted([ProcessScript::running(completed_output("", ""), false)]);
        host.guard_red_process = Box::new(process.clone());
        let start = Instant::now();
        let process_for_clock = process.clone();
        let mut after_start = VecDeque::from([start + std::time::Duration::from_secs(119), start + std::time::Duration::from_secs(120)]);
        let result = host.guard_capture_red_at(reference, GuardNativeObservation::Yes, || {
            if process_for_clock.calls().is_empty() { start } else { after_start.pop_front().unwrap_or(start + std::time::Duration::from_secs(120)) }
        });
        assert_eq!(result, Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut)));
        assert!(host.guard_capture_process.is_some(), "unconfirmed termination/drain must retain exact ownership");
        assert_eq!(process.calls().len(), 1);
        assert_eq!(process.cancel_count(ProcessId(41)), 1, "timeout requests cancellation exactly once");
        assert_eq!(
            host.guard_capture_red(reference, GuardNativeObservation::Yes),
            Err(GuardCandidateError::Capture(GuardCaptureError::CleanupPending))
        );
        assert_eq!(process.calls().len(), 1, "no retry while process ownership is unresolved");
    }

    #[test]
    fn guard_capture_red_rechecks_candidate_inputs_after_process_execution() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let build = ProcessScript::completed(0, completed_output(&format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")), ""));
        let test = ProcessScript::completed(101, completed_output(
            "running 1 test\ntest mod_a::red_case ... FAILED\npanicked at src\\test.rs:7:3: expected failure\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 42 filtered out\n", ""))
            .mutate_on_start(fs.clone(), "D:/candidate/test.rs", b"changed during exact-case execution");
        let process = RecordingProcess::scripted([build, test]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock()),
            Err(GuardCandidateError::Capture(GuardCaptureError::InputStale))
        );
        assert_eq!(process.calls().len(), 2);
        assert!(host.guard_candidates.get(&reference).unwrap().mechanical_capture.is_none());
    }

    #[test]
    fn guard_capture_red_rejects_artifact_bytes_changed_after_execution() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let build = ProcessScript::completed(0, completed_output(&format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")), ""));
        let test = ProcessScript::completed(101, completed_output(
            "running 1 test\ntest mod_a::red_case ... FAILED\npanicked at src\\test.rs:7:3: expected failure\ntest result: FAILED. 0 passed; 1 failed; 0 ignored; 0 measured; 42 filtered out\n", ""))
            .mutate_on_start(fs.clone(), path, b"replacement executable bytes");
        let process = RecordingProcess::scripted([build, test]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock()),
            Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactChanged))
        );
        assert_eq!(process.calls().len(), 2);
    }

    #[test]
    fn guard_capture_red_final_artifact_read_crossing_absolute_budget_is_not_published() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let process = RecordingProcess::scripted(successful_capture_processes(path));
        host.guard_red_process = Box::new(process.clone());
        let start = Instant::now();
        let initial_reads = fs.reads().len();
        let result = host.guard_capture_red_at(reference, GuardNativeObservation::Yes, || {
            if fs.reads().len() >= initial_reads + 6 { start + std::time::Duration::from_secs(120) } else { start }
        });
        assert_eq!(result, Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut)));
        assert_eq!(process.calls().len(), 2);
        assert!(host.guard_candidates.get(&reference).unwrap().mechanical_capture.is_none(), "expired final verification cannot publish a capture");
    }

    #[test]
    fn guard_capture_red_requires_a_unique_artifact_for_the_confirmed_target() {
        let (mut host, _, _, reference) = confirmed_capture_host();
        let process = RecordingProcess::scripted([ProcessScript::completed(
            0,
            completed_output(&format!("{}\n", cargo_artifact_message("D:/candidate/target/other.exe", "other_target")), ""),
        )]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock()),
            Err(GuardCandidateError::Capture(GuardCaptureError::TargetMismatch))
        );
        assert_eq!(process.calls().len(), 1);
    }

    #[test]
    fn guard_capture_red_rejects_stream_error_without_invoking_the_case() {
        let (mut host, fs, _, reference) = confirmed_capture_host();
        let (path, _) = seed_capture_artifact(&fs);
        let build = ProcessOutput {
            stdout: format!("{}\n", cargo_artifact_message(path, "sgenaxis_desktop_lib")),
            stdout_completion: StreamCompletion::Eof,
            stderr_completion: StreamCompletion::Error("scripted stderr failure".into()),
            ..ProcessOutput::default()
        };
        let process = RecordingProcess::scripted([ProcessScript::completed(0, build)]);
        host.guard_red_process = Box::new(process.clone());
        assert_eq!(
            host.guard_capture_red_at(reference, GuardNativeObservation::Yes, deterministic_drain_clock()),
            Err(GuardCandidateError::Capture(GuardCaptureError::ProcessObservation))
        );
        assert_eq!(process.calls().len(), 1, "stream error cannot proceed to exact-case execution");
    }

    #[test]
    fn guard_generic_unknown_task_is_rejected_without_candidate_or_authority() {
        let (mut host, _, _) = setup();
        assert_eq!(
            host.guard_prepare_generic_classification("missing-task"),
            Err(GuardCandidateError::UnknownTask)
        );
        assert!(host.guard_authority.pending.is_none());
        assert!(host.guard_authority.approval.is_none());
        assert!(host.guard_candidates.is_empty());
        assert!(host.guard_intents.is_empty());
    }

    #[test]
    fn guard_generic_yes_records_only_generic_intent_and_replay_is_rejected() {
        let (mut host, fs, _) = setup();
        let reference = host.guard_prepare_generic_classification("TASK-A").expect("prepared");
        assert!(fs.reads().is_empty(), "generic classification has no source snapshot");
        host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes).expect("confirmed");
        assert_eq!(host.guard_intents.get("TASK-A"), Some(&super::super::GuardHostIntent::Generic));
        assert!(host.guard_authority.approval.is_none());
        assert!(host.guard_authority.pending.is_none());
        assert!(host.guard_candidates.get(&reference).unwrap().confirmed);
        assert_eq!(host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes), Err(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord)));
        assert_eq!(host.guard_authority.authorize_start(super::super::GuardHostIntent::Generic, reference, &host.guard_candidates.get(&reference).unwrap().binding), Err(GuardAuthorityError::RequiresApproval));
        assert!(!host.guard_candidates.get(&reference).unwrap().capture_attempted);
        assert!(host.guard_candidates.get(&reference).unwrap().mechanical_capture.is_none());
        assert!(fs.reads().is_empty());
    }

    #[test]
    fn guard_generic_no_cancel_leave_no_intent_or_approval() {
        for observation in [GuardNativeObservation::No, GuardNativeObservation::Cancel] {
            let (mut host, fs, _) = setup();
            let reference = host.guard_prepare_generic_classification("TASK-A").expect("prepared");
            assert_eq!(host.guard_complete_candidate_confirmation(reference, observation), Err(GuardCandidateError::Authority(GuardAuthorityError::NativeDeclined)));
            assert!(host.guard_intents.get("TASK-A").is_none());
            assert!(host.guard_authority.approval.is_none());
            assert!(host.guard_authority.pending.is_none());
            assert!(host.guard_candidates.get(&reference).is_none());
            assert!(fs.reads().is_empty());
        }
    }

    #[test]
    fn gc_candidate_task_removed_during_native_wait_fails_closed_for_both_intents() {
        // A board/task projection may change while the native dialog is open.
        // A Yes must not confirm a candidate whose task no longer exists.
        for implementation in [false, true] {
            let (mut host, _, project) = setup();
            let reference = if implementation {
                host.guard_prepare_candidate("TASK-A", &candidate(project.as_str())).expect("prepared")
            } else {
                host.guard_prepare_generic_classification("TASK-A").expect("prepared")
            };
            host.replace_projection_tasks(Vec::new());
            assert_eq!(
                host.guard_complete_candidate_confirmation(reference, GuardNativeObservation::Yes),
                Err(GuardCandidateError::UnknownTask)
            );
            assert!(host.guard_authority.pending.is_none());
            assert!(host.guard_authority.approval.is_none());
            assert!(host.guard_candidates.get(&reference).is_none());
            assert!(host.guard_intents.get("TASK-A").is_none());
        }
    }
}
