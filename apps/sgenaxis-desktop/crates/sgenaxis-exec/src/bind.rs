//! PD-EXEC-BIND-01 — Run must bind project root + work item + worktree fingerprint.

use crate::error::ExecError;
use crate::port::StartRunRequest;

/// Validated binding stamped onto a Run (PRODUCT-DEVELOPMENT §6.2).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RunBinding {
    pub project_root: String,
    pub work_item_id: String,
    pub worktree_fingerprint: String,
}

/// Reject `start_run` when any binding field is missing／empty.
pub fn require_run_binding(req: &StartRunRequest) -> Result<RunBinding, ExecError> {
    let project_root = require_field("project_root", &req.project_root)?;
    let work_item_id = require_field("work_item_id", &req.work_item_id)?;
    let worktree_fingerprint =
        require_field("worktree_fingerprint", &req.worktree_fingerprint)?;
    Ok(RunBinding {
        project_root,
        work_item_id,
        worktree_fingerprint,
    })
}

/// Ensure request root matches an active WORK lease bound root.
pub fn assert_lease_root_consistent(
    project_root: &str,
    lease_bound_root: &str,
) -> Result<(), ExecError> {
    let got = normalize_root(project_root);
    let expected = normalize_root(lease_bound_root);
    if got != expected {
        return Err(ExecError::LeaseRootMismatch {
            expected: lease_bound_root.into(),
            got: project_root.into(),
        });
    }
    Ok(())
}

fn require_field(name: &str, value: &str) -> Result<String, ExecError> {
    let trimmed = value.trim();
    if trimmed.is_empty() {
        return Err(ExecError::MissingBinding(name.into()));
    }
    Ok(trimmed.to_string())
}

fn normalize_root(path: &str) -> String {
    let mut s: String = path
        .trim()
        .chars()
        .map(|c| if c == '\\' { '/' } else { c })
        .collect();
    while s.ends_with('/') && s.len() > 1 {
        s.pop();
    }
    s.to_lowercase()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::port::{AgentProvider, StartRunRequest};

    fn bound_req() -> StartRunRequest {
        StartRunRequest {
            provider: AgentProvider::Cli,
            dry_run: true,
            project_root: "/proj/A".into(),
            work_item_id: "WI-1".into(),
            worktree_fingerprint: "fp-abc".into(),
            mcp_tool: None,
            mcp_tool_args: None,
        }
    }

    #[test]
    fn require_run_binding_accepts_complete_request() {
        let b = require_run_binding(&bound_req()).expect("bound");
        assert_eq!(b.project_root, "/proj/A");
        assert_eq!(b.work_item_id, "WI-1");
        assert_eq!(b.worktree_fingerprint, "fp-abc");
    }

    #[test]
    fn missing_project_root_is_rejected() {
        let mut req = bound_req();
        req.project_root = "  ".into();
        let err = require_run_binding(&req).expect_err("root");
        assert_eq!(err, ExecError::MissingBinding("project_root".into()));
    }

    #[test]
    fn missing_work_item_id_is_rejected() {
        let mut req = bound_req();
        req.work_item_id.clear();
        let err = require_run_binding(&req).expect_err("work");
        assert_eq!(err, ExecError::MissingBinding("work_item_id".into()));
    }

    #[test]
    fn missing_fingerprint_is_rejected() {
        let mut req = bound_req();
        req.worktree_fingerprint.clear();
        let err = require_run_binding(&req).expect_err("fp");
        assert_eq!(
            err,
            ExecError::MissingBinding("worktree_fingerprint".into())
        );
    }

    #[test]
    fn lease_root_must_match_request_root() {
        assert!(assert_lease_root_consistent("/proj/A", "/proj/A").is_ok());
        assert!(assert_lease_root_consistent("/Proj/A/", r"\proj\A").is_ok());
        let err = assert_lease_root_consistent("/proj/A", "/proj/B").expect_err("mismatch");
        assert!(matches!(err, ExecError::LeaseRootMismatch { .. }));
    }
}
