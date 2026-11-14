//! PD-GUARD-CMD-01 — HOST／command façade over [`sgenaxis_guard`].
//!
//! Tauri／Dispatch call these helpers before EXEC start or write paths.
//! Rejects surface as stable `CODE:detail` traces (BDD-PD-GUARD-CMD-01).
//!
//! Also defines a **minimal EXEC-BIND seam** ([`GuardExecPass`]) so
//! `start_implementation` can hand a pass to the start path while
//! PD-EXEC-BIND-01 lands concurrently.

use serde::{Deserialize, Serialize};
use sgenaxis_guard::{
    check_changes, check_implementation_request, check_start_implementation, Envelope,
    GuardDecision, RedEvidence, RedKind,
};

/// IPC／command view of a GUARD decision.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GuardDecisionView {
    pub allowed: bool,
    pub envelope_hash: Option<String>,
    /// Traceable rejection tokens (`CODE:detail`); empty when allowed.
    pub reasons: Vec<String>,
}

impl GuardDecisionView {
    pub fn from_decision(d: &GuardDecision) -> Self {
        match d {
            GuardDecision::Allow { envelope_hash } => Self {
                allowed: true,
                envelope_hash: Some(envelope_hash.clone()),
                reasons: Vec::new(),
            },
            GuardDecision::Reject { reasons } => Self {
                allowed: false,
                envelope_hash: None,
                reasons: reasons.iter().map(|r| r.trace()).collect(),
            },
        }
    }

    /// Join reasons for `Result::Err` surfaces (`CODE:detail; CODE:detail`).
    pub fn reject_message(&self) -> String {
        if self.reasons.is_empty() {
            "GUARD_REJECTED:unknown".into()
        } else {
            self.reasons.join("; ")
        }
    }
}

/// Envelope fields accepted from UI／Dispatch (no OS).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EnvelopeDto {
    pub id: String,
    pub approved: bool,
    pub primary_module: String,
    #[serde(default)]
    pub integration_modules: Vec<String>,
    #[serde(default)]
    pub allowed_paths: Vec<String>,
    #[serde(default)]
    pub protected_paths: Vec<String>,
    /// `(module, path_prefix)` pairs for boundary escape detection.
    #[serde(default)]
    pub module_path_prefixes: Vec<(String, String)>,
}

impl EnvelopeDto {
    pub fn to_envelope(&self) -> Envelope {
        let mut env = Envelope::new(&self.id, &self.primary_module)
            .with_approved(self.approved)
            .with_allowed(self.allowed_paths.clone())
            .with_protected(self.protected_paths.clone())
            .with_integration(self.integration_modules.clone());
        for (module, prefix) in &self.module_path_prefixes {
            env = env.with_module_prefix(module, prefix);
        }
        env
    }
}

/// RED evidence kind for IPC (`behavioral`｜`compile_error`｜`environment_fault`｜`missing`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum RedKindDto {
    Behavioral,
    CompileError,
    EnvironmentFault,
    Missing,
}

impl RedKindDto {
    pub fn to_red(&self) -> RedEvidence {
        let kind = match self {
            RedKindDto::Behavioral => RedKind::Behavioral,
            RedKindDto::CompileError => RedKind::CompileError,
            RedKindDto::EnvironmentFault => RedKind::EnvironmentFault,
            RedKindDto::Missing => RedKind::Missing,
        };
        RedEvidence { kind }
    }
}

/// Packet for start／write GUARD checks.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GuardPacketDto {
    pub envelope: EnvelopeDto,
    pub red: RedKindDto,
    /// Proposed change paths (empty → start-only gate).
    #[serde(default)]
    pub change_paths: Vec<String>,
}

/// Pass token after GUARD allow — minimal seam for PD-EXEC-BIND-01.
///
/// EXEC start path consumes／clears this. Bind API may later attach
/// project_root／work_item／fingerprint; this card only guarantees GUARD ran.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GuardExecPass {
    pub envelope_hash: String,
    pub work_item_id: Option<String>,
}

/// Start-implementation gate (approval + behavioral RED).
pub fn check_start_view(packet: &GuardPacketDto) -> GuardDecisionView {
    let env = packet.envelope.to_envelope();
    let red = packet.red.to_red();
    GuardDecisionView::from_decision(&check_start_implementation(&env, &red))
}

/// Pre-write／change-path gate (protect wins; `CODE:detail` on reject).
pub fn check_changes_view(packet: &GuardPacketDto) -> GuardDecisionView {
    let env = packet.envelope.to_envelope();
    GuardDecisionView::from_decision(&check_changes(&env, &packet.change_paths))
}

/// Combined gate used before EXEC／write authorization.
pub fn check_implementation_view(packet: &GuardPacketDto) -> GuardDecisionView {
    let env = packet.envelope.to_envelope();
    let red = packet.red.to_red();
    GuardDecisionView::from_decision(&check_implementation_request(
        &env,
        &red,
        &packet.change_paths,
    ))
}

/// Authorize EXEC start: Ok(pass) or Err with `CODE:detail` message.
pub fn authorize_exec_start(
    packet: &GuardPacketDto,
    work_item_id: Option<String>,
) -> Result<GuardExecPass, String> {
    let view = if packet.change_paths.is_empty() {
        check_start_view(packet)
    } else {
        check_implementation_view(packet)
    };
    if view.allowed {
        Ok(GuardExecPass {
            envelope_hash: view
                .envelope_hash
                .clone()
                .unwrap_or_else(|| packet.envelope.to_envelope().hash()),
            work_item_id,
        })
    } else {
        Err(view.reject_message())
    }
}

/// Authorize write／change paths: Ok(()) or Err with `CODE:detail`.
pub fn authorize_write_paths(packet: &GuardPacketDto) -> Result<(), String> {
    let view = check_changes_view(packet);
    if view.allowed {
        Ok(())
    } else {
        Err(view.reject_message())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_packet(approved: bool) -> GuardPacketDto {
        GuardPacketDto {
            envelope: EnvelopeDto {
                id: "GUARD-CMD-01".into(),
                approved,
                primary_module: "GUARD".into(),
                integration_modules: vec![],
                allowed_paths: vec!["packages/guard/**".into(), "tests/guard/**".into()],
                protected_paths: vec![
                    "contracts/approved.json".into(),
                    "docs/PRODUCT-DEVELOPMENT.md".into(),
                ],
                module_path_prefixes: vec![("GUARD".into(), "packages/guard".into())],
            },
            red: RedKindDto::Behavioral,
            change_paths: vec![],
        }
    }

    #[test]
    fn unapproved_start_rejects_with_not_approved_code_detail() {
        let view = check_start_view(&sample_packet(false));
        assert!(!view.allowed);
        assert!(
            view.reasons.iter().any(|r| r.starts_with("NOT_APPROVED:")),
            "reasons={:?}",
            view.reasons
        );
        let err = authorize_exec_start(&sample_packet(false), None).unwrap_err();
        assert!(err.contains("NOT_APPROVED:"), "{err}");
    }

    #[test]
    fn approved_behavioral_allows_exec_pass() {
        let pass = authorize_exec_start(&sample_packet(true), Some("w1".into())).unwrap();
        assert!(!pass.envelope_hash.is_empty());
        assert_eq!(pass.work_item_id.as_deref(), Some("w1"));
    }

    #[test]
    fn protected_path_rejects_with_path_protected_code_detail() {
        let mut packet = sample_packet(true);
        packet.change_paths = vec!["contracts/approved.json".into()];
        let view = check_changes_view(&packet);
        assert!(!view.allowed);
        assert!(
            view.reasons
                .iter()
                .any(|r| r.starts_with("PATH_PROTECTED:")),
            "reasons={:?}",
            view.reasons
        );
        let err = authorize_write_paths(&packet).unwrap_err();
        assert!(err.contains("PATH_PROTECTED:"), "{err}");
    }

    #[test]
    fn allow_path_passes_write_gate() {
        let mut packet = sample_packet(true);
        packet.change_paths = vec!["packages/guard/src/lib.rs".into()];
        assert!(authorize_write_paths(&packet).is_ok());
        let view = check_implementation_view(&packet);
        assert!(view.allowed, "{:?}", view.reasons);
    }

    #[test]
    fn invalid_red_rejects_exec() {
        let mut packet = sample_packet(true);
        packet.red = RedKindDto::CompileError;
        let err = authorize_exec_start(&packet, None).unwrap_err();
        assert!(err.contains("INVALID_RED:"), "{err}");
    }
}
