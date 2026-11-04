use std::sync::{mpsc, Arc, Mutex};

use sgenaxis_ports::{
    GitIndexCommitPort, GitOperationState, GitWriteApproval, IndexCommitError,
    IndexCommitFacts, IndexCommitFingerprint, IndexCommitObservation,
};

use crate::git_index_commit::{validate_facts, IndexCommitCoordinator, IndexCommitRequestDto};

#[derive(Default)]
struct RecordingGitIndexPort {
    facts: Mutex<Option<IndexCommitFacts>>,
    inspect_calls: Mutex<Vec<String>>,
    commit_calls: Mutex<Vec<(String, String, IndexCommitFingerprint, bool)>>,
    fail_next_commit: Mutex<Option<IndexCommitError>>,
    invocation_started: Mutex<bool>,
    exit_code: Mutex<Option<i32>>,
    omit_after: Mutex<bool>,
    diagnostic: Mutex<Option<String>>,
    block_commit: Mutex<Option<(mpsc::SyncSender<()>, mpsc::Receiver<()>)>>,
}

impl GitIndexCommitPort for RecordingGitIndexPort {
    fn inspect_index(&self, root: &str) -> Result<IndexCommitFacts, IndexCommitError> {
        self.inspect_calls.lock().unwrap().push(root.into());
        self.facts.lock().unwrap().clone().ok_or_else(|| IndexCommitError::Unreadable("no scripted facts".into()))
    }

    fn commit_index(
        &self,
        root: &str,
        message: &str,
        expected: &IndexCommitFingerprint,
        approval: GitWriteApproval,
    ) -> Result<IndexCommitObservation, IndexCommitError> {
        if let Some(error) = self.fail_next_commit.lock().unwrap().take() { return Err(error); }
        self.commit_calls.lock().unwrap().push((root.into(), message.into(), expected.clone(), approval.is_granted()));
        if let Some((entered, release)) = self.block_commit.lock().unwrap().take() {
            let _ = entered.send(());
            let _ = release.recv();
        }
        let mut after = self.facts.lock().unwrap().clone();
        if *self.omit_after.lock().unwrap() { after = None; }
        if let Some(facts) = after.as_mut() {
            facts.fingerprint.head_oid = Some("dddddddddddddddddddddddddddddddddddddddd".into());
        }
        let diagnostic = self.diagnostic.lock().unwrap().clone();
        if diagnostic.is_some() { after = None; }
        Ok(IndexCommitObservation {
            invocation_started: *self.invocation_started.lock().unwrap(),
            exit_code: *self.exit_code.lock().unwrap(),
            after,
            observed_parent_oid: expected.head_oid.clone(),
            observed_tree_oid: diagnostic.is_none().then(|| expected.index_tree_oid.clone()),
            diagnostic,
        })
    }
}

fn facts() -> IndexCommitFacts {
    IndexCommitFacts {
        fingerprint: IndexCommitFingerprint {
            repo_root: r"C:\fixture\repo".into(),
            project_root: r"C:\fixture\repo\app".into(),
            head_oid: Some("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".into()),
            index_tree_oid: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".into(),
            staged_paths: vec!["app/src/main.rs".into()],
        },
        index_nonempty: true,
        unmerged: false,
        operation: GitOperationState::None,
    }
}

fn coordinator(port: &Arc<RecordingGitIndexPort>) -> IndexCommitCoordinator {
    port.facts.lock().unwrap().replace(facts());
    *port.invocation_started.lock().unwrap() = true;
    *port.exit_code.lock().unwrap() = Some(0);
    IndexCommitCoordinator::new(port.clone())
}

#[test]
fn prepare_publishes_staged_index_preview_without_mutation() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("valid Index preview");
    assert_eq!(preview.fingerprint.staged_paths, vec!["app/src/main.rs"]);
    assert_eq!(preview.display_paths, vec!["app/src/main.rs"]);
    assert_eq!(port.commit_calls.lock().unwrap().len(), 0);
    assert_eq!(&*port.inspect_calls.lock().unwrap(), &[r"C:\fixture\repo\app"]);
}

#[test]
fn explicit_confirmation_commits_only_the_previewed_index_once() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    let request = IndexCommitRequestDto {
        preview_id: preview.preview_id.clone(),
        generation: preview.generation,
        message: " staged change ".into(),
        confirmed: true,
    };
    let result = host.commit(request.clone()).expect("observed commit");
    assert_eq!(result.state, "Committed");
    let calls = port.commit_calls.lock().unwrap();
    assert_eq!(calls.len(), 1);
    assert_eq!(calls[0].1, " staged change ");
    assert_eq!(calls[0].2, facts().fingerprint);
    assert!(calls[0].3, "approval is scoped to this single invocation");
    drop(calls);
    let replay = host.commit(request);
    assert!(replay.is_err(), "successful preview token is one-use");
}

#[test]
fn simultaneous_replay_of_the_same_preview_has_exactly_one_commit_invocation() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = Arc::new(coordinator(&port));
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    let (entered_tx, entered_rx) = mpsc::sync_channel(0);
    let (release_tx, release_rx) = mpsc::sync_channel(0);
    *port.block_commit.lock().unwrap() = Some((entered_tx, release_rx));
    let request = IndexCommitRequestDto {
        preview_id: preview.preview_id,
        generation: preview.generation,
        message: "message".into(),
        confirmed: true,
    };
    let first_host = Arc::clone(&host);
    let first_request = request.clone();
    let first = std::thread::spawn(move || first_host.commit(first_request));
    entered_rx.recv_timeout(std::time::Duration::from_secs(2)).expect("first request entered the commit port");
    let replay = host.commit(request).unwrap_err();
    assert_eq!(replay.code, "InvalidPreview");
    release_tx.send(()).expect("release scripted port");
    assert_eq!(first.join().unwrap().unwrap().state, "Committed");
    assert_eq!(port.commit_calls.lock().unwrap().len(), 1);
}

#[test]
fn unconfirmed_or_replayed_preview_never_invokes_commit() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    let denied = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id.clone(), generation: preview.generation,
        message: "message".into(), confirmed: false,
    }).unwrap_err();
    assert_eq!(denied.code, "ApprovalRequired");
    assert!(host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id, generation: preview.generation,
        message: "message".into(), confirmed: true,
    }).is_ok(), "a denied confirmation does not consume the preview");
    assert_eq!(port.commit_calls.lock().unwrap().len(), 1);
}

#[test]
fn stale_preview_is_invalidated_without_claiming_commit_consumption() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    let mut changed = facts();
    changed.fingerprint.head_oid = Some("cccccccccccccccccccccccccccccccccccccccc".into());
    port.facts.lock().unwrap().replace(changed);
    let stale = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id.clone(), generation: preview.generation,
        message: "message".into(), confirmed: true,
    }).unwrap_err();
    assert_eq!(stale.code, "StalePreview");
    assert!(!stale.mutation_started);
    assert!(stale.requires_new_preview, "stale preview is invalidated, but no commit was attempted");
    assert_eq!(port.commit_calls.lock().unwrap().len(), 0);
    let replay = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id, generation: preview.generation,
        message: "message".into(), confirmed: true,
    }).unwrap_err();
    assert_eq!(replay.code, "InvalidPreview");
}

#[test]
fn pre_invocation_failure_keeps_preview_retryable() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    *port.fail_next_commit.lock().unwrap() = Some(IndexCommitError::Unavailable("scripted pre-invocation failure".into()));
    let request = IndexCommitRequestDto {
        preview_id: preview.preview_id,
        generation: preview.generation,
        message: "message".into(),
        confirmed: true,
    };
    let failed = host.commit(request.clone()).unwrap_err();
    assert_eq!(failed.code, "Unavailable");
    assert!(!failed.mutation_started);
    assert!(!failed.requires_new_preview);
    assert_eq!(host.commit(request).unwrap().state, "Committed", "pre-invocation failure retains the preview for retry");
    assert_eq!(port.commit_calls.lock().unwrap().len(), 1);
}

#[test]
fn repository_lock_reports_busy_without_consuming_preview() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    let request = IndexCommitRequestDto {
        preview_id: preview.preview_id,
        generation: preview.generation,
        message: "message".into(),
        confirmed: true,
    };
    *port.fail_next_commit.lock().unwrap() = Some(IndexCommitError::Unavailable("seed the per-repository lock without invoking commit".into()));
    assert_eq!(host.commit(request.clone()).unwrap_err().code, "Unavailable");
    let repo_lock = host.state.lock().unwrap().repo_locks
        .get(r"C:\fixture\repo").expect("per-repository lock").clone();
    let held = repo_lock.lock().unwrap();
    let busy = host.commit(request.clone()).unwrap_err();
    assert_eq!(busy.code, "Busy");
    assert!(!busy.mutation_started);
    assert!(port.commit_calls.lock().unwrap().is_empty());
    drop(held);
    assert_eq!(host.commit(request).unwrap().state, "Committed");
    assert_eq!(port.commit_calls.lock().unwrap().len(), 1);
}

#[test]
fn legacy_write_route_is_not_used_by_index_route() {
    // Compile-time boundary assertion: the new coordinator accepts only GitIndexCommitPort.
    fn accepts_index_port(_: &dyn GitIndexCommitPort) {}
    let port = RecordingGitIndexPort::default();
    accepts_index_port(&port);
    assert!(port.commit_calls.lock().unwrap().is_empty());
}

#[test]
fn preview_error_precedence_is_operation_then_conflict_then_scope_then_empty() {
    let mut value = facts();
    value.operation = GitOperationState::Merge;
    value.unmerged = true;
    value.fingerprint.staged_paths = vec!["../outside.rs".into()];
    value.index_nonempty = false;
    assert_eq!(validate_facts(&value), Err(IndexCommitError::OperationInProgress));

    value.operation = GitOperationState::None;
    assert_eq!(validate_facts(&value), Err(IndexCommitError::Conflicted));

    value.unmerged = false;
    assert!(matches!(validate_facts(&value), Err(IndexCommitError::OutsideProjectScope(_))));

    value.fingerprint.staged_paths.clear();
    assert_eq!(validate_facts(&value), Err(IndexCommitError::NothingStaged));
}

#[test]
fn preview_rejects_each_unsafe_or_empty_index_state_before_publishing() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    for (current, expected) in [
        ({ let mut f = facts(); f.operation = GitOperationState::Merge; f }, "OperationInProgress"),
        ({ let mut f = facts(); f.unmerged = true; f }, "Conflicted"),
        ({ let mut f = facts(); f.fingerprint.staged_paths = vec!["../outside.rs".into()]; f }, "OutsideProjectScope"),
        ({ let mut f = facts(); f.index_nonempty = false; f.fingerprint.staged_paths.clear(); f }, "NothingStaged"),
    ] {
        port.facts.lock().unwrap().replace(current.clone());
        let error = host.prepare(r"C:\fixture\repo\app").unwrap_err();
        assert_eq!(error.code, expected);
        assert!(!error.mutation_started);
    }
    assert!(port.commit_calls.lock().unwrap().is_empty());
}

#[test]
fn failed_or_unobservable_commit_requires_fresh_preview_and_never_reuses_token() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    *port.exit_code.lock().unwrap() = None;
    *port.omit_after.lock().unwrap() = true;
    let error = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id.clone(), generation: preview.generation,
        message: "message".into(), confirmed: true,
    }).unwrap_err();
    assert_eq!(error.code, "OutcomeUnknown");
    assert!(error.mutation_started);
    assert!(error.requires_new_preview);
    let replay = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id, generation: preview.generation,
        message: "message".into(), confirmed: true,
    }).unwrap_err();
    assert_eq!(replay.code, "InvalidPreview");
}

#[test]
fn root_commit_can_be_observed_without_a_parent() {
    let port = Arc::new(RecordingGitIndexPort::default());
    port.facts.lock().unwrap().replace({ let mut f = facts(); f.fingerprint.head_oid = None; f });
    *port.invocation_started.lock().unwrap() = true;
    *port.exit_code.lock().unwrap() = Some(0);
    let host = IndexCommitCoordinator::new(port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("unborn repository index preview");
    let result = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id, generation: preview.generation,
        message: "initial commit".into(), confirmed: true,
    }).expect("root commit with no parent");
    assert_eq!(result.state, "Committed");
    assert_eq!(result.before.head_oid, None);
}

#[test]
fn root_commit_with_failed_parent_readback_is_not_claimed_committed() {
    let port = Arc::new(RecordingGitIndexPort::default());
    port.facts.lock().unwrap().replace({ let mut f = facts(); f.fingerprint.head_oid = None; f });
    *port.invocation_started.lock().unwrap() = true;
    *port.exit_code.lock().unwrap() = Some(0);
    *port.diagnostic.lock().unwrap() = Some("parent readback failed".into());
    let host = IndexCommitCoordinator::new(port);
    let preview = host.prepare(r"C:\fixture\repo\app").expect("unborn repository index preview");
    let result = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id, generation: preview.generation,
        message: "initial commit".into(), confirmed: true,
    });
    assert_eq!(result.unwrap_err().code, "OutcomeUnknown", "missing parent because readback failed is not proof of a root commit");
}

#[test]
fn observed_tree_without_started_commit_process_is_never_claimed_committed() {
    let port = Arc::new(RecordingGitIndexPort::default());
    let host = coordinator(&port);
    *port.invocation_started.lock().unwrap() = false;
    let preview = host.prepare(r"C:\fixture\repo\app").expect("preview");
    let error = host.commit(IndexCommitRequestDto {
        preview_id: preview.preview_id,
        generation: preview.generation,
        message: "message".into(),
        confirmed: true,
    }).unwrap_err();
    assert_eq!(error.code, "FailedObserved");
    assert!(!error.mutation_started, "no invocation was started by this route");
    assert!(error.requires_new_preview);
}
