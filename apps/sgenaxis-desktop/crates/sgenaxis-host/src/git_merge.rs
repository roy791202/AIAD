//! PD-GIT-MERGE-FF-01 — approval-gated `git merge --ff-only -- <local-branch>`.
//!
//! Git adapter stays free of WORK/OS lease types. Occupying Run is passed in
//! (from WORK `projection().active_run()` / dispatch `active_run_id`).

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Contract string when an occupying workspace Run/lease blocks merge.
pub const ACTIVE_LEASE_BLOCKS_MERGE: &str = "活動租約禁止合併";

/// Result of a gated ff-only merge (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitMergeFfOnlyResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitMergeFfOnlyResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "merge-ff-only".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "merge-ff-only".into(),
            message: "merge ff-only ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated ff-only merge: empty branch, occupying Run, or unapproved never mutates.
/// Approved + no occupying Run merges via GitWritePort (`git merge --ff-only --`).
pub fn perform_git_merge_ff_only(
    write: &dyn GitWritePort,
    repo: &str,
    branch: &str,
    approved: bool,
    occupying_run: Option<&str>,
) -> GitMergeFfOnlyResult {
    if branch.trim().is_empty() {
        return GitMergeFfOnlyResult::refuse("empty branch name");
    }
    if !approved {
        return GitMergeFfOnlyResult::refuse("approval denied; no mutation");
    }
    if let Some(run_id) = occupying_run.map(str::trim).filter(|s| !s.is_empty()) {
        return GitMergeFfOnlyResult::refuse(format!(
            "{ACTIVE_LEASE_BLOCKS_MERGE}: occupying run {run_id}"
        ));
    }
    match write.merge_ff_only(repo, branch, GitWriteApproval::granted()) {
        Ok(()) => GitMergeFfOnlyResult::ok(),
        Err(e) => GitMergeFfOnlyResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::git_switch::occupying_run_id;
    use sgenaxis_adapters::FakeGitWrite;
    use sgenaxis_ports::GitWriteApproval;
    use sgenaxis_work::{LeaseSummary, WorkspaceProjection};

    fn occupying_proj(run_id: &str) -> WorkspaceProjection {
        WorkspaceProjection {
            active_leases: vec![LeaseSummary {
                project_id: "p1".into(),
                run_id: run_id.into(),
                bound_root: "/r".into(),
                work_item_id: "wi".into(),
                worktree_fingerprint: "fp".into(),
            }],
            ..WorkspaceProjection::default()
        }
    }

    #[test]
    fn approved_merge_succeeds_without_occupying_run() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "topic", GitWriteApproval::granted())
            .unwrap();
        let none = occupying_run_id(Some(&WorkspaceProjection::default()), None);
        assert!(none.is_none());
        let ok = perform_git_merge_ff_only(&w, "/r", "topic", true, none.as_deref());
        assert!(ok.ok);
        assert!(ok.local_preserved);
        assert_eq!(ok.op, "merge-ff-only");
        assert_eq!(w.last_merge_ff_only("/r").as_deref(), Some("topic"));
    }

    #[test]
    fn occupying_run_refuses_merge_and_does_not_call_git_write() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "topic", GitWriteApproval::granted())
            .unwrap();
        let proj = occupying_proj("run-42");
        let occupying = occupying_run_id(Some(&proj), None);
        assert_eq!(occupying.as_deref(), Some("run-42"));
        let refused = perform_git_merge_ff_only(&w, "/r", "topic", true, occupying.as_deref());
        assert!(!refused.ok);
        assert!(refused.local_preserved);
        assert!(
            refused.message.contains(ACTIVE_LEASE_BLOCKS_MERGE),
            "contract: {}",
            refused.message
        );
        assert!(
            refused.message.contains("run-42"),
            "must name occupying run: {}",
            refused.message
        );
        assert!(
            w.last_merge_ff_only("/r").is_none(),
            "GitWritePort must not be called"
        );
    }

    #[test]
    fn merge_succeeds_again_after_occupying_run_cleared() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "topic", GitWriteApproval::granted())
            .unwrap();
        let occupied = occupying_run_id(Some(&occupying_proj("run-7")), Some("7"));
        let blocked = perform_git_merge_ff_only(&w, "/r", "topic", true, occupied.as_deref());
        assert!(!blocked.ok);
        assert!(w.last_merge_ff_only("/r").is_none());

        let cleared = occupying_run_id(Some(&WorkspaceProjection::default()), None);
        let ok = perform_git_merge_ff_only(&w, "/r", "topic", true, cleared.as_deref());
        assert!(ok.ok);
        assert_eq!(w.last_merge_ff_only("/r").as_deref(), Some("topic"));
    }

    #[test]
    fn unapproved_and_empty_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "topic", GitWriteApproval::granted())
            .unwrap();
        let denied = perform_git_merge_ff_only(&w, "/r", "topic", false, None);
        assert!(!denied.ok);
        assert!(w.last_merge_ff_only("/r").is_none());
        let empty = perform_git_merge_ff_only(&w, "/r", "  ", true, None);
        assert!(!empty.ok);
        assert!(w.last_merge_ff_only("/r").is_none());
    }
}
