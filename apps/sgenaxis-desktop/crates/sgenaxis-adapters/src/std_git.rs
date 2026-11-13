//! Read-only `git` CLI adapter (PD-GIT-01).
//!
//! Shells `git -C <repo> status|log|diff` only — never commit / push / reset.
//! Writes: [`crate::std_git_write::StdGitWrite`] (approval required) or
//! [`crate::git_write::GatedGitWrite`] (default deny).

use std::process::Command;

use sgenaxis_ports::{
    GitBranch, GitCommit, GitConflictFile, GitConflictState, GitPort, GitRemote, GitSettings,
    GitStash, GitStatus, GitStatusEntry, GitStatusKind, GitTag, GitUpstream, PortError,
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
        let stdout = self.run_bytes(repo, args)?;
        String::from_utf8(stdout).map_err(|e| PortError::Git(e.to_string()))
    }

    fn run_bytes(&self, repo: &str, args: &[&str]) -> Result<Vec<u8>, PortError> {
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
        Ok(output.stdout)
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
            &[
                "log",
                &format!("-n{n_arg}"),
                "--pretty=format:%H\t%an\t%aI\t%s",
            ],
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

    fn remotes(&self, repo: &str) -> Result<Vec<GitRemote>, PortError> {
        let out = self.run(repo, &["remote", "-v"])?;
        Ok(parse_remotes(&out))
    }

    fn tags(&self, repo: &str) -> Result<Vec<GitTag>, PortError> {
        let out = self.run(repo, &["tag", "--list"])?;
        Ok(parse_tags(&out))
    }

    fn stashes(&self, repo: &str) -> Result<Vec<GitStash>, PortError> {
        let out = self.run(repo, &["stash", "list", "--no-color"])?;
        Ok(parse_stashes(&out))
    }

    fn conflicts(&self, repo: &str) -> Result<GitConflictState, PortError> {
        read_conflicts(self, repo)
    }

    fn settings(&self, repo: &str) -> Result<GitSettings, PortError> {
        read_settings(self, repo)
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
        .filter_map(parse_log_line)
        .collect()
}

/// Two tab-separated fields stay hash+subject (legacy). Four fields are
/// hash, author, date, subject from live `git log`. Missing author/date
/// become empty strings — never drop the commit.
fn parse_log_line(line: &str) -> Option<GitCommit> {
    let fields: Vec<&str> = line.splitn(4, '\t').collect();
    let hash = *fields.first()?;
    if hash.is_empty() {
        return None;
    }
    let (author, date, subject) = match fields.as_slice() {
        [_] => ("", "", ""),
        [_, subject] => ("", "", *subject),
        [_, author, date] => (*author, *date, ""),
        [_, author, date, subject, ..] => (*author, *date, *subject),
        [] => return None,
    };
    Some(GitCommit {
        hash: hash.to_string(),
        subject: subject.to_string(),
        author: author.to_string(),
        date: date.to_string(),
    })
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

/// Parse `git remote -v` output. Each remote appears twice (fetch + push);
/// dedup to one entry per remote (fetch URL preferred), ordered by name.
fn parse_remotes(text: &str) -> Vec<GitRemote> {
    use std::collections::BTreeMap;
    let mut map: BTreeMap<String, String> = BTreeMap::new();
    for line in text.lines() {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }
        // `<name>\t<url> (fetch|push)`
        let mut it = line.split_whitespace();
        let name = match it.next() {
            Some(n) => n,
            None => continue,
        };
        let url = match it.next() {
            Some(u) => u,
            None => continue,
        };
        let kind = it.next().unwrap_or("");
        let entry = map
            .entry(name.to_string())
            .or_insert_with(|| url.to_string());
        if kind == "(fetch)" {
            *entry = url.to_string(); // prefer the fetch URL
        }
    }
    map.into_iter()
        .map(|(name, url)| GitRemote { name, url })
        .collect()
}

/// Parse `git tag --list` output: one tag per line. Trims blanks,
/// sorts by name.
fn parse_tags(text: &str) -> Vec<GitTag> {
    let mut items: Vec<GitTag> = text
        .lines()
        .map(str::trim)
        .filter(|l| !l.is_empty())
        .map(|name| GitTag {
            name: name.to_string(),
        })
        .collect();
    items.sort_by(|a, b| a.name.cmp(&b.name));
    items
}

/// Parse `git stash list` output: one `stash@{N}: <desc>` per line.
/// Splits id from message on the first `: `; preserves newest-first order.
fn parse_stashes(text: &str) -> Vec<GitStash> {
    text.lines()
        .filter(|l| !l.trim().is_empty())
        .filter_map(|line| {
            let (id, message) = line.split_once(": ")?;
            Some(GitStash {
                id: id.trim().to_string(),
                message: message.trim().to_string(),
            })
        })
        .collect()
}

const MAX_STAGE_FETCHES: usize = 32;
const MAX_STAGE_BYTES: usize = 32 * 1024;

fn read_conflicts(git: &StdGit, repo: &str) -> Result<GitConflictState, PortError> {
    let out = git.run(repo, &["status", "--porcelain=v1", "-b"])?;
    let mut files = parse_unmerged_files(&out);
    let marker = conflict_kind_from_markers(git, repo);
    if files.is_empty() && marker.is_none() {
        return Ok(GitConflictState::default());
    }
    let kind = marker.unwrap_or("Merge").to_string();
    let target = parse_porcelain_status(&out).branch.unwrap_or_default();
    let source = conflict_source(git, repo, &kind);
    attach_stage_blobs(git, repo, &mut files);
    Ok(GitConflictState {
        active: true,
        kind,
        source,
        target,
        files,
    })
}

fn conflict_kind_from_markers(git: &StdGit, repo: &str) -> Option<&'static str> {
    const MARKERS: &[(&str, &str)] = &[
        ("MERGE_HEAD", "Merge"),
        ("REBASE_HEAD", "Rebase"),
        ("CHERRY_PICK_HEAD", "CherryPick"),
        ("REVERT_HEAD", "Revert"),
    ];
    MARKERS
        .iter()
        .find(|(rev, _)| {
            git.run(repo, &["rev-parse", "--verify", "--quiet", rev])
                .is_ok()
        })
        .map(|(_, kind)| *kind)
}

fn conflict_source(git: &StdGit, repo: &str, kind: &str) -> String {
    let rev = match kind {
        "Rebase" => "REBASE_HEAD",
        "CherryPick" => "CHERRY_PICK_HEAD",
        "Revert" => "REVERT_HEAD",
        _ => "MERGE_HEAD",
    };
    let named = git
        .run(repo, &["name-rev", "--name-only", rev])
        .or_else(|_| git.run(repo, &["rev-parse", "--short", rev]))
        .unwrap_or_default();
    let named = named.trim();
    if named.is_empty() || named == "undefined" {
        String::new()
    } else {
        named.to_string()
    }
}

fn unmerged_xy(xy: &str) -> bool {
    matches!(xy, "DD" | "AU" | "UD" | "UA" | "DU" | "AA" | "UU")
}

fn unmerged_kind(code: &str) -> &'static str {
    match code {
        "UU" => "雙方皆修改",
        "AA" => "雙方皆新增",
        "DD" => "雙方皆刪除",
        "AU" => "我方新增",
        "UA" => "對方新增",
        "DU" => "我方刪除",
        "UD" => "對方刪除",
        _ => "未合併",
    }
}

fn parse_unmerged_files(text: &str) -> Vec<GitConflictFile> {
    text.lines()
        .filter(|l| !l.is_empty() && !l.starts_with("## "))
        .filter(|l| l.len() >= 3)
        .filter_map(|line| {
            let code = &line[..2];
            if !unmerged_xy(code) {
                return None;
            }
            let path = rename_path(line[3..].trim());
            if path.is_empty() {
                return None;
            }
            Some(GitConflictFile {
                path,
                code: code.to_string(),
                kind: unmerged_kind(code).to_string(),
                ours: String::new(),
                theirs: String::new(),
            })
        })
        .collect()
}

fn decode_stage_blob(bytes: &[u8]) -> String {
    if bytes.contains(&0) {
        return "(二進位內容)".into();
    }
    let text = String::from_utf8_lossy(bytes).into_owned();
    if text.len() <= MAX_STAGE_BYTES {
        return text;
    }
    let mut end = MAX_STAGE_BYTES;
    while end > 0 && !text.is_char_boundary(end) {
        end -= 1;
    }
    format!("{}…", &text[..end])
}

fn stage_blob(git: &StdGit, repo: &str, stage: u8, path: &str) -> String {
    let spec = format!(":{stage}:{path}");
    match git.run_bytes(repo, &["show", &spec]) {
        Ok(bytes) => decode_stage_blob(&bytes),
        Err(_) => String::new(),
    }
}

fn attach_stage_blobs(git: &StdGit, repo: &str, files: &mut [GitConflictFile]) {
    for file in files.iter_mut().take(MAX_STAGE_FETCHES) {
        file.ours = stage_blob(git, repo, 2, &file.path);
        file.theirs = stage_blob(git, repo, 3, &file.path);
    }
}

fn read_settings(git: &StdGit, repo: &str) -> Result<GitSettings, PortError> {
    Ok(GitSettings {
        author: local_config(git, repo, "user.name"),
        email: local_config(git, repo, "user.email"),
        ignore: read_gitignore(repo),
    })
}

fn local_config(git: &StdGit, repo: &str, key: &str) -> String {
    git.run(repo, &["config", "--local", "--get", key])
        .unwrap_or_default()
        .trim()
        .to_string()
}

fn read_gitignore(repo: &str) -> String {
    if repo.trim().is_empty() {
        return String::new();
    }
    let path = std::path::Path::new(repo).join(".gitignore");
    match std::fs::read(&path) {
        Ok(bytes) => decode_stage_blob(&bytes),
        Err(_) => String::new(),
    }
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
        assert!(commits[0].author.is_empty() && commits[0].date.is_empty());
        assert!(commits[1].author.is_empty() && commits[1].date.is_empty());
    }

    // PD-GIT-HISTORY-01 RED: live `git log` lines carry author + ISO date.
    #[test]
    fn log_parses_author_and_date() {
        let commits = parse_log(
            "abc\tAlex\t2026-10-25T16:42:00+00:00\tinit\n\
             def\tMina\t2026-10-25T15:30:00+08:00\tfeat: x\n",
        );
        assert_eq!(commits.len(), 2);
        assert_eq!(commits[0].hash, "abc");
        assert_eq!(commits[0].author, "Alex");
        assert_eq!(commits[0].date, "2026-10-25T16:42:00+00:00");
        assert_eq!(commits[0].subject, "init");
        assert_eq!(commits[1].author, "Mina");
        assert_eq!(commits[1].date, "2026-10-25T15:30:00+08:00");
        assert_eq!(commits[1].subject, "feat: x");
    }

    #[test]
    fn log_parses_empty_author_date_without_dropping_commit() {
        let commits = parse_log("abc\t\t\tsubject only\n");
        assert_eq!(commits.len(), 1);
        assert_eq!(commits[0].hash, "abc");
        assert!(commits[0].author.is_empty());
        assert!(commits[0].date.is_empty());
        assert_eq!(commits[0].subject, "subject only");
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

    // PD-GIT-REMOTES-01 RED: `git remote -v` has two lines per remote
    // (fetch + push); parser dedups to one entry per remote, fetch URL,
    // ordered by name.
    #[test]
    fn parse_remotes_dedups_fetch_and_push() {
        let text = "\
upstream\thttps://github.com/other/AIAD.git (fetch)\n\
upstream\thttps://github.com/other/AIAD.git (push)\n\
origin\thttps://github.com/roy/AIAD.git (fetch)\n\
origin\thttps://github.com/roy/AIAD.git (push)\n";
        let remotes = parse_remotes(text);
        assert_eq!(remotes.len(), 2, "one entry per remote, not per line");
        assert_eq!(remotes[0].name, "origin");
        assert_eq!(remotes[0].url, "https://github.com/roy/AIAD.git");
        assert_eq!(remotes[1].name, "upstream");
    }

    // PD-GIT-TAGS-01 RED: `git tag --list` → one tag per line; parser trims
    // blanks and sorts by name.
    #[test]
    fn parse_tags_sorts_names() {
        let tags = parse_tags("v2\nv1\n\nv10\n");
        assert_eq!(tags.len(), 3, "blank lines dropped");
        assert_eq!(tags[0].name, "v1");
        assert_eq!(tags[1].name, "v10");
        assert_eq!(tags[2].name, "v2");
    }

    // PD-GIT-STASH-01 RED: `git stash list` → "stash@{N}: <desc>" per line;
    // parser splits id from message and keeps newest-first order.
    #[test]
    fn parse_stashes_splits_id_and_message() {
        let text = "\
stash@{0}: WIP on main: a3f9c2d add slot editor\n\
stash@{1}: On feature/x: tweak theme\n";
        let stashes = parse_stashes(text);
        assert_eq!(stashes.len(), 2);
        assert_eq!(stashes[0].id, "stash@{0}");
        assert_eq!(stashes[0].message, "WIP on main: a3f9c2d add slot editor");
        assert_eq!(stashes[1].id, "stash@{1}");
        assert_eq!(stashes[1].message, "On feature/x: tweak theme");
    }

    // PD-GIT-CONFLICTS-01 RED: porcelain unmerged XY codes become conflict files;
    // ordinary status lines are ignored.
    #[test]
    fn parse_unmerged_files_keeps_conflict_codes() {
        let text = "\
## feature/x...origin/feature/x
UU src/git.ts
AA src/components/GitPanel.tsx
 M src/ok.rs
DU deleted-by-us.rs
";
        let files = parse_unmerged_files(text);
        assert_eq!(files.len(), 3, "ordinary status lines dropped");
        assert_eq!(files[0].path, "src/git.ts");
        assert_eq!(files[0].code, "UU");
        assert_eq!(files[0].kind, "雙方皆修改");
        assert_eq!(files[1].code, "AA");
        assert_eq!(files[1].kind, "雙方皆新增");
        assert_eq!(files[2].code, "DU");
        assert_eq!(files[2].kind, "我方刪除");
    }

    #[test]
    fn parse_unmerged_files_empty_when_clean() {
        let files = parse_unmerged_files("## main\n");
        assert!(files.is_empty());
    }

    #[test]
    fn decode_stage_blob_rejects_binary_and_caps_size() {
        assert_eq!(decode_stage_blob(b"abc\0def"), "(二進位內容)");
        let huge = vec![b'a'; MAX_STAGE_BYTES + 8];
        let cut = decode_stage_blob(&huge);
        assert!(cut.ends_with('…'));
        assert!(cut.len() <= MAX_STAGE_BYTES + 3);
    }

    // PD-GIT-SETTINGS-01 RED: missing / empty repo → empty ignore, never panic.
    #[test]
    fn read_gitignore_empty_when_missing() {
        assert_eq!(read_gitignore(""), "");
        assert_eq!(read_gitignore("/no/such/sgenaxis-settings-repo"), "");
    }

    // PD-GIT-SETTINGS-01 RED: working-tree `.gitignore` is the settings source.
    #[test]
    fn read_gitignore_reads_working_tree_file() {
        let dir = std::env::temp_dir().join(format!(
            "sgenaxis-gitignore-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0)
        ));
        std::fs::create_dir_all(&dir).expect("temp gitignore dir");
        std::fs::write(dir.join(".gitignore"), "node_modules/\ndist/\n").expect("write gitignore");
        let text = read_gitignore(dir.to_str().expect("utf8 temp path"));
        let _ = std::fs::remove_dir_all(&dir);
        assert_eq!(text, "node_modules/\ndist/\n");
    }
}
