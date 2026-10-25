//! Listen projection — what UI may subscribe to (never raw OS／adapter events).

use sgenaxis_exec::RunId;

use crate::domain::DomainEvent;
use crate::recon::classification_label;

/// Snapshot of last coalesced listen signals (FS／Git／Agent／Reconcile).
#[derive(Debug, Default, Clone, PartialEq, Eq)]
pub struct ListenProjection {
    pub last_fs_path: Option<String>,
    pub last_fs_burst: u32,
    pub last_git_root: Option<String>,
    pub last_git_burst: u32,
    pub last_agent_run: Option<u64>,
    pub last_agent_kind: Option<String>,
    pub last_agent_burst: u32,
    /// EXEC [`sgenaxis_exec::ExitClassification`] label when the run exited.
    pub last_agent_classification: Option<String>,
    pub last_agent_exit_code: Option<i32>,
    /// True while a non-success end awaits reconciliation (zone stays yellow).
    pub pending_reconcile: bool,
    pub last_reconcile_run: Option<u64>,
    /// Run ids that have reached a terminal AgentChunk (no re-dispatch).
    pub ended_runs: Vec<u64>,
    /// Bumped when any domain event is applied.
    pub generation: u64,
    pub event_count: u64,
}

impl ListenProjection {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn is_run_ended(&self, run_id: RunId) -> bool {
        self.ended_runs.contains(&run_id.0)
    }

    pub fn apply(&mut self, events: &[DomainEvent]) {
        for ev in events {
            self.event_count = self.event_count.saturating_add(1);
            match ev {
                DomainEvent::FsDirty {
                    path,
                    burst_count,
                    ..
                } => {
                    self.last_fs_path = Some(path.clone());
                    self.last_fs_burst = *burst_count;
                }
                DomainEvent::GitDirty {
                    repo_root,
                    burst_count,
                    ..
                } => {
                    self.last_git_root = Some(repo_root.clone());
                    self.last_git_burst = *burst_count;
                }
                DomainEvent::AgentDirty {
                    run_id,
                    last_kind,
                    burst_count,
                    classification,
                } => {
                    self.last_agent_run = Some(run_id.0);
                    self.last_agent_kind = Some(last_kind.as_str().to_string());
                    self.last_agent_burst = *burst_count;
                    if let Some(c) = classification {
                        self.last_agent_classification =
                            Some(classification_label(*c).to_string());
                    }
                    if matches!(
                        last_kind,
                        crate::domain::AgentEventKind::Exited
                            | crate::domain::AgentEventKind::Failed
                    ) {
                        self.mark_ended(*run_id);
                    }
                }
                DomainEvent::AgentReconcile {
                    run_id,
                    classification,
                    exit_code,
                    ..
                } => {
                    self.last_agent_run = Some(run_id.0);
                    self.last_agent_kind = Some("reconcile".to_string());
                    self.last_agent_classification =
                        Some(classification_label(*classification).to_string());
                    self.last_agent_exit_code = *exit_code;
                    self.pending_reconcile = true;
                    self.last_reconcile_run = Some(run_id.0);
                    self.mark_ended(*run_id);
                }
            }
        }
        if !events.is_empty() {
            self.generation = self.generation.saturating_add(1);
        }
    }

    fn mark_ended(&mut self, run_id: RunId) {
        if !self.ended_runs.contains(&run_id.0) {
            self.ended_runs.push(run_id.0);
        }
    }
}
