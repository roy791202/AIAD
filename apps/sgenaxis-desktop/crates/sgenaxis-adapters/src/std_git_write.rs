//! Approving Git write adapter via `git` CLI (PD-GIT-02).
//!
//! - Commit / push only when [`GitWriteApproval`] is granted.
//! - Never force-pushes.
//! - On push failure, does not reset / discard local commits.
//! - Error text is credential-redacted.

use std::process::Command;

use sgenaxis_ports::{GitWriteApproval, GitWritePort, PortError};

use crate::git_write::{git_error_redacted, GIT_WRITE_NOT_APPROVED_MSG};

/// Real Git write adapter — shells `git -C <repo> …` after approval.
#[derive(Debug, Default, Clone)]
pub struct StdGitWrite {
    /// Program name or absolute path; default `"git"`.
    pub program: String,
}

impl StdGitWrite {
    pub fn new() -> Self {
        Self {
            program: "git".into(),
        }
    }

    pub fn with_program(program: impl Into<String>) -> Self {
        Self {
            program: program.into(),
        }
    }

    fn require_approval(approval: GitWriteApproval) -> Result<(), PortError> {
        if approval.is_granted() {
            Ok(())
        } else {
            Err(PortError::PermissionDenied(
                GIT_WRITE_NOT_APPROVED_MSG.into(),
            ))
        }
    }

    fn run(&self, repo: &str, args: &[&str]) -> Result<String, PortError> {
        if repo.trim().is_empty() {
            return Err(PortError::InvalidPath("empty git repo path".into()));
        }
        let output = Command::new(&self.program)
            .arg("-C")
            .arg(repo)
            .args(args)
            .output()
            .map_err(|e| git_error_redacted(&format!("{} spawn", self.program), &e.to_string()))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            let code = output.status.code().unwrap_or(-1);
            return Err(git_error_redacted(
                &format!("git {:?} exit {code}", args),
                &stderr,
            ));
        }

        String::from_utf8(output.stdout)
            .map_err(|e| PortError::Git(crate::git_write::redact_credentials(&e.to_string())))
    }
}

impl GitWritePort for StdGitWrite {
    fn commit(
        &self,
        repo: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        if message.trim().is_empty() {
            return Err(PortError::Other("empty commit message".into()));
        }
        // Stage tracked + untracked in this worktree; no force options.
        self.run(repo, &["add", "-A"])?;
        self.run(repo, &["commit", "-m", message])?;
        Ok(())
    }

    fn push(
        &self,
        repo: &str,
        remote: &str,
        refspec: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        if remote.trim().is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        // Explicitly refuse force: never pass --force / --force-with-lease.
        let mut args: Vec<&str> = vec!["push", remote];
        if let Some(r) = refspec {
            if !r.is_empty() {
                args.push(r);
            }
        }
        // On failure: return redacted error only — do not reset / amend / discard.
        self.run(repo, &args)?;
        Ok(())
    }
}
