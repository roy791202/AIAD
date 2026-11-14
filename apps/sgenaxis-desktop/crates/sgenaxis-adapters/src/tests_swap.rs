//! Contract / swap tests — Fake ↔ Std behind `dyn` Ports (source-level; needs cargo).

use sgenaxis_ports::{FileSystemPort, GitPort, PathPort, ProcessPort};

use crate::compose::{ensure_app_config_dir, BoxedPorts, HostPorts};
use crate::fake::{status_with_modified, FakeFileSystem, FakeGit, FakePath, FakeProcess};
use crate::{StdFileSystem, StdPath};

/// Generic helper: any FileSystemPort can round-trip a write/read.
fn roundtrip_text(fs: &dyn FileSystemPort, path: &str, body: &str) {
    fs.write_atomic(path, body.as_bytes()).expect("write");
    assert!(fs.exists(path).unwrap());
    assert_eq!(fs.read_to_string(path).unwrap(), body);
}

#[test]
fn fake_filesystem_roundtrip() {
    let fs = FakeFileSystem::new();
    roundtrip_text(&fs, "/proj/readme.md", "hello ports");
}

#[test]
fn fake_and_std_path_both_implement_path_port() {
    let fake: &dyn PathPort = &FakePath::windows_style();
    let cfg = fake.config_dir("SGenAxis").unwrap();
    assert!(cfg.contains("SGenAxis"));
    assert!(cfg.contains('\\') || cfg.contains("fake"));

    let joined = fake.join(r"C:\base", &["a", "b"]);
    assert_eq!(joined, r"C:\base\a\b");
    assert_eq!(fake.normalize(r"C:/base\a/"), r"C:\base\a");

    let stdp: &dyn PathPort = &StdPath::new();
    let std_cfg = stdp.config_dir("SGenAxis").expect("std config_dir");
    // Windows: expect LOCALAPPDATA-style or AppData\Local
    #[cfg(windows)]
    {
        assert!(
            std_cfg.to_lowercase().contains("sgenaxis"),
            "unexpected config dir: {std_cfg}"
        );
        assert!(
            std_cfg.contains('\\') || std_cfg.contains('/'),
            "path should have a separator: {std_cfg}"
        );
    }
    #[cfg(not(windows))]
    {
        assert!(std_cfg.contains("SGenAxis") || std_cfg.contains("sgenaxis"));
    }
}

#[test]
fn swap_filesystem_behind_boxed_ports() {
    // Start with fake — use-case only sees dyn FileSystemPort.
    let mut ports = BoxedPorts::fake();
    roundtrip_text(ports.fs.as_ref(), "/mem/a.txt", "via-fake");

    // Swap FS implementation behind the same dyn slot.
    let replacement = FakeFileSystem::new();
    replacement.seed("/mem/b.txt", b"seeded");
    ports.fs = Box::new(replacement);
    assert_eq!(
        ports.fs.read_to_string("/mem/b.txt").unwrap(),
        "seeded"
    );

    // Prove StdFileSystem is also a FileSystemPort (unique temp file — no shared path races).
    let std_fs = StdFileSystem::new();
    let dir = std::env::temp_dir().join(format!(
        "sgenaxis-pd-adapt-01-{}",
        std::process::id()
    ));
    let _ = std::fs::create_dir_all(&dir);
    let file = dir.join("swap.txt");
    let path = file.to_string_lossy().into_owned();
    roundtrip_text(&std_fs as &dyn FileSystemPort, &path, "via-std");
    let _ = std::fs::remove_dir_all(&dir);
}

#[test]
fn ensure_app_config_dir_works_with_fake_or_std_path() {
    let fs = FakeFileSystem::new();
    let path = FakePath::new();
    let dir = ensure_app_config_dir(&path, &fs, "SGenAxis").unwrap();
    assert!(dir.ends_with("SGenAxis") || dir.contains("SGenAxis"));
    assert!(fs.exists(&dir).unwrap());

    // Same helper with StdPath + FakeFileSystem (path string only — no real mkdir needed
    // if we only call path.config_dir; create_dir_all on fake is in-memory).
    let std_path = StdPath::new();
    let dir2 = ensure_app_config_dir(&std_path, &fs, "SGenAxis").unwrap();
    assert!(dir2.to_lowercase().contains("sgenaxis"));
}

#[test]
fn fake_process_start_finish_cancel() {
    let mut proc = FakeProcess::new();
    let id = proc.start("echo", &["hi"], None).unwrap();
    assert_eq!(proc.try_wait(id).unwrap(), None);
    proc.push_stdout(id, "hi\n").unwrap();
    let out = proc.try_read(id).unwrap();
    assert_eq!(out.stdout, "hi\n");
    proc.finish(id, 0).unwrap();
    assert_eq!(proc.try_wait(id).unwrap(), Some(0));

    let id2 = proc.start("slow", &[], None).unwrap();
    proc.cancel(id2).unwrap();
    assert_eq!(proc.try_wait(id2).unwrap(), Some(-1));
}

#[test]
fn fake_git_status_log_diff() {
    let git = FakeGit::new();
    git.set_status("/repo", status_with_modified("main", "src/lib.rs"));
    git.set_log(
        "/repo",
        vec![sgenaxis_ports::GitCommit {
            hash: "abc123".into(),
            subject: "init".into(),
            ..Default::default()
        }],
    );
    git.set_diff("/repo", "diff --git a/src/lib.rs\n");

    let st = git.status("/repo").unwrap();
    assert_eq!(st.branch.as_deref(), Some("main"));
    assert_eq!(st.entries.len(), 1);

    let log = git.log("/repo", 10).unwrap();
    assert_eq!(log[0].hash, "abc123");
    assert!(git.diff("/repo", None).unwrap().contains("lib.rs"));
}

#[test]
fn host_ports_fake_bundle_composes() {
    let host = HostPorts::fake();
    let _fs: &dyn FileSystemPort = &host.fs;
    let _path: &dyn PathPort = &host.path;
    let _git: &dyn GitPort = &host.git;
    let _ = &host.git_write;
    assert!(host.path.config_dir("App").unwrap().contains("App"));
}

#[test]
fn host_ports_std_bundle_available() {
    let host = HostPorts::std_fs_path_process_fake_git();
    let cfg = host.path.config_dir("SGenAxis").unwrap();
    assert!(!cfg.is_empty());
    let _proc: &dyn ProcessPort = &host.process;
}
