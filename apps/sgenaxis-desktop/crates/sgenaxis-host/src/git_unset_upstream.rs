//! Gated local upstream clear (`git branch --unset-upstream -- <local>`).
//! Never `--set-upstream-to` / `-u`. Never create remotes, tracking refs, or local branches.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated unset-upstream (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitUnsetUpstreamResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitUnsetUpstreamResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "unset-upstream".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "unset-upstream".into(),
            message: "unset-upstream ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated unset-upstream: unapproved never mutates.
/// Empty `local` is forwarded so the adapter can resolve the current branch.
pub fn perform_git_unset_upstream(
    write: &dyn GitWritePort,
    repo: &str,
    local: &str,
    approved: bool,
) -> GitUnsetUpstreamResult {
    if !approved {
        return GitUnsetUpstreamResult::refuse("approval denied; no mutation");
    }
    match write.unset_upstream(repo, local.trim(), GitWriteApproval::granted()) {
        Ok(()) => GitUnsetUpstreamResult::ok(),
        Err(e) => GitUnsetUpstreamResult::refuse(e.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_adapters::FakeGitWrite;
    use sgenaxis_ports::GitWriteApproval;

    fn seed(w: &FakeGitWrite) {
        w.add_remote(
            "/r",
            "origin",
            "https://example.invalid/r.git",
            GitWriteApproval::granted(),
        )
        .expect("seed remote");
        w.create_branch("/r", "main", GitWriteApproval::granted())
            .expect("seed local");
        w.set_current_branch("/r", "main");
        w.seed_remote_tracking("/r", "refs/remotes/origin/main", "oid-main");
        w.set_upstream("/r", "origin", "main", "main", GitWriteApproval::granted())
            .expect("seed upstream");
    }

    #[test]
    fn approved_unset_upstream_succeeds() {
        let w = FakeGitWrite::new();
        seed(&w);
        let ok = perform_git_unset_upstream(&w, "/r", "", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "unset-upstream");
        assert_eq!(w.last_unset_upstream("/r"), Some("main".into()));
        assert!(w.upstream_of("/r", "main").is_none());
    }

    #[test]
    fn unapproved_refuses_without_mutation() {
        let w = FakeGitWrite::new();
        seed(&w);

        let denied = perform_git_unset_upstream(&w, "/r", "main", false);
        assert!(!denied.ok);
        assert!(w.last_unset_upstream("/r").is_none());
        assert_eq!(
            w.upstream_of("/r", "main"),
            Some(("origin".into(), "main".into()))
        );
    }
}
