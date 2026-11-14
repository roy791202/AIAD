//! Gated local remote rename (`git remote rename`). URL unchanged (set-url is separate).

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated remote rename (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitRemoteRenameResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitRemoteRenameResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "remote-rename".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "remote-rename".into(),
            message: "remote-rename ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated rename: empty / identical / unapproved never mutates.
pub fn perform_git_rename_remote(
    write: &dyn GitWritePort,
    repo: &str,
    old: &str,
    new: &str,
    approved: bool,
) -> GitRemoteRenameResult {
    let old = old.trim();
    let new = new.trim();
    if old.is_empty() || new.is_empty() {
        return GitRemoteRenameResult::refuse("empty remote name");
    }
    if old == new {
        return GitRemoteRenameResult::refuse("remote name unchanged");
    }
    if !approved {
        return GitRemoteRenameResult::refuse("approval denied; no mutation");
    }
    match write.rename_remote(repo, old, new, GitWriteApproval::granted()) {
        Ok(()) => GitRemoteRenameResult::ok(),
        Err(e) => GitRemoteRenameResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;
    use sgenaxis_ports::GitWriteApproval;

    #[test]
    fn approved_remote_rename_succeeds() {
        let w = FakeGitWrite::new();
        w.add_remote(
            "/r",
            "origin",
            "https://example.invalid/r.git",
            GitWriteApproval::granted(),
        )
        .expect("seed");
        let ok = perform_git_rename_remote(&w, "/r", "origin", "upstream", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "remote-rename");
        assert_eq!(
            w.last_remote_rename("/r"),
            Some(("origin".into(), "upstream".into()))
        );
        assert_eq!(
            w.configured_remotes("/r"),
            vec![(
                "upstream".to_string(),
                "https://example.invalid/r.git".to_string()
            )]
        );
    }

    #[test]
    fn unapproved_and_validation_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        w.add_remote(
            "/r",
            "origin",
            "https://example.invalid/r.git",
            GitWriteApproval::granted(),
        )
        .expect("seed");

        let denied = perform_git_rename_remote(&w, "/r", "origin", "upstream", false);
        assert!(!denied.ok);
        assert!(w.last_remote_rename("/r").is_none());

        let same = perform_git_rename_remote(&w, "/r", "origin", "origin", true);
        assert!(!same.ok);
        assert!(w.last_remote_rename("/r").is_none());

        let empty = perform_git_rename_remote(&w, "/r", "  ", "upstream", true);
        assert!(!empty.ok);
        assert!(w.last_remote_rename("/r").is_none());
    }
}