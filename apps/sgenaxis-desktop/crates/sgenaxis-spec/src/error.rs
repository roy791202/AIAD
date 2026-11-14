//! SPEC domain errors (PD-SPEC-01).

/// Errors from ModuleSpec load / revision / mutation commands.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SpecError {
    /// JSON or schema could not be parsed into a ModuleSpec.
    InvalidSpec(String),
    /// Referenced revision id is unknown in the store.
    UnknownRevision(String),
    /// Approved revision must not be mutated in place — open a new version.
    ImmutableRevision {
        revision_id: String,
        hint: &'static str,
    },
    /// Public contract change on a locked revision requires human replan.
    ReplanRequired {
        revision_id: String,
        contract_id: String,
    },
    /// Evidence ref id is unknown.
    UnknownEvidence(String),
}

impl std::fmt::Display for SpecError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SpecError::InvalidSpec(m) => write!(f, "invalid ModuleSpec: {m}"),
            SpecError::UnknownRevision(id) => write!(f, "unknown revision: {id}"),
            SpecError::ImmutableRevision { revision_id, hint } => {
                write!(f, "revision {revision_id} is immutable: {hint}")
            }
            SpecError::ReplanRequired {
                revision_id,
                contract_id,
            } => write!(
                f,
                "REPLAN_REQUIRED: locked revision {revision_id} contract {contract_id}"
            ),
            SpecError::UnknownEvidence(id) => write!(f, "unknown evidence ref: {id}"),
        }
    }
}

impl std::error::Error for SpecError {}
