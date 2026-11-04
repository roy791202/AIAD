//! M01-S2 approved HOST codec and Port-based project-definition persistence.
//! No filesystem or native ownership; all effects must pass the declared Ports.
use crate::project_preferences::PreferenceChoice;
use sgenaxis_ports::{CommitReceipt, CommitStage, FileCommitPort, FileSystemPort};
use sgenaxis_work::project_definition::{
    DefinitionRevision, PersistentProjectId, ProjectDefinition,
};

/// Exact disk bytes, not reserialized content; separate from logical revision.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RawDefinitionDigest(String);

/// S3 authenticates against its own live owner. Nonempty strings/UI checkbox are NOT authorization. S2 has no window permission service.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DefinitionAuthorityContext {
    pub selection_id: String,
    pub session_id: String,
    pub owner_window: String,
}

/// Supplied from serialized DispatchHost owner snapshot, not a new S2 registry. S3 revalidates before installing returned binding.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenDefinitionClaim {
    pub project_uuid: PersistentProjectId,
    pub canonical_root: String,
}

/// Canonicalization/authorization is outer-native responsibility; IO still validates target. UI-provided root is not authority.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefinitionLocation {
    NewProject {
        canonical_parent: String,
        single_name: String,
    },
    ExistingProject {
        canonical_root: String,
    },
    LegacyAdoption {
        canonical_root: String,
        candidate_uuid: PersistentProjectId,
        portable_legacy_keys: Vec<String>,
    },
}

/// Absent requires missing target; never means overwrite approval.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefinitionBaseline {
    Absent,
    Present {
        raw_digest: RawDefinitionDigest,
        revision: DefinitionRevision,
        project_uuid: PersistentProjectId,
    },
}

/// Prepare/validate before any directory creation. Only NewProject may write selected preferences. Captured import source is never a write target; no source path in portable definition.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PreparedPreferencePlan {
    Skip,
    Preset {
        preset_id: String,
        encoded_bytes: Vec<u8>,
        digest: RawDefinitionDigest,
    },
    ImportedCopy {
        captured_source_digest: RawDefinitionDigest,
        encoded_bytes: Vec<u8>,
        digest: RawDefinitionDigest,
    },
}

/// Only normal constructor bind_definition. Existing/adopt require Skip. Immutable caller-owned value; S2 returns next binding proposal, never installs it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DefinitionBinding {
    context: DefinitionAuthorityContext,
    location: DefinitionLocation,
    project_uuid: PersistentProjectId,
    baseline: DefinitionBaseline,
    preferences: PreparedPreferencePlan,
}

/// Legacy iff definition truly NotFound, no auto ID/write. Saved data does not authorize generation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefinitionOpenView {
    Saved {
        definition: ProjectDefinition,
        raw_digest: RawDefinitionDigest,
        canonical_root: String,
        relative_path: String,
    },
    Legacy {
        canonical_root: String,
        portable_legacy_keys: Vec<String>,
        migration_required: bool,
    },
}

/// Only after verified IO receipt; captured revision, not a later edited snapshot.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DefinitionCommitProof {
    pub project_uuid: PersistentProjectId,
    pub persisted_revision: DefinitionRevision,
    pub relative_path: String,
    pub raw_digest: RawDefinitionDigest,
    pub transaction_id: String,
}

/// Only successful exclusive create/receipt. IO scratch/recovery paths are not HOST cleanup ownership.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OwnedCreationArtifact {
    pub relative_path: String,
    pub kind: CreationArtifactKind,
    pub state: CreationArtifactState,
    pub raw_digest: Option<RawDefinitionDigest>,
    pub transaction_id: Option<String>,
}

/// No recursive rollback/cleanup. Created metadata in old root is NOT a newly created project root.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CreationProgress {
    pub canonical_root: String,
    pub root_created: bool,
    pub phase: CreationPhase,
    pub owned_artifacts: Vec<OwnedCreationArtifact>,
    pub definition_commit: Option<DefinitionCommitProof>,
}

/// Successful receipt has no Failed state. Selected preference failure uses PartialProjectCreated, retaining definition proof.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PreferenceCommitStatus {
    Skipped,
    Committed {
        relative_path: String,
        raw_digest: RawDefinitionDigest,
        transaction_id: String,
    },
}

/// Ok iff all requested S2 steps succeed. No settings/registry/generation mutation. Postcommit projection cannot revoke persistence proof.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DefinitionSaveReceipt {
    pub definition: DefinitionCommitProof,
    pub canonical_root: String,
    pub creation: CreationProgress,
    pub preferences: PreferenceCommitStatus,
    pub next_binding: DefinitionBinding,
}

/// Keep original stage/reason. Read error never implies a verified rollback.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct StoreFault {
    pub stage: CommitStage,
    pub path: String,
    pub reason: String,
}

/// Copy exactly from CommitError::RecoveryRequired; no invented diagnostic paths or version-presence claims.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryInfo {
    pub target_path: String,
    pub journal_path: String,
    pub old_version_path: Option<String>,
    pub new_version_path: Option<String>,
    pub reason: String,
}

/// No IO; syntax/duplicate/resource checks precede schema dispatch.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CodecIssue {
    InputTooLarge {
        actual_bytes: usize,
        limit_bytes: usize,
    },
    InvalidUtf8,
    BomNotAllowed,
    InvalidJson {
        byte_offset: Option<usize>,
    },
    DuplicateKey {
        pointer: String,
    },
    UnknownField {
        pointer: String,
    },
    MissingField {
        pointer: String,
    },
    InvalidField {
        pointer: String,
        code: CodecFieldCode,
    },
    ResourceLimit {
        pointer: String,
        resource: CodecResource,
    },
    OutputTooLarge {
        actual_bytes: usize,
        limit_bytes: usize,
    },
}

/// RecoveryRequired is deliberately not nested; it has higher-priority top-level classification.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreationFailureCause {
    ExistingTarget {
        path: String,
    },
    Conflict {
        expected: Option<RawDefinitionDigest>,
        observed: Option<RawDefinitionDigest>,
    },
    Busy {
        path: String,
    },
    Storage {
        fault: StoreFault,
    },
    InvalidLocation {
        path: String,
        reason: String,
    },
}

/// Local typed HOST data, not new IPC schema. S3 rejects UnauthorizedCaller before S2. No implicit retry/remap/cleanup.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefinitionStoreError {
    NotBound,
    InvalidInput {
        field: String,
        code: DefinitionInputCode,
    },
    Codec {
        issue: CodecIssue,
    },
    UnsupportedSchema {
        schema: String,
        version: String,
    },
    ExistingTarget {
        path: String,
    },
    IdentityConflict {
        expected_uuid: Option<PersistentProjectId>,
        observed_uuid: PersistentProjectId,
        requested_root: String,
        other_root: Option<String>,
        reason: IdentityConflictReason,
    },
    RevisionConflict {
        expected_digest: Option<RawDefinitionDigest>,
        observed_digest: Option<RawDefinitionDigest>,
        expected_revision: Option<DefinitionRevision>,
        observed_revision: Option<DefinitionRevision>,
    },
    Busy {
        path: String,
    },
    StorageFailure {
        fault: StoreFault,
        retained_artifacts: Vec<OwnedCreationArtifact>,
    },
    PartialProjectCreated {
        progress: CreationProgress,
        cause: CreationFailureCause,
    },
    RecoveryRequired {
        diagnostics: RecoveryInfo,
        progress: Option<CreationProgress>,
    },
    InvalidLocation {
        path: String,
        reason: String,
        retained_artifacts: Vec<OwnedCreationArtifact>,
    },
    CommitEvidenceMismatch {
        requested_target: String,
        reported_receipt: CommitReceipt,
        progress: CreationProgress,
    },
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreationArtifactKind {
    RootDirectory,
    MetadataDirectory,
    DefinitionFile,
    PreferencesFile,
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreationArtifactState {
    CreatedDirectory,
    CommittedFile,
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CreationPhase {
    CreateRoot,
    CreateMetadata,
    CommitDefinition,
    CommitPreferences,
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum IdentityConflictReason {
    BoundUuidMismatch,
    DuplicateOpenRoot,
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefinitionInputCode {
    BindingMismatch,
    ExpectedDigestMismatch,
    PreferenceModeMismatch,
    DomainInvalid,
    PreferenceInvalid,
    InvalidLocation,
    RevisionNotAdvanced,
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CodecFieldCode {
    WrongType,
    InvalidEnum,
    InvalidUuid,
    InvalidRevision,
    OutOfRange,
    InconsistentFieldState,
    InvalidNumberToken,
    InvalidPortableAlias,
    InvalidDigest,
}

/// Exact discriminants; no serialization/IPC contract is added in S2.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CodecResource {
    Depth,
    Nodes,
    StringBytes,
    NumberBytes,
}

impl RawDefinitionDigest {
    pub fn try_from_text(raw: &str) -> Option<Self> {
        valid_digest(raw).then(|| Self(raw.to_owned()))
    }
    pub fn as_str(&self) -> &str {
        &self.0
    }
}
impl DefinitionBinding {
    pub fn project_uuid(&self) -> &PersistentProjectId {
        &self.project_uuid
    }
    pub fn baseline(&self) -> &DefinitionBaseline {
        &self.baseline
    }
    pub fn location(&self) -> &DefinitionLocation {
        &self.location
    }
}

pub fn encode_definition(definition: &ProjectDefinition) -> Result<Vec<u8>, DefinitionStoreError> {
    encode_impl(definition)
}

pub fn decode_definition(bytes: &[u8]) -> Result<ProjectDefinition, DefinitionStoreError> {
    decode_impl(bytes)
}

// Private codec machinery. Numbers retain their token; no floating-point or
// serde_json::Value numeric intermediate enters the domain projection.
use sgenaxis_work::project_definition::*;
use std::collections::BTreeMap;
const BYTE_LIMIT: usize = 16_777_216;
const STRING_LIMIT: usize = 1_048_576;
type StoreResult<T> = Result<T, DefinitionStoreError>;
#[derive(Debug, Clone, PartialEq, Eq)]
enum Json {
    Null,
    Bool(bool),
    Number(String),
    String(String),
    Array(Vec<Json>),
    Object(Vec<(String, Json)>),
}
fn codec(issue: CodecIssue) -> DefinitionStoreError {
    DefinitionStoreError::Codec { issue }
}
fn field(pointer: &str, code: CodecFieldCode) -> DefinitionStoreError {
    codec(CodecIssue::InvalidField {
        pointer: pointer.into(),
        code,
    })
}
fn input(field: &str, code: DefinitionInputCode) -> DefinitionStoreError {
    DefinitionStoreError::InvalidInput {
        field: field.into(),
        code,
    }
}
fn pointer(parent: &str, key: &str) -> String {
    format!("{}/{}", parent, key.replace('~', "~0").replace('/', "~1"))
}
fn limit(pointer: &str, resource: CodecResource) -> DefinitionStoreError {
    codec(CodecIssue::ResourceLimit {
        pointer: pointer.into(),
        resource,
    })
}
struct Parser<'a> {
    s: &'a str,
    pos: usize,
    nodes: usize,
}
impl Parser<'_> {
    fn syntax(&self) -> DefinitionStoreError {
        codec(CodecIssue::InvalidJson {
            byte_offset: Some(self.pos),
        })
    }
    fn ws(&mut self) {
        while self
            .s
            .as_bytes()
            .get(self.pos)
            .is_some_and(|c| matches!(c, b' ' | b'\t' | b'\r' | b'\n'))
        {
            self.pos += 1
        }
    }
    fn take(&mut self, c: u8) -> bool {
        self.ws();
        if self.s.as_bytes().get(self.pos) == Some(&c) {
            self.pos += 1;
            true
        } else {
            false
        }
    }
    fn string(&mut self, p: &str) -> StoreResult<String> {
        self.ws();
        let start = self.pos;
        if self.s.as_bytes().get(self.pos) != Some(&b'"') {
            return Err(self.syntax());
        }
        self.pos += 1;
        let mut escaped = false;
        while let Some(c) = self.s.as_bytes().get(self.pos).copied() {
            self.pos += 1;
            if !escaped && c == b'"' {
                let value: String =
                    serde_json::from_str(&self.s[start..self.pos]).map_err(|_| self.syntax())?;
                if value.len() > STRING_LIMIT {
                    return Err(limit(p, CodecResource::StringBytes));
                }
                return Ok(value);
            }
            if escaped {
                escaped = false
            } else if c == b'\\' {
                escaped = true
            }
        }
        Err(self.syntax())
    }
    fn value(&mut self, p: &str, depth: usize) -> StoreResult<Json> {
        if depth > 64 {
            return Err(limit(p, CodecResource::Depth));
        }
        self.nodes += 1;
        if self.nodes > 100000 {
            return Err(limit(p, CodecResource::Nodes));
        }
        self.ws();
        let c = *self
            .s
            .as_bytes()
            .get(self.pos)
            .ok_or_else(|| self.syntax())?;
        match c {
            b'"' => Ok(Json::String(self.string(p)?)),
            b'{' => {
                self.pos += 1;
                let mut values = Vec::new();
                let mut keys = std::collections::BTreeSet::new();
                if self.take(b'}') {
                    return Ok(Json::Object(values));
                }
                loop {
                    let k = self.string(p)?;
                    let path = pointer(p, &k);
                    if !keys.insert(k.clone()) {
                        return Err(codec(CodecIssue::DuplicateKey { pointer: path }));
                    }
                    if !self.take(b':') {
                        return Err(self.syntax());
                    }
                    let value = self.value(&path, depth + 1)?;
                    values.push((k, value));
                    if self.take(b'}') {
                        break;
                    }
                    if !self.take(b',') {
                        return Err(self.syntax());
                    }
                }
                Ok(Json::Object(values))
            }
            b'[' => {
                self.pos += 1;
                let mut a = Vec::new();
                if self.take(b']') {
                    return Ok(Json::Array(a));
                }
                loop {
                    a.push(self.value(&pointer(p, &a.len().to_string()), depth + 1)?);
                    if self.take(b']') {
                        break;
                    }
                    if !self.take(b',') {
                        return Err(self.syntax());
                    }
                }
                Ok(Json::Array(a))
            }
            b'n' | b't' | b'f' => {
                let (token, value) = match c {
                    b'n' => ("null", Json::Null),
                    b't' => ("true", Json::Bool(true)),
                    _ => ("false", Json::Bool(false)),
                };
                if !self.s[self.pos..].starts_with(token) {
                    return Err(self.syntax());
                }
                self.pos += token.len();
                Ok(value)
            }
            b'-' | b'0'..=b'9' => {
                let start = self.pos;
                while self
                    .s
                    .as_bytes()
                    .get(self.pos)
                    .is_some_and(|c| matches!(c, b'-' | b'+' | b'.' | b'e' | b'E' | b'0'..=b'9'))
                {
                    self.pos += 1
                }
                let raw = &self.s[start..self.pos];
                if !number_syntax(raw) {
                    return Err(self.syntax());
                }
                if raw.len() > 4096 {
                    return Err(limit(p, CodecResource::NumberBytes));
                }
                Ok(Json::Number(raw.into()))
            }
            _ => Err(self.syntax()),
        }
    }
}
fn number_syntax(s: &str) -> bool {
    // RawValue validates JSON grammar without coercing the token to a float.
    serde_json::from_str::<Box<serde_json::value::RawValue>>(s)
        .is_ok_and(|v| v.get() == s && matches!(s.as_bytes().first(), Some(b'-' | b'0'..=b'9')))
}
fn parse(bytes: &[u8]) -> StoreResult<Json> {
    if bytes.len() > BYTE_LIMIT {
        return Err(codec(CodecIssue::InputTooLarge {
            actual_bytes: bytes.len(),
            limit_bytes: BYTE_LIMIT,
        }));
    }
    let s = std::str::from_utf8(bytes).map_err(|_| codec(CodecIssue::InvalidUtf8))?;
    if s.starts_with('\u{feff}') {
        return Err(codec(CodecIssue::BomNotAllowed));
    }
    let mut p = Parser {
        s,
        pos: 0,
        nodes: 0,
    };
    let v = p.value("", 0)?;
    p.ws();
    if p.pos != s.len() {
        return Err(p.syntax());
    }
    Ok(v)
}
fn obj<'a>(v: &'a Json, p: &str, keys: &[&str]) -> StoreResult<BTreeMap<&'a str, &'a Json>> {
    let Json::Object(values) = v else {
        return Err(field(p, CodecFieldCode::WrongType));
    };
    for (k, _) in values {
        if !keys.contains(&k.as_str()) {
            return Err(codec(CodecIssue::UnknownField {
                pointer: pointer(p, k),
            }));
        }
    }
    for k in keys {
        if !values.iter().any(|(name, _)| name == k) {
            return Err(codec(CodecIssue::MissingField {
                pointer: pointer(p, k),
            }));
        }
    }
    Ok(values.iter().map(|(k, v)| (k.as_str(), v)).collect())
}
fn text(v: &Json, p: &str) -> StoreResult<String> {
    match v {
        Json::String(s) => Ok(s.clone()),
        _ => Err(field(p, CodecFieldCode::WrongType)),
    }
}
fn array<'a>(v: &'a Json, p: &str) -> StoreResult<&'a [Json]> {
    match v {
        Json::Array(a) => Ok(a),
        _ => Err(field(p, CodecFieldCode::WrongType)),
    }
}
fn strings(v: &Json, p: &str) -> StoreResult<Vec<String>> {
    array(v, p)?
        .iter()
        .enumerate()
        .map(|(i, v)| text(v, &pointer(p, &i.to_string())))
        .collect()
}
fn enum_text(v: &Json, p: &str, choices: &[&str]) -> StoreResult<String> {
    let s = text(v, p)?;
    if !choices.contains(&s.as_str()) {
        return Err(field(p, CodecFieldCode::InvalidEnum));
    }
    Ok(s)
}
fn uuid(s: &str) -> bool {
    let b = s.as_bytes();
    b.len() == 36
        && b[14] == b'4'
        && matches!(b[19], b'8' | b'9' | b'a' | b'b')
        && b.iter().enumerate().all(|(i, c)| {
            if matches!(i, 8 | 13 | 18 | 23) {
                *c == b'-'
            } else {
                c.is_ascii_digit() || (b'a'..=b'f').contains(c)
            }
        })
}
fn valid_digest(s: &str) -> bool {
    s.strip_prefix("sha256:").is_some_and(|s| {
        s.len() == 64
            && s.bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    })
}
fn portable(s: &str) -> bool {
    !s.is_empty()
        && !s.contains(['/', '\\', ':'])
        && !matches!(s, "." | "..")
        && !s.chars().any(char::is_control)
}
fn state(v: &Json, p: &str) -> StoreResult<FieldState<String>> {
    let o = obj(v, p, &["state", "value"])?;
    let tag = enum_text(
        o["state"],
        &pointer(p, "state"),
        &["unresolved", "tentative", "confirmed"],
    )?;
    match (tag.as_str(), o["value"]) {
        ("unresolved", Json::Null) => Ok(FieldState::Unresolved),
        ("tentative", Json::String(s)) => Ok(FieldState::Tentative(s.clone())),
        ("confirmed", Json::String(s)) => Ok(FieldState::Confirmed(s.clone())),
        _ => Err(field(p, CodecFieldCode::InconsistentFieldState)),
    }
}
fn extension_from(v: &Json) -> ExtensionValue {
    match v {
        Json::Null => ExtensionValue::Null,
        Json::Bool(b) => ExtensionValue::Bool(*b),
        Json::Number(n) => ExtensionValue::Number(n.clone()),
        Json::String(s) => ExtensionValue::String(s.clone()),
        Json::Array(a) => ExtensionValue::Array(a.iter().map(extension_from).collect()),
        Json::Object(o) => ExtensionValue::Object(
            o.iter()
                .map(|(k, v)| (k.clone(), extension_from(v)))
                .collect(),
        ),
    }
}
const ROOT_KEYS: &[&str] = &[
    "schema",
    "schemaVersion",
    "projectUuid",
    "definitionRevision",
    "name",
    "purpose",
    "mode",
    "lastSavedStep",
    "deliveryTargets",
    "topology",
    "requirements",
    "preferenceSource",
    "template",
    "openDecisions",
    "approvalRefs",
    "legacyRootKeys",
    "extensions",
];
fn decode_impl(bytes: &[u8]) -> StoreResult<ProjectDefinition> {
    decode_tree(&parse(bytes)?)
}
fn decode_tree(tree: &Json) -> StoreResult<ProjectDefinition> {
    let Json::Object(all) = tree else {
        return Err(field("", CodecFieldCode::WrongType));
    };
    let get = |key: &str| {
        all.iter()
            .find(|(k, _)| k == key)
            .map(|(_, v)| v)
            .ok_or_else(|| {
                codec(CodecIssue::MissingField {
                    pointer: pointer("", key),
                })
            })
    };
    let schema = text(get("schema")?, "/schema")?;
    let version = get("schemaVersion")?;
    let Json::Number(version) = version else {
        return Err(field("/schemaVersion", CodecFieldCode::WrongType));
    };
    if schema != PROJECT_DEFINITION_SCHEMA || version != "1" {
        return Err(DefinitionStoreError::UnsupportedSchema {
            schema,
            version: version.clone(),
        });
    }
    let o = obj(tree, "", ROOT_KEYS)?;
    let id = text(o["projectUuid"], "/projectUuid")?;
    if !uuid(&id) {
        return Err(field("/projectUuid", CodecFieldCode::InvalidUuid));
    }
    let revision = match o["definitionRevision"] {
        Json::String(s)
            if !s.is_empty()
                && (s == "0" || !s.starts_with('0'))
                && s.bytes().all(|c| c.is_ascii_digit()) =>
        {
            s.parse::<u64>().ok()
        }
        _ => None,
    }
    .ok_or_else(|| field("/definitionRevision", CodecFieldCode::InvalidRevision))?;
    let name = text(o["name"], "/name")?;
    if name.chars().count() > 120 {
        return Err(field("/name", CodecFieldCode::OutOfRange));
    }
    let mode = match enum_text(o["mode"], "/mode", &["draft", "defined"])?.as_str() {
        "draft" => DefinitionMode::Draft,
        _ => DefinitionMode::Defined,
    };
    let step = match enum_text(
        o["lastSavedStep"],
        "/lastSavedStep",
        &[
            "basics",
            "delivery",
            "topology",
            "requirements",
            "technology_ui",
            "preview",
        ],
    )?
    .as_str()
    {
        "basics" => WizardStep::Basics,
        "delivery" => WizardStep::Delivery,
        "topology" => WizardStep::Topology,
        "requirements" => WizardStep::Requirements,
        "technology_ui" => WizardStep::TechnologyUi,
        _ => WizardStep::Preview,
    };
    let mut targets = Vec::new();
    for (i, v) in array(o["deliveryTargets"], "/deliveryTargets")?
        .iter()
        .enumerate()
    {
        let p = format!("/deliveryTargets/{i}");
        let t = obj(
            v,
            &p,
            &[
                "id",
                "form",
                "platform",
                "host",
                "hostVersion",
                "language",
                "framework",
                "toolchain",
                "hasUi",
            ],
        )?;
        let id = text(t["id"], &pointer(&p, "id"))?;
        if !uuid(&id) {
            return Err(field(&pointer(&p, "id"), CodecFieldCode::InvalidUuid));
        }
        targets.push(DeliveryTarget {
            id,
            form: state(t["form"], &pointer(&p, "form"))?,
            platform: state(t["platform"], &pointer(&p, "platform"))?,
            host: state(t["host"], &pointer(&p, "host"))?,
            host_version: state(t["hostVersion"], &pointer(&p, "hostVersion"))?,
            language: state(t["language"], &pointer(&p, "language"))?,
            framework: state(t["framework"], &pointer(&p, "framework"))?,
            toolchain: strings(t["toolchain"], &pointer(&p, "toolchain"))?,
            has_ui: match t["hasUi"] {
                Json::Null => None,
                Json::Bool(b) => Some(*b),
                _ => return Err(field(&pointer(&p, "hasUi"), CodecFieldCode::WrongType)),
            },
        })
    }
    let mut requirements = Vec::new();
    for (i, v) in array(o["requirements"], "/requirements")?
        .iter()
        .enumerate()
    {
        let p = format!("/requirements/{i}");
        let r = obj(v, &p, &["id", "intent", "acceptance", "state"])?;
        requirements.push(DefinitionRequirement {
            id: text(r["id"], &pointer(&p, "id"))?,
            intent: text(r["intent"], &pointer(&p, "intent"))?,
            acceptance: strings(r["acceptance"], &pointer(&p, "acceptance"))?,
            state: match enum_text(
                r["state"],
                &pointer(&p, "state"),
                &["unresolved", "tentative", "confirmed"],
            )?
            .as_str()
            {
                "unresolved" => RequirementState::Unresolved,
                "tentative" => RequirementState::Tentative,
                _ => RequirementState::Confirmed,
            },
        })
    }
    let template = if o["template"] == &Json::Null {
        None
    } else {
        let t = obj(
            o["template"],
            "/template",
            &["id", "version", "sourceDigest"],
        )?;
        let id = text(t["id"], "/template/id")?;
        let version = text(t["version"], "/template/version")?;
        if id.is_empty() {
            return Err(field("/template/id", CodecFieldCode::OutOfRange));
        }
        if version.is_empty() {
            return Err(field("/template/version", CodecFieldCode::OutOfRange));
        }
        let source_digest = text(t["sourceDigest"], "/template/sourceDigest")?;
        if !valid_digest(&source_digest) {
            return Err(field(
                "/template/sourceDigest",
                CodecFieldCode::InvalidDigest,
            ));
        }
        Some(TemplateReference {
            id,
            version,
            source_digest,
        })
    };
    let legacy = strings(o["legacyRootKeys"], "/legacyRootKeys")?;
    for (i, s) in legacy.iter().enumerate() {
        if !portable(s) {
            return Err(field(
                &format!("/legacyRootKeys/{i}"),
                CodecFieldCode::InvalidPortableAlias,
            ));
        }
    }
    let extensions = match extension_from(o["extensions"]) {
        ExtensionValue::Object(o) => o,
        _ => return Err(field("/extensions", CodecFieldCode::WrongType)),
    };
    let d = ProjectDefinition {
        project_uuid: PersistentProjectId::candidate(id),
        definition_revision: DefinitionRevision(revision),
        draft: DefinitionDraft {
            name,
            purpose: text(o["purpose"], "/purpose")?,
            last_saved_step: step,
            delivery_targets: targets,
            topology: state(o["topology"], "/topology")?,
            requirements,
            preference_source: match enum_text(
                o["preferenceSource"],
                "/preferenceSource",
                &["skip", "preset", "imported-copy"],
            )?
            .as_str()
            {
                "skip" => PreferenceSource::Skip,
                "preset" => PreferenceSource::Preset,
                _ => PreferenceSource::ImportedCopy,
            },
            template,
            open_decisions: strings(o["openDecisions"], "/openDecisions")?,
            extensions,
        },
        mode,
        approval_refs: strings(o["approvalRefs"], "/approvalRefs")?,
        legacy_root_keys: legacy,
    };
    validate_definition(&d.draft).map_err(|e| match e {
        DefinitionError::InvalidInput { field } => {
            input(&field, DefinitionInputCode::DomainInvalid)
        }
        _ => input("definition", DefinitionInputCode::DomainInvalid),
    })?;
    Ok(d)
}
fn js(s: &str) -> Json {
    Json::String(s.into())
}
fn jo(pairs: Vec<(&str, Json)>) -> Json {
    Json::Object(pairs.into_iter().map(|(k, v)| (k.into(), v)).collect())
}
fn jstrings(v: &[String]) -> Json {
    Json::Array(v.iter().map(|s| js(s)).collect())
}
fn state_to(v: &FieldState<String>) -> Json {
    match v {
        FieldState::Unresolved => jo(vec![("state", js("unresolved")), ("value", Json::Null)]),
        FieldState::Tentative(s) => jo(vec![("state", js("tentative")), ("value", js(s))]),
        FieldState::Confirmed(s) => jo(vec![("state", js("confirmed")), ("value", js(s))]),
    }
}
fn extension_to(v: &ExtensionValue, p: &str, depth: usize, nodes: &mut usize) -> StoreResult<Json> {
    // Guard before recursion: domain candidates can exceed wire limits too.
    if depth > 64 {
        return Err(limit(p, CodecResource::Depth));
    }
    *nodes += 1;
    if *nodes > 100000 {
        return Err(limit(p, CodecResource::Nodes));
    }
    Ok(match v {
        ExtensionValue::Null => Json::Null,
        ExtensionValue::Bool(b) => Json::Bool(*b),
        ExtensionValue::String(s) => {
            if s.len() > STRING_LIMIT {
                return Err(limit(p, CodecResource::StringBytes));
            }
            js(s)
        }
        ExtensionValue::Number(n) => {
            if !number_syntax(n) {
                return Err(field(p, CodecFieldCode::InvalidNumberToken));
            }
            if n.len() > 4096 {
                return Err(limit(p, CodecResource::NumberBytes));
            }
            Json::Number(n.clone())
        }
        ExtensionValue::Array(a) => Json::Array(
            a.iter()
                .enumerate()
                .map(|(i, v)| extension_to(v, &pointer(p, &i.to_string()), depth + 1, nodes))
                .collect::<StoreResult<_>>()?,
        ),
        ExtensionValue::Object(o) => {
            let mut values = Vec::new();
            for (k, v) in o {
                if k.len() > STRING_LIMIT {
                    return Err(limit(p, CodecResource::StringBytes));
                }
                values.push((
                    k.clone(),
                    extension_to(v, &pointer(p, k), depth + 1, nodes)?,
                ))
            }
            Json::Object(values)
        }
    })
}
fn encode_impl(d: &ProjectDefinition) -> StoreResult<Vec<u8>> {
    if !uuid(d.project_uuid.as_str()) {
        return Err(field("/projectUuid", CodecFieldCode::InvalidUuid));
    }
    validate_definition(&d.draft).map_err(|e| match e {
        DefinitionError::InvalidInput { field } => {
            input(&field, DefinitionInputCode::DomainInvalid)
        }
        _ => input("definition", DefinitionInputCode::DomainInvalid),
    })?;
    // Do not recursively clone an untrusted domain extension before its depth
    // guard. Traverse borrowed values and create bounded output nodes instead.
    let mut n = 1;
    let mut values = Vec::new();
    for (key, value) in &d.draft.extensions {
        if key.len() > STRING_LIMIT {
            return Err(limit("/extensions", CodecResource::StringBytes));
        }
        values.push((
            key.clone(),
            extension_to(value, &pointer("/extensions", key), 2, &mut n)?,
        ));
    }
    let extensions = Json::Object(values);
    let targets = d
        .draft
        .delivery_targets
        .iter()
        .map(|t| {
            jo(vec![
                ("id", js(&t.id)),
                ("form", state_to(&t.form)),
                ("platform", state_to(&t.platform)),
                ("host", state_to(&t.host)),
                ("hostVersion", state_to(&t.host_version)),
                ("language", state_to(&t.language)),
                ("framework", state_to(&t.framework)),
                ("toolchain", jstrings(&t.toolchain)),
                ("hasUi", t.has_ui.map(Json::Bool).unwrap_or(Json::Null)),
            ])
        })
        .collect();
    let requirements = d
        .draft
        .requirements
        .iter()
        .map(|r| {
            jo(vec![
                ("id", js(&r.id)),
                ("intent", js(&r.intent)),
                ("acceptance", jstrings(&r.acceptance)),
                (
                    "state",
                    js(match r.state {
                        RequirementState::Unresolved => "unresolved",
                        RequirementState::Tentative => "tentative",
                        RequirementState::Confirmed => "confirmed",
                    }),
                ),
            ])
        })
        .collect();
    let tree = jo(vec![
        ("schema", js(PROJECT_DEFINITION_SCHEMA)),
        ("schemaVersion", Json::Number("1".into())),
        ("projectUuid", js(d.project_uuid.as_str())),
        (
            "definitionRevision",
            js(&d.definition_revision.0.to_string()),
        ),
        ("name", js(&d.draft.name)),
        ("purpose", js(&d.draft.purpose)),
        (
            "mode",
            js(match d.mode {
                DefinitionMode::Draft => "draft",
                DefinitionMode::Defined => "defined",
            }),
        ),
        (
            "lastSavedStep",
            js(match d.draft.last_saved_step {
                WizardStep::Basics => "basics",
                WizardStep::Delivery => "delivery",
                WizardStep::Topology => "topology",
                WizardStep::Requirements => "requirements",
                WizardStep::TechnologyUi => "technology_ui",
                WizardStep::Preview => "preview",
            }),
        ),
        ("deliveryTargets", Json::Array(targets)),
        ("topology", state_to(&d.draft.topology)),
        ("requirements", Json::Array(requirements)),
        (
            "preferenceSource",
            js(match d.draft.preference_source {
                PreferenceSource::Skip => "skip",
                PreferenceSource::Preset => "preset",
                PreferenceSource::ImportedCopy => "imported-copy",
            }),
        ),
        (
            "template",
            d.draft
                .template
                .as_ref()
                .map(|t| {
                    jo(vec![
                        ("id", js(&t.id)),
                        ("version", js(&t.version)),
                        ("sourceDigest", js(&t.source_digest)),
                    ])
                })
                .unwrap_or(Json::Null),
        ),
        ("openDecisions", jstrings(&d.draft.open_decisions)),
        ("approvalRefs", jstrings(&d.approval_refs)),
        ("legacyRootKeys", jstrings(&d.legacy_root_keys)),
        ("extensions", extensions),
    ]);
    decode_tree(&tree)?;
    let mut nodes = 0;
    guard_tree(&tree, "", 0, &mut nodes)?;
    let mut output = String::new();
    pretty(&tree, 0, &mut output);
    output.push('\n');
    if output.len() > BYTE_LIMIT {
        return Err(codec(CodecIssue::OutputTooLarge {
            actual_bytes: output.len(),
            limit_bytes: BYTE_LIMIT,
        }));
    }
    Ok(output.into_bytes())
}
fn guard_tree(v: &Json, p: &str, depth: usize, nodes: &mut usize) -> StoreResult<()> {
    if depth > 64 {
        return Err(limit(p, CodecResource::Depth));
    }
    *nodes += 1;
    if *nodes > 100000 {
        return Err(limit(p, CodecResource::Nodes));
    }
    match v {
        Json::String(s) if s.len() > STRING_LIMIT => {
            return Err(limit(p, CodecResource::StringBytes))
        }
        Json::Number(n) if n.len() > 4096 => return Err(limit(p, CodecResource::NumberBytes)),
        Json::Array(a) => {
            for (i, v) in a.iter().enumerate() {
                guard_tree(v, &pointer(p, &i.to_string()), depth + 1, nodes)?
            }
        }
        Json::Object(o) => {
            for (k, v) in o {
                if k.len() > STRING_LIMIT {
                    return Err(limit(p, CodecResource::StringBytes));
                }
                guard_tree(v, &pointer(p, k), depth + 1, nodes)?
            }
        }
        _ => {}
    }
    Ok(())
}
fn pretty(v: &Json, depth: usize, out: &mut String) {
    match v {
        Json::Null => out.push_str("null"),
        Json::Bool(b) => out.push_str(if *b { "true" } else { "false" }),
        Json::Number(n) => out.push_str(n),
        Json::String(s) => {
            out.push_str(&serde_json::to_string(s).expect("string escaping cannot fail"))
        }
        Json::Array(a) => {
            out.push('[');
            for (i, v) in a.iter().enumerate() {
                if i > 0 {
                    out.push(',')
                }
                out.push('\n');
                out.push_str(&"  ".repeat(depth + 1));
                pretty(v, depth + 1, out)
            }
            if !a.is_empty() {
                out.push('\n');
                out.push_str(&"  ".repeat(depth))
            }
            out.push(']')
        }
        Json::Object(o) => {
            out.push('{');
            for (i, (k, v)) in o.iter().enumerate() {
                if i > 0 {
                    out.push(',')
                }
                out.push('\n');
                out.push_str(&"  ".repeat(depth + 1));
                out.push_str(&serde_json::to_string(k).expect("string key"));
                out.push_str(": ");
                pretty(v, depth + 1, out)
            }
            if !o.is_empty() {
                out.push('\n');
                out.push_str(&"  ".repeat(depth))
            }
            out.push('}')
        }
    }
}

pub fn open_definition(
    fs: &dyn FileSystemPort,
    context: &DefinitionAuthorityContext,
    location: &DefinitionLocation,
    expected_uuid: Option<&PersistentProjectId>,
    open_claims: &[OpenDefinitionClaim],
) -> Result<DefinitionOpenView, DefinitionStoreError> {
    open_impl(fs, context, location, expected_uuid, open_claims)
}

pub fn prepare_definition_preferences(
    choice: PreferenceChoice<'_>,
) -> Result<PreparedPreferencePlan, DefinitionStoreError> {
    use sgenaxis_spec::project_preferences::{parse_project_preferences, preset};
    let (preferences, id, captured) = match choice {
        PreferenceChoice::Skip => return Ok(PreparedPreferencePlan::Skip),
        PreferenceChoice::Preset(id) => (
            preset(id)
                .map_err(|_| input("preferences.preset", DefinitionInputCode::PreferenceInvalid))?,
            Some(id.to_owned()),
            None,
        ),
        PreferenceChoice::Imported(bytes) => (
            parse_project_preferences(bytes)
                .map_err(|_| input("preferences.import", DefinitionInputCode::PreferenceInvalid))?,
            None,
            Some(raw_hash(bytes)),
        ),
    };
    let bytes = serde_json::to_vec_pretty(&preferences)
        .map_err(|_| input("preferences", DefinitionInputCode::PreferenceInvalid))?;
    let digest = raw_hash(&bytes);
    Ok(match id {
        Some(preset_id) => PreparedPreferencePlan::Preset {
            preset_id,
            encoded_bytes: bytes,
            digest,
        },
        None => PreparedPreferencePlan::ImportedCopy {
            captured_source_digest: captured.expect("import branch"),
            encoded_bytes: bytes,
            digest,
        },
    })
}

pub fn bind_definition(
    fs: &dyn FileSystemPort,
    context: DefinitionAuthorityContext,
    location: DefinitionLocation,
    project_uuid: PersistentProjectId,
    baseline: DefinitionBaseline,
    preferences: PreparedPreferencePlan,
    open_claims: &[OpenDefinitionClaim],
) -> Result<DefinitionBinding, DefinitionStoreError> {
    let _ = fs; // Bound native authority belongs to S3; no authority inferred from IO.
    check_context(&context)?;
    if !uuid(project_uuid.as_str()) {
        return Err(input("projectUuid", DefinitionInputCode::DomainInvalid));
    }
    let root = location_root(&location)?;
    check_claims(&project_uuid, &root, open_claims, None)?;
    match (&location, &baseline, &preferences) {
        (DefinitionLocation::NewProject { .. }, DefinitionBaseline::Absent, _) => {}
        (
            DefinitionLocation::ExistingProject { .. },
            DefinitionBaseline::Present {
                project_uuid: old, ..
            },
            PreparedPreferencePlan::Skip,
        ) if old == &project_uuid => {}
        (
            DefinitionLocation::LegacyAdoption {
                candidate_uuid,
                portable_legacy_keys,
                ..
            },
            DefinitionBaseline::Absent,
            PreparedPreferencePlan::Skip,
        ) if candidate_uuid == &project_uuid
            && portable_legacy_keys.iter().all(|s| portable(s)) => {}
        _ => return Err(input("binding", DefinitionInputCode::BindingMismatch)),
    }
    check_prepared(&preferences)?;
    Ok(DefinitionBinding {
        context,
        location,
        project_uuid,
        baseline,
        preferences,
    })
}

pub fn save_definition(
    fs: &dyn FileSystemPort,
    commit: &dyn FileCommitPort,
    binding: &DefinitionBinding,
    expected_disk_digest: Option<&str>,
    definition: &ProjectDefinition,
) -> Result<DefinitionSaveReceipt, DefinitionStoreError> {
    save_impl(fs, commit, binding, expected_disk_digest, definition)
}

fn raw_hash(bytes: &[u8]) -> RawDefinitionDigest {
    RawDefinitionDigest(format!(
        "sha256:{}",
        sgenaxis_spec::packet::source_sha256(bytes)
    ))
}
fn check_context(c: &DefinitionAuthorityContext) -> StoreResult<()> {
    if [&c.selection_id, &c.session_id, &c.owner_window]
        .iter()
        .any(|s| s.trim().is_empty())
    {
        Err(DefinitionStoreError::NotBound)
    } else {
        Ok(())
    }
}
fn join(root: &str, name: &str) -> String {
    let sep = if root.contains('\\') { '\\' } else { '/' };
    format!(
        "{}{sep}{}",
        root.trim_end_matches(['/', '\\']),
        name.replace('/', &sep.to_string())
    )
}
fn location_root(location: &DefinitionLocation) -> StoreResult<String> {
    let root = match location {
        DefinitionLocation::NewProject {
            canonical_parent,
            single_name,
        } => {
            crate::project_new::normalize_project_folder_name(single_name)
                .map_err(|_| input("location", DefinitionInputCode::InvalidLocation))?;
            if single_name != single_name.trim() {
                return Err(input("location", DefinitionInputCode::InvalidLocation));
            }
            join(canonical_parent, single_name)
        }
        DefinitionLocation::ExistingProject { canonical_root }
        | DefinitionLocation::LegacyAdoption { canonical_root, .. } => canonical_root.clone(),
    };
    if root.contains('\0')
        || root.trim() != root
        || crate::project_new::normalize_new_project_path(&root).is_err()
        || !std::path::Path::new(&root).is_absolute()
    {
        return Err(DefinitionStoreError::InvalidLocation {
            path: root,
            reason: "trusted absolute local location required".into(),
            retained_artifacts: vec![],
        });
    }
    Ok(root)
}
fn check_claims(
    id: &PersistentProjectId,
    root: &str,
    claims: &[OpenDefinitionClaim],
    expected: Option<&PersistentProjectId>,
) -> StoreResult<()> {
    if let Some(other) = claims
        .iter()
        .find(|c| &c.project_uuid == id && c.canonical_root != root)
    {
        return Err(DefinitionStoreError::IdentityConflict {
            expected_uuid: expected.cloned(),
            observed_uuid: id.clone(),
            requested_root: root.into(),
            other_root: Some(other.canonical_root.clone()),
            reason: IdentityConflictReason::DuplicateOpenRoot,
        });
    }
    Ok(())
}
fn fs_error(path: &str, e: sgenaxis_ports::PortError) -> DefinitionStoreError {
    DefinitionStoreError::StorageFailure {
        fault: StoreFault {
            stage: CommitStage::Read,
            path: path.into(),
            reason: e.to_string(),
        },
        retained_artifacts: vec![],
    }
}
fn existing_root(fs: &dyn FileSystemPort, root: &str) -> StoreResult<()> {
    if !fs.exists(root).map_err(|e| fs_error(root, e))?
        || fs.is_file(root).map_err(|e| fs_error(root, e))?
    {
        return Err(DefinitionStoreError::InvalidLocation {
            path: root.into(),
            reason: "selected project directory is unavailable".into(),
            retained_artifacts: vec![],
        });
    }
    Ok(())
}
fn open_impl(
    fs: &dyn FileSystemPort,
    c: &DefinitionAuthorityContext,
    loc: &DefinitionLocation,
    expected: Option<&PersistentProjectId>,
    claims: &[OpenDefinitionClaim],
) -> StoreResult<DefinitionOpenView> {
    check_context(c)?;
    if !matches!(loc, DefinitionLocation::ExistingProject { .. }) {
        return Err(input("location", DefinitionInputCode::InvalidLocation));
    }
    let root = location_root(loc)?;
    existing_root(fs, &root)?;
    let path = join(&root, ".sgenaxis/project-definition.json");
    let first = match fs.read(&path) {
        Ok(b) => b,
        Err(sgenaxis_ports::PortError::NotFound(_)) => {
            existing_root(fs, &root)?;
            return Ok(DefinitionOpenView::Legacy {
                canonical_root: root,
                portable_legacy_keys: vec![],
                migration_required: true,
            });
        }
        Err(e) => return Err(fs_error(&path, e)),
    };
    let d = decode_definition(&first)?;
    let first_digest = raw_hash(&first);
    let second = fs.read(&path);
    if second.as_ref().ok() != Some(&first) {
        return Err(DefinitionStoreError::RevisionConflict {
            expected_digest: Some(first_digest),
            observed_digest: second.ok().as_deref().map(raw_hash),
            expected_revision: Some(d.definition_revision),
            observed_revision: None,
        });
    }
    if expected.is_some_and(|id| id != &d.project_uuid) {
        return Err(DefinitionStoreError::IdentityConflict {
            expected_uuid: expected.cloned(),
            observed_uuid: d.project_uuid,
            requested_root: root,
            other_root: None,
            reason: IdentityConflictReason::BoundUuidMismatch,
        });
    }
    check_claims(&d.project_uuid, &root, claims, expected)?;
    Ok(DefinitionOpenView::Saved {
        definition: d,
        raw_digest: first_digest,
        canonical_root: root,
        relative_path: ".sgenaxis/project-definition.json".into(),
    })
}
fn check_prepared(p: &PreparedPreferencePlan) -> StoreResult<()> {
    let (bytes, digest) = match p {
        PreparedPreferencePlan::Skip => return Ok(()),
        PreparedPreferencePlan::Preset {
            preset_id,
            encoded_bytes,
            digest,
        } => {
            let preset = sgenaxis_spec::project_preferences::preset(preset_id)
                .map_err(|_| input("preferences.preset", DefinitionInputCode::PreferenceInvalid))?;
            let parsed =
                sgenaxis_spec::project_preferences::parse_project_preferences(encoded_bytes)
                    .map_err(|_| input("preferences", DefinitionInputCode::PreferenceInvalid))?;
            if preset != parsed {
                return Err(input("preferences", DefinitionInputCode::PreferenceInvalid));
            }
            (encoded_bytes, digest)
        }
        PreparedPreferencePlan::ImportedCopy {
            captured_source_digest,
            encoded_bytes,
            digest,
        } => {
            if !valid_digest(captured_source_digest.as_str()) {
                return Err(input(
                    "preferences.import",
                    DefinitionInputCode::PreferenceInvalid,
                ));
            }
            (encoded_bytes, digest)
        }
    };
    sgenaxis_spec::project_preferences::parse_project_preferences(bytes)
        .map_err(|_| input("preferences", DefinitionInputCode::PreferenceInvalid))?;
    if raw_hash(bytes) != *digest {
        return Err(input("preferences", DefinitionInputCode::PreferenceInvalid));
    }
    Ok(())
}
fn map_commit(
    e: sgenaxis_ports::CommitError,
    p: &CreationProgress,
    path: &str,
) -> DefinitionStoreError {
    use sgenaxis_ports::CommitError as E;
    match e {
        E::RecoveryRequired {
            target_path,
            journal_path,
            old_version_path,
            new_version_path,
            reason,
        } => DefinitionStoreError::RecoveryRequired {
            diagnostics: RecoveryInfo {
                target_path,
                journal_path,
                old_version_path,
                new_version_path,
                reason,
            },
            progress: Some(p.clone()),
        },
        other => {
            let cause = match &other {
                E::AlreadyExists { path } => {
                    CreationFailureCause::ExistingTarget { path: path.clone() }
                }
                E::Conflict { expected, observed } => CreationFailureCause::Conflict {
                    expected: expected
                        .as_deref()
                        .and_then(RawDefinitionDigest::try_from_text),
                    observed: observed
                        .as_deref()
                        .and_then(RawDefinitionDigest::try_from_text),
                },
                E::Busy { path } => CreationFailureCause::Busy { path: path.clone() },
                E::Storage {
                    stage,
                    path,
                    reason,
                } => CreationFailureCause::Storage {
                    fault: StoreFault {
                        stage: *stage,
                        path: path.clone(),
                        reason: reason.clone(),
                    },
                },
                E::InvalidPath { reason } => CreationFailureCause::InvalidLocation {
                    path: path.into(),
                    reason: reason.clone(),
                },
                _ => unreachable!(),
            };
            if p.root_created {
                return DefinitionStoreError::PartialProjectCreated {
                    progress: p.clone(),
                    cause,
                };
            }
            match other {
                E::AlreadyExists { path } => DefinitionStoreError::ExistingTarget { path },
                E::Conflict { expected, observed } => DefinitionStoreError::RevisionConflict {
                    expected_digest: expected
                        .as_deref()
                        .and_then(RawDefinitionDigest::try_from_text),
                    observed_digest: observed
                        .as_deref()
                        .and_then(RawDefinitionDigest::try_from_text),
                    expected_revision: None,
                    observed_revision: None,
                },
                E::Busy { path } => DefinitionStoreError::Busy { path },
                E::Storage {
                    stage,
                    path,
                    reason,
                } => DefinitionStoreError::StorageFailure {
                    fault: StoreFault {
                        stage,
                        path,
                        reason,
                    },
                    retained_artifacts: p.owned_artifacts.clone(),
                },
                E::InvalidPath { reason } => DefinitionStoreError::InvalidLocation {
                    path: path.into(),
                    reason,
                    retained_artifacts: p.owned_artifacts.clone(),
                },
                _ => unreachable!(),
            }
        }
    }
}
fn progress_fs(
    e: sgenaxis_ports::PortError,
    p: &CreationProgress,
    path: &str,
) -> DefinitionStoreError {
    map_commit(
        sgenaxis_ports::CommitError::Storage {
            stage: CommitStage::Read,
            path: path.into(),
            reason: e.to_string(),
        },
        p,
        path,
    )
}
fn owned_dir(p: &mut CreationProgress, relative_path: &str, kind: CreationArtifactKind) {
    p.owned_artifacts.push(OwnedCreationArtifact {
        relative_path: relative_path.into(),
        kind,
        state: CreationArtifactState::CreatedDirectory,
        raw_digest: None,
        transaction_id: None,
    })
}
fn owned_file(
    p: &mut CreationProgress,
    relative_path: &str,
    kind: CreationArtifactKind,
    receipt: &CommitReceipt,
) {
    p.owned_artifacts.push(OwnedCreationArtifact {
        relative_path: relative_path.into(),
        kind,
        state: CreationArtifactState::CommittedFile,
        raw_digest: Some(raw_hash_digest(&receipt.committed_digest)),
        transaction_id: Some(receipt.transaction_id.clone()),
    })
}
fn raw_hash_digest(s: &str) -> RawDefinitionDigest {
    RawDefinitionDigest(s.into())
}
fn checked_receipt(
    receipt: CommitReceipt,
    target: &str,
    expected: Option<&str>,
    bytes: &[u8],
    p: &CreationProgress,
) -> StoreResult<CommitReceipt> {
    if receipt.target_path != target
        || receipt.previous_digest.as_deref() != expected
        || receipt.committed_digest != raw_hash(bytes).as_str()
        || receipt.transaction_id.len() != 32
        || !receipt
            .transaction_id
            .bytes()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    {
        return Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target: target.into(),
            reported_receipt: receipt,
            progress: p.clone(),
        });
    }
    Ok(receipt)
}
fn save_impl(
    fs: &dyn FileSystemPort,
    commit: &dyn FileCommitPort,
    b: &DefinitionBinding,
    expected: Option<&str>,
    d: &ProjectDefinition,
) -> StoreResult<DefinitionSaveReceipt> {
    check_context(&b.context)?;
    let root = location_root(&b.location)?;
    if d.project_uuid != b.project_uuid {
        return Err(input("projectUuid", DefinitionInputCode::BindingMismatch));
    }
    let baseline_digest = match &b.baseline {
        DefinitionBaseline::Absent => None,
        DefinitionBaseline::Present { raw_digest, .. } => Some(raw_digest.as_str()),
    };
    if expected != baseline_digest {
        return Err(input(
            "expectedDiskDigest",
            DefinitionInputCode::ExpectedDigestMismatch,
        ));
    }
    let mode_ok = match (&b.location, &b.preferences, d.draft.preference_source) {
        (
            DefinitionLocation::NewProject { .. },
            PreparedPreferencePlan::Skip,
            PreferenceSource::Skip,
        )
        | (
            DefinitionLocation::NewProject { .. },
            PreparedPreferencePlan::Preset { .. },
            PreferenceSource::Preset,
        )
        | (
            DefinitionLocation::NewProject { .. },
            PreparedPreferencePlan::ImportedCopy { .. },
            PreferenceSource::ImportedCopy,
        ) => true,
        (DefinitionLocation::ExistingProject { .. }, PreparedPreferencePlan::Skip, _) => true,
        (
            DefinitionLocation::LegacyAdoption { .. },
            PreparedPreferencePlan::Skip,
            PreferenceSource::Skip,
        ) => true,
        _ => false,
    };
    if !mode_ok {
        return Err(input(
            "preferences",
            DefinitionInputCode::PreferenceModeMismatch,
        ));
    }
    check_prepared(&b.preferences)?;
    if matches!(b.location, DefinitionLocation::NewProject { .. }) && d.definition_revision.0 != 0 {
        return Err(input(
            "definitionRevision",
            DefinitionInputCode::RevisionNotAdvanced,
        ));
    }
    let bytes = encode_definition(d)?;
    let path = join(&root, ".sgenaxis/project-definition.json");
    let metadata = join(&root, ".sgenaxis");
    let mut p = CreationProgress {
        canonical_root: root.clone(),
        root_created: false,
        phase: CreationPhase::CommitDefinition,
        owned_artifacts: vec![],
        definition_commit: None,
    };
    match &b.location {
        DefinitionLocation::NewProject {
            canonical_parent,
            single_name,
        } => {
            p.phase = CreationPhase::CreateRoot;
            commit
                .create_directory_exclusive(canonical_parent, single_name)
                .map_err(|e| map_commit(e, &p, &root))?;
            p.root_created = true;
            owned_dir(&mut p, ".", CreationArtifactKind::RootDirectory);
            p.phase = CreationPhase::CreateMetadata;
            commit
                .create_directory_exclusive(&root, ".sgenaxis")
                .map_err(|e| map_commit(e, &p, &metadata))?;
            owned_dir(&mut p, ".sgenaxis", CreationArtifactKind::MetadataDirectory);
        }
        DefinitionLocation::LegacyAdoption {
            portable_legacy_keys,
            ..
        } => {
            existing_root(fs, &root)?;
            if &d.legacy_root_keys != portable_legacy_keys {
                return Err(input(
                    "legacyRootKeys",
                    DefinitionInputCode::BindingMismatch,
                ));
            }
            // Refuse a present definition before creating metadata. The later
            // lease comparison still protects against a concurrent arrival.
            match fs.read(&path) {
                Ok(bytes) => {
                    return Err(DefinitionStoreError::RevisionConflict {
                        expected_digest: None,
                        observed_digest: Some(raw_hash(&bytes)),
                        expected_revision: None,
                        observed_revision: None,
                    })
                }
                Err(sgenaxis_ports::PortError::NotFound(_)) => {}
                Err(error) => return Err(progress_fs(error, &p, &path)),
            }
            p.phase = CreationPhase::CreateMetadata;
            if fs
                .is_file(&metadata)
                .map_err(|e| progress_fs(e, &p, &metadata))?
            {
                return Err(DefinitionStoreError::ExistingTarget { path: metadata });
            }
            if !fs
                .exists(&metadata)
                .map_err(|e| progress_fs(e, &p, &metadata))?
            {
                commit
                    .create_directory_exclusive(&root, ".sgenaxis")
                    .map_err(|e| map_commit(e, &p, &metadata))?;
                owned_dir(&mut p, ".sgenaxis", CreationArtifactKind::MetadataDirectory)
            }
        }
        DefinitionLocation::ExistingProject { .. } => {
            existing_root(fs, &root)?;
        }
    }
    p.phase = CreationPhase::CommitDefinition;
    let receipt = {
        let mut lease = commit
            .acquire_write(&path)
            .map_err(|e| map_commit(e, &p, &path))?;
        let current = lease.read_current().map_err(|e| map_commit(e, &p, &path))?;
        let observed = current.as_deref().map(raw_hash);
        let expected_digest = baseline_digest.and_then(RawDefinitionDigest::try_from_text);
        if observed != expected_digest {
            return Err(if p.root_created {
                map_commit(
                    sgenaxis_ports::CommitError::Conflict {
                        expected: baseline_digest.map(String::from),
                        observed: observed.as_ref().map(|d| d.as_str().into()),
                    },
                    &p,
                    &path,
                )
            } else {
                DefinitionStoreError::RevisionConflict {
                    expected_digest,
                    observed_digest: observed,
                    expected_revision: match b.baseline {
                        DefinitionBaseline::Present { revision, .. } => Some(revision),
                        _ => None,
                    },
                    observed_revision: None,
                }
            });
        }
        if let DefinitionBaseline::Present {
            revision,
            project_uuid,
            ..
        } = &b.baseline
        {
            let old = decode_definition(current.as_deref().expect("present matching baseline"))?;
            if &old.project_uuid != project_uuid {
                return Err(DefinitionStoreError::IdentityConflict {
                    expected_uuid: Some(project_uuid.clone()),
                    observed_uuid: old.project_uuid,
                    requested_root: root.clone(),
                    other_root: None,
                    reason: IdentityConflictReason::BoundUuidMismatch,
                });
            }
            if old.definition_revision != *revision {
                return Err(DefinitionStoreError::RevisionConflict {
                    expected_digest: expected_digest.clone(),
                    observed_digest: observed,
                    expected_revision: Some(*revision),
                    observed_revision: Some(old.definition_revision),
                });
            }
            if d.definition_revision.0 < revision.0
                || (d.definition_revision == *revision && d != &old)
            {
                return Err(input(
                    "definitionRevision",
                    DefinitionInputCode::RevisionNotAdvanced,
                ));
            }
        }
        let r = lease
            .replace_checked(baseline_digest, &bytes)
            .map_err(|e| map_commit(e, &p, &path))?;
        checked_receipt(r, &path, baseline_digest, &bytes, &p)?
    };
    let proof = DefinitionCommitProof {
        project_uuid: d.project_uuid.clone(),
        persisted_revision: d.definition_revision,
        relative_path: ".sgenaxis/project-definition.json".into(),
        raw_digest: raw_hash_digest(&receipt.committed_digest),
        transaction_id: receipt.transaction_id.clone(),
    };
    owned_file(
        &mut p,
        ".sgenaxis/project-definition.json",
        CreationArtifactKind::DefinitionFile,
        &receipt,
    );
    p.definition_commit = Some(proof.clone());
    let preferences = match &b.preferences {
        PreparedPreferencePlan::Skip => PreferenceCommitStatus::Skipped,
        PreparedPreferencePlan::Preset { encoded_bytes, .. }
        | PreparedPreferencePlan::ImportedCopy { encoded_bytes, .. } => {
            p.phase = CreationPhase::CommitPreferences;
            let target = join(&root, ".sgenaxis/preferences.json");
            let mut lease = commit
                .acquire_write(&target)
                .map_err(|e| map_commit(e, &p, &target))?;
            let r = lease
                .replace_checked(None, encoded_bytes)
                .map_err(|e| map_commit(e, &p, &target))?;
            let r = checked_receipt(r, &target, None, encoded_bytes, &p)?;
            owned_file(
                &mut p,
                ".sgenaxis/preferences.json",
                CreationArtifactKind::PreferencesFile,
                &r,
            );
            PreferenceCommitStatus::Committed {
                relative_path: ".sgenaxis/preferences.json".into(),
                raw_digest: raw_hash_digest(&r.committed_digest),
                transaction_id: r.transaction_id,
            }
        }
    };
    let next_binding = DefinitionBinding {
        context: b.context.clone(),
        location: DefinitionLocation::ExistingProject {
            canonical_root: root.clone(),
        },
        project_uuid: d.project_uuid.clone(),
        baseline: DefinitionBaseline::Present {
            raw_digest: proof.raw_digest.clone(),
            revision: d.definition_revision,
            project_uuid: d.project_uuid.clone(),
        },
        preferences: PreparedPreferencePlan::Skip,
    };
    Ok(DefinitionSaveReceipt {
        definition: proof,
        canonical_root: root,
        creation: p,
        preferences,
        next_binding,
    })
}
