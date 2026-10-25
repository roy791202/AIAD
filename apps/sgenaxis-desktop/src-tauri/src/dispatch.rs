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
use std::time::Duration;

use sgenaxis_adapters::{FakeProcess, StdProcess};
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
    AgentRouter, CliAgentAdapter, CliAgentSettings, ExitClassification, FakeMcpClient,
    McpAgentAdapter, McpAgentSettings, OutputStream, RunId, StartRunRequest,
};
use sgenaxis_ports::ProcessPort;
use sgenaxis_host::{
    authorize_exec_start, authorize_write_paths, check_changes_view, check_start_view,
    GuardDecisionView, GuardExecPass, GuardPacketDto,
};
use sgenaxis_listen::{EventBridge, ListenProjection, SourceEvent};
use sgenaxis_spec::{
    ApprovalStatus, Contract, EvidenceValidity, SpecError, SpecStore,
};
use sgenaxis_work::{FakePathProbe, FakeWorkspaceStore, WorkspaceService};

use crate::dto::{
    ArchEdgeDto, ArchModuleDto, ArchProjectionDto, BatchWorkTagsArgs, BoardView, ChunkDto,
    CommandDescriptor, EditProjectionDto, EvidenceSummaryDto, EvidenceSummaryLineDto,
    ListenProjectionDto, PollResult, ProviderDto, SpecApproveArgs, SpecContractDto,
    SpecEvidenceRefDto, SpecGetRevisionArgs, SpecProjectionDto, SpecReviseArgs, SpecRevisionDto,
    SpecRevisionSummaryDto, SpecTrySetContractArgs, StartImplementationArgs, StartRunArgs,
    StartRunResult, TaskView, UpsertTaskArgs, ZoneDto, ZoneTitles,
};

/// Sample ModuleSpec fixture (same bytes as sgenaxis-spec unit tests).
const SAMPLE_MODULE_SPEC: &str =
    include_str!("../../crates/sgenaxis-spec/fixtures/sample_module_spec.json");

/// Host-side dispatch state: Core engine + EXEC router (DryRun adapters) + EVID + SPEC + WORK.
pub struct DispatchHost {
    engine: Engine,
    exec: AgentRouter,
    /// WORK registry + execution leases (PD-EXEC-BIND-01／PD-WORK-01).
    work: WorkspaceService<FakePathProbe, FakeWorkspaceStore>,
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
}

impl Default for DispatchHost {
    fn default() -> Self {
        Self::new()
    }
}

impl DispatchHost {
    /// Compose Fake Process + Fake MCP Live seam (`real-mcp`).
    /// DryRun never dials OS; Live CLI needs [`Self::wire_cli_live`] (StdProcess／test ProcessPort).
    /// Live MCP uses in-process [`FakeMcpClient`] (no OS socket／cloud) after settings apply.
    pub fn new() -> Self {
        let exec = AgentRouter::new(
            CliAgentAdapter::with_defaults(Box::new(FakeProcess::new())),
            McpAgentAdapter::with_defaults(Box::new(FakeMcpClient::default())),
        );
        let probe = FakePathProbe::new();
        probe.accept_any_path();
        Self {
            engine: Engine::new(),
            exec,
            work: WorkspaceService::new(probe, FakeWorkspaceStore::new()),
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
        }
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
                        return Err(format!(
                            "NOT RUN: no activatable MCP Live target (endpoint={endpoint:?}); \
                             禁 :8788／:8787；空／未設目標不可 Live；秘密不進投影"
                        ));
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

        let run_id = self.exec.start_run(req).map_err(|e| e.to_string())?;

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
        // Drain so Cancelled classification applies, lease releases, Busy clears.
        let _ = self.poll_chunks(run_id)?;
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

#[cfg(test)]
mod tests {
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

        let board = host.cancel_run(second.run_id).expect("cancel");
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

        let board = host.cancel_run(started.run_id).expect("cancel");
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
        let board = host.cancel_run(started.run_id).expect("cancel");
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
