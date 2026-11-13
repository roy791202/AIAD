//! IPC DTOs for Vanilla UI — projection／Run events only.
//! Adapter types (ProcessPort, McpClientPort, secrets) must never appear here.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

/// DOC-ENTRY-01: callers identify a project/reference, never an identity or root authority.
#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DocumentAdoptArgs {
    pub expected_project_id: String,
    pub reference: String,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct DocumentPrepareArgs {
    pub expected_project_root: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct DocumentPrepareResultDto {
    pub project_id: String,
    pub project_root: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(tag = "code", content = "detail")]
pub enum DocumentPrepareErrorDto {
    UnauthorizedCaller,
    ProjectNotBound,
    ProjectChanged,
    RootUnavailable,
    Busy,
    WorkspaceRejected { reason: String },
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
pub struct DocumentAdoptResultDto {
    pub outcome: String,
    pub document_id: String,
    pub kind: String,
    pub reference: String,
    pub revision_id: String,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(tag = "code", content = "detail")]
pub enum DocumentAdoptErrorDto {
    UnauthorizedCaller,
    ProjectNotBound,
    ProjectMismatch,
    InvalidProjectRoot,
    InvalidReference,
    UnsupportedKind,
    MalformedManifest,
    UnsupportedSchema,
    InvalidManifestRecord,
    InvalidDocumentId,
    DocumentIdConflict,
    ManifestChanged,
    RevisionConflict,
    ReferenceConflict,
    SourceRead(String),
    ManifestRead(String),
    CreateDirectory(String),
    Write(String),
    DurabilityUnverified,
}

/// Kanban zone string for UI (`gray`｜`blue`｜`yellow`｜`red`｜`green`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ZoneDto {
    Gray,
    Blue,
    Yellow,
    Red,
    Green,
}

impl ZoneDto {
    pub fn as_str(&self) -> &'static str {
        match self {
            ZoneDto::Gray => "gray",
            ZoneDto::Blue => "blue",
            ZoneDto::Yellow => "yellow",
            ZoneDto::Red => "red",
            ZoneDto::Green => "green",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "gray" => Some(ZoneDto::Gray),
            "blue" => Some(ZoneDto::Blue),
            "yellow" => Some(ZoneDto::Yellow),
            "red" => Some(ZoneDto::Red),
            "green" => Some(ZoneDto::Green),
            _ => None,
        }
    }
}

/// Read-only board projection consumed by the UI (BDD: 畫面只吃投影).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BoardView {
    pub generation: u64,
    pub gray: usize,
    pub blue: usize,
    pub yellow: usize,
    pub red: usize,
    pub green: usize,
    pub titles: Vec<String>,
    pub titles_by_zone: Vec<ZoneTitles>,
    pub tasks: Vec<TaskView>,
    /// PD-EXEC-SINGLE-01: at most one in-flight Run id (None when idle).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub active_run_id: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ZoneTitles {
    pub zone: String,
    pub titles: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct TaskView {
    pub id: String,
    pub title: String,
    pub zone: String,
    /// BDD tags bound to this work item (PD-REMAIN-WORK-TAGS-01).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub bdd: Vec<String>,
    /// TDD tags bound to this work item (PD-REMAIN-WORK-TAGS-01).
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub tdd: Vec<String>,
}

/// Provider selected by UI／FLOW — never an adapter type.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub enum ProviderDto {
    Cli,
    Mcp,
}

impl ProviderDto {
    pub fn as_str(self) -> &'static str {
        match self {
            ProviderDto::Cli => "cli",
            ProviderDto::Mcp => "mcp",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StartRunArgs {
    pub provider: ProviderDto,
    /// PD-CMD-01 wires DryRun; live spawn／mcp remain feature-gated in exec.
    #[serde(default = "default_true")]
    pub dry_run: bool,
    /// PD-EXEC-BIND-01: required — missing／empty rejected.
    #[serde(default)]
    pub work_item_id: Option<String>,
    /// PD-EXEC-BIND-01: required project root.
    #[serde(default)]
    pub project_root: Option<String>,
    /// PD-EXEC-BIND-01: required worktree fingerprint (aligned with WORK lease).
    #[serde(default)]
    pub worktree_fingerprint: Option<String>,
    /// PD-GUARD-CMD-01: when set, GUARD must allow before EXEC starts.
    #[serde(default)]
    pub guard: Option<sgenaxis_host::GuardPacketDto>,
}

fn default_true() -> bool {
    true
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StartRunResult {
    pub run_id: u64,
    pub provider: ProviderDto,
    pub dry_run: bool,
    pub board: BoardView,
    /// Envelope hash when GUARD gated this start (PD-GUARD-CMD-01).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub envelope_hash: Option<String>,
}

/// PD-GUARD-CMD-01 — GUARD packet + EXEC DryRun args for `start_implementation`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct StartImplementationArgs {
    pub guard: sgenaxis_host::GuardPacketDto,
    pub provider: ProviderDto,
    #[serde(default = "default_true")]
    pub dry_run: bool,
    pub work_item_id: Option<String>,
    pub project_root: Option<String>,
    /// PD-EXEC-BIND-01: required when starting EXEC via GUARD.
    #[serde(default)]
    pub worktree_fingerprint: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(tag = "kind", rename_all = "snake_case")]
pub enum ChunkDto {
    Started {
        run_id: u64,
        provider: ProviderDto,
        dry_run: bool,
        tool: Option<String>,
    },
    Chunk {
        run_id: u64,
        stream: String,
        text: String,
    },
    Progress {
        run_id: u64,
        message: String,
    },
    Exited {
        run_id: u64,
        classification: String,
        exit_code: Option<i32>,
    },
    Failed {
        run_id: u64,
        message: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PollResult {
    pub chunks: Vec<ChunkDto>,
    pub board: BoardView,
}

/// Menu／dispatch command catalogue entry (UI invokes by name only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CommandDescriptor {
    pub name: String,
    pub summary: String,
}

/// PD-REMAIN-EDIT-01 — selection／history projection (Command → Core EditSession).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EditProjectionDto {
    pub selected: Vec<String>,
    pub selected_count: usize,
    pub universe_count: usize,
    pub can_undo: bool,
    pub can_redo: bool,
    /// `ok`｜`empty`｜`noop` — never a fake PASS.
    pub status: String,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct UpsertTaskArgs {
    pub id: String,
    pub title: String,
    #[serde(default = "default_gray")]
    pub zone: String,
}

fn default_gray() -> String {
    "gray".into()
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SetZoneArgs {
    pub id: String,
    pub zone: String,
}

/// PD-BOARD-LIVE-01／PD-WIRE-ROOT-01 — optional path override when loading local board file.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct LoadLocalBoardArgs {
    /// Absolute or relative path to PROJECT-BOARD.html／JSON. Empty → use host settings.
    #[serde(default)]
    pub path: Option<String>,
    /// Bound project root (from settings／OPEN). Relative `path` resolves under this.
    /// Empty → use host `project_root`; still empty → unbound error.
    #[serde(default)]
    pub project_root: Option<String>,
    /// When true, persist the resolved path into host `board_path` (still no write-back to board file).
    #[serde(default)]
    pub persist_path: bool,
}

/// Result of a local board load — UI shows empty／error／ok from these fields.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LoadLocalBoardResult {
    /// `ok`｜`empty`｜`error`
    pub status: String,
    pub path: String,
    pub message: Option<String>,
    /// Always false for this card (protect: default no write-back).
    pub write_back: bool,
    pub board: BoardView,
}

/// PD-EVID-UI-01 — read-only evidence summary for Inspector.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EvidenceSummaryLineDto {
    pub bdd_id: String,
    pub status_label: String,
    pub verdict_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct EvidenceSummaryDto {
    pub work_item_id: String,
    pub title: Option<String>,
    pub zone: Option<String>,
    pub provider_terminal: String,
    /// Always false — Provider Success ≠ product green.
    pub provider_success_implies_green: bool,
    /// Never `"green"` from Provider Success alone.
    pub product_lamp_hint: String,
    pub ready_for_green: bool,
    pub overall_status: String,
    pub gaps: Vec<String>,
    pub lines: Vec<EvidenceSummaryLineDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GetEvidenceSummaryArgs {
    pub work_item_id: String,
}

/// PD-FLOW-EVID-GATE-01 — Accept／Complete work item (EVID+FLOW gated).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct WorkItemGateArgs {
    pub work_item_id: String,
}

/// PD-REMAIN-WORK-TAGS-01 — batch-apply BDD／TDD tags via Command → board projection.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct BatchWorkTagsArgs {
    /// One or more existing work item ids（批次）.
    pub work_item_ids: Vec<String>,
    /// BDD tag ids（可多個；空白＋tdd 空白 → 非法）.
    #[serde(default)]
    pub bdd: Vec<String>,
    /// TDD tag ids（可多個）.
    #[serde(default)]
    pub tdd: Vec<String>,
}

// ── PD-GIT-UI-01 read-only projection ───────────────────────────────────────

/// One working-tree path entry for the Git workbench list.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitEntryDto {
    pub path: String,
    pub kind: String,
}

/// One local branch for the branches view (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitBranchDto {
    pub name: String,
    pub is_current: bool,
}

/// One configured remote for the remotes view (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitRemoteDto {
    pub name: String,
    pub url: String,
    /// Last-known local connectivity; false when unknown (degrade, never invent).
    #[serde(default)]
    pub tested: bool,
}

/// One tag for the tags view (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitTagDto {
    pub name: String,
    /// Peeled commit OID; empty when unavailable (degrade, never invent).
    #[serde(default)]
    pub peeled: String,
}

/// One stash entry for the stash view (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitStashDto {
    pub id: String,
    pub message: String,
}

/// One unmerged path for the conflicts view (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitConflictFileDto {
    pub path: String,
    pub code: String,
    pub kind: String,
    #[serde(default)]
    pub ours: String,
    #[serde(default)]
    pub theirs: String,
}

/// Conflict snapshot for the conflicts view. Inactive when none / unavailable.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitConflictDto {
    pub active: bool,
    #[serde(default)]
    pub kind: String,
    #[serde(default)]
    pub source: String,
    #[serde(default)]
    pub target: String,
    #[serde(default)]
    pub files: Vec<GitConflictFileDto>,
}

/// Local identity + root `.gitignore` for the settings view (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitSettingsDto {
    #[serde(default)]
    pub author: String,
    #[serde(default)]
    pub email: String,
    #[serde(default)]
    pub ignore: String,
}

/// Recent commit line for the branch／log strip.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitCommitDto {
    pub hash: String,
    pub subject: String,
    /// Author name; empty when the log line omitted it (degrade, never invent).
    #[serde(default)]
    pub author: String,
    /// Author date (ISO 8601); empty when the log line omitted it.
    #[serde(default)]
    pub date: String,
}

/// Worktree summary projection; `writes_enabled` reflects host approving write adapter.
/// PD-WIRE-BOOT-01: unbound／非 git／缺檔 → `status=not_run`（可讀空態，不拋崩潰）.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitWorkbenchDto {
    pub repo: String,
    pub branch: Option<String>,
    pub entries: Vec<GitEntryDto>,
    pub entry_count: usize,
    pub recent_commits: Vec<GitCommitDto>,
    pub diff_text: String,
    /// Commits ahead of upstream (0 when the branch has no upstream).
    #[serde(default)]
    pub ahead: usize,
    /// Commits behind upstream (0 when the branch has no upstream).
    #[serde(default)]
    pub behind: usize,
    /// Upstream ref name when tracking a remote (e.g. `origin/main`).
    #[serde(default)]
    pub upstream: Option<String>,
    /// Local branches (current-first); empty when unavailable.
    #[serde(default)]
    pub branches: Vec<GitBranchDto>,
    /// Configured remotes (name-sorted); empty when unavailable.
    #[serde(default)]
    pub remotes: Vec<GitRemoteDto>,
    /// Tags (name + peeled OID, name-sorted); empty when unavailable.
    #[serde(default)]
    pub tags: Vec<GitTagDto>,
    /// Stashes (newest-first); empty when unavailable.
    #[serde(default)]
    pub stashes: Vec<GitStashDto>,
    /// Conflict snapshot; inactive/empty when unavailable (degrade, never block).
    #[serde(default)]
    pub conflict: GitConflictDto,
    /// Local identity + root `.gitignore`; empty when unavailable (degrade, never block).
    #[serde(default)]
    pub settings: GitSettingsDto,
    /// When true, UI may offer commit／push; each mutation still needs explicit approval
    /// (PD-GIT-WRITE-UI-01 → GitWriteApproval).
    pub writes_enabled: bool,
    /// `ok`｜`empty`｜`not_run`｜`error` — boot／bind 空態契約（PD-WIRE-BOOT-01）.
    #[serde(default = "git_workbench_status_ok")]
    pub status: String,
    /// Human-readable reason when `status` is not `ok`.
    #[serde(default)]
    pub message: Option<String>,
}

fn git_workbench_status_ok() -> String {
    "ok".into()
}

/// Pathspec-scoped unified diff (read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitDiffDto {
    pub repo: String,
    pub pathspec: Option<String>,
    pub diff_text: String,
}

/// Args for approval-gated commit (PD-GIT-WRITE-UI-01).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteCommitArgs {
    pub repo: Option<String>,
    pub message: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated push (PD-GIT-WRITE-UI-01). Force push is forbidden.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWritePushArgs {
    pub repo: Option<String>,
    pub remote: String,
    pub refspec: Option<String>,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated branch switch (PD-GIT-SWITCH-03). Existing branch only.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteSwitchArgs {
    pub repo: Option<String>,
    pub branch: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local identity (`git config --local user.name` / `user.email`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteIdentityArgs {
    pub repo: Option<String>,
    pub author: String,
    pub email: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated root `.gitignore` write (never untrack existing files).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteIgnoreArgs {
    pub repo: Option<String>,
    pub ignore: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated stash apply / pop / drop (`stash@{n}` only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteStashArgs {
    pub repo: Option<String>,
    /// Stash selector, e.g. `stash@{0}`. Never flags or other stash verbs.
    pub stash: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated `git stash push -m` (tracked-only; never `-u` / `--all`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteStashPushArgs {
    pub repo: Option<String>,
    /// Stash message passed to `git stash push -m`. Never flags.
    pub message: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local tag create (`git tag -- name` or `git tag -a -m`).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteTagArgs {
    pub repo: Option<String>,
    /// Tag name. Never flags (`-f`, `--delete`).
    pub name: String,
    /// Empty → lightweight; non-empty → annotated `-m`.
    #[serde(default)]
    pub message: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local tag delete (`git tag -d -- name`). Never push.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteTagDeleteArgs {
    pub repo: Option<String>,
    /// Tag name. Never flags (`-f`, `--delete`) and never a remote refspec.
    pub name: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local branch create (`git branch -- name`). Never switch.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteBranchCreateArgs {
    pub repo: Option<String>,
    /// Local branch name. Never flags (`-C`, `-D`, `--set-upstream`).
    pub name: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local branch delete (`git branch -d -- name`). Never `-D`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteBranchDeleteArgs {
    pub repo: Option<String>,
    /// Local branch name. Never flags (`-D`, `--force`, `-r`) and never current HEAD.
    pub name: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local `git remote add -- name url`. Never fetch/`-f`/set-url/push.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteRemoteAddArgs {
    pub repo: Option<String>,
    /// Remote name. Never flags (`-f`, `--mirror`, `set-url`).
    pub name: String,
    /// Remote URL. Never flags; never `set-url`.
    pub url: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local `git remote remove -- name`. Never prune/fetch.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteRemoteRemoveArgs {
    pub repo: Option<String>,
    /// Remote name. Never flags (`-f`, `prune`, `push`).
    pub name: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated local `git remote set-url -- name url`. Never fetch/push.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteRemoteSetUrlArgs {
    pub repo: Option<String>,
    /// Existing remote name. Never flags (`-f`, `--mirror`, `--push`, `--add`).
    pub name: String,
    /// Replacement fetch URL. Never flags; never `--push` URL.
    pub url: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated conflict save (`git add -- path` after the UI/host wrote the file).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteConflictSaveArgs {
    pub repo: Option<String>,
    /// Conflicted relative path. Never `.` / `-A` / flags.
    pub path: String,
    /// Optional resolution body. Host writes this path then the port stages it.
    #[serde(default)]
    pub contents: String,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Args for approval-gated conflict continue / abort.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Default)]
pub struct GitWriteConflictOpArgs {
    pub repo: Option<String>,
    /// Must be `true` after UI confirm; `false` → no mutation.
    pub approved: bool,
}

/// Result of a gated write attempt (commit／push).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GitWriteResultDto {
    pub ok: bool,
    pub op: String,
    pub message: String,
    /// Always `true` when push fails — local commits are never discarded.
    pub local_preserved: bool,
}

// ── PD-SPEC-UI-01 ModuleSpec／契約唯讀投影 ───────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecContractDto {
    pub id: String,
    pub title: String,
    pub body: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecRevisionSummaryDto {
    pub id: String,
    pub version_label: String,
    /// `draft`｜`approved`
    pub status: String,
    pub contract_count: usize,
    pub content_hash: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecEvidenceRefDto {
    pub id: String,
    pub bound_revision_id: String,
    /// `valid`｜`needs_revalidation`
    pub validity: String,
}

/// Read-only Spec projection for the ModuleSpec panel.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecProjectionDto {
    pub loaded: bool,
    pub module_id: String,
    pub module_name: String,
    pub responsibility: String,
    pub revisions: Vec<SpecRevisionSummaryDto>,
    pub evidence_refs: Vec<SpecEvidenceRefDto>,
    pub evidence_needing_revalidation: usize,
}

/// Full revision with contracts (UI display; approved → treat as read-only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecRevisionDto {
    pub id: String,
    pub module_id: String,
    pub version_label: String,
    pub status: String,
    pub content_hash: Option<String>,
    pub contracts: Vec<SpecContractDto>,
    /// True when status is approved — UI must not offer in-place edit.
    pub immutable: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecTrySetContractArgs {
    pub revision_id: String,
    pub contract_id: String,
    pub new_body: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecReviseArgs {
    pub from_revision_id: String,
    pub new_revision_id: String,
    pub new_version_label: String,
    /// Optional contract bodies for the new Draft; empty → clone baseline contracts.
    #[serde(default)]
    pub contracts: Vec<SpecContractDto>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecApproveArgs {
    pub revision_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SpecGetRevisionArgs {
    pub revision_id: String,
}

// ── PD-REMAIN-ARCH-UI-01 ─────────────────────────────────────────────────────

/// One module node in the architecture projection (Command-sourced; not UI-static).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArchModuleDto {
    pub id: String,
    pub name: String,
    /// `presentation`｜`ipc`｜`host`｜`domain`｜`ports`｜`adapters`
    pub layer: String,
    pub role: String,
}

/// Directed dependency edge `from` → `to` (module ids).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArchEdgeDto {
    pub from: String,
    pub to: String,
    pub kind: String,
}

/// Read-only module／dependency projection for the arch panel.
///
/// `status`: `ok` when modules present; `empty` when no graph; UI maps no-IPC → NOT RUN.
/// Never treat a hard-coded HTML diagram as live — only this DTO after `arch_get_projection`.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArchProjectionDto {
    /// `ok`｜`empty`｜`not_run`
    pub status: String,
    /// True only when this payload came from DispatchHost Command projection.
    pub live: bool,
    pub source: String,
    pub modules: Vec<ArchModuleDto>,
    pub edges: Vec<ArchEdgeDto>,
    pub generation: u64,
}

// ── PD-REMAIN-LISTEN-UI-01 ───────────────────────────────────────────────────

/// Read-only FS／Git／Agent listen snapshot for the Listen panel.
///
/// UI → `listen_get_projection` only — never OS `notify`／pipe from JS.
/// `status`: `empty` when no domain events yet; `ok` after bridge apply.
/// Host OS FS／Git watch loops that are not wired stay `NOT RUN` in the gap fields.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ListenProjectionDto {
    /// `empty`｜`ok`
    pub status: String,
    pub generation: u64,
    pub event_count: u64,
    pub last_fs_path: Option<String>,
    pub last_fs_burst: u32,
    pub last_git_root: Option<String>,
    pub last_git_burst: u32,
    pub last_agent_run: Option<u64>,
    pub last_agent_kind: Option<String>,
    pub last_agent_burst: u32,
    pub last_agent_classification: Option<String>,
    pub last_agent_exit_code: Option<i32>,
    pub pending_reconcile: bool,
    pub last_reconcile_run: Option<u64>,
    pub ended_runs: Vec<u64>,
    /// Host WinFsNotify／pump loop — `NOT RUN` until Tauri host wires it.
    pub host_fs_watch: String,
    /// Host Git watch loop — `NOT RUN` until wired.
    pub host_git_watch: String,
    /// Agent ingress via `poll_chunks` → EventBridge (wired).
    pub host_agent_bridge: String,
    pub note: Option<String>,
}

// ── GUARD-S1: reviewed DTO declarations only (no handler switch / fallback) ─
// Shapes from owner-approved dto-schema.json. Existing StartRun／StartImplementation
// commands remain on legacy GuardPacket until a separately gated migration slice.

/// Owner classify task intent + optional implementation candidate draft.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct OwnerClassifyGuardTaskArgs {
    pub task_id: String,
    /// `generic`｜`implementation`
    pub intent: String,
    #[serde(default)]
    pub candidate: Option<CandidateDraft>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct CandidateDraft {
    pub module_id: String,
    pub project_id: String,
    pub manifest_revision: String,
    pub input_paths: Vec<String>,
    pub architecture_paths: Vec<String>,
    pub bdd_paths: Vec<String>,
    pub skeleton_paths: Vec<String>,
    pub test_paths: Vec<String>,
    pub envelope: EnvelopeDraft,
    pub red_job: RedJobDraft,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct EnvelopeDraft {
    pub primary_module: String,
    #[serde(default)]
    pub integration_modules: Vec<String>,
    pub allowed_patterns: Vec<String>,
    #[serde(default)]
    pub protected_patterns: Vec<String>,
    /// Sorted module → relative prefix map (BTreeMap for stable JSON).
    #[serde(default)]
    pub module_prefixes: BTreeMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct RedJobDraft {
    pub program: String,
    pub build_argv: Vec<String>,
    pub cwd_ref: String,
    pub test_target: String,
    pub test_id: String,
    pub bdd_id: String,
    /// Fixed approved maximum (120000); client override rejected at HOST.
    pub timeout_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct OwnerRequestGuardRedCaptureArgs {
    pub candidate_ref: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct OwnerRequestGuardApprovalArgs {
    pub candidate_ref: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct OwnerRevokeGuardApprovalArgs {
    pub approval_ref: u64,
}

/// Reference-only implementation start (approval_ref required; no caller approved bool).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct GuardReferenceStartImplementationArgs {
    pub approval_ref: u64,
    pub provider: ProviderDto,
    #[serde(default = "default_true")]
    pub dry_run: bool,
    pub work_item_id: String,
    #[serde(default)]
    pub project_root: Option<String>,
    #[serde(default)]
    pub worktree_fingerprint: Option<String>,
}

/// Reference-only generic start; legacy `guard` packet rejected as authority.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(deny_unknown_fields)]
pub struct GuardReferenceStartRunArgs {
    pub provider: ProviderDto,
    #[serde(default = "default_true")]
    pub dry_run: bool,
    pub work_item_id: String,
    #[serde(default)]
    pub project_root: Option<String>,
    #[serde(default)]
    pub worktree_fingerprint: Option<String>,
    #[serde(default)]
    pub guard: Option<sgenaxis_host::GuardPacketDto>,
    #[serde(default)]
    pub approval_ref: Option<u64>,
}

/// Read-only owner projection (HOST-computed digests only).
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct GuardOwnerProjection {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub candidate_ref: Option<u64>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub approval_ref: Option<u64>,
    /// pending_confirmation｜capture_requested｜capture_running｜red_unqualified｜
    /// awaiting_red_qualification｜ready_for_approval｜approved｜consumed｜revoked｜stale｜rejected
    pub state: String,
    pub task_id: String,
    pub intent: String,
    pub module_id: String,
    pub project_id: String,
    pub input_snapshot_fingerprint: String,
    pub artifact_digests: BTreeMap<String, String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub red_evidence_id: Option<String>,
    pub diagnostic_code: String,
    pub message: String,
}
