//! M07-S1 pure recovery-state policy.
//! HOST supplies elapsed time, verified capture and durable-publication outcomes.
//! No timer, filesystem, codec, fingerprint computation or asset pinning lives here.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CapturedAttempt {
    pub attempt_id: String,
    pub captured_revision: u64,
    pub captured_fingerprint: String,
    pub asset_manifest_digest: String,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryPolicyState {
    pub project_id: String,
    pub session_id: String,
    pub last_check_ms: u64,
    pub successful_fingerprint: Option<String>,
    pub capture_requested: bool,
    pub inflight: Option<CapturedAttempt>,
    pub closed: bool,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompletionOutcome {
    Published,
    Failed,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RecoveryEventKind {
    Check {
        now_ms: u64,
        current_fingerprint: Option<String>,
        mutation_in_progress: bool,
    },
    BeginAttempt {
        capture: CapturedAttempt,
    },
    Complete {
        attempt_id: String,
        outcome: CompletionOutcome,
    },
    Close,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryEvent {
    pub project_id: String,
    pub session_id: String,
    pub kind: RecoveryEventKind,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryTransition {
    pub state: RecoveryPolicyState,
    pub action: RecoveryAction,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RecoveryAction {
    SkipUnchanged,
    NotDue,
    DeferMutation,
    WaitInFlight,
    RequestCapture,
    AttemptRegistered,
    BaselineAdvanced,
    RetryPending,
    Closed,
    IgnoreClosedCompletion,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RecoveryPolicyError {
    InvalidInput { field: String, reason: String },
    SessionMismatch,
    StaleAttempt,
    AttemptAlreadyActive,
    CaptureNotRequested,
    TimeRegressed,
}

/// Returns a new state/action; it cannot mutate the caller or publish a snapshot.
/// Published is a trusted HOST receipt, not a claim authenticated by this policy.
pub fn transition_recovery(
    state: &RecoveryPolicyState,
    event: &RecoveryEvent,
) -> Result<RecoveryTransition, RecoveryPolicyError> {
    validate_id("state.project_id", &state.project_id)?;
    validate_id("state.session_id", &state.session_id)?;
    validate_id("event.project_id", &event.project_id)?;
    validate_id("event.session_id", &event.session_id)?;
    if state.project_id != event.project_id || state.session_id != event.session_id {
        return Err(RecoveryPolicyError::SessionMismatch);
    }
    if let Some(value) = &state.successful_fingerprint {
        validate_fingerprint("successful_fingerprint", value)?;
    }
    if let Some(capture) = &state.inflight {
        validate_capture(capture)?;
    }
    match &event.kind {
        RecoveryEventKind::Check {
            current_fingerprint,
            ..
        } => {
            if let Some(value) = current_fingerprint {
                validate_fingerprint("current_fingerprint", value)?;
            }
        }
        RecoveryEventKind::BeginAttempt { capture } => validate_capture(capture)?,
        RecoveryEventKind::Complete { attempt_id, .. } => validate_id("attempt_id", attempt_id)?,
        RecoveryEventKind::Close => {}
    }
    let mut next = state.clone();
    let action = match &event.kind {
        RecoveryEventKind::Complete { .. } if state.closed => {
            RecoveryAction::IgnoreClosedCompletion
        }
        _ if state.closed => RecoveryAction::Closed,
        RecoveryEventKind::Check {
            now_ms,
            current_fingerprint,
            mutation_in_progress,
        } => {
            let elapsed = now_ms
                .checked_sub(state.last_check_ms)
                .ok_or(RecoveryPolicyError::TimeRegressed)?;
            if elapsed < 60000 {
                RecoveryAction::NotDue
            } else if state.inflight.is_some() || state.capture_requested {
                next.last_check_ms = *now_ms;
                RecoveryAction::WaitInFlight
            } else if *mutation_in_progress {
                RecoveryAction::DeferMutation
            } else {
                let current = current_fingerprint.as_ref().ok_or_else(|| {
                    invalid(
                        "current_fingerprint",
                        "stable content fingerprint is required",
                    )
                })?;
                next.last_check_ms = *now_ms;
                if state.successful_fingerprint.as_ref() == Some(current) {
                    RecoveryAction::SkipUnchanged
                } else {
                    next.capture_requested = true;
                    RecoveryAction::RequestCapture
                }
            }
        }
        RecoveryEventKind::BeginAttempt { capture } => {
            if state.inflight.is_some() {
                return Err(RecoveryPolicyError::AttemptAlreadyActive);
            }
            if !state.capture_requested {
                return Err(RecoveryPolicyError::CaptureNotRequested);
            }
            next.capture_requested = false;
            next.inflight = Some(capture.clone());
            RecoveryAction::AttemptRegistered
        }
        RecoveryEventKind::Complete {
            attempt_id,
            outcome,
        } => {
            let capture = state
                .inflight
                .as_ref()
                .filter(|c| &c.attempt_id == attempt_id)
                .ok_or(RecoveryPolicyError::StaleAttempt)?;
            next.inflight = None;
            match outcome {
                CompletionOutcome::Published => {
                    next.successful_fingerprint = Some(capture.captured_fingerprint.clone());
                    RecoveryAction::BaselineAdvanced
                }
                CompletionOutcome::Failed => RecoveryAction::RetryPending,
            }
        }
        RecoveryEventKind::Close => {
            next.closed = true;
            next.capture_requested = false;
            RecoveryAction::Closed
        }
    };
    Ok(RecoveryTransition {
        state: next,
        action,
    })
}

fn invalid(field: &str, reason: &str) -> RecoveryPolicyError {
    RecoveryPolicyError::InvalidInput {
        field: field.into(),
        reason: reason.into(),
    }
}
fn validate_id(field: &str, value: &str) -> Result<(), RecoveryPolicyError> {
    if value.is_empty() || value.len() > 256 || value.contains('\0') {
        Err(invalid(field, "expected 1..256 UTF-8 bytes without NUL"))
    } else {
        Ok(())
    }
}
fn validate_fingerprint(field: &str, value: &str) -> Result<(), RecoveryPolicyError> {
    if value.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64
            && hex
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    }) {
        Ok(())
    } else {
        Err(invalid(field, "expected lowercase SHA-256 fingerprint"))
    }
}
fn validate_capture(capture: &CapturedAttempt) -> Result<(), RecoveryPolicyError> {
    validate_id("attempt_id", &capture.attempt_id)?;
    validate_fingerprint("captured_fingerprint", &capture.captured_fingerprint)?;
    validate_fingerprint("asset_manifest_digest", &capture.asset_manifest_digest)
}
