//! Domain selection／history for Edit menu (PD-REMAIN-EDIT-01 path C).
//!
//! Pure in-memory session: no OS／Tauri. UI reaches this only via
//! Command → DispatchHost → [`EditSession`].

use std::collections::BTreeSet;

/// Snapshot of selection state for undo／redo.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditCheckpoint {
    pub selection: BTreeSet<String>,
}

/// Errors from edit mutations.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EditError {
    /// Undo stack empty.
    NothingToUndo,
    /// Redo stack empty.
    NothingToRedo,
}

impl std::fmt::Display for EditError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            EditError::NothingToUndo => write!(f, "nothing to undo"),
            EditError::NothingToRedo => write!(f, "nothing to redo"),
        }
    }
}

impl std::error::Error for EditError {}

/// Read-only projection for UI／Command DTO mapping.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct EditProjection {
    pub selected: Vec<String>,
    pub selected_count: usize,
    pub universe_count: usize,
    pub can_undo: bool,
    pub can_redo: bool,
}

/// In-memory selection + history for board／change entity ids.
#[derive(Debug, Clone, Default)]
pub struct EditSession {
    /// Ids the session may select (synced from board／change universe).
    universe: BTreeSet<String>,
    selection: BTreeSet<String>,
    undo: Vec<EditCheckpoint>,
    redo: Vec<EditCheckpoint>,
}

impl EditSession {
    pub fn new() -> Self {
        Self::default()
    }

    /// Replace selectable universe; drop selection ids no longer present.
    pub fn set_universe<I, S>(&mut self, ids: I)
    where
        I: IntoIterator<Item = S>,
        S: Into<String>,
    {
        self.universe = ids.into_iter().map(Into::into).collect();
        self.selection.retain(|id| self.universe.contains(id));
    }

    pub fn universe_len(&self) -> usize {
        self.universe.len()
    }

    pub fn selection(&self) -> &BTreeSet<String> {
        &self.selection
    }

    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }

    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }

    fn checkpoint(&self) -> EditCheckpoint {
        EditCheckpoint {
            selection: self.selection.clone(),
        }
    }

    fn push_undo_clear_redo(&mut self) {
        self.undo.push(self.checkpoint());
        self.redo.clear();
    }

    fn apply_checkpoint(&mut self, cp: EditCheckpoint) {
        self.selection = cp
            .selection
            .into_iter()
            .filter(|id| self.universe.contains(id))
            .collect();
    }

    /// Select every id in the universe (「全選變更」).
    pub fn select_all(&mut self) -> EditProjection {
        if self.selection == self.universe {
            return self.project();
        }
        self.push_undo_clear_redo();
        self.selection = self.universe.clone();
        self.project()
    }

    /// Clear selection.
    pub fn clear(&mut self) -> EditProjection {
        if self.selection.is_empty() {
            return self.project();
        }
        self.push_undo_clear_redo();
        self.selection.clear();
        self.project()
    }

    /// Restore previous selection checkpoint.
    pub fn undo(&mut self) -> Result<EditProjection, EditError> {
        let prev = self.undo.pop().ok_or(EditError::NothingToUndo)?;
        self.redo.push(self.checkpoint());
        self.apply_checkpoint(prev);
        Ok(self.project())
    }

    /// Re-apply undone selection checkpoint.
    pub fn redo(&mut self) -> Result<EditProjection, EditError> {
        let next = self.redo.pop().ok_or(EditError::NothingToRedo)?;
        self.undo.push(self.checkpoint());
        self.apply_checkpoint(next);
        Ok(self.project())
    }

    pub fn project(&self) -> EditProjection {
        EditProjection {
            selected: self.selection.iter().cloned().collect(),
            selected_count: self.selection.len(),
            universe_count: self.universe.len(),
            can_undo: self.can_undo(),
            can_redo: self.can_redo(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn select_all_then_clear_undo_redo() {
        let mut s = EditSession::new();
        s.set_universe(["a", "b", "c"]);
        let p = s.select_all();
        assert_eq!(p.selected_count, 3);
        assert!(p.can_undo);
        assert!(!p.can_redo);

        let p = s.clear();
        assert_eq!(p.selected_count, 0);
        assert!(p.can_undo);

        let p = s.undo().unwrap();
        assert_eq!(p.selected_count, 3);
        assert!(p.can_redo);

        let p = s.redo().unwrap();
        assert_eq!(p.selected_count, 0);
    }

    #[test]
    fn undo_empty_errors() {
        let mut s = EditSession::new();
        assert_eq!(s.undo().unwrap_err(), EditError::NothingToUndo);
        assert_eq!(s.redo().unwrap_err(), EditError::NothingToRedo);
    }

    #[test]
    fn universe_prune_drops_stale_selection() {
        let mut s = EditSession::new();
        s.set_universe(["a", "b"]);
        s.select_all();
        s.set_universe(["a"]);
        assert_eq!(s.selection().len(), 1);
        assert!(s.selection().contains("a"));
    }

    #[test]
    fn noop_select_all_does_not_push_history() {
        let mut s = EditSession::new();
        s.set_universe(["x"]);
        s.select_all();
        assert!(s.can_undo());
        s.select_all();
        // still one undo frame from first select_all
        s.undo().unwrap();
        assert!(!s.can_undo());
    }
}
