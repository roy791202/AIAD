//! Restricted IPC surface — allowlist only; **no** arbitrary shell／exec.

use crate::error::HostError;

/// Commands the Tauri host may expose to the Vanilla UI.
///
/// Anything not in this enum is rejected. Shell／spawn／eval are never registered.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AllowedIpcCommand {
    /// DOC-ENTRY-01: explicit adoption via the bound WORK project only.
    ProjectDocumentAdopt,
    ProjectDocumentPrepare,
    /// Read [`crate::lifecycle::LifecyclePhase`].
    HostGetPhase,
    /// Read persisted [`crate::settings::HostSettings`].
    HostGetSettings,
    HostProjectPreferencesLoad,
    HostProjectPreferencesSave,
    HostProjectPreferencesPresets,
    HostProjectPreferencesPickImport,
    HostCreateProjectWithPreferences,
    /// M01-S3 six-step project wizard command bridge (begin/apply/prepare/commit/cancel).
    WizardBegin,
    WizardApplyStep,
    WizardPreparePreferences,
    WizardCommit,
    WizardCancel,
    /// Update＋persist host settings (validated).
    HostSetSettings,
    /// PD-SET-01: update＋persist CLI／MCP agent settings (draft or activate).
    HostSetAgentSettings,
    /// PD-WIRE-OPEN-01: native folder pick only (no settings mutate; UI then host_set_settings).
    HostPickProjectDirectory,
    /// PD-REMAIN-FILE-NEW-01: legacy save dialog + create dir (kept for ACL compat).
    HostNewProjectDirectory,
    /// PD-BUG-FILE-NEW-01: create under parent+name via FileSystemPort (UI then host_set_settings).
    HostCreateProjectDirectory,
    /// PD-REMAIN-FILE-SAVE-01: persist host settings／board path binding only
    /// (fixed host-settings store; never arbitrary path; never board HTML write-back).
    FileSave,
    /// Request graceful shutdown (Ready → ShuttingDown).
    HostRequestShutdown,
    /// PD-GIT-UI-01: read-only worktree summary (status／branch／log／diff).
    GitWorkbenchSummary,
    /// PD-GIT-UI-01: read-only pathspec diff (no commit／push).
    GitWorkbenchDiff,
    /// PD-GIT-WRITE-UI-01: approval-gated commit via GitWritePort (no force).
    GitWriteCommit,
    /// PD-GIT-WRITE-UI-01: approval-gated push via GitWritePort (no force).
    GitWritePush,
    /// PD-GIT-SWITCH-03 / GIT-002-03: approval-gated switch (no force／create／detach; occupying Run refuses).
    GitSwitchBranch,
    /// Approval-gated local `user.name` / `user.email` via GitWritePort (never --global).
    GitWriteIdentity,
    /// Approval-gated root `.gitignore` via GitWritePort (never untrack existing files).
    GitWriteIgnore,
    /// Approval-gated `git stash apply -- stash@{n}` via GitWritePort (never quiet/drop).
    GitWriteStashApply,
    /// Approval-gated `git stash pop -- stash@{n}` via GitWritePort (conflict keeps stash).
    GitWriteStashPop,
    /// Approval-gated `git stash drop -- stash@{n}` via GitWritePort (never clear).
    GitWriteStashDrop,
    /// Approval-gated `git stash push -m` via GitWritePort (tracked-only; never -u/--all).
    GitWriteStashPush,
    /// Approval-gated local `git tag -- name` / `git tag -a -m` via GitWritePort (never -f/--delete/push).
    GitWriteTag,
    /// Approval-gated local `git tag -d -- name` via GitWritePort (never -f/push/--delete on remotes).
    GitWriteTagDelete,
    /// Approval-gated local `git branch -- name` via GitWritePort (never -C/-D/--set-upstream/switch).
    GitWriteBranchCreate,
    /// Approval-gated local `git branch -d -- name` via GitWritePort (never -D/--force/-r/switch).
    GitWriteBranchDelete,
    /// Approval-gated local `git branch -m -- old new` via GitWritePort (never -M/--force/remote rename).
    GitWriteBranchRename,
    /// Approval-gated local `git remote add -- name url` via GitWritePort (never -f/fetch/set-url/push).
    GitWriteRemoteAdd,
    /// Approval-gated local `git remote remove -- name` via GitWritePort (never prune/fetch).
    GitWriteRemoteRemove,
    /// Approval-gated local `git remote set-url -- name url` via GitWritePort (never fetch/push/--add/--delete/--push).
    GitWriteRemoteSetUrl,
    /// Approval-gated local `git remote rename -- old new` via GitWritePort (never fetch/set-url/push).
    GitWriteRemoteRename,
    /// Approval-gated `git add -- path` for one resolved conflict (never -A / .).
    GitWriteConflictSave,
    /// Approval-gated merge/rebase/cherry-pick continue (never --skip / -X).
    GitWriteConflictContinue,
    /// Approval-gated merge/rebase/cherry-pick abort (never reset --hard).
    GitWriteConflictAbort,
    /// Approval-gated rebase/cherry-pick skip (never continue/abort fallback).
    GitWriteConflictSkip,
    /// Approval-gated `git fetch -- remote` via GitWritePort (never merge/pull/force/prune).
    GitWriteFetch,
    /// Approval-gated `git fetch --prune -- remote` via GitWritePort (never prune-tags/force/pull).
    GitWriteFetchPrune,
    /// Approval-gated `git pull --ff-only -- remote [branch]` via GitWritePort (never rebase/no-ff/force).
    GitWritePullFfOnly,
    /// PD-ELU-GIT-ARCH-01 A1: preview the already-staged Index without mutation.
    GitIndexCommitPreview,
    /// PD-ELU-GIT-ARCH-01 A1: confirm one HOST preview generation and commit only its Index.
    GitIndexCommitConfirm,
    /// PD-DEPLOY-CMD-01: read-only deploy／packaging status.
    DeployStatus,
    /// PD-DEPLOY-CMD-01: read-only deploy check (no elevated `/qn`).
    DeployCheck,
    /// PD-DEPLOY-CMD-01: list packaging artifacts (existence probe).
    ListArtifacts,
    /// PD-REMAIN-PORTS-UI-01: registered Port／adapter status projection (no OS enum).
    PortsStatus,
    /// PD-GUARD-CMD-01: start_implementation gate (approval + RED).
    GuardCheckStart,
    /// GC01/GC05: prepare one implementation candidate with native owner confirmation.
    OwnerClassifyGuardTask,
    /// PD-GUARD-CMD-01: pre-change／write path gate.
    GuardCheckChanges,
    /// PD-GUARD-CMD-01: GUARD pass then EXEC DryRun start.
    StartImplementation,
    /// PD-UIDESIGNER-FORMAT-01: save `.sgendesign` via FileSystemPort.
    UidesignSaveDesign,
    /// PD-UIDESIGNER-FORMAT-01: load `.sgendesign`.
    UidesignLoadDesign,
    /// PD-UIDESIGNER-BUILD-01: build interactive preview HTML (communication).
    UidesignBuildPreview,
    /// PD-UIDESIGNER-ASK-01: draft BDD／title from selected node (not product PASS).
    UidesignAskAgent,
    /// Project-scoped scene text save under `scene/` (`.ess`／`.es`／`.esml`／`.esui`; legacy `.sgs`／`.sg`／…).
    SceneSave,
    /// Project-scoped scene text load under `scene/`.
    SceneLoad,
    /// PD-ELU-IMPORT-ARCH-01: read-only Rust syntax preview under the bound project root.
    ImportPreview,
}

impl AllowedIpcCommand {
    /// Stable invoke name (snake_case) used by `invoke(...)`.
    pub fn name(self) -> &'static str {
        match self {
            AllowedIpcCommand::ProjectDocumentAdopt => "project_document_adopt",
            AllowedIpcCommand::ProjectDocumentPrepare => "project_document_prepare",
            AllowedIpcCommand::HostGetPhase => "host_get_phase",
            AllowedIpcCommand::HostGetSettings => "host_get_settings",
            AllowedIpcCommand::HostProjectPreferencesLoad => "host_project_preferences_load",
            AllowedIpcCommand::HostProjectPreferencesSave => "host_project_preferences_save",
            AllowedIpcCommand::HostProjectPreferencesPresets => "host_project_preferences_presets",
            AllowedIpcCommand::HostProjectPreferencesPickImport => {
                "host_project_preferences_pick_import"
            }
            AllowedIpcCommand::HostCreateProjectWithPreferences => {
                "host_create_project_with_preferences"
            }
            AllowedIpcCommand::WizardBegin => "wizard_begin",
            AllowedIpcCommand::WizardApplyStep => "wizard_apply_step",
            AllowedIpcCommand::WizardPreparePreferences => "wizard_prepare_preferences",
            AllowedIpcCommand::WizardCommit => "wizard_commit",
            AllowedIpcCommand::WizardCancel => "wizard_cancel",
            AllowedIpcCommand::HostSetSettings => "host_set_settings",
            AllowedIpcCommand::HostSetAgentSettings => "host_set_agent_settings",
            AllowedIpcCommand::HostPickProjectDirectory => "host_pick_project_directory",
            AllowedIpcCommand::HostNewProjectDirectory => "host_new_project_directory",
            AllowedIpcCommand::HostCreateProjectDirectory => "host_create_project_directory",
            AllowedIpcCommand::FileSave => "file_save",
            AllowedIpcCommand::HostRequestShutdown => "host_request_shutdown",
            AllowedIpcCommand::GitWorkbenchSummary => "git_workbench_summary",
            AllowedIpcCommand::GitWorkbenchDiff => "git_workbench_diff",
            AllowedIpcCommand::GitWriteCommit => "git_write_commit",
            AllowedIpcCommand::GitWritePush => "git_write_push",
            AllowedIpcCommand::GitSwitchBranch => "git_switch_branch",
            AllowedIpcCommand::GitWriteIdentity => "git_write_identity",
            AllowedIpcCommand::GitWriteIgnore => "git_write_ignore",
            AllowedIpcCommand::GitWriteStashApply => "git_write_stash_apply",
            AllowedIpcCommand::GitWriteStashPop => "git_write_stash_pop",
            AllowedIpcCommand::GitWriteStashDrop => "git_write_stash_drop",
            AllowedIpcCommand::GitWriteStashPush => "git_write_stash_push",
            AllowedIpcCommand::GitWriteTag => "git_write_tag",
            AllowedIpcCommand::GitWriteTagDelete => "git_write_tag_delete",
            AllowedIpcCommand::GitWriteBranchCreate => "git_write_branch_create",
            AllowedIpcCommand::GitWriteBranchDelete => "git_write_branch_delete",
            AllowedIpcCommand::GitWriteBranchRename => "git_write_branch_rename",
            AllowedIpcCommand::GitWriteRemoteAdd => "git_write_remote_add",
            AllowedIpcCommand::GitWriteRemoteRemove => "git_write_remote_remove",
            AllowedIpcCommand::GitWriteRemoteSetUrl => "git_write_remote_set_url",
            AllowedIpcCommand::GitWriteRemoteRename => "git_write_remote_rename",
            AllowedIpcCommand::GitWriteConflictSave => "git_write_conflict_save",
            AllowedIpcCommand::GitWriteConflictContinue => "git_write_conflict_continue",
            AllowedIpcCommand::GitWriteConflictAbort => "git_write_conflict_abort",
            AllowedIpcCommand::GitWriteConflictSkip => "git_write_conflict_skip",
            AllowedIpcCommand::GitWriteFetch => "git_write_fetch",
            AllowedIpcCommand::GitWriteFetchPrune => "git_write_fetch_prune",
            AllowedIpcCommand::GitWritePullFfOnly => "git_write_pull_ff_only",
            AllowedIpcCommand::GitIndexCommitPreview => "git_index_commit_preview",
            AllowedIpcCommand::GitIndexCommitConfirm => "git_index_commit_confirm",
            AllowedIpcCommand::DeployStatus => "deploy_status",
            AllowedIpcCommand::DeployCheck => "deploy_check",
            AllowedIpcCommand::ListArtifacts => "list_artifacts",
            AllowedIpcCommand::PortsStatus => "ports_status",
            AllowedIpcCommand::GuardCheckStart => "guard_check_start",
            AllowedIpcCommand::OwnerClassifyGuardTask => "owner_classify_guard_task",
            AllowedIpcCommand::GuardCheckChanges => "guard_check_changes",
            AllowedIpcCommand::StartImplementation => "start_implementation",
            AllowedIpcCommand::UidesignSaveDesign => "uidesign_save_design",
            AllowedIpcCommand::UidesignLoadDesign => "uidesign_load_design",
            AllowedIpcCommand::UidesignBuildPreview => "uidesign_build_preview",
            AllowedIpcCommand::UidesignAskAgent => "uidesign_ask_agent",
            AllowedIpcCommand::SceneSave => "scene_save",
            AllowedIpcCommand::SceneLoad => "scene_load",
            AllowedIpcCommand::ImportPreview => "import_preview",
        }
    }

    pub fn all() -> &'static [AllowedIpcCommand] {
        &[
            AllowedIpcCommand::ProjectDocumentAdopt,
            AllowedIpcCommand::ProjectDocumentPrepare,
            AllowedIpcCommand::HostGetPhase,
            AllowedIpcCommand::HostGetSettings,
            AllowedIpcCommand::HostProjectPreferencesLoad,
            AllowedIpcCommand::HostProjectPreferencesSave,
            AllowedIpcCommand::HostProjectPreferencesPresets,
            AllowedIpcCommand::HostProjectPreferencesPickImport,
            AllowedIpcCommand::HostCreateProjectWithPreferences,
            AllowedIpcCommand::WizardBegin,
            AllowedIpcCommand::WizardApplyStep,
            AllowedIpcCommand::WizardPreparePreferences,
            AllowedIpcCommand::WizardCommit,
            AllowedIpcCommand::WizardCancel,
            AllowedIpcCommand::HostSetSettings,
            AllowedIpcCommand::HostSetAgentSettings,
            AllowedIpcCommand::HostPickProjectDirectory,
            AllowedIpcCommand::HostNewProjectDirectory,
            AllowedIpcCommand::HostCreateProjectDirectory,
            AllowedIpcCommand::FileSave,
            AllowedIpcCommand::HostRequestShutdown,
            AllowedIpcCommand::GitWorkbenchSummary,
            AllowedIpcCommand::GitWorkbenchDiff,
            AllowedIpcCommand::GitWriteCommit,
            AllowedIpcCommand::GitWritePush,
            AllowedIpcCommand::GitSwitchBranch,
            AllowedIpcCommand::GitWriteIdentity,
            AllowedIpcCommand::GitWriteIgnore,
            AllowedIpcCommand::GitWriteStashApply,
            AllowedIpcCommand::GitWriteStashPop,
            AllowedIpcCommand::GitWriteStashDrop,
            AllowedIpcCommand::GitWriteStashPush,
            AllowedIpcCommand::GitWriteTag,
            AllowedIpcCommand::GitWriteTagDelete,
            AllowedIpcCommand::GitWriteBranchCreate,
            AllowedIpcCommand::GitWriteBranchDelete,
            AllowedIpcCommand::GitWriteBranchRename,
            AllowedIpcCommand::GitWriteRemoteAdd,
            AllowedIpcCommand::GitWriteRemoteRemove,
            AllowedIpcCommand::GitWriteRemoteSetUrl,
            AllowedIpcCommand::GitWriteRemoteRename,
            AllowedIpcCommand::GitWriteConflictSave,
            AllowedIpcCommand::GitWriteConflictContinue,
            AllowedIpcCommand::GitWriteConflictAbort,
            AllowedIpcCommand::GitWriteConflictSkip,
            AllowedIpcCommand::GitWriteFetch,
            AllowedIpcCommand::GitWriteFetchPrune,
            AllowedIpcCommand::GitWritePullFfOnly,
            AllowedIpcCommand::GitIndexCommitPreview,
            AllowedIpcCommand::GitIndexCommitConfirm,
            AllowedIpcCommand::DeployStatus,
            AllowedIpcCommand::DeployCheck,
            AllowedIpcCommand::ListArtifacts,
            AllowedIpcCommand::PortsStatus,
            AllowedIpcCommand::GuardCheckStart,
            AllowedIpcCommand::OwnerClassifyGuardTask,
            AllowedIpcCommand::GuardCheckChanges,
            AllowedIpcCommand::StartImplementation,
            AllowedIpcCommand::UidesignSaveDesign,
            AllowedIpcCommand::UidesignLoadDesign,
            AllowedIpcCommand::UidesignBuildPreview,
            AllowedIpcCommand::UidesignAskAgent,
            AllowedIpcCommand::SceneSave,
            AllowedIpcCommand::SceneLoad,
            AllowedIpcCommand::ImportPreview,
        ]
    }

    pub fn parse(name: &str) -> Result<AllowedIpcCommand, HostError> {
        for cmd in Self::all() {
            if cmd.name() == name {
                return Ok(*cmd);
            }
        }
        Err(HostError::Ipc(format!("command not allowlisted: {name}")))
    }
}

/// Names that must never be accepted as host IPC (defense in depth).
const FORBIDDEN_SHELL_NAMES: &[&str] = &[
    "shell_execute",
    "shell_exec",
    "execute",
    "exec",
    "spawn",
    "run_command",
    "run_shell",
    "eval",
    "system",
    "cmd",
    "powershell",
    "bash",
    "open_shell",
    "plugin:shell|execute",
    "plugin:shell|spawn",
];

/// Returns `true` if `name` is on the allowlist.
pub fn is_allowed(name: &str) -> bool {
    AllowedIpcCommand::parse(name).is_ok()
}

/// Explicitly reject known shell／exec aliases even if someone expands the allowlist later.
pub fn reject_if_shell(name: &str) -> Result<(), HostError> {
    let lower = name.to_ascii_lowercase();
    if FORBIDDEN_SHELL_NAMES
        .iter()
        .any(|f| *f == lower || lower.contains("shell") && lower.contains("exec"))
    {
        return Err(HostError::Ipc(format!(
            "arbitrary shell IPC forbidden: {name}"
        )));
    }
    // Broad patterns
    if lower.contains("shell_execute")
        || lower.contains("shell::execute")
        || lower == "execute"
        || lower.starts_with("spawn_")
    {
        return Err(HostError::Ipc(format!(
            "arbitrary shell IPC forbidden: {name}"
        )));
    }
    Ok(())
}

/// Gate used by host before dispatching an invoke name.
pub fn authorize(name: &str) -> Result<AllowedIpcCommand, HostError> {
    reject_if_shell(name)?;
    AllowedIpcCommand::parse(name)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allowlist_contains_host_commands_only() {
        assert!(is_allowed("host_get_phase"));
        assert!(is_allowed("host_get_settings"));
        assert!(is_allowed("host_set_settings"));
        assert!(is_allowed("host_set_agent_settings"));
        assert!(is_allowed("host_pick_project_directory"));
        assert!(is_allowed("host_new_project_directory"));
        assert!(is_allowed("host_create_project_directory"));
        assert!(is_allowed("wizard_begin"));
        assert!(is_allowed("wizard_apply_step"));
        assert!(is_allowed("wizard_prepare_preferences"));
        assert!(is_allowed("wizard_commit"));
        assert!(is_allowed("wizard_cancel"));
        assert!(is_allowed("file_save"));
        assert!(is_allowed("host_request_shutdown"));
        assert!(is_allowed("git_workbench_summary"));
        assert!(is_allowed("git_workbench_diff"));
        assert!(is_allowed("git_write_commit"));
        assert!(is_allowed("git_write_push"));
        assert!(is_allowed("git_switch_branch"));
        assert!(is_allowed("git_write_identity"));
        assert!(is_allowed("git_write_ignore"));
        assert!(is_allowed("git_write_stash_apply"));
        assert!(is_allowed("git_write_stash_pop"));
        assert!(is_allowed("git_write_stash_drop"));
        assert!(is_allowed("git_write_stash_push"));
        assert!(is_allowed("git_write_tag"));
        assert!(is_allowed("git_write_tag_delete"));
        assert!(is_allowed("git_write_branch_create"));
        assert!(is_allowed("git_write_branch_delete"));
        assert!(is_allowed("git_write_branch_rename"));
        assert!(is_allowed("git_write_remote_add"));
        assert!(is_allowed("git_write_remote_remove"));
        assert!(is_allowed("git_write_remote_set_url"));
        assert!(is_allowed("git_write_remote_rename"));
        assert!(is_allowed("git_write_conflict_save"));
        assert!(is_allowed("git_write_conflict_continue"));
        assert!(is_allowed("git_write_conflict_abort"));
        assert!(is_allowed("git_write_conflict_skip"));
        assert!(is_allowed("git_write_fetch"));
        assert!(is_allowed("git_write_fetch_prune"));
        assert!(is_allowed("git_write_pull_ff_only"));
        assert!(!is_allowed("git_stash"));
        assert!(!is_allowed("git_stash_drop"));
        assert!(!is_allowed("git_stash_clear"));
        assert!(!is_allowed("git_stash_push"));
        assert!(!is_allowed("git_tag"));
        assert!(!is_allowed("git_tag_delete"));
        assert!(!is_allowed("git_tag_push"));
        assert!(!is_allowed("git_branch"));
        assert!(!is_allowed("git_branch_create"));
        assert!(!is_allowed("git_branch_delete"));
        assert!(!is_allowed("git_branch_rename"));
        assert!(!is_allowed("git_branch_force_delete"));
        assert!(!is_allowed("git_checkout"));
        assert!(!is_allowed("git_remote"));
        assert!(!is_allowed("git_remote_add"));
        assert!(!is_allowed("git_remote_remove"));
        assert!(!is_allowed("git_remote_set_url"));
        assert!(!is_allowed("git_remote_rename"));
        assert!(!is_allowed("git_fetch"));
        assert!(!is_allowed("git_fetch_prune"));
        assert!(!is_allowed("git_pull"));
        assert!(!is_allowed("git_conflict_save"));
        assert!(!is_allowed("git_merge_continue"));
        assert!(!is_allowed("git_rebase_skip"));
        assert!(!is_allowed("git_reset_hard"));
        assert!(is_allowed("git_index_commit_preview"));
        assert!(is_allowed("git_index_commit_confirm"));
        assert!(is_allowed("deploy_status"));
        assert!(is_allowed("deploy_check"));
        assert!(is_allowed("list_artifacts"));
        assert!(is_allowed("ports_status"));
        assert!(is_allowed("guard_check_start"));
        assert!(is_allowed("guard_check_changes"));
        assert!(is_allowed("start_implementation"));
        assert!(is_allowed("uidesign_save_design"));
        assert!(is_allowed("uidesign_load_design"));
        assert!(is_allowed("uidesign_build_preview"));
        assert!(is_allowed("uidesign_ask_agent"));
        assert!(is_allowed("scene_save"));
        assert!(is_allowed("scene_load"));
        assert!(!is_allowed("shell_execute"));
        assert!(!is_allowed("list_os_devices"));
        assert!(!is_allowed("enumerate_drives"));
        assert!(!is_allowed("execute"));
        assert!(!is_allowed("spawn"));
        // Raw CLI-sounding names stay off the list; UI uses git_write_* + approval.
        assert!(!is_allowed("git_commit"));
        assert!(!is_allowed("git_push"));
        assert!(!is_allowed("git_force_push"));
        assert!(!is_allowed("git_config"));
        assert!(!is_allowed("git_config_global"));
        assert!(!is_allowed("git_credential"));
        assert!(!is_allowed("deploy_install"));
        assert!(!is_allowed("deploy_msiexec"));
        assert!(!is_allowed("deploy_qn"));
        // PD-REMAIN-FILE-SAVE-01: no arbitrary path write IPC.
        assert!(!is_allowed("write_file"));
        assert!(!is_allowed("fs_write"));
        assert!(!is_allowed("save_as"));
    }

    #[test]
    fn authorize_rejects_arbitrary_shell() {
        for name in [
            "shell_execute",
            "execute",
            "spawn",
            "run_command",
            "eval",
            "plugin:shell|execute",
        ] {
            let err = authorize(name).expect_err(name);
            assert!(
                matches!(err, HostError::Ipc(_)),
                "{name} should be Ipc error"
            );
        }
    }

    #[test]
    fn authorize_accepts_allowlisted() {
        assert_eq!(
            authorize("host_get_phase").unwrap(),
            AllowedIpcCommand::HostGetPhase
        );
        assert_eq!(
            authorize("import_preview").unwrap(),
            AllowedIpcCommand::ImportPreview
        );
        assert_eq!(
            authorize("owner_classify_guard_task").unwrap(),
            AllowedIpcCommand::OwnerClassifyGuardTask
        );
        assert_eq!(
            authorize("git_index_commit_preview").unwrap(),
            AllowedIpcCommand::GitIndexCommitPreview
        );
        assert_eq!(
            authorize("git_index_commit_confirm").unwrap(),
            AllowedIpcCommand::GitIndexCommitConfirm
        );
        assert_eq!(
            authorize("git_write_identity").unwrap(),
            AllowedIpcCommand::GitWriteIdentity
        );
        assert_eq!(
            authorize("git_write_ignore").unwrap(),
            AllowedIpcCommand::GitWriteIgnore
        );
        assert_eq!(
            authorize("git_write_stash_apply").unwrap(),
            AllowedIpcCommand::GitWriteStashApply
        );
        assert_eq!(
            authorize("git_write_stash_pop").unwrap(),
            AllowedIpcCommand::GitWriteStashPop
        );
        assert_eq!(
            authorize("git_write_stash_drop").unwrap(),
            AllowedIpcCommand::GitWriteStashDrop
        );
        assert_eq!(
            authorize("git_write_stash_push").unwrap(),
            AllowedIpcCommand::GitWriteStashPush
        );
        assert_eq!(
            authorize("git_write_tag").unwrap(),
            AllowedIpcCommand::GitWriteTag
        );
        assert_eq!(
            authorize("git_write_tag_delete").unwrap(),
            AllowedIpcCommand::GitWriteTagDelete
        );
        assert_eq!(
            authorize("git_write_branch_create").unwrap(),
            AllowedIpcCommand::GitWriteBranchCreate
        );
        assert_eq!(
            authorize("git_write_branch_delete").unwrap(),
            AllowedIpcCommand::GitWriteBranchDelete
        );
        assert_eq!(
            authorize("git_write_branch_rename").unwrap(),
            AllowedIpcCommand::GitWriteBranchRename
        );
        assert_eq!(
            authorize("git_write_remote_add").unwrap(),
            AllowedIpcCommand::GitWriteRemoteAdd
        );
        assert_eq!(
            authorize("git_write_remote_remove").unwrap(),
            AllowedIpcCommand::GitWriteRemoteRemove
        );
        assert_eq!(
            authorize("git_write_remote_set_url").unwrap(),
            AllowedIpcCommand::GitWriteRemoteSetUrl
        );
        assert_eq!(
            authorize("git_write_remote_rename").unwrap(),
            AllowedIpcCommand::GitWriteRemoteRename
        );
        assert_eq!(
            authorize("git_write_conflict_save").unwrap(),
            AllowedIpcCommand::GitWriteConflictSave
        );
        assert_eq!(
            authorize("git_write_conflict_continue").unwrap(),
            AllowedIpcCommand::GitWriteConflictContinue
        );
        assert_eq!(
            authorize("git_write_conflict_abort").unwrap(),
            AllowedIpcCommand::GitWriteConflictAbort
        );
        assert_eq!(
            authorize("git_write_conflict_skip").unwrap(),
            AllowedIpcCommand::GitWriteConflictSkip
        );
        assert_eq!(
            authorize("git_write_fetch").unwrap(),
            AllowedIpcCommand::GitWriteFetch
        );
        assert_eq!(
            authorize("git_write_fetch_prune").unwrap(),
            AllowedIpcCommand::GitWriteFetchPrune
        );
        assert_eq!(
            authorize("git_write_pull_ff_only").unwrap(),
            AllowedIpcCommand::GitWritePullFfOnly
        );
        assert!(authorize("git_stash_drop").is_err());
        assert!(authorize("git_stash_push").is_err());
        assert!(authorize("git_stash_clear").is_err());
        assert!(authorize("git_tag").is_err());
        assert!(authorize("git_tag_delete").is_err());
        assert!(authorize("git_tag_push").is_err());
        assert!(authorize("git_branch").is_err());
        assert!(authorize("git_branch_create").is_err());
        assert!(authorize("git_branch_delete").is_err());
        assert!(authorize("git_branch_rename").is_err());
        assert!(authorize("git_checkout").is_err());
        assert!(authorize("git_remote").is_err());
        assert!(authorize("git_remote_add").is_err());
        assert!(authorize("git_remote_set_url").is_err());
        assert!(authorize("git_remote_rename").is_err());
        assert!(authorize("git_fetch").is_err());
        assert!(authorize("git_fetch_prune").is_err());
        assert!(authorize("git_pull").is_err());
        assert!(authorize("git_conflict_save").is_err());
        assert!(authorize("git_rebase_skip").is_err());
        assert!(authorize("git_reset_hard").is_err());
        assert!(authorize("import_apply").is_err());
        assert!(authorize("shell_execute").is_err());
    }
}
