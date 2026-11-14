use sgenaxis_work::{
    FakePathProbe, FakeWorkspaceStore, ProjectId, RegisterOutcome, RunBindingReservation,
    WorkError, WorkspaceService,
};

fn service_with_project(
    path: &str,
) -> (
    WorkspaceService<FakePathProbe, FakeWorkspaceStore>,
    ProjectId,
) {
    let probe = FakePathProbe::new();
    probe.seed_dir(path);
    let mut service = WorkspaceService::new(probe, FakeWorkspaceStore::new());
    let project = match service.register(path).expect("register fixture") {
        RegisterOutcome::Created(project) | RegisterOutcome::Existing(project) => project,
    };
    (service, project.id)
}

fn reserve(
    service: &mut WorkspaceService<FakePathProbe, FakeWorkspaceStore>,
    project_id: &ProjectId,
) -> RunBindingReservation {
    service
        .reserve_run_binding(
            project_id,
            "/project/A",
            "TASK-42",
            "source-sha256",
            "spec-r7",
            "module-a",
        )
        .expect("reserve before EXEC")
}

#[test]
fn reservation_blocks_legacy_binding_and_rebind_until_explicit_no_run_release() {
    let (mut service, id) = service_with_project("/project/A");
    let token = reserve(&mut service, &id);

    assert!(matches!(
        service.acquire_lease(&id, "legacy-run", "TASK-42", "source-sha256"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    assert!(matches!(
        service.preflight_run_binding("/project/A", "TASK-42", "source-sha256"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    assert!(matches!(
        service.rebind_root(&id, "/project/B"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    assert!(matches!(
        service.register("/project/B"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    assert!(matches!(
        service.reserve_run_binding(&id, "/project/A", "TASK-43", "fp", "spec-r7", "module-a"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    assert!(service.projection().unwrap().active_leases.is_empty());

    service
        .release_run_reservation_after_no_run(&token)
        .unwrap();
    assert!(matches!(
        service.release_run_reservation_after_no_run(&token),
        Err(WorkError::ReservationTokenMismatch)
    ));
    service
        .acquire_lease(&id, "legacy-run", "TASK-42", "source-sha256")
        .unwrap();
}

#[test]
fn reservation_is_global_and_blocks_rebind_of_a_different_registered_project() {
    let probe = FakePathProbe::new();
    probe.seed_dir("/project/A");
    probe.seed_dir("/project/B");
    let mut service = WorkspaceService::new(probe, FakeWorkspaceStore::new());
    let a = match service.register("/project/A").unwrap() {
        RegisterOutcome::Created(p) | RegisterOutcome::Existing(p) => p,
    };
    let b = match service.register("/project/B").unwrap() {
        RegisterOutcome::Created(p) | RegisterOutcome::Existing(p) => p,
    };
    let _token = reserve(&mut service, &a.id);

    assert!(matches!(
        service.rebind_root(&b.id, "/project/A"),
        Err(WorkError::RunBindingReserved { project_id }) if project_id == a.id.as_str()
    ));
    assert_eq!(
        service.get_project(&b.id).unwrap().unwrap().root,
        "/project/B"
    );
}

#[test]
fn successful_exec_commits_only_the_exact_reservation_and_projects_active_run() {
    let (mut service, id) = service_with_project("/project/A");
    let token = reserve(&mut service, &id);
    let lease = service
        .commit_run_reservation(&token, "returned-run-9")
        .unwrap();

    assert_eq!(lease.project_id, id);
    assert_eq!(lease.run_id, "returned-run-9");
    assert_eq!(lease.bound_root, "/project/A");
    assert_eq!(lease.work_item_id, "TASK-42");
    assert_eq!(lease.worktree_fingerprint, "source-sha256");
    assert_eq!(
        service.projection().unwrap().active_run().unwrap().run_id,
        "returned-run-9"
    );
    assert!(matches!(
        service.commit_run_reservation(&token, "replayed-run"),
        Err(WorkError::ReservationTokenMismatch)
    ));
    assert_eq!(
        service.projection().unwrap().active_run().unwrap().run_id,
        "returned-run-9"
    );
}

#[test]
fn blank_returned_run_id_does_not_consume_or_commit_reservation() {
    let (mut service, id) = service_with_project("/project/A");
    let token = reserve(&mut service, &id);

    assert!(matches!(
        service.commit_run_reservation(&token, " \t "),
        Err(WorkError::LeaseMismatch { field, .. }) if field == "run_id"
    ));
    assert!(matches!(
        service.acquire_lease(&id, "legacy-run", "TASK-42", "source-sha256"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    let committed = service
        .commit_run_reservation(&token, "returned-run")
        .unwrap();
    assert_eq!(committed.run_id, "returned-run");
}

#[test]
fn ambiguous_exec_outcome_retains_slot_and_legacy_release_cannot_clear_it() {
    let (mut service, id) = service_with_project("/project/A");
    let token = reserve(&mut service, &id);
    service.mark_run_reservation_unresolved(&token).unwrap();

    assert!(matches!(
        service.acquire_lease(&id, "second-run", "TASK-42", "source-sha256"),
        Err(WorkError::RunBindingUnresolved { .. })
    ));
    assert!(matches!(
        service.rebind_root(&id, "/project/B"),
        Err(WorkError::RunBindingUnresolved { .. })
    ));
    service.release_lease_for_project_id(id.as_str());
    service.release_lease(&id).unwrap();
    assert!(matches!(
        service.reserve_run_binding(&id, "/project/A", "TASK-42", "fp", "spec-r7", "module-a"),
        Err(WorkError::RunBindingUnresolved { .. })
    ));
    assert!(service.projection().unwrap().active_leases.is_empty());
}

#[test]
fn token_from_another_workspace_service_is_rejected_without_clearing_owner_state() {
    let (mut owner, owner_id) = service_with_project("/project/A");
    let (mut other, other_id) = service_with_project("/project/A");
    let token = reserve(&mut owner, &owner_id);

    assert!(matches!(
        other.commit_run_reservation(&token, "forged-run"),
        Err(WorkError::ReservationTokenMismatch)
    ));
    assert!(matches!(
        owner.acquire_lease(&owner_id, "legacy-run", "TASK-42", "source-sha256"),
        Err(WorkError::RunBindingReserved { .. })
    ));
    owner.commit_run_reservation(&token, "owner-run").unwrap();
    assert!(matches!(
        other.acquire_lease(&other_id, "legacy-run", "TASK-42", "source-sha256"),
        Ok(_)
    ));
}

#[test]
fn reservation_rejects_missing_binding_identity_without_occupying_slot() {
    let (mut service, id) = service_with_project("/project/A");
    assert!(matches!(
        service.reserve_run_binding(&id, "/project/B", "TASK-42", "fp", "spec-r7", "module-a"),
        Err(WorkError::LeaseMismatch { field, .. }) if field == "project_root"
    ));
    let result = service.reserve_run_binding(&id, "/project/A", "", "fp", "spec-r7", "module-a");
    assert!(
        matches!(result, Err(WorkError::LeaseMismatch { field, .. }) if field == "work_item_id")
    );
    for (work_item, fingerprint, revision, module) in [
        ("TASK-42", "", "spec-r7", "module-a"),
        ("TASK-42", "fp", "", "module-a"),
        ("TASK-42", "fp", "spec-r7", ""),
    ] {
        assert!(matches!(
            service.reserve_run_binding(
                &id,
                "/project/A",
                work_item,
                fingerprint,
                revision,
                module
            ),
            Err(WorkError::LeaseMismatch { .. })
        ));
    }
    assert!(service
        .acquire_lease(&id, "legacy-run", "TASK-42", "source-sha256")
        .is_ok());
}
