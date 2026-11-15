//! Gated mixed unstage-file (`git reset -- <path>` from the repo root).
//! Never commit / push / `git add -A` / `git add -- .` / `reset --hard` /
//! `--force`. Distinct from unstage-all (`git reset -- .`) and conflict-abort.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.
//! An already-unstaged path is a success no-op. Untracked files remain.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated unstage-file (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitUnstageFileResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitUnstageFileResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "unstage-file".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "unstage-file".into(),
            message: "unstage-file ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated unstage-file: unapproved never mutates.
pub fn perform_git_unstage_file(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    approved: bool,
) -> GitUnstageFileResult {
    if !approved {
        return GitUnstageFileResult::refuse("approval denied; no mutation");
    }
    match write.unstage_file(repo, path, GitWriteApproval::granted()) {
        Ok(()) => GitUnstageFileResult::ok(),
        Err(e) => GitUnstageFileResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_unstage_file_succeeds_including_already_unstaged_noop() {
        let w = FakeGitWrite::new();
        let ok = perform_git_unstage_file(&w, "/r", "a.txt", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "unstage-file");
        assert_eq!(w.last_unstage_file("/r").as_deref(), Some("a.txt"));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
        let again = perform_git_unstage_file(&w, "/r", "a.txt", true);
        assert!(again.ok);
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_unstage_file(&w, "/r", "a.txt", false);
        assert!(!denied.ok);
        assert!(w.last_unstage_file("/r").is_none());
    }

    #[test]
    fn invalid_paths_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        for path in ["", "-", "-A", "--force", "../x", "a/../b", "."] {
            let failed = perform_git_unstage_file(&w, "/r", path, true);
            assert!(!failed.ok, "{path}");
            assert!(w.last_unstage_file("/r").is_none(), "{path}");
        }
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_unstage_file(&w, "/r", "src/a.rs", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_unstage_file("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
