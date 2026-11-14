//! SGenAxis Tauri host — PD-HOST-01 + PD-CMD-01 + prior M1/M2 wiring.
//!
//! Re-exports:
//! - `core` — Property + Dirty + Evaluation (no OS)
//! - `ports` — OS boundary traits only
//! - `adapters` — Fake + Std Port implementations
//! - `exec` — Agent Providers A (CLI) + B (local MCP)
//! - `evid` — Evidence classify / store / version bind / green gate (PD-EVID-01)
//! - Inspector evidence summary via `get_evidence_summary` (PD-EVID-UI-01; read-only)
//! - Accept／Complete via `accept_work_item`／`complete_work_item` (PD-FLOW-EVID-GATE-01; EVID+FLOW)
//! - ModuleSpec／契約唯讀 via `spec_*` (PD-SPEC-UI-01; approved → REPLAN; revise 另入口)
//! - Architecture projection via `arch_get_projection` (PD-REMAIN-ARCH-UI-01; no UI-static live fake)
//! - Listen projection via `listen_get_projection` (PD-REMAIN-LISTEN-UI-01; no UI-owned notify)
//! - Report projection via `project_pd_report` (PD-REPORT-UI-01; calls tools/pd_report; no spec write-back)
//! - `listen` — FS／Git／AgentChunk debounce → DomainEvent／Dirty (PD-LISTEN-01)
//! - `host` — lifecycle / settings store / restricted IPC allowlist
//!
//! IPC: Vanilla UI → allowlisted `#[tauri::command]` → HOST／DispatchHost.
//! **No** arbitrary shell. Do not put OS logic in command closures.
//! Deploy IPC (PD-DEPLOY-CMD-01): `deploy_status`／`deploy_check`／`list_artifacts` only.
//! Git write IPC (PD-GIT-WRITE-UI-01): `git_write_commit`／`git_write_push` + approval.
//! GUARD IPC (PD-GUARD-CMD-01): `guard_check_start`／`guard_check_changes`／`start_implementation`.
//! UI design package (PD-SHELL-UIDESIGN-VIEW-01): `uidesign_package_status`／`uidesign_open_package`
//! (controlled docs/ui-design/index.html only; ≠ product evidence / not formal acceptance PASS).

mod code_import;
mod commands;
mod dispatch;
mod document_identity;
mod dto;
mod git_index_commit;
#[cfg(test)]
mod mcp_stdio;
mod pd_report_call;

/// Pure Property + Dirty + Evaluation core (no OS).
pub use sgenaxis_core as core;

/// Port traits (FileSystem / Path / Process / Git).
pub use sgenaxis_ports as ports;

/// Port adapters + compose for Fake ↔ Std swap at host boot.
pub use sgenaxis_adapters as adapters;

/// Agent EXEC (CLI + MCP).
pub use sgenaxis_exec as exec;

/// EVID — immutable evidence, RED/GREEN classification, version binding (PD-EVID-01).
pub use sgenaxis_evid as evid;

/// SPEC — ModuleSpec / contract load; approved revisions immutable (PD-SPEC-01).
pub use sgenaxis_spec as spec;

/// Listen bridge — adapter events → debounce → Dirty／ListenProjection (PD-LISTEN-01).
pub use sgenaxis_listen as listen;

/// HOST lifecycle / settings / restricted IPC (PD-HOST-01).
pub use sgenaxis_host as host;

pub use commands::{AppState, HostState};
pub use dispatch::DispatchHost;
pub use dto::*;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let host_state = HostState::boot().expect("HOST composition root failed to boot");

    tauri::Builder::default()
        .manage(AppState::new())
        .manage(host_state)
        .invoke_handler(tauri::generate_handler![
            commands::list_commands,
            commands::get_board,
            commands::load_local_board,
            commands::upsert_task,
            commands::set_task_zone,
            commands::start_run,
            commands::guard_check_start,
            commands::owner_classify_guard_task,
            commands::guard_check_changes,
            commands::start_implementation,
            commands::poll_chunks,
            commands::cancel_run,
            commands::get_evidence_summary,
            commands::accept_work_item,
            commands::complete_work_item,
            commands::batch_work_tags,
            commands::edit_get_projection,
            commands::edit_undo,
            commands::edit_redo,
            commands::edit_select_all,
            commands::edit_clear,
            commands::spec_load_fixture,
            commands::spec_get_projection,
            commands::spec_get_revision,
            commands::spec_approve,
            commands::spec_try_set_contract,
            commands::spec_revise,
            commands::arch_get_projection,
            commands::listen_get_projection,
            commands::project_pd_report,
            commands::host_get_phase,
            commands::host_get_settings,
            commands::project_document_adopt,
            commands::project_document_prepare,
            commands::host_project_preferences_load,
            commands::host_project_preferences_save,
            commands::host_project_preferences_presets,
            commands::host_project_preferences_pick_import,
            commands::host_create_project_with_preferences,
            commands::wizard_begin,
            commands::wizard_apply_step,
            commands::wizard_prepare_preferences,
            commands::wizard_commit,
            commands::wizard_cancel,
            commands::host_set_settings,
            commands::host_set_agent_settings,
            commands::host_pick_project_directory,
            commands::host_new_project_directory,
            commands::host_create_project_directory,
            commands::file_save,
            commands::host_request_shutdown,
            commands::git_workbench_summary,
            commands::git_workbench_diff,
            commands::git_index_commit_preview,
            commands::git_index_commit_confirm,
            commands::git_write_commit,
            commands::git_write_push,
            commands::git_switch_branch,
            commands::git_write_identity,
            commands::git_write_ignore,
            commands::git_write_stash_apply,
            commands::git_write_stash_pop,
            commands::git_write_stash_drop,
            commands::git_write_stash_push,
            commands::git_write_tag,
            commands::git_write_tag_delete,
            commands::git_write_tag_push,
            commands::git_write_branch_create,
            commands::git_write_branch_delete,
            commands::git_write_branch_rename,
            commands::git_write_remote_add,
            commands::git_write_remote_remove,
            commands::git_write_remote_set_url,
            commands::git_write_remote_rename,
            commands::git_write_set_upstream,
            commands::git_write_unset_upstream,
            commands::git_write_stage_all,
            commands::git_write_unstage_all,
            commands::git_write_conflict_save,
            commands::git_write_conflict_continue,
            commands::git_write_conflict_abort,
            commands::git_write_conflict_skip,
            commands::git_write_fetch,
            commands::git_write_fetch_prune,
            commands::git_write_pull_ff_only,
            commands::deploy_status,
            commands::deploy_check,
            commands::list_artifacts,
            commands::ports_status,
            commands::uidesign_package_status,
            commands::uidesign_open_package,
            commands::uidesign_save_design,
            commands::uidesign_load_design,
            commands::uidesign_build_preview,
            commands::uidesign_ask_agent,
            commands::scene_save,
            commands::scene_load,
            commands::import_preview,
        ])
        .run(tauri::generate_context!())
        .expect("error while running SGenAxis");
}

#[cfg(test)]
mod host_ipc_integration {
    use sgenaxis_host::{authorize, is_allowed, CompositionRoot, LifecyclePhase};

    #[test]
    fn boot_std_reaches_ready() {
        let root = CompositionRoot::boot_std().expect("boot_std");
        assert_eq!(root.phase(), LifecyclePhase::Ready);
    }

    #[test]
    fn host_commands_allowlisted_shell_rejected() {
        for name in [
            "host_get_phase",
            "host_get_settings",
            "host_set_settings",
            "host_set_agent_settings",
            "host_pick_project_directory",
            "host_new_project_directory",
            "host_create_project_directory",
            "wizard_begin",
            "wizard_apply_step",
            "wizard_prepare_preferences",
            "wizard_commit",
            "wizard_cancel",
            "file_save",
            "host_request_shutdown",
            "git_workbench_summary",
            "git_workbench_diff",
            "git_write_commit",
            "git_write_push",
            "git_switch_branch",
            "git_write_identity",
            "git_write_ignore",
            "git_write_stash_apply",
            "git_write_stash_pop",
            "git_write_stash_drop",
            "git_write_stash_push",
            "git_write_tag",
            "git_write_tag_delete",
            "git_write_tag_push",
            "git_write_branch_create",
            "git_write_branch_delete",
            "git_write_branch_rename",
            "git_write_remote_add",
            "git_write_remote_remove",
            "git_write_remote_set_url",
            "git_write_remote_rename",
            "git_write_set_upstream",
            "git_write_unset_upstream",
            "git_write_stage_all",
            "git_write_unstage_all",
            "git_write_conflict_save",
            "git_write_conflict_continue",
            "git_write_conflict_abort",
            "git_write_conflict_skip",
            "git_write_fetch",
            "git_write_fetch_prune",
            "git_write_pull_ff_only",
            "deploy_status",
            "deploy_check",
            "list_artifacts",
            "ports_status",
            "guard_check_start",
            "guard_check_changes",
            "start_implementation",
            "uidesign_save_design",
            "uidesign_load_design",
            "uidesign_build_preview",
            "uidesign_ask_agent",
            "scene_save",
            "scene_load",
        ] {
            assert!(is_allowed(name), "{name}");
            assert!(authorize(name).is_ok(), "{name}");
        }
        assert!(authorize("shell_execute").is_err());
        assert!(authorize("execute").is_err());
        assert!(!is_allowed("spawn"));
        assert!(!is_allowed("git_commit"));
        assert!(!is_allowed("git_push"));
        assert!(!is_allowed("git_force_push"));
        assert!(!is_allowed("git_tag"));
        assert!(!is_allowed("git_tag_delete"));
        assert!(!is_allowed("git_tag_push"));
        assert!(!is_allowed("git_branch_delete"));
        assert!(!is_allowed("git_branch_rename"));
        assert!(!is_allowed("git_remote"));
        assert!(!is_allowed("git_remote_add"));
        assert!(!is_allowed("git_remote_set_url"));
        assert!(!is_allowed("git_remote_rename"));
        assert!(!is_allowed("git_set_upstream"));
        assert!(!is_allowed("git_unset_upstream"));
        assert!(!is_allowed("git_unstage_all"));
        assert!(!is_allowed("git_fetch"));
        assert!(!is_allowed("git_fetch_prune"));
        assert!(!is_allowed("git_pull"));
        assert!(!is_allowed("git_conflict_save"));
        assert!(!is_allowed("git_rebase_skip"));
        assert!(!is_allowed("git_reset_hard"));
        assert!(!is_allowed("deploy_install"));
        assert!(!is_allowed("deploy_msiexec"));
        assert!(!is_allowed("list_os_devices"));
    }

    #[test]
    fn boot_std_enables_approving_git_write() {
        let root = CompositionRoot::boot_std().expect("boot_std");
        assert!(root.git_writes_enabled());
    }

    #[test]
    fn boot_std_ports_status_non_empty() {
        let root = CompositionRoot::boot_std().expect("boot_std");
        let v = root.ports_status();
        assert_eq!(v.status, "ok");
        assert!(v.entry_count >= 6);
    }
}
