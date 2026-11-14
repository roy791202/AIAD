//! Green-light gate: Provider done ≠ task green; versions must bind; Pass evidence required.
//! FLOW Accept／Complete must consult this gate (PD-FLOW-EVID-GATE-01).

use crate::binding::VersionBinding;
use crate::store::{EvidenceStore, EvidenceVerdict};

/// Agent / Provider terminal state (mirrors EXEC exit success without depending on exec crate).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProviderTerminal {
    Success,
    Failure,
    Cancelled,
    Crashed,
    /// Provider has not finished.
    Running,
}

/// Result of asking whether a work item may go green.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GreenDecision {
    /// All required BDDs have Pass evidence bound to current versions.
    ReadyForGreen,
    /// Missing / stale / non-Pass evidence — keep yellow/red; do **not** admin-green.
    NotReady { gaps: Vec<String> },
}

/// Product lamp hint when EVID gaps block Accept／Complete (never `"green"`).
pub const EVIDENCE_GAP_LAMP_HINT: &str = "yellow";

/// Whether FLOW Accept／Complete may proceed (PD-FLOW-EVID-GATE-01).
///
/// `ReadyForGreen` → true; any gap → false (caller rejects and keeps yellow).
pub fn evidence_allows_flow_accept_or_complete(decision: &GreenDecision) -> bool {
    matches!(decision, GreenDecision::ReadyForGreen)
}

/// Extract gap strings for reject messages (empty when ready).
pub fn evidence_gaps(decision: &GreenDecision) -> Vec<String> {
    match decision {
        GreenDecision::ReadyForGreen => Vec::new(),
        GreenDecision::NotReady { gaps } => gaps.clone(),
    }
}

/// Evaluate READY_FOR_GREEN from evidence only.
///
/// Rules:
/// - Provider [`ProviderTerminal::Success`] alone never yields ReadyForGreen.
/// - Every `required_bdd` must have a latest matching Pass under `current` binding.
/// - Skipped / NotMeasured / Infra / BehavioralRed / missing → gap.
pub fn evaluate_ready_for_green(
    store: &EvidenceStore,
    current: &VersionBinding,
    required_bdd: &[String],
    provider: ProviderTerminal,
) -> GreenDecision {
    let mut gaps: Vec<String> = Vec::new();

    // Explicit: Provider done ≠ green. Even on Success we still require evidence.
    if matches!(
        provider,
        ProviderTerminal::Running
            | ProviderTerminal::Failure
            | ProviderTerminal::Cancelled
            | ProviderTerminal::Crashed
    ) {
        // Running / failed provider is a gap, but Success still needs evidence below.
        if !matches!(provider, ProviderTerminal::Running) {
            gaps.push(format!("provider_terminal:{provider:?}"));
        } else {
            gaps.push("provider_still_running".into());
        }
    }

    for bdd in required_bdd {
        match store.latest_matching(bdd, current) {
            Some(rec) if matches!(rec.verdict, EvidenceVerdict::Pass) => {}
            Some(rec) => {
                gaps.push(format!(
                    "{bdd}:verdict={:?}:binding_ok={}",
                    rec.verdict,
                    rec.binding.matches_current(current)
                ));
            }
            None => {
                // Check if stale evidence exists under a different binding.
                let any = store.records_for_bdd(bdd);
                if any.is_empty() {
                    gaps.push(format!("{bdd}:missing_evidence"));
                } else {
                    gaps.push(format!("{bdd}:stale_or_unbound"));
                }
            }
        }
    }

    // Provider Success with empty required list still not green without an explicit policy —
    // empty required_bdd + Success → Ready only if we treat "nothing required" as ready.
    // Product rule: Provider done ≠ green; if nothing required, still NotReady unless
    // caller passes required list that is satisfied. Empty required + Success → ReadyForGreen
    // would let "provider done" sneak through. Force at least one gap when required is empty
    // AND we only have provider success.
    if required_bdd.is_empty() {
        gaps.push("no_required_bdd_cannot_green".into());
    }

    if gaps.is_empty() {
        GreenDecision::ReadyForGreen
    } else {
        GreenDecision::NotReady { gaps }
    }
}

/// Convenience: Provider Success alone never greens a task.
pub fn provider_success_implies_task_green(provider: ProviderTerminal) -> bool {
    let _ = provider;
    false
}
