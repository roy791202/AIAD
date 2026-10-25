//! In-memory SPEC store — load, approve, revise (no in-place approved mutation).

use crate::error::SpecError;
use crate::model::{
    ApprovalStatus, Contract, EvidenceRef, EvidenceValidity, ModuleSpecDocument, SpecRevision,
};
use crate::projection::SpecProjection;

/// Owns ModuleSpec revisions + related evidence validity (PD-SPEC-01).
#[derive(Debug, Clone, Default)]
pub struct SpecStore {
    module_id: String,
    module_name: String,
    responsibility: String,
    revisions: Vec<SpecRevision>,
    evidence_refs: Vec<EvidenceRef>,
}

impl SpecStore {
    pub fn new() -> Self {
        Self::default()
    }

    /// Load a ModuleSpec JSON document (fixture / extracted module-spec).
    pub fn load_document(doc: ModuleSpecDocument) -> Result<Self, SpecError> {
        if doc.module_id.trim().is_empty() {
            return Err(SpecError::InvalidSpec("module_id is required".into()));
        }
        if doc.revisions.is_empty() {
            return Err(SpecError::InvalidSpec(
                "at least one revision is required".into(),
            ));
        }
        let mut ids = std::collections::BTreeSet::new();
        for r in &doc.revisions {
            if !ids.insert(r.id.as_str()) {
                return Err(SpecError::InvalidSpec(format!(
                    "duplicate revision id: {}",
                    r.id
                )));
            }
        }
        Ok(Self {
            module_id: doc.module_id,
            module_name: doc.module_name,
            responsibility: doc.responsibility,
            revisions: doc.revisions,
            evidence_refs: doc.evidence_refs,
        })
    }

    /// Parse JSON text into a store.
    pub fn load_json(json: &str) -> Result<Self, SpecError> {
        let doc: ModuleSpecDocument = serde_json::from_str(json)
            .map_err(|e| SpecError::InvalidSpec(e.to_string()))?;
        Self::load_document(doc)
    }

    /// Read-only projection (規格投影).
    pub fn projection(&self) -> SpecProjection {
        SpecProjection::from_parts(
            &self.module_id,
            &self.module_name,
            &self.responsibility,
            &self.revisions,
            &self.evidence_refs,
        )
    }

    pub fn revision(&self, id: &str) -> Option<&SpecRevision> {
        self.revisions.iter().find(|r| r.id == id)
    }

    pub fn evidence_refs(&self) -> &[EvidenceRef] {
        &self.evidence_refs
    }

    /// Approve a Draft revision — binds content hash; thereafter immutable in place.
    pub fn approve(&mut self, revision_id: &str) -> Result<&SpecRevision, SpecError> {
        let rev = self
            .revisions
            .iter_mut()
            .find(|r| r.id == revision_id)
            .ok_or_else(|| SpecError::UnknownRevision(revision_id.into()))?;
        match rev.status {
            ApprovalStatus::Approved => Ok(&*rev),
            ApprovalStatus::Draft => {
                let hash = SpecRevision::fingerprint(&rev.contracts);
                rev.content_hash = Some(hash);
                rev.status = ApprovalStatus::Approved;
                Ok(&*rev)
            }
        }
    }

    /// Attempt to mutate a contract on an existing revision in place.
    ///
    /// Approved → [`SpecError::ReplanRequired`] (never mutates).
    /// Draft → updates body in place.
    pub fn try_set_contract_body(
        &mut self,
        revision_id: &str,
        contract_id: &str,
        new_body: impl Into<String>,
    ) -> Result<(), SpecError> {
        let rev = self
            .revisions
            .iter_mut()
            .find(|r| r.id == revision_id)
            .ok_or_else(|| SpecError::UnknownRevision(revision_id.into()))?;

        if rev.status == ApprovalStatus::Approved {
            return Err(SpecError::ReplanRequired {
                revision_id: revision_id.into(),
                contract_id: contract_id.into(),
            });
        }

        let contract = rev
            .contracts
            .iter_mut()
            .find(|c| c.id == contract_id)
            .ok_or_else(|| {
                SpecError::InvalidSpec(format!(
                    "contract {contract_id} not found on revision {revision_id}"
                ))
            })?;
        contract.body = new_body.into();
        Ok(())
    }

    /// Create a new Draft revision from an approved baseline (never mutates the baseline).
    ///
    /// Related evidence refs bound to `from_revision_id` become [`EvidenceValidity::NeedsRevalidation`].
    pub fn revise_from_approved(
        &mut self,
        from_revision_id: &str,
        new_revision_id: impl Into<String>,
        new_version_label: impl Into<String>,
        contracts: Vec<Contract>,
    ) -> Result<&SpecRevision, SpecError> {
        let new_revision_id = new_revision_id.into();
        let new_version_label = new_version_label.into();

        let baseline = self
            .revisions
            .iter()
            .find(|r| r.id == from_revision_id)
            .ok_or_else(|| SpecError::UnknownRevision(from_revision_id.into()))?;

        if baseline.status != ApprovalStatus::Approved {
            return Err(SpecError::InvalidSpec(format!(
                "revise_from_approved requires Approved baseline; {} is {:?}",
                from_revision_id, baseline.status
            )));
        }

        if self.revisions.iter().any(|r| r.id == new_revision_id) {
            return Err(SpecError::InvalidSpec(format!(
                "revision id already exists: {new_revision_id}"
            )));
        }

        let module_id = baseline.module_id.clone();
        // Snapshot baseline contracts for immutability assert after insert.
        let baseline_contracts = baseline.contracts.clone();
        let baseline_hash = baseline.content_hash.clone();

        self.revisions.push(SpecRevision {
            id: new_revision_id.clone(),
            module_id,
            version_label: new_version_label,
            contracts,
            status: ApprovalStatus::Draft,
            content_hash: None,
        });

        // Invalidate evidence bound to the revised-from revision.
        for ev in self.evidence_refs.iter_mut() {
            if ev.bound_revision_id == from_revision_id {
                ev.validity = EvidenceValidity::NeedsRevalidation;
            }
        }

        // Prove baseline untouched.
        let still = self
            .revisions
            .iter()
            .find(|r| r.id == from_revision_id)
            .expect("baseline must remain");
        debug_assert_eq!(still.contracts, baseline_contracts);
        debug_assert_eq!(still.content_hash, baseline_hash);
        debug_assert_eq!(still.status, ApprovalStatus::Approved);

        self.revisions
            .iter()
            .find(|r| r.id == new_revision_id)
            .ok_or_else(|| SpecError::UnknownRevision(new_revision_id))
    }

    /// Register an evidence ref bound to a revision (for tests / EVID handoff).
    pub fn attach_evidence(
        &mut self,
        evidence_id: impl Into<String>,
        bound_revision_id: impl Into<String>,
    ) -> Result<&EvidenceRef, SpecError> {
        let bound_revision_id = bound_revision_id.into();
        if !self.revisions.iter().any(|r| r.id == bound_revision_id) {
            return Err(SpecError::UnknownRevision(bound_revision_id));
        }
        let id = evidence_id.into();
        if self.evidence_refs.iter().any(|e| e.id == id) {
            return Err(SpecError::InvalidSpec(format!(
                "duplicate evidence id: {id}"
            )));
        }
        self.evidence_refs.push(EvidenceRef {
            id,
            bound_revision_id,
            validity: EvidenceValidity::Valid,
        });
        Ok(self.evidence_refs.last().expect("just pushed"))
    }
}
