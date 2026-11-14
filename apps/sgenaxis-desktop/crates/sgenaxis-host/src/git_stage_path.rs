//! Gated single-path worktree stage (`git add -- <path>`).
//! Never commit / push / `reset --hard` / `--force`. Never `git add -A` / `.`.
//! In-progress merge/rebase/cherry-pick/revert with unmerged paths fails honestly.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated stage-path (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitStagePathResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitStagePathResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "stage-path".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "stage-path".into(),
            message: "stage-path ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated stage-path: unapproved never mutates.
pub fn perform_git_stage_path(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    approved: bool,
) -> GitStagePathResult {
    if !approved {
        return GitStagePathResult::refuse("approval denied; no mutation");
    }
    match write.stage_path(repo, path, GitWriteApproval::granted()) {
        Ok(()) => GitStagePathResult::ok(),
        Err(e) => GitStagePathResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn bdd_pd_git_stage_path_01_approved_stage_path_succeeds() {
        let w = FakeGitWrite::new();
        let ok = perform_git_stage_path(&w, "/r", "src/a.rs", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "stage-path");
        assert_eq!(w.last_stage_path("/r"), Some("src/a.rs".into()));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn bdd_pd_git_stage_path_01_unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_stage_path(&w, "/r", "src/a.rs", false);
        assert!(!denied.ok);
        assert!(w.last_stage_path("/r").is_none());
    }

    #[test]
    fn bdd_pd_git_stage_path_01_in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_stage_path(&w, "/r", "src/other.rs", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_stage_path("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}