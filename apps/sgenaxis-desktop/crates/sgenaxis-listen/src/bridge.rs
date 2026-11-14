//! Event bridge: SourceEvent → debounce → DomainEvent → mark Dirty.
//!
//! UI must only [`sgenaxis_core::Engine::subscribe`] / snapshot — never call OS
//! watchers or push [`crate::SourceEvent`] from the front-end.
//!
//! PD-LISTEN-RECON-01: terminal AgentChunk flushes immediately; last Chunk is
//! retained; non-success ends emit [`DomainEvent::AgentReconcile`]; ended runs
//! are not re-ingested.

use std::collections::{HashMap, HashSet};
use std::time::Duration;

use sgenaxis_core::{DirtySet, Engine, PropertyId, PropertyValue, Zone};
use sgenaxis_exec::{AgentChunk, ExitClassification, RunId};

use crate::clock::{Clock, SystemClock};
use crate::domain::{AgentEventKind, DomainEvent};
use crate::projection::ListenProjection;
use crate::recon::{classification_label, is_terminal_chunk, needs_reconcile};
use crate::source::{DebounceKey, FsChange, GitChange, SourceEvent};

struct Pending {
    first_at: std::time::Instant,
    last_at: std::time::Instant,
    burst_count: u32,
    /// Latest source payload for coalescing.
    latest: SourceEvent,
    /// Last [`AgentChunk::Chunk`] seen in this burst (must not be dropped on exit).
    retained_chunk: Option<AgentChunk>,
}

/// Debouncing listen bridge (FS／Git／Agent → DomainEvent／Dirty).
pub struct EventBridge {
    window: Duration,
    clock: Box<dyn Clock>,
    pending: HashMap<DebounceKey, Pending>,
    /// Runs that already reached Exited／Failed — drop further Agent ingress.
    ended_runs: HashSet<RunId>,
    /// Terminal Agent pending waiting for the next [`Self::tick`].
    immediate: Vec<Pending>,
}

impl Default for EventBridge {
    fn default() -> Self {
        Self::new(Duration::from_millis(50))
    }
}

impl EventBridge {
    /// Create a bridge with the given debounce window and system clock.
    pub fn new(window: Duration) -> Self {
        Self::with_clock(window, Box::new(SystemClock))
    }

    /// Inject a clock (use [`crate::FakeClock`] in tests).
    pub fn with_clock(window: Duration, clock: Box<dyn Clock>) -> Self {
        Self {
            window,
            clock,
            pending: HashMap::new(),
            ended_runs: HashSet::new(),
            immediate: Vec::new(),
        }
    }

    pub fn window(&self) -> Duration {
        self.window
    }

    pub fn pending_count(&self) -> usize {
        self.pending.len() + self.immediate.len()
    }

    /// Whether this run has already ended (no further Agent ingest／re-dispatch).
    pub fn is_run_ended(&self, run_id: RunId) -> bool {
        self.ended_runs.contains(&run_id)
    }

    /// Ingest one adapter event. Returns `false` when an Agent event for an
    /// already-ended run is dropped (不重複派發已結束 Run).
    ///
    /// Terminal AgentChunk (Exited／Failed) flushes that key on the next tick
    /// without waiting for the debounce window.
    pub fn push(&mut self, event: SourceEvent) -> bool {
        if let SourceEvent::Agent(ref chunk) = event {
            if self.ended_runs.contains(&chunk.run_id()) {
                return false;
            }
        }

        let terminal = matches!(&event, SourceEvent::Agent(c) if is_terminal_chunk(c));
        let key = event.debounce_key();
        let now = self.clock.now();

        let retained_update = match &event {
            SourceEvent::Agent(c @ AgentChunk::Chunk { .. }) => Some(c.clone()),
            _ => None,
        };

        match self.pending.get_mut(&key) {
            Some(p) => {
                p.last_at = now;
                p.burst_count = p.burst_count.saturating_add(1);
                if let Some(c) = retained_update {
                    p.retained_chunk = Some(c);
                }
                p.latest = event;
            }
            None => {
                self.pending.insert(
                    key.clone(),
                    Pending {
                        first_at: now,
                        last_at: now,
                        burst_count: 1,
                        latest: event,
                        retained_chunk: retained_update,
                    },
                );
            }
        }

        if terminal {
            if let Some(p) = self.pending.remove(&key) {
                self.immediate.push(p);
            }
        }
        true
    }

    /// Flush immediate terminal Agent ends, then keys whose debounce window
    /// has elapsed since `first_at`.
    pub fn tick(&mut self) -> Vec<DomainEvent> {
        let mut out = Vec::new();

        let immediate: Vec<Pending> = self.immediate.drain(..).collect();
        for p in immediate {
            out.extend(pending_to_domain(p, &mut self.ended_runs));
        }

        let now = self.clock.now();
        let window = self.window;
        let mut ready_keys: Vec<DebounceKey> = self
            .pending
            .iter()
            .filter(|(_, p)| now.duration_since(p.first_at) >= window)
            .map(|(k, _)| k.clone())
            .collect();
        // Stable order for tests: Fs, Git, Agent by Debug string.
        ready_keys.sort_by(|a, b| format!("{a:?}").cmp(&format!("{b:?}")));

        for key in ready_keys {
            if let Some(p) = self.pending.remove(&key) {
                out.extend(pending_to_domain(p, &mut self.ended_runs));
            }
        }
        out
    }

    /// Convenience: push then tick (useful when clock already advanced).
    pub fn push_and_tick(&mut self, event: SourceEvent) -> Vec<DomainEvent> {
        self.push(event);
        self.tick()
    }

    /// Apply domain events to a [`DirtySet`] (mark property + projection).
    pub fn mark_dirty(dirty: &mut DirtySet, events: &[DomainEvent]) {
        for ev in events {
            dirty.mark_property(ev.property_id());
        }
    }

    /// Apply domain events onto Core [`Engine`]: set listen properties, flip
    /// indicator tasks (so board projection updates), then evaluate.
    ///
    /// Indicator task ids: `listen-fs`, `listen-git`, `listen-agent`.
    pub fn apply_to_engine(engine: &mut Engine, events: &[DomainEvent]) -> usize {
        if events.is_empty() {
            return 0;
        }
        ensure_listen_tasks(engine);
        let mut applied = 0;
        for ev in events {
            let id = ev.property_id();
            let value = PropertyValue::String(domain_value(ev));
            if !engine.set_property(id.clone(), value) {
                engine.mark_dirty(id);
            }
            match ev {
                DomainEvent::FsDirty { .. } => {
                    let _ = engine.set_zone("listen-fs", Zone::Yellow);
                }
                DomainEvent::GitDirty { .. } => {
                    let _ = engine.set_zone("listen-git", Zone::Yellow);
                }
                DomainEvent::AgentDirty { .. } | DomainEvent::AgentReconcile { .. } => {
                    let _ = engine.set_zone("listen-agent", Zone::Yellow);
                }
            }
            applied += 1;
        }
        engine.evaluate();
        applied
    }

    /// Tick → update [`ListenProjection`] + [`DirtySet`].
    pub fn drain_into(
        &mut self,
        dirty: &mut DirtySet,
        projection: &mut ListenProjection,
    ) -> Vec<DomainEvent> {
        let events = self.tick();
        if !events.is_empty() {
            Self::mark_dirty(dirty, &events);
            projection.apply(&events);
        }
        events
    }

    /// Tick → Core engine (indicator tasks + listen properties).
    pub fn drain_into_engine(&mut self, engine: &mut Engine) -> Vec<DomainEvent> {
        let events = self.tick();
        if !events.is_empty() {
            Self::apply_to_engine(engine, &events);
        }
        events
    }
}

fn ensure_listen_tasks(engine: &mut Engine) {
    let store = engine.property_store();
    let need_fs = store.get(&PropertyId::task_zone("listen-fs")).is_none();
    let need_git = store.get(&PropertyId::task_zone("listen-git")).is_none();
    let need_agent = store.get(&PropertyId::task_zone("listen-agent")).is_none();
    if need_fs {
        engine.upsert_task("listen-fs", "FS listen", Zone::Gray);
    }
    if need_git {
        engine.upsert_task("listen-git", "Git listen", Zone::Gray);
    }
    if need_agent {
        engine.upsert_task("listen-agent", "Agent listen", Zone::Gray);
    }
}

fn pending_to_domain(p: Pending, ended: &mut HashSet<RunId>) -> Vec<DomainEvent> {
    let burst = p.burst_count;
    match p.latest {
        SourceEvent::Fs(FsChange { path, kind }) => vec![DomainEvent::FsDirty {
            path,
            kind,
            burst_count: burst,
        }],
        SourceEvent::Git(GitChange { repo_root, hint }) => vec![DomainEvent::GitDirty {
            repo_root,
            hint,
            burst_count: burst,
        }],
        SourceEvent::Agent(chunk) => agent_pending_to_domain(chunk, burst, p.retained_chunk, ended),
    }
}

fn agent_pending_to_domain(
    chunk: AgentChunk,
    burst: u32,
    retained_chunk: Option<AgentChunk>,
    ended: &mut HashSet<RunId>,
) -> Vec<DomainEvent> {
    let run_id = chunk.run_id();
    let mut out = Vec::new();

    // 不丟最後 chunk: if we exit／fail and had a prior Chunk, emit it first.
    let last_chunk_retained = matches!(
        &chunk,
        AgentChunk::Exited { .. } | AgentChunk::Failed { .. }
    ) && retained_chunk.is_some();

    if last_chunk_retained {
        out.push(DomainEvent::AgentDirty {
            run_id,
            last_kind: AgentEventKind::Chunk,
            burst_count: burst.saturating_sub(1).max(1),
            classification: None,
        });
    }

    match chunk {
        AgentChunk::Exited {
            run_id,
            classification,
            exit_code,
        } => {
            out.push(DomainEvent::AgentDirty {
                run_id,
                last_kind: AgentEventKind::Exited,
                burst_count: burst,
                classification: Some(classification),
            });
            if needs_reconcile(classification) {
                out.push(DomainEvent::AgentReconcile {
                    run_id,
                    classification,
                    exit_code,
                    last_chunk_retained,
                });
            }
            ended.insert(run_id);
        }
        AgentChunk::Failed { run_id, .. } => {
            out.push(DomainEvent::AgentDirty {
                run_id,
                last_kind: AgentEventKind::Failed,
                burst_count: burst,
                classification: Some(ExitClassification::Failure),
            });
            out.push(DomainEvent::AgentReconcile {
                run_id,
                classification: ExitClassification::Failure,
                exit_code: None,
                last_chunk_retained,
            });
            ended.insert(run_id);
        }
        other => {
            out.push(DomainEvent::AgentDirty {
                run_id: other.run_id(),
                last_kind: agent_kind(&other),
                burst_count: burst,
                classification: None,
            });
        }
    }
    out
}

fn agent_kind(chunk: &AgentChunk) -> AgentEventKind {
    match chunk {
        AgentChunk::Started { .. } => AgentEventKind::Started,
        AgentChunk::Chunk { .. } => AgentEventKind::Chunk,
        AgentChunk::Progress { .. } => AgentEventKind::Progress,
        AgentChunk::Exited { .. } => AgentEventKind::Exited,
        AgentChunk::Failed { .. } => AgentEventKind::Failed,
    }
}

fn domain_value(ev: &DomainEvent) -> String {
    match ev {
        DomainEvent::FsDirty {
            kind,
            burst_count,
            ..
        } => format!("fs:{kind:?}:{burst_count}"),
        DomainEvent::GitDirty {
            hint,
            burst_count,
            ..
        } => format!("git:{hint}:{burst_count}"),
        DomainEvent::AgentDirty {
            last_kind,
            burst_count,
            classification,
            ..
        } => match classification {
            Some(c) => format!(
                "agent:{}:{}:{burst_count}",
                last_kind.as_str(),
                classification_label(*c)
            ),
            None => format!("agent:{}:{burst_count}", last_kind.as_str()),
        },
        DomainEvent::AgentReconcile {
            classification,
            last_chunk_retained,
            ..
        } => format!(
            "recon:{}:chunk_retained={last_chunk_retained}",
            classification_label(*classification)
        ),
    }
}
