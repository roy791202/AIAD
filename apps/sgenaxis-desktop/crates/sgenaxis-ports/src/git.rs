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

/// One commit from `git log`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitCommit {
    pub hash: String,
    pub subject: String,
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
}

/// Write / push operations — require [`GitWriteApproval`] (PD-GIT-02).
///
/// Invariants:
/// - Unapproved → `PermissionDenied` (no mutation).
/// - Push failure must not discard local commits.
/// - Error strings must not leak credentials (adapters redact).
/// - No force push.
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
}
