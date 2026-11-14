//! FLOW lamp state machine (PD-FLOW-01 / BDD-PD-FLOW-01 / PD-FLOW-EVID-GATE-01).
//!
//! Product lamps align with [`crate::Zone`]: gray / blue / yellow / red / green.
//! Transitions are event-driven; **COMPLETE → green requires prior acceptance**.
//! **Accept／Complete also require EVID readiness** (PD-FLOW-EVID-GATE-01):
//! Provider／Agent "done" alone never greens; missing evidence → reject (caller keeps yellow).
//! Illegal transitions are rejected and leave state unchanged.
//! Duplicate `event_id`s are idempotent (at most one real transition).

use std::collections::HashSet;

use crate::Zone;

/// Authoritative task flow record: lamp + reason + acceptance gate.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskFlow {
    pub id: String,
    /// Current product lamp (same vocabulary as UI / [`Zone`]).
    pub lamp: Zone,
    /// Human/agent-visible reason for the current lamp (required on fail).
    pub reason: String,
    /// Wall-clock or fixture timestamp of last successful mutation (caller-supplied).
    pub changed_at: String,
    /// Acceptance gate: must be true before [`FlowEvent::Complete`] may move to green.
    /// Set only via [`FlowEvent::Accept`] when EVID evidence is ready.
    pub accepted: bool,
    /// Monotonic version; bumps only on a real state/flag change.
    pub version: u64,
    seen_event_ids: HashSet<String>,
}

/// Events that may drive a lamp transition (or acceptance flag).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FlowEvent {
    /// gray → blue (active run / implementation starts).
    Start,
    /// gray → yellow (queued pending / await schedule without run).
    QueuePending,
    /// blue → yellow (await approval / pending human).
    AwaitApproval,
    /// yellow → blue (resume after approval).
    Resume,
    /// non-green → red (failure / block; reason required, non-empty).
    Fail,
    /// red → yellow (recover to pending).
    Recover,
    /// Record acceptance **only if** EVID evidence is ready; does not change lamp by itself.
    Accept,
    /// → green **only if** `accepted` **and** EVID evidence still ready; otherwise rejected.
    Complete,
}

impl FlowEvent {
    pub fn as_str(self) -> &'static str {
        match self {
            FlowEvent::Start => "start",
            FlowEvent::QueuePending => "queue_pending",
            FlowEvent::AwaitApproval => "await_approval",
            FlowEvent::Resume => "resume",
            FlowEvent::Fail => "fail",
            FlowEvent::Recover => "recover",
            FlowEvent::Accept => "accept",
            FlowEvent::Complete => "complete",
        }
    }
}

/// Outcome of a successful [`TaskFlow::apply`] (including idempotent no-ops).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TransitionOutcome {
    pub lamp: Zone,
    pub reason: String,
    pub accepted: bool,
    pub version: u64,
    /// True when lamp/accepted/reason/version actually changed.
    pub changed: bool,
}

/// Rejection reasons for illegal or gated transitions.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FlowError {
    IllegalTransition {
        from: Zone,
        event: FlowEvent,
    },
    /// COMPLETE requested but acceptance gate is false — state must stay put.
    CompleteWithoutAcceptance {
        from: Zone,
    },
    /// ACCEPT without EVID readiness — Provider done ≠ accept (PD-FLOW-EVID-GATE-01).
    AcceptWithoutEvidence {
        from: Zone,
    },
    /// COMPLETE without EVID readiness — state preserved; caller keeps yellow.
    CompleteWithoutEvidence {
        from: Zone,
    },
    /// Fail requires a non-empty reason.
    ReasonRequired,
}

impl std::fmt::Display for FlowError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            FlowError::IllegalTransition { from, event } => {
                write!(
                    f,
                    "illegal transition: {} + {} rejected",
                    from.as_str(),
                    event.as_str()
                )
            }
            FlowError::CompleteWithoutAcceptance { from } => {
                write!(
                    f,
                    "complete without acceptance rejected (lamp={})",
                    from.as_str()
                )
            }
            FlowError::AcceptWithoutEvidence { from } => {
                write!(
                    f,
                    "accept without EVID evidence rejected (lamp={})",
                    from.as_str()
                )
            }
            FlowError::CompleteWithoutEvidence { from } => {
                write!(
                    f,
                    "complete without EVID evidence rejected (lamp={})",
                    from.as_str()
                )
            }
            FlowError::ReasonRequired => write!(f, "fail requires a non-empty reason"),
        }
    }
}

impl std::error::Error for FlowError {}

impl TaskFlow {
    /// New task starts gray (未開始／等依賴), not accepted.
    pub fn new(id: impl Into<String>, at: impl Into<String>) -> Self {
        Self {
            id: id.into(),
            lamp: Zone::Gray,
            reason: "unstarted".into(),
            changed_at: at.into(),
            accepted: false,
            version: 0,
            seen_event_ids: HashSet::new(),
        }
    }

    /// Apply an event. On error, **no fields change**.
    ///
    /// `evidence_ready` is consulted **only** for [`FlowEvent::Accept`] and
    /// [`FlowEvent::Complete`] (PD-FLOW-EVID-GATE-01). Other events ignore it.
    ///
    /// When `event_id` is `Some` and already seen, returns `Ok` with `changed: false`
    /// (idempotent; version unchanged).
    pub fn apply(
        &mut self,
        event: FlowEvent,
        reason: impl Into<String>,
        at: impl Into<String>,
        event_id: Option<&str>,
        evidence_ready: bool,
    ) -> Result<TransitionOutcome, FlowError> {
        if let Some(eid) = event_id {
            if !eid.is_empty() && self.seen_event_ids.contains(eid) {
                return Ok(self.snapshot_outcome(false));
            }
        }

        let reason = reason.into();
        let at = at.into();

        // Validate + compute next state without mutating yet.
        let next = self.plan(event, &reason, evidence_ready)?;

        // Commit
        let changed = next.lamp != self.lamp
            || next.accepted != self.accepted
            || next.reason != self.reason;
        self.lamp = next.lamp;
        self.accepted = next.accepted;
        self.reason = next.reason;
        self.changed_at = at;
        if changed {
            self.version = self.version.saturating_add(1);
        }
        if let Some(eid) = event_id {
            if !eid.is_empty() {
                self.seen_event_ids.insert(eid.to_string());
            }
        }

        Ok(self.snapshot_outcome(changed))
    }

    fn snapshot_outcome(&self, changed: bool) -> TransitionOutcome {
        TransitionOutcome {
            lamp: self.lamp,
            reason: self.reason.clone(),
            accepted: self.accepted,
            version: self.version,
            changed,
        }
    }

    /// Pure transition table. Does not mutate `self`.
    fn plan(
        &self,
        event: FlowEvent,
        reason: &str,
        evidence_ready: bool,
    ) -> Result<Planned, FlowError> {
        match event {
            FlowEvent::Start => match self.lamp {
                Zone::Gray => Ok(Planned {
                    lamp: Zone::Blue,
                    accepted: self.accepted,
                    reason: nonempty_or(reason, "started"),
                }),
                _ => Err(FlowError::IllegalTransition {
                    from: self.lamp,
                    event,
                }),
            },
            FlowEvent::QueuePending => match self.lamp {
                Zone::Gray => Ok(Planned {
                    lamp: Zone::Yellow,
                    accepted: self.accepted,
                    reason: nonempty_or(reason, "queued_pending"),
                }),
                _ => Err(FlowError::IllegalTransition {
                    from: self.lamp,
                    event,
                }),
            },
            FlowEvent::AwaitApproval => match self.lamp {
                Zone::Blue => Ok(Planned {
                    lamp: Zone::Yellow,
                    accepted: self.accepted,
                    reason: nonempty_or(reason, "await_approval"),
                }),
                _ => Err(FlowError::IllegalTransition {
                    from: self.lamp,
                    event,
                }),
            },
            FlowEvent::Resume => match self.lamp {
                Zone::Yellow => Ok(Planned {
                    lamp: Zone::Blue,
                    accepted: self.accepted,
                    reason: nonempty_or(reason, "resumed"),
                }),
                _ => Err(FlowError::IllegalTransition {
                    from: self.lamp,
                    event,
                }),
            },
            FlowEvent::Fail => {
                if reason.trim().is_empty() {
                    return Err(FlowError::ReasonRequired);
                }
                match self.lamp {
                    Zone::Gray | Zone::Blue | Zone::Yellow => Ok(Planned {
                        lamp: Zone::Red,
                        accepted: self.accepted,
                        reason: reason.to_string(),
                    }),
                    Zone::Red | Zone::Green => Err(FlowError::IllegalTransition {
                        from: self.lamp,
                        event,
                    }),
                }
            }
            FlowEvent::Recover => match self.lamp {
                Zone::Red => Ok(Planned {
                    lamp: Zone::Yellow,
                    accepted: self.accepted,
                    reason: nonempty_or(reason, "recovered"),
                }),
                _ => Err(FlowError::IllegalTransition {
                    from: self.lamp,
                    event,
                }),
            },
            FlowEvent::Accept => {
                // PD-FLOW-EVID-GATE-01: Accept requires EVID readiness (Provider done ≠ accept).
                if !evidence_ready {
                    return Err(FlowError::AcceptWithoutEvidence { from: self.lamp });
                }
                match self.lamp {
                    // Acceptance may be recorded while work is active / pending / blocked.
                    Zone::Blue | Zone::Yellow | Zone::Red => Ok(Planned {
                        lamp: self.lamp,
                        accepted: true,
                        reason: nonempty_or(reason, "accepted"),
                    }),
                    Zone::Gray | Zone::Green => Err(FlowError::IllegalTransition {
                        from: self.lamp,
                        event,
                    }),
                }
            }
            FlowEvent::Complete => {
                if !self.accepted {
                    return Err(FlowError::CompleteWithoutAcceptance { from: self.lamp });
                }
                // PD-FLOW-EVID-GATE-01: Complete still needs live EVID readiness.
                if !evidence_ready {
                    return Err(FlowError::CompleteWithoutEvidence { from: self.lamp });
                }
                match self.lamp {
                    Zone::Blue | Zone::Yellow => Ok(Planned {
                        lamp: Zone::Green,
                        accepted: true,
                        reason: nonempty_or(reason, "complete"),
                    }),
                    // Already green + accepted: idempotent no-op at plan level
                    // (still counts as legal when accepted + evidence ready).
                    Zone::Green => Ok(Planned {
                        lamp: Zone::Green,
                        accepted: true,
                        reason: if reason.trim().is_empty() {
                            self.reason.clone()
                        } else {
                            reason.to_string()
                        },
                    }),
                    Zone::Gray | Zone::Red => Err(FlowError::IllegalTransition {
                        from: self.lamp,
                        event,
                    }),
                }
            }
        }
    }
}

struct Planned {
    lamp: Zone,
    accepted: bool,
    reason: String,
}

fn nonempty_or(reason: &str, fallback: &str) -> String {
    let t = reason.trim();
    if t.is_empty() {
        fallback.to_string()
    } else {
        t.to_string()
    }
}

/// Lamp meaning strings (PRODUCT-DEVELOPMENT §5.5) — for projection / UI copy.
pub fn lamp_meaning(lamp: Zone) -> &'static str {
    match lamp {
        Zone::Gray => "unstarted_or_waiting_deps",
        Zone::Blue => "running_active_run",
        Zone::Yellow => "pending_approval_or_action",
        Zone::Red => "failed_or_blocked",
        Zone::Green => "accepted_in_scope_complete",
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn flow() -> TaskFlow {
        TaskFlow::new("PD-FLOW-01", "t0")
    }

    /// BDD-PD-FLOW-01: lamp semantics match product vocabulary / Zone.
    #[test]
    fn lamp_semantics_match_zone_vocabulary() {
        assert_eq!(Zone::Gray.as_str(), "gray");
        assert_eq!(Zone::Blue.as_str(), "blue");
        assert_eq!(Zone::Yellow.as_str(), "yellow");
        assert_eq!(Zone::Red.as_str(), "red");
        assert_eq!(Zone::Green.as_str(), "green");
        assert_eq!(lamp_meaning(Zone::Gray), "unstarted_or_waiting_deps");
        assert_eq!(lamp_meaning(Zone::Blue), "running_active_run");
        assert_eq!(lamp_meaning(Zone::Yellow), "pending_approval_or_action");
        assert_eq!(lamp_meaning(Zone::Red), "failed_or_blocked");
        assert_eq!(lamp_meaning(Zone::Green), "accepted_in_scope_complete");
    }

    /// Happy path: gray → blue → yellow → (accept+EVID) → green.
    #[test]
    fn legal_path_to_green_with_acceptance() {
        let mut t = flow();
        assert_eq!(t.lamp, Zone::Gray);

        let o = t
            .apply(FlowEvent::Start, "begin impl", "t1", Some("e-start"), false)
            .unwrap();
        assert_eq!(o.lamp, Zone::Blue);
        assert!(o.changed);
        assert_eq!(t.version, 1);
        assert_eq!(t.reason, "begin impl");
        assert_eq!(t.changed_at, "t1");

        t.apply(FlowEvent::AwaitApproval, "need review", "t2", None, false)
            .unwrap();
        assert_eq!(t.lamp, Zone::Yellow);

        t.apply(FlowEvent::Accept, "owner ok", "t3", None, true)
            .unwrap();
        assert!(t.accepted);
        assert_eq!(t.lamp, Zone::Yellow);

        let done = t
            .apply(
                FlowEvent::Complete,
                "shipped slice",
                "t4",
                Some("e-complete"),
                true,
            )
            .unwrap();
        assert_eq!(done.lamp, Zone::Green);
        assert_eq!(t.lamp, Zone::Green);
        assert_eq!(t.reason, "shipped slice");
        assert!(t.accepted);
    }

    /// BDD-PD-FLOW-01 / BDD-FLOW-001-02: COMPLETE without acceptance is rejected; state kept.
    #[test]
    fn reject_complete_without_acceptance_preserves_state() {
        let mut t = flow();
        t.apply(FlowEvent::Start, "go", "t1", None, false).unwrap();
        let before = t.clone();
        // Agent says done + claims evidence — still no Accept → reject.
        let err = t
            .apply(FlowEvent::Complete, "agent says done", "t2", None, true)
            .unwrap_err();
        assert_eq!(
            err,
            FlowError::CompleteWithoutAcceptance {
                from: Zone::Blue
            }
        );
        assert_eq!(t.lamp, before.lamp);
        assert_eq!(t.reason, before.reason);
        assert_eq!(t.accepted, before.accepted);
        assert_eq!(t.version, before.version);
        assert_eq!(t.changed_at, before.changed_at);
    }

    #[test]
    fn reject_complete_from_gray_even_if_somehow_accepted_flag_false() {
        let mut t = flow();
        let err = t
            .apply(FlowEvent::Complete, "nope", "t1", None, true)
            .unwrap_err();
        assert_eq!(
            err,
            FlowError::CompleteWithoutAcceptance { from: Zone::Gray }
        );
        assert_eq!(t.lamp, Zone::Gray);
        assert_eq!(t.version, 0);
    }

    /// BDD-PD-FLOW-EVID-GATE-01: Accept without EVID readiness is rejected.
    #[test]
    fn reject_accept_without_evidence_preserves_state() {
        let mut t = flow();
        t.apply(FlowEvent::Start, "go", "t1", None, false).unwrap();
        t.apply(FlowEvent::AwaitApproval, "wait", "t2", None, false)
            .unwrap();
        assert_eq!(t.lamp, Zone::Yellow);
        let before = t.clone();
        let err = t
            .apply(FlowEvent::Accept, "provider done", "t3", None, false)
            .unwrap_err();
        assert_eq!(
            err,
            FlowError::AcceptWithoutEvidence {
                from: Zone::Yellow
            }
        );
        assert!(!t.accepted);
        assert_eq!(t.lamp, before.lamp);
        assert_eq!(t.version, before.version);
    }

    /// BDD-PD-FLOW-EVID-GATE-01: Complete without EVID (even if accepted) is rejected.
    #[test]
    fn reject_complete_without_evidence_preserves_state() {
        let mut t = flow();
        t.apply(FlowEvent::Start, "go", "t1", None, false).unwrap();
        t.apply(FlowEvent::Accept, "had evid", "t2", None, true)
            .unwrap();
        assert!(t.accepted);
        let before = t.clone();
        let err = t
            .apply(FlowEvent::Complete, "stale evid", "t3", None, false)
            .unwrap_err();
        assert_eq!(
            err,
            FlowError::CompleteWithoutEvidence { from: Zone::Blue }
        );
        assert_eq!(t.lamp, before.lamp);
        assert_ne!(t.lamp, Zone::Green);
        assert_eq!(t.version, before.version);
    }

    /// Illegal transitions are all rejected (sample matrix).
    #[test]
    fn illegal_transitions_all_rejected() {
        let cases: &[(Zone, FlowEvent)] = &[
            (Zone::Blue, FlowEvent::Start),
            (Zone::Yellow, FlowEvent::Start),
            (Zone::Red, FlowEvent::Start),
            (Zone::Green, FlowEvent::Start),
            (Zone::Blue, FlowEvent::QueuePending),
            (Zone::Gray, FlowEvent::AwaitApproval),
            (Zone::Gray, FlowEvent::Resume),
            (Zone::Blue, FlowEvent::Resume),
            (Zone::Red, FlowEvent::Resume),
            (Zone::Green, FlowEvent::Fail),
            (Zone::Gray, FlowEvent::Recover),
            (Zone::Blue, FlowEvent::Recover),
            (Zone::Gray, FlowEvent::Accept),
            (Zone::Green, FlowEvent::Accept),
        ];

        for &(from, event) in cases {
            let mut t = flow();
            // Drive to `from` via legal path (best-effort fixtures).
            match from {
                Zone::Gray => {}
                Zone::Blue => {
                    t.apply(FlowEvent::Start, "s", "a", None, false).unwrap();
                }
                Zone::Yellow => {
                    t.apply(FlowEvent::QueuePending, "q", "a", None, false)
                        .unwrap();
                }
                Zone::Red => {
                    t.apply(FlowEvent::Start, "s", "a", None, false).unwrap();
                    t.apply(FlowEvent::Fail, "blocked", "b", None, false)
                        .unwrap();
                }
                Zone::Green => {
                    t.apply(FlowEvent::Start, "s", "a", None, false).unwrap();
                    t.apply(FlowEvent::Accept, "ok", "b", None, true)
                        .unwrap();
                    t.apply(FlowEvent::Complete, "done", "c", None, true)
                        .unwrap();
                }
            }
            assert_eq!(t.lamp, from, "fixture lamp");
            let v = t.version;
            // Accept on Gray／Green uses evidence_ready=true so we hit IllegalTransition
            // (not AcceptWithoutEvidence).
            let evid = matches!(event, FlowEvent::Accept | FlowEvent::Complete);
            let err = t.apply(event, "x", "z", None, evid).unwrap_err();
            assert_eq!(
                err,
                FlowError::IllegalTransition { from, event },
                "expected illegal {from:?} + {event:?}"
            );
            assert_eq!(t.lamp, from);
            assert_eq!(t.version, v);
        }
    }

    #[test]
    fn fail_requires_nonempty_reason() {
        let mut t = flow();
        t.apply(FlowEvent::Start, "s", "t1", None, false).unwrap();
        let err = t
            .apply(FlowEvent::Fail, "   ", "t2", None, false)
            .unwrap_err();
        assert_eq!(err, FlowError::ReasonRequired);
        assert_eq!(t.lamp, Zone::Blue);
    }

    #[test]
    fn fail_and_recover_roundtrip() {
        let mut t = flow();
        t.apply(FlowEvent::Start, "s", "t1", None, false).unwrap();
        t.apply(FlowEvent::Fail, "compile error", "t2", None, false)
            .unwrap();
        assert_eq!(t.lamp, Zone::Red);
        assert_eq!(t.reason, "compile error");
        t.apply(FlowEvent::Recover, "fixed locally", "t3", None, false)
            .unwrap();
        assert_eq!(t.lamp, Zone::Yellow);
    }

    /// BDD-FLOW-001-03: duplicate event id → only one real transition.
    #[test]
    fn duplicate_event_id_is_idempotent() {
        let mut t = flow();
        let first = t
            .apply(FlowEvent::Start, "go", "t1", Some("e1"), false)
            .unwrap();
        assert!(first.changed);
        assert_eq!(t.version, 1);
        assert_eq!(t.lamp, Zone::Blue);

        let second = t
            .apply(FlowEvent::Start, "go again", "t2", Some("e1"), false)
            .unwrap();
        assert!(!second.changed);
        assert_eq!(t.version, 1);
        assert_eq!(t.lamp, Zone::Blue);
        assert_eq!(t.reason, "go"); // preserved from first commit
        assert_eq!(t.changed_at, "t1");
    }

    #[test]
    fn resume_yellow_to_blue() {
        let mut t = flow();
        t.apply(FlowEvent::QueuePending, "wait", "t1", None, false)
            .unwrap();
        t.apply(FlowEvent::Resume, "deps ready", "t2", None, false)
            .unwrap();
        assert_eq!(t.lamp, Zone::Blue);
    }

    #[test]
    fn complete_from_red_rejected_even_when_accepted() {
        let mut t = flow();
        t.apply(FlowEvent::Start, "s", "t1", None, false).unwrap();
        t.apply(FlowEvent::Fail, "blocked", "t2", None, false)
            .unwrap();
        t.apply(FlowEvent::Accept, "evidence ok", "t3", None, true)
            .unwrap();
        assert!(t.accepted);
        let err = t
            .apply(FlowEvent::Complete, "force green", "t4", None, true)
            .unwrap_err();
        assert_eq!(
            err,
            FlowError::IllegalTransition {
                from: Zone::Red,
                event: FlowEvent::Complete
            }
        );
        assert_eq!(t.lamp, Zone::Red);
    }

    /// Engine projection alignment: TaskFlow.lamp is a Zone usable by set_zone.
    #[test]
    fn lamp_aligns_with_engine_zone_projection() {
        use crate::Engine;

        let mut flow = flow();
        flow.apply(FlowEvent::Start, "run", "t1", None, false)
            .unwrap();
        flow.apply(FlowEvent::Accept, "ok", "t2", None, true)
            .unwrap();
        flow.apply(FlowEvent::Complete, "done", "t3", None, true)
            .unwrap();
        assert_eq!(flow.lamp, Zone::Green);

        let mut eng = Engine::new();
        eng.upsert_task(&flow.id, "FLOW lamp", Zone::Gray);
        let snap = eng.set_zone(&flow.id, flow.lamp).unwrap();
        assert_eq!(snap.green, 1);
        assert_eq!(snap.gray, 0);
    }
}
