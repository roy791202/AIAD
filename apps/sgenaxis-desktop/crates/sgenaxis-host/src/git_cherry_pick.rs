//! Gated cherry-pick (`git cherry-pick -- <oid>`).
//! Never `--ff` / `-n` / `--no-commit` / `--continue` / `--skip` / `--abort`.
//! Never rebase. Never push. Occupying Run/lease refuses before GitWritePort.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Contract string: occupying Run/lease refuses cherry-pick.
pub const ACTIVE_LEASE_BLOCKS_CHERRY_PICK: &str = "活動租約禁止 cherry-pick";

/// Result of a gated cherry-pick (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitCherryPickResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitCherryPickResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "cherry-pick".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "cherry-pick".into(),
            message: "cherry-pick ok".into(),
            local_preserved: true,
        }
    }
}

fn cherry_pick_oid_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.starts_with('-')
        || t.starts_with('+')
        || t.contains('\0')
        || t.contains('\n')
        || t.contains(' ')
        || matches!(
            lower.as_str(),
            "-n" | "--no-commit"
                | "--ff"
                | "--ff-only"
                | "--continue"
                | "--skip"
                | "--abort"
                | "-x"
                | "-m"
                | "--mainline"
                | "-f"
                | "--force"
                | "rebase"
                | "--rebase"
                | "push"
                | "--push"
        )
}

/// Soft-gated cherry-pick: occupying Run refuses before GitWritePort.
/// Option-like names fail honestly (no mutation).
pub fn perform_git_cherry_pick(
    write: &dyn GitWritePort,
    repo: &str,
    oid: &str,
    approved: bool,
    occupying_run: Option<&str>,
) -> Result<GitCherryPickResult, String> {
    let source = oid.trim();
    if cherry_pick_oid_out_of_scope(source) {
        return Err("ff/no-commit/continue/rebase/push cherry-pick writes are out of scope".into());
    }
    if source.is_empty() {
        return Ok(GitCherryPickResult::refuse("empty cherry-pick oid"));
    }
    if let Some(run_id) = occupying_run.map(str::trim).filter(|s| !s.is_empty()) {
        return Ok(GitCherryPickResult::refuse(format!(
            "{ACTIVE_LEASE_BLOCKS_CHERRY_PICK}: occupying run {run_id}"
        )));
    }
    if !approved {
        return Ok(GitCherryPickResult::refuse("approval denied; no mutation"));
    }
    match write.cherry_pick(repo, source, GitWriteApproval::granted()) {
        Ok(()) => Ok(GitCherryPickResult::ok()),
        Err(e) => Ok(GitCherryPickResult::refuse(e.to_string())),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    use crate::git_switch::occupying_run_id;
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
    fn denied_does_not_call_git_write() {
        let w = FakeGitWrite::new();
        w.seed_reachable_oid("/r", "abc1234", "feat: picked");
        let denied = perform_git_cherry_pick(&w, "/r", "abc1234", false, None).unwrap();
        assert!(!denied.ok);
        assert!(denied.local_preserved);
        assert!(w.last_cherry_pick("/r").is_none());
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn occupying_run_refuses_before_git_write() {
        let w = FakeGitWrite::new();
        w.seed_reachable_oid("/r", "abc1234", "feat: picked");
        let occupying = occupying_run_id(Some(&occupying_proj("run-42")), None);
        let blocked =
            perform_git_cherry_pick(&w, "/r", "abc1234", true, occupying.as_deref()).unwrap();
        assert!(!blocked.ok);
        assert!(blocked.local_preserved);
        assert!(blocked.message.contains(ACTIVE_LEASE_BLOCKS_CHERRY_PICK));
        assert!(blocked.message.contains("run-42"));
        assert!(w.last_cherry_pick("/r").is_none());
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn approved_cherry_pick_records_without_push_or_ff() {
        let w = FakeGitWrite::new();
        w.seed_reachable_oid("/r", "abc1234", "feat: picked");
        let ok = perform_git_cherry_pick(&w, "/r", "abc1234", true, None).unwrap();
        assert!(ok.ok);
        assert_eq!(ok.op, "cherry-pick");
        assert_eq!(w.last_cherry_pick("/r").as_deref(), Some("abc1234"));
        assert_eq!(w.push_count("/r"), 0);
        assert!(w.last_pull_ff_only("/r").is_none());
    }

    #[test]
    fn option_like_names_fail_honestly() {
        let w = FakeGitWrite::new();
        w.seed_reachable_oid("/r", "abc1234", "feat: picked");
        let ff = perform_git_cherry_pick(&w, "/r", "--ff", true, None).unwrap_err();
        assert!(ff.contains("out of scope"));
        let n = perform_git_cherry_pick(&w, "/r", "-n", true, None).unwrap_err();
        assert!(n.contains("out of scope"));
        assert!(w.last_cherry_pick("/r").is_none());
    }

    #[test]
    fn missing_oid_fails_without_mutation() {
        let w = FakeGitWrite::new();
        let missing = perform_git_cherry_pick(&w, "/r", "deadbeef", true, None).unwrap();
        assert!(!missing.ok);
        assert!(missing
            .message
            .to_ascii_lowercase()
            .contains("bad revision"));
        assert!(w.last_cherry_pick("/r").is_none());
    }
}
