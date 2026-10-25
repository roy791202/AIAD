//! SGenAxis **GUARD** (PD-GUARD-01) — envelope／path allow vs protect gate.
//!
//! Pure Rust library: no Tauri, no OS ports, no Agent adapters.
//!
//! ```text
//! check_start_implementation(envelope, red)
//!   → Allow { envelope_hash } | Reject { reasons[] }
//!
//! check_changes(envelope, paths)
//!   → protect wins over allow; MODULE_BOUNDARY_ESCAPE; PATH_TRAVERSAL
//! ```
//!
//! BDD: `BDD-PD-GUARD-01` — 未核准或越界路徑不得啟動產品實作；拒絕原因可追溯。
//! Maps product-plan GUARD-001 scenarios (approval／RED／module boundary).

#![forbid(unsafe_code)]

mod envelope;
mod gate;
mod path_gate;
mod reason;

pub use envelope::{Envelope, RedEvidence, RedKind};
pub use gate::{
    check_changes, check_implementation_request, check_start_implementation, GuardDecision,
};
pub use path_gate::{has_traversal, normalize_path, path_matches};
pub use reason::{RejectCode, RejectReason};

#[cfg(test)]
mod tests {
    use super::*;

    /// Fixture envelope aligned with GUARD-001 allowed_scope + foreign module B.
    fn guard_envelope() -> Envelope {
        Envelope::new("GUARD-001", "GUARD")
            .with_approved(true)
            .with_allowed([
                "packages/guard/**",
                "tests/guard/**",
                // Intentionally lists a foreign-module file (boundary escape case).
                "packages/B/foreign.rs",
            ])
            .with_protected([
                "contracts/approved.json",
                "docs/PRODUCT-DEVELOPMENT.md",
            ])
            .with_module_prefix("GUARD", "packages/guard")
            .with_module_prefix("B", "packages/B")
    }

    // —— BDD-PD-GUARD-01 / BDD-GUARD-001-01 ——
    #[test]
    fn tdd_guard_001_01_approved_behavioral_red_allows_with_hash() {
        let env = guard_envelope();
        let red = RedEvidence::behavioral();
        let decision = check_start_implementation(&env, &red);
        assert!(decision.is_allow(), "expected allow, got {decision:?}");
        let hash = decision.envelope_hash().expect("hash");
        assert_eq!(hash, env.hash());
        assert_eq!(hash.len(), 16);
        assert!(decision.traces().is_empty());
    }

    // —— BDD-GUARD-001-02 ——
    #[test]
    fn tdd_guard_001_02_unapproved_rejects_with_not_approved() {
        let env = guard_envelope().with_approved(false);
        let decision = check_start_implementation(&env, &RedEvidence::behavioral());
        assert!(decision.is_reject());
        assert!(decision.has_code(RejectCode::NotApproved));
        let traces = decision.traces();
        assert!(
            traces.iter().any(|t| t.starts_with("NOT_APPROVED:")),
            "traces={traces:?}"
        );
    }

    #[test]
    fn tdd_guard_001_02_compile_error_red_rejects_with_invalid_red() {
        let env = guard_envelope();
        let decision = check_start_implementation(&env, &RedEvidence::compile_error());
        assert!(decision.is_reject());
        assert!(decision.has_code(RejectCode::InvalidRed));
        assert!(decision
            .traces()
            .iter()
            .any(|t| t.starts_with("INVALID_RED:")));
    }

    #[test]
    fn tdd_guard_001_02_both_gates_fail_accumulate_reasons() {
        let env = guard_envelope().with_approved(false);
        let decision = check_start_implementation(&env, &RedEvidence::compile_error());
        assert!(decision.has_code(RejectCode::NotApproved));
        assert!(decision.has_code(RejectCode::InvalidRed));
        assert_eq!(decision.reasons().len(), 2);
    }

    // —— BDD-GUARD-001-03 ——
    #[test]
    fn tdd_guard_001_03_foreign_module_without_integration_is_boundary_escape() {
        let env = guard_envelope(); // integration_modules empty
        let decision = check_changes(&env, &["packages/B/foreign.rs"]);
        assert!(decision.is_reject());
        assert!(
            decision.has_code(RejectCode::ModuleBoundaryEscape),
            "got {:?}",
            decision.traces()
        );
        assert!(decision
            .traces()
            .iter()
            .any(|t| t.contains("MODULE_BOUNDARY_ESCAPE")));
    }

    #[test]
    fn foreign_module_allowed_when_integration_declared() {
        let env = guard_envelope().with_integration(["B"]);
        let decision = check_changes(&env, &["packages/B/foreign.rs"]);
        assert!(
            decision.is_allow(),
            "expected allow after integration, got {:?}",
            decision.traces()
        );
    }

    // —— Path allow vs protect ——
    #[test]
    fn allow_path_inside_scope_passes() {
        let env = guard_envelope();
        let decision = check_changes(&env, &["packages/guard/src/lib.rs"]);
        assert!(decision.is_allow(), "{:?}", decision.traces());
    }

    #[test]
    fn protect_wins_over_allow() {
        // Even if someone adds a protected path to allowed_paths, protect wins.
        let env = guard_envelope().with_allowed([
            "packages/guard/**",
            "contracts/approved.json",
        ]);
        let decision = check_changes(&env, &["contracts/approved.json"]);
        assert!(decision.has_code(RejectCode::PathProtected));
        assert!(decision
            .traces()
            .iter()
            .any(|t| t.starts_with("PATH_PROTECTED:")));
    }

    #[test]
    fn path_outside_allowlist_rejected() {
        let env = guard_envelope();
        let decision = check_changes(&env, &["apps/sgenaxis-desktop/src-tauri/src/lib.rs"]);
        assert!(decision.has_code(RejectCode::PathNotAllowed));
    }

    #[test]
    fn path_traversal_rejected() {
        let env = guard_envelope();
        let decision = check_changes(&env, &["../other-project/secret.rs"]);
        assert!(decision.has_code(RejectCode::PathTraversal));
    }

    #[test]
    fn combined_request_rejects_unapproved_before_paths() {
        let env = guard_envelope().with_approved(false);
        let decision = check_implementation_request(
            &env,
            &RedEvidence::behavioral(),
            &["packages/guard/src/lib.rs"],
        );
        assert!(decision.is_reject());
        assert!(decision.has_code(RejectCode::NotApproved));
        assert!(!decision.is_allow());
    }

    #[test]
    fn combined_request_allows_when_all_gates_pass() {
        let env = guard_envelope();
        let decision = check_implementation_request(
            &env,
            &RedEvidence::behavioral(),
            &["packages/guard/src/gate.rs", "tests/guard/smoke.rs"],
        );
        assert!(decision.is_allow(), "{:?}", decision.traces());
        assert_eq!(decision.envelope_hash(), Some(env.hash().as_str()));
    }

    #[test]
    fn envelope_hash_stable_for_same_fields() {
        let a = guard_envelope();
        let b = guard_envelope();
        assert_eq!(a.hash(), b.hash());
    }

    #[test]
    fn envelope_hash_changes_when_approval_flips() {
        let a = guard_envelope();
        let b = guard_envelope().with_approved(false);
        assert_ne!(a.hash(), b.hash());
    }

    #[test]
    fn reject_reasons_are_display_traceable() {
        let r = RejectReason::new(RejectCode::ModuleBoundaryEscape, "packages/B/x.rs");
        assert_eq!(r.to_string(), "MODULE_BOUNDARY_ESCAPE:packages/B/x.rs");
        assert_eq!(RejectCode::ModuleBoundaryEscape.as_str(), "MODULE_BOUNDARY_ESCAPE");
    }
}
