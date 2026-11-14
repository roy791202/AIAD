//! Gated single-hunk unstage (`git apply --cached -R` of one text hunk).
//! Never commit / push / `git add -A` / `reset --hard` / `--force`.
//! Remaining staged hunks stay staged. Worktree bytes outside the hunk stay.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated hunk-unstage (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitHunkUnstageResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitHunkUnstageResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "hunk-unstage".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "hunk-unstage".into(),
            message: "hunk-unstage ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated hunk-unstage: unapproved never mutates.
pub fn perform_git_hunk_unstage(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    hunk_spec: &str,
    approved: bool,
) -> GitHunkUnstageResult {
    if !approved {
        return GitHunkUnstageResult::refuse("approval denied; no mutation");
    }
    match write.hunk_unstage(repo, path, hunk_spec, GitWriteApproval::granted()) {
        Ok(()) => GitHunkUnstageResult::ok(),
        Err(e) => GitHunkUnstageResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn pd_git_hunk_unstage_01_approved_unstages_only_specified_hunk() {
        let w = FakeGitWrite::new();
        w.stage_text_hunk("/r", "a.txt", "@@ -2,1 +2,1 @@");
        w.stage_text_hunk("/r", "a.txt", "@@ -18,1 +18,1 @@");
        let ok = perform_git_hunk_unstage(&w, "/r", "a.txt", "@@ -2,1 +2,1 @@", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "hunk-unstage");
        assert_eq!(
            w.last_hunk_unstage("/r"),
            Some(("a.txt".into(), "@@ -2,1 +2,1 @@".into()))
        );
        assert_eq!(
            w.staged_hunks("/r", "a.txt"),
            vec!["@@ -18,1 +18,1 @@".to_string()]
        );
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn pd_git_hunk_unstage_01_unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        w.stage_text_hunk("/r", "a.txt", "@@ -2,1 +2,1 @@");
        let denied = perform_git_hunk_unstage(&w, "/r", "a.txt", "@@ -2,1 +2,1 @@", false);
        assert!(!denied.ok);
        assert!(w.last_hunk_unstage("/r").is_none());
        assert_eq!(
            w.staged_hunks("/r", "a.txt"),
            vec!["@@ -2,1 +2,1 @@".to_string()]
        );
    }

    #[test]
    fn pd_git_hunk_unstage_01_in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.stage_text_hunk("/r", "a.txt", "@@ -2,1 +2,1 @@");
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_hunk_unstage(&w, "/r", "a.txt", "@@ -2,1 +2,1 @@", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_hunk_unstage("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
        assert_eq!(
            w.staged_hunks("/r", "a.txt"),
            vec!["@@ -2,1 +2,1 @@".to_string()]
        );
    }
}
