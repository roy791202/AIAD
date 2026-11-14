//! SGenAxis **HOST** (PD-HOST-01 + PD-BOARD-LIVE-01 + PD-DEPLOY-CMD-01 + PD-GUARD-CMD-01
//! + PD-GIT-BOARD-SYNC-01)
//! — lifecycle, settings, restricted IPC, read-only local board／deploy, GUARD façade,
//! Git↔board read isolation.
//!
//! - [`AppLifecycle`] — start／close phases (no business state)
//! - [`SettingsStore`] — persistent host prefs via [`FileSystemPort`]
//! - [`AllowedIpcCommand`] — allowlist; **no** arbitrary shell
//! - [`CompositionRoot`] — wires Ports at boot
//! - [`board_live`] — parse `#board-snapshot` from local HTML／JSON（no :8788）
//! - [`git_board_sync`] — Git summary ↔ board snapshot isolation assertions
//! - [`deploy`] — façade over [`sgenaxis_ports::DeployPort`]（status／check／list_artifacts）
//! - [`ports_view`] — registered Port／adapter status projection (PD-REMAIN-PORTS-UI-01)
//! - [`guard_cmd`] — start_implementation／change-path gate → `CODE:detail` (PD-GUARD-CMD-01)
//!
//! Tauri command closures in `src-tauri` must stay thin and call into this crate.

#![forbid(unsafe_code)]

pub mod board_live;
pub mod composition;
pub mod deploy;
pub mod error;
pub mod git_board_sync;
pub mod git_hunk_unstage;
pub mod git_remote_rename;
pub mod git_rename;
pub mod git_set_upstream;
pub mod git_stage_all;
pub mod git_switch;
pub mod git_tag_push;
pub mod git_unset_upstream;
pub mod git_unstage_all;
pub mod guard_cmd;
pub mod identity_preview;
pub mod ipc;
pub mod lifecycle;
pub mod module_packet;
pub mod packet_admission;
pub mod ports_view;
pub mod project_manifest;
pub mod project_new;
pub mod project_preferences;
pub mod scene_doc;
pub mod settings;
pub mod uidesign_doc;

pub use board_live::{
    extract_snapshot_json, load_board_file, parse_board_snapshot, BoardSnapshot, SnapshotTask,
};
pub use composition::{CompositionRoot, APP_NAME};
pub use deploy::{
    check_view, default_workspace_root, find_workspace_root, focus_platform, list_artifact_views,
    platform_label, status_view, DeployArtifactView, DeployCheckView, DeployStatusView,
};
pub use error::HostError;
pub use git_board_sync::{
    load_git_and_board_isolated, GitBoardSyncViews, SyncFailKind, SyncReadOrder,
};
pub use git_hunk_unstage::{perform_git_hunk_unstage, GitHunkUnstageResult};
pub use git_remote_rename::{perform_git_rename_remote, GitRemoteRenameResult};
pub use git_rename::{perform_git_rename_branch, GitRenameResult};
pub use git_set_upstream::{perform_git_set_upstream, GitSetUpstreamResult};
pub use git_stage_all::{perform_git_stage_all, GitStageAllResult};
pub use git_switch::{
    occupying_run_id, perform_git_switch, GitSwitchResult, ACTIVE_LEASE_BLOCKS_SWITCH,
};
pub use git_tag_push::{perform_git_push_tag, GitTagPushResult};
pub use git_unset_upstream::{perform_git_unset_upstream, GitUnsetUpstreamResult};
pub use git_unstage_all::{perform_git_unstage_all, GitUnstageAllResult};
pub use guard_cmd::{
    authorize_exec_start, authorize_write_paths, check_changes_view, check_implementation_view,
    check_start_view, EnvelopeDto, GuardDecisionView, GuardExecPass, GuardPacketDto, RedKindDto,
};
pub use ipc::{authorize, is_allowed, reject_if_shell, AllowedIpcCommand};
pub use lifecycle::{AppLifecycle, LifecyclePhase};
pub use ports_view::{project_ports_status, PortAdapterLabels, PortBindingView, PortsStatusView};
pub use project_manifest::{
    adopt_project_document, DocumentAdoptionOutcome, ProjectManifestStoreError,
};
pub use project_new::{
    create_new_project_root, create_new_project_under, join_new_project_path,
    normalize_new_project_path, normalize_project_folder_name,
};
pub use scene_doc::{
    load_scene_text, normalize_scene_rel, save_scene_text, scene_file_exists, DEFAULT_SGML_REL,
    DEFAULT_SGS_REL, DEFAULT_SGUI_REL, DEFAULT_SG_REL, SCENE_DIR,
};
pub use settings::{
    HostSettings, SettingsStore, DEFAULT_BOARD_PATH_HINT, HOST_SETTINGS_FILE, HOST_SETTINGS_VERSION,
};
pub use uidesign_doc::{
    ask_agent_draft, build_preview_file, build_preview_html, load_design_file, parse_design_json,
    save_design_file, serialize_design, DesignDoc, DesignMeta, DesignNode, DEFAULT_REL_PATH,
    DESIGN_FORMAT, DESIGN_FORMAT_VERSION, PREVIEW_BANNER,
};
// Live CLI probe types re-exported from exec (PD-LIVE-TARGET-01 consumers).
pub use sgenaxis_exec::{
    LiveTargetProbeResult, LIVE_TARGET_STATUS_NOT_RUN, LIVE_TARGET_STATUS_PASS,
};

/// M01-S2 local definition persistence boundary.
pub mod project_definition;

/// M01-S3 wizard command bridge — step-wise lifecycle over the S2 domain.
pub mod project_wizard;
