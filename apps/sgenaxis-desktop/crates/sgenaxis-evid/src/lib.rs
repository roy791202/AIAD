//! SGenAxis **EVID** — immutable test evidence, valid RED／GREEN, version binding (PD-EVID-01).
//!
//! ```text
//! RunCapture → classify_capture
//!   ├─ Pass
//!   ├─ BehavioralRed   (valid RED; link BDD)
//!   ├─ InfraFailure    (compile / fixture — reject RED qualification)
//!   └─ NotMeasured     (empty exit-0 → never PASS)
//!        ↓
//! EvidenceStore::record / record_behavioral_red  (append + index; bind versions)
//!        ↓
//! evaluate_ready_for_green  (Provider done ≠ task green)
//! ```
//!
//! Pure Rust: no Tauri, no OS ports, no Agent adapters.

#![forbid(unsafe_code)]

mod binding;
mod capture;
mod classify;
mod gate;
mod store;
mod summary;

pub use binding::VersionBinding;
pub use capture::{CaseResult, RunCapture};
pub use classify::{classify_capture, is_valid_behavioral_red, OutcomeClass};
pub use gate::{
    evidence_allows_flow_accept_or_complete, evidence_gaps, evaluate_ready_for_green,
    provider_success_implies_task_green, GreenDecision, ProviderTerminal, EVIDENCE_GAP_LAMP_HINT,
};
pub use store::{EvidError, EvidenceId, EvidenceRecord, EvidenceStore, EvidenceVerdict};
pub use summary::{project_inspector_evidence, EvidenceSummaryLine, InspectorEvidenceSummary};

#[cfg(test)]
mod tests {
    use super::*;

    fn binding_v1() -> VersionBinding {
        VersionBinding::new("spec-aaa", "wt-111")
    }

    fn binding_v2() -> VersionBinding {
        VersionBinding::new("spec-bbb", "wt-222")
    }

    /// BDD-PD-EVID-01 / BDD-EVID-001-01: behavioral RED logged and linked to BDD.
    #[test]
    fn tdd_evid_001_01_behavioral_red_linked_to_bdd() {
        let mut store = EvidenceStore::new();
        let cap = RunCapture::new("cargo test -p demo", "/work", 101)
            .with_stdout(
                "test case1 ... FAILED\nassertion failed: feature missing\ntest result: FAILED. 0 passed; 1 failed",
            )
            .with_cases(vec![CaseResult {
                test_id: "case1".into(),
                passed: false,
                message: "feature missing".into(),
            }]);

        let class = classify_capture(&cap);
        assert_eq!(class, OutcomeClass::BehavioralRed);
        assert!(is_valid_behavioral_red(&class));

        let rec = store
            .record_behavioral_red("ev-red-1", "BDD-EVID-001-01", binding_v1(), cap)
            .expect("valid RED");
        assert!(rec.red_qualified);
        assert_eq!(rec.bdd_id.as_deref(), Some("BDD-EVID-001-01"));
        assert_eq!(rec.verdict, EvidenceVerdict::BehavioralRed);
        assert_eq!(rec.binding, binding_v1());
        assert_eq!(store.records_for_bdd("BDD-EVID-001-01").len(), 1);
    }

    /// BDD-EVID-001-02: compile / fixture failure rejects RED qualification.
    #[test]
    fn tdd_evid_001_02_infra_rejects_red_qualification() {
        let mut store = EvidenceStore::new();
        let cap = RunCapture::new("cargo test -p demo", "/work", 101)
            .with_stderr("error: could not compile `demo`\nerror[E0425]: cannot find value")
            .with_build_ok(false);

        let class = classify_capture(&cap);
        assert!(matches!(class, OutcomeClass::InfraFailure { .. }));
        assert!(!is_valid_behavioral_red(&class));

        let err = store
            .record_behavioral_red("ev-infra-1", "BDD-EVID-001-02", binding_v1(), cap)
            .expect_err("infra must not RED-qualify");
        assert!(matches!(err, EvidError::RedNotQualified(_)));

        // Still may store as unclassified/general record for audit — classified Infra.
        let mut store2 = EvidenceStore::new();
        let cap2 = RunCapture::new("cargo test", "/work", 101)
            .with_stderr("error: could not compile `demo`")
            .with_build_ok(false);
        let rec = store2
            .record(
                "ev-infra-audit",
                Some("BDD-EVID-001-02".into()),
                binding_v1(),
                cap2,
            )
            .unwrap();
        assert!(matches!(rec.verdict, EvidenceVerdict::InfraFailure { .. }));
        assert!(!rec.red_qualified);
    }

    /// BDD-EVID-001-03: exit 0 + empty → 未測得, never PASS.
    #[test]
    fn tdd_evid_001_03_empty_exit_zero_not_pass() {
        let cap = RunCapture::new("cargo test -p demo", "/work", 0);
        let class = classify_capture(&cap);
        assert_eq!(class, OutcomeClass::NotMeasured);
        assert!(!matches!(class, OutcomeClass::Pass));

        let mut store = EvidenceStore::new();
        let rec = store
            .record("ev-empty", Some("BDD-EVID-001-03".into()), binding_v1(), cap)
            .unwrap();
        assert_eq!(rec.verdict, EvidenceVerdict::NotMeasured);
        assert!(!rec.red_qualified);

        let err = store
            .record_behavioral_red(
                "ev-empty-red",
                "BDD-EVID-001-03",
                binding_v1(),
                RunCapture::new("cargo test", "/work", 0),
            )
            .expect_err("empty cannot be RED");
        assert!(matches!(err, EvidError::RedNotQualified(_)));
    }

    /// Version binding: stale evidence does not support current green.
    #[test]
    fn evidence_binds_versions_stale_does_not_support_green() {
        let mut store = EvidenceStore::new();
        let cap = RunCapture::new("cargo test", "/work", 0)
            .with_stdout("test result: ok. 1 passed; 0 failed")
            .with_cases(vec![CaseResult {
                test_id: "case1".into(),
                passed: true,
                message: String::new(),
            }]);
        store
            .record("ev-pass-old", Some("BDD-PD-EVID-01".into()), binding_v1(), cap)
            .unwrap();

        let decision = evaluate_ready_for_green(
            &store,
            &binding_v2(),
            &["BDD-PD-EVID-01".into()],
            ProviderTerminal::Success,
        );
        match decision {
            GreenDecision::NotReady { gaps } => {
                assert!(gaps.iter().any(|g| g.contains("stale") || g.contains("BDD-PD-EVID-01")));
            }
            GreenDecision::ReadyForGreen => panic!("stale binding must not green"),
        }

        // Matching binding + Pass → ReadyForGreen.
        let ok = evaluate_ready_for_green(
            &store,
            &binding_v1(),
            &["BDD-PD-EVID-01".into()],
            ProviderTerminal::Success,
        );
        assert_eq!(ok, GreenDecision::ReadyForGreen);
    }

    /// Provider done ≠ work-item green.
    #[test]
    fn provider_done_does_not_imply_task_green() {
        assert!(!provider_success_implies_task_green(ProviderTerminal::Success));
        assert!(!provider_success_implies_task_green(ProviderTerminal::Failure));

        let store = EvidenceStore::new();
        let decision = evaluate_ready_for_green(
            &store,
            &binding_v1(),
            &["BDD-PD-EVID-01".into()],
            ProviderTerminal::Success,
        );
        assert!(matches!(decision, GreenDecision::NotReady { .. }));
    }

    /// BDD-PD-FLOW-EVID-GATE-01: missing evidence blocks FLOW Accept／Complete; gap → yellow hint.
    #[test]
    fn evid_gate_blocks_flow_accept_complete_when_gaps() {
        assert_eq!(EVIDENCE_GAP_LAMP_HINT, "yellow");

        let store = EvidenceStore::new();
        let decision = evaluate_ready_for_green(
            &store,
            &binding_v1(),
            &["BDD-PD-FLOW-EVID-GATE-01".into()],
            ProviderTerminal::Success,
        );
        assert!(!evidence_allows_flow_accept_or_complete(&decision));
        let gaps = evidence_gaps(&decision);
        assert!(gaps.iter().any(|g| g.contains("missing_evidence") || g.contains("BDD-PD-FLOW-EVID-GATE-01")));

        let mut store_ok = EvidenceStore::new();
        let cap = RunCapture::new("cargo test", "/work", 0)
            .with_stdout("test result: ok. 1 passed; 0 failed")
            .with_cases(vec![CaseResult {
                test_id: "gate".into(),
                passed: true,
                message: String::new(),
            }]);
        store_ok
            .record(
                "ev-gate-pass",
                Some("BDD-PD-FLOW-EVID-GATE-01".into()),
                binding_v1(),
                cap,
            )
            .unwrap();
        let ok = evaluate_ready_for_green(
            &store_ok,
            &binding_v1(),
            &["BDD-PD-FLOW-EVID-GATE-01".into()],
            ProviderTerminal::Success,
        );
        assert!(evidence_allows_flow_accept_or_complete(&ok));
        assert!(evidence_gaps(&ok).is_empty());
    }

    /// Three failure classes remain distinct in the store.
    #[test]
    fn three_failure_classes_not_conflated() {
        let mut store = EvidenceStore::new();
        let b = binding_v1();

        store
            .record_behavioral_red(
                "c-beh",
                "BDD-A",
                b.clone(),
                RunCapture::new("t", "/", 1)
                    .with_stdout("assertion failed")
                    .with_cases(vec![CaseResult {
                        test_id: "case1".into(),
                        passed: false,
                        message: "x".into(),
                    }]),
            )
            .unwrap();

        store
            .record(
                "c-inf",
                Some("BDD-B".into()),
                b.clone(),
                RunCapture::new("t", "/", 101)
                    .with_stderr("error: could not compile `x`")
                    .with_build_ok(false),
            )
            .unwrap();

        store
            .record(
                "c-empty",
                Some("BDD-C".into()),
                b,
                RunCapture::new("t", "/", 0),
            )
            .unwrap();

        assert_eq!(
            store.get("c-beh").unwrap().verdict,
            EvidenceVerdict::BehavioralRed
        );
        assert!(matches!(
            store.get("c-inf").unwrap().verdict,
            EvidenceVerdict::InfraFailure { .. }
        ));
        assert_eq!(
            store.get("c-empty").unwrap().verdict,
            EvidenceVerdict::NotMeasured
        );
    }

    #[test]
    fn fixture_damaged_is_infra() {
        let cap = RunCapture::new("cargo test", "/work", 1)
            .with_stderr("fixture damaged: missing cases.json");
        let class = classify_capture(&cap);
        assert!(matches!(class, OutcomeClass::InfraFailure { reason } if reason == "fixture_damaged"));
    }
}
