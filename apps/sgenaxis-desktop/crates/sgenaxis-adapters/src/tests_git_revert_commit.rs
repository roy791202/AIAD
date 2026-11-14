//! PD-GIT-REVERT-COMMIT-01 — approval-gated `git revert --no-edit -- <sha>`.

use sgenaxis_ports::{GitWriteApproval, GitWritePort, PortError};

use crate::fake::FakeGitWrite;
use crate::git_write::GIT_WRITE_NOT_APPROVED_MSG;

#[cfg(feature = "std-adapters")]
use crate::StdGitWrite;

#[test]
fn fake_revert_denied_without_approval_no_new_commit() {
    let w = FakeGitWrite::new();
    let repo = "/r";
    w.commit(repo, "one", GitWriteApproval::granted()).unwrap();
    w.commit(repo, "two", GitWriteApproval::granted()).unwrap();
    let before = w.local_commit_count(repo);
    let target = w.commit_hashes(repo)[0].clone();
    let err = w
        .revert_commit(repo, &target, GitWriteApproval::denied())
        .expect_err("denied");
    assert!(matches!(err, PortError::PermissionDenied(ref m) if m == GIT_WRITE_NOT_APPROVED_MSG));
    assert_eq!(w.local_commit_count(repo), before);
    assert!(w.last_revert_sha(repo).is_none());
}

#[test]
fn fake_revert_approved_records_revert_commit() {
    let w = FakeGitWrite::new();
    let repo = "/r";
    w.commit(repo, "feat: add", GitWriteApproval::granted()).unwrap();
    w.commit(repo, "feat: tweak", GitWriteApproval::granted()).unwrap();
    let target = w.commit_hashes(repo)[0].clone();
    w.revert_commit(repo, &target, GitWriteApproval::granted())
        .expect("approved revert");
    assert_eq!(w.local_commit_count(repo), 3);
    assert_eq!(w.last_revert_sha(repo).as_deref(), Some(target.as_str()));
    assert_eq!(
        w.last_commit_message(repo).as_deref(),
        Some("Revert \"feat: add\"")
    );
}

#[test]
fn fake_revert_missing_sha_fails_honestly() {
    let w = FakeGitWrite::new();
    let repo = "/r";
    w.commit(repo, "seed", GitWriteApproval::granted()).unwrap();
    let before = w.local_commit_count(repo);
    w.revert_commit(repo, "  ", GitWriteApproval::granted())
        .expect_err("empty sha");
    w.revert_commit(repo, "deadbeefcafe", GitWriteApproval::granted())
        .expect_err("unknown sha");
    assert_eq!(w.local_commit_count(repo), before);
}

#[test]
fn fake_revert_merge_commit_fails_without_invented_m1() {
    let w = FakeGitWrite::new();
    let repo = "/r";
    w.commit(repo, "base", GitWriteApproval::granted()).unwrap();
    let merge = w.commit_hashes(repo)[0].clone();
    w.mark_merge_commit(repo, merge.clone());
    let err = w
        .revert_commit(repo, &merge, GitWriteApproval::granted())
        .expect_err("merge");
    assert!(matches!(err, PortError::Git(ref m) if m.contains("mainline")));
    assert_eq!(w.local_commit_count(repo), 1);
}

#[test]
fn fake_revert_failure_redacts_credentials() {
    let w = FakeGitWrite::new();
    let repo = "/r";
    w.commit(repo, "x", GitWriteApproval::granted()).unwrap();
    let target = w.commit_hashes(repo)[0].clone();
    w.fail_next_revert(
        repo,
        "fatal: https://alice:sekretP@host.example/repo.git failed",
    );
    let err = w
        .revert_commit(repo, &target, GitWriteApproval::granted())
        .expect_err("injected");
    let rendered = err.to_string();
    assert!(!rendered.contains("sekretP"), "credential leaked: {rendered}");
    assert_eq!(w.local_commit_count(repo), 1);
}

#[cfg(feature = "std-adapters")]
mod std_revert_temp {
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
        std::env::temp_dir().join(format!("sgenaxis-pd-git-revert-{label}-{nanos}-{n}"))
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
        git(repo, &["config", "user.email", "pd-revert@test.local"]);
        git(repo, &["config", "user.name", "PD Revert Test"]);
        git(repo, &["config", "commit.gpgsign", "false"]);
        git(repo, &["config", "core.autocrlf", "false"]);
    }

    fn rev_parse(repo: &str, rev: &str) -> String {
        let out = Command::new("git")
            .args(["-C", repo, "rev-parse", rev])
            .output()
            .expect("rev-parse");
        assert!(out.status.success());
        String::from_utf8_lossy(&out.stdout).trim().to_string()
    }

    fn make_linear_repo() -> (PathBuf, String, String) {
        let root = unique_temp("linear");
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "-b", "main"]);
        init_identity(&root);
        fs::write(root.join("a.txt"), "1\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "first"]);
        fs::write(root.join("b.txt"), "feat\n").unwrap();
        git(&root, &["add", "b.txt"]);
        git(&root, &["commit", "-m", "second"]);
        let repo = root.to_str().unwrap().to_string();
        // Revert the tip commit (touches only `b.txt`) — avoids same-file conflicts.
        let target = rev_parse(&repo, "HEAD");
        let head = target.clone();
        (root, target, head)
    }

    fn make_merge_commit_repo() -> (PathBuf, String) {
        let root = unique_temp("merge");
        fs::create_dir_all(&root).unwrap();
        git(&root, &["init", "-b", "main"]);
        init_identity(&root);
        fs::write(root.join("a.txt"), "base\n").unwrap();
        git(&root, &["add", "a.txt"]);
        git(&root, &["commit", "-m", "base"]);
        git(&root, &["branch", "feat"]);
        git(&root, &["checkout", "feat"]);
        fs::write(root.join("b.txt"), "feat\n").unwrap();
        git(&root, &["add", "b.txt"]);
        git(&root, &["commit", "-m", "on feat"]);
        git(&root, &["checkout", "main"]);
        git(&root, &["merge", "--no-ff", "-m", "merge feat", "feat"]);
        let repo = root.to_str().unwrap().to_string();
        let merge = rev_parse(&repo, "HEAD");
        (root, merge)
    }

    #[test]
    fn std_revert_denied_leaves_head_unchanged() {
        let (root, first, head_before) = make_linear_repo();
        let repo = root.to_str().unwrap();
        let w = StdGitWrite::new();
        let err = w
            .revert_commit(repo, &first, GitWriteApproval::denied())
            .expect_err("denied");
        assert!(matches!(err, PortError::PermissionDenied(_)));
        assert_eq!(rev_parse(repo, "HEAD"), head_before);
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn std_revert_approved_creates_new_commit() {
        let (root, first, head_before) = make_linear_repo();
        let repo = root.to_str().unwrap();
        let w = StdGitWrite::new();
        w.revert_commit(repo, &first, GitWriteApproval::granted())
            .expect("revert ok");
        let head_after = rev_parse(repo, "HEAD");
        assert_ne!(head_before, head_after);
        let log = Command::new("git")
            .args(["-C", repo, "log", "-1", "--format=%s"])
            .output()
            .unwrap();
        let subject = String::from_utf8_lossy(&log.stdout);
        assert!(
            subject.contains("Revert") && subject.contains("second"),
            "expected revert commit subject: {subject}"
        );
        let out = Command::new("git")
            .args(["-C", repo, "status", "--porcelain"])
            .output()
            .unwrap();
        assert!(
            out.stdout.is_empty(),
            "revert must land as a commit, not --no-commit index-only"
        );
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn std_revert_unknown_sha_and_flags_fail_honestly() {
        let (root, _first, head_before) = make_linear_repo();
        let repo = root.to_str().unwrap();
        let w = StdGitWrite::new();
        w.revert_commit(repo, "0000000000000000000000000000000000000000", GitWriteApproval::granted())
            .expect_err("missing");
        w.revert_commit(repo, "--force", GitWriteApproval::granted())
            .expect_err("flag sha");
        assert_eq!(rev_parse(repo, "HEAD"), head_before);
        let _ = fs::remove_dir_all(root);
    }

    #[test]
    fn std_revert_merge_commit_fails_without_m1() {
        let (root, merge) = make_merge_commit_repo();
        let repo = root.to_str().unwrap();
        let head_before = rev_parse(repo, "HEAD");
        let w = StdGitWrite::new();
        let err = w
            .revert_commit(repo, &merge, GitWriteApproval::granted())
            .expect_err("merge");
        assert!(matches!(err, PortError::Git(ref m) if m.contains("mainline")));
        assert_eq!(rev_parse(repo, "HEAD"), head_before);
        let _ = fs::remove_dir_all(root);
    }
}