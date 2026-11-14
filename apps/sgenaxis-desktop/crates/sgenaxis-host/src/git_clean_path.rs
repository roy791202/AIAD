//! Gated delete of one untracked path (`git clean -f -- <path>`).
//! Never `-fdx` / `-x` / `-d .` / `rm -rf` / commit / push / `reset --hard`.
//! Tracked paths fail honestly. In-progress merge/rebase/cherry-pick/revert
//! fails honestly. Unapproved never mutates.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated clean-path (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitCleanPathResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitCleanPathResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "clean-path".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "clean-path".into(),
            message: "clean-path ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated clean-path: unapproved never mutates.
pub fn perform_git_clean_path(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    approved: bool,
) -> GitCleanPathResult {
    if !approved {
        return GitCleanPathResult::refuse("approval denied; no mutation");
    }
    match write.clean_path(repo, path, GitWriteApproval::granted()) {
        Ok(()) => GitCleanPathResult::ok(),
        Err(e) => GitCleanPathResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_clean_path_deletes_seeded_untracked() {
        let w = FakeGitWrite::new();
        w.seed_untracked_path("/r", "scratch.tmp");
        let ok = perform_git_clean_path(&w, "/r", "scratch.tmp", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "clean-path");
        assert_eq!(w.last_clean_path("/r").as_deref(), Some("scratch.tmp"));
        assert!(w.remaining_untracked_paths("/r").is_empty());
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        w.seed_untracked_path("/r", "scratch.tmp");
        let denied = perform_git_clean_path(&w, "/r", "scratch.tmp", false);
        assert!(!denied.ok);
        assert!(w.last_clean_path("/r").is_none());
        assert_eq!(w.remaining_untracked_paths("/r"), vec!["scratch.tmp"]);
    }

    #[test]
    fn tracked_path_fails_honestly() {
        let w = FakeGitWrite::new();
        let failed = perform_git_clean_path(&w, "/r", "a.txt", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("tracked path"));
        assert!(w.last_clean_path("/r").is_none());
    }

    #[test]
    fn option_like_and_dot_fail_honestly() {
        let w = FakeGitWrite::new();
        for path in [".", "..", "-fdx", "-x", "-d", "../secret", ""] {
            let failed = perform_git_clean_path(&w, "/r", path, true);
            assert!(!failed.ok, "expected fail for {path:?}: {}", failed.message);
            assert!(w.last_clean_path("/r").is_none());
        }
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.seed_untracked_path("/r", "scratch.tmp");
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_clean_path(&w, "/r", "scratch.tmp", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_clean_path("/r").is_none());
        assert_eq!(w.remaining_untracked_paths("/r"), vec!["scratch.tmp"]);
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
