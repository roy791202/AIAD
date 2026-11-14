//! Tauri outer-adapter source for cross-project document identity candidates.
//!
//! This module supplies entropy only. WORK remains responsible for validating
//! the UUID candidate, checking manifest conflicts, and owning the identity.

use sgenaxis_ports::FileSystemPort;
use sgenaxis_work::Project;

pub(crate) fn new_document_id_candidate() -> String {
    uuid::Uuid::new_v4().to_string()
}

/// Outer HOST adapter handoff for an explicit adoption request. No Tauri IPC
/// command is registered here; a future command must pass its bound Project.
#[allow(dead_code)]
pub(crate) fn adopt_project_document_by_reference(
    fs: &dyn FileSystemPort,
    project: &Project,
    reference: &str,
) -> Result<sgenaxis_host::DocumentAdoptionOutcome, sgenaxis_host::ProjectManifestStoreError> {
    let candidate = new_document_id_candidate();
    sgenaxis_host::adopt_project_document(fs, project, reference, &candidate)
}

#[cfg(test)]
mod tests {
    use super::{adopt_project_document_by_reference, new_document_id_candidate};
    use sgenaxis_ports::{FileSystemPort, PortError};
    use sgenaxis_work::{Project, ProjectId};
    use std::collections::{HashMap, HashSet};
    use std::sync::Mutex;

    #[derive(Default)]
    struct MemoryFs(Mutex<HashMap<String, Vec<u8>>>);

    impl MemoryFs {
        fn put(&self, path: &str, bytes: &[u8]) {
            self.0
                .lock()
                .unwrap()
                .insert(path.to_owned(), bytes.to_vec());
        }

        fn get(&self, path: &str) -> Option<Vec<u8>> {
            self.0.lock().unwrap().get(path).cloned()
        }
    }

    impl FileSystemPort for MemoryFs {
        fn exists(&self, path: &str) -> Result<bool, PortError> {
            Ok(self.0.lock().unwrap().contains_key(path))
        }

        fn read_to_string(&self, path: &str) -> Result<String, PortError> {
            String::from_utf8(self.read(path)?).map_err(|e| PortError::Io(e.to_string()))
        }

        fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
            self.get(path)
                .ok_or_else(|| PortError::NotFound(path.to_owned()))
        }

        fn write_atomic(&self, path: &str, contents: &[u8]) -> Result<(), PortError> {
            self.put(path, contents);
            Ok(())
        }

        fn create_dir_all(&self, _path: &str) -> Result<(), PortError> {
            Ok(())
        }

        fn is_file(&self, path: &str) -> Result<bool, PortError> {
            self.exists(path)
        }

        fn remove_file(&self, path: &str) -> Result<(), PortError> {
            self.0
                .lock()
                .unwrap()
                .remove(path)
                .map(|_| ())
                .ok_or_else(|| PortError::NotFound(path.to_owned()))
        }
    }

    #[test]
    fn candidates_are_canonical_v4_uuids_and_unique_in_a_batch() {
        let candidates = (0..256)
            .map(|_| new_document_id_candidate())
            .collect::<Vec<_>>();
        assert!(candidates.iter().all(|candidate| {
            candidate.len() == 36
                && candidate.as_bytes()[14] == b'4'
                && matches!(candidate.as_bytes()[19], b'8' | b'9' | b'a' | b'b')
                && uuid::Uuid::parse_str(candidate)
                    .is_ok_and(|parsed| parsed.to_string() == *candidate)
        }));
        assert_eq!(
            candidates.iter().collect::<HashSet<_>>().len(),
            candidates.len()
        );
    }

    #[test]
    fn outer_adapter_hands_uuid_to_host_and_manifest() {
        let fs = MemoryFs::default();
        fs.put(
            "/fixture/project/docs/legacy.ess",
            b"existing project document",
        );
        let project = Project::new(
            ProjectId::new("project-fixture"),
            "/fixture/project".into(),
            "/fixture/project".into(),
        );

        let outcome = adopt_project_document_by_reference(&fs, &project, "docs/legacy.ess")
            .expect("controlled explicit adoption succeeds");
        let sgenaxis_host::DocumentAdoptionOutcome::Adopted(record) = outcome else {
            panic!("first adoption should persist");
        };
        assert!(uuid::Uuid::parse_str(&record.document_id).is_ok());
        let manifest = fs
            .get("/fixture/project/.sgenaxis/project-manifest.json")
            .expect("manifest saved through controlled FileSystemPort");
        let wire: serde_json::Value = serde_json::from_slice(&manifest).unwrap();
        assert_eq!(wire["documents"][0]["documentId"], record.document_id);
    }
}
