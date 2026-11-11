use std::sync::Mutex;

use sgenaxis_ports::{GitCommit, GitPort, GitStatus, GitStatusEntry, GitStatusKind, PortError};
use sgenaxis_work::{
    FakePathProbe, FakeWorkspaceStore, Project, RegisterOutcome, WorkError, WorkspaceService,
};

#[derive(Debug)]
struct RecordingGitPort {
    status_result: Result<GitStatus, PortError>,
    status_roots: Mutex<Vec<String>>,
    other_calls: Mutex<Vec<&'static str>>,
}

impl RecordingGitPort {
    fn returning(result: Result<GitStatus, PortError>) -> Self {
        Self {
            status_result: result,
            status_roots: Mutex::new(Vec::new()),
            other_calls: Mutex::new(Vec::new()),
        }
    }
}

impl GitPort for RecordingGitPort {
    fn status(&self, repo: &str) -> Result<GitStatus, PortError> {
        self.status_roots.lock().unwrap().push(repo.to_owned());
        self.status_result.clone()
    }

    fn log(&self, _repo: &str, _limit: usize) -> Result<Vec<GitCommit>, PortError> {
        self.other_calls.lock().unwrap().push("log");
        Ok(Vec::new())
    }

    fn diff(&self, _repo: &str, _pathspec: Option<&str>) -> Result<String, PortError> {
        self.other_calls.lock().unwrap().push("diff");
        Ok(String::new())
    }
}

fn workspace() -> WorkspaceService<FakePathProbe, FakeWorkspaceStore> {
    let probe = FakePathProbe::new();
    probe.seed_dir("/fixture/A");
    probe.seed_dir("/fixture/B");
    probe.seed_denied("/fixture/denied");
    probe.seed_alias("/FIXTURE/ALIAS", "/fixture/A");
    WorkspaceService::new(probe, FakeWorkspaceStore::new())
}

fn create_project(
    ws: &mut WorkspaceService<FakePathProbe, FakeWorkspaceStore>,
    path: &str,
) -> Project {
    match ws.register(path).expect("register fixture project") {
        RegisterOutcome::Created(project) | RegisterOutcome::Existing(project) => project,
    }
}

fn snapshot(
    ws: &WorkspaceService<FakePathProbe, FakeWorkspaceStore>,
) -> (usize, sgenaxis_work::WorkspaceProjection) {
    (
        ws.store_len().expect("store length"),
        ws.projection().expect("projection"),
    )
}

#[test]
fn no_git_capability_keeps_file_project_usable_and_does_not_mutate_workspace() {
    let mut ws = workspace();
    let project = create_project(&mut ws, "/fixture/A");
    let before = snapshot(&ws);

    assert_eq!(project.git_status(None), None);
    assert_eq!(snapshot(&ws), before);
    assert_eq!(before.0, 1);
    assert_eq!(before.1.selected_root.as_deref(), Some("/fixture/A"));
}

fn assert_status_error_is_preserved(expected: PortError) {
    let mut ws = workspace();
    let project = create_project(&mut ws, "/fixture/A");
    let before = snapshot(&ws);
    let git = RecordingGitPort::returning(Err(expected.clone()));

    assert_eq!(project.git_status(Some(&git)), Some(Err(expected)));
    assert_eq!(*git.status_roots.lock().unwrap(), vec!["/fixture/A"]);
    assert!(git.other_calls.lock().unwrap().is_empty());
    assert_eq!(snapshot(&ws), before);
}

#[test]
fn git_unavailable_error_is_preserved_without_classifying_fixture_text() {
    // This label models an unavailable-Git fixture; it is not an instruction
    // to infer capability from stderr or error text.
    assert_status_error_is_preserved(PortError::Git("fixture: executable unavailable".to_owned()));
}

#[test]
fn installed_no_repo_error_is_preserved_without_synthesizing_git_state() {
    // No branch or HEAD is supplied by this no-repository fixture.
    assert_status_error_is_preserved(PortError::Git("fixture: not a repository".to_owned()));
}

#[test]
fn permission_denied_status_error_is_preserved() {
    assert_status_error_is_preserved(PortError::PermissionDenied(
        "fixture: status denied".to_owned(),
    ));
}

fn assert_status_snapshot_is_returned_exactly(expected: GitStatus) {
    let mut ws = workspace();
    let project = create_project(&mut ws, "/fixture/A");
    let before = snapshot(&ws);
    let git = RecordingGitPort::returning(Ok(expected.clone()));

    assert_eq!(project.git_status(Some(&git)), Some(Ok(expected)));
    assert_eq!(*git.status_roots.lock().unwrap(), vec!["/fixture/A"]);
    assert!(git.other_calls.lock().unwrap().is_empty());
    assert_eq!(snapshot(&ws), before);
}

#[test]
fn successful_status_with_no_branch_preserves_exact_snapshot() {
    assert_status_snapshot_is_returned_exactly(GitStatus {
        branch: None,
        entries: vec![GitStatusEntry {
            path: "draft.txt".to_owned(),
            kind: GitStatusKind::Untracked,
        }],
        upstream: None,
    });
}

#[test]
fn successful_status_with_branch_preserves_exact_snapshot() {
    assert_status_snapshot_is_returned_exactly(GitStatus {
        branch: Some("fixture-branch".to_owned()),
        entries: Vec::new(),
        upstream: None,
    });
}

#[test]
fn duplicate_root_registration_reuses_project_without_changing_registry_or_selection() {
    let mut ws = workspace();
    let first = create_project(&mut ws, "/fixture/A");
    let before = snapshot(&ws);

    match ws.register("/FIXTURE/ALIAS").expect("register alias") {
        RegisterOutcome::Existing(existing) => assert_eq!(existing, first),
        RegisterOutcome::Created(_) => panic!("canonical alias must not create a second project"),
    }

    assert_eq!(snapshot(&ws), before);
    assert_eq!(before.0, 1);
}

#[test]
fn invalid_or_denied_root_registration_preserves_existing_project_and_selection() {
    let mut ws = workspace();
    let project = create_project(&mut ws, "/fixture/A");
    let before = snapshot(&ws);

    assert!(matches!(ws.register(""), Err(WorkError::InvalidPath(_))));
    assert_eq!(snapshot(&ws), before);
    assert!(matches!(
        ws.register("/fixture/denied"),
        Err(WorkError::PathNotAccessible(_))
    ));
    assert_eq!(snapshot(&ws), before);
    assert_eq!(ws.get_project(&project.id).unwrap(), Some(project));
}
