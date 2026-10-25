//! WORK use cases: register, rebind, lease, select (view-only).

use std::collections::BTreeMap;

use crate::error::WorkError;
use crate::id::ProjectId;
use crate::lease::ExecutionLease;
use crate::probe::PathProbePort;
use crate::project::{Project, RegisterOutcome};
use crate::projection::WorkspaceProjection;
use crate::store::WorkspaceStorePort;

/// Application service owning project registry + execution leases.
///
/// UI [`Self::select`] only updates the view projection; Run-bound roots
/// stay on active [`ExecutionLease`] entries until released.
pub struct WorkspaceService<P, S> {
    probe: P,
    store: S,
    leases: BTreeMap<String, ExecutionLease>,
    selected: Option<ProjectId>,
}

impl<P: PathProbePort, S: WorkspaceStorePort> WorkspaceService<P, S> {
    pub fn new(probe: P, store: S) -> Self {
        Self {
            probe,
            store,
            leases: BTreeMap::new(),
            selected: None,
        }
    }

    /// Register a project root. Failure leaves the store unchanged (no partial).
    pub fn register(&mut self, path: &str) -> Result<RegisterOutcome, WorkError> {
        let probed = self.probe_usable(path)?;
        if let Some(existing_id) = self.store.find_by_canonical(&probed.canonical)? {
            let project = self
                .store
                .get(&existing_id)?
                .ok_or_else(|| WorkError::UnknownProject(existing_id.to_string()))?;
            self.selected = Some(project.id.clone());
            return Ok(RegisterOutcome::Existing(project));
        }

        let id = ProjectId::from_canonical_root(&probed.canonical);
        let project = Project::new(id, probed.normalized.clone(), probed.canonical);
        self.store.upsert(project.clone())?;
        self.selected = Some(project.id.clone());
        Ok(RegisterOutcome::Created(project))
    }

    /// Rebind root for an existing project. Rejected while an execution lease is active.
    pub fn rebind_root(
        &mut self,
        project_id: &ProjectId,
        new_path: &str,
    ) -> Result<Project, WorkError> {
        if let Some(lease) = self.leases.get(project_id.as_str()) {
            return Err(WorkError::LeaseActive {
                project_id: lease.project_id.as_str().to_string(),
                run_id: lease.run_id.clone(),
                bound_root: lease.bound_root.clone(),
            });
        }
        if self.store.get(project_id)?.is_none() {
            return Err(WorkError::UnknownProject(project_id.to_string()));
        }

        let probed = self.probe_usable(new_path)?;
        // Keep Project ID; refresh root + display leaf from new path.
        let updated = Project::new(project_id.clone(), probed.normalized, probed.canonical);
        self.store.upsert(updated.clone())?;
        Ok(updated)
    }

    /// Acquire execution lease — freezes current bound root／work item／fingerprint.
    pub fn acquire_lease(
        &mut self,
        project_id: &ProjectId,
        run_id: impl Into<String>,
        work_item_id: impl Into<String>,
        worktree_fingerprint: impl Into<String>,
    ) -> Result<ExecutionLease, WorkError> {
        let project = self
            .store
            .get(project_id)?
            .ok_or_else(|| WorkError::UnknownProject(project_id.to_string()))?;
        // PD-EXEC-SINGLE-01: at most one active lease globally (not only per-project).
        if let Some(existing) = self.leases.values().next() {
            return Err(WorkError::LeaseActive {
                project_id: existing.project_id.as_str().to_string(),
                run_id: existing.run_id.clone(),
                bound_root: existing.bound_root.clone(),
            });
        }
        let work_item_id = work_item_id.into();
        let worktree_fingerprint = worktree_fingerprint.into();
        if work_item_id.trim().is_empty() {
            return Err(WorkError::LeaseMismatch {
                field: "work_item_id".into(),
                expected: "(non-empty)".into(),
                got: work_item_id,
            });
        }
        if worktree_fingerprint.trim().is_empty() {
            return Err(WorkError::LeaseMismatch {
                field: "worktree_fingerprint".into(),
                expected: "(non-empty)".into(),
                got: worktree_fingerprint,
            });
        }
        let lease = ExecutionLease {
            project_id: project.id.clone(),
            run_id: run_id.into(),
            bound_root: project.root.clone(),
            work_item_id,
            worktree_fingerprint,
        };
        self.leases
            .insert(project_id.as_str().to_string(), lease.clone());
        Ok(lease)
    }

    /// Register (or reuse) project for `project_root`, then acquire／verify lease
    /// against the Run binding (PD-EXEC-BIND-01).
    pub fn bind_run(
        &mut self,
        project_root: &str,
        run_id: impl Into<String>,
        work_item_id: impl Into<String>,
        worktree_fingerprint: impl Into<String>,
    ) -> Result<ExecutionLease, WorkError> {
        let project = self.ensure_project_for_root(project_root)?;
        let run_id = run_id.into();
        let work_item_id = work_item_id.into();
        let worktree_fingerprint = worktree_fingerprint.into();

        if let Some(existing) = self.leases.get(project.id.as_str()) {
            self.assert_lease_matches(
                existing,
                &project.root,
                &work_item_id,
                &worktree_fingerprint,
            )?;
            return Ok(existing.clone());
        }

        self.acquire_lease(
            &project.id,
            run_id,
            work_item_id,
            worktree_fingerprint,
        )
    }

    /// Register／reuse project and verify any active lease matches the binding
    /// **before** EXEC `start_run` (no lease acquire yet).
    ///
    /// PD-EXEC-CANCEL-01: even a matching fingerprint while a lease is active
    /// is rejected (`LeaseActive`) — no blind second mutation until the prior
    /// Run is cancelled／crashed／exited and the lease released (reconciled).
    pub fn preflight_run_binding(
        &mut self,
        project_root: &str,
        work_item_id: &str,
        worktree_fingerprint: &str,
    ) -> Result<crate::project::Project, WorkError> {
        let project = self.ensure_project_for_root(project_root)?;
        if let Some(existing) = self.leases.get(project.id.as_str()) {
            self.assert_lease_matches(
                existing,
                &project.root,
                work_item_id,
                worktree_fingerprint,
            )?;
            return Err(WorkError::LeaseActive {
                project_id: existing.project_id.as_str().to_string(),
                run_id: existing.run_id.clone(),
                bound_root: existing.bound_root.clone(),
            });
        }
        Ok(project)
    }

    fn ensure_project_for_root(
        &mut self,
        project_root: &str,
    ) -> Result<crate::project::Project, WorkError> {
        let outcome = self.register(project_root)?;
        Ok(match outcome {
            RegisterOutcome::Created(p) | RegisterOutcome::Existing(p) => p,
        })
    }

    /// Ensure an active lease matches the requested Run binding.
    pub fn assert_lease_matches(
        &self,
        lease: &ExecutionLease,
        project_root: &str,
        work_item_id: &str,
        worktree_fingerprint: &str,
    ) -> Result<(), WorkError> {
        if normalize_root(&lease.bound_root) != normalize_root(project_root) {
            return Err(WorkError::LeaseMismatch {
                field: "project_root".into(),
                expected: lease.bound_root.clone(),
                got: project_root.into(),
            });
        }
        if lease.work_item_id != work_item_id {
            return Err(WorkError::LeaseMismatch {
                field: "work_item_id".into(),
                expected: lease.work_item_id.clone(),
                got: work_item_id.into(),
            });
        }
        if lease.worktree_fingerprint != worktree_fingerprint {
            return Err(WorkError::LeaseMismatch {
                field: "worktree_fingerprint".into(),
                expected: lease.worktree_fingerprint.clone(),
                got: worktree_fingerprint.into(),
            });
        }
        Ok(())
    }

    /// Release lease by project id when a Run exits (idempotent).
    pub fn release_lease_for_project_id(&mut self, project_id: &str) {
        self.leases.remove(project_id);
    }

    /// Release execution lease so rebind may proceed.
    pub fn release_lease(&mut self, project_id: &ProjectId) -> Result<(), WorkError> {
        if self.leases.remove(project_id.as_str()).is_none() {
            // Idempotent: no lease is fine.
        }
        Ok(())
    }

    /// Switch UI selection only — does **not** rewrite any lease bound_root.
    pub fn select(&mut self, project_id: &ProjectId) -> Result<WorkspaceProjection, WorkError> {
        let _ = self
            .store
            .get(project_id)?
            .ok_or_else(|| WorkError::UnknownProject(project_id.to_string()))?;
        self.selected = Some(project_id.clone());
        Ok(self.projection()?)
    }

    pub fn projection(&self) -> Result<WorkspaceProjection, WorkError> {
        let projects = self.store.list()?;
        let leases: Vec<ExecutionLease> = self.leases.values().cloned().collect();
        Ok(WorkspaceProjection::from_state(
            self.selected.as_ref(),
            &projects,
            &leases,
        ))
    }

    pub fn store_len(&self) -> Result<usize, WorkError> {
        Ok(self.store.len()?)
    }

    /// Look up a registered project (tests / host read).
    pub fn get_project(&self, id: &ProjectId) -> Result<Option<Project>, WorkError> {
        Ok(self.store.get(id)?)
    }

    fn probe_usable(
        &self,
        path: &str,
    ) -> Result<crate::probe::PathProbeResult, WorkError> {
        let probed = self.probe.probe(path)?;
        if !probed.exists {
            return Err(WorkError::PathNotFound(path.into()));
        }
        if !probed.is_usable() {
            return Err(WorkError::PathNotAccessible(path.into()));
        }
        Ok(probed)
    }
}

fn normalize_root(path: &str) -> String {
    let mut s: String = path
        .trim()
        .chars()
        .map(|c| if c == '\\' { '/' } else { c })
        .collect();
    while s.ends_with('/') && s.len() > 1 {
        s.pop();
    }
    s.to_lowercase()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::probe::FakePathProbe;
    use crate::project::RegisterOutcome;
    use crate::store::FakeWorkspaceStore;

    fn fixture_service() -> WorkspaceService<FakePathProbe, FakeWorkspaceStore> {
        let probe = FakePathProbe::new();
        // WORK-001 fixtures: Chinese + space, missing, alias
        probe.seed_dir("/fake/專案 A");
        probe.seed_dir("/fake/A");
        probe.seed_dir("/fake/B");
        probe.seed_dir("/fake/A-new");
        probe.seed_denied("/fake/locked");
        probe.seed_alias("/fake/PROJECTS/A", "/fake/A");
        probe.seed_alias("/Fake/A", "/fake/A");
        WorkspaceService::new(probe, FakeWorkspaceStore::new())
    }

    /// BDD-PD-WORK-01 / BDD-WORK-001-01: register + bind root (Chinese/space path).
    #[test]
    fn register_binds_root_and_emits_stable_project_id() {
        let mut ws = fixture_service();
        let outcome = ws.register("/fake/專案 A").expect("register");
        match outcome {
            RegisterOutcome::Created(p) => {
                assert_eq!(p.root, "/fake/專案 A");
                assert_eq!(p.display_name, "專案 A");
                assert!(p.id.as_str().starts_with("proj_"));
                assert_eq!(p.canonical_root, "/fake/專案 a");
            }
            RegisterOutcome::Existing(_) => panic!("expected Created"),
        }
        assert_eq!(ws.store_len().unwrap(), 1);
        let proj = ws.projection().unwrap();
        assert_eq!(proj.selected_root.as_deref(), Some("/fake/專案 A"));
    }

    /// BDD-WORK-001-02: missing path → reason + no partial register.
    #[test]
    fn register_missing_fails_without_partial_entry() {
        let mut ws = fixture_service();
        let err = ws.register("/fake/missing").unwrap_err();
        assert!(matches!(err, WorkError::PathNotFound(_)));
        assert_eq!(ws.store_len().unwrap(), 0);
    }

    #[test]
    fn register_denied_fails_without_partial_entry() {
        let mut ws = fixture_service();
        let err = ws.register("/fake/locked").unwrap_err();
        assert!(matches!(err, WorkError::PathNotAccessible(_)));
        assert_eq!(ws.store_len().unwrap(), 0);
    }

    /// BDD-WORK-001-03: alias / case → existing project, no duplicate.
    #[test]
    fn register_alias_or_case_returns_existing() {
        let mut ws = fixture_service();
        let first = match ws.register("/fake/A").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(_) => panic!("first should create"),
        };
        let second = ws.register("/Fake/A").unwrap();
        match second {
            RegisterOutcome::Existing(p) => {
                assert_eq!(p.id, first.id);
                assert_eq!(p.root, first.root);
            }
            RegisterOutcome::Created(_) => panic!("alias must not create duplicate"),
        }
        let third = ws.register("/fake/PROJECTS/A").unwrap();
        match third {
            RegisterOutcome::Existing(p) => assert_eq!(p.id, first.id),
            RegisterOutcome::Created(_) => panic!("junction alias must not duplicate"),
        }
        assert_eq!(ws.store_len().unwrap(), 1);
    }

    /// BDD-PD-WORK-01 / BDD-WORK-002-02: lease active → reject rebind; report run.
    #[test]
    fn rebind_rejected_while_lease_active() {
        let mut ws = fixture_service();
        let a = match ws.register("/fake/A").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(p) => p,
        };
        let lease = ws
            .acquire_lease(&a.id, "run-1", "WI-1", "fp-1")
            .unwrap();
        assert_eq!(lease.bound_root, "/fake/A");
        assert_eq!(lease.work_item_id, "WI-1");
        assert_eq!(lease.worktree_fingerprint, "fp-1");

        let err = ws.rebind_root(&a.id, "/fake/A-new").unwrap_err();
        match err {
            WorkError::LeaseActive {
                project_id,
                run_id,
                bound_root,
            } => {
                assert_eq!(project_id, a.id.as_str());
                assert_eq!(run_id, "run-1");
                assert_eq!(bound_root, "/fake/A");
            }
            other => panic!("expected LeaseActive, got {other:?}"),
        }
        // Authority root unchanged.
        let still = ws.get_project(&a.id).unwrap().unwrap();
        assert_eq!(still.root, "/fake/A");
    }

    /// BDD-PD-WORK-01 / BDD-WORK-002-01: select B → view B; A Run root unchanged.
    #[test]
    fn select_switches_view_only_lease_root_unchanged() {
        let mut ws = fixture_service();
        let a = match ws.register("/fake/A").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(p) => p,
        };
        let b = match ws.register("/fake/B").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(p) => p,
        };
        ws.acquire_lease(&a.id, "run-A", "WI-A", "fp-A")
            .unwrap();

        let before_lease_root = ws
            .projection()
            .unwrap()
            .lease_bound_root(a.id.as_str())
            .unwrap()
            .to_string();
        assert_eq!(before_lease_root, "/fake/A");

        let after = ws.select(&b.id).unwrap();
        assert_eq!(after.selected_project_id.as_deref(), Some(b.id.as_str()));
        assert_eq!(after.selected_root.as_deref(), Some("/fake/B"));
        assert_eq!(
            after.lease_bound_root(a.id.as_str()),
            Some("/fake/A"),
            "UI switch must not rewrite Run-bound root"
        );
        assert_ne!(
            after.selected_root.as_deref(),
            after.lease_bound_root(a.id.as_str())
        );
    }

    /// BDD-WORK-002-03 (happy rebind after stop): release lease → rebind keeps Project ID.
    #[test]
    fn rebind_after_release_keeps_project_id() {
        let mut ws = fixture_service();
        let a = match ws.register("/fake/A").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(p) => p,
        };
        let id = a.id.clone();
        ws.acquire_lease(&id, "run-1", "WI-1", "fp-1").unwrap();
        ws.release_lease(&id).unwrap();
        let updated = ws.rebind_root(&id, "/fake/A-new").unwrap();
        assert_eq!(updated.id, id);
        assert_eq!(updated.root, "/fake/A-new");
        assert_eq!(ws.store_len().unwrap(), 1);
    }

    #[test]
    fn empty_path_is_invalid() {
        let mut ws = fixture_service();
        let err = ws.register("").unwrap_err();
        assert!(matches!(err, WorkError::InvalidPath(_)));
        assert_eq!(ws.store_len().unwrap(), 0);
    }

    /// BDD-PD-EXEC-CANCEL-01: same fingerprint while lease active →拒盲目重跑.
    #[test]
    fn preflight_rejects_same_fingerprint_while_lease_active() {
        let mut ws = fixture_service();
        let _ = ws
            .bind_run("/fake/A", "run-1", "WI-1", "fp-1")
            .expect("bind");
        let err = ws
            .preflight_run_binding("/fake/A", "WI-1", "fp-1")
            .expect_err("busy");
        assert!(
            matches!(err, WorkError::LeaseActive { .. }),
            "unexpected: {err:?}"
        );
        let msg = err.to_string();
        assert!(
            msg.contains("lease") || msg.contains("reconcile") || msg.contains("blind"),
            "unexpected msg: {msg}"
        );
    }

    /// BDD-PD-EXEC-SINGLE-01: second project cannot acquire while another lease is active.
    #[test]
    fn single_active_lease_rejects_second_project() {
        let mut ws = fixture_service();
        let a = match ws.register("/fake/A").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(p) => p,
        };
        let b = match ws.register("/fake/B").unwrap() {
            RegisterOutcome::Created(p) => p,
            RegisterOutcome::Existing(p) => p,
        };
        ws.acquire_lease(&a.id, "run-A", "WI-A", "fp-A")
            .unwrap();
        let err = ws
            .acquire_lease(&b.id, "run-B", "WI-B", "fp-B")
            .expect_err("second lease");
        assert!(matches!(err, WorkError::LeaseActive { .. }));
        let msg = err.to_string();
        assert!(
            msg.contains("PD-EXEC-SINGLE-01") || msg.contains("only one"),
            "unexpected: {msg}"
        );

        let proj = ws.projection().unwrap();
        assert_eq!(proj.active_leases.len(), 1);
        assert_eq!(
            proj.active_run().map(|l| l.run_id.as_str()),
            Some("run-A")
        );

        ws.release_lease(&a.id).unwrap();
        ws.acquire_lease(&b.id, "run-B", "WI-B", "fp-B")
            .expect("after release");
        let proj = ws.projection().unwrap();
        assert_eq!(proj.active_leases.len(), 1);
        assert_eq!(
            proj.active_run().map(|l| l.run_id.as_str()),
            Some("run-B")
        );
    }

    /// BDD-PD-EXEC-BIND-01: bind_run freezes root＋work item＋fingerprint; mismatch rejected.
    #[test]
    fn bind_run_matches_lease_or_rejects_mismatch() {
        let mut ws = fixture_service();
        let lease = ws
            .bind_run("/fake/A", "run-1", "WI-1", "fp-1")
            .expect("bind");
        assert_eq!(lease.bound_root, "/fake/A");
        assert_eq!(lease.work_item_id, "WI-1");
        assert_eq!(lease.worktree_fingerprint, "fp-1");

        // Same binding while lease active → ok (idempotent view).
        let again = ws
            .bind_run("/fake/A", "run-2", "WI-1", "fp-1")
            .expect("same bind");
        assert_eq!(again.run_id, "run-1");

        let err = ws
            .bind_run("/fake/A", "run-3", "WI-OTHER", "fp-1")
            .expect_err("work item mismatch");
        assert!(matches!(
            err,
            WorkError::LeaseMismatch {
                field,
                ..
            } if field == "work_item_id"
        ));

        let err = ws
            .bind_run("/fake/A", "run-3", "WI-1", "fp-OTHER")
            .expect_err("fingerprint mismatch");
        assert!(matches!(
            err,
            WorkError::LeaseMismatch {
                field,
                ..
            } if field == "worktree_fingerprint"
        ));
    }
}
