//! Gated single-hunk discard (`git apply --reverse` of one path).
//! Never commit / push / `reset --hard` / `checkout .` / `-f`.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.
//! Missing or unmatched hunks fail honestly; other files stay unchanged.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated hunk discard (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitHunkDiscardResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitHunkDiscardResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "hunk-discard".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "hunk-discard".into(),
            message: "hunk-discard ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated hunk discard: unapproved never mutates.
pub fn perform_git_hunk_discard(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    hunk: &str,
    approved: bool,
) -> GitHunkDiscardResult {
    if !approved {
        return GitHunkDiscardResult::refuse("approval denied; no mutation");
    }
    match write.discard_hunk(repo, path, hunk, GitWriteApproval::granted()) {
        Ok(()) => GitHunkDiscardResult::ok(),
        Err(e) => GitHunkDiscardResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    const PATH: &str = "src/a.rs";
    const HUNK: &str = "@@ -1,2 +1,2 @@\n line\n-old\n+new\n";

    #[test]
    fn approved_hunk_discard_succeeds() {
        let w = FakeGitWrite::new();
        w.seed_hunk("/r", PATH, HUNK);
        w.seed_other_file("/r", "src/b.rs", "keep\n");
        let ok = perform_git_hunk_discard(&w, "/r", PATH, HUNK, true);
        assert!(ok.ok);
        assert_eq!(ok.op, "hunk-discard");
        assert_eq!(w.last_hunk_discard("/r"), Some((PATH.into(), HUNK.into())));
        assert_eq!(w.other_file("/r", "src/b.rs").as_deref(), Some("keep\n"));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        w.seed_hunk("/r", PATH, HUNK);
        let denied = perform_git_hunk_discard(&w, "/r", PATH, HUNK, false);
        assert!(!denied.ok);
        assert!(w.last_hunk_discard("/r").is_none());
        assert_eq!(w.remaining_hunks("/r", PATH).len(), 1);
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.seed_hunk("/r", PATH, HUNK);
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_hunk_discard(&w, "/r", PATH, HUNK, true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_hunk_discard("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
        assert_eq!(w.remaining_hunks("/r", PATH).len(), 1);
    }

    #[test]
    fn unmatched_hunk_fails_honestly() {
        let w = FakeGitWrite::new();
        w.seed_hunk("/r", PATH, HUNK);
        w.seed_other_file("/r", "src/b.rs", "keep\n");
        let failed =
            perform_git_hunk_discard(&w, "/r", PATH, "@@ -9,1 +9,1 @@\n-missing\n+nope\n", true);
        assert!(!failed.ok);
        assert!(w.last_hunk_discard("/r").is_none());
        assert_eq!(w.remaining_hunks("/r", PATH).len(), 1);
        assert_eq!(w.other_file("/r", "src/b.rs").as_deref(), Some("keep\n"));
    }
}
