//! Project-local document identity records owned by WORK.
//!
//! This module defines the v1 manifest contract and adoption decision seam.
//! Persistence is performed by the HOST filesystem adapter; identity and
//! conflict decisions remain on the authoritative [`crate::Project`].

pub const PROJECT_MANIFEST_SCHEMA: &str = "sgenaxis.project-manifest";
pub const PROJECT_MANIFEST_VERSION: u32 = 1;
pub const PROJECT_MANIFEST_RELATIVE_PATH: &str = ".sgenaxis/project-manifest.json";

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProjectDocumentKind {
    Ess,
    Design,
}

impl ProjectDocumentKind {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Ess => "ess",
            Self::Design => "design",
        }
    }

    pub fn from_reference(reference: &str) -> Result<Self, ProjectManifestError> {
        let lower = reference.to_ascii_lowercase();
        if lower.ends_with(".ess") {
            Ok(Self::Ess)
        } else if lower.ends_with(".sgendesign") {
            Ok(Self::Design)
        } else {
            Err(ProjectManifestError::UnsupportedKind)
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectDocumentRecord {
    pub document_id: String,
    pub kind: ProjectDocumentKind,
    pub reference: String,
    pub revision_id: String,
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ProjectManifest {
    pub documents: Vec<ProjectDocumentRecord>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProjectManifestError {
    InvalidProjectRoot,
    InvalidReference,
    UnsupportedKind,
    InvalidRevision,
    InvalidDocumentId,
    DocumentIdConflict,
    RevisionConflict,
    ReferenceConflict,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DocumentAdoptionPlan {
    AlreadyAdopted(ProjectDocumentRecord),
    Persist {
        record: ProjectDocumentRecord,
        manifest: ProjectManifest,
    },
}

/// Canonicalizes a project-relative reference without resolving filesystem
/// links. The HOST must use this value with the already-bound project root.
pub fn normalize_project_reference(reference: &str) -> Result<String, ProjectManifestError> {
    if reference.is_empty() || reference.contains('\0') {
        return Err(ProjectManifestError::InvalidReference);
    }
    let normalized = reference.replace('\\', "/");
    if normalized.starts_with('/') {
        return Err(ProjectManifestError::InvalidReference);
    }
    let mut parts = normalized.split('/');
    let first = parts.next().ok_or(ProjectManifestError::InvalidReference)?;
    if first.is_empty() || first.contains(':') {
        return Err(ProjectManifestError::InvalidReference);
    }
    if std::iter::once(first)
        .chain(parts.clone())
        .any(|part| part.is_empty() || part == "." || part == ".." || part.contains(':'))
    {
        return Err(ProjectManifestError::InvalidReference);
    }
    ProjectDocumentKind::from_reference(&normalized)?;
    Ok(normalized)
}

/// Validate the exact lowercase SHA-256 revision representation used by v1.
pub fn validate_revision_id(revision_id: &str) -> Result<(), ProjectManifestError> {
    let digest = revision_id
        .strip_prefix("sha256:")
        .ok_or(ProjectManifestError::InvalidRevision)?;
    if digest.len() != 64
        || !digest
            .bytes()
            .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
    {
        return Err(ProjectManifestError::InvalidRevision);
    }
    Ok(())
}

/// Validate the canonical lowercase UUID string supplied by the outer HOST
/// adapter. WORK never creates entropy or reaches the operating system.
pub fn validate_document_id(document_id: &str) -> Result<(), ProjectManifestError> {
    let bytes = document_id.as_bytes();
    if bytes.len() != 36
        || [8, 13, 18, 23].iter().any(|&index| bytes[index] != b'-')
        || bytes.iter().enumerate().any(|(index, byte)| {
            if [8, 13, 18, 23].contains(&index) {
                false
            } else {
                !byte.is_ascii_digit() && !(b'a'..=b'f').contains(byte)
            }
        })
    {
        return Err(ProjectManifestError::InvalidDocumentId);
    }
    Ok(())
}

/// Decode a manifest record's schema enum from its stable wire token.
pub fn document_kind_from_str(value: &str) -> Result<ProjectDocumentKind, ProjectManifestError> {
    match value {
        "ess" => Ok(ProjectDocumentKind::Ess),
        "design" => Ok(ProjectDocumentKind::Design),
        _ => Err(ProjectManifestError::UnsupportedKind),
    }
}

pub(crate) fn prepare_adoption(
    existing: &ProjectManifest,
    reference: &str,
    kind: ProjectDocumentKind,
    revision_id: &str,
    document_id_candidate: &str,
) -> Result<DocumentAdoptionPlan, ProjectManifestError> {
    let reference = normalize_project_reference(reference)?;
    validate_revision_id(revision_id)?;
    validate_document_id(document_id_candidate)?;
    if ProjectDocumentKind::from_reference(&reference)? != kind {
        return Err(ProjectManifestError::UnsupportedKind);
    }

    let mut ids = std::collections::BTreeSet::new();
    let mut references = std::collections::BTreeSet::new();
    for record in &existing.documents {
        validate_document_id(&record.document_id)?;
        if !ids.insert(record.document_id.as_str())
            || !references.insert(record.reference.as_str())
            || normalize_project_reference(&record.reference)? != record.reference
        {
            return Err(ProjectManifestError::ReferenceConflict);
        }
        validate_revision_id(&record.revision_id)?;
        if ProjectDocumentKind::from_reference(&record.reference)? != record.kind {
            return Err(ProjectManifestError::UnsupportedKind);
        }
    }

    if let Some(record) = existing
        .documents
        .iter()
        .find(|record| record.reference == reference)
    {
        if record.kind != kind {
            return Err(ProjectManifestError::ReferenceConflict);
        }
        if record.revision_id != revision_id {
            return Err(ProjectManifestError::RevisionConflict);
        }
        return Ok(DocumentAdoptionPlan::AlreadyAdopted(record.clone()));
    }

    if ids.contains(document_id_candidate) {
        return Err(ProjectManifestError::DocumentIdConflict);
    }
    let record = ProjectDocumentRecord {
        document_id: document_id_candidate.to_owned(),
        kind,
        reference,
        revision_id: revision_id.to_owned(),
    };
    let mut manifest = existing.clone();
    manifest.documents.push(record.clone());
    Ok(DocumentAdoptionPlan::Persist { record, manifest })
}
