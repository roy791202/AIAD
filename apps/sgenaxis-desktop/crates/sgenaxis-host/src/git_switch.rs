//! GIT-002-03 — approval-gated branch switch at the HOST use-case layer.
//!
//! Git adapter stays free of WORK/OS lease types. Occupying Run is passed in
//! (from WORK `projection().active_run()` / dispatch `active_run_id`).

use sgenaxis_ports::{GitWriteApproval, GitWritePort};
use sgenaxis_work::WorkspaceProjection;

/// Contract string for BDD-GIT-002-03 (活動租約禁止切換).
pub const ACTIVE_LEASE_BLOCKS_SWITCH: &str = "活動租約禁止切換";

/// Result of a gated switch (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitSwitchResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitSwitchResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "switch".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "switch".into(),
            message: "switch ok".into(),
            local_preserved: true,
        }
    }
}

/// Occupying Run id from WORK projection, else host `active_run_id`.
pub fn occupying_run_id(
    projection: Option<&WorkspaceProjection>,
    host_active_run_id: Option<&str>,
) -> Option<String> {
    if let Some(proj) = projection {
        if let Some(lease) = proj.active_run() {
            let id = lease.run_id.trim();
            if !id.is_empty() {
                return Some(id.to_string());
            }
        }
    }
    host_active_run_id
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
}

/// Soft-gated switch: empty branch, occupying Run, or unapproved never mutates.
/// Approved + no occupying Run switches via GitWritePort (`git switch --`).
pub fn perform_git_switch(
    write: &dyn GitWritePort,
    repo: &str,
    branch: &str,
    approved: bool,
    occupying_run: Option<&str>,
) -> GitSwitchResult {
    if branch.trim().is_empty() {
        return GitSwitchResult::refuse("empty branch name");
    }
    if !approved {
        return GitSwitchResult::refuse("approval denied; no mutation");
    }
    if let Some(run_id) = occupying_run.map(str::trim).filter(|s| !s.is_empty()) {
        return GitSwitchResult::refuse(format!(
            "{ACTIVE_LEASE_BLOCKS_SWITCH}: occupying run {run_id}"
        ));
    }
    match write.switch_branch(repo, branch, GitWriteApproval::granted()) {
        Ok(()) => GitSwitchResult::ok(),
        Err(e) => GitSwitchResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;
    use sgenaxis_work::LeaseSummary;

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

    // TDD-GIT-002-03: no occupying Run → approved switch still succeeds.
    #[test]
    fn approved_switch_succeeds_without_occupying_run() {
        let w = FakeGitWrite::new();
        let none = occupying_run_id(Some(&WorkspaceProjection::default()), None);
        assert!(none.is_none());
        let ok = perform_git_switch(&w, "/r", "feature", true, none.as_deref());
        assert!(ok.ok);
        assert!(ok.local_preserved);
        assert_eq!(ok.op, "switch");
        assert_eq!(w.switched_branch("/r").as_deref(), Some("feature"));
    }

    // TDD-GIT-002-03: occupying Run refuses; names run id; FakeGitWrite records no switch.
    #[test]
    fn occupying_run_refuses_switch_and_does_not_call_git_write() {
        let w = FakeGitWrite::new();
        let proj = occupying_proj("run-42");
        let occupying = occupying_run_id(Some(&proj), None);
        assert_eq!(occupying.as_deref(), Some("run-42"));
        let refused = perform_git_switch(&w, "/r", "feature", true, occupying.as_deref());
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
            w.switched_branch("/r").is_none(),
            "GitWritePort must not be called"
        );
    }

    // TDD-GIT-002-03: after lease gone, approved switch succeeds again.
    #[test]
    fn switch_succeeds_again_after_occupying_run_cleared() {
        let w = FakeGitWrite::new();
        let occupied = occupying_run_id(Some(&occupying_proj("run-7")), Some("7"));
        let blocked = perform_git_switch(&w, "/r", "feature", true, occupied.as_deref());
        assert!(!blocked.ok);
        assert!(w.switched_branch("/r").is_none());

        let cleared = occupying_run_id(Some(&WorkspaceProjection::default()), None);
        let ok = perform_git_switch(&w, "/r", "feature", true, cleared.as_deref());
        assert!(ok.ok);
        assert_eq!(w.switched_branch("/r").as_deref(), Some("feature"));
    }

    #[test]
    fn host_active_run_id_occupies_when_projection_empty() {
        let occupying = occupying_run_id(Some(&WorkspaceProjection::default()), Some("99"));
        assert_eq!(occupying.as_deref(), Some("99"));
    }
}
