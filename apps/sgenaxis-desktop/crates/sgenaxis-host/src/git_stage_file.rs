//! Gated single-file stage (`git add -- <path>` from the repo root).
//! Never commit / push / `git add -A` / `git add -- .` / `reset --hard` / `--force`.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.
//! Option-like, traversal, and absolute paths are rejected.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated file-stage (mirrors desktop `GitWriteResultDto`).
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

/// Soft-gated file-stage: unapproved never mutates.
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
    fn approved_stage_file_succeeds() {
        let w = FakeGitWrite::new();
        let ok = perform_git_stage_file(&w, "/r", "a.txt", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "stage-file");
        assert_eq!(w.last_stage_file("/r").as_deref(), Some("a.txt"));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_stage_file(&w, "/r", "a.txt", false);
        assert!(!denied.ok);
        assert!(w.last_stage_file("/r").is_none());
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_stage_file(&w, "/r", "a.txt", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_stage_file("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }

    #[test]
    fn option_like_and_traversal_paths_are_refused() {
        let w = FakeGitWrite::new();
        for path in ["-A", "--all", ".", "..", "../x", "/tmp/x"] {
            let failed = perform_git_stage_file(&w, "/r", path, true);
            assert!(!failed.ok, "{path}");
            assert!(w.last_stage_file("/r").is_none(), "{path}");
        }
    }
}
