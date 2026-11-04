//! Project-owned preferences, pure v1 schema. No persistence or execution authority.
use serde::{Deserialize, Serialize};
pub const PREFERENCES_PATH: &str = ".sgenaxis/preferences.json";
pub const PREFERENCES_FORMAT: &str = "sgenaxis.project-preferences";
pub const PREFERENCES_VERSION: u32 = 1;
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ProjectPreferences {
    pub format: String,
    pub format_version: u32,
    pub preset_id: PresetId,
    pub model_policy: ModelPolicy,
    pub budget: Budget,
    pub batch: BatchPolicy,
    pub workflow: WorkflowPolicy,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum PresetId {
    Custom,
    Conservative,
    Balanced,
    Throughput,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct ModelPolicy {
    pub allowed_model_ids: Vec<String>,
    pub preferred_model_id: Option<String>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct Budget {
    pub max_input_tokens: Option<u64>,
    pub max_output_tokens: Option<u64>,
    pub max_wall_time_seconds: Option<u64>,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct BatchPolicy {
    pub mode: BatchMode,
    pub max_tasks: u64,
    pub max_concurrent: u64,
    pub on_limit: OnLimit,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum BatchMode {
    Suggest,
}
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum OnLimit {
    Block,
}
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields, rename_all = "camelCase")]
pub struct WorkflowPolicy {
    pub confirm_before_run: bool,
}
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PreferenceError {
    InvalidDocument,
    UnsupportedVersion,
    InvalidPolicy,
    UnknownPreset,
}
/// Parsing never normalizes or rewrites the supplied bytes. All schema levels
/// reject unknown fields; direct deserialization is not a validation shortcut.
pub fn parse_project_preferences(bytes: &[u8]) -> Result<ProjectPreferences, PreferenceError> {
    let preferences: ProjectPreferences =
        serde_json::from_slice(bytes).map_err(|_| PreferenceError::InvalidDocument)?;
    validate(&preferences)?;
    Ok(preferences)
}
pub fn validate(preferences: &ProjectPreferences) -> Result<(), PreferenceError> {
    use std::collections::BTreeSet;
    if preferences.format != PREFERENCES_FORMAT {
        return Err(PreferenceError::InvalidDocument);
    }
    if preferences.format_version != PREFERENCES_VERSION {
        return Err(PreferenceError::UnsupportedVersion);
    }
    let mut seen = BTreeSet::new();
    for id in &preferences.model_policy.allowed_model_ids {
        if id.trim().is_empty() || !seen.insert(id) {
            return Err(PreferenceError::InvalidPolicy);
        }
    }
    if preferences
        .model_policy
        .preferred_model_id
        .as_ref()
        .is_some_and(|id| !seen.contains(id))
    {
        return Err(PreferenceError::InvalidPolicy);
    }
    for limit in [
        preferences.budget.max_input_tokens,
        preferences.budget.max_output_tokens,
        preferences.budget.max_wall_time_seconds,
    ] {
        if limit == Some(0) {
            return Err(PreferenceError::InvalidPolicy);
        }
    }
    if preferences.batch.max_tasks == 0
        || preferences.batch.max_concurrent == 0
        || preferences.batch.max_concurrent > preferences.batch.max_tasks
    {
        return Err(PreferenceError::InvalidPolicy);
    }
    Ok(())
}
/// Returns an owned draft. No model is invented; null budgets are unconfigured.
/// v1 supports suggestion-only mode: this schema cannot enable automatic runs.
pub fn preset(id: &str) -> Result<ProjectPreferences, PreferenceError> {
    let (preset_id, max_tasks, max_concurrent) = match id {
        "conservative" => (PresetId::Conservative, 1, 1),
        "balanced" => (PresetId::Balanced, 4, 2),
        "throughput" => (PresetId::Throughput, 8, 4),
        _ => return Err(PreferenceError::UnknownPreset),
    };
    Ok(ProjectPreferences {
        format: PREFERENCES_FORMAT.into(),
        format_version: PREFERENCES_VERSION,
        preset_id,
        model_policy: ModelPolicy {
            allowed_model_ids: vec![],
            preferred_model_id: None,
        },
        budget: Budget {
            max_input_tokens: None,
            max_output_tokens: None,
            max_wall_time_seconds: None,
        },
        batch: BatchPolicy {
            mode: BatchMode::Suggest,
            max_tasks,
            max_concurrent,
            on_limit: OnLimit::Block,
        },
        workflow: WorkflowPolicy {
            confirm_before_run: true,
        },
    })
}
