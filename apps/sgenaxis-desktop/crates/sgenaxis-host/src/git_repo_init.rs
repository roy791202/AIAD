//! Gated local `git init -- <dir>` (REPO-INIT).
//! Never clone, `--bare`, `--template`, `--separate-git-dir`, add remote, or fetch.
//! Existing repos and option-like paths fail honestly.
//! Denied approval leaves no `.git`.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated repo init (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitRepoInitResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitRepoInitResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "repo-init".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "repo-init".into(),
            message: "repo-init ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated repo init: unapproved never mutates.
pub fn perform_git_repo_init(
    write: &dyn GitWritePort,
    dir: &str,
    approved: bool,
) -> GitRepoInitResult {
    if !approved {
        return GitRepoInitResult::refuse("approval denied; no mutation");
    }
    match write.init_repo(dir, GitWriteApproval::granted()) {
        Ok(()) => GitRepoInitResult::ok(),
        Err(e) => GitRepoInitResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;

    #[test]
    fn approved_init_records_non_bare_without_remote() {
        let w = FakeGitWrite::new();
        let ok = perform_git_repo_init(&w, "/empty", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "repo-init");
        assert_eq!(w.last_init_repo("/empty"), Some(true));
        assert!(w.configured_remotes("/empty").is_empty());
        assert_eq!(w.push_count("/empty"), 0);
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        let denied = perform_git_repo_init(&w, "/empty", false);
        assert!(!denied.ok);
        assert!(w.last_init_repo("/empty").is_none());
        assert!(w.configured_remotes("/empty").is_empty());
    }

    #[test]
    fn existing_and_option_like_paths_fail_honestly() {
        let w = FakeGitWrite::new();
        assert!(perform_git_repo_init(&w, "/empty", true).ok);
        let existing = perform_git_repo_init(&w, "/empty", true);
        assert!(!existing.ok);
        assert!(existing.message.to_ascii_lowercase().contains("already"));
        assert_eq!(w.last_init_repo("/empty"), Some(true));

        let bare = perform_git_repo_init(&w, "--bare", true);
        assert!(!bare.ok);
        assert!(w.last_init_repo("--bare").is_none());

        let url = perform_git_repo_init(&w, "https://example.com/org/repo.git", true);
        assert!(!url.ok);
        assert!(w
            .last_init_repo("https://example.com/org/repo.git")
            .is_none());
    }
}
