//! M05-S1 pure retention policy. No physical cleanup behavior.
//! Root projections are supplied by their authoritative owners through HOST.
//! Eligibility is never permission to delete; no paths, leases or IO enter here.

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssetCandidate {
    pub asset_id: String,
    pub content_digest: String,
    pub owned_by_operation: Option<String>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RootKind {
    LiveDocuments,
    UndoHistory,
    RedoHistory,
    RecoverySnapshots,
    InFlightTransactions,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Completeness {
    Complete,
    Unknown,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RootReference {
    pub asset_id: String,
    pub content_digest: String,
    pub owner_id: String,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RootObservation {
    pub kind: RootKind,
    pub revision: String,
    pub completeness: Completeness,
    pub references: Vec<RootReference>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RootSnapshot {
    pub project_id: String,
    pub session_id: String,
    pub observations: Vec<RootObservation>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvaluationContext {
    pub project_id: String,
    pub session_id: String,
    pub operation_id: String,
    pub expected_root_revisions: Vec<(RootKind, String)>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RetentionDecision {
    Retain {
        reasons: Vec<RetentionReason>,
    },
    EligibleForCleanup {
        asset_id: String,
        content_digest: String,
    },
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RetentionReason {
    Referenced { kind: RootKind, owner_id: String },
    RootsIncomplete { kind: RootKind },
    StaleRoots { kind: RootKind },
    NotOwnedByOperation,
    IdentityConflict { asset_id: String },
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RetentionError {
    InvalidInput { field: String, reason: String },
}

/// Evaluate conservative retention from immutable owner-supplied projections.
/// An eligible identity is not a cleanup lease or a deletion authorization.
pub fn evaluate_asset_retention(
    candidate: &AssetCandidate,
    roots: &RootSnapshot,
    context: &EvaluationContext,
) -> Result<RetentionDecision, RetentionError> {
    for (field, value) in [
        ("asset_id", candidate.asset_id.as_str()),
        ("project_id", roots.project_id.as_str()),
        ("session_id", roots.session_id.as_str()),
        ("context.project_id", context.project_id.as_str()),
        ("context.session_id", context.session_id.as_str()),
        ("operation_id", context.operation_id.as_str()),
    ] {
        validate_text(field, value)?;
    }
    validate_digest("content_digest", &candidate.content_digest)?;
    if let Some(owner) = &candidate.owned_by_operation {
        validate_text("owned_by_operation", owner)?;
    }
    if roots.project_id != context.project_id || roots.session_id != context.session_id {
        return Err(invalid(
            "roots.identity",
            "project or session does not match context",
        ));
    }
    let mut observed = [None; 5];
    let mut expected = [None; 5];
    let mut total = 0usize;
    for observation in &roots.observations {
        let i = root_index(observation.kind);
        if observed[i].replace(observation).is_some() {
            return Err(invalid("observations.kind", "duplicate root provider"));
        }
        validate_text("observations.revision", &observation.revision)?;
        if observation.references.len() > 4096 {
            return Err(invalid(
                "observations.references",
                "per-provider limit exceeded",
            ));
        }
        total = total
            .checked_add(observation.references.len())
            .ok_or_else(|| invalid("references", "count overflow"))?;
        if total > 16384 {
            return Err(invalid("references", "total reference limit exceeded"));
        }
        for reference in &observation.references {
            validate_text("references.asset_id", &reference.asset_id)?;
            validate_text("references.owner_id", &reference.owner_id)?;
            validate_digest("references.content_digest", &reference.content_digest)?;
        }
    }
    for (kind, revision) in &context.expected_root_revisions {
        let i = root_index(*kind);
        if expected[i].replace(revision.as_str()).is_some() {
            return Err(invalid(
                "expected_root_revisions",
                "duplicate expected provider",
            ));
        }
        validate_text("expected_root_revisions.revision", revision)?;
    }
    let mut reasons = Vec::new();
    for kind in [
        RootKind::LiveDocuments,
        RootKind::UndoHistory,
        RootKind::RedoHistory,
        RootKind::RecoverySnapshots,
        RootKind::InFlightTransactions,
    ] {
        let i = root_index(kind);
        let Some(observation) = observed[i] else {
            reasons.push(RetentionReason::RootsIncomplete { kind });
            continue;
        };
        if observation.completeness == Completeness::Unknown || expected[i].is_none() {
            reasons.push(RetentionReason::RootsIncomplete { kind });
        } else if expected[i] != Some(observation.revision.as_str()) {
            reasons.push(RetentionReason::StaleRoots { kind });
        }
        for reference in &observation.references {
            if reference.asset_id == candidate.asset_id {
                if reference.content_digest == candidate.content_digest {
                    reasons.push(RetentionReason::Referenced {
                        kind,
                        owner_id: reference.owner_id.clone(),
                    });
                } else {
                    reasons.push(RetentionReason::IdentityConflict {
                        asset_id: candidate.asset_id.clone(),
                    });
                }
            }
        }
    }
    if candidate.owned_by_operation.as_deref() != Some(context.operation_id.as_str()) {
        reasons.push(RetentionReason::NotOwnedByOperation);
    }
    reasons.sort_by(|a, b| reason_key(a).cmp(&reason_key(b)));
    reasons.dedup();
    if reasons.is_empty() {
        Ok(RetentionDecision::EligibleForCleanup {
            asset_id: candidate.asset_id.clone(),
            content_digest: candidate.content_digest.clone(),
        })
    } else {
        Ok(RetentionDecision::Retain { reasons })
    }
}

fn invalid(field: &str, reason: &str) -> RetentionError {
    RetentionError::InvalidInput {
        field: field.into(),
        reason: reason.into(),
    }
}
fn validate_text(field: &str, value: &str) -> Result<(), RetentionError> {
    if value.is_empty() || value.len() > 256 || value.contains('\0') {
        Err(invalid(field, "expected 1..256 UTF-8 bytes without NUL"))
    } else {
        Ok(())
    }
}
fn validate_digest(field: &str, value: &str) -> Result<(), RetentionError> {
    if value.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64
            && hex
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    }) {
        Ok(())
    } else {
        Err(invalid(field, "expected lowercase SHA-256 digest"))
    }
}
fn root_index(kind: RootKind) -> usize {
    match kind {
        RootKind::LiveDocuments => 0,
        RootKind::UndoHistory => 1,
        RootKind::RedoHistory => 2,
        RootKind::RecoverySnapshots => 3,
        RootKind::InFlightTransactions => 4,
    }
}
fn reason_key(reason: &RetentionReason) -> (usize, u8, &str) {
    match reason {
        RetentionReason::Referenced { kind, owner_id } => (root_index(*kind), 0, owner_id),
        RetentionReason::RootsIncomplete { kind } => (root_index(*kind), 1, ""),
        RetentionReason::StaleRoots { kind } => (root_index(*kind), 2, ""),
        RetentionReason::NotOwnedByOperation => (5, 0, ""),
        RetentionReason::IdentityConflict { asset_id } => (5, 1, asset_id),
    }
}
