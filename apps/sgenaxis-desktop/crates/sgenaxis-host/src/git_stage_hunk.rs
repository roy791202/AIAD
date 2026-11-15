//! Gated index stage-hunk (`git apply --cached` from stdin).
//! Never commit / push / `git add -A` / `git add -- .` / `reset --hard` /
//! `--force`. Distinct from stage-file and conflict-save.
//! In-progress merge/rebase/cherry-pick/revert fails honestly.
//! Empty / truncated / binary / rename patches fail honestly.
//! Patch drift (check fails) refuses with no mutation.
//! An already-applied matching hunk is a success no-op.

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
    patch: &str,
    content_hash: &str,
    approved: bool,
) -> GitStageHunkResult {
    if !approved {
        return GitStageHunkResult::refuse("approval denied; no mutation");
    }
    match write.stage_hunk(repo, path, patch, content_hash, GitWriteApproval::granted()) {
        Ok(()) => GitStageHunkResult::ok(),
        Err(e) => GitStageHunkResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    const TEXT_HUNK: &str =
        "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n";

    #[test]
    fn approved_stage_hunk_succeeds_including_already_applied_noop() {
        let w = FakeGitWrite::new();
        let ok = perform_git_stage_hunk(&w, "/r", "a.txt", TEXT_HUNK, "abc", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "stage-hunk");
        let rec = w.last_stage_hunk("/r").expect("recorded");
        assert_eq!(rec.0, "a.txt");
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
        let again = perform_git_stage_hunk(&w, "/r", "a.txt", TEXT_HUNK, "abc", true);
        assert!(again.ok);
        assert_eq!(w.local_commit_count("/r"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_stage_hunk(&w, "/r", "a.txt", TEXT_HUNK, "abc", false);
        assert!(!denied.ok);
        assert!(w.last_stage_hunk("/r").is_none());
    }

    #[test]
    fn invalid_paths_and_patches_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        for path in ["", "-", "-A", "--force", "../x", "a/../b", "."] {
            let failed = perform_git_stage_hunk(&w, "/r", path, TEXT_HUNK, "abc", true);
            assert!(!failed.ok, "{path}");
            assert!(w.last_stage_hunk("/r").is_none(), "{path}");
        }
        let empty_patch = perform_git_stage_hunk(&w, "/r", "a.txt", "", "abc", true);
        assert!(!empty_patch.ok);
        let binary = perform_git_stage_hunk(
            &w,
            "/r",
            "a.txt",
            "GIT binary patch\nliteral 1\n",
            "abc",
            true,
        );
        assert!(!binary.ok);
        assert!(w.last_stage_hunk("/r").is_none());
    }

    #[test]
    fn in_progress_conflict_fails_honestly() {
        let w = FakeGitWrite::new();
        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let failed = perform_git_stage_hunk(&w, "/r", "src/a.rs", TEXT_HUNK, "abc", true);
        assert!(!failed.ok);
        assert!(failed.message.contains("OPERATION_IN_PROGRESS"));
        assert!(w.last_stage_hunk("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
