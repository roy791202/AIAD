use sgenaxis_spec::identity_preview::*;
use sgenaxis_spec::packet::source_sha256;

#[test]
fn legacy_is_derived_without_fabricating_identity() {
    let bytes = b"exact source bytes\r\n";
    let result = inspect_identity_claims(bytes, &IdentityClaims::default()).unwrap();
    assert_eq!(result.state, IdentityState::LegacyUnidentified);
    assert_eq!(result.document_id, None);
    assert_eq!(result.payload_sha256, source_sha256(bytes));
    assert_eq!(result.validated_base_sha256, None);
}
#[test]
fn explicit_identity_and_revision_are_preserved_exactly() {
    let bytes = b"payload";
    let claims = IdentityClaims {
        document_id: Some("Doc-A".into()),
        revision_id: Some(source_sha256(bytes)),
        ..Default::default()
    };
    let result = inspect_identity_claims(bytes, &claims).unwrap();
    assert_eq!(result.document_id.as_deref(), Some("Doc-A"));
    assert_eq!(result.state, IdentityState::PreviewCurrent);
    assert_eq!(claims.document_id.as_deref(), Some("Doc-A"));
}
#[test]
fn revision_must_hash_exact_bytes_including_whitespace() {
    let claims = IdentityClaims {
        revision_id: Some(source_sha256(b"payload")),
        ..Default::default()
    };
    assert_eq!(
        inspect_identity_claims(b"payload\n", &claims),
        Err(IdentityError::RevisionPayloadMismatch)
    );
}
#[test]
fn base_reference_without_matching_bytes_is_not_ancestry() {
    for base in [None, Some(b"wrong".to_vec())] {
        let claims = IdentityClaims {
            base_revision_id: Some(source_sha256(b"base")),
            accepted_base_bytes: base,
            ..Default::default()
        };
        assert_eq!(
            inspect_identity_claims(b"new", &claims),
            Err(IdentityError::BaseMissing)
        );
    }
}
#[test]
fn matching_base_is_validated_but_unreferenced_bytes_are_not_a_base() {
    let mut claims = IdentityClaims {
        accepted_base_bytes: Some(b"base".to_vec()),
        ..Default::default()
    };
    assert_eq!(
        inspect_identity_claims(b"new", &claims)
            .unwrap()
            .validated_base_sha256,
        None
    );
    claims.base_revision_id = Some(source_sha256(b"base"));
    assert_eq!(
        inspect_identity_claims(b"new", &claims)
            .unwrap()
            .validated_base_sha256,
        claims.base_revision_id
    );
}
#[test]
fn blank_explicit_identity_is_rejected() {
    let claims = IdentityClaims {
        document_id: Some("  ".into()),
        ..Default::default()
    };
    assert_eq!(
        inspect_identity_claims(b"x", &claims),
        Err(IdentityError::InvalidRequest)
    );
}
