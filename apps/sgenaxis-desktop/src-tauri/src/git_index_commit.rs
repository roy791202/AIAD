//! HOST-owned one-use preview and confirmation coordinator for the A1 staged Index route.

use std::collections::HashMap;
use std::path::Path;
use std::sync::{Arc, Mutex, TryLockError};

use serde::{Deserialize, Serialize};
use sgenaxis_ports::{GitIndexCommitPort, IndexCommitError, IndexCommitFacts, IndexCommitFingerprint};
use sgenaxis_ports::{GitOperationState, GitWriteApproval};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexCommitFingerprintDto {
    pub repo_root: String,
    pub project_root: String,
    pub head_oid: Option<String>,
    pub index_tree_oid: String,
    pub staged_paths: Vec<String>,
}

impl From<IndexCommitFingerprint> for IndexCommitFingerprintDto {
    fn from(value: IndexCommitFingerprint) -> Self {
        Self { repo_root: value.repo_root, project_root: value.project_root,
            head_oid: value.head_oid, index_tree_oid: value.index_tree_oid,
            staged_paths: value.staged_paths }
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexCommitFactsDto {
    pub fingerprint: IndexCommitFingerprintDto,
    pub index_nonempty: bool,
    pub unmerged: bool,
    pub operation: String,
}

impl From<IndexCommitFacts> for IndexCommitFactsDto {
    fn from(value: IndexCommitFacts) -> Self {
        Self { fingerprint: value.fingerprint.into(), index_nonempty: value.index_nonempty,
            unmerged: value.unmerged, operation: format!("{:?}", value.operation) }
    }
}

impl From<&IndexCommitFingerprint> for IndexCommitFingerprintDto {
    fn from(value: &IndexCommitFingerprint) -> Self {
        Self { repo_root: value.repo_root.clone(), project_root: value.project_root.clone(),
            head_oid: value.head_oid.clone(), index_tree_oid: value.index_tree_oid.clone(),
            staged_paths: value.staged_paths.clone() }
    }
}

impl From<&IndexCommitFingerprintDto> for IndexCommitFingerprint {
    fn from(value: &IndexCommitFingerprintDto) -> Self {
        Self { repo_root: value.repo_root.clone(), project_root: value.project_root.clone(),
            head_oid: value.head_oid.clone(), index_tree_oid: value.index_tree_oid.clone(),
            staged_paths: value.staged_paths.clone() }
    }
}

fn error_parts(value: &IndexCommitError) -> (&'static str, String) {
    match value {
        IndexCommitError::InvalidInput(s) => ("InvalidInput", s.clone()),
        IndexCommitError::ApprovalRequired => ("ApprovalRequired", "explicit confirmation is required".into()),
        IndexCommitError::Unavailable(s) => ("Unavailable", s.clone()),
        IndexCommitError::NonRepo(s) => ("NonRepo", s.clone()),
        IndexCommitError::Unreadable(s) => ("Unreadable", s.clone()),
        IndexCommitError::OutsideProjectScope(s) => ("OutsideProjectScope", s.clone()),
        IndexCommitError::UnsupportedPolicy(s) => ("UnsupportedPolicy", s.clone()),
        IndexCommitError::StalePreview => ("StalePreview", "HEAD or Index changed after preview".into()),
        IndexCommitError::Busy => ("Busy", "another A1 commit is active for this repository".into()),
        IndexCommitError::Conflicted => ("Conflicted", "Index contains unmerged entries".into()),
        IndexCommitError::OperationInProgress => ("OperationInProgress", "Git operation is in progress".into()),
        IndexCommitError::NothingStaged => ("NothingStaged", "Index has no staged changes".into()),
        IndexCommitError::FailedObserved(s) => ("FailedObserved", s.clone()),
        IndexCommitError::OutcomeUnknown(s) => ("OutcomeUnknown", s.clone()),
        IndexCommitError::InvalidPreview => ("InvalidPreview", "preview is missing, stale, or consumed".into()),
    }
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexCommitPreviewDto {
    pub preview_id: String,
    pub generation: u64,
    pub fingerprint: IndexCommitFingerprintDto,
    pub display_paths: Vec<String>,
    pub message_required: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexCommitRequestDto {
    pub preview_id: String,
    pub generation: u64,
    pub message: String,
    pub confirmed: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexCommitOutcomeDto {
    pub preview_id: String,
    pub state: String,
    pub before: IndexCommitFingerprintDto,
    pub after: Option<IndexCommitFingerprintDto>,
    pub created_commit_oid: Option<String>,
    pub process_exit_code: Option<i32>,
    pub diagnostic: Option<String>,
    pub worktree_preserved_guarantee: String,
    pub retry_requires_new_preview: bool,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IndexCommitErrorDto {
    pub code: String,
    pub preview_id: Option<String>,
    pub observed: Option<IndexCommitFactsDto>,
    pub diagnostic: String,
    pub mutation_started: bool,
    pub requires_new_preview: bool,
}

impl From<IndexCommitError> for IndexCommitErrorDto {
    fn from(value: IndexCommitError) -> Self {
        let (code, diagnostic) = error_parts(&value);
        let mutation_started = matches!(&value, IndexCommitError::FailedObserved(_) | IndexCommitError::OutcomeUnknown(_));
        let requires_new_preview = mutation_started || matches!(&value, IndexCommitError::StalePreview | IndexCommitError::InvalidPreview);
        Self { code: code.into(), preview_id: None, observed: None, diagnostic,
            mutation_started, requires_new_preview }
    }
}

/// Owns session-scoped preview records; Git owns the Index, HEAD and worktree.
pub struct IndexCommitCoordinator {
    port: Arc<dyn GitIndexCommitPort>,
    state: Mutex<CoordinatorState>,
}

struct PreviewRecord {
    dto: IndexCommitPreviewDto,
    consumed: bool,
}

#[derive(Default)]
struct CoordinatorState {
    next_generation: u64,
    previews: HashMap<String, PreviewRecord>,
    repo_locks: HashMap<String, Arc<Mutex<()>>>,
}

impl IndexCommitCoordinator {
    pub fn new(port: Arc<dyn GitIndexCommitPort>) -> Self {
        Self { port, state: Mutex::new(CoordinatorState::default()) }
    }

    pub fn prepare(&self, project_root: &str) -> Result<IndexCommitPreviewDto, IndexCommitErrorDto> {
        if project_root.trim().is_empty() || project_root.contains('\0') || !Path::new(project_root).is_absolute() {
            return Err(IndexCommitError::InvalidInput("project root must be a nonempty absolute path without NUL".into()).into());
        }
        let facts = self.port.inspect_index(project_root).map_err(IndexCommitErrorDto::from)?;
        validate_facts(&facts).map_err(IndexCommitErrorDto::from)?;
        let mut state = self.state.lock().map_err(|_| IndexCommitErrorDto::from(IndexCommitError::OutcomeUnknown("preview state lock poisoned".into())))?;
        state.next_generation = state.next_generation.checked_add(1)
            .ok_or_else(|| IndexCommitErrorDto::from(IndexCommitError::OutcomeUnknown("preview generation exhausted".into())))?;
        let generation = state.next_generation;
        let preview_id = uuid::Uuid::new_v4().to_string();
        let dto = IndexCommitPreviewDto {
            preview_id: preview_id.clone(), generation,
            fingerprint: (&facts.fingerprint).into(),
            display_paths: facts.fingerprint.staged_paths.clone(),
            message_required: true,
        };
        state.previews.retain(|_, record| record.dto.fingerprint.project_root != facts.fingerprint.project_root);
        state.previews.insert(preview_id, PreviewRecord { dto: dto.clone(), consumed: false });
        Ok(dto)
    }

    pub fn commit(&self, request: IndexCommitRequestDto) -> Result<IndexCommitOutcomeDto, IndexCommitErrorDto> {
        if request.message.trim().is_empty() || request.message.contains('\0') {
            return Err(IndexCommitError::InvalidInput("commit message must be nonempty and contain no NUL".into()).into());
        }
        if !request.confirmed { return Err(IndexCommitError::ApprovalRequired.into()); }

        let record = {
            let state = self.state.lock().map_err(|_| IndexCommitErrorDto::from(IndexCommitError::InvalidPreview))?;
            let record = state.previews.get(&request.preview_id).ok_or_else(|| IndexCommitErrorDto::from(IndexCommitError::InvalidPreview))?;
            if record.consumed || record.dto.generation != request.generation {
                return Err(IndexCommitError::InvalidPreview.into());
            }
            record.dto.clone()
        };
        let repo_lock = {
            let mut state = self.state.lock().map_err(|_| IndexCommitErrorDto::from(IndexCommitError::Busy))?;
            state.repo_locks.entry(record.fingerprint.repo_root.clone())
                .or_insert_with(|| Arc::new(Mutex::new(()))).clone()
        };
        let _guard = match repo_lock.try_lock() {
            Ok(guard) => guard,
            Err(TryLockError::WouldBlock) => return Err(IndexCommitError::Busy.into()),
            Err(TryLockError::Poisoned(_)) => return Err(IndexCommitError::Busy.into()),
        };

        let current = self.port.inspect_index(&record.fingerprint.project_root).map_err(|e| {
            let mut dto = IndexCommitErrorDto::from(e);
            dto.preview_id = Some(request.preview_id.clone());
            dto
        })?;
        validate_facts(&current).map_err(|e| { let mut dto = IndexCommitErrorDto::from(e); dto.preview_id = Some(request.preview_id.clone()); dto })?;
        if IndexCommitFingerprintDto::from(&current.fingerprint) != record.fingerprint {
            if let Ok(mut state) = self.state.lock() { state.previews.remove(&request.preview_id); }
            let mut dto = IndexCommitErrorDto::from(IndexCommitError::StalePreview);
            dto.preview_id = Some(request.preview_id);
            dto.mutation_started = false;
            dto.requires_new_preview = true;
            return Err(dto);
        }

        {
            let mut state = self.state.lock().map_err(|_| IndexCommitErrorDto::from(IndexCommitError::InvalidPreview))?;
            let stored = state.previews.get_mut(&request.preview_id).ok_or_else(|| IndexCommitErrorDto::from(IndexCommitError::InvalidPreview))?;
            if stored.consumed || stored.dto.generation != request.generation { return Err(IndexCommitError::InvalidPreview.into()); }
            stored.consumed = true;
        }

        let expected: IndexCommitFingerprint = (&record.fingerprint).into();
        let observation = self.port.commit_index(
            &record.fingerprint.project_root,
            &request.message,
            &expected,
            GitWriteApproval::granted(),
        );
        let observation = match observation {
            Ok(observation) => {
                if let Ok(mut state) = self.state.lock() { state.previews.remove(&request.preview_id); }
                observation
            }
            Err(error) => {
                if matches!(&error, IndexCommitError::StalePreview) {
                    if let Ok(mut state) = self.state.lock() { state.previews.remove(&request.preview_id); }
                    let mut dto = IndexCommitErrorDto::from(IndexCommitError::StalePreview);
                    dto.preview_id = Some(request.preview_id);
                    dto.mutation_started = false;
                    dto.requires_new_preview = true;
                    return Err(dto);
                }
                let attempted = matches!(&error, IndexCommitError::FailedObserved(_) | IndexCommitError::OutcomeUnknown(_));
                if !attempted {
                    if let Ok(mut state) = self.state.lock() {
                        if let Some(stored) = state.previews.get_mut(&request.preview_id) { stored.consumed = false; }
                    }
                } else if let Ok(mut state) = self.state.lock() {
                    state.previews.remove(&request.preview_id);
                }
                let mut dto = IndexCommitErrorDto::from(error);
                dto.preview_id = Some(request.preview_id);
                dto.mutation_started = attempted;
                dto.requires_new_preview = attempted;
                return Err(dto);
            }
        };
        let after = observation.after.as_ref().map(|facts| IndexCommitFingerprintDto::from(&facts.fingerprint));
        let after_head = observation.after.as_ref().and_then(|facts| facts.fingerprint.head_oid.clone());
        let observed_commit = observation.invocation_started
            && observation.exit_code == Some(0)
            && observation.diagnostic.is_none()
            && after_head.is_some()
            && after_head != record.fingerprint.head_oid
            && observation.observed_parent_oid == record.fingerprint.head_oid
            && observation.observed_tree_oid.as_deref() == Some(record.fingerprint.index_tree_oid.as_str())
            && observation.after.as_ref().is_some_and(|facts| facts.fingerprint.index_tree_oid == record.fingerprint.index_tree_oid);
        if observed_commit {
            Ok(IndexCommitOutcomeDto {
                preview_id: request.preview_id,
                state: "Committed".into(),
                before: record.fingerprint,
                after,
                created_commit_oid: after_head,
                process_exit_code: observation.exit_code,
                diagnostic: observation.diagnostic,
                worktree_preserved_guarantee: "NotMutatedByThisRoute".into(),
                retry_requires_new_preview: true,
            })
        } else {
            let spawn_failed = !observation.invocation_started;
            let mut dto = IndexCommitErrorDto::from(if spawn_failed && observation.after.is_some() || observation.exit_code.is_some_and(|code| code != 0) {
                IndexCommitError::FailedObserved(observation.diagnostic.clone().unwrap_or_else(|| "commit process failed".into()))
            } else {
                IndexCommitError::OutcomeUnknown(observation.diagnostic.clone().unwrap_or_else(|| "commit postconditions were not observed".into()))
            });
            dto.preview_id = Some(request.preview_id);
            dto.observed = observation.after.map(Into::into);
            dto.mutation_started = observation.invocation_started;
            dto.requires_new_preview = true;
            Err(dto)
        }
    }
}

fn validate_facts(facts: &IndexCommitFacts) -> Result<(), IndexCommitError> {
    if facts.operation != GitOperationState::None { return Err(IndexCommitError::OperationInProgress); }
    if facts.unmerged { return Err(IndexCommitError::Conflicted); }
    let root = Path::new(&facts.fingerprint.repo_root);
    let project = Path::new(&facts.fingerprint.project_root);
    let project_rel = project.strip_prefix(root).map_err(|_| IndexCommitError::OutsideProjectScope("project root is outside repository".into()))?;
    let prefix = project_rel.to_string_lossy().replace('\\', "/");
    for path in &facts.fingerprint.staged_paths {
        let candidate = Path::new(path);
        if candidate.is_absolute() || candidate.components().any(|c| matches!(c, std::path::Component::ParentDir)) {
            return Err(IndexCommitError::OutsideProjectScope(path.clone()));
        }
        let normalized = path.replace('\\', "/");
        if !prefix.is_empty() && normalized != prefix && !normalized.starts_with(&(prefix.clone() + "/")) {
            return Err(IndexCommitError::OutsideProjectScope(path.clone()));
        }
    }
    if facts.fingerprint.staged_paths.is_empty() || !facts.index_nonempty { return Err(IndexCommitError::NothingStaged); }
    Ok(())
}

#[cfg(test)]
#[path = "git_index_commit_tests.rs"]
mod tests;
