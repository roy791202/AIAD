//! In-memory fake adapters — no OS; for Core / contract unit tests.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use sgenaxis_ports::{
    unsupported_platform_reason, windows_wix_supported, DeployCapability, DeployPlatform,
    DeployPort, DeploySupport, FileSystemPort, GitBranch, GitCommit, GitPort, GitRemote,
    GitStash, GitStatus, GitStatusEntry, GitTag,
    GitStatusKind, GitWriteApproval, GitWritePort, PathPort, PortError, ProcessId, ProcessOutput,
    ProcessPort, WINDOWS_WIX_PRODUCT_VERSION,
};

use crate::git_write::{git_error_redacted, GIT_WRITE_NOT_APPROVED_MSG};

// ── FileSystem ──────────────────────────────────────────────────────────────

/// In-memory path → bytes map. Paths normalized with `/`.
///
/// Tracks write／mkdir counts for PD-GIT-BOARD-SYNC-01 read-path assertions.
#[derive(Debug, Default, Clone)]
pub struct FakeFileSystem {
    inner: Arc<Mutex<HashMap<String, Vec<u8>>>>,
    write_ops: Arc<Mutex<u64>>,
    mkdir_ops: Arc<Mutex<u64>>,
}

impl FakeFileSystem {
    pub fn new() -> Self {
        Self::default()
    }

    fn key(path: &str) -> String {
        path.replace('\\', "/")
            .trim_end_matches('/')
            .to_string()
    }

    /// Seed a file for tests (does **not** count as a write op).
    pub fn seed(&self, path: &str, contents: impl AsRef<[u8]>) {
        let mut map = self.inner.lock().expect("fake fs lock");
        map.insert(Self::key(path), contents.as_ref().to_vec());
    }

    /// Number of [`FileSystemPort::write_atomic`] calls since construction.
    pub fn write_count(&self) -> u64 {
        *self.write_ops.lock().expect("fake fs write_ops lock")
    }

    /// Number of [`FileSystemPort::create_dir_all`] calls since construction.
    pub fn mkdir_count(&self) -> u64 {
        *self.mkdir_ops.lock().expect("fake fs mkdir_ops lock")
    }
}

impl FileSystemPort for FakeFileSystem {
    fn exists(&self, path: &str) -> Result<bool, PortError> {
        let map = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let k = Self::key(path);
        if map.contains_key(&k) {
            return Ok(true);
        }
        // Directory exists if any key is under it.
        let prefix = format!("{k}/");
        Ok(map.keys().any(|p| p.starts_with(&prefix)))
    }

    fn read_to_string(&self, path: &str) -> Result<String, PortError> {
        let bytes = self.read(path)?;
        String::from_utf8(bytes).map_err(|e| PortError::Io(e.to_string()))
    }

    fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
        let map = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        map.get(&Self::key(path))
            .cloned()
            .ok_or_else(|| PortError::NotFound(path.into()))
    }

    fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError> {
        {
            let mut n = self
                .write_ops
                .lock()
                .map_err(|e| PortError::Other(e.to_string()))?;
            *n = n.saturating_add(1);
        }
        let mut map = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        map.insert(Self::key(path), contents.to_vec());
        Ok(())
    }

    fn create_dir_all(&self, path: &str) -> Result<(), PortError> {
        {
            let mut n = self
                .mkdir_ops
                .lock()
                .map_err(|e| PortError::Other(e.to_string()))?;
            *n = n.saturating_add(1);
        }
        // Directory marker: empty key with trailing convention — store a sentinel.
        let mut map = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let marker = format!("{}/.dir", Self::key(path));
        map.entry(marker).or_insert_with(Vec::new);
        Ok(())
    }

    fn is_file(&self, path: &str) -> Result<bool, PortError> {
        let map = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let k = Self::key(path);
        if k.ends_with("/.dir") {
            return Ok(false);
        }
        Ok(map.contains_key(&k))
    }

    fn remove_file(&self, path: &str) -> Result<(), PortError> {
        let mut map = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let k = Self::key(path);
        if map.remove(&k).is_some() {
            Ok(())
        } else {
            Err(PortError::NotFound(path.into()))
        }
    }
}

// ── Path ────────────────────────────────────────────────────────────────────

/// Fake path conventions: fixed roots under `/fake/{config|cache}/<app>`.
#[derive(Debug, Default, Clone)]
pub struct FakePath {
    pub config_root: String,
    pub cache_root: String,
    pub sep: char,
}

impl FakePath {
    pub fn new() -> Self {
        Self {
            config_root: "/fake/config".into(),
            cache_root: "/fake/cache".into(),
            sep: '/',
        }
    }

    /// Windows-like separator for swap tests without touching real OS dirs.
    pub fn windows_style() -> Self {
        Self {
            config_root: r"C:\fake\config".into(),
            cache_root: r"C:\fake\cache".into(),
            sep: '\\',
        }
    }
}

impl PathPort for FakePath {
    fn config_dir(&self, app_name: &str) -> Result<String, PortError> {
        Ok(self.join(&self.config_root, &[app_name]))
    }

    fn cache_dir(&self, app_name: &str) -> Result<String, PortError> {
        Ok(self.join(&self.cache_root, &[app_name]))
    }

    fn join(&self, base: &str, parts: &[&str]) -> String {
        let mut out = base.trim_end_matches(['/', '\\']).to_string();
        for p in parts {
            let part = p.trim_matches(['/', '\\']);
            if part.is_empty() {
                continue;
            }
            out.push(self.sep);
            out.push_str(part);
        }
        out
    }

    fn normalize(&self, path: &str) -> String {
        let sep = self.sep;
        let other = if sep == '/' { '\\' } else { '/' };
        let mut s: String = path.chars().map(|c| if c == other { sep } else { c }).collect();
        while s.ends_with(sep) && s.len() > 1 {
            s.pop();
        }
        s
    }
}

// ── Process ─────────────────────────────────────────────────────────────────

#[derive(Debug, Default)]
struct FakeProcEntry {
    /// `None` = still running; `Some(code)` exited.
    exit: Option<i32>,
    stdout: String,
    stderr: String,
}

#[derive(Debug)]
struct FakeProcState {
    next_id: u64,
    procs: HashMap<u64, FakeProcEntry>,
    last_id: Option<u64>,
}

/// Fake process port: records starts; `finish` / `cancel` / `push_*` control outcomes.
#[derive(Debug, Clone)]
pub struct FakeProcess {
    inner: Arc<Mutex<FakeProcState>>,
}

impl Default for FakeProcess {
    fn default() -> Self {
        Self::new()
    }
}

impl FakeProcess {
    pub fn new() -> Self {
        Self {
            inner: Arc::new(Mutex::new(FakeProcState {
                next_id: 1,
                procs: HashMap::new(),
                last_id: None,
            })),
        }
    }

    /// Most recently started process id (for tests wiring live CliAgentAdapter).
    pub fn last_id(&self) -> Option<ProcessId> {
        let st = self.inner.lock().ok()?;
        st.last_id.map(ProcessId)
    }

    /// Append stdout text available to the next [`ProcessPort::try_read`].
    pub fn push_stdout(&self, id: ProcessId, text: impl Into<String>) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let entry = st
            .procs
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        entry.stdout.push_str(&text.into());
        Ok(())
    }

    /// Append stderr text available to the next [`ProcessPort::try_read`].
    pub fn push_stderr(&self, id: ProcessId, text: impl Into<String>) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let entry = st
            .procs
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        entry.stderr.push_str(&text.into());
        Ok(())
    }

    /// Mark a started process as exited with `code` (for tests).
    pub fn finish(&self, id: ProcessId, code: i32) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        match st.procs.get_mut(&id.0) {
            Some(entry) => {
                entry.exit = Some(code);
                Ok(())
            }
            None => Err(PortError::NotFound(format!("process {}", id.0))),
        }
    }
}

impl ProcessPort for FakeProcess {
    fn start(
        &mut self,
        _program: &str,
        _args: &[&str],
        _cwd: Option<&str>,
    ) -> Result<ProcessId, PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let id = st.next_id;
        st.next_id = st.next_id.saturating_add(1);
        st.procs.insert(id, FakeProcEntry::default());
        st.last_id = Some(id);
        Ok(ProcessId(id))
    }

    fn try_wait(&mut self, id: ProcessId) -> Result<Option<i32>, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        match st.procs.get(&id.0) {
            Some(entry) => Ok(entry.exit),
            None => Err(PortError::NotFound(format!("process {}", id.0))),
        }
    }

    fn cancel(&mut self, id: ProcessId) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        match st.procs.get_mut(&id.0) {
            Some(entry) => {
                if entry.exit.is_none() {
                    entry.exit = Some(-1);
                }
                Ok(())
            }
            None => Err(PortError::NotFound(format!("process {}", id.0))),
        }
    }

    fn try_read(&mut self, id: ProcessId) -> Result<ProcessOutput, PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let entry = st
            .procs
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        Ok(ProcessOutput {
            stdout: std::mem::take(&mut entry.stdout),
            stderr: std::mem::take(&mut entry.stderr),
            stdout_completion: if entry.exit.is_some() { sgenaxis_ports::StreamCompletion::Eof } else { Default::default() },
            stderr_completion: if entry.exit.is_some() { sgenaxis_ports::StreamCompletion::Eof } else { Default::default() },
        })
    }
}

// ── Git ─────────────────────────────────────────────────────────────────────

/// In-memory Git snapshot keyed by repo path string.
#[derive(Debug, Default, Clone)]
pub struct FakeGit {
    statuses: Arc<Mutex<HashMap<String, GitStatus>>>,
    logs: Arc<Mutex<HashMap<String, Vec<GitCommit>>>>,
    diffs: Arc<Mutex<HashMap<String, String>>>,
    branches: Arc<Mutex<HashMap<String, Vec<GitBranch>>>>,
    remotes: Arc<Mutex<HashMap<String, Vec<GitRemote>>>>,
    tags: Arc<Mutex<HashMap<String, Vec<GitTag>>>>,
    stashes: Arc<Mutex<HashMap<String, Vec<GitStash>>>>,
}

impl FakeGit {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set_status(&self, repo: &str, status: GitStatus) {
        let mut m = self.statuses.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), status);
    }

    pub fn set_log(&self, repo: &str, commits: Vec<GitCommit>) {
        let mut m = self.logs.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), commits);
    }

    pub fn set_diff(&self, repo: &str, diff: impl Into<String>) {
        let mut m = self.diffs.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), diff.into());
    }

    pub fn set_branches(&self, repo: &str, branches: Vec<GitBranch>) {
        let mut m = self.branches.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), branches);
    }

    pub fn set_remotes(&self, repo: &str, remotes: Vec<GitRemote>) {
        let mut m = self.remotes.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), remotes);
    }

    pub fn set_tags(&self, repo: &str, tags: Vec<GitTag>) {
        let mut m = self.tags.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), tags);
    }

    pub fn set_stashes(&self, repo: &str, stashes: Vec<GitStash>) {
        let mut m = self.stashes.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), stashes);
    }
}

impl GitPort for FakeGit {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError> {
        let m = self.statuses.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        m.get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git(format!("no status for {repo}")))
    }

    fn log(&self, repo: &str, limit: usize) -> Result<Vec<GitCommit>, PortError> {
        let m = self.logs.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        let all = m
            .get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git(format!("no log for {repo}")))?;
        Ok(all.into_iter().take(limit).collect())
    }

    fn diff(&self, repo: &str, _pathspec: Option<&str>) -> Result<String, PortError> {
        let m = self.diffs.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        m.get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git(format!("no diff for {repo}")))
    }

    fn branches(&self, repo: &str) -> Result<Vec<GitBranch>, PortError> {
        let m = self.branches.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn remotes(&self, repo: &str) -> Result<Vec<GitRemote>, PortError> {
        let m = self.remotes.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn tags(&self, repo: &str) -> Result<Vec<GitTag>, PortError> {
        let m = self.tags.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn stashes(&self, repo: &str) -> Result<Vec<GitStash>, PortError> {
        let m = self.stashes.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }
}

/// Helper to build a modified-file status for tests.
pub fn status_with_modified(branch: &str, path: &str) -> GitStatus {
    GitStatus {
        branch: Some(branch.into()),
        entries: vec![GitStatusEntry {
            path: path.into(),
            kind: GitStatusKind::Modified,
        }],
        upstream: None,
    }
}

// ── Git write (PD-GIT-02) ───────────────────────────────────────────────────

#[derive(Debug, Default)]
struct FakeGitWriteState {
    /// repo → commit messages (oldest first); hash is synthetic.
    commits: HashMap<String, Vec<(String, String)>>,
    /// repo → next push error (raw; redacted on return).
    push_fail: HashMap<String, String>,
    /// repo → successful push count.
    push_count: HashMap<String, u32>,
    next_hash: u64,
}

/// In-memory approving [`GitWritePort`] for unit tests (no OS / no user repos).
#[derive(Debug, Default, Clone)]
pub struct FakeGitWrite {
    inner: Arc<Mutex<FakeGitWriteState>>,
}

impl FakeGitWrite {
    pub fn new() -> Self {
        Self::default()
    }

    fn key(repo: &str) -> String {
        repo.replace('\\', "/")
    }

    pub fn local_commit_count(&self, repo: &str) -> usize {
        let st = self.inner.lock().expect("fake git write lock");
        st.commits
            .get(&Self::key(repo))
            .map(|v| v.len())
            .unwrap_or(0)
    }

    pub fn last_commit_message(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.commits
            .get(&Self::key(repo))
            .and_then(|v| v.last().map(|(m, _)| m.clone()))
    }

    pub fn push_count(&self, repo: &str) -> u32 {
        let st = self.inner.lock().expect("fake git write lock");
        *st.push_count.get(&Self::key(repo)).unwrap_or(&0)
    }

    /// Inject a one-shot push failure; local commits are left intact.
    pub fn fail_next_push(&self, repo: &str, raw_error: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.push_fail.insert(Self::key(repo), raw_error.into());
    }
}

impl GitWritePort for FakeGitWrite {
    fn commit(
        &self,
        repo: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        st.next_hash = st.next_hash.saturating_add(1);
        let hash = format!("{:012x}", st.next_hash);
        st.commits
            .entry(Self::key(repo))
            .or_default()
            .push((message.to_string(), hash));
        Ok(())
    }

    fn push(
        &self,
        repo: &str,
        _remote: &str,
        _refspec: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if let Some(raw) = st.push_fail.remove(&key) {
            // Do not clear commits — preserve local state on remote failure.
            return Err(git_error_redacted("push rejected", &raw));
        }
        *st.push_count.entry(key).or_insert(0) += 1;
        Ok(())
    }
}

// ── Deploy (PD-DEPLOY-PORT-01) ──────────────────────────────────────────────

#[derive(Debug, Default)]
struct FakeDeployState {
    last_artifact_path: Option<String>,
    /// When set, Windows capability becomes Unsupported (edge tests).
    force_windows_unsupported: Option<String>,
    version: String,
}

/// In-memory [`DeployPort`] — M3 defaults: Windows WiX/MSI Supported; macOS/Linux Unsupported.
#[derive(Debug, Clone)]
pub struct FakeDeploy {
    inner: Arc<Mutex<FakeDeployState>>,
}

impl Default for FakeDeploy {
    fn default() -> Self {
        Self::m3_defaults()
    }
}

impl FakeDeploy {
    /// Windows Supported (WiX/MSI path convention); macOS/Linux → Unsupported.
    pub fn m3_defaults() -> Self {
        Self {
            inner: Arc::new(Mutex::new(FakeDeployState {
                last_artifact_path: None,
                force_windows_unsupported: None,
                version: WINDOWS_WIX_PRODUCT_VERSION.into(),
            })),
        }
    }

    pub fn set_last_artifact_path(&self, path: Option<String>) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        st.last_artifact_path = path;
        Ok(())
    }

    /// Force Windows to Unsupported (optional negative fixture).
    pub fn force_windows_unsupported(&self, reason: impl Into<String>) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        st.force_windows_unsupported = Some(reason.into());
        Ok(())
    }
}

impl DeployPort for FakeDeploy {
    fn capability(&self, platform: DeployPlatform) -> Result<DeployCapability, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        let support = match platform {
            DeployPlatform::Windows => {
                if let Some(reason) = st.force_windows_unsupported.as_ref() {
                    DeploySupport::Unsupported {
                        reason: reason.clone(),
                    }
                } else {
                    windows_wix_supported(&st.version)
                }
            }
            DeployPlatform::MacOs | DeployPlatform::Linux => DeploySupport::Unsupported {
                reason: unsupported_platform_reason(platform),
            },
        };
        Ok(DeployCapability { platform, support })
    }

    fn last_artifact_path(&self) -> Result<Option<String>, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        Ok(st.last_artifact_path.clone())
    }
}
