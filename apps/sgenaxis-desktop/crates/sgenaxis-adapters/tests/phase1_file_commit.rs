#![cfg(all(windows, feature = "std-adapters"))]
//! IO-PREREQ observable contracts. Setup uses only owned temporary fixtures.
//! Controlled lease tests supply a real fixture handle via a cfg(test)-only
//! constructor; they do not count as proof that product acquire_write works.

#[path = "../src/file_commit.rs"]
mod controlled;

use controlled::{StdFileWriteLease, TestCheckpoints};
use sgenaxis_adapters::StdFileCommit;
use sgenaxis_ports::{CommitError, CommitStage, FileCommitPort, FileWriteLease};
use sgenaxis_spec::packet::source_sha256;
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::os::windows::fs::OpenOptionsExt;
use std::os::windows::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{mpsc, Arc};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

const OLD: &[u8] = b"OLD-COMPLETE-DOCUMENT";
const NEW: &[u8] = b"NEW-COMPLETE-DOCUMENT";

fn digest(bytes: &[u8]) -> String {
    format!("sha256:{}", source_sha256(bytes))
}

struct Fixture {
    base: PathBuf,
    root: PathBuf,
    owner: String,
}
impl Fixture {
    fn new() -> Self {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        Self::at_stamp(stamp)
    }
    fn at_stamp(stamp: u128) -> Self {
        static SEQUENCE: AtomicU64 = AtomicU64::new(0);
        let base = std::env::temp_dir().join("eluslot-io-red-fixtures");
        fs::create_dir_all(&base).expect("fixture base must be available");
        let base = base.canonicalize().unwrap();
        Self::exclusive(base, || {
            format!(
                "io-{}-{}-{}",
                std::process::id(),
                stamp,
                SEQUENCE.fetch_add(1, Ordering::Relaxed)
            )
        })
    }
    fn exclusive(base: PathBuf, mut name: impl FnMut() -> String) -> Self {
        for _ in 0..32 {
            let owner = name();
            let root = base.join(&owner);
            match fs::create_dir(&root) {
                Ok(()) => {
                    fs::write(root.join(".owned-fixture"), owner.as_bytes()).unwrap();
                    return Self { base, root, owner };
                }
                Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => continue,
                Err(e) => panic!("FIXTURE_SETUP directory: {e}"),
            }
        }
        panic!("FIXTURE_SETUP exclusive fixture retry exhausted after 32 attempts");
    }
    fn target(&self) -> String {
        self.root.join("document.ess").to_str().unwrap().into()
    }
    fn sidecar(&self) -> PathBuf {
        PathBuf::from(format!("{}.eluslot-lock", self.target()))
    }
    fn tx_dir(&self) -> PathBuf {
        PathBuf::from(format!("{}.eluslot-commit", self.target()))
    }
    fn old(&self) {
        fs::write(self.target(), OLD).unwrap();
    }
    fn fixture_handle(&self) -> File {
        OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .share_mode(0)
            .open(self.sidecar())
            .expect("fixture must establish a real OS handle")
    }
    fn lease(&self, hooks: TestCheckpoints) -> StdFileWriteLease {
        StdFileWriteLease::for_test(self.target(), self.fixture_handle(), hooks)
    }
    fn journal(&self, bytes: &[u8]) {
        fs::create_dir(self.tx_dir()).unwrap();
        fs::write(self.tx_dir().join("journal.v1"), bytes).unwrap();
        fs::write(self.tx_dir().join("old.bin"), OLD).unwrap();
        fs::write(self.tx_dir().join("new.bin"), NEW).unwrap();
    }
}
impl Drop for Fixture {
    fn drop(&mut self) {
        // Verify the resolved absolute target and ownership before recursive cleanup.
        if let Ok(root) = self.root.canonicalize() {
            if root.parent() == Some(self.base.as_path())
                && root.starts_with(&self.base)
                && fs::read_to_string(root.join(".owned-fixture"))
                    .ok()
                    .as_deref()
                    == Some(&self.owner)
            {
                let _ = fs::remove_dir_all(root);
            }
        }
    }
}

struct ChildFixture {
    child: Child,
    line: mpsc::Receiver<String>,
}
impl ChildFixture {
    fn hold(f: &Fixture) -> Self {
        let helper = std::env::var_os("FILE_COMMIT_PROBE_PATH")
            .expect("missing helper is invalid setup, never valid RED");
        assert!(
            Path::new(&helper).is_file(),
            "helper must be built before tests"
        );
        let mut child = Command::new(helper)
            .arg("native-hold")
            .arg(&f.root)
            .arg(f.sidecar())
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .creation_flags(0x0800_0000)
            .spawn()
            .expect("fixture helper must launch");
        let stdout = child.stdout.take().unwrap();
        let (tx, line) = mpsc::channel();
        std::thread::spawn(move || {
            let mut value = String::new();
            let _ = BufReader::new(stdout).read_line(&mut value);
            let _ = tx.send(value.trim().to_string());
        });
        let fixture = Self { child, line };
        assert_eq!(
            fixture
                .line
                .recv_timeout(Duration::from_secs(5))
                .expect("helper timeout is invalid fixture setup"),
            "READY",
            "fixture helper must acquire its independent OS handle"
        );
        fixture
    }
    fn kill_and_wait(&mut self) {
        self.child
            .kill()
            .expect("owned fixture process must terminate");
        self.child.wait().unwrap();
    }
    fn release(&mut self) {
        self.child
            .stdin
            .take()
            .unwrap()
            .write_all(b"EXIT\n")
            .unwrap();
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            if let Some(status) = self.child.try_wait().unwrap() {
                assert!(status.success(), "fixture helper must exit cleanly");
                return;
            }
            assert!(
                Instant::now() < deadline,
                "helper shutdown timeout is invalid fixture setup"
            );
            std::thread::sleep(Duration::from_millis(10));
        }
    }
}
impl Drop for ChildFixture {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn prepared_record(f: &Fixture) -> Vec<u8> {
    // Independent fixture encoder only. No product journal codec is implemented.
    let mut payload = Vec::new();
    for field in [
        "0123456789abcdef0123456789abcdef".to_string(),
        f.target(),
        digest(OLD),
        digest(NEW),
        "old.bin".into(),
        "new.bin".into(),
    ] {
        payload.extend_from_slice(&(field.len() as u32).to_le_bytes());
        payload.extend_from_slice(field.as_bytes());
    }
    payload.push(1); // PREPARED, record version 1.
    let mut record = b"ELUCOMMIT".to_vec();
    record.extend_from_slice(&1u32.to_le_bytes());
    record.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    record.extend_from_slice(&payload);
    let checksum = source_sha256(&record);
    record.extend_from_slice(checksum.as_bytes());
    record
}

#[test]
fn io_01_creates_exactly_one_new_directory() {
    let f = Fixture::new();
    let r =
        StdFileCommit::new().create_directory_exclusive(f.root.to_str().unwrap(), "new-project");
    assert!(r.is_ok(), "exclusive creation must succeed: {r:?}");
    assert!(f.root.join("new-project").is_dir());
}

#[test]
fn io_02_existing_file_or_directory_is_never_replaced() {
    let f = Fixture::new();
    f.old();
    fs::create_dir(f.root.join("empty")).unwrap();
    fs::create_dir(f.root.join("nonempty")).unwrap();
    fs::write(f.root.join("nonempty/keep"), OLD).unwrap();
    for name in ["document.ess", "empty", "nonempty"] {
        let r = StdFileCommit::new().create_directory_exclusive(f.root.to_str().unwrap(), name);
        assert!(
            matches!(r, Err(CommitError::AlreadyExists { .. })),
            "must reject existing target: {r:?}"
        );
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
        assert_eq!(fs::read(f.root.join("nonempty/keep")).unwrap(), OLD);
    }
}

#[test]
fn io_03_invalid_names_are_rejected_without_child_creation() {
    let f = Fixture::new();
    for name in ["", " ", "..", "../outside", "a/b", "CON", "a:b"] {
        let r = StdFileCommit::new().create_directory_exclusive(f.root.to_str().unwrap(), name);
        assert!(
            matches!(r, Err(CommitError::InvalidPath { .. })),
            "must reject {name:?}: {r:?}"
        );
        assert_eq!(fs::read_dir(&f.root).unwrap().count(), 1);
    }
}

#[test]
fn io_04_other_adapter_instance_cannot_take_an_owned_lease() {
    let f = Fixture::new();
    let first = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        first.is_ok(),
        "first product lease must be obtainable: {:?}",
        first.as_ref().err()
    );
    let _first = first.unwrap();
    let second = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        matches!(second, Err(CommitError::Busy { .. })),
        "second product writer must be busy: {:?}",
        second.err()
    );
}

#[test]
fn io_receipt_echoes_requested_path_not_canonicalized_form() {
    // Contract: the commit receipt reports the path the CALLER passed to
    // acquire_write, not the adapter's internally-canonicalized form. A caller
    // may legitimately pass a valid non-canonical path (e.g. without the Windows
    // \\?\ extended-length prefix); the receipt must echo it verbatim so strict
    // callers (save_definition's checked_receipt) do not see a false mismatch.
    let f = Fixture::new();
    let canonical = f.target();
    let requested = canonical
        .strip_prefix("\\\\?\\")
        .unwrap_or(&canonical)
        .to_string();
    assert_ne!(
        requested, canonical,
        "fixture base is expected to be \\\\?\\-canonical on Windows"
    );
    let mut lease = StdFileCommit::new()
        .acquire_write(&requested)
        .expect("acquire with a valid non-canonical path");
    let receipt = lease
        .replace_checked(None, NEW)
        .expect("commit via non-canonical path");
    assert_eq!(
        receipt.target_path, requested,
        "receipt echoes the requested path verbatim"
    );
    assert_eq!(fs::read(&canonical).unwrap(), NEW, "bytes landed at the target");
}

#[test]
fn io_05_independent_process_handle_blocks_product_lease() {
    let f = Fixture::new();
    let _child = ChildFixture::hold(&f);
    let r = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        matches!(r, Err(CommitError::Busy { .. })),
        "must recognize cooperating OS-held lock: {:?}",
        r.err()
    );
}

#[test]
fn io_06_process_death_releases_handle_without_stale_file_deletion() {
    let f = Fixture::new();
    let mut child = ChildFixture::hold(&f);
    child.kill_and_wait();
    assert!(
        f.sidecar().exists(),
        "fixture precondition: persistent sidecar remains"
    );
    let r = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        r.is_ok(),
        "dead process no longer owns OS handle: {:?}",
        r.as_ref().err()
    );
}

#[test]
fn io_07_new_file_commit_matches_bytes_and_receipt() {
    let f = Fixture::new();
    let mut lease = f.lease(TestCheckpoints::default());
    let r = lease.replace_checked(None, NEW);
    assert!(r.is_ok(), "new target commit must succeed: {r:?}");
    let receipt = r.unwrap();
    assert_eq!(fs::read(f.target()).unwrap(), NEW);
    assert_eq!(receipt.previous_digest, None);
    assert_eq!(receipt.committed_digest, digest(NEW));
    assert!(!receipt.transaction_id.is_empty());
}

#[test]
fn io_08_existing_file_commit_keeps_complete_new_content() {
    let f = Fixture::new();
    f.old();
    let mut lease = f.lease(TestCheckpoints::default());
    let r = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(r.is_ok(), "matching digest must permit replace: {r:?}");
    assert_eq!(r.unwrap().previous_digest, Some(digest(OLD)));
    assert_eq!(fs::read(f.target()).unwrap(), NEW);
}

#[test]
fn io_09_stale_digest_rejects_without_changing_original() {
    let f = Fixture::new();
    f.old();
    let mut lease = f.lease(TestCheckpoints::default());
    let r = lease.replace_checked(Some(&digest(b"stale")), NEW);
    assert!(
        matches!(r, Err(CommitError::Conflict { .. })),
        "stale digest must conflict: {r:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}

#[test]
fn io_10_expected_presence_mismatch_never_overwrites() {
    let f = Fixture::new();
    f.old();
    let mut lease = f.lease(TestCheckpoints::default());
    let r = lease.replace_checked(None, NEW);
    assert!(
        matches!(r, Err(CommitError::Conflict { .. })),
        "expected absent but present: {r:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}

#[test]
fn io_11_pre_publish_faults_leave_old_bytes_and_owned_diagnostics() {
    for stage in [
        CommitStage::PrepareOld,
        CommitStage::PrepareNew,
        CommitStage::WritePreparedJournal,
        CommitStage::BeforePublish,
    ] {
        let f = Fixture::new();
        f.old();
        let hooks = TestCheckpoints {
            fail_at: vec![stage],
            ..Default::default()
        };
        let visited = hooks.observed.clone();
        let mut lease = f.lease(hooks);
        let r = lease.replace_checked(Some(&digest(OLD)), NEW);
        assert!(
            matches!(&r, Err(CommitError::Storage { stage: reached, .. }) if *reached == stage),
            "must reach requested fault, not Skeleton error: {r:?}"
        );
        assert!(visited.lock().unwrap().contains(&stage));
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
    }
}

#[test]
fn io_12_post_publish_failure_restores_old_before_ordinary_error() {
    let f = Fixture::new();
    f.old();
    let hooks = TestCheckpoints {
        fail_at: vec![CommitStage::VerifyPublished],
        ..Default::default()
    };
    let visited = hooks.observed.clone();
    let mut lease = f.lease(hooks);
    let r = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        matches!(
            &r,
            Err(CommitError::Storage {
                stage: CommitStage::VerifyPublished,
                ..
            })
        ),
        "must report real injected failure after restoration: {r:?}"
    );
    assert!(visited.lock().unwrap().contains(&CommitStage::Restore));
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}

#[test]
fn io_13_failed_restore_retains_versions_and_blocks_followup() {
    let f = Fixture::new();
    f.old();
    let hooks = TestCheckpoints {
        fail_at: vec![CommitStage::VerifyPublished, CommitStage::Restore],
        ..Default::default()
    };
    let mut lease = f.lease(hooks);
    let r = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        matches!(&r, Err(CommitError::RecoveryRequired { .. })),
        "failed restore is not a successful rollback: {r:?}"
    );
    if let Err(CommitError::RecoveryRequired {
        journal_path,
        old_version_path,
        new_version_path,
        ..
    }) = r
    {
        assert!(Path::new(&journal_path).is_file());
        assert_eq!(fs::read(old_version_path.unwrap()).unwrap(), OLD);
        assert_eq!(fs::read(new_version_path.unwrap()).unwrap(), NEW);
    }
    let again = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(matches!(again, Err(CommitError::RecoveryRequired { .. })));
}

#[test]
fn io_14_unfinished_prepared_record_rejects_reopen() {
    let f = Fixture::new();
    f.old();
    f.journal(&prepared_record(&f));
    let r = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        matches!(r, Err(CommitError::RecoveryRequired { .. })),
        "unfinished journal must fail closed: {:?}",
        r.err()
    );
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(f.tx_dir().join("new.bin")).unwrap(), NEW);
}

#[test]
fn io_15_corrupt_record_cannot_trigger_path_actions_or_cleanup() {
    let f = Fixture::new();
    f.old();
    f.journal(b"unknown-version-or-corrupt-checksum");
    let r = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        matches!(r, Err(CommitError::RecoveryRequired { .. })),
        "unknown journal cannot be interpreted: {:?}",
        r.err()
    );
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(f.tx_dir().join("old.bin")).unwrap(), OLD);
}

#[test]
fn io_16_normal_handle_close_allows_immediate_reacquisition() {
    let f = Fixture::new();
    let mut child = ChildFixture::hold(&f);
    child.release();
    let r = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        r.is_ok(),
        "normal close releases OS ownership immediately: {:?}",
        r.as_ref().err()
    );
}

#[test]
fn io_17_observed_external_edit_before_publish_is_not_overwritten() {
    let f = Fixture::new();
    f.old();
    let path = f.target();
    let hooks = TestCheckpoints {
        before_publish: Some(Arc::new(move || {
            fs::write(&path, b"EXTERNAL-CHANGE").unwrap();
        })),
        ..Default::default()
    };
    let mut lease = f.lease(hooks);
    let r = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        matches!(r, Err(CommitError::Conflict { .. })),
        "must recheck the observed target: {r:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), b"EXTERNAL-CHANGE");
}

#[test]
fn io_18a_foreign_temp_collision_is_not_deleted() {
    let f = Fixture::new();
    f.old();
    let foreign = f.root.join("foreign.tmp");
    fs::write(&foreign, b"FOREIGN").unwrap();
    let hooks = TestCheckpoints {
        temp_candidates: vec![
            foreign.to_str().unwrap().into(),
            f.root.join("owned.tmp").to_str().unwrap().into(),
        ],
        ..Default::default()
    };
    let mut lease = f.lease(hooks);
    let r = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        r.is_ok(),
        "collision must be retried using an owned new temp: {r:?}"
    );
    assert_eq!(fs::read(foreign).unwrap(), b"FOREIGN");
    assert_eq!(fs::read(f.target()).unwrap(), NEW);
}

#[test]
fn io_18b_cleanup_fault_does_not_destroy_preimage_or_foreign_data() {
    let f = Fixture::new();
    f.old();
    let foreign = f.root.join("foreign.tmp");
    fs::write(&foreign, b"FOREIGN").unwrap();
    let hooks = TestCheckpoints {
        fail_at: vec![CommitStage::VerifyPublished, CommitStage::Cleanup],
        ..Default::default()
    };
    let visited = hooks.observed.clone();
    let mut lease = f.lease(hooks);
    let r = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        visited.lock().unwrap().contains(&CommitStage::Cleanup),
        "cleanup fault must actually be reached; result={r:?}"
    );
    assert!(r.is_err());
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(foreign).unwrap(), b"FOREIGN");
}

#[test]
fn io_read_current_observes_complete_bytes_under_a_fixture_lease() {
    let f = Fixture::new();
    f.old();
    let lease = f.lease(TestCheckpoints::default());
    assert_eq!(
        lease.read_current(),
        Ok(Some(OLD.to_vec())),
        "fourth Port method must read exact bytes"
    );
}

// IO-G1..G6 / IO-ADD-01..14: separately named rows, not a first-failure loop.
use controlled::{decode_journal_for_test, JournalDecodeError as DecodeError};
use std::collections::BTreeMap;
use std::sync::Mutex;

const TX: &str = "0123456789abcdef0123456789abcdef";
fn fields(target: &str, present: bool) -> Vec<Vec<u8>> {
    vec![
        TX.as_bytes().to_vec(),
        target.as_bytes().to_vec(),
        if present {
            digest(OLD).into_bytes()
        } else {
            vec![]
        },
        digest(NEW).into_bytes(),
        if present { b"old.bin".to_vec() } else { vec![] },
        b"new.bin".to_vec(),
    ]
}
fn encode_fields(fields: &[Vec<u8>], state: u8) -> Vec<u8> {
    let mut payload = Vec::new();
    for field in fields {
        payload.extend_from_slice(&(field.len() as u32).to_le_bytes());
        payload.extend_from_slice(field);
    }
    payload.push(state);
    let mut bytes = b"ELUCOMMIT".to_vec();
    bytes.extend_from_slice(&1u32.to_le_bytes());
    bytes.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    bytes.extend(payload);
    resign(&mut bytes);
    bytes
}
fn resign(bytes: &mut Vec<u8>) {
    let hash = source_sha256(bytes);
    bytes.extend_from_slice(hash.as_bytes());
}
fn rewrite_checksum(bytes: &mut Vec<u8>) {
    bytes.truncate(bytes.len() - 64);
    resign(bytes);
}
fn snapshot(root: &Path) -> BTreeMap<String, Vec<u8>> {
    fn walk(root: &Path, at: &Path, out: &mut BTreeMap<String, Vec<u8>>) {
        for entry in fs::read_dir(at).unwrap() {
            let entry = entry.unwrap();
            assert!(
                !entry.file_type().unwrap().is_symlink(),
                "FIXTURE_SETUP symlink"
            );
            let path = entry.path();
            if path.is_dir() {
                out.insert(
                    format!("{}/", path.strip_prefix(root).unwrap().to_string_lossy()),
                    Vec::new(),
                );
                walk(root, &path, out);
            } else {
                out.insert(
                    path.strip_prefix(root)
                        .unwrap()
                        .to_string_lossy()
                        .into_owned(),
                    fs::read(path).unwrap(),
                );
            }
        }
    }
    let mut result = BTreeMap::new();
    walk(root, root, &mut result);
    result
}
fn assert_fixture_record(bytes: &[u8], target: &str, state: u8) -> String {
    assert_eq!(&bytes[..9], b"ELUCOMMIT");
    assert_eq!(u32::from_le_bytes(bytes[9..13].try_into().unwrap()), 1);
    let n = u32::from_le_bytes(bytes[13..17].try_into().unwrap()) as usize;
    assert_eq!(bytes.len(), 17 + n + 64);
    assert_eq!(&bytes[17 + n..], source_sha256(&bytes[..17 + n]).as_bytes());
    let mut pos = 17;
    let mut values = Vec::new();
    for _ in 0..6 {
        let len = u32::from_le_bytes(bytes[pos..pos + 4].try_into().unwrap()) as usize;
        pos += 4;
        values.push(std::str::from_utf8(&bytes[pos..pos + len]).unwrap());
        pos += len;
    }
    assert_eq!(values[1], target);
    assert_eq!(bytes[pos], state);
    assert_eq!(pos + 1, 17 + n);
    values[0].into()
}

// IO-A-R1/R2: verified terminal evidence is captured before optional cleanup.
// Postconditions accept both completed cleanup and safe partial cleanup orders.
fn terminal_observer(
    journal: PathBuf,
    point: &'static str,
    captured: Arc<Mutex<Option<Vec<u8>>>>,
) -> Arc<dyn Fn(&str) + Send + Sync> {
    Arc::new(move |seen| {
        if seen == point {
            *captured.lock().unwrap() = Some(
                fs::read(&journal).expect("verified terminal journal must exist at observation"),
            );
        }
    })
}

fn assert_terminal_record(f: &Fixture, bytes: &[u8], state: u8, present: bool) {
    let transaction = assert_fixture_record(bytes, &f.target(), state);
    assert_eq!(transaction.len(), 32);
    assert!(transaction
        .bytes()
        .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v)));
    let mut expected = fields(&f.target(), present);
    expected[0] = transaction.into_bytes();
    assert_eq!(bytes, encode_fields(&expected, state));
}

fn assert_safe_terminal_layout(f: &Fixture, verified: &[u8], present: bool) {
    if !f.tx_dir().exists() {
        return;
    }
    let journal = f.tx_dir().join("journal.v1");
    if journal.exists() {
        assert_eq!(
            fs::read(journal).unwrap(),
            verified,
            "retained terminal provenance must stay valid"
        );
        let old = f.tx_dir().join("old.bin");
        if old.exists() {
            assert!(present, "original absence cannot have an old version");
            assert_eq!(fs::read(old).unwrap(), OLD);
        }
        let new = f.tx_dir().join("new.bin");
        if new.exists() {
            assert_eq!(fs::read(new).unwrap(), NEW);
        }
    } else {
        assert_eq!(
            fs::read_dir(f.tx_dir()).unwrap().count(),
            0,
            "journal is removed last; no transaction artifacts may lose provenance"
        );
    }
}

// IO-A-R3: safe-looking paths are not proof of verified version provenance.
fn assert_invalid_diagnostics(f: &Fixture, kind: &str, old: &Option<String>, new: &Option<String>) {
    if [
        "magic",
        "version",
        "checksum",
        "truncated",
        "trailing",
        "overflow",
        "length",
        "field_length",
        "oversize",
    ]
    .contains(&kind)
    {
        assert_eq!(
            old, &None,
            "pre-parse rejection cannot claim verified old version"
        );
        assert_eq!(
            new, &None,
            "pre-parse rejection cannot claim verified new version"
        );
    } else {
        for (name, candidate, bytes) in [("old.bin", old, OLD), ("new.bin", new, NEW)] {
            if let Some(path) = candidate {
                assert_eq!(PathBuf::from(path), f.tx_dir().join(name));
                assert_eq!(fs::read(path).unwrap(), bytes);
            }
        }
    }
}

#[test]
fn gap_01_expected_present_actual_absent() {
    let f = Fixture::new();
    let mut lease = f.lease(Default::default());
    let expected = digest(OLD);
    let result = lease.replace_checked(Some(&expected), NEW);
    assert!(
        matches!(&result, Err(CommitError::Conflict { expected: e, observed: None }) if e.as_deref()==Some(expected.as_str())),
        "PRODUCT_RED IO-ADD-01 {result:?}"
    );
    assert!(!Path::new(&f.target()).exists());
}

fn success_case(present: bool, empty: bool) {
    let f = Fixture::new();
    if present {
        f.old();
    }
    let captured = Arc::new(Mutex::new(None));
    let output = captured.clone();
    let journal = f.tx_dir().join("journal.v1");
    let hooks = TestCheckpoints {
        at_point: Some(Arc::new(move |point| {
            if point == "committed.verified" {
                *output.lock().unwrap() = Some(fs::read(&journal).unwrap());
            }
        })),
        ..Default::default()
    };
    let mut lease = f.lease(hooks);
    let old = present.then(|| digest(OLD));
    let bytes = if empty { &[][..] } else { NEW };
    let result = lease.replace_checked(old.as_deref(), bytes);
    assert!(result.is_ok(), "PRODUCT_RED IO-ADD-02 {result:?}");
    let receipt = result.unwrap();
    assert_eq!(receipt.target_path, f.target());
    assert_eq!(receipt.previous_digest, old);
    assert_eq!(receipt.committed_digest, digest(bytes));
    assert_eq!(receipt.transaction_id.len(), 32);
    assert!(receipt
        .transaction_id
        .bytes()
        .all(|v| v.is_ascii_digit() || (b'a'..=b'f').contains(&v)));
    assert_eq!(fs::read(f.target()).unwrap(), bytes);
    let record = captured.lock().unwrap();
    let record = record
        .as_ref()
        .expect("must observe committed journal before cleanup");
    assert_eq!(
        assert_fixture_record(record, &f.target(), 2),
        receipt.transaction_id
    );
    let mut expected_record = fields(&f.target(), present);
    expected_record[0] = receipt.transaction_id.as_bytes().to_vec();
    expected_record[3] = digest(bytes).into_bytes();
    assert_eq!(record, &encode_fields(&expected_record, 2));
}
macro_rules! successes { ($($name:ident:$present:expr,$empty:expr;)*) => {$ (#[test] fn $name(){success_case($present,$empty);})*}; }
successes! {
    gap_02_new_nonempty:false,false; gap_02_new_empty:false,true;
    gap_02_replace_nonempty:true,false; gap_02_replace_empty:true,true;
}

fn ordinary_fault(present: bool, stage: CommitStage, point: &'static str, post: bool) {
    let f = Fixture::new();
    if present {
        f.old();
    }
    let terminal = Arc::new(Mutex::new(None));
    let hooks = TestCheckpoints {
        fault_points: vec![point],
        at_point: Some(terminal_observer(
            f.tx_dir().join("journal.v1"),
            "rolled_back.verified",
            terminal.clone(),
        )),
        ..Default::default()
    };
    let seen = hooks.observed_points.clone();
    let consumed = hooks.consumed_points.clone();
    let mut lease = f.lease(hooks);
    let old = present.then(|| digest(OLD));
    let result = lease.replace_checked(old.as_deref(), NEW);
    assert!(
        matches!(&result,Err(CommitError::Storage{stage:s,reason,..}) if *s==stage && reason!="SKELETON_NOT_IMPLEMENTED"),
        "PRODUCT_RED IO-ADD-03 {point} {result:?}"
    );
    assert!(seen.lock().unwrap().iter().any(|p| p == point));
    assert!(consumed.lock().unwrap().iter().any(|p| p == point));
    if present {
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
    } else {
        assert!(!Path::new(&f.target()).exists());
    }
    if post {
        let record = terminal.lock().unwrap();
        let verified = record
            .as_ref()
            .expect("verified rollback must be observed before cleanup");
        assert_terminal_record(&f, verified, 3, present);
        assert_safe_terminal_layout(&f, verified, present);
    }
}
macro_rules! faults { ($($name:ident:$present:expr,$stage:ident,$point:literal,$post:expr;)*) => {$ (#[test] fn $name(){ordinary_fault($present,CommitStage::$stage,$point,$post);})*}; }
faults! {
    gap_03_old_write:true,PrepareOld,"old.write",false;
    gap_03_old_sync:true,PrepareOld,"old.sync",false;
    gap_03_new_write_old:true,PrepareNew,"new.write",false;
    gap_03_new_sync_old:true,PrepareNew,"new.sync",false;
    gap_03_new_write_absent:false,PrepareNew,"new.write",false;
    gap_03_new_sync_absent:false,PrepareNew,"new.sync",false;
    gap_03_prepared_write_old:true,WritePreparedJournal,"prepared.write",false;
    gap_03_prepared_sync_old:true,WritePreparedJournal,"prepared.sync",false;
    gap_03_prepared_publish_old:true,WritePreparedJournal,"prepared.publish",false;
    gap_03_prepared_verify_old:true,WritePreparedJournal,"prepared.verify",false;
    gap_03_prepared_write_absent:false,WritePreparedJournal,"prepared.write",false;
    gap_03_prepared_sync_absent:false,WritePreparedJournal,"prepared.sync",false;
    gap_03_prepared_publish_absent:false,WritePreparedJournal,"prepared.publish",false;
    gap_03_prepared_verify_absent:false,WritePreparedJournal,"prepared.verify",false;
    gap_03_before_publish_old:true,BeforePublish,"publish.before",true;
    gap_03_before_publish_absent:false,BeforePublish,"publish.before",true;
    gap_03_publish_old:true,Publish,"target.publish",true;
    gap_03_publish_absent:false,Publish,"target.publish",true;
    gap_03_verify_old:true,VerifyPublished,"target.verify",true;
    gap_03_verify_absent:false,VerifyPublished,"target.verify",true;
    gap_03_commit_write_old:true,WriteCommittedJournal,"committed.write",true;
    gap_03_commit_sync_old:true,WriteCommittedJournal,"committed.sync",true;
    gap_03_commit_publish_old:true,WriteCommittedJournal,"committed.publish",true;
    gap_03_commit_verify_old:true,WriteCommittedJournal,"committed.verify",true;
    gap_03_commit_write_absent:false,WriteCommittedJournal,"committed.write",true;
    gap_03_commit_sync_absent:false,WriteCommittedJournal,"committed.sync",true;
    gap_03_commit_publish_absent:false,WriteCommittedJournal,"committed.publish",true;
    gap_03_commit_verify_absent:false,WriteCommittedJournal,"committed.verify",true;
}

fn recovery_fault(present: bool, first: CommitStage, second: CommitStage, point: &'static str) {
    let f = Fixture::new();
    if present {
        f.old();
    }
    let hooks = TestCheckpoints {
        fail_at: vec![first],
        fault_points: vec![point],
        ..Default::default()
    };
    let consumed = hooks.consumed.clone();
    let consumed_points = hooks.consumed_points.clone();
    let observed = hooks.observed.clone();
    let mut lease = f.lease(hooks);
    let old = present.then(|| digest(OLD));
    let result = lease.replace_checked(old.as_deref(), NEW);
    assert!(
        matches!(&result, Err(CommitError::RecoveryRequired { .. })),
        "PRODUCT_RED IO-ADD-04 {point} {result:?}"
    );
    assert!(consumed.lock().unwrap().contains(&first));
    assert!(observed.lock().unwrap().contains(&second));
    assert!(consumed_points.lock().unwrap().iter().any(|x| x == point));
    if let Err(CommitError::RecoveryRequired {
        target_path,
        journal_path,
        old_version_path,
        new_version_path,
        ..
    }) = result
    {
        assert_eq!(target_path, f.target());
        assert!(Path::new(&journal_path).is_file());
        if present {
            assert_eq!(fs::read(old_version_path.unwrap()).unwrap(), OLD);
        } else {
            assert_eq!(old_version_path, None);
        }
        assert_eq!(fs::read(new_version_path.unwrap()).unwrap(), NEW);
    }
    assert!(matches!(
        lease.replace_checked(old.as_deref(), NEW),
        Err(CommitError::RecoveryRequired { .. })
    ));
    drop(lease);
    let again = StdFileCommit::new().acquire_write(&f.target());
    assert!(matches!(again, Err(CommitError::RecoveryRequired { .. })));
}
macro_rules! recoveries { ($($name:ident:$present:expr,$first:ident,$second:ident,$point:literal;)*) => {$ (#[test] fn $name(){recovery_fault($present,CommitStage::$first,CommitStage::$second,$point);})*}; }
recoveries! {
    gap_04_verify_restore_old:true,VerifyPublished,Restore,"restore.write";
    gap_04_verify_restore_absent:false,VerifyPublished,Restore,"restore.remove";
    gap_04_commit_restore_old:true,WriteCommittedJournal,Restore,"restore.write";
    gap_04_commit_restore_absent:false,WriteCommittedJournal,Restore,"restore.remove";
    gap_04_verify_restored_old:true,VerifyPublished,VerifyRestored,"restored.verify";
    gap_04_verify_restored_absent:false,VerifyPublished,VerifyRestored,"restored.verify";
    gap_04_commit_verify_restored_old:true,WriteCommittedJournal,VerifyRestored,"restored.verify";
    gap_04_commit_verify_restored_absent:false,WriteCommittedJournal,VerifyRestored,"restored.verify";
    gap_04_rollback_record_write_old:true,VerifyPublished,WriteCommittedJournal,"rolled_back.write";
    gap_04_rollback_record_write_absent:false,VerifyPublished,WriteCommittedJournal,"rolled_back.write";
    gap_04_rollback_record_sync_old:true,VerifyPublished,WriteCommittedJournal,"rolled_back.sync";
    gap_04_rollback_record_sync_absent:false,VerifyPublished,WriteCommittedJournal,"rolled_back.sync";
    gap_04_rollback_record_publish_old:true,VerifyPublished,WriteCommittedJournal,"rolled_back.publish";
    gap_04_rollback_record_publish_absent:false,VerifyPublished,WriteCommittedJournal,"rolled_back.publish";
    gap_04_rollback_record_verify_old:true,VerifyPublished,VerifyRestored,"rolled_back.verify";
    gap_04_rollback_record_verify_absent:false,VerifyPublished,VerifyRestored,"rolled_back.verify";
}

fn malformed_record(kind: &str, target: &str) -> (Vec<u8>, DecodeError) {
    let mut f = fields(target, true);
    let mut state = 1;
    let error = match kind {
        "magic" | "truncated" | "trailing" | "overflow" | "length" | "field_length"
        | "extra_field" => DecodeError::Framing,
        "version" => DecodeError::Version,
        "checksum" => DecodeError::Checksum,
        "utf8" | "nul" | "bom" => DecodeError::Text,
        "state" => DecodeError::State,
        "binding" => DecodeError::Binding,
        "relative" | "absolute" | "unc" | "device" | "ads" | "drive" | "old_relative" => {
            DecodeError::RelativePath
        }
        "oversize" => DecodeError::Size,
        _ => DecodeError::Field,
    };
    match kind {
        "utf8" => f[1] = vec![0xff],
        "nul" => f[1].push(0),
        "bom" => f[1].splice(0..0, [0xef, 0xbb, 0xbf]).for_each(drop),
        "state" => state = 255,
        "binding" => f[1] = br"C:\elsewhere\document.ess".to_vec(),
        "relative" => f[5] = b"../outside".to_vec(),
        "old_relative" => f[4] = b"../old.bin".to_vec(),
        "absolute" => f[5] = br"C:\outside\new.bin".to_vec(),
        "unc" => f[5] = br"\\host\share\new.bin".to_vec(),
        "device" => f[5] = br"\\?\GLOBALROOT\new.bin".to_vec(),
        "ads" => f[5] = b"new.bin:stream".to_vec(),
        "drive" => f[5] = b"C:new.bin".to_vec(),
        "txid" => f[0] = b"invalid-id".to_vec(),
        "digest" => f[3] = b"sha256:WRONG".to_vec(),
        "old_pair" => f[2].clear(),
        "extra_field" => f.push(b"extra".to_vec()),
        _ => {}
    }
    let mut bytes = encode_fields(&f, state);
    match kind {
        "magic" => {
            bytes[0] = 0;
            rewrite_checksum(&mut bytes);
        }
        "version" => {
            bytes[9..13].copy_from_slice(&2u32.to_le_bytes());
            rewrite_checksum(&mut bytes);
        }
        "checksum" => {
            let n = bytes.len();
            bytes[n - 1] = if bytes[n - 1] == b'0' { b'1' } else { b'0' };
        }
        "truncated" => {
            bytes.pop();
        }
        "trailing" => bytes.push(0),
        "overflow" => {
            bytes[13..17].copy_from_slice(&u32::MAX.to_le_bytes());
            rewrite_checksum(&mut bytes);
        }
        "length" => {
            bytes[13..17].copy_from_slice(&0u32.to_le_bytes());
            rewrite_checksum(&mut bytes);
        }
        "field_length" => {
            bytes[17..21].copy_from_slice(&u32::MAX.to_le_bytes());
            rewrite_checksum(&mut bytes);
        }
        "oversize" => bytes.resize(65537, 0),
        _ => {}
    }
    (bytes, error)
}
fn codec_case(kind: &str) {
    let target = r"C:\fixture\document.ess";
    let (bytes, error) = malformed_record(kind, target);
    let result = decode_journal_for_test(&bytes, target);
    assert_eq!(result, Err(error), "PRODUCT_RED IO-ADD-05/06 codec {kind}");
}
fn acquisition_invalid(kind: &str) {
    let fixture = Fixture::new();
    let outside = Fixture::new();
    fixture.old();
    fs::write(outside.root.join("sentinel"), b"OUTSIDE-KEEP").unwrap();
    let (mut bytes, _) = malformed_record(kind, &fixture.target());
    if ["relative", "old_relative", "absolute"].contains(&kind) {
        let mut unsafe_fields = fields(&fixture.target(), true);
        let path = if kind == "absolute" {
            outside.root.join("sentinel").to_string_lossy().into_owned()
        } else {
            format!("../../{}/sentinel", outside.owner)
        };
        unsafe_fields[if kind == "old_relative" { 4 } else { 5 }] = path.into_bytes();
        bytes = encode_fields(&unsafe_fields, 1);
    }
    fixture.journal(&bytes);
    drop(fixture.fixture_handle());
    let before = snapshot(&fixture.root);
    let outside_before = snapshot(&outside.root);
    let r = StdFileCommit::new().acquire_write(&fixture.target());
    assert!(
        matches!(&r, Err(CommitError::RecoveryRequired { .. })),
        "PRODUCT_RED IO-ADD-06 acquisition {kind} {:?}",
        r.as_ref().err()
    );
    if let Err(CommitError::RecoveryRequired {
        target_path,
        journal_path,
        old_version_path,
        new_version_path,
        reason,
    }) = r
    {
        assert_eq!(target_path, fixture.target());
        assert_eq!(
            PathBuf::from(journal_path),
            fixture.tx_dir().join("journal.v1")
        );
        assert!(!reason.is_empty());
        assert_invalid_diagnostics(&fixture, kind, &old_version_path, &new_version_path);
    }
    assert_eq!(snapshot(&fixture.root), before);
    assert_eq!(snapshot(&outside.root), outside_before);
}
macro_rules! codecs { ($($name:ident:$kind:literal;)*) => {$ (#[test] fn $name(){codec_case($kind);})*}; }
codecs! {
    gap_05_magic:"magic";gap_05_version_valid_checksum:"version";gap_05_checksum:"checksum";
    gap_05_truncated:"truncated";gap_05_trailing:"trailing";gap_05_overflow:"overflow";
    gap_05_payload_length:"length";gap_05_field_length:"field_length";
    gap_05_invalid_utf8:"utf8";gap_05_nul:"nul";gap_05_bom:"bom";gap_05_state:"state";
    gap_05_txid:"txid";gap_05_digest:"digest";gap_05_old_pair:"old_pair";gap_05_extra_field:"extra_field";
    gap_06_target_binding:"binding";gap_06_traversal:"relative";gap_06_old_traversal:"old_relative";
    gap_06_absolute:"absolute";gap_06_unc:"unc";gap_06_device:"device";gap_06_ads:"ads";gap_06_drive:"drive";
    gap_07_total_over_limit:"oversize";
}

fn codec_valid(state: u8, present: bool, path_len: usize, multibyte: bool) {
    let mut target = String::from("C:\\");
    while target.len() + if multibyte { 3 } else { 1 } <= path_len {
        if target.rsplit('\\').next().unwrap().len() >= 120 && target.len() + 1 < path_len {
            target.push('\\');
        } else {
            target.push(if multibyte { '界' } else { 'x' });
        }
    }
    while target.len() < path_len {
        target.push('x');
    }
    let bytes = encode_fields(&fields(&target, present), state);
    let result = decode_journal_for_test(&bytes, &target);
    assert!(
        result.is_ok(),
        "PRODUCT_RED IO-ADD-07 positive state={state} len={path_len} {result:?}"
    );
    let r = result.unwrap();
    assert_eq!(r.transaction_id, TX);
    assert_eq!(r.target_path, target);
    assert_eq!(r.state, state);
    assert_eq!(r.previous_digest, present.then(|| digest(OLD)));
    assert_eq!(r.new_digest, digest(NEW));
    if path_len == 4096 && present {
        assert_eq!(bytes.len(), 4390);
    }
}
macro_rules! valid_codecs { ($($name:ident:$state:expr,$present:expr,$length:expr,$multi:expr;)*) => {$ (#[test] fn $name(){codec_valid($state,$present,$length,$multi);})*}; }
valid_codecs! {
    gap_07_path_minimum_file:1,true,4,false;gap_07_prepared:1,true,30,false;gap_07_committed:2,true,30,false;gap_07_rolledback:3,true,30,false;
    gap_07_recovery:4,true,30,false;gap_07_absent:1,false,30,false;
    gap_07_path_4095:1,true,4095,false;gap_07_path_4096_max_record:1,true,4096,false;
    gap_07_multibyte_4096:1,true,4096,true;
}
fn size_case(path_len: usize, total: Option<usize>, expected: DecodeError) {
    let target = if path_len >= 3 {
        format!("C:\\{}", "x".repeat(path_len - 3))
    } else {
        "x".repeat(path_len)
    };
    let mut bytes = encode_fields(&fields(&target, true), 1);
    if let Some(size) = total {
        bytes.resize(size, 0);
    }
    let result = decode_journal_for_test(&bytes, &target);
    assert_eq!(
        result,
        Err(expected),
        "PRODUCT_RED IO-ADD-07 length boundary"
    );
}
#[test]
fn gap_07_path_empty() {
    size_case(0, None, DecodeError::Field);
}
#[test]
fn gap_07_path_4097() {
    size_case(4097, None, DecodeError::Field);
}
#[test]
fn gap_07_total_65535_not_valid_padding() {
    size_case(30, Some(65535), DecodeError::Framing);
}
#[test]
fn gap_07_total_65536_not_valid_padding() {
    size_case(30, Some(65536), DecodeError::Framing);
}

struct Probe {
    child: Child,
    lines: mpsc::Receiver<String>,
    started: Instant,
}
fn fixture_line(lines: &mpsc::Receiver<String>, wait: Duration) -> Result<String, &'static str> {
    lines.recv_timeout(wait).map_err(|e| match e {
        mpsc::RecvTimeoutError::Timeout => "FIXTURE_SETUP protocol timeout",
        mpsc::RecvTimeoutError::Disconnected => "FIXTURE_SETUP protocol disconnected",
    })
}
fn check_helper(path: &Path) -> Result<(), &'static str> {
    if path.is_file() {
        Ok(())
    } else {
        Err("FIXTURE_SETUP helper not built")
    }
}
impl Probe {
    fn spawn(f: &Fixture, mode: &str, point: Option<&str>) -> Self {
        let key = if point.is_some() {
            "FILE_COMMIT_CHECKPOINT_PROBE_PATH"
        } else {
            "FILE_COMMIT_PROBE_PATH"
        };
        let executable = std::env::var_os(key).expect("FIXTURE_SETUP missing helper");
        check_helper(Path::new(&executable)).expect("FIXTURE_SETUP helper validation");
        let mut command = Command::new(executable);
        if let Some(point) = point {
            command
                .args(["--exact", "checkpoint_probe_entry", "--nocapture"])
                .env("FILE_COMMIT_CHECKPOINT_ROOT", &f.root)
                .env("FILE_COMMIT_CHECKPOINT_POINT", point);
        } else {
            command.arg(mode).arg(&f.root).arg(f.sidecar());
        }
        let mut child = command
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .creation_flags(0x0800_0000)
            .spawn()
            .expect("FIXTURE_SETUP spawn");
        let stdout = child.stdout.take().unwrap();
        let (tx, lines) = mpsc::channel();
        std::thread::spawn(move || {
            for line in BufReader::new(stdout).lines() {
                let line = line.unwrap();
                if tx.send(line).is_err() {
                    break;
                }
            }
        });
        let mut p = Self {
            child,
            lines,
            started: Instant::now(),
        };
        assert_eq!(p.event(), "PROBE_STARTED");
        p
    }
    fn event(&mut self) -> String {
        loop {
            assert!(
                self.started.elapsed() < Duration::from_secs(15),
                "FIXTURE_SETUP child case deadline"
            );
            let line = fixture_line(&self.lines, Duration::from_secs(5))
                .expect("FIXTURE_SETUP missing protocol event, not RED");
            // Rust test harness may prefix output with the selected test name.
            for tag in ["PROBE_STARTED", "RESULT ", "LEASE_READY", "CHECKPOINT "] {
                if let Some(at) = line.find(tag) {
                    return line[at..].to_string();
                }
            }
        }
    }
    fn release(&mut self) {
        self.child
            .stdin
            .as_mut()
            .unwrap()
            .write_all(b"RELEASE\n")
            .unwrap();
    }
    fn wait_ok(&mut self) {
        let deadline = Instant::now() + Duration::from_secs(5);
        loop {
            if let Some(s) = self.child.try_wait().unwrap() {
                assert!(s.success(), "FIXTURE_SETUP child exit");
                break;
            }
            assert!(
                Instant::now() < deadline,
                "FIXTURE_SETUP child exit timeout"
            );
            std::thread::sleep(Duration::from_millis(5));
        }
    }
}
impl Drop for Probe {
    fn drop(&mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn reopen_case(kind: &str) {
    let f = Fixture::new();
    f.old();
    let mut state = 1;
    let mut present = true;
    match kind {
        "recovery" => state = 4,
        "committed" | "committed_mismatch" | "committed_bad_artifact" | "committed_foreign" => {
            state = 2
        }
        "rolledback" | "rolledback_mismatch" | "rolledback_missing_versions" => state = 3,
        "rolledback_absent" | "rolledback_absent_missing_versions" => {
            state = 3;
            present = false;
        }
        _ => {}
    }
    let bytes = encode_fields(&fields(&f.target(), present), state);
    f.journal(&bytes);
    if !present {
        fs::remove_file(f.target()).unwrap();
        fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
    }
    if [
        "committed",
        "committed_bad_artifact",
        "committed_foreign",
        "rolledback_mismatch",
    ]
    .contains(&kind)
    {
        fs::write(f.target(), NEW).unwrap();
    }
    if kind == "unknown" {
        let mut b = bytes.clone();
        b[9..13].copy_from_slice(&2u32.to_le_bytes());
        rewrite_checksum(&mut b);
        fs::write(f.tx_dir().join("journal.v1"), b).unwrap();
    }
    if kind == "missing" {
        fs::remove_file(f.tx_dir().join("journal.v1")).unwrap();
    }
    if kind == "next" {
        fs::write(f.tx_dir().join(format!("journal.next-{TX}")), b"partial").unwrap();
    }
    if ["foreign", "committed_foreign"].contains(&kind) {
        fs::write(f.tx_dir().join("foreign.keep"), b"FOREIGN").unwrap();
    }
    if ["bad_artifact", "committed_bad_artifact"].contains(&kind) {
        fs::write(f.tx_dir().join("new.bin"), b"FOREIGN").unwrap();
    }
    if kind == "terminal_missing_versions" {
        fs::write(f.target(), NEW).unwrap();
        fs::write(
            f.tx_dir().join("journal.v1"),
            encode_fields(&fields(&f.target(), true), 2),
        )
        .unwrap();
        fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
        fs::remove_file(f.tx_dir().join("new.bin")).unwrap();
    }
    if [
        "rolledback_missing_versions",
        "rolledback_absent_missing_versions",
    ]
    .contains(&kind)
    {
        if present {
            fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
        }
        fs::remove_file(f.tx_dir().join("new.bin")).unwrap();
    }
    drop(f.fixture_handle());
    let before = snapshot(&f.root);
    let mut probe = Probe::spawn(&f, "acquire-once", None);
    let result = probe.event();
    probe.wait_ok();
    let ok = [
        "committed",
        "rolledback",
        "rolledback_absent",
        "terminal_missing_versions",
        "rolledback_missing_versions",
        "rolledback_absent_missing_versions",
    ]
    .contains(&kind);
    assert!(
        if ok {
            result == "RESULT OK"
        } else {
            result.starts_with("RESULT ERROR RecoveryRequired")
        },
        "PRODUCT_RED IO-ADD-08 {kind} {result}"
    );
    assert_eq!(snapshot(&f.root), before);
}
macro_rules! reopen_cases { ($($name:ident:$kind:literal;)*) => {$ (#[test] fn $name(){reopen_case($kind);})*}; }
reopen_cases! {
    gap_08_prepared:"prepared";gap_08_recovery:"recovery";gap_08_unknown:"unknown";
    gap_08_missing_journal:"missing";gap_08_next_orphan:"next";gap_08_committed:"committed";
    gap_08_committed_mismatch:"committed_mismatch";gap_08_rolledback:"rolledback";
    gap_08_rolledback_absent:"rolledback_absent";gap_08_foreign:"foreign";
    gap_08_bad_artifact:"bad_artifact";gap_08_terminal_missing_versions:"terminal_missing_versions";
    gap_08_committed_bad_artifact:"committed_bad_artifact";gap_08_committed_foreign:"committed_foreign";
    gap_08_rolledback_mismatch:"rolledback_mismatch";
    gap_08_rolledback_missing_versions:"rolledback_missing_versions";
    gap_08_rolledback_absent_missing_versions:"rolledback_absent_missing_versions";
}
fn product_lifetime(kill: bool) {
    let f = Fixture::new();
    let mut holder = Probe::spawn(&f, "hold-product-lease", None);
    let result = holder.event();
    assert_eq!(
        result, "LEASE_READY",
        "PRODUCT_RED IO-ADD-09 actual product acquire: {result}"
    );
    let mut competitor = Probe::spawn(&f, "acquire-once", None);
    let busy = competitor.event();
    competitor.wait_ok();
    assert!(
        busy.starts_with("RESULT ERROR Busy"),
        "live product lease excludes child: {busy}"
    );
    if kill {
        holder.child.kill().unwrap();
        holder.child.wait().unwrap();
    } else {
        holder.release();
        assert_eq!(holder.event(), "RESULT OK");
        holder.wait_ok();
    }
    assert!(f.sidecar().exists());
    let mut next = Probe::spawn(&f, "acquire-once", None);
    assert_eq!(next.event(), "RESULT OK");
    next.wait_ok();
    assert!(f.sidecar().exists());
}
#[test]
fn gap_09_product_drop_allows_child() {
    product_lifetime(false);
}
#[test]
fn gap_09_product_death_allows_child() {
    product_lifetime(true);
}

fn cleanup_case(committed: bool) {
    let f = Fixture::new();
    f.old();
    fs::write(f.root.join("foreign.keep"), b"FOREIGN").unwrap();
    let terminal = Arc::new(Mutex::new(None));
    let hooks = TestCheckpoints {
        fail_at: if committed {
            vec![]
        } else {
            vec![CommitStage::VerifyPublished]
        },
        fault_points: vec!["cleanup.remove"],
        at_point: Some(terminal_observer(
            f.tx_dir().join("journal.v1"),
            if committed {
                "committed.verified"
            } else {
                "rolled_back.verified"
            },
            terminal.clone(),
        )),
        ..Default::default()
    };
    let consumed = hooks.consumed_points.clone();
    let mut lease = f.lease(hooks);
    let result = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        consumed
            .lock()
            .unwrap()
            .iter()
            .any(|v| v == "cleanup.remove"),
        "PRODUCT_RED IO-ADD-10 cleanup not consumed {result:?}"
    );
    if committed {
        assert!(result.is_ok());
        assert_eq!(fs::read(f.target()).unwrap(), NEW);
    } else {
        assert!(result.is_err());
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
    }
    let record = terminal.lock().unwrap();
    let verified = record
        .as_ref()
        .expect("terminal record must be verified before cleanup fault");
    assert_terminal_record(&f, verified, if committed { 2 } else { 3 }, true);
    assert_safe_terminal_layout(&f, verified, true);
    assert_eq!(fs::read(f.root.join("foreign.keep")).unwrap(), b"FOREIGN");
}
#[test]
fn gap_10_committed_cleanup_failure_stays_success() {
    cleanup_case(true);
}
#[test]
fn gap_10_rollback_cleanup_preserves_preimage() {
    cleanup_case(false);
}

fn invalid_name(name: &str) {
    let f = Fixture::new();
    let before = snapshot(&f.root);
    let result = StdFileCommit::new().create_directory_exclusive(f.root.to_str().unwrap(), name);
    assert!(
        matches!(&result, Err(CommitError::InvalidPath { .. })),
        "PRODUCT_RED IO-ADD-11 {name:?} {result:?}"
    );
    assert_eq!(snapshot(&f.root), before);
}
macro_rules! invalid_names { ($($name:ident:$value:literal;)*) => {$ (#[test] fn $name(){invalid_name($value);})*}; }
invalid_names! {
    gap_11_empty:"";gap_11_space:" ";gap_11_parent:"..";gap_11_traversal:"../outside";
    gap_11_forward:"a/b";gap_11_backslash:"a\\b";gap_11_reserved:"CON";gap_11_ads:"a:b";
    gap_11_trailing_space:"name ";gap_11_trailing_dot:"name.";
}
#[test]
fn gap_11_parent_missing() {
    let f = Fixture::new();
    let result = StdFileCommit::new()
        .create_directory_exclusive(f.root.join("missing").to_str().unwrap(), "new");
    assert!(
        matches!(&result,Err(CommitError::Storage{stage:CommitStage::CreateDirectory,reason,..}) if reason!="SKELETON_NOT_IMPLEMENTED"),
        "PRODUCT_RED IO-ADD-11 {result:?}"
    );
    assert!(!f.root.join("missing").exists());
}
fn existing_case(kind: &str) {
    let f = Fixture::new();
    match kind {
        "file" => f.old(),
        "empty" => fs::create_dir(f.root.join("document.ess")).unwrap(),
        _ => {
            fs::create_dir(f.root.join("document.ess")).unwrap();
            fs::write(f.root.join("document.ess/keep"), OLD).unwrap();
        }
    }
    let before = snapshot(&f.root);
    let result =
        StdFileCommit::new().create_directory_exclusive(f.root.to_str().unwrap(), "document.ess");
    assert!(
        matches!(&result, Err(CommitError::AlreadyExists { .. })),
        "PRODUCT_RED IO-ADD-11 {kind} {result:?}"
    );
    assert_eq!(snapshot(&f.root), before);
}
#[test]
fn gap_11_existing_file() {
    existing_case("file");
}
#[test]
fn gap_11_existing_empty_dir() {
    existing_case("empty");
}
#[test]
fn gap_11_existing_nonempty_dir() {
    existing_case("nonempty");
}

fn external_rollback(present: bool) {
    let f = Fixture::new();
    if present {
        f.old();
    }
    let target = f.target();
    let hooks = TestCheckpoints {
        fail_at: vec![CommitStage::VerifyPublished],
        at_point: Some(Arc::new(move |point| {
            if point == "restore.before" {
                fs::write(&target, b"THIRD-PARTY").unwrap();
            }
        })),
        ..Default::default()
    };
    let mut lease = f.lease(hooks);
    let old = present.then(|| digest(OLD));
    let result = lease.replace_checked(old.as_deref(), NEW);
    assert!(
        matches!(&result, Err(CommitError::RecoveryRequired { .. })),
        "PRODUCT_RED IO-ADD-12 {result:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), b"THIRD-PARTY");
}
#[test]
fn gap_12_rollback_preserves_external_replacement() {
    external_rollback(true);
}
#[test]
fn gap_12_absent_rollback_preserves_external_new_file() {
    external_rollback(false);
}

fn interruption(point: &str) {
    let f = Fixture::new();
    f.old();
    let mut p = Probe::spawn(&f, "commit-until-checkpoint", Some(point));
    let result = p.event();
    assert_eq!(
        result,
        format!("CHECKPOINT {point}"),
        "PRODUCT_RED IO-ADD-13 checkpoint not reached: {result}"
    );
    p.child.kill().unwrap();
    p.child.wait().unwrap();
    let before = snapshot(&f.root);
    let mut reopen = Probe::spawn(&f, "acquire-once", None);
    let status = reopen.event();
    reopen.wait_ok();
    if ["committed.verified", "cleanup.before"].contains(&point) {
        assert_eq!(status, "RESULT OK");
        assert_eq!(fs::read(f.target()).unwrap(), NEW);
    } else {
        assert!(status.starts_with("RESULT ERROR RecoveryRequired"));
        assert!(f.tx_dir().join("new.bin").exists());
    }
    assert_eq!(snapshot(&f.root), before);
}
macro_rules! interruptions { ($($name:ident:$point:literal;)*) => {$ (#[test] fn $name(){interruption($point);})*}; }
interruptions! {gap_13_new_synced:"new.synced";gap_13_prepared:"prepared.verified";gap_13_published:"target.published";gap_13_committed:"committed.verified";gap_13_cleanup:"cleanup.before";}

#[test]
fn gap_14_fixture_collision_retry_support() {
    let parent = Fixture::new();
    let base = parent.base.clone();
    let taken = parent.owner.clone();
    let name = format!("{taken}-next");
    let mut calls = 0;
    let second = Fixture::exclusive(base, || {
        calls += 1;
        if calls == 1 {
            taken.clone()
        } else {
            name.clone()
        }
    });
    assert_eq!(calls, 2);
    assert_eq!(second.owner, name);
    assert!(parent.root.exists());
}
#[test]
fn gap_14_fixture_retry_exhaustion_support() {
    let f = Fixture::new();
    let result =
        std::panic::catch_unwind(|| Fixture::exclusive(f.base.clone(), || f.owner.clone()));
    let error = result.err().expect("must classify exhausted fixture setup");
    let message = error
        .downcast_ref::<String>()
        .map(String::as_str)
        .or_else(|| error.downcast_ref::<&str>().copied())
        .expect("fixture panic payload must be text");
    assert!(message.contains("FIXTURE_SETUP exclusive fixture retry exhausted"));
    assert!(f.root.exists());
}
#[test]
fn gap_14_fixed_clock_parallel_names_support() {
    let mut handles = Vec::new();
    for _ in 0..16 {
        handles.push(std::thread::spawn(|| Fixture::at_stamp(123456)));
    }
    let fixtures: Vec<_> = handles.into_iter().map(|h| h.join().unwrap()).collect();
    let names: std::collections::BTreeSet<_> = fixtures.iter().map(|f| f.owner.clone()).collect();
    assert_eq!(names.len(), 16);
}
#[test]
fn gap_14_v1_encoder_support() {
    let bytes = encode_fields(&fields(r"C:\fixture\document.ess", true), 1);
    assert_eq!(
        assert_fixture_record(&bytes, r"C:\fixture\document.ess", 1),
        TX
    );
    let mut changed = bytes.clone();
    changed[9] = 2;
    let n = changed.len() - 64;
    assert_ne!(&changed[n..], source_sha256(&changed[..n]).as_bytes());
}
#[test]
fn gap_14_helper_health_support() {
    let helper = std::env::var_os("FILE_COMMIT_PROBE_PATH").expect("FIXTURE_SETUP helper");
    let output = Command::new(helper)
        .arg("health")
        .creation_flags(0x0800_0000)
        .output()
        .unwrap();
    assert!(output.status.success());
    assert_eq!(
        String::from_utf8(output.stdout).unwrap().trim(),
        "FIXTURE_HELPER_OK"
    );
}

// Independent public-Port rows: parser failures never mask these preservation assertions.
macro_rules! acquisitions {
    ($($name:ident:$kind:literal;)*) => {$ (#[test] fn $name(){acquisition_invalid($kind);})*};
}
acquisitions! {
    gap_06_acquire_magic:"magic";gap_06_acquire_version:"version";gap_06_acquire_checksum:"checksum";
    gap_06_acquire_truncated:"truncated";gap_06_acquire_trailing:"trailing";
    gap_06_acquire_overflow:"overflow";gap_06_acquire_payload_length:"length";
    gap_06_acquire_field_length:"field_length";gap_06_acquire_utf8:"utf8";
    gap_06_acquire_nul:"nul";gap_06_acquire_bom:"bom";gap_06_acquire_state:"state";
    gap_06_acquire_txid:"txid";gap_06_acquire_digest:"digest";
    gap_06_acquire_old_pair:"old_pair";gap_06_acquire_extra_field:"extra_field";
    gap_06_acquire_binding:"binding";gap_06_acquire_traversal:"relative";
    gap_06_acquire_old_traversal:"old_relative";gap_06_acquire_absolute:"absolute";
    gap_06_acquire_unc:"unc";gap_06_acquire_device:"device";
    gap_06_acquire_ads:"ads";gap_06_acquire_drive:"drive";gap_06_acquire_oversize:"oversize";
}

#[test]
fn gap_07_path_one_byte_cannot_be_absolute_file() {
    size_case(1, None, DecodeError::Field);
}

fn collision_case(journal: bool) {
    let f = Fixture::new();
    f.old();
    let directory = if journal {
        fs::create_dir(f.tx_dir()).unwrap();
        f.tx_dir()
    } else {
        f.root.clone()
    };
    let foreign = directory.join(if journal {
        format!("journal.next-{TX}")
    } else {
        "foreign.tmp".into()
    });
    fs::write(&foreign, b"FOREIGN-COLLISION").unwrap();
    let owned = directory.join(if journal {
        "journal.next-fedcba9876543210fedcba9876543210"
    } else {
        "owned.tmp"
    });
    let candidates = vec![
        foreign.to_str().unwrap().into(),
        owned.to_str().unwrap().into(),
    ];
    let hooks = if journal {
        TestCheckpoints {
            journal_candidates: candidates,
            ..Default::default()
        }
    } else {
        TestCheckpoints {
            temp_candidates: candidates,
            ..Default::default()
        }
    };
    let mut lease = f.lease(hooks);
    let result = lease.replace_checked(Some(&digest(OLD)), NEW);
    // An unknown transaction area must fail closed, not silently remove the colliding file.
    if journal {
        assert!(
            matches!(&result, Err(CommitError::RecoveryRequired { .. })),
            "PRODUCT_RED IO-ADD-10 journal collision {result:?}"
        );
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
    } else {
        assert!(
            result.is_ok(),
            "PRODUCT_RED IO-ADD-10 owned temp retry {result:?}"
        );
        assert_eq!(fs::read(f.target()).unwrap(), NEW);
    }
    assert_eq!(fs::read(foreign).unwrap(), b"FOREIGN-COLLISION");
}
#[test]
fn gap_10_temp_collision_foreign_kept() {
    collision_case(false);
}
#[test]
fn gap_10_orphan_next_collision_fails_closed() {
    collision_case(true);
}

#[test]
fn gap_10_active_journal_next_collision_never_deletes_foreign() {
    let f = Fixture::new();
    f.old();
    let foreign = f.tx_dir().join(format!("journal.next-{TX}"));
    let path = foreign.clone();
    let hooks = TestCheckpoints {
        journal_candidates: vec![foreign.to_str().unwrap().into()],
        at_point: Some(Arc::new(move |point| {
            if point == "prepared.before_create_next" {
                // Simulates an independent creator after the area was prepared, before create_new.
                fs::write(&path, b"FOREIGN-COLLISION").unwrap();
            }
        })),
        ..Default::default()
    };
    let observed = hooks.observed_points.clone();
    let mut lease = f.lease(hooks);
    let result = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        observed
            .lock()
            .unwrap()
            .iter()
            .any(|p| p == "prepared.before_create_next"),
        "PRODUCT_RED IO-ADD-10 journal create checkpoint {result:?}"
    );
    assert!(result.is_err());
    assert_eq!(fs::read(foreign).unwrap(), b"FOREIGN-COLLISION");
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}

#[test]
fn gap_12_prepare_external_edit_preserved() {
    let f = Fixture::new();
    f.old();
    let path = f.target();
    let hooks = TestCheckpoints {
        before_publish: Some(Arc::new(move || {
            fs::write(&path, b"EXTERNAL-CHANGE").unwrap();
        })),
        ..Default::default()
    };
    let mut lease = f.lease(hooks);
    let result = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        matches!(&result,Err(CommitError::Conflict{expected:Some(e),observed:Some(o)}) if *e==digest(OLD) && *o==digest(b"EXTERNAL-CHANGE")),
        "PRODUCT_RED IO-ADD-12 recheck {result:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), b"EXTERNAL-CHANGE");
}

#[test]
fn gap_01_expected_absent_actual_present_digests() {
    let f = Fixture::new();
    f.old();
    let mut lease = f.lease(Default::default());
    let result = lease.replace_checked(None, NEW);
    assert!(
        matches!(&result,Err(CommitError::Conflict{expected:None,observed:Some(o)}) if *o==digest(OLD)),
        "PRODUCT_RED IO-ADD-01 {result:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}

#[test]
fn gap_01_empty_file_is_present_not_absent() {
    let f = Fixture::new();
    fs::write(f.target(), []).unwrap();
    let mut lease = f.lease(Default::default());
    let result = lease.replace_checked(None, NEW);
    assert!(
        matches!(&result,Err(CommitError::Conflict{expected:None,observed:Some(o)}) if *o==digest(&[])),
        "PRODUCT_RED IO-ADD-01 empty file {result:?}"
    );
    assert_eq!(fs::read(f.target()).unwrap(), b"");
}

#[test]
fn gap_02_read_absent_exactly_none() {
    let f = Fixture::new();
    let lease = f.lease(Default::default());
    assert_eq!(lease.read_current(), Ok(None), "PRODUCT_RED read absent");
}
#[test]
fn gap_02_read_empty_exactly_some_empty() {
    let f = Fixture::new();
    fs::write(f.target(), []).unwrap();
    let lease = f.lease(Default::default());
    assert_eq!(
        lease.read_current(),
        Ok(Some(vec![])),
        "PRODUCT_RED read empty"
    );
}

#[test]
fn gap_14_v1_maximum_field_vector_support() {
    let target = format!("C:\\{}", "x".repeat(4093));
    let bytes = encode_fields(&fields(&target, true), 1);
    assert_eq!(target.len(), 4096);
    assert_eq!(bytes.len(), 4390);
    assert_eq!(assert_fixture_record(&bytes, &target, 1), TX);
    assert_eq!(&bytes[9..13], &1u32.to_le_bytes());
    let length = u32::from_le_bytes(bytes[13..17].try_into().unwrap()) as usize;
    assert_eq!(17 + length + 64, 4390);
}

#[test]
fn gap_14_mutation_fixtures_preserve_checksum_support() {
    for kind in [
        "version",
        "binding",
        "relative",
        "old_relative",
        "absolute",
        "unc",
        "device",
        "ads",
        "drive",
        "state",
        "digest",
        "txid",
        "utf8",
        "nul",
        "bom",
        "old_pair",
        "extra_field",
        "overflow",
        "length",
        "field_length",
    ] {
        let (bytes, _) = malformed_record(kind, r"C:\fixture\document.ess");
        let n = bytes.len() - 64;
        assert_eq!(
            &bytes[n..],
            source_sha256(&bytes[..n]).as_bytes(),
            "fixture mutation must not merely test checksum: {kind}"
        );
    }
    let (bytes, _) = malformed_record("version", r"C:\fixture\document.ess");
    assert_eq!(u32::from_le_bytes(bytes[9..13].try_into().unwrap()), 2);
    let (bytes, _) = malformed_record("field_length", r"C:\fixture\document.ess");
    assert_eq!(
        u32::from_le_bytes(bytes[17..21].try_into().unwrap()),
        u32::MAX
    );
}

#[test]
fn gap_14_owned_native_handle_release_support() {
    let f = Fixture::new();
    let mut child = ChildFixture::hold(&f);
    assert!(OpenOptions::new()
        .read(true)
        .write(true)
        .share_mode(0)
        .open(f.sidecar())
        .is_err());
    child.release();
    let handle = OpenOptions::new()
        .read(true)
        .write(true)
        .share_mode(0)
        .open(f.sidecar())
        .unwrap();
    drop(handle);
    let mut dead = ChildFixture::hold(&f);
    dead.kill_and_wait();
    let handle = OpenOptions::new()
        .read(true)
        .write(true)
        .share_mode(0)
        .open(f.sidecar())
        .unwrap();
    drop(handle);
    assert!(f.sidecar().exists());
}

recoveries! {
    gap_04_commit_rollback_record_write_old:true,WriteCommittedJournal,WriteCommittedJournal,"rolled_back.write";
    gap_04_commit_rollback_record_write_absent:false,WriteCommittedJournal,WriteCommittedJournal,"rolled_back.write";
    gap_04_commit_rollback_record_sync_old:true,WriteCommittedJournal,WriteCommittedJournal,"rolled_back.sync";
    gap_04_commit_rollback_record_sync_absent:false,WriteCommittedJournal,WriteCommittedJournal,"rolled_back.sync";
    gap_04_commit_rollback_record_publish_old:true,WriteCommittedJournal,WriteCommittedJournal,"rolled_back.publish";
    gap_04_commit_rollback_record_publish_absent:false,WriteCommittedJournal,WriteCommittedJournal,"rolled_back.publish";
    gap_04_commit_rollback_record_verify_old:true,WriteCommittedJournal,VerifyRestored,"rolled_back.verify";
    gap_04_commit_rollback_record_verify_absent:false,WriteCommittedJournal,VerifyRestored,"rolled_back.verify";
}

#[test]
fn gap_07_multibyte_4097_rejected_by_byte_count() {
    let target = format!("C:\\{}xx", "界".repeat(1364));
    assert_eq!(target.len(), 4097);
    let bytes = encode_fields(&fields(&target, true), 1);
    assert_eq!(
        decode_journal_for_test(&bytes, &target),
        Err(DecodeError::Field),
        "PRODUCT_RED IO-ADD-07 multibyte byte limit"
    );
}

#[test]
fn gap_10_prepare_cleanup_fault_preserves_formal_and_foreign() {
    let f = Fixture::new();
    f.old();
    fs::write(f.root.join("foreign.keep"), b"FOREIGN").unwrap();
    let hooks = TestCheckpoints {
        fail_at: vec![CommitStage::PrepareNew],
        fault_points: vec!["cleanup.remove"],
        ..Default::default()
    };
    let consumed = hooks.consumed_points.clone();
    let mut lease = f.lease(hooks);
    let result = lease.replace_checked(Some(&digest(OLD)), NEW);
    assert!(
        consumed
            .lock()
            .unwrap()
            .iter()
            .any(|p| p == "cleanup.remove"),
        "PRODUCT_RED IO-ADD-10 prepublish cleanup not consumed {result:?}"
    );
    assert!(result.is_err());
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(f.root.join("foreign.keep")).unwrap(), b"FOREIGN");
}

#[test]
fn gap_11_traversal_cannot_create_in_another_owned_root() {
    let f = Fixture::new();
    let outside = Fixture::new();
    fs::write(outside.root.join("sentinel"), OLD).unwrap();
    let before = snapshot(&outside.root);
    let name = format!("../{}/intrusion", outside.owner);
    let result = StdFileCommit::new().create_directory_exclusive(f.root.to_str().unwrap(), &name);
    assert!(
        matches!(&result, Err(CommitError::InvalidPath { .. })),
        "PRODUCT_RED IO-ADD-11 cross-root {result:?}"
    );
    assert_eq!(snapshot(&outside.root), before);
}

#[test]
fn gap_14_missing_helper_classified_as_fixture_failure_support() {
    let f = Fixture::new();
    assert_eq!(
        check_helper(&f.root.join("missing-helper.exe")),
        Err("FIXTURE_SETUP helper not built")
    );
}
#[test]
fn gap_14_protocol_timeout_classified_as_fixture_failure_support() {
    let (_tx, rx) = mpsc::channel::<String>();
    assert_eq!(
        fixture_line(&rx, Duration::ZERO),
        Err("FIXTURE_SETUP protocol timeout")
    );
}
#[test]
fn gap_14_protocol_disconnect_classified_as_fixture_failure_support() {
    let (tx, rx) = mpsc::channel::<String>();
    drop(tx);
    assert_eq!(
        fixture_line(&rx, Duration::ZERO),
        Err("FIXTURE_SETUP protocol disconnected")
    );
}
#[test]
fn gap_14_nonzero_helper_is_fixture_failure_support() {
    let executable = std::env::var_os("FILE_COMMIT_PROBE_PATH").unwrap();
    let output = Command::new(executable)
        .arg("invalid-fixture-mode")
        .creation_flags(0x0800_0000)
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(70));
    assert!(String::from_utf8(output.stderr)
        .unwrap()
        .contains("FIXTURE_ERROR"));
    assert!(!String::from_utf8(output.stdout).unwrap().contains("RESULT"));
}

fn verified_prepared_diagnostics(present: bool) {
    let f = Fixture::new();
    if present {
        f.old();
    }
    f.journal(&encode_fields(&fields(&f.target(), present), 1));
    if !present {
        fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
    }
    drop(f.fixture_handle());
    let before = snapshot(&f.root);
    let result = StdFileCommit::new().acquire_write(&f.target());
    assert!(
        matches!(&result, Err(CommitError::RecoveryRequired { .. })),
        "PRODUCT_RED IO-A-R3 valid prepared record {:?}",
        result.as_ref().err()
    );
    if let Err(CommitError::RecoveryRequired {
        target_path,
        journal_path,
        old_version_path,
        new_version_path,
        reason,
    }) = result
    {
        assert_eq!(target_path, f.target());
        assert_eq!(PathBuf::from(journal_path), f.tx_dir().join("journal.v1"));
        assert!(!reason.is_empty());
        let expected_old =
            present.then(|| f.tx_dir().join("old.bin").to_string_lossy().into_owned());
        assert_eq!(old_version_path, expected_old);
        assert_eq!(
            PathBuf::from(new_version_path.unwrap()),
            f.tx_dir().join("new.bin")
        );
        if let Some(old) = old_version_path {
            assert_eq!(fs::read(old).unwrap(), OLD);
        }
        assert_eq!(fs::read(f.tx_dir().join("new.bin")).unwrap(), NEW);
    }
    assert_eq!(snapshot(&f.root), before);
}
#[test]
fn gap_06_verified_prepared_diagnostics_old() {
    verified_prepared_diagnostics(true);
}
#[test]
fn gap_06_verified_prepared_diagnostics_absent() {
    verified_prepared_diagnostics(false);
}

// Fixture-level counterexamples from independent acceptance: these must PASS.
// They validate the assertions, not actual product rollback/cleanup behavior.
fn terminal_layout_fixture(present: bool) -> (Fixture, Vec<u8>) {
    let f = Fixture::new();
    if present {
        f.old();
    }
    let record = encode_fields(&fields(&f.target(), present), 3);
    f.journal(&record);
    if !present {
        fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
    }
    assert_terminal_record(&f, &record, 3, present);
    (f, record)
}
fn completed_rollback_layout(present: bool) {
    let (f, record) = terminal_layout_fixture(present);
    if present {
        fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
    }
    fs::remove_file(f.tx_dir().join("new.bin")).unwrap();
    fs::remove_file(f.tx_dir().join("journal.v1")).unwrap();
    assert_safe_terminal_layout(&f, &record, present);
    if present {
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
    } else {
        assert!(!Path::new(&f.target()).exists());
    }
}
#[test]
fn gap_14_complete_rollback_cleanup_old_support() {
    completed_rollback_layout(true);
}
#[test]
fn gap_14_complete_rollback_cleanup_absent_support() {
    completed_rollback_layout(false);
}
#[test]
fn gap_14_partial_rollback_old_removed_support() {
    let (f, record) = terminal_layout_fixture(true);
    fs::remove_file(f.tx_dir().join("old.bin")).unwrap();
    assert_safe_terminal_layout(&f, &record, true);
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(f.tx_dir().join("new.bin")).unwrap(), NEW);
}
#[test]
fn gap_14_partial_rollback_new_removed_support() {
    let (f, record) = terminal_layout_fixture(true);
    fs::remove_file(f.tx_dir().join("new.bin")).unwrap();
    assert_safe_terminal_layout(&f, &record, true);
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(f.tx_dir().join("old.bin")).unwrap(), OLD);
}
#[test]
fn gap_14_corrupt_remaining_version_rejected_support() {
    let (f, record) = terminal_layout_fixture(true);
    fs::write(f.tx_dir().join("new.bin"), b"UNVERIFIED").unwrap();
    assert!(std::panic::catch_unwind(|| assert_safe_terminal_layout(&f, &record, true)).is_err());
    assert_eq!(fs::read(f.tx_dir().join("new.bin")).unwrap(), b"UNVERIFIED");
}
#[test]
fn gap_14_premature_journal_deletion_rejected_support() {
    let (f, record) = terminal_layout_fixture(true);
    fs::remove_file(f.tx_dir().join("journal.v1")).unwrap();
    assert!(std::panic::catch_unwind(|| assert_safe_terminal_layout(&f, &record, true)).is_err());
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}
#[test]
fn gap_14_unparsed_version_diagnostics_rejected_support() {
    let f = Fixture::new();
    for kind in [
        "magic",
        "version",
        "checksum",
        "truncated",
        "trailing",
        "overflow",
        "length",
        "field_length",
        "oversize",
    ] {
        assert_invalid_diagnostics(&f, kind, &None, &None);
        let old = Some(f.tx_dir().join("old.bin").to_str().unwrap().into());
        let new = Some(f.tx_dir().join("new.bin").to_str().unwrap().into());
        assert!(
            std::panic::catch_unwind(|| assert_invalid_diagnostics(&f, kind, &old, &new)).is_err(),
            "safe-looking unverified paths must fail diagnostic assertion: {kind}"
        );
    }
}

#[test]
fn implementation_partial_publish_temp_is_owned_and_cleaned() {
    for point in ["target.write", "target.sync"] {
        let f = Fixture::new(); f.old();
        let mut lease = f.lease(TestCheckpoints { fault_points: vec![point], ..Default::default() });
        let result = lease.replace_checked(Some(&digest(OLD)), NEW);
        assert!(matches!(result, Err(CommitError::Storage { stage: CommitStage::Publish, .. })), "{point}: {result:?}");
        assert_eq!(fs::read(f.target()).unwrap(), OLD);
        let leftovers: Vec<_> = fs::read_dir(&f.root).unwrap().map(|e| e.unwrap().file_name()).filter(|n| n.to_string_lossy().starts_with(".eluslot-publish-")).collect();
        assert!(leftovers.is_empty(), "owned publish artifacts must be cleaned after verified rollback: {leftovers:?}");
    }
}

#[test]
fn implementation_same_lease_can_commit_again_with_latest_digest() {
    let f = Fixture::new();
    let mut lease = StdFileCommit::new().acquire_write(&f.target()).unwrap();
    let first = lease.replace_checked(None, OLD).unwrap();
    let second = lease.replace_checked(Some(&first.committed_digest), NEW).unwrap();
    assert_ne!(first.transaction_id, second.transaction_id);
    assert_eq!(second.previous_digest, Some(digest(OLD)));
    assert_eq!(lease.read_current().unwrap(), Some(NEW.to_vec()));
    drop(lease);
    assert!(StdFileCommit::new().acquire_write(&f.target()).is_ok());
}

#[test]
fn implementation_hard_link_target_is_refused_without_content_change() {
    let f = Fixture::new(); f.old();
    let alias = f.root.join("alias.ess");
    fs::hard_link(f.target(), &alias).expect("native fixture requires hard-link support");
    assert!(StdFileCommit::new().acquire_write(alias.to_str().unwrap()).is_err());
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
    assert_eq!(fs::read(&alias).unwrap(), OLD);
    assert!(!f.tx_dir().exists());
}

#[test]
fn implementation_case_alias_is_conservatively_refused() {
    let f = Fixture::new(); f.old();
    let alias = f.root.join("DOCUMENT.ESS");
    assert!(matches!(StdFileCommit::new().acquire_write(alias.to_str().unwrap()), Err(CommitError::InvalidPath { .. })), "uncertain alias must not establish a second target identity");
    assert_eq!(fs::read(f.target()).unwrap(), OLD);
}

#[test]
fn implementation_prepare_failure_with_external_edit_is_not_ordinary_storage() {
    let f = Fixture::new(); f.old(); let target = f.target();
    let mut lease = f.lease(TestCheckpoints {
        fault_points: vec!["new.sync"],
        at_point: Some(Arc::new(move |point| { if point == "new.sync" { fs::write(&target, b"EXTERNAL").unwrap(); } })),
        ..Default::default()
    });
    assert!(matches!(lease.replace_checked(Some(&digest(OLD)), NEW), Err(CommitError::RecoveryRequired { .. })), "ordinary failure requires confirmed original state");
    assert_eq!(fs::read(f.target()).unwrap(), b"EXTERNAL");
    assert!(f.tx_dir().join("old.bin").exists(), "uncertain failure must retain preimage");
}
