//! Git workbench summary use-case (PD-GIT-01) — DTO for later UI projection.
//!
//! Depends only on [`GitPort`]. Write capability is reported as gated (`false`)
//! here — approving writes go through [`crate::StdGitWrite`] / FakeGitWrite
//! with explicit approval; this helper never calls commit / push.

use sgenaxis_ports::{
    GitBranch, GitCommit, GitPort, GitRemote, GitStatusEntry, GitTag, PortError,
};

/// Projection-friendly snapshot of a working tree (status + recent log + diff).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitWorkbenchSummary {
    pub repo: String,
    pub branch: Option<String>,
    pub entries: Vec<GitStatusEntry>,
    pub entry_count: usize,
    pub recent_commits: Vec<GitCommit>,
    /// Full unified diff text from [`GitPort::diff`] (may be large).
    pub diff_text: String,
    /// Commits the local branch is ahead of its upstream (0 when untracked).
    pub ahead: usize,
    /// Commits the local branch is behind its upstream (0 when untracked).
    pub behind: usize,
    /// Upstream ref name when the branch tracks a remote (e.g. `origin/main`).
    pub upstream: Option<String>,
    /// Local branches (current-first); empty when the port read fails (degrade, not blank).
    pub branches: Vec<GitBranch>,
    /// Configured remotes (name-sorted); empty when the port read fails (degrade, not blank).
    pub remotes: Vec<GitRemote>,
    /// Tags (name-sorted); empty when the port read fails (degrade, not blank).
    pub tags: Vec<GitTag>,
    /// `false` for this read-only helper; host enables writes via approving
    /// [`crate::StdGitWrite`] / [`crate::FakeGitWrite`] separately.
    pub writes_enabled: bool,
}

/// Build a summary for UI / Inspector projection. Read-only; never commits.
pub fn summarize_worktree(
    git: &dyn GitPort,
    repo: &str,
    log_limit: usize,
) -> Result<GitWorkbenchSummary, PortError> {
    let status = git.status(repo)?;
    let recent_commits = git.log(repo, log_limit)?;
    let diff_text = git.diff(repo, None)?;

    let (ahead, behind, upstream) = match status.upstream {
        Some(u) => (u.ahead, u.behind, Some(u.name)),
        None => (0, 0, None),
    };

    Ok(GitWorkbenchSummary {
        repo: repo.to_string(),
        branch: status.branch,
        entry_count: status.entries.len(),
        entries: status.entries,
        recent_commits,
        diff_text,
        ahead,
        behind,
        upstream,
        branches: git.branches(repo).unwrap_or_default(),
        remotes: git.remotes(repo).unwrap_or_default(),
        tags: git.tags(repo).unwrap_or_default(),
        writes_enabled: false,
    })
}
