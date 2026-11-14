//! Registered project record (authority lives in WORK store).

use crate::id::ProjectId;
use crate::manifest::{
    normalize_project_reference, prepare_adoption, DocumentAdoptionPlan, ProjectDocumentKind,
    ProjectManifest, ProjectManifestError, PROJECT_MANIFEST_RELATIVE_PATH,
};
use sgenaxis_ports::{GitPort, GitStatus, PortError};

/// Authoritative project entry after successful register / rebind.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Project {
    pub id: ProjectId,
    /// Display / bound root as last successfully validated.
    pub root: String,
    /// Dedup key (case-folded / alias-resolved).
    pub canonical_root: String,
    pub display_name: String,
}

impl Project {
    pub fn new(id: ProjectId, root: String, canonical_root: String) -> Self {
        let display_name = display_name_from_root(&root);
        Self {
            id,
            root,
            canonical_root,
            display_name,
        }
    }

    /// Read the Git status capability for this authoritative WORK root.
    ///
    /// `None` means no Git capability was supplied; `Some(Err(_))` preserves
    /// the adapter's typed failure without guessing whether Git is absent or
    /// the root is not a repository. Neither case invalidates the file-mode
    /// project session. A successful value is only the snapshot returned by
    /// the existing read-only `GitPort`.
    ///
    /// This narrow application seam does not initialize repositories or
    /// synthesize branch / HEAD data.
    pub fn git_status(&self, git: Option<&dyn GitPort>) -> Option<Result<GitStatus, PortError>> {
        git.map(|git| git.status(&self.root))
    }

    /// Prepare an explicit v1 manifest adoption. WORK Project is the authority
    /// for identity and conflict decisions; callers persist only this returned
    /// plan through the existing filesystem capability.
    pub fn plan_document_adoption(
        &self,
        manifest: &ProjectManifest,
        reference: &str,
        kind: ProjectDocumentKind,
        revision_id: &str,
        document_id_candidate: &str,
    ) -> Result<DocumentAdoptionPlan, ProjectManifestError> {
        prepare_adoption(
            manifest,
            reference,
            kind,
            revision_id,
            document_id_candidate,
        )
    }

    /// Resolve a normalized project-relative reference under the bound root.
    pub fn document_path(&self, reference: &str) -> Result<String, ProjectManifestError> {
        let root = self.root.trim();
        if root.is_empty() || root.contains('\0') {
            return Err(ProjectManifestError::InvalidProjectRoot);
        }
        let reference = normalize_project_reference(reference)?;
        ProjectDocumentKind::from_reference(&reference)?;
        let separator = if root.ends_with(['/', '\\']) { "" } else { "/" };
        Ok(format!("{root}{separator}{reference}"))
    }

    /// Return the v1 manifest's project-local storage path.
    pub fn manifest_path(&self) -> Result<String, ProjectManifestError> {
        let root = self.root.trim();
        if root.is_empty() || root.contains('\0') {
            return Err(ProjectManifestError::InvalidProjectRoot);
        }
        let separator = if root.ends_with(['/', '\\']) { "" } else { "/" };
        Ok(format!("{root}{separator}{PROJECT_MANIFEST_RELATIVE_PATH}"))
    }
}

fn display_name_from_root(root: &str) -> String {
    let trimmed = root.trim_end_matches(['/', '\\']);
    trimmed
        .rsplit(['/', '\\'])
        .next()
        .unwrap_or(trimmed)
        .to_string()
}

/// Outcome of [`crate::WorkspaceService::register`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegisterOutcome {
    /// New project created and root bound.
    Created(Project),
    /// Same canonical root already registered — no duplicate.
    Existing(Project),
}
