//! PD-GIT-02 TDD — approval gate, push-fail preserves state, credential redaction.
//!
//! Temp dirs only for StdGitWrite; never touches user repos.

use sgenaxis_ports::{GitWriteApproval, GitWritePort, PortError};

use crate::fake::FakeGitWrite;
use crate::git_write::{
    redact_credentials, GatedGitWrite, GIT_WRITE_GATED_MSG, GIT_WRITE_NOT_APPROVED_MSG,
};

#[cfg(feature = "std-adapters")]
use crate::StdGitWrite;

#[test]
fn redact_credentials_strips_url_userinfo_and_tokens() {
    let raw =
        "fatal: Authentication failed for 'https://alice:s3cretTOKEN@github.com/org/repo.git'\n\
               Authorization: Bearer leaky-jwt-value\n\
               password=hunter2 token=abc123";
    let clean = redact_credentials(raw);
    assert!(
        !clean.contains("s3cretTOKEN"),
        "password must not leak: {clean}"
    );
    assert!(
        !clean.contains("leaky-jwt-value"),
        "bearer must not leak: {clean}"
    );
    assert!(
        !clean.contains("hunter2"),
        "password= must not leak: {clean}"
    );
    assert!(!clean.contains("abc123"), "token= must not leak: {clean}");
    assert!(
        clean.contains("***") || clean.contains("[REDACTED]"),
        "expected redaction markers: {clean}"
    );
}

#[test]
fn gated_git_write_blocks_even_when_approved() {
    let w = GatedGitWrite::new();
    let c = w.commit("/any", "msg", GitWriteApproval::granted());
    assert!(matches!(c, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));
    let p = w.push("/any", "origin", Some("main"), GitWriteApproval::granted());
    assert!(matches!(p, Err(PortError::PermissionDenied(_))));
}

#[test]
fn fake_write_denies_without_approval() {
    let w = FakeGitWrite::new();
    let err = w
        .commit("/r", "x", GitWriteApproval::denied())
        .expect_err("must deny");
    assert!(matches!(err, PortError::PermissionDenied(ref m) if m == GIT_WRITE_NOT_APPROVED_MSG));
    assert!(w.local_commit_count("/r") == 0);
    let err = w
        .push("/r", "origin", None, GitWriteApproval::denied())
        .expect_err("must deny");
    assert!(matches!(err, PortError::PermissionDenied(_)));
}

#[test]
fn fake_write_commit_when_approved() {
    let w = FakeGitWrite::new();
    w.commit("/r", "feat: one", GitWriteApproval::granted())
        .expect("approved commit");
    assert_eq!(w.local_commit_count("/r"), 1);
    assert_eq!(w.last_commit_message("/r").as_deref(), Some("feat: one"));
}

#[test]
fn fake_push_failure_preserves_local_commits_and_redacts() {
    let w = FakeGitWrite::new();
    w.commit("/r", "local keep", GitWriteApproval::granted())
        .unwrap();
    assert_eq!(w.local_commit_count("/r"), 1);

    w.fail_next_push(
        "/r",
        "remote rejected: https://ci:p@ssw0rd@example.com/r.git Authentication failed",
    );
    let err = w
        .push("/r", "origin", None, GitWriteApproval::granted())
        .expect_err("injected push fail");

    // Failure preserves local state (INV: 遠端寫入失敗保留本機 commit).
    assert_eq!(w.local_commit_count("/r"), 1);
    assert_eq!(w.last_commit_message("/r").as_deref(), Some("local keep"));

    let rendered = err.to_string();
    assert!(
        !rendered.contains("p@ssw0rd"),
        "credential leaked in error: {rendered}"
    );
    assert!(
        matches!(err, PortError::Git(_)),
        "push failures surface as Git errors"
    );
}

#[test]
fn fake_approved_push_clears_fail_flag() {
    let w = FakeGitWrite::new();
    w.commit("/r", "ok", GitWriteApproval::granted()).unwrap();
    w.push(
        "/r",
        "origin",
        Some("HEAD:main"),
        GitWriteApproval::granted(),
    )
    .expect("push ok");
    assert_eq!(w.push_count("/r"), 1);
}

#[cfg(feature = "std-adapters")]
mod std_write_temp {
    use super::*;
    use std::fs;
    use std::path::{Path, PathBuf};
    use std::process::Command;
    use std::sync::atomic::{AtomicU64, Ordering};
    use std::time::{SystemTime, UNIX_EPOCH};

    static SEQ: AtomicU64 = AtomicU64::new(0);

    fn unique_temp(label: &str) -> PathBuf {
        let nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos())
            .unwrap_or(0);
        let n = SEQ.fetch_add(1, Ordering::Relaxed);
        std::env::temp_dir().join(format!("sgenaxis-pd-git-02-{label}-{nanos}-{n}"))
    }

    fn git(cwd: &Path, args: &[&str]) {
        let out = Command::new("git")
            .args(args)
            .current_dir(cwd)
            .output()
            .expect("spawn git");
        assert!(
            out.status.success(),
            "git {:?} failed: {}",
            args,
            String::from_utf8_lossy(&out.stderr)
        );
    }

    fn init_identity(repo: &Path) {
        git(repo, &["config", "user.email", "pd-git-02@test.local"]);
        git(repo, &["config", "user.name", "PD-GIT-02 Test"]);
        // Avoid signing / hooks in temp fixtures.
        git(repo, &["config", "commit.gpgsign", "false"]);
        // Windows Git defaults to autocrlf=true; stash apply/pop then rewrites
        // seeded LF files as CRLF and breaks exact content assertions.
        git(repo, &["config", "core.autocrlf", "false"]);
        git(repo, &["config", "core.eol", "lf"]);
    }

    fn make_worktree_with_bare_remote() -> (PathBuf, PathBuf) {
        let root = unique_temp("pair");
        fs::create_dir_all(&root).unwrap();
        let bare = root.join("remote.git");
        let work = root.join("work");
        fs::create_dir_all(&work).unwrap();

        // Pin bare default to `main` so clone checks out a real branch (bare
        // `git init` often leaves HEAD → master while we only push `main`).
        git(
            &root,
            &["init", "--bare", "-b", "main", bare.to_str().unwrap()],
        );
        git(&work, &["init", "-b", "main"]);
        init_identity(&work);
        fs::write(work.join("a.txt"), "v1\n").unwrap();
        git(&work, &["add", "a.txt"]);
        git(&work, &["commit", "-m", "seed"]);
        git(
            &work,
            &["remote", "add", "origin", bare.to_str().expect("utf8 path")],
        );
        git(&work, &["push", "-u", "origin", "main"]);
        (work, bare)
    }

    #[test]
    fn std_write_denies_without_approval_no_mutation() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let before = Command::new("git")
            .args(["-C", repo, "rev-parse", "HEAD"])
            .output()
            .unwrap();
        let head_before = String::from_utf8_lossy(&before.stdout).trim().to_string();

        fs::write(work.join("a.txt"), "dirty\n").unwrap();
        let w = StdGitWrite::new();
        let err = w
            .commit(repo, "should not land", GitWriteApproval::denied())
            .expect_err("denied");
        assert!(matches!(err, PortError::PermissionDenied(_)));

        let after = Command::new("git")
            .args(["-C", repo, "rev-parse", "HEAD"])
            .output()
            .unwrap();
        let head_after = String::from_utf8_lossy(&after.stdout).trim().to_string();
        assert_eq!(head_before, head_after, "unapproved commit must not mutate");
        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_approved_commit_and_push() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        fs::write(work.join("a.txt"), "v2\n").unwrap();

        let w = StdGitWrite::new();
        w.commit(repo, "feat: v2", GitWriteApproval::granted())
            .expect("commit");
        w.push(repo, "origin", Some("main"), GitWriteApproval::granted())
            .expect("push");

        let log = Command::new("git")
            .args(["-C", repo, "log", "-1", "--pretty=%s"])
            .output()
            .unwrap();
        assert_eq!(String::from_utf8_lossy(&log.stdout).trim(), "feat: v2");
        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_push_non_fast_forward_preserves_local_commit() {
        let (work, bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let root = work.parent().unwrap();

        // Advance remote independently (fixture may force-push; StdGitWrite never does).
        let other = root.join("other");
        let clone = Command::new("git")
            .args(["clone", bare.to_str().unwrap(), other.to_str().unwrap()])
            .current_dir(root)
            .output()
            .expect("spawn clone");
        assert!(
            clone.status.success(),
            "clone failed: {}",
            String::from_utf8_lossy(&clone.stderr)
        );
        init_identity(&other);
        fs::write(other.join("remote-only.txt"), "x\n").unwrap();
        git(&other, &["add", "remote-only.txt"]);
        git(&other, &["commit", "-m", "remote advance"]);
        // Force only in fixture setup to create divergence; product path forbids force.
        git(&other, &["push", "--force", "origin", "HEAD:main"]);

        fs::write(work.join("a.txt"), "local-ahead\n").unwrap();
        let w = StdGitWrite::new();
        w.commit(repo, "local only", GitWriteApproval::granted())
            .unwrap();
        let head = Command::new("git")
            .args(["-C", repo, "rev-parse", "HEAD"])
            .output()
            .unwrap();
        let local_head = String::from_utf8_lossy(&head.stdout).trim().to_string();

        let err = w
            .push(repo, "origin", Some("main"), GitWriteApproval::granted())
            .expect_err("non-ff push must fail");
        assert!(matches!(err, PortError::Git(_)));

        let head2 = Command::new("git")
            .args(["-C", repo, "rev-parse", "HEAD"])
            .output()
            .unwrap();
        assert_eq!(
            String::from_utf8_lossy(&head2.stdout).trim(),
            local_head,
            "push failure must preserve local commit"
        );
        let subj = Command::new("git")
            .args(["-C", repo, "log", "-1", "--pretty=%s"])
            .output()
            .unwrap();
        assert_eq!(String::from_utf8_lossy(&subj.stdout).trim(), "local only");
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn std_write_redacts_credentials_in_errors() {
        // Unit-level via the same helper StdGitWrite uses — injected stderr path.
        let dirty = "fatal: could not read Password for 'https://bot:ghp_LEAKEDSECRET@host/r.git'";
        let clean = crate::git_write::redact_credentials(dirty);
        assert!(!clean.contains("ghp_LEAKEDSECRET"));
        assert!(!clean.contains("bot:ghp_"));
    }

    fn head_ref(repo: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "rev-parse", "--abbrev-ref", "HEAD"])
            .output()
            .unwrap();
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    }

    // PD-GIT-SWITCH-02 RED: approved switch moves HEAD to an existing local branch.
    #[test]
    fn std_write_switch_moves_head_to_existing_branch() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        // Second local branch at the seed commit; stay on main.
        git(&work, &["branch", "feature"]);
        assert_eq!(head_ref(repo), "main", "fixture starts on main");

        let w = StdGitWrite::new();
        w.switch_branch(repo, "feature", GitWriteApproval::granted())
            .expect("approved switch");

        assert_eq!(head_ref(repo), "feature", "approved switch must move HEAD");
        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    fn local_config(repo: &str, key: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "config", "--local", "--get", key])
            .output()
            .unwrap();
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    }

    #[test]
    fn std_write_identity_sets_local_not_global_when_approved() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let unique = format!("sgenaxis-settings-{}", SEQ.fetch_add(1, Ordering::Relaxed));
        let email = format!("{unique}@example.invalid");

        let w = StdGitWrite::new();
        w.set_identity(
            repo,
            "should not land",
            "nope@example.invalid",
            GitWriteApproval::denied(),
        )
        .expect_err("denied identity must not mutate");
        assert_ne!(local_config(repo, "user.name"), "should not land");

        w.set_identity(repo, &unique, &email, GitWriteApproval::granted())
            .expect("approved identity");
        assert_eq!(local_config(repo, "user.name"), unique);
        assert_eq!(local_config(repo, "user.email"), email);

        let global = Command::new("git")
            .args(["config", "--global", "--get", "user.name"])
            .output()
            .unwrap();
        let global_name = String::from_utf8_lossy(&global.stdout).trim().to_string();
        assert_ne!(
            global_name, unique,
            "identity write must never land in --global"
        );

        w.set_identity(
            repo,
            "--global",
            "x@example.invalid",
            GitWriteApproval::granted(),
        )
        .expect_err("global flag as name is out of scope");
        assert_eq!(local_config(repo, "user.name"), unique);

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_ignore_writes_root_gitignore_without_untracking() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        fs::write(work.join("keep.txt"), "tracked\n").unwrap();
        git(&work, &["add", "keep.txt"]);
        git(&work, &["commit", "-m", "keep tracked"]);

        let w = StdGitWrite::new();
        w.set_ignore(repo, "keep.txt\n", GitWriteApproval::denied())
            .expect_err("denied ignore must not mutate");
        assert!(
            !work.join(".gitignore").exists() || {
                let body = fs::read_to_string(work.join(".gitignore")).unwrap_or_default();
                !body.contains("keep.txt")
            }
        );

        w.set_ignore(repo, "keep.txt\n*.tmp\n", GitWriteApproval::granted())
            .expect("approved ignore");
        let body = fs::read_to_string(work.join(".gitignore")).expect("gitignore written");
        assert_eq!(body, "keep.txt\n*.tmp\n");

        let tracked = Command::new("git")
            .args(["-C", repo, "ls-files", "--", "keep.txt"])
            .output()
            .unwrap();
        assert_eq!(
            String::from_utf8_lossy(&tracked.stdout).trim(),
            "keep.txt",
            "writing .gitignore must not stop tracking existing files"
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    fn stash_list(repo: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "stash", "list"])
            .output()
            .unwrap();
        String::from_utf8_lossy(&out.stdout).to_string()
    }

    fn unmerged(repo: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "ls-files", "-u"])
            .output()
            .unwrap();
        String::from_utf8_lossy(&out.stdout).to_string()
    }

    fn is_honest_stash_failure(err: &PortError, repo: &str) -> bool {
        let msg = err.to_string().to_ascii_lowercase();
        msg.contains("conflict")
            || msg.contains("abort")
            || msg.contains("overwritten")
            || !unmerged(repo).trim().is_empty()
    }

    fn seed_stash(work: &Path) {
        fs::write(work.join("a.txt"), "stashed\n").unwrap();
        git(work, &["stash", "push", "-m", "wip"]);
    }

    #[test]
    fn std_write_stash_apply_keeps_stash_when_approved() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        seed_stash(&work);
        assert!(stash_list(repo).contains("stash@{0}"));
        assert_eq!(fs::read_to_string(work.join("a.txt")).unwrap(), "v1\n");

        let w = StdGitWrite::new();
        w.stash_apply(repo, "stash@{0}", GitWriteApproval::denied())
            .expect_err("denied apply must not mutate");
        assert_eq!(fs::read_to_string(work.join("a.txt")).unwrap(), "v1\n");
        assert!(stash_list(repo).contains("stash@{0}"));

        w.stash_apply(repo, "-q", GitWriteApproval::granted())
            .expect_err("quiet flag is out of scope");
        w.stash_apply(repo, "drop", GitWriteApproval::granted())
            .expect_err("drop is out of scope");

        w.stash_apply(repo, "stash@{0}", GitWriteApproval::granted())
            .expect("approved apply");
        assert_eq!(fs::read_to_string(work.join("a.txt")).unwrap(), "stashed\n");
        assert!(
            stash_list(repo).contains("stash@{0}"),
            "apply must keep the stash: {}",
            stash_list(repo)
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_stash_pop_drops_only_on_success() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        seed_stash(&work);
        assert!(stash_list(repo).contains("stash@{0}"));

        let w = StdGitWrite::new();
        w.stash_pop(repo, "stash@{0}", GitWriteApproval::denied())
            .expect_err("denied pop must not mutate");
        assert!(stash_list(repo).contains("stash@{0}"));

        w.stash_pop(repo, "stash@{0}", GitWriteApproval::granted())
            .expect("approved pop");
        assert_eq!(fs::read_to_string(work.join("a.txt")).unwrap(), "stashed\n");
        assert!(
            stash_list(repo).trim().is_empty(),
            "successful pop must remove the stash: {}",
            stash_list(repo)
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_stash_conflict_preserves_stash_and_does_not_invent_success() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        seed_stash(&work);
        fs::write(work.join("a.txt"), "other\n").unwrap();
        git(&work, &["add", "a.txt"]);
        git(&work, &["commit", "-m", "divergent"]);

        let w = StdGitWrite::new();
        let apply_err = w
            .stash_apply(repo, "stash@{0}", GitWriteApproval::granted())
            .expect_err("conflicting apply must fail");
        assert!(matches!(apply_err, PortError::Git(_)));
        assert!(
            is_honest_stash_failure(&apply_err, repo),
            "conflict must not be hidden by -q: {apply_err}"
        );
        assert!(
            stash_list(repo).contains("stash@{0}"),
            "apply conflict must keep the stash"
        );

        git(&work, &["reset", "--hard", "HEAD"]);
        let pop_err = w
            .stash_pop(repo, "stash@{0}", GitWriteApproval::granted())
            .expect_err("conflicting pop must fail");
        assert!(matches!(pop_err, PortError::Git(_)));
        assert!(
            stash_list(repo).contains("stash@{0}"),
            "pop conflict must keep the stash; must not invent success"
        );
        assert!(
            is_honest_stash_failure(&pop_err, repo),
            "pop conflict must leave honest repo state: {pop_err}"
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_stash_drop_removes_only_the_named_stash() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        seed_stash(&work);
        assert!(stash_list(repo).contains("stash@{0}"));

        let w = StdGitWrite::new();
        w.stash_drop(repo, "stash@{0}", GitWriteApproval::denied())
            .expect_err("denied drop must not mutate");
        assert!(stash_list(repo).contains("stash@{0}"));

        w.stash_drop(repo, "clear", GitWriteApproval::granted())
            .expect_err("clear is out of scope");
        assert!(stash_list(repo).contains("stash@{0}"));

        w.stash_drop(repo, "stash@{0}", GitWriteApproval::granted())
            .expect("approved drop");
        assert!(
            stash_list(repo).trim().is_empty(),
            "successful drop must remove the named stash: {}",
            stash_list(repo)
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_stash_drop_missing_fails_honestly() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        seed_stash(&work);
        assert!(stash_list(repo).contains("stash@{0}"));

        let w = StdGitWrite::new();
        let err = w
            .stash_drop(repo, "stash@{9}", GitWriteApproval::granted())
            .expect_err("missing stash must fail");
        assert!(matches!(err, PortError::Git(_)));
        let msg = err.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("stash@{9}") || msg.contains("not a valid reference"),
            "missing drop must fail honestly: {err}"
        );
        assert!(
            stash_list(repo).contains("stash@{0}"),
            "failed drop must leave existing stashes: {}",
            stash_list(repo)
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_stash_push_tracked_only_when_approved() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        fs::write(work.join("a.txt"), "tracked dirty\n").unwrap();
        fs::write(work.join("untracked.txt"), "leave me\n").unwrap();

        let w = StdGitWrite::new();
        w.stash_push(repo, "wip", GitWriteApproval::denied())
            .expect_err("denied push must not mutate");
        assert_eq!(
            fs::read_to_string(work.join("a.txt")).unwrap(),
            "tracked dirty\n"
        );
        assert!(stash_list(repo).trim().is_empty());

        w.stash_push(repo, "   ", GitWriteApproval::granted())
            .expect_err("empty message must fail");
        assert!(stash_list(repo).trim().is_empty());

        w.stash_push(repo, "WIP: panel", GitWriteApproval::granted())
            .expect("approved tracked-only push");
        assert_eq!(fs::read_to_string(work.join("a.txt")).unwrap(), "v1\n");
        assert_eq!(
            fs::read_to_string(work.join("untracked.txt")).unwrap(),
            "leave me\n",
            "tracked-only push must not consume untracked files"
        );
        let list = stash_list(repo);
        assert!(
            list.contains("WIP: panel"),
            "stash list must include the message: {list}"
        );
        assert!(
            list.contains("stash@{0}"),
            "successful push must create a stash: {list}"
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    fn tag_list(repo: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "tag", "-l"])
            .output()
            .expect("git tag -l");
        String::from_utf8_lossy(&out.stdout).to_string()
    }

    fn tag_object_type(repo: &str, name: &str) -> String {
        let spec = format!("refs/tags/{name}");
        let out = Command::new("git")
            .args(["-C", repo, "cat-file", "-t", &spec])
            .output()
            .expect("git cat-file -t");
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    }

    #[test]
    fn std_write_create_tag_lightweight_and_annotated_when_approved() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let w = StdGitWrite::new();

        w.create_tag(repo, "v1.0.0", "", GitWriteApproval::denied())
            .expect_err("denied tag must not mutate");
        assert!(tag_list(repo).trim().is_empty());

        w.create_tag(repo, "  ", "", GitWriteApproval::granted())
            .expect_err("empty name must fail");
        assert!(tag_list(repo).trim().is_empty());

        w.create_tag(repo, "-f", "", GitWriteApproval::granted())
            .expect_err("force flag name is out of scope");
        w.create_tag(repo, "--delete", "", GitWriteApproval::granted())
            .expect_err("delete is out of scope");
        assert!(tag_list(repo).trim().is_empty());

        w.create_tag(repo, "v1.0.0", "", GitWriteApproval::granted())
            .expect("approved lightweight");
        let list = tag_list(repo);
        assert!(list.contains("v1.0.0"), "lightweight tag missing: {list}");
        assert_eq!(tag_object_type(repo, "v1.0.0"), "commit");

        w.create_tag(repo, "v1.1.0", "release notes", GitWriteApproval::granted())
            .expect("approved annotated");
        let list = tag_list(repo);
        assert!(list.contains("v1.1.0"), "annotated tag missing: {list}");
        assert_eq!(tag_object_type(repo, "v1.1.0"), "tag");

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_create_tag_duplicate_fails_honestly() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let w = StdGitWrite::new();
        w.create_tag(repo, "v1.0.0", "first", GitWriteApproval::granted())
            .expect("first tag");
        let err = w
            .create_tag(repo, "v1.0.0", "overwrite", GitWriteApproval::granted())
            .expect_err("duplicate must fail without -f");
        assert!(matches!(err, PortError::Git(_)));
        let msg = err.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("already exists") || msg.contains("v1.0.0"),
            "duplicate must fail honestly: {err}"
        );
        assert_eq!(tag_object_type(repo, "v1.0.0"), "tag");
        let log = Command::new("git")
            .args(["-C", repo, "tag", "-l", "-n1", "v1.0.0"])
            .output()
            .unwrap();
        let annotated = String::from_utf8_lossy(&log.stdout);
        assert!(
            annotated.contains("first"),
            "duplicate must not overwrite annotated message: {annotated}"
        );
        assert!(
            !annotated.contains("overwrite"),
            "duplicate must not force-update: {annotated}"
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    fn remote_tag_list(bare: &Path) -> String {
        let out = Command::new("git")
            .args(["-C", bare.to_str().unwrap(), "tag", "-l"])
            .output()
            .expect("git tag -l remote");
        String::from_utf8_lossy(&out.stdout).to_string()
    }

    #[test]
    fn std_write_delete_tag_local_only_when_approved() {
        let (work, bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        git(&work, &["tag", "v1.0.0"]);
        git(&work, &["tag", "-a", "-m", "keep", "v1.1.0"]);
        git(&work, &["push", "origin", "v1.0.0"]);
        assert!(tag_list(repo).contains("v1.0.0"));
        assert!(remote_tag_list(&bare).contains("v1.0.0"));

        let w = StdGitWrite::new();
        w.delete_tag(repo, "v1.0.0", GitWriteApproval::denied())
            .expect_err("denied delete must not mutate");
        assert!(tag_list(repo).contains("v1.0.0"));
        assert!(remote_tag_list(&bare).contains("v1.0.0"));

        w.delete_tag(repo, "  ", GitWriteApproval::granted())
            .expect_err("empty name must fail");
        w.delete_tag(repo, "-f", GitWriteApproval::granted())
            .expect_err("force flag name is out of scope");
        w.delete_tag(repo, "--delete", GitWriteApproval::granted())
            .expect_err("delete flag as name is out of scope");
        assert!(tag_list(repo).contains("v1.0.0"));

        w.delete_tag(repo, "v1.0.0", GitWriteApproval::granted())
            .expect("approved local delete");
        let list = tag_list(repo);
        assert!(!list.contains("v1.0.0"), "local tag must be gone: {list}");
        assert!(
            list.contains("v1.1.0"),
            "other local tags must remain: {list}"
        );
        assert!(
            remote_tag_list(&bare).contains("v1.0.0"),
            "local delete must never push --delete: {}",
            remote_tag_list(&bare)
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_delete_tag_missing_fails_honestly() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        git(&work, &["tag", "v1.0.0"]);
        assert!(tag_list(repo).contains("v1.0.0"));

        let w = StdGitWrite::new();
        let err = w
            .delete_tag(repo, "v9.9.9", GitWriteApproval::granted())
            .expect_err("missing tag must fail");
        assert!(matches!(err, PortError::Git(_)));
        let msg = err.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("v9.9.9") || msg.contains("not found") || msg.contains("not exist"),
            "missing delete must fail honestly: {err}"
        );
        assert!(
            tag_list(repo).contains("v1.0.0"),
            "failed delete must leave existing tags: {}",
            tag_list(repo)
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    fn local_branch_list(repo: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "branch", "--list"])
            .output()
            .expect("git branch --list");
        String::from_utf8_lossy(&out.stdout).to_string()
    }

    #[test]
    fn std_write_create_branch_from_head_without_switch_when_approved() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        assert_eq!(head_ref(repo), "main");
        let w = StdGitWrite::new();

        w.create_branch(repo, "feature/slot", GitWriteApproval::denied())
            .expect_err("denied create must not mutate");
        assert!(!local_branch_list(repo).contains("feature/slot"));
        assert_eq!(head_ref(repo), "main");

        w.create_branch(repo, "  ", GitWriteApproval::granted())
            .expect_err("empty name must fail");
        w.create_branch(repo, "-D", GitWriteApproval::granted())
            .expect_err("delete flag name is out of scope");
        w.create_branch(repo, "-C", GitWriteApproval::granted())
            .expect_err("force-create flag name is out of scope");
        w.create_branch(repo, "--set-upstream", GitWriteApproval::granted())
            .expect_err("upstream is out of scope");
        w.create_branch(repo, "bad..name", GitWriteApproval::granted())
            .expect_err("invalid name must fail");
        assert_eq!(head_ref(repo), "main");
        assert!(!local_branch_list(repo).contains("feature/slot"));

        w.create_branch(repo, "feature/slot", GitWriteApproval::granted())
            .expect("approved create");
        let list = local_branch_list(repo);
        assert!(
            list.contains("feature/slot"),
            "local branch missing: {list}"
        );
        assert_eq!(
            head_ref(repo),
            "main",
            "create must not switch HEAD as a side effect"
        );

        let dup = w
            .create_branch(repo, "feature/slot", GitWriteApproval::granted())
            .expect_err("duplicate must fail without -f/-C");
        assert!(matches!(dup, PortError::Git(_)));
        let msg = dup.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("already exists") || msg.contains("feature/slot"),
            "duplicate must fail honestly: {dup}"
        );
        assert_eq!(head_ref(repo), "main");

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_delete_branch_safe_only_when_approved() {
        let (work, _bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        git(&work, &["branch", "--", "feature/slot"]);
        git(&work, &["checkout", "-b", "unmerged"]);
        fs::write(work.join("a.txt"), "v2-unmerged\n").unwrap();
        git(&work, &["add", "a.txt"]);
        git(&work, &["commit", "-m", "unmerged"]);
        git(&work, &["checkout", "main"]);
        assert_eq!(head_ref(repo), "main");
        let w = StdGitWrite::new();

        w.delete_branch(repo, "feature/slot", GitWriteApproval::denied())
            .expect_err("denied delete must not mutate");
        assert!(local_branch_list(repo).contains("feature/slot"));
        assert_eq!(head_ref(repo), "main");

        w.delete_branch(repo, "  ", GitWriteApproval::granted())
            .expect_err("empty name must fail");
        w.delete_branch(repo, "-D", GitWriteApproval::granted())
            .expect_err("force-delete flag name is out of scope");
        w.delete_branch(repo, "-r", GitWriteApproval::granted())
            .expect_err("remote-tracking flag name is out of scope");
        w.delete_branch(repo, "../evil", GitWriteApproval::granted())
            .expect_err("path traversal name is out of scope");
        w.delete_branch(repo, "main", GitWriteApproval::granted())
            .expect_err("current HEAD must not be deleted");
        assert_eq!(head_ref(repo), "main");
        assert!(local_branch_list(repo).contains("feature/slot"));
        assert!(local_branch_list(repo).contains("unmerged"));

        let unmerged = w
            .delete_branch(repo, "unmerged", GitWriteApproval::granted())
            .expect_err("unmerged must fail without -D");
        assert!(matches!(unmerged, PortError::Git(_)));
        let umsg = unmerged.to_string().to_ascii_lowercase();
        assert!(
            umsg.contains("not fully merged") || umsg.contains("unmerged"),
            "unmerged must fail honestly: {unmerged}"
        );
        assert!(
            local_branch_list(repo).contains("unmerged"),
            "failed -d must leave the unmerged branch"
        );
        assert_eq!(head_ref(repo), "main");

        let missing = w
            .delete_branch(repo, "ghost", GitWriteApproval::granted())
            .expect_err("missing branch must fail");
        assert!(matches!(missing, PortError::Git(_)));

        w.delete_branch(repo, "feature/slot", GitWriteApproval::granted())
            .expect("approved safe delete");
        let list = local_branch_list(repo);
        assert!(
            !list.contains("feature/slot"),
            "merged local branch should be gone: {list}"
        );
        assert!(list.contains("unmerged"), "unmerged branch must remain");
        assert_eq!(
            head_ref(repo),
            "main",
            "delete must not switch HEAD as a side effect"
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    fn remote_list(repo: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "remote", "-v"])
            .output()
            .expect("git remote -v");
        String::from_utf8_lossy(&out.stdout).to_string()
    }

    #[test]
    fn std_write_add_and_remove_remote_without_fetch_when_approved() {
        let (work, bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let url = bare.to_str().unwrap();
        let w = StdGitWrite::new();

        w.add_remote(repo, "upstream", url, GitWriteApproval::denied())
            .expect_err("denied add must not mutate");
        assert!(!remote_list(repo).contains("upstream"));
        assert!(!work.join(".git").join("FETCH_HEAD").exists());

        w.add_remote(repo, "  ", url, GitWriteApproval::granted())
            .expect_err("empty name must fail");
        w.add_remote(repo, "upstream", "  ", GitWriteApproval::granted())
            .expect_err("empty url must fail");
        w.add_remote(repo, "-f", url, GitWriteApproval::granted())
            .expect_err("fetch flag name is out of scope");
        w.add_remote(repo, "--mirror", url, GitWriteApproval::granted())
            .expect_err("mirror flag name is out of scope");
        w.add_remote(repo, "upstream", "-u", GitWriteApproval::granted())
            .expect_err("flag-like url is out of scope");
        assert!(!remote_list(repo).contains("upstream"));

        w.add_remote(repo, "upstream", url, GitWriteApproval::granted())
            .expect("approved add");
        let listed = remote_list(repo);
        assert!(listed.contains("upstream"), "remote missing: {listed}");
        assert!(listed.contains(url), "url missing: {listed}");
        assert!(
            !work.join(".git").join("FETCH_HEAD").exists(),
            "add must not fetch as a side effect"
        );
        assert!(
            !work
                .join(".git")
                .join("refs")
                .join("remotes")
                .join("upstream")
                .exists(),
            "add must not create remote-tracking refs"
        );

        let dup = w
            .add_remote(repo, "upstream", url, GitWriteApproval::granted())
            .expect_err("duplicate must fail without -f/set-url");
        assert!(matches!(dup, PortError::Git(_)));
        let msg = dup.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("already exists") || msg.contains("upstream"),
            "duplicate must fail honestly: {dup}"
        );

        w.remove_remote(repo, "ghost", GitWriteApproval::granted())
            .expect_err("missing remote must fail honestly");
        assert!(remote_list(repo).contains("upstream"));

        w.remove_remote(repo, "upstream", GitWriteApproval::denied())
            .expect_err("denied remove must not mutate");
        assert!(remote_list(repo).contains("upstream"));

        w.remove_remote(repo, "upstream", GitWriteApproval::granted())
            .expect("approved remove");
        assert!(
            !remote_list(repo).contains("upstream"),
            "removed remote still listed: {}",
            remote_list(repo)
        );
        assert!(remote_list(repo).contains("origin"));

        let _ = fs::remove_dir_all(work.parent().unwrap());
    }

    #[test]
    fn std_write_set_remote_url_without_fetch_when_approved() {
        let (work, bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let old = bare.to_str().unwrap();
        let w = StdGitWrite::new();
        let next = unique_temp("set-url-bare");
        fs::create_dir_all(&next).unwrap();
        git(&next, &["init", "--bare"]);
        let new_url = next.to_str().unwrap();

        w.set_remote_url(repo, "origin", new_url, GitWriteApproval::denied())
            .expect_err("denied set-url must not mutate");
        assert!(remote_list(repo).contains(old));
        assert!(!work.join(".git").join("FETCH_HEAD").exists());

        w.set_remote_url(repo, "  ", new_url, GitWriteApproval::granted())
            .expect_err("empty name must fail");
        w.set_remote_url(repo, "origin", "  ", GitWriteApproval::granted())
            .expect_err("empty url must fail");
        w.set_remote_url(repo, "-f", new_url, GitWriteApproval::granted())
            .expect_err("fetch flag name is out of scope");
        w.set_remote_url(repo, "--mirror", new_url, GitWriteApproval::granted())
            .expect_err("mirror flag name is out of scope");
        w.set_remote_url(repo, "--push", new_url, GitWriteApproval::granted())
            .expect_err("push-url flag name is out of scope");
        w.set_remote_url(repo, "origin", "-u", GitWriteApproval::granted())
            .expect_err("flag-like url is out of scope");
        w.set_remote_url(
            repo,
            "origin",
            &format!("{new_url};echo"),
            GitWriteApproval::granted(),
        )
        .expect_err("shell metacharacters in url are out of scope");
        assert!(remote_list(repo).contains(old));

        let missing = w
            .set_remote_url(repo, "ghost", new_url, GitWriteApproval::granted())
            .expect_err("unknown remote must fail honestly");
        assert!(matches!(missing, PortError::Git(_)));
        let msg = missing.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("no such remote") || msg.contains("ghost"),
            "missing remote must fail honestly: {missing}"
        );

        w.set_remote_url(repo, "origin", new_url, GitWriteApproval::granted())
            .expect("approved set-url");
        let listed = remote_list(repo);
        assert!(listed.contains("origin"), "remote missing: {listed}");
        assert!(listed.contains(new_url), "new url missing: {listed}");
        assert!(!listed.contains(old), "old url still listed: {listed}");
        assert!(
            !work.join(".git").join("FETCH_HEAD").exists(),
            "set-url must not fetch as a side effect"
        );

        let _ = fs::remove_dir_all(work.parent().unwrap());
        let _ = fs::remove_dir_all(&next);
    }

    fn rev_parse(repo: &str, rev: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "rev-parse", rev])
            .output()
            .expect("git rev-parse");
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    }

    #[test]
    fn std_write_fetch_updates_remote_tracking_without_moving_head() {
        let (work, bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let root = work.parent().unwrap();
        let other = root.join("other");
        git(
            root,
            &["clone", bare.to_str().unwrap(), other.to_str().unwrap()],
        );
        init_identity(&other);
        fs::write(other.join("a.txt"), "v2-remote\n").unwrap();
        git(&other, &["add", "a.txt"]);
        git(&other, &["commit", "-m", "remote tip"]);
        git(&other, &["push", "origin", "main"]);

        let head_before = rev_parse(repo, "HEAD");
        let tracking_before = rev_parse(repo, "refs/remotes/origin/main");
        let worktree_before = fs::read_to_string(work.join("a.txt")).unwrap();
        assert_eq!(head_before, tracking_before);
        assert_eq!(worktree_before, "v1\n");

        let w = StdGitWrite::new();
        w.fetch(repo, "origin", None, GitWriteApproval::denied())
            .expect_err("denied fetch must not mutate");
        assert_eq!(rev_parse(repo, "HEAD"), head_before);
        assert_eq!(rev_parse(repo, "refs/remotes/origin/main"), tracking_before);

        let missing = w
            .fetch(repo, "ghost", None, GitWriteApproval::granted())
            .expect_err("unknown remote must fail honestly");
        assert!(matches!(missing, PortError::Git(_)));
        let msg = missing.to_string().to_ascii_lowercase();
        assert!(
            msg.contains("no such remote") || msg.contains("ghost"),
            "missing remote must fail honestly: {missing}"
        );
        assert!(!remote_list(repo).contains("ghost"));

        w.fetch(
            repo,
            "origin",
            Some("+refs/heads/main:refs/remotes/origin/main"),
            GitWriteApproval::granted(),
        )
        .expect_err("force refspec is out of scope");
        w.fetch(repo, "origin", Some("--prune"), GitWriteApproval::granted())
            .expect_err("ordinary fetch must reject --prune refspec");
        w.fetch(repo, "--prune", None, GitWriteApproval::granted())
            .expect_err("ordinary fetch must reject --prune remote");
        assert_eq!(rev_parse(repo, "refs/remotes/origin/main"), tracking_before);

        w.fetch(repo, "origin", None, GitWriteApproval::granted())
            .expect("approved fetch");
        let tracking_after = rev_parse(repo, "refs/remotes/origin/main");
        assert_ne!(
            tracking_after, tracking_before,
            "fetch must update remote-tracking refs"
        );
        assert_eq!(rev_parse(repo, "HEAD"), head_before);
        assert_eq!(
            fs::read_to_string(work.join("a.txt")).unwrap(),
            worktree_before,
            "fetch must not merge into the worktree"
        );
        assert_eq!(
            Command::new("git")
                .args(["-C", repo, "rev-parse", "--abbrev-ref", "HEAD"])
                .output()
                .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                .unwrap(),
            "main"
        );

        let _ = fs::remove_dir_all(root);
    }

    fn ref_exists(repo: &str, rev: &str) -> bool {
        Command::new("git")
            .args(["-C", repo, "show-ref", "--verify", "--quiet", rev])
            .status()
            .map(|s| s.success())
            .unwrap_or(false)
    }

    #[test]
    fn std_write_fetch_prune_deletes_stale_remote_tracking_without_moving_head() {
        let (work, bare) = make_worktree_with_bare_remote();
        let repo = work.to_str().unwrap();
        let root = work.parent().unwrap();
        let other = root.join("other");
        git(
            root,
            &["clone", bare.to_str().unwrap(), other.to_str().unwrap()],
        );
        init_identity(&other);
        git(&other, &["checkout", "-b", "stale"]);
        fs::write(other.join("s.txt"), "stale\n").unwrap();
        git(&other, &["add", "s.txt"]);
        git(&other, &["commit", "-m", "stale branch"]);
        git(&other, &["push", "origin", "stale"]);
        git(&other, &["checkout", "main"]);

        let w = StdGitWrite::new();
        w.fetch(repo, "origin", None, GitWriteApproval::granted())
            .expect("fetch stale tracking");
        assert!(
            ref_exists(repo, "refs/remotes/origin/stale"),
            "setup must create origin/stale"
        );

        let head_before = rev_parse(repo, "HEAD");
        let worktree_before = fs::read_to_string(work.join("a.txt")).unwrap();
        let branches_before = local_branch_list(repo);
        assert!(!branches_before.contains("stale"));

        w.fetch(repo, "origin", Some("--prune"), GitWriteApproval::granted())
            .expect_err("ordinary fetch must still reject --prune");
        w.fetch(
            repo,
            "origin",
            Some("+refs/heads/main:refs/remotes/origin/main"),
            GitWriteApproval::granted(),
        )
        .expect_err("ordinary fetch must still reject force refspec");
        assert!(ref_exists(repo, "refs/remotes/origin/stale"));

        git(&other, &["push", "origin", "--delete", "stale"]);

        w.fetch_prune(repo, "origin", GitWriteApproval::denied())
            .expect_err("denied fetch-prune must not mutate");
        assert!(ref_exists(repo, "refs/remotes/origin/stale"));
        assert_eq!(rev_parse(repo, "HEAD"), head_before);

        w.fetch_prune(repo, "--force", GitWriteApproval::granted())
            .expect_err("force flag is out of scope");
        w.fetch_prune(repo, "--prune-tags", GitWriteApproval::granted())
            .expect_err("prune-tags is out of scope");
        w.fetch_prune(
            repo,
            "+refs/heads/main:refs/remotes/origin/main",
            GitWriteApproval::granted(),
        )
        .expect_err("force refspec is out of scope");
        let missing = w
            .fetch_prune(repo, "ghost", GitWriteApproval::granted())
            .expect_err("unknown remote must fail honestly");
        assert!(matches!(missing, PortError::Git(_)));

        w.fetch_prune(repo, "origin", GitWriteApproval::granted())
            .expect("approved fetch-prune");
        assert!(
            !ref_exists(repo, "refs/remotes/origin/stale"),
            "fetch-prune must delete stale remote-tracking refs"
        );
        assert!(ref_exists(repo, "refs/remotes/origin/main"));
        assert_eq!(rev_parse(repo, "HEAD"), head_before);
        assert_eq!(
            fs::read_to_string(work.join("a.txt")).unwrap(),
            worktree_before,
            "fetch-prune must not change the worktree"
        );
        assert_eq!(local_branch_list(repo), branches_before);
        assert_eq!(
            Command::new("git")
                .args(["-C", repo, "rev-parse", "--abbrev-ref", "HEAD"])
                .output()
                .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                .unwrap(),
            "main"
        );

        let _ = fs::remove_dir_all(root);
    }

    fn make_merge_conflict() -> PathBuf {
        let root = unique_temp("merge-conflict");
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "-b", "main"]);
        init_identity(&root);
        fs::write(root.join("a.txt"), "base\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "base"]);
        git(&root, &["checkout", "-b", "other"]);
        fs::write(root.join("a.txt"), "theirs\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "theirs"]);
        git(&root, &["checkout", "main"]);
        fs::write(root.join("a.txt"), "ours\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "ours"]);
        let merge = Command::new("git")
            .args(["merge", "other"])
            .current_dir(&root)
            .output()
            .expect("merge");
        assert!(
            !merge.status.success(),
            "expected conflict: {}",
            String::from_utf8_lossy(&merge.stderr)
        );
        root
    }

    fn merge_head_exists(repo: &Path) -> bool {
        repo.join(".git").join("MERGE_HEAD").exists()
    }

    #[test]
    fn std_write_conflict_save_continue_abort_when_approved() {
        let work = make_merge_conflict();
        let repo = work.to_str().unwrap();
        let w = StdGitWrite::new();

        w.conflict_save(repo, "a.txt", GitWriteApproval::denied())
            .expect_err("denied save must not stage");
        assert!(merge_head_exists(&work));
        let unmerged = Command::new("git")
            .args(["-C", repo, "ls-files", "-u"])
            .output()
            .unwrap();
        assert!(
            String::from_utf8_lossy(&unmerged.stdout).contains("a.txt"),
            "denied save must leave the path unmerged"
        );

        w.conflict_save(repo, "a.txt", GitWriteApproval::granted())
            .expect_err("markers must fail honestly");
        w.conflict_save(repo, ".", GitWriteApproval::granted())
            .expect_err("dot add is out of scope");
        w.conflict_save(repo, "-A", GitWriteApproval::granted())
            .expect_err("add -A is out of scope");
        w.conflict_continue(repo, GitWriteApproval::granted())
            .expect_err("unmerged continue must fail");

        fs::write(work.join("a.txt"), "resolved\n").unwrap();
        w.conflict_save(repo, "a.txt", GitWriteApproval::granted())
            .expect("approved save");
        let staged = Command::new("git")
            .args(["-C", repo, "diff", "--cached", "--name-only"])
            .output()
            .unwrap();
        assert!(
            String::from_utf8_lossy(&staged.stdout).contains("a.txt"),
            "resolved path must be staged"
        );
        assert!(merge_head_exists(&work), "save must not finish the merge");

        w.conflict_continue(repo, GitWriteApproval::denied())
            .expect_err("denied continue must not mutate");
        assert!(merge_head_exists(&work));

        w.conflict_continue(repo, GitWriteApproval::granted())
            .expect("approved continue");
        assert!(
            !merge_head_exists(&work),
            "merge --continue must clear MERGE_HEAD"
        );
        let log = Command::new("git")
            .args(["-C", repo, "log", "-1", "--pretty=%s"])
            .output()
            .unwrap();
        let subject = String::from_utf8_lossy(&log.stdout);
        assert!(
            subject.to_ascii_lowercase().contains("merge"),
            "continue should create merge commit: {subject}"
        );

        w.conflict_abort(repo, GitWriteApproval::granted())
            .expect_err("missing conflict state must fail honestly");

        let work2 = make_merge_conflict();
        let repo2 = work2.to_str().unwrap();
        w.conflict_abort(repo2, GitWriteApproval::denied())
            .expect_err("denied abort must not mutate");
        assert!(merge_head_exists(&work2));
        w.conflict_abort(repo2, GitWriteApproval::granted())
            .expect("approved abort");
        assert!(
            !merge_head_exists(&work2),
            "merge --abort must clear MERGE_HEAD"
        );
        let body = fs::read_to_string(work2.join("a.txt")).unwrap();
        assert_eq!(body, "ours\n");

        let _ = fs::remove_dir_all(&work);
        let _ = fs::remove_dir_all(&work2);
    }

    #[test]
    fn std_write_conflict_continue_rebase_without_skip() {
        let root = unique_temp("rebase-conflict");
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "-b", "main"]);
        init_identity(&root);
        fs::write(root.join("a.txt"), "base\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "base"]);
        git(&root, &["checkout", "-b", "topic"]);
        fs::write(root.join("a.txt"), "topic\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "topic"]);
        git(&root, &["checkout", "main"]);
        fs::write(root.join("a.txt"), "mainline\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "mainline"]);
        git(&root, &["checkout", "topic"]);
        let rebase = Command::new("git")
            .args(["rebase", "main"])
            .current_dir(&root)
            .output()
            .expect("rebase");
        assert!(!rebase.status.success(), "expected rebase conflict");

        let repo = root.to_str().unwrap();
        let w = StdGitWrite::new();
        fs::write(root.join("a.txt"), "rebased\n").unwrap();
        w.conflict_save(repo, "a.txt", GitWriteApproval::granted())
            .expect("save rebase path");
        w.conflict_continue(repo, GitWriteApproval::granted())
            .expect("rebase --continue");
        assert!(
            !root.join(".git").join("rebase-merge").exists()
                && !root.join(".git").join("rebase-apply").exists(),
            "rebase --continue must finish without --skip"
        );
        let st = Command::new("git")
            .args(["-C", repo, "status", "--porcelain"])
            .output()
            .unwrap();
        assert!(
            String::from_utf8_lossy(&st.stdout).trim().is_empty(),
            "rebase continue should leave a clean worktree"
        );

        let _ = fs::remove_dir_all(&root);
    }

    fn make_rebase_conflict() -> PathBuf {
        let root = unique_temp("rebase-skip-conflict");
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "-b", "main"]);
        init_identity(&root);
        fs::write(root.join("a.txt"), "base\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "base"]);
        git(&root, &["checkout", "-b", "topic"]);
        fs::write(root.join("a.txt"), "topic\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "topic"]);
        git(&root, &["checkout", "main"]);
        fs::write(root.join("a.txt"), "mainline\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "mainline"]);
        git(&root, &["checkout", "topic"]);
        let rebase = Command::new("git")
            .args(["rebase", "main"])
            .current_dir(&root)
            .output()
            .expect("rebase");
        assert!(!rebase.status.success(), "expected rebase conflict");
        root
    }

    fn rebase_in_progress(repo: &Path) -> bool {
        repo.join(".git").join("rebase-merge").exists()
            || repo.join(".git").join("rebase-apply").exists()
    }

    #[test]
    fn std_write_conflict_skip_rebase_when_approved() {
        let root = make_rebase_conflict();
        let repo = root.to_str().unwrap();
        let w = StdGitWrite::new();

        w.conflict_skip(repo, GitWriteApproval::denied())
            .expect_err("denied skip must not mutate");
        assert!(rebase_in_progress(&root));

        w.conflict_skip(repo, GitWriteApproval::granted())
            .expect("approved rebase --skip");
        assert!(
            !rebase_in_progress(&root),
            "rebase --skip must finish the in-progress rebase"
        );
        let body = fs::read_to_string(root.join("a.txt")).unwrap();
        assert_eq!(
            body, "mainline\n",
            "skip must drop the topic patch, not add+continue it"
        );
        let log = Command::new("git")
            .args(["-C", repo, "log", "--oneline"])
            .output()
            .unwrap();
        let history = String::from_utf8_lossy(&log.stdout);
        assert!(
            !history.contains("topic"),
            "skipped commit must not remain: {history}"
        );

        let _ = fs::remove_dir_all(&root);
    }

    #[test]
    fn std_write_conflict_skip_refuses_when_not_skippable() {
        let w = StdGitWrite::new();
        let clean = unique_temp("skip-clean");
        fs::create_dir_all(&clean).unwrap();
        git(&clean, &["init", "-b", "main"]);
        init_identity(&clean);
        fs::write(clean.join("a.txt"), "ok\n").unwrap();
        git(&clean, &["add", "a.txt"]);
        git(&clean, &["commit", "-m", "ok"]);
        let clean_repo = clean.to_str().unwrap();
        let missing = w
            .conflict_skip(clean_repo, GitWriteApproval::granted())
            .expect_err("skip without in-progress must fail");
        assert!(
            missing.to_string().contains("no in-progress")
                || missing.to_string().contains("cannot be skipped"),
            "missing skip must fail honestly: {missing}"
        );

        let merge = make_merge_conflict();
        let merge_repo = merge.to_str().unwrap();
        let refused = w
            .conflict_skip(merge_repo, GitWriteApproval::granted())
            .expect_err("merge skip must fail");
        assert!(
            refused.to_string().contains("cannot be skipped"),
            "merge skip must not fall back to continue/abort: {refused}"
        );
        assert!(
            merge_head_exists(&merge),
            "refused skip must leave MERGE_HEAD"
        );

        w.conflict_abort(merge_repo, GitWriteApproval::granted())
            .expect("abort still works after refused skip");
        assert!(!merge_head_exists(&merge));

        let _ = fs::remove_dir_all(&clean);
        let _ = fs::remove_dir_all(&merge);
    }
}
