//! SGenAxis **SPEC** — ModuleSpec / contract load & revision locking (PD-SPEC-01).
//!
//! BDD-PD-SPEC-01：可載入規格投影；核准修訂產新版本並使相關證據待重驗。
//!
//! Rules:
//! - Load ModuleSpec + contracts into a projection
//! - Approved revision is **immutable in place**
//! - Changes produce a **new** Draft revision
//! - Evidence refs bound to the prior revision → [`EvidenceValidity::NeedsRevalidation`]
//!
//! Pure Rust: no Tauri, no OS ports. Fixture JSON only.

#![forbid(unsafe_code)]

mod error;
mod model;
mod projection;
mod store;

pub use error::SpecError;
pub use model::{
    ApprovalStatus, Contract, EvidenceRef, EvidenceValidity, ModuleSpecDocument, SpecRevision,
};
pub use projection::{RevisionSummary, SpecProjection};
pub use store::SpecStore;

#[cfg(test)]
mod tests {
    use super::*;

    const SAMPLE_FIXTURE: &str = include_str!("../fixtures/sample_module_spec.json");

    #[test]
    fn load_fixture_yields_spec_projection() {
        let store = SpecStore::load_json(SAMPLE_FIXTURE).expect("fixture parses");
        let proj = store.projection();

        assert_eq!(proj.module_id, "SPEC");
        assert_eq!(proj.module_name, "工程規格");
        assert!(!proj.responsibility.is_empty());
        assert_eq!(proj.revisions.len(), 1);
        assert_eq!(proj.revisions[0].id, "rev-v1");
        assert_eq!(proj.revisions[0].version_label, "v1");
        assert_eq!(proj.revisions[0].status, ApprovalStatus::Draft);
        assert_eq!(proj.revisions[0].contract_count, 2);
        assert_eq!(proj.evidence_refs.len(), 1);
        assert_eq!(proj.evidence_needing_revalidation, 0);
    }

    #[test]
    fn approve_binds_hash_and_locks_revision() {
        let mut store = SpecStore::load_json(SAMPLE_FIXTURE).unwrap();
        let approved = store.approve("rev-v1").unwrap();
        assert_eq!(approved.status, ApprovalStatus::Approved);
        assert!(approved.content_hash.is_some());

        let hash = approved.content_hash.clone().unwrap();
        let again = store.approve("rev-v1").unwrap();
        assert_eq!(again.content_hash.as_deref(), Some(hash.as_str()));
    }

    #[test]
    fn approved_in_place_mutation_returns_replan_required() {
        let mut store = SpecStore::load_json(SAMPLE_FIXTURE).unwrap();
        store.approve("rev-v1").unwrap();

        let err = store
            .try_set_contract_body("rev-v1", "CTR-SPEC-001", "sneaky change")
            .unwrap_err();

        assert_eq!(
            err,
            SpecError::ReplanRequired {
                revision_id: "rev-v1".into(),
                contract_id: "CTR-SPEC-001".into(),
            }
        );

        let body = &store.revision("rev-v1").unwrap().contracts[0].body;
        assert_eq!(body, "每個 Task 恰有一個主要模組");
    }

    #[test]
    fn revise_creates_new_version_keeps_approved_immutable() {
        let mut store = SpecStore::load_json(SAMPLE_FIXTURE).unwrap();
        store.approve("rev-v1").unwrap();
        let v1_hash = store
            .revision("rev-v1")
            .unwrap()
            .content_hash
            .clone()
            .unwrap();
        let v1_contracts = store.revision("rev-v1").unwrap().contracts.clone();

        let new_contracts = vec![
            Contract {
                id: "CTR-SPEC-001".into(),
                title: "Task primary module".into(),
                body: "每個 Task 恰有一個主要模組（修訂）".into(),
            },
            Contract {
                id: "CTR-SPEC-002".into(),
                title: "Approved immutability".into(),
                body: "核准後規格不可原地變更；修訂產生新版本".into(),
            },
        ];

        let v2 = store
            .revise_from_approved("rev-v1", "rev-v2", "v2", new_contracts)
            .unwrap();
        assert_eq!(v2.id, "rev-v2");
        assert_eq!(v2.status, ApprovalStatus::Draft);
        assert!(v2.content_hash.is_none());

        let still_v1 = store.revision("rev-v1").unwrap();
        assert_eq!(still_v1.status, ApprovalStatus::Approved);
        assert_eq!(still_v1.content_hash.as_deref(), Some(v1_hash.as_str()));
        assert_eq!(still_v1.contracts, v1_contracts);

        let proj = store.projection();
        assert_eq!(proj.revisions.len(), 2);
    }

    #[test]
    fn revise_invalidates_related_evidence_refs() {
        let mut store = SpecStore::load_json(SAMPLE_FIXTURE).unwrap();
        store.approve("rev-v1").unwrap();

        assert_eq!(
            store.evidence_refs()[0].validity,
            EvidenceValidity::Valid
        );

        store
            .revise_from_approved(
                "rev-v1",
                "rev-v2",
                "v2",
                store.revision("rev-v1").unwrap().contracts.clone(),
            )
            .unwrap();

        let ev = store
            .evidence_refs()
            .iter()
            .find(|e| e.id == "EVID-SAMPLE-01")
            .expect("fixture evidence");
        assert_eq!(ev.bound_revision_id, "rev-v1");
        assert_eq!(ev.validity, EvidenceValidity::NeedsRevalidation);

        let proj = store.projection();
        assert_eq!(proj.evidence_needing_revalidation, 1);
    }

    #[test]
    fn draft_contract_body_can_be_edited() {
        let mut store = SpecStore::load_json(SAMPLE_FIXTURE).unwrap();
        store
            .try_set_contract_body("rev-v1", "CTR-SPEC-001", "draft edit")
            .unwrap();
        assert_eq!(
            store.revision("rev-v1").unwrap().contracts[0].body,
            "draft edit"
        );
    }

    #[test]
    fn load_rejects_empty_module_id() {
        let json = r#"{
          "module_id": "",
          "module_name": "x",
          "responsibility": "y",
          "revisions": [{
            "id": "r1",
            "module_id": "SPEC",
            "version_label": "v1",
            "contracts": [],
            "status": "draft"
          }]
        }"#;
        let err = SpecStore::load_json(json).unwrap_err();
        assert!(matches!(err, SpecError::InvalidSpec(_)));
    }
}
