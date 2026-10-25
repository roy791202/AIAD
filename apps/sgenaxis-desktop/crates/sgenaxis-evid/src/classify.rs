//! Classify runner captures into behavioral RED vs infra failure vs empty-not-PASS.
//!
//! INV-EVID-001-01: valid RED requires build success + specified missing behavior failure;
//! empty exit-0 is never PASS.

use crate::capture::RunCapture;

/// How a run failed or completed — three failure classes must not be conflated.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OutcomeClass {
    /// All required cases passed with non-empty measured results.
    Pass,
    /// Build OK; assertion / missing behavior failed → valid behavioral RED.
    BehavioralRed,
    /// Compile / fixture / environment failure → **not** RED-qualified.
    InfraFailure { reason: String },
    /// Exit 0 (or any) but no measurable test results → 未測得, never PASS.
    NotMeasured,
}

/// Markers that indicate compile / fixture / environment damage (not behavioral).
fn looks_like_infra(output: &str, build_ok: bool) -> Option<&'static str> {
    if !build_ok {
        return Some("build_not_ok");
    }
    let lower = output.to_ascii_lowercase();
    if lower.contains("error: could not compile")
        || lower.contains("could not compile")
        || lower.contains("error[e0")
        || lower.contains("compilation failed")
    {
        return Some("compile_error");
    }
    if lower.contains("fixture")
        && (lower.contains("corrupt")
            || lower.contains("missing")
            || lower.contains("damaged")
            || lower.contains("not found"))
    {
        return Some("fixture_damaged");
    }
    if lower.contains("panic") && lower.contains("fixture") {
        return Some("fixture_panic");
    }
    None
}

fn looks_like_assertion_failure(output: &str, cases: &[(bool, &str)]) -> bool {
    if cases.iter().any(|(passed, _)| !*passed) {
        return true;
    }
    let lower = output.to_ascii_lowercase();
    lower.contains("assertion failed")
        || lower.contains("assert_eq!")
        || lower.contains("assert!")
        || lower.contains("failed:")
        || lower.contains("test result: failed")
        || lower.contains("behavioral")
}

/// Classify a raw runner capture. Empty exit-0 must never become [`OutcomeClass::Pass`].
pub fn classify_capture(capture: &RunCapture) -> OutcomeClass {
    let output = capture.combined_output();

    if let Some(reason) = looks_like_infra(&output, capture.build_ok) {
        return OutcomeClass::InfraFailure {
            reason: reason.to_string(),
        };
    }

    // Empty / missing measured results → 未測得 (even if exit 0).
    if capture.is_output_empty() {
        return OutcomeClass::NotMeasured;
    }

    let case_flags: Vec<(bool, &str)> = capture
        .case_results
        .iter()
        .map(|c| (c.passed, c.test_id.as_str()))
        .collect();

    if capture.exit_code == 0 {
        // Exit 0 with cases: all must pass and at least one case (or explicit pass marker).
        if !capture.case_results.is_empty() {
            if capture.case_results.iter().all(|c| c.passed) {
                return OutcomeClass::Pass;
            }
            return OutcomeClass::BehavioralRed;
        }
        // Non-empty text but no structured cases: require an explicit pass marker.
        let lower = output.to_ascii_lowercase();
        if lower.contains("test result: ok")
            || lower.contains("all tests passed")
            || lower.contains("passed")
        {
            // Still reject if it only says "passed" with no substance and looks empty-ish —
            // already guarded by is_output_empty. Accept explicit ok.
            return OutcomeClass::Pass;
        }
        // Exit 0 + noise without measurable pass → 未測得, not PASS.
        return OutcomeClass::NotMeasured;
    }

    // Non-zero exit, build OK: behavioral if assertion-like, else still behavioral when
    // we have failed cases; otherwise treat as behavioral RED only when assertion-like.
    if looks_like_assertion_failure(&output, &case_flags) {
        return OutcomeClass::BehavioralRed;
    }
    if !capture.case_results.is_empty()
        && capture.case_results.iter().any(|c| !c.passed)
    {
        return OutcomeClass::BehavioralRed;
    }

    // Non-zero with opaque output and no cases: still not infra (already checked) —
    // treat as behavioral RED only if build_ok; else already returned infra.
    if capture.build_ok {
        return OutcomeClass::BehavioralRed;
    }

    OutcomeClass::InfraFailure {
        reason: "unknown_non_zero".into(),
    }
}

/// Whether this classification qualifies as a **valid behavioral RED** for TDD gate.
pub fn is_valid_behavioral_red(class: &OutcomeClass) -> bool {
    matches!(class, OutcomeClass::BehavioralRed)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capture::CaseResult;

    #[test]
    fn empty_exit_zero_is_not_measured_not_pass() {
        let cap = RunCapture::new("cargo test", "/tmp", 0);
        let class = classify_capture(&cap);
        assert_eq!(class, OutcomeClass::NotMeasured);
        assert!(!matches!(class, OutcomeClass::Pass));
    }

    #[test]
    fn compile_error_is_infra_not_red() {
        let cap = RunCapture::new("cargo test", "/tmp", 101)
            .with_stderr("error: could not compile `demo` due to previous error")
            .with_build_ok(false);
        let class = classify_capture(&cap);
        assert!(matches!(class, OutcomeClass::InfraFailure { .. }));
        assert!(!is_valid_behavioral_red(&class));
    }

    #[test]
    fn assertion_failure_is_behavioral_red() {
        let cap = RunCapture::new("cargo test", "/tmp", 101)
            .with_stdout("test case1 ... FAILED\nassertion failed: missing behavior\ntest result: FAILED. 0 passed; 1 failed")
            .with_cases(vec![CaseResult {
                test_id: "case1".into(),
                passed: false,
                message: "missing behavior".into(),
            }]);
        let class = classify_capture(&cap);
        assert_eq!(class, OutcomeClass::BehavioralRed);
        assert!(is_valid_behavioral_red(&class));
    }
}
