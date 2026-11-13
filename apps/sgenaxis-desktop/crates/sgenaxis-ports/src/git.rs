//! Git Port — read-oriented status / log / diff; write behind approval gate.

use crate::PortError;

/// Kind of a working-tree / index change.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GitStatusKind {
    Modified,
    Added,
    Deleted,
    Renamed,
    Untracked,
    Other,
}

/// One path entry from `git status`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitStatusEntry {
    pub path: String,
    pub kind: GitStatusKind,
}

/// Upstream tracking divergence parsed from the porcelain branch header.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitUpstream {
    pub name: String,
    pub ahead: usize,
    pub behind: usize,
}

/// Aggregated status snapshot.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitStatus {
    pub branch: Option<String>,
    pub entries: Vec<GitStatusEntry>,
    /// Upstream divergence (`Some` only when the branch tracks a remote).
    pub upstream: Option<GitUpstream>,
}

/// One local branch entry for the branches view (read-only).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitBranch {
    pub name: String,
    /// True for the currently checked-out branch (none when detached).
    pub is_current: bool,
}

/// One configured remote for the remotes view (read-only).
///
/// `tested` is last-known local connectivity (remote-tracking refs exist
/// under `refs/remotes/<name>/`). False when unknown — never invent, never
/// block the remotes list.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitRemote {
    pub name: String,
    /// Fetch URL for the remote.
    pub url: String,
    /// True when local remote-tracking refs exist for this remote.
    pub tested: bool,
}

/// One tag for the tags view (read-only).
///
/// `peeled` is the commit OID the tag points at. Empty when the adapter
/// could not peel (degrade, never invent).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitTag {
    pub name: String,
    /// Peeled commit OID. Empty when unavailable.
    pub peeled: String,
}

/// One stash entry for the stash view (read-only).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitStash {
    /// Stash ref, e.g. `stash@{0}`.
    pub id: String,
    /// Human-readable description.
    pub message: String,
}

/// One unmerged path for the conflicts view (read-only).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitConflictFile {
    pub path: String,
    /// Porcelain unmerged code (`UU`, `AA`, `DU`, …).
    pub code: String,
    /// Human-readable unmerged type (e.g. `雙方皆修改`).
    pub kind: String,
    /// Stage 2 blob text (ours / replay target). Empty when missing or binary.
    pub ours: String,
    /// Stage 3 blob text (theirs / incoming). Empty when missing or binary.
    pub theirs: String,
}

/// Merge / rebase / cherry-pick / revert snapshot for the conflicts view.
///
/// `active` is false when no in-progress operation and no unmerged paths.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitConflictState {
    pub active: bool,
    /// `Merge` | `Rebase` | `CherryPick` | `Revert`.
    pub kind: String,
    /// Incoming side (`MERGE_HEAD` / `REBASE_HEAD` / …).
    pub source: String,
    /// Current branch / HEAD name.
    pub target: String,
    pub files: Vec<GitConflictFile>,
}

/// Local identity + root `.gitignore` for the settings view (read-only).
///
/// Empty strings when unset / missing. Never includes global config.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitSettings {
    /// `git config --local user.name`.
    pub author: String,
    /// `git config --local user.email`.
    pub email: String,
    /// Working-tree `.gitignore` at the repo root.
    pub ignore: String,
}

/// One commit from `git log`.
///
/// `author` / `date` are empty when the log line omits them (degrade, never invent).
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct GitCommit {
    pub hash: String,
    pub subject: String,
    /// Author name (`%an`). Empty when unavailable.
    pub author: String,
    /// Author date, strict ISO 8601 (`%aI`). Empty when unavailable.
    pub date: String,
}

/// Explicit FLOW / human approval for a single write mutation (PD-GIT-02).
///
/// Default-deny: construct with [`GitWriteApproval::denied`] unless the caller
/// has a granted gate for this commit or push.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct GitWriteApproval {
    granted: bool,
}

impl GitWriteApproval {
    /// No approval — adapters must refuse the write.
    pub const fn denied() -> Self {
        Self { granted: false }
    }

    /// Granted for this single mutation only (not a standing permission).
    pub const fn granted() -> Self {
        Self { granted: true }
    }

    pub const fn is_granted(self) -> bool {
        self.granted
    }
}

/// Read-oriented Git operations (PD-GIT-01). Commit / push live on [`GitWritePort`].
pub trait GitPort: Send + Sync {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError>;

    fn log(&self, repo: &str, limit: usize) -> Result<Vec<GitCommit>, PortError>;

    /// Unified diff text; `pathspec` optional.
    fn diff(&self, repo: &str, pathspec: Option<&str>) -> Result<String, PortError>;

    /// Local branches (current-first). Default empty keeps existing impls valid;
    /// read adapters override. Never mutates.
    fn branches(&self, _repo: &str) -> Result<Vec<GitBranch>, PortError> {
        Ok(Vec::new())
    }

    /// Configured remotes (name-sorted, with last-known `tested`). Default
    /// empty keeps existing impls valid; read adapters override. Never mutates.
    fn remotes(&self, _repo: &str) -> Result<Vec<GitRemote>, PortError> {
        Ok(Vec::new())
    }

    /// Tags (name-sorted). Default empty keeps existing impls valid;
    /// read adapters override. Never mutates.
    fn tags(&self, _repo: &str) -> Result<Vec<GitTag>, PortError> {
        Ok(Vec::new())
    }

    /// Stashes (newest-first). Default empty keeps existing impls valid;
    /// read adapters override. Never mutates.
    fn stashes(&self, _repo: &str) -> Result<Vec<GitStash>, PortError> {
        Ok(Vec::new())
    }

    /// Conflict snapshot (inactive when none). Default empty keeps existing
    /// impls valid; read adapters override. Never mutates.
    fn conflicts(&self, _repo: &str) -> Result<GitConflictState, PortError> {
        Ok(GitConflictState::default())
    }

    /// Local `user.name` / `user.email` and root `.gitignore`. Default empty
    /// keeps existing impls valid; read adapters override. Never mutates.
    fn settings(&self, _repo: &str) -> Result<GitSettings, PortError> {
        Ok(GitSettings::default())
    }
}

/// Write / push operations — require [`GitWriteApproval`] (PD-GIT-02).
///
/// Invariants:
/// - Unapproved → `PermissionDenied` (no mutation).
/// - Push failure must not discard local commits.
/// - Error strings must not leak credentials (adapters redact).
/// - No force push.
/// - Settings writes are local-only: never `--global` / `--system`, never
///   credential helpers, never `git rm --cached` / untrack existing files.
/// - Stash apply/pop/drop/push require approval (no skip default). Never quiet.
///   Conflicts surface as errors; pop must not invent success or drop.
///   Drop of a missing stash must fail honestly. Push is tracked-only
///   (`git stash push -m`); never `-u` / `--all`, never `stash clear`, never force.
/// - Tag create requires approval (no skip default). Lightweight:
///   `git tag -- <name>`. Annotated: `git tag -a -m <msg> -- <name>`.
///   Never `-f` / `--force`. Never `--delete`. Never push. Duplicate names
///   must fail honestly.
pub trait GitWritePort: Send + Sync {
    fn commit(
        &self,
        repo: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    fn push(
        &self,
        repo: &str,
        remote: &str,
        refspec: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Switch the worktree to an existing local branch. Requires approval.
    /// Never creates, force-switches, or detaches.
    fn switch_branch(
        &self,
        repo: &str,
        branch: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Persist local `user.name` / `user.email`. Requires approval.
    /// Never writes `--global` / `--system` / credential helpers.
    fn set_identity(
        &self,
        repo: &str,
        name: &str,
        email: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Persist the repo-root `.gitignore`. Requires approval.
    /// Never `git rm --cached`; never stop tracking existing files.
    fn set_ignore(
        &self,
        repo: &str,
        contents: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Apply an existing stash (`git stash apply -- stash@{n}`). Requires approval.
    /// Never `-q` / `--quiet` (conflicts must not be hidden). Never drop/clear/push.
    fn stash_apply(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Pop an existing stash (`git stash pop -- stash@{n}`). Requires approval.
    /// On conflict git keeps the stash; adapters must not invent success.
    /// Never drop/clear/push as a separate step.
    fn stash_pop(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Drop an existing stash (`git stash drop -- stash@{n}`). Requires approval.
    /// Missing stash must fail honestly. Never `stash clear`. Never force.
    fn stash_drop(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Create a stash of tracked changes (`git stash push -m <message>`).
    /// Requires approval. Never `-u` / `--all`. Never `stash clear`. Never force.
    fn stash_push(
        &self,
        repo: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Create a local tag. Requires approval.
    /// Empty `message` → lightweight (`git tag -- <name>`).
    /// Non-empty `message` → annotated (`git tag -a -m <msg> -- <name>`).
    /// Never `-f` / `--force` / `--delete`. Never push. Duplicate names fail honestly.
    fn create_tag(
        &self,
        repo: &str,
        name: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;
}
