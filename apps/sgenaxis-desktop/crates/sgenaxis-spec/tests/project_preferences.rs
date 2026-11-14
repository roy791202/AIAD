use serde_json::{json, Value};
use sgenaxis_spec::project_preferences::*;
fn fixture() -> Value {
    json!({"format":"sgenaxis.project-preferences","formatVersion":1,"presetId":"custom",
        "modelPolicy":{"allowedModelIds":[],"preferredModelId":null},
        "budget":{"maxInputTokens":null,"maxOutputTokens":null,"maxWallTimeSeconds":null},
        "batch":{"mode":"suggest","maxTasks":1,"maxConcurrent":1,"onLimit":"block"},
        "workflow":{"confirmBeforeRun":true}})
}
fn parse(v: &Value) -> Result<ProjectPreferences, PreferenceError> {
    parse_project_preferences(&serde_json::to_vec(v).unwrap())
}
#[test]
fn unconfigured_policy_is_preserved_without_invented_model_or_budget() {
    let p = parse(&fixture()).unwrap();
    assert!(p.model_policy.allowed_model_ids.is_empty());
    assert_eq!(p.model_policy.preferred_model_id, None);
    assert_eq!(p.budget.max_input_tokens, None);
    assert_eq!(p.budget.max_output_tokens, None);
    assert_eq!(p.budget.max_wall_time_seconds, None);
    assert_eq!(p.batch.mode, BatchMode::Suggest);
    assert!(p.workflow.confirm_before_run);
    assert_eq!(PREFERENCES_PATH, ".sgenaxis/preferences.json");
}
#[test]
fn presets_have_approved_limits_and_independent_custom_copies() {
    for (id, tasks, concurrency) in [
        ("conservative", 1, 1),
        ("balanced", 4, 2),
        ("throughput", 8, 4),
    ] {
        let p = preset(id).unwrap();
        assert_eq!(
            (p.batch.max_tasks, p.batch.max_concurrent),
            (tasks, concurrency)
        );
        assert_eq!(validate(&p), Ok(()));
        assert!(p.model_policy.allowed_model_ids.is_empty());
        assert_eq!(p.budget.max_input_tokens, None);
        assert_eq!(p.budget.max_output_tokens, None);
        assert_eq!(p.budget.max_wall_time_seconds, None);
        assert_eq!(p.batch.mode, BatchMode::Suggest);
        assert!(p.workflow.confirm_before_run);
        let mut copy = p.clone();
        copy.preset_id = PresetId::Custom;
        copy.batch.max_tasks = 9;
        assert_eq!(preset(id).unwrap(), p);
        assert_ne!(copy, p);
    }
}
#[test]
fn unknown_preset_is_not_silently_substituted() {
    assert_eq!(preset("missing"), Err(PreferenceError::UnknownPreset));
}
#[test]
fn accepts_explicit_models_and_positive_budgets_without_normalizing_source() {
    let mut f = fixture();
    f["modelPolicy"] =
        json!({"allowedModelIds":["Model-A","Model-B"],"preferredModelId":"Model-B"});
    f["budget"] = json!({"maxInputTokens":1,"maxOutputTokens":u64::MAX,"maxWallTimeSeconds":2});
    let bytes = serde_json::to_vec_pretty(&f).unwrap();
    let before = bytes.clone();
    let p = parse_project_preferences(&bytes).unwrap();
    assert_eq!(bytes, before);
    assert_eq!(
        p.model_policy.preferred_model_id.as_deref(),
        Some("Model-B")
    );
    assert_eq!(p.budget.max_output_tokens, Some(u64::MAX));
    assert_eq!(serde_json::to_value(&p).unwrap(), f);
}
#[test]
fn invalid_models_and_preferred_membership_are_rejected() {
    for policy in [
        json!({"allowedModelIds":["a","a"],"preferredModelId":null}),
        json!({"allowedModelIds":[" "],"preferredModelId":null}),
        json!({"allowedModelIds":["a"],"preferredModelId":"b"}),
        json!({"allowedModelIds":[],"preferredModelId":""}),
    ] {
        let mut f = fixture();
        f["modelPolicy"] = policy;
        assert_eq!(parse(&f), Err(PreferenceError::InvalidPolicy));
    }
}
#[test]
fn zero_limits_and_concurrency_above_batch_are_rejected() {
    for (field, value) in [("maxTasks", 0), ("maxConcurrent", 0), ("maxConcurrent", 2)] {
        let mut f = fixture();
        f["batch"][field] = json!(value);
        assert_eq!(parse(&f), Err(PreferenceError::InvalidPolicy));
    }
    for field in ["maxInputTokens", "maxOutputTokens", "maxWallTimeSeconds"] {
        let mut f = fixture();
        f["budget"][field] = json!(0);
        assert_eq!(parse(&f), Err(PreferenceError::InvalidPolicy));
    }
}
#[test]
fn negative_fractional_overflow_and_wrong_types_are_rejected() {
    for value in [json!(-1), json!(1.5), json!("100"), json!(true)] {
        let mut f = fixture();
        f["budget"]["maxInputTokens"] = value;
        assert_eq!(parse(&f), Err(PreferenceError::InvalidDocument));
    }
    let text = serde_json::to_string(&fixture()).unwrap().replace(
        "\"maxInputTokens\":null",
        "\"maxInputTokens\":18446744073709551616",
    );
    assert_eq!(
        parse_project_preferences(text.as_bytes()),
        Err(PreferenceError::InvalidDocument)
    );
}
#[test]
fn unknown_fields_at_every_level_including_secrets_are_rejected() {
    for key in ["", "modelPolicy", "budget", "batch", "workflow"] {
        let mut f = fixture();
        if key.is_empty() {
            f["token"] = json!("must-not-import")
        } else {
            f[key]["token"] = json!("must-not-import")
        }
        assert_eq!(parse(&f), Err(PreferenceError::InvalidDocument));
    }
}
#[test]
fn unknown_format_version_mode_and_missing_required_data_are_rejected() {
    let mut f = fixture();
    f["formatVersion"] = json!(2);
    assert_eq!(parse(&f), Err(PreferenceError::UnsupportedVersion));
    let mut f = fixture();
    f["format"] = json!("other");
    assert!(parse(&f).is_err());
    let mut f = fixture();
    f["batch"]["mode"] = json!("automatic");
    assert_eq!(parse(&f), Err(PreferenceError::InvalidDocument));
    let mut f = fixture();
    f.as_object_mut().unwrap().remove("budget");
    assert_eq!(parse(&f), Err(PreferenceError::InvalidDocument));
}
#[test]
fn invalid_text_and_duplicate_json_keys_are_rejected() {
    for bytes in [&b""[..], &b"{"[..], &b"null"[..], &b"[]"[..], &[0xff][..]] {
        assert_eq!(
            parse_project_preferences(bytes),
            Err(PreferenceError::InvalidDocument)
        );
    }
    let text = serde_json::to_string(&fixture())
        .unwrap()
        .replacen("{", "{\"formatVersion\":1,", 1);
    assert_eq!(
        parse_project_preferences(text.as_bytes()),
        Err(PreferenceError::InvalidDocument)
    );
}
#[test]
fn direct_struct_validation_cannot_bypass_policy_checks() {
    let mut p: ProjectPreferences = serde_json::from_value(fixture()).unwrap();
    assert_eq!(validate(&p), Ok(()));
    p.format_version = 99;
    assert_eq!(validate(&p), Err(PreferenceError::UnsupportedVersion));
    p.format_version = 1;
    p.batch.max_tasks = 0;
    assert_eq!(validate(&p), Err(PreferenceError::InvalidPolicy));
}
