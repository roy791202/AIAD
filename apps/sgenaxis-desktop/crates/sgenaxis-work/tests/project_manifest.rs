use sgenaxis_work::{
    DocumentAdoptionPlan, Project, ProjectDocumentKind, ProjectDocumentRecord, ProjectManifest,
    ProjectManifestError,
};

fn make_project() -> Project {
    Project::new(
        sgenaxis_work::ProjectId::new("proj_fixture"),
        "/fixture/project".to_owned(),
        "/fixture/project".to_owned(),
    )
}

const HASH_A: &str = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const HASH_B: &str = "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb";
const DOCUMENT_ID_A: &str = "550e8400-e29b-41d4-a716-446655440000";
const DOCUMENT_ID_B: &str = "550e8400-e29b-41d4-b716-446655440001";

#[test]
fn adoption_generates_opaque_stable_id_and_repeat_is_idempotent() {
    let project = make_project();
    let empty = ProjectManifest::default();
    let first = project
        .plan_document_adoption(
            &empty,
            "docs/legacy.sgendesign",
            ProjectDocumentKind::Design,
            HASH_A,
            DOCUMENT_ID_A,
        )
        .expect("valid local document adoption");
    let (record, manifest) = match first {
        DocumentAdoptionPlan::Persist { record, manifest } => (record, manifest),
        DocumentAdoptionPlan::AlreadyAdopted(_) => panic!("first adoption must create a record"),
    };
    assert!(!record.document_id.is_empty());
    assert!(!record.document_id.contains("legacy.sgendesign"));
    assert!(!record.document_id.contains(HASH_A));
    assert_eq!(record.document_id, DOCUMENT_ID_A);
    assert_eq!(record.reference, "docs/legacy.sgendesign");
    assert_eq!(record.revision_id, HASH_A);

    assert_eq!(
        project.plan_document_adoption(
            &manifest,
            "docs/legacy.sgendesign",
            ProjectDocumentKind::Design,
            HASH_A,
            DOCUMENT_ID_B,
        ),
        Ok(DocumentAdoptionPlan::AlreadyAdopted(record)),
    );
    let second = project
        .plan_document_adoption(
            &manifest,
            "docs/second.ess",
            ProjectDocumentKind::Ess,
            HASH_A,
            DOCUMENT_ID_B,
        )
        .expect("distinct reference gets a new project-local identity");
    let DocumentAdoptionPlan::Persist { record: second, .. } = second else {
        panic!("distinct reference must create a record");
    };
    assert_eq!(second.document_id, DOCUMENT_ID_B);
}

#[test]
fn existing_document_reference_with_changed_bytes_is_revision_conflict() {
    let project = make_project();
    let original = ProjectDocumentRecord {
        document_id: DOCUMENT_ID_A.to_owned(),
        kind: ProjectDocumentKind::Ess,
        reference: "scenes/main.ess".to_owned(),
        revision_id: HASH_A.to_owned(),
    };
    let manifest = ProjectManifest {
        documents: vec![original.clone()],
    };

    assert_eq!(
        project.plan_document_adoption(
            &manifest,
            "scenes/main.ess",
            ProjectDocumentKind::Ess,
            HASH_B,
            DOCUMENT_ID_B,
        ),
        Err(ProjectManifestError::RevisionConflict),
    );
    assert_eq!(manifest.documents, vec![original]);
}

#[test]
fn duplicate_manifest_reference_under_different_ids_is_conflict() {
    let project = make_project();
    let existing = ProjectDocumentRecord {
        document_id: DOCUMENT_ID_A.to_owned(),
        kind: ProjectDocumentKind::Ess,
        reference: "docs/shared.ess".to_owned(),
        revision_id: HASH_A.to_owned(),
    };
    let duplicate = ProjectDocumentRecord {
        document_id: DOCUMENT_ID_B.to_owned(),
        ..existing.clone()
    };
    let manifest = ProjectManifest {
        documents: vec![existing, duplicate],
    };

    assert_eq!(
        project.plan_document_adoption(
            &manifest,
            "docs/new.ess",
            ProjectDocumentKind::Ess,
            HASH_A,
            DOCUMENT_ID_B,
        ),
        Err(ProjectManifestError::ReferenceConflict),
    );
}

#[test]
fn invalid_and_nonlocal_references_are_rejected() {
    let project = make_project();
    for input in [
        "",
        "../outside.ess",
        "/abs/file.ess",
        "C:/outside.ess",
        "docs\\..\\outside.ess",
    ] {
        assert_eq!(
            project.plan_document_adoption(
                &ProjectManifest::default(),
                input,
                ProjectDocumentKind::Ess,
                HASH_A,
                DOCUMENT_ID_A,
            ),
            Err(ProjectManifestError::InvalidReference),
            "reference {input:?} must be rejected",
        );
    }
    assert_eq!(
        make_project().plan_document_adoption(
            &ProjectManifest::default(),
            "docs/file.txt",
            ProjectDocumentKind::Ess,
            HASH_A,
            DOCUMENT_ID_A,
        ),
        Err(ProjectManifestError::UnsupportedKind),
    );
}

#[test]
fn malformed_revision_digest_is_rejected() {
    assert_eq!(
        make_project().plan_document_adoption(
            &ProjectManifest::default(),
            "docs/valid.ess",
            ProjectDocumentKind::Ess,
            "sha256:bad",
            DOCUMENT_ID_A,
        ),
        Err(ProjectManifestError::InvalidRevision),
    );
}

#[test]
fn invalid_candidate_id_is_rejected() {
    assert_eq!(
        make_project().plan_document_adoption(
            &ProjectManifest::default(),
            "docs/valid.ess",
            ProjectDocumentKind::Ess,
            HASH_A,
            "doc_1",
        ),
        Err(ProjectManifestError::InvalidDocumentId),
    );
}

#[test]
fn candidate_id_already_owned_by_another_document_is_conflict() {
    let existing = ProjectManifest {
        documents: vec![ProjectDocumentRecord {
            document_id: DOCUMENT_ID_A.to_owned(),
            kind: ProjectDocumentKind::Ess,
            reference: "docs/existing.ess".to_owned(),
            revision_id: HASH_A.to_owned(),
        }],
    };

    assert_eq!(
        make_project().plan_document_adoption(
            &existing,
            "docs/new.ess",
            ProjectDocumentKind::Ess,
            HASH_B,
            DOCUMENT_ID_A,
        ),
        Err(ProjectManifestError::DocumentIdConflict),
    );
}
