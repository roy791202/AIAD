//! Registered project record (authority lives in WORK store).

use crate::id::ProjectId;

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
