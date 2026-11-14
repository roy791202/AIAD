//! Gated single-tag push (`git push -- <remote> refs/tags/<tag>`). Never force / bulk.

use sgenaxis_ports::{GitWriteApproval, GitWritePort};

/// Result of a gated tag push (mirrors desktop `GitWriteResultDto`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitTagPushResult {
    pub ok: bool,
    pub op: String,
    pub message: String,
    pub local_preserved: bool,
}

impl GitTagPushResult {
    fn refuse(message: impl Into<String>) -> Self {
        Self {
            ok: false,
            op: "tag-push".into(),
            message: message.into(),
            local_preserved: true,
        }
    }

    fn ok() -> Self {
        Self {
            ok: true,
            op: "tag-push".into(),
            message: "tag-push ok".into(),
            local_preserved: true,
        }
    }
}

/// Soft-gated tag push: unapproved / empty tag never mutates.
/// Empty remote after trim defaults to `origin`.
pub fn perform_git_push_tag(
    write: &dyn GitWritePort,
    repo: &str,
    remote: &str,
    name: &str,
    approved: bool,
) -> GitTagPushResult {
    let tag = name.trim();
    if tag.is_empty() {
        return GitTagPushResult::refuse("empty tag name");
    }
    if !approved {
        return GitTagPushResult::refuse("approval denied; no mutation");
    }
    let remote = if remote.trim().is_empty() {
        "origin"
    } else {
        remote.trim()
    };
    match write.push_tag(repo, remote, tag, GitWriteApproval::granted()) {
        Ok(()) => GitTagPushResult::ok(),
        Err(e) => GitTagPushResult::refuse(e.to_string()),
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
        w.create_tag("/r", "v1.0.0", "", GitWriteApproval::granted())
            .expect("seed tag");
    }

    #[test]
    fn approved_tag_push_succeeds() {
        let w = FakeGitWrite::new();
        seed(&w);
        let ok = perform_git_push_tag(&w, "/r", "", "v1.0.0", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "tag-push");
        assert_eq!(
            w.last_tag_push("/r"),
            Some(("origin".into(), "v1.0.0".into()))
        );
        assert_eq!(w.remote_tags("/r", "origin"), vec!["v1.0.0".to_string()]);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn unapproved_and_validation_refuse_without_mutation() {
        let w = FakeGitWrite::new();
        seed(&w);

        let denied = perform_git_push_tag(&w, "/r", "origin", "v1.0.0", false);
        assert!(!denied.ok);
        assert!(w.last_tag_push("/r").is_none());

        let empty = perform_git_push_tag(&w, "/r", "origin", "  ", true);
        assert!(!empty.ok);
        assert!(w.last_tag_push("/r").is_none());
    }
}
