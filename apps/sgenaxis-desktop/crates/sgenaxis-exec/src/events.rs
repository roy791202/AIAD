//! Unified Run event stream (PRODUCT-DEVELOPMENT §6.3).
//!
//! CLI and MCP adapters emit the same `AgentChunk` variants (started／chunk／progress／exited／failed).

use crate::port::{AgentProvider, RunId};
use crate::settings::CliToolKind;

/// Stdout vs stderr for streamed text chunks.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum OutputStream {
    Stdout,
    Stderr,
}

/// How a run ended — for accounting; **not** a work-item green light.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ExitClassification {
    Success,
    Failure,
    Cancelled,
    Crashed,
}

impl ExitClassification {
    /// Map a process exit code to a classification (CLI path).
    pub fn from_exit_code(code: i32) -> Self {
        match code {
            0 => ExitClassification::Success,
            -1 => ExitClassification::Cancelled,
            c if c < 0 => ExitClassification::Crashed,
            _ => ExitClassification::Failure,
        }
    }
}

/// Shared Run event (started／chunk／progress／exited／failed).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum AgentChunk {
    Started {
        run_id: RunId,
        provider: AgentProvider,
        dry_run: bool,
        tool: Option<CliToolKind>,
    },
    Chunk {
        run_id: RunId,
        stream: OutputStream,
        text: String,
    },
    Progress {
        run_id: RunId,
        message: String,
    },
    Exited {
        run_id: RunId,
        classification: ExitClassification,
        exit_code: Option<i32>,
    },
    Failed {
        run_id: RunId,
        message: String,
    },
}

impl AgentChunk {
    pub fn run_id(&self) -> RunId {
        match self {
            AgentChunk::Started { run_id, .. }
            | AgentChunk::Chunk { run_id, .. }
            | AgentChunk::Progress { run_id, .. }
            | AgentChunk::Exited { run_id, .. }
            | AgentChunk::Failed { run_id, .. } => *run_id,
        }
    }
}
