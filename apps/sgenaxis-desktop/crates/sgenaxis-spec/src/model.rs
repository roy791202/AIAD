//! ModuleSpec domain model — contracts, revisions, evidence refs.

use serde::{Deserialize, Serialize};

/// Approval lifecycle for a single revision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ApprovalStatus {
    /// Editable draft; not locked.
    Draft,
    /// Human-approved; content hash bound; immutable in place.
    Approved,
}

/// Validity of an evidence record bound to a spec revision.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EvidenceValidity {
    /// Still bound to the revision it was recorded against.
    Valid,
    /// Spec revision changed; evidence must be re-run (待重驗).
    NeedsRevalidation,
}

/// Public contract entry owned by SPEC.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Contract {
    pub id: String,
    pub title: String,
    pub body: String,
}

/// One immutable (once approved) ModuleSpec revision.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct SpecRevision {
    pub id: String,
    pub module_id: String,
    pub version_label: String,
    pub contracts: Vec<Contract>,
    pub status: ApprovalStatus,
    /// Content fingerprint bound at approve time; `None` while Draft.
    #[serde(default)]
    pub content_hash: Option<String>,
}

/// Evidence record referenced by a revision (EVID seam; SPEC tracks validity only).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct EvidenceRef {
    pub id: String,
    /// Revision this evidence was recorded against.
    pub bound_revision_id: String,
    pub validity: EvidenceValidity,
}

/// Canonical ModuleSpec document (loadable from JSON fixture / module.html extract).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ModuleSpecDocument {
    pub module_id: String,
    pub module_name: String,
    pub responsibility: String,
    pub revisions: Vec<SpecRevision>,
    #[serde(default)]
    pub evidence_refs: Vec<EvidenceRef>,
}

impl SpecRevision {
    /// Deterministic content fingerprint for approve binding.
    pub fn fingerprint(contracts: &[Contract]) -> String {
        let payload = serde_json::to_string(contracts).unwrap_or_default();
        // Stable FNV-1a 64 over UTF-8 bytes (no OS / crypto dep).
        let mut hash: u64 = 0xcbf29ce484222325;
        for b in payload.as_bytes() {
            hash ^= u64::from(*b);
            hash = hash.wrapping_mul(0x100000001b3);
        }
        format!("{hash:016x}")
    }
}
