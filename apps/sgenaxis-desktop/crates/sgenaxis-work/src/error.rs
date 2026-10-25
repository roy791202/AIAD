//! WORK use-case errors — no OS types.

use std::fmt;

use sgenaxis_ports::PortError;

/// Failures from workspace register / bind / lease / select.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkError {
    /// Path missing or not a usable project root.
    PathNotFound(String),
    /// Probe reported no read/write access.
    PathNotAccessible(String),
    /// Invalid / empty path string.
    InvalidPath(String),
    /// Unknown project id.
    UnknownProject(String),
    /// Active execution lease blocks root rebind.
    LeaseActive {
        project_id: String,
        run_id: String,
        bound_root: String,
    },
    /// PD-EXEC-BIND-01: start_run binding ≠ active lease (root／work item／fingerprint).
    LeaseMismatch {
        field: String,
        expected: String,
        got: String,
    },
    /// Port / store failure (wrapped message).
    Port(String),
}

impl fmt::Display for WorkError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            WorkError::PathNotFound(p) => write!(f, "path not found: {p}"),
            WorkError::PathNotAccessible(p) => write!(f, "path not accessible: {p}"),
            WorkError::InvalidPath(p) => write!(f, "invalid path: {p}"),
            WorkError::UnknownProject(id) => write!(f, "unknown project: {id}"),
            WorkError::LeaseActive {
                project_id,
                run_id,
                bound_root,
            } => write!(
                f,
                "execution lease active for {project_id} (run={run_id}, root={bound_root}); only one in-flight Run (PD-EXEC-SINGLE-01／CANCEL-01); reconcile/cancel before new mutation (no blind re-run)"
            ),
            WorkError::LeaseMismatch {
                field,
                expected,
                got,
            } => write!(
                f,
                "WORK lease mismatch on {field} (expected={expected}, got={got})"
            ),
            WorkError::Port(s) => write!(f, "port: {s}"),
        }
    }
}

impl std::error::Error for WorkError {}

impl From<PortError> for WorkError {
    fn from(e: PortError) -> Self {
        match e {
            PortError::NotFound(s) => WorkError::PathNotFound(s),
            PortError::PermissionDenied(s) => WorkError::PathNotAccessible(s),
            PortError::InvalidPath(s) => WorkError::InvalidPath(s),
            other => WorkError::Port(other.to_string()),
        }
    }
}
