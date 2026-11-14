//! IO-PREREQ Windows single-file commit adapter, approved journal protocol A.

use sgenaxis_ports::{CommitError, CommitReceipt, CommitStage, FileCommitPort, FileWriteLease};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::os::windows::fs::{MetadataExt, OpenOptionsExt};
use std::path::{Path, PathBuf};

#[derive(Debug, Default, Clone, Copy)]
pub struct StdFileCommit;

impl StdFileCommit {
    pub fn new() -> Self {
        Self
    }
}

impl FileCommitPort for StdFileCommit {
    fn create_directory_exclusive(
        &self,
        parent: &str,
        single_name: &str,
    ) -> Result<String, CommitError> {
        create_directory(parent, single_name)
    }

    fn acquire_write(&self, path: &str) -> Result<Box<dyn FileWriteLease>, CommitError> {
        Ok(Box::new(acquire(path)?))
    }
}

/// The owned native sidecar handle is held for the entire lease lifetime.
pub(crate) struct StdFileWriteLease {
    /// Internally-canonicalized absolute target used for all filesystem ops and
    /// the private journal.
    target_path: String,
    /// The exact path string the caller passed to `acquire_write`. The commit
    /// receipt echoes THIS verbatim so the Port contract — "the receipt reports
    /// the target you asked me to write" — holds regardless of how the adapter
    /// canonicalizes internally (e.g. Windows `\\?\` extended-length prefix).
    requested_path: String,
    _lock_handle: std::fs::File,
    blocked: bool,
    #[cfg(test)]
    _checkpoints: TestCheckpoints,
}

impl FileWriteLease for StdFileWriteLease {
    fn read_current(&self) -> Result<Option<Vec<u8>>, CommitError> {
        read_optional(Path::new(&self.target_path))
    }

    fn replace_checked(
        &mut self,
        expected_digest: Option<&str>,
        bytes: &[u8],
    ) -> Result<CommitReceipt, CommitError> {
        self.replace(expected_digest, bytes)
    }
}

// Private journal protocol A; no persistence representation escapes the Port.
#[allow(dead_code)]
#[derive(Debug, Clone, PartialEq, Eq)]
enum JournalState {
    Prepared,
    Committed,
    RolledBack,
    RecoveryRequired,
}

#[allow(dead_code)]
#[derive(Debug, Clone, PartialEq, Eq)]
struct JournalRecord {
    version: u32,
    transaction_id: String,
    target_path: String,
    previous_digest: Option<String>,
    new_digest: String,
    old_version_relative: Option<String>,
    new_version_relative: String,
    state: JournalState,
}

/// Internal fault-injection seam, absent from the shipping crate interface.
/// Callbacks observe the same transaction used by the shipping adapter.
#[cfg(test)]
#[derive(Clone, Default)]
#[allow(dead_code)]
pub(crate) struct TestCheckpoints {
    pub fail_at: Vec<CommitStage>,
    pub observed: std::sync::Arc<std::sync::Mutex<Vec<CommitStage>>>,
    pub before_publish: Option<std::sync::Arc<dyn Fn() + Send + Sync>>,
    pub temp_candidates: Vec<String>,
    pub journal_candidates: Vec<String>,
    pub consumed: std::sync::Arc<std::sync::Mutex<Vec<CommitStage>>>,
    pub fault_points: Vec<&'static str>,
    pub observed_points: std::sync::Arc<std::sync::Mutex<Vec<String>>>,
    pub consumed_points: std::sync::Arc<std::sync::Mutex<Vec<String>>>,
    pub at_point: Option<std::sync::Arc<dyn Fn(&str) + Send + Sync>>,
}

// Private decoding error model, projected through a test-only probe below.
#[derive(Debug, Clone, PartialEq, Eq)]
#[allow(dead_code)]
pub(crate) enum JournalDecodeError {
    SkeletonNotImplemented,
    Size,
    Framing,
    Version,
    Checksum,
    Text,
    Field,
    State,
    Binding,
    RelativePath,
}

#[cfg(test)]
#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct JournalProbe {
    pub transaction_id: String,
    pub target_path: String,
    pub previous_digest: Option<String>,
    pub new_digest: String,
    pub state: u8,
}

#[cfg(test)]
pub(crate) fn decode_journal_for_test(
    bytes: &[u8],
    expected_target: &str,
) -> Result<JournalProbe, JournalDecodeError> {
    decode(bytes, expected_target).map(|r| JournalProbe {
        transaction_id: r.transaction_id,
        target_path: r.target_path,
        previous_digest: r.previous_digest,
        new_digest: r.new_digest,
        state: match r.state {
            JournalState::Prepared => 1,
            JournalState::Committed => 2,
            JournalState::RolledBack => 3,
            JournalState::RecoveryRequired => 4,
        },
    })
}

#[cfg(test)]
impl StdFileCommit {
    // Private consumer entry for deterministic process-death checkpoints.
    pub(crate) fn acquire_with_checkpoints(
        &self,
        path: &str,
        checkpoints: TestCheckpoints,
    ) -> Result<Box<dyn FileWriteLease>, CommitError> {
        let mut lease = acquire(path)?;
        lease._checkpoints = checkpoints;
        Ok(Box::new(lease))
    }
}

#[cfg(test)]
impl StdFileWriteLease {
    /// Data/ownership constructor for tests that independently establish the
    /// handle precondition; not a public way to bypass product acquisition.
    pub(crate) fn for_test(
        target_path: String,
        handle: std::fs::File,
        checkpoints: TestCheckpoints,
    ) -> Self {
        Self {
            requested_path: target_path.clone(),
            target_path,
            _lock_handle: handle,
            blocked: false,
            _checkpoints: checkpoints,
        }
    }
}

fn digest(bytes: &[u8]) -> String {
    format!("sha256:{}", sgenaxis_spec::packet::source_sha256(bytes))
}
fn storage(stage: CommitStage, path: &Path, error: impl std::fmt::Display) -> CommitError {
    CommitError::Storage {
        stage,
        path: path.to_string_lossy().into_owned(),
        reason: error.to_string(),
    }
}
fn invalid(reason: &str) -> CommitError {
    CommitError::InvalidPath {
        reason: reason.into(),
    }
}
fn area(target: &str) -> PathBuf {
    PathBuf::from(format!("{target}.eluslot-commit"))
}
fn safe_name(name: &str) -> bool {
    if name.is_empty()
        || name.trim() != name
        || name.ends_with('.')
        || name
            .chars()
            .any(|c| c < ' ' || c == '\u{feff}' || "<>:\"/\\|?*".contains(c))
        || name == "."
        || name == ".."
    {
        return false;
    }
    let stem = name.split('.').next().unwrap_or("").to_uppercase();
    !matches!(
        stem.as_str(),
        "CON" | "PRN" | "AUX" | "NUL" | "CONIN$" | "CONOUT$"
    ) && !(stem.starts_with("COM") || stem.starts_with("LPT"))
        .then(|| &stem[3..])
        .map(|n| {
            matches!(
                n,
                "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9" | "¹" | "²" | "³"
            )
        })
        .unwrap_or(false)
}
fn local_absolute(path: &str) -> bool {
    let p = path.strip_prefix("\\\\?\\").unwrap_or(path).as_bytes();
    p.len() >= 3
        && p[0].is_ascii_alphabetic()
        && p[1] == b':'
        && p[2] == b'\\'
        && !p[3..].contains(&b':')
}
fn check_ancestors(path: &Path) -> Result<(), CommitError> {
    for p in path.ancestors() {
        if let Ok(m) = fs::symlink_metadata(p) {
            if m.file_attributes() & 0x400 != 0 {
                return Err(invalid("reparse paths are not accepted"));
            }
        }
    }
    Ok(())
}
#[allow(unsafe_code)]
fn regular_identity(file: &File) -> std::io::Result<()> {
    use std::os::windows::io::AsRawHandle;
    use windows_sys::Win32::Storage::FileSystem::{
        GetFileInformationByHandle, BY_HANDLE_FILE_INFORMATION,
    };
    let mut info: BY_HANDLE_FILE_INFORMATION = unsafe { std::mem::zeroed() };
    if unsafe { GetFileInformationByHandle(file.as_raw_handle(), &mut info) } == 0 {
        return Err(std::io::Error::last_os_error());
    }
    if info.dwFileAttributes & (0x400 | 0x10) != 0 || info.nNumberOfLinks != 1 {
        return Err(std::io::Error::other(
            "file identity is not a single regular non-reparse file",
        ));
    }
    Ok(())
}
fn open_read(path: &Path) -> std::io::Result<File> {
    let f = OpenOptions::new()
        .read(true)
        .share_mode(7)
        .custom_flags(0x00200000)
        .open(path)?;
    regular_identity(&f)?;
    Ok(f)
}
fn read_optional(path: &Path) -> Result<Option<Vec<u8>>, CommitError> {
    let mut f = match open_read(path) {
        Ok(f) => f,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(storage(CommitStage::Read, path, e)),
    };
    let mut b = Vec::new();
    f.read_to_end(&mut b)
        .map_err(|e| storage(CommitStage::Read, path, e))?;
    Ok(Some(b))
}
fn read_journal(path: &Path) -> Result<Vec<u8>, CommitError> {
    let f = open_read(path).map_err(|e| storage(CommitStage::Read, path, e))?;
    let mut bytes = Vec::new();
    f.take(65537)
        .read_to_end(&mut bytes)
        .map_err(|e| storage(CommitStage::Read, path, e))?;
    Ok(bytes)
}
fn normalize_target(path: &str) -> Result<String, CommitError> {
    if !local_absolute(path) {
        return Err(invalid("absolute local Windows path required"));
    }
    let p = Path::new(path);
    let name = p
        .file_name()
        .and_then(|n| n.to_str())
        .ok_or_else(|| invalid("missing UTF-8 filename"))?;
    if !safe_name(name) {
        return Err(invalid("unsafe filename"));
    }
    let parent = p.parent().ok_or_else(|| invalid("missing parent"))?;
    check_ancestors(parent)?;
    let parent = parent
        .canonicalize()
        .map_err(|e| storage(CommitStage::Acquire, parent, e))?;
    check_ancestors(&parent)?;
    let target = parent.join(name);
    if let Ok(m) = fs::symlink_metadata(&target) {
        if m.file_attributes() & (0x400 | 0x10) != 0 {
            return Err(invalid("target is not a regular file"));
        }
        let resolved = target
            .canonicalize()
            .map_err(|e| storage(CommitStage::Acquire, &target, e))?;
        if resolved.as_os_str() != target.as_os_str() {
            return Err(invalid("non-canonical target alias is not accepted"));
        }
    }
    let target = target
        .to_str()
        .ok_or_else(|| invalid("UTF-8 path required"))?;
    if target.len() > 4096 || target.contains('\u{feff}') {
        return Err(invalid("target exceeds journal path bounds"));
    }
    Ok(target.into())
}
fn create_directory(parent: &str, name: &str) -> Result<String, CommitError> {
    if !local_absolute(parent) || !safe_name(name) {
        return Err(invalid("absolute parent and safe single name required"));
    }
    let p = Path::new(parent);
    check_ancestors(p)?;
    let p = p.join(name);
    fs::create_dir(&p).map_err(|e| {
        if e.kind() == std::io::ErrorKind::AlreadyExists {
            CommitError::AlreadyExists {
                path: p.to_string_lossy().into_owned(),
            }
        } else {
            storage(CommitStage::CreateDirectory, &p, e)
        }
    })?;
    Ok(p.to_string_lossy().into_owned())
}
fn recovery(
    target: &str,
    reason: impl std::fmt::Display,
    record: Option<&JournalRecord>,
) -> CommitError {
    let a = area(target);
    let verified = |name: &str, expected: &str| {
        read_optional(&a.join(name))
            .ok()
            .flatten()
            .filter(|b| digest(b) == expected)
            .map(|_| a.join(name).to_string_lossy().into_owned())
    };
    CommitError::RecoveryRequired {
        target_path: target.into(),
        journal_path: a.join("journal.v1").to_string_lossy().into_owned(),
        old_version_path: record
            .and_then(|r| r.previous_digest.as_deref())
            .and_then(|d| verified("old.bin", d)),
        new_version_path: record.and_then(|r| verified("new.bin", &r.new_digest)),
        reason: reason.to_string(),
    }
}
fn inspect(target: &str) -> Result<Option<JournalRecord>, CommitError> {
    let a = area(target);
    match fs::symlink_metadata(&a) {
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(e) => return Err(recovery(target, e, None)),
        Ok(m) if !m.is_dir() || m.file_attributes() & 0x400 != 0 => {
            return Err(recovery(target, "unsafe transaction area", None))
        }
        _ => (),
    }
    let entries = fs::read_dir(&a).map_err(|e| recovery(target, e, None))?;
    for item in entries {
        let item = item.map_err(|e| recovery(target, e, None))?;
        if !matches!(
            item.file_name().to_str(),
            Some("journal.v1" | "old.bin" | "new.bin")
        ) {
            return Err(recovery(target, "unknown transaction artifact", None));
        }
    }
    let bytes = read_journal(&a.join("journal.v1"))
        .map_err(|e| recovery(target, format!("journal unavailable: {e:?}"), None))?;
    let r = decode(&bytes, target)
        .map_err(|e| recovery(target, format!("invalid journal: {e:?}"), None))?;
    let target_digest = read_optional(Path::new(target))
        .map_err(|e| recovery(target, format!("target unavailable: {e:?}"), Some(&r)))?
        .map(|b| digest(&b));
    if !matches!(r.state, JournalState::Committed | JournalState::RolledBack) {
        return Err(recovery(target, "unresolved transaction", Some(&r)));
    }
    let expected = if r.state == JournalState::Committed {
        Some(r.new_digest.clone())
    } else {
        r.previous_digest.clone()
    };
    if target_digest != expected {
        return Err(recovery(target, "terminal target mismatch", Some(&r)));
    }
    for (name, expected) in [
        ("old.bin", r.previous_digest.as_ref()),
        ("new.bin", Some(&r.new_digest)),
    ] {
        let b = read_optional(&a.join(name))
            .map_err(|e| recovery(target, format!("artifact unavailable: {e:?}"), Some(&r)))?;
        if let Some(b) = b {
            if expected.map(|e| digest(&b) == *e) != Some(true) {
                return Err(recovery(target, "terminal artifact mismatch", Some(&r)));
            }
        }
    }
    Ok(Some(r))
}
fn acquire(path: &str) -> Result<StdFileWriteLease, CommitError> {
    let requested = path.to_owned();
    let target = normalize_target(path)?;
    let side = PathBuf::from(format!("{target}.eluslot-lock"));
    if let Ok(m) = fs::symlink_metadata(&side) {
        if m.file_attributes() & (0x400 | 0x10) != 0 {
            return Err(invalid("unsafe lease sidecar"));
        }
    }
    let handle = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(false)
        .share_mode(0)
        .custom_flags(0x00200000)
        .open(&side)
        .map_err(|e| {
            if matches!(e.raw_os_error(), Some(32 | 33)) {
                CommitError::Busy {
                    path: target.clone(),
                }
            } else {
                storage(CommitStage::Acquire, &side, e)
            }
        })?;
    regular_identity(&handle).map_err(|e| storage(CommitStage::Acquire, &side, e))?;
    read_optional(Path::new(&target))?;
    inspect(&target)?;
    Ok(StdFileWriteLease {
        target_path: target,
        requested_path: requested,
        _lock_handle: handle,
        blocked: false,
        #[cfg(test)]
        _checkpoints: TestCheckpoints::default(),
    })
}
fn valid_digest(s: &str) -> bool {
    s.strip_prefix("sha256:")
        .map(|h| {
            h.len() == 64
                && h.bytes()
                    .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        })
        .unwrap_or(false)
}
fn encode(r: &JournalRecord) -> Vec<u8> {
    let mut payload = Vec::new();
    for s in [
        &r.transaction_id,
        &r.target_path,
        r.previous_digest.as_deref().unwrap_or(""),
        &r.new_digest,
        r.old_version_relative.as_deref().unwrap_or(""),
        &r.new_version_relative,
    ] {
        payload.extend_from_slice(&(s.len() as u32).to_le_bytes());
        payload.extend_from_slice(s.as_bytes());
    }
    payload.push(match r.state {
        JournalState::Prepared => 1,
        JournalState::Committed => 2,
        JournalState::RolledBack => 3,
        JournalState::RecoveryRequired => 4,
    });
    let mut b = b"ELUCOMMIT".to_vec();
    b.extend_from_slice(&r.version.to_le_bytes());
    b.extend_from_slice(&(payload.len() as u32).to_le_bytes());
    b.extend(payload);
    let hash = sgenaxis_spec::packet::source_sha256(&b);
    b.extend_from_slice(hash.as_bytes());
    b
}
fn decode(b: &[u8], target: &str) -> Result<JournalRecord, JournalDecodeError> {
    use JournalDecodeError::*;
    if b.len() > 65536 {
        return Err(Size);
    }
    if b.len() < 81 || &b[..9] != b"ELUCOMMIT" {
        return Err(Framing);
    }
    let version = u32::from_le_bytes(b[9..13].try_into().map_err(|_| Framing)?);
    let len = u32::from_le_bytes(b[13..17].try_into().map_err(|_| Framing)?) as usize;
    let end = 17usize.checked_add(len).ok_or(Framing)?;
    if end.checked_add(64) != Some(b.len()) {
        return Err(Framing);
    }
    if version != 1 {
        return Err(Version);
    }
    if sgenaxis_spec::packet::source_sha256(&b[..end]).as_bytes() != &b[end..] {
        return Err(Checksum);
    }
    let mut p = 17usize;
    let mut fields = Vec::new();
    for _ in 0..6 {
        let nend = p.checked_add(4).filter(|n| *n <= end).ok_or(Framing)?;
        let n = u32::from_le_bytes(b[p..nend].try_into().map_err(|_| Framing)?) as usize;
        p = nend;
        let next = p.checked_add(n).filter(|n| *n <= end).ok_or(Framing)?;
        let s = std::str::from_utf8(&b[p..next]).map_err(|_| Text)?;
        if s.contains('\0') || s.contains('\u{feff}') {
            return Err(Text);
        }
        fields.push(s);
        p = next;
    }
    if p.checked_add(1) != Some(end) {
        return Err(Framing);
    }
    let f = &fields;
    if f[0].len() != 32
        || !f[0]
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        || f[1].len() > 4096
        || !local_absolute(f[1])
        || !valid_digest(f[3])
        || (!f[2].is_empty() && !valid_digest(f[2]))
        || (f[2].is_empty() != f[4].is_empty())
    {
        return Err(Field);
    }
    let state = match b[p] {
        1 => JournalState::Prepared,
        2 => JournalState::Committed,
        3 => JournalState::RolledBack,
        4 => JournalState::RecoveryRequired,
        _ => return Err(State),
    };
    if f[1] != target {
        return Err(Binding);
    }
    if (!f[4].is_empty() && f[4] != "old.bin") || f[5] != "new.bin" {
        return Err(RelativePath);
    }
    Ok(JournalRecord {
        version,
        transaction_id: f[0].into(),
        target_path: f[1].into(),
        previous_digest: (!f[2].is_empty()).then(|| f[2].into()),
        new_digest: f[3].into(),
        old_version_relative: (!f[4].is_empty()).then(|| f[4].into()),
        new_version_relative: f[5].into(),
        state,
    })
}
fn transaction_id() -> String {
    use std::sync::atomic::{AtomicU64, Ordering};
    static SEQ: AtomicU64 = AtomicU64::new(0);
    let n = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos()
        ^ ((std::process::id() as u128) << 64)
        ^ SEQ.fetch_add(1, Ordering::Relaxed) as u128;
    format!("{n:032x}")
}
struct Transaction {
    record: JournalRecord,
    owned: Vec<(PathBuf, Vec<u8>)>,
    journal_bytes: Option<Vec<u8>>,
}
impl StdFileWriteLease {
    fn stage(&self, stage: CommitStage) -> Result<(), CommitError> {
        #[cfg(test)]
        {
            self._checkpoints
                .observed
                .lock()
                .unwrap()
                .push(stage.clone());
            let mut used = self._checkpoints.consumed.lock().unwrap();
            if self._checkpoints.fail_at.contains(&stage) && !used.contains(&stage) {
                used.push(stage.clone());
                return Err(storage(
                    stage,
                    Path::new(&self.target_path),
                    "injected stage failure",
                ));
            }
        }
        let _ = stage;
        Ok(())
    }
    fn point(&self, name: &str, stage: CommitStage) -> Result<(), CommitError> {
        #[cfg(test)]
        {
            self._checkpoints
                .observed_points
                .lock()
                .unwrap()
                .push(name.into());
            if let Some(f) = &self._checkpoints.at_point {
                f(name);
            }
            let mut used = self._checkpoints.consumed_points.lock().unwrap();
            if self._checkpoints.fault_points.contains(&name) && !used.iter().any(|n| n == name) {
                used.push(name.into());
                return Err(storage(
                    stage,
                    Path::new(&self.target_path),
                    format!("injected {name}"),
                ));
            }
        }
        let _ = (name, stage);
        Ok(())
    }
    fn create_owned(
        &self,
        tx: &mut Transaction,
        p: &Path,
        bytes: &[u8],
        stage: CommitStage,
        prefix: &str,
    ) -> Result<(), CommitError> {
        let mut f = OpenOptions::new()
            .read(true)
            .write(true)
            .create_new(true)
            .share_mode(0)
            .custom_flags(0x00200000)
            .open(p)
            .map_err(|e| storage(stage.clone(), p, e))?;
        // A later terminal record reuses the transaction's staging name. Track
        // the bytes of the current exclusive creation, not its prior incarnation.
        tx.owned.retain(|(owned, _)| owned != p);
        tx.owned.push((p.into(), bytes.to_vec()));
        self.point(&format!("{prefix}.write"), stage.clone())?;
        f.write_all(bytes)
            .map_err(|e| storage(stage.clone(), p, e))?;
        self.point(&format!("{prefix}.sync"), stage.clone())?;
        f.sync_all().map_err(|e| storage(stage.clone(), p, e))?;
        drop(f);
        self.point(&format!("{prefix}.synced"), stage)
    }
    fn discard_owned_next(&self, tx: &mut Transaction) -> Result<(), CommitError> {
        for (p, b) in &tx.owned {
            if p.file_name()
                .and_then(|n| n.to_str())
                .map(|n| n.starts_with("journal.next-"))
                .unwrap_or(false)
            {
                if let Some(actual) = read_optional(p)? {
                    if !b.starts_with(&actual) {
                        return Err(recovery(
                            &self.target_path,
                            "owned next changed",
                            Some(&tx.record),
                        ));
                    }
                    fs::remove_file(p).map_err(|e| storage(CommitStage::Cleanup, p, e))?;
                }
            }
        }
        Ok(())
    }
    fn journal(
        &self,
        tx: &mut Transaction,
        state: JournalState,
        prefix: &str,
    ) -> Result<(), CommitError> {
        let stage = if state == JournalState::Prepared {
            CommitStage::WritePreparedJournal
        } else {
            CommitStage::WriteCommittedJournal
        };
        self.stage(stage.clone())?;
        let mut r = tx.record.clone();
        r.state = state;
        let bytes = encode(&r);
        let a = area(&self.target_path);
        self.point(&format!("{prefix}.before_create_next"), stage.clone())?;
        #[allow(unused_mut)]
        let mut next = a.join(format!("journal.next-{}", r.transaction_id));
        #[cfg(test)]
        if prefix == "prepared" {
            if let Some(candidate) = self._checkpoints.journal_candidates.first() {
                next = PathBuf::from(candidate);
            }
        }
        if next.parent() != Some(a.as_path())
            || !next
                .file_name()
                .and_then(|n| n.to_str())
                .map(|n| {
                    n.strip_prefix("journal.next-")
                        .map(|s| {
                            s.len() == 32
                                && s.bytes()
                                    .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
                        })
                        .unwrap_or(false)
                })
                .unwrap_or(false)
        {
            return Err(invalid("unsafe journal staging candidate"));
        }
        self.create_owned(tx, &next, &bytes, stage.clone(), prefix)?;
        self.point(&format!("{prefix}.publish"), stage.clone())?;
        let journal = a.join("journal.v1");
        if read_optional(&journal)? != tx.journal_bytes {
            return Err(recovery(
                &self.target_path,
                "journal changed before publication",
                Some(&r),
            ));
        }
        fs::rename(&next, &journal).map_err(|e| storage(stage.clone(), &journal, e))?;
        tx.journal_bytes = Some(bytes.clone());
        let verify_stage = if prefix == "rolled_back" {
            self.stage(CommitStage::VerifyRestored)?;
            CommitStage::VerifyRestored
        } else {
            stage
        };
        self.point(&format!("{prefix}.verify"), verify_stage.clone())?;
        if read_journal(&journal)? != bytes
            || decode(&bytes, &self.target_path).ok() != Some(r.clone())
        {
            return Err(storage(
                verify_stage,
                &journal,
                "journal verification failed",
            ));
        }
        tx.record = r;
        self.point(&format!("{prefix}.verified"), verify_stage)
    }
    fn publish_temp(
        &self,
        tx: &mut Transaction,
        bytes: &[u8],
        prefix: &str,
    ) -> Result<(), CommitError> {
        let target = Path::new(&self.target_path);
        let parent = target.parent().ok_or_else(|| invalid("missing parent"))?;
        let mut candidates = Vec::new();
        #[cfg(test)]
        if prefix == "target" {
            candidates.extend(self._checkpoints.temp_candidates.iter().map(PathBuf::from));
        }
        for _ in 0..32 {
            candidates.push(parent.join(format!(".eluslot-publish-{}", transaction_id())));
        }
        for p in candidates {
            if p.parent() != Some(parent) {
                return Err(invalid("publish temporary must share target parent"));
            }
            let stage = if prefix == "restore" {
                CommitStage::Restore
            } else {
                CommitStage::Publish
            };
            match self.create_owned(tx, &p, bytes, stage.clone(), prefix) {
                Err(CommitError::Storage { .. })
                    if !tx.owned.iter().any(|(owned, _)| owned == &p) && p.exists() =>
                {
                    continue
                }
                Err(e) => return Err(e),
                Ok(()) => {
                    fs::rename(&p, target).map_err(|e| storage(stage, &p, e))?;
                    return Ok(());
                }
            }
        }
        Err(storage(
            CommitStage::Publish,
            target,
            "exclusive temporary retry exhausted",
        ))
    }
    fn cleanup_terminal(&self, r: &JournalRecord) -> Result<(), CommitError> {
        self.stage(CommitStage::Cleanup)?;
        self.point("cleanup.before", CommitStage::Cleanup)?;
        if inspect(&self.target_path)?.as_ref() != Some(r) {
            return Err(recovery(
                &self.target_path,
                "terminal record changed",
                Some(r),
            ));
        }
        let a = area(&self.target_path);
        for name in ["old.bin", "new.bin"] {
            let p = a.join(name);
            if p.exists() {
                self.point("cleanup.remove", CommitStage::Cleanup)?;
                fs::remove_file(&p).map_err(|e| storage(CommitStage::Cleanup, &p, e))?;
            }
        }
        let p = a.join("journal.v1");
        if read_journal(&p)? != encode(r) {
            return Err(recovery(
                &self.target_path,
                "journal changed during cleanup",
                Some(r),
            ));
        }
        self.point("cleanup.remove", CommitStage::Cleanup)?;
        fs::remove_file(&p).map_err(|e| storage(CommitStage::Cleanup, &p, e))?;
        fs::remove_dir(&a).map_err(|e| storage(CommitStage::Cleanup, &a, e))?;
        Ok(())
    }
    fn cleanup_unprepared(&self, tx: &Transaction) -> Result<(), CommitError> {
        self.stage(CommitStage::Cleanup)?;
        for (p, expected) in tx.owned.iter().rev() {
            if let Some(b) = read_optional(p)? {
                if !expected.starts_with(&b) {
                    return Err(recovery(
                        &self.target_path,
                        "owned preparation changed",
                        None,
                    ));
                }
                self.point("cleanup.remove", CommitStage::Cleanup)?;
                fs::remove_file(p).map_err(|e| storage(CommitStage::Cleanup, p, e))?;
            }
        }
        let a = area(&self.target_path);
        fs::remove_dir(&a).map_err(|e| storage(CommitStage::Cleanup, &a, e))?;
        Ok(())
    }
    fn cleanup_publish_temps(&self, tx: &Transaction) -> Result<(), CommitError> {
        let parent = Path::new(&self.target_path).parent();
        for (path, expected) in &tx.owned {
            if path.parent() != parent {
                continue;
            }
            if let Some(bytes) = read_optional(path)? {
                if !expected.starts_with(&bytes) {
                    return Err(recovery(
                        &self.target_path,
                        "owned publish temporary changed",
                        Some(&tx.record),
                    ));
                }
                self.point("cleanup.remove", CommitStage::Cleanup)?;
                fs::remove_file(path).map_err(|e| storage(CommitStage::Cleanup, path, e))?;
            }
        }
        Ok(())
    }
    fn rollback(&self, tx: &mut Transaction, old: Option<&[u8]>) -> Result<(), CommitError> {
        self.point("restore.before", CommitStage::Restore)?;
        self.stage(CommitStage::Restore)?;
        let current = read_optional(Path::new(&self.target_path))?;
        if current.as_deref() != old {
            if current.as_ref().map(|b| digest(b)) != Some(tx.record.new_digest.clone()) {
                return Err(recovery(
                    &self.target_path,
                    "external edit prevents rollback",
                    Some(&tx.record),
                ));
            }
            if let Some(old) = old {
                self.publish_temp(tx, old, "restore")?;
            } else {
                self.point("restore.remove", CommitStage::Restore)?;
                fs::remove_file(&self.target_path)
                    .map_err(|e| storage(CommitStage::Restore, Path::new(&self.target_path), e))?;
            }
        } else if old.is_some() {
            self.point("restore.write", CommitStage::Restore)?;
        } else {
            self.point("restore.remove", CommitStage::Restore)?;
        }
        self.stage(CommitStage::VerifyRestored)?;
        self.point("restored.verify", CommitStage::VerifyRestored)?;
        if read_optional(Path::new(&self.target_path))?.as_deref() != old {
            return Err(recovery(
                &self.target_path,
                "restoration verification mismatch",
                Some(&tx.record),
            ));
        }
        self.discard_owned_next(tx)?;
        self.journal(tx, JournalState::RolledBack, "rolled_back")?;
        if self.cleanup_publish_temps(tx).is_ok() {
            let _ = self.cleanup_terminal(&tx.record);
        }
        Ok(())
    }
    fn replace(
        &mut self,
        expected: Option<&str>,
        bytes: &[u8],
    ) -> Result<CommitReceipt, CommitError> {
        if self.blocked {
            return Err(recovery(&self.target_path, "lease requires recovery", None));
        }
        if let Some(r) = inspect(&self.target_path)? {
            self.cleanup_terminal(&r)?;
        }
        let old = read_optional(Path::new(&self.target_path))?;
        let previous = old.as_ref().map(|b| digest(b));
        if previous.as_deref() != expected {
            return Err(CommitError::Conflict {
                expected: expected.map(str::to_owned),
                observed: previous,
            });
        }
        let a = area(&self.target_path);
        fs::create_dir(&a).map_err(|e| storage(CommitStage::PrepareOld, &a, e))?;
        let mut tx = Transaction {
            record: JournalRecord {
                version: 1,
                transaction_id: transaction_id(),
                target_path: self.target_path.clone(),
                previous_digest: previous.clone(),
                new_digest: digest(bytes),
                old_version_relative: old.as_ref().map(|_| "old.bin".into()),
                new_version_relative: "new.bin".into(),
                state: JournalState::Prepared,
            },
            owned: Vec::new(),
            journal_bytes: None,
        };
        let result = (|| {
            self.stage(CommitStage::PrepareOld)?;
            if let Some(old) = &old {
                self.create_owned(
                    &mut tx,
                    &a.join("old.bin"),
                    old,
                    CommitStage::PrepareOld,
                    "old",
                )?;
            }
            self.stage(CommitStage::PrepareNew)?;
            self.create_owned(
                &mut tx,
                &a.join("new.bin"),
                bytes,
                CommitStage::PrepareNew,
                "new",
            )?;
            self.journal(&mut tx, JournalState::Prepared, "prepared")?;
            self.stage(CommitStage::BeforePublish)?;
            #[cfg(test)]
            if let Some(f) = &self._checkpoints.before_publish {
                f();
            }
            self.point("publish.before", CommitStage::BeforePublish)?;
            let observed = read_optional(Path::new(&self.target_path))?.map(|b| digest(&b));
            if observed != previous {
                return Err(CommitError::Conflict {
                    expected: previous.clone(),
                    observed,
                });
            }
            self.stage(CommitStage::Publish)?;
            self.point("target.publish", CommitStage::Publish)?;
            self.publish_temp(&mut tx, bytes, "target")?;
            self.point("target.published", CommitStage::Publish)?;
            self.stage(CommitStage::VerifyPublished)?;
            self.point("target.verify", CommitStage::VerifyPublished)?;
            if read_optional(Path::new(&self.target_path))?.as_deref() != Some(bytes) {
                return Err(storage(
                    CommitStage::VerifyPublished,
                    Path::new(&self.target_path),
                    "published bytes mismatch",
                ));
            }
            self.journal(&mut tx, JournalState::Committed, "committed")?;
            if read_optional(Path::new(&self.target_path))?.as_deref() != Some(bytes) {
                return Err(recovery(
                    &self.target_path,
                    "committed target changed",
                    Some(&tx.record),
                ));
            }
            Ok(())
        })();
        match result {
            Ok(()) => {
                let receipt = CommitReceipt {
                    // Echo the caller's requested path (Port contract), not the
                    // internally-canonicalized form.
                    target_path: self.requested_path.clone(),
                    previous_digest: previous,
                    committed_digest: tx.record.new_digest.clone(),
                    transaction_id: tx.record.transaction_id.clone(),
                };
                if self.cleanup_publish_temps(&tx).is_ok() {
                    let _ = self.cleanup_terminal(&tx.record);
                }
                Ok(receipt)
            }
            Err(e) => {
                if matches!(e, CommitError::Conflict { .. }) {
                    return Err(e);
                }
                let restored = if tx.journal_bytes.is_some() {
                    self.rollback(&mut tx, old.as_deref())
                } else {
                    match read_optional(Path::new(&self.target_path)) {
                        Ok(current) if current.as_deref() == old.as_deref() => {
                            self.cleanup_unprepared(&tx)
                        }
                        _ => Err(recovery(
                            &self.target_path,
                            "original state changed or cannot be verified during preparation",
                            Some(&tx.record),
                        )),
                    }
                };
                if let Err(failure) = restored {
                    self.blocked = true;
                    if tx.journal_bytes.is_some() {
                        let _ = self.discard_owned_next(&mut tx);
                        let _ = self.journal(
                            &mut tx,
                            JournalState::RecoveryRequired,
                            "recovery_required",
                        );
                    }
                    return Err(recovery(
                        &self.target_path,
                        format!(
                            "transaction failed: {e:?}; rollback/cleanup unconfirmed: {failure:?}"
                        ),
                        Some(&tx.record),
                    ));
                }
                Err(e)
            }
        }
    }
}
