//! M02-S1 approved C policy: immutable generation planning, without rendering/IO.
//!
//! HOST authenticates approval and raw-byte digests before mapping these values.
//! Candidate structs are not authorization. Both operations are pure, take only
//! immutable inputs and must not persist definitions, render templates or use IO.
//! HOST owns evidence authentication and any later publication transaction.

use crate::project_definition::{
    DefinitionRevision, FieldPath, ProjectDefinition, TemplateReference,
};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct TargetCapability {
    pub form: String,
    pub platform: String,
    pub language: String,
    pub framework: String,
    pub has_ui: bool,
}

/// Typed discriminant of the two approved artifact-intent products.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ArtifactProduct {
    Program,
    UiUx,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ArtifactIntent {
    pub relative_path: String,
    pub product: ArtifactProduct,
    pub template_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationTemplateContract {
    pub template_ref: TemplateReference,
    pub target: TargetCapability,
    pub artifacts: Vec<ArtifactIntent>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationBinding {
    pub project_uuid: String,
    pub definition_revision: DefinitionRevision,
    pub definition_digest: String,
    pub target_id: String,
    pub template_ref: TemplateReference,
    pub approval_digest: String,
    pub base_activation_digest: Option<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationPolicyContext {
    pub binding: GenerationBinding,
    pub verified_approval_refs: Vec<String>,
    pub required_approvals_satisfied: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenerationPlan {
    pub binding: GenerationBinding,
    pub artifact_intents: Vec<ArtifactIntent>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GenerationDecision {
    /// Action value only; M01 owns any actual definition save.
    SaveDefinitionOnly {
        missing: Vec<FieldPath>,
    },
    Prepared {
        plan: GenerationPlan,
    },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GenerationPlanError {
    InvalidInput { field: FieldPath, reason: String },
    UnsupportedTarget { target_id: String },
    TemplateMismatch { field: FieldPath },
    ApprovalMismatch { field: FieldPath },
    InvalidArtifactPath { path: String, reason: String },
    DuplicateArtifact { path: String },
    StaleBinding { field: FieldPath },
}

/// Validate structure first, then return sorted/deduplicated missing decisions,
/// or a deterministic dual-product plan. No IO, hashing/authentication or render.
pub fn prepare_generation(
    definition: &ProjectDefinition,
    template: &GenerationTemplateContract,
    context: &GenerationPolicyContext,
) -> Result<GenerationDecision, GenerationPlanError> {
    use crate::project_definition::{
        missing_generation_requirements, validate_definition, DefinitionError, RequirementState,
    };
    if !valid_uuid(definition.project_uuid.as_str())
        || definition.project_uuid.as_str() != context.binding.project_uuid
    {
        return Err(invalid(
            "projectUuid",
            "invalid or mismatched project identity",
        ));
    }
    if definition.definition_revision != context.binding.definition_revision {
        return Err(invalid(
            "definitionRevision",
            "definition revision does not match binding",
        ));
    }
    if let Err(DefinitionError::InvalidInput { field }) = validate_definition(&definition.draft) {
        return Err(invalid(&field, "invalid definition structure"));
    }
    if definition.draft.name.len() > 1024 || definition.draft.purpose.len() > 16384 {
        return Err(invalid("definition", "definition text byte limit exceeded"));
    }
    if !valid_uuid(&context.binding.target_id) {
        return Err(invalid("target_id", "invalid target identity"));
    }
    for (field, value) in [
        (
            "definition_digest",
            context.binding.definition_digest.as_str(),
        ),
        ("approval_digest", context.binding.approval_digest.as_str()),
        (
            "template.source_digest",
            template.template_ref.source_digest.as_str(),
        ),
        (
            "binding.template_ref.source_digest",
            context.binding.template_ref.source_digest.as_str(),
        ),
    ] {
        validate_digest(field, value)?;
    }
    if let Some(digest) = &context.binding.base_activation_digest {
        validate_digest("base_activation_digest", digest)?;
    }
    if template.template_ref.id.trim().is_empty() || template.template_ref.version.trim().is_empty()
    {
        return Err(invalid(
            "template_ref",
            "template identity and version are required",
        ));
    }
    compare_template(&template.template_ref, &context.binding.template_ref)?;
    if let Some(selected) = &definition.draft.template {
        compare_template(&template.template_ref, selected)?;
    }
    let selected = definition
        .draft
        .delivery_targets
        .iter()
        .find(|target| target.id == context.binding.target_id);
    if !definition.draft.delivery_targets.is_empty() && selected.is_none() {
        return Err(invalid("target_id", "target is not in this definition"));
    }
    validate_artifacts(&template.artifacts)?;
    if context.required_approvals_satisfied && !definition.approval_refs.is_empty() {
        let declared: std::collections::BTreeSet<_> = definition.approval_refs.iter().collect();
        let verified: std::collections::BTreeSet<_> =
            context.verified_approval_refs.iter().collect();
        if declared != verified {
            return Err(GenerationPlanError::ApprovalMismatch {
                field: "approvalRefs".into(),
            });
        }
    }
    let mut missing = missing_generation_requirements(definition);
    if definition.draft.template.is_none() {
        missing.push("template".into());
    }
    if definition.draft.requirements.is_empty() {
        missing.push("requirements".into());
    }
    for (i, requirement) in definition.draft.requirements.iter().enumerate() {
        if requirement.state != RequirementState::Confirmed {
            missing.push(format!("requirements[{i}].state"));
        }
        if requirement.intent.trim().is_empty() {
            missing.push(format!("requirements[{i}].intent"));
        }
        if requirement.acceptance.is_empty()
            || requirement.acceptance.iter().any(|a| a.trim().is_empty())
        {
            missing.push(format!("requirements[{i}].acceptance"));
        }
    }
    for (i, decision) in definition.draft.open_decisions.iter().enumerate() {
        if decision.trim().is_empty() {
            return Err(invalid(
                &format!("openDecisions[{i}]"),
                "missing decision must identify its field",
            ));
        }
        missing.push(decision.clone());
    }
    if !context.required_approvals_satisfied || context.verified_approval_refs.is_empty() {
        missing.push("approvalRefs".into());
    }
    missing.sort();
    missing.dedup();
    if !missing.is_empty() {
        return Ok(GenerationDecision::SaveDefinitionOnly { missing });
    }
    let target = selected.ok_or_else(|| invalid("target_id", "target selection is required"))?;
    let supported = template.target.form == "desktop"
        && template.target.platform == "windows-x64"
        && template.target.language == "rust"
        && template.target.framework == "tauri2+vanilla"
        && template.target.has_ui;
    use crate::project_definition::FieldState;
    let matches = |field: &FieldState<String>, expected: &str| matches!(field, FieldState::Confirmed(value) if value == expected);
    if !supported
        || !matches(&target.form, &template.target.form)
        || !matches(&target.platform, &template.target.platform)
        || !matches(&target.language, &template.target.language)
        || !matches(&target.framework, &template.target.framework)
        || target.has_ui != Some(template.target.has_ui)
    {
        return Err(GenerationPlanError::UnsupportedTarget {
            target_id: target.id.clone(),
        });
    }
    let mut artifact_intents = template.artifacts.clone();
    artifact_intents.sort_by(|a, b| a.relative_path.cmp(&b.relative_path));
    Ok(GenerationDecision::Prepared {
        plan: GenerationPlan {
            binding: context.binding.clone(),
            artifact_intents,
        },
    })
}

/// Compare every immutable binding field; a mismatch reports StaleBinding.
/// This validates value freshness, not the authenticity of HOST evidence.
pub fn validate_plan_binding(
    plan: &GenerationPlan,
    current: &GenerationBinding,
) -> Result<(), GenerationPlanError> {
    let old = &plan.binding;
    let mismatches = [
        ("project_uuid", old.project_uuid != current.project_uuid),
        (
            "definition_revision",
            old.definition_revision != current.definition_revision,
        ),
        (
            "definition_digest",
            old.definition_digest != current.definition_digest,
        ),
        ("target_id", old.target_id != current.target_id),
        (
            "template_ref.id",
            old.template_ref.id != current.template_ref.id,
        ),
        (
            "template_ref.version",
            old.template_ref.version != current.template_ref.version,
        ),
        (
            "template_ref.source_digest",
            old.template_ref.source_digest != current.template_ref.source_digest,
        ),
        (
            "approval_digest",
            old.approval_digest != current.approval_digest,
        ),
        (
            "base_activation_digest",
            old.base_activation_digest != current.base_activation_digest,
        ),
    ];
    if let Some((field, _)) = mismatches.iter().find(|(_, changed)| *changed) {
        return Err(GenerationPlanError::StaleBinding {
            field: (*field).into(),
        });
    }
    Ok(())
}

fn invalid(field: &str, reason: &str) -> GenerationPlanError {
    GenerationPlanError::InvalidInput {
        field: field.into(),
        reason: reason.into(),
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
fn validate_digest(field: &str, value: &str) -> Result<(), GenerationPlanError> {
    if value.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64
            && hex
                .bytes()
                .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(&c))
    }) {
        Ok(())
    } else {
        Err(invalid(field, "expected lowercase SHA-256 digest"))
    }
}
fn compare_template(
    expected: &TemplateReference,
    actual: &TemplateReference,
) -> Result<(), GenerationPlanError> {
    for (field, different) in [
        ("template_ref.id", expected.id != actual.id),
        ("template_ref.version", expected.version != actual.version),
        (
            "template_ref.source_digest",
            expected.source_digest != actual.source_digest,
        ),
    ] {
        if different {
            return Err(GenerationPlanError::TemplateMismatch {
                field: field.into(),
            });
        }
    }
    Ok(())
}
fn validate_path(path: &str) -> Result<(), GenerationPlanError> {
    let bad = |reason: &str| GenerationPlanError::InvalidArtifactPath {
        path: path.into(),
        reason: reason.into(),
    };
    if path.is_empty() || path.len() > 240 || !path.is_ascii() {
        return Err(bad("expected 1..240 ASCII path bytes"));
    }
    let components: Vec<_> = path.split('/').collect();
    if components.len() > 16 {
        return Err(bad("too many path components"));
    }
    for part in components {
        if part.is_empty()
            || part.len() > 64
            || matches!(part, "." | "..")
            || part.ends_with('.')
            || !part
                .bytes()
                .all(|c| c.is_ascii_alphanumeric() || b"_-.".contains(&c))
        {
            return Err(bad("invalid path component"));
        }
        let upper = part.split('.').next().unwrap_or("").to_ascii_uppercase();
        let reserved = matches!(upper.as_str(), "CON" | "PRN" | "AUX" | "NUL")
            || ["COM", "LPT"].iter().any(|prefix| {
                upper
                    .strip_prefix(prefix)
                    .is_some_and(|s| s.len() == 1 && matches!(s.as_bytes()[0], b'1'..=b'9'))
            });
        if reserved {
            return Err(bad("reserved Windows path component"));
        }
    }
    Ok(())
}
fn validate_artifacts(artifacts: &[ArtifactIntent]) -> Result<(), GenerationPlanError> {
    if artifacts.len() < 2
        || artifacts.len() > 128
        || !artifacts
            .iter()
            .any(|a| a.product == ArtifactProduct::Program)
        || !artifacts.iter().any(|a| a.product == ArtifactProduct::UiUx)
    {
        return Err(invalid(
            "artifacts",
            "expected 2..128 intents including both products",
        ));
    }
    let mut paths = Vec::new();
    for artifact in artifacts {
        validate_path(&artifact.relative_path)?;
        validate_path(&artifact.template_key)?;
        paths.push((
            artifact.relative_path.to_ascii_lowercase(),
            &artifact.relative_path,
        ));
    }
    paths.sort();
    // A sibling such as `a.ext` may sort between the file `a` and `a/child`.
    // Compare every earlier path, not only adjacent entries (at most 128 files).
    for (i, path) in paths.iter().enumerate() {
        if paths[..i]
            .iter()
            .any(|previous| previous.0 == path.0 || path.0.starts_with(&(previous.0.clone() + "/")))
        {
            return Err(GenerationPlanError::DuplicateArtifact {
                path: path.1.clone(),
            });
        }
    }
    Ok(())
}
