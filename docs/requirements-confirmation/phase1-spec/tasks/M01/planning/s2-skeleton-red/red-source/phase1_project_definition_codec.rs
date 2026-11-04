//! Approved M01-S2 codec behavior, isolated from filesystem and production parsing.
use sgenaxis_host::project_definition::*;
use sgenaxis_work::project_definition::*;
fn base() -> ProjectDefinition {
    ProjectDefinition {
        project_uuid: PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),
        definition_revision: DefinitionRevision(0),
        mode: DefinitionMode::Draft,
        approval_refs: vec![],
        legacy_root_keys: vec!["proj_legacy_A".into()],
        draft: DefinitionDraft {
            name: "Local Design".into(),
            purpose: "先保存需求草稿".into(),
            last_saved_step: WizardStep::Delivery,
            delivery_targets: vec![],
            topology: FieldState::Unresolved,
            requirements: vec![],
            preference_source: PreferenceSource::Skip,
            template: None,
            open_decisions: vec!["delivery.form".into(), "technology.framework".into()],
            extensions: match ExtensionValue::Object([].into_iter().collect()) {
                ExtensionValue::Object(o) => o,
                _ => unreachable!(),
            },
        },
    }
}
fn wire() -> serde_json::Value {
    serde_json::from_str("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}").expect("fixture JSON")
}
fn raw(v: &serde_json::Value) -> Vec<u8> {
    serde_json::to_vec(v).expect("fixture serialization")
}
fn invalid(pointer: &str, code: CodecFieldCode) -> DefinitionStoreError {
    DefinitionStoreError::Codec {
        issue: CodecIssue::InvalidField {
            pointer: pointer.into(),
            code,
        },
    }
}
fn check_decode(bytes: &[u8], expected: DefinitionStoreError) {
    assert_eq!(
        decode_definition(bytes),
        Err(expected),
        "product result must match the exact approved error"
    );
}
fn roundtrip(expected: ProjectDefinition, bytes: &[u8]) {
    let before = expected.clone();
    assert_eq!(
        decode_definition(bytes),
        Ok(expected.clone()),
        "decode exact independent domain oracle"
    );
    let encoded = encode_definition(&expected);
    assert!(encoded.is_ok(), "encoding valid domain: {encoded:?}");
    let encoded = encoded.unwrap();
    assert_eq!(decode_definition(&encoded), Ok(before.clone()));
    assert_eq!(
        encode_definition(&before),
        Ok(encoded.clone()),
        "deterministic"
    );
    assert_eq!(expected, before, "input untouched");
    assert!(encoded.ends_with(b"\n"));
    assert!(!encoded.starts_with(&[239, 187, 191]));
}

#[test]
fn t001_basics() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Basics,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"basics\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t001_delivery() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t001_topology() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Topology,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"topology\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t001_requirements() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Requirements,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"requirements\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t001_technology_ui() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::TechnologyUi,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"technology_ui\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t001_preview() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Preview,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"preview\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t002_draft() {
    let d = ProjectDefinition {
        project_uuid: PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),
        definition_revision: DefinitionRevision(0),
        mode: DefinitionMode::Draft,
        approval_refs: vec![],
        legacy_root_keys: vec!["proj_legacy_A".into()],
        draft: DefinitionDraft {
            name: "Local Design".into(),
            purpose: "先保存需求草稿".into(),
            last_saved_step: WizardStep::Delivery,
            delivery_targets: vec![],
            topology: FieldState::Unresolved,
            requirements: vec![],
            preference_source: PreferenceSource::Skip,
            template: None,
            open_decisions: vec!["delivery.form".into(), "technology.framework".into()],
            extensions: match ExtensionValue::Object([].into_iter().collect()) {
                ExtensionValue::Object(o) => o,
                _ => unreachable!(),
            },
        },
    };
    assert!(!missing_generation_requirements(&d).is_empty());
    roundtrip(d,"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t003_defined() {
    let d = ProjectDefinition {
        project_uuid: PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),
        definition_revision: DefinitionRevision(0),
        mode: DefinitionMode::Defined,
        approval_refs: vec![],
        legacy_root_keys: vec!["proj_legacy_A".into()],
        draft: DefinitionDraft {
            name: "Local Design".into(),
            purpose: "先保存需求草稿".into(),
            last_saved_step: WizardStep::Delivery,
            delivery_targets: vec![],
            topology: FieldState::Unresolved,
            requirements: vec![],
            preference_source: PreferenceSource::Skip,
            template: None,
            open_decisions: vec!["delivery.form".into(), "technology.framework".into()],
            extensions: match ExtensionValue::Object([].into_iter().collect()) {
                ExtensionValue::Object(o) => o,
                _ => unreachable!(),
            },
        },
    };
    assert!(!missing_generation_requirements(&d).is_empty());
    roundtrip(d,"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"defined\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t004_revision() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t005_revision() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(18446744073709551615),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"18446744073709551615\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t006_invalid_revision() {
    let mut v = wire();
    v["definitionRevision"] = serde_json::json!("01");
    check_decode(
        &raw(&v),
        invalid("/definitionRevision", CodecFieldCode::InvalidRevision),
    );
}

#[test]
fn t007_invalid_revision() {
    let mut v = wire();
    v["definitionRevision"] = serde_json::json!("+1");
    check_decode(
        &raw(&v),
        invalid("/definitionRevision", CodecFieldCode::InvalidRevision),
    );
}

#[test]
fn t008_invalid_revision() {
    let mut v = wire();
    v["definitionRevision"] = serde_json::json!("-1");
    check_decode(
        &raw(&v),
        invalid("/definitionRevision", CodecFieldCode::InvalidRevision),
    );
}

#[test]
fn t009_invalid_revision() {
    let mut v = wire();
    v["definitionRevision"] = serde_json::json!("18446744073709551616");
    check_decode(
        &raw(&v),
        invalid("/definitionRevision", CodecFieldCode::InvalidRevision),
    );
}

#[test]
fn t010_invalid_revision() {
    let mut v = wire();
    v["definitionRevision"] = serde_json::json!(1);
    check_decode(
        &raw(&v),
        invalid("/definitionRevision", CodecFieldCode::InvalidRevision),
    );
}

#[test]
fn t011_field_state() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t012_field_state() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Tentative("".into()),requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"tentative\", \"value\": \"\"}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t013_field_state() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Confirmed("".into()),requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"confirmed\", \"value\": \"\"}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t014_inconsistent() {
    let mut v = wire();
    v["topology"] = serde_json::json!({"state": "unresolved", "value": "data"});
    check_decode(
        &raw(&v),
        invalid("/topology", CodecFieldCode::InconsistentFieldState),
    );
}

#[test]
fn t015_inconsistent() {
    let mut v = wire();
    v["topology"] = serde_json::json!({"state": "tentative", "value": null});
    check_decode(
        &raw(&v),
        invalid("/topology", CodecFieldCode::InconsistentFieldState),
    );
}

#[test]
fn t016_inconsistent() {
    let mut v = wire();
    v["topology"] = serde_json::json!({"state": "confirmed", "value": null});
    check_decode(
        &raw(&v),
        invalid("/topology", CodecFieldCode::InconsistentFieldState),
    );
}

#[test]
fn t017_null() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![DeliveryTarget{id:"11111111-1111-4111-8111-111111111111".into(),form:FieldState::Unresolved,platform:FieldState::Unresolved,host:FieldState::Unresolved,host_version:FieldState::Unresolved,language:FieldState::Unresolved,framework:FieldState::Unresolved,toolchain:vec![],has_ui:None}],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t017_false() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![DeliveryTarget{id:"11111111-1111-4111-8111-111111111111".into(),form:FieldState::Unresolved,platform:FieldState::Unresolved,host:FieldState::Unresolved,host_version:FieldState::Unresolved,language:FieldState::Unresolved,framework:FieldState::Unresolved,toolchain:vec![],has_ui:Some(false)}],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": false}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t018_references() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec!["approval-data-only".into()],legacy_root_keys:vec!["opaque-id".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:Some(TemplateReference{id:"base".into(),version:"1".into(),source_digest:"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa".into()}),open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [\"approval-data-only\"], \"legacyRootKeys\": [\"opaque-id\"], \"extensions\": {}}".as_bytes());
}

#[test]
fn t019_number() {
    let mut d = base();
    d.draft
        .extensions
        .insert("number".into(), ExtensionValue::Number("-0".into()));
    roundtrip(d.clone(),"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {\"number\":-0}}".as_bytes());
    let b = encode_definition(&d).unwrap();
    assert!(String::from_utf8(b).unwrap().contains("-0"));
}

#[test]
fn t020_number() {
    let mut d = base();
    d.draft
        .extensions
        .insert("number".into(), ExtensionValue::Number("1.00".into()));
    roundtrip(d.clone(),"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {\"number\":1.00}}".as_bytes());
    let b = encode_definition(&d).unwrap();
    assert!(String::from_utf8(b).unwrap().contains("1.00"));
}

#[test]
fn t021_number() {
    let mut d = base();
    d.draft
        .extensions
        .insert("number".into(), ExtensionValue::Number("1E+03".into()));
    roundtrip(d.clone(),"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {\"number\":1E+03}}".as_bytes());
    let b = encode_definition(&d).unwrap();
    assert!(String::from_utf8(b).unwrap().contains("1E+03"));
}

#[test]
fn t022_number() {
    let mut d = base();
    d.draft.extensions.insert(
        "number".into(),
        ExtensionValue::Number("18446744073709551616".into()),
    );
    roundtrip(d.clone(),"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {\"number\":18446744073709551616}}".as_bytes());
    let b = encode_definition(&d).unwrap();
    assert!(String::from_utf8(b)
        .unwrap()
        .contains("18446744073709551616"));
}

#[test]
fn t023_number() {
    let mut d = base();
    d.draft.extensions.insert(
        "number".into(),
        ExtensionValue::Number("0.123456789012345678901234567890".into()),
    );
    roundtrip(d.clone(),"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {\"number\":0.123456789012345678901234567890}}".as_bytes());
    let b = encode_definition(&d).unwrap();
    assert!(String::from_utf8(b)
        .unwrap()
        .contains("0.123456789012345678901234567890"));
}

#[test]
fn t024_tree() {
    roundtrip(ProjectDefinition{project_uuid:PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),definition_revision:DefinitionRevision(0),mode:DefinitionMode::Draft,approval_refs:vec![],legacy_root_keys:vec!["proj_legacy_A".into()],draft:DefinitionDraft{name:"Local Design".into(),purpose:"先保存需求草稿".into(),last_saved_step:WizardStep::Delivery,delivery_targets:vec![],topology:FieldState::Unresolved,requirements:vec![],preference_source:PreferenceSource::Skip,template:None,open_decisions:vec!["delivery.form".into(),"technology.framework".into()],extensions:match ExtensionValue::Object([("$serde_json::private::Number".into(),ExtensionValue::String("ordinary".into())),("a".into(),ExtensionValue::Object([("y".into(),ExtensionValue::Bool(false))].into_iter().collect())),("z".into(),ExtensionValue::Array(vec![ExtensionValue::Bool(true),ExtensionValue::Null,ExtensionValue::Object([("x".into(),ExtensionValue::String("維持順序".into()))].into_iter().collect())]))].into_iter().collect()){ExtensionValue::Object(o)=>o,_=>unreachable!()}}},"{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {\"$serde_json::private::Number\": \"ordinary\", \"z\": [true, null, {\"x\": \"維持順序\"}], \"a\": {\"y\": false}}}".as_bytes());
}

#[test]
fn t025_root() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}, \"futureRoot\": true}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::UnknownField{pointer:"/futureRoot".into()}});
}

#[test]
fn t026_target() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null, \"future\": true}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::UnknownField{pointer:"/deliveryTargets/0/future".into()}});
}

#[test]
fn t027_template() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\", \"future\": true}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::UnknownField{pointer:"/template/future".into()}});
}

#[test]
fn t028_0() {
    check_decode("{\"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/schema".into()}});
}

#[test]
fn t028_1() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/schemaVersion".into()}});
}

#[test]
fn t028_2() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/projectUuid".into()}});
}

#[test]
fn t028_3() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/definitionRevision".into()}});
}

#[test]
fn t028_4() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/name".into()}});
}

#[test]
fn t028_5() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/purpose".into()}});
}

#[test]
fn t028_6() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/mode".into()}});
}

#[test]
fn t028_7() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/lastSavedStep".into()}});
}

#[test]
fn t028_8() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets".into()}});
}

#[test]
fn t028_9() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/topology".into()}});
}

#[test]
fn t028_10() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/requirements".into()}});
}

#[test]
fn t028_11() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/preferenceSource".into()}});
}

#[test]
fn t028_12() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/template".into()}});
}

#[test]
fn t028_13() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/openDecisions".into()}});
}

#[test]
fn t028_14() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/approvalRefs".into()}});
}

#[test]
fn t028_15() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/legacyRootKeys".into()}});
}

#[test]
fn t028_16() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"]}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/extensions".into()}});
}

#[test]
fn t028_17() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/id".into()}});
}

#[test]
fn t028_18() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/form".into()}});
}

#[test]
fn t028_19() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/platform".into()}});
}

#[test]
fn t028_20() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/host".into()}});
}

#[test]
fn t028_21() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/hostVersion".into()}});
}

#[test]
fn t028_22() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/language".into()}});
}

#[test]
fn t028_23() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/framework".into()}});
}

#[test]
fn t028_24() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/toolchain".into()}});
}

#[test]
fn t028_25() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": []}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/hasUi".into()}});
}

#[test]
fn t028_26() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/form/state".into()}});
}

#[test]
fn t028_27() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\"}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/form/value".into()}});
}

#[test]
fn t028_28() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/platform/state".into()}});
}

#[test]
fn t028_29() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\"}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/platform/value".into()}});
}

#[test]
fn t028_30() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/host/state".into()}});
}

#[test]
fn t028_31() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\"}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/host/value".into()}});
}

#[test]
fn t028_32() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/hostVersion/state".into()}});
}

#[test]
fn t028_33() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\"}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/hostVersion/value".into()}});
}

#[test]
fn t028_34() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/language/state".into()}});
}

#[test]
fn t028_35() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\"}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/language/value".into()}});
}

#[test]
fn t028_36() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/framework/state".into()}});
}

#[test]
fn t028_37() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\"}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/deliveryTargets/0/framework/value".into()}});
}

#[test]
fn t028_38() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/topology/state".into()}});
}

#[test]
fn t028_39() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\"}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/topology/value".into()}});
}

#[test]
fn t028_40() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/requirements/0/id".into()}});
}

#[test]
fn t028_41() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/requirements/0/intent".into()}});
}

#[test]
fn t028_42() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/requirements/0/acceptance".into()}});
}

#[test]
fn t028_43() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": []}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/requirements/0/state".into()}});
}

#[test]
fn t028_44() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"version\": \"1\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/template/id".into()}});
}

#[test]
fn t028_45() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"sourceDigest\": \"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/template/version".into()}});
}

#[test]
fn t028_46() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [{\"form\": {\"state\": \"unresolved\", \"value\": null}, \"platform\": {\"state\": \"unresolved\", \"value\": null}, \"host\": {\"state\": \"unresolved\", \"value\": null}, \"hostVersion\": {\"state\": \"unresolved\", \"value\": null}, \"language\": {\"state\": \"unresolved\", \"value\": null}, \"framework\": {\"state\": \"unresolved\", \"value\": null}, \"id\": \"11111111-1111-4111-8111-111111111111\", \"toolchain\": [], \"hasUi\": null}], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [{\"id\": \"r\", \"intent\": \"\", \"acceptance\": [], \"state\": \"unresolved\"}], \"preferenceSource\": \"skip\", \"template\": {\"id\": \"base\", \"version\": \"1\"}, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:"/template/sourceDigest".into()}});
}

#[test]
fn t029_utf8() {
    let mut b = vec![255];
    b.extend(raw(&wire()));
    check_decode(
        &b,
        DefinitionStoreError::Codec {
            issue: CodecIssue::InvalidUtf8,
        },
    );
}

#[test]
fn t030_bom() {
    let mut b = vec![239, 187, 191];
    b.extend(raw(&wire()));
    check_decode(
        &b,
        DefinitionStoreError::Codec {
            issue: CodecIssue::BomNotAllowed,
        },
    );
}

#[test]
fn t031_grammar() {
    let mut b = raw(&wire());
    b.pop();
    assert!(
        matches!(
            decode_definition(&b),
            Err(DefinitionStoreError::Codec {
                issue: CodecIssue::InvalidJson { .. }
            })
        ),
        "exact grammar classification"
    );
}

#[test]
fn t032_duplicate() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {},\"name\":\"second\"}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::DuplicateKey{pointer:"/name".into()}});
}

#[test]
fn t033_duplicate() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\":{\"plugin\":1,\"plugin\":2}}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::DuplicateKey{pointer:"/extensions/plugin".into()}});
}

#[test]
fn t034_schema() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 2, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::UnsupportedSchema{schema:"eluslot.project-definition".into(),version:"2".into()});
}

#[test]
fn t035_schema() {
    check_decode("{\"schema\": \"other.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes(),DefinitionStoreError::UnsupportedSchema{schema:"other.project-definition".into(),version:"1".into()});
}

#[test]
fn t036_version_unknown() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 2, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}, \"futureRoot\": true}".as_bytes(),DefinitionStoreError::UnsupportedSchema{schema:"eluslot.project-definition".into(),version:"2".into()});
}

#[test]
fn t036_version_duplicate() {
    check_decode("{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 2, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"0\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}, \"futureRoot\": true,\"name\":\"second\"}".as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::DuplicateKey{pointer:"/name".into()}});
}

fn nodes(v: &serde_json::Value) -> usize {
    1 + match v {
        serde_json::Value::Object(o) => o.values().map(nodes).sum(),
        serde_json::Value::Array(a) => a.iter().map(nodes).sum(),
        _ => 0,
    }
}
fn depth(v: &serde_json::Value) -> usize {
    match v {
        serde_json::Value::Object(o) => o.values().map(depth).max().map_or(0, |x| x + 1),
        serde_json::Value::Array(a) => a.iter().map(depth).max().map_or(0, |x| x + 1),
        _ => 0,
    }
}
fn resource(b: &[u8], r: CodecResource) {
    assert!(
        matches!(decode_definition(b),Err(DefinitionStoreError::Codec{issue:CodecIssue::ResourceLimit{resource,..}}) if resource==r),
        "resource guard, not parser/environment failure"
    );
}

#[test]
fn t037_1() {
    let mut v = wire();
    v["name"] = serde_json::json!("設".repeat(1));
    let b = raw(&v);
    let mut d = base();
    d.draft.name = "設".repeat(1);
    assert_eq!(decode_definition(&b), Ok(d));
}

#[test]
fn t037_120() {
    let mut v = wire();
    v["name"] = serde_json::json!("設".repeat(120));
    let b = raw(&v);
    let mut d = base();
    d.draft.name = "設".repeat(120);
    assert_eq!(decode_definition(&b), Ok(d));
}

#[test]
fn t037_121() {
    let mut v = wire();
    v["name"] = serde_json::json!("設".repeat(121));
    let b = raw(&v);
    check_decode(&b, invalid("/name", CodecFieldCode::OutOfRange));
}

#[test]
fn t038_16777215() {
    let mut b = raw(&wire());
    b.resize(16777215, b' ');
    assert_eq!(b.len(), 16777215);
    assert!(serde_json::from_slice::<serde_json::Value>(&b).is_ok());
    assert_eq!(decode_definition(&b), Ok(base()));
}

#[test]
fn t038_16777216() {
    let mut b = raw(&wire());
    b.resize(16777216, b' ');
    assert_eq!(b.len(), 16777216);
    assert!(serde_json::from_slice::<serde_json::Value>(&b).is_ok());
    assert_eq!(decode_definition(&b), Ok(base()));
}

#[test]
fn t038_16777217() {
    let mut b = raw(&wire());
    b.resize(16777217, b' ');
    assert_eq!(b.len(), 16777217);
    assert!(serde_json::from_slice::<serde_json::Value>(&b).is_ok());
    check_decode(
        &b,
        DefinitionStoreError::Codec {
            issue: CodecIssue::InputTooLarge {
                actual_bytes: 16777217,
                limit_bytes: 16777216,
            },
        },
    );
}

#[test]
fn t039_63() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nest":"MARKER"});
    let raw = String::from_utf8(raw(&v)).unwrap().replace(
        "\"MARKER\"",
        &format!("{}{}{}", "[".repeat(63 - 2), "null", "]".repeat(63 - 2)),
    );
    let mut d = base();
    let mut nest = ExtensionValue::Null;
    for _ in 0..63 - 2 {
        nest = ExtensionValue::Array(vec![nest]);
    }
    d.draft.extensions.insert("nest".into(), nest);
    assert_eq!(decode_definition(raw.as_bytes()), Ok(d));
}

#[test]
fn t039_64() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nest":"MARKER"});
    let raw = String::from_utf8(raw(&v)).unwrap().replace(
        "\"MARKER\"",
        &format!("{}{}{}", "[".repeat(64 - 2), "null", "]".repeat(64 - 2)),
    );
    let mut d = base();
    let mut nest = ExtensionValue::Null;
    for _ in 0..64 - 2 {
        nest = ExtensionValue::Array(vec![nest]);
    }
    d.draft.extensions.insert("nest".into(), nest);
    assert_eq!(decode_definition(raw.as_bytes()), Ok(d));
}

#[test]
fn t039_65() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nest":"MARKER"});
    let raw = String::from_utf8(raw(&v)).unwrap().replace(
        "\"MARKER\"",
        &format!("{}{}{}", "[".repeat(65 - 2), "null", "]".repeat(65 - 2)),
    );
    resource(raw.as_bytes(), CodecResource::Depth);
}

#[test]
fn t039_129() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nest":"MARKER"});
    let raw = String::from_utf8(raw(&v)).unwrap().replace(
        "\"MARKER\"",
        &format!("{}{}{}", "[".repeat(129 - 2), "null", "]".repeat(129 - 2)),
    );
    resource(raw.as_bytes(), CodecResource::Depth);
}

#[test]
fn t040_99999() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nodes":[]});
    let extra = 99999 - nodes(&v);
    v["extensions"]["nodes"] = serde_json::json!(vec![serde_json::Value::Null; extra]);
    assert_eq!(nodes(&v), 99999);
    assert!(depth(&v) < 64);
    let b = raw(&v);
    let mut d = base();
    d.draft.extensions.insert(
        "nodes".into(),
        ExtensionValue::Array(vec![ExtensionValue::Null; extra]),
    );
    assert_eq!(decode_definition(&b), Ok(d));
}

#[test]
fn t040_100000() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nodes":[]});
    let extra = 100000 - nodes(&v);
    v["extensions"]["nodes"] = serde_json::json!(vec![serde_json::Value::Null; extra]);
    assert_eq!(nodes(&v), 100000);
    assert!(depth(&v) < 64);
    let b = raw(&v);
    let mut d = base();
    d.draft.extensions.insert(
        "nodes".into(),
        ExtensionValue::Array(vec![ExtensionValue::Null; extra]),
    );
    assert_eq!(decode_definition(&b), Ok(d));
}

#[test]
fn t040_100001() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"nodes":[]});
    let extra = 100001 - nodes(&v);
    v["extensions"]["nodes"] = serde_json::json!(vec![serde_json::Value::Null; extra]);
    assert_eq!(nodes(&v), 100001);
    assert!(depth(&v) < 64);
    let b = raw(&v);
    resource(&b, CodecResource::Nodes);
}

#[test]
fn t041_1048575() {
    let mut v = wire();
    let text = format!("{}x", "界".repeat((1048575 - 1) / 3));
    let text = format!("{}{}", text, "x".repeat(1048575 - text.len()));
    assert_eq!(text.len(), 1048575);
    v["purpose"] = serde_json::json!(text);
    let b = raw(&v);
    let mut d = base();
    d.draft.purpose = v["purpose"].as_str().unwrap().to_owned();
    assert_eq!(decode_definition(&b), Ok(d));
}

#[test]
fn t041_1048576() {
    let mut v = wire();
    let text = format!("{}x", "界".repeat((1048576 - 1) / 3));
    let text = format!("{}{}", text, "x".repeat(1048576 - text.len()));
    assert_eq!(text.len(), 1048576);
    v["purpose"] = serde_json::json!(text);
    let b = raw(&v);
    let mut d = base();
    d.draft.purpose = v["purpose"].as_str().unwrap().to_owned();
    assert_eq!(decode_definition(&b), Ok(d));
}

#[test]
fn t041_1048577() {
    let mut v = wire();
    let text = format!("{}x", "界".repeat((1048577 - 1) / 3));
    let text = format!("{}{}", text, "x".repeat(1048577 - text.len()));
    assert_eq!(text.len(), 1048577);
    v["purpose"] = serde_json::json!(text);
    let b = raw(&v);
    resource(&b, CodecResource::StringBytes);
}

#[test]
fn t042_4095() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"number":"MARKER"});
    let token = "7".repeat(4095);
    assert_eq!(token.len(), 4095);
    assert!(token.bytes().all(|x| x == b'7'));
    let b = String::from_utf8(raw(&v))
        .unwrap()
        .replace("\"MARKER\"", &token);
    let mut d = base();
    d.draft
        .extensions
        .insert("number".into(), ExtensionValue::Number(token));
    assert_eq!(decode_definition(b.as_bytes()), Ok(d));
}

#[test]
fn t042_4096() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"number":"MARKER"});
    let token = "7".repeat(4096);
    assert_eq!(token.len(), 4096);
    assert!(token.bytes().all(|x| x == b'7'));
    let b = String::from_utf8(raw(&v))
        .unwrap()
        .replace("\"MARKER\"", &token);
    let mut d = base();
    d.draft
        .extensions
        .insert("number".into(), ExtensionValue::Number(token));
    assert_eq!(decode_definition(b.as_bytes()), Ok(d));
}

#[test]
fn t042_4097() {
    let mut v = wire();
    v["extensions"] = serde_json::json!({"number":"MARKER"});
    let token = "7".repeat(4097);
    assert_eq!(token.len(), 4097);
    assert!(token.bytes().all(|x| x == b'7'));
    let b = String::from_utf8(raw(&v))
        .unwrap()
        .replace("\"MARKER\"", &token);
    resource(b.as_bytes(), CodecResource::NumberBytes);
}

#[test]
fn t043_16777216() {
    let mut d = base();
    d.draft
        .extensions
        .insert("k00".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k01".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k02".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k03".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k04".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k05".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k06".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k07".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k08".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k09".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k10".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k11".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k12".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k13".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k14".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k15".into(), ExtensionValue::String("x".repeat(1047741)));
    let result = encode_definition(&d);
    assert_eq!(result.as_ref().map(Vec::len), Ok(16777216));
}

#[test]
fn t043_16777217() {
    let mut d = base();
    d.draft
        .extensions
        .insert("k00".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k01".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k02".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k03".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k04".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k05".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k06".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k07".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k08".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k09".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k10".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k11".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k12".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k13".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k14".into(), ExtensionValue::String("x".repeat(1048576)));
    d.draft
        .extensions
        .insert("k15".into(), ExtensionValue::String("x".repeat(1047742)));
    let result = encode_definition(&d);
    assert_eq!(
        result,
        Err(DefinitionStoreError::Codec {
            issue: CodecIssue::OutputTooLarge {
                actual_bytes: 16777217,
                limit_bytes: 16777216
            }
        })
    );
}

#[test]
fn t044_encode_reject() {
    let mut d = base();
    d.draft.name = "   ".into();
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(DefinitionStoreError::InvalidInput {
            field: "name".into(),
            code: DefinitionInputCode::DomainInvalid
        })
    );
    assert_eq!(d, before);
}

#[test]
fn t045_encode_reject() {
    let mut d = base();
    d.project_uuid = PersistentProjectId::candidate("bad");
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(invalid("/projectUuid", CodecFieldCode::InvalidUuid))
    );
    assert_eq!(d, before);
}

#[test]
fn t046_encode_reject() {
    let mut d = base();
    let t = ProjectDefinition {
        project_uuid: PersistentProjectId::candidate("11111111-1111-4111-8111-111111111111"),
        definition_revision: DefinitionRevision(0),
        mode: DefinitionMode::Draft,
        approval_refs: vec![],
        legacy_root_keys: vec!["proj_legacy_A".into()],
        draft: DefinitionDraft {
            name: "Local Design".into(),
            purpose: "先保存需求草稿".into(),
            last_saved_step: WizardStep::Delivery,
            delivery_targets: vec![DeliveryTarget {
                id: "11111111-1111-4111-8111-111111111111".into(),
                form: FieldState::Unresolved,
                platform: FieldState::Unresolved,
                host: FieldState::Unresolved,
                host_version: FieldState::Unresolved,
                language: FieldState::Unresolved,
                framework: FieldState::Unresolved,
                toolchain: vec![],
                has_ui: None,
            }],
            topology: FieldState::Unresolved,
            requirements: vec![],
            preference_source: PreferenceSource::Skip,
            template: None,
            open_decisions: vec!["delivery.form".into(), "technology.framework".into()],
            extensions: match ExtensionValue::Object([].into_iter().collect()) {
                ExtensionValue::Object(o) => o,
                _ => unreachable!(),
            },
        },
    }
    .draft
    .delivery_targets
    .remove(0);
    d.draft.delivery_targets = vec![t.clone(), t];
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(DefinitionStoreError::InvalidInput {
            field: "deliveryTargets[1].id".into(),
            code: DefinitionInputCode::DomainInvalid
        })
    );
    assert_eq!(d, before);
}

#[test]
fn t047_encode_reject() {
    let mut d = base();
    d.draft.requirements = vec![DefinitionRequirement {
        id: " ".into(),
        intent: "".into(),
        acceptance: vec![],
        state: RequirementState::Unresolved,
    }];
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(DefinitionStoreError::InvalidInput {
            field: "requirements[0].id".into(),
            code: DefinitionInputCode::DomainInvalid
        })
    );
    assert_eq!(d, before);
}

#[test]
fn t048_encode_reject() {
    let mut d = base();
    d.draft.template = Some(TemplateReference {
        id: "base".into(),
        version: "1".into(),
        source_digest: "sha256:bad".into(),
    });
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(invalid(
            "/template/sourceDigest",
            CodecFieldCode::InvalidDigest
        ))
    );
    assert_eq!(d, before);
}

#[test]
fn t049_encode_reject() {
    let mut d = base();
    d.legacy_root_keys = vec!["C:\\private\\old-root".into()];
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(invalid(
            "/legacyRootKeys/0",
            CodecFieldCode::InvalidPortableAlias
        ))
    );
    assert_eq!(d, before);
}

#[test]
fn t050_encode_reject() {
    let mut d = base();
    d.draft
        .extensions
        .insert("number".into(), ExtensionValue::Number("01".into()));
    let before = d.clone();
    assert_eq!(
        encode_definition(&d),
        Err(invalid(
            "/extensions/number",
            CodecFieldCode::InvalidNumberToken
        ))
    );
    assert_eq!(d, before);
}

#[test]
fn fixture_health() {
    let v = wire();
    assert_eq!(v["schema"], "eluslot.project-definition");
    assert_eq!(v["definitionRevision"], "0");
    assert_eq!(validate_definition(&base().draft), Ok(()));
    assert!(nodes(&v) < 100000);
    assert!(depth(&v) < 64);
}
