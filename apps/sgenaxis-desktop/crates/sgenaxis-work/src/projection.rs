//! View projection — UI selection is separate from Run lease bindings.

use crate::id::ProjectId;
use crate::lease::ExecutionLease;
use crate::project::Project;

/// Snapshot for UI / toolbar — selection ≠ Run root.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct WorkspaceProjection {
    pub selected_project_id: Option<String>,
    pub selected_root: Option<String>,
    pub selected_display_name: Option<String>,
    pub projects: Vec<ProjectSummary>,
    /// Active leases: Run-bound roots (must survive UI switch).
    /// PD-EXEC-SINGLE-01 first wave: at most one entry.
    pub active_leases: Vec<LeaseSummary>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectSummary {
    pub id: String,
    pub root: String,
    pub display_name: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LeaseSummary {
    pub project_id: String,
    pub run_id: String,
    pub bound_root: String,
    pub work_item_id: String,
    pub worktree_fingerprint: String,
}

impl WorkspaceProjection {
    pub fn from_state(
        selected: Option<&ProjectId>,
        projects: &[Project],
        leases: &[ExecutionLease],
    ) -> Self {
        let selected_project = selected.and_then(|id| {
            projects.iter().find(|p| &p.id == id)
        });
        Self {
            selected_project_id: selected.map(|id| id.as_str().to_string()),
            selected_root: selected_project.map(|p| p.root.clone()),
            selected_display_name: selected_project.map(|p| p.display_name.clone()),
            projects: projects
                .iter()
                .map(|p| ProjectSummary {
                    id: p.id.as_str().to_string(),
                    root: p.root.clone(),
                    display_name: p.display_name.clone(),
                })
                .collect(),
            active_leases: leases
                .iter()
                .map(|l| LeaseSummary {
                    project_id: l.project_id.as_str().to_string(),
                    run_id: l.run_id.clone(),
                    bound_root: l.bound_root.clone(),
                    work_item_id: l.work_item_id.clone(),
                    worktree_fingerprint: l.worktree_fingerprint.clone(),
                })
                .collect(),
        }
    }

    /// Bound root for a project under an active lease (Run identity).
    pub fn lease_bound_root(&self, project_id: &str) -> Option<&str> {
        self.active_leases
            .iter()
            .find(|l| l.project_id == project_id)
            .map(|l| l.bound_root.as_str())
    }

    /// PD-EXEC-SINGLE-01: the single in-flight Run lease, if any.
    pub fn active_run(&self) -> Option<&LeaseSummary> {
        debug_assert!(
            self.active_leases.len() <= 1,
            "first-wave projection must show at most one active Run"
        );
        self.active_leases.first()
    }
}
