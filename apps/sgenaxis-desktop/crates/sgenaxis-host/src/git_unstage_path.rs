//! Gated mixed unstage-path (`git reset -- <path>` from the repo root).
//! Never commit / push / `git add -A` / `reset --hard` / `--force`.
//! Never unstage other paths. In-progress merge/rebase/cherry-pick/revert fails honestly.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated unstage-path (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitUnstagePathResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitUnstagePathResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "unstage-path".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "unstage-path".into(),
            message: "unstage-path ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated unstage-path: unapproved never mutates.
pub fn perform_git_unstage_path(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    approved: bool,
) -> GitUnstagePathResult {
    if !approved {
        return GitUnstagePathResult::refuse("approval denied; no mutation");
    }
    match write.unstage_path(repo, path, GitWriteApproval::granted()) {
        Ok(()) => GitUnstagePathResult::ok(),
        Err(e) => GitUnstagePathResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn s_git_write_p2_file_unstage_grant_one_path() {
        let w = FakeGitWrite::new();
        w.seed_staged_paths("/r", &["a.txt", "b.txt"]);
        let ok = perform_git_unstage_path(&w, "/r", "a.txt", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "unstage-path");
        assert_eq!(w.last_unstage_path("/r").as_deref(), Some("a.txt"));
        assert_eq!(w.remaining_staged_paths("/r"), vec!["b.txt".to_string()]);
    }

    #[test]
    fn s_git_write_p2_file_unstage_deny_no_mutation() {
        let w = FakeGitWrite::new();
        w.seed_staged_paths("/r", &["a.txt"]);
        let denied = perform_git_unstage_path(&w, "/r", "a.txt", false);
        assert!(!denied.ok);
        assert!(w.last_unstage_path("/r").is_none());
        assert_eq!(w.remaining_staged_paths("/r"), vec!["a.txt".to_string()]);
    }
}
