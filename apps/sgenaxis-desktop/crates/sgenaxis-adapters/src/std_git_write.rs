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
//! - Tag push: `git push -- <remote> refs/tags/<tag>` (empty remote → origin).
//!   Never `--force` / `--force-with-lease` / `+refspec` / `--delete` /
//!   `--all` / `--mirror` / `--tags` (bulk) / branch refspecs.
//!   Existing remote tags fail closed. Unknown remotes are not created.
//! - Branch create: `git branch -- <name>` from current HEAD. Never `-C` /
//!   `--force` / `-D` / `-d`. Never remote create. Never `--set-upstream`.
//!   Never checkout/switch. Duplicate / invalid names fail honestly.
//! - Branch delete: `git branch -d -- <name>` (safe). Never `-D` / `--force` /
//!   `-f`. Never `-r`. Never remote delete. Never checkout/switch.
//!   Current HEAD / missing / unmerged names fail honestly.
//! - Branch rename: `git branch -m -- <old> <new>`. Never `-M` / `--force`.
//!   Never remote rename. Existing target / missing / remote-only fail honestly.
//! - Remote add: `git remote add -- <name> <url>`. Never `-f`. Never fetch.
//!   Never `set-url`. Never `git push`. Duplicate names fail honestly.
//! - Remote remove: `git remote remove -- <name>`. Never prune/fetch.
//!   Missing remotes fail honestly.
//! - Remote set-url: `git remote set-url -- <name> <url>`. Never `--add` /
//!   `--delete` / `--push` / `--mirror`. Never fetch. Never `git push`.
//!   Unknown remotes fail honestly.
//! - Remote rename: `git remote rename -- <old> <new>`. Never fetch /
//!   set-url / push. URL unchanged. Unknown / duplicate names fail honestly.
//! - Set-upstream: `git branch --set-upstream-to=<remote>/<branch> -- <local>`.
//!   Empty local → current branch. Never `--unset-upstream`. Never `-M` / `-C`
//!   / `--force`. Never fetch / pull / push / rebase / merge / checkout /
//!   switch. Never create remotes, tracking refs, or local branches.
//! - Unset-upstream: `git branch --unset-upstream -- <local>`.
//!   Empty local → current branch. Never `--set-upstream-to` / `-u`. Never
//!   `-M` / `-C` / `--force`. Never fetch / pull / push. Never create
//!   remotes, tracking refs, or local branches.
//! - Stage-all: `git add -- .` from the repo root. Never commit / push /
//!   `reset --hard` / `--force`. Never `git add -A` (conflict-save forbids
//!   `-A` / `.`; this path is the explicit ALL-STAGE exception for `.` only).
//!   In-progress merge/rebase/cherry-pick/revert fails with
//!   `OPERATION_IN_PROGRESS`. Clean worktree → success no-op.
//! - Unstage-all: `git reset -- .` from the repo root (mixed pathspec reset).
//!   Never commit / push / `git add -A` / `reset --hard` / `--force`.
//!   In-progress merge/rebase/cherry-pick/revert fails with
//!   `OPERATION_IN_PROGRESS`. Clean index → success no-op. Untracked files
//!   remain `??`.
//! - Stage-file: `git add -- <path>` from the repo root (exactly one pathspec).
//!   Never `.` / `-A` / commit / push / `reset --hard` / `--force`. Distinct
//!   from conflict-save. In-progress merge/rebase/cherry-pick/revert fails
//!   with `OPERATION_IN_PROGRESS`. Empty / `-flag` / `..` paths fail honestly.
//!   Already-staged path → success no-op. Missing path fails honestly.
//! - Unstage-file: `git reset -- <path>` from the repo root (exactly one
//!   pathspec; mixed reset: that path's index → HEAD). Worktree unchanged.
//!   Never `.` / commit / push / `git add -A` / `git add -- .` /
//!   `reset --hard` / `--force`. Distinct from unstage-all (`git reset -- .`)
//!   and conflict-abort (`--abort`). In-progress merge/rebase/cherry-pick/
//!   revert fails with `OPERATION_IN_PROGRESS`. Empty / `-flag` / `..` / `.`
//!   paths fail honestly. Already-unstaged path → success no-op. Untracked
//!   files remain untracked. Missing path fails honestly.
//! - Stage-hunk: `git apply --cached --check -` then `git apply --cached -`
//!   with a text hunk on stdin. Never commit / push / `git add -A` /
//!   `git add -- .` / `reset --hard` / `--force`. Distinct from stage-file
//!   and conflict-save. Empty / `-flag` / `..` paths fail honestly. Empty /
//!   truncated / binary / rename patches fail honestly. Content-hash
//!   mismatch or apply `--check` failure is patch drift (no mutation; do not
//!   guess positions). In-progress merge/rebase/cherry-pick/revert fails
//!   with `OPERATION_IN_PROGRESS`. Already-applied matching hunk → success
//!   no-op when reverse `--check` succeeds.
//! - Fetch: `git fetch -- <remote>` with an optional non-force refspec.
//!   Never merge / pull / rebase / checkout. Never `--force` / `+refspec` /
//!   `--update-head-ok`. Never prune. Unknown remotes fail honestly.
//! - Fetch-prune: `git fetch --prune -- <remote>`. Never `--prune-tags`.
//!   Never `--force` / `+refspec` / `--update-head-ok` / `--add` / `--delete` /
//!   `--push` / `--mirror`. Never pull / merge / rebase. HEAD unchanged.
//! - Pull (ff-only): `git pull --ff-only -- <remote> [<branch>]`. Never
//!   `--rebase` / `--no-ff` / `--force` / `+refspec` / `--update-head-ok`.
//! - Conflict save: `git add -- <path>` after markers are gone. Never `-A` / `.`.
//!   Continue: `git rebase|merge|cherry-pick|revert --continue` for detected
//!   state. Never `--skip`. Never `-X theirs/ours`.
//!   Abort: matching `--abort` family. Never `reset --hard`.
//!   Missing in-progress state fails honestly.
//! - Error text is credential-redacted.

use std::fs;
use std::io::Write;
use std::path::Path;
use std::process::{Command, Stdio};

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

    fn run_stdin(&self, repo: &str, args: &[&str], stdin: &str) -> Result<String, PortError> {
        if repo.trim().is_empty() {
            return Err(PortError::InvalidPath("empty git repo path".into()));
        }
        let mut child = Command::new(&self.program)
            .arg("-C")
            .arg(repo)
            .args(args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()
            .map_err(|e| git_error_redacted(&format!("{} spawn", self.program), &e.to_string()))?;
        if let Some(mut sin) = child.stdin.take() {
            sin.write_all(stdin.as_bytes()).map_err(|e| {
                git_error_redacted(&format!("git {:?} stdin", args), &e.to_string())
            })?;
        }
        let output = child
            .wait_with_output()
            .map_err(|e| git_error_redacted(&format!("git {:?} wait", args), &e.to_string()))?;
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
        if crate::git_write::tag_name_out_of_scope(name) {
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

    fn require_remote_name(name: &str) -> Result<(), PortError> {
        if name.trim().is_empty() {
            return Err(PortError::Other("empty remote name".into()));
        }
        if name.contains('\n') || name.contains('\0') {
            return Err(PortError::Other("remote name must be a single line".into()));
        }
        if crate::git_write::remote_name_out_of_scope(name) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn require_remote_url(url: &str) -> Result<(), PortError> {
        if url.trim().is_empty() {
            return Err(PortError::Other("empty remote url".into()));
        }
        if url.contains('\n') || url.contains('\0') {
            return Err(PortError::Other("remote url must be a single line".into()));
        }
        if crate::git_write::remote_url_out_of_scope(url) {
            return Err(PortError::Other(
                "fetch/force/set-url/push remote writes are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn require_fetch_refspec(refspec: &str) -> Result<(), PortError> {
        if refspec.trim().is_empty() {
            return Ok(());
        }
        if crate::git_write::fetch_refspec_out_of_scope(refspec) {
            return Err(PortError::Other(
                "force/prune/update-head-ok fetch refspecs are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn require_conflict_path(path: &str) -> Result<(), PortError> {
        if path.trim().is_empty() {
            return Err(PortError::Other("empty conflict path".into()));
        }
        if path.contains('\n') || path.contains('\0') {
            return Err(PortError::Other(
                "conflict path must be a single line".into(),
            ));
        }
        if crate::git_write::conflict_path_out_of_scope(path) {
            return Err(PortError::Other(
                "add-all/force/flag conflict paths are out of scope".into(),
            ));
        }
        Ok(())
    }

    fn rev_exists(&self, repo: &str, rev: &str) -> bool {
        if repo.trim().is_empty() {
            return false;
        }
        Command::new(&self.program)
            .arg("-C")
            .arg(repo)
            .args(["rev-parse", "--verify", "--quiet", rev])
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
    }

    fn git_dir_has(&self, repo: &str, relative: &str) -> bool {
        Path::new(repo).join(".git").join(relative).exists()
    }

    /// Detect merge / rebase / cherry-pick / revert. Missing state is an error.
    fn require_conflict_kind(&self, repo: &str) -> Result<&'static str, PortError> {
        // Prefer rebase-merge / rebase-apply. A leftover REBASE_HEAD file can
        // remain after a successful rebase on some Git versions.
        if self.git_dir_has(repo, "rebase-merge") || self.git_dir_has(repo, "rebase-apply") {
            return Ok("Rebase");
        }
        if self.rev_exists(repo, "CHERRY_PICK_HEAD") {
            return Ok("CherryPick");
        }
        if self.rev_exists(repo, "REVERT_HEAD") {
            return Ok("Revert");
        }
        if self.rev_exists(repo, "MERGE_HEAD") {
            return Ok("Merge");
        }
        Err(PortError::Git("no in-progress conflict".into()))
    }

    fn continue_args(kind: &str) -> Result<&'static [&'static str], PortError> {
        match kind {
            "Rebase" => Ok(&["rebase", "--continue"]),
            "CherryPick" => Ok(&["cherry-pick", "--continue"]),
            "Revert" => Ok(&["revert", "--continue"]),
            "Merge" => Ok(&["merge", "--continue"]),
            _ => Err(PortError::Git("no in-progress conflict".into())),
        }
    }

    fn abort_args(kind: &str) -> Result<&'static [&'static str], PortError> {
        match kind {
            "Rebase" => Ok(&["rebase", "--abort"]),
            "CherryPick" => Ok(&["cherry-pick", "--abort"]),
            "Revert" => Ok(&["revert", "--abort"]),
            "Merge" => Ok(&["merge", "--abort"]),
            _ => Err(PortError::Git("no in-progress conflict".into())),
        }
    }

    fn skip_args(kind: &str) -> Result<&'static [&'static str], PortError> {
        match kind {
            "Rebase" => Ok(&["rebase", "--skip"]),
            "CherryPick" => Ok(&["cherry-pick", "--skip"]),
            _ => Err(PortError::Git(
                "conflict cannot be skipped (no skippable rebase/cherry-pick in progress)".into(),
            )),
        }
    }

    fn run_with_editor(&self, repo: &str, args: &[&str]) -> Result<String, PortError> {
        if repo.trim().is_empty() {
            return Err(PortError::InvalidPath("empty git repo path".into()));
        }
        let output = Command::new(&self.program)
            .arg("-C")
            .arg(repo)
            .args([
                "-c",
                "core.editor=/bin/true",
                "-c",
                "sequence.editor=/bin/true",
            ])
            .args(args)
            .env("GIT_EDITOR", "/bin/true")
            .env("GIT_SEQUENCE_EDITOR", "/bin/true")
            .env("EDITOR", "/bin/true")
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

    fn reject_unresolved_markers(repo: &str, rel: &str) -> Result<(), PortError> {
        let path = Path::new(repo).join(rel);
        let text = fs::read_to_string(&path).map_err(|e| PortError::Io(e.to_string()))?;
        if crate::git_write::conflict_markers_present(&text) {
            return Err(PortError::Git(
                "conflict markers still present; not staged".into(),
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

    fn push_tag(
        &self,
        repo: &str,
        remote: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let remote_name = if remote.trim().is_empty() {
            "origin"
        } else {
            remote.trim()
        };
        let tag = name.trim();
        Self::require_remote_name(remote_name)?;
        Self::require_tag_name(tag)?;
        let listed = self.run(repo, &["remote"])?;
        if !listed.lines().any(|line| line.trim() == remote_name) {
            return Err(PortError::Git(format!("No such remote: '{remote_name}'")));
        }
        let tag_ref = format!("refs/tags/{tag}");
        if !self.rev_exists(repo, &tag_ref) {
            return Err(PortError::Git(format!("tag '{tag}' not found")));
        }
        let remote_list = self.run(repo, &["ls-remote", "--tags", "--", remote_name, &tag_ref])?;
        if remote_list.lines().any(|line| {
            let lower = line.to_ascii_lowercase();
            lower.contains(&format!("refs/tags/{tag}")) && !lower.contains("^{}")
        }) {
            return Err(PortError::Git(format!("remote tag '{tag}' already exists")));
        }
        // One tag only: `git push -- <remote> refs/tags/<tag>`.
        // `--` stops option parse. Never `--force` / `+refspec` / `--tags` /
        // `--all` / `--mirror` / `--delete` / branch refspecs.
        self.run(repo, &["push", "--", remote_name, &tag_ref])?;
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

    fn delete_branch(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let branch = name.trim();
        Self::require_branch_name(branch)?;
        let head = self.run(repo, &["rev-parse", "--abbrev-ref", "HEAD"])?;
        if head.trim() == branch {
            return Err(PortError::Other(
                "cannot delete the current HEAD branch".into(),
            ));
        }
        // Safe delete only: `git branch -d -- <name>`. Never `-D` / `--force` /
        // `-f`. Never `-r` (remote-tracking). Never checkout/switch.
        // Unmerged branches fail honestly (git `-d`); no force fallback.
        self.run(repo, &["branch", "-d", "--", branch])?;
        Ok(())
    }

    fn rename_branch(
        &self,
        repo: &str,
        old: &str,
        new: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let old = old.trim();
        let new = new.trim();
        Self::require_branch_name(old)?;
        Self::require_branch_name(new)?;
        let head = self.run(repo, &["rev-parse", "--abbrev-ref", "HEAD"])?;
        let head = head.trim();
        if head == "HEAD" && old.eq_ignore_ascii_case("HEAD") {
            return Err(PortError::Other("cannot rename detached HEAD".into()));
        }
        let local_old = format!("refs/heads/{old}");
        if self
            .run(repo, &["show-ref", "--verify", "--quiet", &local_old])
            .is_err()
        {
            let remote_old = format!("refs/remotes/{old}");
            if self
                .run(repo, &["show-ref", "--verify", "--quiet", &remote_old])
                .is_ok()
            {
                return Err(PortError::Other(format!(
                    "refusing remote-only name '{old}'"
                )));
            }
            return Err(PortError::Git(format!("branch '{old}' not found")));
        }
        let local_new = format!("refs/heads/{new}");
        if old != new
            && self
                .run(repo, &["show-ref", "--verify", "--quiet", &local_new])
                .is_ok()
        {
            return Err(PortError::Git(format!("branch '{new}' already exists")));
        }
        // Non-force only: `git branch -m -- <old> <new>`. Never `-M`.
        self.run(repo, &["branch", "-m", "--", old, new])?;
        Ok(())
    }

    fn add_remote(
        &self,
        repo: &str,
        name: &str,
        url: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let remote = name.trim();
        let remote_url = url.trim();
        Self::require_remote_name(remote)?;
        Self::require_remote_url(remote_url)?;
        // Local config only: `git remote add -- <name> <url>`.
        // Never `-f` (would fetch). Never `set-url`. Never `git push`.
        // `--` stops option parse so name/url cannot be read as flags.
        self.run(repo, &["remote", "add", "--", remote, remote_url])?;
        Ok(())
    }

    fn remove_remote(
        &self,
        repo: &str,
        name: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let remote = name.trim();
        Self::require_remote_name(remote)?;
        // Local config only: `git remote remove -- <name>`.
        // Never prune/fetch. `--` stops option parse.
        // Missing remotes fail honestly (git exits non-zero).
        self.run(repo, &["remote", "remove", "--", remote])?;
        Ok(())
    }

    fn set_remote_url(
        &self,
        repo: &str,
        name: &str,
        url: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let remote = name.trim();
        let remote_url = url.trim();
        Self::require_remote_name(remote)?;
        Self::require_remote_url(remote_url)?;
        // Local config only: `git remote set-url -- <name> <url>`.
        // Never `--add` / `--delete` / `--push` / `--mirror`.
        // Never fetch. Never `git push`. `--` stops option parse.
        self.run(repo, &["remote", "set-url", "--", remote, remote_url])?;
        Ok(())
    }

    fn rename_remote(
        &self,
        repo: &str,
        old: &str,
        new: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let old_name = old.trim();
        let new_name = new.trim();
        Self::require_remote_name(old_name)?;
        Self::require_remote_name(new_name)?;
        if old_name == new_name {
            return Err(PortError::Other("remote name unchanged".into()));
        }
        // Local config only: `git remote rename -- <old> <new>`.
        // Never fetch / set-url / push. `--` stops option parse.
        self.run(repo, &["remote", "rename", "--", old_name, new_name])?;
        Ok(())
    }

    fn set_upstream(
        &self,
        repo: &str,
        remote: &str,
        branch: &str,
        local: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let remote_name = remote.trim();
        let remote_branch = branch.trim();
        Self::require_remote_name(remote_name)?;
        Self::require_branch_name(remote_branch)?;
        let listed = self.run(repo, &["remote"])?;
        if !listed.lines().any(|line| line.trim() == remote_name) {
            return Err(PortError::Git(format!("No such remote: '{remote_name}'")));
        }
        let local_name = if local.trim().is_empty() {
            let head = self.run(repo, &["rev-parse", "--abbrev-ref", "HEAD"])?;
            let head = head.trim();
            if head.is_empty() || head == "HEAD" {
                return Err(PortError::Other(
                    "cannot set upstream on detached HEAD".into(),
                ));
            }
            head.to_string()
        } else {
            local.trim().to_string()
        };
        Self::require_branch_name(&local_name)?;
        let local_ref = format!("refs/heads/{local_name}");
        if self
            .run(repo, &["show-ref", "--verify", "--quiet", &local_ref])
            .is_err()
        {
            return Err(PortError::Git(format!("branch '{local_name}' not found")));
        }
        let tracking = format!("refs/remotes/{remote_name}/{remote_branch}");
        if self
            .run(repo, &["show-ref", "--verify", "--quiet", &tracking])
            .is_err()
        {
            return Err(PortError::Git(format!(
                "remote-tracking branch '{remote_name}/{remote_branch}' not found"
            )));
        }
        let spec = format!("--set-upstream-to={remote_name}/{remote_branch}");
        // Tracking only. Never `--unset-upstream`. Never `-M` / `-C` / `--force`.
        // Never fetch / pull / push / rebase / merge / checkout / switch.
        // `--` stops option parse so a local name cannot be read as a flag.
        self.run(repo, &["branch", &spec, "--", &local_name])?;
        Ok(())
    }

    fn unset_upstream(
        &self,
        repo: &str,
        local: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let local_name = if local.trim().is_empty() {
            let head = self.run(repo, &["rev-parse", "--abbrev-ref", "HEAD"])?;
            let head = head.trim();
            if head.is_empty() || head == "HEAD" {
                return Err(PortError::Other(
                    "cannot unset upstream on detached HEAD".into(),
                ));
            }
            head.to_string()
        } else {
            local.trim().to_string()
        };
        Self::require_branch_name(&local_name)?;
        let local_ref = format!("refs/heads/{local_name}");
        if self
            .run(repo, &["show-ref", "--verify", "--quiet", &local_ref])
            .is_err()
        {
            return Err(PortError::Git(format!("branch '{local_name}' not found")));
        }
        // Tracking clear only. Never `--set-upstream-to` / `-u`. Never `-M` /
        // `-C` / `--force`. Never fetch / pull / push. `--` stops option parse.
        self.run(repo, &["branch", "--unset-upstream", "--", &local_name])?;
        Ok(())
    }

    fn stage_all(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        if self.require_conflict_kind(repo).is_ok() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: resolve or abort before stage-all".into(),
            ));
        }
        let unmerged = self.run(repo, &["ls-files", "-u"])?;
        if !unmerged.trim().is_empty() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: unmerged paths; do not use stage-all to mark conflicts resolved"
                    .into(),
            ));
        }
        // Worktree-only: `git add -- .` from repo root (`git -C <repo>`).
        // Never `-A`. Never commit / push / reset --hard / --force.
        self.run(repo, &["add", "--", "."])?;
        Ok(())
    }

    fn unstage_all(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        if self.require_conflict_kind(repo).is_ok() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: resolve or abort before unstage-all".into(),
            ));
        }
        let unmerged = self.run(repo, &["ls-files", "-u"])?;
        if !unmerged.trim().is_empty() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: unmerged paths; do not use unstage-all to clear conflict state"
                    .into(),
            ));
        }
        // Mixed pathspec reset from repo root: index → HEAD. Worktree unchanged.
        // Never `--hard`. Never commit / push / add -A / --force.
        self.run(repo, &["reset", "--", "."])?;
        Ok(())
    }

    fn stage_file(
        &self,
        repo: &str,
        path: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let rel = path.trim();
        if rel.is_empty() {
            return Err(PortError::Other("empty stage path".into()));
        }
        if crate::git_write::stage_file_path_out_of_scope(rel) {
            return Err(PortError::Other(
                "flag/traversal/all stage paths are out of scope".into(),
            ));
        }
        if self.require_conflict_kind(repo).is_ok() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: resolve or abort before stage-file".into(),
            ));
        }
        let unmerged = self.run(repo, &["ls-files", "-u"])?;
        if !unmerged.trim().is_empty() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: unmerged paths; do not use stage-file to mark conflicts resolved"
                    .into(),
            ));
        }
        // Worktree-only: exactly one pathspec. Never `.` / `-A`.
        // Never commit / push / reset --hard / --force.
        self.run(repo, &["add", "--", rel])?;
        Ok(())
    }

    fn unstage_file(
        &self,
        repo: &str,
        path: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let rel = path.trim();
        if rel.is_empty() {
            return Err(PortError::Other("empty unstage path".into()));
        }
        if crate::git_write::stage_file_path_out_of_scope(rel) {
            return Err(PortError::Other(
                "flag/traversal/all unstage paths are out of scope".into(),
            ));
        }
        if self.require_conflict_kind(repo).is_ok() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: resolve or abort before unstage-file".into(),
            ));
        }
        let unmerged = self.run(repo, &["ls-files", "-u"])?;
        if !unmerged.trim().is_empty() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: unmerged paths; do not use unstage-file to clear conflict state"
                    .into(),
            ));
        }
        let present = Path::new(repo).join(rel).exists()
            || !self.run(repo, &["ls-files", "--", rel])?.trim().is_empty();
        if !present {
            return Err(PortError::Git(format!(
                "pathspec '{rel}' did not match any files"
            )));
        }
        // Mixed pathspec reset: that path's index → HEAD. Worktree unchanged.
        // Never `--hard`. Never commit / push / add -A / `.` / --force.
        self.run(repo, &["reset", "--", rel])?;
        Ok(())
    }

    fn stage_hunk(
        &self,
        repo: &str,
        path: &str,
        patch: &str,
        content_hash: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let rel = path.trim();
        if rel.is_empty() {
            return Err(PortError::Other("empty stage path".into()));
        }
        if crate::git_write::stage_file_path_out_of_scope(rel) {
            return Err(PortError::Other(
                "flag/traversal/all stage paths are out of scope".into(),
            ));
        }
        if content_hash.trim().is_empty() {
            return Err(PortError::Other("empty content hash".into()));
        }
        if let Some(reason) = crate::git_write::stage_hunk_patch_refused(patch) {
            return Err(PortError::Git(reason.into()));
        }
        if patch_targets_other_path(patch, rel) {
            return Err(PortError::Git(
                "patch path does not match selected file".into(),
            ));
        }
        if self.require_conflict_kind(repo).is_ok() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: resolve or abort before stage-hunk".into(),
            ));
        }
        let unmerged = self.run(repo, &["ls-files", "-u"])?;
        if !unmerged.trim().is_empty() {
            return Err(PortError::Git(
                "OPERATION_IN_PROGRESS: unmerged paths; do not use stage-hunk to mark conflicts resolved"
                    .into(),
            ));
        }
        let worktree = Path::new(repo).join(rel);
        let bytes = fs::read(&worktree)
            .map_err(|e| PortError::Git(format!("cannot read worktree path '{rel}': {e}")))?;
        if bytes.contains(&0) {
            return Err(PortError::Git("binary hunks are disabled".into()));
        }
        let sha = sgenaxis_spec::packet::source_sha256(&bytes);
        let oid = self
            .run(repo, &["hash-object", "--", rel])
            .ok()
            .unwrap_or_default();
        let hash_ok = content_hash.eq_ignore_ascii_case(&sha) || content_hash.trim() == oid.trim();
        if !hash_ok {
            return Err(PortError::Git(
                "patch drift: content hash mismatch; no mutation".into(),
            ));
        }
        match self.run_stdin(repo, &["apply", "--cached", "--check", "-"], patch) {
            Ok(_) => {}
            Err(_) => {
                // Already-applied matching hunk: reverse check succeeds → no-op.
                if self
                    .run_stdin(
                        repo,
                        &["apply", "--cached", "--reverse", "--check", "-"],
                        patch,
                    )
                    .is_ok()
                {
                    return Ok(());
                }
                return Err(PortError::Git("patch drift refused; no mutation".into()));
            }
        }
        self.run_stdin(repo, &["apply", "--cached", "-"], patch)?;
        Ok(())
    }

    fn conflict_save(
        &self,
        repo: &str,
        path: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let rel = path.trim();
        Self::require_conflict_path(rel)?;
        self.require_conflict_kind(repo)?;
        Self::reject_unresolved_markers(repo, rel)?;
        // One path only: `git add -- <path>`. Never `-A` / `.` / `--all`.
        self.run(repo, &["add", "--", rel])?;
        Ok(())
    }

    fn conflict_continue(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let kind = self.require_conflict_kind(repo)?;
        let args = Self::continue_args(kind)?;
        // Never `--skip`. Never `-X theirs` / `-X ours`.
        // GIT_EDITOR=true finishes the existing commit message without a TTY.
        self.run_with_editor(repo, args)?;
        Ok(())
    }

    fn conflict_abort(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let kind = self.require_conflict_kind(repo)?;
        let args = Self::abort_args(kind)?;
        // Prefer `--abort`. Never `reset --hard`.
        self.run(repo, args)?;
        Ok(())
    }

    fn conflict_skip(&self, repo: &str, approval: GitWriteApproval) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let kind = self.require_conflict_kind(repo)?;
        let args = Self::skip_args(kind)?;
        // Real `git rebase --skip` / `git cherry-pick --skip` only.
        // Never `--continue` / `--abort` as a fallback. Never delete files.
        self.run(repo, args)?;
        Ok(())
    }

    fn fetch(
        &self,
        repo: &str,
        remote: &str,
        refspec: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let name = remote.trim();
        Self::require_remote_name(name)?;
        let spec = refspec.map(str::trim).filter(|s| !s.is_empty());
        if let Some(s) = spec {
            Self::require_fetch_refspec(s)?;
        }
        let listed = self.run(repo, &["remote"])?;
        if !listed.lines().any(|line| line.trim() == name) {
            return Err(PortError::Git(format!("No such remote: '{name}'")));
        }
        // Remote-tracking refs only: `git fetch -- <remote> [refspec]`.
        // `--` stops option parse. Never `--force` / `+refspec` / prune /
        // `--update-head-ok`. Never merge / pull / rebase / checkout.
        let spec_owned = spec.map(str::to_string);
        let mut args = vec!["fetch", "--", name];
        if let Some(s) = spec_owned.as_deref() {
            args.push(s);
        }
        self.run(repo, &args)?;
        Ok(())
    }

    fn fetch_prune(
        &self,
        repo: &str,
        remote: &str,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let name = remote.trim();
        Self::require_remote_name(name)?;
        let listed = self.run(repo, &["remote"])?;
        if !listed.lines().any(|line| line.trim() == name) {
            return Err(PortError::Git(format!("No such remote: '{name}'")));
        }
        // Remote-tracking refs only: `git fetch --prune -- <remote>`.
        // `--prune` is a dedicated flag on this path; `--` stops option parse.
        // Never `--prune-tags`. Never `--force` / `+refspec` / `--update-head-ok`.
        // Never pull / merge / rebase / checkout.
        self.run(repo, &["fetch", "--prune", "--", name])?;
        Ok(())
    }

    fn pull_ff_only(
        &self,
        repo: &str,
        remote: &str,
        branch: Option<&str>,
        approval: GitWriteApproval,
    ) -> Result<(), PortError> {
        Self::require_approval(approval)?;
        let name = remote.trim();
        Self::require_remote_name(name)?;
        let branch_owned = branch.map(str::trim).filter(|s| !s.is_empty());
        if let Some(b) = branch_owned {
            Self::require_branch_name(b)?;
        }
        let listed = self.run(repo, &["remote"])?;
        if !listed.lines().any(|line| line.trim() == name) {
            return Err(PortError::Git(format!("No such remote: '{name}'")));
        }
        // Only fast-forward pull: `git pull --ff-only -- <remote> [<branch>]`.
        // `--` stops option parse. Never `--rebase` / `--no-ff` / `--force`.
        let mut args = vec!["pull", "--ff-only", "--", name];
        if let Some(b) = branch_owned {
            args.push(b);
        }
        self.run(repo, &args)?;
        Ok(())
    }
}

fn patch_targets_other_path(patch: &str, rel: &str) -> bool {
    let mut saw_path = false;
    for line in patch.lines() {
        if let Some(rest) = line.strip_prefix("diff --git ") {
            saw_path = true;
            let parts: Vec<&str> = rest.split_whitespace().collect();
            if parts.len() >= 2 {
                let a = parts[0].trim_start_matches("a/");
                let b = parts[1].trim_start_matches("b/");
                if a != rel || b != rel {
                    return true;
                }
            }
        }
        if let Some(rest) = line.strip_prefix("--- ") {
            if rest != "/dev/null" {
                saw_path = true;
                let p = rest.trim_start_matches("a/");
                if p != rel {
                    return true;
                }
            }
        }
        if let Some(rest) = line.strip_prefix("+++ ") {
            if rest != "/dev/null" {
                saw_path = true;
                let p = rest.trim_start_matches("b/");
                if p != rel {
                    return true;
                }
            }
        }
    }
    !saw_path
}
