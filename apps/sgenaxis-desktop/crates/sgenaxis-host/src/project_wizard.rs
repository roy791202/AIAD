//! M01-S3 wizard command bridge — wraps the S2 project-definition DOMAIN
//! (`crate::project_definition` + `sgenaxis_work::project_definition`) as a
//! step-wise lifecycle the Tauri command layer can expose over IPC.
//!
//! Boundaries (HEX / DDD):
//! - This module holds NO filesystem ownership; all effects pass the declared
//!   Ports (`FileSystemPort` / `FileCommitPort`) supplied by the command layer.
//! - In-flight state (option A) is held server-side in [`WizardSessionStore`],
//!   keyed by an opaque [`WizardToken`] handed to the UI. The UI never sees
//!   [`DefinitionBinding`] internals or the non-serde [`ProjectDefinition`].
//! - Serde DTOs (request/view/receipt/error) are defined HERE, at the bridge
//!   boundary, and the domain → DTO mapping happens here. The domain
//!   `ProjectDefinition` keeps its Debug/Clone/PartialEq/Eq-only derive set.
//! - Authority ([`DefinitionAuthorityContext`]) is produced from a host-owned
//!   owner-window snapshot ([`snapshot_definition_authority`]); it is NEVER
//!   inferred from a UI-supplied root.
//!
//! SKELETON + RED: the filesystem orchestration [`wizard_commit`] is NOT
//! implemented; it returns [`WizardBridgeError::NotImplemented`]. The other
//! lifecycle entrypoints manage in-flight draft state only (no IO) so the RED
//! integration test can drive begin → apply → prepare → commit and observe the
//! sentinel exactly at the commit boundary.

use std::collections::BTreeMap;

use serde::{Deserialize, Serialize};

use sgenaxis_ports::{FileCommitPort, FileSystemPort};
use sgenaxis_work::project_definition::{
    missing_generation_requirements, validate_definition, DefinitionDraft, DefinitionError,
    DefinitionMode, DefinitionRequirement, DefinitionRevision, DeliveryTarget, ExtensionValue,
    FieldState, PersistentProjectId, PreferenceSource, ProjectDefinition, RequirementState,
    WizardStep,
};

use crate::project_definition::{
    bind_definition, save_definition, DefinitionAuthorityContext, DefinitionBaseline,
    DefinitionBinding, DefinitionLocation, DefinitionSaveReceipt, DefinitionStoreError,
    PreferenceCommitStatus, PreparedPreferencePlan,
};
use crate::project_preferences::PreferenceChoice;

// ───────────────────────── Owner-snapshot authority ─────────────────────────

/// Host-owned owner-window snapshot. The command layer fills this from the
/// *live* DispatchHost owner (window label + selection + session), never from
/// any UI-supplied project root. It is the sole authorized source of a
/// [`DefinitionAuthorityContext`].
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OwnerWindowSnapshot {
    pub owner_window: String,
    pub selection_id: String,
    pub session_id: String,
}

/// Produce a [`DefinitionAuthorityContext`] from a host-owned owner snapshot.
///
/// This is the owner-snapshot authority *producer* prerequisite. A non-empty
/// snapshot is required; emptiness is treated as "no live owner" and rejected,
/// mirroring the domain `NotBound` contract. Authority is derived only from the
/// host's own owner facts.
pub fn snapshot_definition_authority(
    snapshot: &OwnerWindowSnapshot,
) -> Result<DefinitionAuthorityContext, WizardBridgeError> {
    if [
        &snapshot.owner_window,
        &snapshot.selection_id,
        &snapshot.session_id,
    ]
    .iter()
    .any(|s| s.trim().is_empty())
    {
        return Err(WizardBridgeError::Unauthorized);
    }
    Ok(DefinitionAuthorityContext {
        selection_id: snapshot.selection_id.clone(),
        session_id: snapshot.session_id.clone(),
        owner_window: snapshot.owner_window.clone(),
    })
}

// ───────────────────────────── Opaque token ─────────────────────────────────

/// Opaque handle to one server-side in-flight wizard session. The UI round-trips
/// this and never sees binding internals.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord)]
pub struct WizardToken(String);

impl WizardToken {
    /// Reconstruct a token from the raw string the UI passes back.
    pub fn from_raw(raw: impl Into<String>) -> Self {
        Self(raw.into())
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

// ───────────────────────── Server-side in-flight state ───────────────────────

/// One wizard session's in-flight state (option A: held server-side). Carries
/// the non-serde draft and the (optional) committed binding so the UI never
/// observes either.
///
/// Fields `location`/`baseline`/`prepared`/`binding` are stored by the skeleton
/// but consumed only by the GREEN `wizard_commit` orchestration (bind + save).
#[allow(dead_code)]
#[derive(Debug, Clone)]
struct InFlight {
    authority: DefinitionAuthorityContext,
    location: DefinitionLocation,
    baseline: DefinitionBaseline,
    prepared: PreparedPreferencePlan,
    draft: ProjectDefinition,
    binding: Option<DefinitionBinding>,
}

/// Opaque-token-keyed holder for in-flight wizard sessions. Owned by the command
/// layer (`HostState`) in production and constructed directly by tests.
#[derive(Debug, Default)]
pub struct WizardSessionStore {
    next: u64,
    minted: u64,
    sessions: BTreeMap<String, InFlight>,
}

impl WizardSessionStore {
    pub fn new() -> Self {
        Self::default()
    }

    /// Mint a fresh persistent project identity, host-side.
    ///
    /// Identity minting is a HOST responsibility (never derived from a UI root).
    /// A monotonic per-store counter is formatted as a RFC-4122 v4-shaped uuid so
    /// it passes the domain's structural `valid_uuid` check without pulling a uuid
    /// dependency into this crate. It is unique within one running store; a
    /// process-global random id is a defensible later refinement.
    fn mint_identity(&mut self) -> PersistentProjectId {
        self.minted = self.minted.wrapping_add(1);
        PersistentProjectId::candidate(format!("00000000-0000-4000-8000-{:012x}", self.minted))
    }

    /// Number of live in-flight sessions (diagnostics / tests).
    pub fn len(&self) -> usize {
        self.sessions.len()
    }

    pub fn is_empty(&self) -> bool {
        self.sessions.is_empty()
    }

    fn issue(&mut self) -> WizardToken {
        self.next = self.next.wrapping_add(1);
        WizardToken(format!("wiz-{:016x}", self.next))
    }

    fn insert(&mut self, token: &WizardToken, state: InFlight) {
        self.sessions.insert(token.0.clone(), state);
    }

    fn get(&self, token: &WizardToken) -> Result<&InFlight, WizardBridgeError> {
        self.sessions
            .get(&token.0)
            .ok_or(WizardBridgeError::UnknownToken)
    }

    fn get_mut(&mut self, token: &WizardToken) -> Result<&mut InFlight, WizardBridgeError> {
        self.sessions
            .get_mut(&token.0)
            .ok_or(WizardBridgeError::UnknownToken)
    }

    fn remove(&mut self, token: &WizardToken) -> Result<InFlight, WizardBridgeError> {
        self.sessions
            .remove(&token.0)
            .ok_or(WizardBridgeError::UnknownToken)
    }
}

// ───────────────────────────────── DTOs ─────────────────────────────────────

/// Serde-safe mirror of the domain [`WizardStep`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "kebab-case")]
pub enum WizardStepDto {
    Basics,
    Delivery,
    Topology,
    Requirements,
    TechnologyUi,
    Preview,
}

impl From<WizardStepDto> for WizardStep {
    fn from(step: WizardStepDto) -> Self {
        match step {
            WizardStepDto::Basics => WizardStep::Basics,
            WizardStepDto::Delivery => WizardStep::Delivery,
            WizardStepDto::Topology => WizardStep::Topology,
            WizardStepDto::Requirements => WizardStep::Requirements,
            WizardStepDto::TechnologyUi => WizardStep::TechnologyUi,
            WizardStepDto::Preview => WizardStep::Preview,
        }
    }
}

impl From<WizardStep> for WizardStepDto {
    fn from(step: WizardStep) -> Self {
        match step {
            WizardStep::Basics => WizardStepDto::Basics,
            WizardStep::Delivery => WizardStepDto::Delivery,
            WizardStep::Topology => WizardStepDto::Topology,
            WizardStep::Requirements => WizardStepDto::Requirements,
            WizardStep::TechnologyUi => WizardStepDto::TechnologyUi,
            WizardStep::Preview => WizardStepDto::Preview,
        }
    }
}

/// Serde-safe kind of a prepared preferences plan (never carries raw bytes).
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "kebab-case")]
pub enum PreferencePlanKind {
    Skip,
    Preset,
    ImportedCopy,
}

/// Request DTO: a partial patch of one wizard step's inputs. Every field is
/// optional; `wizard_apply_step` maps the subset relevant to the named step into
/// the in-flight draft. Empty/absent fields are no-ops, so a default patch leaves
/// the draft unchanged. Delivery/TechnologyUi fields feed a single delivery
/// target; requirement fields feed a single requirement.
#[derive(Debug, Clone, Default, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct WizardDraftPatch {
    // Basics
    pub name: Option<String>,
    pub purpose: Option<String>,
    // Delivery (single target)
    pub delivery_form: Option<String>,
    pub delivery_platform: Option<String>,
    pub delivery_language: Option<String>,
    pub delivery_framework: Option<String>,
    pub delivery_has_ui: Option<bool>,
    // Topology
    pub topology: Option<String>,
    // Requirements (single requirement)
    pub requirement_intent: Option<String>,
    /// Newline/comma-separated acceptance list.
    pub requirement_acceptance: Option<String>,
    // TechnologyUi (refines the single delivery target)
    pub delivery_host: Option<String>,
    pub delivery_host_version: Option<String>,
    /// Comma-separated toolchain list.
    pub delivery_toolchain: Option<String>,
}

/// Response DTO: a read-only projection of the in-flight draft. Never exposes
/// the binding or the non-serde `ProjectDefinition`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WizardDraftView {
    pub name: String,
    pub purpose: String,
    pub last_saved_step: WizardStepDto,
    pub preference_source: String,
    /// Confirmed topology value, if any.
    pub topology: Option<String>,
    pub delivery_count: usize,
    pub requirement_count: usize,
    /// Field paths still missing for generation (projection; never blocks commit).
    pub missing_generation_requirements: Vec<String>,
}

/// Response DTO: validation outcome of applying one step.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WizardValidationDto {
    pub ok: bool,
    pub invalid_field: Option<String>,
}

/// `wizard_begin` result.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WizardBeginView {
    pub token: String,
    pub step: WizardStepDto,
    pub view: WizardDraftView,
}

/// `wizard_apply_step` result.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WizardStepView {
    pub step: WizardStepDto,
    pub validation: WizardValidationDto,
    pub view: WizardDraftView,
}

/// `wizard_prepare_preferences` result.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WizardPreferencePlanView {
    pub kind: PreferencePlanKind,
    pub preset_id: Option<String>,
}

/// `wizard_commit` result (GREEN maps `DefinitionSaveReceipt` → this).
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct WizardCommitReceipt {
    pub project_root: String,
    pub relative_path: String,
    pub persisted_revision: u64,
    pub raw_digest: String,
    pub transaction_id: String,
    pub preferences_committed: bool,
}

/// Bridge-layer error DTO. Serializable so the command layer can forward it to
/// the UI without leaking the non-serde domain `DefinitionStoreError`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
#[serde(tag = "code", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum WizardBridgeError {
    /// Owner snapshot was empty / no live owner window.
    Unauthorized,
    /// Token does not match a live in-flight session.
    UnknownToken,
    /// A draft input failed the pure WORK validator.
    InvalidInput { field: String },
    /// The domain bind/save boundary rejected the commit (digest / revision /
    /// existing-target / storage fault). Carries the domain error's debug form.
    Commit { message: String },
    /// SKELETON sentinel: orchestration body not yet implemented (RED).
    NotImplemented { detail: String },
}

impl From<DefinitionStoreError> for WizardBridgeError {
    fn from(err: DefinitionStoreError) -> Self {
        WizardBridgeError::Commit {
            message: format!("{err:?}"),
        }
    }
}

impl std::fmt::Display for WizardBridgeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WizardBridgeError::Unauthorized => write!(f, "UNAUTHORIZED"),
            WizardBridgeError::UnknownToken => write!(f, "UNKNOWN_TOKEN"),
            WizardBridgeError::InvalidInput { field } => write!(f, "INVALID_INPUT: {field}"),
            WizardBridgeError::Commit { message } => write!(f, "COMMIT_REJECTED: {message}"),
            WizardBridgeError::NotImplemented { detail } => {
                write!(f, "NOT_IMPLEMENTED: {detail}")
            }
        }
    }
}

impl std::error::Error for WizardBridgeError {}

impl From<DefinitionError> for WizardBridgeError {
    fn from(err: DefinitionError) -> Self {
        match err {
            DefinitionError::InvalidInput { field } => WizardBridgeError::InvalidInput { field },
            other => WizardBridgeError::InvalidInput {
                field: format!("{other:?}"),
            },
        }
    }
}

// ───────────────────────────── Draft helpers ────────────────────────────────

fn empty_draft(name: &str, purpose: &str) -> DefinitionDraft {
    DefinitionDraft {
        name: name.to_owned(),
        purpose: purpose.to_owned(),
        last_saved_step: WizardStep::Basics,
        delivery_targets: Vec::new(),
        topology: FieldState::Unresolved,
        requirements: Vec::new(),
        preference_source: PreferenceSource::Skip,
        template: None,
        open_decisions: Vec::new(),
        extensions: BTreeMap::<String, ExtensionValue>::new(),
    }
}

fn draft_view(def: &ProjectDefinition) -> WizardDraftView {
    let topology = match &def.draft.topology {
        FieldState::Confirmed(v) => Some(v.clone()),
        _ => None,
    };
    WizardDraftView {
        name: def.draft.name.clone(),
        purpose: def.draft.purpose.clone(),
        last_saved_step: def.draft.last_saved_step.into(),
        preference_source: match def.draft.preference_source {
            PreferenceSource::Skip => "skip",
            PreferenceSource::Preset => "preset",
            PreferenceSource::ImportedCopy => "imported-copy",
        }
        .to_owned(),
        topology,
        delivery_count: def.draft.delivery_targets.len(),
        requirement_count: def.draft.requirements.len(),
        missing_generation_requirements: missing_generation_requirements(def),
    }
}

/// `Confirmed` for a non-blank value, else `Unresolved`.
fn field_state(value: Option<String>) -> Option<FieldState<String>> {
    value.map(|s| {
        if s.trim().is_empty() {
            FieldState::Unresolved
        } else {
            FieldState::Confirmed(s)
        }
    })
}

/// Split a comma/newline-separated list into trimmed, non-empty entries.
fn split_list(value: Option<String>) -> Option<Vec<String>> {
    value.map(|s| {
        s.split([',', '\n', ';'])
            .map(|x| x.trim().to_owned())
            .filter(|x| !x.is_empty())
            .collect()
    })
}

/// Ensure the single delivery target exists (id = the project uuid, which is a
/// valid uuid and trivially unique for one target) and return it for mutation.
fn ensure_target<'a>(draft: &'a mut DefinitionDraft, uuid: &str) -> &'a mut DeliveryTarget {
    if draft.delivery_targets.is_empty() {
        draft.delivery_targets.push(DeliveryTarget {
            id: uuid.to_owned(),
            form: FieldState::Unresolved,
            platform: FieldState::Unresolved,
            host: FieldState::Unresolved,
            host_version: FieldState::Unresolved,
            language: FieldState::Unresolved,
            framework: FieldState::Unresolved,
            toolchain: Vec::new(),
            has_ui: None,
        });
    }
    &mut draft.delivery_targets[0]
}

fn delivery_has_input(patch: &WizardDraftPatch) -> bool {
    patch.delivery_form.is_some()
        || patch.delivery_platform.is_some()
        || patch.delivery_language.is_some()
        || patch.delivery_framework.is_some()
        || patch.delivery_has_ui.is_some()
}

fn technology_has_input(patch: &WizardDraftPatch) -> bool {
    patch.delivery_host.is_some()
        || patch.delivery_host_version.is_some()
        || patch.delivery_toolchain.is_some()
}

fn plan_kind(plan: &PreparedPreferencePlan) -> PreferencePlanKind {
    match plan {
        PreparedPreferencePlan::Skip => PreferencePlanKind::Skip,
        PreparedPreferencePlan::Preset { .. } => PreferencePlanKind::Preset,
        PreparedPreferencePlan::ImportedCopy { .. } => PreferencePlanKind::ImportedCopy,
    }
}

// ─────────────────────────── Lifecycle entrypoints ──────────────────────────

/// Begin a wizard session: validate the owner authority, build an initial
/// in-flight draft (no filesystem), store it, and hand back an opaque token.
///
/// The initial draft carries a placeholder identity; real identity minting and
/// `open_definition` adoption for Existing/Legacy locations are GREEN work.
pub fn wizard_begin(
    store: &mut WizardSessionStore,
    authority: DefinitionAuthorityContext,
    location: DefinitionLocation,
    name: &str,
    purpose: &str,
) -> Result<WizardBeginView, WizardBridgeError> {
    if [&authority.selection_id, &authority.session_id, &authority.owner_window]
        .iter()
        .any(|s| s.trim().is_empty())
    {
        return Err(WizardBridgeError::Unauthorized);
    }
    let draft = ProjectDefinition {
        project_uuid: store.mint_identity(),
        definition_revision: DefinitionRevision(0),
        draft: empty_draft(name, purpose),
        mode: DefinitionMode::Draft,
        approval_refs: Vec::new(),
        legacy_root_keys: Vec::new(),
    };
    let token = store.issue();
    let view = draft_view(&draft);
    store.insert(
        &token,
        InFlight {
            authority,
            location,
            baseline: DefinitionBaseline::Absent,
            prepared: PreparedPreferencePlan::Skip,
            draft,
            binding: None,
        },
    );
    Ok(WizardBeginView {
        token: token.0,
        step: WizardStepDto::Basics,
        view,
    })
}

/// Apply one wizard step's input patch to the in-flight draft and report the
/// pure-WORK validation outcome. No filesystem; no binding.
pub fn wizard_apply_step(
    store: &mut WizardSessionStore,
    token: &WizardToken,
    step: WizardStepDto,
    patch: WizardDraftPatch,
) -> Result<WizardStepView, WizardBridgeError> {
    let state = store.get_mut(token)?;
    let uuid = state.draft.project_uuid.as_str().to_owned();
    let draft = &mut state.draft.draft;
    match step {
        WizardStepDto::Basics => {
            if let Some(name) = patch.name {
                draft.name = name;
            }
            if let Some(purpose) = patch.purpose {
                draft.purpose = purpose;
            }
        }
        WizardStepDto::Delivery => {
            if delivery_has_input(&patch) {
                let target = ensure_target(draft, &uuid);
                if let Some(v) = field_state(patch.delivery_form) {
                    target.form = v;
                }
                if let Some(v) = field_state(patch.delivery_platform) {
                    target.platform = v;
                }
                if let Some(v) = field_state(patch.delivery_language) {
                    target.language = v;
                }
                if let Some(v) = field_state(patch.delivery_framework) {
                    target.framework = v;
                }
                if let Some(b) = patch.delivery_has_ui {
                    target.has_ui = Some(b);
                }
            }
        }
        WizardStepDto::Topology => {
            if let Some(v) = field_state(patch.topology) {
                draft.topology = v;
            }
        }
        WizardStepDto::Requirements => {
            if let Some(intent) = patch.requirement_intent {
                if !intent.trim().is_empty() {
                    draft.requirements = vec![DefinitionRequirement {
                        id: "requirement-1".to_owned(),
                        intent,
                        acceptance: split_list(patch.requirement_acceptance).unwrap_or_default(),
                        state: RequirementState::Confirmed,
                    }];
                }
            }
        }
        WizardStepDto::TechnologyUi => {
            if technology_has_input(&patch) {
                let target = ensure_target(draft, &uuid);
                if let Some(v) = field_state(patch.delivery_host) {
                    target.host = v;
                }
                if let Some(v) = field_state(patch.delivery_host_version) {
                    target.host_version = v;
                }
                if let Some(list) = split_list(patch.delivery_toolchain) {
                    target.toolchain = list;
                }
            }
        }
        WizardStepDto::Preview => {}
    }
    draft.last_saved_step = step.into();
    let validation = match validate_definition(&state.draft.draft) {
        Ok(()) => WizardValidationDto {
            ok: true,
            invalid_field: None,
        },
        Err(DefinitionError::InvalidInput { field }) => WizardValidationDto {
            ok: false,
            invalid_field: Some(field),
        },
        Err(other) => WizardValidationDto {
            ok: false,
            invalid_field: Some(format!("{other:?}")),
        },
    };
    Ok(WizardStepView {
        step,
        validation,
        view: draft_view(&state.draft),
    })
}

/// Prepare the preferences plan for the in-flight session by wrapping the domain
/// [`crate::project_definition::prepare_definition_preferences`]. Stores the
/// prepared plan; no filesystem.
pub fn wizard_prepare_preferences(
    store: &mut WizardSessionStore,
    token: &WizardToken,
    choice: PreferenceChoice<'_>,
) -> Result<WizardPreferencePlanView, WizardBridgeError> {
    let plan = crate::project_definition::prepare_definition_preferences(choice)
        .map_err(|e| WizardBridgeError::InvalidInput {
            field: format!("{e:?}"),
        })?;
    let kind = plan_kind(&plan);
    let preset_id = match &plan {
        PreparedPreferencePlan::Preset { preset_id, .. } => Some(preset_id.clone()),
        _ => None,
    };
    let state = store.get_mut(token)?;
    state.draft.draft.preference_source = match &plan {
        PreparedPreferencePlan::Skip => PreferenceSource::Skip,
        PreparedPreferencePlan::Preset { .. } => PreferenceSource::Preset,
        PreparedPreferencePlan::ImportedCopy { .. } => PreferenceSource::ImportedCopy,
    };
    state.prepared = plan;
    Ok(WizardPreferencePlanView { kind, preset_id })
}

/// Commit the in-flight session to disk: re-check owner authority via
/// `bind_definition`, persist via `save_definition`, map the receipt to a DTO,
/// and clear the token (single-use).
///
/// The session snapshot is cloned up front so a domain rejection leaves the
/// in-flight session intact for a retry; the token is removed only on success.
pub fn wizard_commit(
    fs: &dyn FileSystemPort,
    commit: &dyn FileCommitPort,
    store: &mut WizardSessionStore,
    token: &WizardToken,
) -> Result<WizardCommitReceipt, WizardBridgeError> {
    let state = store.get(token)?.clone();

    // bind_definition re-validates the owner authority context and the
    // location/baseline/preferences shape; it never infers authority from IO.
    let binding = bind_definition(
        fs,
        state.authority.clone(),
        state.location.clone(),
        state.draft.project_uuid.clone(),
        state.baseline.clone(),
        state.prepared.clone(),
        &[],
    )?;

    // Absent baseline → no expected on-disk digest; Present → the baseline digest.
    let expected = match &state.baseline {
        DefinitionBaseline::Present { raw_digest, .. } => Some(raw_digest.as_str().to_owned()),
        DefinitionBaseline::Absent => None,
    };

    let receipt = save_definition(fs, commit, &binding, expected.as_deref(), &state.draft)?;
    let dto = commit_receipt_view(&receipt);

    // Single-use: drop the in-flight session now that it is persisted.
    store.remove(token)?;
    Ok(dto)
}

fn commit_receipt_view(receipt: &DefinitionSaveReceipt) -> WizardCommitReceipt {
    WizardCommitReceipt {
        project_root: receipt.canonical_root.clone(),
        relative_path: receipt.definition.relative_path.clone(),
        persisted_revision: receipt.definition.persisted_revision.0,
        raw_digest: receipt.definition.raw_digest.as_str().to_owned(),
        transaction_id: receipt.definition.transaction_id.clone(),
        preferences_committed: matches!(
            receipt.preferences,
            PreferenceCommitStatus::Committed { .. }
        ),
    }
}

/// Drop the in-flight session for `token`.
pub fn wizard_cancel(
    store: &mut WizardSessionStore,
    token: &WizardToken,
) -> Result<(), WizardBridgeError> {
    store.remove(token).map(|_| ())
}
