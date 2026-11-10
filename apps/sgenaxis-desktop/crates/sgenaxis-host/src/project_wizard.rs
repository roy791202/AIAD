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
    validate_definition, DefinitionDraft, DefinitionError, DefinitionMode, DefinitionRevision,
    ExtensionValue, FieldState, PersistentProjectId, PreferenceSource, ProjectDefinition,
    WizardStep,
};

use crate::project_definition::{
    DefinitionAuthorityContext, DefinitionBaseline, DefinitionBinding, DefinitionLocation,
    PreparedPreferencePlan,
};
use crate::project_preferences::PreferenceChoice;

/// Placeholder identity used while the draft is in-flight. Real persistent-id
/// minting / `open_definition` adoption is GREEN work performed by
/// [`wizard_commit`]; the skeleton never persists this value.
const DRAFT_PLACEHOLDER_UUID: &str = "11111111-1111-4111-8111-111111111111";

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
    sessions: BTreeMap<String, InFlight>,
}

impl WizardSessionStore {
    pub fn new() -> Self {
        Self::default()
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

/// Request DTO: a partial patch of one wizard step's inputs. Only the Basics
/// fields are modeled in the skeleton; later steps are GREEN work.
#[derive(Debug, Clone, Default, Deserialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct WizardDraftPatch {
    pub name: Option<String>,
    pub purpose: Option<String>,
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
    /// SKELETON sentinel: orchestration body not yet implemented (RED).
    NotImplemented { detail: String },
}

impl std::fmt::Display for WizardBridgeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WizardBridgeError::Unauthorized => write!(f, "UNAUTHORIZED"),
            WizardBridgeError::UnknownToken => write!(f, "UNKNOWN_TOKEN"),
            WizardBridgeError::InvalidInput { field } => write!(f, "INVALID_INPUT: {field}"),
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
    }
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
        project_uuid: PersistentProjectId::candidate(DRAFT_PLACEHOLDER_UUID),
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
    if let Some(name) = patch.name {
        state.draft.draft.name = name;
    }
    if let Some(purpose) = patch.purpose {
        state.draft.draft.purpose = purpose;
    }
    state.draft.draft.last_saved_step = step.into();
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

/// Commit the in-flight session to disk: re-check owner authority, `bind_definition`
/// then `save_definition`, map the receipt, and clear the token.
///
/// SKELETON: not implemented. Returns [`WizardBridgeError::NotImplemented`] so the
/// RED integration test observes the sentinel exactly at the commit boundary.
pub fn wizard_commit(
    fs: &dyn FileSystemPort,
    commit: &dyn FileCommitPort,
    store: &mut WizardSessionStore,
    token: &WizardToken,
) -> Result<WizardCommitReceipt, WizardBridgeError> {
    // Touch the inputs so the orchestration signature is exercised and the
    // skeleton stays honest about what GREEN must consume.
    let _ = (fs, commit);
    let _state = store.get(token)?;
    Err(WizardBridgeError::NotImplemented {
        detail: "wizard_commit: bind_definition + save_definition orchestration pending GREEN"
            .into(),
    })
}

/// Drop the in-flight session for `token`.
pub fn wizard_cancel(
    store: &mut WizardSessionStore,
    token: &WizardToken,
) -> Result<(), WizardBridgeError> {
    store.remove(token).map(|_| ())
}
