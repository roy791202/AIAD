//! Property store — source-of-truth values keyed by stable ids.

use std::collections::HashMap;
use std::fmt;

/// Stable property identity (e.g. `task.t1.zone`, `task.t1.title`).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct PropertyId(String);

impl PropertyId {
    pub fn new(id: impl Into<String>) -> Self {
        Self(id.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    pub fn task_zone(task_id: &str) -> Self {
        Self(format!("task.{task_id}.zone"))
    }

    pub fn task_title(task_id: &str) -> Self {
        Self(format!("task.{task_id}.title"))
    }
}

impl fmt::Display for PropertyId {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(&self.0)
    }
}

/// Property values used by the fake task-board domain.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PropertyValue {
    String(String),
}

impl PropertyValue {
    pub fn as_str(&self) -> &str {
        match self {
            PropertyValue::String(s) => s,
        }
    }
}

/// Mutable map of property id → value.
#[derive(Debug, Default, Clone)]
pub struct PropertyStore {
    values: HashMap<PropertyId, PropertyValue>,
}

impl PropertyStore {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn get(&self, id: &PropertyId) -> Option<&PropertyValue> {
        self.values.get(id)
    }

    /// Insert or replace. Returns `true` when the stored value changed.
    pub fn set(&mut self, id: PropertyId, value: PropertyValue) -> bool {
        match self.values.get(&id) {
            Some(existing) if existing == &value => false,
            _ => {
                self.values.insert(id, value);
                true
            }
        }
    }

    pub fn remove(&mut self, id: &PropertyId) -> Option<PropertyValue> {
        self.values.remove(id)
    }

    pub fn contains(&self, id: &PropertyId) -> bool {
        self.values.contains_key(id)
    }

    pub fn len(&self) -> usize {
        self.values.len()
    }

    pub fn is_empty(&self) -> bool {
        self.values.is_empty()
    }
}
