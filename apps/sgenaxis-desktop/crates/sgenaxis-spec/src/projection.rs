//! Read-only SPEC projection for UI / REPORT (no mutations).

use crate::model::{ApprovalStatus, EvidenceRef, EvidenceValidity, SpecRevision};

/// Snapshot safe for UI / REPORT consumers.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SpecProjection {
    pub module_id: String,
    pub module_name: String,
    pub responsibility: String,
    pub revisions: Vec<RevisionSummary>,
    pub evidence_refs: Vec<EvidenceRef>,
    /// Count of evidence refs awaiting revalidation after a revise.
    pub evidence_needing_revalidation: usize,
}

/// Compact revision row for projection lists.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RevisionSummary {
    pub id: String,
    pub version_label: String,
    pub status: ApprovalStatus,
    pub contract_count: usize,
    pub content_hash: Option<String>,
}

impl SpecProjection {
    pub(crate) fn from_parts(
        module_id: impl Into<String>,
        module_name: impl Into<String>,
        responsibility: impl Into<String>,
        revisions: &[SpecRevision],
        evidence_refs: &[EvidenceRef],
    ) -> Self {
        let evidence_needing_revalidation = evidence_refs
            .iter()
            .filter(|e| e.validity == EvidenceValidity::NeedsRevalidation)
            .count();
        Self {
            module_id: module_id.into(),
            module_name: module_name.into(),
            responsibility: responsibility.into(),
            revisions: revisions
                .iter()
                .map(|r| RevisionSummary {
                    id: r.id.clone(),
                    version_label: r.version_label.clone(),
                    status: r.status,
                    contract_count: r.contracts.len(),
                    content_hash: r.content_hash.clone(),
                })
                .collect(),
            evidence_refs: evidence_refs.to_vec(),
            evidence_needing_revalidation,
        }
    }
}
