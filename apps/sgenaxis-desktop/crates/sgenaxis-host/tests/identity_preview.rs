use sgenaxis_host::identity_preview::inspect_document_identity;
use sgenaxis_ports::{FileSystemPort, PortError};
use sgenaxis_spec::identity_preview::*;
use std::sync::Mutex;

struct ReadOnlyFs {
    reads: Mutex<Vec<Result<Vec<u8>, PortError>>>,
    paths: Mutex<Vec<String>>,
}
impl ReadOnlyFs {
    fn sequence(values: Vec<Result<Vec<u8>, PortError>>) -> Self {
        Self {
            reads: Mutex::new(values),
            paths: Mutex::new(vec![]),
        }
    }
    fn stable(bytes: &[u8]) -> Self {
        Self::sequence(vec![Ok(bytes.to_vec()), Ok(bytes.to_vec())])
    }
}
impl FileSystemPort for ReadOnlyFs {
    fn read(&self, path: &str) -> Result<Vec<u8>, PortError> {
        self.paths.lock().unwrap().push(path.into());
        self.reads.lock().unwrap().remove(0)
    }
    fn read_to_string(&self, _: &str) -> Result<String, PortError> {
        panic!("unexpected alternate read")
    }
    fn exists(&self, _: &str) -> Result<bool, PortError> {
        panic!("unexpected exists")
    }
    fn is_file(&self, _: &str) -> Result<bool, PortError> {
        panic!("unexpected is_file")
    }
    fn write_atomic(&self, _: &str, _: &[u8]) -> Result<(), PortError> {
        panic!("inspection attempted write")
    }
    fn create_dir_all(&self, _: &str) -> Result<(), PortError> {
        panic!("inspection attempted mkdir")
    }
    fn remove_file(&self, _: &str) -> Result<(), PortError> {
        panic!("inspection attempted delete")
    }
}
const DESIGN: &[u8] = br#"{"format":"sgenaxis.design","formatVersion":1,"nodes":[]}"#;
const ESS: &[u8] = br#"<eluslotScene format="eluslot.ess" formatVersion="1" encoding="xml"><architecture encoding="xml"><eluslotArch format="eluslot.esml" formatVersion="1"><nodes/><edges/></eluslotArch></architecture></eluslotScene>"#;
fn request(kind: DocumentKind) -> IdentityInspectionRequest {
    IdentityInspectionRequest {
        path: "copy/document".into(),
        kind,
        claims: IdentityClaims::default(),
    }
}
#[test]
fn legacy_both_formats_are_read_only_and_do_not_require_git() {
    for (kind, bytes) in [(DocumentKind::Design, DESIGN), (DocumentKind::Ess, ESS)] {
        let fs = ReadOnlyFs::stable(bytes);
        let result = inspect_document_identity(&fs, &request(kind)).unwrap();
        assert_eq!(result.state, IdentityState::LegacyUnidentified);
        assert!(result.document_id.is_none());
        assert_eq!(fs.paths.lock().unwrap().len(), 2);
    }
}
#[test]
fn display_path_does_not_change_explicit_identity() {
    let mut req = request(DocumentKind::Design);
    req.claims.document_id = Some("doc-1".into());
    let before = inspect_document_identity(&ReadOnlyFs::stable(DESIGN), &req).unwrap();
    req.path = "moved/renamed.sgendesign".into();
    let after = inspect_document_identity(&ReadOnlyFs::stable(DESIGN), &req).unwrap();
    assert_eq!(before, after);
    assert_eq!(after.document_id.as_deref(), Some("doc-1"));
}
#[test]
fn changed_source_never_publishes_preview() {
    let fs = ReadOnlyFs::sequence(vec![Ok(DESIGN.to_vec()), Ok(b"changed".to_vec())]);
    assert_eq!(
        inspect_document_identity(&fs, &request(DocumentKind::Design)),
        Err(IdentityError::StaleSource)
    );
}
#[test]
fn blank_location_is_rejected_before_io() {
    let fs = ReadOnlyFs::sequence(vec![]);
    let mut req = request(DocumentKind::Design);
    req.path = "  ".into();
    assert_eq!(
        inspect_document_identity(&fs, &req),
        Err(IdentityError::InvalidRequest)
    );
    assert!(fs.paths.lock().unwrap().is_empty());
}
#[test]
fn permission_failure_at_either_read_is_explicit() {
    for values in [
        vec![Err(PortError::PermissionDenied("first".into()))],
        vec![
            Ok(DESIGN.to_vec()),
            Err(PortError::PermissionDenied("second".into())),
        ],
    ] {
        assert_eq!(
            inspect_document_identity(
                &ReadOnlyFs::sequence(values),
                &request(DocumentKind::Design)
            ),
            Err(IdentityError::PermissionDenied)
        );
    }
}
#[test]
fn missing_source_is_not_a_permission_error() {
    let fs = ReadOnlyFs::sequence(vec![Err(PortError::NotFound("missing".into()))]);
    assert_eq!(
        inspect_document_identity(&fs, &request(DocumentKind::Design)),
        Err(IdentityError::SourceReadFailed)
    );
}
#[test]
fn malformed_unknown_and_duplicate_designs_are_rejected() {
    for (bytes, expected) in [
        (&b"invalid"[..], IdentityError::MalformedDocument),
        (&br#"{"format":"sgenaxis.design","formatVersion":2,"nodes":[]}"#[..], IdentityError::UnsupportedSchema),
        (&br#"{"format":"wrong","formatVersion":1,"nodes":[]}"#[..], IdentityError::UnsupportedSchema),
        (&br#"{"format":"sgenaxis.design","formatVersion":1,"nodes":[{"id":"same","type":"Form"},{"id":"same","type":"Form"}]}"#[..], IdentityError::DuplicateElementId),
    ] {
        let fs = ReadOnlyFs::sequence(vec![Ok(bytes.to_vec())]);
        assert_eq!(inspect_document_identity(&fs, &request(DocumentKind::Design)), Err(expected));
    }
}
#[test]
fn invalid_ess_schema_and_duplicate_ids_are_rejected() {
    for (bytes, expected) in [
        (&b"<broken"[..], IdentityError::MalformedDocument),
        (&br#"<eluslotScene format="eluslot.ess" formatVersion="2" encoding="xml"/>"#[..], IdentityError::UnsupportedSchema),
        (&br#"<eluslotScene format="eluslot.ess" formatVersion="1" encoding="xml"><architecture encoding="xml"><eluslotArch format="eluslot.esml" formatVersion="1"><nodes><node id="a"/><node id="a"/></nodes><edges/></eluslotArch></architecture></eluslotScene>"#[..], IdentityError::DuplicateElementId),
    ] {
        assert_eq!(inspect_document_identity(&ReadOnlyFs::sequence(vec![Ok(bytes.to_vec())]), &request(DocumentKind::Ess)), Err(expected));
    }
}
