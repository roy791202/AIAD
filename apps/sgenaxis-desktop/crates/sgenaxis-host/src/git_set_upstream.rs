//! Gated local upstream tracking (`git branch --set-upstream-to=<remote>/<branch>`).
//! Never `--unset-upstream`. Never create remotes, tracking refs, or local branches.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated set-upstream (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitSetUpstreamResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitSetUpstreamResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "set-upstream".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "set-upstream".into(),
            message: "set-upstream ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated set-upstream: empty remote/branch / unapproved never mutates.
/// Empty `local` is forwarded so the adapter can resolve the current branch.
pub fn perform_git_set_upstream(
    write: &dyn GitWritePort,
    repo: &str,
    remote: &str,
    branch: &str,
    local: &str,
    approved: bool,
) -> GitSetUpstreamResult {
    let remote = remote.trim();
    let branch = branch.trim();
    if remote.is_empty() {
        return GitSetUpstreamResult::refuse("empty remote name");
    }
    if branch.is_empty() {
        return GitSetUpstreamResult::refuse("empty branch name");
    }
    if !approved {
        return GitSetUpstreamResult::refuse("approval denied; no mutation");
    }
    match write.set_upstream(
        repo,
        remote,
        branch,
        local.trim(),
        GitWriteApproval::granted(),
    ) {
        Ok(()) => GitSetUpstreamResult::ok(),
        Err(e) => GitSetUpstreamResult::refuse(e.to_string()),
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
    }

    #[test]
    fn approved_set_upstream_succeeds() {
        let w = FakeGitWrite::new();
        seed(&w);
        let ok = perform_git_set_upstream(&w, "/r", "origin", "main", "", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "set-upstream");
        assert_eq!(
            w.last_set_upstream("/r"),
            Some(("main".into(), "origin".into(), "main".into()))
        );
        assert_eq!(
            w.upstream_of("/r", "main"),
            Some(("origin".into(), "main".into()))
        );
    }

    #[test]
    fn unapproved_and_validation_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        seed(&w);

        let denied = perform_git_set_upstream(&w, "/r", "origin", "main", "main", false);
        assert!(!denied.ok);
        assert!(w.last_set_upstream("/r").is_none());

        let empty = perform_git_set_upstream(&w, "/r", "  ", "main", "main", true);
        assert!(!empty.ok);
        assert!(w.last_set_upstream("/r").is_none());

        let empty_branch = perform_git_set_upstream(&w, "/r", "origin", "  ", "main", true);
        assert!(!empty_branch.ok);
        assert!(w.last_set_upstream("/r").is_none());
    }
}
