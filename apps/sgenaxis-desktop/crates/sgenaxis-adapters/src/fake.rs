//! In-memory fake adapters — no OS; for Core / contract unit tests.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};

use sgenaxis_ports::{
    unsupported_platform_reason, windows_wix_supported, DeployCapability, DeployPlatform,
    DeployPort, DeploySupport, FileSystemPort, GitBranch, GitCommit, GitConflictState, GitPort,
    GitRemote, GitSettings, GitStash, GitStatus, GitStatusEntry, GitStatusKind, GitTag,
    GitWriteApproval, GitWritePort, PathPort, PortError, ProcessId, ProcessOutput, ProcessPort,
    WINDOWS_WIX_PRODUCT_VERSION,
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
        path.replace('\\', "/").trim_end_matches('/').to_string()
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
        let map = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let map = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let mut map = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let mut map = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let marker = format!("{}/.dir", Self::key(path));
        map.entry(marker).or_insert_with(Vec::new);
        Ok(())
    }

    fn is_file(&self, path: &str) -> Result<bool, PortError> {
        let map = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let k = Self::key(path);
        if k.ends_with("/.dir") {
            return Ok(false);
        }
        Ok(map.contains_key(&k))
    }

    fn remove_file(&self, path: &str) -> Result<(), PortError> {
        let mut map = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let mut s: String = path
            .chars()
            .map(|c| if c == other { sep } else { c })
            .collect();
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let entry = st
            .procs
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        entry.stdout.push_str(&text.into());
        Ok(())
    }

    /// Append stderr text available to the next [`ProcessPort::try_read`].
    pub fn push_stderr(&self, id: ProcessId, text: impl Into<String>) -> Result<(), PortError> {
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let entry = st
            .procs
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        entry.stderr.push_str(&text.into());
        Ok(())
    }

    /// Mark a started process as exited with `code` (for tests).
    pub fn finish(&self, id: ProcessId, code: i32) -> Result<(), PortError> {
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let id = st.next_id;
        st.next_id = st.next_id.saturating_add(1);
        st.procs.insert(id, FakeProcEntry::default());
        st.last_id = Some(id);
        Ok(ProcessId(id))
    }

    fn try_wait(&mut self, id: ProcessId) -> Result<Option<i32>, PortError> {
        let st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        match st.procs.get(&id.0) {
            Some(entry) => Ok(entry.exit),
            None => Err(PortError::NotFound(format!("process {}", id.0))),
        }
    }

    fn cancel(&mut self, id: ProcessId) -> Result<(), PortError> {
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let entry = st
            .procs
            .get_mut(&id.0)
            .ok_or_else(|| PortError::NotFound(format!("process {}", id.0)))?;
        Ok(ProcessOutput {
            stdout: std::mem::take(&mut entry.stdout),
            stderr: std::mem::take(&mut entry.stderr),
            stdout_completion: if entry.exit.is_some() {
                sgenaxis_ports::StreamCompletion::Eof
            } else {
                Default::default()
            },
            stderr_completion: if entry.exit.is_some() {
                sgenaxis_ports::StreamCompletion::Eof
            } else {
                Default::default()
            },
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
    conflicts: Arc<Mutex<HashMap<String, GitConflictState>>>,
    settings: Arc<Mutex<HashMap<String, GitSettings>>>,
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

    pub fn set_conflicts(&self, repo: &str, conflict: GitConflictState) {
        let mut m = self.conflicts.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), conflict);
    }

    pub fn set_settings(&self, repo: &str, settings: GitSettings) {
        let mut m = self.settings.lock().expect("fake git lock");
        m.insert(repo.replace('\\', "/"), settings);
    }
}

impl GitPort for FakeGit {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError> {
        let m = self
            .statuses
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        m.get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git(format!("no status for {repo}")))
    }

    fn log(&self, repo: &str, limit: usize) -> Result<Vec<GitCommit>, PortError> {
        let m = self
            .logs
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        let all = m
            .get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git(format!("no log for {repo}")))?;
        Ok(all.into_iter().take(limit).collect())
    }

    fn diff(&self, repo: &str, _pathspec: Option<&str>) -> Result<String, PortError> {
        let m = self
            .diffs
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        m.get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git(format!("no diff for {repo}")))
    }

    fn branches(&self, repo: &str) -> Result<Vec<GitBranch>, PortError> {
        let m = self
            .branches
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn remotes(&self, repo: &str) -> Result<Vec<GitRemote>, PortError> {
        let m = self
            .remotes
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn tags(&self, repo: &str) -> Result<Vec<GitTag>, PortError> {
        let m = self
            .tags
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn stashes(&self, repo: &str) -> Result<Vec<GitStash>, PortError> {
        let m = self
            .stashes
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn conflicts(&self, repo: &str) -> Result<GitConflictState, PortError> {
        let m = self
            .conflicts
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = repo.replace('\\', "/");
        Ok(m.get(&key).cloned().unwrap_or_default())
    }

    fn settings(&self, repo: &str) -> Result<GitSettings, PortError> {
        let m = self
            .settings
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
    /// repo → last branch switched to (approved).
    switched: HashMap<String, String>,
    /// repo → last approved local identity (`user.name`, `user.email`).
    identity: HashMap<String, (String, String)>,
    /// repo → last approved root `.gitignore` contents.
    ignore: HashMap<String, String>,
    /// repo → last approved stash apply selector.
    stash_apply: HashMap<String, String>,
    /// repo → last approved stash pop selector.
    stash_pop: HashMap<String, String>,
    /// repo → last approved stash drop selector.
    stash_drop: HashMap<String, String>,
    /// repo → last approved stash push message.
    stash_push: HashMap<String, String>,
    /// repo → next stash apply/pop/drop/push error (raw; redacted on return).
    stash_fail: HashMap<String, String>,
    /// repo → last approved tag create `(name, message)`. Empty message = lightweight.
    tag_create: HashMap<String, (String, String)>,
    /// repo → last approved local tag delete name.
    tag_delete: HashMap<String, String>,
    /// repo → last approved tag push `(remote, name)`.
    tag_push: HashMap<String, (String, String)>,
    /// repo → created tag names (duplicate create fails honestly; delete removes).
    tags: HashMap<String, Vec<String>>,
    /// repo → remote → tag names already present on that remote.
    remote_tags: HashMap<String, HashMap<String, Vec<String>>>,
    /// repo → last approved local branch create name.
    branch_create: HashMap<String, String>,
    /// repo → last approved local branch delete name.
    branch_delete: HashMap<String, String>,
    /// repo → last approved local branch rename `(old, new)`.
    branch_rename: HashMap<String, (String, String)>,
    /// repo → created local branch names (duplicate create fails honestly).
    branches: HashMap<String, Vec<String>>,
    /// repo → names that exist only as remote-tracking refs (not local).
    remote_only_branches: HashMap<String, Vec<String>>,
    /// repo → local branches that must fail `-d` as unmerged (no force).
    unmerged_branches: HashMap<String, Vec<String>>,
    /// repo → last approved remote add `(name, url)`.
    remote_add: HashMap<String, (String, String)>,
    /// repo → last approved remote remove name.
    remote_remove: HashMap<String, String>,
    /// repo → last approved remote set-url `(name, url)`.
    remote_set_url: HashMap<String, (String, String)>,
    /// repo → last approved remote rename `(old, new)`.
    remote_rename: HashMap<String, (String, String)>,
    /// repo → last approved set-upstream `(local, remote, branch)`.
    last_set_upstream: HashMap<String, (String, String, String)>,
    /// repo → last approved unset-upstream local branch.
    last_unset_upstream: HashMap<String, String>,
    /// repo → last approved stage-all recorded (true even on clean no-op).
    last_stage_all: HashMap<String, bool>,
    /// repo → local branch → `(remote, branch)` tracking.
    upstreams: HashMap<String, HashMap<String, (String, String)>>,
    /// repo → current HEAD branch name (empty local uses this).
    current_branch: HashMap<String, String>,
    /// repo → last approved fetch `(remote, optional refspec)`.
    last_fetch: HashMap<String, (String, Option<String>)>,
    /// repo → last approved fetch-prune remote.
    last_fetch_prune: HashMap<String, String>,
    /// repo → last approved ff-only pull `(remote, optional branch)`.
    last_pull_ff_only: HashMap<String, (String, Option<String>)>,
    /// repo → local has commits not reachable by ff-only pull.
    pull_local_ahead: HashMap<String, bool>,
    /// repo → dirty worktree would be overwritten by pull.
    pull_dirty_overwrite: HashMap<String, bool>,
    /// repo → remote-tracking refs marked stale on the remote (fetch-prune deletes these).
    stale_remote_tracking: HashMap<String, Vec<String>>,
    /// repo → remote-tracking refs `(refs/remotes/…, oid)`. Fetch updates these only.
    remote_tracking: HashMap<String, Vec<(String, String)>>,
    /// repo → synthetic local HEAD oid (fetch must not move this).
    local_head: HashMap<String, String>,
    /// repo → local remotes `(name, url)` (duplicate add fails; missing remove fails).
    remotes: HashMap<String, Vec<(String, String)>>,
    /// repo → in-progress conflict kind (`Merge` / `Rebase` / `CherryPick` / `Revert`).
    conflict_kind: HashMap<String, String>,
    /// repo → remaining unmerged paths.
    conflict_files: HashMap<String, Vec<String>>,
    /// repo → path → worktree text (marker check; optional).
    conflict_text: HashMap<String, HashMap<String, String>>,
    /// repo → last approved conflict save path.
    conflict_save: HashMap<String, String>,
    /// repo → last approved continue kind.
    conflict_continue: HashMap<String, String>,
    /// repo → last approved abort kind.
    conflict_abort: HashMap<String, String>,
    /// repo → last approved skip kind.
    conflict_skip: HashMap<String, String>,
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

    /// Last branch an approved switch moved to for `repo`, if any.
    pub fn switched_branch(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.switched.get(&Self::key(repo)).cloned()
    }

    /// Last approved local identity for `repo`, if any.
    pub fn last_identity(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.identity.get(&Self::key(repo)).cloned()
    }

    /// Last approved root `.gitignore` contents for `repo`, if any.
    pub fn last_ignore(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.ignore.get(&Self::key(repo)).cloned()
    }

    /// Last stash selector an approved apply recorded for `repo`, if any.
    pub fn last_stash_apply(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.stash_apply.get(&Self::key(repo)).cloned()
    }

    /// Last stash selector an approved pop recorded for `repo`, if any.
    pub fn last_stash_pop(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.stash_pop.get(&Self::key(repo)).cloned()
    }

    /// Last stash selector an approved drop recorded for `repo`, if any.
    pub fn last_stash_drop(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.stash_drop.get(&Self::key(repo)).cloned()
    }

    /// Last message an approved stash push recorded for `repo`, if any.
    pub fn last_stash_push(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.stash_push.get(&Self::key(repo)).cloned()
    }

    /// Last approved tag create for `repo` as `(name, message)`. Empty message = lightweight.
    pub fn last_tag_create(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.tag_create.get(&Self::key(repo)).cloned()
    }

    /// Tag names recorded for `repo` (creation order; deletes remove entries).
    pub fn created_tags(&self, repo: &str) -> Vec<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.tags.get(&Self::key(repo)).cloned().unwrap_or_default()
    }

    /// Last approved local tag delete name for `repo`, if any.
    pub fn last_tag_delete(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.tag_delete.get(&Self::key(repo)).cloned()
    }

    /// Last approved tag push for `repo` as `(remote, name)`.
    pub fn last_tag_push(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.tag_push.get(&Self::key(repo)).cloned()
    }

    /// Tag names Fake believes exist on `remote` for `repo`.
    pub fn remote_tags(&self, repo: &str, remote: &str) -> Vec<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remote_tags
            .get(&Self::key(repo))
            .and_then(|m| m.get(remote))
            .cloned()
            .unwrap_or_default()
    }

    /// Last approved local branch create name for `repo`, if any.
    pub fn last_branch_create(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.branch_create.get(&Self::key(repo)).cloned()
    }

    /// Local branch names recorded for `repo` (creation order).
    pub fn created_branches(&self, repo: &str) -> Vec<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.branches
            .get(&Self::key(repo))
            .cloned()
            .unwrap_or_default()
    }

    /// Last approved local branch delete name for `repo`, if any.
    pub fn last_branch_delete(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.branch_delete.get(&Self::key(repo)).cloned()
    }

    /// Last approved local branch rename for `repo` as `(old, new)`.
    pub fn last_branch_rename(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.branch_rename.get(&Self::key(repo)).cloned()
    }

    /// Mark `name` as remote-tracking only so local rename refuses it.
    pub fn mark_remote_only(&self, repo: &str, name: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.remote_only_branches
            .entry(Self::key(repo))
            .or_default()
            .push(name.into());
    }

    /// Mark `branch` as unmerged for `repo` so safe delete fails honestly.
    pub fn mark_unmerged(&self, repo: &str, branch: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.unmerged_branches
            .entry(Self::key(repo))
            .or_default()
            .push(branch.into());
    }

    /// Last approved remote add for `repo` as `(name, url)`.
    pub fn last_remote_add(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remote_add.get(&Self::key(repo)).cloned()
    }

    /// Last approved remote remove name for `repo`, if any.
    pub fn last_remote_remove(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remote_remove.get(&Self::key(repo)).cloned()
    }

    /// Last approved remote set-url for `repo` as `(name, url)`.
    pub fn last_remote_set_url(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remote_set_url.get(&Self::key(repo)).cloned()
    }

    /// Last approved remote rename for `repo` as `(old, new)`.
    pub fn last_remote_rename(&self, repo: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remote_rename.get(&Self::key(repo)).cloned()
    }

    /// Last approved set-upstream for `repo` as `(local, remote, branch)`.
    pub fn last_set_upstream(&self, repo: &str) -> Option<(String, String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.last_set_upstream.get(&Self::key(repo)).cloned()
    }

    /// Last approved unset-upstream local branch for `repo`, if any.
    pub fn last_unset_upstream(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.last_unset_upstream.get(&Self::key(repo)).cloned()
    }

    /// Whether an approved stage-all ran for `repo` (clean tree still records).
    pub fn last_stage_all(&self, repo: &str) -> Option<bool> {
        let st = self.inner.lock().expect("fake git write lock");
        st.last_stage_all.get(&Self::key(repo)).copied()
    }

    /// Recorded upstream for `local` as `(remote, branch)`.
    pub fn upstream_of(&self, repo: &str, local: &str) -> Option<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.upstreams
            .get(&Self::key(repo))
            .and_then(|m| m.get(local))
            .cloned()
    }

    /// Set Fake's current HEAD branch so empty `local` can resolve.
    pub fn set_current_branch(&self, repo: &str, name: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.current_branch.insert(Self::key(repo), name.into());
    }

    /// Last approved fetch for `repo` as `(remote, optional refspec)`.
    pub fn last_fetch(&self, repo: &str) -> Option<(String, Option<String>)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.last_fetch.get(&Self::key(repo)).cloned()
    }

    /// Last approved fetch-prune remote for `repo`, if any.
    pub fn last_fetch_prune(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.last_fetch_prune.get(&Self::key(repo)).cloned()
    }

    /// Last approved ff-only pull for `repo` as `(remote, optional branch)`.
    pub fn last_pull_ff_only(&self, repo: &str) -> Option<(String, Option<String>)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.last_pull_ff_only.get(&Self::key(repo)).cloned()
    }

    /// Mark `repo` as diverged for pull (local commits block ff-only).
    pub fn mark_pull_local_ahead(&self, repo: &str) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.pull_local_ahead.insert(Self::key(repo), true);
    }

    /// Mark `repo` as having dirty overwrites that block pull.
    pub fn mark_pull_dirty_overwrite(&self, repo: &str) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.pull_dirty_overwrite.insert(Self::key(repo), true);
    }

    /// Seed a remote-tracking ref without fetching (tests for prune).
    pub fn seed_remote_tracking(
        &self,
        repo: &str,
        refname: impl Into<String>,
        oid: impl Into<String>,
    ) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.remote_tracking
            .entry(Self::key(repo))
            .or_default()
            .push((refname.into(), oid.into()));
    }

    /// Mark a remote-tracking ref as deleted on the remote (fetch-prune removes it).
    pub fn mark_stale_remote_tracking(&self, repo: &str, refname: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.stale_remote_tracking
            .entry(Self::key(repo))
            .or_default()
            .push(refname.into());
    }

    /// Remote-tracking refs recorded for `repo` as `(name, oid)`.
    pub fn remote_tracking_refs(&self, repo: &str) -> Vec<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remote_tracking
            .get(&Self::key(repo))
            .cloned()
            .unwrap_or_default()
    }

    /// Synthetic local HEAD oid for `repo` (fetch must leave this unchanged).
    pub fn local_head(&self, repo: &str) -> String {
        let st = self.inner.lock().expect("fake git write lock");
        st.local_head
            .get(&Self::key(repo))
            .cloned()
            .unwrap_or_else(|| "local-head".into())
    }

    /// Local remotes recorded for `repo` as `(name, url)` (add order).
    pub fn configured_remotes(&self, repo: &str) -> Vec<(String, String)> {
        let st = self.inner.lock().expect("fake git write lock");
        st.remotes
            .get(&Self::key(repo))
            .cloned()
            .unwrap_or_default()
    }

    /// Inject a one-shot stash apply/pop/drop/push failure; do not record success.
    pub fn fail_next_stash(&self, repo: &str, raw_error: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.stash_fail.insert(Self::key(repo), raw_error.into());
    }

    /// Seed an in-progress conflict so Fake save/continue/abort can succeed.
    pub fn set_conflict_in_progress(&self, repo: &str, kind: &str, files: &[&str]) {
        let mut st = self.inner.lock().expect("fake git write lock");
        let key = Self::key(repo);
        st.conflict_kind.insert(key.clone(), kind.to_string());
        st.conflict_files
            .insert(key, files.iter().map(|p| (*p).to_string()).collect());
    }

    /// Optional worktree text used to fail honestly on remaining conflict markers.
    pub fn set_conflict_file_text(&self, repo: &str, path: &str, text: impl Into<String>) {
        let mut st = self.inner.lock().expect("fake git write lock");
        st.conflict_text
            .entry(Self::key(repo))
            .or_default()
            .insert(path.to_string(), text.into());
    }

    pub fn last_conflict_save(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.conflict_save.get(&Self::key(repo)).cloned()
    }

    pub fn last_conflict_continue(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.conflict_continue.get(&Self::key(repo)).cloned()
    }

    pub fn last_conflict_abort(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.conflict_abort.get(&Self::key(repo)).cloned()
    }

    pub fn last_conflict_skip(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.conflict_skip.get(&Self::key(repo)).cloned()
    }

    pub fn conflict_kind(&self, repo: &str) -> Option<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.conflict_kind.get(&Self::key(repo)).cloned()
    }

    pub fn remaining_conflict_files(&self, repo: &str) -> Vec<String> {
        let st = self.inner.lock().expect("fake git write lock");
        st.conflict_files
            .get(&Self::key(repo))
            .cloned()
            .unwrap_or_default()
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if let Some(raw) = st.push_fail.remove(&key) {
            // Do not clear commits — preserve local state on remote failure.
            return Err(git_error_redacted("push rejected", &raw));
        }
        *st.push_count.entry(key).or_insert(0) += 1;
        Ok(())
    }

    fn switch_branch(
        &self,
        repo: &str,
        branch: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        st.switched.insert(Self::key(repo), branch.to_string());
        Ok(())
    }

    fn set_identity(
        &self,
        repo: &str,
        name: &str,
        email: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        st.identity
            .insert(Self::key(repo), (name.to_string(), email.to_string()));
        Ok(())
    }

    fn set_ignore(
        &self,
        repo: &str,
        contents: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        st.ignore.insert(Self::key(repo), contents.to_string());
        Ok(())
    }

    fn stash_apply(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if let Some(raw) = st.stash_fail.remove(&key) {
            return Err(git_error_redacted("stash apply conflict", &raw));
        }
        st.stash_apply.insert(key, stash_ref.to_string());
        Ok(())
    }

    fn stash_pop(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if let Some(raw) = st.stash_fail.remove(&key) {
            // Conflict: do not record pop (stash remains).
            return Err(git_error_redacted("stash pop conflict", &raw));
        }
        st.stash_pop.insert(key, stash_ref.to_string());
        Ok(())
    }

    fn stash_drop(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if let Some(raw) = st.stash_fail.remove(&key) {
            // Missing / invalid stash: do not record drop (list unchanged).
            return Err(git_error_redacted("stash drop failed", &raw));
        }
        st.stash_drop.insert(key, stash_ref.to_string());
        Ok(())
    }

    fn stash_push(
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if let Some(raw) = st.stash_fail.remove(&key) {
            return Err(git_error_redacted("stash push failed", &raw));
        }
        st.stash_push.insert(key, message.to_string());
        Ok(())
    }

    fn create_tag(
        &self,
        repo: &str,
        name: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let tag = name.trim();
        if tag.is_empty() {
            return Err(PortError::Other("empty tag name".into()));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.tags.entry(key.clone()).or_default();
        if existing.iter().any(|t| t == tag) {
            // Duplicate: do not overwrite; fail honestly (no `-f`).
            return Err(PortError::Git(format!("tag '{tag}' already exists")));
        }
        existing.push(tag.to_string());
        st.tag_create
            .insert(key, (tag.to_string(), message.to_string()));
        Ok(())
    }

    fn delete_tag(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let tag = name.trim();
        if tag.is_empty() {
            return Err(PortError::Other("empty tag name".into()));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.tags.entry(key.clone()).or_default();
        if !existing.iter().any(|t| t == tag) {
            // Missing: do not record delete; fail honestly (no `-f`, no push).
            return Err(PortError::Git(format!("tag '{tag}' not found")));
        }
        existing.retain(|t| t != tag);
        st.tag_delete.insert(key, tag.to_string());
        Ok(())
    }

    fn push_tag(
        &self,
        repo: &str,
        remote: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let remote_name = if remote.trim().is_empty() {
            "origin"
        } else {
            remote.trim()
        };
        let tag = name.trim();
        if tag.is_empty() {
            return Err(PortError::Other("empty tag name".into()));
        }
        if crate::git_write::tag_name_out_of_scope(tag) {
            return Err(PortError::Other(
                "force/delete/push tag writes are out of scope".into(),
            ));
        }
        if crate::git_write::remote_name_out_of_scope(remote_name) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let has_remote = st
            .remotes
            .get(&key)
            .map(|remotes| remotes.iter().any(|(n, _)| n == remote_name))
            .unwrap_or(false);
        if !has_remote {
            return Err(PortError::Git(format!("No such remote: '{remote_name}'")));
        }
        let has_local = st
            .tags
            .get(&key)
            .map(|tags| tags.iter().any(|t| t == tag))
            .unwrap_or(false);
        if !has_local {
            return Err(PortError::Git(format!("tag '{tag}' not found")));
        }
        let on_remote = st
            .remote_tags
            .entry(key.clone())
            .or_default()
            .entry(remote_name.to_string())
            .or_default();
        if on_remote.iter().any(|t| t == tag) {
            return Err(PortError::Git(format!("remote tag '{tag}' already exists")));
        }
        on_remote.push(tag.to_string());
        st.tag_push
            .insert(key, (remote_name.to_string(), tag.to_string()));
        Ok(())
    }

    fn create_branch(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let branch = name.trim();
        if branch.is_empty() {
            return Err(PortError::Other("empty branch name".into()));
        }
        if crate::git_write::branch_name_out_of_scope(branch) {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.branches.entry(key.clone()).or_default();
        if existing.iter().any(|b| b == branch) {
            return Err(PortError::Git(format!("branch '{branch}' already exists")));
        }
        existing.push(branch.to_string());
        st.branch_create.insert(key, branch.to_string());
        Ok(())
    }

    fn delete_branch(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let branch = name.trim();
        if branch.is_empty() {
            return Err(PortError::Other("empty branch name".into()));
        }
        if crate::git_write::branch_name_out_of_scope(branch) {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let current = st
            .switched
            .get(&key)
            .cloned()
            .unwrap_or_else(|| "main".to_string());
        if current == branch {
            return Err(PortError::Other(
                "cannot delete the current HEAD branch".into(),
            ));
        }
        let exists = st
            .branches
            .get(&key)
            .map(|v| v.iter().any(|b| b == branch))
            .unwrap_or(false);
        if !exists {
            return Err(PortError::Git(format!("branch '{branch}' not found")));
        }
        let is_unmerged = st
            .unmerged_branches
            .get(&key)
            .map(|v| v.iter().any(|b| b == branch))
            .unwrap_or(false);
        if is_unmerged {
            return Err(PortError::Git(format!(
                "branch '{branch}' is not fully merged"
            )));
        }
        if let Some(existing) = st.branches.get_mut(&key) {
            existing.retain(|b| b != branch);
        }
        st.branch_delete.insert(key, branch.to_string());
        Ok(())
    }

    fn rename_branch(
        &self,
        repo: &str,
        old: &str,
        new: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let old = old.trim();
        let new = new.trim();
        if old.is_empty() || new.is_empty() {
            return Err(PortError::Other("empty branch name".into()));
        }
        if crate::git_write::branch_name_out_of_scope(old)
            || crate::git_write::branch_name_out_of_scope(new)
        {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let remote_only = st
            .remote_only_branches
            .get(&key)
            .map(|v| v.iter().any(|b| b == old))
            .unwrap_or(false);
        if remote_only {
            return Err(PortError::Other(format!(
                "refusing remote-only name '{old}'"
            )));
        }
        let exists = st
            .branches
            .get(&key)
            .map(|v| v.iter().any(|b| b == old))
            .unwrap_or(false);
        if !exists {
            return Err(PortError::Git(format!("branch '{old}' not found")));
        }
        let taken = st
            .branches
            .get(&key)
            .map(|v| v.iter().any(|b| b == new))
            .unwrap_or(false);
        if taken && old != new {
            return Err(PortError::Git(format!("branch '{new}' already exists")));
        }
        if let Some(existing) = st.branches.get_mut(&key) {
            for b in existing.iter_mut() {
                if b == old {
                    *b = new.to_string();
                }
            }
        }
        if st.switched.get(&key).map(|s| s.as_str()) == Some(old) {
            st.switched.insert(key.clone(), new.to_string());
        }
        st.branch_rename
            .insert(key, (old.to_string(), new.to_string()));
        Ok(())
    }

    fn add_remote(
        &self,
        repo: &str,
        name: &str,
        url: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let remote = name.trim();
        let remote_url = url.trim();
        if remote.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if remote_url.is_empty() {
            return Err(PortError::Other("empty remote url".into()));
        }
        if crate::git_write::remote_name_out_of_scope(remote) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        if crate::git_write::remote_url_out_of_scope(remote_url) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.remotes.entry(key.clone()).or_default();
        if existing.iter().any(|(n, _)| n == remote) {
            return Err(PortError::Git(format!("remote '{remote}' already exists")));
        }
        existing.push((remote.to_string(), remote_url.to_string()));
        st.remote_add
            .insert(key, (remote.to_string(), remote_url.to_string()));
        Ok(())
    }

    fn remove_remote(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let remote = name.trim();
        if remote.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if crate::git_write::remote_name_out_of_scope(remote) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.remotes.entry(key.clone()).or_default();
        if !existing.iter().any(|(n, _)| n == remote) {
            return Err(PortError::Git(format!("No such remote: '{remote}'")));
        }
        existing.retain(|(n, _)| n != remote);
        st.remote_remove.insert(key, remote.to_string());
        Ok(())
    }

    fn set_remote_url(
        &self,
        repo: &str,
        name: &str,
        url: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let remote = name.trim();
        let remote_url = url.trim();
        if remote.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if remote_url.is_empty() {
            return Err(PortError::Other("empty remote url".into()));
        }
        if crate::git_write::remote_name_out_of_scope(remote) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        if crate::git_write::remote_url_out_of_scope(remote_url) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.remotes.entry(key.clone()).or_default();
        if !existing.iter().any(|(n, _)| n == remote) {
            return Err(PortError::Git(format!("No such remote: '{remote}'")));
        }
        for pair in existing.iter_mut() {
            if pair.0 == remote {
                pair.1 = remote_url.to_string();
            }
        }
        st.remote_set_url
            .insert(key, (remote.to_string(), remote_url.to_string()));
        Ok(())
    }

    fn rename_remote(
        &self,
        repo: &str,
        old: &str,
        new: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let old_name = old.trim();
        let new_name = new.trim();
        if old_name.is_empty() || new_name.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if old_name == new_name {
            return Err(PortError::Other("remote name unchanged".into()));
        }
        if crate::git_write::remote_name_out_of_scope(old_name)
            || crate::git_write::remote_name_out_of_scope(new_name)
        {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let existing = st.remotes.entry(key.clone()).or_default();
        if !existing.iter().any(|(n, _)| n == old_name) {
            return Err(PortError::Git(format!("No such remote: '{old_name}'")));
        }
        if existing.iter().any(|(n, _)| n == new_name) {
            return Err(PortError::Git(format!(
                "remote '{new_name}' already exists"
            )));
        }
        for pair in existing.iter_mut() {
            if pair.0 == old_name {
                pair.0 = new_name.to_string();
            }
        }
        let prefix_old = format!("refs/remotes/{old_name}/");
        let prefix_new = format!("refs/remotes/{new_name}/");
        if let Some(tracking) = st.remote_tracking.get_mut(&key) {
            for pair in tracking.iter_mut() {
                if pair.0.starts_with(&prefix_old) {
                    pair.0 = format!("{}{}", prefix_new, &pair.0[prefix_old.len()..]);
                }
            }
        }
        st.remote_rename
            .insert(key, (old_name.to_string(), new_name.to_string()));
        Ok(())
    }

    fn set_upstream(
        &self,
        repo: &str,
        remote: &str,
        branch: &str,
        local: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let remote_name = remote.trim();
        let remote_branch = branch.trim();
        if remote_name.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if remote_branch.is_empty() {
            return Err(PortError::Other("empty branch name".into()));
        }
        if crate::git_write::remote_name_out_of_scope(remote_name)
            || crate::git_write::branch_name_out_of_scope(remote_branch)
        {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let local_name = if local.trim().is_empty() {
            st.current_branch
                .get(&key)
                .cloned()
                .filter(|n| !n.is_empty() && n != "HEAD")
                .ok_or_else(|| PortError::Other("cannot set upstream on detached HEAD".into()))?
        } else {
            local.trim().to_string()
        };
        if crate::git_write::branch_name_out_of_scope(&local_name) {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        let has_remote = st
            .remotes
            .get(&key)
            .map(|remotes| remotes.iter().any(|(n, _)| n == remote_name))
            .unwrap_or(false);
        if !has_remote {
            return Err(PortError::Git(format!("No such remote: '{remote_name}'")));
        }
        let has_local = st
            .branches
            .get(&key)
            .map(|names| names.iter().any(|n| n == &local_name))
            .unwrap_or(false);
        if !has_local {
            return Err(PortError::Git(format!("branch '{local_name}' not found")));
        }
        let tracking = format!("refs/remotes/{remote_name}/{remote_branch}");
        let has_tracking = st
            .remote_tracking
            .get(&key)
            .map(|refs| refs.iter().any(|(n, _)| n == &tracking))
            .unwrap_or(false);
        if !has_tracking {
            return Err(PortError::Git(format!(
                "remote-tracking branch '{remote_name}/{remote_branch}' not found"
            )));
        }
        st.upstreams.entry(key.clone()).or_default().insert(
            local_name.clone(),
            (remote_name.to_string(), remote_branch.to_string()),
        );
        st.last_set_upstream.insert(
            key,
            (
                local_name,
                remote_name.to_string(),
                remote_branch.to_string(),
            ),
        );
        Ok(())
    }

    fn unset_upstream(
        &self,
        repo: &str,
        local: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let local_name = if local.trim().is_empty() {
            st.current_branch
                .get(&key)
                .cloned()
                .filter(|n| !n.is_empty() && n != "HEAD")
                .ok_or_else(|| PortError::Other("cannot unset upstream on detached HEAD".into()))?
        } else {
            local.trim().to_string()
        };
        if crate::git_write::branch_name_out_of_scope(&local_name) {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        let has_local = st
            .branches
            .get(&key)
            .map(|names| names.iter().any(|n| n == &local_name))
            .unwrap_or(false);
        if !has_local {
            return Err(PortError::Git(format!("branch '{local_name}' not found")));
        }
        let had_upstream = st
            .upstreams
            .get(&key)
            .map(|m| m.contains_key(&local_name))
            .unwrap_or(false);
        if !had_upstream {
            return Err(PortError::Git(format!(
                "branch '{local_name}' has no upstream information"
            )));
        }
        if let Some(map) = st.upstreams.get_mut(&key) {
            map.remove(&local_name);
        }
        st.last_unset_upstream.insert(key, local_name);
        Ok(())
    }

    fn stage_all(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if st.conflict_kind.contains_key(&key) {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: resolve or abort before stage-all".into(),
            ));
        }
        let unmerged = st
            .conflict_files
            .get(&key)
            .map(|files| !files.is_empty())
            .unwrap_or(false);
        if unmerged {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: unmerged paths; do not use stage-all to mark conflicts resolved"
                    .into(),
            ));
        }
        st.last_stage_all.insert(key, true);
        Ok(())
    }

    fn conflict_save(
        &self,
        repo: &str,
        path: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let rel = path.trim();
        if rel.is_empty() {
            return Err(PortError::Other("empty conflict path".into()));
        }
        if crate::git_write::conflict_path_out_of_scope(rel) {
            return Err(PortError::Other(
                "add-all/force/flag conflict paths are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        if !st.conflict_kind.contains_key(&key) {
            return Err(PortError::Git("no in-progress conflict".into()));
        }
        if let Some(text) = st.conflict_text.get(&key).and_then(|m| m.get(rel)) {
            if crate::git_write::conflict_markers_present(text) {
                return Err(PortError::Git(
                    "conflict markers still present; not staged".into(),
                ));
            }
        }
        let files = st.conflict_files.entry(key.clone()).or_default();
        if !files.iter().any(|p| p == rel) {
            return Err(PortError::Git(format!(
                "path '{rel}' is not an unmerged conflict"
            )));
        }
        files.retain(|p| p != rel);
        st.conflict_save.insert(key, rel.to_string());
        Ok(())
    }

    fn conflict_continue(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let kind = st
            .conflict_kind
            .get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git("no in-progress conflict".into()))?;
        let remaining = st.conflict_files.get(&key).map(|v| v.len()).unwrap_or(0);
        if remaining > 0 {
            return Err(PortError::Git(
                "unmerged paths remain; cannot continue".into(),
            ));
        }
        st.conflict_continue.insert(key.clone(), kind);
        st.conflict_kind.remove(&key);
        st.conflict_files.remove(&key);
        Ok(())
    }

    fn conflict_abort(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let kind = st
            .conflict_kind
            .get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git("no in-progress conflict".into()))?;
        st.conflict_abort.insert(key.clone(), kind);
        st.conflict_kind.remove(&key);
        st.conflict_files.remove(&key);
        Ok(())
    }

    fn conflict_skip(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        let kind = st
            .conflict_kind
            .get(&key)
            .cloned()
            .ok_or_else(|| PortError::Git("no in-progress conflict".into()))?;
        if kind != "Rebase" && kind != "CherryPick" {
            return Err(PortError::Git(
                "conflict cannot be skipped (no skippable rebase/cherry-pick in progress)".into(),
            ));
        }
        st.conflict_skip.insert(key.clone(), kind);
        st.conflict_kind.remove(&key);
        st.conflict_files.remove(&key);
        Ok(())
    }

    fn fetch(
        &self,
        repo: &str,
        remote: &str,
        refspec: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let name = remote.trim();
        if name.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if crate::git_write::remote_name_out_of_scope(name) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let spec = refspec.map(str::trim).filter(|s| !s.is_empty());
        if let Some(s) = spec {
            if crate::git_write::fetch_refspec_out_of_scope(s) {
                return Err(PortError::Other(
                    "force/prune/update-head-ok fetch refspecs are out of scope".into(),
                ));
            }
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        st.local_head
            .entry(key.clone())
            .or_insert_with(|| "local-head".into());
        let has_remote = {
            let remotes = st.remotes.entry(key.clone()).or_default();
            remotes.iter().any(|(n, _)| n == name)
        };
        if !has_remote {
            return Err(PortError::Git(format!("No such remote: '{name}'")));
        }
        st.next_hash = st.next_hash.saturating_add(1);
        let oid = format!("{:012x}", st.next_hash);
        let tracking = format!("refs/remotes/{name}/main");
        let refs = st.remote_tracking.entry(key.clone()).or_default();
        if let Some(existing) = refs.iter_mut().find(|(r, _)| r == &tracking) {
            existing.1 = oid;
        } else {
            refs.push((tracking, oid));
        }
        st.last_fetch
            .insert(key, (name.to_string(), spec.map(str::to_string)));
        Ok(())
    }

    fn fetch_prune(
        &self,
        repo: &str,
        remote: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let name = remote.trim();
        if name.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if crate::git_write::remote_name_out_of_scope(name)
            || crate::git_write::fetch_refspec_out_of_scope(name)
        {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        st.local_head
            .entry(key.clone())
            .or_insert_with(|| "local-head".into());
        let has_remote = {
            let remotes = st.remotes.entry(key.clone()).or_default();
            remotes.iter().any(|(n, _)| n == name)
        };
        if !has_remote {
            return Err(PortError::Git(format!("No such remote: '{name}'")));
        }
        let stale: Vec<String> = st
            .stale_remote_tracking
            .get(&key)
            .cloned()
            .unwrap_or_default();
        if let Some(refs) = st.remote_tracking.get_mut(&key) {
            refs.retain(|(r, _)| !stale.iter().any(|s| s == r));
        }
        st.last_fetch_prune.insert(key, name.to_string());
        Ok(())
    }

    fn pull_ff_only(
        &self,
        repo: &str,
        remote: &str,
        branch: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        if !approval.is_granted() {
            return Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ));
        }
        let name = remote.trim();
        if name.is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if crate::git_write::remote_name_out_of_scope(name)
            || crate::git_write::fetch_refspec_out_of_scope(name)
        {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        let branch_owned = branch.map(str::trim).filter(|s| !s.is_empty());
        if let Some(b) = branch_owned {
            if crate::git_write::branch_name_out_of_scope(b) {
                return Err(PortError::Other(
                    "force/delete/upstream/switch branch writes are out of scope".into(),
                ));
            }
        }
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        let key = Self::key(repo);
        st.local_head
            .entry(key.clone())
            .or_insert_with(|| "local-head".into());
        let has_remote = {
            let remotes = st.remotes.entry(key.clone()).or_default();
            remotes.iter().any(|(n, _)| n == name)
        };
        if !has_remote {
            return Err(PortError::Git(format!("No such remote: '{name}'")));
        }
        if st.pull_dirty_overwrite.get(&key).copied().unwrap_or(false) {
            return Err(PortError::Git(
                "Your local changes to the following files would be overwritten by merge".into(),
            ));
        }
        if st.pull_local_ahead.get(&key).copied().unwrap_or(false) {
            return Err(PortError::Git(
                "Not possible to fast-forward, aborting".into(),
            ));
        }
        let br = branch_owned.as_deref().unwrap_or("main");
        let tracking = format!("refs/remotes/{name}/{br}");
        let branch_record = branch_owned.map(|s| s.to_string());
        let remote_oid = st.remote_tracking.get(&key).and_then(|refs| {
            refs.iter()
                .find(|(r, _)| r == &tracking)
                .map(|(_, o)| o.clone())
        });
        let remote_oid = remote_oid.unwrap_or_else(|| {
            st.next_hash = st.next_hash.saturating_add(1);
            format!("{:012x}", st.next_hash)
        });
        if let Some(refs) = st.remote_tracking.get_mut(&key) {
            if let Some(existing) = refs.iter_mut().find(|(r, _)| r == &tracking) {
                existing.1 = remote_oid.clone();
            } else {
                refs.push((tracking, remote_oid.clone()));
            }
        } else {
            st.remote_tracking
                .insert(key.clone(), vec![(tracking, remote_oid.clone())]);
        }
        st.local_head.insert(key.clone(), remote_oid);
        st.last_pull_ff_only
            .insert(key, (name.to_string(), branch_record));
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
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        st.last_artifact_path = path;
        Ok(())
    }

    /// Force Windows to Unsupported (optional negative fixture).
    pub fn force_windows_unsupported(&self, reason: impl Into<String>) -> Result<(), PortError> {
        let mut st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        st.force_windows_unsupported = Some(reason.into());
        Ok(())
    }
}

impl DeployPort for FakeDeploy {
    fn capability(&self, platform: DeployPlatform) -> Result<DeployCapability, PortError> {
        let st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
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
        let st = self
            .inner
            .lock()
            .map_err(|e| PortError::Other(e.to_string()))?;
        Ok(st.last_artifact_path.clone())
    }
}
