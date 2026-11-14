//! PD-CMD-01 command façade — UI → Core／EXEC; Ports only at the outer seam.
//! PD-REMAIN-LIVE-SPAWN-01 — Live CLI: start_run → DispatchHost → EXEC → StdProcess.
//! PD-EVID-UI-01 — read-only evidence summary projection for Inspector.
//! PD-SPEC-UI-01 — ModuleSpec／契約唯讀投影；核准版不可原地改（REPLAN）；revise 另入口。
//! PD-REMAIN-ARCH-UI-01 — module／dependency architecture projection via Command.
//! PD-REMAIN-WORK-TAGS-01 — batch BDD／TDD tags via Command → WORK／board projection.
//! PD-REMAIN-LISTEN-UI-01 — FS／Git／Agent listen → EventBridge → ListenProjection via Command.
//! PD-GUARD-CMD-01 — GUARD gate before start_implementation／optional start_run guard.
//! PD-FLOW-EVID-GATE-01 — Accept／Complete require EVID+FLOW; Provider done ≠ green.
//! PD-REMAIN-LIVE-MCP-01 — Live MCP via Command→DispatchHost (not DryRun-only);
//!   ban `:8788`／`:8787`; empty target → NOT RUN.
//! PD-REMAIN-EDIT-01 — Edit selection／history via Core [`EditSession`] (path C).
//!
//! Tauri `#[command]` handlers call into [`DispatchHost`]. Unit tests exercise
//! this module without WebView／IPC. UI never calls adapters directly.

use std::collections::BTreeMap;
use std::sync::Arc;
use std::time::Duration;

use sgenaxis_adapters::{FakeProcess, StdFileSystem, StdGitIndexCommit, StdProcess};
use sgenaxis_core::{
    EditError, EditSession, Engine, FlowError, FlowEvent, PropertyId, TaskFlow, Zone,
};
use sgenaxis_evid::{
    evidence_allows_flow_accept_or_complete, evidence_gaps, evaluate_ready_for_green,
    project_inspector_evidence, CaseResult, EvidenceStore, ProviderTerminal, RunCapture,
    VersionBinding, EVIDENCE_GAP_LAMP_HINT,
};
use sgenaxis_exec::{
    is_mcp_endpoint_activatable, require_run_binding, AgentChunk, AgentPort, AgentProvider,
    AgentRouter, CliAgentAdapter, CliAgentSettings, ExecError, ExitClassification,
    McpAgentAdapter, McpAgentSettings, OutputStream, RunId, StartRunRequest, StubMcpClient,
};
use sgenaxis_ports::{
    Cleanup, GitIndexCommitPort, InteractiveError, InteractiveFixturePort, InteractiveId,
    InteractiveObservation, FileSystemPort, InteractiveSize, PortError, ProcessPort, ReadState,
};
use sgenaxis_host::{
    authorize_exec_start, authorize_write_paths, check_changes_view, check_start_view,
    occupying_run_id, GuardDecisionView, GuardExecPass, GuardPacketDto,
};
use sgenaxis_listen::{EventBridge, ListenProjection, SourceEvent};
use sgenaxis_spec::{ApprovalStatus, Contract, EvidenceValidity, SpecError, SpecStore};
use sgenaxis_work::{FakePathProbe, FakeWorkspaceStore, WorkspaceService};

use crate::dto::{
    ArchEdgeDto, ArchModuleDto, ArchProjectionDto, BatchWorkTagsArgs, BoardView, CandidateDraft, ChunkDto,
    CommandDescriptor, EditProjectionDto, EvidenceSummaryDto, EvidenceSummaryLineDto,
    ListenProjectionDto, PollResult, ProviderDto, SpecApproveArgs, SpecContractDto,
    SpecEvidenceRefDto, SpecGetRevisionArgs, SpecProjectionDto, SpecReviseArgs, SpecRevisionDto,
    SpecRevisionSummaryDto, SpecTrySetContractArgs, StartImplementationArgs, StartRunArgs,
    StartRunResult, TaskView, UpsertTaskArgs, ZoneDto, ZoneTitles,
};
use crate::git_index_commit::IndexCommitCoordinator;

/// Sample ModuleSpec fixture (same bytes as sgenaxis-spec unit tests).
const SAMPLE_MODULE_SPEC: &str =
    include_str!("../../crates/sgenaxis-spec/fixtures/sample_module_spec.json");

/// Host-side dispatch state: Core engine + EXEC router (DryRun adapters) + EVID + SPEC + WORK.
pub struct DispatchHost {
    engine: Engine,
    exec: AgentRouter,
    /// WORK registry + execution leases (PD-EXEC-BIND-01／PD-WORK-01).
    work: WorkspaceService<FakePathProbe, FakeWorkspaceStore>,
    /// GUARD F-A exact-byte input reads, owned by the application host.
    #[allow(dead_code)]
    guard_input_fs: Box<dyn FileSystemPort>,
    /// GUARD R-A owns a separate ProcessPort; it never borrows EXEC's active child.
    #[allow(dead_code)]
    guard_red_process: Box<dyn ProcessPort>,
    /// Retains exact child ownership when cancellation/drain remains unresolved.
    #[allow(dead_code)]
    guard_capture_process: Option<GuardCaptureProcessSlot>,
    guard_next_capture_id: u64,
    /// Work item bound to the in-flight run (for zone projection updates).
    active_work_item: Option<String>,
    /// Project id holding the active Run lease (released on exit).
    active_lease_project: Option<String>,
    /// PD-EXEC-SINGLE-01: the single in-flight Run id (mirrored into BoardView).
    active_run_id: Option<u64>,
    /// Immutable evidence store (UI reads only via [`Self::get_evidence_summary`]).
    evid: EvidenceStore,
    /// Current spec／worktree binding for green gate.
    evid_binding: VersionBinding,
    /// work_item_id → required BDD ids (empty → Inspector shows NOT RUN).
    required_bdd: BTreeMap<String, Vec<String>>,
    /// work_item_id → TDD tag ids (PD-REMAIN-WORK-TAGS-01 board projection).
    required_tdd: BTreeMap<String, Vec<String>>,
    /// Last Provider terminal per work item (Success ≠ product green).
    provider_by_work: BTreeMap<String, ProviderTerminal>,
    /// FLOW lamp SM per work item (PD-FLOW-01／PD-FLOW-EVID-GATE-01).
    flows: BTreeMap<String, TaskFlow>,
    /// ModuleSpec store (PD-SPEC-UI-01); empty until `spec_load_fixture`.
    spec: SpecStore,
    /// Whether a ModuleSpec document is loaded.
    spec_loaded: bool,
    /// PD-GUARD-CMD-01／EXEC-BIND seam: last GUARD pass (consumed on EXEC start).
    guard_pass: Option<GuardExecPass>,
    /// PD-REMAIN-LISTEN-UI-01: adapter events → debounce → domain／Dirty.
    listen: EventBridge,
    /// UI-facing listen snapshot (never raw OS／adapter events).
    listen_proj: ListenProjection,
    /// PD-REMAIN-EDIT-01: domain selection／history (board task ids as universe).
    edit: EditSession,
    /// GUARD-S1 private session authority ownership (pure policy; no native／ACL proof).
    #[allow(dead_code)]
    guard_authority: GuardSessionState,
    /// Candidate records and task intent are private to this DispatchHost session.
    guard_candidates: BTreeMap<u64, GuardCandidateRecord>,
    guard_next_candidate: u64,
    guard_intents: BTreeMap<String, GuardHostIntent>,
    /// HOST-owned one-use staged-Index preview / confirm coordinator (A1 only).
    git_index_commit: Arc<IndexCommitCoordinator>,
}

impl Default for DispatchHost {
    fn default() -> Self {
        Self::new()
    }
}

/// Host-local session seed for opaque u64 Guard references. The monotonic
/// per-host counter is checked; no process-global authority counter is used.
fn guard_session_nonce() -> u64 {
    // Candidate refs cross Tauri's JSON boundary into JavaScript Number. Keep
    // them in its exact integer range. UUID entropy seeds each HOST-local
    // sequence; mapping to the safe range means collisions assume 53 bits and
    // are not a global uniqueness guarantee.
    let bytes = uuid::Uuid::new_v4();
    let mixed = u64::from_be_bytes(bytes.as_bytes()[..8].try_into().expect("UUID prefix is 8 bytes"));
    (mixed % (GUARD_JS_SAFE_INTEGER_MAX - 1)) + 1
}

const GUARD_JS_SAFE_INTEGER_MAX: u64 = (1u64 << 53) - 1;

impl DispatchHost {
    /// DOC-UI-02: explicit registry preparation, separate from manifest adoption.
    pub(crate) fn project_document_prepare(
        &mut self, fs: &dyn FileSystemPort, bound_root: &str,
        args: &crate::dto::DocumentPrepareArgs, label: &str, local: bool,
    ) -> Result<crate::dto::DocumentPrepareResultDto, crate::dto::DocumentPrepareErrorDto> {
        use crate::dto::{DocumentPrepareErrorDto as E, DocumentPrepareResultDto};
        if guard_require_main_local(label, local).is_err() { return Err(E::UnauthorizedCaller); }
        if bound_root.trim().is_empty() { return Err(E::ProjectNotBound); }
        if args.expected_project_root != bound_root { return Err(E::ProjectChanged); }
        if self.active_run_id.is_some() || self.active_lease_project.is_some() || self.guard_capture_process.is_some() {
            return Err(E::Busy);
        }
        let projection = self.work.projection().map_err(|e| E::WorkspaceRejected { reason: format!("{e:?}") })?;
        if !projection.active_leases.is_empty() { return Err(E::Busy); }
        // FakePathProbe provides WORK identity machinery, not filesystem proof.
        if !fs.exists(bound_root).unwrap_or(false) || fs.is_file(bound_root).unwrap_or(true) {
            return Err(E::RootUnavailable);
        }
        let outcome = self.work.register(bound_root).map_err(|e| E::WorkspaceRejected { reason: format!("{e:?}") })?;
        let project = match outcome {
            sgenaxis_work::RegisterOutcome::Created(p) | sgenaxis_work::RegisterOutcome::Existing(p) => p,
        };
        // WORK selected-view may change. HostSettings, leases and Run roots do not.
        Ok(DocumentPrepareResultDto { project_id: project.id.to_string(), project_root: bound_root.into() })
    }

    /// Same lexical key as WORK probe::normalize_light/case_fold_key. This does
    /// not resolve filesystem aliases, dot segments, symlinks or junctions.
    fn document_root_key(root: &str) -> String {
        let mut key = root.replace('\\', "/");
        while key.ends_with('/') && key.len() > 1 { key.pop(); }
        key.to_lowercase()
    }

    #[cfg(test)]
    pub(crate) fn document_test_projection(&self) -> (usize, Option<String>) {
        (self.work.store_len().unwrap(), self.work.projection().unwrap().selected_project_id)
    }

    #[cfg(test)]
    pub(crate) fn document_test_busy(&mut self, kind: &str, root: &str) {
        match kind {
            "run" => self.active_run_id = Some(77),
            "lease_flag" => self.active_lease_project = Some("fixture".into()),
            "capture" => self.guard_capture_process = Some(GuardCaptureProcessSlot {
                candidate_ref: 0, process_id: sgenaxis_ports::ProcessId(0), stage: GuardCaptureStage::BuildOnly }),
            "active_lease" | "reserved" | "unresolved" => {
                let id = sgenaxis_work::ProjectId::new(self.document_test_register(root));
                if kind == "active_lease" {
                    self.work.acquire_lease(&id, "fixture-run", "fixture-work", "fixture-fp").unwrap();
                } else {
                    let reservation = self.work.reserve_run_binding(&id, root, "fixture-work", "fixture-fp", "fixture-spec", "fixture-module").unwrap();
                    if kind == "unresolved" { self.work.mark_run_reservation_unresolved(&reservation).unwrap(); }
                }
            }
            _ => panic!("unknown fixture busy state"),
        }
    }

    /// DOC-ENTRY-01: resolve only an already registered WORK project matching
    /// the trusted HostSettings binding. Caller root/UUID fields do not exist.
    pub(crate) fn project_document_adopt(
        &mut self,
        fs: &dyn FileSystemPort,
        bound_root: &str,
        args: &crate::dto::DocumentAdoptArgs,
        candidate: &str,
        caller_label: &str,
        trusted_local: bool,
    ) -> Result<crate::dto::DocumentAdoptResultDto, crate::dto::DocumentAdoptErrorDto> {
        use crate::dto::{DocumentAdoptErrorDto as E, DocumentAdoptResultDto};
        if guard_require_main_local(caller_label, trusted_local).is_err() {
            return Err(E::UnauthorizedCaller);
        }
        if bound_root.trim().is_empty() || args.expected_project_id.trim().is_empty() {
            return Err(E::ProjectNotBound);
        }
        let project = self.work.get_project(&sgenaxis_work::ProjectId::new(&args.expected_project_id))
            .map_err(|_| E::ProjectNotBound)?.ok_or(E::ProjectNotBound)?;
        if Self::document_root_key(&project.root) != Self::document_root_key(bound_root) {
            return Err(E::ProjectMismatch);
        }
        use sgenaxis_host::{DocumentAdoptionOutcome, ProjectManifestStoreError as H};
        let outcome = sgenaxis_host::adopt_project_document(fs, &project, &args.reference, candidate)
            .map_err(|error| match error {
                H::InvalidProjectRoot => E::InvalidProjectRoot,
                H::InvalidReference => E::InvalidReference,
                H::UnsupportedKind => E::UnsupportedKind,
                H::MalformedManifest => E::MalformedManifest,
                H::UnsupportedSchema => E::UnsupportedSchema,
                H::InvalidManifestRecord => E::InvalidManifestRecord,
                H::InvalidDocumentId => E::InvalidDocumentId,
                H::DocumentIdConflict => E::DocumentIdConflict,
                H::ManifestChanged => E::ManifestChanged,
                H::RevisionConflict => E::RevisionConflict,
                H::ReferenceConflict => E::ReferenceConflict,
                H::SourceRead(e) => E::SourceRead(e.to_string()),
                H::ManifestRead(e) => E::ManifestRead(e.to_string()),
                H::CreateDirectory(e) => E::CreateDirectory(e.to_string()),
                H::Write(e) => E::Write(e.to_string()),
                H::DurabilityUnverified => E::DurabilityUnverified,
            })?;
        let (status, record) = match outcome {
            DocumentAdoptionOutcome::Adopted(record) => ("Adopted", record),
            DocumentAdoptionOutcome::AlreadyAdopted(record) => ("AlreadyAdopted", record),
        };
        Ok(DocumentAdoptResultDto { outcome: status.into(), document_id: record.document_id,
            kind: record.kind.as_str().into(), reference: record.reference, revision_id: record.revision_id })
    }

    #[cfg(test)]
    pub(crate) fn document_test_register(&mut self, root: &str) -> String {
        match self.work.register(root).unwrap() {
            sgenaxis_work::RegisterOutcome::Created(p) | sgenaxis_work::RegisterOutcome::Existing(p) => p.id.to_string(),
        }
    }

    pub fn project_policy_load(fs: &dyn FileSystemPort, bound: &str, expected: &str) -> Result<serde_json::Value, String> {
        if bound.trim().is_empty() || bound != expected {return Err("PROJECT_CHANGED_OR_UNBOUND".into());}
        let view=sgenaxis_host::project_preferences::load_project_preferences(fs,bound).map_err(|e|format!("{e:?}"))?;
        Ok(match view {Some(v)=>serde_json::json!({"configured":true,"projectRoot":v.project_root,"digest":v.digest,"preferences":v.preferences}),None=>serde_json::json!({"configured":false,"projectRoot":bound,"digest":null,"preferences":null})})
    }
    pub fn project_policy_save(fs: &dyn FileSystemPort, bound: &str, expected: &str, digest: Option<&str>, draft: &[u8]) -> Result<serde_json::Value, String> {
        if bound.trim().is_empty() || bound != expected {return Err("PROJECT_CHANGED_OR_UNBOUND".into());}
        let draft=sgenaxis_spec::project_preferences::parse_project_preferences(draft).map_err(|e|format!("{e:?}"))?;
        let v=sgenaxis_host::project_preferences::save_project_preferences(fs,bound,digest,&draft).map_err(|e|format!("{e:?}"))?;
        Ok(serde_json::json!({"configured":true,"projectRoot":v.project_root,"digest":v.digest,"preferences":v.preferences}))
    }
    pub fn project_policy_create(fs: &dyn FileSystemPort, parent: &str, name: &str, preset: Option<&str>, imported: Option<&str>) -> Result<serde_json::Value, String> {
        use sgenaxis_host::project_preferences::{CreationOutcome,PreferenceChoice};
        if preset.is_some()&&imported.is_some(){return Err("CHOOSE_PRESET_OR_IMPORT".into());}
        let root=sgenaxis_host::join_new_project_path(parent,name).map_err(|e|e.to_string())?;
        let choice=match(preset,imported){(Some(id),None)=>PreferenceChoice::Preset(id),(None,Some(text))=>PreferenceChoice::Imported(text.as_bytes()),_=>PreferenceChoice::Skip};
        match sgenaxis_host::project_preferences::create_project_with_preferences(fs,&root,choice).map_err(|e|format!("{e:?}"))? {
            CreationOutcome::Created{project_root,..}=>Ok(serde_json::json!({"status":"ok","path":project_root})),
            CreationOutcome::DirectoryCreatedPreferencesFailed{project_root,error}=>Ok(serde_json::json!({"status":"error","path":project_root,"message":format!("目錄已建立，偏好未完成：{error:?}；目前專案未切換。") })),
        }
    }
    pub fn project_policy_presets() -> Result<serde_json::Value,String> {
        let mut result=serde_json::Map::new();
        for id in ["conservative","balanced","throughput"] {result.insert(id.into(),serde_json::to_value(sgenaxis_spec::project_preferences::preset(id).map_err(|e|format!("{e:?}"))?).map_err(|e|e.to_string())?);}
        Ok(serde_json::Value::Object(result))
    }
    pub fn project_policy_import(fs: &dyn FileSystemPort,path:&str) -> Result<serde_json::Value,String> {
        let bytes=fs.read(path).map_err(|e|e.to_string())?;
        sgenaxis_spec::project_preferences::parse_project_preferences(&bytes).map_err(|e|format!("{e:?}"))?;
        let text=String::from_utf8(bytes).map_err(|e|e.to_string())?;
        Ok(serde_json::json!({"status":"ok","json":text}))
    }
    /// M01-S3 owner-snapshot authority producer. Snapshots the host's *live*
    /// owner facts (owner window + a per-host selection/session nonce) into a
    /// [`sgenaxis_host::project_definition::DefinitionAuthorityContext`]. Authority
    /// is derived only from the host owner; it is NEVER inferred from a
    /// UI-supplied project root.
    pub fn definition_authority(
        &self,
        owner_window: &str,
    ) -> Result<
        sgenaxis_host::project_definition::DefinitionAuthorityContext,
        sgenaxis_host::project_wizard::WizardBridgeError,
    > {
        let snapshot = sgenaxis_host::project_wizard::OwnerWindowSnapshot {
            owner_window: owner_window.to_owned(),
            selection_id: format!("sel-{:016x}", guard_session_nonce()),
            session_id: format!("ses-{:016x}", guard_session_nonce()),
        };
        sgenaxis_host::project_wizard::snapshot_definition_authority(&snapshot)
    }

    /// Compose Fake Process + unavailable MCP transport.
    /// DryRun never dials OS; Live CLI needs [`Self::wire_cli_live`] (StdProcess／test ProcessPort).
    /// Live MCP remains unavailable with [`StubMcpClient`], including with `real-mcp` enabled.
    pub fn new() -> Self {
        Self::with_git_index_port(Arc::new(StdGitIndexCommit::new()))
    }

    /// GIT-002-03: occupying workspace Run/lease that must block `git switch`.
    pub fn occupying_run_for_git_switch(&self) -> Option<String> {
        let proj = self.work.projection().ok();
        let host_run = self.active_run_id.map(|id| id.to_string());
        occupying_run_id(proj.as_ref(), host_run.as_deref()).or_else(|| {
            self.active_lease_project
                .as_deref()
                .filter(|s| !s.is_empty())
                .map(|s| s.to_string())
        })
    }

    pub(crate) fn with_git_index_port(port: Arc<dyn GitIndexCommitPort>) -> Self {
        let exec = AgentRouter::new(
            CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),
            McpAgentAdapter::with_defaults(Box::new(StubMcpClient)),
        );
        let probe = FakePathProbe::new();
        probe.accept_any_path();
        Self {
            engine: Engine::new(),
            exec,
            work: WorkspaceService::new(probe, FakeWorkspaceStore::new()),
            guard_input_fs: Box::new(StdFileSystem::new()),
            guard_red_process: Box::new(StdProcess::new()),
            guard_capture_process: None,
            guard_next_capture_id: 0,
            active_work_item: None,
            active_lease_project: None,
            active_run_id: None,
            evid: EvidenceStore::new(),
            evid_binding: VersionBinding::new("demo-spec", "demo-wt"),
            required_bdd: BTreeMap::new(),
            required_tdd: BTreeMap::new(),
            provider_by_work: BTreeMap::new(),
            flows: BTreeMap::new(),
            spec: SpecStore::new(),
            spec_loaded: false,
            guard_pass: None,
            listen: EventBridge::new(Duration::from_millis(50)),
            listen_proj: ListenProjection::new(),
            edit: EditSession::new(),
            guard_authority: GuardSessionState { boot: guard_session_nonce(), ..GuardSessionState::default() },
            guard_candidates: BTreeMap::new(),
            guard_next_candidate: guard_session_nonce(),
            guard_intents: BTreeMap::new(),
            git_index_commit: Arc::new(IndexCommitCoordinator::new(port)),
        }
    }

    pub(crate) fn git_index_commit_coordinator(&self) -> Arc<IndexCommitCoordinator> {
        Arc::clone(&self.git_index_commit)
    }

    /// Keep EditSession universe aligned with Core board task ids.
    fn sync_edit_universe(&mut self) {
        self.edit.set_universe(self.engine.task_ids());
    }

    fn edit_dto_from(
        proj: sgenaxis_core::EditProjection,
        status: &str,
        message: impl Into<String>,
    ) -> EditProjectionDto {
        EditProjectionDto {
            selected: proj.selected,
            selected_count: proj.selected_count,
            universe_count: proj.universe_count,
            can_undo: proj.can_undo,
            can_redo: proj.can_redo,
            status: status.into(),
            message: message.into(),
        }
    }

    /// PD-REMAIN-EDIT-01: read-only edit projection.
    pub fn edit_get_projection(&mut self) -> EditProjectionDto {
        self.sync_edit_universe();
        let p = self.edit.project();
        let status = if p.universe_count == 0 { "empty" } else { "ok" };
        Self::edit_dto_from(
            p,
            status,
            if status == "empty" {
                "無選取宇宙（看板尚無工項）"
            } else {
                "edit projection"
            },
        )
    }

    /// 復原 — Core EditSession undo.
    pub fn edit_undo(&mut self) -> Result<EditProjectionDto, String> {
        self.sync_edit_universe();
        match self.edit.undo() {
            Ok(p) => Ok(Self::edit_dto_from(p, "ok", "已復原選取")),
            Err(EditError::NothingToUndo) => Err("edit.undo：無可復原（歷史空）".into()),
            Err(EditError::NothingToRedo) => Err("edit.undo：內部錯誤".into()),
        }
    }

    /// 重做 — Core EditSession redo.
    pub fn edit_redo(&mut self) -> Result<EditProjectionDto, String> {
        self.sync_edit_universe();
        match self.edit.redo() {
            Ok(p) => Ok(Self::edit_dto_from(p, "ok", "已重做選取")),
            Err(EditError::NothingToRedo) => Err("edit.redo：無可重做".into()),
            Err(EditError::NothingToUndo) => Err("edit.redo：內部錯誤".into()),
        }
    }

    /// 全選變更 — select all board task ids in universe.
    pub fn edit_select_all(&mut self) -> EditProjectionDto {
        self.sync_edit_universe();
        let p = self.edit.select_all();
        let status = if p.universe_count == 0 { "empty" } else { "ok" };
        Self::edit_dto_from(
            p,
            status,
            if status == "empty" {
                "全選：宇宙空（無工項可選）"
            } else {
                "已全選變更（看板工項）"
            },
        )
    }

    /// 清除選取.
    pub fn edit_clear(&mut self) -> EditProjectionDto {
        self.sync_edit_universe();
        let p = self.edit.clear();
        Self::edit_dto_from(p, "ok", "已清除選取")
    }

    /// PD-REMAIN-LIVE-MCP-01: apply host MCP settings before Live `start_run` (Command path).
    pub fn apply_mcp_settings(&mut self, settings: McpAgentSettings) {
        self.exec.mcp_mut().apply_settings(settings);
    }

    /// Read-only MCP settings currently wired into EXEC (tests／projection checks).
    pub fn mcp_settings(&self) -> &McpAgentSettings {
        self.exec.mcp().settings()
    }

    /// Apply CLI settings for DryRun (no ProcessPort swap). Secrets stay in settings, not board.
    pub fn apply_cli_settings(&mut self, settings: CliAgentSettings) {
        self.exec.cli_mut().apply_settings(settings);
    }

    /// PD-REMAIN-LIVE-SPAWN-01: wire approved CLI + ProcessPort for true EXEC spawn.
    /// Unapproved／empty path → readable `NOT RUN` reject (no silent DryRun compose).
    pub fn wire_cli_live_process(
        &mut self,
        settings: CliAgentSettings,
        process: Box<dyn ProcessPort>,
    ) -> Result<(), String> {
        if !settings.live_approved {
            return Err(
                "Live 未核准：NOT RUN — 請先存為作用中（live_approved／agent_active）；\
                 派工僅經 start_run → DispatchHost → EXEC；秘密不進投影"
                    .into(),
            );
        }
        let path = settings.selected_config().path.trim();
        if path.is_empty() {
            return Err(
                "Live 無 CLI：NOT RUN — 路徑空白不可起程；秘密不進投影".into(),
            );
        }
        let cli = CliAgentAdapter::new(settings, process);
        self.exec.replace_cli(cli).map_err(|e| e.to_string())
    }

    /// Production Live CLI: StdProcess via EXEC `real-spawn` (never UI→adapter).
    pub fn wire_cli_live(&mut self, settings: CliAgentSettings) -> Result<(), String> {
        self.wire_cli_live_process(settings, Box::new(StdProcess::new()))
    }

    /// Read-only CLI settings currently wired into EXEC.
    pub fn cli_settings(&self) -> &CliAgentSettings {
        self.exec.cli().settings()
    }

    pub fn list_commands() -> Vec<CommandDescriptor> {
        vec![
            CommandDescriptor {
                name: "list_commands".into(),
                summary: "Command catalogue for UI menus".into(),
            },
            CommandDescriptor {
                name: "get_board".into(),
                summary: "Read board projection snapshot".into(),
            },
            CommandDescriptor {
                name: "load_local_board".into(),
                summary: "Load read-only local PROJECT-BOARD #board-snapshot into projection".into(),
            },
            CommandDescriptor {
                name: "upsert_task".into(),
                summary: "Insert／update a fake work item via Core".into(),
            },
            CommandDescriptor {
                name: "set_task_zone".into(),
                summary: "Change work-item zone → dirty → projection".into(),
            },
            CommandDescriptor {
                name: "start_run".into(),
                summary: "Start Agent DryRun (Cli｜Mcp); requires root＋work item＋fingerprint".into(),
            },
            CommandDescriptor {
                name: "poll_chunks".into(),
                summary: "Drain AgentChunk events; refresh board on exit".into(),
            },
            CommandDescriptor {
                name: "cancel_run".into(),
                summary: "Cancel in-flight DryRun".into(),
            },
            CommandDescriptor {
                name: "get_evidence_summary".into(),
                summary: "PD-EVID-UI-01: read-only Inspector evidence summary".into(),
            },
            CommandDescriptor {
                name: "spec_load_fixture".into(),
                summary: "PD-SPEC-UI-01: load sample ModuleSpec into projection".into(),
            },
            CommandDescriptor {
                name: "spec_get_projection".into(),
                summary: "PD-SPEC-UI-01: read-only Spec projection".into(),
            },
            CommandDescriptor {
                name: "spec_get_revision".into(),
                summary: "PD-SPEC-UI-01: revision＋contracts (approved = immutable)".into(),
            },
            CommandDescriptor {
                name: "spec_approve".into(),
                summary: "PD-SPEC-UI-01: approve Draft revision (locks in place)".into(),
            },
            CommandDescriptor {
                name: "spec_try_set_contract".into(),
                summary: "PD-SPEC-UI-01: in-place body edit; approved → REPLAN_REQUIRED".into(),
            },
            CommandDescriptor {
                name: "spec_revise".into(),
                summary: "PD-SPEC-UI-01: revise entry — new Draft from approved baseline".into(),
            },
            CommandDescriptor {
                name: "arch_get_projection".into(),
                summary: "PD-REMAIN-ARCH-UI-01: module／dependency architecture projection".into(),
            },
            CommandDescriptor {
                name: "listen_get_projection".into(),
                summary: "PD-REMAIN-LISTEN-UI-01: FS／Git／Agent listen projection (Command only)"
                    .into(),
            },
            CommandDescriptor {
                name: "guard_check_start".into(),
                summary: "PD-GUARD-CMD-01: start_implementation gate (CODE:detail on reject)".into(),
            },
            CommandDescriptor {
                name: "guard_check_changes".into(),
                summary: "PD-GUARD-CMD-01: pre-write path gate (CODE:detail on reject)".into(),
            },
            CommandDescriptor {
                name: "start_implementation".into(),
                summary: "PD-GUARD-CMD-01: GUARD pass then EXEC DryRun".into(),
            },
            CommandDescriptor {
                name: "accept_work_item".into(),
                summary: "PD-FLOW-EVID-GATE-01: Accept via EVID+FLOW (gaps → yellow/reject)".into(),
            },
            CommandDescriptor {
                name: "complete_work_item".into(),
                summary: "PD-FLOW-EVID-GATE-01: Complete via EVID+FLOW (Provider done ≠ green)"
                    .into(),
            },
            CommandDescriptor {
                name: "batch_work_tags".into(),
                summary: "PD-REMAIN-WORK-TAGS-01: batch BDD／TDD tags → work／board projection"
                    .into(),
            },
            CommandDescriptor {
                name: "edit_get_projection".into(),
                summary: "PD-REMAIN-EDIT-01: read-only selection／history projection".into(),
            },
            CommandDescriptor {
                name: "edit_undo".into(),
                summary: "PD-REMAIN-EDIT-01: undo selection via Core EditSession".into(),
            },
            CommandDescriptor {
                name: "edit_redo".into(),
                summary: "PD-REMAIN-EDIT-01: redo selection via Core EditSession".into(),
            },
            CommandDescriptor {
                name: "edit_select_all".into(),
                summary: "PD-REMAIN-EDIT-01: select all board／change ids in universe".into(),
            },
            CommandDescriptor {
                name: "edit_clear".into(),
                summary: "PD-REMAIN-EDIT-01: clear selection via Core EditSession".into(),
            },
        ]
    }

    /// PD-GUARD-CMD-01: approval + RED check (does not start EXEC).
    pub fn guard_check_start(&self, packet: &GuardPacketDto) -> GuardDecisionView {
        check_start_view(packet)
    }

    /// PD-GUARD-CMD-01: protect／allow path check before write.
    pub fn guard_check_changes(&self, packet: &GuardPacketDto) -> GuardDecisionView {
        check_changes_view(packet)
    }

    /// Pre-write authorize — Err carries `CODE:detail`.
    pub fn authorize_write(&self, packet: &GuardPacketDto) -> Result<(), String> {
        authorize_write_paths(packet)
    }

    /// BDD-PD-GUARD-CMD-01: GUARD must allow; then EXEC DryRun starts.
    /// Reject → `Err` with `CODE:detail` (joined). Stores [`GuardExecPass`] seam.
    pub fn start_implementation(
        &mut self,
        args: StartImplementationArgs,
    ) -> Result<StartRunResult, String> {
        let pass = authorize_exec_start(&args.guard, args.work_item_id.clone())?;
        self.guard_pass = Some(pass.clone());
        let mut run_args = StartRunArgs {
            provider: args.provider,
            dry_run: args.dry_run,
            work_item_id: args.work_item_id,
            project_root: args.project_root,
            worktree_fingerprint: args.worktree_fingerprint,
            guard: None,
        };
        let mut result = self.start_run_ungated(&mut run_args)?;
        result.envelope_hash = Some(pass.envelope_hash);
        Ok(result)
    }

    pub fn get_board(&self) -> BoardView {
        self.board_view()
    }

    /// Replace Core projection with tasks from a local board snapshot (read-only load).
    pub fn replace_projection_tasks(
        &mut self,
        tasks: Vec<sgenaxis_core::TaskRecord>,
    ) -> BoardView {
        self.engine.replace_all_tasks(tasks);
        self.sync_edit_universe();
        self.board_view()
    }

    pub fn upsert_task(&mut self, args: UpsertTaskArgs) -> Result<BoardView, String> {
        let zone = parse_zone(&args.zone)?;
        self.engine.upsert_task(args.id, args.title, zone);
        self.sync_edit_universe();
        Ok(self.board_view())
    }

    pub fn set_task_zone(&mut self, id: &str, zone: &str) -> Result<BoardView, String> {
        let zone = parse_zone(zone)?;
        self.engine
            .set_zone(id, zone)
            .map_err(|e| e.to_string())?;
        self.sync_edit_universe();
        Ok(self.board_view())
    }

    pub fn start_run(&mut self, args: StartRunArgs) -> Result<StartRunResult, String> {
        let mut args = args;
        // PD-GUARD-CMD-01: optional guard packet on start_run → gate before EXEC.
        let envelope_hash = if let Some(ref packet) = args.guard {
            let pass = authorize_exec_start(packet, args.work_item_id.clone())?;
            self.guard_pass = Some(pass.clone());
            Some(pass.envelope_hash)
        } else {
            None
        };
        let mut result = self.start_run_ungated(&mut args)?;
        result.envelope_hash = envelope_hash;
        Ok(result)
    }

    /// EXEC start after GUARD (or DryRun demo without packet). Clears consumed pass.
    ///
    /// PD-EXEC-BIND-01: requires project_root＋work_item_id＋worktree_fingerprint;
    /// binds WORK lease consistently before／with the Run.
    ///
    /// PD-REMAIN-LIVE-SPAWN-01: Live **CLI** via DispatchHost→EXEC→ProcessPort
    /// (`real-spawn` + approved settings); unapproved／empty path → **NOT RUN**.
    /// PD-REMAIN-LIVE-MCP-01: Live **MCP** similarly; empty／`:8788`／`:8787` → **NOT RUN**.
    /// Never UI→adapters.
    fn start_run_ungated(&mut self, args: &mut StartRunArgs) -> Result<StartRunResult, String> {
        let live = !args.dry_run;
        if live {
            match args.provider {
                ProviderDto::Cli => {
                    let cli = self.exec.cli().settings();
                    if !cli.live_approved {
                        return Err(
                            "Live 未核准：NOT RUN — live_approved／agent_active 未開；\
                             請先 wire_cli_live（Command 路徑）；秘密不進投影"
                                .into(),
                        );
                    }
                    let path = cli.selected_config().path.trim();
                    if path.is_empty() {
                        return Err(
                            "Live 無 CLI：NOT RUN — 路徑空白不可起程；秘密不進投影".into(),
                        );
                    }
                }
                ProviderDto::Mcp => {
                    let endpoint = self.exec.mcp().settings().endpoint.clone();
                    if endpoint.trim().is_empty() || !is_mcp_endpoint_activatable(&endpoint) {
                        return Err(
                            "NOT RUN: no activatable MCP Live target; \
                             禁 :8788／:8787；空／未設目標不可 Live；秘密不進投影"
                                .into(),
                        );
                    }
                }
            }
        }

        // PD-EXEC-SINGLE-01: reject a second start while one Run is in flight.
        if self.active_run_id.is_some()
            || self.active_work_item.is_some()
            || self.active_lease_project.is_some()
        {
            return Err(format!(
                "busy: only one in-flight Agent Run allowed (PD-EXEC-SINGLE-01); active lease/run must finish, cancel, or reconcile first (active_run_id={:?})",
                self.active_run_id
            ));
        }

        let project_root = require_arg_field("project_root", args.project_root.as_deref())?;
        let work_item_id = require_arg_field("work_item_id", args.work_item_id.as_deref())?;
        let worktree_fingerprint =
            require_arg_field("worktree_fingerprint", args.worktree_fingerprint.as_deref())?;

        let provider = match args.provider {
            ProviderDto::Cli => AgentProvider::Cli,
            ProviderDto::Mcp => AgentProvider::Mcp,
        };

        let req = StartRunRequest {
            provider,
            dry_run: args.dry_run,
            project_root: project_root.clone(),
            work_item_id: work_item_id.clone(),
            worktree_fingerprint: worktree_fingerprint.clone(),
            mcp_tool: None,
            mcp_tool_args: None,
        };
        let _ = require_run_binding(&req).map_err(|e| e.to_string())?;

        // WORK lease preflight before EXEC (reject mismatch without starting a Run).
        let project = self
            .work
            .preflight_run_binding(&project_root, &work_item_id, &worktree_fingerprint)
            .map_err(|e| e.to_string())?;

        let run_id = self.exec.start_run(req).map_err(|e| {
            if provider == AgentProvider::Mcp && matches!(e, ExecError::RealMcpDisabled) {
                "NOT RUN: real MCP transport unavailable; use explicit DryRun for simulation"
                    .to_string()
            } else {
                e.to_string()
            }
        })?;

        let lease = self
            .work
            .bind_run(
                &project_root,
                format!("{}", run_id.0),
                &work_item_id,
                &worktree_fingerprint,
            )
            .map_err(|e| e.to_string())?;
        debug_assert_eq!(lease.project_id, project.id);
        self.active_lease_project = Some(lease.project_id.as_str().to_string());

        // Consume GUARD／EXEC-BIND pass once EXEC is started.
        let _ = self.guard_pass.take();

        // Ensure task exists then mark blue (running).
        if self
            .engine
            .property_store()
            .get(&PropertyId::task_zone(&work_item_id))
            .is_none()
        {
            self.engine.upsert_task(
                work_item_id.clone(),
                format!("Run {work_item_id}"),
                Zone::Gray,
            );
        }
        let _ = self.engine.set_zone(&work_item_id, Zone::Blue);
        self.sync_flow_event(&work_item_id, FlowEvent::Start, "run_started", false);
        self.active_work_item = Some(work_item_id.clone());
        self.active_run_id = Some(run_id.0);
        self.provider_by_work
            .insert(work_item_id, ProviderTerminal::Running);

        Ok(StartRunResult {
            run_id: run_id.0,
            provider: args.provider,
            dry_run: args.dry_run,
            board: self.board_view(),
            envelope_hash: None,
        })
    }

    pub fn poll_chunks(&mut self, run_id: u64) -> Result<PollResult, String> {
        let chunks = self
            .exec
            .poll_chunks(RunId(run_id))
            .map_err(|e| e.to_string())?;

        // PD-REMAIN-LISTEN-UI-01: AgentChunk → EventBridge → ListenProjection (no UI notify).
        for c in &chunks {
            let _ = self.listen.push(SourceEvent::Agent(c.clone()));
        }
        self.drain_listen();

        let mut exited = false;
        let mut failed = false;
        let mut cancelled = false;
        let mut crashed = false;
        for c in &chunks {
            match c {
                AgentChunk::Exited {
                    classification, ..
                } => {
                    exited = true;
                    match classification {
                        ExitClassification::Success => {}
                        ExitClassification::Cancelled => cancelled = true,
                        ExitClassification::Crashed => crashed = true,
                        ExitClassification::Failure => failed = true,
                    }
                }
                AgentChunk::Failed { .. } => failed = true,
                _ => {}
            }
        }

        // PD-EXEC-CANCEL-01: cancel／crash／non-zero → reconcile (release WORK lease + terminal).
        if exited || failed || crashed || cancelled {
            self.reconcile_run_exit(failed, cancelled, crashed);
        }

        Ok(PollResult {
            chunks: chunks.into_iter().map(chunk_to_dto).collect(),
            board: self.board_view(),
        })
    }

    /// Release WORK lease and project Cancelled／Crashed／Failure／Success end state.
    /// Never sets product zone green (§7.1 / Provider Success ≠ 工項綠燈).
    fn reconcile_run_exit(&mut self, failed: bool, cancelled: bool, crashed: bool) {
        if let Some(pid) = self.active_lease_project.take() {
            self.work.release_lease_for_project_id(&pid);
        }
        // PD-EXEC-SINGLE-01: clear the single active Run so a new start_run may proceed.
        self.active_run_id = None;
        if let Some(wid) = self.active_work_item.take() {
            let (zone, terminal) = if failed {
                (Zone::Red, ProviderTerminal::Failure)
            } else if crashed {
                // Crash → 待對帳 (yellow); distinct from Failure.
                (Zone::Yellow, ProviderTerminal::Crashed)
            } else if cancelled {
                (Zone::Yellow, ProviderTerminal::Cancelled)
            } else {
                // DryRun success → awaiting review (not product green).
                // PD-FLOW-EVID-GATE-01: Provider Success ≠ Accept／Complete／green.
                (Zone::Yellow, ProviderTerminal::Success)
            };
            let _ = self.engine.set_zone(&wid, zone);
            if failed {
                self.sync_flow_event(&wid, FlowEvent::Fail, "provider_failed", false);
            } else {
                // Success／cancel／crash → yellow pending; never Accept／Complete here.
                self.sync_flow_event(&wid, FlowEvent::AwaitApproval, "provider_terminal", false);
            }
            self.provider_by_work.insert(wid, terminal);
        }
    }

    pub fn cancel_run(&mut self, run_id: u64) -> Result<BoardView, String> {
        self.exec
            .cancel(RunId(run_id))
            .map_err(|e| e.to_string())?;
        // Acknowledge only. The existing poll path delivers final output and
        // reconciles the WORK lease after an actual terminal event.
        Ok(self.board_view())
    }

    /// Test／demo seam: crash／non-zero exit reconcile without live spawn (PD-EXEC-CANCEL-01).
    /// Drains EXEC busy via cancel+poll on the adapter, then projects Crashed (not Cancelled).
    #[cfg(test)]
    fn reconcile_crash_for_test(&mut self, run_id: u64) {
        let rid = RunId(run_id);
        let _ = self.exec.cancel(rid);
        let _ = self.exec.poll_chunks(rid); // clear adapter busy; ignore Cancelled chunk
        self.reconcile_run_exit(false, false, true);
    }

    /// PD-EVID-UI-01: read-only evidence summary for a selected work item.
    /// Does **not** mutate the evidence store or board zone.
    pub fn get_evidence_summary(&self, work_item_id: &str) -> EvidenceSummaryDto {
        let required = self
            .required_bdd
            .get(work_item_id)
            .cloned()
            .unwrap_or_default();
        let provider = self
            .provider_by_work
            .get(work_item_id)
            .copied()
            .unwrap_or(ProviderTerminal::Running);
        let summary = project_inspector_evidence(
            &self.evid,
            work_item_id,
            &self.evid_binding,
            &required,
            provider,
        );

        let (title, zone) =
            sgenaxis_core::task_from_store(self.engine.property_store(), work_item_id).map_or(
                (None, None),
                |rec| (Some(rec.title), Some(rec.zone.as_str().to_string())),
            );

        EvidenceSummaryDto {
            work_item_id: summary.work_item_id,
            title,
            zone,
            provider_terminal: summary.provider_terminal,
            provider_success_implies_green: summary.provider_success_implies_green,
            product_lamp_hint: summary.product_lamp_hint,
            ready_for_green: summary.ready_for_green,
            overall_status: summary.overall_status,
            gaps: summary.gaps,
            lines: summary
                .lines
                .into_iter()
                .map(|l| EvidenceSummaryLineDto {
                    bdd_id: l.bdd_id,
                    status_label: l.status_label,
                    verdict_key: l.verdict_key,
                })
                .collect(),
        }
    }

    /// BDD-PD-REMAIN-WORK-TAGS-01: batch-write BDD／TDD tags into WORK／board projection.
    ///
    /// Illegal ids／tags → readable `Err` (never silent). Does **not** change zone／green.
    pub fn batch_work_tags(&mut self, args: BatchWorkTagsArgs) -> Result<BoardView, String> {
        let ids = normalize_work_item_ids(&args.work_item_ids)?;
        let bdd = normalize_tag_list("BDD", &args.bdd)?;
        let tdd = normalize_tag_list("TDD", &args.tdd)?;
        if bdd.is_empty() && tdd.is_empty() {
            return Err("非法批次標籤：至少需一個 BDD 或 TDD 標籤".into());
        }
        for id in &ids {
            if !self.engine.task_ids().iter().any(|t| t == id) {
                return Err(format!("未知工項：{id}"));
            }
        }
        for id in &ids {
            self.required_bdd.insert(id.clone(), bdd.clone());
            self.required_tdd.insert(id.clone(), tdd.clone());
        }
        Ok(self.board_view())
    }

    /// Test／demo seam: bind required BDDs for a work item (not exposed as UI write).
    #[cfg(test)]
    pub fn set_required_bdd_for_test(&mut self, work_item_id: &str, bdds: Vec<String>) {
        self.required_bdd.insert(work_item_id.into(), bdds);
    }

    /// Test／demo seam: append Pass evidence for a BDD under the current binding.
    #[cfg(test)]
    pub fn seed_pass_evidence_for_test(&mut self, evid_id: &str, bdd_id: &str) {
        let cap = RunCapture::new("cargo test", "/work", 0)
            .with_stdout("test result: ok. 1 passed; 0 failed")
            .with_cases(vec![CaseResult {
                test_id: "case1".into(),
                passed: true,
                message: String::new(),
            }]);
        let _ = self
            .evid
            .record(evid_id, Some(bdd_id.into()), self.evid_binding.clone(), cap);
    }

    // ── PD-FLOW-EVID-GATE-01 ─────────────────────────────────────────────────

    /// Accept work item: EVID ReadyForGreen required; missing → keep yellow + reject.
    ///
    /// Provider／Agent "done" alone never accepts. Does **not** admin-green the board card.
    pub fn accept_work_item(&mut self, work_item_id: &str) -> Result<BoardView, String> {
        self.ensure_task_and_flow(work_item_id)?;
        let decision = self.evid_decision(work_item_id);
        let ready = evidence_allows_flow_accept_or_complete(&decision);
        let gaps = evidence_gaps(&decision);

        match self.apply_flow(
            work_item_id,
            FlowEvent::Accept,
            "accept_via_evid",
            ready,
        ) {
            Ok(_) => {
                // Accept does not change lamp; keep current (typically yellow).
                Ok(self.board_view())
            }
            Err(FlowError::AcceptWithoutEvidence { .. }) => {
                let _ = self.engine.set_zone(work_item_id, Zone::Yellow);
                debug_assert_eq!(EVIDENCE_GAP_LAMP_HINT, "yellow");
                Err(format!(
                    "EVID_GAP:accept rejected; lamp=yellow; gaps={}",
                    gaps.join(",")
                ))
            }
            Err(e) => Err(e.to_string()),
        }
    }

    /// Complete work item → product green **only** when FLOW accepted + EVID ready.
    ///
    /// Missing evidence → reject, force yellow. Provider Success never calls this path.
    pub fn complete_work_item(&mut self, work_item_id: &str) -> Result<BoardView, String> {
        self.ensure_task_and_flow(work_item_id)?;
        let decision = self.evid_decision(work_item_id);
        let ready = evidence_allows_flow_accept_or_complete(&decision);
        let gaps = evidence_gaps(&decision);

        match self.apply_flow(
            work_item_id,
            FlowEvent::Complete,
            "complete_via_evid",
            ready,
        ) {
            Ok(outcome) => {
                let _ = self.engine.set_zone(work_item_id, outcome.lamp);
                Ok(self.board_view())
            }
            Err(FlowError::CompleteWithoutEvidence { .. })
            | Err(FlowError::CompleteWithoutAcceptance { .. })
            | Err(FlowError::AcceptWithoutEvidence { .. }) => {
                let _ = self.engine.set_zone(work_item_id, Zone::Yellow);
                Err(format!(
                    "EVID_GAP:complete rejected; lamp=yellow; gaps={}",
                    gaps.join(",")
                ))
            }
            Err(e) => Err(e.to_string()),
        }
    }

    fn evid_decision(&self, work_item_id: &str) -> sgenaxis_evid::GreenDecision {
        let required = self
            .required_bdd
            .get(work_item_id)
            .cloned()
            .unwrap_or_default();
        let provider = self
            .provider_by_work
            .get(work_item_id)
            .copied()
            .unwrap_or(ProviderTerminal::Running);
        evaluate_ready_for_green(&self.evid, &self.evid_binding, &required, provider)
    }

    fn ensure_task_and_flow(&mut self, work_item_id: &str) -> Result<(), String> {
        if self
            .engine
            .property_store()
            .get(&PropertyId::task_zone(work_item_id))
            .is_none()
        {
            return Err(format!("unknown work item: {work_item_id}"));
        }
        if !self.flows.contains_key(work_item_id) {
            let mut flow = TaskFlow::new(work_item_id, "dispatch");
            // Best-effort align: if already blue／yellow／red from Engine, drive SM.
            if let Some(rec) =
                sgenaxis_core::task_from_store(self.engine.property_store(), work_item_id)
            {
                match rec.zone {
                    Zone::Blue => {
                        let _ = flow.apply(FlowEvent::Start, "align", "t", None, false);
                    }
                    Zone::Yellow => {
                        let _ = flow.apply(FlowEvent::QueuePending, "align", "t", None, false);
                    }
                    Zone::Red => {
                        let _ = flow.apply(FlowEvent::Start, "align", "t", None, false);
                        let _ = flow.apply(FlowEvent::Fail, "align_fail", "t2", None, false);
                    }
                    Zone::Gray | Zone::Green => {}
                }
            }
            self.flows.insert(work_item_id.into(), flow);
        }
        Ok(())
    }

    fn apply_flow(
        &mut self,
        work_item_id: &str,
        event: FlowEvent,
        reason: &str,
        evidence_ready: bool,
    ) -> Result<sgenaxis_core::TransitionOutcome, FlowError> {
        self.ensure_task_and_flow(work_item_id)
            .map_err(|_| FlowError::IllegalTransition {
                from: Zone::Gray,
                event,
            })?;
        let flow = self
            .flows
            .get_mut(work_item_id)
            .expect("flow inserted by ensure");
        flow.apply(event, reason, "dispatch", None, evidence_ready)
    }

    /// Best-effort FLOW sync (ignores illegal transitions — e.g. already yellow).
    fn sync_flow_event(
        &mut self,
        work_item_id: &str,
        event: FlowEvent,
        reason: &str,
        evidence_ready: bool,
    ) {
        if !self.flows.contains_key(work_item_id) {
            self.flows
                .insert(work_item_id.into(), TaskFlow::new(work_item_id, "dispatch"));
        }
        if let Some(flow) = self.flows.get_mut(work_item_id) {
            let _ = flow.apply(event, reason, "dispatch", None, evidence_ready);
        }
    }

    // ── PD-SPEC-UI-01 ───────────────────────────────────────────────────────

    /// Load the bundled sample ModuleSpec fixture into the SPEC store.
    pub fn spec_load_fixture(&mut self) -> Result<SpecProjectionDto, String> {
        let store = SpecStore::load_json(SAMPLE_MODULE_SPEC).map_err(map_spec_err)?;
        self.spec = store;
        self.spec_loaded = true;
        Ok(self.spec_projection_dto())
    }

    /// Read-only Spec projection (empty when not loaded).
    pub fn spec_get_projection(&self) -> SpecProjectionDto {
        self.spec_projection_dto()
    }

    /// Revision＋contracts for UI display. Approved → `immutable: true`.
    pub fn spec_get_revision(
        &self,
        args: SpecGetRevisionArgs,
    ) -> Result<SpecRevisionDto, String> {
        if !self.spec_loaded {
            return Err("spec not loaded — call spec_load_fixture first".into());
        }
        let rev = self
            .spec
            .revision(&args.revision_id)
            .ok_or_else(|| format!("unknown revision: {}", args.revision_id))?;
        Ok(revision_to_dto(rev))
    }

    /// Approve a Draft revision — thereafter immutable in place.
    pub fn spec_approve(&mut self, args: SpecApproveArgs) -> Result<SpecRevisionDto, String> {
        if !self.spec_loaded {
            return Err("spec not loaded — call spec_load_fixture first".into());
        }
        let rev = self
            .spec
            .approve(&args.revision_id)
            .map_err(map_spec_err)?;
        Ok(revision_to_dto(rev))
    }

    /// Attempt in-place contract body edit.
    ///
    /// Approved revision → [`SpecError::ReplanRequired`] (never mutates).
    /// Draft → updates body. Revise must use [`Self::spec_revise`] (separate entry).
    pub fn spec_try_set_contract(
        &mut self,
        args: SpecTrySetContractArgs,
    ) -> Result<SpecRevisionDto, String> {
        if !self.spec_loaded {
            return Err("spec not loaded — call spec_load_fixture first".into());
        }
        self.spec
            .try_set_contract_body(&args.revision_id, &args.contract_id, args.new_body)
            .map_err(map_spec_err)?;
        let rev = self
            .spec
            .revision(&args.revision_id)
            .ok_or_else(|| format!("unknown revision: {}", args.revision_id))?;
        Ok(revision_to_dto(rev))
    }

    /// Separate revise entry: new Draft from an Approved baseline (never mutates baseline).
    pub fn spec_revise(&mut self, args: SpecReviseArgs) -> Result<SpecRevisionDto, String> {
        if !self.spec_loaded {
            return Err("spec not loaded — call spec_load_fixture first".into());
        }
        let contracts = if args.contracts.is_empty() {
            let baseline = self
                .spec
                .revision(&args.from_revision_id)
                .ok_or_else(|| format!("unknown revision: {}", args.from_revision_id))?;
            baseline.contracts.clone()
        } else {
            args.contracts
                .into_iter()
                .map(|c| Contract {
                    id: c.id,
                    title: c.title,
                    body: c.body,
                })
                .collect()
        };
        let rev = self
            .spec
            .revise_from_approved(
                &args.from_revision_id,
                args.new_revision_id,
                args.new_version_label,
                contracts,
            )
            .map_err(map_spec_err)?;
        Ok(revision_to_dto(rev))
    }

    // ── PD-REMAIN-LISTEN-UI-01 ───────────────────────────────────────────────

    /// Tick debounce + apply DomainEvent onto ListenProjection／Engine indicators.
    fn drain_listen(&mut self) {
        let events = self.listen.tick();
        if events.is_empty() {
            return;
        }
        EventBridge::apply_to_engine(&mut self.engine, &events);
        self.listen_proj.apply(&events);
    }

    /// Read-only listen snapshot for UI (Command only; never OS notify from JS).
    pub fn listen_get_projection(&mut self) -> ListenProjectionDto {
        // Flush any elapsed debounce window before snapshot.
        self.drain_listen();
        self.listen_projection_dto()
    }

    fn listen_projection_dto(&self) -> ListenProjectionDto {
        let p = &self.listen_proj;
        let status = if p.event_count == 0 {
            "empty"
        } else {
            "ok"
        };
        ListenProjectionDto {
            status: status.into(),
            generation: p.generation,
            event_count: p.event_count,
            last_fs_path: p.last_fs_path.clone(),
            last_fs_burst: p.last_fs_burst,
            last_git_root: p.last_git_root.clone(),
            last_git_burst: p.last_git_burst,
            last_agent_run: p.last_agent_run,
            last_agent_kind: p.last_agent_kind.clone(),
            last_agent_burst: p.last_agent_burst,
            last_agent_classification: p.last_agent_classification.clone(),
            last_agent_exit_code: p.last_agent_exit_code,
            pending_reconcile: p.pending_reconcile,
            last_reconcile_run: p.last_reconcile_run,
            ended_runs: p.ended_runs.clone(),
            host_fs_watch: "NOT RUN".into(),
            host_git_watch: "NOT RUN".into(),
            host_agent_bridge: "wired".into(),
            note: Some(
                "UI reads listen_get_projection only. Host WinFsNotify／Git watch pump = NOT RUN \
                 (adapter in sgenaxis-listen; Tauri host loop not attached). Agent via poll_chunks."
                    .into(),
            ),
        }
    }

    /// Host／test seam: push adapter SourceEvent into the bridge (never from UI IPC).
    #[cfg(test)]
    fn listen_push_source(&mut self, event: SourceEvent) {
        let _ = self.listen.push(event);
    }

    /// Test helper: FakeClock-backed bridge for deterministic debounce.
    #[cfg(test)]
    fn with_fake_listen(
        window_ms: u64,
    ) -> (Self, sgenaxis_listen::FakeClock) {
        let clock = sgenaxis_listen::FakeClock::new();
        let mut host = Self::new();
        host.listen = EventBridge::with_clock(
            Duration::from_millis(window_ms),
            Box::new(clock.clone()),
        );
        (host, clock)
    }

    // ── PD-REMAIN-ARCH-UI-01 ─────────────────────────────────────────────────

    /// Module／dependency projection for the arch panel (UI → Command → this).
    ///
    /// Inventory mirrors ARCH: UI → Command → DispatchHost → Core／FLOW／EXEC／WORK／EVID → Ports.
    /// Empty modules → `status: empty` (UI shows empty／NOT RUN). Never a UI-static fake as live.
    pub fn arch_get_projection(&self) -> ArchProjectionDto {
        self.arch_projection_dto()
    }

    fn arch_projection_dto(&self) -> ArchProjectionDto {
        let modules = vec![
            ArchModuleDto {
                id: "ui".into(),
                name: "UI".into(),
                layer: "presentation".into(),
                role: "Vanilla shell; invoke only".into(),
            },
            ArchModuleDto {
                id: "command".into(),
                name: "Tauri Command".into(),
                layer: "ipc".into(),
                role: "Allowlisted #[tauri::command]".into(),
            },
            ArchModuleDto {
                id: "dispatch_host".into(),
                name: "DispatchHost".into(),
                layer: "host".into(),
                role: "Command façade; no OS in closures".into(),
            },
            ArchModuleDto {
                id: "core".into(),
                name: "Core".into(),
                layer: "domain".into(),
                role: "Property + Dirty + Evaluation".into(),
            },
            ArchModuleDto {
                id: "flow".into(),
                name: "FLOW".into(),
                layer: "domain".into(),
                role: "Lamp state machine".into(),
            },
            ArchModuleDto {
                id: "exec".into(),
                name: "EXEC".into(),
                layer: "domain".into(),
                role: "Agent DryRun／Live providers".into(),
            },
            ArchModuleDto {
                id: "work".into(),
                name: "WORK".into(),
                layer: "domain".into(),
                role: "Workspace／leases".into(),
            },
            ArchModuleDto {
                id: "evid".into(),
                name: "EVID".into(),
                layer: "domain".into(),
                role: "Evidence classify／green gate".into(),
            },
            ArchModuleDto {
                id: "ports".into(),
                name: "Ports".into(),
                layer: "ports".into(),
                role: "OS boundary traits only".into(),
            },
        ];
        let edges = vec![
            ArchEdgeDto {
                from: "ui".into(),
                to: "command".into(),
                kind: "invoke".into(),
            },
            ArchEdgeDto {
                from: "command".into(),
                to: "dispatch_host".into(),
                kind: "dispatch".into(),
            },
            ArchEdgeDto {
                from: "dispatch_host".into(),
                to: "core".into(),
                kind: "domain".into(),
            },
            ArchEdgeDto {
                from: "dispatch_host".into(),
                to: "flow".into(),
                kind: "domain".into(),
            },
            ArchEdgeDto {
                from: "dispatch_host".into(),
                to: "exec".into(),
                kind: "domain".into(),
            },
            ArchEdgeDto {
                from: "dispatch_host".into(),
                to: "work".into(),
                kind: "domain".into(),
            },
            ArchEdgeDto {
                from: "dispatch_host".into(),
                to: "evid".into(),
                kind: "domain".into(),
            },
            ArchEdgeDto {
                from: "core".into(),
                to: "ports".into(),
                kind: "port".into(),
            },
            ArchEdgeDto {
                from: "exec".into(),
                to: "ports".into(),
                kind: "port".into(),
            },
            ArchEdgeDto {
                from: "work".into(),
                to: "ports".into(),
                kind: "port".into(),
            },
        ];
        let empty = modules.is_empty();
        ArchProjectionDto {
            status: if empty {
                "empty".into()
            } else {
                "ok".into()
            },
            live: !empty,
            source: "dispatch_host.arch_get_projection".into(),
            modules,
            edges,
            generation: self.engine.generation(),
        }
    }

    fn spec_projection_dto(&self) -> SpecProjectionDto {
        if !self.spec_loaded {
            return SpecProjectionDto {
                loaded: false,
                module_id: String::new(),
                module_name: String::new(),
                responsibility: String::new(),
                revisions: vec![],
                evidence_refs: vec![],
                evidence_needing_revalidation: 0,
            };
        }
        let p = self.spec.projection();
        SpecProjectionDto {
            loaded: true,
            module_id: p.module_id,
            module_name: p.module_name,
            responsibility: p.responsibility,
            revisions: p
                .revisions
                .into_iter()
                .map(|r| SpecRevisionSummaryDto {
                    id: r.id,
                    version_label: r.version_label,
                    status: approval_status_str(r.status).into(),
                    contract_count: r.contract_count,
                    content_hash: r.content_hash,
                })
                .collect(),
            evidence_refs: p
                .evidence_refs
                .into_iter()
                .map(|e| SpecEvidenceRefDto {
                    id: e.id,
                    bound_revision_id: e.bound_revision_id,
                    validity: evidence_validity_str(e.validity).into(),
                })
                .collect(),
            evidence_needing_revalidation: p.evidence_needing_revalidation,
        }
    }

    fn board_view(&self) -> BoardView {
        let snap = self.engine.snapshot();
        let mut tasks = Vec::new();
        for id in self.engine.task_ids() {
            if let Some(rec) = sgenaxis_core::task_from_store(self.engine.property_store(), &id) {
                let bdd = self
                    .required_bdd
                    .get(&rec.id)
                    .cloned()
                    .unwrap_or_default();
                let tdd = self
                    .required_tdd
                    .get(&rec.id)
                    .cloned()
                    .unwrap_or_default();
                tasks.push(TaskView {
                    id: rec.id,
                    title: rec.title,
                    zone: rec.zone.as_str().to_string(),
                    bdd,
                    tdd,
                });
            }
        }

        let titles_by_zone: Vec<ZoneTitles> = snap
            .titles_by_zone
            .iter()
            .map(|(z, titles)| ZoneTitles {
                zone: (*z).to_string(),
                titles: titles.clone(),
            })
            .collect();

        BoardView {
            generation: self.engine.generation(),
            gray: snap.gray,
            blue: snap.blue,
            yellow: snap.yellow,
            red: snap.red,
            green: snap.green,
            titles: snap.titles,
            titles_by_zone,
            tasks,
            active_run_id: self.active_run_id,
        }
    }
}

/// PD-EXEC-BIND-01 seam: reject missing／blank bind fields with a stable message.
fn require_arg_field(name: &str, value: Option<&str>) -> Result<String, String> {
    match value.map(str::trim).filter(|s| !s.is_empty()) {
        Some(s) => Ok(s.to_string()),
        None => Err(format!("start_run missing binding field: {name}")),
    }
}

/// PD-REMAIN-WORK-TAGS-01: non-empty trimmed work item ids (deduped, stable order).
fn normalize_work_item_ids(raw: &[String]) -> Result<Vec<String>, String> {
    if raw.is_empty() {
        return Err("非法批次標籤：未指定工項".into());
    }
    let mut out = Vec::new();
    for id in raw {
        let s = id.trim();
        if s.is_empty() {
            return Err("非法批次標籤：工項 id 空白".into());
        }
        if !out.iter().any(|x| x == s) {
            out.push(s.to_string());
        }
    }
    Ok(out)
}

/// PD-REMAIN-WORK-TAGS-01: trim／dedupe tags; reject blank／control／comma-embedded.
fn normalize_tag_list(kind: &str, raw: &[String]) -> Result<Vec<String>, String> {
    let mut out = Vec::new();
    for t in raw {
        let s = t.trim();
        if s.is_empty() {
            return Err(format!("非法{kind}標籤：空白"));
        }
        if s.chars().any(|c| c.is_control() || c == ',' || c.is_whitespace()) {
            return Err(format!("非法{kind}標籤：{s}"));
        }
        if !s
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_' || c == '/')
        {
            return Err(format!("非法{kind}標籤：{s}"));
        }
        if !out.iter().any(|x| x == s) {
            out.push(s.to_string());
        }
    }
    Ok(out)
}

fn parse_zone(s: &str) -> Result<Zone, String> {
    Zone::parse(s)
        .or_else(|| ZoneDto::parse(s).and_then(|d| Zone::parse(d.as_str())))
        .ok_or_else(|| format!("invalid zone: {s}"))
}

fn map_spec_err(e: SpecError) -> String {
    e.to_string()
}

fn approval_status_str(s: ApprovalStatus) -> &'static str {
    match s {
        ApprovalStatus::Draft => "draft",
        ApprovalStatus::Approved => "approved",
    }
}

fn evidence_validity_str(v: EvidenceValidity) -> &'static str {
    match v {
        EvidenceValidity::Valid => "valid",
        EvidenceValidity::NeedsRevalidation => "needs_revalidation",
    }
}

fn revision_to_dto(rev: &sgenaxis_spec::SpecRevision) -> SpecRevisionDto {
    let immutable = rev.status == ApprovalStatus::Approved;
    SpecRevisionDto {
        id: rev.id.clone(),
        module_id: rev.module_id.clone(),
        version_label: rev.version_label.clone(),
        status: approval_status_str(rev.status).into(),
        content_hash: rev.content_hash.clone(),
        contracts: rev
            .contracts
            .iter()
            .map(|c| SpecContractDto {
                id: c.id.clone(),
                title: c.title.clone(),
                body: c.body.clone(),
            })
            .collect(),
        immutable,
    }
}

fn chunk_to_dto(c: AgentChunk) -> ChunkDto {
    match c {
        AgentChunk::Started {
            run_id,
            provider,
            dry_run,
            tool,
        } => ChunkDto::Started {
            run_id: run_id.0,
            provider: match provider {
                AgentProvider::Cli => ProviderDto::Cli,
                AgentProvider::Mcp => ProviderDto::Mcp,
            },
            dry_run,
            tool: tool.map(|t| t.config_key().to_string()),
        },
        AgentChunk::Chunk {
            run_id,
            stream,
            text,
        } => ChunkDto::Chunk {
            run_id: run_id.0,
            stream: match stream {
                OutputStream::Stdout => "stdout".into(),
                OutputStream::Stderr => "stderr".into(),
            },
            text,
        },
        AgentChunk::Progress { run_id, message } => ChunkDto::Progress {
            run_id: run_id.0,
            message,
        },
        AgentChunk::Exited {
            run_id,
            classification,
            exit_code,
        } => ChunkDto::Exited {
            run_id: run_id.0,
            classification: match classification {
                ExitClassification::Success => "success".into(),
                ExitClassification::Failure => "failure".into(),
                ExitClassification::Cancelled => "cancelled".into(),
                ExitClassification::Crashed => "crashed".into(),
            },
            exit_code,
        },
        AgentChunk::Failed { run_id, message } => ChunkDto::Failed {
            run_id: run_id.0,
            message,
        },
    }
}

// ─── GUARD-S1 PRIVATE POLICY (PD-RUST-GUARD-POLICY-IMPLEMENT-01) ─────────────
// Private HOST authority ownership; pure policy bodies only (GC／GB).
// Does not prove real native／ACL／FS／capture／EXEC. Not a second Manager.

/// Host-resolved task intent (never deserialized from caller authority fields).
#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GuardHostIntent {
    Unknown,
    Generic,
    Implementation,
}

/// Private authority errors for formal RED assertions.
/// `NotReady` is a skeleton stub marker only — not a shipping IPC contract.
#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GuardAuthorityError {
    NotReady,
    AuthorityDenied,
    IntentUnknown,
    RequiresApproval,
    MissingRecord,
    Stale(&'static str),
    Revoked,
    Consumed,
    RedUnqualified,
    InvalidManifest,
    NativeDeclined,
}

/// Binding snapshot fields owned by HOST (GC04).
#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct GuardSnapshot {
    pub task: String,
    pub module: String,
    pub project: String,
    pub root: String,
    pub input_fp: String,
    pub architecture: String,
    pub bdd: String,
    pub skeleton: String,
    pub envelope: String,
    pub red_id: String,
    pub test_manifest: String,
}

#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GuardApprovalStatus {
    Approved,
    Consumed,
    Revoked,
}

#[allow(dead_code)]
#[derive(Clone, Debug)]
pub(crate) struct GuardApproval {
    pub session: u64,
    pub id: u64,
    pub binding: GuardSnapshot,
    pub status: GuardApprovalStatus,
}

/// Machine capture facts produced by HOST adapters — never caller JSON.
#[allow(dead_code)]
#[derive(Clone, Debug)]
pub(crate) struct GuardCaptureFacts {
    pub host_owned: bool,
    pub build_ok: bool,
    pub case_id: String,
    pub expected_case_id: String,
    pub case_executed: bool,
    pub case_ignored: bool,
    pub case_failed: bool,
    pub exit_code: i32,
    pub dual_eof: bool,
    pub stream_error: bool,
    pub same_snapshot: bool,
    pub owner_qualifies: bool,
}

#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct GuardManifestEntry {
    pub relative_path: String,
    pub sha256: String,
}

/// Private native observation from Rust-controlled rfd — must not become invoke DTO.
#[allow(dead_code)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum GuardNativeObservation {
    Yes,
    No,
    Cancel,
}

#[allow(dead_code)]
#[derive(Clone, Debug)]
pub(crate) struct GuardPending {
    pub nonce: u64,
    pub binding: GuardSnapshot,
    pub revoked: bool,
}

/// Private session authority record owned by [`DispatchHost`].
#[allow(dead_code)]
#[derive(Clone, Debug, Default)]
pub(crate) struct GuardSessionState {
    pub boot: u64,
    pub approval: Option<GuardApproval>,
    pub pending: Option<GuardPending>,
}

#[derive(Clone, Debug)]
struct GuardCandidateRecord {
    task_id: String,
    draft: Option<CandidateDraft>,
    binding: GuardSnapshot,
    confirmed: bool,
    capture_attempted: bool,
    mechanical_capture: Option<GuardMechanicalCapture>,
    pending_qualification: Option<GuardPendingQualification>,
    qualified_red: Option<GuardQualifiedRed>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct GuardRedQualificationPrompt {
    pub candidate_ref: u64,
    pub producer_id: u64,
    pub bdd_id: String,
    pub test_id: String,
    pub artifact_sha256: String,
    pub observed_case_line: String,
    pub failure_summary_line: String,
    pub bdd_text: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct GuardPendingQualification {
    producer_id: u64,
    binding: GuardSnapshot,
    artifact_sha256: String,
    test_id: String,
    bdd_id: String,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct GuardQualifiedRed {
    pub id: u64,
    pub binding: GuardSnapshot,
    pub producer_id: u64,
    pub test_id: String,
    pub bdd_id: String,
    pub artifact_sha256: String,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum GuardCaptureStage {
    BuildOnly,
    ExactTest,
}

#[derive(Clone, Debug, PartialEq, Eq)]
struct GuardCaptureProcessSlot {
    candidate_ref: u64,
    process_id: sgenaxis_ports::ProcessId,
    stage: GuardCaptureStage,
}

/// HOST-produced mechanical facts only; a separate native owner action must
/// still attest that the observed case failure matches the approved BDD.
#[derive(Clone, PartialEq, Eq)]
pub(crate) struct GuardMechanicalCapture {
    pub producer_id: u64,
    pub artifact_path: String,
    pub artifact_sha256: String,
    /// Exact Cargo JSON record selecting this executable; retained privately
    /// so later qualification can inspect the precise producer evidence.
    selected_artifact_record: String,
    pub target: String,
    pub test_id: String,
    pub build_exit_code: i32,
    pub test_exit_code: i32,
    pub dual_eof: bool,
    pub inputs_unchanged: bool,
    pub input_fingerprint: String,
    pub input_artifact_fingerprints: BTreeMap<String, String>,
    /// Raw exact-case diagnostics stay private in HOST memory; never serialize
    /// or project these fields through EVID/IPC/UI.
    observed_case_line: Option<String>,
    failure_summary_line: Option<String>,
    raw_test_stdout: String,
    raw_test_stderr: String,
    build_stdout_sha256: String,
    build_stderr_sha256: String,
}

impl std::fmt::Debug for GuardMechanicalCapture {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        formatter.debug_struct("GuardMechanicalCapture")
            .field("producer_id", &self.producer_id)
            .field("artifact_path", &self.artifact_path)
            .field("artifact_sha256", &self.artifact_sha256)
            .field("selected_artifact_record", &"<private Cargo record>")
            .field("target", &self.target)
            .field("test_id", &self.test_id)
            .field("build_exit_code", &self.build_exit_code)
            .field("test_exit_code", &self.test_exit_code)
            .field("dual_eof", &self.dual_eof)
            .field("inputs_unchanged", &self.inputs_unchanged)
            .field("input_fingerprint", &self.input_fingerprint)
            .field("input_artifact_fingerprints", &self.input_artifact_fingerprints)
            .field("build_stdout_sha256", &self.build_stdout_sha256)
            .field("build_stderr_sha256", &self.build_stderr_sha256)
            .finish_non_exhaustive()
    }
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GuardCaptureError {
    ConsentDeclined,
    MissingCandidate,
    CandidateNotConfirmed,
    CleanupPending,
    TimedOut,
    ProcessStart,
    ProcessObservation,
    BuildFailed,
    ArtifactMissing,
    ArtifactAmbiguous,
    ArtifactUnreadable,
    ArtifactChanged,
    TargetMismatch,
    CaseNotObserved,
    StreamIncomplete,
    InputStale,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GuardCandidateError {
    NotReady,
    InvalidCandidate,
    UnknownTask,
    ProjectNotFound,
    ProjectReadFailure,
    Snapshot(GuardSnapshotProducerError),
    Authority(GuardAuthorityError),
    Capture(GuardCaptureError),
}

impl DispatchHost {
    /// Prepare a HOST-owned generic-intent candidate without reading project
    /// files. A native Yes records intent only; it does not create approval.
    pub(crate) fn guard_prepare_generic_classification(
        &mut self,
        task_id: &str,
    ) -> Result<u64, GuardCandidateError> {
        if task_id.trim().is_empty() || !self.engine.task_ids().iter().any(|id| id == task_id) {
            return Err(GuardCandidateError::UnknownTask);
        }
        if self.guard_authority.pending.is_some()
            || self.guard_next_candidate >= GUARD_JS_SAFE_INTEGER_MAX
        {
            return Err(GuardCandidateError::InvalidCandidate);
        }

        let candidate_ref = self.guard_next_candidate.checked_add(1)
            .filter(|reference| *reference <= GUARD_JS_SAFE_INTEGER_MAX)
            .ok_or(GuardCandidateError::InvalidCandidate)?;
        self.guard_next_candidate = candidate_ref;
        let binding = GuardSnapshot {
            task: task_id.to_owned(),
            module: String::new(),
            project: String::new(),
            root: String::new(),
            input_fp: String::new(),
            architecture: String::new(),
            bdd: String::new(),
            skeleton: String::new(),
            envelope: String::new(),
            red_id: String::new(),
            test_manifest: String::new(),
        };
        self.guard_authority.pending = Some(GuardPending {
            nonce: candidate_ref,
            binding: binding.clone(),
            revoked: false,
        });
        self.guard_candidates.insert(candidate_ref, GuardCandidateRecord {
            task_id: task_id.to_owned(),
            draft: None,
            binding,
            confirmed: false,
            capture_attempted: false,
            mechanical_capture: None,
            pending_qualification: None,
            qualified_red: None,
        });
        Ok(candidate_ref)
    }

    /// Prepare an implementation candidate from HOST-owned project state.
    /// Native confirmation is a separate callback and never supplied by DTO.
    pub(crate) fn guard_prepare_candidate(
        &mut self,
        task_id: &str,
        draft: &CandidateDraft,
    ) -> Result<u64, GuardCandidateError> {
        if task_id.trim().is_empty() || !self.engine.task_ids().iter().any(|id| id == task_id) {
            return Err(GuardCandidateError::UnknownTask);
        }
        if self.guard_authority.pending.is_some()
            || self.guard_next_candidate >= GUARD_JS_SAFE_INTEGER_MAX
            || draft.module_id.trim().is_empty()
            || draft.project_id.trim().is_empty()
            || draft.manifest_revision.trim().is_empty()
            || draft.module_id != draft.envelope.primary_module
            || draft.envelope.allowed_patterns.is_empty()
            || draft.envelope.allowed_patterns.iter().any(|p| p.trim().is_empty())
            || draft.red_job.program.trim().is_empty()
            || !std::path::Path::new(&draft.red_job.program).is_absolute()
            || draft.red_job.build_argv.is_empty()
            || draft.red_job.build_argv.iter().any(|arg| arg.is_empty() || arg.contains('\0'))
            || draft.red_job.cwd_ref.trim().is_empty()
            || draft.red_job.test_target.trim().is_empty()
            || draft.red_job.test_id.trim().is_empty()
            || draft.red_job.bdd_id.trim().is_empty()
            || draft.red_job.timeout_ms != 120_000
        {
            return Err(GuardCandidateError::InvalidCandidate);
        }
        let project_id = sgenaxis_work::ProjectId::new(draft.project_id.clone());
        let project = self.work.get_project(&project_id)
            .map_err(|_| GuardCandidateError::ProjectReadFailure)?
            .ok_or(GuardCandidateError::ProjectNotFound)?;
        if !guard_capture_cwd_is_within_root(&draft.red_job.cwd_ref, &project.root) {
            return Err(GuardCandidateError::InvalidCandidate);
        }
        let manifest = GuardInputManifest {
            revision: draft.manifest_revision.clone(),
            inputs: draft.input_paths.clone(),
            architecture: draft.architecture_paths.clone(),
            bdd: draft.bdd_paths.clone(),
            skeleton: draft.skeleton_paths.clone(),
            tests: draft.test_paths.clone(),
        };
        let snapshot = guard_current_byte_snapshot(self.guard_input_fs.as_ref(), &project.root, &manifest)
            .map_err(GuardCandidateError::Snapshot)?;
        let envelope_bytes = serde_json::to_vec(&draft.envelope)
            .map_err(|_| GuardCandidateError::InvalidCandidate)?;
        let candidate_ref = self.guard_next_candidate.checked_add(1)
            .filter(|reference| *reference <= GUARD_JS_SAFE_INTEGER_MAX)
            .ok_or(GuardCandidateError::InvalidCandidate)?;
        self.guard_next_candidate = candidate_ref;
        let binding = GuardSnapshot {
            task: task_id.into(),
            module: draft.module_id.clone(),
            project: draft.project_id.clone(),
            root: project.root,
            input_fp: snapshot.manifest_fingerprint,
            architecture: snapshot.artifact_digests.get("architecture").cloned().unwrap_or_default(),
            bdd: snapshot.artifact_digests.get("bdd").cloned().unwrap_or_default(),
            skeleton: snapshot.artifact_digests.get("skeleton").cloned().unwrap_or_default(),
            envelope: sgenaxis_spec::packet::source_sha256(&envelope_bytes),
            red_id: String::new(),
            test_manifest: snapshot.artifact_digests.get("tests").cloned().unwrap_or_default(),
        };
        self.guard_authority.pending = Some(GuardPending {
            nonce: candidate_ref,
            binding: binding.clone(),
            revoked: false,
        });
        self.guard_candidates.insert(candidate_ref, GuardCandidateRecord {
            task_id: task_id.into(),
            draft: Some(draft.clone()),
            binding,
            confirmed: false,
            capture_attempted: false,
            mechanical_capture: None,
            pending_qualification: None,
            qualified_red: None,
        });
        Ok(candidate_ref)
    }

    /// Re-read the exact source declaration after the native callback before commit.
    pub(crate) fn guard_complete_candidate_confirmation(
        &mut self,
        candidate_ref: u64,
        observation: GuardNativeObservation,
    ) -> Result<(), GuardCandidateError> {
        let candidate = self.guard_candidates.get(&candidate_ref)
            .cloned()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord))?;
        let pending = self.guard_authority.pending.as_ref()
            .filter(|pending| pending.nonce == candidate_ref)
            .cloned()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord))?;
        if pending.revoked {
            self.guard_authority.pending = None;
            self.guard_candidates.remove(&candidate_ref);
            return Err(GuardCandidateError::Authority(GuardAuthorityError::Revoked));
        }

        // A native denial is final for this one-shot candidate. Do not let an
        // unrelated source read failure strand the pending nonce.
        if matches!(observation, GuardNativeObservation::No | GuardNativeObservation::Cancel) {
            self.guard_authority.pending = None;
            self.guard_candidates.remove(&candidate_ref);
            return Err(GuardCandidateError::Authority(GuardAuthorityError::NativeDeclined));
        }

        // The task projection can change while the native dialog is open.
        // Revalidate the HOST-owned task for every affirmative intent before
        // committing either a generic classification or implementation intent.
        if !self.engine.task_ids().iter().any(|id| id == &candidate.task_id) {
            self.guard_authority.pending = None;
            self.guard_candidates.remove(&candidate_ref);
            return Err(GuardCandidateError::UnknownTask);
        }

        let Some(draft) = candidate.draft.as_ref() else {
            self.guard_authority.pending = None;
            if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
                record.confirmed = true;
            }
            self.guard_intents.insert(candidate.task_id, GuardHostIntent::Generic);
            return Ok(());
        };

        let project_id = sgenaxis_work::ProjectId::new(draft.project_id.clone());
        let manifest = GuardInputManifest {
            revision: draft.manifest_revision.clone(),
            inputs: draft.input_paths.clone(),
            architecture: draft.architecture_paths.clone(),
            bdd: draft.bdd_paths.clone(),
            skeleton: draft.skeleton_paths.clone(),
            tests: draft.test_paths.clone(),
        };
        let recheck = (|| {
            let current = self.guard_project_input_snapshot(&project_id, &manifest)
                .map_err(|error| match error {
                GuardProjectSnapshotError::NotReady => GuardCandidateError::NotReady,
                GuardProjectSnapshotError::ProjectNotFound => GuardCandidateError::ProjectNotFound,
                GuardProjectSnapshotError::ProjectReadFailure(_) => GuardCandidateError::ProjectReadFailure,
                GuardProjectSnapshotError::Snapshot(error) => GuardCandidateError::Snapshot(error),
                })?;
            let project = self.work.get_project(&project_id)
                .map_err(|_| GuardCandidateError::ProjectReadFailure)?
                .ok_or(GuardCandidateError::ProjectNotFound)?;
            let mut current_binding = candidate.binding.clone();
            current_binding.root = project.root;
            current_binding.input_fp = current.manifest_fingerprint;
            current_binding.architecture = current.artifact_digests.get("architecture").cloned().unwrap_or_default();
            current_binding.bdd = current.artifact_digests.get("bdd").cloned().unwrap_or_default();
            current_binding.skeleton = current.artifact_digests.get("skeleton").cloned().unwrap_or_default();
            current_binding.test_manifest = current.artifact_digests.get("tests").cloned().unwrap_or_default();
            Ok::<GuardSnapshot, GuardCandidateError>(current_binding)
        })();
        let current_binding = match recheck {
            Ok(binding) => binding,
            Err(error) => {
                // Affirmative confirmation with unavailable evidence fails
                // closed and consumes this exact one-shot pending record.
                self.guard_authority.pending = None;
                self.guard_candidates.remove(&candidate_ref);
                return Err(error);
            }
        };
        if let Some(field) = guard_binding_stale_field(&pending.binding, &current_binding) {
            self.guard_authority.pending = None;
            self.guard_candidates.remove(&candidate_ref);
            return Err(GuardCandidateError::Authority(GuardAuthorityError::Stale(field)));
        }

        self.guard_authority.pending = None;
        if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
            record.confirmed = true;
        }
        self.guard_intents.insert(candidate.task_id, GuardHostIntent::Implementation);
        Ok(())
    }

    /// Collect a bounded build-only and exact-case mechanical capture after a
    /// Rust-controlled native side-effect confirmation. It cannot approve RED.
    pub(crate) fn guard_capture_red(
        &mut self,
        candidate_ref: u64,
        consent: GuardNativeObservation,
    ) -> Result<GuardMechanicalCapture, GuardCandidateError> {
        self.guard_capture_red_at(candidate_ref, consent, std::time::Instant::now)
    }

    /// Snapshot the exact mechanically captured RED and declared BDD text for
    /// a separate native semantic-qualification prompt.
    pub(crate) fn guard_prepare_red_qualification(
        &mut self,
        candidate_ref: u64,
    ) -> Result<GuardRedQualificationPrompt, GuardCandidateError> {
        let candidate = self.guard_candidates.get(&candidate_ref)
            .cloned()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord))?;
        let draft = candidate.draft.as_ref()
            .ok_or(GuardCandidateError::Capture(GuardCaptureError::MissingCandidate))?;
        if !candidate.confirmed
            || self.guard_intents.get(&candidate.task_id) != Some(&GuardHostIntent::Implementation)
            || !self.engine.task_ids().iter().any(|id| id == &candidate.task_id)
        {
            return Err(GuardCandidateError::Capture(GuardCaptureError::CandidateNotConfirmed));
        }
        let capture = candidate.mechanical_capture.as_ref()
            .ok_or(GuardCandidateError::Capture(GuardCaptureError::MissingCandidate))?;
        if capture.build_exit_code != 0
            || capture.test_exit_code == 0
            || !capture.dual_eof
            || !capture.inputs_unchanged
            || capture.observed_case_line.as_deref() != Some(format!("test {} ... FAILED", capture.test_id).as_str())
            || capture.failure_summary_line.as_deref().map_or(true, str::is_empty)
            || capture.selected_artifact_record.is_empty()
            || capture.target != draft.red_job.test_target
            || capture.test_id != draft.red_job.test_id
            || capture.input_fingerprint != candidate.binding.input_fp
            || capture.input_artifact_fingerprints.get("architecture") != Some(&candidate.binding.architecture)
            || capture.input_artifact_fingerprints.get("bdd") != Some(&candidate.binding.bdd)
            || capture.input_artifact_fingerprints.get("skeleton") != Some(&candidate.binding.skeleton)
            || capture.input_artifact_fingerprints.get("envelope") != Some(&candidate.binding.envelope)
            || capture.input_artifact_fingerprints.get("tests") != Some(&candidate.binding.test_manifest)
        {
            return Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified));
        }
        if candidate.pending_qualification.is_some() {
            return Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified));
        }

        let current_before = self.guard_qualification_current_binding(&candidate)?;
        if let Some(field) = guard_binding_stale_field(&candidate.binding, &current_before) {
            return Err(GuardCandidateError::Authority(GuardAuthorityError::Stale(field)));
        }
        let artifact_bytes = self.guard_input_fs.read(&capture.artifact_path)
            .map_err(|_| GuardCandidateError::Capture(GuardCaptureError::ArtifactUnreadable))?;
        if sgenaxis_spec::packet::source_sha256(&artifact_bytes) != capture.artifact_sha256 {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactChanged));
        }
        let mut bdd_text = String::new();
        for path in &draft.bdd_paths {
            let root = candidate.binding.root.trim_end_matches(|character| character == '/' || character == '\\');
            let full_path = format!("{root}/{path}");
            let bytes = self.guard_input_fs.read(&full_path)
                .map_err(|_| GuardCandidateError::Capture(GuardCaptureError::InputStale))?;
            let text = String::from_utf8(bytes)
                .map_err(|_| GuardCandidateError::Capture(GuardCaptureError::InputStale))?;
            if !bdd_text.is_empty() { bdd_text.push_str("\n\n"); }
            bdd_text.push_str(&format!("# {path}\n{text}"));
        }
        let current_after = self.guard_qualification_current_binding(&candidate)?;
        if let Some(field) = guard_binding_stale_field(&candidate.binding, &current_after) {
            return Err(GuardCandidateError::Authority(GuardAuthorityError::Stale(field)));
        }
        let artifact_after_prompt_read = self.guard_input_fs.read(&capture.artifact_path)
            .map_err(|_| GuardCandidateError::Capture(GuardCaptureError::ArtifactUnreadable))?;
        if sgenaxis_spec::packet::source_sha256(&artifact_after_prompt_read) != capture.artifact_sha256 {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactChanged));
        }

        let prompt = GuardRedQualificationPrompt {
            candidate_ref,
            producer_id: capture.producer_id,
            bdd_id: draft.red_job.bdd_id.clone(),
            test_id: capture.test_id.clone(),
            artifact_sha256: capture.artifact_sha256.clone(),
            observed_case_line: capture.observed_case_line.clone().unwrap_or_default(),
            failure_summary_line: capture.failure_summary_line.clone().unwrap_or_default(),
            bdd_text,
        };
        let pending = GuardPendingQualification {
            producer_id: capture.producer_id,
            binding: candidate.binding.clone(),
            artifact_sha256: capture.artifact_sha256.clone(),
            test_id: capture.test_id.clone(),
            bdd_id: draft.red_job.bdd_id.clone(),
        };
        if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
            record.pending_qualification = Some(pending);
            record.qualified_red = None;
        }
        Ok(prompt)
    }

    /// Complete one native qualification callback bound to the exact producer
    /// capture shown to the owner. This records qualification only, not approval.
    pub(crate) fn guard_complete_red_qualification(
        &mut self,
        candidate_ref: u64,
        producer_id: u64,
        observation: GuardNativeObservation,
    ) -> Result<GuardQualifiedRed, GuardCandidateError> {
        let candidate = self.guard_candidates.get(&candidate_ref)
            .cloned()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord))?;
        let pending = candidate.pending_qualification.as_ref()
            .filter(|pending| pending.producer_id == producer_id)
            .cloned()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified))?;
        if matches!(observation, GuardNativeObservation::No | GuardNativeObservation::Cancel) {
            if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
                record.pending_qualification = None;
                record.qualified_red = None;
            }
            return Err(GuardCandidateError::Authority(GuardAuthorityError::NativeDeclined));
        }
        let Some(draft) = candidate.draft.as_ref() else {
            self.guard_clear_pending_qualification(candidate_ref);
            return Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified));
        };
        let Some(capture) = candidate.mechanical_capture.as_ref() else {
            self.guard_clear_pending_qualification(candidate_ref);
            return Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified));
        };
        if !candidate.confirmed
            || self.guard_intents.get(&candidate.task_id) != Some(&GuardHostIntent::Implementation)
            || !self.engine.task_ids().iter().any(|id| id == &candidate.task_id)
            || capture.producer_id != producer_id
            || capture.artifact_sha256 != pending.artifact_sha256
            || capture.test_id != pending.test_id
            || draft.red_job.bdd_id != pending.bdd_id
            || candidate.binding != pending.binding
        {
            if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
                record.pending_qualification = None;
                record.qualified_red = None;
            }
            return Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified));
        }
        let current = match self.guard_qualification_current_binding(&candidate) {
            Ok(current) => current,
            Err(error) => {
                self.guard_clear_pending_qualification(candidate_ref);
                return Err(error);
            }
        };
        if let Some(field) = guard_binding_stale_field(&pending.binding, &current) {
            if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
                record.pending_qualification = None;
                record.qualified_red = None;
            }
            return Err(GuardCandidateError::Authority(GuardAuthorityError::Stale(field)));
        }
        let artifact_bytes = match self.guard_input_fs.read(&capture.artifact_path) {
            Ok(bytes) => bytes,
            Err(_) => {
                self.guard_clear_pending_qualification(candidate_ref);
                return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactUnreadable));
            }
        };
        if sgenaxis_spec::packet::source_sha256(&artifact_bytes) != pending.artifact_sha256 {
            if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
                record.pending_qualification = None;
                record.qualified_red = None;
            }
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactChanged));
        }
        let mut binding = current;
        binding.red_id = producer_id.to_string();
        let qualified = GuardQualifiedRed {
            id: producer_id,
            binding,
            producer_id,
            test_id: capture.test_id.clone(),
            bdd_id: draft.red_job.bdd_id.clone(),
            artifact_sha256: capture.artifact_sha256.clone(),
        };
        let Some(record) = self.guard_candidates.get_mut(&candidate_ref) else {
            return Err(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord));
        };
        record.pending_qualification = None;
        record.qualified_red = Some(qualified.clone());
        Ok(qualified)
    }

    /// Return the current private qualification record to the separately
    /// authorized final-approval path; never expose mechanical/raw diagnostics.
    pub(crate) fn guard_qualified_red_for_approval(
        &self,
        candidate_ref: u64,
    ) -> Result<GuardQualifiedRed, GuardCandidateError> {
        let candidate = self.guard_candidates.get(&candidate_ref)
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::MissingRecord))?;
        let qualified = candidate.qualified_red.as_ref()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified))?;
        let capture = candidate.mechanical_capture.as_ref()
            .ok_or(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified))?;
        let mut unqualified_binding = qualified.binding.clone();
        unqualified_binding.red_id.clear();
        if !candidate.confirmed
            || self.guard_intents.get(&candidate.task_id) != Some(&GuardHostIntent::Implementation)
            || !self.engine.task_ids().iter().any(|id| id == &candidate.task_id)
            || capture.producer_id != qualified.producer_id
            || capture.artifact_sha256 != qualified.artifact_sha256
            || capture.test_id != qualified.test_id
            || unqualified_binding != candidate.binding
            || qualified.id != qualified.producer_id
        {
            return Err(GuardCandidateError::Authority(GuardAuthorityError::RedUnqualified));
        }
        Ok(qualified.clone())
    }

    fn guard_clear_pending_qualification(&mut self, candidate_ref: u64) {
        if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
            record.pending_qualification = None;
            record.qualified_red = None;
        }
    }

    /// Deterministic monotonic-clock seam for production-bound ProcessPort tests.
    fn guard_capture_red_at<F>(
        &mut self,
        candidate_ref: u64,
        consent: GuardNativeObservation,
        mut now: F,
    ) -> Result<GuardMechanicalCapture, GuardCandidateError>
    where
        F: FnMut() -> std::time::Instant,
    {
        if self.guard_capture_process.is_some() {
            self.guard_capture_drain_pending_once();
            return Err(GuardCandidateError::Capture(GuardCaptureError::CleanupPending));
        }
        if consent != GuardNativeObservation::Yes {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ConsentDeclined));
        }
        let Some(candidate) = self.guard_candidates.get(&candidate_ref).cloned() else {
            return Err(GuardCandidateError::Capture(GuardCaptureError::MissingCandidate));
        };
        let Some(draft) = candidate.draft.clone() else {
            return Err(GuardCandidateError::Capture(GuardCaptureError::MissingCandidate));
        };
        if !candidate.confirmed
            || self.guard_intents.get(&candidate.task_id) != Some(&GuardHostIntent::Implementation)
        {
            return Err(GuardCandidateError::Capture(GuardCaptureError::CandidateNotConfirmed));
        }
        if !self.engine.task_ids().iter().any(|task_id| task_id == &candidate.task_id) {
            return Err(GuardCandidateError::UnknownTask);
        }
        if !guard_capture_draft_is_safe(&draft, &candidate.binding.root) {
            return Err(GuardCandidateError::InvalidCandidate);
        }
        let started = now();
        let deadline = started + std::time::Duration::from_millis(120_000);
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let before = self.guard_capture_current_binding(&candidate, deadline, &mut now)?;
        if guard_binding_stale_field(&candidate.binding, &before).is_some() {
            return Err(GuardCandidateError::Capture(GuardCaptureError::InputStale));
        }

        // One explicit native Yes starts one bounded capture attempt. We never
        // retry a process within this request; a later explicit request needs
        // a fresh prompt and may only begin after any retained process drains.
        if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
            record.capture_attempted = true;
            record.mechanical_capture = None;
            record.pending_qualification = None;
            record.qualified_red = None;
        }
        let producer_id = self.guard_next_capture_id.checked_add(1)
            .ok_or(GuardCandidateError::Capture(GuardCaptureError::ProcessObservation))?;
        self.guard_next_capture_id = producer_id;
        let build_args = draft.red_job.build_argv.iter().map(String::as_str).collect::<Vec<_>>();
        let build = self.guard_run_capture_process(
            candidate_ref,
            GuardCaptureStage::BuildOnly,
            &draft.red_job.program,
            &build_args,
            Some(&draft.red_job.cwd_ref),
            deadline,
            &mut now,
        )?;
        if build.exit_code != 0 {
            return Err(GuardCandidateError::Capture(GuardCaptureError::BuildFailed));
        }

        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let selected_artifact = guard_capture_select_artifact(
            &build.stdout,
            &draft.red_job.test_target,
            &candidate.binding.root,
            deadline,
            &mut now,
        )?;
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let artifact_before = self.guard_input_fs.read(&selected_artifact.path)
            .map_err(|error| GuardCandidateError::Capture(match error {
                PortError::NotFound(_) => GuardCaptureError::ArtifactMissing,
                _ => GuardCaptureError::ArtifactUnreadable,
            }))?;
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let artifact_sha256 = sgenaxis_spec::packet::source_sha256(&artifact_before);
        let exact_args = ["--exact", draft.red_job.test_id.as_str(), "--nocapture"];
        let test = self.guard_run_capture_process(
            candidate_ref,
            GuardCaptureStage::ExactTest,
            &selected_artifact.path,
            &exact_args,
            Some(&draft.red_job.cwd_ref),
            deadline,
            &mut now,
        )?;
        let observed_failure = if test.exit_code != 0 {
            guard_capture_exact_case_failure(&test.stdout, &draft.red_job.test_id, deadline, &mut now)
                .map_err(GuardCandidateError::Capture)?
        } else {
            None
        };
        let Some(observed_failure) = observed_failure else {
            return Err(GuardCandidateError::Capture(GuardCaptureError::CaseNotObserved));
        };
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let artifact_after = self.guard_input_fs.read(&selected_artifact.path)
            .map_err(|error| GuardCandidateError::Capture(match error {
                PortError::NotFound(_) => GuardCaptureError::ArtifactMissing,
                _ => GuardCaptureError::ArtifactUnreadable,
            }))?;
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        if sgenaxis_spec::packet::source_sha256(&artifact_after) != artifact_sha256 {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactChanged));
        }
        let after = self.guard_capture_current_binding(&candidate, deadline, &mut now)?;
        if guard_binding_stale_field(&candidate.binding, &after).is_some()
            || !self.engine.task_ids().iter().any(|task_id| task_id == &candidate.task_id)
        {
            return Err(GuardCandidateError::Capture(GuardCaptureError::InputStale));
        }
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }

        let capture = GuardMechanicalCapture {
            producer_id,
            artifact_path: selected_artifact.path,
            artifact_sha256,
            selected_artifact_record: selected_artifact.json_record,
            target: draft.red_job.test_target,
            test_id: draft.red_job.test_id,
            build_exit_code: build.exit_code,
            test_exit_code: test.exit_code,
            dual_eof: build.dual_eof && test.dual_eof,
            inputs_unchanged: true,
            input_fingerprint: candidate.binding.input_fp.clone(),
            input_artifact_fingerprints: BTreeMap::from([
                ("architecture".to_owned(), candidate.binding.architecture.clone()),
                ("bdd".to_owned(), candidate.binding.bdd.clone()),
                ("skeleton".to_owned(), candidate.binding.skeleton.clone()),
                ("envelope".to_owned(), candidate.binding.envelope.clone()),
                ("tests".to_owned(), candidate.binding.test_manifest.clone()),
            ]),
            observed_case_line: Some(observed_failure.case_line),
            failure_summary_line: Some(observed_failure.summary_line),
            raw_test_stdout: test.stdout,
            raw_test_stderr: test.stderr,
            build_stdout_sha256: sgenaxis_spec::packet::source_sha256(build.stdout.as_bytes()),
            build_stderr_sha256: sgenaxis_spec::packet::source_sha256(build.stderr.as_bytes()),
        };
        if let Some(record) = self.guard_candidates.get_mut(&candidate_ref) {
            record.mechanical_capture = Some(capture.clone());
        }
        Ok(capture)
    }

    fn guard_capture_current_binding(
        &self,
        candidate: &GuardCandidateRecord,
        deadline: std::time::Instant,
        now: &mut impl FnMut() -> std::time::Instant,
    ) -> Result<GuardSnapshot, GuardCandidateError> {
        let draft = candidate.draft.as_ref().ok_or(GuardCandidateError::Capture(GuardCaptureError::MissingCandidate))?;
        let project_id = sgenaxis_work::ProjectId::new(draft.project_id.clone());
        let manifest = GuardInputManifest {
            revision: draft.manifest_revision.clone(),
            inputs: draft.input_paths.clone(),
            architecture: draft.architecture_paths.clone(),
            bdd: draft.bdd_paths.clone(),
            skeleton: draft.skeleton_paths.clone(),
            tests: draft.test_paths.clone(),
        };
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let project = self.work.get_project(&project_id)
            .map_err(|_| GuardCandidateError::Capture(GuardCaptureError::InputStale))?
            .ok_or(GuardCandidateError::Capture(GuardCaptureError::InputStale))?;
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let current = guard_current_byte_snapshot_with_checkpoint(
            self.guard_input_fs.as_ref(),
            &project.root,
            &manifest,
            || if now() >= deadline { Err(GuardSnapshotProducerError::TimedOut) } else { Ok(()) },
        ).map_err(|error| match error {
            GuardSnapshotProducerError::TimedOut => GuardCandidateError::Capture(GuardCaptureError::TimedOut),
            _ => GuardCandidateError::Capture(GuardCaptureError::InputStale),
        })?;
        let mut binding = candidate.binding.clone();
        binding.root = project.root;
        binding.input_fp = current.manifest_fingerprint;
        binding.architecture = current.artifact_digests.get("architecture").cloned().unwrap_or_default();
        binding.bdd = current.artifact_digests.get("bdd").cloned().unwrap_or_default();
        binding.skeleton = current.artifact_digests.get("skeleton").cloned().unwrap_or_default();
        binding.test_manifest = current.artifact_digests.get("tests").cloned().unwrap_or_default();
        Ok(binding)
    }

    fn guard_qualification_current_binding(
        &self,
        candidate: &GuardCandidateRecord,
    ) -> Result<GuardSnapshot, GuardCandidateError> {
        let draft = candidate.draft.as_ref()
            .ok_or(GuardCandidateError::Capture(GuardCaptureError::MissingCandidate))?;
        let project_id = sgenaxis_work::ProjectId::new(draft.project_id.clone());
        let manifest = GuardInputManifest {
            revision: draft.manifest_revision.clone(),
            inputs: draft.input_paths.clone(),
            architecture: draft.architecture_paths.clone(),
            bdd: draft.bdd_paths.clone(),
            skeleton: draft.skeleton_paths.clone(),
            tests: draft.test_paths.clone(),
        };
        let current = self.guard_project_input_snapshot(&project_id, &manifest)
            .map_err(|error| match error {
                GuardProjectSnapshotError::NotReady => GuardCandidateError::NotReady,
                GuardProjectSnapshotError::ProjectNotFound => GuardCandidateError::ProjectNotFound,
                GuardProjectSnapshotError::ProjectReadFailure(_) => GuardCandidateError::ProjectReadFailure,
                GuardProjectSnapshotError::Snapshot(error) => GuardCandidateError::Snapshot(error),
            })?;
        let project = self.work.get_project(&project_id)
            .map_err(|_| GuardCandidateError::ProjectReadFailure)?
            .ok_or(GuardCandidateError::ProjectNotFound)?;
        let mut binding = candidate.binding.clone();
        binding.root = project.root;
        binding.input_fp = current.manifest_fingerprint;
        binding.architecture = current.artifact_digests.get("architecture").cloned().unwrap_or_default();
        binding.bdd = current.artifact_digests.get("bdd").cloned().unwrap_or_default();
        binding.skeleton = current.artifact_digests.get("skeleton").cloned().unwrap_or_default();
        binding.test_manifest = current.artifact_digests.get("tests").cloned().unwrap_or_default();
        Ok(binding)
    }

    fn guard_capture_drain_pending_once(&mut self) {
        let Some(slot) = self.guard_capture_process.clone() else { return; };
        let exited = self.guard_red_process.try_wait(slot.process_id).ok().flatten().is_some();
        let output = self.guard_red_process.try_read(slot.process_id).ok();
        if exited && output.as_ref().is_some_and(|output| {
            guard_capture_stream_terminal(&output.stdout_completion)
                && guard_capture_stream_terminal(&output.stderr_completion)
        }) {
            self.guard_capture_process = None;
        }
    }

    fn guard_run_capture_process<F>(
        &mut self,
        candidate_ref: u64,
        stage: GuardCaptureStage,
        program: &str,
        args: &[&str],
        cwd: Option<&str>,
        deadline: std::time::Instant,
        now: &mut F,
    ) -> Result<GuardCaptureProcessResult, GuardCandidateError>
    where
        F: FnMut() -> std::time::Instant,
    {
        if self.guard_capture_process.is_some() {
            return Err(GuardCandidateError::Capture(GuardCaptureError::CleanupPending));
        }
        if now() >= deadline {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
        }
        let process_id = self.guard_red_process.start(program, args, cwd)
            .map_err(|_| GuardCandidateError::Capture(GuardCaptureError::ProcessStart))?;
        self.guard_capture_process = Some(GuardCaptureProcessSlot { candidate_ref, process_id, stage });
        let mut stdout = String::new();
        let mut stderr = String::new();
        let mut stdout_completion = sgenaxis_ports::StreamCompletion::Open;
        let mut stderr_completion = sgenaxis_ports::StreamCompletion::Open;
        let mut exit_code = None;
        let mut drain_deadline = None;

        loop {
            let current = now();
            if current >= deadline {
                self.guard_cancel_capture_process(process_id, exit_code, &stdout_completion, &stderr_completion);
                return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
            }

            match self.guard_red_process.try_wait(process_id) {
                Ok(Some(code)) => {
                    if exit_code.is_none() {
                        exit_code = Some(code);
                        drain_deadline = Some(current + std::time::Duration::from_secs(2));
                    }
                }
                Ok(None) => {}
                Err(_) => {
                    self.guard_cancel_capture_process(process_id, exit_code, &stdout_completion, &stderr_completion);
                    return Err(GuardCandidateError::Capture(GuardCaptureError::ProcessObservation));
                }
            }
            if now() >= deadline {
                self.guard_cancel_capture_process(process_id, exit_code, &stdout_completion, &stderr_completion);
                return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
            }

            let output = match self.guard_red_process.try_read(process_id) {
                Ok(output) => output,
                Err(_) => {
                    self.guard_cancel_capture_process(process_id, exit_code, &stdout_completion, &stderr_completion);
                    return Err(GuardCandidateError::Capture(GuardCaptureError::ProcessObservation));
                }
            };
            stdout.push_str(&output.stdout);
            stderr.push_str(&output.stderr);
            stdout_completion = output.stdout_completion;
            stderr_completion = output.stderr_completion;
            if now() >= deadline {
                self.guard_cancel_capture_process(process_id, exit_code, &stdout_completion, &stderr_completion);
                return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut));
            }

            if matches!(stdout_completion, sgenaxis_ports::StreamCompletion::Error(_))
                || matches!(stderr_completion, sgenaxis_ports::StreamCompletion::Error(_))
            {
                self.guard_cancel_capture_process(process_id, exit_code, &stdout_completion, &stderr_completion);
                return Err(GuardCandidateError::Capture(GuardCaptureError::ProcessObservation));
            }
            if let Some(code) = exit_code {
                if stdout_completion == sgenaxis_ports::StreamCompletion::Eof
                    && stderr_completion == sgenaxis_ports::StreamCompletion::Eof
                {
                    self.guard_capture_process = None;
                    return Ok(GuardCaptureProcessResult { exit_code: code, stdout, stderr, dual_eof: true });
                }
                if now() >= drain_deadline.unwrap_or(deadline) {
                    // The child has exited, but its streams are still owned
                    // and unresolved. Keep the slot for a later explicit drain.
                    return Err(GuardCandidateError::Capture(GuardCaptureError::StreamIncomplete));
                }
            }
            std::thread::sleep(std::time::Duration::from_millis(10));
        }
    }

    fn guard_cancel_capture_process(
        &mut self,
        process_id: sgenaxis_ports::ProcessId,
        known_exit: Option<i32>,
        stdout_completion: &sgenaxis_ports::StreamCompletion,
        stderr_completion: &sgenaxis_ports::StreamCompletion,
    ) {
        if known_exit.is_none() {
            let _ = self.guard_red_process.cancel(process_id);
        }
        let exit = known_exit.or_else(|| self.guard_red_process.try_wait(process_id).ok().flatten());
        let output = self.guard_red_process.try_read(process_id).ok();
        let stdout_done = output.as_ref().map(|output| guard_capture_stream_terminal(&output.stdout_completion))
            .unwrap_or_else(|| guard_capture_stream_terminal(stdout_completion));
        let stderr_done = output.as_ref().map(|output| guard_capture_stream_terminal(&output.stderr_completion))
            .unwrap_or_else(|| guard_capture_stream_terminal(stderr_completion));
        if exit.is_some() && stdout_done && stderr_done {
            self.guard_capture_process = None;
        }
    }
}

#[derive(Clone, Debug)]
struct GuardCaptureProcessResult {
    exit_code: i32,
    stdout: String,
    #[allow(dead_code)]
    stderr: String,
    dual_eof: bool,
}

fn guard_capture_stream_terminal(completion: &sgenaxis_ports::StreamCompletion) -> bool {
    !matches!(completion, sgenaxis_ports::StreamCompletion::Open)
}

fn guard_capture_draft_is_safe(draft: &CandidateDraft, bound_root: &str) -> bool {
    let expected_build_args = ["test", "--no-run", "--message-format=json", "--lib"];
    guard_capture_cwd_is_within_root(&draft.red_job.cwd_ref, bound_root)
        && std::path::Path::new(&draft.red_job.program).is_absolute()
        && std::path::Path::new(&draft.red_job.program).file_name()
            .is_some_and(|name| name.to_string_lossy().eq_ignore_ascii_case("cargo.exe") || name.to_string_lossy().eq_ignore_ascii_case("cargo"))
        && draft.red_job.build_argv.iter().map(String::as_str).eq(expected_build_args)
        && draft.red_job.timeout_ms == 120_000
        && !draft.red_job.test_target.trim().is_empty()
        && !draft.red_job.test_id.trim().is_empty()
        && !draft.red_job.test_id.contains('\0')
}

/// Accept the bound project root or an explicitly declared lexical descendant.
/// This validates only the logical path reference; it makes no symlink/reparse
/// containment claim and performs no filesystem existence probe.
fn guard_capture_cwd_is_within_root(cwd_ref: &str, bound_root: &str) -> bool {
    let root = bound_root.trim_end_matches(|character| character == '/' || character == '\\');
    if cwd_ref == root { return true; }
    let Some(suffix) = cwd_ref.strip_prefix(root) else { return false; };
    let Some(relative) = suffix.strip_prefix('/').or_else(|| suffix.strip_prefix('\\')) else { return false; };
    if relative.is_empty() || relative.contains('\0') || relative.contains(':') {
        return false;
    }
    let normalized = relative.replace('\\', "/");
    guard_manifest_path_ok(&normalized)
}

struct GuardSelectedArtifact {
    path: String,
    json_record: String,
}

fn guard_capture_select_artifact(
    cargo_stdout: &str,
    target_name: &str,
    project_root: &str,
    deadline: std::time::Instant,
    now: &mut impl FnMut() -> std::time::Instant,
) -> Result<GuardSelectedArtifact, GuardCandidateError> {
    let mut exact_paths = std::collections::BTreeMap::<String, String>::new();
    let mut other_test_target = false;
    for line in cargo_stdout.lines() {
        if now() >= deadline { return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut)); }
        let Ok(value) = serde_json::from_str::<serde_json::Value>(line) else { continue; };
        if now() >= deadline { return Err(GuardCandidateError::Capture(GuardCaptureError::TimedOut)); }
        if value.get("reason").and_then(serde_json::Value::as_str) != Some("compiler-artifact") {
            continue;
        }
        let target = value.get("target");
        let is_test_target = target.and_then(|target| target.get("test")).and_then(serde_json::Value::as_bool) == Some(true)
            && value.get("profile").and_then(|profile| profile.get("test")).and_then(serde_json::Value::as_bool) == Some(true);
        if !is_test_target { continue; }
        let actual_name = target.and_then(|target| target.get("name")).and_then(serde_json::Value::as_str).unwrap_or_default();
        if actual_name != target_name {
            other_test_target = true;
            continue;
        }
        let Some(executable) = value.get("executable").and_then(serde_json::Value::as_str) else {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactMissing));
        };
        let executable_listed = value.get("filenames")
            .and_then(serde_json::Value::as_array)
            .is_some_and(|filenames| filenames.iter().any(|filename| filename.as_str() == Some(executable)));
        if !executable_listed {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactMissing));
        }
        let artifact = std::path::Path::new(executable);
        if !artifact.is_absolute() || !artifact.starts_with(project_root) {
            return Err(GuardCandidateError::Capture(GuardCaptureError::TargetMismatch));
        }
        if exact_paths.insert(executable.to_owned(), line.to_owned()).is_some() {
            return Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactAmbiguous));
        }
    }
    match exact_paths.len() {
        0 if other_test_target => Err(GuardCandidateError::Capture(GuardCaptureError::TargetMismatch)),
        0 => Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactMissing)),
        1 => {
            let (path, json_record) = exact_paths.into_iter().next().unwrap_or_default();
            Ok(GuardSelectedArtifact { path, json_record })
        },
        _ => Err(GuardCandidateError::Capture(GuardCaptureError::ArtifactAmbiguous)),
    }
}

struct GuardObservedTestFailure {
    case_line: String,
    summary_line: String,
}

fn guard_capture_exact_case_failure(
    test_stdout: &str,
    expected_case: &str,
    deadline: std::time::Instant,
    now: &mut impl FnMut() -> std::time::Instant,
) -> Result<Option<GuardObservedTestFailure>, GuardCaptureError> {
    let mut exact_failed = false;
    let mut exact_count = 0usize;
    let mut exact_passed_or_ignored = false;
    let mut case_line = None;
    let mut summary_line = None;
    for line in test_stdout.lines() {
        if now() >= deadline { return Err(GuardCaptureError::TimedOut); }
        if let Some(rest) = line.strip_prefix("test ") {
            if let Some((case_id, status)) = rest.split_once(" ... ") {
                if case_id == expected_case {
                    exact_count += 1;
                    match status.trim() {
                        "FAILED" => { exact_failed = true; case_line = Some(line.to_owned()); },
                        "ok" | "ignored" => exact_passed_or_ignored = true,
                        _ => {}
                    }
                }
            }
        }
        if line.starts_with("test result: FAILED.")
            && line.contains("0 passed; 1 failed; 0 ignored;")
        {
            summary_line = Some(line.to_owned());
        }
        if now() >= deadline { return Err(GuardCaptureError::TimedOut); }
    }
    if exact_count == 1 && exact_failed && !exact_passed_or_ignored {
        match (case_line, summary_line) {
            (Some(case_line), Some(summary_line)) => Ok(Some(GuardObservedTestFailure { case_line, summary_line })),
            _ => Ok(None),
        }
    } else {
        Ok(None)
    }
}

/// First differing GC04 binding field name, or `None` when exact-equal.
fn guard_binding_stale_field(
    bound: &GuardSnapshot,
    current: &GuardSnapshot,
) -> Option<&'static str> {
    if bound.task != current.task {
        return Some("task");
    }
    if bound.module != current.module {
        return Some("module");
    }
    if bound.project != current.project {
        return Some("project");
    }
    if bound.root != current.root {
        return Some("root");
    }
    if bound.input_fp != current.input_fp {
        return Some("input_fp");
    }
    if bound.architecture != current.architecture {
        return Some("architecture");
    }
    if bound.bdd != current.bdd {
        return Some("bdd");
    }
    if bound.skeleton != current.skeleton {
        return Some("skeleton");
    }
    if bound.envelope != current.envelope {
        return Some("envelope");
    }
    if bound.red_id != current.red_id {
        return Some("red_id");
    }
    if bound.test_manifest != current.test_manifest {
        return Some("test_manifest");
    }
    None
}

fn guard_sha256_hex_ok(hash: &str) -> bool {
    hash.len() == 64 && hash.bytes().all(|b| matches!(b, b'0'..=b'9' | b'a'..=b'f'))
}

/// Canonical relative path: slash-separated, no empty／`.`／`..`／absolute／drive.
fn guard_manifest_path_ok(path: &str) -> bool {
    if path.is_empty() || path.starts_with('/') || path.starts_with('\\') {
        return false;
    }
    let bytes = path.as_bytes();
    if bytes.len() >= 2 && bytes[0].is_ascii_alphabetic() && bytes[1] == b':' {
        return false;
    }
    for component in path.split('/') {
        if component.is_empty() || component == "." || component == ".." {
            return false;
        }
        if component.contains('\\') {
            return false;
        }
    }
    true
}

impl GuardSessionState {
    /// Authorize implementation start against current HOST snapshot (GC10).
    pub(crate) fn authorize_start(
        &mut self,
        host_resolved_intent: GuardHostIntent,
        reference: u64,
        current: &GuardSnapshot,
    ) -> Result<(), GuardAuthorityError> {
        match host_resolved_intent {
            GuardHostIntent::Unknown => return Err(GuardAuthorityError::IntentUnknown),
            GuardHostIntent::Generic => return Err(GuardAuthorityError::RequiresApproval),
            GuardHostIntent::Implementation => {}
        }

        let approval = self
            .approval
            .as_mut()
            .filter(|a| a.session == self.boot && a.id == reference)
            .ok_or(GuardAuthorityError::MissingRecord)?;

        match approval.status {
            GuardApprovalStatus::Consumed => return Err(GuardAuthorityError::Consumed),
            GuardApprovalStatus::Revoked => return Err(GuardAuthorityError::Revoked),
            GuardApprovalStatus::Approved => {}
        }

        if let Some(field) = guard_binding_stale_field(&approval.binding, current) {
            return Err(GuardAuthorityError::Stale(field));
        }

        approval.status = GuardApprovalStatus::Consumed;
        Ok(())
    }

    /// Generic route checks HOST-owned intent only (GC01／GC11).
    pub(crate) fn authorize_generic(
        &self,
        host_resolved_intent: GuardHostIntent,
    ) -> Result<(), GuardAuthorityError> {
        match host_resolved_intent {
            GuardHostIntent::Generic => Ok(()),
            GuardHostIntent::Unknown => Err(GuardAuthorityError::IntentUnknown),
            GuardHostIntent::Implementation => Err(GuardAuthorityError::RequiresApproval),
        }
    }

    /// Commit native Yes／No／Cancel observation after lock reacquire (GC05／GC06).
    pub(crate) fn commit_native_observation(
        &mut self,
        nonce: u64,
        observation: GuardNativeObservation,
        current: &GuardSnapshot,
    ) -> Result<(), GuardAuthorityError> {
        let pending = match self.pending.as_ref() {
            Some(p) if p.nonce == nonce => p,
            _ => return Err(GuardAuthorityError::MissingRecord),
        };

        if pending.revoked {
            self.pending = None;
            return Err(GuardAuthorityError::Revoked);
        }

        match observation {
            GuardNativeObservation::No | GuardNativeObservation::Cancel => {
                self.pending = None;
                return Err(GuardAuthorityError::NativeDeclined);
            }
            GuardNativeObservation::Yes => {}
        }

        if let Some(field) = guard_binding_stale_field(&pending.binding, current) {
            self.pending = None;
            return Err(GuardAuthorityError::Stale(field));
        }

        let binding = pending.binding.clone();
        self.pending = None;
        self.approval = Some(GuardApproval {
            session: self.boot,
            id: nonce,
            binding,
            status: GuardApprovalStatus::Approved,
        });
        Ok(())
    }

    /// Idempotent revoke of known approval／pending (GC11).
    pub(crate) fn revoke(&mut self, reference: u64) -> Result<(), GuardAuthorityError> {
        if let Some(approval) = self.approval.as_mut() {
            if approval.id == reference {
                approval.status = GuardApprovalStatus::Revoked;
            }
        }
        if let Some(pending) = self.pending.as_mut() {
            if pending.nonce == reference {
                pending.revoked = true;
            }
        }
        Ok(())
    }
}

/// Qualify RED from HOST-produced capture facts (GC07／GC08).
pub(crate) fn guard_qualify_red(facts: &GuardCaptureFacts) -> Result<(), GuardAuthorityError> {
    let mechanical_ok = facts.host_owned
        && facts.build_ok
        && facts.case_executed
        && !facts.case_ignored
        && facts.case_failed
        && facts.exit_code != 0
        && facts.dual_eof
        && !facts.stream_error
        && facts.same_snapshot
        && facts.case_id == facts.expected_case_id;
    if !mechanical_ok || !facts.owner_qualifies {
        return Err(GuardAuthorityError::RedUnqualified);
    }
    Ok(())
}

/// Validate canonical relative-path manifest entries (GC03).
pub(crate) fn guard_validate_manifest(
    entries: &[GuardManifestEntry],
) -> Result<(), GuardAuthorityError> {
    if entries.is_empty() {
        return Err(GuardAuthorityError::InvalidManifest);
    }
    let mut seen = std::collections::BTreeSet::new();
    for entry in entries {
        if !guard_manifest_path_ok(&entry.relative_path) || !guard_sha256_hex_ok(&entry.sha256) {
            return Err(GuardAuthorityError::InvalidManifest);
        }
        if !seen.insert(entry.relative_path.as_str()) {
            return Err(GuardAuthorityError::InvalidManifest);
        }
    }
    Ok(())
}

// ─── GUARD F-A CURRENT-BYTE SNAPSHOT PRODUCER ───────────────────────────────
// Private application helper after independently verified intended RED.
// HOST composition, trusted root resolution and approval binding are separate.

#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct GuardInputManifest {
    pub revision: String,
    pub inputs: Vec<String>,
    pub architecture: Vec<String>,
    pub bdd: Vec<String>,
    pub skeleton: Vec<String>,
    pub tests: Vec<String>,
}

#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) struct GuardCurrentByteSnapshot {
    pub manifest_fingerprint: String,
    pub entries: Vec<GuardManifestEntry>,
    pub artifact_digests: BTreeMap<String, String>,
}

#[allow(dead_code)]
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum GuardReadFailureCategory {
    NotFound,
    PermissionDenied,
    InvalidPath,
    Io,
    Other,
}

#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
pub(crate) enum GuardSnapshotProducerError {
    NotReady,
    TimedOut,
    InvalidManifest,
    ReadFailure {
        relative_path: String,
        category: GuardReadFailureCategory,
    },
}

/// Read and hash the exact bytes of a validated F-A manifest.
///
/// F-A covers only explicitly listed inputs and binds a logical root. It does
/// not fingerprint the whole worktree or claim hostile-filesystem containment.
#[allow(dead_code)]
pub(crate) fn guard_current_byte_snapshot(
    fs: &dyn FileSystemPort,
    logical_root: &str,
    manifest: &GuardInputManifest,
) -> Result<GuardCurrentByteSnapshot, GuardSnapshotProducerError> {
    guard_current_byte_snapshot_with_checkpoint(fs, logical_root, manifest, || Ok(()))
}

fn guard_current_byte_snapshot_with_checkpoint<F>(
    fs: &dyn FileSystemPort,
    logical_root: &str,
    manifest: &GuardInputManifest,
    mut checkpoint: F,
) -> Result<GuardCurrentByteSnapshot, GuardSnapshotProducerError>
where
    F: FnMut() -> Result<(), GuardSnapshotProducerError>,
{
    use sgenaxis_spec::packet::source_sha256;
    let invalid = GuardSnapshotProducerError::InvalidManifest;
    checkpoint()?;
    if logical_root.is_empty() || manifest.revision.is_empty() || manifest.inputs.is_empty() {
        return Err(invalid);
    }
    let mut paths = manifest.inputs.clone();
    paths.sort_by(|a, b| a.as_bytes().cmp(b.as_bytes()));
    if paths.windows(2).any(|pair| pair[0] == pair[1])
        || paths.iter().any(|path| !guard_manifest_path_ok(path)
            || path.contains('\0') || path.contains(':'))
    {
        return Err(invalid);
    }
    // Validate the entire declaration before the first read. These four sets
    // are the approved file categories; EnvelopeDraft is bound separately.
    let categories = [
        ("architecture", &manifest.architecture),
        ("bdd", &manifest.bdd),
        ("skeleton", &manifest.skeleton),
        ("tests", &manifest.tests),
    ];
    for (_, members) in &categories {
        if members.is_empty() || members.iter().any(|path| paths.binary_search(path).is_err()) {
            return Err(invalid);
        }
    }
    let root = logical_root.trim_end_matches(|c| c == '/' || c == '\\');
    let mut entries = Vec::with_capacity(paths.len());
    for path in paths {
        checkpoint()?;
        let bytes = fs.read(&format!("{root}/{path}")).map_err(|error| {
            use sgenaxis_ports::PortError;
            let category = match error {
                PortError::NotFound(_) => GuardReadFailureCategory::NotFound,
                PortError::PermissionDenied(_) => GuardReadFailureCategory::PermissionDenied,
                PortError::InvalidPath(_) => GuardReadFailureCategory::InvalidPath,
                PortError::Io(_) => GuardReadFailureCategory::Io,
                _ => GuardReadFailureCategory::Other,
            };
            GuardSnapshotProducerError::ReadFailure { relative_path: path.clone(), category }
        })?;
        checkpoint()?;
        let sha256 = source_sha256(&bytes);
        checkpoint()?;
        entries.push(GuardManifestEntry { relative_path: path, sha256 });
    }
    // Private canonical format: sorted UTF-8 paths, fixed sorted object keys,
    // compact JSON and exact-byte SHA. Never serialize caller-supplied hashes.
    let entry_values = |selected: &[&GuardManifestEntry]| {
        selected.iter().map(|entry| BTreeMap::from([
            ("relative_path", entry.relative_path.clone()),
            ("sha256", entry.sha256.clone()),
        ])).collect::<Vec<_>>()
    };
    let mut artifact_digests = BTreeMap::new();
    for (name, members) in categories {
        let selected = entries.iter().filter(|entry| members.contains(&entry.relative_path)).collect::<Vec<_>>();
        checkpoint()?;
        let encoded = serde_json::to_vec(&entry_values(&selected)).map_err(|_| GuardSnapshotProducerError::InvalidManifest)?;
        checkpoint()?;
        artifact_digests.insert(name.to_string(), source_sha256(&encoded));
        checkpoint()?;
    }
    let all = entries.iter().collect::<Vec<_>>();
    let canonical = BTreeMap::from([
        ("artifacts", serde_json::to_value(&artifact_digests).map_err(|_| GuardSnapshotProducerError::InvalidManifest)?),
        ("entries", serde_json::to_value(entry_values(&all)).map_err(|_| GuardSnapshotProducerError::InvalidManifest)?),
        ("logical_root", serde_json::Value::String(logical_root.to_string())),
        ("revision", serde_json::Value::String(manifest.revision.clone())),
    ]);
    let encoded = serde_json::to_vec(&canonical).map_err(|_| GuardSnapshotProducerError::InvalidManifest)?;
    checkpoint()?;
    let manifest_fingerprint = source_sha256(&encoded);
    checkpoint()?;
    Ok(GuardCurrentByteSnapshot { manifest_fingerprint, entries, artifact_digests })
}

/// Failure boundary for HOST-owned project-root resolution plus snapshot production.
#[allow(dead_code)]
#[derive(Clone, Debug, PartialEq, Eq)]
enum GuardProjectSnapshotError {
    NotReady,
    ProjectNotFound,
    ProjectReadFailure(sgenaxis_work::WorkError),
    Snapshot(GuardSnapshotProducerError),
}

impl DispatchHost {
    /// Compute a current snapshot using only the root registered for `project_id`.
    ///
    /// No caller root or selected-project projection is an authority here.
    /// Re-read WORK and the declared bytes on every request; do not cache them.
    #[allow(dead_code)]
    fn guard_project_input_snapshot(
        &self,
        project_id: &sgenaxis_work::ProjectId,
        manifest: &GuardInputManifest,
    ) -> Result<GuardCurrentByteSnapshot, GuardProjectSnapshotError> {
        let project = self.work.get_project(project_id)
            .map_err(GuardProjectSnapshotError::ProjectReadFailure)?
            .ok_or(GuardProjectSnapshotError::ProjectNotFound)?;
        guard_current_byte_snapshot(self.guard_input_fs.as_ref(), &project.root, manifest)
            .map_err(GuardProjectSnapshotError::Snapshot)
    }
}

/// Predicate-only main＋trusted-local origin check (GC05). Not ACL wiring proof.
pub(crate) fn guard_require_main_local(
    injected_label: &str,
    is_trusted_local_app_origin: bool,
) -> Result<(), GuardAuthorityError> {
    if injected_label == "main" && is_trusted_local_app_origin {
        Ok(())
    } else {
        Err(GuardAuthorityError::AuthorityDenied)
    }
}

// === EA-A0 SKELETON ONLY (PD-RUST-EA-A0-SKELETON-MATERIALIZE-01) ===
// Private DispatchHost fixture-session ownership + approved signatures.
// Structural stubs intentionally omit approved observable transitions.
// NOT a public Manager/Service; ProcessPort / EXEC / ConPTY / six commands untouched.

/// Private fixture lifecycle phase (HOST-owned; UI only projects).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Phase {
    Idle,
    Starting,
    Running,
    Closing,
    Closed,
    FailedNoHandle,
    CleanupFailed,
}

/// Private fixture session policy errors (not InteractiveError).
#[derive(Debug, Clone, PartialEq, Eq)]
enum SessionError {
    Busy,
    Unbound,
    InvalidState,
    InputTooLarge,
    InvalidSize,
    Port,
}

/// Maps to DispatchHost's private fixture use-case state, not a new production service.
#[allow(dead_code)]
struct Session<P: InteractiveFixturePort> {
    port: P,
    phase: Phase,
    id: u64,
    resource: Option<InteractiveId>,
    stop_requested: bool,
    stop_observed_ms: Option<u64>,
    executable: String,
    cwd: String,
}

#[allow(dead_code)]
impl<P: InteractiveFixturePort> Session<P> {
    fn new(port: P) -> Self {
        Self {
            port,
            phase: Phase::Idle,
            id: 0,
            resource: None,
            stop_requested: false,
            stop_observed_ms: None,
            executable: "LOCKED_FIXTURE_NOT_STARTED".into(),
            cwd: "ISOLATED_FIXTURE_ROOT_NOT_STARTED".into(),
        }
    }

    /// Private spawn-barrier phase (not a public command).
    fn begin_start(&mut self, bound: bool) -> Result<u64, SessionError> {
        if !bound {
            return Err(SessionError::Unbound);
        }
        match self.phase {
            Phase::Idle | Phase::FailedNoHandle | Phase::Closed => {
                self.id = self.id.saturating_add(1);
                self.phase = Phase::Starting;
                self.resource = None;
                self.stop_requested = false;
                self.stop_observed_ms = None;
                Ok(self.id)
            }
            _ => Err(SessionError::Busy),
        }
    }

    /// Private spawn-barrier completion (not a public command).
    fn finish_start(
        &mut self,
        result: Result<InteractiveId, InteractiveError>,
    ) -> Result<(), SessionError> {
        if self.phase != Phase::Starting {
            return Err(SessionError::InvalidState);
        }
        match result {
            Ok(id) => {
                self.resource = Some(id);
                if self.stop_requested {
                    match self.port.request_stop(id) {
                        Ok(()) => {
                            self.phase = Phase::Closing;
                            Ok(())
                        }
                        Err(_) => {
                            self.phase = Phase::CleanupFailed;
                            Ok(())
                        }
                    }
                } else {
                    self.phase = Phase::Running;
                    Ok(())
                }
            }
            Err(_) => {
                self.resource = None;
                self.phase = Phase::FailedNoHandle;
                Ok(())
            }
        }
    }

    fn send(&mut self, text: &str) -> Result<(), SessionError> {
        if self.phase != Phase::Running {
            return Err(SessionError::InvalidState);
        }
        if text.is_empty() {
            return Ok(());
        }
        if text.len() > 4096 {
            return Err(SessionError::InputTooLarge);
        }
        let id = self.resource.ok_or(SessionError::InvalidState)?;
        self.port
            .write_text(id, text)
            .map_err(|_| SessionError::Port)
    }

    fn resize(&mut self, cols: i32, rows: i32) -> Result<(), SessionError> {
        if self.phase != Phase::Running {
            return Err(SessionError::InvalidState);
        }
        if !(1..=512).contains(&cols) || !(1..=256).contains(&rows) {
            return Err(SessionError::InvalidSize);
        }
        let id = self.resource.ok_or(SessionError::InvalidState)?;
        let size = InteractiveSize {
            cols: cols as u16,
            rows: rows as u16,
        };
        self.port.resize(id, size).map_err(|_| SessionError::Port)
    }

    fn close_at(&mut self, now_ms: u64) -> Result<(), SessionError> {
        match self.phase {
            Phase::Starting => {
                self.stop_requested = true;
                if self.stop_observed_ms.is_none() {
                    self.stop_observed_ms = Some(now_ms);
                }
                Ok(())
            }
            Phase::Running => {
                self.stop_requested = true;
                if self.stop_observed_ms.is_none() {
                    self.stop_observed_ms = Some(now_ms);
                }
                self.phase = Phase::Closing;
                if let Some(id) = self.resource {
                    if self.port.request_stop(id).is_err() {
                        self.phase = Phase::CleanupFailed;
                    }
                }
                Ok(())
            }
            Phase::Closing | Phase::CleanupFailed => Ok(()),
            Phase::Idle | Phase::Closed | Phase::FailedNoHandle => Ok(()),
        }
    }

    fn poll_at(&mut self, now_ms: u64) -> Result<Phase, SessionError> {
        if matches!(self.phase, Phase::Running | Phase::Closing | Phase::CleanupFailed) {
            if let Some(id) = self.resource {
                match self.port.poll(id) {
                    Ok(obs) => self.apply_fixture_observation(obs),
                    // EC04: observation/poll error => CleanupFailed; retain unresolved handle.
                    Err(_) => {
                        self.phase = Phase::CleanupFailed;
                    }
                }
            }
            if self.phase == Phase::Closing {
                if let Some(t0) = self.stop_observed_ms {
                    if now_ms.saturating_sub(t0) >= 2000 {
                        self.phase = Phase::CleanupFailed;
                    }
                }
            }
        }
        Ok(self.phase)
    }

    fn apply_fixture_observation(&mut self, obs: InteractiveObservation) {
        // EC04: stream error => CleanupFailed with unresolved handle retained.
        // Stream failure is not successful cleanup even if cleanup bits look terminal.
        if matches!(obs.read_state, ReadState::Error(_)) {
            self.phase = Phase::CleanupFailed;
            return;
        }
        match obs.cleanup {
            Cleanup::Complete if obs.child_exit.is_some() => {
                self.phase = Phase::Closed;
                self.resource = None;
            }
            Cleanup::Failed => {
                self.phase = Phase::CleanupFailed;
            }
            Cleanup::Complete | Cleanup::Pending => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use sgenaxis_exec::FakeMcpClient;
    mod mcp_notrun_tests { include!("mcp_notrun_tests.rs"); }
    use super::*;
    use sgenaxis_exec::{DEMO_PROJECT_ROOT, DEMO_WORK_ITEM_ID, DEMO_WORKTREE_FINGERPRINT};
    use sgenaxis_listen::FsChangeKind;

    #[test]
    fn list_commands_exposes_dispatch_table() {
        let names: Vec<_> = DispatchHost::list_commands()
            .into_iter()
            .map(|c| c.name)
            .collect();
        assert!(names.contains(&"get_board".to_string()));
        assert!(names.contains(&"load_local_board".to_string()));
        assert!(names.contains(&"start_run".to_string()));
        assert!(names.contains(&"poll_chunks".to_string()));
        assert!(names.contains(&"upsert_task".to_string()));
        assert!(names.contains(&"get_evidence_summary".to_string()));
        assert!(names.contains(&"spec_load_fixture".to_string()));
        assert!(names.contains(&"spec_get_projection".to_string()));
        assert!(names.contains(&"spec_try_set_contract".to_string()));
        assert!(names.contains(&"spec_revise".to_string()));
        assert!(names.contains(&"arch_get_projection".to_string()));
        assert!(names.contains(&"listen_get_projection".to_string()));
    }

    /// BDD-PD-REMAIN-LISTEN-UI-01: FS／Git／Agent via bridge → Command projection; empty → empty;
    /// host FS／Git watch gaps = NOT RUN; no UI-owned notify.
    #[test]
    fn listen_ui_projects_fs_git_agent_via_bridge() {
        let (mut host, clock) = DispatchHost::with_fake_listen(10);
        let empty = host.listen_get_projection();
        assert_eq!(empty.status, "empty");
        assert_eq!(empty.event_count, 0);
        assert_eq!(empty.host_fs_watch, "NOT RUN");
        assert_eq!(empty.host_git_watch, "NOT RUN");
        assert_eq!(empty.host_agent_bridge, "wired");

        host.listen_push_source(SourceEvent::fs("/proj/a.rs", FsChangeKind::Modify));
        host.listen_push_source(SourceEvent::git("/proj", "index"));
        clock.advance(Duration::from_millis(10));
        let mid = host.listen_get_projection();
        assert_eq!(mid.status, "ok");
        assert_eq!(mid.last_fs_path.as_deref(), Some("/proj/a.rs"));
        assert!(mid.last_fs_burst >= 1);
        assert_eq!(mid.last_git_root.as_deref(), Some("/proj"));

        // Agent terminal flushes immediately (no debounce wait).
        host.listen_push_source(SourceEvent::Agent(AgentChunk::Exited {
            run_id: RunId(7),
            exit_code: Some(0),
            classification: ExitClassification::Success,
        }));
        let after = host.listen_get_projection();
        assert_eq!(after.last_agent_run, Some(7));
        assert!(after.ended_runs.contains(&7));
        assert_eq!(after.host_fs_watch, "NOT RUN", "must not forge FS watch live");
    }

    /// Agent path: poll_chunks feeds EventBridge → listen projection.
    #[test]
    fn listen_ui_agent_via_poll_chunks_command_path() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some(DEMO_WORK_ITEM_ID.into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start_run");
        let _ = host.poll_chunks(started.run_id).expect("poll");
        let proj = host.listen_get_projection();
        assert!(
            proj.event_count > 0 || proj.last_agent_run.is_some(),
            "poll_chunks must project Agent listen; got {proj:?}"
        );
        assert_eq!(proj.host_agent_bridge, "wired");
    }

    /// BDD-PD-REMAIN-ARCH-UI-01: Command projects modules／deps; empty→empty status; not UI-static live.
    #[test]
    fn arch_ui_command_projects_modules_and_deps() {
        let host = DispatchHost::new();
        let proj = host.arch_get_projection();
        assert_eq!(proj.source, "dispatch_host.arch_get_projection");
        assert_eq!(proj.status, "ok");
        assert!(proj.live);
        assert!(!proj.modules.is_empty());
        assert!(!proj.edges.is_empty());
        let ids: Vec<_> = proj.modules.iter().map(|m| m.id.as_str()).collect();
        for need in [
            "ui",
            "command",
            "dispatch_host",
            "core",
            "flow",
            "exec",
            "work",
            "evid",
            "ports",
        ] {
            assert!(ids.contains(&need), "missing module {need}");
        }
        assert!(proj.edges.iter().any(|e| e.from == "ui" && e.to == "command"));
        assert!(proj
            .edges
            .iter()
            .any(|e| e.from == "command" && e.to == "dispatch_host"));
        assert!(proj
            .edges
            .iter()
            .any(|e| e.from == "dispatch_host" && e.to == "core"));
        // No UI → ports／adapters bypass edge in the projected graph.
        assert!(!proj.edges.iter().any(|e| e.from == "ui" && e.to == "ports"));
        assert!(!proj
            .edges
            .iter()
            .any(|e| e.from == "ui" && e.to == "adapters"));
    }

    /// BDD-PD-SPEC-UI-01: load＋display Spec projection; approved in-place → REPLAN; revise separate.
    #[test]
    fn spec_ui_load_display_replan_and_revise_entry() {
        let mut host = DispatchHost::new();
        let empty = host.spec_get_projection();
        assert!(!empty.loaded);

        let proj = host.spec_load_fixture().expect("load fixture");
        assert!(proj.loaded);
        assert_eq!(proj.module_id, "SPEC");
        assert_eq!(proj.module_name, "工程規格");
        assert!(!proj.revisions.is_empty());
        assert_eq!(proj.revisions[0].id, "rev-v1");
        assert_eq!(proj.revisions[0].status, "draft");

        let detail = host
            .spec_get_revision(SpecGetRevisionArgs {
                revision_id: "rev-v1".into(),
            })
            .expect("revision");
        assert_eq!(detail.contracts.len(), 2);
        assert!(!detail.immutable);

        let approved = host
            .spec_approve(SpecApproveArgs {
                revision_id: "rev-v1".into(),
            })
            .expect("approve");
        assert_eq!(approved.status, "approved");
        assert!(approved.immutable);
        assert!(approved.content_hash.is_some());

        let err = host
            .spec_try_set_contract(SpecTrySetContractArgs {
                revision_id: "rev-v1".into(),
                contract_id: "CTR-SPEC-001".into(),
                new_body: "sneaky in-place".into(),
            })
            .expect_err("approved must refuse in-place edit");
        assert!(
            err.contains("REPLAN_REQUIRED"),
            "expected REPLAN_REQUIRED, got: {err}"
        );

        // Baseline body unchanged after refused mutate.
        let still = host
            .spec_get_revision(SpecGetRevisionArgs {
                revision_id: "rev-v1".into(),
            })
            .unwrap();
        assert_eq!(still.contracts[0].body, "每個 Task 恰有一個主要模組");

        // Revise is a separate entry — creates new Draft; approved stays locked.
        let v2 = host
            .spec_revise(SpecReviseArgs {
                from_revision_id: "rev-v1".into(),
                new_revision_id: "rev-v2".into(),
                new_version_label: "v2".into(),
                contracts: vec![SpecContractDto {
                    id: "CTR-SPEC-001".into(),
                    title: "Task primary module".into(),
                    body: "每個 Task 恰有一個主要模組（修訂）".into(),
                }],
            })
            .expect("revise entry");
        assert_eq!(v2.id, "rev-v2");
        assert_eq!(v2.status, "draft");
        assert!(!v2.immutable);

        let after = host.spec_get_projection();
        assert_eq!(after.revisions.len(), 2);
        assert_eq!(after.evidence_needing_revalidation, 1);
        let v1 = after.revisions.iter().find(|r| r.id == "rev-v1").unwrap();
        assert_eq!(v1.status, "approved");
    }

    #[test]
    fn replace_projection_from_local_snapshot_tasks() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "scratch".into(),
            title: "temp".into(),
            zone: "gray".into(),
        })
        .unwrap();
        let board = host.replace_projection_tasks(vec![
            sgenaxis_core::TaskRecord {
                id: "PD-A".into(),
                title: "Alpha".into(),
                zone: Zone::Yellow,
            },
            sgenaxis_core::TaskRecord {
                id: "PD-B".into(),
                title: "Beta".into(),
                zone: Zone::Green,
            },
        ]);
        assert_eq!(board.yellow, 1);
        assert_eq!(board.green, 1);
        assert_eq!(board.gray, 0);
        assert_eq!(board.tasks.len(), 2);
        assert!(!board.tasks.iter().any(|t| t.id == "scratch"));
    }

    /// BDD-PD-EVID-UI-01: selected work item → evidence summary; empty → NOT RUN; Success ≠ green.
    #[test]
    fn evidence_summary_empty_not_run_provider_success_not_green() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "t-evid".into(),
            title: "Evid UI".into(),
            zone: "gray".into(),
        })
        .unwrap();
        host.set_required_bdd_for_test("t-evid", vec!["BDD-EVID-UI".into()]);

        let empty = host.get_evidence_summary("t-evid");
        assert_eq!(empty.work_item_id, "t-evid");
        assert_eq!(empty.title.as_deref(), Some("Evid UI"));
        assert_eq!(empty.overall_status, "NOT RUN");
        assert_eq!(empty.lines[0].status_label, "NOT RUN");
        assert!(!empty.provider_success_implies_green);
        assert_ne!(empty.product_lamp_hint, "green");

        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("t-evid".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .unwrap();
        let poll = host.poll_chunks(started.run_id).unwrap();
        assert_eq!(poll.board.green, 0);
        assert!(poll.board.yellow >= 1);
        assert_eq!(
            poll.board.tasks.iter().find(|t| t.id == "t-evid").map(|t| t.zone.as_str()),
            Some("yellow")
        );

        let after = host.get_evidence_summary("t-evid");
        assert_eq!(after.provider_terminal, "Success");
        assert!(!after.provider_success_implies_green);
        assert!(!after.ready_for_green);
        assert_eq!(after.overall_status, "NOT RUN");
        assert_ne!(after.product_lamp_hint, "green");
        // Product zone on board stays yellow — never auto-green.
        assert_eq!(after.zone.as_deref(), Some("yellow"));
    }

    #[test]
    fn upsert_then_get_board_reflects_projection() {
        let mut host = DispatchHost::new();
        let board = host
            .upsert_task(UpsertTaskArgs {
                id: "t1".into(),
                title: "Wire commands".into(),
                zone: "gray".into(),
            })
            .expect("upsert");
        assert_eq!(board.gray, 1);
        assert_eq!(board.titles, vec!["Wire commands".to_string()]);
        assert_eq!(board.tasks.len(), 1);
        assert_eq!(board.tasks[0].id, "t1");

        let again = host.get_board();
        assert_eq!(again.generation, board.generation);
        assert_eq!(again.gray, 1);
    }

    #[test]
    fn start_run_cli_dry_run_emits_cli_started() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w1".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start");
        assert_eq!(started.provider, ProviderDto::Cli);
        assert!(started.dry_run);
        assert_eq!(started.board.blue, 1);

        let poll = host.poll_chunks(started.run_id).expect("poll");
        assert!(matches!(
            poll.chunks.first(),
            Some(ChunkDto::Started {
                provider: ProviderDto::Cli,
                dry_run: true,
                ..
            })
        ));
        assert!(poll
            .chunks
            .iter()
            .any(|c| matches!(c, ChunkDto::Exited { classification, .. } if classification == "success")));
        // Success → yellow (awaiting), never auto-green.
        // listen-agent indicator may also be yellow after poll (PD-REMAIN-LISTEN-UI-01).
        assert_eq!(poll.board.blue, 0);
        assert!(poll.board.yellow >= 1);
        assert_eq!(poll.board.green, 0);
        let w1 = poll.board.tasks.iter().find(|t| t.id == "w1");
        assert_eq!(w1.map(|t| t.zone.as_str()), Some("yellow"));
    }

    #[test]
    fn start_run_mcp_dry_run_emits_mcp_started() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start");
        assert_eq!(started.provider, ProviderDto::Mcp);

        let poll = host.poll_chunks(started.run_id).expect("poll");
        assert!(matches!(
            poll.chunks.first(),
            Some(ChunkDto::Started {
                provider: ProviderDto::Mcp,
                dry_run: true,
                ..
            })
        ));
    }

    #[test]
    fn provider_switch_cli_then_mcp() {
        let mut host = DispatchHost::new();
        let cli = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .unwrap();
        let _ = host.poll_chunks(cli.run_id).unwrap();

        let mcp = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .unwrap();
        let poll = host.poll_chunks(mcp.run_id).unwrap();
        assert!(matches!(
            poll.chunks.first(),
            Some(ChunkDto::Started {
                provider: ProviderDto::Mcp,
                ..
            })
        ));
    }

    /// BDD-PD-REMAIN-LIVE-SPAWN-01: Live without wire／approval → NOT RUN readable reject.
    #[test]
    fn live_cli_unapproved_rejects_not_run() {
        let mut host = DispatchHost::new();
        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: false,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("must reject");
        assert!(
            err.contains("NOT RUN") || err.contains("未核准") || err.contains("live_approved"),
            "readable Live reject; got {err}"
        );
    }

    /// BDD-PD-REMAIN-LIVE-SPAWN-01: empty CLI path → NOT RUN (no silent DryRun).
    #[test]
    fn live_cli_empty_path_wire_rejects_not_run() {
        let mut host = DispatchHost::new();
        let mut settings = CliAgentSettings::defaults();
        settings.live_approved = true;
        settings.claude.path = String::new();
        let err = host
            .wire_cli_live_process(settings, Box::new(FakeProcess::new()))
            .expect_err("empty path");
        assert!(
            err.contains("NOT RUN") && err.contains("CLI"),
            "readable no-CLI reject; got {err}"
        );
    }

    /// BDD-PD-REMAIN-LIVE-SPAWN-01: approved Live + ProcessPort → true EXEC spawn
    /// (Started.dry_run=false; FakeProcess.start called — not DryRun-only compose).
    #[test]
    fn live_cli_approved_spawns_via_dispatch_host_exec() {
        let mut host = DispatchHost::new();
        let fake = FakeProcess::new();
        let mut settings = CliAgentSettings::defaults();
        settings.live_approved = true;
        settings.claude.path = "/tools/claude".into();
        settings.claude.args = vec!["--print".into()];
        host.wire_cli_live_process(settings, Box::new(fake.clone()))
            .expect("wire");

        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: false,
                work_item_id: Some("w-live-spawn".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("live start");
        assert!(!started.dry_run);
        assert!(
            fake.last_id().is_some(),
            "ProcessPort::start must be called (not DryRun-only compose)"
        );

        let pid = fake.last_id().expect("pid");
        fake.finish(pid, 0).expect("finish");
        let poll = host.poll_chunks(started.run_id).expect("poll");
        assert!(matches!(
            poll.chunks.first(),
            Some(ChunkDto::Started {
                provider: ProviderDto::Cli,
                dry_run: false,
                ..
            })
        ));
        let board_json = serde_json::to_string(&started.board).expect("board json");
        assert!(!board_json.contains("secret_token"));
    }

    /// BDD-PD-REMAIN-LIVE-MCP-01: approved Live＋activatable endpoint → DispatchHost Live MCP.
    #[test]
    fn live_mcp_via_dispatch_host_is_not_dry_run_only() {
        let mut host = DispatchHost::new();
        // Explicit simulated transport: this is adapter coverage, not production availability.
        host.exec = AgentRouter::new(
            CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),
            McpAgentAdapter::with_defaults(Box::new(FakeMcpClient::default())),
        );
        let mut settings = McpAgentSettings::defaults();
        settings.endpoint = "http://127.0.0.1:3920/sse".into();
        settings.approved_tools = vec!["list_tools".into()];
        settings.secret_token = Some("must-not-leak".into());
        host.apply_mcp_settings(settings);

        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: false,
                work_item_id: Some("live-mcp-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("Live MCP via DispatchHost");
        assert!(!started.dry_run, "must not forge DryRun as Live");
        assert_eq!(started.provider, ProviderDto::Mcp);

        let poll = host.poll_chunks(started.run_id).expect("poll");
        assert!(
            matches!(
                poll.chunks.first(),
                Some(ChunkDto::Started {
                    provider: ProviderDto::Mcp,
                    dry_run: false,
                    ..
                })
            ),
            "Started dry_run=false required; got {:?}",
            poll.chunks.first()
        );
        assert!(
            poll.chunks.iter().any(|c| matches!(
                c,
                ChunkDto::Chunk { text, .. } if text.contains("[mcp-tool:list_tools]")
            )),
            "expected Live tool chunk; got {:?}",
            poll.chunks
        );
        assert_eq!(poll.board.green, 0, "Provider Success ≠ product green");
        let dbg = format!("{:?}", poll.chunks);
        assert!(!dbg.contains("must-not-leak"), "secret leaked into chunks");
    }

    /// BDD-PD-REMAIN-LIVE-MCP-01: empty／:8788／:8787 → NOT RUN (never dial).
    #[test]
    fn live_mcp_no_target_or_banned_port_is_not_run() {
        let mut host = DispatchHost::new();
        let mut empty = McpAgentSettings::defaults();
        empty.endpoint = String::new();
        host.apply_mcp_settings(empty);
        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: false,
                work_item_id: Some("live-mcp-empty".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("empty → NOT RUN");
        assert!(err.contains("NOT RUN"), "{err}");

        let mut banned = McpAgentSettings::defaults();
        banned.endpoint = "http://127.0.0.1:8788/sse".into();
        host.apply_mcp_settings(banned);
        let err8788 = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: false,
                work_item_id: Some("live-mcp-8788".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err(":8788 banned");
        assert!(
            err8788.contains("NOT RUN") && (err8788.contains("8788") || err8788.contains("禁")),
            "{err8788}"
        );

        let mut banned7 = McpAgentSettings::defaults();
        banned7.endpoint = "http://127.0.0.1:8787/events".into();
        host.apply_mcp_settings(banned7);
        let err8787 = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: false,
                work_item_id: Some("live-mcp-8787".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err(":8787 banned");
        assert!(err8787.contains("NOT RUN"), "{err8787}");
    }

    /// BDD-PD-EXEC-BIND-01: missing fingerprint／root／work item →拒跑.
    #[test]
    fn start_run_rejects_missing_binding_fields() {
        let mut host = DispatchHost::new();
        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-bind".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: None,
                guard: None,
            })
            .expect_err("fingerprint required");
        assert!(
            err.contains("worktree_fingerprint"),
            "unexpected err: {err}"
        );

        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-bind".into()),
                project_root: None,
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("root required");
        assert!(err.contains("project_root"), "unexpected err: {err}");
    }

    /// BDD-PD-EXEC-SINGLE-01: second start_run while first in flight →拒; projection shows one active Run;
    /// after end／cancel may start again.
    #[test]
    fn single_agent_rejects_second_start_until_end_or_cancel() {
        let mut host = DispatchHost::new();
        let first = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-single".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("first");
        assert_eq!(first.board.active_run_id, Some(first.run_id));
        assert_eq!(host.get_board().active_run_id, Some(first.run_id));

        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("w-single-2".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("second must be busy");
        assert!(
            err.contains("PD-EXEC-SINGLE-01") || err.contains("busy"),
            "unexpected: {err}"
        );
        // Projection still shows exactly the first active Run.
        assert_eq!(host.get_board().active_run_id, Some(first.run_id));

        let poll = host.poll_chunks(first.run_id).expect("drain end");
        assert!(poll.board.active_run_id.is_none());

        let second = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("w-single-2".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("after end");
        assert_eq!(second.board.active_run_id, Some(second.run_id));

        let busy_again = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-single-3".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("busy while second active");
        assert!(busy_again.contains("busy") || busy_again.contains("PD-EXEC-SINGLE-01"));

        let pending = host.cancel_run(second.run_id).expect("cancel");
        assert_eq!(pending.active_run_id, Some(second.run_id), "cancel is request acknowledgment");
        let board = host.poll_chunks(second.run_id).expect("terminal poll").board;
        assert!(board.active_run_id.is_none());

        let third = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-single-3".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("after cancel");
        assert_eq!(third.board.active_run_id, Some(third.run_id));
        let _ = host.poll_chunks(third.run_id);
    }

    /// BDD-PD-EXEC-BIND-01: second start with different fingerprint while lease active →拒.
    #[test]
    fn start_run_rejects_lease_fingerprint_mismatch() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-lease".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some("fp-A".into()),
                guard: None,
            })
            .expect("first");
        // Do not poll — lease stays active.
        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("w-lease".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some("fp-B".into()),
                guard: None,
            })
            .expect_err("mismatch");
        assert!(
            err.contains("fingerprint") || err.contains("lease") || err.contains("busy"),
            "unexpected err: {err}"
        );
        let _ = started;
    }

    /// BDD-PD-EXEC-CANCEL-01: cancel_run → Cancelled；釋放 WORK 租約；zone 黃（非綠）.
    #[test]
    fn cancel_run_classifies_cancelled_releases_lease() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-cancel".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start");
        assert_eq!(started.board.blue, 1);

        // Same fingerprint while lease active → 禁盲目重跑.
        let busy = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-cancel".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("must reject blind re-run");
        assert!(
            busy.contains("lease") || busy.contains("blind") || busy.contains("reconcile"),
            "unexpected: {busy}"
        );

        let pending = host.cancel_run(started.run_id).expect("cancel");
        assert_eq!(pending.active_run_id, Some(started.run_id), "cancel acknowledgment retains lease until terminal poll");
        let board = host.poll_chunks(started.run_id).expect("terminal poll").board;
        assert_eq!(board.green, 0, "§7.1 never green on cancel");
        assert!(board.yellow >= 1);
        assert_eq!(board.blue, 0);
        assert_eq!(
            board.tasks.iter().find(|t| t.id == "w-cancel").map(|t| t.zone.as_str()),
            Some("yellow")
        );

        let summary = host.get_evidence_summary("w-cancel");
        assert_eq!(summary.provider_terminal, "Cancelled");
        assert_eq!(summary.zone.as_deref(), Some("yellow"));
        assert!(!summary.ready_for_green);

        // After reconcile, same fingerprint may start again (not a blind double mutation).
        let again = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-cancel".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("after cancel lease released");
        let _ = host.poll_chunks(again.run_id).expect("drain");
    }

    /// BDD-PD-EXEC-CANCEL-01: crash 對帳 → Crashed；釋放租約；禁綠燈.
    #[test]
    fn crash_reconcile_releases_lease_projects_crashed() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("w-crash".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start");
        assert_eq!(started.board.blue, 1);

        host.reconcile_crash_for_test(started.run_id);
        let board = host.get_board();
        assert_eq!(board.green, 0);
        assert_eq!(board.yellow, 1);
        assert_eq!(board.blue, 0);

        let summary = host.get_evidence_summary("w-crash");
        assert_eq!(summary.provider_terminal, "Crashed");
        assert_eq!(summary.zone.as_deref(), Some("yellow"));
        assert!(!summary.ready_for_green);

        let again = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("w-crash".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("lease+exec released after crash reconcile");
        let _ = host.poll_chunks(again.run_id).expect("drain");
    }

    #[test]
    fn dto_chunks_have_no_secret_fields() {
        // Structural guard: ChunkDto／BoardView JSON must not mention secret／token／password.
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Mcp,
                dry_run: true,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .unwrap();
        let poll = host.poll_chunks(started.run_id).unwrap();
        let json = serde_json::to_string(&poll).unwrap();
        let lower = json.to_lowercase();
        assert!(!lower.contains("secret"));
        assert!(!lower.contains("token"));
        assert!(!lower.contains("password"));
        assert!(!lower.contains("fakprocess"));
        assert!(!lower.contains("stubmcp"));
    }

    // —— BDD-PD-GUARD-CMD-01 ——
    fn sample_guard_packet(approved: bool) -> sgenaxis_host::GuardPacketDto {
        use sgenaxis_host::{EnvelopeDto, GuardPacketDto, RedKindDto};
        GuardPacketDto {
            envelope: EnvelopeDto {
                id: "GUARD-CMD-01".into(),
                approved,
                primary_module: "GUARD".into(),
                integration_modules: vec![],
                allowed_paths: vec!["packages/guard/**".into()],
                protected_paths: vec!["contracts/approved.json".into()],
                module_path_prefixes: vec![("GUARD".into(), "packages/guard".into())],
            },
            red: RedKindDto::Behavioral,
            change_paths: vec![],
        }
    }

    #[test]
    fn guard_cmd_unapproved_start_rejects_with_code_detail() {
        let host = DispatchHost::new();
        let view = host.guard_check_start(&sample_guard_packet(false));
        assert!(!view.allowed);
        assert!(
            view.reasons.iter().any(|r| r.starts_with("NOT_APPROVED:")),
            "{:?}",
            view.reasons
        );
        let mut host = DispatchHost::new();
        let err = host
            .start_implementation(StartImplementationArgs {
                guard: sample_guard_packet(false),
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some(DEMO_WORK_ITEM_ID.into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
            })
            .expect_err("must reject unapproved");
        assert!(err.contains("NOT_APPROVED:"), "{err}");
    }

    #[test]
    fn guard_cmd_protected_path_rejects_with_code_detail() {
        let host = DispatchHost::new();
        let mut packet = sample_guard_packet(true);
        packet.change_paths = vec!["contracts/approved.json".into()];
        let view = host.guard_check_changes(&packet);
        assert!(!view.allowed);
        assert!(
            view.reasons
                .iter()
                .any(|r| r.starts_with("PATH_PROTECTED:")),
            "{:?}",
            view.reasons
        );
        let err = host.authorize_write(&packet).unwrap_err();
        assert!(err.contains("PATH_PROTECTED:"), "{err}");
    }

    #[test]
    fn guard_cmd_approved_allows_exec_start_implementation() {
        let mut host = DispatchHost::new();
        let started = host
            .start_implementation(StartImplementationArgs {
                guard: sample_guard_packet(true),
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some(DEMO_WORK_ITEM_ID.into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
            })
            .expect("approved should start");
        assert!(started.envelope_hash.is_some());
        assert_eq!(started.board.blue, 1);
        assert!(started.dry_run);
    }

    #[test]
    fn list_commands_exposes_guard_cmd_entries() {
        let names: Vec<_> = DispatchHost::list_commands()
            .into_iter()
            .map(|c| c.name)
            .collect();
        assert!(names.contains(&"guard_check_start".to_string()));
        assert!(names.contains(&"guard_check_changes".to_string()));
        assert!(names.contains(&"start_implementation".to_string()));
    }

    /// BDD-PD-UI-RUN-01: cancel before poll → Cancelled terminal; never auto-green.
    #[test]
    fn ui_run_cancel_before_poll_yields_cancelled() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start");
        assert_eq!(started.board.blue, 1);

        // cancel_run → EXEC cancel + drain; UI maps host cancelled → badge cancelled.
        let pending = host.cancel_run(started.run_id).expect("cancel");
        assert_eq!(pending.active_run_id, Some(started.run_id), "cancel acknowledgment retains lease until terminal poll");
        let board = host.poll_chunks(started.run_id).expect("terminal poll").board;
        assert_eq!(board.green, 0);
        assert_eq!(board.blue, 0);
        assert!(board.yellow >= 1);

        let summary = host.get_evidence_summary("dispatch-demo");
        assert_eq!(summary.provider_terminal, "Cancelled");
        assert_ne!(summary.product_lamp_hint, "green");
        assert!(!summary.provider_success_implies_green);
    }

    /// BDD-PD-UI-RUN-01: DryRun success stream ends with success (UI maps → ok); chunks present.
    #[test]
    fn ui_run_poll_streams_chunks_and_ok_exit() {
        let mut host = DispatchHost::new();
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect("start");
        let poll = host.poll_chunks(started.run_id).expect("poll");
        assert!(
            poll.chunks.iter().any(|c| matches!(c, ChunkDto::Chunk { .. })),
            "expected stdout/stderr chunk for stream UI"
        );
        assert!(poll.chunks.iter().any(|c| matches!(
            c,
            ChunkDto::Exited { classification, .. } if classification == "success"
        )));
        assert_eq!(poll.board.green, 0);
        assert!(poll.board.yellow >= 1);
        assert_eq!(
            poll.board
                .tasks
                .iter()
                .find(|t| t.id == "dispatch-demo")
                .map(|t| t.zone.as_str()),
            Some("yellow")
        );
    }

    /// BDD-PD-UI-RUN-01: readable host errors (no silent fail); Live unapproved → NOT RUN.
    #[test]
    fn ui_run_errors_are_readable_strings() {
        let mut host = DispatchHost::new();
        let err = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: false,
                work_item_id: Some("dispatch-demo".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .expect_err("live CLI without wire／approval must fail");
        assert!(!err.is_empty());
        assert!(
            err.contains("NOT RUN")
                || err.contains("未核准")
                || err.contains("live_approved")
                || err.contains("wire_cli_live"),
            "readable Live／NOT RUN EXEC path message; got {err}"
        );
    }

    // —— BDD-PD-FLOW-EVID-GATE-01 ——

    #[test]
    fn flow_evid_gate_provider_success_does_not_green_or_accept() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "t-gate".into(),
            title: "Gate".into(),
            zone: "gray".into(),
        })
        .unwrap();
        host.set_required_bdd_for_test("t-gate", vec!["BDD-PD-FLOW-EVID-GATE-01".into()]);

        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("t-gate".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .unwrap();
        let poll = host.poll_chunks(started.run_id).unwrap();
        assert_eq!(poll.board.green, 0);
        assert!(poll.board.yellow >= 1);
        assert_eq!(
            poll.board.tasks.iter().find(|t| t.id == "t-gate").map(|t| t.zone.as_str()),
            Some("yellow")
        );

        let err = host
            .accept_work_item("t-gate")
            .expect_err("provider done ≠ accept without EVID");
        assert!(err.contains("EVID_GAP"), "{err}");
        assert_eq!(host.get_board().green, 0);
        assert_eq!(
            host.get_board()
                .tasks
                .iter()
                .find(|t| t.id == "t-gate")
                .map(|t| t.zone.as_str()),
            Some("yellow")
        );

        let err2 = host
            .complete_work_item("t-gate")
            .expect_err("complete without accept+EVID");
        assert!(err2.contains("EVID_GAP"), "{err2}");
        assert_eq!(host.get_board().green, 0);
        assert_eq!(
            host.get_board()
                .tasks
                .iter()
                .find(|t| t.id == "t-gate")
                .map(|t| t.zone.as_str()),
            Some("yellow")
        );
    }

    #[test]
    fn flow_evid_gate_accept_complete_with_pass_evidence() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "t-gate-ok".into(),
            title: "Gate OK".into(),
            zone: "gray".into(),
        })
        .unwrap();
        host.set_required_bdd_for_test("t-gate-ok", vec!["BDD-PD-FLOW-EVID-GATE-01".into()]);

        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some("t-gate-ok".into()),
                project_root: Some(DEMO_PROJECT_ROOT.into()),
                worktree_fingerprint: Some(DEMO_WORKTREE_FINGERPRINT.into()),
                guard: None,
            })
            .unwrap();
        let _ = host.poll_chunks(started.run_id).unwrap();
        assert_eq!(
            host.get_board()
                .tasks
                .iter()
                .find(|t| t.id == "t-gate-ok")
                .map(|t| t.zone.as_str()),
            Some("yellow")
        );

        host.seed_pass_evidence_for_test("ev-gate-1", "BDD-PD-FLOW-EVID-GATE-01");

        let after_accept = host.accept_work_item("t-gate-ok").expect("accept with EVID");
        assert_eq!(after_accept.green, 0);
        assert_eq!(
            after_accept
                .tasks
                .iter()
                .find(|t| t.id == "t-gate-ok")
                .map(|t| t.zone.as_str()),
            Some("yellow")
        );

        let after_complete = host
            .complete_work_item("t-gate-ok")
            .expect("complete with EVID+accept");
        assert_eq!(after_complete.green, 1);
        assert_eq!(
            after_complete
                .tasks
                .iter()
                .find(|t| t.id == "t-gate-ok")
                .map(|t| t.zone.as_str()),
            Some("green")
        );
    }

    #[test]
    fn list_commands_exposes_flow_evid_gate_entries() {
        let names: Vec<_> = DispatchHost::list_commands()
            .into_iter()
            .map(|c| c.name)
            .collect();
        assert!(names.contains(&"accept_work_item".to_string()));
        assert!(names.contains(&"complete_work_item".to_string()));
    }

    /// BDD-PD-WIRE-SMOKE-01 — command-path smoke (invoke → DispatchHost), not raw adapters.
    ///
    /// Under a fixture root: bind via `start_run` (WORK lease inside DispatchHost), then
    /// observe DryRun chunks **and** board projection via the same façade `load_local_board`
    /// feeds (`replace_projection_tasks`／`get_board`). Does **not** call AgentRouter／
    /// FakeGit／`load_board_file` directly. Full Tauri WebView IPC／`git_workbench_*` live
    /// invoke → NOT RUN in this unit path (see pytest). Never claims full-feature／Live PASS.
    #[test]
    fn pd_wire_smoke_01_bind_fixture_dispatch_host_observable() {
        const FIXTURE_ROOT: &str = "/fixture/wire-smoke-root";
        const WORK_ITEM: &str = "PD-WIRE-SMOKE-01";
        const FP: &str = "wire-smoke-fp";

        let mut host = DispatchHost::new();

        let names: Vec<_> = DispatchHost::list_commands()
            .into_iter()
            .map(|c| c.name)
            .collect();
        assert!(
            names.contains(&"start_run".to_string()),
            "catalogue must expose invoke start_run"
        );
        assert!(
            names.contains(&"load_local_board".to_string()),
            "catalogue must expose invoke load_local_board"
        );
        assert!(
            names.contains(&"get_board".to_string()),
            "catalogue must expose get_board"
        );

        // Board command-path seam (what load_local_board writes into DispatchHost).
        let board = host.replace_projection_tasks(vec![sgenaxis_core::TaskRecord {
            id: WORK_ITEM.into(),
            title: "wire smoke fixture".into(),
            zone: Zone::Gray,
        }]);
        assert!(
            board.tasks.iter().any(|t| t.id == WORK_ITEM),
            "board projection must show fixture work item"
        );
        assert_eq!(host.get_board().tasks.len(), 1);

        // DryRun via DispatchHost.start_run (= tauri command start_run), not raw AgentPort.
        let started = host
            .start_run(StartRunArgs {
                provider: ProviderDto::Cli,
                dry_run: true,
                work_item_id: Some(WORK_ITEM.into()),
                project_root: Some(FIXTURE_ROOT.into()),
                worktree_fingerprint: Some(FP.into()),
                guard: None,
            })
            .expect("DispatchHost.start_run under fixture root");
        assert!(started.dry_run);
        assert_eq!(started.provider, ProviderDto::Cli);

        let poll = host.poll_chunks(started.run_id).expect("poll_chunks");
        assert!(
            matches!(
                poll.chunks.first(),
                Some(ChunkDto::Started {
                    dry_run: true,
                    provider: ProviderDto::Cli,
                    ..
                })
            ),
            "first chunk must be Started dry_run via DispatchHost: {:?}",
            poll.chunks.first()
        );
        assert!(
            poll.chunks.iter().any(|c| {
                matches!(
                    c,
                    ChunkDto::Exited {
                        classification,
                        ..
                    } if classification == "success"
                )
            }),
            "DryRun must exit success via DispatchHost: {:?}",
            poll.chunks
        );

        eprintln!(
            "PD-WIRE-SMOKE-01 PASS (DispatchHost command-path: bind＋board＋DryRun). \
             Tauri WebView IPC／git_workbench_* live invoke → NOT RUN here. \
             NOT a full-feature Live／GA PASS."
        );
    }

    /// BDD-PD-REMAIN-WORK-TAGS-01: batch tags write into board projection domain.
    #[test]
    fn batch_work_tags_writes_board_projection() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "wi-a".into(),
            title: "Alpha".into(),
            zone: "gray".into(),
        })
        .unwrap();
        host.upsert_task(UpsertTaskArgs {
            id: "wi-b".into(),
            title: "Beta".into(),
            zone: "yellow".into(),
        })
        .unwrap();

        let board = host
            .batch_work_tags(BatchWorkTagsArgs {
                work_item_ids: vec!["wi-a".into(), "wi-b".into()],
                bdd: vec!["BDD-PD-REMAIN-WORK-TAGS-01".into()],
                tdd: vec!["TDD-REMAIN-TAGS-01".into()],
            })
            .expect("batch tags");

        assert_eq!(board.green, 0, "§7.1 tags must never auto-green");
        for id in ["wi-a", "wi-b"] {
            let t = board.tasks.iter().find(|t| t.id == id).expect("task");
            assert_eq!(t.bdd, vec!["BDD-PD-REMAIN-WORK-TAGS-01".to_string()]);
            assert_eq!(t.tdd, vec!["TDD-REMAIN-TAGS-01".to_string()]);
        }
        let evid = host.get_evidence_summary("wi-a");
        assert_eq!(evid.lines.len(), 1);
        assert_eq!(evid.lines[0].bdd_id, "BDD-PD-REMAIN-WORK-TAGS-01");
    }

    /// BDD-PD-REMAIN-WORK-TAGS-01: illegal／unknown → readable errors.
    #[test]
    fn batch_work_tags_rejects_illegal_with_readable_errors() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "wi-ok".into(),
            title: "Ok".into(),
            zone: "gray".into(),
        })
        .unwrap();

        let empty = host
            .batch_work_tags(BatchWorkTagsArgs {
                work_item_ids: vec![],
                bdd: vec!["BDD-X".into()],
                tdd: vec![],
            })
            .unwrap_err();
        assert!(empty.contains("未指定工項"), "{empty}");

        let no_tags = host
            .batch_work_tags(BatchWorkTagsArgs {
                work_item_ids: vec!["wi-ok".into()],
                bdd: vec![],
                tdd: vec![],
            })
            .unwrap_err();
        assert!(no_tags.contains("至少需一個"), "{no_tags}");

        let bad_tag = host
            .batch_work_tags(BatchWorkTagsArgs {
                work_item_ids: vec!["wi-ok".into()],
                bdd: vec!["BAD TAG".into()],
                tdd: vec![],
            })
            .unwrap_err();
        assert!(bad_tag.contains("非法BDD標籤"), "{bad_tag}");

        let unknown = host
            .batch_work_tags(BatchWorkTagsArgs {
                work_item_ids: vec!["missing".into()],
                bdd: vec!["BDD-X".into()],
                tdd: vec![],
            })
            .unwrap_err();
        assert!(unknown.contains("未知工項"), "{unknown}");
    }

    #[test]
    fn list_commands_exposes_batch_work_tags() {
        let names: Vec<_> = DispatchHost::list_commands()
            .into_iter()
            .map(|c| c.name)
            .collect();
        assert!(names.contains(&"batch_work_tags".to_string()));
    }

    /// BDD-PD-REMAIN-EDIT-01 path C: Command → DispatchHost → Core EditSession.
    #[test]
    fn edit_select_all_clear_undo_via_dispatch() {
        let mut host = DispatchHost::new();
        host.upsert_task(UpsertTaskArgs {
            id: "e1".into(),
            title: "One".into(),
            zone: "gray".into(),
        })
        .unwrap();
        host.upsert_task(UpsertTaskArgs {
            id: "e2".into(),
            title: "Two".into(),
            zone: "yellow".into(),
        })
        .unwrap();

        let all = host.edit_select_all();
        assert_eq!(all.status, "ok");
        assert_eq!(all.selected_count, 2);
        assert!(all.can_undo);

        let cleared = host.edit_clear();
        assert_eq!(cleared.selected_count, 0);

        let undone = host.edit_undo().unwrap();
        assert_eq!(undone.selected_count, 2);
        assert!(undone.can_redo);

        let redone = host.edit_redo().unwrap();
        assert_eq!(redone.selected_count, 0);

        let names: Vec<_> = DispatchHost::list_commands()
            .into_iter()
            .map(|c| c.name)
            .collect();
        for n in [
            "edit_undo",
            "edit_redo",
            "edit_select_all",
            "edit_clear",
            "edit_get_projection",
        ] {
            assert!(names.contains(&n.to_string()), "missing {n}");
        }
    }

    #[test]
    fn edit_undo_empty_is_readable_error() {
        let mut host = DispatchHost::new();
        let err = host.edit_undo().unwrap_err();
        assert!(err.contains("無可復原"), "{err}");
    }
}

#[cfg(test)]
#[path = "process_lifecycle_tests.rs"]
mod process_lifecycle_tests;

#[cfg(test)]
#[path = "guard_authority_tests.rs"]
mod guard_authority_tests;

#[cfg(test)]
#[path = "interactive_session_tests.rs"]
mod interactive_session_tests;
