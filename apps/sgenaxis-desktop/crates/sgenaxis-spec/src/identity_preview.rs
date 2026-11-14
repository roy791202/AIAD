//! Derived identity claims only; no adoption, serialization or authoritative state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DocumentKind {
    Ess,
    Design,
}
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct IdentityClaims {
    pub document_id: Option<String>,
    pub revision_id: Option<String>,
    pub base_revision_id: Option<String>,
    pub accepted_base_bytes: Option<Vec<u8>>,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityInspectionRequest {
    pub path: String,
    pub kind: DocumentKind,
    pub claims: IdentityClaims,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityState {
    LegacyUnidentified,
    PreviewCurrent,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct IdentityPreview {
    pub payload_sha256: String,
    pub document_id: Option<String>,
    pub state: IdentityState,
    pub validated_base_sha256: Option<String>,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum IdentityError {
    InvalidRequest,
    MalformedDocument,
    UnsupportedSchema,
    DuplicateElementId,
    RevisionPayloadMismatch,
    BaseMissing,
    StaleSource,
    PermissionDenied,
    SourceReadFailed,
}
pub fn inspect_identity_claims(
    bytes: &[u8],
    claims: &IdentityClaims,
) -> Result<IdentityPreview, IdentityError> {
    use crate::packet::source_sha256;
    if claims
        .document_id
        .as_ref()
        .is_some_and(|id| id.trim().is_empty())
    {
        return Err(IdentityError::InvalidRequest);
    }
    let hash = source_sha256(bytes);
    if claims
        .revision_id
        .as_ref()
        .is_some_and(|revision| revision != &hash)
    {
        return Err(IdentityError::RevisionPayloadMismatch);
    }
    let base = match &claims.base_revision_id {
        None => None,
        Some(revision) => {
            let bytes = claims
                .accepted_base_bytes
                .as_ref()
                .ok_or(IdentityError::BaseMissing)?;
            if source_sha256(bytes) != *revision {
                return Err(IdentityError::BaseMissing);
            }
            Some(revision.clone())
        }
    };
    Ok(IdentityPreview {
        payload_sha256: hash,
        document_id: claims.document_id.clone(),
        state: if claims.document_id.is_some() {
            IdentityState::PreviewCurrent
        } else {
            IdentityState::LegacyUnidentified
        },
        validated_base_sha256: base,
    })
}
