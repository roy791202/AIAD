//! Interactive fixture Port — PTY session boundary (EA-A0 skeleton only).
//!
//! Distinct from [`crate::ProcessPort`]: merged PTY stream, resize, stop/observe.
//! No argv/shell/tool/auth routes. Adapters own native handles; HOST owns session state.

/// Opaque interactive fixture resource id (not [`crate::ProcessId`]).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct InteractiveId(pub u64);

/// Fixture PTY dimensions; application validates approved bounds before the adapter.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct InteractiveSize {
    pub cols: u16,
    pub rows: u16,
}

/// Read side of the merged PTY output stream.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ReadState {
    Open,
    Eof,
    Error(String),
}

/// Adapter cleanup progress for a fixture child.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Cleanup {
    Pending,
    Complete,
    Failed,
}

/// Non-blocking observation of fixture output / exit / cleanup.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InteractiveObservation {
    pub output: Vec<u8>,
    pub child_exit: Option<i32>,
    pub read_state: ReadState,
    pub cleanup: Cleanup,
}

/// Sanitized interactive error kind (payload must not contain secrets).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InteractiveErrorKind {
    Unsupported,
    Spawn,
    Input,
    Resize,
    Observe,
    Stop,
    Cleanup,
}

/// Typed interactive fixture error.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct InteractiveError {
    pub kind: InteractiveErrorKind,
    pub message: String,
}

/// Direct-child fixture PTY port (EA-A0). Not ProcessPort; not Agent/provider.
pub trait InteractiveFixturePort: Send {
    fn start_fixture(
        &mut self,
        executable: &str,
        cwd: &str,
        size: InteractiveSize,
    ) -> Result<InteractiveId, InteractiveError>;

    fn write_text(&mut self, id: InteractiveId, text: &str) -> Result<(), InteractiveError>;

    fn resize(&mut self, id: InteractiveId, size: InteractiveSize) -> Result<(), InteractiveError>;

    fn request_stop(&mut self, id: InteractiveId) -> Result<(), InteractiveError>;

    fn poll(&mut self, id: InteractiveId) -> Result<InteractiveObservation, InteractiveError>;
}
