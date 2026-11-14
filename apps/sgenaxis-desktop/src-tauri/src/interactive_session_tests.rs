//! EA-A0 frozen policy assertions (SKELETON_ONLY).
//! Copied from approved scratch envelope; assertion intent immutable.
//! Targets production private Session seams + InteractiveFixturePort FakePort.
//! FakePort is NOT Native/ConPTY/ACL proof.
use super::*;
use sgenaxis_ports::{Cleanup, InteractiveObservation, InteractiveSize, ReadState};
use std::collections::VecDeque;

#[derive(Default)]
struct FakePort {
    stop_calls: usize,
    writes: usize,
    resizes: usize,
    observations: VecDeque<InteractiveObservation>,
    written: Vec<String>,
    dimensions: Vec<InteractiveSize>,
    stop_error: bool,
    poll_error: bool,
}

impl InteractiveFixturePort for FakePort {
    fn start_fixture(
        &mut self,
        _: &str,
        _: &str,
        _: InteractiveSize,
    ) -> Result<InteractiveId, InteractiveError> {
        Ok(InteractiveId(7))
    }

    fn write_text(&mut self, _: InteractiveId, text: &str) -> Result<(), InteractiveError> {
        self.writes += 1;
        self.written.push(text.to_string());
        Ok(())
    }

    fn resize(&mut self, _: InteractiveId, size: InteractiveSize) -> Result<(), InteractiveError> {
        self.resizes += 1;
        self.dimensions.push(size);
        Ok(())
    }

    fn request_stop(&mut self, _: InteractiveId) -> Result<(), InteractiveError> {
        self.stop_calls += 1;
        if self.stop_error { return Err(InteractiveError { kind: sgenaxis_ports::InteractiveErrorKind::Stop, message: "controlled stop error".into() }); }
        Ok(())
    }

    fn poll(&mut self, _: InteractiveId) -> Result<InteractiveObservation, InteractiveError> {
        if self.poll_error {
            return Err(InteractiveError {
                kind: sgenaxis_ports::InteractiveErrorKind::Observe,
                message: "controlled observation error".into(),
            });
        }
        Ok(self.observations.pop_front().unwrap_or(InteractiveObservation {
            output: vec![],
            child_exit: None,
            read_state: ReadState::Open,
            cleanup: Cleanup::Pending,
        }))
    }
}

fn fixture(phase: Phase) -> Session<FakePort> {
    let mut s = Session::new(FakePort::default());
    s.phase = phase;
    if phase != Phase::Starting {
        s.resource = Some(InteractiveId(7));
    }
    s
}

#[test]
fn ea01_create_reserves_starting_then_second_create_busy() {
    let mut s = Session::new(FakePort::default());
    s.begin_start(true).unwrap();
    assert_eq!(
        s.phase,
        Phase::Starting,
        "missing approved reservation transition"
    );
    assert_eq!(s.begin_start(true), Err(SessionError::Busy));
}

#[test]
fn ea02_starting_close_retains_intent_until_spawn_handle_arrives() {
    let mut s = fixture(Phase::Starting);
    s.close_at(10).unwrap();
    assert!(s.stop_requested, "missing Starting-close intent");
    s.finish_start(Ok(InteractiveId(7))).unwrap();
    assert_eq!(s.port.stop_calls, 1);
    assert_eq!(s.phase, Phase::Closing);
}

#[test]
fn ea03_oversize_input_rejects_whole_payload_in_utf8_bytes() {
    let mut s = fixture(Phase::Running);
    assert_eq!(
        s.send(&"測".repeat(1366)),
        Err(SessionError::InputTooLarge)
    );
    assert_eq!(s.port.writes, 0);
}

#[test]
fn ea04_resize_rejects_zero_negative_and_above_limits_without_port() {
    let mut s = fixture(Phase::Running);
    for (c, r) in [(0, 1), (-1, 1), (513, 1), (1, 0), (1, 257)] {
        assert_eq!(s.resize(c, r), Err(SessionError::InvalidSize));
    }
    assert_eq!(s.port.resizes, 0);
}

#[test]
fn ea05_close_1999_pending_2000_cleanupfailed_retains_handle() {
    let mut s = fixture(Phase::Closing);
    s.stop_requested = true;
    s.stop_observed_ms = Some(0);
    assert_eq!(s.poll_at(1999).unwrap(), Phase::Closing);
    assert_eq!(
        s.poll_at(2000).unwrap(),
        Phase::CleanupFailed,
        "missing approved stop observation deadline"
    );
    assert_eq!(s.resource, Some(InteractiveId(7)));
}

#[test]
fn ea06_closed_requires_child_exit_and_completed_cleanup() {
    let mut s = fixture(Phase::Closing);
    s.port.observations.push_back(InteractiveObservation {
        output: b"tail".to_vec(),
        child_exit: Some(0),
        read_state: ReadState::Eof,
        cleanup: Cleanup::Complete,
    });
    assert_eq!(
        s.poll_at(1).unwrap(),
        Phase::Closed,
        "missing resource-observed terminal transition"
    );
}

#[test]
fn ea07_cleanupfailed_blocks_reopen() {
    let mut s = fixture(Phase::CleanupFailed);
    assert_eq!(s.begin_start(true), Err(SessionError::Busy));
    assert_eq!(s.resource, Some(InteractiveId(7)));
}

#[test]
fn ea08_send_while_closing_rejected_without_portwrite() {
    let mut s = fixture(Phase::Closing);
    assert_eq!(s.send("text"), Err(SessionError::InvalidState));
    assert_eq!(s.port.writes, 0);
}

#[test]
fn ea09_unbound_start_rejected_without_reservation() {
    let mut s = Session::new(FakePort::default());
    assert_eq!(s.begin_start(false), Err(SessionError::Unbound));
    assert_eq!(s.phase, Phase::Idle);
}

// Codex independent approved-contract coverage additions; original nine assertions unchanged.
#[test]
fn ea10_exact_4096_utf8_bytes_forwarded_without_truncation() {
    let mut s = fixture(Phase::Running);
    let text = format!("{}a", "測".repeat(1365));
    assert_eq!(text.len(), 4096);
    s.send(&text).unwrap();
    assert_eq!(s.port.writes, 1);
    assert_eq!(s.port.written, vec![text]);
}
#[test]
fn ea11_empty_input_noop_without_port_call() {
    let mut s = fixture(Phase::Running);
    s.send("").unwrap();
    assert_eq!(s.phase, Phase::Running);
    assert_eq!(s.port.writes, 0);
}
#[test]
fn ea12_valid_resize_all_four_corners_forwarded_exactly() {
    let mut s = fixture(Phase::Running);
    for (cols, rows) in [(1,1),(1,256),(512,1),(512,256)] { s.resize(cols,rows).unwrap(); }
    assert_eq!(s.port.resizes, 4);
    assert_eq!(s.port.dimensions, vec![InteractiveSize{cols:1,rows:1},InteractiveSize{cols:1,rows:256},InteractiveSize{cols:512,rows:1},InteractiveSize{cols:512,rows:256}]);
}
#[test]
fn ea13_cleanup_complete_without_child_exit_cannot_close() {
    let mut s = fixture(Phase::Closing);
    s.port.observations.push_back(InteractiveObservation { output:vec![], child_exit:None, read_state:ReadState::Eof, cleanup:Cleanup::Complete });
    assert_eq!(s.poll_at(1).unwrap(),Phase::Closing);
    assert!(s.port.observations.is_empty(), "the public resource observation must actually be consumed");
    assert_eq!(s.resource,Some(InteractiveId(7)));
}
#[test]
fn ea14_late_cleanup_after_timeout_allows_fresh_session_id() {
    let mut s = fixture(Phase::CleanupFailed);
    s.id = 41;
    s.stop_requested = true;
    s.stop_observed_ms = Some(0);
    s.port.observations.push_back(InteractiveObservation { output:b"tail".to_vec(), child_exit:Some(0), read_state:ReadState::Eof, cleanup:Cleanup::Complete });
    assert_eq!(s.poll_at(2001).unwrap(),Phase::Closed);
    assert!(s.resource.is_none(),"completed cleanup releases handle association");
    let next=s.begin_start(true).unwrap();
    assert_ne!(next,41);
    assert_eq!(s.phase,Phase::Starting);
}
#[test]
fn ea15_stop_error_retains_unresolved_resource_and_blocks_reopen() {
    let mut s=fixture(Phase::Running);
    s.port.stop_error=true;
    let _result=s.close_at(17);
    assert_eq!(s.phase,Phase::CleanupFailed);
    assert_eq!(s.resource,Some(InteractiveId(7)));
    assert_eq!(s.begin_start(true),Err(SessionError::Busy));
    assert_eq!(s.port.stop_calls,1);
}
#[test]
fn ea16_repeated_close_does_not_duplicate_stop_or_extend_deadline() {
    let mut s=fixture(Phase::Running);
    s.close_at(10).unwrap();
    s.close_at(1000).unwrap();
    assert_eq!(s.port.stop_calls,1);
    assert_eq!(s.stop_observed_ms,Some(10));
    assert_eq!(s.poll_at(2009).unwrap(),Phase::Closing);
    assert_eq!(s.poll_at(2010).unwrap(),Phase::CleanupFailed);
}
#[test]
fn ea17_spawn_failure_owns_no_handle_and_reopen_gets_new_id() {
    let mut s=Session::new(FakePort::default());
    let first=s.begin_start(true).unwrap();
    let _result=s.finish_start(Err(InteractiveError { kind:sgenaxis_ports::InteractiveErrorKind::Spawn,message:"controlled spawn failure".into() }));
    assert_eq!(s.phase,Phase::FailedNoHandle);
    assert!(s.resource.is_none());
    let next=s.begin_start(true).unwrap();
    assert_ne!(next,first);
    assert_eq!(s.phase,Phase::Starting);
}
#[test]
fn ea18_ascii_4097_rejected_whole_input_without_write() {
    let mut s=fixture(Phase::Running);
    assert_eq!(s.send(&"a".repeat(4097)),Err(SessionError::InputTooLarge));
    assert_eq!(s.port.writes,0);
}
#[test]
fn ea19_cleanup_failed_observation_retains_resource() {
    let mut s=fixture(Phase::Closing);
    s.port.observations.push_back(InteractiveObservation { output:vec![],child_exit:Some(0),read_state:ReadState::Eof,cleanup:Cleanup::Failed });
    let _result=s.poll_at(1);
    assert_eq!(s.phase,Phase::CleanupFailed);
    assert_eq!(s.resource,Some(InteractiveId(7)));
    assert_eq!(s.begin_start(true),Err(SessionError::Busy));
}

// Independent regression: approved EC04 classifies stream failure immediately,
// retaining unresolved ownership. Successful stop is not successful cleanup.
#[test]
fn ea20_stream_error_retains_resource_and_reports_cleanup_failed() {
    let mut s = fixture(Phase::Closing);
    s.stop_observed_ms = Some(0);
    s.port.observations.push_back(InteractiveObservation {
        output: vec![],
        child_exit: None,
        read_state: ReadState::Error("controlled fixture stream failure".into()),
        cleanup: Cleanup::Pending,
    });
    assert_eq!(s.poll_at(1).unwrap(), Phase::CleanupFailed);
    assert_eq!(s.resource, Some(InteractiveId(7)));
    assert_eq!(s.begin_start(true), Err(SessionError::Busy));
}

// EC04 observation/poll Err must not be swallowed; unresolved ownership retained (EC08 Busy).
#[test]
fn ea21_observation_error_retains_resource_and_reports_cleanup_failed() {
    let mut s = fixture(Phase::Closing);
    s.stop_observed_ms = Some(0);
    s.port.poll_error = true;
    assert_eq!(s.poll_at(1).unwrap(), Phase::CleanupFailed);
    assert_eq!(s.resource, Some(InteractiveId(7)));
    assert_eq!(s.begin_start(true), Err(SessionError::Busy));
}

// EC04 applies while Running as well as Closing. No native/output projection
// is required to observe the already-declared resource failure state.
#[test]
fn ea22_running_stream_error_is_observed_and_retains_resource() {
    let mut s = fixture(Phase::Running);
    s.port.observations.push_back(InteractiveObservation {
        output: vec![],
        child_exit: None,
        read_state: ReadState::Error("controlled running stream failure".into()),
        cleanup: Cleanup::Pending,
    });
    assert_eq!(s.poll_at(1).unwrap(), Phase::CleanupFailed);
    assert_eq!(s.resource, Some(InteractiveId(7)));
    assert_eq!(s.begin_start(true), Err(SessionError::Busy));
}

// Independent takeover regressions: approved EC04 observation and lifecycle only.
#[test]
fn ea23_running_poll_error_retains_resource_and_blocks_reopen() {
    let mut s = fixture(Phase::Running);
    s.port.poll_error = true;
    assert_eq!(s.poll_at(500), Ok(Phase::CleanupFailed));
    assert_eq!(s.resource, Some(InteractiveId(7)));
    assert_eq!(s.begin_start(true), Err(SessionError::Busy));
}

#[test]
fn ea24_running_open_pending_has_no_stop_deadline() {
    let mut s = fixture(Phase::Running);
    assert_eq!(s.poll_at(100_000), Ok(Phase::Running));
    assert_eq!(s.poll_at(102_000), Ok(Phase::Running));
    assert_eq!(s.resource, Some(InteractiveId(7)));
    assert_eq!(s.stop_observed_ms, None);
    assert_eq!(s.port.stop_calls, 0);
}

#[test]
fn ea25_running_natural_exit_and_complete_cleanup_releases_resource() {
    let mut s = fixture(Phase::Running);
    s.id = 41;
    s.port.observations.push_back(InteractiveObservation {
        output: vec![], child_exit: Some(0), read_state: ReadState::Eof,
        cleanup: Cleanup::Complete,
    });
    assert_eq!(s.poll_at(500), Ok(Phase::Closed));
    assert_eq!(s.resource, None);
    assert_eq!(s.port.stop_calls, 0);
    assert_eq!(s.begin_start(true), Ok(42));
}
