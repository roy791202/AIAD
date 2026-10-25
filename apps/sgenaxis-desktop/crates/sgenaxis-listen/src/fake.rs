//! Fake adapter sources — no OS, no real Git, no real Agent process.
//!
//! Tests inject [`crate::SourceEvent`] bursts; production later swaps in notify／pipe／MCP.

use std::collections::VecDeque;

use sgenaxis_exec::{
    AgentChunk, AgentProvider, ExitClassification, OutputStream, RunId,
};

use crate::source::{FsChangeKind, SourceEvent};

/// In-memory FS notify queue.
#[derive(Debug, Default)]
pub struct FakeFsSource {
    queue: VecDeque<SourceEvent>,
}

impl FakeFsSource {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn emit(&mut self, path: impl Into<String>, kind: FsChangeKind) {
        self.queue.push_back(SourceEvent::fs(path, kind));
    }

    pub fn emit_burst(&mut self, path: impl Into<String>, kind: FsChangeKind, n: usize) {
        let path = path.into();
        for _ in 0..n {
            self.queue
                .push_back(SourceEvent::fs(path.clone(), kind));
        }
    }

    pub fn drain(&mut self) -> Vec<SourceEvent> {
        self.queue.drain(..).collect()
    }
}

/// In-memory Git watch queue.
#[derive(Debug, Default)]
pub struct FakeGitSource {
    queue: VecDeque<SourceEvent>,
}

impl FakeGitSource {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn emit(&mut self, repo_root: impl Into<String>, hint: impl Into<String>) {
        self.queue
            .push_back(SourceEvent::git(repo_root, hint));
    }

    pub fn emit_burst(
        &mut self,
        repo_root: impl Into<String>,
        hint: impl Into<String>,
        n: usize,
    ) {
        let root = repo_root.into();
        let hint = hint.into();
        for _ in 0..n {
            self.queue
                .push_back(SourceEvent::git(root.clone(), hint.clone()));
        }
    }

    pub fn drain(&mut self) -> Vec<SourceEvent> {
        self.queue.drain(..).collect()
    }
}

/// In-memory AgentChunk stream (pipe／MCP notification stand-in).
#[derive(Debug, Default)]
pub struct FakeAgentSource {
    queue: VecDeque<SourceEvent>,
}

impl FakeAgentSource {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn emit(&mut self, chunk: AgentChunk) {
        self.queue.push_back(SourceEvent::agent(chunk));
    }

    /// Simulate a short DryRun-like lifecycle for one run.
    pub fn emit_run_lifecycle(&mut self, run_id: RunId, dry_run: bool) {
        self.emit(AgentChunk::Started {
            run_id,
            provider: AgentProvider::Cli,
            dry_run,
            tool: None,
        });
        self.emit(AgentChunk::Chunk {
            run_id,
            stream: OutputStream::Stdout,
            text: "hello".into(),
        });
        self.emit(AgentChunk::Progress {
            run_id,
            message: "working".into(),
        });
        self.emit(AgentChunk::Exited {
            run_id,
            classification: ExitClassification::Success,
            exit_code: Some(0),
        });
    }

    pub fn drain(&mut self) -> Vec<SourceEvent> {
        self.queue.drain(..).collect()
    }
}
