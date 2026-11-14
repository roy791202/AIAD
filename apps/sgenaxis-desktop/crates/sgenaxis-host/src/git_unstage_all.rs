//! Gated mixed unstage-all (`git reset -- .` from the repo root).
//! Never commit / push / `git add -A` / `reset --hard` / `--force`.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.
//! A clean index relative to HEAD is a success no-op.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated unstage-all (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitUnstageAllResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitUnstageAllResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "unstage-all".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "unstage-all".into(),
            message: "unstage-all ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated unstage-all: unapproved never mutates.
pub fn perform_git_unstage_all(
    write: &dyn GitWritePort,
    repo: &str,
    approved: bool,
) -> GitUnstageAllResult {
    if !approved {
        return GitUnstageAllResult::refuse("approval denied; no mutation");
    }
    match write.unstage_all(repo, GitWriteApproval::granted()) {
        Ok(()) => GitUnstageAllResult::ok(),
        Err(e) => GitUnstageAllResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_unstage_all_succeeds_including_clean_noop() {
        let w = FakeGitWrite::new();
        let ok = perform_git_unstage_all(&w, "/r", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "unstage-all");
        assert_eq!(w.last_unstage_all("/r"), Some(true));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_unstage_all(&w, "/r", false);
        assert!(!denied.ok);
        assert!(w.last_unstage_all("/r").is_none());
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_unstage_all(&w, "/r", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_unstage_all("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
