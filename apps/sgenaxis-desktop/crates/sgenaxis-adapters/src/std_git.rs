//! Read-only `git` CLI adapter (PD-GIT-01).
//!
//! Shells `git -C <repo> status|log|diff` only — never commit / push / reset.
//! Writes: [`crate::std_git_write::StdGitWrite`] (approval required) or
//! [`crate::git_write::GatedGitWrite`] (default deny).

use std::process::Command;

use sgenaxis_ports::{
    GitBranch, GitCommit, GitPort, GitStatus, GitStatusEntry, GitStatusKind, GitUpstream,
    PortError,
};

/// Real Git read adapter via the `git` executable on `PATH`.
#[derive(Debug, Default, Clone)]
pub struct StdGit {
    /// Program name or absolute path; default `"git"`.
    pub program: String,
}

impl StdGit {
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

    fn run(&self, repo: &str, args: &[&str]) -> Result<String, PortError> {
        if repo.trim().is_empty() {
            return Err(PortError::InvalidPath("empty git repo path".into()));
        }
        let output = Command::new(&self.program)
            .arg("-C")
            .arg(repo)
            .args(args)
            .output()
            .map_err(|e| PortError::Git(format!("{}: {e}", self.program)))?;

        if !output.status.success() {
            let stderr = String::from_utf8_lossy(&output.stderr).trim().to_string();
            let code = output.status.code().unwrap_or(-1);
            return Err(PortError::Git(format!(
                "git {:?} exit {code}: {stderr}",
                args
            )));
        }

        String::from_utf8(output.stdout).map_err(|e| PortError::Git(e.to_string()))
    }
}

impl GitPort for StdGit {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError> {
        // Porcelain v1 + branch header; read-only.
        let out = self.run(repo, &["status", "--porcelain=v1", "-b"])?;
        Ok(parse_porcelain_status(&out))
    }

    fn log(&self, repo: &str, limit: usize) -> Result<Vec<GitCommit>, PortError> {
        let n = if limit == 0 { 0 } else { limit };
        if n == 0 {
            return Ok(Vec::new());
        }
        let n_arg = n.to_string();
        let out = self.run(
            repo,
            &["log", &format!("-n{n_arg}"), "--pretty=format:%H\t%s"],
        )?;
        Ok(parse_log(&out))
    }

    fn diff(&self, repo: &str, pathspec: Option<&str>) -> Result<String, PortError> {
        let mut args: Vec<&str> = vec!["diff", "--no-ext-diff", "--"];
        if let Some(p) = pathspec {
            if !p.is_empty() {
                args.push(p);
            }
        }
        self.run(repo, &args)
    }

    fn branches(&self, repo: &str) -> Result<Vec<GitBranch>, PortError> {
        let out = self.run(repo, &["branch", "--no-color"])?;
        Ok(parse_branches(&out))
    }
}

fn parse_porcelain_status(text: &str) -> GitStatus {
    let mut branch = None;
    let mut entries = Vec::new();
    let mut upstream = None;

    for line in text.lines() {
        if line.is_empty() {
            continue;
        }
        if let Some(rest) = line.strip_prefix("## ") {
            let (name, up) = parse_branch_header(rest);
            branch = Some(name);
            upstream = up;
            continue;
        }
        if line.len() < 3 {
            continue;
        }
        let xy = &line[..2];
        let path_part = line[3..].trim();
        if path_part.is_empty() {
            continue;
        }
        let path = rename_path(path_part);
        let kind = status_kind(xy);
        entries.push(GitStatusEntry { path, kind });
    }

    GitStatus {
        branch,
        entries,
        upstream,
    }
}

fn parse_branch_header(rest: &str) -> (String, Option<GitUpstream>) {
    // `main...origin/main [ahead 1, behind 2]` → ("main", upstream origin/main 1/2)
    // `main...origin/main`                     → ("main", upstream origin/main 0/0)
    // `main`                                   → ("main", None)
    // `No commits yet on main`                 → ("main", None)
    let head = rest.split_whitespace().next().unwrap_or(rest);
    if let Some((local, remote)) = head.split_once("...") {
        let (ahead, behind) = parse_ahead_behind(rest);
        return (
            local.to_string(),
            Some(GitUpstream {
                name: remote.to_string(),
                ahead,
                behind,
            }),
        );
    }
    if let Some(name) = rest.strip_prefix("No commits yet on ") {
        let local = name.split_whitespace().next().unwrap_or(name).to_string();
        return (local, None);
    }
    (head.to_string(), None)
}

/// Parse a trailing `[ahead N, behind M]` (either term optional) into counts.
fn parse_ahead_behind(rest: &str) -> (usize, usize) {
    let (mut ahead, mut behind) = (0usize, 0usize);
    if let Some(open) = rest.find('[') {
        if let Some(rel) = rest[open..].find(']') {
            let inside = &rest[open + 1..open + rel];
            for part in inside.split(',') {
                let mut it = part.split_whitespace();
                match (it.next(), it.next()) {
                    (Some("ahead"), Some(n)) => ahead = n.parse().unwrap_or(0),
                    (Some("behind"), Some(n)) => behind = n.parse().unwrap_or(0),
                    _ => {}
                }
            }
        }
    }
    (ahead, behind)
}

fn rename_path(path_part: &str) -> String {
    // `old -> new` or quoted forms; take the destination when renaming.
    if let Some((_, new)) = path_part.split_once(" -> ") {
        new.trim().trim_matches('"').to_string()
    } else {
        path_part.trim_matches('"').to_string()
    }
}

fn status_kind(xy: &str) -> GitStatusKind {
    let chars: Vec<char> = xy.chars().collect();
    let (x, y) = match chars.as_slice() {
        [a, b] => (*a, *b),
        _ => return GitStatusKind::Other,
    };
    if x == '?' || y == '?' {
        return GitStatusKind::Untracked;
    }
    // Prefer index letter, else worktree.
    let code = if x != ' ' && x != '?' { x } else { y };
    match code {
        'M' => GitStatusKind::Modified,
        'A' => GitStatusKind::Added,
        'D' => GitStatusKind::Deleted,
        'R' | 'C' => GitStatusKind::Renamed,
        _ => GitStatusKind::Other,
    }
}

fn parse_log(text: &str) -> Vec<GitCommit> {
    text.lines()
        .filter(|l| !l.is_empty())
        .filter_map(|line| {
            let (hash, subject) = line.split_once('\t')?;
            Some(GitCommit {
                hash: hash.to_string(),
                subject: subject.to_string(),
            })
        })
        .collect()
}

/// Parse `git branch` output into local branches; `*` marks current.
/// Orders current-first, then by name. Detached-HEAD synthetic lines are skipped.
fn parse_branches(text: &str) -> Vec<GitBranch> {
    let mut items: Vec<GitBranch> = text
        .lines()
        .map(str::trim_end)
        .filter(|l| !l.is_empty())
        .filter_map(|line| {
            let is_current = line.starts_with('*');
            let name = line.trim_start_matches('*').trim();
            if name.is_empty() || name.starts_with('(') {
                return None; // detached HEAD / non-branch line
            }
            Some(GitBranch {
                name: name.to_string(),
                is_current,
            })
        })
        .collect();
    items.sort_by(|a, b| {
        b.is_current
            .cmp(&a.is_current)
            .then_with(|| a.name.cmp(&b.name))
    });
    items
}

#[cfg(test)]
mod parse_tests {
    use super::*;

    #[test]
    fn porcelain_parses_branch_and_entries() {
        let text = "\
## feature/x...origin/feature/x
 M src/a.rs
A  new.txt
?? scratch.md
R  old.rs -> renamed.rs
";
        let st = parse_porcelain_status(text);
        assert_eq!(st.branch.as_deref(), Some("feature/x"));
        assert_eq!(st.entries.len(), 4);
        assert_eq!(st.entries[0].kind, GitStatusKind::Modified);
        assert_eq!(st.entries[1].kind, GitStatusKind::Added);
        assert_eq!(st.entries[2].kind, GitStatusKind::Untracked);
        assert_eq!(st.entries[3].path, "renamed.rs");
        assert_eq!(st.entries[3].kind, GitStatusKind::Renamed);
    }

    #[test]
    fn log_parses_hash_and_subject() {
        let commits = parse_log("abc\tinit\ndef\tfeat: x\n");
        assert_eq!(commits.len(), 2);
        assert_eq!(commits[0].hash, "abc");
        assert_eq!(commits[1].subject, "feat: x");
    }

    // G2 RED (PD-GIT-01): upstream ahead/behind must be captured, not discarded.
    #[test]
    fn porcelain_captures_upstream_ahead_behind() {
        let text = "## main...origin/main [ahead 2, behind 3]\n M src/a.rs\n";
        let st = parse_porcelain_status(text);
        assert_eq!(st.branch.as_deref(), Some("main"));
        let up = st.upstream.expect("upstream divergence parsed");
        assert_eq!(up.name, "origin/main");
        assert_eq!(up.ahead, 2);
        assert_eq!(up.behind, 3);
    }

    // PD-GIT-BRANCHES-01 RED: local branch list marks current, orders current-first then name-sorted.
    #[test]
    fn parse_branches_marks_current_and_orders() {
        // `git branch` style: '*' marks the current branch.
        let text = "  zeta\n* main\n  alpha\n";
        let branches = parse_branches(text);
        assert_eq!(branches.len(), 3);
        assert_eq!(branches[0].name, "main");
        assert!(branches[0].is_current, "current branch first and marked");
        assert_eq!(branches[1].name, "alpha");
        assert_eq!(branches[2].name, "zeta");
        assert!(!branches[1].is_current && !branches[2].is_current);
    }
}
