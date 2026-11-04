//! PD-GIT-BOARD-SYNC-01 — Git workbench summary ↔ board snapshot read isolation.
//!
//! Under one fixture: `summarize_worktree` (status／log／diff) and
//! [`crate::board_live::load_board_file`] must not cross-contaminate. Read paths
//! never write (no force push; no new write semantics). Failures are classified
//! as `git`｜`board`｜`pollution`｜`write`.

use sgenaxis_adapters::{summarize_worktree, GitWorkbenchSummary};
use sgenaxis_ports::{FileSystemPort, GitPort, GitStatus, PortError};

use crate::board_live::{load_board_file, BoardSnapshot};
use crate::error::HostError;

/// Classified failure for Git↔board sync assertions (BDD failure taxonomy).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SyncFailKind {
    /// GitPort／summary path failed.
    Git(String),
    /// Board snapshot read／parse failed.
    Board(String),
    /// One read mutated the other side's observable state.
    Pollution(String),
    /// A purported read path performed a write／mkdir.
    WriteDetected(String),
}

impl SyncFailKind {
    /// Stable ASCII class label for tests／UI／reports.
    pub fn class(&self) -> &'static str {
        match self {
            SyncFailKind::Git(_) => "git",
            SyncFailKind::Board(_) => "board",
            SyncFailKind::Pollution(_) => "pollution",
            SyncFailKind::WriteDetected(_) => "write",
        }
    }

    pub fn detail(&self) -> &str {
        match self {
            SyncFailKind::Git(m)
            | SyncFailKind::Board(m)
            | SyncFailKind::Pollution(m)
            | SyncFailKind::WriteDetected(m) => m.as_str(),
        }
    }
}

impl std::fmt::Display for SyncFailKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{}: {}", self.class(), self.detail())
    }
}

impl std::error::Error for SyncFailKind {}

/// Paired views after an isolated dual-read under one fixture.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitBoardSyncViews {
    pub summary: GitWorkbenchSummary,
    pub board: BoardSnapshot,
}

/// Order of the two read operations (both must stay isolated).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SyncReadOrder {
    /// Git summary first, then board load.
    GitThenBoard,
    /// Board load first, then Git summary.
    BoardThenGit,
}

/// FS façade that rejects all writes — used so board load cannot mutate storage.
struct ReadOnlyFs<'a> {
    inner: &'a dyn FileSystemPort,
}

impl FileSystemPort for ReadOnlyFs<'_> {
    fn exists(&self, path: &str) -> Result<bool, PortError> {
        self.inner.exists(path)
    }

    fn read_to_string(&self, path: &str) -> Result<String, PortError> {
        self.inner.read_to_string(path)
    }

    fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
        self.inner.read(path)
    }

    fn write_atomic(&self, path: &str, _contents: &[u8]) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(format!(
            "PD-GIT-BOARD-SYNC-01: write forbidden on read path ({path})"
        )))
    }

    fn create_dir_all(&self, path: &str) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(format!(
            "PD-GIT-BOARD-SYNC-01: mkdir forbidden on read path ({path})"
        )))
    }

    fn is_file(&self, path: &str) -> Result<bool, PortError> {
        self.inner.is_file(path)
    }

    fn remove_file(&self, path: &str) -> Result<(), PortError> {
        Err(PortError::PermissionDenied(format!(
            "PD-GIT-BOARD-SYNC-01: remove_file forbidden on read path ({path})"
        )))
    }
}

fn map_git(err: PortError) -> SyncFailKind {
    SyncFailKind::Git(err.to_string())
}

fn map_board(err: HostError) -> SyncFailKind {
    match err {
        HostError::Board(m) => SyncFailKind::Board(m),
        HostError::Port(PortError::PermissionDenied(m)) if m.contains("PD-GIT-BOARD-SYNC-01") => {
            SyncFailKind::WriteDetected(m)
        }
        HostError::Port(e) => SyncFailKind::Board(format!("port: {e}")),
        other => SyncFailKind::Board(other.to_string()),
    }
}

fn board_bytes(fs: &dyn FileSystemPort, path: &str) -> Result<Vec<u8>, SyncFailKind> {
    fs.read(path)
        .map_err(|e| SyncFailKind::Board(format!("fingerprint: {e}")))
}

fn git_baseline(
    git: &dyn GitPort,
    repo: &str,
    log_limit: usize,
) -> Result<(GitStatus, Vec<sgenaxis_ports::GitCommit>), SyncFailKind> {
    let status = git.status(repo).map_err(map_git)?;
    let log = git.log(repo, log_limit).map_err(map_git)?;
    Ok((status, log))
}

fn load_summary(
    git: &dyn GitPort,
    repo: &str,
    log_limit: usize,
) -> Result<GitWorkbenchSummary, SyncFailKind> {
    summarize_worktree(git, repo, log_limit).map_err(map_git)
}

fn load_board_ro(fs: &dyn FileSystemPort, board_path: &str) -> Result<BoardSnapshot, SyncFailKind> {
    let ro = ReadOnlyFs { inner: fs };
    load_board_file(&ro, board_path).map_err(map_board)
}

/// Load Git workbench summary and board snapshot under one fixture.
///
/// Asserts:
/// 1. Board file bytes are unchanged by the Git summary read.
/// 2. Git status／log are unchanged by the board read.
/// 3. Board load goes through a write-forbidding FS wrapper.
///
/// Does **not** call [`sgenaxis_ports::GitWritePort`] (no commit／push／force).
pub fn load_git_and_board_isolated(
    git: &dyn GitPort,
    fs: &dyn FileSystemPort,
    repo: &str,
    board_path: &str,
    log_limit: usize,
    order: SyncReadOrder,
) -> Result<GitBoardSyncViews, SyncFailKind> {
    let bytes_before = board_bytes(fs, board_path)?;
    let (status_before, log_before) = git_baseline(git, repo, log_limit)?;

    let (summary, board) = match order {
        SyncReadOrder::GitThenBoard => {
            let summary = load_summary(git, repo, log_limit)?;
            let after_git = board_bytes(fs, board_path)?;
            if after_git != bytes_before {
                return Err(SyncFailKind::Pollution(
                    "git summary mutated board file bytes".into(),
                ));
            }
            let board = load_board_ro(fs, board_path)?;
            (summary, board)
        }
        SyncReadOrder::BoardThenGit => {
            let board = load_board_ro(fs, board_path)?;
            let (status_mid, log_mid) = git_baseline(git, repo, log_limit)?;
            if status_mid != status_before || log_mid != log_before {
                return Err(SyncFailKind::Pollution(
                    "board load mutated git status/log".into(),
                ));
            }
            let summary = load_summary(git, repo, log_limit)?;
            (summary, board)
        }
    };

    let bytes_after = board_bytes(fs, board_path)?;
    if bytes_after != bytes_before {
        return Err(SyncFailKind::Pollution(
            "dual-read left board file bytes changed".into(),
        ));
    }
    let (status_after, log_after) = git_baseline(git, repo, log_limit)?;
    if status_after != status_before || log_after != log_before {
        return Err(SyncFailKind::Pollution(
            "dual-read left git status/log changed".into(),
        ));
    }
    if summary.writes_enabled {
        return Err(SyncFailKind::WriteDetected(
            "summarize_worktree reported writes_enabled=true".into(),
        ));
    }

    Ok(GitBoardSyncViews { summary, board })
}

#[cfg(test)]
mod tests {
    use sgenaxis_adapters::fake::status_with_modified;
    use sgenaxis_adapters::{FakeFileSystem, FakeGit, GatedGitWrite};
    use sgenaxis_ports::{
        GitCommit, GitStatus, GitStatusEntry, GitStatusKind, GitWriteApproval, GitWritePort,
    };

    use super::*;

    const BOARD_PATH: &str = "/fixture/docs/PROJECT-BOARD.html";
    const REPO: &str = "/fixture/repo";

    const MINI_BOARD: &str = r#"<!DOCTYPE html><html><body>
<script type="application/json" id="board-snapshot">
{
  "asOf": "2026-10-24T13:00:00+08:00",
  "version": "sync-fixture",
  "tasks": [
    {"id": "PD-A", "title": "Alpha", "zone": "yellow"},
    {"id": "PD-B", "title": "Beta", "zone": "blue"}
  ]
}
</script>
</body></html>"#;

    fn seed_fixture() -> (FakeGit, FakeFileSystem) {
        let git = FakeGit::new();
        git.set_status(
            REPO,
            GitStatus {
                branch: Some("main".into()),
                entries: vec![GitStatusEntry {
                    path: "src/a.rs".into(),
                    kind: GitStatusKind::Modified,
                }],
            },
        );
        git.set_log(
            REPO,
            vec![
                GitCommit {
                    hash: "aaa111".into(),
                    subject: "feat: a".into(),
                },
                GitCommit {
                    hash: "bbb222".into(),
                    subject: "chore: b".into(),
                },
            ],
        );
        git.set_diff(REPO, "diff --git a/src/a.rs\n+line\n");

        let fs = FakeFileSystem::new();
        fs.seed(BOARD_PATH, MINI_BOARD.as_bytes());
        (git, fs)
    }

    #[test]
    fn git_then_board_isolated_under_one_fixture() {
        let (git, fs) = seed_fixture();
        let writes_before = fs.write_count();
        let mkdirs_before = fs.mkdir_count();

        let views = load_git_and_board_isolated(
            &git,
            &fs,
            REPO,
            BOARD_PATH,
            2,
            SyncReadOrder::GitThenBoard,
        )
        .expect("isolated");

        assert_eq!(views.summary.branch.as_deref(), Some("main"));
        assert_eq!(views.summary.entry_count, 1);
        assert_eq!(views.summary.recent_commits.len(), 2);
        assert!(!views.summary.writes_enabled);
        assert_eq!(views.board.tasks.len(), 2);
        assert_eq!(views.board.tasks[0].id, "PD-A");
        assert_eq!(fs.write_count(), writes_before);
        assert_eq!(fs.mkdir_count(), mkdirs_before);
    }

    #[test]
    fn board_then_git_isolated_under_one_fixture() {
        let (git, fs) = seed_fixture();
        let views = load_git_and_board_isolated(
            &git,
            &fs,
            REPO,
            BOARD_PATH,
            1,
            SyncReadOrder::BoardThenGit,
        )
        .expect("isolated");
        assert_eq!(views.summary.recent_commits.len(), 1);
        assert_eq!(views.board.version.as_deref(), Some("sync-fixture"));
    }

    #[test]
    fn git_failure_classified_as_git() {
        let git = FakeGit::new();
        let fs = FakeFileSystem::new();
        fs.seed(BOARD_PATH, MINI_BOARD.as_bytes());
        let err = load_git_and_board_isolated(
            &git,
            &fs,
            REPO,
            BOARD_PATH,
            1,
            SyncReadOrder::GitThenBoard,
        )
        .expect_err("missing git data");
        assert_eq!(err.class(), "git");
    }

    #[test]
    fn board_failure_classified_as_board() {
        let (git, fs) = seed_fixture();
        let err = load_git_and_board_isolated(
            &git,
            &fs,
            REPO,
            "/missing/board.html",
            1,
            SyncReadOrder::BoardThenGit,
        )
        .expect_err("missing board");
        assert_eq!(err.class(), "board");
        assert!(err.detail().contains("not found") || err.detail().contains("fingerprint"));
    }

    #[test]
    fn fail_classes_are_distinct_labels() {
        assert_eq!(SyncFailKind::Git("x".into()).class(), "git");
        assert_eq!(SyncFailKind::Board("x".into()).class(), "board");
        assert_eq!(SyncFailKind::Pollution("x".into()).class(), "pollution");
        assert_eq!(SyncFailKind::WriteDetected("x".into()).class(), "write");
        assert!(SyncFailKind::Git("e".into())
            .to_string()
            .starts_with("git:"));
    }

    #[test]
    fn gated_write_still_blocked_no_new_write_semantics() {
        let w = GatedGitWrite::new();
        let err = w
            .commit(REPO, "nope", GitWriteApproval::granted())
            .expect_err("must gate");
        assert!(matches!(err, PortError::PermissionDenied(_)));
        // Isolation helper never opens GitWritePort — force push out of scope.
        let _ = status_with_modified("main", "x.rs");
    }

    #[test]
    fn parse_error_classified_as_board() {
        let git = FakeGit::new();
        git.set_status(REPO, status_with_modified("main", "z.rs"));
        git.set_log(REPO, vec![]);
        git.set_diff(REPO, "");
        let fs = FakeFileSystem::new();
        fs.seed(
            BOARD_PATH,
            br#"<!DOCTYPE html><script type="application/json" id="board-snapshot">{bad</script>"#,
        );
        let err = load_git_and_board_isolated(
            &git,
            &fs,
            REPO,
            BOARD_PATH,
            1,
            SyncReadOrder::GitThenBoard,
        )
        .expect_err("bad json");
        assert_eq!(err.class(), "board");
    }
}
