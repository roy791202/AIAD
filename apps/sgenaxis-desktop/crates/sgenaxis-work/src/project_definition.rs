//! M01-S1 pure project-definition policy; no persistence or generation runtime.
//!
//! Data constructors only carry candidate values; they do not validate, approve,
//! persist, migrate identities, or generate artifacts. Operation boundaries must
//! validate them through the policy functions below. No runtime wiring.

use std::collections::BTreeMap;

pub const PROJECT_DEFINITION_SCHEMA: &str = "eluslot.project-definition";
pub const PROJECT_DEFINITION_VERSION: u32 = 1;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PersistentProjectId(String);

impl PersistentProjectId {
    /// Structural input seam for trusted codec mapping and isolated fixtures.
    /// A candidate is not evidence of a valid identity or mutation permission.
    pub fn candidate(raw: impl Into<String>) -> Self {
        Self(raw.into())
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct DefinitionRevision(pub u64);

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FieldState<T> {
    Unresolved,
    Tentative(T),
    Confirmed(T),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum WizardStep {
    Basics,
    Delivery,
    Topology,
    Requirements,
    TechnologyUi,
    Preview,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum DefinitionMode {
    Draft,
    Defined,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PreferenceSource {
    Skip,
    Preset,
    ImportedCopy,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DeliveryTarget {
    pub id: String,
    pub form: FieldState<String>,
    pub platform: FieldState<String>,
    pub host: FieldState<String>,
    pub host_version: FieldState<String>,
    pub language: FieldState<String>,
    pub framework: FieldState<String>,
    pub toolchain: Vec<String>,
    pub has_ui: Option<bool>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RequirementState {
    Unresolved,
    Tentative,
    Confirmed,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DefinitionRequirement {
    pub id: String,
    pub intent: String,
    pub acceptance: Vec<String>,
    pub state: RequirementState,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TemplateReference {
    pub id: String,
    pub version: String,
    pub source_digest: String,
}

/// Framework-neutral extension data. Number text preserves the codec's value
/// without introducing serde/JSON or floating-point policy into WORK.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ExtensionValue {
    Null,
    Bool(bool),
    Number(String),
    String(String),
    Array(Vec<ExtensionValue>),
    Object(BTreeMap<String, ExtensionValue>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DefinitionDraft {
    pub name: String,
    pub purpose: String,
    pub last_saved_step: WizardStep,
    pub delivery_targets: Vec<DeliveryTarget>,
    pub topology: FieldState<String>,
    pub requirements: Vec<DefinitionRequirement>,
    pub preference_source: PreferenceSource,
    pub template: Option<TemplateReference>,
    pub open_decisions: Vec<String>,
    pub extensions: BTreeMap<String, ExtensionValue>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProjectDefinition {
    pub project_uuid: PersistentProjectId,
    pub definition_revision: DefinitionRevision,
    pub draft: DefinitionDraft,
    pub mode: DefinitionMode,
    pub approval_refs: Vec<String>,
    pub legacy_root_keys: Vec<String>,
}

pub type FieldPath = String;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DefinitionError {
    /// Reserved marker retained for source compatibility; implemented policies do not return it.
    NotReady,
    InvalidInput {
        field: FieldPath,
    },
    RevisionConflict,
    RevisionOverflow,
}

fn invalid(field: impl Into<String>) -> DefinitionError {
    DefinitionError::InvalidInput {
        field: field.into(),
    }
}

fn valid_uuid(value: &str) -> bool {
    let bytes = value.as_bytes();
    bytes.len() == 36
        && bytes[14] == b'4'
        && matches!(bytes[19], b'8' | b'9' | b'a' | b'b')
        && bytes.iter().enumerate().all(|(i, c)| {
            if matches!(i, 8 | 13 | 18 | 23) {
                *c == b'-'
            } else {
                c.is_ascii_digit() || (b'a'..=b'f').contains(c)
            }
        })
}

fn confirmed(value: &FieldState<String>) -> bool {
    matches!(value, FieldState::Confirmed(text) if !text.trim().is_empty())
}

/// Incomplete choices are valid draft data. Structural identity/name conflicts
/// are not; generation completeness is checked separately.
pub fn validate_definition(draft: &DefinitionDraft) -> Result<(), DefinitionError> {
    let name = draft.name.trim();
    let base = name
        .split('.')
        .next()
        .unwrap_or("")
        .trim_end()
        .to_ascii_uppercase();
    let reserved = matches!(base.as_str(), "CON" | "PRN" | "AUX" | "NUL")
        || ["COM", "LPT"].iter().any(|prefix| {
            base.strip_prefix(prefix).is_some_and(|suffix| {
                suffix.chars().count() == 1
                    && suffix
                        .chars()
                        .all(|c| matches!(c, '1'..='9' | '¹' | '²' | '³'))
            })
        });
    if name.is_empty()
        || name.chars().count() > 120
        || matches!(name, "." | "..")
        || name.ends_with('.')
        || name
            .chars()
            .any(|c| c.is_control() || "<>:\"/\\|?*".contains(c))
        || reserved
    {
        return Err(invalid("name"));
    }
    let mut ids = std::collections::BTreeSet::new();
    for (i, target) in draft.delivery_targets.iter().enumerate() {
        if !valid_uuid(&target.id) || !ids.insert(&target.id) {
            return Err(invalid(format!("deliveryTargets[{i}].id")));
        }
    }
    let mut ids = std::collections::BTreeSet::new();
    for (i, requirement) in draft.requirements.iter().enumerate() {
        if requirement.id.trim().is_empty() || !ids.insert(&requirement.id) {
            return Err(invalid(format!("requirements[{i}].id")));
        }
    }
    Ok(())
}

/// Return an updated value without mutating the caller's current snapshot.
/// Changes invalidate its old approval references; only the trusted approval
/// boundary can subsequently resolve evidence for the revised definition.
pub fn apply_definition(
    current: &ProjectDefinition,
    expected: DefinitionRevision,
    draft: DefinitionDraft,
) -> Result<ProjectDefinition, DefinitionError> {
    if !valid_uuid(current.project_uuid.as_str()) {
        return Err(invalid("projectUuid"));
    }
    if expected != current.definition_revision {
        return Err(DefinitionError::RevisionConflict);
    }
    validate_definition(&draft)?;
    let revision = current
        .definition_revision
        .0
        .checked_add(1)
        .ok_or(DefinitionError::RevisionOverflow)?;
    let mut next = current.clone();
    if draft != current.draft {
        next.approval_refs.clear();
        next.mode = DefinitionMode::Draft;
    }
    next.draft = draft;
    next.definition_revision = DefinitionRevision(revision);
    Ok(next)
}

/// Completeness projection only, never evidence authentication or permission to
/// generate. The HOST approval boundary still resolves the actual evidence.
pub fn missing_generation_requirements(def: &ProjectDefinition) -> Vec<FieldPath> {
    let mut missing = Vec::new();
    if !valid_uuid(def.project_uuid.as_str()) {
        missing.push("projectUuid".into());
    }
    if let Err(DefinitionError::InvalidInput { field }) = validate_definition(&def.draft) {
        missing.push(field);
    }
    if def.draft.delivery_targets.is_empty() {
        missing.push("deliveryTargets".into());
    }
    for (i, target) in def.draft.delivery_targets.iter().enumerate() {
        for (field, value) in [
            ("form", &target.form),
            ("platform", &target.platform),
            ("language", &target.language),
            ("framework", &target.framework),
        ] {
            if !confirmed(value) {
                missing.push(format!("deliveryTargets[{i}].{field}"));
            }
        }
        if target.toolchain.is_empty() || target.toolchain.iter().any(|s| s.trim().is_empty()) {
            missing.push(format!("deliveryTargets[{i}].toolchain"));
        }
        if target.has_ui.is_none() {
            missing.push(format!("deliveryTargets[{i}].hasUi"));
        }
    }
    if !confirmed(&def.draft.topology) {
        missing.push("topology".into());
    }
    if def.approval_refs.is_empty() || def.approval_refs.iter().any(|s| s.trim().is_empty()) {
        missing.push("approvalRefs".into());
    }
    missing
}
