//! Snapshot projection for the fake task-board UI (zone / title counts).

use std::collections::BTreeMap;

/// Kanban-style zone used by fake board fixtures (product lamp semantics).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Zone {
    Gray,
    Blue,
    Yellow,
    Red,
    Green,
}

impl Zone {
    pub fn as_str(self) -> &'static str {
        match self {
            Zone::Gray => "gray",
            Zone::Blue => "blue",
            Zone::Yellow => "yellow",
            Zone::Red => "red",
            Zone::Green => "green",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "gray" => Some(Zone::Gray),
            "blue" => Some(Zone::Blue),
            "yellow" => Some(Zone::Yellow),
            "red" => Some(Zone::Red),
            "green" => Some(Zone::Green),
            _ => None,
        }
    }
}

/// Read-only board projection consumed by UI / tests (no OS).
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct BoardProjection {
    pub gray: usize,
    pub blue: usize,
    pub yellow: usize,
    pub red: usize,
    pub green: usize,
    /// Titles in insertion / id order for stable snapshots.
    pub titles: Vec<String>,
    /// Per-zone title lists (sorted by task id for determinism).
    pub titles_by_zone: BTreeMap<&'static str, Vec<String>>,
}

impl BoardProjection {
    pub fn total_tasks(&self) -> usize {
        self.gray + self.blue + self.yellow + self.red + self.green
    }

    pub fn count_for(&self, zone: Zone) -> usize {
        match zone {
            Zone::Gray => self.gray,
            Zone::Blue => self.blue,
            Zone::Yellow => self.yellow,
            Zone::Red => self.red,
            Zone::Green => self.green,
        }
    }
}

/// One fake task row held in core (not a port / adapter type).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TaskRecord {
    pub id: String,
    pub title: String,
    pub zone: Zone,
}
