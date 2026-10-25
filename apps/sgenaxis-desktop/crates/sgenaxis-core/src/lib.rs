//! SGenAxis Core — **Property + Dirty + Evaluation** (stage 2) + **FLOW** lamps (PD-FLOW-01).
//!
//! Pure Rust library: no Tauri, no OS ports, no Agent/Git adapters.
//! UI (later) must only consume snapshots / subscriptions — never call OS.
//!
//! Minimal pipeline:
//! 1. Mutate a [`PropertyStore`] value → [`DirtySet::mark_property`]
//! 2. [`Engine::evaluate`] propagates dirty → rebuilds [`BoardProjection`]
//! 3. Subscribers / [`Engine::snapshot`] observe the projection
//!
//! FLOW (PD-FLOW-01／PD-FLOW-EVID-GATE-01): [`TaskFlow`] lamp state machine —
//! gray/blue/yellow/red/green; Accept／Complete require EVID readiness + acceptance;
//! illegal transitions rejected.
//!
//! Edit (PD-REMAIN-EDIT-01 path C): [`EditSession`] selection／history —
//! reached only via Command → DispatchHost (no UI-local half-stub).

#![forbid(unsafe_code)]

mod dirty;
mod edit;
mod eval;
mod flow;
mod projection;
mod property;

pub use dirty::DirtySet;
pub use edit::{EditCheckpoint, EditError, EditProjection, EditSession};
pub use eval::{evaluate_board, task_from_store};
pub use flow::{lamp_meaning, FlowError, FlowEvent, TaskFlow, TransitionOutcome};
pub use projection::{BoardProjection, TaskRecord, Zone};
pub use property::{PropertyId, PropertyStore, PropertyValue};

use std::collections::BTreeMap;

/// Errors from core mutations (fake board only).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CoreError {
    UnknownTask(String),
    InvalidZone(String),
}

impl std::fmt::Display for CoreError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CoreError::UnknownTask(id) => write!(f, "unknown task id: {id}"),
            CoreError::InvalidZone(s) => write!(f, "invalid zone: {s}"),
        }
    }
}

impl std::error::Error for CoreError {}

type Subscriber = Box<dyn FnMut(&BoardProjection) + Send>;

/// In-memory dirty pipeline for the fake task board.
pub struct Engine {
    store: PropertyStore,
    dirty: DirtySet,
    /// Stable task id order (BTreeMap for deterministic evaluation).
    task_ids: BTreeMap<String, ()>,
    projection: BoardProjection,
    subscribers: Vec<Subscriber>,
    /// Generation bumped on each successful evaluate that changed the projection.
    generation: u64,
}

impl Default for Engine {
    fn default() -> Self {
        Self::new()
    }
}

impl Engine {
    pub fn new() -> Self {
        Self {
            store: PropertyStore::new(),
            dirty: DirtySet::new(),
            task_ids: BTreeMap::new(),
            projection: BoardProjection::default(),
            subscribers: Vec::new(),
            generation: 0,
        }
    }

    pub fn property_store(&self) -> &PropertyStore {
        &self.store
    }

    pub fn dirty_set(&self) -> &DirtySet {
        &self.dirty
    }

    pub fn generation(&self) -> u64 {
        self.generation
    }

    /// Register a listener invoked after evaluate when the projection changes.
    pub fn subscribe<F>(&mut self, f: F)
    where
        F: FnMut(&BoardProjection) + Send + 'static,
    {
        self.subscribers.push(Box::new(f));
    }

    /// Current projection snapshot (clone). Safe for UI / tests.
    pub fn snapshot(&self) -> BoardProjection {
        self.projection.clone()
    }

    /// Stable task ids known to the engine (sorted). For host／IPC projection DTOs.
    pub fn task_ids(&self) -> Vec<String> {
        self.task_ids.keys().cloned().collect()
    }

    /// Mark a property dirty (does not evaluate yet).
    pub fn mark_dirty(&mut self, id: PropertyId) {
        self.dirty.mark_property(id);
    }

    /// Set a property and mark dirty; does **not** evaluate (caller runs [`Self::evaluate`]).
    pub fn set_property(&mut self, id: PropertyId, value: PropertyValue) -> bool {
        let changed = self.store.set(id.clone(), value);
        if changed {
            self.mark_dirty(id);
        }
        changed
    }

    /// Insert or update a fake task; marks zone+title dirty and evaluates.
    pub fn upsert_task(
        &mut self,
        id: impl Into<String>,
        title: impl Into<String>,
        zone: Zone,
    ) -> BoardProjection {
        let id = id.into();
        let title = title.into();
        let zone_id = PropertyId::task_zone(&id);
        let title_id = PropertyId::task_title(&id);

        let zone_changed = self.set_property(
            zone_id,
            PropertyValue::String(zone.as_str().into()),
        );
        let title_changed =
            self.set_property(title_id, PropertyValue::String(title));

        let is_new = self.task_ids.insert(id, ()).is_none();
        if is_new && !zone_changed && !title_changed {
            self.dirty.mark_projection();
        }

        self.evaluate()
    }

    /// Replace all tasks with `tasks` (PD-BOARD-LIVE-01 local projection load).
    /// Clears prior task ids／properties, then upserts; empty input → empty board.
    pub fn replace_all_tasks(&mut self, tasks: Vec<TaskRecord>) -> BoardProjection {
        let old_ids: Vec<String> = self.task_ids.keys().cloned().collect();
        for id in &old_ids {
            self.store.remove(&PropertyId::task_zone(id));
            self.store.remove(&PropertyId::task_title(id));
        }
        self.task_ids.clear();
        self.dirty.mark_projection();

        if tasks.is_empty() {
            return self.evaluate();
        }

        for task in tasks {
            let zone_id = PropertyId::task_zone(&task.id);
            let title_id = PropertyId::task_title(&task.id);
            self.set_property(
                zone_id,
                PropertyValue::String(task.zone.as_str().into()),
            );
            self.set_property(title_id, PropertyValue::String(task.title));
            self.task_ids.insert(task.id, ());
        }
        self.evaluate()
    }

    /// Change one task's zone (property) → dirty → evaluate → updated projection.
    pub fn set_zone(&mut self, task_id: &str, zone: Zone) -> Result<BoardProjection, CoreError> {
        if !self.task_ids.contains_key(task_id) {
            return Err(CoreError::UnknownTask(task_id.to_string()));
        }
        let zone_id = PropertyId::task_zone(task_id);
        if self
            .store
            .set(zone_id.clone(), PropertyValue::String(zone.as_str().into()))
        {
            self.mark_dirty(zone_id);
        }
        Ok(self.evaluate())
    }

    /// Change one task's title → dirty → evaluate.
    pub fn set_title(
        &mut self,
        task_id: &str,
        title: impl Into<String>,
    ) -> Result<BoardProjection, CoreError> {
        if !self.task_ids.contains_key(task_id) {
            return Err(CoreError::UnknownTask(task_id.to_string()));
        }
        let title_id = PropertyId::task_title(task_id);
        if self
            .store
            .set(title_id.clone(), PropertyValue::String(title.into()))
        {
            self.mark_dirty(title_id);
        }
        Ok(self.evaluate())
    }

    /// Propagate dirty properties into the board projection; notify subscribers on change.
    pub fn evaluate(&mut self) -> BoardProjection {
        if self.dirty.is_empty() {
            return self.projection.clone();
        }

        let tasks: Vec<TaskRecord> = self
            .task_ids
            .keys()
            .filter_map(|id| task_from_store(&self.store, id))
            .collect();

        let next = evaluate_board(&tasks);
        let changed = next != self.projection;
        self.dirty.clear();

        if changed {
            self.projection = next;
            self.generation = self.generation.saturating_add(1);
            let snap = self.projection.clone();
            for sub in self.subscribers.iter_mut() {
                sub(&snap);
            }
        }

        self.projection.clone()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Mutex};

    #[test]
    fn change_one_zone_updates_projection_counts() {
        let mut eng = Engine::new();
        eng.upsert_task("t1", "Wire UI shell", Zone::Gray);
        eng.upsert_task("t2", "Dirty pipeline", Zone::Gray);

        let before = eng.snapshot();
        assert_eq!(before.gray, 2);
        assert_eq!(before.yellow, 0);
        assert_eq!(before.titles.len(), 2);

        let after = eng.set_zone("t2", Zone::Yellow).expect("task exists");
        assert_eq!(after.gray, 1);
        assert_eq!(after.yellow, 1);
        assert_eq!(after.red, 0);
        assert_eq!(after.total_tasks(), 2);
        assert_eq!(
            after.titles_by_zone.get("yellow"),
            Some(&vec!["Dirty pipeline".to_string()])
        );
        assert!(eng.generation() >= 1);
        assert!(eng.dirty_set().is_empty());
    }

    #[test]
    fn replace_all_tasks_clears_and_loads() {
        let mut eng = Engine::new();
        eng.upsert_task("old", "Gone", Zone::Red);
        assert_eq!(eng.snapshot().red, 1);

        let next = eng.replace_all_tasks(vec![
            TaskRecord {
                id: "a".into(),
                title: "Alpha".into(),
                zone: Zone::Yellow,
            },
            TaskRecord {
                id: "b".into(),
                title: "Beta".into(),
                zone: Zone::Green,
            },
        ]);
        assert_eq!(next.red, 0);
        assert_eq!(next.yellow, 1);
        assert_eq!(next.green, 1);
        assert_eq!(eng.task_ids(), vec!["a".to_string(), "b".to_string()]);

        let empty = eng.replace_all_tasks(Vec::new());
        assert_eq!(empty.total_tasks(), 0);
        assert!(eng.task_ids().is_empty());
    }

    #[test]
    fn mark_dirty_then_evaluate_propagates() {
        let mut eng = Engine::new();
        eng.upsert_task("a", "Alpha", Zone::Gray);

        // Bypass set_zone: set_property marks dirty; evaluate propagates.
        let zone_id = PropertyId::task_zone("a");
        assert!(eng.set_property(
            zone_id,
            PropertyValue::String(Zone::Red.as_str().into())
        ));
        assert!(eng.dirty_set().is_projection_dirty());

        let snap = eng.evaluate();
        assert_eq!(snap.red, 1);
        assert_eq!(snap.gray, 0);
        assert!(eng.dirty_set().is_empty());
    }

    #[test]
    fn subscribe_receives_projection_after_property_change() {
        let mut eng = Engine::new();
        eng.upsert_task("x", "First", Zone::Gray);

        let seen = Arc::new(Mutex::new(Vec::new()));
        let seen_c = Arc::clone(&seen);
        eng.subscribe(move |p| {
            seen_c.lock().unwrap().push(p.yellow);
        });

        eng.set_zone("x", Zone::Yellow).unwrap();
        let history = seen.lock().unwrap().clone();
        assert_eq!(history, vec![1]);
    }

    #[test]
    fn unknown_task_returns_error() {
        let mut eng = Engine::new();
        let err = eng.set_zone("missing", Zone::Red).unwrap_err();
        assert_eq!(err, CoreError::UnknownTask("missing".into()));
    }
}
