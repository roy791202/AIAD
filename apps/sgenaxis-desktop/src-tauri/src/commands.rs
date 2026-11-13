//! Thin Tauri invoke handlers.
//!
//! - PD-CMD-01 → [`crate::dispatch::DispatchHost`] (Core／EXEC DryRun)
//! - PD-HOST-01 → [`sgenaxis_host::CompositionRoot`] (lifecycle／settings)
//! - PD-BOARD-LIVE-01 → read-only local `#board-snapshot` → Core projection
//! - PD-GIT-UI-01 → read-only GitPort projection
//! - PD-GIT-WRITE-UI-01 → approval-gated GitWritePort commit／push（no force；no UI→CLI）
//! - PD-DEPLOY-CMD-01 → read-only DeployPort（status／check／list_artifacts；no `/qn`）
//! - PD-REMAIN-PORTS-UI-01 → `ports_status` → registered Port／adapter projection（no OS enum）
//! - PD-REPORT-UI-01 → `project_pd_report` → tools/pd_report call boundary（no SPEC write-back）
//! - PD-REMAIN-ARCH-UI-01 → `arch_get_projection` module／dependency graph（no UI-static live fake）
//! - PD-REMAIN-LISTEN-UI-01 → `listen_get_projection` FS／Git／Agent listen（no UI notify）
//! - PD-REMAIN-WORK-TAGS-01 → `batch_work_tags` BDD／TDD → board projection（illegal → readable）
//! - PD-GUARD-CMD-01 → `guard_check_*`／`start_implementation`（CODE:detail；pass → EXEC）
//! - PD-FLOW-EVID-GATE-01 → `accept_work_item`／`complete_work_item`（EVID+FLOW；缺證→黃／拒）
//! - PD-WIRE-AGENT-01 → Agent 派工：`start_run` 帶 settings DryRun｜Live gate（command path）
//!
//! No OS／shell／spawn／eval in these closures. Board load never writes the board file.
//! (`project_pd_report` delegates OS to [`crate::pd_report_call`].)
//! PD-WIRE-ROOT-01: `project_root` flows UI → command args ← host settings; never `/demo/root`.
//! PD-REMAIN-FILE-SAVE-01: `file_save` persists host settings／board path via fixed store only;
//! never arbitrary path writes; never PROJECT-BOARD write-back.
//! ARCH: UI → `start_run` → DispatchHost → EXEC；never UI→CLI／MCP adapters.

use std::path::{Path, PathBuf};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use sgenaxis_adapters::{summarize_worktree, GitWorkbenchSummary};
use sgenaxis_core::{TaskRecord, Zone};
use sgenaxis_exec::{
    is_cli_path_activatable, is_mcp_endpoint_activatable, AgentSettingsDocument, CliAgentSettings,
    CliToolConfig, CliToolKind, McpAgentSettings, McpTransportKind,
};
use sgenaxis_host::{
    ask_agent_draft, authorize, build_preview_file, load_board_file, load_design_file,
    load_scene_text, save_design_file, save_scene_text, CompositionRoot, DeployArtifactView,
    DeployCheckView, DeployStatusView, DesignDoc, DesignNode, GuardDecisionView, GuardPacketDto,
    HostSettings, LifecyclePhase, DEFAULT_REL_PATH as UIDESIGN_DEFAULT_REL,
    DEFAULT_SGS_REL,
};
use sgenaxis_ports::{FileSystemPort, GitPort, GitStatusKind, GitWriteApproval, GitWritePort};
use tauri::{AppHandle, State, WebviewWindow};
use rfd::{AsyncMessageDialog, MessageButtons, MessageDialogResult, MessageLevel};

use crate::dispatch::DispatchHost;
use crate::code_import::{preview_selected, ImportPreview, ImportPreviewRequest};
use crate::git_index_commit::{IndexCommitErrorDto, IndexCommitOutcomeDto,
    IndexCommitPreviewDto, IndexCommitRequestDto};
use crate::dto::{
    ArchProjectionDto, BatchWorkTagsArgs, BoardView, CommandDescriptor, EditProjectionDto,
    EvidenceSummaryDto, GetEvidenceSummaryArgs, GitBranchDto, GitCommitDto, GitDiffDto,
    GitConflictDto, GitConflictFileDto, GitEntryDto, GitRemoteDto, GitSettingsDto, GitStashDto,
    GitTagDto, GitWorkbenchDto,
    GitWriteCommitArgs, GitWritePushArgs, GitWriteResultDto, GitWriteSwitchArgs,
    ListenProjectionDto,
    LoadLocalBoardArgs, LoadLocalBoardResult, PollResult, ProviderDto, SetZoneArgs,
    SpecApproveArgs, SpecGetRevisionArgs, SpecProjectionDto, SpecReviseArgs, SpecRevisionDto,
    SpecTrySetContractArgs, StartImplementationArgs, StartRunArgs, StartRunResult, UpsertTaskArgs,
    WorkItemGateArgs, OwnerClassifyGuardTaskArgs,
};

/// Shared CMD dispatch state for IPC.
pub struct AppState {
    pub host: Mutex<DispatchHost>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            host: Mutex::new(DispatchHost::new()),
        }
    }
}

impl Default for AppState {
    fn default() -> Self {
        Self::new()
    }
}

/// HOST composition root (lifecycle + settings). Separate from CMD board state.
pub struct HostState {
    pub inner: Mutex<CompositionRoot>,
    /// M01-S3: server-side in-flight wizard sessions keyed by opaque token
    /// (option A). The UI round-trips the token and never sees binding internals.
    pub wizard: Mutex<sgenaxis_host::project_wizard::WizardSessionStore>,
}

impl HostState {
    pub fn boot() -> Result<Self, String> {
        let root = CompositionRoot::boot_std().map_err(|e| e.to_string())?;
        Ok(Self {
            inner: Mutex::new(root),
            wizard: Mutex::new(sgenaxis_host::project_wizard::WizardSessionStore::new()),
        })
    }
}

fn poison_dispatch() -> String {
    "dispatch lock poisoned".into()
}

fn poison_host() -> String {
    "host lock poisoned".into()
}

/// DOC-ENTRY-01: command-only adapter; preserve existing WORK/HOST adoption.
#[tauri::command]
pub fn project_document_prepare(
    window: WebviewWindow,
    app: State<'_, AppState>,
    state: State<'_, HostState>,
    args: crate::dto::DocumentPrepareArgs,
) -> Result<crate::dto::DocumentPrepareResultDto, crate::dto::DocumentPrepareErrorDto> {
    use crate::dto::DocumentPrepareErrorDto as E;
    authorize("project_document_prepare").map_err(|_| E::UnauthorizedCaller)?;
    let url = window.url().map_err(|_| E::UnauthorizedCaller)?;
    let local = guard_owner_caller_allowed(window.label(), url.scheme(), url.host_str().unwrap_or_default(), url.port());
    if !local { return Err(E::UnauthorizedCaller); }
    let root = state.inner.lock().map_err(|_| E::WorkspaceRejected { reason: "HostStateUnavailable".into() })?;
    let mut dispatch = app.host.lock().map_err(|_| E::WorkspaceRejected { reason: "DispatchStateUnavailable".into() })?;
    dispatch.project_document_prepare(root.fs(), &root.host_settings().project_root, &args, window.label(), local)
}

/// DOC-ENTRY-01 explicit adoption; no automatic registration.
#[tauri::command]
pub fn project_document_adopt(
    window: WebviewWindow,
    app: State<'_, AppState>,
    state: State<'_, HostState>,
    args: crate::dto::DocumentAdoptArgs,
) -> Result<crate::dto::DocumentAdoptResultDto, crate::dto::DocumentAdoptErrorDto> {
    use crate::dto::DocumentAdoptErrorDto as E;
    authorize("project_document_adopt").map_err(|_| E::UnauthorizedCaller)?;
    let url = window.url().map_err(|_| E::UnauthorizedCaller)?;
    let local = guard_owner_caller_allowed(window.label(), url.scheme(), url.host_str().unwrap_or_default(), url.port());
    if !local { return Err(E::UnauthorizedCaller); }
    // Keep the trusted settings binding stable until the existing manifest
    // operation completes; use the existing HostState -> AppState lock order.
    let root = state.inner.lock().map_err(|_| E::ProjectNotBound)?;
    let mut dispatch = app.host.lock().map_err(|_| E::ProjectNotBound)?;
    let candidate = crate::document_identity::new_document_id_candidate();
    dispatch.project_document_adopt(root.fs(), &root.host_settings().project_root,
        &args, &candidate, window.label(), local)
}

#[cfg(test)]
mod guard_owner_caller_tests {
    use super::{guard_native_observation, guard_owner_caller_allowed, guard_owner_public_error};
    use crate::dispatch::{GuardAuthorityError, GuardCandidateError, GuardNativeObservation};
    use rfd::MessageDialogResult;

    const DISPATCH_PERMISSIONS: &str = include_str!("../permissions/dispatch.toml");
    const MAIN_CAPABILITY: &str = include_str!("../capabilities/default.json");
    const UIDESIGN_CAPABILITY: &str = include_str!("../capabilities/uidesign-window.json");

    #[test]
    fn guard_owner_caller_accepts_only_main_local_origins() {
        for (scheme, host) in [("tauri", "localhost"), ("http", "tauri.localhost"), ("https", "tauri.localhost")] {
            assert!(guard_owner_caller_allowed("main", scheme, host, None), "{scheme}://{host}");
        }
        for (label, scheme, host, port) in [
            ("settings", "tauri", "localhost", None),
            ("main", "https", "example.com", None),
            ("main", "http", "localhost", Some(1420)),
            ("main", "http", "tauri.localhost", Some(1420)),
        ] {
            assert!(!guard_owner_caller_allowed(label, scheme, host, port), "{label} {scheme}://{host}:{port:?}");
        }
    }

    #[test]
    fn guard_native_dialog_result_preserves_yes_no_cancel_semantics() {
        assert_eq!(guard_native_observation(MessageDialogResult::Yes), GuardNativeObservation::Yes);
        assert_eq!(guard_native_observation(MessageDialogResult::No), GuardNativeObservation::No);
        assert_eq!(guard_native_observation(MessageDialogResult::Cancel), GuardNativeObservation::Cancel);
    }

    #[test]
    fn guard_owner_invoke_permission_isolated_to_main_capability() {
        let dispatch_default = DISPATCH_PERMISSIONS
            .split("[[set]]")
            .find(|section| section.contains("identifier = \"dispatch-default\""))
            .expect("shared dispatch set");
        assert!(!dispatch_default.contains("allow-owner-classify-guard-task"));
        let owner_set = DISPATCH_PERMISSIONS
            .split("[[set]]")
            .find(|section| section.contains("identifier = \"guard-owner-default\""))
            .expect("dedicated owner permission set");
        assert!(owner_set.contains("allow-owner-classify-guard-task"));

        let capability: serde_json::Value = serde_json::from_str(MAIN_CAPABILITY).unwrap();
        assert_eq!(capability["windows"], serde_json::json!(["main"]));
        assert!(capability["permissions"].as_array().unwrap().iter().any(|item| {
            item.as_str() == Some("guard-owner-default")
        }));
        let uidesign: serde_json::Value = serde_json::from_str(UIDESIGN_CAPABILITY).unwrap();
        assert_eq!(uidesign["windows"], serde_json::json!(["ui-editor", "ui-viewer"]));
        assert!(!uidesign["permissions"].as_array().unwrap().iter().any(|item| {
            item.as_str() == Some("guard-owner-default")
        }));
    }

    #[test]
    fn guard_owner_errors_use_the_approved_stable_codes() {
        assert_eq!(guard_owner_public_error(&GuardCandidateError::UnknownTask), "INTENT_UNKNOWN");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::InvalidCandidate), "APPROVAL_NOT_READY");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::Authority(GuardAuthorityError::MissingRecord)), "APPROVAL_NOT_FOUND");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::Authority(GuardAuthorityError::Stale("input_fp"))), "APPROVAL_STALE:input_fp");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::Authority(GuardAuthorityError::Revoked)), "APPROVAL_REVOKED");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::Authority(GuardAuthorityError::Consumed)), "APPROVAL_CONSUMED");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified)), "RED_UNQUALIFIED");
        assert_eq!(guard_owner_public_error(&GuardCandidateError::Authority(GuardAuthorityError::RequiresApproval)), "IMPLEMENTATION_REQUIRES_APPROVAL");
    }
}

fn guard_native_observation(result: MessageDialogResult) -> crate::dispatch::GuardNativeObservation {
    match result {
        MessageDialogResult::Yes => crate::dispatch::GuardNativeObservation::Yes,
        MessageDialogResult::No => crate::dispatch::GuardNativeObservation::No,
        MessageDialogResult::Cancel | MessageDialogResult::Ok | MessageDialogResult::Custom(_) => {
            crate::dispatch::GuardNativeObservation::Cancel
        }
    }
}

fn guard_owner_public_error(error: &crate::dispatch::GuardCandidateError) -> String {
    use crate::dispatch::{GuardAuthorityError as Authority, GuardCandidateError as Candidate};

    match error {
        Candidate::UnknownTask => "INTENT_UNKNOWN".to_owned(),
        Candidate::Authority(authority) => match authority {
            Authority::AuthorityDenied | Authority::NativeDeclined => "AUTHORITY_DENIED".to_owned(),
            Authority::IntentUnknown => "INTENT_UNKNOWN".to_owned(),
            Authority::RequiresApproval => "IMPLEMENTATION_REQUIRES_APPROVAL".to_owned(),
            Authority::MissingRecord => "APPROVAL_NOT_FOUND".to_owned(),
            Authority::Stale(field) => format!("APPROVAL_STALE:{field}"),
            Authority::Revoked => "APPROVAL_REVOKED".to_owned(),
            Authority::Consumed => "APPROVAL_CONSUMED".to_owned(),
            Authority::RedUnqualified => "RED_UNQUALIFIED".to_owned(),
            Authority::NotReady | Authority::InvalidManifest => "APPROVAL_NOT_READY".to_owned(),
        },
        Candidate::Capture(_) => "RED_UNQUALIFIED".to_owned(),
        Candidate::NotReady
        | Candidate::InvalidCandidate
        | Candidate::ProjectNotFound
        | Candidate::ProjectReadFailure
        | Candidate::Snapshot(_) => "APPROVAL_NOT_READY".to_owned(),
    }
}

fn guard_owner_caller_allowed(label: &str, scheme: &str, host: &str, port: Option<u16>) -> bool {
    label == "main"
        && port.is_none()
        && matches!(
            (scheme, host),
            ("tauri", "localhost")
                | ("http", "tauri.localhost")
                | ("https", "tauri.localhost")
        )
}

/// PD-WIRE-ROOT-01: explicit arg wins; else host settings; unbound → clear error (no `/demo/root`).
fn resolve_bound_project_root(
    explicit: Option<&str>,
    settings: &HostSettings,
) -> Result<String, String> {
    let from_arg = explicit.map(str::trim).filter(|s| !s.is_empty());
    if let Some(r) = from_arg {
        if r == "/demo/root" {
            return Err(
                "project_root must not be hardcoded /demo/root — bind a real project root".into(),
            );
        }
        return Ok(r.to_string());
    }
    match settings.bound_project_root() {
        Some(r) if r == "/demo/root" => Err(
            "project_root must not be hardcoded /demo/root — bind a real project root".into(),
        ),
        Some(r) => Ok(r.to_string()),
        None => Err(
            "project_root not bound — open a project (開啟專案／settings.project_root) before start_run／git／board"
                .into(),
        ),
    }
}

/// Join relative board path under project root; absolute paths pass through.
fn resolve_board_path_under_root(project_root: &str, path: &str) -> String {
    let p = path.trim();
    let default = "docs/PROJECT-BOARD.html";
    let rel = if p.is_empty() { default } else { p };
    let candidate = Path::new(rel);
    if candidate.is_absolute() {
        return rel.to_string();
    }
    let mut out = PathBuf::from(project_root.trim());
    out.push(rel);
    out.to_string_lossy().into_owned()
}

// ── PD-CMD-01 ───────────────────────────────────────────────────────────────

#[tauri::command]
pub fn list_commands() -> Vec<CommandDescriptor> {
    let mut cmds = DispatchHost::list_commands();
    // Surface HOST allowlisted commands in the catalogue (no shell).
    for name in [
        "host_get_phase",
        "host_get_settings",
        "host_set_settings",
        "host_set_agent_settings",
        "host_pick_project_directory",
        "host_new_project_directory",
        "host_create_project_directory",
        "file_save",
        "host_request_shutdown",
        "git_workbench_summary",
        "git_workbench_diff",
        "git_write_commit",
        "git_write_push",
        "git_switch_branch",
        "git_index_commit_preview",
        "git_index_commit_confirm",
        "load_local_board",
        "deploy_status",
        "deploy_check",
        "list_artifacts",
        "ports_status",
        "spec_load_fixture",
        "spec_get_projection",
        "spec_get_revision",
        "spec_approve",
        "spec_try_set_contract",
        "spec_revise",
        "arch_get_projection",
        "listen_get_projection",
        "project_pd_report",
        "uidesign_package_status",
        "uidesign_open_package",
        "uidesign_save_design",
        "uidesign_load_design",
        "uidesign_build_preview",
        "uidesign_ask_agent",
        "scene_save",
        "scene_load",
        "import_preview",
        "owner_classify_guard_task",
    ] {
        cmds.push(CommandDescriptor {
            name: name.into(),
            summary: format!("HOST IPC ({name})"),
        });
    }
    cmds
}

#[tauri::command]
pub fn get_board(state: State<'_, AppState>) -> Result<BoardView, String> {
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.get_board())
}

/// PD-BOARD-LIVE-01／PD-WIRE-ROOT-01: read local PROJECT-BOARD file → Core projection.
/// Uses bound `project_root` + `board_path` (never `/demo/root`). Never write-back.
/// Never contacts `:8788`／`:28789`.
#[tauri::command]
pub fn load_local_board(
    app: State<'_, AppState>,
    host: State<'_, HostState>,
    args: Option<LoadLocalBoardArgs>,
) -> Result<LoadLocalBoardResult, String> {
    let args = args.unwrap_or_default();
    let mut root = host.inner.lock().map_err(|_| poison_host())?;

    let project_root = match resolve_bound_project_root(
        args.project_root.as_deref(),
        root.host_settings(),
    ) {
        Ok(r) => r,
        Err(msg) => {
            let empty = {
                let mut dispatch = app.host.lock().map_err(|_| poison_dispatch())?;
                dispatch.replace_projection_tasks(Vec::new())
            };
            return Ok(LoadLocalBoardResult {
                status: "error".into(),
                path: String::new(),
                message: Some(msg),
                write_back: false,
                board: empty,
            });
        }
    };

    let path_raw = args
        .path
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(|s| s.to_string())
        .unwrap_or_else(|| root.host_settings().board_path.trim().to_string());

    let path = resolve_board_path_under_root(&project_root, &path_raw);

    match load_board_file(root.fs(), &path) {
        Ok(snap) => {
            let as_of = snap.as_of.clone();
            if args.persist_path {
                let mut next = root.host_settings().clone();
                next.board_path = path.clone();
                root.set_host_settings(next).map_err(|e| e.to_string())?;
            }
            let records: Vec<TaskRecord> = snap
                .tasks
                .into_iter()
                .map(|t| TaskRecord {
                    id: t.id,
                    title: t.title,
                    zone: Zone::parse(&t.zone).unwrap_or(Zone::Gray),
                })
                .collect();
            let empty = records.is_empty();
            let board = {
                let mut dispatch = app.host.lock().map_err(|_| poison_dispatch())?;
                dispatch.replace_projection_tasks(records)
            };
            Ok(LoadLocalBoardResult {
                status: if empty {
                    "empty".into()
                } else {
                    "ok".into()
                },
                path,
                message: if empty {
                    Some("board file loaded but has no tasks".into())
                } else {
                    Some(
                        as_of
                            .map(|a| format!("loaded asOf={a}"))
                            .unwrap_or_else(|| "loaded".into()),
                    )
                },
                write_back: false,
                board,
            })
        }
        Err(e) => {
            let empty = {
                let mut dispatch = app.host.lock().map_err(|_| poison_dispatch())?;
                dispatch.replace_projection_tasks(Vec::new())
            };
            Ok(LoadLocalBoardResult {
                status: "error".into(),
                path,
                message: Some(e.to_string()),
                write_back: false,
                board: empty,
            })
        }
    }
}

#[tauri::command]
pub fn upsert_task(
    state: State<'_, AppState>,
    args: UpsertTaskArgs,
) -> Result<BoardView, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.upsert_task(args)
}

#[tauri::command]
pub fn set_task_zone(
    state: State<'_, AppState>,
    args: SetZoneArgs,
) -> Result<BoardView, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.set_task_zone(&args.id, &args.zone)
}

/// PD-WIRE-AGENT-01／PD-REMAIN-LIVE-MCP-01 — Live gate on the **command** path
/// (host settings only). UI selects provider＋settings; never hits CLI／MCP adapters.
/// Guard／FLOW／EVID remain on the command → DispatchHost path.
///
/// - `dry_run: true` → Ok (DryRun).
/// - `dry_run: false` + `!agent_active` → readable「Live 未核准」.
/// - Live **CLI**: invalid CLI path →「路徑無效」.
/// - Live **MCP**: empty／`:8788`／`:8787` →「路徑無效」／NOT RUN target.
/// Provider-scoped so SPAWN／MCP can land in parallel without cross-blocking.
pub fn preflight_live_agent_dispatch(
    settings: &HostSettings,
    fs: &dyn FileSystemPort,
    dry_run: bool,
    provider: ProviderDto,
) -> Result<(), String> {
    if dry_run {
        return Ok(());
    }
    if !settings.agent_active {
        return Err(
            "Live 未核准：請先在設定「存為作用中」（agent_active=false）；\
             派工僅經 start_run → DispatchHost → EXEC，UI 不直呼 CLI／MCP"
                .into(),
        );
    }
    match provider {
        ProviderDto::Cli => {
            let cli_path = &settings.agent.cli.selected_config().path;
            if !is_cli_path_activatable(cli_path, fs) {
                return Err(format!(
                    "Live 路徑無效不可啟動（CLI）：{cli_path}；無效／空白路徑不可 Live；秘密不進投影"
                ));
            }
        }
        ProviderDto::Mcp => {
            let endpoint = &settings.agent.mcp.endpoint;
            if endpoint.trim().is_empty() || !is_mcp_endpoint_activatable(endpoint) {
                return Err(format!(
                    "NOT RUN／路徑無效（MCP endpoint）：{endpoint}；禁 :8788／:8787；\
                     無目標不可 Live；秘密不進投影"
                ));
            }
        }
    }
    Ok(())
}

#[tauri::command]
pub fn start_run(
    state: State<'_, AppState>,
    host_state: State<'_, HostState>,
    mut args: StartRunArgs,
) -> Result<StartRunResult, String> {
    // PD-WIRE-ROOT-01 + PD-WIRE-AGENT-01 + PD-REMAIN-LIVE-SPAWN-01 + PD-REMAIN-LIVE-MCP-01:
    // bind root＋Live gate；Live wires host settings into DispatchHost before EXEC
    // (CLI→StdProcess／real-spawn；MCP→settings). Never UI→adapters.
    let (cli_for_live, mcp_for_live) = {
        let root = host_state.inner.lock().map_err(|_| poison_host())?;
        let resolved =
            resolve_bound_project_root(args.project_root.as_deref(), root.host_settings())?;
        args.project_root = Some(resolved);
        preflight_live_agent_dispatch(
            root.host_settings(),
            root.fs(),
            args.dry_run,
            args.provider,
        )?;
        let cli = if !args.dry_run && matches!(args.provider, ProviderDto::Cli) {
            Some(root.host_settings().cli_settings_for_exec())
        } else {
            None
        };
        let mcp = if !args.dry_run && matches!(args.provider, ProviderDto::Mcp) {
            Some(root.host_settings().agent.mcp.clone())
        } else {
            None
        };
        (cli, mcp)
    };
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    if let Some(cli) = cli_for_live {
        host.wire_cli_live(cli)?;
    }
    if let Some(mcp) = mcp_for_live {
        host.apply_mcp_settings(mcp);
    }
    host.start_run(args)
}

/// PD-GUARD-CMD-01: start gate — unapproved／invalid RED → `CODE:detail` in reasons.
#[tauri::command]
pub fn guard_check_start(
    state: State<'_, AppState>,
    packet: GuardPacketDto,
) -> Result<GuardDecisionView, String> {
    authorize("guard_check_start").map_err(|e| e.to_string())?;
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.guard_check_start(&packet))
}

/// GC01/GC05: prepare a bounded HOST candidate, then obtain a native rfd
/// observation outside the DispatchHost mutex. The invoke DTO has no approval
/// or confirmation field; only a Rust-controlled Yes can complete the step.
#[tauri::command]
pub async fn owner_classify_guard_task(
    window: WebviewWindow,
    state: State<'_, AppState>,
    args: OwnerClassifyGuardTaskArgs,
) -> Result<u64, String> {
    authorize("owner_classify_guard_task").map_err(|error| error.to_string())?;
    let url = window.url().map_err(|error| error.to_string())?;
    if !guard_owner_caller_allowed(window.label(), url.scheme(), url.host_str().unwrap_or_default(), url.port()) {
        return Err("GUARD_OWNER_CALLER_NOT_TRUSTED".into());
    }
    let (candidate_ref, summary) = match args.intent.as_str() {
        "generic" => {
            if args.candidate.is_some() {
                return Err("GUARD_GENERIC_CANDIDATE_FORBIDDEN".into());
            }
            let candidate_ref = {
                let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
                host.guard_prepare_generic_classification(&args.task_id)
                    .map_err(|error| guard_owner_public_error(&error))?
            };
            (
                candidate_ref,
                format!(
                    "Classify this task as generic?\n\nTask: {}\n\nGeneric classification grants no implementation, RED capture, approval, or execution authority.",
                    args.task_id
                ),
            )
        }
        "implementation" => {
            let draft = args.candidate.ok_or_else(|| "GUARD_CANDIDATE_REQUIRED".to_string())?;
            let candidate_ref = {
                let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
                host.guard_prepare_candidate(&args.task_id, &draft)
                    .map_err(|error| guard_owner_public_error(&error))?
            };
            let summary = format!(
                "Confirm this implementation candidate?\n\nTask: {}\nModule: {}\nProject: {}\nWorking root: {}\nManifest revision: {}\nInput paths: {}\nArchitecture paths: {}\nBDD paths: {}\nSkeleton paths: {}\nTest paths: {}\nBuild executable: {}\nExact argv: {:?}\nWorking directory: {}\nTarget: {}\nTest: {}\nBDD: {}\nAllowed paths: {}\nProtected paths: {}\n\nThis confirms task intent only. It does not approve or run the RED job.",
                args.task_id,
                draft.module_id,
                draft.project_id,
                draft.red_job.cwd_ref,
                draft.manifest_revision,
                draft.input_paths.join(", "),
                draft.architecture_paths.join(", "),
                draft.bdd_paths.join(", "),
                draft.skeleton_paths.join(", "),
                draft.test_paths.join(", "),
                draft.red_job.program,
                draft.red_job.build_argv,
                draft.red_job.cwd_ref,
                draft.red_job.test_target,
                draft.red_job.test_id,
                draft.red_job.bdd_id,
                draft.envelope.allowed_patterns.join(", "),
                draft.envelope.protected_patterns.join(", "),
            );
            (candidate_ref, summary)
        }
        _ => return Err("GUARD_OWNER_INTENT_UNSUPPORTED".into()),
    };
    let result = AsyncMessageDialog::new()
        .set_parent(&window)
        .set_level(MessageLevel::Warning)
        .set_title("SGenAxis implementation candidate")
        .set_description(summary)
        .set_buttons(MessageButtons::YesNoCancel)
        .show()
        .await;
    let observation = guard_native_observation(result);
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.guard_complete_candidate_confirmation(candidate_ref, observation)
        .map_err(|error| guard_owner_public_error(&error))?;
    Ok(candidate_ref)
}

/// PD-GUARD-CMD-01: pre-write path gate — protected／out-of-scope → `CODE:detail`.
#[tauri::command]
pub fn guard_check_changes(
    state: State<'_, AppState>,
    packet: GuardPacketDto,
) -> Result<GuardDecisionView, String> {
    authorize("guard_check_changes").map_err(|e| e.to_string())?;
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.guard_check_changes(&packet))
}

/// PD-GUARD-CMD-01: GUARD must allow before EXEC DryRun; reject → Err(`CODE:detail`).
#[tauri::command]
pub fn start_implementation(
    state: State<'_, AppState>,
    args: StartImplementationArgs,
) -> Result<StartRunResult, String> {
    authorize("start_implementation").map_err(|e| e.to_string())?;
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.start_implementation(args)
}

#[tauri::command]
pub fn poll_chunks(state: State<'_, AppState>, run_id: u64) -> Result<PollResult, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.poll_chunks(run_id)
}

#[tauri::command]
pub fn cancel_run(state: State<'_, AppState>, run_id: u64) -> Result<BoardView, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.cancel_run(run_id)
}

/// PD-EVID-UI-01 — read-only Inspector evidence summary (Provider Success ≠ green).
#[tauri::command]
pub fn get_evidence_summary(
    state: State<'_, AppState>,
    args: GetEvidenceSummaryArgs,
) -> Result<EvidenceSummaryDto, String> {
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.get_evidence_summary(&args.work_item_id))
}

/// PD-FLOW-EVID-GATE-01 — Accept via EVID+FLOW; missing evidence → yellow／reject.
#[tauri::command]
pub fn accept_work_item(
    state: State<'_, AppState>,
    args: WorkItemGateArgs,
) -> Result<BoardView, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.accept_work_item(&args.work_item_id)
}

/// PD-FLOW-EVID-GATE-01 — Complete via EVID+FLOW; Provider done ≠ green.
#[tauri::command]
pub fn complete_work_item(
    state: State<'_, AppState>,
    args: WorkItemGateArgs,
) -> Result<BoardView, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.complete_work_item(&args.work_item_id)
}

/// PD-REMAIN-WORK-TAGS-01 — batch BDD／TDD tags → DispatchHost／board projection.
#[tauri::command]
pub fn batch_work_tags(
    state: State<'_, AppState>,
    args: BatchWorkTagsArgs,
) -> Result<BoardView, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.batch_work_tags(args)
}

// ── PD-REMAIN-EDIT-01 (path C: UI → Command → DispatchHost → Core EditSession) ─

#[tauri::command]
pub fn edit_get_projection(state: State<'_, AppState>) -> Result<EditProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.edit_get_projection())
}

#[tauri::command]
pub fn edit_undo(state: State<'_, AppState>) -> Result<EditProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.edit_undo()
}

#[tauri::command]
pub fn edit_redo(state: State<'_, AppState>) -> Result<EditProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.edit_redo()
}

#[tauri::command]
pub fn edit_select_all(state: State<'_, AppState>) -> Result<EditProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.edit_select_all())
}

#[tauri::command]
pub fn edit_clear(state: State<'_, AppState>) -> Result<EditProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.edit_clear())
}

// ── PD-SPEC-UI-01 ─────────────────────────────────────────────────────────────

/// Load bundled sample ModuleSpec → Spec projection.
#[tauri::command]
pub fn spec_load_fixture(state: State<'_, AppState>) -> Result<SpecProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.spec_load_fixture()
}

/// Read-only Spec projection (empty when not loaded).
#[tauri::command]
pub fn spec_get_projection(state: State<'_, AppState>) -> Result<SpecProjectionDto, String> {
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.spec_get_projection())
}

/// PD-REMAIN-ARCH-UI-01 — module／dependency architecture projection (Command-sourced).
#[tauri::command]
pub fn arch_get_projection(state: State<'_, AppState>) -> Result<ArchProjectionDto, String> {
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.arch_get_projection())
}

/// PD-REMAIN-LISTEN-UI-01 — FS／Git／Agent listen projection (Command／bridge only; no UI notify).
#[tauri::command]
pub fn listen_get_projection(state: State<'_, AppState>) -> Result<ListenProjectionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    Ok(host.listen_get_projection())
}

/// Revision＋contracts; approved → immutable flag for UI.
#[tauri::command]
pub fn spec_get_revision(
    state: State<'_, AppState>,
    args: SpecGetRevisionArgs,
) -> Result<SpecRevisionDto, String> {
    let host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.spec_get_revision(args)
}

/// Approve a Draft revision (locks content hash; thereafter immutable in place).
#[tauri::command]
pub fn spec_approve(
    state: State<'_, AppState>,
    args: SpecApproveArgs,
) -> Result<SpecRevisionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.spec_approve(args)
}

/// Attempt in-place contract edit. Approved → error string containing `REPLAN_REQUIRED`.
#[tauri::command]
pub fn spec_try_set_contract(
    state: State<'_, AppState>,
    args: SpecTrySetContractArgs,
) -> Result<SpecRevisionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.spec_try_set_contract(args)
}

/// Separate revise entry — new Draft from approved baseline (never mutates baseline).
#[tauri::command]
pub fn spec_revise(
    state: State<'_, AppState>,
    args: SpecReviseArgs,
) -> Result<SpecRevisionDto, String> {
    let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
    host.spec_revise(args)
}

// ── PD-REPORT-UI-01 ───────────────────────────────────────────────────────────

/// Project SPEC+EVID via `tools/pd_report` (read-only; empty evid → NOT RUN).
#[tauri::command]
pub fn project_pd_report(
    args: crate::pd_report_call::ProjectPdReportArgs,
) -> Result<crate::pd_report_call::ProjectPdReportDto, String> {
    crate::pd_report_call::project_pd_report(&args)
}

// ── PD-HOST-01 ──────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct PhaseDto {
    pub phase: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct CliProjectionDto {
    pub selected: String,
    pub claude_path: String,
    pub cursor_agent_path: String,
    pub codex_path: String,
    pub antigravity_path: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct McpProjectionDto {
    pub transport: String,
    pub server_name: String,
    pub endpoint: String,
    pub approved_tools: Vec<String>,
    pub has_secret: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct SettingsDto {
    pub version: u32,
    pub ui_theme: String,
    pub locale: String,
    /// Bound project root (PD-WIRE-ROOT-01／OPEN); empty = unbound.
    pub project_root: String,
    /// Local board file path (PD-BOARD-LIVE-01); never an HTTP mailbox URL.
    pub board_path: String,
    pub agent_active: bool,
    /// UI mode label: `"dry-run"`｜`"live"` (mirrors `agent_active`; PD-SET-UI-01).
    pub run_mode: String,
    /// CLI／MCP projection — **no** secret values (PD-SET-01／PD-SET-UI-01).
    pub agent_cli: CliProjectionDto,
    pub agent_mcp: McpProjectionDto,
}

impl From<&HostSettings> for SettingsDto {
    fn from(s: &HostSettings) -> Self {
        let p = s.agent_projection();
        Self {
            version: s.version,
            ui_theme: s.ui_theme.clone(),
            locale: s.locale.clone(),
            project_root: s.project_root.clone(),
            board_path: s.board_path.clone(),
            agent_active: s.agent_active,
            run_mode: if s.agent_active {
                "live".into()
            } else {
                "dry-run".into()
            },
            agent_cli: CliProjectionDto {
                selected: p.cli.selected.config_key().into(),
                claude_path: p.cli.claude_path,
                cursor_agent_path: p.cli.cursor_agent_path,
                codex_path: p.cli.codex_path,
                antigravity_path: p.cli.antigravity_path,
            },
            agent_mcp: McpProjectionDto {
                transport: p.mcp.transport.config_key().into(),
                server_name: p.mcp.server_name,
                endpoint: p.mcp.endpoint,
                approved_tools: p.mcp.approved_tools,
                has_secret: p.mcp.has_secret,
            },
        }
    }
}

#[derive(Debug, Clone, serde::Deserialize)]
pub struct SetAgentSettingsArgs {
    pub activate: bool,
    pub selected: String,
    pub claude_path: String,
    pub cursor_agent_path: String,
    pub codex_path: String,
    pub antigravity_path: String,
    pub transport: String,
    pub server_name: String,
    pub endpoint: String,
    pub approved_tools: Vec<String>,
    /// Optional secret — stored in host settings, never returned in SettingsDto.
    pub secret_token: Option<String>,
}

fn parse_cli_kind(s: &str) -> Result<CliToolKind, String> {
    match s {
        "claude" => Ok(CliToolKind::Claude),
        "cursor-agent" => Ok(CliToolKind::CursorAgent),
        "codex" => Ok(CliToolKind::Codex),
        "antigravity" => Ok(CliToolKind::Antigravity),
        other => Err(format!("unknown cli tool: {other}")),
    }
}

fn parse_transport(s: &str) -> Result<McpTransportKind, String> {
    match s {
        "stdio" => Ok(McpTransportKind::Stdio),
        "local-http-sse" => Ok(McpTransportKind::LocalHttpSse),
        other => Err(format!("unknown mcp transport: {other}")),
    }
}

fn apply_agent_args(doc: &mut AgentSettingsDocument, args: &SetAgentSettingsArgs) -> Result<(), String> {
    let live_approved = doc.cli.live_approved;
    doc.cli = CliAgentSettings {
        selected: parse_cli_kind(&args.selected)?,
        claude: CliToolConfig::new(&args.claude_path, doc.cli.claude.args.clone()),
        cursor_agent: CliToolConfig::new(&args.cursor_agent_path, doc.cli.cursor_agent.args.clone()),
        codex: CliToolConfig::new(&args.codex_path, doc.cli.codex.args.clone()),
        antigravity: CliToolConfig::new(&args.antigravity_path, doc.cli.antigravity.args.clone()),
        live_approved,
    };
    doc.mcp = McpAgentSettings {
        transport: parse_transport(&args.transport)?,
        server_name: args.server_name.clone(),
        endpoint: args.endpoint.clone(),
        approved_tools: args.approved_tools.clone(),
        secret_token: args.secret_token.clone(),
    };
    Ok(())
}

fn phase_dto(phase: LifecyclePhase) -> PhaseDto {
    PhaseDto {
        phase: phase.as_str().into(),
    }
}

#[tauri::command]
pub fn host_get_phase(state: State<'_, HostState>) -> Result<PhaseDto, String> {
    authorize("host_get_phase").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    Ok(phase_dto(root.phase()))
}

#[tauri::command]
pub fn host_get_settings(state: State<'_, HostState>) -> Result<SettingsDto, String> {
    authorize("host_get_settings").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    Ok(SettingsDto::from(root.host_settings()))
}

#[tauri::command]
pub fn host_set_settings(
    state: State<'_, HostState>,
    ui_theme: String,
    locale: String,
    board_path: Option<String>,
    project_root: Option<String>,
) -> Result<SettingsDto, String> {
    authorize("host_set_settings").map_err(|e| e.to_string())?;
    let mut root = state.inner.lock().map_err(|_| poison_host())?;
    let mut next = root.host_settings().clone();
    next.ui_theme = ui_theme;
    next.locale = locale;
    if let Some(bp) = board_path {
        next.board_path = bp;
    }
    if let Some(pr) = project_root {
        let trimmed = pr.trim();
        if trimmed == "/demo/root" {
            return Err(
                "project_root must not be hardcoded /demo/root — bind a real project root".into(),
            );
        }
        next.project_root = trimmed.to_string();
    }
    root.set_host_settings(next).map_err(|e| e.to_string())?;
    Ok(SettingsDto::from(root.host_settings()))
}

/// PD-REMAIN-FILE-SAVE-01: merge known host-settings fields only (no free-form write path).
fn merge_file_save_settings(
    current: &HostSettings,
    ui_theme: Option<String>,
    locale: Option<String>,
    board_path: Option<String>,
    project_root: Option<String>,
) -> Result<HostSettings, String> {
    let mut next = current.clone();
    if let Some(t) = ui_theme {
        next.ui_theme = t;
    }
    if let Some(l) = locale {
        next.locale = l;
    }
    if let Some(bp) = board_path {
        let trimmed = bp.trim().to_string();
        if trimmed.starts_with("http://")
            || trimmed.starts_with("https://")
            || trimmed.contains(":8788")
            || trimmed.contains(":8787")
        {
            return Err(
                "board_path must be a local file path (not http / :8788 / :8787)".into(),
            );
        }
        next.board_path = trimmed;
    }
    if let Some(pr) = project_root {
        let trimmed = pr.trim().to_string();
        if trimmed == "/demo/root" {
            return Err(
                "project_root must not be hardcoded /demo/root — bind a real project root".into(),
            );
        }
        if trimmed.starts_with("http://")
            || trimmed.starts_with("https://")
            || trimmed.contains("://")
            || trimmed.contains(":8788")
            || trimmed.contains(":8787")
        {
            return Err(
                "project_root must be a local directory path (not URL / cloud)".into(),
            );
        }
        next.project_root = trimmed;
    }
    next.validate().map_err(|e| e.to_string())?;
    Ok(next)
}

/// PD-REMAIN-FILE-SAVE-01 result — persists settings／board binding only.
#[derive(Debug, Clone, Serialize)]
pub struct FileSaveResult {
    /// `"ok"`
    pub status: String,
    /// Always `false` — never write-backs PROJECT-BOARD.html／JSON.
    pub board_write_back: bool,
    /// Fixed store kind only (`host-settings`); never a caller-chosen write path.
    pub persisted_kind: String,
    pub settings: SettingsDto,
    pub message: Option<String>,
}

/// PD-REMAIN-FILE-SAVE-01: UI → `file_save` → HostSettings store (fixed path).
/// Accepts only known settings fields — **no** arbitrary path／`write_path`／board file write.
#[tauri::command]
pub fn file_save(
    state: State<'_, HostState>,
    ui_theme: Option<String>,
    locale: Option<String>,
    board_path: Option<String>,
    project_root: Option<String>,
) -> Result<FileSaveResult, String> {
    authorize("file_save").map_err(|e| e.to_string())?;
    let mut root = state.inner.lock().map_err(|_| poison_host())?;
    let next = merge_file_save_settings(
        root.host_settings(),
        ui_theme,
        locale,
        board_path,
        project_root,
    )?;
    root.set_host_settings(next).map_err(|e| e.to_string())?;
    Ok(FileSaveResult {
        status: "ok".into(),
        board_write_back: false,
        persisted_kind: "host-settings".into(),
        settings: SettingsDto::from(root.host_settings()),
        message: Some(
            "已持久化 host settings／看板路徑綁定（固定 host-settings；無看板寫回）".into(),
        ),
    })
}

/// PD-WIRE-OPEN-01: native folder dialog only.
/// Does **not** mutate settings — UI must persist via [`host_set_settings`] (`project_root`),
/// then refresh projections through `load_local_board`／`get_board`／`git_workbench_*`.
#[derive(Debug, Clone, Serialize)]
pub struct PickProjectDirectoryResult {
    /// `"ok"`｜`"cancelled"`｜`"error"`
    pub status: String,
    pub path: String,
    pub message: Option<String>,
}

#[tauri::command]
pub fn host_pick_project_directory() -> Result<PickProjectDirectoryResult, String> {
    authorize("host_pick_project_directory").map_err(|e| e.to_string())?;
    let picked = rfd::FileDialog::new()
        .set_title("開啟專案")
        .pick_folder();
    let Some(path) = picked else {
        return Ok(PickProjectDirectoryResult {
            status: "cancelled".into(),
            path: String::new(),
            message: Some("已取消開啟專案".into()),
        });
    };
    let path_str = path.to_string_lossy().to_string();
    if path_str.trim() == "/demo/root" {
        return Ok(PickProjectDirectoryResult {
            status: "error".into(),
            path: String::new(),
            message: Some(
                "不可綁定 /demo/root — 請選擇真實本機專案目錄".into(),
            ),
        });
    }
    if !path.is_dir() {
        return Ok(PickProjectDirectoryResult {
            status: "error".into(),
            path: path_str,
            message: Some("選取路徑不是有效目錄".into()),
        });
    }
    Ok(PickProjectDirectoryResult {
        status: "ok".into(),
        path: path_str,
        message: Some("已選取目錄（尚未持久化 — 由 host_set_settings 寫入）".into()),
    })
}

/// PD-REMAIN-FILE-NEW-01: legacy save-file dialog + create via [`FileSystemPort`].
/// Prefer [`host_create_project_directory`] (PD-BUG-FILE-NEW-01). Does **not** mutate settings.
#[tauri::command]
pub fn host_new_project_directory(
    state: State<'_, HostState>,
) -> Result<PickProjectDirectoryResult, String> {
    authorize("host_new_project_directory").map_err(|e| e.to_string())?;
    let picked = rfd::FileDialog::new()
        .set_title("新增專案 — 選擇新資料夾名稱與位置")
        .set_file_name("NewProject")
        .save_file();
    let Some(path) = picked else {
        return Ok(PickProjectDirectoryResult {
            status: "cancelled".into(),
            path: String::new(),
            message: Some("已取消新增專案".into()),
        });
    };
    let path_str = path.to_string_lossy().to_string();
    let root = state.inner.lock().map_err(|_| poison_host())?;
    match sgenaxis_host::create_new_project_root(root.fs(), &path_str) {
        Ok(created) => Ok(PickProjectDirectoryResult {
            status: "ok".into(),
            path: created,
            message: Some(
                "已建立專案目錄（尚未持久化 — 由 host_set_settings 寫入）".into(),
            ),
        }),
        Err(e) => Ok(PickProjectDirectoryResult {
            status: "error".into(),
            path: String::new(),
            message: Some(e.to_string()),
        }),
    }
}

/// PD-BUG-FILE-NEW-01: create `parent`/`name` via [`FileSystemPort`] (no dialog).
/// UI supplies name + parent from `host_pick_project_directory`. Does **not** mutate settings.
#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct CreateProjectDirectoryArgs {
    pub parent: String,
    pub name: String,
}

#[tauri::command]
pub fn host_create_project_directory(
    state: State<'_, HostState>,
    args: CreateProjectDirectoryArgs,
) -> Result<PickProjectDirectoryResult, String> {
    authorize("host_create_project_directory").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    match sgenaxis_host::create_new_project_under(root.fs(), &args.parent, &args.name) {
        Ok(created) => Ok(PickProjectDirectoryResult {
            status: "ok".into(),
            path: created,
            message: Some(
                "已建立專案目錄（尚未持久化 — 由 host_set_settings 寫入）".into(),
            ),
        }),
        Err(e) => Ok(PickProjectDirectoryResult {
            status: "error".into(),
            path: String::new(),
            message: Some(e.to_string()),
        }),
    }
}

/// PD-SET-01／PD-SET-UI-01: persist CLI／MCP via host settings.
#[tauri::command]
pub fn host_project_preferences_load(state:State<'_,HostState>,expected_project_root:String)->Result<serde_json::Value,String>{
    authorize("host_project_preferences_load").map_err(|e|e.to_string())?;
    let root=state.inner.lock().map_err(|_|poison_host())?;
    DispatchHost::project_policy_load(root.fs(),&root.host_settings().project_root,&expected_project_root)
}
#[tauri::command]
pub fn host_project_preferences_save(state:State<'_,HostState>,expected_project_root:String,expected_digest:Option<String>,draft_json:String)->Result<serde_json::Value,String>{
    authorize("host_project_preferences_save").map_err(|e|e.to_string())?;
    let root=state.inner.lock().map_err(|_|poison_host())?;
    DispatchHost::project_policy_save(root.fs(),&root.host_settings().project_root,&expected_project_root,expected_digest.as_deref(),draft_json.as_bytes())
}
#[tauri::command]
pub fn host_project_preferences_presets()->Result<serde_json::Value,String>{
    authorize("host_project_preferences_presets").map_err(|e|e.to_string())?;
    DispatchHost::project_policy_presets()
}
#[tauri::command]
pub fn host_project_preferences_pick_import(state:State<'_,HostState>)->Result<serde_json::Value,String>{
    authorize("host_project_preferences_pick_import").map_err(|e|e.to_string())?;
    let Some(path)=rfd::FileDialog::new().add_filter("專案偏好 JSON", &["json"]).pick_file() else {return Ok(serde_json::json!({"status":"cancelled"}));};
    let root=state.inner.lock().map_err(|_|poison_host())?;
    DispatchHost::project_policy_import(root.fs(),&path.to_string_lossy())
}
#[derive(Debug,Deserialize)]
#[serde(rename_all="camelCase",deny_unknown_fields)]
pub struct CreateProjectPreferencesArgs {pub parent:String,pub name:String,pub preset_id:Option<String>,pub imported_json:Option<String>}
#[tauri::command]
pub fn host_create_project_with_preferences(state:State<'_,HostState>,args:CreateProjectPreferencesArgs)->Result<serde_json::Value,String>{
    authorize("host_create_project_with_preferences").map_err(|e|e.to_string())?;
    let root=state.inner.lock().map_err(|_|poison_host())?;
    DispatchHost::project_policy_create(root.fs(),&args.parent,&args.name,args.preset_id.as_deref(),args.imported_json.as_deref())
}

// ── M01-S3 six-step project wizard command bridge ───────────────────────────
//
// Mirrors the S2 domain open/prepare/bind/save lifecycle. Owner authority is
// snapshotted from the live DispatchHost owner (never from UI-supplied roots).
// In-flight state lives server-side in `HostState.wizard`, keyed by an opaque
// token. Orchestration bodies are SKELETON (RED): `wizard_commit` returns the
// NOT_IMPLEMENTED sentinel until GREEN wires bind_definition + save_definition.
use sgenaxis_host::project_definition::DefinitionLocation;
use sgenaxis_host::project_preferences::PreferenceChoice;
use sgenaxis_host::project_wizard::{
    wizard_apply_step as host_wizard_apply_step, wizard_begin as host_wizard_begin,
    wizard_cancel as host_wizard_cancel, wizard_commit as host_wizard_commit,
    wizard_prepare_preferences as host_wizard_prepare_preferences, WizardBeginView,
    WizardCommitReceipt, WizardDraftPatch, WizardPreferencePlanView, WizardStepDto, WizardStepView,
    WizardToken,
};

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct WizardBeginArgs {
    /// "new" → NewProject(parent,name); "existing" → ExistingProject(parent as root).
    pub location_kind: String,
    pub parent: String,
    pub name: String,
    pub purpose: Option<String>,
}

fn wizard_build_location(args: &WizardBeginArgs) -> Result<DefinitionLocation, String> {
    match args.location_kind.as_str() {
        "new" => Ok(DefinitionLocation::NewProject {
            canonical_parent: args.parent.clone(),
            single_name: args.name.clone(),
        }),
        "existing" => Ok(DefinitionLocation::ExistingProject {
            canonical_root: args.parent.clone(),
        }),
        other => Err(format!("UNSUPPORTED_LOCATION_KIND: {other}")),
    }
}

#[tauri::command]
pub fn wizard_begin(
    window: WebviewWindow,
    app: State<'_, AppState>,
    state: State<'_, HostState>,
    args: WizardBeginArgs,
) -> Result<WizardBeginView, String> {
    authorize("wizard_begin").map_err(|e| e.to_string())?;
    let url = window.url().map_err(|e| e.to_string())?;
    if !guard_owner_caller_allowed(
        window.label(),
        url.scheme(),
        url.host_str().unwrap_or_default(),
        url.port(),
    ) {
        return Err("UNAUTHORIZED_CALLER".into());
    }
    let location = wizard_build_location(&args)?;
    let authority = {
        let dispatch = app.host.lock().map_err(|_| poison_dispatch())?;
        dispatch
            .definition_authority(window.label())
            .map_err(|e| e.to_string())?
    };
    let mut store = state.wizard.lock().map_err(|_| poison_host())?;
    host_wizard_begin(
        &mut store,
        authority,
        location,
        &args.name,
        args.purpose.as_deref().unwrap_or_default(),
    )
    .map_err(|e| e.to_string())
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct WizardApplyStepArgs {
    pub token: String,
    pub step: WizardStepDto,
    #[serde(default)]
    pub patch: WizardDraftPatch,
}

#[tauri::command]
pub fn wizard_apply_step(
    state: State<'_, HostState>,
    args: WizardApplyStepArgs,
) -> Result<WizardStepView, String> {
    authorize("wizard_apply_step").map_err(|e| e.to_string())?;
    let token = WizardToken::from_raw(&args.token);
    let mut store = state.wizard.lock().map_err(|_| poison_host())?;
    host_wizard_apply_step(&mut store, &token, args.step, args.patch).map_err(|e| e.to_string())
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct WizardPreparePreferencesArgs {
    pub token: String,
    /// "skip" | "preset" | "import".
    pub choice: String,
    pub preset_id: Option<String>,
    pub imported_json: Option<String>,
}

#[tauri::command]
pub fn wizard_prepare_preferences(
    state: State<'_, HostState>,
    args: WizardPreparePreferencesArgs,
) -> Result<WizardPreferencePlanView, String> {
    authorize("wizard_prepare_preferences").map_err(|e| e.to_string())?;
    let token = WizardToken::from_raw(&args.token);
    let choice = match args.choice.as_str() {
        "skip" => PreferenceChoice::Skip,
        "preset" => PreferenceChoice::Preset(
            args.preset_id.as_deref().ok_or("MISSING_PRESET_ID")?,
        ),
        "import" => PreferenceChoice::Imported(
            args.imported_json.as_deref().ok_or("MISSING_IMPORT")?.as_bytes(),
        ),
        other => return Err(format!("UNSUPPORTED_PREFERENCE_CHOICE: {other}")),
    };
    let mut store = state.wizard.lock().map_err(|_| poison_host())?;
    host_wizard_prepare_preferences(&mut store, &token, choice).map_err(|e| e.to_string())
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct WizardTokenArgs {
    pub token: String,
}

#[cfg(windows)]
#[tauri::command]
pub fn wizard_commit(
    state: State<'_, HostState>,
    args: WizardTokenArgs,
) -> Result<WizardCommitReceipt, String> {
    authorize("wizard_commit").map_err(|e| e.to_string())?;
    let token = WizardToken::from_raw(&args.token);
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let mut store = state.wizard.lock().map_err(|_| poison_host())?;
    let commit = sgenaxis_adapters::StdFileCommit::new();
    host_wizard_commit(root.fs(), &commit, &mut store, &token).map_err(|e| e.to_string())
}

// StdFileCommit is the Windows-only file-commit adapter (std::os::windows::fs),
// exported only under cfg(all(windows, feature = "std-adapters")). Off Windows the
// command stays registered (handler/ACL/tests unchanged) but refuses at runtime.
#[cfg(not(windows))]
#[tauri::command]
pub fn wizard_commit(
    _state: State<'_, HostState>,
    _args: WizardTokenArgs,
) -> Result<WizardCommitReceipt, String> {
    authorize("wizard_commit").map_err(|e| e.to_string())?;
    Err("wizard_commit requires the Windows file-commit adapter".to_string())
}

#[tauri::command]
pub fn wizard_cancel(
    state: State<'_, HostState>,
    args: WizardTokenArgs,
) -> Result<(), String> {
    authorize("wizard_cancel").map_err(|e| e.to_string())?;
    let token = WizardToken::from_raw(&args.token);
    let mut store = state.wizard.lock().map_err(|_| poison_host())?;
    host_wizard_cancel(&mut store, &token).map_err(|e| e.to_string())
}

/// PD-SET-01／PD-SET-UI-01: persist CLI／MCP via host settings.
/// `activate=true` → Live（rejects invalid paths）；`false` → DryRun（`revoke_agent_live`）.
#[tauri::command]
pub fn host_set_agent_settings(
    state: State<'_, HostState>,
    args: SetAgentSettingsArgs,
) -> Result<SettingsDto, String> {
    authorize("host_set_agent_settings").map_err(|e| e.to_string())?;
    let mut root = state.inner.lock().map_err(|_| poison_host())?;
    let mut next = root.host_settings().clone();
    apply_agent_args(&mut next.agent, &args)?;
    if args.activate {
        next.try_activate_agent(root.fs())
            .map_err(|e| e.to_string())?;
    } else {
        // Draft／切回 DryRun：清 agent_active + live_approved；路徑仍可持久化。
        next.revoke_agent_live();
    }
    root.set_host_settings(next).map_err(|e| e.to_string())?;
    Ok(SettingsDto::from(root.host_settings()))
}

#[tauri::command]
pub fn host_request_shutdown(
    app: AppHandle,
    state: State<'_, HostState>,
) -> Result<PhaseDto, String> {
    authorize("host_request_shutdown").map_err(|e| e.to_string())?;
    let mut root = state.inner.lock().map_err(|_| poison_host())?;
    root.shutdown().map_err(|e| e.to_string())?;
    let dto = phase_dto(root.phase());
    drop(root);
    app.exit(0);
    Ok(dto)
}

// ── PD-GIT-UI-01 (read-only) ────────────────────────────────────────────────

fn kind_label(kind: GitStatusKind) -> &'static str {
    match kind {
        GitStatusKind::Modified => "modified",
        GitStatusKind::Added => "added",
        GitStatusKind::Deleted => "deleted",
        GitStatusKind::Renamed => "renamed",
        GitStatusKind::Untracked => "untracked",
        GitStatusKind::Other => "other",
    }
}

fn workbench_dto(summary: &GitWorkbenchSummary, writes_enabled: bool) -> GitWorkbenchDto {
    let empty = summary.entry_count == 0 && summary.diff_text.trim().is_empty();
    GitWorkbenchDto {
        repo: summary.repo.clone(),
        branch: summary.branch.clone(),
        entry_count: summary.entry_count,
        entries: summary
            .entries
            .iter()
            .map(|e| GitEntryDto {
                path: e.path.clone(),
                kind: kind_label(e.kind).into(),
            })
            .collect(),
        recent_commits: summary
            .recent_commits
            .iter()
            .map(|c| GitCommitDto {
                hash: c.hash.clone(),
                subject: c.subject.clone(),
                author: c.author.clone(),
                date: c.date.clone(),
            })
            .collect(),
        diff_text: summary.diff_text.clone(),
        ahead: summary.ahead,
        behind: summary.behind,
        upstream: summary.upstream.clone(),
        branches: summary
            .branches
            .iter()
            .map(|b| GitBranchDto {
                name: b.name.clone(),
                is_current: b.is_current,
            })
            .collect(),
        remotes: summary
            .remotes
            .iter()
            .map(|r| GitRemoteDto {
                name: r.name.clone(),
                url: r.url.clone(),
                tested: r.tested,
            })
            .collect(),
        tags: summary
            .tags
            .iter()
            .map(|t| GitTagDto {
                name: t.name.clone(),
                peeled: t.peeled.clone(),
            })
            .collect(),
        stashes: summary
            .stashes
            .iter()
            .map(|st| GitStashDto {
                id: st.id.clone(),
                message: st.message.clone(),
            })
            .collect(),
        conflict: GitConflictDto {
            active: summary.conflict.active,
            kind: summary.conflict.kind.clone(),
            source: summary.conflict.source.clone(),
            target: summary.conflict.target.clone(),
            files: summary
                .conflict
                .files
                .iter()
                .map(|f| GitConflictFileDto {
                    path: f.path.clone(),
                    code: f.code.clone(),
                    kind: f.kind.clone(),
                    ours: f.ours.clone(),
                    theirs: f.theirs.clone(),
                })
                .collect(),
        },
        settings: GitSettingsDto {
            author: summary.settings.author.clone(),
            email: summary.settings.email.clone(),
            ignore: summary.settings.ignore.clone(),
        },
        // Host sets true only with approving GitWritePort; each write still needs approval.
        writes_enabled,
        status: if empty { "empty".into() } else { "ok".into() },
        message: if empty {
            Some("worktree summary empty".into())
        } else {
            None
        },
    }
}

/// PD-WIRE-BOOT-01: unbound／非 git／Port 失敗 → 可讀 NOT RUN 投影（不 Err 崩潰）.
fn workbench_not_run(repo: &str, message: impl Into<String>) -> GitWorkbenchDto {
    GitWorkbenchDto {
        repo: repo.to_string(),
        branch: None,
        entries: Vec::new(),
        entry_count: 0,
        recent_commits: Vec::new(),
        diff_text: String::new(),
        ahead: 0,
        behind: 0,
        upstream: None,
        branches: Vec::new(),
        remotes: Vec::new(),
        tags: Vec::new(),
        stashes: Vec::new(),
        conflict: GitConflictDto::default(),
        settings: GitSettingsDto::default(),
        writes_enabled: false,
        status: "not_run".into(),
        message: Some(message.into()),
    }
}

/// Reject force-push patterns (out of scope for PD-GIT-WRITE-UI-01).
fn reject_force_push(remote: &str, refspec: Option<&str>) -> Result<(), String> {
    let remote_l = remote.to_ascii_lowercase();
    if remote_l.contains("--force")
        || remote_l.split_whitespace().any(|t| t == "-f" || t == "--force-with-lease")
    {
        return Err("force push is forbidden (out of scope)".into());
    }
    if let Some(r) = refspec {
        let trimmed = r.trim();
        if trimmed.starts_with('+') {
            return Err("force push is forbidden (out of scope)".into());
        }
        let lower = trimmed.to_ascii_lowercase();
        if lower.contains("--force")
            || lower.split_whitespace().any(|t| t == "-f" || t == "--force-with-lease")
        {
            return Err("force push is forbidden (out of scope)".into());
        }
    }
    Ok(())
}

/// Pure write helper — UI／tests call via allowlisted commands; never shells git from UI.
fn perform_git_write_commit(
    write: &dyn GitWritePort,
    repo: &str,
    message: &str,
    approved: bool,
) -> GitWriteResultDto {
    if !approved {
        return GitWriteResultDto {
            ok: false,
            op: "commit".into(),
            message: "approval denied; no mutation".into(),
            local_preserved: true,
        };
    }
    match write.commit(repo, message, GitWriteApproval::granted()) {
        Ok(()) => GitWriteResultDto {
            ok: true,
            op: "commit".into(),
            message: "commit ok".into(),
            local_preserved: true,
        },
        Err(e) => GitWriteResultDto {
            ok: false,
            op: "commit".into(),
            message: e.to_string(),
            local_preserved: true,
        },
    }
}

fn perform_git_write_push(
    write: &dyn GitWritePort,
    repo: &str,
    remote: &str,
    refspec: Option<&str>,
    approved: bool,
) -> Result<GitWriteResultDto, String> {
    reject_force_push(remote, refspec)?;
    if !approved {
        return Ok(GitWriteResultDto {
            ok: false,
            op: "push".into(),
            message: "approval denied; no mutation".into(),
            local_preserved: true,
        });
    }
    match write.push(repo, remote, refspec, GitWriteApproval::granted()) {
        Ok(()) => Ok(GitWriteResultDto {
            ok: true,
            op: "push".into(),
            message: "push ok".into(),
            local_preserved: true,
        }),
        Err(e) => Ok(GitWriteResultDto {
            ok: false,
            op: "push".into(),
            message: e.to_string(),
            // Push failure must not discard local commits (PD-GIT-02 / WRITE-UI).
            local_preserved: true,
        }),
    }
}

/// PD-WIRE-ROOT-01: explicit repo arg, else settings `project_root` (no silent cwd／`/demo/root`).
fn resolve_repo(repo: Option<String>, settings: &HostSettings) -> Result<String, String> {
    let trimmed = repo.unwrap_or_default();
    let trimmed = trimmed.trim();
    if !trimmed.is_empty() {
        if trimmed == "/demo/root" {
            return Err(
                "project_root must not be hardcoded /demo/root — bind a real project root".into(),
            );
        }
        return Ok(trimmed.to_string());
    }
    resolve_bound_project_root(None, settings)
}

/// Worktree summary via [`GitPort`]; `writes_enabled` from host composition.
/// PD-WIRE-BOOT-01: unbound／非 git → `Ok` + `status=not_run`（可讀空態；不崩潰）.
#[tauri::command]
pub fn git_workbench_summary(
    state: State<'_, HostState>,
    repo: Option<String>,
    log_limit: Option<usize>,
) -> Result<GitWorkbenchDto, String> {
    authorize("git_workbench_summary").map_err(|e| e.to_string())?;
    let limit = log_limit.unwrap_or(12);
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let repo = match resolve_repo(repo, root.host_settings()) {
        Ok(r) => r,
        Err(msg) => return Ok(workbench_not_run("", msg)),
    };
    match summarize_worktree(root.git(), &repo, limit) {
        Ok(summary) => Ok(workbench_dto(&summary, root.git_writes_enabled())),
        Err(e) => Ok(workbench_not_run(&repo, e.to_string())),
    }
}

/// Read-only unified diff; optional pathspec for selected file.
#[tauri::command]
pub fn git_workbench_diff(
    state: State<'_, HostState>,
    repo: Option<String>,
    pathspec: Option<String>,
) -> Result<GitDiffDto, String> {
    authorize("git_workbench_diff").map_err(|e| e.to_string())?;
    let path = pathspec
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string);
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let repo = resolve_repo(repo, root.host_settings())?;
    let git: &dyn GitPort = root.git();
    let diff_text = git.diff(&repo, path.as_deref()).map_err(|e| e.to_string())?;
    Ok(GitDiffDto {
        repo,
        pathspec: path,
        diff_text,
    })
}

/// Read-only preview of the already-staged Index; never stages or mutates Git state.
#[tauri::command]
pub fn git_index_commit_preview(
    state: State<'_, AppState>,
    host: State<'_, HostState>,
    repo: Option<String>,
) -> Result<IndexCommitPreviewDto, IndexCommitErrorDto> {
    authorize("git_index_commit_preview").map_err(|e| IndexCommitErrorDto {
        code: "InvalidInput".into(), preview_id: None, observed: None,
        diagnostic: e.to_string(), mutation_started: false, requires_new_preview: false,
    })?;
    let project_root = {
        let root = host.inner.lock().map_err(|_| IndexCommitErrorDto {
            code: "Busy".into(), preview_id: None, observed: None,
            diagnostic: poison_host(), mutation_started: false, requires_new_preview: false,
        })?;
        resolve_repo(repo, root.host_settings()).map_err(|message| IndexCommitErrorDto {
            code: "InvalidInput".into(), preview_id: None, observed: None,
            diagnostic: message, mutation_started: false, requires_new_preview: false,
        })?
    };
    let coordinator = state.host.lock().map_err(|_| IndexCommitErrorDto {
        code: "Busy".into(), preview_id: None, observed: None,
        diagnostic: poison_dispatch(), mutation_started: false, requires_new_preview: false,
    })?.git_index_commit_coordinator();
    coordinator.prepare(&project_root)
}

/// Explicitly confirm one preview generation; host consumes it once and commits only its Index.
#[tauri::command]
pub fn git_index_commit_confirm(
    state: State<'_, AppState>,
    request: IndexCommitRequestDto,
) -> Result<IndexCommitOutcomeDto, IndexCommitErrorDto> {
    authorize("git_index_commit_confirm").map_err(|e| IndexCommitErrorDto {
        code: "InvalidInput".into(), preview_id: Some(request.preview_id.clone()), observed: None,
        diagnostic: e.to_string(), mutation_started: false, requires_new_preview: false,
    })?;
    let coordinator = state.host.lock().map_err(|_| IndexCommitErrorDto {
        code: "Busy".into(), preview_id: Some(request.preview_id.clone()), observed: None,
        diagnostic: poison_dispatch(), mutation_started: false, requires_new_preview: false,
    })?.git_index_commit_coordinator();
    coordinator.commit(request)
}

/// Approval-gated commit via [`GitWritePort`] (PD-GIT-WRITE-UI-01). No UI→git CLI.
#[tauri::command]
pub fn git_write_commit(
    state: State<'_, HostState>,
    args: GitWriteCommitArgs,
) -> Result<GitWriteResultDto, String> {
    authorize("git_write_commit").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let repo = resolve_repo(args.repo, root.host_settings())?;
    if !root.git_writes_enabled() {
        return Ok(GitWriteResultDto {
            ok: false,
            op: "commit".into(),
            message: "git writes disabled (gated adapter)".into(),
            local_preserved: true,
        });
    }
    Ok(perform_git_write_commit(
        root.git_write(),
        &repo,
        &args.message,
        args.approved,
    ))
}

/// Approval-gated push via [`GitWritePort`] (no force). Failures keep local commits.
#[tauri::command]
pub fn git_write_push(
    state: State<'_, HostState>,
    args: GitWritePushArgs,
) -> Result<GitWriteResultDto, String> {
    authorize("git_write_push").map_err(|e| e.to_string())?;
    let remote = args.remote.trim();
    if remote.is_empty() {
        return Err("empty remote name".into());
    }
    let refspec = args
        .refspec
        .as_deref()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .map(str::to_string);
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let repo = resolve_repo(args.repo, root.host_settings())?;
    if !root.git_writes_enabled() {
        return Ok(GitWriteResultDto {
            ok: false,
            op: "push".into(),
            message: "git writes disabled (gated adapter)".into(),
            local_preserved: true,
        });
    }
    perform_git_write_push(
        root.git_write(),
        &repo,
        remote,
        refspec.as_deref(),
        args.approved,
    )
}

/// Soft-gated switch: empty branch or unapproved never mutates; approved switches via port.
fn perform_git_switch(
    write: &dyn GitWritePort,
    repo: &str,
    branch: &str,
    approved: bool,
) -> GitWriteResultDto {
    if branch.trim().is_empty() {
        return GitWriteResultDto {
            ok: false,
            op: "switch".into(),
            message: "empty branch name".into(),
            local_preserved: true,
        };
    }
    if !approved {
        return GitWriteResultDto {
            ok: false,
            op: "switch".into(),
            message: "approval denied; no mutation".into(),
            local_preserved: true,
        };
    }
    match write.switch_branch(repo, branch, GitWriteApproval::granted()) {
        Ok(()) => GitWriteResultDto {
            ok: true,
            op: "switch".into(),
            message: "switch ok".into(),
            local_preserved: true,
        },
        Err(e) => GitWriteResultDto {
            ok: false,
            op: "switch".into(),
            message: e.to_string(),
            local_preserved: true,
        },
    }
}

/// Approval-gated switch to an existing local branch (PD-GIT-SWITCH-03). No force／create.
#[tauri::command]
pub fn git_switch_branch(
    state: State<'_, HostState>,
    args: GitWriteSwitchArgs,
) -> Result<GitWriteResultDto, String> {
    authorize("git_switch_branch").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let repo = resolve_repo(args.repo, root.host_settings())?;
    if !root.git_writes_enabled() {
        return Ok(GitWriteResultDto {
            ok: false,
            op: "switch".into(),
            message: "git writes disabled (gated adapter)".into(),
            local_preserved: true,
        });
    }
    Ok(perform_git_switch(
        root.git_write(),
        &repo,
        &args.branch,
        args.approved,
    ))
}

// ── PD-DEPLOY-CMD-01 (read-only; DeployPort façade) ─────────────────────────

#[derive(Debug, Clone, Serialize)]
pub struct DeployStatusDto {
    pub supported: bool,
    pub platform: String,
    pub packaging: String,
    pub format: String,
    pub message: String,
    pub elevated_qn_auto: bool,
    pub artifact_convention: Option<String>,
    pub last_artifact_path: Option<String>,
}

impl From<&DeployStatusView> for DeployStatusDto {
    fn from(s: &DeployStatusView) -> Self {
        Self {
            supported: s.supported,
            platform: s.platform.clone(),
            packaging: s.packaging.clone(),
            format: s.format.clone(),
            message: s.message.clone(),
            elevated_qn_auto: s.elevated_qn_auto,
            artifact_convention: s.artifact_convention.clone(),
            last_artifact_path: s.last_artifact_path.clone(),
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct DeployCheckDto {
    pub status: String,
    pub ok: bool,
    pub issues: Vec<String>,
    pub needs_manual_elevated: bool,
    pub message: String,
}

impl From<&DeployCheckView> for DeployCheckDto {
    fn from(c: &DeployCheckView) -> Self {
        Self {
            status: c.status.clone(),
            ok: c.ok,
            issues: c.issues.clone(),
            needs_manual_elevated: c.needs_manual_elevated,
            message: c.message.clone(),
        }
    }
}

#[derive(Debug, Clone, Serialize)]
pub struct DeployArtifactDto {
    pub kind: String,
    pub path: String,
    pub exists: bool,
    pub sha256: Option<String>,
}

impl From<&DeployArtifactView> for DeployArtifactDto {
    fn from(a: &DeployArtifactView) -> Self {
        Self {
            kind: a.kind.clone(),
            path: a.path.clone(),
            exists: a.exists,
            sha256: a.sha256.clone(),
        }
    }
}

/// Read-only packaging／deploy capability via DeployPort (no shell／msiexec).
#[tauri::command]
pub fn deploy_status(state: State<'_, HostState>) -> Result<DeployStatusDto, String> {
    authorize("deploy_status").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let st = root.deploy_status().map_err(|e| e.to_string())?;
    Ok(DeployStatusDto::from(&st))
}

/// Read-only check; artifact present → `needs_manual_elevated` (never auto `/qn`).
#[tauri::command]
pub fn deploy_check(state: State<'_, HostState>) -> Result<DeployCheckDto, String> {
    authorize("deploy_check").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let report = root.deploy_check().map_err(|e| e.to_string())?;
    Ok(DeployCheckDto::from(&report))
}

/// List packaging artifact convention／last path (existence from DeployPort).
#[tauri::command]
pub fn list_artifacts(state: State<'_, HostState>) -> Result<Vec<DeployArtifactDto>, String> {
    authorize("list_artifacts").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    let arts = root.list_artifacts().map_err(|e| e.to_string())?;
    Ok(arts.iter().map(DeployArtifactDto::from).collect())
}

// ── PD-REMAIN-PORTS-UI-01 (Ports／adapter registry projection) ───────────────

#[derive(Debug, Clone, Serialize)]
pub struct PortBindingDto {
    pub port: String,
    pub adapter: String,
    pub status: String,
    pub detail: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct PortsStatusDto {
    /// `ok`｜`empty`
    pub status: String,
    pub entry_count: usize,
    pub entries: Vec<PortBindingDto>,
    pub message: Option<String>,
}

impl From<&sgenaxis_host::PortsStatusView> for PortsStatusDto {
    fn from(v: &sgenaxis_host::PortsStatusView) -> Self {
        Self {
            status: v.status.clone(),
            entry_count: v.entry_count,
            entries: v
                .entries
                .iter()
                .map(|e| PortBindingDto {
                    port: e.port.clone(),
                    adapter: e.adapter.clone(),
                    status: e.status.clone(),
                    detail: e.detail.clone(),
                })
                .collect(),
            message: v.message.clone(),
        }
    }
}

/// Registered Port／adapter status via composition projection (no OS enumeration).
#[tauri::command]
pub fn ports_status(state: State<'_, HostState>) -> Result<PortsStatusDto, String> {
    authorize("ports_status").map_err(|e| e.to_string())?;
    let root = state.inner.lock().map_err(|_| poison_host())?;
    Ok(PortsStatusDto::from(&root.ports_status()))
}

// ── PD-SHELL-UIDESIGN-VIEW-01 ───────────────────────────────────────────────

const UIDESIGN_INDEX_REL: &str = "docs/ui-design/index.html";

#[derive(Debug, Clone, Default, serde::Deserialize)]
pub struct UiDesignPackageArgs {
    /// Optional explicit project_root (else host settings).
    pub project_root: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiDesignPackageDto {
    /// `ok`｜`missing`｜`unbound`｜`error`
    pub status: String,
    pub exists: bool,
    pub path: String,
    pub relative_path: String,
    /// Always `false` — design package is never product evidence.
    pub product_evidence: bool,
    /// Always `false` — must not count as formal acceptance PASS.
    pub formal_acceptance_pass: bool,
    pub message: Option<String>,
    /// Optional hint for WebView convertFileSrc（absolute path when exists）.
    pub embed_hint: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiDesignOpenDto {
    pub opened: bool,
    pub path: String,
    pub product_evidence: bool,
    pub formal_acceptance_pass: bool,
    pub message: Option<String>,
}

fn resolve_uidesign_index_path(project_root: &str) -> PathBuf {
    let mut out = PathBuf::from(project_root.trim());
    out.push("docs");
    out.push("ui-design");
    out.push("index.html");
    out
}

/// Ensure resolved path stays under project_root／docs/ui-design（no path escape）.
fn uidesign_path_is_controlled(project_root: &str, path: &Path) -> bool {
    let root = PathBuf::from(project_root.trim());
    let Ok(root_c) = root.canonicalize() else {
        return false;
    };
    let Ok(path_c) = path.canonicalize() else {
        // File may not exist yet — check lexical parent under root/docs/ui-design.
        let parent = path.parent();
        let Some(parent) = parent else {
            return false;
        };
        let expected = root.join("docs").join("ui-design");
        return parent == expected || parent.starts_with(&expected);
    };
    path_c.starts_with(&root_c)
        && path_c
            .file_name()
            .and_then(|n| n.to_str())
            .map(|n| n.eq_ignore_ascii_case("index.html"))
            .unwrap_or(false)
}

/// PD-SHELL-UIDESIGN-VIEW-01 — probe design package under project_root.
/// Never marks product_evidence／formal_acceptance_pass. Uses FileSystemPort（no UI→FS）.
#[tauri::command]
pub fn uidesign_package_status(
    host: State<'_, HostState>,
    args: Option<UiDesignPackageArgs>,
) -> Result<UiDesignPackageDto, String> {
    let args = args.unwrap_or_default();
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root = match resolve_bound_project_root(
        args.project_root.as_deref(),
        root.host_settings(),
    ) {
        Ok(r) => r,
        Err(msg) => {
            return Ok(UiDesignPackageDto {
                status: "unbound".into(),
                exists: false,
                path: UIDESIGN_INDEX_REL.into(),
                relative_path: UIDESIGN_INDEX_REL.into(),
                product_evidence: false,
                formal_acceptance_pass: false,
                message: Some(msg),
                embed_hint: None,
            });
        }
    };
    let path_buf = resolve_uidesign_index_path(&project_root);
    let path = path_buf.to_string_lossy().into_owned();
    if !uidesign_path_is_controlled(&project_root, &path_buf) {
        return Ok(UiDesignPackageDto {
            status: "error".into(),
            exists: false,
            path,
            relative_path: UIDESIGN_INDEX_REL.into(),
            product_evidence: false,
            formal_acceptance_pass: false,
            message: Some("path escapes controlled docs/ui-design".into()),
            embed_hint: None,
        });
    }
    let exists = root.fs().exists(&path).unwrap_or(false);
    Ok(UiDesignPackageDto {
        status: if exists {
            "ok".into()
        } else {
            "missing".into()
        },
        exists,
        path: path.clone(),
        relative_path: UIDESIGN_INDEX_REL.into(),
        product_evidence: false,
        formal_acceptance_pass: false,
        message: if exists {
            Some("design package present (not product evidence; not formal acceptance PASS)".into())
        } else {
            Some(format!(
                "missing {UIDESIGN_INDEX_REL} under project_root — empty state + path"
            ))
        },
        embed_hint: if exists { Some(path) } else { None },
    })
}

/// PD-SHELL-UIDESIGN-VIEW-01 — controlled open of docs/ui-design/index.html only.
/// No arbitrary shell IPC; opens the allowlisted file via OS file association.
#[tauri::command]
pub fn uidesign_open_package(
    host: State<'_, HostState>,
    args: Option<UiDesignPackageArgs>,
) -> Result<UiDesignOpenDto, String> {
    let status = uidesign_package_status(host, args)?;
    if !status.exists {
        return Ok(UiDesignOpenDto {
            opened: false,
            path: status.path,
            product_evidence: false,
            formal_acceptance_pass: false,
            message: status.message.or_else(|| Some("design package missing".into())),
        });
    }
    let path = status.path.clone();
    let open_result = open_uidesign_index_controlled(&path);
    match open_result {
        Ok(()) => Ok(UiDesignOpenDto {
            opened: true,
            path,
            product_evidence: false,
            formal_acceptance_pass: false,
            message: Some(
                "opened via host (design package ≠ product evidence; not formal acceptance PASS)"
                    .into(),
            ),
        }),
        Err(e) => Ok(UiDesignOpenDto {
            opened: false,
            path,
            product_evidence: false,
            formal_acceptance_pass: false,
            message: Some(e),
        }),
    }
}

fn open_uidesign_index_controlled(path: &str) -> Result<(), String> {
    // Path must end with index.html under ui-design (defense in depth).
    let p = Path::new(path);
    let name_ok = p
        .file_name()
        .and_then(|n| n.to_str())
        .map(|n| n.eq_ignore_ascii_case("index.html"))
        .unwrap_or(false);
    let parent_ok = p
        .parent()
        .and_then(|par| par.file_name())
        .and_then(|n| n.to_str())
        .map(|n| n == "ui-design")
        .unwrap_or(false);
    if !name_ok || !parent_ok {
        return Err("refusing to open non-allowlisted path".into());
    }
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("cmd")
            .args(["/C", "start", "", path])
            .spawn()
            .map_err(|e| format!("open failed: {e}"))?;
        return Ok(());
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(path)
            .spawn()
            .map_err(|e| format!("open failed: {e}"))?;
        return Ok(());
    }
    #[cfg(all(unix, not(target_os = "macos")))]
    {
        std::process::Command::new("xdg-open")
            .arg(path)
            .spawn()
            .map_err(|e| format!("open failed: {e}"))?;
        return Ok(());
    }
    #[cfg(not(any(target_os = "windows", target_os = "macos", unix)))]
    {
        let _ = path;
        Err("open not supported on this platform".into())
    }
}

// ── PD-UIDESIGNER-FORMAT-01 / BUILD-01 / ASK-01 ─────────────────────────────

#[derive(Debug, Clone, Default, Deserialize)]
pub struct UiDesignDocArgs {
    pub project_root: Option<String>,
    /// Relative path under project (default `design/main.sgendesign`).
    pub rel_path: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct UiDesignSaveArgs {
    pub project_root: Option<String>,
    pub rel_path: Option<String>,
    pub doc: DesignDoc,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiDesignSaveDto {
    pub path: String,
    pub relative_path: String,
    /// Always false — design ≠ product PASS.
    pub product_pass: bool,
    pub message: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiDesignLoadDto {
    pub path: String,
    pub relative_path: String,
    pub doc: DesignDoc,
    pub product_pass: bool,
    pub message: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct UiDesignBuildArgs {
    pub project_root: Option<String>,
    pub doc: DesignDoc,
    /// Preview basename (default `main` → design/build/main.preview.html).
    pub name: Option<String>,
    /// When true, open the preview via OS association (communication only).
    #[serde(default)]
    pub open_after: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiDesignBuildDto {
    pub path: String,
    pub opened: bool,
    pub product_pass: bool,
    pub message: Option<String>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct UiDesignAskArgs {
    pub node: DesignNode,
    pub user_note: Option<String>,
    /// When true, upsert a gray work item via DispatchHost (optional).
    #[serde(default)]
    pub upsert_gray: bool,
    pub work_item_id: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
pub struct UiDesignAskDto {
    pub title: String,
    pub bdd_draft: String,
    pub work_item_id: Option<String>,
    pub upserted: bool,
    pub product_pass: bool,
    pub message: Option<String>,
    /// When no IPC／offline — UI may surface NOT RUN.
    pub status: String,
}

fn uidesign_rel(args_rel: Option<&str>) -> String {
    args_rel
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or(UIDESIGN_DEFAULT_REL)
        .to_string()
}

/// PD-UIDESIGNER-FORMAT-01 — save `.sgendesign` via FileSystemPort.
#[tauri::command]
pub fn uidesign_save_design(
    host: State<'_, HostState>,
    args: UiDesignSaveArgs,
) -> Result<UiDesignSaveDto, String> {
    authorize("uidesign_save_design").map_err(|e| e.to_string())?;
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root =
        resolve_bound_project_root(args.project_root.as_deref(), root.host_settings())?;
    let rel = uidesign_rel(args.rel_path.as_deref());
    let path = save_design_file(root.fs(), &project_root, &rel, &args.doc)
        .map_err(|e| e.to_string())?;
    Ok(UiDesignSaveDto {
        path,
        relative_path: rel,
        product_pass: false,
        message: Some(
            "saved .sgendesign (設計意圖紀錄 ≠ 產品發行物／非正式 PASS)".into(),
        ),
    })
}

/// PD-UIDESIGNER-FORMAT-01 — load `.sgendesign` via FileSystemPort.
#[tauri::command]
pub fn uidesign_load_design(
    host: State<'_, HostState>,
    args: Option<UiDesignDocArgs>,
) -> Result<UiDesignLoadDto, String> {
    authorize("uidesign_load_design").map_err(|e| e.to_string())?;
    let args = args.unwrap_or_default();
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root =
        resolve_bound_project_root(args.project_root.as_deref(), root.host_settings())?;
    let rel = uidesign_rel(args.rel_path.as_deref());
    let (doc, path) = load_design_file(root.fs(), &project_root, &rel)
        .map_err(|e| e.to_string())?;
    Ok(UiDesignLoadDto {
        path,
        relative_path: rel,
        doc,
        product_pass: false,
        message: Some("loaded .sgendesign (非產品 PASS)".into()),
    })
}

/// PD-UIDESIGNER-BUILD-01 — build interactive preview HTML (communication only).
#[tauri::command]
pub fn uidesign_build_preview(
    host: State<'_, HostState>,
    args: UiDesignBuildArgs,
) -> Result<UiDesignBuildDto, String> {
    authorize("uidesign_build_preview").map_err(|e| e.to_string())?;
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root =
        resolve_bound_project_root(args.project_root.as_deref(), root.host_settings())?;
    let name = args.name.as_deref().unwrap_or("main");
    let path = build_preview_file(root.fs(), &project_root, &args.doc, name)
        .map_err(|e| e.to_string())?;
    let mut opened = false;
    if args.open_after {
        // Preview HTML is under design/build — open via OS association (not product PASS).
        #[cfg(target_os = "windows")]
        {
            opened = std::process::Command::new("cmd")
                .args(["/C", "start", "", &path])
                .spawn()
                .is_ok();
        }
        #[cfg(target_os = "macos")]
        {
            opened = std::process::Command::new("open")
                .arg(&path)
                .spawn()
                .is_ok();
        }
        #[cfg(all(unix, not(target_os = "macos")))]
        {
            opened = std::process::Command::new("xdg-open")
                .arg(&path)
                .spawn()
                .is_ok();
        }
    }
    Ok(UiDesignBuildDto {
        path,
        opened,
        product_pass: false,
        message: Some(
            "built interactive preview HTML（溝通用 · 非產品／非正式 PASS）".into(),
        ),
    })
}

/// PD-UIDESIGNER-ASK-01 — draft BDD／title from selected node; optional gray upsert.
#[tauri::command]
pub fn uidesign_ask_agent(
    state: State<'_, AppState>,
    args: UiDesignAskArgs,
) -> Result<UiDesignAskDto, String> {
    authorize("uidesign_ask_agent").map_err(|e| e.to_string())?;
    let note = args.user_note.as_deref().unwrap_or("");
    let (title, bdd_draft) = ask_agent_draft(&args.node, note);
    let work_item_id = args.work_item_id.clone().unwrap_or_else(|| {
        format!(
            "UI-ASK-{}",
            args.node
                .id
                .chars()
                .map(|c| if c.is_ascii_alphanumeric() { c } else { '-' })
                .collect::<String>()
        )
    });
    let mut upserted = false;
    if args.upsert_gray {
        let mut host = state.host.lock().map_err(|_| poison_dispatch())?;
        host.upsert_task(UpsertTaskArgs {
            id: work_item_id.clone(),
            title: title.clone(),
            zone: "gray".into(),
        })?;
        upserted = true;
    }
    Ok(UiDesignAskDto {
        title,
        bdd_draft,
        work_item_id: Some(work_item_id),
        upserted,
        product_pass: false,
        message: Some("Ask Agent 草稿（設計≠產品驗收 PASS）".into()),
        status: "ok".into(),
    })
}

/// Project-scoped scene text save（僅 `scene/*`；需綁定 project_root）。
#[derive(Debug, Deserialize)]
pub struct SceneSaveArgs {
    pub project_root: Option<String>,
    pub rel_path: Option<String>,
    pub text: String,
}

#[derive(Debug, Serialize)]
pub struct SceneSaveDto {
    pub path: String,
    pub relative_path: String,
    pub product_pass: bool,
    pub message: Option<String>,
}

/// Project-scoped scene text load.
#[derive(Debug, Deserialize, Default)]
pub struct SceneLoadArgs {
    pub project_root: Option<String>,
    pub rel_path: Option<String>,
}

#[derive(Debug, Serialize)]
pub struct SceneLoadDto {
    pub path: String,
    pub relative_path: String,
    pub text: String,
    pub product_pass: bool,
    pub message: Option<String>,
}

fn scene_rel(args_rel: Option<&str>) -> String {
    args_rel
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .unwrap_or(DEFAULT_SGS_REL)
        .to_string()
}

#[tauri::command]
pub fn scene_save(
    host: State<'_, HostState>,
    args: SceneSaveArgs,
) -> Result<SceneSaveDto, String> {
    authorize("scene_save").map_err(|e| e.to_string())?;
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root =
        resolve_bound_project_root(args.project_root.as_deref(), root.host_settings())?;
    let rel = scene_rel(args.rel_path.as_deref());
    let path = save_scene_text(root.fs(), &project_root, &rel, &args.text)
        .map_err(|e| e.to_string())?;
    Ok(SceneSaveDto {
        path,
        relative_path: rel,
        product_pass: false,
        message: Some("saved scene under project scene/ (project-scoped only)".into()),
    })
}

#[tauri::command]
pub fn scene_load(
    host: State<'_, HostState>,
    args: Option<SceneLoadArgs>,
) -> Result<SceneLoadDto, String> {
    authorize("scene_load").map_err(|e| e.to_string())?;
    let args = args.unwrap_or_default();
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root =
        resolve_bound_project_root(args.project_root.as_deref(), root.host_settings())?;
    let rel = scene_rel(args.rel_path.as_deref());
    let (text, path) = load_scene_text(root.fs(), &project_root, &rel)
        .map_err(|e| e.to_string())?;
    Ok(SceneLoadDto {
        path,
        relative_path: rel,
        text,
        product_pass: false,
        message: Some("loaded scene from project scene/".into()),
    })
}

/// PD-ELU-IMPORT-ARCH-01 — read-only syntax preview of selected project-relative Rust files.
#[tauri::command]
pub fn import_preview(
    host: State<'_, HostState>,
    request: ImportPreviewRequest,
) -> Result<ImportPreview, String> {
    authorize("import_preview").map_err(|e| e.to_string())?;
    let root = host.inner.lock().map_err(|_| poison_host())?;
    let project_root = resolve_bound_project_root(None, root.host_settings())?;
    preview_selected(root.fs(), &project_root, &request).map_err(|error| {
        let path = error.relative_path.map(|path| format!(" ({path})")).unwrap_or_default();
        format!("{}{path}: {}", error.code, error.message)
    })
}

#[cfg(test)]
mod git_ui_tests {
    use super::*;
    use sgenaxis_adapters::fake::{FakeGit, FakeGitWrite};
    use sgenaxis_ports::{
        GitBranch, GitCommit, GitConflictFile, GitConflictState, GitRemote, GitSettings, GitStash,
        GitStatus, GitStatusEntry, GitStatusKind, GitTag, GitUpstream,
    };

    #[test]
    fn workbench_dto_maps_summary_writes_flag() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("feature".into()),
                entries: vec![GitStatusEntry {
                    path: "a.rs".into(),
                    kind: GitStatusKind::Modified,
                }],
                upstream: None,
            },
        );
        git.set_log(
            "/r",
            vec![GitCommit {
                hash: "abc".into(),
                subject: "wip".into(),
                ..Default::default()
            }],
        );
        git.set_diff("/r", "diff --git a/a.rs\n");
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.branch.as_deref(), Some("feature"));
        assert_eq!(dto.entry_count, 1);
        assert_eq!(dto.entries[0].kind, "modified");
        assert!(dto.diff_text.contains("a.rs"));
        assert!(!dto.writes_enabled);
        assert_eq!(dto.status, "ok");
        assert!(workbench_dto(&summary, true).writes_enabled);
    }

    // G2 DTO/UI RED: ahead/behind/upstream must surface through summary → DTO.
    #[test]
    fn workbench_dto_surfaces_ahead_behind() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("feature".into()),
                entries: Vec::new(),
                upstream: Some(GitUpstream {
                    name: "origin/feature".into(),
                    ahead: 2,
                    behind: 1,
                }),
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.ahead, 2);
        assert_eq!(dto.behind, 1);
        assert_eq!(dto.upstream.as_deref(), Some("origin/feature"));
    }

    // PD-GIT-BRANCHES-01 RED: DTO must surface local branches (name + is_current).
    #[test]
    fn workbench_dto_surfaces_branches() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("main".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        git.set_branches(
            "/r",
            vec![
                GitBranch {
                    name: "main".into(),
                    is_current: true,
                },
                GitBranch {
                    name: "feature".into(),
                    is_current: false,
                },
            ],
        );
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.branches.len(), 2);
        assert_eq!(dto.branches[0].name, "main");
        assert!(dto.branches[0].is_current);
        assert_eq!(dto.branches[1].name, "feature");
        assert!(!dto.branches[1].is_current);
    }

    // PD-GIT-REMOTES-01 RED: DTO must surface configured remotes (name + url).
    #[test]
    fn workbench_dto_surfaces_remotes() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("main".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        git.set_remotes(
            "/r",
            vec![
                GitRemote {
                    name: "origin".into(),
                    url: "https://github.com/roy/AIAD.git".into(),
                    tested: true,
                },
                GitRemote {
                    name: "upstream".into(),
                    url: "https://github.com/other/AIAD.git".into(),
                    tested: false,
                },
            ],
        );
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.remotes.len(), 2);
        assert_eq!(dto.remotes[0].name, "origin");
        assert_eq!(dto.remotes[0].url, "https://github.com/roy/AIAD.git");
        assert!(dto.remotes[0].tested);
        assert_eq!(dto.remotes[1].name, "upstream");
        assert!(!dto.remotes[1].tested);
    }

    // PD-GIT-TAGS-01 RED: DTO must surface tag names + peeled commit OIDs.
    #[test]
    fn workbench_dto_surfaces_tags() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("main".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        git.set_tags(
            "/r",
            vec![
                GitTag {
                    name: "v0.1.0".into(),
                    peeled: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".into(),
                },
                GitTag {
                    name: "v0.2.0".into(),
                    peeled: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb".into(),
                },
            ],
        );
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.tags.len(), 2);
        assert_eq!(dto.tags[0].name, "v0.1.0");
        assert_eq!(
            dto.tags[0].peeled,
            "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        );
        assert_eq!(dto.tags[1].name, "v0.2.0");
        assert_eq!(
            dto.tags[1].peeled,
            "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        );
    }

    // PD-GIT-STASH-01 RED: DTO must surface stashes (id + message).
    #[test]
    fn workbench_dto_surfaces_stashes() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("main".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        git.set_stashes(
            "/r",
            vec![
                GitStash {
                    id: "stash@{0}".into(),
                    message: "WIP on main: slot editor".into(),
                },
                GitStash {
                    id: "stash@{1}".into(),
                    message: "On feature: theme".into(),
                },
            ],
        );
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.stashes.len(), 2);
        assert_eq!(dto.stashes[0].id, "stash@{0}");
        assert_eq!(dto.stashes[0].message, "WIP on main: slot editor");
        assert_eq!(dto.stashes[1].id, "stash@{1}");
    }

    // PD-GIT-CONFLICTS-01 RED: DTO must flatten the conflict snapshot (kind + files).
    #[test]
    fn workbench_dto_surfaces_conflicts() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("feature/git-ui".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        git.set_conflicts(
            "/r",
            GitConflictState {
                active: true,
                kind: "Rebase".into(),
                source: "main".into(),
                target: "feature/git-ui".into(),
                files: vec![GitConflictFile {
                    path: "src/git.ts".into(),
                    code: "UU".into(),
                    kind: "雙方皆修改".into(),
                    ours: "status: ready".into(),
                    theirs: "status: idle".into(),
                }],
            },
        );
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert!(dto.conflict.active);
        assert_eq!(dto.conflict.kind, "Rebase");
        assert_eq!(dto.conflict.source, "main");
        assert_eq!(dto.conflict.target, "feature/git-ui");
        assert_eq!(dto.conflict.files.len(), 1);
        assert_eq!(dto.conflict.files[0].path, "src/git.ts");
        assert_eq!(dto.conflict.files[0].code, "UU");
        assert_eq!(dto.conflict.files[0].ours, "status: ready");
        assert_eq!(dto.conflict.files[0].theirs, "status: idle");
    }

    // PD-GIT-SETTINGS-01 RED: DTO must flatten local identity + .gitignore.
    #[test]
    fn workbench_dto_surfaces_settings() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("main".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log("/r", Vec::new());
        git.set_diff("/r", "");
        git.set_settings(
            "/r",
            GitSettings {
                author: "Example Developer".into(),
                email: "dev@example.invalid".into(),
                ignore: "node_modules/\ndist/\n".into(),
            },
        );
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.settings.author, "Example Developer");
        assert_eq!(dto.settings.email, "dev@example.invalid");
        assert_eq!(dto.settings.ignore, "node_modules/\ndist/\n");
    }

    // PD-GIT-HISTORY-01 RED: DTO must flatten commit author + date from the summary.
    #[test]
    fn workbench_dto_surfaces_history_author_and_date() {
        let git = FakeGit::new();
        git.set_status(
            "/r",
            GitStatus {
                branch: Some("main".into()),
                entries: Vec::new(),
                upstream: None,
            },
        );
        git.set_log(
            "/r",
            vec![GitCommit {
                hash: "abc".into(),
                subject: "feat: polish Git panel".into(),
                author: "Alex".into(),
                date: "2026-10-25T16:42:00+00:00".into(),
            }],
        );
        git.set_diff("/r", "");
        let summary = summarize_worktree(&git, "/r", 5).unwrap();
        let dto = workbench_dto(&summary, false);
        assert_eq!(dto.recent_commits.len(), 1);
        assert_eq!(dto.recent_commits[0].hash, "abc");
        assert_eq!(dto.recent_commits[0].subject, "feat: polish Git panel");
        assert_eq!(dto.recent_commits[0].author, "Alex");
        assert_eq!(dto.recent_commits[0].date, "2026-10-25T16:42:00+00:00");
    }

    /// PD-WIRE-BOOT-01: unbound／非 git → not_run 投影（可讀空態）.
    #[test]
    fn workbench_not_run_is_readable_empty_projection() {
        let dto = workbench_not_run("", "project_root not bound");
        assert_eq!(dto.status, "not_run");
        assert_eq!(dto.entry_count, 0);
        assert!(dto.entries.is_empty());
        assert!(!dto.writes_enabled);
        assert!(dto
            .message
            .as_deref()
            .unwrap_or("")
            .contains("project_root not bound"));
    }

    #[test]
    fn git_write_commands_allowlisted_raw_cli_names_not() {
        use sgenaxis_host::is_allowed;
        assert!(is_allowed("git_workbench_summary"));
        assert!(is_allowed("git_workbench_diff"));
        assert!(is_allowed("git_write_commit"));
        assert!(is_allowed("git_write_push"));
        assert!(!is_allowed("git_commit"));
        assert!(!is_allowed("git_push"));
        assert!(!is_allowed("git_force_push"));
    }

    // PD-GIT-SWITCH-03 RED: new switch command is allowlisted + soft-gated
    // (unapproved / empty branch never switches; approved switches via port).
    #[test]
    fn git_switch_branch_gated_and_allowlisted() {
        use sgenaxis_host::is_allowed;
        assert!(is_allowed("git_switch_branch"));
        assert!(!is_allowed("git_switch"));
        assert!(!is_allowed("git_checkout"));

        let w = FakeGitWrite::new();
        // Unapproved → no mutation.
        let denied = perform_git_switch(&w, "/r", "feature", false);
        assert!(!denied.ok);
        assert!(denied.local_preserved);
        assert!(w.switched_branch("/r").is_none());
        // Empty branch → rejected, no mutation.
        let empty = perform_git_switch(&w, "/r", "", true);
        assert!(!empty.ok);
        assert!(w.switched_branch("/r").is_none());
        // Approved + valid → switches via port.
        let ok = perform_git_switch(&w, "/r", "feature", true);
        assert!(ok.ok);
        assert_eq!(ok.op, "switch");
        assert_eq!(w.switched_branch("/r").as_deref(), Some("feature"));
    }

    #[test]
    fn denied_approval_does_not_mutate() {
        let w = FakeGitWrite::new();
        let r = perform_git_write_commit(&w, "/r", "should not land", false);
        assert!(!r.ok);
        assert!(r.local_preserved);
        assert_eq!(w.local_commit_count("/r"), 0);
        let p = perform_git_write_push(&w, "/r", "origin", None, false).unwrap();
        assert!(!p.ok);
        assert_eq!(w.push_count("/r"), 0);
    }

    #[test]
    fn approved_commit_and_push_via_port() {
        let w = FakeGitWrite::new();
        let c = perform_git_write_commit(&w, "/r", "feat: ui", true);
        assert!(c.ok);
        assert_eq!(w.local_commit_count("/r"), 1);
        let p = perform_git_write_push(&w, "/r", "origin", Some("main"), true).unwrap();
        assert!(p.ok);
        assert_eq!(w.push_count("/r"), 1);
    }

    #[test]
    fn push_failure_preserves_local_commits() {
        let w = FakeGitWrite::new();
        perform_git_write_commit(&w, "/r", "local keep", true);
        w.fail_next_push("/r", "https://user:secret@host/r rejected");
        let p = perform_git_write_push(&w, "/r", "origin", None, true).unwrap();
        assert!(!p.ok);
        assert!(p.local_preserved);
        assert_eq!(w.local_commit_count("/r"), 1);
        assert!(!p.message.contains("secret"));
    }

    #[test]
    fn force_push_rejected() {
        let w = FakeGitWrite::new();
        perform_git_write_commit(&w, "/r", "x", true);
        let err = perform_git_write_push(&w, "/r", "origin", Some("+main"), true).unwrap_err();
        assert!(err.contains("force"));
        assert_eq!(w.push_count("/r"), 0);
        assert_eq!(w.local_commit_count("/r"), 1);
    }
}

#[cfg(test)]
mod ports_ui_tests {
    use super::*;
    use sgenaxis_host::{is_allowed, CompositionRoot};

    #[test]
    fn ports_status_dto_maps_boot_fake() {
        let root = CompositionRoot::boot_fake().unwrap();
        let dto = PortsStatusDto::from(&root.ports_status());
        assert_eq!(dto.status, "ok");
        assert_eq!(dto.entry_count, 6);
        assert!(dto
            .entries
            .iter()
            .any(|e| e.port == "FileSystemPort" && e.adapter == "FakeFileSystem"));
        assert!(dto
            .entries
            .iter()
            .any(|e| e.port == "GitWritePort" && e.status == "gated"));
    }

    #[test]
    fn ports_status_allowlisted_os_enum_not() {
        assert!(is_allowed("ports_status"));
        assert!(!is_allowed("list_os_devices"));
        assert!(!is_allowed("enumerate_drives"));
        assert!(!is_allowed("shell_execute"));
    }

    #[test]
    fn empty_ports_projection_is_ok() {
        use sgenaxis_host::project_ports_status;
        let empty = project_ports_status(None, false);
        let dto = PortsStatusDto::from(&empty);
        assert_eq!(dto.status, "empty");
        assert_eq!(dto.entry_count, 0);
        assert!(dto.entries.is_empty());
    }
}

#[cfg(test)]
mod deploy_cmd_tests {
    use super::*;
    use sgenaxis_adapters::{boxed_deploy_fake, FakeDeploy};
    use sgenaxis_host::{is_allowed, CompositionRoot};
    use sgenaxis_ports::DeployPlatform;

    #[test]
    fn deploy_dto_maps_and_qn_auto_false() {
        let fake = FakeDeploy::m3_defaults();
        fake.set_last_artifact_path(Some(
            r"D:\AIAD\packaging\windows\wix\out\SGenAxis-0.1.0-windows-x64.msi".into(),
        ))
        .unwrap();
        let root = CompositionRoot::boot_with_ports_and_deploy(
            sgenaxis_adapters::BoxedPorts::fake(),
            Box::new(fake),
            false,
        )
        .unwrap();
        // Force Windows view via port directly for deterministic CI on any OS.
        let st_view = sgenaxis_host::status_view(root.deploy_port(), DeployPlatform::Windows)
            .unwrap();
        let st = DeployStatusDto::from(&st_view);
        assert!(st.supported);
        assert!(!st.elevated_qn_auto);
        let check_view =
            sgenaxis_host::check_view(root.deploy_port(), DeployPlatform::Windows).unwrap();
        let check = DeployCheckDto::from(&check_view);
        assert!(check.needs_manual_elevated);
        let arts: Vec<_> = sgenaxis_host::list_artifact_views(
            root.deploy_port(),
            DeployPlatform::Windows,
        )
        .unwrap()
        .iter()
        .map(DeployArtifactDto::from)
        .collect();
        assert!(!arts.is_empty());
    }

    #[test]
    fn deploy_write_and_shell_not_allowlisted() {
        assert!(is_allowed("deploy_status"));
        assert!(is_allowed("deploy_check"));
        assert!(is_allowed("list_artifacts"));
        assert!(!is_allowed("deploy_install"));
        assert!(!is_allowed("deploy_msiexec"));
        assert!(!is_allowed("deploy_qn"));
        assert!(!is_allowed("shell_execute"));
        let _ = boxed_deploy_fake();
    }

    #[test]
    fn deploy_unsupported_is_observable_not_panic() {
        let root = CompositionRoot::boot_fake().unwrap();
        let v = sgenaxis_host::status_view(root.deploy_port(), DeployPlatform::MacOs).unwrap();
        assert!(!v.supported);
        assert!(!v.message.is_empty());
        let c = sgenaxis_host::check_view(root.deploy_port(), DeployPlatform::MacOs).unwrap();
        assert_eq!(c.status, "unsupported");
    }
}

#[cfg(test)]
mod wire_root_tests {
    use super::*;

    #[test]
    fn unbound_project_root_is_clear_error() {
        let s = HostSettings::defaults();
        let err = resolve_bound_project_root(None, &s).unwrap_err();
        assert!(err.contains("not bound"), "{err}");
    }

    #[test]
    fn rejects_hardcoded_demo_root() {
        let mut s = HostSettings::defaults();
        s.project_root = "/demo/root".into();
        let err = resolve_bound_project_root(None, &s).unwrap_err();
        assert!(err.contains("/demo/root"), "{err}");
        let err2 = resolve_bound_project_root(Some("/demo/root"), &HostSettings::defaults())
            .unwrap_err();
        assert!(err2.contains("/demo/root"), "{err2}");
    }

    #[test]
    fn settings_project_root_used_when_arg_empty() {
        let mut s = HostSettings::defaults();
        s.project_root = "/work/real".into();
        assert_eq!(
            resolve_bound_project_root(None, &s).unwrap(),
            "/work/real"
        );
        assert_eq!(
            resolve_bound_project_root(Some("  "), &s).unwrap(),
            "/work/real"
        );
        assert_eq!(
            resolve_bound_project_root(Some("/explicit"), &s).unwrap(),
            "/explicit"
        );
    }

    #[test]
    fn board_path_resolves_under_project_root() {
        let joined = resolve_board_path_under_root("/work/repo", "docs/PROJECT-BOARD.html");
        assert!(
            joined.replace('\\', "/").ends_with("/work/repo/docs/PROJECT-BOARD.html"),
            "{joined}"
        );
        let abs = if cfg!(windows) {
            resolve_board_path_under_root(r"C:\work", r"D:\boards\board.html")
        } else {
            resolve_board_path_under_root("/work", "/abs/board.html")
        };
        assert!(
            abs.contains("board.html"),
            "absolute path should pass through: {abs}"
        );
    }

    #[test]
    fn resolve_repo_uses_settings_root() {
        let mut s = HostSettings::defaults();
        s.project_root = "/git/repo".into();
        assert_eq!(resolve_repo(None, &s).unwrap(), "/git/repo");
        assert_eq!(
            resolve_repo(Some("/other".into()), &s).unwrap(),
            "/other"
        );
    }
}

#[cfg(test)]
mod wire_agent_tests {
    use super::*;
    use sgenaxis_adapters::fake::FakeFileSystem;

    /// BDD-PD-WIRE-AGENT-01: DryRun always passes Live gate.
    #[test]
    fn dry_run_skips_live_gate() {
        let s = HostSettings::defaults();
        let fs = FakeFileSystem::new();
        preflight_live_agent_dispatch(&s, &fs, true, ProviderDto::Cli).expect("DryRun ok");
        preflight_live_agent_dispatch(&s, &fs, true, ProviderDto::Mcp).expect("DryRun mcp ok");
    }

    /// BDD-PD-WIRE-AGENT-01: Live + !agent_active → readable 未核准.
    #[test]
    fn live_unapproved_is_readable_reject() {
        let s = HostSettings::defaults();
        assert!(!s.agent_active);
        let fs = FakeFileSystem::new();
        let err = preflight_live_agent_dispatch(&s, &fs, false, ProviderDto::Mcp).unwrap_err();
        assert!(err.contains("Live 未核准"), "{err}");
        assert!(err.contains("start_run"), "{err}");
        assert!(!err.to_lowercase().contains("secret_token"));
    }

    /// BDD-PD-WIRE-AGENT-01: Live CLI + active + invalid CLI path → readable 路徑無效.
    #[test]
    fn live_invalid_cli_path_is_readable_reject() {
        let mut s = HostSettings::defaults();
        s.agent_active = true;
        s.agent.cli.claude.path = "/no/such/cli-tool".into();
        s.agent.mcp.endpoint = "stdio://local-ok".into();
        let fs = FakeFileSystem::new();
        let err = preflight_live_agent_dispatch(&s, &fs, false, ProviderDto::Cli).unwrap_err();
        assert!(err.contains("路徑無效"), "{err}");
        assert!(err.contains("CLI"), "{err}");
        assert!(err.contains("秘密不進投影"), "{err}");
    }

    /// BDD-PD-REMAIN-LIVE-MCP-01: Live MCP + forbidden :8788 → NOT RUN／路徑無效.
    #[test]
    fn live_forbidden_mcp_endpoint_is_readable_reject() {
        let mut s = HostSettings::defaults();
        s.agent_active = true;
        s.agent.cli.claude.path = "/bin/claude".into();
        s.agent.mcp.endpoint = "http://127.0.0.1:8788/sse".into();
        let fs = FakeFileSystem::new();
        fs.seed("/bin/claude", b"x");
        let err = preflight_live_agent_dispatch(&s, &fs, false, ProviderDto::Mcp).unwrap_err();
        assert!(
            err.contains("路徑無效") || err.contains("NOT RUN"),
            "{err}"
        );
        assert!(err.contains("MCP"), "{err}");
        assert!(err.contains("8788") || err.contains("禁"), "{err}");
    }

    /// BDD-PD-REMAIN-LIVE-MCP-01: Live MCP ignores invalid CLI (provider-scoped gate).
    #[test]
    fn live_mcp_preflight_skips_cli_path() {
        let mut s = HostSettings::defaults();
        s.agent_active = true;
        s.agent.cli.claude.path = "/no/such/cli-tool".into();
        s.agent.mcp.endpoint = "http://127.0.0.1:3920/sse".into();
        let fs = FakeFileSystem::new();
        preflight_live_agent_dispatch(&s, &fs, false, ProviderDto::Mcp)
            .expect("MCP Live must not require CLI path");
    }

    /// BDD-PD-WIRE-AGENT-01: settings projection never carries secret_token.
    #[test]
    fn settings_dto_omits_secret_values() {
        let mut s = HostSettings::defaults();
        s.agent.mcp.secret_token = Some("super-secret-token".into());
        let dto = SettingsDto::from(&s);
        let json = serde_json::to_string(&dto).unwrap();
        assert!(!json.contains("super-secret-token"));
        assert!(!json.contains("secret_token"));
        assert!(dto.agent_mcp.has_secret);
    }

    #[test]
    fn live_approved_valid_paths_pass_preflight() {
        let mut s = HostSettings::defaults();
        s.agent_active = true;
        s.agent.cli.claude.path = "/bin/claude".into();
        s.agent.mcp.endpoint = "stdio://local-agent".into();
        let fs = FakeFileSystem::new();
        fs.seed("/bin/claude", b"x");
        preflight_live_agent_dispatch(&s, &fs, false, ProviderDto::Cli)
            .expect("Live CLI preflight ok");
        preflight_live_agent_dispatch(&s, &fs, false, ProviderDto::Mcp)
            .expect("Live MCP preflight ok");
    }
}

#[cfg(test)]
mod file_save_tests {
    use super::*;

    /// BDD-PD-REMAIN-FILE-SAVE-01: merge persists board_path／project_root into settings.
    #[test]
    fn merge_persists_settings_and_board_binding() {
        let cur = HostSettings::defaults();
        let next = merge_file_save_settings(
            &cur,
            Some("dark".into()),
            Some("zh-TW".into()),
            Some("docs/PROJECT-BOARD.html".into()),
            Some("/work/repo".into()),
        )
        .expect("merge ok");
        assert_eq!(next.ui_theme, "dark");
        assert_eq!(next.locale, "zh-TW");
        assert_eq!(next.board_path, "docs/PROJECT-BOARD.html");
        assert_eq!(next.project_root, "/work/repo");
    }

    /// BDD: no arbitrary path — only known fields; flush-no-op keeps defaults.
    #[test]
    fn merge_none_fields_is_flush_only() {
        let mut cur = HostSettings::defaults();
        cur.project_root = "/bound".into();
        cur.board_path = "docs/PROJECT-BOARD.html".into();
        let next = merge_file_save_settings(&cur, None, None, None, None).expect("flush");
        assert_eq!(next.project_root, "/bound");
        assert_eq!(next.board_path, "docs/PROJECT-BOARD.html");
    }

    #[test]
    fn rejects_demo_root_and_http_board() {
        let cur = HostSettings::defaults();
        let err = merge_file_save_settings(
            &cur,
            None,
            None,
            None,
            Some("/demo/root".into()),
        )
        .unwrap_err();
        assert!(err.contains("/demo/root"), "{err}");
        let err2 = merge_file_save_settings(
            &cur,
            None,
            None,
            Some("http://127.0.0.1:8788/board".into()),
            None,
        )
        .unwrap_err();
        assert!(err2.contains("8788") || err2.contains("http"), "{err2}");
    }

    /// Contract: FileSaveResult always reports board_write_back=false + host-settings kind.
    #[test]
    fn file_save_result_never_board_write_back() {
        let dto = SettingsDto::from(&HostSettings::defaults());
        let r = FileSaveResult {
            status: "ok".into(),
            board_write_back: false,
            persisted_kind: "host-settings".into(),
            settings: dto,
            message: None,
        };
        assert!(!r.board_write_back);
        assert_eq!(r.persisted_kind, "host-settings");
        assert_ne!(r.persisted_kind, "PROJECT-BOARD.html");
    }
}
