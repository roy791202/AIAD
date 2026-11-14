//! Gated single-hunk stage (`git apply --cached` of one hunk).
//! Never `--force`. Never commit / push / `reset --hard`.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated stage-hunk (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitStageHunkResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitStageHunkResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "stage-hunk".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "stage-hunk".into(),
            message: "stage-hunk ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated stage-hunk: unapproved never mutates.
pub fn perform_git_stage_hunk(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    old_start: u32,
    approved: bool,
) -> GitStageHunkResult {
    if !approved {
        return GitStageHunkResult::refuse("approval denied; no mutation");
    }
    match write.stage_hunk(repo, path, old_start, GitWriteApproval::granted()) {
        Ok(()) => GitStageHunkResult::ok(),
        Err(e) => GitStageHunkResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_stage_hunk_records_path_and_old_start() {
        let w = FakeGitWrite::new();
        let ok = perform_git_stage_hunk(&w, "/r", "a.txt", 2, true);
        assert!(ok.ok);
        assert_eq!(ok.op, "stage-hunk");
        assert_eq!(w.last_stage_hunk("/r"), Some(("a.txt".into(), 2)));
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_stage_hunk(&w, "/r", "a.txt", 2, false);
        assert!(!denied.ok);
        assert!(w.last_stage_hunk("/r").is_none());
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_stage_hunk(&w, "/r", "src/a.rs", 1, true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_stage_hunk("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
