//! Domain events emitted **after** debounce — drive Dirty／projections.
//!
//! UI must subscribe to Core projections only; never ingest [`crate::SourceEvent`].

use sgenaxis_exec::{ExitClassification, RunId};

use crate::source::FsChangeKind;

/// Coalesced domain signal ready to mark dirty / update projections.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DomainEvent {
    /// One or more FS changes for a path (last kind wins within the window).
    FsDirty {
        path: String,
        kind: FsChangeKind,
        burst_count: u32,
    },
    /// Git worktree changed (coalesced per repo root).
    GitDirty {
        repo_root: String,
        hint: String,
        burst_count: u32,
    },
    /// Agent run produced chunks／lifecycle within the window.
    AgentDirty {
        run_id: RunId,
        /// Last chunk kind label for tests／projection (no secrets).
        last_kind: AgentEventKind,
        burst_count: u32,
        /// Present when `last_kind` is [`AgentEventKind::Exited`] (EXEC end class).
        classification: Option<ExitClassification>,
    },
    /// PD-LISTEN-RECON-01: abnormal／non-success end → 待對帳 (≠ work-item green).
    AgentReconcile {
        run_id: RunId,
        classification: ExitClassification,
        exit_code: Option<i32>,
        /// True when a [`AgentEventKind::Chunk`] immediately before exit was retained.
        last_chunk_retained: bool,
    },
}

/// Coarse AgentChunk classification for projections (no payload text).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgentEventKind {
    Started,
    Chunk,
    Progress,
    Exited,
    Failed,
}

impl AgentEventKind {
    pub fn as_str(self) -> &'static str {
        match self {
            AgentEventKind::Started => "started",
            AgentEventKind::Chunk => "chunk",
            AgentEventKind::Progress => "progress",
            AgentEventKind::Exited => "exited",
            AgentEventKind::Failed => "failed",
        }
    }
}

impl DomainEvent {
    /// Stable property id used when marking Core dirty.
    pub fn property_id(&self) -> sgenaxis_core::PropertyId {
        match self {
            DomainEvent::FsDirty { path, .. } => {
                sgenaxis_core::PropertyId::new(format!("listen.fs:{path}"))
            }
            DomainEvent::GitDirty { repo_root, .. } => {
                sgenaxis_core::PropertyId::new(format!("listen.git:{repo_root}"))
            }
            DomainEvent::AgentDirty { run_id, .. } => {
                sgenaxis_core::PropertyId::new(format!("listen.agent:{}", run_id.0))
            }
            DomainEvent::AgentReconcile { run_id, .. } => {
                sgenaxis_core::PropertyId::new(format!("listen.agent.recon:{}", run_id.0))
            }
        }
    }
}
