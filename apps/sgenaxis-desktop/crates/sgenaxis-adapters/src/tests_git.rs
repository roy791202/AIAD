//! PD-GIT-01 unit tests — FakeGit + gated write + summary DTO (no real repos).

use sgenaxis_ports::{
    GitBranch, GitCommit, GitConflictFile, GitConflictState, GitPort, GitRemote, GitSettings,
    GitStash, GitStatus, GitStatusEntry, GitStatusKind, GitTag, GitWriteApproval, GitWritePort,
    PortError,
};

use crate::compose::{BoxedPorts, HostPorts};
use crate::fake::{status_with_modified, FakeGit, FakeGitWrite};
use crate::git_summary::summarize_worktree;
use crate::git_write::{GatedGitWrite, GIT_WRITE_GATED_MSG};

#[cfg(feature = "std-adapters")]
use crate::StdGit;

#[test]
fn fake_git_summary_dto_for_ui_projection() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![
                GitStatusEntry {
                    path: "a.rs".into(),
                    kind: GitStatusKind::Modified,
                },
                GitStatusEntry {
                    path: "b.txt".into(),
                    kind: GitStatusKind::Untracked,
                },
            ],
            upstream: None,
        },
    );
    git.set_log(
        "/proj",
        vec![
            GitCommit {
                hash: "aaa".into(),
                subject: "one".into(),
            },
            GitCommit {
                hash: "bbb".into(),
                subject: "two".into(),
            },
        ],
    );
    git.set_diff("/proj", "diff --git a/a.rs\n+line\n");

    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.repo, "/proj");
    assert_eq!(summary.branch.as_deref(), Some("main"));
    assert_eq!(summary.entry_count, 2);
    assert_eq!(summary.entries.len(), 2);
    assert_eq!(summary.recent_commits.len(), 1);
    assert_eq!(summary.recent_commits[0].hash, "aaa");
    assert!(summary.diff_text.contains("a.rs"));
    assert!(!summary.writes_enabled);
}

// PD-GIT-BRANCHES-01 RED: summary must surface local branches (current-first) from the port.
#[test]
fn summarize_worktree_surfaces_branches() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log("/proj", Vec::new());
    git.set_diff("/proj", "");
    git.set_branches(
        "/proj",
        vec![
            GitBranch {
                name: "main".into(),
                is_current: true,
            },
            GitBranch {
                name: "feature".into(),
                is_current: false,
            },
        ],
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.branches.len(), 2);
    assert_eq!(summary.branches[0].name, "main");
    assert!(summary.branches[0].is_current);
    assert_eq!(summary.branches[1].name, "feature");
    assert!(!summary.branches[1].is_current);
}

// PD-GIT-REMOTES-01 RED: summary must surface configured remotes (name-sorted) from the port.
#[test]
fn summarize_worktree_surfaces_remotes() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log("/proj", Vec::new());
    git.set_diff("/proj", "");
    git.set_remotes(
        "/proj",
        vec![
            GitRemote {
                name: "origin".into(),
                url: "https://github.com/roy/AIAD.git".into(),
            },
            GitRemote {
                name: "upstream".into(),
                url: "https://github.com/other/AIAD.git".into(),
            },
        ],
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.remotes.len(), 2);
    assert_eq!(summary.remotes[0].name, "origin");
    assert_eq!(summary.remotes[0].url, "https://github.com/roy/AIAD.git");
    assert_eq!(summary.remotes[1].name, "upstream");
}

// PD-GIT-TAGS-01 RED: summary must surface tags (name-sorted) from the port.
#[test]
fn summarize_worktree_surfaces_tags() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log("/proj", Vec::new());
    git.set_diff("/proj", "");
    git.set_tags(
        "/proj",
        vec![
            GitTag {
                name: "v0.1.0".into(),
            },
            GitTag {
                name: "v0.2.0".into(),
            },
        ],
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.tags.len(), 2);
    assert_eq!(summary.tags[0].name, "v0.1.0");
    assert_eq!(summary.tags[1].name, "v0.2.0");
}

// PD-GIT-STASH-01 RED: summary must surface stashes (newest-first) from the port.
#[test]
fn summarize_worktree_surfaces_stashes() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log("/proj", Vec::new());
    git.set_diff("/proj", "");
    git.set_stashes(
        "/proj",
        vec![
            GitStash {
                id: "stash@{0}".into(),
                message: "WIP on main: slot editor".into(),
            },
            GitStash {
                id: "stash@{1}".into(),
                message: "On feature: theme".into(),
            },
        ],
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.stashes.len(), 2);
    assert_eq!(summary.stashes[0].id, "stash@{0}");
    assert_eq!(summary.stashes[0].message, "WIP on main: slot editor");
    assert_eq!(summary.stashes[1].id, "stash@{1}");
}

// PD-GIT-CONFLICTS-01 RED: summary must surface the conflict snapshot from the port.
#[test]
fn summarize_worktree_surfaces_conflicts() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("feature/git-ui".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log("/proj", Vec::new());
    git.set_diff("/proj", "");
    git.set_conflicts(
        "/proj",
        GitConflictState {
            active: true,
            kind: "Merge".into(),
            source: "main".into(),
            target: "feature/git-ui".into(),
            files: vec![
                GitConflictFile {
                    path: "src/git.ts".into(),
                    code: "UU".into(),
                    kind: "雙方皆修改".into(),
                    ours: "ours".into(),
                    theirs: "theirs".into(),
                },
                GitConflictFile {
                    path: "src/components/GitPanel.tsx".into(),
                    code: "AA".into(),
                    kind: "雙方皆新增".into(),
                    ours: String::new(),
                    theirs: String::new(),
                },
            ],
        },
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert!(summary.conflict.active);
    assert_eq!(summary.conflict.kind, "Merge");
    assert_eq!(summary.conflict.source, "main");
    assert_eq!(summary.conflict.target, "feature/git-ui");
    assert_eq!(summary.conflict.files.len(), 2);
    assert_eq!(summary.conflict.files[0].path, "src/git.ts");
    assert_eq!(summary.conflict.files[0].code, "UU");
    assert_eq!(summary.conflict.files[0].ours, "ours");
}

struct ConflictsUnavailable {
    inner: FakeGit,
}

impl GitPort for ConflictsUnavailable {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError> {
        self.inner.status(repo)
    }
    fn log(&self, repo: &str, limit: usize) -> Result<Vec<GitCommit>, PortError> {
        self.inner.log(repo, limit)
    }
    fn diff(&self, repo: &str, pathspec: Option<&str>) -> Result<String, PortError> {
        self.inner.diff(repo, pathspec)
    }
    fn conflicts(&self, _repo: &str) -> Result<GitConflictState, PortError> {
        Err(PortError::Git("conflicts unavailable".into()))
    }
}

// PD-GIT-CONFLICTS-01: a conflicts-port failure must degrade to empty, never block the snapshot.
#[test]
fn summarize_worktree_degrades_conflicts_to_empty() {
    let inner = FakeGit::new();
    inner.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    inner.set_log("/proj", Vec::new());
    inner.set_diff("/proj", "");
    let git = ConflictsUnavailable { inner };
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary must not block");
    assert!(!summary.conflict.active);
    assert!(summary.conflict.files.is_empty());
}

// PD-GIT-SETTINGS-01 RED: summary must surface local identity + .gitignore from the port.
#[test]
fn summarize_worktree_surfaces_settings() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log("/proj", Vec::new());
    git.set_diff("/proj", "");
    git.set_settings(
        "/proj",
        GitSettings {
            author: "Example Developer".into(),
            email: "dev@example.invalid".into(),
            ignore: "node_modules/\ndist/\n".into(),
        },
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.settings.author, "Example Developer");
    assert_eq!(summary.settings.email, "dev@example.invalid");
    assert_eq!(summary.settings.ignore, "node_modules/\ndist/\n");
}

struct SettingsUnavailable {
    inner: FakeGit,
}

impl GitPort for SettingsUnavailable {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError> {
        self.inner.status(repo)
    }
    fn log(&self, repo: &str, limit: usize) -> Result<Vec<GitCommit>, PortError> {
        self.inner.log(repo, limit)
    }
    fn diff(&self, repo: &str, pathspec: Option<&str>) -> Result<String, PortError> {
        self.inner.diff(repo, pathspec)
    }
    fn settings(&self, _repo: &str) -> Result<GitSettings, PortError> {
        Err(PortError::Git("settings unavailable".into()))
    }
}

// PD-GIT-SETTINGS-01: a settings-port failure must degrade to empty, never block the snapshot.
#[test]
fn summarize_worktree_degrades_settings_to_empty() {
    let inner = FakeGit::new();
    inner.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    inner.set_log("/proj", Vec::new());
    inner.set_diff("/proj", "");
    let git = SettingsUnavailable { inner };
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary must not block");
    assert!(summary.settings.author.is_empty());
    assert!(summary.settings.email.is_empty());
    assert!(summary.settings.ignore.is_empty());
}

// PD-GIT-SWITCH-01 RED: FakeGitWrite records an approved switch; denies without approval.
#[test]
fn fake_git_write_switch_records_when_approved() {
    let w = FakeGitWrite::new();
    // Without approval: PermissionDenied and nothing recorded.
    let denied = w.switch_branch("/r", "feature", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.switched_branch("/r").is_none());
    // With approval: records the target branch.
    w.switch_branch("/r", "feature", GitWriteApproval::granted())
        .expect("switch");
    assert_eq!(w.switched_branch("/r").as_deref(), Some("feature"));
}

#[test]
fn gated_git_write_blocks_commit_and_push() {
    let w = GatedGitWrite::new();
    let c = w.commit("/any", "msg", GitWriteApproval::denied());
    assert!(matches!(c, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let p = w.push("/any", "origin", Some("main"), GitWriteApproval::granted());
    assert!(matches!(p, Err(PortError::PermissionDenied(_))));
}

#[test]
fn boxed_ports_exposes_gated_write() {
    let ports = BoxedPorts::fake();
    let err = ports
        .git_write
        .commit("/r", "x", GitWriteApproval::granted())
        .expect_err("must gate");
    assert!(matches!(err, PortError::PermissionDenied(_)));
}

#[test]
fn host_ports_fake_includes_git_write_gate() {
    let host = HostPorts::fake();
    let _git: &dyn GitPort = &host.git;
    let _w: &dyn GitWritePort = &host.git_write;
    host.git
        .set_status("/r", status_with_modified("dev", "x.rs"));
    assert_eq!(host.git.status("/r").unwrap().branch.as_deref(), Some("dev"));
    assert!(host
        .git_write
        .push("/r", "origin", None, GitWriteApproval::granted())
        .is_err());
}

#[cfg(feature = "std-adapters")]
#[test]
fn std_git_is_git_port_type() {
    // Type-level only — does not shell git or touch user repos.
    let git = StdGit::new();
    let _dyn: &dyn GitPort = &git;
    let host = HostPorts::std_with_git();
    let _g: &dyn GitPort = &host.git;
}

#[cfg(feature = "std-adapters")]
#[test]
fn std_git_porcelain_parser_via_module_tests() {
    // Parser coverage lives in `std_git::parse_tests`; this asserts StdGit
    // binary default and that empty repo path is rejected without spawning.
    let git = StdGit::new();
    assert_eq!(git.program, "git");
    let err = git.status("").expect_err("empty path");
    assert!(matches!(err, PortError::InvalidPath(_)));
}
