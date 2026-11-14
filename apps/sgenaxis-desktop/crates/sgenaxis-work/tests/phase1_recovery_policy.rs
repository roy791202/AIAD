//! M07-S1 pure state contracts, without real time, snapshot storage or IO.
use sgenaxis_work::recovery_state::*;
fn digest(c: char) -> String {
    format!("sha256:{}", c.to_string().repeat(64))
}
fn state() -> RecoveryPolicyState {
    RecoveryPolicyState {
        project_id: "project-1".into(),
        session_id: "session-1".into(),
        last_check_ms: 0,
        successful_fingerprint: Some(digest('a')),
        capture_requested: false,
        inflight: None,
        closed: false,
    }
}
fn attempt() -> CapturedAttempt {
    CapturedAttempt {
        attempt_id: "attempt-1".into(),
        captured_revision: 1,
        captured_fingerprint: digest('b'),
        asset_manifest_digest: digest('c'),
    }
}
fn event(kind: RecoveryEventKind) -> RecoveryEvent {
    RecoveryEvent {
        project_id: "project-1".into(),
        session_id: "session-1".into(),
        kind,
    }
}
fn check(now: u64, current: Option<String>, mutation: bool) -> RecoveryEvent {
    event(RecoveryEventKind::Check {
        now_ms: now,
        current_fingerprint: current,
        mutation_in_progress: mutation,
    })
}
fn assert_transition(
    s: &RecoveryPolicyState,
    e: &RecoveryEvent,
    next: RecoveryPolicyState,
    action: RecoveryAction,
) {
    let before = (s.clone(), e.clone());
    assert_eq!(
        transition_recovery(s, e),
        Ok(RecoveryTransition {
            state: next,
            action
        })
    );
    assert_eq!((s.clone(), e.clone()), before);
}
#[test]
fn fixture_has_distinct_current_baseline_and_capture_identities() {
    let s = state();
    let a = attempt();
    assert_ne!(
        s.successful_fingerprint.as_ref(),
        Some(&a.captured_fingerprint)
    );
    assert_eq!(a.captured_fingerprint.len(), 71);
    assert_eq!(s.session_id, event(RecoveryEventKind::Close).session_id);
    assert!(!s.capture_requested && s.inflight.is_none());
}
#[test]
fn m07_59000ms_is_not_due() {
    let s = state();
    assert_transition(
        &s,
        &check(59000, Some(digest('b')), false),
        s.clone(),
        RecoveryAction::NotDue,
    );
}
macro_rules! due {
    ($name:ident,$now:expr) => {
        #[test]
        fn $name() {
            let s = state();
            let mut next = s.clone();
            next.last_check_ms = $now;
            next.capture_requested = true;
            assert_transition(
                &s,
                &check($now, Some(digest('b')), false),
                next,
                RecoveryAction::RequestCapture,
            );
        }
    };
}
due!(m07_60000ms_requests_capture, 60000);
due!(m07_61000ms_requests_capture, 61000);
due!(m07_long_resume_requests_one_capture, 60000000);
#[test]
fn m07_equal_content_skips_despite_elapsed_time() {
    let s = state();
    let mut next = s.clone();
    next.last_check_ms = 60000;
    assert_transition(
        &s,
        &check(60000, Some(digest('a')), false),
        next,
        RecoveryAction::SkipUnchanged,
    );
}
#[test]
fn m07_first_unsaved_content_requests_capture() {
    let mut s = state();
    s.successful_fingerprint = None;
    let mut next = s.clone();
    next.last_check_ms = 60000;
    next.capture_requested = true;
    assert_transition(
        &s,
        &check(60000, Some(digest('b')), false),
        next,
        RecoveryAction::RequestCapture,
    );
}
#[test]
fn m07_mutation_defers_without_consuming_deadline() {
    let s = state();
    assert_transition(
        &s,
        &check(60000, Some(digest('b')), true),
        s.clone(),
        RecoveryAction::DeferMutation,
    );
}
#[test]
fn m07_stable_same_time_check_after_defer_is_eligible() {
    let s = state();
    let deferred = transition_recovery(&s, &check(60000, Some(digest('b')), true)).unwrap();
    assert_eq!(deferred.action, RecoveryAction::DeferMutation);
    assert_eq!(deferred.state, s);
    let mut next = s.clone();
    next.last_check_ms = 60000;
    next.capture_requested = true;
    assert_transition(
        &deferred.state,
        &check(60000, Some(digest('b')), false),
        next,
        RecoveryAction::RequestCapture,
    );
}
#[test]
fn m07_inflight_check_does_not_overlap() {
    let mut s = state();
    s.inflight = Some(attempt());
    let mut next = s.clone();
    next.last_check_ms = 60000;
    assert_transition(
        &s,
        &check(60000, Some(digest('d')), false),
        next,
        RecoveryAction::WaitInFlight,
    );
}
#[test]
fn m07_pending_capture_check_does_not_request_twice() {
    let mut s = state();
    s.capture_requested = true;
    let mut next = s.clone();
    next.last_check_ms = 60000;
    assert_transition(
        &s,
        &check(60000, Some(digest('d')), false),
        next,
        RecoveryAction::WaitInFlight,
    );
}
#[test]
fn m07_begin_records_actual_newer_captured_revision() {
    let mut s = state();
    s.capture_requested = true;
    let mut a = attempt();
    a.captured_revision = 2;
    a.captured_fingerprint = digest('d');
    let mut next = s.clone();
    next.capture_requested = false;
    next.inflight = Some(a.clone());
    assert_transition(
        &s,
        &event(RecoveryEventKind::BeginAttempt { capture: a }),
        next,
        RecoveryAction::AttemptRegistered,
    );
}
#[test]
fn m07_published_acknowledges_only_captured_fingerprint() {
    let mut s = state();
    s.inflight = Some(attempt());
    let mut next = s.clone();
    next.inflight = None;
    next.successful_fingerprint = Some(digest('b'));
    assert_transition(
        &s,
        &event(RecoveryEventKind::Complete {
            attempt_id: "attempt-1".into(),
            outcome: CompletionOutcome::Published,
        }),
        next,
        RecoveryAction::BaselineAdvanced,
    );
}
#[test]
fn m07_newer_edit_still_requests_capture_after_old_completion() {
    let mut s = state();
    s.inflight = Some(attempt());
    let done = transition_recovery(
        &s,
        &event(RecoveryEventKind::Complete {
            attempt_id: "attempt-1".into(),
            outcome: CompletionOutcome::Published,
        }),
    )
    .unwrap();
    assert_eq!(done.state.successful_fingerprint, Some(digest('b')));
    let mut next = done.state.clone();
    next.last_check_ms = 60000;
    next.capture_requested = true;
    assert_transition(
        &done.state,
        &check(60000, Some(digest('d')), false),
        next,
        RecoveryAction::RequestCapture,
    );
}
#[test]
fn m07_failed_completion_keeps_previous_baseline() {
    let mut s = state();
    s.inflight = Some(attempt());
    let mut next = s.clone();
    next.inflight = None;
    assert_transition(
        &s,
        &event(RecoveryEventKind::Complete {
            attempt_id: "attempt-1".into(),
            outcome: CompletionOutcome::Failed,
        }),
        next,
        RecoveryAction::RetryPending,
    );
}
#[test]
fn m07_next_due_check_retries_failed_capture() {
    let mut s = state();
    s.inflight = Some(attempt());
    let failed = transition_recovery(
        &s,
        &event(RecoveryEventKind::Complete {
            attempt_id: "attempt-1".into(),
            outcome: CompletionOutcome::Failed,
        }),
    )
    .unwrap();
    assert_eq!(
        failed.state.successful_fingerprint,
        s.successful_fingerprint
    );
    let mut next = failed.state.clone();
    next.last_check_ms = 60000;
    next.capture_requested = true;
    assert_transition(
        &failed.state,
        &check(60000, Some(digest('b')), false),
        next,
        RecoveryAction::RequestCapture,
    );
}
#[test]
fn m07_close_clears_only_unstarted_capture_request() {
    let mut s = state();
    s.capture_requested = true;
    let mut next = s.clone();
    next.closed = true;
    next.capture_requested = false;
    assert_transition(
        &s,
        &event(RecoveryEventKind::Close),
        next,
        RecoveryAction::Closed,
    );
}
#[test]
fn m07_closed_completion_cannot_advance_baseline() {
    let mut s = state();
    s.closed = true;
    s.inflight = Some(attempt());
    assert_transition(
        &s,
        &event(RecoveryEventKind::Complete {
            attempt_id: "attempt-1".into(),
            outcome: CompletionOutcome::Published,
        }),
        s.clone(),
        RecoveryAction::IgnoreClosedCompletion,
    );
}
macro_rules! exact_error {
    ($name:ident,$setup:expr,$event:expr,$expected:expr) => {
        #[test]
        fn $name() {
            let mut s = state();
            ($setup)(&mut s);
            let e = $event;
            let before = (s.clone(), e.clone());
            assert_eq!(transition_recovery(&s, &e), Err($expected));
            assert_eq!((s, e), before);
        }
    };
}
exact_error!(
    m07_begin_requires_capture_request,
    |_: &mut RecoveryPolicyState| {},
    event(RecoveryEventKind::BeginAttempt { capture: attempt() }),
    RecoveryPolicyError::CaptureNotRequested
);
exact_error!(
    m07_unknown_completion_is_stale,
    |_: &mut RecoveryPolicyState| {},
    event(RecoveryEventKind::Complete {
        attempt_id: "unknown".into(),
        outcome: CompletionOutcome::Published
    }),
    RecoveryPolicyError::StaleAttempt
);
exact_error!(
    m07_mismatched_attempt_is_stale,
    |s: &mut RecoveryPolicyState| s.inflight = Some(attempt()),
    event(RecoveryEventKind::Complete {
        attempt_id: "other".into(),
        outcome: CompletionOutcome::Published
    }),
    RecoveryPolicyError::StaleAttempt
);
exact_error!(
    m07_time_regression_rejected,
    |s: &mut RecoveryPolicyState| s.last_check_ms = 60000,
    check(59000, Some(digest('b')), false),
    RecoveryPolicyError::TimeRegressed
);
#[test]
fn m07_other_session_completion_rejected() {
    let mut s = state();
    s.inflight = Some(attempt());
    let mut e = event(RecoveryEventKind::Complete {
        attempt_id: "attempt-1".into(),
        outcome: CompletionOutcome::Published,
    });
    e.session_id = "other-session".into();
    assert_eq!(
        transition_recovery(&s, &e),
        Err(RecoveryPolicyError::SessionMismatch)
    );
}
#[test]
fn m07_other_project_event_rejected() {
    let s = state();
    let mut e = check(60000, Some(digest('b')), false);
    e.project_id = "other-project".into();
    assert_eq!(
        transition_recovery(&s, &e),
        Err(RecoveryPolicyError::SessionMismatch)
    );
}
#[test]
fn m07_max_elapsed_counter_uses_subtraction_without_wrap() {
    let mut s = state();
    s.last_check_ms = u64::MAX - 59999;
    assert_transition(
        &s,
        &check(u64::MAX, Some(digest('b')), false),
        s.clone(),
        RecoveryAction::NotDue,
    );
}
#[test]
fn m07_max_elapsed_due_counter_requests_capture() {
    let mut s = state();
    s.last_check_ms = u64::MAX - 60000;
    let mut next = s.clone();
    next.last_check_ms = u64::MAX;
    next.capture_requested = true;
    assert_transition(
        &s,
        &check(u64::MAX, Some(digest('b')), false),
        next,
        RecoveryAction::RequestCapture,
    );
}
#[test]
fn m07_no_timer_backlog_after_large_jump() {
    let s = state();
    let once = transition_recovery(&s, &check(60000000, Some(digest('b')), false)).unwrap();
    assert_eq!(once.action, RecoveryAction::RequestCapture);
    assert_transition(
        &once.state,
        &check(60000000, Some(digest('b')), false),
        once.state.clone(),
        RecoveryAction::NotDue,
    );
}
macro_rules! invalid {
    ($name:ident,$setup:expr,$event:expr) => {
        #[test]
        fn $name() {
            let mut s = state();
            ($setup)(&mut s);
            let e = $event;
            let before = (s.clone(), e.clone());
            match transition_recovery(&s, &e) {
                Err(RecoveryPolicyError::InvalidInput { field, reason }) => {
                    assert!(!field.is_empty());
                    assert!(!reason.is_empty());
                }
                other => panic!("expected invalid input: {other:?}"),
            };
            assert_eq!((s, e), before);
        }
    };
}
invalid!(
    m07_unknown_current_fingerprint_rejected,
    |_: &mut RecoveryPolicyState| {},
    check(60000, None, false)
);
invalid!(
    m07_invalid_current_fingerprint_rejected,
    |_: &mut RecoveryPolicyState| {},
    check(60000, Some("bad".into()), false)
);
invalid!(
    m07_invalid_saved_fingerprint_rejected,
    |s: &mut RecoveryPolicyState| s.successful_fingerprint = Some("bad".into()),
    check(60000, Some(digest('b')), false)
);
invalid!(
    m07_empty_state_identity_rejected,
    |s: &mut RecoveryPolicyState| s.project_id.clear(),
    check(60000, Some(digest('b')), false)
);
invalid!(
    m07_empty_attempt_id_rejected,
    |s: &mut RecoveryPolicyState| s.capture_requested = true,
    event(RecoveryEventKind::BeginAttempt {
        capture: CapturedAttempt {
            attempt_id: "".into(),
            ..attempt()
        }
    })
);
invalid!(
    m07_257_byte_attempt_id_rejected,
    |s: &mut RecoveryPolicyState| s.capture_requested = true,
    event(RecoveryEventKind::BeginAttempt {
        capture: CapturedAttempt {
            attempt_id: "a".repeat(257),
            ..attempt()
        }
    })
);
invalid!(
    m07_invalid_asset_digest_rejected,
    |s: &mut RecoveryPolicyState| s.capture_requested = true,
    event(RecoveryEventKind::BeginAttempt {
        capture: CapturedAttempt {
            asset_manifest_digest: "bad".into(),
            ..attempt()
        }
    })
);
#[test]
fn m07_256_byte_attempt_id_is_valid() {
    let mut s = state();
    s.capture_requested = true;
    let a = CapturedAttempt {
        attempt_id: "a".repeat(256),
        ..attempt()
    };
    let mut next = s.clone();
    next.capture_requested = false;
    next.inflight = Some(a.clone());
    assert_transition(
        &s,
        &event(RecoveryEventKind::BeginAttempt { capture: a }),
        next,
        RecoveryAction::AttemptRegistered,
    );
}
