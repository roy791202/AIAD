//! Gated single-hunk unstage (`git apply --cached --reverse` of one hunk).
//! Never `--force`. Never commit / push / `reset --hard`.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated unstage-hunk (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitUnstageHunkResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitUnstageHunkResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "unstage-hunk".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "unstage-hunk".into(),
            message: "unstage-hunk ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated unstage-hunk: unapproved never mutates.
pub fn perform_git_unstage_hunk(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    old_start: u32,
    approved: bool,
) -> GitUnstageHunkResult {
    if !approved {
        return GitUnstageHunkResult::refuse("approval denied; no mutation");
    }
    match write.unstage_hunk(repo, path, old_start, GitWriteApproval::granted()) {
        Ok(()) => GitUnstageHunkResult::ok(),
        Err(e) => GitUnstageHunkResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_unstage_hunk_records_path_and_old_start() {
        let w = FakeGitWrite::new();
        let ok = perform_git_unstage_hunk(&w, "/r", "a.txt", 12, true);
        assert!(ok.ok);
        assert_eq!(ok.op, "unstage-hunk");
        assert_eq!(w.last_unstage_hunk("/r"), Some(("a.txt".into(), 12)));
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_unstage_hunk(&w, "/r", "a.txt", 12, false);
        assert!(!denied.ok);
        assert!(w.last_unstage_hunk("/r").is_none());
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Rebase", &["src/a.rs"]);
        let failed = perform_git_unstage_hunk(&w, "/r", "src/a.rs", 1, true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_unstage_hunk("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
