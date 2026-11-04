//! HOST filesystem adapter for the WORK-owned project document manifest.
//! The manifest is one project-local file; this module does no identity policy.

use serde::{Deserialize, Serialize};
use sgenaxis_ports::{FileSystemPort, PortError};
use sgenaxis_work::{
    DocumentAdoptionPlan, Project, ProjectDocumentKind, ProjectDocumentRecord, ProjectManifest,
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectManifestStoreError {
    InvalidProjectRoot,
    InvalidReference,
    UnsupportedKind,
    MalformedManifest,
    UnsupportedSchema,
    InvalidManifestRecord,
    InvalidDocumentId,
    DocumentIdConflict,
    ManifestChanged,
    RevisionConflict,
    ReferenceConflict,
    SourceRead(PortError),
    ManifestRead(PortError),
    CreateDirectory(PortError),
    Write(PortError),
    DurabilityUnverified,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DocumentAdoptionOutcome {
    Adopted(ProjectDocumentRecord),
    AlreadyAdopted(ProjectDocumentRecord),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct WireManifest {
    schema: String,
    #[serde(rename = "schemaVersion")]
    schema_version: u32,
    documents: Vec<WireDocument>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
struct WireDocument {
    #[serde(rename = "documentId")]
    document_id: String,
    kind: String,
    reference: String,
    #[serde(rename = "revisionId")]
    revision_id: String,
}

/// Explicitly adopt one existing project-local .ess or .sgendesign reference.
///
/// WORK computes identity and conflict outcomes. HOST only reads bytes and
/// persists the returned whole-manifest plan via the existing FileSystemPort.
/// The UUID candidate is supplied by the outer Tauri adapter; this adapter
/// does not create identity entropy.
/// Callers must serialize mutations for a project. The current FileSystemPort
/// offers atomic replacement but no cross-process compare-and-swap; the read
/// recheck below does not claim a cross-process transaction.
pub fn adopt_project_document(
    fs: &dyn FileSystemPort,
    project: &Project,
    reference: &str,
    document_id_candidate: &str,
) -> Result<DocumentAdoptionOutcome, ProjectManifestStoreError> {
    use sgenaxis_work::{
        document_kind_from_str, normalize_project_reference, validate_document_id,
        validate_revision_id, PROJECT_MANIFEST_SCHEMA, PROJECT_MANIFEST_VERSION,
    };

    validate_document_id(document_id_candidate).map_err(map_work_error)?;
    let normalized_reference = normalize_project_reference(reference).map_err(map_work_error)?;
    let kind =
        ProjectDocumentKind::from_reference(&normalized_reference).map_err(map_work_error)?;
    let source_path = project
        .document_path(&normalized_reference)
        .map_err(map_work_error)?;
    let source_bytes = fs
        .read(&source_path)
        .map_err(ProjectManifestStoreError::SourceRead)?;
    let revision_id = format!(
        "sha256:{}",
        sgenaxis_spec::packet::source_sha256(&source_bytes)
    );

    let manifest_path = project.manifest_path().map_err(map_work_error)?;
    let original_bytes = read_manifest(fs, &manifest_path)?;
    let mut manifest = match original_bytes.as_deref() {
        None => ProjectManifest::default(),
        Some(bytes) => {
            let wire: WireManifest = serde_json::from_slice(bytes)
                .map_err(|_| ProjectManifestStoreError::MalformedManifest)?;
            if wire.schema != PROJECT_MANIFEST_SCHEMA
                || wire.schema_version != PROJECT_MANIFEST_VERSION
            {
                return Err(ProjectManifestStoreError::UnsupportedSchema);
            }
            let mut documents = Vec::with_capacity(wire.documents.len());
            for document in wire.documents {
                if document.document_id.trim().is_empty() {
                    return Err(ProjectManifestStoreError::InvalidManifestRecord);
                }
                validate_document_id(&document.document_id)
                    .map_err(|_| ProjectManifestStoreError::InvalidManifestRecord)?;
                let kind = document_kind_from_str(&document.kind)
                    .map_err(|_| ProjectManifestStoreError::InvalidManifestRecord)?;
                let normalized = normalize_project_reference(&document.reference)
                    .map_err(|_| ProjectManifestStoreError::InvalidManifestRecord)?;
                if normalized != document.reference {
                    return Err(ProjectManifestStoreError::InvalidManifestRecord);
                }
                validate_revision_id(&document.revision_id)
                    .map_err(|_| ProjectManifestStoreError::InvalidManifestRecord)?;
                if ProjectDocumentKind::from_reference(&normalized)
                    .map_err(|_| ProjectManifestStoreError::InvalidManifestRecord)?
                    != kind
                {
                    return Err(ProjectManifestStoreError::InvalidManifestRecord);
                }
                documents.push(ProjectDocumentRecord {
                    document_id: document.document_id,
                    kind,
                    reference: normalized,
                    revision_id: document.revision_id,
                });
            }
            ProjectManifest { documents }
        }
    };

    match project
        .plan_document_adoption(
            &manifest,
            &normalized_reference,
            kind,
            &revision_id,
            document_id_candidate,
        )
        .map_err(map_work_error)?
    {
        DocumentAdoptionPlan::AlreadyAdopted(record) => {
            Ok(DocumentAdoptionOutcome::AlreadyAdopted(record))
        }
        DocumentAdoptionPlan::Persist {
            record,
            manifest: planned,
        } => {
            // Recheck the single-file snapshot before replacing it. This detects
            // observed concurrent edits; FileSystemPort has no cross-process CAS.
            if read_manifest(fs, &manifest_path)? != original_bytes {
                return Err(ProjectManifestStoreError::ManifestChanged);
            }
            manifest = planned;
            let wire = WireManifest {
                schema: PROJECT_MANIFEST_SCHEMA.to_owned(),
                schema_version: PROJECT_MANIFEST_VERSION,
                documents: manifest
                    .documents
                    .iter()
                    .map(|record| WireDocument {
                        document_id: record.document_id.clone(),
                        kind: record.kind.as_str().to_owned(),
                        reference: record.reference.clone(),
                        revision_id: record.revision_id.clone(),
                    })
                    .collect(),
            };
            let bytes = serde_json::to_vec_pretty(&wire)
                .map_err(|_| ProjectManifestStoreError::InvalidManifestRecord)?;
            let parent = manifest_path
                .rsplit_once(['/', '\\'])
                .map(|(parent, _)| parent)
                .ok_or(ProjectManifestStoreError::InvalidProjectRoot)?;
            fs.create_dir_all(parent)
                .map_err(ProjectManifestStoreError::CreateDirectory)?;
            fs.write_atomic(&manifest_path, &bytes)
                .map_err(ProjectManifestStoreError::Write)?;
            match fs.read(&manifest_path) {
                Ok(readback) if readback == bytes => Ok(DocumentAdoptionOutcome::Adopted(record)),
                Ok(_) | Err(_) => Err(ProjectManifestStoreError::DurabilityUnverified),
            }
        }
    }
}

fn read_manifest(
    fs: &dyn FileSystemPort,
    path: &str,
) -> Result<Option<Vec<u8>>, ProjectManifestStoreError> {
    match fs.read(path) {
        Ok(bytes) => Ok(Some(bytes)),
        Err(PortError::NotFound(_)) => Ok(None),
        Err(error) => Err(ProjectManifestStoreError::ManifestRead(error)),
    }
}

fn map_work_error(error: sgenaxis_work::ProjectManifestError) -> ProjectManifestStoreError {
    use sgenaxis_work::ProjectManifestError as WorkError;
    match error {
        WorkError::InvalidProjectRoot => ProjectManifestStoreError::InvalidProjectRoot,
        WorkError::InvalidReference => ProjectManifestStoreError::InvalidReference,
        WorkError::UnsupportedKind => ProjectManifestStoreError::UnsupportedKind,
        WorkError::InvalidRevision => ProjectManifestStoreError::InvalidManifestRecord,
        WorkError::InvalidDocumentId => ProjectManifestStoreError::InvalidDocumentId,
        WorkError::DocumentIdConflict => ProjectManifestStoreError::DocumentIdConflict,
        WorkError::RevisionConflict => ProjectManifestStoreError::RevisionConflict,
        WorkError::ReferenceConflict => ProjectManifestStoreError::ReferenceConflict,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use sgenaxis_ports::PortError;
    use std::collections::HashMap;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::sync::Mutex;

    const SOURCE_PATH: &str = "/fixture/project/docs/legacy.sgendesign";
    const MANIFEST_PATH: &str = "/fixture/project/.sgenaxis/project-manifest.json";
    const DOCUMENT_ID_A: &str = "550e8400-e29b-41d4-a716-446655440000";
    const DOCUMENT_ID_B: &str = "550e8400-e29b-41d4-b716-446655440001";

    #[derive(Default)]
    struct ControlledFs {
        files: Mutex<HashMap<String, Vec<u8>>>,
        reads: Mutex<Vec<String>>,
        fail_write: AtomicBool,
        fail_manifest_readback: AtomicBool,
        has_written: AtomicBool,
        fail_source_read: AtomicBool,
    }

    impl ControlledFs {
        fn put(&self, path: &str, bytes: &[u8]) {
            self.files
                .lock()
                .unwrap()
                .insert(path.to_owned(), bytes.to_vec());
        }

        fn get(&self, path: &str) -> Option<Vec<u8>> {
            self.files.lock().unwrap().get(path).cloned()
        }

        fn read_count(&self) -> usize {
            self.reads.lock().unwrap().len()
        }
    }

    impl FileSystemPort for ControlledFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> {
            Ok(self.files.lock().unwrap().contains_key(path))
        }

        fn read_to_string(&self, path: &str) -> Result<String, PortError> {
            String::from_utf8(self.read(path)?).map_err(|_| PortError::Io("fixture utf8".into()))
        }

        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
            self.reads.lock().unwrap().push(path.to_owned());
            if path == SOURCE_PATH && self.fail_source_read.load(Ordering::SeqCst) {
                return Err(PortError::PermissionDenied("fixture source denied".into()));
            }
            if path == MANIFEST_PATH
                && self.has_written.load(Ordering::SeqCst)
                && self.fail_manifest_readback.load(Ordering::SeqCst)
            {
                return Err(PortError::PermissionDenied(
                    "fixture readback denied".into(),
                ));
            }
            self.files
                .lock()
                .unwrap()
                .get(path)
                .cloned()
                .ok_or_else(|| PortError::NotFound(path.to_owned()))
        }

        fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError> {
            if self.fail_write.load(Ordering::SeqCst) {
                return Err(PortError::Io("fixture atomic write failed".into()));
            }
            self.files
                .lock()
                .unwrap()
                .insert(path.to_owned(), contents.to_vec());
            self.has_written.store(true, Ordering::SeqCst);
            Ok(())
        }

        fn create_dir_all(&self, _path: &str) -> Result<(), PortError> {
            Ok(())
        }

        fn is_file(&self, path: &str) -> Result<bool, PortError> {
            Ok(self.files.lock().unwrap().contains_key(path))
        }

        fn remove_file(&self, path: &str) -> Result<(), PortError> {
            self.files
                .lock()
                .unwrap()
                .remove(path)
                .map(|_| ())
                .ok_or_else(|| PortError::NotFound(path.to_owned()))
        }
    }

    fn project() -> Project {
        Project::new(
            sgenaxis_work::ProjectId::new("proj_fixture"),
            "/fixture/project".to_owned(),
            "/fixture/project".to_owned(),
        )
    }

    fn adopt(
        fs: &ControlledFs,
        reference: &str,
    ) -> Result<DocumentAdoptionOutcome, ProjectManifestStoreError> {
        adopt_project_document(fs, &project(), reference, DOCUMENT_ID_A)
    }

    #[test]
    fn malformed_candidate_id_is_rejected_before_any_file_read() {
        let fs = ControlledFs::default();
        source(&fs);

        let result = adopt_project_document(&fs, &project(), "docs/legacy.sgendesign", "doc_1");

        assert_eq!(result, Err(ProjectManifestStoreError::InvalidDocumentId));
        assert_eq!(fs.read_count(), 0);
        assert!(fs.get(MANIFEST_PATH).is_none());
        assert!(fs.get(SOURCE_PATH).is_some());
    }

    #[test]
    fn candidate_id_already_owned_in_manifest_is_typed_conflict_without_write() {
        let fs = ControlledFs::default();
        source(&fs);
        let prior = format!(
            r#"{{"schema":"sgenaxis.project-manifest","schemaVersion":1,"documents":[{{"documentId":"{DOCUMENT_ID_A}","kind":"design","reference":"docs/other.sgendesign","revisionId":"sha256:{}"}}]}}"#,
            "a".repeat(64)
        );
        fs.put(MANIFEST_PATH, prior.as_bytes());
        let before = fs.get(MANIFEST_PATH).unwrap();

        let result =
            adopt_project_document(&fs, &project(), "docs/legacy.sgendesign", DOCUMENT_ID_A);

        assert_eq!(result, Err(ProjectManifestStoreError::DocumentIdConflict));
        assert_eq!(fs.get(MANIFEST_PATH).unwrap(), before);
    }

    fn source(fs: &ControlledFs) -> Vec<u8> {
        let bytes = b"<fixture design bytes>".to_vec();
        fs.put(SOURCE_PATH, &bytes);
        bytes
    }

    #[test]
    fn adoption_persists_v1_record_and_preserves_source_bytes() {
        let fs = ControlledFs::default();
        let source_before = source(&fs);

        let result = adopt(&fs, "docs/legacy.sgendesign");

        let DocumentAdoptionOutcome::Adopted(record) = result.expect("adoption should succeed")
        else {
            panic!("first adoption must write one manifest record");
        };
        assert_eq!(record.kind, ProjectDocumentKind::Design);
        assert_eq!(record.document_id, DOCUMENT_ID_A);
        assert_eq!(record.reference, "docs/legacy.sgendesign");
        assert_eq!(
            record.revision_id,
            format!(
                "sha256:{}",
                sgenaxis_spec::packet::source_sha256(&source_before)
            )
        );
        assert_eq!(fs.get(SOURCE_PATH).unwrap(), source_before);
        let bytes = fs.get(MANIFEST_PATH).expect("manifest persisted");
        let manifest: WireManifest = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(manifest.schema, "sgenaxis.project-manifest");
        assert_eq!(manifest.schema_version, 1);
        assert_eq!(manifest.documents.len(), 1);
        assert_eq!(manifest.documents[0].document_id, record.document_id);
        let value: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
        assert_eq!(value["documents"][0]["revisionId"], record.revision_id);
        assert!(value["documents"][0].get("revision_id").is_none());
    }

    #[test]
    fn repeated_same_reference_and_revision_is_idempotent_without_write() {
        let fs = ControlledFs::default();
        source(&fs);
        let first = adopt(&fs, "docs/legacy.sgendesign").unwrap();
        let first_record = match first {
            DocumentAdoptionOutcome::Adopted(r) => r,
            other => panic!("{other:?}"),
        };
        let before = fs.get(MANIFEST_PATH).unwrap();
        let repeated =
            adopt_project_document(&fs, &project(), "docs/legacy.sgendesign", DOCUMENT_ID_B)
                .unwrap();
        assert_eq!(
            repeated,
            DocumentAdoptionOutcome::AlreadyAdopted(first_record)
        );
        assert_eq!(fs.get(MANIFEST_PATH).unwrap(), before);
    }

    #[test]
    fn changed_payload_for_existing_reference_is_conflict_without_mutation() {
        let fs = ControlledFs::default();
        source(&fs);
        adopt(&fs, "docs/legacy.sgendesign").unwrap();
        let manifest_before = fs.get(MANIFEST_PATH).unwrap();
        let source_before = fs.get(SOURCE_PATH).unwrap();
        fs.put(SOURCE_PATH, b"changed payload");

        let result = adopt(&fs, "docs/legacy.sgendesign");

        assert_eq!(result, Err(ProjectManifestStoreError::RevisionConflict));
        assert_eq!(fs.get(MANIFEST_PATH).unwrap(), manifest_before);
        assert_eq!(fs.get(SOURCE_PATH).unwrap(), b"changed payload".to_vec());
        assert_ne!(source_before, fs.get(SOURCE_PATH).unwrap());
    }

    #[test]
    fn nonlocal_or_unsupported_reference_is_rejected_before_read() {
        for reference in ["../outside.ess", "C:/outside.ess", "", "docs/../escape.ess"] {
            let fs = ControlledFs::default();
            let result = adopt(&fs, reference);
            assert_eq!(result, Err(ProjectManifestStoreError::InvalidReference));
            assert_eq!(fs.read_count(), 0, "must reject {reference:?} before IO");
            assert!(fs.get(MANIFEST_PATH).is_none());
        }
        let fs = ControlledFs::default();
        assert_eq!(
            adopt(&fs, "docs/file.txt"),
            Err(ProjectManifestStoreError::UnsupportedKind),
        );
        assert_eq!(fs.read_count(), 0);
    }

    #[test]
    fn malformed_or_unsupported_manifest_is_never_replaced() {
        for bytes in [
            b"not json".as_slice(),
            br#"{"schema":"wrong","schemaVersion":1,"documents":[]}"#.as_slice(),
        ] {
            let fs = ControlledFs::default();
            source(&fs);
            fs.put(MANIFEST_PATH, bytes);
            let before = fs.get(MANIFEST_PATH).unwrap();
            let result = adopt(&fs, "docs/legacy.sgendesign");
            assert!(matches!(
                result,
                Err(ProjectManifestStoreError::MalformedManifest
                    | ProjectManifestStoreError::UnsupportedSchema)
            ));
            assert_eq!(fs.get(MANIFEST_PATH).unwrap(), before);
        }
    }

    #[test]
    fn atomic_write_failure_preserves_existing_manifest_bytes() {
        let fs = ControlledFs::default();
        source(&fs);
        let prior = br#"{"schema":"sgenaxis.project-manifest","schemaVersion":1,"documents":[]}"#;
        fs.put(MANIFEST_PATH, prior);
        fs.fail_write.store(true, Ordering::SeqCst);

        let result = adopt(&fs, "docs/legacy.sgendesign");

        assert!(matches!(result, Err(ProjectManifestStoreError::Write(_))));
        assert_eq!(fs.get(MANIFEST_PATH).unwrap(), prior);
    }

    #[test]
    fn failed_readback_reports_unverified_durability_without_claiming_rollback() {
        let fs = ControlledFs::default();
        source(&fs);
        fs.fail_manifest_readback.store(true, Ordering::SeqCst);

        let result = adopt(&fs, "docs/legacy.sgendesign");

        assert_eq!(result, Err(ProjectManifestStoreError::DurabilityUnverified));
        assert!(
            fs.get(MANIFEST_PATH).is_some(),
            "atomic write may have committed before readback failed"
        );
    }

    #[test]
    fn source_read_failure_does_not_create_or_replace_manifest() {
        let fs = ControlledFs::default();
        fs.fail_source_read.store(true, Ordering::SeqCst);

        let result = adopt(&fs, "docs/legacy.sgendesign");

        assert!(matches!(
            result,
            Err(ProjectManifestStoreError::SourceRead(_))
        ));
        assert!(fs.get(MANIFEST_PATH).is_none());
    }
}
