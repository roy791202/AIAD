//! Additive, staged-Index-only Git commit boundary (PD-ELU-GIT-ARCH-01 A1).
//! This port deliberately does not replace `GitWritePort::commit` (add -A).

use crate::git::GitWriteApproval;
use crate::PortError;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum GitOperationState {
    None,
    Merge,
    Rebase,
    CherryPick,
    Revert,
    Bisect,
    Unknown,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndexCommitFingerprint {
    pub repo_root: String,
    pub project_root: String,
    pub head_oid: Option<String>,
    pub index_tree_oid: String,
    /// Normalized repository-relative paths in bytewise order.
    pub staged_paths: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndexCommitFacts {
    pub fingerprint: IndexCommitFingerprint,
    pub index_nonempty: bool,
    pub unmerged: bool,
    pub operation: GitOperationState,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IndexCommitError {
    InvalidInput(String),
    ApprovalRequired,
    Unavailable(String),
    NonRepo(String),
    Unreadable(String),
    OutsideProjectScope(String),
    UnsupportedPolicy(String),
    InvalidPreview,
    StalePreview,
    Busy,
    Conflicted,
    OperationInProgress,
    NothingStaged,
    FailedObserved(String),
    OutcomeUnknown(String),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IndexCommitObservation {
    /// True only after the Git process was successfully spawned for the commit command.
    pub invocation_started: bool,
    pub exit_code: Option<i32>,
    pub after: Option<IndexCommitFacts>,
    pub observed_parent_oid: Option<String>,
    pub observed_tree_oid: Option<String>,
    pub diagnostic: Option<String>,
}

/// Separate route for committing the existing Index; never stages files.
pub trait GitIndexCommitPort: Send + Sync {
    fn inspect_index(&self, project_root: &str) -> Result<IndexCommitFacts, IndexCommitError>;

    fn commit_index(
        &self,
        project_root: &str,
        message: &str,
        expected: &IndexCommitFingerprint,
        approval: GitWriteApproval,
    ) -> Result<IndexCommitObservation, IndexCommitError>;
}

impl From<PortError> for IndexCommitError {
    fn from(value: PortError) -> Self {
        Self::Unreadable(value.to_string())
    }
}
