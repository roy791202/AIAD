//! M04-S1 pure single-document history, capture and independent save baselines.
//! Candidate content is supplied by the future trusted codec boundary; this
//! module does not parse XML, hash bytes, write files, pin assets or run timers.

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Revision(pub u64);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AssetVersionRef {
    pub asset_id: String,
    pub content_digest: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BindingStatus {
    Valid,
    Pending,
    Invalid,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct BindingState {
    pub id: String,
    pub target_id: Option<String>,
    pub state: BindingStatus,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentContent {
    canonical_payload: Vec<u8>,
    semantic_digest: String,
    asset_refs: Vec<AssetVersionRef>,
    bindings: Vec<BindingState>,
    blocked_capabilities: Vec<String>,
}

impl DocumentContent {
    /// Structural codec/fixture input seam only, not parsing or validation.
    pub fn from_parts(
        canonical_payload: Vec<u8>,
        semantic_digest: String,
        asset_refs: Vec<AssetVersionRef>,
        bindings: Vec<BindingState>,
        blocked_capabilities: Vec<String>,
    ) -> Self {
        Self {
            canonical_payload,
            semantic_digest,
            asset_refs,
            bindings,
            blocked_capabilities,
        }
    }

    pub fn canonical_payload(&self) -> &[u8] {
        &self.canonical_payload
    }
    pub fn semantic_digest(&self) -> &str {
        &self.semantic_digest
    }
    pub fn asset_refs(&self) -> &[AssetVersionRef] {
        &self.asset_refs
    }
    pub fn bindings(&self) -> &[BindingState] {
        &self.bindings
    }
    pub fn blocked_capabilities(&self) -> &[String] {
        &self.blocked_capabilities
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum MutationKind {
    Edit,
    Clear,
    Merge,
}

/// Plain plan data is not authority. Commit must eventually verify document,
/// session, revision, before-content and required asset versions independently.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MutationPlan {
    pub document_uuid: String,
    pub session_uuid: String,
    pub expected_revision: Revision,
    pub kind: MutationKind,
    pub before: DocumentContent,
    pub after: DocumentContent,
    pub required_asset_versions: Vec<AssetVersionRef>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentHistoryEntry {
    pub kind: MutationKind,
    pub before: DocumentContent,
    pub after: DocumentContent,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SavedContentBaseline {
    pub revision: Revision,
    pub semantic_digest: String,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SessionStatus {
    Editing,
    Applying,
    Saving,
    RecoveryRequired,
    Closed,
}

/// Ownership scaffold for a trusted session initializer. No writable reference
/// escapes DocumentSession; history has one owner, not duplicated counters.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentSessionState {
    pub project_uuid: String,
    pub document_uuid: String,
    pub session_uuid: String,
    pub content_revision: Revision,
    pub content: DocumentContent,
    pub formal_baseline: Option<SavedContentBaseline>,
    pub snapshot_baseline: Option<SavedContentBaseline>,
    pub status: SessionStatus,
    pub undo: Vec<DocumentHistoryEntry>,
    pub redo: Vec<DocumentHistoryEntry>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CommitProjection {
    pub revision: Revision,
    pub changed: bool,
    pub dirty: bool,
    pub history_depth: usize,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ImmutableDocumentSnapshot {
    pub document_uuid: String,
    pub session_uuid: String,
    pub revision: Revision,
    pub content: DocumentContent,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SaveProjection {
    pub captured_revision: Revision,
    pub dirty: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RecoveryProjection {
    pub captured_revision: Revision,
    pub needs_snapshot: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum EditError {
    /// Reserved marker retained for source compatibility; implemented operations do not return it.
    NotReady,
    InvalidInput {
        field: String,
    },
    RevisionConflict,
    RevisionOverflow,
    Busy,
    NoUndo,
    Closed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DocumentSession {
    state: DocumentSessionState,
}

impl DocumentSession {
    /// Ownership construction only. No runtime hydration or business mutation.
    pub fn new(initial: DocumentSessionState) -> Self {
        Self { state: initial }
    }
    /// Observation seam, no mutable access and no derived dirty/history policy.
    pub fn state(&self) -> &DocumentSessionState {
        &self.state
    }

    pub fn prepare(
        &self,
        expected: Revision,
        kind: MutationKind,
        validated_after: DocumentContent,
    ) -> Result<MutationPlan, EditError> {
        self.check_editable()?;
        self.check_revision(expected)?;
        self.check_content(&validated_after)?;
        let mut required = self.state.content.asset_refs.clone();
        for version in &validated_after.asset_refs {
            if !required.contains(version) {
                required.push(version.clone());
            }
        }
        Ok(MutationPlan {
            document_uuid: self.state.document_uuid.clone(),
            session_uuid: self.state.session_uuid.clone(),
            expected_revision: expected,
            kind,
            before: self.state.content.clone(),
            after: validated_after,
            required_asset_versions: required,
        })
    }

    pub fn commit(&mut self, plan: MutationPlan) -> Result<CommitProjection, EditError> {
        self.check_editable()?;
        if plan.document_uuid != self.state.document_uuid {
            return Err(EditError::InvalidInput {
                field: "documentUuid".into(),
            });
        }
        if plan.session_uuid != self.state.session_uuid {
            return Err(EditError::InvalidInput {
                field: "sessionUuid".into(),
            });
        }
        self.check_revision(plan.expected_revision)?;
        if plan.before != self.state.content {
            return Err(EditError::RevisionConflict);
        }
        self.check_content(&plan.after)?;
        for version in plan.before.asset_refs.iter().chain(&plan.after.asset_refs) {
            if !plan.required_asset_versions.contains(version) {
                return Err(EditError::InvalidInput {
                    field: "requiredAssetVersions".into(),
                });
            }
        }
        if plan.after == self.state.content {
            return Ok(self.projection(false));
        }
        let revision = self.next_revision()?;
        // Complete all fallible policy checks before mutating authoritative data.
        self.state.undo.push(DocumentHistoryEntry {
            kind: plan.kind,
            before: plan.before,
            after: plan.after.clone(),
        });
        self.state.content = plan.after;
        self.state.content_revision = revision;
        self.state.redo.clear();
        Ok(self.projection(true))
    }

    pub fn undo(&mut self, expected: Revision) -> Result<CommitProjection, EditError> {
        self.check_editable()?;
        self.check_revision(expected)?;
        let entry = self.state.undo.last().ok_or(EditError::NoUndo)?;
        if entry.after != self.state.content {
            return Err(EditError::RevisionConflict);
        }
        let revision = self.next_revision()?;
        let entry = self
            .state
            .undo
            .pop()
            .expect("history inspected under exclusive borrow");
        self.state.content = entry.before.clone();
        self.state.content_revision = revision;
        self.state.redo.push(entry);
        Ok(self.projection(true))
    }

    pub fn capture(&self) -> Result<ImmutableDocumentSnapshot, EditError> {
        self.check_editable()?;
        Ok(ImmutableDocumentSnapshot {
            document_uuid: self.state.document_uuid.clone(),
            session_uuid: self.state.session_uuid.clone(),
            revision: self.state.content_revision,
            content: self.state.content.clone(),
        })
    }

    pub fn acknowledge_formal_save(
        &mut self,
        captured: Revision,
        digest: &str,
    ) -> Result<SaveProjection, EditError> {
        self.check_ack(captured, digest, self.state.formal_baseline.as_ref())?;
        self.state.formal_baseline = Some(SavedContentBaseline {
            revision: captured,
            semantic_digest: digest.into(),
        });
        Ok(SaveProjection {
            captured_revision: captured,
            dirty: self.dirty(),
        })
    }

    pub fn acknowledge_recovery_save(
        &mut self,
        captured: Revision,
        digest: &str,
    ) -> Result<RecoveryProjection, EditError> {
        self.check_ack(captured, digest, self.state.snapshot_baseline.as_ref())?;
        self.state.snapshot_baseline = Some(SavedContentBaseline {
            revision: captured,
            semantic_digest: digest.into(),
        });
        Ok(RecoveryProjection {
            captured_revision: captured,
            needs_snapshot: self.state.content.semantic_digest != digest,
        })
    }

    fn check_editable(&self) -> Result<(), EditError> {
        match self.state.status {
            SessionStatus::Editing | SessionStatus::Saving => Ok(()),
            SessionStatus::Closed => Err(EditError::Closed),
            SessionStatus::Applying | SessionStatus::RecoveryRequired => Err(EditError::Busy),
        }
    }

    fn check_revision(&self, expected: Revision) -> Result<(), EditError> {
        if expected == self.state.content_revision {
            Ok(())
        } else {
            Err(EditError::RevisionConflict)
        }
    }

    fn next_revision(&self) -> Result<Revision, EditError> {
        self.state
            .content_revision
            .0
            .checked_add(1)
            .map(Revision)
            .ok_or(EditError::RevisionOverflow)
    }

    fn check_content(&self, after: &DocumentContent) -> Result<(), EditError> {
        // Codec owns normalization/hashing. Never accept a contradictory value
        // under the current semantic identity, even from a plain Rust plan.
        if !valid_digest(&after.semantic_digest)
            || (after.semantic_digest == self.state.content.semantic_digest
                && after != &self.state.content)
        {
            Err(EditError::InvalidInput {
                field: "semanticDigest".into(),
            })
        } else {
            Ok(())
        }
    }

    fn check_ack(
        &self,
        captured: Revision,
        digest: &str,
        baseline: Option<&SavedContentBaseline>,
    ) -> Result<(), EditError> {
        self.check_editable()?;
        if !valid_digest(digest) {
            return Err(EditError::InvalidInput {
                field: "semanticDigest".into(),
            });
        }
        if captured.0 > self.state.content_revision.0
            || (captured == self.state.content_revision
                && digest != self.state.content.semantic_digest)
            || baseline.is_some_and(|saved| {
                captured.0 < saved.revision.0
                    || (captured == saved.revision && digest != saved.semantic_digest)
            })
        {
            return Err(EditError::RevisionConflict);
        }
        Ok(())
    }

    fn dirty(&self) -> bool {
        self.state
            .formal_baseline
            .as_ref()
            .map(|saved| saved.semantic_digest != self.state.content.semantic_digest)
            .unwrap_or(true)
    }

    fn projection(&self, changed: bool) -> CommitProjection {
        CommitProjection {
            revision: self.state.content_revision,
            changed,
            dirty: self.dirty(),
            history_depth: self.state.undo.len(),
        }
    }
}

fn valid_digest(digest: &str) -> bool {
    digest.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64
            && hex
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    })
}
