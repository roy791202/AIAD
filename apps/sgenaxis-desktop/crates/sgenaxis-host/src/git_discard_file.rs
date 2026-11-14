//! Gated single-path worktree discard (`git restore --worktree -- path`).
//! Never `reset --hard` / `--force`. Untracked files are not deleted.
//! Paths outside the repo, option-like paths, and unmerged paths fail honestly.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated discard-file (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitDiscardFileResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitDiscardFileResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "discard-file".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "discard-file".into(),
            message: "discard-file ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated discard-file: unapproved never mutates.
pub fn perform_git_discard_file(
    write: &dyn GitWritePort,
    repo: &str,
    path: &str,
    approved: bool,
) -> GitDiscardFileResult {
    if !approved {
        return GitDiscardFileResult::refuse("approval denied; no mutation");
    }
    match write.discard_file(repo, path, GitWriteApproval::granted()) {
        Ok(()) => GitDiscardFileResult::ok(),
        Err(e) => GitDiscardFileResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn s_git_write_p2_3_discard_file() {
        let w = FakeGitWrite::new();
        let ok = perform_git_discard_file(&w, "/r", "a.txt", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "discard-file");
        assert_eq!(w.last_discard_file("/r").as_deref(), Some("a.txt"));
        assert_eq!(w.local_commit_count("/r"), 0);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn s_git_write_p2_4_discard_reject() {
        let w = FakeGitWrite::new();
        let denied = perform_git_discard_file(&w, "/r", "a.txt", false);
        assert!(!denied.ok);
        assert!(w.last_discard_file("/r").is_none());

        w.mark_untracked("/r", &["scratch.txt"]);
        let untracked = perform_git_discard_file(&w, "/r", "scratch.txt", true);
        assert!(!untracked.ok);
        assert!(untracked.message.to_ascii_lowercase().contains("untracked"));
        assert!(w.untracked_still_present("/r", "scratch.txt"));
        assert!(w.last_discard_file("/r").is_none());

        w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
        let conflict = perform_git_discard_file(&w, "/r", "src/a.rs", true);
        assert!(!conflict.ok);
        assert!(w.last_discard_file("/r").is_none());
        assert_eq!(w.remaining_conflict_files("/r").len(), 1);
    }
}
