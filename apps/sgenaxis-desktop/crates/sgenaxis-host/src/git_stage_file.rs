//! Gated worktree stage-file (`git add -- <path>` from the repo root).
//! Never commit / push / `git add -A` / `git add -- .` / `reset --hard` /
//! `--force`. Distinct from conflict-save.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.
//! An already-staged path is a success no-op.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated stage-file (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitStageFileResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitStageFileResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "stage-file".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "stage-file".into(),
            message: "stage-file ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated stage-file: unapproved never mutates.
pub fn perform_git_stage_file(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    approved: bool,
) -> GitStageFileResult {
    if !approved {
        return GitStageFileResult::refuse("approval denied; no mutation");
    }
    match write.stage_file(repo, path, GitWriteApproval::granted()) {
        Ok(()) => GitStageFileResult::ok(),
        Err(e) => GitStageFileResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_stage_file_succeeds_including_already_staged_noop() {
        let w = FakeGitWrite::new();
        let ok = perform_git_stage_file(&w, "/r", "a.txt", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "stage-file");
        assert_eq!(w.last_stage_file("/r").as_deref(), Some("a.txt"));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
        let again = perform_git_stage_file(&w, "/r", "a.txt", true);
        assert!(again.ok);
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_stage_file(&w, "/r", "a.txt", false);
        assert!(!denied.ok);
        assert!(w.last_stage_file("/r").is_none());
    }

    #[test]
    fn invalid_paths_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        for path in ["", "-", "-A", "--force", "../x", "a/../b", "."] {
            let failed = perform_git_stage_file(&w, "/r", path, true);
            assert!(!failed.ok, "{path}");
            assert!(w.last_stage_file("/r").is_none(), "{path}");
        }
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_stage_file(&w, "/r", "src/a.rs", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_stage_file("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
