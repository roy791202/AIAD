//! Adapter-side source events (FS notify／Git watch／Agent pipe｜MCP stream).
//!
//! Produced by watch adapters or fakes — **not** by UI. UI never sees these.

use sgenaxis_exec::{AgentChunk, RunId};

/// Kind of filesystem change (notify-style; OS-agnostic enum).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FsChangeKind {
    Create,
    Modify,
    Remove,
    Rename,
    Any,
}

/// One FS notification from a watch adapter (or [`crate::fake::FakeFsSource`]).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FsChange {
    pub path: String,
    pub kind: FsChangeKind,
}

/// One Git worktree signal (status／index／HEAD tip change).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GitChange {
    pub repo_root: String,
    /// Optional hint (e.g. "status", "head") — not shown as secret.
    pub hint: String,
}

/// Unified adapter event ingress for the listen bridge.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum SourceEvent {
    Fs(FsChange),
    Git(GitChange),
    Agent(AgentChunk),
}

impl SourceEvent {
    pub fn fs(path: impl Into<String>, kind: FsChangeKind) -> Self {
        Self::Fs(FsChange {
            path: path.into(),
            kind,
        })
    }

    pub fn git(repo_root: impl Into<String>, hint: impl Into<String>) -> Self {
        Self::Git(GitChange {
            repo_root: repo_root.into(),
            hint: hint.into(),
        })
    }

    pub fn agent(chunk: AgentChunk) -> Self {
        Self::Agent(chunk)
    }

    /// Debounce coalescing key (same key → one DomainEvent after window).
    pub fn debounce_key(&self) -> DebounceKey {
        match self {
            SourceEvent::Fs(c) => DebounceKey::Fs(normalize_path(&c.path)),
            SourceEvent::Git(c) => DebounceKey::Git(normalize_path(&c.repo_root)),
            SourceEvent::Agent(c) => DebounceKey::Agent(c.run_id()),
        }
    }
}

/// Key used by the debouncer to coalesce bursts.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum DebounceKey {
    Fs(String),
    Git(String),
    Agent(RunId),
}

fn normalize_path(p: &str) -> String {
    p.replace('\\', "/")
        .trim_end_matches('/')
        .to_string()
}
