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
                ..Default::default()
            },
            GitCommit {
                hash: "bbb".into(),
                subject: "two".into(),
                ..Default::default()
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

// PD-GIT-HISTORY-01 RED: summary must surface author + date from the port log.
#[test]
fn summarize_worktree_surfaces_history_author_and_date() {
    let git = FakeGit::new();
    git.set_status(
        "/proj",
        GitStatus {
            branch: Some("main".into()),
            entries: vec![],
            upstream: None,
        },
    );
    git.set_log(
        "/proj",
        vec![GitCommit {
            hash: "aaa".into(),
            subject: "feat: polish Git panel".into(),
            author: "Alex".into(),
            date: "2026-10-25T16:42:00+00:00".into(),
        }],
    );
    git.set_diff("/proj", "");
    let summary = summarize_worktree(&git, "/proj", 5).expect("summary");
    assert_eq!(summary.recent_commits.len(), 1);
    assert_eq!(summary.recent_commits[0].hash, "aaa");
    assert_eq!(summary.recent_commits[0].subject, "feat: polish Git panel");
    assert_eq!(summary.recent_commits[0].author, "Alex");
    assert_eq!(summary.recent_commits[0].date, "2026-10-25T16:42:00+00:00");
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
                tested: true,
            },
            GitRemote {
                name: "upstream".into(),
                url: "https://github.com/other/AIAD.git".into(),
                tested: false,
            },
        ],
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.remotes.len(), 2);
    assert_eq!(summary.remotes[0].name, "origin");
    assert_eq!(summary.remotes[0].url, "https://github.com/roy/AIAD.git");
    assert!(summary.remotes[0].tested);
    assert_eq!(summary.remotes[1].name, "upstream");
    assert!(!summary.remotes[1].tested);
}

// PD-GIT-TAGS-01 RED: summary must surface tags (name-sorted) from the port,
// including peeled commit OIDs set by the adapter (never invented here).
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
                peeled: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".into(),
            },
            GitTag {
                name: "v0.2.0".into(),
                peeled: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".into(),
            },
        ],
    );
    let summary = summarize_worktree(&git, "/proj", 1).expect("summary");
    assert_eq!(summary.tags.len(), 2);
    assert_eq!(summary.tags[0].name, "v0.1.0");
    assert_eq!(
        summary.tags[0].peeled,
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    );
    assert_eq!(summary.tags[1].name, "v0.2.0");
    assert_eq!(
        summary.tags[1].peeled,
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    );
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

// Settings writes: FakeGitWrite records approved identity / ignore; denies without.
#[test]
fn fake_git_write_settings_record_when_approved() {
    let w = FakeGitWrite::new();
    let denied_id = w.set_identity(
        "/r",
        "Ada",
        "ada@example.invalid",
        GitWriteApproval::denied(),
    );
    assert!(matches!(denied_id, Err(PortError::PermissionDenied(_))));
    assert!(w.last_identity("/r").is_none());
    let denied_ig = w.set_ignore("/r", "target/\n", GitWriteApproval::denied());
    assert!(matches!(denied_ig, Err(PortError::PermissionDenied(_))));
    assert!(w.last_ignore("/r").is_none());

    w.set_identity(
        "/r",
        "Ada",
        "ada@example.invalid",
        GitWriteApproval::granted(),
    )
    .expect("identity");
    assert_eq!(
        w.last_identity("/r"),
        Some(("Ada".into(), "ada@example.invalid".into()))
    );
    w.set_ignore("/r", "target/\n", GitWriteApproval::granted())
        .expect("ignore");
    assert_eq!(w.last_ignore("/r").as_deref(), Some("target/\n"));
}

#[test]
fn fake_git_write_stash_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied_apply = w.stash_apply("/r", "stash@{0}", GitWriteApproval::denied());
    assert!(matches!(denied_apply, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stash_apply("/r").is_none());
    let denied_pop = w.stash_pop("/r", "stash@{0}", GitWriteApproval::denied());
    assert!(matches!(denied_pop, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stash_pop("/r").is_none());

    w.stash_apply("/r", "stash@{0}", GitWriteApproval::granted())
        .expect("apply");
    assert_eq!(w.last_stash_apply("/r").as_deref(), Some("stash@{0}"));
    w.stash_pop("/r", "stash@{1}", GitWriteApproval::granted())
        .expect("pop");
    assert_eq!(w.last_stash_pop("/r").as_deref(), Some("stash@{1}"));

    w.fail_next_stash("/r", "CONFLICT (content): merge conflict in a.txt");
    let conflict = w.stash_pop("/r", "stash@{0}", GitWriteApproval::granted());
    assert!(matches!(conflict, Err(PortError::Git(_))));
    assert_eq!(w.last_stash_pop("/r").as_deref(), Some("stash@{1}"));

    let denied_drop = w.stash_drop("/r", "stash@{0}", GitWriteApproval::denied());
    assert!(matches!(denied_drop, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stash_drop("/r").is_none());
    w.stash_drop("/r", "stash@{2}", GitWriteApproval::granted())
        .expect("drop");
    assert_eq!(w.last_stash_drop("/r").as_deref(), Some("stash@{2}"));
    w.fail_next_stash("/r", "stash@{9} is not a valid reference");
    let missing = w.stash_drop("/r", "stash@{9}", GitWriteApproval::granted());
    assert!(matches!(missing, Err(PortError::Git(_))));
    assert_eq!(w.last_stash_drop("/r").as_deref(), Some("stash@{2}"));

    let denied_push = w.stash_push("/r", "wip", GitWriteApproval::denied());
    assert!(matches!(denied_push, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stash_push("/r").is_none());
    w.stash_push("/r", "WIP: panel", GitWriteApproval::granted())
        .expect("push");
    assert_eq!(w.last_stash_push("/r").as_deref(), Some("WIP: panel"));
}

#[test]
fn fake_git_write_tag_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.create_tag("/r", "v1.0.0", "", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_tag_create("/r").is_none());
    assert!(w.created_tags("/r").is_empty());

    w.create_tag("/r", "v1.0.0", "", GitWriteApproval::granted())
        .expect("lightweight");
    assert_eq!(w.last_tag_create("/r"), Some(("v1.0.0".into(), "".into())));
    assert_eq!(w.created_tags("/r"), vec!["v1.0.0".to_string()]);

    w.create_tag("/r", "v1.1.0", "release", GitWriteApproval::granted())
        .expect("annotated");
    assert_eq!(
        w.last_tag_create("/r"),
        Some(("v1.1.0".into(), "release".into()))
    );
    assert_eq!(
        w.created_tags("/r"),
        vec!["v1.0.0".to_string(), "v1.1.0".to_string()]
    );

    let dup = w.create_tag("/r", "v1.0.0", "again", GitWriteApproval::granted());
    assert!(matches!(dup, Err(PortError::Git(ref m)) if m.contains("already exists")));
    assert_eq!(
        w.last_tag_create("/r"),
        Some(("v1.1.0".into(), "release".into()))
    );
    assert_eq!(
        w.created_tags("/r"),
        vec!["v1.0.0".to_string(), "v1.1.0".to_string()]
    );
}

#[test]
fn fake_git_write_tag_delete_records_when_approved() {
    let w = FakeGitWrite::new();
    w.create_tag("/r", "v1.0.0", "", GitWriteApproval::granted())
        .expect("seed");
    w.create_tag("/r", "v1.1.0", "release", GitWriteApproval::granted())
        .expect("seed annotated");
    assert_eq!(
        w.created_tags("/r"),
        vec!["v1.0.0".to_string(), "v1.1.0".to_string()]
    );

    let denied = w.delete_tag("/r", "v1.0.0", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_tag_delete("/r").is_none());
    assert_eq!(
        w.created_tags("/r"),
        vec!["v1.0.0".to_string(), "v1.1.0".to_string()]
    );

    w.delete_tag("/r", "v1.0.0", GitWriteApproval::granted())
        .expect("delete");
    assert_eq!(w.last_tag_delete("/r").as_deref(), Some("v1.0.0"));
    assert_eq!(w.created_tags("/r"), vec!["v1.1.0".to_string()]);
    assert_eq!(
        w.last_tag_create("/r"),
        Some(("v1.1.0".into(), "release".into()))
    );

    let missing = w.delete_tag("/r", "v9.9.9", GitWriteApproval::granted());
    assert!(matches!(missing, Err(PortError::Git(ref m)) if m.contains("not found")));
    assert_eq!(w.last_tag_delete("/r").as_deref(), Some("v1.0.0"));
    assert_eq!(w.created_tags("/r"), vec!["v1.1.0".to_string()]);
}

#[test]
fn fake_git_write_tag_push_records_when_approved() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .expect("seed remote");
    w.create_tag("/r", "v1.0.0", "", GitWriteApproval::granted())
        .expect("seed light");
    w.create_tag("/r", "v1.1.0", "release", GitWriteApproval::granted())
        .expect("seed annotated");

    let denied = w.push_tag("/r", "origin", "v1.0.0", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_tag_push("/r").is_none());

    let empty = w.push_tag("/r", "origin", "  ", GitWriteApproval::granted());
    assert!(matches!(empty, Err(PortError::Other(_))));

    let flag = w.push_tag("/r", "origin", "-f", GitWriteApproval::granted());
    assert!(matches!(flag, Err(PortError::Other(_))));
    let plus = w.push_tag("/r", "origin", "+v1.0.0", GitWriteApproval::granted());
    assert!(matches!(plus, Err(PortError::Other(_))));
    let bulk = w.push_tag("/r", "origin", "--tags", GitWriteApproval::granted());
    assert!(matches!(bulk, Err(PortError::Other(_))));
    let branch = w.push_tag(
        "/r",
        "origin",
        "refs/heads/main",
        GitWriteApproval::granted(),
    );
    assert!(matches!(branch, Err(PortError::Other(_))));
    let url = w.push_tag(
        "/r",
        "https://example.invalid/r.git",
        "v1.0.0",
        GitWriteApproval::granted(),
    );
    assert!(matches!(url, Err(PortError::Other(_))));

    let ghost = w.push_tag("/r", "ghost", "v1.0.0", GitWriteApproval::granted());
    assert!(
        matches!(ghost, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );
    assert!(w.configured_remotes("/r").iter().all(|(n, _)| n != "ghost"));

    let missing = w.push_tag("/r", "origin", "v9.9.9", GitWriteApproval::granted());
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("not found"))
    );

    w.push_tag("/r", "  ", "v1.0.0", GitWriteApproval::granted())
        .expect("default origin");
    assert_eq!(
        w.last_tag_push("/r"),
        Some(("origin".to_string(), "v1.0.0".to_string()))
    );
    assert_eq!(w.remote_tags("/r", "origin"), vec!["v1.0.0".to_string()]);
    assert_eq!(w.push_count("/r"), 0);

    let exists = w.push_tag("/r", "origin", "v1.0.0", GitWriteApproval::granted());
    assert!(
        matches!(exists, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("already exists"))
    );

    w.push_tag("/r", "origin", "v1.1.0", GitWriteApproval::granted())
        .expect("annotated");
    assert_eq!(
        w.last_tag_push("/r"),
        Some(("origin".to_string(), "v1.1.0".to_string()))
    );
}

#[test]
fn gated_git_write_blocks_tag_push_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.push_tag("/any", "origin", "v1.0.0", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
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
fn gated_git_write_blocks_settings_even_when_approved() {
    let w = GatedGitWrite::new();
    let id = w.set_identity(
        "/any",
        "Ada",
        "ada@example.invalid",
        GitWriteApproval::granted(),
    );
    assert!(matches!(id, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let ig = w.set_ignore("/any", "target/\n", GitWriteApproval::granted());
    assert!(matches!(ig, Err(PortError::PermissionDenied(_))));
}

#[test]
fn gated_git_write_blocks_stash_even_when_approved() {
    let w = GatedGitWrite::new();
    let apply = w.stash_apply("/any", "stash@{0}", GitWriteApproval::granted());
    assert!(matches!(apply, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let pop = w.stash_pop("/any", "stash@{0}", GitWriteApproval::granted());
    assert!(matches!(pop, Err(PortError::PermissionDenied(_))));
    let drop = w.stash_drop("/any", "stash@{0}", GitWriteApproval::granted());
    assert!(matches!(drop, Err(PortError::PermissionDenied(_))));
    let push = w.stash_push("/any", "wip", GitWriteApproval::granted());
    assert!(matches!(push, Err(PortError::PermissionDenied(_))));
}

#[test]
fn gated_git_write_blocks_tag_even_when_approved() {
    let w = GatedGitWrite::new();
    let tag = w.create_tag("/any", "v1.0.0", "msg", GitWriteApproval::granted());
    assert!(matches!(tag, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let del = w.delete_tag("/any", "v1.0.0", GitWriteApproval::granted());
    assert!(matches!(del, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_create_branch_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.create_branch("/r", "feature/slot", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_branch_create("/r").is_none());
    assert!(w.created_branches("/r").is_empty());
    assert!(w.switched_branch("/r").is_none());

    w.create_branch("/r", "feature/slot", GitWriteApproval::granted())
        .expect("create");
    assert_eq!(w.last_branch_create("/r").as_deref(), Some("feature/slot"));
    assert_eq!(w.created_branches("/r"), vec!["feature/slot".to_string()]);
    assert!(
        w.switched_branch("/r").is_none(),
        "create must not switch HEAD"
    );

    let dup = w.create_branch("/r", "feature/slot", GitWriteApproval::granted());
    assert!(matches!(dup, Err(PortError::Git(ref m)) if m.contains("already exists")));
    assert_eq!(w.created_branches("/r"), vec!["feature/slot".to_string()]);

    let force = w.create_branch("/r", "-D", GitWriteApproval::granted());
    assert!(matches!(force, Err(PortError::Other(_))));
    let invalid = w.create_branch("/r", "bad..name", GitWriteApproval::granted());
    assert!(matches!(invalid, Err(PortError::Other(_))));
    assert_eq!(w.created_branches("/r"), vec!["feature/slot".to_string()]);
}

#[test]
fn gated_git_write_blocks_branch_create_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.create_branch("/any", "feature/slot", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_delete_branch_records_when_approved() {
    let w = FakeGitWrite::new();
    w.create_branch("/r", "feature/slot", GitWriteApproval::granted())
        .expect("seed");
    w.create_branch("/r", "unmerged", GitWriteApproval::granted())
        .expect("seed unmerged");
    w.mark_unmerged("/r", "unmerged");

    let denied = w.delete_branch("/r", "feature/slot", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_branch_delete("/r").is_none());
    assert_eq!(
        w.created_branches("/r"),
        vec!["feature/slot".to_string(), "unmerged".to_string()]
    );
    assert!(w.switched_branch("/r").is_none());

    let head = w.delete_branch("/r", "main", GitWriteApproval::granted());
    assert!(matches!(head, Err(PortError::Other(ref m)) if m.contains("HEAD")));
    let empty = w.delete_branch("/r", "  ", GitWriteApproval::granted());
    assert!(matches!(empty, Err(PortError::Other(_))));
    let force = w.delete_branch("/r", "-D", GitWriteApproval::granted());
    assert!(matches!(force, Err(PortError::Other(_))));
    let traversal = w.delete_branch("/r", "../evil", GitWriteApproval::granted());
    assert!(matches!(traversal, Err(PortError::Other(_))));
    let missing = w.delete_branch("/r", "ghost", GitWriteApproval::granted());
    assert!(matches!(missing, Err(PortError::Git(ref m)) if m.contains("not found")));
    let unmerged = w.delete_branch("/r", "unmerged", GitWriteApproval::granted());
    assert!(matches!(unmerged, Err(PortError::Git(ref m)) if m.contains("not fully merged")));
    assert_eq!(
        w.created_branches("/r"),
        vec!["feature/slot".to_string(), "unmerged".to_string()]
    );

    w.delete_branch("/r", "feature/slot", GitWriteApproval::granted())
        .expect("delete");
    assert_eq!(w.last_branch_delete("/r").as_deref(), Some("feature/slot"));
    assert_eq!(w.created_branches("/r"), vec!["unmerged".to_string()]);
    assert!(
        w.switched_branch("/r").is_none(),
        "delete must not switch HEAD"
    );

    w.switch_branch("/r", "unmerged", GitWriteApproval::granted())
        .expect("switch");
    let current = w.delete_branch("/r", "unmerged", GitWriteApproval::granted());
    assert!(matches!(current, Err(PortError::Other(ref m)) if m.contains("HEAD")));
    assert_eq!(w.created_branches("/r"), vec!["unmerged".to_string()]);
}

#[test]
fn gated_git_write_blocks_branch_delete_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.delete_branch("/any", "feature/slot", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_rename_branch_records_when_approved() {
    let w = FakeGitWrite::new();
    w.create_branch("/r", "feature/slot", GitWriteApproval::granted())
        .expect("seed");
    w.create_branch("/r", "taken", GitWriteApproval::granted())
        .expect("seed taken");
    w.mark_remote_only("/r", "origin/main");

    let denied = w.rename_branch(
        "/r",
        "feature/slot",
        "feature/renamed",
        GitWriteApproval::denied(),
    );
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_branch_rename("/r").is_none());
    assert_eq!(
        w.created_branches("/r"),
        vec!["feature/slot".to_string(), "taken".to_string()]
    );

    let empty_old = w.rename_branch("/r", "  ", "feature/renamed", GitWriteApproval::granted());
    assert!(matches!(empty_old, Err(PortError::Other(_))));
    let empty_new = w.rename_branch("/r", "feature/slot", "  ", GitWriteApproval::granted());
    assert!(matches!(empty_new, Err(PortError::Other(_))));
    let force = w.rename_branch("/r", "feature/slot", "-M", GitWriteApproval::granted());
    assert!(matches!(force, Err(PortError::Other(_))));
    let dash = w.rename_branch("/r", "-m", "feature/renamed", GitWriteApproval::granted());
    assert!(matches!(dash, Err(PortError::Other(_))));
    let traversal = w.rename_branch("/r", "../evil", "ok", GitWriteApproval::granted());
    assert!(matches!(traversal, Err(PortError::Other(_))));
    let git_trick = w.rename_branch("/r", "feature/slot", ".git", GitWriteApproval::granted());
    assert!(matches!(git_trick, Err(PortError::Other(_))));
    let git_seg = w.rename_branch(
        "/r",
        "feature/slot",
        "foo/.git/bar",
        GitWriteApproval::granted(),
    );
    assert!(matches!(git_seg, Err(PortError::Other(_))));
    let taken = w.rename_branch("/r", "feature/slot", "taken", GitWriteApproval::granted());
    assert!(
        matches!(taken, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("already exists"))
    );
    let missing = w.rename_branch(
        "/r",
        "ghost",
        "feature/renamed",
        GitWriteApproval::granted(),
    );
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("not found"))
    );
    let remote_only = w.rename_branch(
        "/r",
        "origin/main",
        "feature/from-remote",
        GitWriteApproval::granted(),
    );
    assert!(matches!(
        remote_only,
        Err(PortError::Other(ref m) | PortError::Git(ref m))
            if m.to_ascii_lowercase().contains("remote")
    ));
    assert!(w.last_branch_rename("/r").is_none());
    assert_eq!(
        w.created_branches("/r"),
        vec!["feature/slot".to_string(), "taken".to_string()]
    );

    w.rename_branch(
        "/r",
        "feature/slot",
        "feature/renamed",
        GitWriteApproval::granted(),
    )
    .expect("rename");
    assert_eq!(
        w.last_branch_rename("/r"),
        Some(("feature/slot".into(), "feature/renamed".into()))
    );
    assert_eq!(
        w.created_branches("/r"),
        vec!["feature/renamed".to_string(), "taken".to_string()]
    );
    assert!(
        w.switched_branch("/r").is_none(),
        "rename of a non-current branch must not switch HEAD"
    );
}

#[test]
fn gated_git_write_blocks_branch_rename_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.rename_branch(
        "/any",
        "feature/slot",
        "feature/renamed",
        GitWriteApproval::granted(),
    );
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_add_and_remove_remote_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.add_remote(
        "/r",
        "upstream",
        "https://example.invalid/r.git",
        GitWriteApproval::denied(),
    );
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_remote_add("/r").is_none());
    assert!(w.configured_remotes("/r").is_empty());
    assert_eq!(w.push_count("/r"), 0);

    w.add_remote(
        "/r",
        "upstream",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .expect("add");
    assert_eq!(
        w.last_remote_add("/r"),
        Some((
            "upstream".to_string(),
            "https://example.invalid/r.git".to_string()
        ))
    );
    assert_eq!(
        w.configured_remotes("/r"),
        vec![(
            "upstream".to_string(),
            "https://example.invalid/r.git".to_string()
        )]
    );
    assert_eq!(w.push_count("/r"), 0);

    let dup = w.add_remote(
        "/r",
        "upstream",
        "https://example.invalid/other.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(dup, Err(PortError::Git(ref m)) if m.contains("already exists")));
    assert_eq!(
        w.configured_remotes("/r"),
        vec![(
            "upstream".to_string(),
            "https://example.invalid/r.git".to_string()
        )]
    );

    let force = w.add_remote(
        "/r",
        "-f",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(force, Err(PortError::Other(_))));
    let flag_url = w.add_remote("/r", "mirror", "-u", GitWriteApproval::granted());
    assert!(matches!(flag_url, Err(PortError::Other(_))));
    assert_eq!(w.configured_remotes("/r").len(), 1);

    let denied_rm = w.remove_remote("/r", "upstream", GitWriteApproval::denied());
    assert!(matches!(denied_rm, Err(PortError::PermissionDenied(_))));
    assert!(w.last_remote_remove("/r").is_none());
    assert_eq!(w.configured_remotes("/r").len(), 1);

    let missing = w.remove_remote("/r", "ghost", GitWriteApproval::granted());
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );
    assert!(w.last_remote_remove("/r").is_none());

    w.remove_remote("/r", "upstream", GitWriteApproval::granted())
        .expect("remove");
    assert_eq!(w.last_remote_remove("/r").as_deref(), Some("upstream"));
    assert!(w.configured_remotes("/r").is_empty());
    assert_eq!(w.push_count("/r"), 0);
}

#[test]
fn gated_git_write_blocks_remote_even_when_approved() {
    let w = GatedGitWrite::new();
    let add = w.add_remote(
        "/any",
        "upstream",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(add, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let rm = w.remove_remote("/any", "origin", GitWriteApproval::granted());
    assert!(matches!(rm, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_set_remote_url_records_when_approved() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/old.git",
        GitWriteApproval::granted(),
    )
    .expect("seed remote");

    let denied = w.set_remote_url(
        "/r",
        "origin",
        "https://example.invalid/new.git",
        GitWriteApproval::denied(),
    );
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_remote_set_url("/r").is_none());
    assert_eq!(
        w.configured_remotes("/r"),
        vec![(
            "origin".to_string(),
            "https://example.invalid/old.git".to_string()
        )]
    );
    assert_eq!(w.push_count("/r"), 0);

    let empty = w.set_remote_url(
        "/r",
        "  ",
        "https://example.invalid/new.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(empty, Err(PortError::Other(_))));
    let empty_url = w.set_remote_url("/r", "origin", "  ", GitWriteApproval::granted());
    assert!(matches!(empty_url, Err(PortError::Other(_))));

    let missing = w.set_remote_url(
        "/r",
        "ghost",
        "https://example.invalid/new.git",
        GitWriteApproval::granted(),
    );
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );

    let flag = w.set_remote_url(
        "/r",
        "-f",
        "https://example.invalid/new.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(flag, Err(PortError::Other(_))));
    let mirror = w.set_remote_url(
        "/r",
        "--mirror",
        "https://example.invalid/new.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(mirror, Err(PortError::Other(_))));
    let flag_url = w.set_remote_url("/r", "origin", "-u", GitWriteApproval::granted());
    assert!(matches!(flag_url, Err(PortError::Other(_))));
    let meta = w.set_remote_url(
        "/r",
        "origin",
        "https://example.invalid/r.git;echo",
        GitWriteApproval::granted(),
    );
    assert!(matches!(meta, Err(PortError::Other(_))));
    assert_eq!(
        w.configured_remotes("/r")[0].1,
        "https://example.invalid/old.git"
    );

    w.set_remote_url(
        "/r",
        "origin",
        "https://example.invalid/new.git",
        GitWriteApproval::granted(),
    )
    .expect("set-url");
    assert_eq!(
        w.last_remote_set_url("/r"),
        Some((
            "origin".to_string(),
            "https://example.invalid/new.git".to_string()
        ))
    );
    assert_eq!(
        w.configured_remotes("/r"),
        vec![(
            "origin".to_string(),
            "https://example.invalid/new.git".to_string()
        )]
    );
    assert_eq!(w.push_count("/r"), 0);
}

#[test]
fn fake_git_write_fetch_updates_remote_tracking_without_moving_head() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .expect("seed remote");
    let head_before = w.local_head("/r");

    let denied = w.fetch("/r", "origin", None, GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_fetch("/r").is_none());
    assert!(w.remote_tracking_refs("/r").is_empty());
    assert_eq!(w.local_head("/r"), head_before);
    assert!(w.switched_branch("/r").is_none());

    let missing = w.fetch("/r", "ghost", None, GitWriteApproval::granted());
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );
    assert_eq!(w.configured_remotes("/r").len(), 1);

    let force = w.fetch(
        "/r",
        "origin",
        Some("+refs/heads/main:refs/remotes/origin/main"),
        GitWriteApproval::granted(),
    );
    assert!(matches!(force, Err(PortError::Other(_))));
    assert!(w.last_fetch("/r").is_none());

    w.fetch("/r", "origin", Some("--prune"), GitWriteApproval::granted())
        .expect_err("ordinary fetch must reject --prune refspec");
    w.fetch("/r", "--prune", None, GitWriteApproval::granted())
        .expect_err("ordinary fetch must reject --prune remote");
    w.fetch("/r", "origin", None, GitWriteApproval::granted())
        .expect("fetch");
    assert_eq!(w.last_fetch("/r"), Some(("origin".to_string(), None)));
    let refs = w.remote_tracking_refs("/r");
    assert_eq!(refs.len(), 1);
    assert_eq!(refs[0].0, "refs/remotes/origin/main");
    assert_eq!(w.local_head("/r"), head_before);
    assert!(w.switched_branch("/r").is_none());
    assert_eq!(w.push_count("/r"), 0);
}

#[test]
fn fake_git_write_fetch_prune_deletes_stale_remote_tracking_without_moving_head() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .expect("seed remote");
    w.create_branch("/r", "keep-local", GitWriteApproval::granted())
        .expect("seed local branch");
    w.seed_remote_tracking("/r", "refs/remotes/origin/main", "aaa");
    w.seed_remote_tracking("/r", "refs/remotes/origin/stale", "bbb");
    w.mark_stale_remote_tracking("/r", "refs/remotes/origin/stale");
    let head_before = w.local_head("/r");
    let branches_before = w.created_branches("/r");

    w.fetch_prune("/r", "origin", GitWriteApproval::denied())
        .expect_err("denied fetch-prune must not mutate");
    assert!(w.last_fetch_prune("/r").is_none());
    assert!(w
        .remote_tracking_refs("/r")
        .iter()
        .any(|(r, _)| r == "refs/remotes/origin/stale"));
    assert_eq!(w.local_head("/r"), head_before);

    w.fetch_prune("/r", "--force", GitWriteApproval::granted())
        .expect_err("force flag remote is out of scope");
    w.fetch_prune(
        "/r",
        "+refs/heads/main:refs/remotes/origin/main",
        GitWriteApproval::granted(),
    )
    .expect_err("force refspec remote is out of scope");
    w.fetch_prune("/r", "--prune-tags", GitWriteApproval::granted())
        .expect_err("prune-tags is out of scope");
    w.fetch_prune("/r", "--update-head-ok", GitWriteApproval::granted())
        .expect_err("update-head-ok is out of scope");
    w.fetch_prune("/r", "--mirror", GitWriteApproval::granted())
        .expect_err("mirror is out of scope");
    w.fetch_prune("/r", "--push", GitWriteApproval::granted())
        .expect_err("push is out of scope");
    assert!(w.last_fetch_prune("/r").is_none());

    let missing = w.fetch_prune("/r", "ghost", GitWriteApproval::granted());
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );

    w.fetch_prune("/r", "origin", GitWriteApproval::granted())
        .expect("fetch-prune");
    assert_eq!(w.last_fetch_prune("/r"), Some("origin".to_string()));
    let refs = w.remote_tracking_refs("/r");
    assert!(refs.iter().any(|(r, _)| r == "refs/remotes/origin/main"));
    assert!(!refs.iter().any(|(r, _)| r == "refs/remotes/origin/stale"));
    assert_eq!(w.local_head("/r"), head_before);
    assert_eq!(w.created_branches("/r"), branches_before);
    assert!(w.switched_branch("/r").is_none());
    assert_eq!(w.push_count("/r"), 0);
    assert!(w.last_fetch("/r").is_none());
}

#[test]
fn gated_git_write_blocks_fetch_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.fetch("/any", "origin", None, GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let prune = w.fetch_prune("/any", "origin", GitWriteApproval::granted());
    assert!(matches!(prune, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let pull = w.pull_ff_only("/any", "origin", None, GitWriteApproval::granted());
    assert!(matches!(pull, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_pull_ff_only_denied_diverged_dirty_and_ff_success() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .unwrap();
    w.fetch("/r", "origin", None, GitWriteApproval::granted())
        .expect("seed tracking");
    let head_before = w.local_head("/r");

    w.pull_ff_only("/r", "origin", None, GitWriteApproval::denied())
        .expect_err("denied pull");
    assert!(w.last_pull_ff_only("/r").is_none());
    assert_eq!(w.local_head("/r"), head_before);

    w.pull_ff_only("/r", "--rebase", None, GitWriteApproval::granted())
        .expect_err("rebase remote");
    w.pull_ff_only("/r", "origin", Some("--no-ff"), GitWriteApproval::granted())
        .expect_err("noff branch");
    assert!(w.last_pull_ff_only("/r").is_none());

    w.mark_pull_local_ahead("/r");
    let diverged = w
        .pull_ff_only("/r", "origin", None, GitWriteApproval::granted())
        .expect_err("diverged");
    assert!(matches!(diverged, PortError::Git(_)));
    assert!(w.last_pull_ff_only("/r").is_none());
    assert_eq!(w.local_head("/r"), head_before);

    let w2 = FakeGitWrite::new();
    w2.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .unwrap();
    w2.fetch("/r", "origin", None, GitWriteApproval::granted())
        .expect("seed");
    w2.mark_pull_dirty_overwrite("/r");
    let dirty = w2
        .pull_ff_only("/r", "origin", None, GitWriteApproval::granted())
        .expect_err("dirty");
    assert!(matches!(dirty, PortError::Git(_)));

    let w3 = FakeGitWrite::new();
    w3.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .unwrap();
    w3.fetch("/r", "origin", None, GitWriteApproval::granted())
        .expect("seed");
    let before = w3.local_head("/r");
    w3.pull_ff_only("/r", "origin", None, GitWriteApproval::granted())
        .expect("ff pull");
    assert_eq!(
        w3.last_pull_ff_only("/r"),
        Some(("origin".to_string(), None))
    );
    assert_ne!(w3.local_head("/r"), before);
}

#[test]
fn gated_git_write_blocks_remote_set_url_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.set_remote_url(
        "/any",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_remote_rename_records_when_approved() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .expect("seed remote");

    let denied = w.rename_remote("/r", "origin", "upstream", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_remote_rename("/r").is_none());

    let empty = w.rename_remote("/r", "  ", "upstream", GitWriteApproval::granted());
    assert!(matches!(empty, Err(PortError::Other(_))));

    let same = w.rename_remote("/r", "origin", "origin", GitWriteApproval::granted());
    assert!(matches!(same, Err(PortError::Other(_))));

    let missing = w.rename_remote("/r", "ghost", "upstream", GitWriteApproval::granted());
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );

    let flag = w.rename_remote("/r", "-f", "upstream", GitWriteApproval::granted());
    assert!(matches!(flag, Err(PortError::Other(_))));
    let url_name = w.rename_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    );
    assert!(matches!(url_name, Err(PortError::Other(_))));

    w.rename_remote("/r", "origin", "upstream", GitWriteApproval::granted())
        .expect("rename");
    assert_eq!(
        w.last_remote_rename("/r"),
        Some(("origin".to_string(), "upstream".to_string()))
    );
    assert_eq!(
        w.configured_remotes("/r"),
        vec![(
            "upstream".to_string(),
            "https://example.invalid/r.git".to_string()
        )]
    );
    assert_eq!(w.push_count("/r"), 0);
}

#[test]
fn gated_git_write_blocks_remote_rename_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.rename_remote("/any", "origin", "upstream", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_set_upstream_records_when_approved() {
    let w = FakeGitWrite::new();
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

    let denied = w.set_upstream("/r", "origin", "main", "main", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_set_upstream("/r").is_none());
    assert!(w.upstream_of("/r", "main").is_none());

    let empty_remote = w.set_upstream("/r", "  ", "main", "main", GitWriteApproval::granted());
    assert!(matches!(empty_remote, Err(PortError::Other(_))));

    let flag = w.set_upstream("/r", "-f", "main", "main", GitWriteApproval::granted());
    assert!(matches!(flag, Err(PortError::Other(_))));
    let unset = w.set_upstream(
        "/r",
        "origin",
        "--unset-upstream",
        "main",
        GitWriteApproval::granted(),
    );
    assert!(matches!(unset, Err(PortError::Other(_))));

    let ghost = w.set_upstream("/r", "ghost", "main", "main", GitWriteApproval::granted());
    assert!(
        matches!(ghost, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no such remote"))
    );
    assert!(w.configured_remotes("/r").iter().all(|(n, _)| n != "ghost"));

    let missing_ref = w.set_upstream("/r", "origin", "nope", "main", GitWriteApproval::granted());
    assert!(
        matches!(missing_ref, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("not found"))
    );
    assert!(w
        .remote_tracking_refs("/r")
        .iter()
        .all(|(n, _)| n != "refs/remotes/origin/nope"));

    let missing_local =
        w.set_upstream("/r", "origin", "main", "topic", GitWriteApproval::granted());
    assert!(
        matches!(missing_local, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("not found"))
    );
    assert!(!w.created_branches("/r").iter().any(|b| b == "topic"));

    w.set_upstream("/r", "origin", "main", "", GitWriteApproval::granted())
        .expect("empty local uses current");
    assert_eq!(
        w.last_set_upstream("/r"),
        Some(("main".into(), "origin".into(), "main".into()))
    );
    assert_eq!(
        w.upstream_of("/r", "main"),
        Some(("origin".into(), "main".into()))
    );
    assert_eq!(w.push_count("/r"), 0);
}

#[test]
fn gated_git_write_blocks_set_upstream_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.set_upstream(
        "/any",
        "origin",
        "main",
        "main",
        GitWriteApproval::granted(),
    );
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_unset_upstream_records_when_approved() {
    let w = FakeGitWrite::new();
    w.add_remote(
        "/r",
        "origin",
        "https://example.invalid/r.git",
        GitWriteApproval::granted(),
    )
    .expect("seed remote");
    w.create_branch("/r", "main", GitWriteApproval::granted())
        .expect("seed local");
    w.create_branch("/r", "topic", GitWriteApproval::granted())
        .expect("seed topic");
    w.set_current_branch("/r", "main");
    w.seed_remote_tracking("/r", "refs/remotes/origin/main", "oid-main");
    w.set_upstream("/r", "origin", "main", "main", GitWriteApproval::granted())
        .expect("seed upstream");
    w.set_upstream("/r", "origin", "main", "topic", GitWriteApproval::granted())
        .expect("seed topic upstream");

    let denied = w.unset_upstream("/r", "main", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_unset_upstream("/r").is_none());
    assert_eq!(
        w.upstream_of("/r", "main"),
        Some(("origin".into(), "main".into()))
    );

    let flag = w.unset_upstream("/r", "-u", GitWriteApproval::granted());
    assert!(matches!(flag, Err(PortError::Other(_))));
    let set_to = w.unset_upstream("/r", "--set-upstream-to", GitWriteApproval::granted());
    assert!(matches!(set_to, Err(PortError::Other(_))));
    let force = w.unset_upstream("/r", "--force", GitWriteApproval::granted());
    assert!(matches!(force, Err(PortError::Other(_))));

    let missing = w.unset_upstream("/r", "ghost", GitWriteApproval::granted());
    assert!(
        matches!(missing, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("not found"))
    );
    assert!(!w.created_branches("/r").iter().any(|b| b == "ghost"));
    assert!(w.last_unset_upstream("/r").is_none());

    w.create_branch("/r", "lonely", GitWriteApproval::granted())
        .expect("seed lonely");
    let none = w.unset_upstream("/r", "lonely", GitWriteApproval::granted());
    assert!(
        matches!(none, Err(PortError::Git(ref m)) if m.to_ascii_lowercase().contains("no upstream"))
    );
    assert!(w.last_unset_upstream("/r").is_none());

    w.unset_upstream("/r", "", GitWriteApproval::granted())
        .expect("empty local uses current");
    assert_eq!(w.last_unset_upstream("/r"), Some("main".into()));
    assert!(w.upstream_of("/r", "main").is_none());
    assert_eq!(
        w.upstream_of("/r", "topic"),
        Some(("origin".into(), "main".into()))
    );
    assert_eq!(w.push_count("/r"), 0);

    w.unset_upstream("/r", "topic", GitWriteApproval::granted())
        .expect("explicit local");
    assert_eq!(w.last_unset_upstream("/r"), Some("topic".into()));
    assert!(w.upstream_of("/r", "topic").is_none());
}

#[test]
fn gated_git_write_blocks_unset_upstream_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.unset_upstream("/any", "main", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_stage_all_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.stage_all("/r", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stage_all("/r").is_none());

    w.stage_all("/r", GitWriteApproval::granted())
        .expect("clean tree is success no-op");
    assert_eq!(w.last_stage_all("/r"), Some(true));
    assert_eq!(w.local_commit_count("/r"), 0);
    assert_eq!(w.push_count("/r"), 0);

    w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
    let conflict = w.stage_all("/r", GitWriteApproval::granted());
    assert!(matches!(conflict, Err(PortError::Git(ref m)) if m.contains("OPERATION_IN_PROGRESS")));
}

#[test]
fn gated_git_write_blocks_stage_all_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.stage_all("/any", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_unstage_all_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.unstage_all("/r", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_unstage_all("/r").is_none());

    w.unstage_all("/r", GitWriteApproval::granted())
        .expect("clean index is success no-op");
    assert_eq!(w.last_unstage_all("/r"), Some(true));
    assert_eq!(w.local_commit_count("/r"), 0);
    assert_eq!(w.push_count("/r"), 0);

    w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
    let conflict = w.unstage_all("/r", GitWriteApproval::granted());
    assert!(matches!(conflict, Err(PortError::Git(ref m)) if m.contains("OPERATION_IN_PROGRESS")));
    assert_eq!(w.remaining_conflict_files("/r").len(), 1);
}

#[test]
fn gated_git_write_blocks_unstage_all_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.unstage_all("/any", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_stage_file_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.stage_file("/r", "a.txt", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stage_file("/r").is_none());

    w.stage_file("/r", "a.txt", GitWriteApproval::granted())
        .expect("already-staged path is success no-op");
    assert_eq!(w.last_stage_file("/r").as_deref(), Some("a.txt"));
    assert_eq!(w.local_commit_count("/r"), 0);
    assert_eq!(w.push_count("/r"), 0);

    for path in ["", "-", "-A", "../secret", "a/../b", "."] {
        let err = w.stage_file("/r", path, GitWriteApproval::granted());
        assert!(err.is_err(), "{path}");
        assert_eq!(w.last_stage_file("/r").as_deref(), Some("a.txt"));
    }

    w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
    let conflict = w.stage_file("/r", "src/a.rs", GitWriteApproval::granted());
    assert!(matches!(conflict, Err(PortError::Git(ref m)) if m.contains("OPERATION_IN_PROGRESS")));
    assert_eq!(w.last_stage_file("/r").as_deref(), Some("a.txt"));
}

#[test]
fn gated_git_write_blocks_stage_file_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.stage_file("/any", "a.txt", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_unstage_file_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.unstage_file("/r", "a.txt", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_unstage_file("/r").is_none());

    w.unstage_file("/r", "a.txt", GitWriteApproval::granted())
        .expect("already-unstaged path is success no-op");
    assert_eq!(w.last_unstage_file("/r").as_deref(), Some("a.txt"));
    assert_eq!(w.local_commit_count("/r"), 0);
    assert_eq!(w.push_count("/r"), 0);

    for path in ["", "-", "-A", "../secret", "a/../b", "."] {
        let err = w.unstage_file("/r", path, GitWriteApproval::granted());
        assert!(err.is_err(), "{path}");
        assert_eq!(w.last_unstage_file("/r").as_deref(), Some("a.txt"));
    }

    w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
    let conflict = w.unstage_file("/r", "src/a.rs", GitWriteApproval::granted());
    assert!(matches!(conflict, Err(PortError::Git(ref m)) if m.contains("OPERATION_IN_PROGRESS")));
    assert_eq!(w.last_unstage_file("/r").as_deref(), Some("a.txt"));
}

#[test]
fn gated_git_write_blocks_unstage_file_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.unstage_file("/any", "a.txt", GitWriteApproval::granted());
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

const TEXT_HUNK: &str =
    "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1 +1 @@\n-old\n+new\n";

#[test]
fn fake_git_write_stage_hunk_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.stage_hunk("/r", "a.txt", TEXT_HUNK, "abc", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_stage_hunk("/r").is_none());

    w.stage_hunk("/r", "a.txt", TEXT_HUNK, "abc", GitWriteApproval::granted())
        .expect("approved stage-hunk records");
    let recorded = w.last_stage_hunk("/r").expect("recorded");
    assert_eq!(recorded.0, "a.txt");
    assert_eq!(recorded.2, "abc");
    assert_eq!(w.local_commit_count("/r"), 0);
    assert_eq!(w.push_count("/r"), 0);

    w.stage_hunk("/r", "a.txt", TEXT_HUNK, "abc", GitWriteApproval::granted())
        .expect("already-applied matching hunk is success no-op");
    assert_eq!(w.local_commit_count("/r"), 0);

    for path in ["", "-", "-A", "../secret", "a/../b", "."] {
        let err = w.stage_hunk("/r", path, TEXT_HUNK, "abc", GitWriteApproval::granted());
        assert!(err.is_err(), "{path}");
        assert_eq!(
            w.last_stage_hunk("/r").as_ref().map(|t| t.0.as_str()),
            Some("a.txt")
        );
    }

    let empty_patch = w.stage_hunk("/r", "a.txt", "", "abc", GitWriteApproval::granted());
    assert!(empty_patch.is_err());
    let binary = w.stage_hunk(
        "/r",
        "a.txt",
        "GIT binary patch\nliteral 1\n",
        "abc",
        GitWriteApproval::granted(),
    );
    assert!(binary.is_err(), "binary must refuse");
    let rename = w.stage_hunk(
        "/r",
        "a.txt",
        "diff --git a/a.txt b/b.txt\nrename from a.txt\nrename to b.txt\n@@ -1 +1 @@\n-old\n+new\n",
        "abc",
        GitWriteApproval::granted(),
    );
    assert!(rename.is_err(), "rename must refuse");
    let truncated = w.stage_hunk(
        "/r",
        "a.txt",
        "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -1,3 +1,3 @@\n-old\n",
        "abc",
        GitWriteApproval::granted(),
    );
    assert!(truncated.is_err(), "truncated hunk must refuse");
    let empty_hash = w.stage_hunk("/r", "a.txt", TEXT_HUNK, "", GitWriteApproval::granted());
    assert!(empty_hash.is_err());
    assert_eq!(
        w.last_stage_hunk("/r").as_ref().map(|t| t.0.as_str()),
        Some("a.txt")
    );

    w.set_conflict_in_progress("/r", "Merge", &["src/a.rs"]);
    let conflict = w.stage_hunk(
        "/r",
        "src/a.rs",
        TEXT_HUNK,
        "abc",
        GitWriteApproval::granted(),
    );
    assert!(matches!(conflict, Err(PortError::Git(ref m)) if m.contains("OPERATION_IN_PROGRESS")));
    assert_eq!(
        w.last_stage_hunk("/r").as_ref().map(|t| t.0.as_str()),
        Some("a.txt")
    );
}

#[test]
fn gated_git_write_blocks_stage_hunk_even_when_approved() {
    let w = GatedGitWrite::new();
    let err = w.stage_hunk(
        "/any",
        "a.txt",
        TEXT_HUNK,
        "abc",
        GitWriteApproval::granted(),
    );
    assert!(matches!(err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
}

#[test]
fn fake_git_write_conflict_save_continue_abort_records_when_approved() {
    let w = FakeGitWrite::new();
    let denied = w.conflict_save("/r", "src/a.rs", GitWriteApproval::denied());
    assert!(matches!(denied, Err(PortError::PermissionDenied(_))));
    assert!(w.last_conflict_save("/r").is_none());

    let missing = w.conflict_save("/r", "src/a.rs", GitWriteApproval::granted());
    assert!(matches!(missing, Err(PortError::Git(ref m)) if m.contains("no in-progress")));
    assert!(w.last_conflict_save("/r").is_none());

    w.set_conflict_in_progress("/r", "Merge", &["src/a.rs", "src/b.rs"]);
    w.set_conflict_file_text(
        "/r",
        "src/a.rs",
        "<<<<<<< ours\nx\n=======\ny\n>>>>>>> theirs\n",
    );
    let markers = w.conflict_save("/r", "src/a.rs", GitWriteApproval::granted());
    assert!(matches!(markers, Err(PortError::Git(ref m)) if m.contains("markers")));
    assert!(w.last_conflict_save("/r").is_none());
    assert_eq!(w.remaining_conflict_files("/r").len(), 2);

    let widen = w.conflict_save("/r", ".", GitWriteApproval::granted());
    assert!(matches!(widen, Err(PortError::Other(_))));
    let all = w.conflict_save("/r", "-A", GitWriteApproval::granted());
    assert!(matches!(all, Err(PortError::Other(_))));

    w.set_conflict_file_text("/r", "src/a.rs", "resolved a\n");
    w.conflict_save("/r", "src/a.rs", GitWriteApproval::granted())
        .expect("save a");
    assert_eq!(w.last_conflict_save("/r").as_deref(), Some("src/a.rs"));
    assert_eq!(
        w.remaining_conflict_files("/r"),
        vec!["src/b.rs".to_string()]
    );

    let early = w.conflict_continue("/r", GitWriteApproval::granted());
    assert!(matches!(early, Err(PortError::Git(ref m)) if m.contains("unmerged")));
    assert!(w.last_conflict_continue("/r").is_none());
    assert_eq!(w.conflict_kind("/r").as_deref(), Some("Merge"));

    w.set_conflict_file_text("/r", "src/b.rs", "resolved b\n");
    w.conflict_save("/r", "src/b.rs", GitWriteApproval::granted())
        .expect("save b");
    w.conflict_continue("/r", GitWriteApproval::granted())
        .expect("continue");
    assert_eq!(w.last_conflict_continue("/r").as_deref(), Some("Merge"));
    assert!(w.conflict_kind("/r").is_none());

    let no_state = w.conflict_abort("/r", GitWriteApproval::granted());
    assert!(matches!(no_state, Err(PortError::Git(ref m)) if m.contains("no in-progress")));

    w.set_conflict_in_progress("/r", "Rebase", &["src/c.rs"]);
    let denied_abort = w.conflict_abort("/r", GitWriteApproval::denied());
    assert!(matches!(denied_abort, Err(PortError::PermissionDenied(_))));
    assert!(w.last_conflict_abort("/r").is_none());
    w.conflict_abort("/r", GitWriteApproval::granted())
        .expect("abort");
    assert_eq!(w.last_conflict_abort("/r").as_deref(), Some("Rebase"));
    assert!(w.conflict_kind("/r").is_none());

    let skip_missing = w.conflict_skip("/r", GitWriteApproval::granted());
    assert!(matches!(
        skip_missing,
        Err(PortError::Git(ref m)) if m.contains("no in-progress")
    ));
    w.set_conflict_in_progress("/r", "Merge", &["src/m.rs"]);
    let skip_merge = w.conflict_skip("/r", GitWriteApproval::granted());
    assert!(matches!(
        skip_merge,
        Err(PortError::Git(ref m)) if m.contains("cannot be skipped")
    ));
    assert_eq!(w.conflict_kind("/r").as_deref(), Some("Merge"));
    assert!(w.last_conflict_skip("/r").is_none());
    w.conflict_abort("/r", GitWriteApproval::granted())
        .expect("abort merge after refused skip");
    assert_eq!(w.last_conflict_abort("/r").as_deref(), Some("Merge"));

    w.set_conflict_in_progress("/r", "Rebase", &["src/skip.rs"]);
    let denied_skip = w.conflict_skip("/r", GitWriteApproval::denied());
    assert!(matches!(denied_skip, Err(PortError::PermissionDenied(_))));
    assert!(w.last_conflict_skip("/r").is_none());
    assert_eq!(w.conflict_kind("/r").as_deref(), Some("Rebase"));
    w.conflict_skip("/r", GitWriteApproval::granted())
        .expect("skip rebase");
    assert_eq!(w.last_conflict_skip("/r").as_deref(), Some("Rebase"));
    assert!(w.conflict_kind("/r").is_none());
}

#[test]
fn gated_git_write_blocks_conflict_even_when_approved() {
    let w = GatedGitWrite::new();
    let save = w.conflict_save("/any", "src/a.rs", GitWriteApproval::granted());
    assert!(matches!(save, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let cont = w.conflict_continue("/any", GitWriteApproval::granted());
    assert!(matches!(cont, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let abort = w.conflict_abort("/any", GitWriteApproval::granted());
    assert!(matches!(abort, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let skip = w.conflict_skip("/any", GitWriteApproval::granted());
    assert!(matches!(skip, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
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
    assert_eq!(
        host.git.status("/r").unwrap().branch.as_deref(),
        Some("dev")
    );
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
