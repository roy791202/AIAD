//! Gated local branch rename (`git branch -m`). Occupying Run blocks renaming
//! the current HEAD branch (same lease gate as GIT-002-03 switch).

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

use crate::git_switch::ACTIVE_LEASE_BLOCKS_SWITCH;

/// Result of a gated rename (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitRenameResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitRenameResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "branch-rename".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "branch-rename".into(),
            message: "branch-rename ok".into(),
            local_preserved: true,
        }
    }
}

fn is_detached(current_head: Option<&str>) -> bool {
    match current_head.map(str::trim).filter(|s| !s.is_empty()) {
        None => true,
        Some("HEAD") => true,
        Some(_) => false,
    }
}

/// Soft-gated rename: empty names, occupying Run on current HEAD, or unapproved
/// never mutates. Approved rename uses GitWritePort (`git branch -m -- old new`).
pub fn perform_git_rename_branch(
    write: &dyn GitWritePort,
    repo: &str,
    old: &str,
    new: &str,
    approved: bool,
    occupying_run: Option<&str>,
    current_head: Option<&str>,
) -> GitRenameResult {
    let old = old.trim();
    let new = new.trim();
    if old.is_empty() || new.is_empty() {
        return GitRenameResult::refuse("empty branch name");
    }
    if !approved {
        return GitRenameResult::refuse("approval denied; no mutation");
    }
    if is_detached(current_head) && old.eq_ignore_ascii_case("HEAD") {
        return GitRenameResult::refuse("cannot rename detached HEAD");
    }
    let current = current_head.map(str::trim).filter(|s| !s.is_empty());
    let renaming_current = current.map(|c| c == old).unwrap_or(false);
    if renaming_current {
        if let Some(run_id) = occupying_run.map(str::trim).filter(|s| !s.is_empty()) {
            return GitRenameResult::refuse(format!(
                "{ACTIVE_LEASE_BLOCKS_SWITCH}: occupying run {run_id}"
            ));
        }
    }
    match write.rename_branch(repo, old, new, GitWriteApproval::granted()) {
        Ok(()) => GitRenameResult::ok(),
        Err(e) => GitRenameResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;
    use sgenaxis_ports::GitWriteApproval;
    use sgenaxis_work::LeaseSummary;
    use sgenaxis_work::WorkspaceProjection;

    use crate::git_switch::occupying_run_id;

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
    fn approved_rename_succeeds_without_occupying_run() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "feature/slot", GitWriteApproval::granted())
            .expect("seed");
        let none = occupying_run_id(Some(&WorkspaceProjection::default()), None);
        assert!(none.is_none());
        let ok = perform_git_rename_branch(
            &w,
            "/r",
            "feature/slot",
            "feature/renamed",
            true,
            none.as_deref(),
            Some("main"),
        );
        assert!(ok.ok);
        assert!(ok.local_preserved);
        assert_eq!(ok.op, "branch-rename");
        assert_eq!(
            w.last_branch_rename("/r"),
            Some(("feature/slot".into(), "feature/renamed".into()))
        );
    }

    #[test]
    fn occupying_run_refuses_rename_of_current_and_does_not_call_git_write() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "main", GitWriteApproval::granted())
            .expect("seed");
        let proj = occupying_proj("run-42");
        let occupying = occupying_run_id(Some(&proj), None);
        assert_eq!(occupying.as_deref(), Some("run-42"));
        let refused = perform_git_rename_branch(
            &w,
            "/r",
            "main",
            "trunk",
            true,
            occupying.as_deref(),
            Some("main"),
        );
        assert!(!refused.ok);
        assert!(refused.local_preserved);
        assert!(
            refused.message.contains(ACTIVE_LEASE_BLOCKS_SWITCH),
            "contract: {}",
            refused.message
        );
        assert!(
            refused.message.contains("run-42"),
            "must name occupying run: {}",
            refused.message
        );
        assert!(
            w.last_branch_rename("/r").is_none(),
            "GitWritePort must not be called"
        );
    }

    #[test]
    fn occupying_run_allows_rename_of_non_current_branch() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "feature/slot", GitWriteApproval::granted())
            .expect("seed");
        let occupying = occupying_run_id(Some(&occupying_proj("run-7")), None);
        let ok = perform_git_rename_branch(
            &w,
            "/r",
            "feature/slot",
            "feature/renamed",
            true,
            occupying.as_deref(),
            Some("main"),
        );
        assert!(ok.ok);
        assert_eq!(
            w.last_branch_rename("/r"),
            Some(("feature/slot".into(), "feature/renamed".into()))
        );
    }

    #[test]
    fn rename_succeeds_again_after_occupying_run_cleared() {
        let w = FakeGitWrite::new();
        w.create_branch("/r", "main", GitWriteApproval::granted())
            .expect("seed");
        let occupied = occupying_run_id(Some(&occupying_proj("run-7")), Some("7"));
        let blocked = perform_git_rename_branch(
            &w,
            "/r",
            "main",
            "trunk",
            true,
            occupied.as_deref(),
            Some("main"),
        );
        assert!(!blocked.ok);
        assert!(w.last_branch_rename("/r").is_none());

        let cleared = occupying_run_id(Some(&WorkspaceProjection::default()), None);
        let ok = perform_git_rename_branch(
            &w,
            "/r",
            "main",
            "trunk",
            true,
            cleared.as_deref(),
            Some("main"),
        );
        assert!(ok.ok);
        assert_eq!(
            w.last_branch_rename("/r"),
            Some(("main".into(), "trunk".into()))
        );
    }
}
