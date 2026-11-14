//! Host-layer errors (lifecycle / settings / IPC). No OS types.

use sgenaxis_ports::PortError;

/// Failures at the HOST boundary (not business-domain errors).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum HostError {
    Lifecycle(String),
    Settings(String),
    Ipc(String),
    /// PD-BOARD-LIVE-01: local board file read／parse (read-only; never write-back).
    Board(String),
    Port(PortError),
}

impl std::fmt::Display for HostError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            HostError::Lifecycle(m) => write!(f, "lifecycle: {m}"),
            HostError::Settings(m) => write!(f, "settings: {m}"),
            HostError::Ipc(m) => write!(f, "ipc: {m}"),
            HostError::Board(m) => write!(f, "board: {m}"),
            HostError::Port(e) => write!(f, "port: {e}"),
        }
    }
}

impl std::error::Error for HostError {}

impl From<PortError> for HostError {
    fn from(value: PortError) -> Self {
        HostError::Port(value)
    }
}
