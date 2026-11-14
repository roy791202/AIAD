//! Shared port error — no OS error types leaked.

use std::fmt;

/// Portable failure from any Port implementation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PortError {
    NotFound(String),
    AlreadyExists(String),
    PermissionDenied(String),
    InvalidPath(String),
    Io(String),
    Process(String),
    Git(String),
    Cancelled(String),
    Other(String),
}

impl fmt::Display for PortError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PortError::NotFound(s) => write!(f, "not found: {s}"),
            PortError::AlreadyExists(s) => write!(f, "already exists: {s}"),
            PortError::PermissionDenied(s) => write!(f, "permission denied: {s}"),
            PortError::InvalidPath(s) => write!(f, "invalid path: {s}"),
            PortError::Io(s) => write!(f, "io: {s}"),
            PortError::Process(s) => write!(f, "process: {s}"),
            PortError::Git(s) => write!(f, "git: {s}"),
            PortError::Cancelled(s) => write!(f, "cancelled: {s}"),
            PortError::Other(s) => write!(f, "{s}"),
        }
    }
}

impl std::error::Error for PortError {}
