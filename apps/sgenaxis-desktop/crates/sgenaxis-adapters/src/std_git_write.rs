//! Approving Git write adapter via `git` CLI (PD-GIT-02).
//!
//! - Commit / push / switch / local settings / stash apply+pop+drop+push only
//!   when [`GitWriteApproval`] is granted.
//! - Never force-pushes.
//! - On push failure, does not reset / discard local commits.
//! - Settings: `git config --local` for identity; direct `.gitignore` write.
//!   Never `--global` / `--system`. Never `git rm --cached`.
//! - Stash: `git stash apply/pop/drop -- stash@{n}` and
//!   `git stash push -m <message>` (tracked-only). Never `-q` / `--quiet`.
//!   Never `-u` / `--all`. Never `stash clear`. Never force.
//! - Tag: `git tag -- <name>` (lightweight) or `git tag -a -m <msg> -- <name>`
//!   (annotated). Local delete: `git tag -d -- <name>`. Never `-f` / `--force`.
//!   Never push. Never `git push --delete`. Missing tag fails honestly.
//! - Branch create: `git branch -- <name>` from current HEAD. Never `-C` /
//!   `--force` / `-D` / `-d`. Never remote create. Never `--set-upstream`.
//!   Never checkout/switch. Duplicate / invalid names fail honestly.
//! - Error text is credential-redacted.

use std::fs;
use std::path::Path;
use std::process::Command;

use sgenaxis_ports::{GitWriteApproval, GitWritePort, PortError};

use crate::git_write::{git_error_redacted, GIT_WRITE_NOT_APPROVED_MSG};

/// Root `.gitignore` is a text file; keep a hard cap so the UI cannot dump unbounded bytes.
const MAX_GITIGNORE_BYTES: usize = 1_048_576;

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

    fn require_local_identity(name: &str, email: &str) -> Result<(), PortError> {
        if name.trim().is_empty() || email.trim().is_empty() {
            return Err(PortError::Other("empty user.name or user.email".into()));
        }
        if name.contains('\n')
            || name.contains('\0')
            || email.contains('\n')
            || email.contains('\0')
        {
            return Err(PortError::Other(
                "user.name / user.email must be a single line".into(),
            ));
        }
        if identity_out_of_scope(name) || identity_out_of_scope(email) {
            return Err(PortError::Other(
                "force/global/credential writes are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn write_root_gitignore(repo: &str, contents: &str) -> Result<(), PortError> {
        if repo.trim().is_empty() {
            return Err(PortError::InvalidPath("empty git repo path".into()));
        }
        if contents.len() > MAX_GITIGNORE_BYTES {
            return Err(PortError::Other("gitignore too large".into()));
        }
        if contents.contains('\0') {
            return Err(PortError::Other("gitignore must be text".into()));
        }
        let path = Path::new(repo).join(".gitignore");
        fs::write(&path, contents).map_err(|e| PortError::Io(e.to_string()))
    }

    fn require_stash_selector(stash_ref: &str) -> Result<(), PortError> {
        if stash_ref.trim().is_empty() {
            return Err(PortError::Other("empty stash ref".into()));
        }
        if !is_stash_selector(stash_ref.trim()) {
            return Err(PortError::Other(
                "stash ref must be stash@{n}; drop/clear/push/quiet are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn require_tag_name(name: &str) -> Result<(), PortError> {
        if name.trim().is_empty() {
            return Err(PortError::Other("empty tag name".into()));
        }
        if name.contains('\n') || name.contains('\0') {
            return Err(PortError::Other("tag name must be a single line".into()));
        }
        if tag_out_of_scope(name) {
            return Err(PortError::Other(
                "force/delete/push tag writes are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn require_branch_name(name: &str) -> Result<(), PortError> {
        if name.trim().is_empty() {
            return Err(PortError::Other("empty branch name".into()));
        }
        if name.contains('\n') || name.contains('\0') {
            return Err(PortError::Other("branch name must be a single line".into()));
        }
        if crate::git_write::branch_name_out_of_scope(name) {
            return Err(PortError::Other(
                "force/delete/upstream/switch branch writes are out of scope".into(),
            ));
        }
        Ok(())
    }
}

/// `stash@{N}` only — never flags (`-q`, `--index`) or other stash verbs.
fn is_stash_selector(value: &str) -> bool {
    let Some(rest) = value.strip_prefix("stash@{") else {
        return false;
    };
    let Some(digits) = rest.strip_suffix('}') else {
        return false;
    };
    !digits.is_empty() && digits.bytes().all(|b| b.is_ascii_digit())
}

/// Names that would become flags or destructive tag verbs without `--`.
fn tag_out_of_scope(value: &str) -> bool {
    let t = value.trim();
    let lower = t.to_ascii_lowercase();
    t.starts_with('-')
        || matches!(
            lower.as_str(),
            "--delete" | "-d" | "-f" | "--force" | "push" | "--points-at"
        )
        || lower.contains("..")
}

/// Tokens that would widen identity writes beyond `--local user.name` / `user.email`.
fn identity_out_of_scope(value: &str) -> bool {
    value.split_whitespace().any(|token| {
        let t = token.to_ascii_lowercase();
        matches!(
            t.as_str(),
            "--global" | "--system" | "--file" | "--worktree" | "--force" | "-f" | "--add"
        ) || t.starts_with("--file=")
            || t.starts_with("credential.")
    })
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

    fn switch_branch(
        &self,
        repo: &str,
        branch: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        if branch.trim().is_empty() {
            return Err(PortError::Other("empty branch name".into()));
        }
        // Switch to an existing local branch only: no -c/-C (create),
        // no --force, no --detach. `--` terminates options so a branch
        // named like a flag can never be misread.
        self.run(repo, &["switch", "--", branch])?;
        Ok(())
    }

    fn set_identity(
        &self,
        repo: &str,
        name: &str,
        email: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        Self::require_local_identity(name, email)?;
        // `--local` only. `--` stops option parse so a value like `--global`
        // cannot widen the file scope. Never `--global` / `--system`.
        self.run(
            repo,
            &[
                "config",
                "--local",
                "--replace-all",
                "--",
                "user.name",
                name,
            ],
        )?;
        self.run(
            repo,
            &[
                "config",
                "--local",
                "--replace-all",
                "--",
                "user.email",
                email,
            ],
        )?;
        Ok(())
    }

    fn set_ignore(
        &self,
        repo: &str,
        contents: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        // Direct file write at `<repo>/.gitignore`. Never `git rm --cached`,
        // never `git update-index`, never stop tracking existing files.
        Self::write_root_gitignore(repo, contents)
    }

    fn stash_apply(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let selector = stash_ref.trim();
        Self::require_stash_selector(selector)?;
        // Never `-q` / `--quiet`: conflicts must surface as a failed Result.
        // `--` stops option parse so a selector cannot be read as a flag.
        self.run(repo, &["stash", "apply", "--", selector])?;
        Ok(())
    }

    fn stash_pop(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let selector = stash_ref.trim();
        Self::require_stash_selector(selector)?;
        // Pop itself drops only after a clean apply. Conflict → non-zero,
        // git keeps the stash; we return Err and do not invent success.
        self.run(repo, &["stash", "pop", "--", selector])?;
        Ok(())
    }

    fn stash_drop(
        &self,
        repo: &str,
        stash_ref: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let selector = stash_ref.trim();
        Self::require_stash_selector(selector)?;
        // Never `stash clear` (would wipe the whole list). Never `-q`.
        // `--` stops option parse so a selector cannot be read as a flag.
        self.run(repo, &["stash", "drop", "--", selector])?;
        Ok(())
    }

    fn stash_push(
        &self,
        repo: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let msg = message.trim();
        if msg.is_empty() {
            return Err(PortError::Other("empty stash message".into()));
        }
        if msg.contains('\0') {
            return Err(PortError::Other("stash message must be text".into()));
        }
        // Tracked-only: never `-u` / `--include-untracked` / `--all`.
        // `-m` takes the next argv as the message (not a flag).
        self.run(repo, &["stash", "push", "-m", msg])?;
        Ok(())
    }

    fn create_tag(
        &self,
        repo: &str,
        name: &str,
        message: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let tag = name.trim();
        Self::require_tag_name(tag)?;
        let msg = message.trim();
        if msg.contains('\0') {
            return Err(PortError::Other("tag message must be text".into()));
        }
        // Never `-f` / `--force` (would overwrite). Never `-d` / `--delete`.
        // `--` stops option parse so a name cannot be read as a flag.
        // Duplicate names fail honestly (git exits non-zero without `-f`).
        if msg.is_empty() {
            self.run(repo, &["tag", "--", tag])?;
        } else {
            self.run(repo, &["tag", "-a", "-m", msg, "--", tag])?;
        }
        Ok(())
    }

    fn delete_tag(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let tag = name.trim();
        Self::require_tag_name(tag)?;
        // Local only: `git tag -d -- <name>`. Never `-f` / `--force`.
        // Never `git push` / `git push --delete`. `--` stops option parse
        // so a name cannot be read as a flag. Missing tags fail honestly.
        self.run(repo, &["tag", "-d", "--", tag])?;
        Ok(())
    }

    fn create_branch(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let branch = name.trim();
        Self::require_branch_name(branch)?;
        // Create only: `git branch -- <name>` from current HEAD.
        // Never `-C` / `-c` (would create+switch or overwrite). Never `-D`/`-d`.
        // Never `--force`. Never `--set-upstream`. Never checkout/switch.
        // `--` stops option parse so a name cannot be read as a flag.
        self.run(repo, &["branch", "--", branch])?;
        Ok(())
    }
}
