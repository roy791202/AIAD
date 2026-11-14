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
/// - Tag delete requires approval (no skip default). Local only:
///   `git tag -d -- <name>` (or `git tag --delete -- <name>`). Never `-f`.
///   Never push. Never `git push --delete`. Missing tag must fail honestly.
/// - Tag push requires approval (no skip default). Non-force only:
///   `git push -- <remote> refs/tags/<tag>`. Empty remote defaults to
///   `origin`. Never `--force` / `--force-with-lease` / `+refspec` /
///   `--delete` / `--all` / `--mirror` / `--tags` (bulk) / branch refspecs.
///   Never fetch/pull/rebase/merge/checkout. Never rewrite an existing tag.
///   Unknown remotes, missing local tags, and existing remote tags fail
///   honestly (no remote is created).
/// - Branch create requires approval (no skip default). Local only:
///   `git branch -- <name>` from current HEAD. Never `-C` / `--force` / `-D` /
///   `-d`. Never remote create, never `--set-upstream`. Never checkout/switch
///   as a hidden side effect. Duplicate and invalid names fail honestly.
/// - Branch delete requires approval (no skip default). Local only:
///   `git branch -d -- <name>` (safe delete). Never `-D` / `--force` / `-f`.
///   Never `-r` / remote tracking delete / `push :branch`. Never checkout/switch.
///   Current HEAD, missing names, empty names, and option-like names fail
///   honestly. Unmerged branches fail as git `-d` (no force fallback).
/// - Branch rename requires approval (no skip default). Local only:
///   `git branch -m -- <old> <new>`. Never `-M` / `--force`. Never remote
///   rename. Existing target names, missing local names, remote-only names,
///   empty names, and option-like names fail honestly.
/// - Remote add requires approval (no skip default). Local config only:
///   `git remote add -- <name> <url>`. Never `-f`. Never fetch as a hidden
///   side effect. Never `remote set-url`. Never `git push`. Duplicate names
///   and invalid name/url (including leading `-`) fail honestly.
/// - Remote remove requires approval (no skip default). Local config only:
///   `git remote remove -- <name>` (or `git remote rm`). Never prune/fetch.
///   Missing remotes fail honestly.
/// - Remote set-url requires approval (no skip default). Local config only:
///   `git remote set-url -- <name> <url>`. Never `--add` / `--delete` /
///   `--push` / `--mirror`. Never fetch. Never `git push`. Unknown names
///   and invalid name/url (including leading `-` and shell metacharacters)
///   fail honestly.
/// - Remote rename requires approval (no skip default). Local config only:
///   `git remote rename -- <old> <new>`. URL unchanged (use set-url for URL).
///   Never fetch / set-url / push. Unknown `old`, duplicate `new`, empty names,
///   identical old==new, invalid names, and option-like names fail honestly.
/// - Fetch requires approval (no skip default). Updates remote-tracking
///   refs only: `git fetch -- <remote>` with an optional non-force refspec.
///   Never merge / pull / rebase / checkout. Never `--force` / `+refspec` /
///   `--update-head-ok`. Never prune in this command. Unknown remotes fail
///   honestly and must not be created. HEAD and the worktree stay unchanged.
/// - Fetch-prune requires approval (no skip default). Distinct from fetch:
///   `git fetch --prune -- <remote>` deletes stale remote-tracking refs only.
///   Never `--prune-tags`. Never `--force` / `+refspec` / `--update-head-ok` /
///   `--add` / `--delete` / `--push` / `--mirror`. Never pull / merge / rebase.
///   HEAD, local branches, and the worktree stay unchanged.
/// - Pull (ff-only) requires approval (no skip default). Distinct from fetch:
///   `git pull --ff-only -- <remote> [<branch>]`. Never `--rebase` / `--no-ff` /
///   `--force` / `+refspec` / `--update-head-ok`. Never merge commits. Diverged
///   branches and dirty overwrites fail honestly; local commits and files stay
///   intact. Unknown remotes fail honestly.
/// - Stage-all requires approval (no skip default). Distinct from conflict
///   save and from commit: `git add -- .` from the repo root only. Never
///   `git add -A` as a bulk conflict resolve. Never commit / push /
///   `reset --hard` / `--force`. Paths outside the repo are never added.
///   In-progress merge/rebase/cherry-pick/revert (unmerged paths) fails
///   honestly (`OPERATION_IN_PROGRESS`); do not use stage-all to mark
///   conflicts resolved. A clean worktree is a success no-op (`git add`
///   on an empty dirty tree succeeds).
/// - Conflict save/continue/abort require approval (no skip default).
///   Save stages one resolved path: `git add -- <path>` after the UI (or host)
///   wrote the worktree file. Never `git add -A` / `.`. Remaining conflict
///   markers (`<<<<<<<` / `=======` / `>>>>>>>`) fail honestly.
///   Continue uses `git rebase --continue` / `git merge --continue` /
///   `git cherry-pick --continue` (or `git revert --continue`) matching the
///   detected in-progress state. Never `--skip`. Never `-X theirs/ours`.
///   Skip uses `git rebase --skip` / `git cherry-pick --skip` only when Git
///   itself allows skipping. Merge (and other non-skippable states) fail
///   honestly. Never fall back to `--continue` / `--abort`. Never skip by
///   deleting files or `git add` + continue.
///   Abort uses the matching `--abort` family. Never `reset --hard`.
///   Missing conflict state fails honestly.
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

    /// Delete a local tag. Requires approval.
    /// `git tag -d -- <name>` (or `git tag --delete -- <name>`).
    /// Never `-f` / `--force`. Never push. Never remote `-d`.
    /// Missing tag must fail honestly.
    fn delete_tag(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Push one local tag. Requires approval.
    /// `git push -- <remote> refs/tags/<tag>` (empty remote → `origin`).
    /// Never `--force` / `--force-with-lease` / `+refspec` / `--delete` /
    /// `--all` / `--mirror` / `--tags` (bulk). Never branch refspecs.
    /// Never fetch / pull / rebase / merge / checkout. Never rewrite tags.
    /// Unknown remotes, missing local tags, and existing remote tags fail
    /// honestly.
    fn push_tag(
        &self,
        repo: &str,
        remote: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Create a new local branch at current HEAD. Requires approval.
    /// `git branch -- <name>`. Never `-C` / `--force` / `-D` / `-d`.
    /// Never remote create. Never `--set-upstream`. Never switch/checkout.
    /// Duplicate and invalid names fail honestly.
    fn create_branch(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Delete a local branch. Requires approval.
    /// `git branch -d -- <name>`. Never `-D` / `--force` / `-f`.
    /// Never `-r`. Never remote delete. Never switch/checkout.
    /// Current HEAD, missing names, and unmerged branches fail honestly.
    fn delete_branch(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Rename a local branch. Requires approval.
    /// `git branch -m -- <old> <new>`. Never `-M` / `--force` / `-f`.
    /// Never remote rename. Never switch/checkout as a separate step.
    /// Existing target names, missing local names, remote-only names,
    /// and invalid names fail honestly.
    fn rename_branch(
        &self,
        repo: &str,
        old: &str,
        new: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Add a local remote. Requires approval.
    /// `git remote add -- <name> <url>`. Never `-f`. Never fetch. Never
    /// `set-url`. Never push. Duplicate names fail honestly.
    fn add_remote(
        &self,
        repo: &str,
        name: &str,
        url: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Remove a local remote. Requires approval.
    /// `git remote remove -- <name>` (or `git remote rm`). Never prune/fetch.
    /// Missing remotes fail honestly.
    fn remove_remote(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Update an existing local remote URL. Requires approval.
    /// `git remote set-url -- <name> <url>`. Never `--add` / `--delete` /
    /// `--push` / `--mirror`. Never fetch. Never push. Unknown remotes fail honestly.
    fn set_remote_url(
        &self,
        repo: &str,
        name: &str,
        url: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Rename an existing local remote. Requires approval.
    /// `git remote rename -- <old> <new>`. Never fetch / set-url / push.
    /// URL unchanged. Unknown `old`, duplicate `new`, and invalid names fail honestly.
    fn rename_remote(
        &self,
        repo: &str,
        old: &str,
        new: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Set upstream tracking for a local branch. Requires approval.
    /// `git branch --set-upstream-to=<remote>/<branch> -- <local>`.
    /// Empty `local` → current branch. Never `--unset-upstream`. Never `-M` /
    /// `-C` / `--force`. Never fetch / pull / push / rebase / merge / checkout /
    /// switch. Never create remotes, remote-tracking refs, or local branches.
    /// Unknown remotes, missing tracking refs, missing local branches, and
    /// empty / invalid / option-like names fail honestly.
    fn set_upstream(
        &self,
        repo: &str,
        remote: &str,
        branch: &str,
        local: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Clear upstream tracking for a local branch. Requires approval.
    /// `git branch --unset-upstream -- <local>`.
    /// Empty `local` → current branch. Never `--set-upstream-to` / `-u`.
    /// Never `-M` / `-C` / `--force`. Never fetch / pull / push / rebase /
    /// merge / checkout / switch. Never create remotes, tracking refs, or
    /// local branches. Missing local branches, detached HEAD (empty local),
    /// and branches with no upstream fail honestly.
    fn unset_upstream(
        &self,
        repo: &str,
        local: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Stage current worktree changes without committing. Requires approval.
    /// `git add -- .` from the repo root. Never `-A` as conflict-resolve.
    /// Never commit / push / `reset --hard` / `--force`. Never add paths
    /// outside the repo. In-progress merge/rebase/cherry-pick/revert with
    /// unmerged paths fails honestly (`OPERATION_IN_PROGRESS`). A clean
    /// worktree succeeds as a no-op.
    fn stage_all(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError>;

    /// Unstage the index without touching worktree contents. Requires approval.
    /// `git reset -- .` from the repo root (mixed pathspec reset: index → HEAD).
    /// Never commit / push / `git add -A` / `reset --hard` / `--force` / `-f` /
    /// `-D`. Never merge / rebase / pull / fetch. In-progress
    /// merge/rebase/cherry-pick/revert with unmerged paths fails honestly
    /// (`OPERATION_IN_PROGRESS`). A clean index relative to HEAD succeeds as
    /// a no-op. Untracked files remain untracked.
    fn unstage_all(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError>;

    /// Unstage one text hunk of `path` from the index. Requires approval.
    /// `git apply --cached -R` of that hunk (or equivalent). Remaining staged
    /// hunks stay staged. Worktree bytes outside that hunk stay unchanged.
    /// Never commit / push / `git add -A` / `reset --hard` / `--force` / `-f`.
    /// Never path-escape. Binary paths, missing paths, and hunks not in the
    /// index fail honestly. In-progress merge/rebase/cherry-pick/revert with
    /// unmerged paths fails honestly (`OPERATION_IN_PROGRESS`).
    fn hunk_unstage(
        &self,
        repo: &str,
        path: &str,
        hunk_spec: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Stage one resolved conflict path (`git add -- <path>`). Requires approval.
    /// Never `git add -A` / `.`. Remaining conflict markers fail honestly.
    /// Missing in-progress merge/rebase/cherry-pick/revert fails honestly.
    fn conflict_save(
        &self,
        repo: &str,
        path: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Continue the in-progress merge/rebase/cherry-pick/revert.
    /// Requires approval. Never `--skip`. Never `-X theirs/ours`.
    /// Missing conflict state fails honestly.
    fn conflict_continue(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError>;

    /// Abort the in-progress merge/rebase/cherry-pick/revert (`--abort`).
    /// Requires approval. Never `reset --hard`. Missing state fails honestly.
    fn conflict_abort(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError>;

    /// Skip the current patch of an in-progress rebase or cherry-pick (`--skip`).
    /// Requires approval. Never `--continue` / `--abort` as a fallback.
    /// Merge (and other operations Git cannot `--skip`) fail honestly.
    fn conflict_skip(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError>;

    /// Update remote-tracking refs only. Requires approval.
    /// `git fetch -- <remote>` with an optional non-force refspec.
    /// Never merge / pull / rebase / checkout. Never `--force` / `+refspec` /
    /// `--update-head-ok`. Never prune. Unknown remotes fail honestly.
    fn fetch(
        &self,
        repo: &str,
        remote: &str,
        refspec: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Delete stale remote-tracking refs. Requires approval.
    /// `git fetch --prune -- <remote>`. Never `--prune-tags`. Never `--force` /
    /// `+refspec` / `--update-head-ok` / `--add` / `--delete` / `--push` /
    /// `--mirror`. Never pull / merge / rebase. HEAD and the worktree stay
    /// unchanged. Unknown remotes fail honestly.
    fn fetch_prune(
        &self,
        repo: &str,
        remote: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;

    /// Fast-forward pull only. Requires approval.
    /// `git pull --ff-only -- <remote> [<branch>]`. Never `--rebase` / `--no-ff`
    /// / `--force` / `+refspec` / `--update-head-ok`. Never merge commits.
    /// Diverged histories and dirty overwrites fail honestly. Unknown remotes
    /// fail honestly.
    fn pull_ff_only(
        &self,
        repo: &str,
        remote: &str,
        branch: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError>;
}
