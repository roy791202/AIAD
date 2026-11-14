//! Start-implementation and change-path gates (INV-GUARD-001-01).

use crate::envelope::{Envelope, RedEvidence};
use crate::path_gate::{has_traversal, matches_any, normalize_path};
use crate::reason::{RejectCode, RejectReason};

/// Outcome of a GUARD check — allow carries envelope hash; reject carries reasons.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GuardDecision {
    Allow { envelope_hash: String },
    Reject { reasons: Vec<RejectReason> },
}

impl GuardDecision {
    pub fn is_allow(&self) -> bool {
        matches!(self, GuardDecision::Allow { .. })
    }

    pub fn is_reject(&self) -> bool {
        matches!(self, GuardDecision::Reject { .. })
    }

    pub fn reasons(&self) -> &[RejectReason] {
        match self {
            GuardDecision::Allow { .. } => &[],
            GuardDecision::Reject { reasons } => reasons,
        }
    }

    pub fn envelope_hash(&self) -> Option<&str> {
        match self {
            GuardDecision::Allow { envelope_hash } => Some(envelope_hash.as_str()),
            GuardDecision::Reject { .. } => None,
        }
    }

    /// All rejection traces (`CODE:detail`), empty when allowed.
    pub fn traces(&self) -> Vec<String> {
        self.reasons().iter().map(RejectReason::trace).collect()
    }

    pub fn has_code(&self, code: RejectCode) -> bool {
        self.reasons().iter().any(|r| r.code == code)
    }
}

fn reject(reasons: Vec<RejectReason>) -> GuardDecision {
    GuardDecision::Reject { reasons }
}

fn allow(env: &Envelope) -> GuardDecision {
    GuardDecision::Allow {
        envelope_hash: env.hash(),
    }
}

/// Gate: may the executor start product implementation for this envelope?
///
/// Requires `approved` + valid behavioral RED. Does not check paths
/// (use [`check_changes`] for path allow／protect／boundary).
pub fn check_start_implementation(env: &Envelope, red: &RedEvidence) -> GuardDecision {
    let mut reasons = Vec::new();

    if !env.approved {
        reasons.push(RejectReason::new(
            RejectCode::NotApproved,
            format!("envelope {} is not approved", env.id),
        ));
    }

    if !red.kind.is_valid_for_implementation() {
        reasons.push(RejectReason::new(
            RejectCode::InvalidRed,
            format!(
                "RED kind {:?} is not a valid behavioral RED for envelope {}",
                red.kind, env.id
            ),
        ));
    }

    if reasons.is_empty() {
        allow(env)
    } else {
        reject(reasons)
    }
}

/// Gate: proposed change paths against allow／protect／module boundary.
///
/// Rules (INV-GUARD-001-01):
/// 1. Traversal (`..`) → `PATH_TRAVERSAL`
/// 2. Protect match → `PATH_PROTECTED` (wins over allow)
/// 3. Foreign module path without declared integration → `MODULE_BOUNDARY_ESCAPE`
/// 4. Not on allowlist → `PATH_NOT_ALLOWED`
pub fn check_changes(env: &Envelope, paths: &[impl AsRef<str>]) -> GuardDecision {
    let mut reasons = Vec::new();

    for path in paths {
        let raw = path.as_ref();
        let norm = normalize_path(raw);

        if has_traversal(raw) {
            reasons.push(RejectReason::new(
                RejectCode::PathTraversal,
                format!("path '{raw}' contains '..'"),
            ));
            continue;
        }

        if matches_any(&env.protected_paths, &norm) {
            reasons.push(RejectReason::new(
                RejectCode::PathProtected,
                format!("path '{norm}' is protected"),
            ));
            continue;
        }

        if let Some(foreign) = foreign_module_without_integration(env, &norm) {
            reasons.push(RejectReason::new(
                RejectCode::ModuleBoundaryEscape,
                format!(
                    "path '{norm}' belongs to module '{foreign}' without integration scope"
                ),
            ));
            continue;
        }

        if !matches_any(&env.allowed_paths, &norm) {
            reasons.push(RejectReason::new(
                RejectCode::PathNotAllowed,
                format!("path '{norm}' is outside allowed_scope"),
            ));
        }
    }

    if reasons.is_empty() {
        allow(env)
    } else {
        reject(reasons)
    }
}

/// Combined gate used by executors before starting implementation work:
/// start gate + path gate. Rejects accumulate all reasons (traceable).
pub fn check_implementation_request(
    env: &Envelope,
    red: &RedEvidence,
    change_paths: &[impl AsRef<str>],
) -> GuardDecision {
    let start = check_start_implementation(env, red);
    let paths = check_changes(env, change_paths);

    match (start, paths) {
        (GuardDecision::Allow { envelope_hash }, GuardDecision::Allow { .. }) => {
            GuardDecision::Allow { envelope_hash }
        }
        (a, b) => {
            let mut reasons = Vec::new();
            reasons.extend(a.reasons().iter().cloned());
            reasons.extend(b.reasons().iter().cloned());
            reject(reasons)
        }
    }
}

fn foreign_module_without_integration(env: &Envelope, path: &str) -> Option<String> {
    for (module, prefix) in &env.module_path_prefixes {
        if module == &env.primary_module {
            continue;
        }
        if path_matches_prefix_or_glob(prefix, path) {
            let integrated = env.integration_modules.iter().any(|m| m == module);
            if !integrated {
                return Some(module.clone());
            }
        }
    }
    None
}

fn path_matches_prefix_or_glob(pattern: &str, path: &str) -> bool {
    use crate::path_gate::path_matches;
    if pattern.contains('*') {
        path_matches(pattern, path)
    } else {
        let p = normalize_path(pattern);
        let c = normalize_path(path);
        c == p || c.starts_with(&format!("{p}/"))
    }
}
