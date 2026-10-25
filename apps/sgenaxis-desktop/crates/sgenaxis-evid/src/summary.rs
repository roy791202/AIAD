//! Read-only Inspector evidence summary projection (PD-EVID-UI-01).
//!
//! Pure: no Tauri, no board zone mutation. Provider Success never implies product green.

use crate::binding::VersionBinding;
use crate::gate::{
    evaluate_ready_for_green, provider_success_implies_task_green, GreenDecision, ProviderTerminal,
};
use crate::store::{EvidenceStore, EvidenceVerdict};

/// One BDD line in the Inspector evidence block.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvidenceSummaryLine {
    pub bdd_id: String,
    /// Display status: `NOT RUN`｜`未測`｜`PASS`｜`RED`｜`INFRA`｜`STALE`.
    pub status_label: String,
    /// Machine key for UI／tests.
    pub verdict_key: String,
}

/// Inspector projection for a selected work item.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InspectorEvidenceSummary {
    pub work_item_id: String,
    pub provider_terminal: String,
    /// Always `false` — Provider Success ≠ product green (BDD-PD-EVID-UI-01).
    pub provider_success_implies_green: bool,
    /// Hint for product lamp; **never** `"green"` from Provider Success alone.
    /// `ReadyForGreen` still yields `"yellow"` (awaiting admin extinguish).
    pub product_lamp_hint: String,
    pub ready_for_green: bool,
    /// Overall: empty evidence → `NOT RUN`／`未測`.
    pub overall_status: String,
    pub gaps: Vec<String>,
    pub lines: Vec<EvidenceSummaryLine>,
}

fn provider_label(p: ProviderTerminal) -> &'static str {
    match p {
        ProviderTerminal::Success => "Success",
        ProviderTerminal::Failure => "Failure",
        ProviderTerminal::Cancelled => "Cancelled",
        ProviderTerminal::Crashed => "Crashed",
        ProviderTerminal::Running => "Running",
    }
}

fn line_for_bdd(
    store: &EvidenceStore,
    bdd_id: &str,
    current: &VersionBinding,
) -> EvidenceSummaryLine {
    match store.latest_matching(bdd_id, current) {
        Some(rec) => {
            let (status_label, verdict_key) = match &rec.verdict {
                EvidenceVerdict::Pass => ("PASS".into(), "pass".into()),
                EvidenceVerdict::BehavioralRed => ("RED".into(), "behavioral_red".into()),
                EvidenceVerdict::InfraFailure { .. } => ("INFRA".into(), "infra".into()),
                EvidenceVerdict::NotMeasured => ("未測".into(), "not_measured".into()),
            };
            EvidenceSummaryLine {
                bdd_id: bdd_id.into(),
                status_label,
                verdict_key,
            }
        }
        None => {
            let any = store.records_for_bdd(bdd_id);
            if any.is_empty() {
                EvidenceSummaryLine {
                    bdd_id: bdd_id.into(),
                    status_label: "NOT RUN".into(),
                    verdict_key: "not_run".into(),
                }
            } else {
                EvidenceSummaryLine {
                    bdd_id: bdd_id.into(),
                    status_label: "STALE".into(),
                    verdict_key: "stale".into(),
                }
            }
        }
    }
}

fn overall_from_lines(lines: &[EvidenceSummaryLine], ready: bool) -> String {
    if lines.is_empty() {
        return "NOT RUN".into();
    }
    if lines
        .iter()
        .all(|l| l.verdict_key == "not_run" || l.verdict_key == "not_measured")
    {
        // Prefer 未測 when any NotMeasured; else NOT RUN.
        if lines.iter().any(|l| l.verdict_key == "not_measured") {
            return "未測".into();
        }
        return "NOT RUN".into();
    }
    if ready {
        return "READY_FOR_GREEN".into();
    }
    if lines.iter().any(|l| l.verdict_key == "behavioral_red") {
        return "RED".into();
    }
    if lines.iter().any(|l| l.verdict_key == "infra") {
        return "INFRA".into();
    }
    if lines.iter().any(|l| l.verdict_key == "stale") {
        return "STALE".into();
    }
    "PARTIAL".into()
}

fn lamp_hint(ready: bool, lines: &[EvidenceSummaryLine], provider: ProviderTerminal) -> String {
    // HARD: Provider Success must not auto-green the product lamp.
    let _ = provider;
    if ready {
        return "yellow".into();
    }
    if lines.iter().any(|l| l.verdict_key == "behavioral_red") {
        return "red".into();
    }
    if lines
        .iter()
        .all(|l| l.verdict_key == "not_run" || l.verdict_key == "not_measured")
        || lines.is_empty()
    {
        return "gray".into();
    }
    "yellow".into()
}

/// Project a read-only evidence summary for Inspector (PD-EVID-UI-01).
///
/// - Empty／missing evidence → overall `NOT RUN` or `未測`.
/// - [`provider_success_implies_task_green`] is always reflected as `false`.
/// - `product_lamp_hint` is never `"green"` from this path.
pub fn project_inspector_evidence(
    store: &EvidenceStore,
    work_item_id: &str,
    current: &VersionBinding,
    required_bdd: &[String],
    provider: ProviderTerminal,
) -> InspectorEvidenceSummary {
    let decision = evaluate_ready_for_green(store, current, required_bdd, provider);
    let (ready, gaps) = match decision {
        GreenDecision::ReadyForGreen => (true, Vec::new()),
        GreenDecision::NotReady { gaps } => (false, gaps),
    };

    let lines: Vec<EvidenceSummaryLine> = if required_bdd.is_empty() {
        // No required BDD → still show empty-evidence state for the work item.
        vec![EvidenceSummaryLine {
            bdd_id: "(none)".into(),
            status_label: "NOT RUN".into(),
            verdict_key: "not_run".into(),
        }]
    } else {
        required_bdd
            .iter()
            .map(|b| line_for_bdd(store, b, current))
            .collect()
    };

    InspectorEvidenceSummary {
        work_item_id: work_item_id.into(),
        provider_terminal: provider_label(provider).into(),
        provider_success_implies_green: provider_success_implies_task_green(provider),
        product_lamp_hint: lamp_hint(ready, &lines, provider),
        ready_for_green: ready,
        overall_status: overall_from_lines(&lines, ready),
        gaps,
        lines,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capture::{CaseResult, RunCapture};

    fn binding() -> VersionBinding {
        VersionBinding::new("spec-1", "wt-1")
    }

    #[test]
    fn empty_evidence_shows_not_run() {
        let store = EvidenceStore::new();
        let s = project_inspector_evidence(
            &store,
            "task-1",
            &binding(),
            &["BDD-A".into()],
            ProviderTerminal::Running,
        );
        assert_eq!(s.overall_status, "NOT RUN");
        assert_eq!(s.lines[0].status_label, "NOT RUN");
        assert_eq!(s.product_lamp_hint, "gray");
        assert!(!s.ready_for_green);
        assert!(!s.provider_success_implies_green);
        assert_ne!(s.product_lamp_hint, "green");
    }

    #[test]
    fn provider_success_does_not_auto_green() {
        let store = EvidenceStore::new();
        let s = project_inspector_evidence(
            &store,
            "task-1",
            &binding(),
            &["BDD-A".into()],
            ProviderTerminal::Success,
        );
        assert!(!s.provider_success_implies_green);
        assert!(!s.ready_for_green);
        assert_ne!(s.product_lamp_hint, "green");
        assert_eq!(s.overall_status, "NOT RUN");
        assert_eq!(s.provider_terminal, "Success");
    }

    #[test]
    fn not_measured_shows_wei_ce() {
        let mut store = EvidenceStore::new();
        store
            .record(
                "ev-empty",
                Some("BDD-A".into()),
                binding(),
                RunCapture::new("cargo test", "/w", 0),
            )
            .unwrap();
        let s = project_inspector_evidence(
            &store,
            "task-1",
            &binding(),
            &["BDD-A".into()],
            ProviderTerminal::Success,
        );
        assert_eq!(s.lines[0].status_label, "未測");
        assert_eq!(s.overall_status, "未測");
        assert_ne!(s.product_lamp_hint, "green");
    }

    #[test]
    fn pass_evidence_ready_for_green_stays_yellow_lamp() {
        let mut store = EvidenceStore::new();
        store
            .record(
                "ev-pass",
                Some("BDD-A".into()),
                binding(),
                RunCapture::new("cargo test", "/w", 0)
                    .with_stdout("test result: ok. 1 passed; 0 failed")
                    .with_cases(vec![CaseResult {
                        test_id: "c1".into(),
                        passed: true,
                        message: String::new(),
                    }]),
            )
            .unwrap();
        let s = project_inspector_evidence(
            &store,
            "task-1",
            &binding(),
            &["BDD-A".into()],
            ProviderTerminal::Success,
        );
        assert!(s.ready_for_green);
        assert_eq!(s.overall_status, "READY_FOR_GREEN");
        assert_eq!(s.product_lamp_hint, "yellow");
        assert!(!s.provider_success_implies_green);
        assert_ne!(s.product_lamp_hint, "green");
    }

    #[test]
    fn empty_required_bdd_still_not_run() {
        let store = EvidenceStore::new();
        let s = project_inspector_evidence(
            &store,
            "task-x",
            &binding(),
            &[],
            ProviderTerminal::Success,
        );
        assert_eq!(s.overall_status, "NOT RUN");
        assert!(!s.provider_success_implies_green);
        assert_ne!(s.product_lamp_hint, "green");
    }
}
