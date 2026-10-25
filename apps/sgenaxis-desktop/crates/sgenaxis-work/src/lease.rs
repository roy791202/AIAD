//! Execution lease — freezes Run-bound root／work item／fingerprint while active.

use crate::id::ProjectId;

/// Active execution lease on a project (protects root from rebind).
///
/// PD-EXEC-BIND-01: lease also stamps work item + worktree fingerprint so
/// `start_run` bindings stay consistent with WORK.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExecutionLease {
    pub project_id: ProjectId,
    pub run_id: String,
    /// Root frozen at lease acquire — UI select must not rewrite this.
    pub bound_root: String,
    pub work_item_id: String,
    pub worktree_fingerprint: String,
}
