//! Workspace store Port — in-memory fake for unit tests.

use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};

use sgenaxis_ports::PortError;

use crate::id::ProjectId;
use crate::project::Project;

/// Output Port: persist / look up registered projects.
pub trait WorkspaceStorePort: Send + Sync {
    fn upsert(&self, project: Project) -> Result<(), PortError>;
    fn get(&self, id: &ProjectId) -> Result<Option<Project>, PortError>;
    fn find_by_canonical(&self, canonical: &str) -> Result<Option<ProjectId>, PortError>;
    fn list(&self) -> Result<Vec<Project>, PortError>;
    fn len(&self) -> Result<usize, PortError>;
}

/// Thread-safe in-memory store (Fake ports OK).
#[derive(Debug, Default, Clone)]
pub struct FakeWorkspaceStore {
    inner: Arc<Mutex<StoreState>>,
}

#[derive(Debug, Default)]
struct StoreState {
    by_id: BTreeMap<String, Project>,
    by_canonical: BTreeMap<String, String>,
}

impl FakeWorkspaceStore {
    pub fn new() -> Self {
        Self::default()
    }
}

impl WorkspaceStorePort for FakeWorkspaceStore {
    fn upsert(&self, project: Project) -> Result<(), PortError> {
        let mut st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        // Drop stale canonical index if root changed.
        let stale_canonical = st
            .by_id
            .get(project.id.as_str())
            .filter(|prev| prev.canonical_root != project.canonical_root)
            .map(|prev| prev.canonical_root.clone());
        if let Some(old) = stale_canonical {
            st.by_canonical.remove(&old);
        }
        st.by_canonical
            .insert(project.canonical_root.clone(), project.id.as_str().to_string());
        st.by_id
            .insert(project.id.as_str().to_string(), project);
        Ok(())
    }

    fn get(&self, id: &ProjectId) -> Result<Option<Project>, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        Ok(st.by_id.get(id.as_str()).cloned())
    }

    fn find_by_canonical(&self, canonical: &str) -> Result<Option<ProjectId>, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        Ok(st
            .by_canonical
            .get(canonical)
            .map(|s| ProjectId::new(s.clone())))
    }

    fn list(&self) -> Result<Vec<Project>, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        Ok(st.by_id.values().cloned().collect())
    }

    fn len(&self) -> Result<usize, PortError> {
        let st = self.inner.lock().map_err(|e| PortError::Other(e.to_string()))?;
        Ok(st.by_id.len())
    }
}
