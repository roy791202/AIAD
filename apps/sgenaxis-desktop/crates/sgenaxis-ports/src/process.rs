//! Process Port — spawn / wait / cancel without exposing `std::process` types.

use crate::PortError;

/// Opaque process handle for Port callers.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub struct ProcessId(pub u64);

/// Independent observation of one captured process output stream.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub enum StreamCompletion {
    #[default]
    Open,
    Eof,
    Error(String),
}

/// Non-blocking drain of stdout／stderr text (lossy UTF-8 from adapter is OK).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ProcessOutput {
    pub stdout: String,
    pub stderr: String,
    pub stdout_completion: StreamCompletion,
    pub stderr_completion: StreamCompletion,
}

impl ProcessOutput {
    pub fn is_empty(&self) -> bool {
        self.stdout.is_empty() && self.stderr.is_empty()
    }
}

/// Start / observe / cancel external processes (Agent CLI — PD-EXEC-*).
///
/// Adapters must not expose OS process types through this trait.
pub trait ProcessPort: Send {
    /// Start `program` with `args` optionally in `cwd`. Returns a local id.
    fn start(
        &mut self,
        program: &str,
        args: &[&str],
        cwd: Option<&str>,
    ) -> Result<ProcessId, PortError>;

    /// Non-blocking poll: `None` still running; `Some(code)` exited.
    fn try_wait(&mut self, id: ProcessId) -> Result<Option<i32>, PortError>;

    /// Request cancel / kill. Idempotent if already exited.
    fn cancel(&mut self, id: ProcessId) -> Result<(), PortError>;

    /// Non-blocking drain of available stdout／stderr since last call.
    ///
    /// Empty strings mean no new bytes. Safe to call after exit (final drain).
    fn try_read(&mut self, id: ProcessId) -> Result<ProcessOutput, PortError>;
}
