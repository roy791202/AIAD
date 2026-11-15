//! PD-GIT-SET-UPSTREAM-01 — BDD TDD lock for [`GitWritePort::set_upstream`].
//!
//! `git branch --set-upstream-to=<remote>/<branch> -- <local>` only; never
//! fetch / pull / push / checkout / `--unset-upstream`.

use sgenaxis_ports::{GitWriteApproval, GitWritePort, PortError};

use crate::fake::FakeGitWrite;
use crate::git_write::{GatedGitWrite, GIT_WRITE_GATED_MSG, GIT_WRITE_NOT_APPROVED_MSG};

fn seed_fake(w: &FakeGitWrite) {
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
}

#[test]
fn pd_git_set_upstream_01_1_denied_no_upstream() {
    let w = FakeGitWrite::new();
    seed_fake(&w);

    let err = w
        .set_upstream(
            "/r",
            "origin",
            "main",
            "main",
            GitWriteApproval::denied(),
        )
        .expect_err("PD-GIT-SET-UPSTREAM-01-1");
    assert!(matches!(err, PortError::PermissionDenied(ref m) if m == GIT_WRITE_NOT_APPROVED_MSG));
    assert!(w.last_set_upstream("/r").is_none());
    assert!(w.upstream_of("/r", "main").is_none());
    assert_eq!(w.push_count("/r"), 0);
    assert!(w.last_fetch("/r").is_none());
    assert!(w.switched_branch("/r").is_none());

    let gated = GatedGitWrite::new();
    let gated_err = gated.set_upstream(
        "/any",
        "origin",
        "main",
        "main",
        GitWriteApproval::granted(),
    );
    assert!(matches!(gated_err, Err(PortError::PermissionDenied(ref m)) if m == GIT_WRITE_GATED_MSG));

    #[cfg(feature = "std-adapters")]
    {
        use std::fs;
        use std::path::{Path, PathBuf};
        use std::process::Command;
        use std::sync::atomic::{AtomicU64, Ordering};
        use std::time::{SystemTime, UNIX_EPOCH};

        use crate::StdGitWrite;

        static SEQ: AtomicU64 = AtomicU64::new(0);

        fn unique_temp(label: &str) -> PathBuf {
            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            let n = SEQ.fetch_add(1, Ordering::Relaxed);
            std::env::temp_dir().join(format!("pd-git-set-upstream-01-{label}-{nanos}-{n}"))
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
            git(repo, &["config", "user.email", "pd-set-upstream@test.local"]);
            git(repo, &["config", "user.name", "PD Set Upstream"]);
            git(repo, &["config", "commit.gpgsign", "false"]);
            git(repo, &["config", "core.autocrlf", "false"]);
        }

        let root = unique_temp("denied");
        fs::create_dir_all(&root).unwrap();
        let bare = root.join("remote.git");
        let work = root.join("work");
        fs::create_dir_all(&work).unwrap();
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
            &[
                "remote",
                "add",
                "origin",
                bare.to_str().expect("utf8 path"),
            ],
        );
        git(&work, &["push", "-u", "origin", "main"]);
        git(&work, &["branch", "--unset-upstream", "--", "main"]);

        let repo = work.to_str().unwrap();
        let head_before = Command::new("git")
            .args(["-C", repo, "rev-parse", "HEAD"])
            .output()
            .unwrap();
        let head_before = String::from_utf8_lossy(&head_before.stdout)
            .trim()
            .to_string();

        let writer = StdGitWrite::new();
        writer
            .set_upstream(repo, "origin", "main", "main", GitWriteApproval::denied())
            .expect_err("denied must not set upstream");
        let up = Command::new("git")
            .args(["-C", repo, "rev-parse", "--abbrev-ref", "main@{upstream}"])
            .output()
            .unwrap();
        assert!(!up.status.success(), "denied must leave main without upstream");

        let head_after = Command::new("git")
            .args(["-C", repo, "rev-parse", "HEAD"])
            .output()
            .unwrap();
        assert_eq!(
            head_before,
            String::from_utf8_lossy(&head_after.stdout).trim()
        );
        let _ = fs::remove_dir_all(&root);
    }
}

#[test]
fn pd_git_set_upstream_01_2_granted_tracks_without_fetch() {
    let w = FakeGitWrite::new();
    seed_fake(&w);

    w.set_upstream(
        "/r",
        "origin",
        "main",
        "",
        GitWriteApproval::granted(),
    )
    .expect("PD-GIT-SET-UPSTREAM-01-2");
    assert_eq!(
        w.upstream_of("/r", "main"),
        Some(("origin".into(), "main".into()))
    );
    assert_eq!(
        w.last_set_upstream("/r"),
        Some(("main".into(), "origin".into(), "main".into()))
    );
    assert_eq!(w.push_count("/r"), 0);
    assert!(w.last_fetch("/r").is_none());
    assert!(w.switched_branch("/r").is_none());

    #[cfg(feature = "std-adapters")]
    {
        use std::fs;
        use std::path::{Path, PathBuf};
        use std::process::Command;
        use std::sync::atomic::{AtomicU64, Ordering};
        use std::time::{SystemTime, UNIX_EPOCH};

        use crate::StdGitWrite;

        static SEQ: AtomicU64 = AtomicU64::new(0);

        fn unique_temp(label: &str) -> PathBuf {
            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            let n = SEQ.fetch_add(1, Ordering::Relaxed);
            std::env::temp_dir().join(format!("pd-git-set-upstream-01-{label}-{nanos}-{n}"))
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
            git(repo, &["config", "user.email", "pd-set-upstream@test.local"]);
            git(repo, &["config", "user.name", "PD Set Upstream"]);
            git(repo, &["config", "commit.gpgsign", "false"]);
            git(repo, &["config", "core.autocrlf", "false"]);
        }

        fn upstream_of(repo: &str, local: &str) -> String {
            let spec = format!("{local}@{{upstream}}");
            let out = Command::new("git")
                .args(["-C", repo, "rev-parse", "--abbrev-ref", &spec])
                .output()
                .expect("rev-parse upstream");
            String::from_utf8_lossy(&out.stdout).trim().to_string()
        }

        let root = unique_temp("granted");
        fs::create_dir_all(&root).unwrap();
        let bare = root.join("remote.git");
        let work = root.join("work");
        fs::create_dir_all(&work).unwrap();
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
            &[
                "remote",
                "add",
                "origin",
                bare.to_str().expect("utf8 path"),
            ],
        );
        git(&work, &["push", "-u", "origin", "main"]);
        git(&work, &["branch", "--unset-upstream", "--", "main"]);
        git(&work, &["branch", "--", "topic"]);

        let repo = work.to_str().unwrap();
        let head_before = Command::new("git")
            .args(["-C", repo, "rev-parse", "--abbrev-ref", "HEAD"])
            .output()
            .unwrap();
        let head_before = String::from_utf8_lossy(&head_before.stdout)
            .trim()
            .to_string();
        let origin_main_before = Command::new("git")
            .args(["-C", repo, "rev-parse", "origin/main"])
            .output()
            .unwrap();
        let origin_main_before = String::from_utf8_lossy(&origin_main_before.stdout)
            .trim()
            .to_string();

        let writer = StdGitWrite::new();
        writer
            .set_upstream(repo, "origin", "main", "", GitWriteApproval::granted())
            .expect("approved set-upstream");
        assert_eq!(upstream_of(repo, "main"), "origin/main");
        assert_eq!(
            head_before,
            String::from_utf8_lossy(
                &Command::new("git")
                    .args(["-C", repo, "rev-parse", "--abbrev-ref", "HEAD"])
                    .output()
                    .unwrap()
                    .stdout
            )
            .trim()
        );
        let origin_main_after = Command::new("git")
            .args(["-C", repo, "rev-parse", "origin/main"])
            .output()
            .unwrap();
        assert_eq!(
            origin_main_before,
            String::from_utf8_lossy(&origin_main_after.stdout).trim()
        );
        let _ = fs::remove_dir_all(&root);
    }
}

#[test]
fn pd_git_set_upstream_01_3_missing_remote_and_invalid_names_fail() {
    let w = FakeGitWrite::new();
    seed_fake(&w);

    let ghost = w
        .set_upstream("/r", "ghost", "main", "main", GitWriteApproval::granted())
        .expect_err("unknown remote");
    assert!(
        matches!(ghost, PortError::Git(ref m) if m.to_ascii_lowercase().contains("no such remote"))
    );
    assert!(w.configured_remotes("/r").iter().all(|(n, _)| n != "ghost"));

    let missing_ref = w
        .set_upstream("/r", "origin", "nope", "main", GitWriteApproval::granted())
        .expect_err("missing tracking ref");
    assert!(matches!(
        missing_ref,
        PortError::Git(ref m) if m.to_ascii_lowercase().contains("not found")
    ));

    let missing_local = w
        .set_upstream(
            "/r",
            "origin",
            "main",
            "missing-local",
            GitWriteApproval::granted(),
        )
        .expect_err("missing local branch");
    assert!(matches!(
        missing_local,
        PortError::Git(ref m) if m.to_ascii_lowercase().contains("not found")
    ));
    assert!(!w.created_branches("/r").iter().any(|b| b == "missing-local"));

    let empty_remote = w.set_upstream("/r", "  ", "main", "main", GitWriteApproval::granted());
    assert!(matches!(empty_remote, Err(PortError::Other(_))));

    let flag_remote = w.set_upstream("/r", "-f", "main", "main", GitWriteApproval::granted());
    assert!(matches!(flag_remote, Err(PortError::Other(_))));

    let unset_as_branch = w.set_upstream(
        "/r",
        "origin",
        "--unset-upstream",
        "main",
        GitWriteApproval::granted(),
    );
    assert!(matches!(unset_as_branch, Err(PortError::Other(_))));

    assert!(w.upstream_of("/r", "main").is_none());

    #[cfg(feature = "std-adapters")]
    {
        use std::fs;
        use std::path::{Path, PathBuf};
        use std::process::Command;
        use std::sync::atomic::{AtomicU64, Ordering};
        use std::time::{SystemTime, UNIX_EPOCH};

        use crate::StdGitWrite;

        static SEQ: AtomicU64 = AtomicU64::new(0);

        fn unique_temp(label: &str) -> PathBuf {
            let nanos = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0);
            let n = SEQ.fetch_add(1, Ordering::Relaxed);
            std::env::temp_dir().join(format!("pd-git-set-upstream-01-{label}-{nanos}-{n}"))
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
            git(repo, &["config", "user.email", "pd-set-upstream@test.local"]);
            git(repo, &["config", "user.name", "PD Set Upstream"]);
            git(repo, &["config", "commit.gpgsign", "false"]);
            git(repo, &["config", "core.autocrlf", "false"]);
        }

        let root = unique_temp("invalid");
        fs::create_dir_all(&root).unwrap();
        let bare = root.join("remote.git");
        let work = root.join("work");
        fs::create_dir_all(&work).unwrap();
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
            &[
                "remote",
                "add",
                "origin",
                bare.to_str().expect("utf8 path"),
            ],
        );
        git(&work, &["push", "-u", "origin", "main"]);

        let repo = work.to_str().unwrap();
        let writer = StdGitWrite::new();

        let ghost = writer
            .set_upstream(repo, "ghost", "main", "main", GitWriteApproval::granted())
            .expect_err("std unknown remote");
        assert!(
            ghost.to_string().to_ascii_lowercase().contains("no such remote")
                || ghost.to_string().contains("ghost")
        );
        let remotes = Command::new("git")
            .args(["-C", repo, "remote"])
            .output()
            .unwrap();
        assert!(
            !String::from_utf8_lossy(&remotes.stdout)
                .lines()
                .any(|l| l.trim() == "ghost")
        );

        writer
            .set_upstream(repo, "origin", "nope", "main", GitWriteApproval::granted())
            .expect_err("std missing tracking ref");

        writer
            .set_upstream(
                repo,
                "origin",
                "main",
                "missing-local",
                GitWriteApproval::granted(),
            )
            .expect_err("std missing local");

        let _ = fs::remove_dir_all(&root);
    }
}