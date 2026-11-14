//! M01-S2 approved local HOST boundary. Skeleton only; no runtime wiring.
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
        // Candidate-only Skeleton seam. Validation tests must remain RED.
        Some(Self(raw.to_owned()))
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
fn not_implemented<T>() -> Result<T, DefinitionStoreError> {
    Err(DefinitionStoreError::InvalidInput {
        field: "$SKELETON_NOT_IMPLEMENTED".into(),
        code: DefinitionInputCode::DomainInvalid,
    })
}

#[allow(unused_variables)]
pub fn encode_definition(definition: &ProjectDefinition) -> Result<Vec<u8>, DefinitionStoreError> {
    not_implemented()
}

#[allow(unused_variables)]
pub fn decode_definition(bytes: &[u8]) -> Result<ProjectDefinition, DefinitionStoreError> {
    not_implemented()
}

#[allow(unused_variables)]
pub fn open_definition(
    fs: &dyn FileSystemPort,
    context: &DefinitionAuthorityContext,
    location: &DefinitionLocation,
    expected_uuid: Option<&PersistentProjectId>,
    open_claims: &[OpenDefinitionClaim],
) -> Result<DefinitionOpenView, DefinitionStoreError> {
    not_implemented()
}

#[allow(unused_variables)]
pub fn prepare_definition_preferences(
    choice: PreferenceChoice<'_>,
) -> Result<PreparedPreferencePlan, DefinitionStoreError> {
    not_implemented()
}

#[allow(unused_variables)]
pub fn bind_definition(
    fs: &dyn FileSystemPort,
    context: DefinitionAuthorityContext,
    location: DefinitionLocation,
    project_uuid: PersistentProjectId,
    baseline: DefinitionBaseline,
    preferences: PreparedPreferencePlan,
    open_claims: &[OpenDefinitionClaim],
) -> Result<DefinitionBinding, DefinitionStoreError> {
    // Structural capture only. No validation, IO, or authority grant.
    Ok(DefinitionBinding {
        context,
        location,
        project_uuid,
        baseline,
        preferences,
    })
}

#[allow(unused_variables)]
pub fn save_definition(
    fs: &dyn FileSystemPort,
    commit: &dyn FileCommitPort,
    binding: &DefinitionBinding,
    expected_disk_digest: Option<&str>,
    definition: &ProjectDefinition,
) -> Result<DefinitionSaveReceipt, DefinitionStoreError> {
    not_implemented()
}
