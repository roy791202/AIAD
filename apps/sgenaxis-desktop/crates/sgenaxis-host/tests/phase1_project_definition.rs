//! M01-S2 shared-state Port contract tests; no native filesystem proof.
use sgenaxis_host::project_definition::*;
use sgenaxis_host::project_preferences::PreferenceChoice;
use sgenaxis_ports::*;
use sgenaxis_work::project_definition::*;
use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};
const ROOT: &str = "C:/owned-fixture-parent/Project-A";
const PATH: &str = "C:/owned-fixture-parent/Project-A/.sgenaxis/project-definition.json";
const PREF: &str = "C:/owned-fixture-parent/Project-A/.sgenaxis/preferences.json";
const OLD: &[u8] = "{\"schema\": \"eluslot.project-definition\", \"schemaVersion\": 1, \"projectUuid\": \"11111111-1111-4111-8111-111111111111\", \"definitionRevision\": \"3\", \"name\": \"Local Design\", \"purpose\": \"先保存需求草稿\", \"mode\": \"draft\", \"lastSavedStep\": \"delivery\", \"deliveryTargets\": [], \"topology\": {\"state\": \"unresolved\", \"value\": null}, \"requirements\": [], \"preferenceSource\": \"skip\", \"template\": null, \"openDecisions\": [\"delivery.form\", \"technology.framework\"], \"approvalRefs\": [], \"legacyRootKeys\": [\"proj_legacy_A\"], \"extensions\": {}}".as_bytes();
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
fn context() -> DefinitionAuthorityContext {
    DefinitionAuthorityContext {
        selection_id: "selection-A".into(),
        session_id: "session-A".into(),
        owner_window: "main".into(),
    }
}
fn new_location() -> DefinitionLocation {
    DefinitionLocation::NewProject {
        canonical_parent: "C:/owned-fixture-parent".into(),
        single_name: "Project-A".into(),
    }
}
fn existing() -> DefinitionLocation {
    DefinitionLocation::ExistingProject {
        canonical_root: ROOT.into(),
    }
}
fn digest(b: &[u8]) -> String {
    format!("sha256:{}", sgenaxis_spec::packet::source_sha256(b))
}
fn raw_digest(b: &[u8]) -> RawDefinitionDigest {
    RawDefinitionDigest::try_from_text(&digest(b)).expect("fixture digest is valid")
}
#[derive(Debug, Clone, PartialEq, Eq)]
enum Node {
    Dir,
    File(Vec<u8>),
}
#[derive(Default)]
struct State {
    tree: BTreeMap<String, Node>,
    log: Vec<String>,
    fault: Option<(String, CommitError)>,
    receipt_fault: Option<(String, u8)>,
    reads: usize,
    read_change: Option<Result<Vec<u8>, PortError>>,
    first_read_error: Option<PortError>,
    race_root: bool,
    race_meta: bool,
}
#[derive(Clone, Default)]
struct Rig(Arc<Mutex<State>>);
impl Rig {
    fn seed(&self, p: &str, node: Node) {
        self.0.lock().unwrap().tree.insert(p.into(), node);
    }
    fn tree(&self) -> BTreeMap<String, Node> {
        self.0.lock().unwrap().tree.clone()
    }
    fn log(&self) -> Vec<String> {
        self.0.lock().unwrap().log.clone()
    }
    fn fail(&self, op: &str, e: CommitError) {
        self.0.lock().unwrap().fault = Some((op.into(), e));
    }
    fn call(&self, op: &str) -> Result<(), CommitError> {
        let mut s = self.0.lock().unwrap();
        s.log.push(op.into());
        if let Some((key, e)) = &s.fault {
            if key == op {
                return Err(e.clone());
            }
        }
        Ok(())
    }
    fn from_existing() -> Self {
        let r = Self::default();
        r.seed(ROOT, Node::Dir);
        r.seed(&format!("{ROOT}/.sgenaxis"), Node::Dir);
        r.seed(PATH, Node::File(OLD.to_vec()));
        r
    }
}
impl FileSystemPort for Rig {
    fn exists(&self, p: &str) -> Result<bool, PortError> {
        self.0.lock().unwrap().log.push(format!("exists:{p}"));
        Ok(self.tree().contains_key(p))
    }
    fn is_file(&self, p: &str) -> Result<bool, PortError> {
        self.0.lock().unwrap().log.push(format!("is_file:{p}"));
        Ok(matches!(self.tree().get(p), Some(Node::File(_))))
    }
    fn read(&self, p: &str) -> Result<Vec<u8>, PortError> {
        let mut s = self.0.lock().unwrap();
        s.log.push(format!("read:{p}"));
        s.reads += 1;
        if s.reads == 1 {
            if let Some(e) = &s.first_read_error {
                return Err(e.clone());
            }
        }
        if s.reads > 1 {
            if let Some(v) = &s.read_change {
                return v.clone();
            }
        }
        match s.tree.get(p) {
            Some(Node::File(b)) => Ok(b.clone()),
            _ => Err(PortError::NotFound(p.into())),
        }
    }
    fn read_to_string(&self, p: &str) -> Result<String, PortError> {
        String::from_utf8(self.read(p)?).map_err(|e| PortError::Other(e.to_string()))
    }
    fn write_atomic(&self, p: &str, _: &[u8]) -> Result<(), PortError> {
        self.0
            .lock()
            .unwrap()
            .log
            .push(format!("FORBIDDEN_write:{p}"));
        Err(PortError::Other("forbidden HOST write".into()))
    }
    fn create_dir_all(&self, p: &str) -> Result<(), PortError> {
        self.0
            .lock()
            .unwrap()
            .log
            .push(format!("FORBIDDEN_mkdir:{p}"));
        Err(PortError::Other("forbidden recursive create".into()))
    }
    fn remove_file(&self, p: &str) -> Result<(), PortError> {
        self.0
            .lock()
            .unwrap()
            .log
            .push(format!("FORBIDDEN_remove:{p}"));
        Err(PortError::Other("forbidden delete".into()))
    }
}
impl FileCommitPort for Rig {
    fn create_directory_exclusive(&self, parent: &str, name: &str) -> Result<String, CommitError> {
        let p = format!("{}/{name}", parent.trim_end_matches(['/', '\\']));
        self.call(&format!("mkdir:{p}"))?;
        let mut s = self.0.lock().unwrap();
        if s.race_root && p == ROOT {
            s.tree.insert(p.clone(), Node::Dir);
        }
        if s.race_meta && p == format!("{ROOT}/.sgenaxis") {
            s.tree.insert(p.clone(), Node::Dir);
        }
        if s.tree.contains_key(&p) {
            return Err(CommitError::AlreadyExists { path: p });
        }
        s.tree.insert(p.clone(), Node::Dir);
        Ok(p)
    }
    fn acquire_write(&self, p: &str) -> Result<Box<dyn FileWriteLease>, CommitError> {
        self.call(&format!("acquire:{p}"))?;
        Ok(Box::new(Lease {
            rig: self.clone(),
            path: p.into(),
        }))
    }
}
struct Lease {
    rig: Rig,
    path: String,
}
impl FileWriteLease for Lease {
    fn read_current(&self) -> Result<Option<Vec<u8>>, CommitError> {
        self.rig.call(&format!("current:{}", self.path))?;
        Ok(match self.rig.tree().get(&self.path) {
            Some(Node::File(b)) => Some(b.clone()),
            _ => None,
        })
    }
    fn replace_checked(
        &mut self,
        expected: Option<&str>,
        bytes: &[u8],
    ) -> Result<CommitReceipt, CommitError> {
        self.rig.call(&format!("replace:{}", self.path))?;
        let mut s = self.rig.0.lock().unwrap();
        let old = match s.tree.get(&self.path) {
            Some(Node::File(b)) => Some(digest(b)),
            _ => None,
        };
        if old.as_deref() != expected {
            return Err(CommitError::Conflict {
                expected: expected.map(String::from),
                observed: old,
            });
        }
        s.tree.insert(self.path.clone(), Node::File(bytes.to_vec()));
        let mut proof = CommitReceipt {
            target_path: self.path.clone(),
            previous_digest: old,
            committed_digest: digest(bytes),
            transaction_id: "0123456789abcdef0123456789abcdef".into(),
        };
        if let Some((p, n)) = &s.receipt_fault {
            if p == &self.path {
                match n {
                    0 => proof.target_path = "C:/wrong".into(),
                    1 => proof.committed_digest = digest(b"wrong"),
                    2 => proof.previous_digest = Some(digest(b"wrong")),
                    _ => proof.transaction_id = "bad".into(),
                }
            }
        }
        Ok(proof)
    }
}
fn binding(
    r: &Rig,
    loc: DefinitionLocation,
    baseline: DefinitionBaseline,
    prefs: PreparedPreferencePlan,
) -> DefinitionBinding {
    let result = bind_definition(r, context(), loc, base().project_uuid, baseline, prefs, &[]);
    assert!(
        result.is_ok(),
        "product binding boundary rejected valid fixture: {result:?}"
    );
    result.unwrap()
}
fn new_binding(r: &Rig) -> DefinitionBinding {
    binding(
        r,
        new_location(),
        DefinitionBaseline::Absent,
        PreparedPreferencePlan::Skip,
    )
}
fn old_binding(r: &Rig) -> DefinitionBinding {
    binding(
        r,
        existing(),
        DefinitionBaseline::Present {
            raw_digest: raw_digest(OLD),
            revision: DefinitionRevision(3),
            project_uuid: base().project_uuid,
        },
        PreparedPreferencePlan::Skip,
    )
}
fn save_new(r: &Rig) -> Result<DefinitionSaveReceipt, DefinitionStoreError> {
    save_definition(r, r, &new_binding(r), None, &base())
}
fn storage(stage: CommitStage, p: &str) -> CommitError {
    CommitError::Storage {
        stage,
        path: p.into(),
        reason: "injected".into(),
    }
}
fn recovery(p: &str) -> CommitError {
    CommitError::RecoveryRequired {
        target_path: p.into(),
        journal_path: format!("{p}.journal"),
        old_version_path: Some(format!("{p}.old")),
        new_version_path: Some(format!("{p}.new")),
        reason: "uncertain".into(),
    }
}
fn assert_no_forbidden(r: &Rig) {
    assert!(
        !r.log().iter().any(|x| x.starts_with("FORBIDDEN")),
        "{:?}",
        r.log()
    );
}
fn receipt(
    r: &Rig,
    b: DefinitionBinding,
    d: ProjectDefinition,
    expected: Option<&str>,
) -> DefinitionSaveReceipt {
    let result = save_definition(r, r, &b, expected, &d);
    assert!(result.is_ok(), "save boundary: {result:?}");
    let p = result.unwrap();
    assert_eq!(p.definition.project_uuid, d.project_uuid);
    assert_eq!(p.definition.persisted_revision, d.definition_revision);
    assert_eq!(
        p.definition.relative_path,
        ".sgenaxis/project-definition.json"
    );
    assert_eq!(p.canonical_root, ROOT);
    assert_eq!(p.definition.transaction_id.len(), 32);
    let bytes = match r.tree().get(PATH).unwrap() {
        Node::File(b) => b.clone(),
        _ => panic!("definition is not a file"),
    };
    assert_eq!(p.definition.raw_digest.as_str(), digest(&bytes));
    assert_eq!(decode_definition(&bytes), Ok(d));
    assert_no_forbidden(r);
    p
}
fn prepared_preset() -> PreparedPreferencePlan {
    let p = sgenaxis_spec::project_preferences::preset("balanced").expect("fixture preset");
    let b = serde_json::to_vec_pretty(&p).expect("fixture preference JSON");
    PreparedPreferencePlan::Preset {
        preset_id: "balanced".into(),
        digest: raw_digest(&b),
        encoded_bytes: b,
    }
}
fn with_prefs(r: &Rig) -> (DefinitionBinding, ProjectDefinition) {
    let b = binding(
        r,
        new_location(),
        DefinitionBaseline::Absent,
        prepared_preset(),
    );
    let mut d = base();
    d.draft.preference_source = PreferenceSource::Preset;
    (b, d)
}
#[test]
fn fixture_health_same_state_receipts_and_faults() {
    let r = Rig::default();
    let p = r
        .create_directory_exclusive("C:/owned-fixture-parent", "Project-A")
        .unwrap();
    assert_eq!(p, ROOT);
    let mut l = r.acquire_write(PATH).unwrap();
    assert_eq!(l.read_current(), Ok(None));
    let proof = l.replace_checked(None, OLD).unwrap();
    assert_eq!(proof.committed_digest, digest(OLD));
    assert_eq!(r.read(PATH).unwrap(), OLD);
    assert!(matches!(
        l.replace_checked(None, b"changed"),
        Err(CommitError::Conflict { .. })
    ));
    let before = r.tree();
    r.fail(&format!("replace:{PATH}"), recovery(PATH));
    assert!(matches!(
        l.replace_checked(Some(&digest(OLD)), b"changed"),
        Err(CommitError::RecoveryRequired { .. })
    ));
    assert_eq!(r.tree(), before);
}

#[test]
fn t051_new_skip() {
    let r = Rig::default();
    let p = receipt(&r, new_binding(&r), base(), None);
    assert!(p.creation.root_created);
    assert_eq!(p.preferences, PreferenceCommitStatus::Skipped);
    assert!(!r.tree().contains_key(PREF));
    assert_eq!(
        r.log().iter().filter(|s| s.starts_with("mkdir:")).count(),
        2
    );
    assert!(matches!(
        p.next_binding.baseline(),
        DefinitionBaseline::Present {
            revision: DefinitionRevision(0),
            ..
        }
    ));
}

#[test]
fn t052_preference_commit() {
    let r = Rig::default();
    let source = b"source unrelated sentinel";
    r.seed("C:/source/sentinel", Node::File(source.to_vec()));
    let mut plan = prepared_preset();
    let before = r.tree().get("C:/source/sentinel").cloned();
    let b = binding(&r, new_location(), DefinitionBaseline::Absent, plan.clone());
    let mut d = base();
    d.draft.preference_source = PreferenceSource::Preset;
    let p = receipt(&r, b, d, None);
    assert!(
        matches!(p.preferences,PreferenceCommitStatus::Committed{ref relative_path,..} if relative_path==".sgenaxis/preferences.json")
    );
    let expected = match plan {
        PreparedPreferencePlan::Preset { encoded_bytes, .. }
        | PreparedPreferencePlan::ImportedCopy { encoded_bytes, .. } => encoded_bytes,
        _ => unreachable!(),
    };
    assert_eq!(r.tree().get(PREF), Some(&Node::File(expected)));
    assert_eq!(r.tree().get("C:/source/sentinel").cloned(), before);
    let logs = r.log();
    assert!(
        logs.iter()
            .position(|s| s == &format!("replace:{PATH}"))
            .unwrap()
            < logs
                .iter()
                .position(|s| s == &format!("replace:{PREF}"))
                .unwrap()
    );
}

#[test]
fn t053_preference_commit() {
    let r = Rig::default();
    let source = b"source unrelated sentinel";
    r.seed("C:/source/sentinel", Node::File(source.to_vec()));
    let mut plan = prepared_preset();
    if let PreparedPreferencePlan::Preset {
        encoded_bytes,
        digest,
        ..
    } = plan
    {
        plan = PreparedPreferencePlan::ImportedCopy {
            captured_source_digest: digest.clone(),
            encoded_bytes,
            digest,
        };
    }
    let source_bytes = match &plan {
        PreparedPreferencePlan::ImportedCopy { encoded_bytes, .. } => encoded_bytes.clone(),
        _ => unreachable!(),
    };
    r.seed("C:/source/sentinel", Node::File(source_bytes.clone()));
    let before = r.tree().get("C:/source/sentinel").cloned();
    let b = binding(&r, new_location(), DefinitionBaseline::Absent, plan.clone());
    let mut d = base();
    d.draft.preference_source = PreferenceSource::ImportedCopy;
    let p = receipt(&r, b, d, None);
    assert!(
        matches!(p.preferences,PreferenceCommitStatus::Committed{ref relative_path,..} if relative_path==".sgenaxis/preferences.json")
    );
    let expected = match plan {
        PreparedPreferencePlan::Preset { encoded_bytes, .. }
        | PreparedPreferencePlan::ImportedCopy { encoded_bytes, .. } => encoded_bytes,
        _ => unreachable!(),
    };
    assert_eq!(r.tree().get(PREF), Some(&Node::File(expected)));
    assert_eq!(r.tree().get("C:/source/sentinel").cloned(), before);
    let changed =
        serde_json::to_vec(&sgenaxis_spec::project_preferences::preset("throughput").unwrap())
            .unwrap();
    let mut lease = r.acquire_write(PREF).unwrap();
    let old_digest = match r.tree().get(PREF).unwrap() {
        Node::File(bytes) => digest(bytes),
        _ => unreachable!(),
    };
    lease.replace_checked(Some(&old_digest), &changed).unwrap();
    assert_eq!(
        r.tree().get("C:/source/sentinel"),
        Some(&Node::File(source_bytes))
    );
    let logs = r.log();
    assert!(
        logs.iter()
            .position(|s| s == &format!("replace:{PATH}"))
            .unwrap()
            < logs
                .iter()
                .position(|s| s == &format!("replace:{PREF}"))
                .unwrap()
    );
}

#[test]
fn t054_prepare_invalid_preset() {
    assert_eq!(
        prepare_definition_preferences(PreferenceChoice::Preset("unknown")),
        Err(DefinitionStoreError::InvalidInput {
            field: "preferences.preset".into(),
            code: DefinitionInputCode::PreferenceInvalid
        })
    );
}

#[test]
fn t055_prepare_invalid_import() {
    assert_eq!(
        prepare_definition_preferences(PreferenceChoice::Imported(b"bad")),
        Err(DefinitionStoreError::InvalidInput {
            field: "preferences.import".into(),
            code: DefinitionInputCode::PreferenceInvalid
        })
    );
}

#[test]
fn t056_mismatch_before_create() {
    let r = Rig::default();
    let b = binding(
        &r,
        new_location(),
        DefinitionBaseline::Absent,
        prepared_preset(),
    );
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::InvalidInput {
            field: "preferences".into(),
            code: DefinitionInputCode::PreferenceModeMismatch
        })
    );
    assert_eq!(r.tree(), before);
    assert!(!r
        .log()
        .iter()
        .any(|s| s.starts_with("mkdir:") || s.starts_with("replace:")));
}

#[test]
fn t057_file() {
    let r = Rig::default();
    r.seed(ROOT, Node::File(b"do not delete".to_vec()));
    let b = new_binding(&r);
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::ExistingTarget { path: ROOT.into() })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t058_empty() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    let b = new_binding(&r);
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::ExistingTarget { path: ROOT.into() })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t059_nonempty() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    r.seed(
        &format!("{ROOT}/keep.ess"),
        Node::File(b"protected".to_vec()),
    );
    let b = new_binding(&r);
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::ExistingTarget { path: ROOT.into() })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t060_race() {
    let r = Rig::default();
    let b = new_binding(&r);
    let before = r.tree();
    r.0.lock().unwrap().race_root = true;
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::ExistingTarget { path: ROOT.into() })
    );
    let mut expected = before;
    expected.insert(ROOT.into(), Node::Dir);
    assert_eq!(r.tree(), expected);
    assert_no_forbidden(&r);
}

#[test]
fn t061_skip() {
    let r = Rig::from_existing();
    let mut old = base();
    old.definition_revision = DefinitionRevision(3);
    old.draft.preference_source = PreferenceSource::Skip;
    let mut v: serde_json::Value = serde_json::from_slice(OLD).unwrap();
    v["preferenceSource"] = serde_json::json!("skip");
    let bytes = serde_json::to_vec(&v).unwrap();
    r.seed(PATH, Node::File(bytes.clone()));
    r.seed(PREF, Node::File(b"historical preference".to_vec()));
    let b = binding(
        &r,
        existing(),
        DefinitionBaseline::Present {
            raw_digest: raw_digest(&bytes),
            revision: DefinitionRevision(3),
            project_uuid: base().project_uuid,
        },
        PreparedPreferencePlan::Skip,
    );
    let mut d = old;
    d.definition_revision = DefinitionRevision(5);
    let p = receipt(&r, b, d, Some(&digest(&bytes)));
    assert_eq!(p.preferences, PreferenceCommitStatus::Skipped);
    assert_eq!(
        r.tree().get(PREF),
        Some(&Node::File(b"historical preference".to_vec()))
    );
    assert!(!r.log().iter().any(|s| s.starts_with("mkdir:")));
}

#[test]
fn t061_preset() {
    let r = Rig::from_existing();
    let mut old = base();
    old.definition_revision = DefinitionRevision(3);
    old.draft.preference_source = PreferenceSource::Preset;
    let mut v: serde_json::Value = serde_json::from_slice(OLD).unwrap();
    v["preferenceSource"] = serde_json::json!("preset");
    let bytes = serde_json::to_vec(&v).unwrap();
    r.seed(PATH, Node::File(bytes.clone()));
    r.seed(PREF, Node::File(b"historical preference".to_vec()));
    let b = binding(
        &r,
        existing(),
        DefinitionBaseline::Present {
            raw_digest: raw_digest(&bytes),
            revision: DefinitionRevision(3),
            project_uuid: base().project_uuid,
        },
        PreparedPreferencePlan::Skip,
    );
    let mut d = old;
    d.definition_revision = DefinitionRevision(5);
    let p = receipt(&r, b, d, Some(&digest(&bytes)));
    assert_eq!(p.preferences, PreferenceCommitStatus::Skipped);
    assert_eq!(
        r.tree().get(PREF),
        Some(&Node::File(b"historical preference".to_vec()))
    );
    assert!(!r.log().iter().any(|s| s.starts_with("mkdir:")));
}

#[test]
fn t061_importedcopy() {
    let r = Rig::from_existing();
    let mut old = base();
    old.definition_revision = DefinitionRevision(3);
    old.draft.preference_source = PreferenceSource::ImportedCopy;
    let mut v: serde_json::Value = serde_json::from_slice(OLD).unwrap();
    v["preferenceSource"] = serde_json::json!("imported-copy");
    let bytes = serde_json::to_vec(&v).unwrap();
    r.seed(PATH, Node::File(bytes.clone()));
    r.seed(PREF, Node::File(b"historical preference".to_vec()));
    let b = binding(
        &r,
        existing(),
        DefinitionBaseline::Present {
            raw_digest: raw_digest(&bytes),
            revision: DefinitionRevision(3),
            project_uuid: base().project_uuid,
        },
        PreparedPreferencePlan::Skip,
    );
    let mut d = old;
    d.definition_revision = DefinitionRevision(5);
    let p = receipt(&r, b, d, Some(&digest(&bytes)));
    assert_eq!(p.preferences, PreferenceCommitStatus::Skipped);
    assert_eq!(
        r.tree().get(PREF),
        Some(&Node::File(b"historical preference".to_vec()))
    );
    assert!(!r.log().iter().any(|s| s.starts_with("mkdir:")));
}

#[test]
fn t062_same_revision_noop() {
    let r = Rig::from_existing();
    let mut d = base();
    d.definition_revision = DefinitionRevision(3);
    let p = receipt(&r, old_binding(&r), d, Some(&digest(OLD)));
    assert_eq!(p.definition.persisted_revision, DefinitionRevision(3));
}

#[test]
fn t063_same_revision_changed() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let mut d = base();
    d.definition_revision = DefinitionRevision(3);
    d.draft.purpose = "changed".into();
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, Some(&digest(OLD)), &d),
        Err(DefinitionStoreError::InvalidInput {
            field: "definitionRevision".into(),
            code: DefinitionInputCode::RevisionNotAdvanced
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t064_changed() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let bytes = b"external malformed".to_vec();
    let observed = Some(raw_digest(&bytes));
    r.seed(PATH, Node::File(bytes));
    let before = r.tree();
    let mut d = base();
    d.definition_revision = DefinitionRevision(5);
    assert_eq!(
        save_definition(&r, &r, &b, Some(&digest(OLD)), &d),
        Err(DefinitionStoreError::RevisionConflict {
            expected_digest: Some(raw_digest(OLD)),
            observed_digest: observed,
            expected_revision: Some(DefinitionRevision(3)),
            observed_revision: None
        })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t065_reformat() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let bytes = format!(" {} ", String::from_utf8(OLD.to_vec()).unwrap()).into_bytes();
    let observed = Some(raw_digest(&bytes));
    r.seed(PATH, Node::File(bytes));
    let before = r.tree();
    let mut d = base();
    d.definition_revision = DefinitionRevision(5);
    assert_eq!(
        save_definition(&r, &r, &b, Some(&digest(OLD)), &d),
        Err(DefinitionStoreError::RevisionConflict {
            expected_digest: Some(raw_digest(OLD)),
            observed_digest: observed,
            expected_revision: Some(DefinitionRevision(3)),
            observed_revision: None
        })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t066_absent() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    r.0.lock().unwrap().tree.remove(PATH);
    let observed = None;
    let before = r.tree();
    let mut d = base();
    d.definition_revision = DefinitionRevision(5);
    assert_eq!(
        save_definition(&r, &r, &b, Some(&digest(OLD)), &d),
        Err(DefinitionStoreError::RevisionConflict {
            expected_digest: Some(raw_digest(OLD)),
            observed_digest: observed,
            expected_revision: Some(DefinitionRevision(3)),
            observed_revision: None
        })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t067_adoption_race() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    let loc = DefinitionLocation::LegacyAdoption {
        canonical_root: ROOT.into(),
        candidate_uuid: base().project_uuid,
        portable_legacy_keys: base().legacy_root_keys,
    };
    let b = binding(
        &r,
        loc,
        DefinitionBaseline::Absent,
        PreparedPreferencePlan::Skip,
    );
    r.seed(PATH, Node::File(b"external".to_vec()));
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::RevisionConflict {
            expected_digest: None,
            observed_digest: Some(raw_digest(b"external")),
            expected_revision: None,
            observed_revision: None
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t076_adoption_race() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    let loc = DefinitionLocation::LegacyAdoption {
        canonical_root: ROOT.into(),
        candidate_uuid: base().project_uuid,
        portable_legacy_keys: base().legacy_root_keys,
    };
    let b = binding(
        &r,
        loc,
        DefinitionBaseline::Absent,
        PreparedPreferencePlan::Skip,
    );
    r.seed(PATH, Node::File(b"external".to_vec()));
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::RevisionConflict {
            expected_digest: None,
            observed_digest: Some(raw_digest(b"external")),
            expected_revision: None,
            observed_revision: None
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t068_expected_digest_mismatch() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::InvalidInput {
            field: "expectedDiskDigest".into(),
            code: DefinitionInputCode::ExpectedDigestMismatch
        })
    );
    assert_eq!(r.tree(), before);
    assert!(!r.log().iter().any(|s| s.starts_with("acquire:")));
}

#[test]
fn t069_uuid_mismatch() {
    let r = Rig::default();
    let b = new_binding(&r);
    let mut d = base();
    d.project_uuid = PersistentProjectId::candidate("22222222-2222-4222-8222-222222222222");
    assert_eq!(
        save_definition(&r, &r, &b, None, &d),
        Err(DefinitionStoreError::InvalidInput {
            field: "projectUuid".into(),
            code: DefinitionInputCode::BindingMismatch
        })
    );
    assert!(r.tree().is_empty());
}

#[test]
fn t070_readonly_open() {
    let r = Rig::from_existing();
    let before = r.tree();
    let mut d = base();
    d.definition_revision = DefinitionRevision(3);
    assert_eq!(
        open_definition(&r, &context(), &existing(), Some(&d.project_uuid), &[]),
        Ok(DefinitionOpenView::Saved {
            definition: d,
            raw_digest: raw_digest(OLD),
            canonical_root: ROOT.into(),
            relative_path: ".sgenaxis/project-definition.json".into()
        })
    );
    assert_eq!(r.tree(), before);
    assert_eq!(r.log().iter().filter(|s| s.starts_with("read:")).count(), 2);
    assert_no_forbidden(&r);
}

#[test]
fn t071_duplicate_root() {
    let r = Rig::from_existing();
    let claims = vec![OpenDefinitionClaim {
        project_uuid: base().project_uuid,
        canonical_root: "C:/other".into(),
    }];
    let before = r.tree();
    assert_eq!(
        open_definition(&r, &context(), &existing(), None, &claims),
        Err(DefinitionStoreError::IdentityConflict {
            expected_uuid: None,
            observed_uuid: base().project_uuid,
            requested_root: ROOT.into(),
            other_root: Some("C:/other".into()),
            reason: IdentityConflictReason::DuplicateOpenRoot
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t072_read_denied() {
    let r = Rig::from_existing();
    r.0.lock().unwrap().first_read_error = Some(PortError::Io("denied".into()));
    let before = r.tree();
    assert_eq!(
        open_definition(&r, &context(), &existing(), None, &[]),
        Err(DefinitionStoreError::StorageFailure {
            fault: StoreFault {
                stage: CommitStage::Read,
                path: PATH.into(),
                reason: PortError::Io("denied".into()).to_string()
            },
            retained_artifacts: vec![]
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t072_missing_root() {
    let r = Rig::default();
    assert!(
        matches!(open_definition(&r,&context(),&existing(),None,&[]),Err(DefinitionStoreError::InvalidLocation{path,retained_artifacts,..}) if path==ROOT&&retained_artifacts.is_empty())
    );
    assert!(r.tree().is_empty());
}

#[test]
fn t073_changed() {
    let r = Rig::from_existing();
    r.0.lock().unwrap().read_change = Some(Ok(b"other".to_vec()));
    let before = r.tree();
    assert!(
        matches!(open_definition(&r,&context(),&existing(),None,&[]),Err(DefinitionStoreError::RevisionConflict{expected_digest:Some(ref d),..}) if d==&raw_digest(OLD))
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t073_absent() {
    let r = Rig::from_existing();
    r.0.lock().unwrap().read_change = Some(Err(PortError::NotFound(PATH.into())));
    let before = r.tree();
    assert!(
        matches!(open_definition(&r,&context(),&existing(),None,&[]),Err(DefinitionStoreError::RevisionConflict{expected_digest:Some(ref d),..}) if d==&raw_digest(OLD))
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t073_denied() {
    let r = Rig::from_existing();
    r.0.lock().unwrap().read_change = Some(Err(PortError::Io("denied".into())));
    let before = r.tree();
    assert!(
        matches!(open_definition(&r,&context(),&existing(),None,&[]),Err(DefinitionStoreError::RevisionConflict{expected_digest:Some(ref d),..}) if d==&raw_digest(OLD))
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t074_readonly_legacy() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    r.seed(&format!("{ROOT}/old.ess"), Node::File(b"original".to_vec()));
    let before = r.tree();
    let result = open_definition(&r, &context(), &existing(), None, &[]);
    assert!(
        matches!(result,Ok(DefinitionOpenView::Legacy{canonical_root,migration_required:true,..}) if canonical_root==ROOT)
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t075_adopt_only_definition() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    r.seed(PREF, Node::File(b"original-prefs".to_vec()));
    r.seed(&format!("{ROOT}/.sgenaxis"), Node::Dir);
    r.seed(&format!("{ROOT}/old.ess"), Node::File(b"original".to_vec()));
    let before = r.tree();
    let loc = DefinitionLocation::LegacyAdoption {
        canonical_root: ROOT.into(),
        candidate_uuid: base().project_uuid,
        portable_legacy_keys: base().legacy_root_keys,
    };
    let b = binding(
        &r,
        loc,
        DefinitionBaseline::Absent,
        PreparedPreferencePlan::Skip,
    );
    let p = receipt(&r, b, base(), None);
    assert!(!p.creation.root_created);
    for (path, node) in before {
        assert_eq!(r.tree().get(&path), Some(&node));
    }
    assert_eq!(r.tree().len(), 4 + 1);
    assert_eq!(p.preferences, PreferenceCommitStatus::Skipped);
}

#[test]
fn t077_foreign_metadata() {
    let r = Rig::default();
    r.seed(ROOT, Node::Dir);
    r.seed(
        &format!("{ROOT}/.sgenaxis"),
        Node::File(b"foreign metadata file".to_vec()),
    );
    let b = binding(
        &r,
        DefinitionLocation::LegacyAdoption {
            canonical_root: ROOT.into(),
            candidate_uuid: base().project_uuid,
            portable_legacy_keys: base().legacy_root_keys,
        },
        DefinitionBaseline::Absent,
        PreparedPreferencePlan::Skip,
    );
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::ExistingTarget {
            path: format!("{ROOT}/.sgenaxis")
        })
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t078_failure() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(
        "mkdir:C:/owned-fixture-parent/Project-A",
        storage(
            CommitStage::CreateDirectory,
            "C:/owned-fixture-parent/Project-A",
        ),
    );
    let result = save_definition(&r, &r, &b, None, &d);
    assert!(
        matches!(result,Err(DefinitionStoreError::StorageFailure{fault:StoreFault{stage:CommitStage::CreateDirectory,..},retained_artifacts}) if retained_artifacts.is_empty())
    );
    assert!(r.tree().is_empty());
    assert!(
        r.log()
            .contains(&"mkdir:C:/owned-fixture-parent/Project-A".into()),
        "fault point reached"
    );
    assert_no_forbidden(&r);
}

#[test]
fn t079_failure() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(
        "mkdir:C:/owned-fixture-parent/Project-A/.sgenaxis",
        storage(
            CommitStage::CreateDirectory,
            "C:/owned-fixture-parent/Project-A/.sgenaxis",
        ),
    );
    let result = save_definition(&r, &r, &b, None, &d);
    let progress = match result {
        Err(DefinitionStoreError::PartialProjectCreated {
            progress,
            cause: CreationFailureCause::Storage { fault },
        }) => {
            assert_eq!(fault.stage, CommitStage::CreateDirectory);
            progress
        }
        other => panic!("exact partial error: {other:?}"),
    };
    assert!(progress.root_created);
    assert_eq!(progress.phase, CreationPhase::CreateMetadata);
    assert_eq!(progress.definition_commit.is_some(), false);
    assert!(r.tree().contains_key(ROOT));
    assert_eq!(r.tree().contains_key(PATH), false);
    assert!(
        r.log()
            .contains(&"mkdir:C:/owned-fixture-parent/Project-A/.sgenaxis".into()),
        "fault point reached"
    );
    assert_no_forbidden(&r);
}

#[test]
fn t080_failure() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(
        "replace:C:/owned-fixture-parent/Project-A/.sgenaxis/project-definition.json",
        storage(
            CommitStage::VerifyPublished,
            "C:/owned-fixture-parent/Project-A/.sgenaxis/project-definition.json",
        ),
    );
    let result = save_definition(&r, &r, &b, None, &d);
    let progress = match result {
        Err(DefinitionStoreError::PartialProjectCreated {
            progress,
            cause: CreationFailureCause::Storage { fault },
        }) => {
            assert_eq!(fault.stage, CommitStage::VerifyPublished);
            progress
        }
        other => panic!("exact partial error: {other:?}"),
    };
    assert!(progress.root_created);
    assert_eq!(progress.phase, CreationPhase::CommitDefinition);
    assert_eq!(progress.definition_commit.is_some(), false);
    assert!(r.tree().contains_key(ROOT));
    assert_eq!(r.tree().contains_key(PATH), false);
    assert!(
        r.log().contains(
            &"replace:C:/owned-fixture-parent/Project-A/.sgenaxis/project-definition.json".into()
        ),
        "fault point reached"
    );
    assert_no_forbidden(&r);
}

#[test]
fn t081_failure() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(
        "replace:C:/owned-fixture-parent/Project-A/.sgenaxis/preferences.json",
        storage(
            CommitStage::BeforePublish,
            "C:/owned-fixture-parent/Project-A/.sgenaxis/preferences.json",
        ),
    );
    let result = save_definition(&r, &r, &b, None, &d);
    let progress = match result {
        Err(DefinitionStoreError::PartialProjectCreated {
            progress,
            cause: CreationFailureCause::Storage { fault },
        }) => {
            assert_eq!(fault.stage, CommitStage::BeforePublish);
            progress
        }
        other => panic!("exact partial error: {other:?}"),
    };
    assert!(progress.root_created);
    assert_eq!(progress.phase, CreationPhase::CommitPreferences);
    assert_eq!(progress.definition_commit.is_some(), true);
    assert!(r.tree().contains_key(ROOT));
    assert_eq!(r.tree().contains_key(PATH), true);
    assert!(
        r.log().contains(
            &"replace:C:/owned-fixture-parent/Project-A/.sgenaxis/preferences.json".into()
        ),
        "fault point reached"
    );
    assert_no_forbidden(&r);
}

#[test]
fn t082_recovery() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(&format!("replace:{}", PATH), recovery(PATH));
    let result = save_definition(&r, &r, &b, None, &d);
    let progress = match result {
        Err(DefinitionStoreError::RecoveryRequired {
            diagnostics,
            progress: Some(progress),
        }) => {
            assert_eq!(
                diagnostics,
                RecoveryInfo {
                    target_path: PATH.into(),
                    journal_path: format!("{}.journal", PATH),
                    old_version_path: Some(format!("{}.old", PATH)),
                    new_version_path: Some(format!("{}.new", PATH)),
                    reason: "uncertain".into()
                }
            );
            progress
        }
        other => panic!("top-level recovery {other:?}"),
    };
    assert_eq!(progress.definition_commit.is_some(), false);
    assert_no_forbidden(&r);
}

#[test]
fn t083_recovery() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(&format!("replace:{}", PREF), recovery(PREF));
    let result = save_definition(&r, &r, &b, None, &d);
    let progress = match result {
        Err(DefinitionStoreError::RecoveryRequired {
            diagnostics,
            progress: Some(progress),
        }) => {
            assert_eq!(
                diagnostics,
                RecoveryInfo {
                    target_path: PREF.into(),
                    journal_path: format!("{}.journal", PREF),
                    old_version_path: Some(format!("{}.old", PREF)),
                    new_version_path: Some(format!("{}.new", PREF)),
                    reason: "uncertain".into()
                }
            );
            progress
        }
        other => panic!("top-level recovery {other:?}"),
    };
    assert_eq!(progress.definition_commit.is_some(), true);
    assert_no_forbidden(&r);
}

#[test]
fn t084_preference_conflict() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.fail(
        &format!("replace:{PREF}"),
        CommitError::Conflict {
            expected: None,
            observed: Some(digest(b"external")),
        },
    );
    assert!(
        matches!(save_definition(&r,&r,&b,None,&d),Err(DefinitionStoreError::PartialProjectCreated{progress:CreationProgress{definition_commit:Some(_),..},cause:CreationFailureCause::Conflict{expected:None,observed:Some(d)},..}) if d==raw_digest(b"external"))
    );
    assert!(r.tree().contains_key(PATH));
    assert_no_forbidden(&r);
}

#[test]
fn t085_busy() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let before = r.tree();
    r.fail(
        &format!("acquire:{PATH}"),
        CommitError::Busy { path: PATH.into() },
    );
    let mut d = base();
    d.definition_revision = DefinitionRevision(5);
    assert_eq!(
        save_definition(&r, &r, &b, Some(&digest(OLD)), &d),
        Err(DefinitionStoreError::Busy { path: PATH.into() })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t086_captured_receipt() {
    let r = Rig::default();
    let mut live = base();
    let captured = live.clone();
    let b = new_binding(&r);
    let p = receipt(&r, b, captured.clone(), None);
    live.definition_revision = DefinitionRevision(9);
    assert_eq!(
        p.definition.persisted_revision,
        captured.definition_revision
    );
    assert_ne!(p.definition.persisted_revision, live.definition_revision);
    assert_eq!(p.next_binding.project_uuid(), &captured.project_uuid);
}

#[test]
fn t087_duplicate_request() {
    let r = Rig::default();
    let b = new_binding(&r);
    let _ = receipt(&r, b.clone(), base(), None);
    let before = r.tree();
    assert_eq!(
        save_definition(&r, &r, &b, None, &base()),
        Err(DefinitionStoreError::ExistingTarget { path: ROOT.into() })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t088_port_order() {
    let r = Rig::default();
    let _ = receipt(&r, new_binding(&r), base(), None);
    let calls = r.log();
    let writes: Vec<_> = calls
        .iter()
        .filter(|s| {
            s.starts_with("mkdir:") || s.starts_with("acquire:") || s.starts_with("replace:")
        })
        .cloned()
        .collect();
    assert_eq!(
        writes,
        vec![
            format!("mkdir:{ROOT}"),
            format!("mkdir:{ROOT}/.sgenaxis"),
            format!("acquire:{PATH}"),
            format!("replace:{PATH}")
        ]
    );
    assert_no_forbidden(&r);
}

#[test]
fn t089_version() {
    let r = Rig::from_existing();
    let mut v: serde_json::Value = serde_json::from_slice(OLD).unwrap();
    v["schemaVersion"] = serde_json::json!(2);
    r.seed(PATH, Node::File(serde_json::to_vec(&v).unwrap()));
    let before = r.tree();
    assert_eq!(
        open_definition(&r, &context(), &existing(), None, &[]),
        Err(DefinitionStoreError::UnsupportedSchema {
            schema: "eluslot.project-definition".into(),
            version: "2".into()
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t089_unknown() {
    let r = Rig::from_existing();
    let mut v: serde_json::Value = serde_json::from_slice(OLD).unwrap();
    v["futureRoot"] = serde_json::json!(true);
    r.seed(PATH, Node::File(serde_json::to_vec(&v).unwrap()));
    let before = r.tree();
    assert_eq!(
        open_definition(&r, &context(), &existing(), None, &[]),
        Err(DefinitionStoreError::Codec {
            issue: CodecIssue::UnknownField {
                pointer: "/futureRoot".into()
            }
        })
    );
    assert_eq!(r.tree(), before);
}

#[test]
fn t102_selection_id() {
    let r = Rig::from_existing();
    let mut c = context();
    c.selection_id.clear();
    assert_eq!(
        open_definition(&r, &c, &existing(), None, &[]),
        Err(DefinitionStoreError::NotBound)
    );
    assert!(r.log().is_empty());
    assert_eq!(
        bind_definition(
            &r,
            c,
            new_location(),
            base().project_uuid,
            DefinitionBaseline::Absent,
            PreparedPreferencePlan::Skip,
            &[]
        ),
        Err(DefinitionStoreError::NotBound)
    );
    assert!(r.log().is_empty());
}

#[test]
fn t102_session_id() {
    let r = Rig::from_existing();
    let mut c = context();
    c.session_id.clear();
    assert_eq!(
        open_definition(&r, &c, &existing(), None, &[]),
        Err(DefinitionStoreError::NotBound)
    );
    assert!(r.log().is_empty());
    assert_eq!(
        bind_definition(
            &r,
            c,
            new_location(),
            base().project_uuid,
            DefinitionBaseline::Absent,
            PreparedPreferencePlan::Skip,
            &[]
        ),
        Err(DefinitionStoreError::NotBound)
    );
    assert!(r.log().is_empty());
}

#[test]
fn t102_owner_window() {
    let r = Rig::from_existing();
    let mut c = context();
    c.owner_window.clear();
    assert_eq!(
        open_definition(&r, &c, &existing(), None, &[]),
        Err(DefinitionStoreError::NotBound)
    );
    assert!(r.log().is_empty());
    assert_eq!(
        bind_definition(
            &r,
            c,
            new_location(),
            base().project_uuid,
            DefinitionBaseline::Absent,
            PreparedPreferencePlan::Skip,
            &[]
        ),
        Err(DefinitionStoreError::NotBound)
    );
    assert!(r.log().is_empty());
}

#[test]
fn t103_native_error_mapping() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let before = r.tree();
    r.fail(
        &format!("acquire:{PATH}"),
        CommitError::InvalidPath {
            reason: "native reject".into(),
        },
    );
    let mut d = base();
    d.definition_revision = DefinitionRevision(5);
    let result = save_definition(&r, &r, &b, Some(&digest(OLD)), &d);
    assert!(
        matches!(result,Err(DefinitionStoreError::InvalidLocation{path,reason,retained_artifacts}) if path==PATH&&reason=="native reject"&&retained_artifacts.is_empty())
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t104_native_error_mapping() {
    let r = Rig::default();
    let b = new_binding(&r);
    let before = r.tree();
    r.fail(
        &format!("acquire:{PATH}"),
        CommitError::InvalidPath {
            reason: "native reject".into(),
        },
    );
    let mut d = base();
    let result = save_definition(&r, &r, &b, None, &d);
    assert!(
        matches!(result,Err(DefinitionStoreError::PartialProjectCreated{progress:CreationProgress{root_created:true,..},cause:CreationFailureCause::InvalidLocation{path,reason}}) if path==PATH&&reason=="native reject")
    );
    assert!(r.tree().contains_key(ROOT));
    assert_no_forbidden(&r);
}

#[test]
fn t105_native_error_mapping() {
    let r = Rig::from_existing();
    let b = old_binding(&r);
    let before = r.tree();
    r.fail(
        &format!("replace:{PATH}"),
        storage(CommitStage::VerifyPublished, PATH),
    );
    let mut d = base();
    d.definition_revision = DefinitionRevision(5);
    let result = save_definition(&r, &r, &b, Some(&digest(OLD)), &d);
    assert!(
        matches!(result,Err(DefinitionStoreError::StorageFailure{fault:StoreFault{stage:CommitStage::VerifyPublished,..},retained_artifacts}) if retained_artifacts.is_empty())
    );
    assert_eq!(r.tree(), before);
    assert_no_forbidden(&r);
}

#[test]
fn t107_0() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PATH.into(), 0));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PATH);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.target_path, "C:/wrong");
    assert_eq!(progress.definition_commit.is_some(), false);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PATH))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t107_1() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PATH.into(), 1));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PATH);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.committed_digest, digest(b"wrong"));
    assert_eq!(progress.definition_commit.is_some(), false);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PATH))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t107_2() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PATH.into(), 2));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PATH);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.previous_digest, Some(digest(b"wrong")));
    assert_eq!(progress.definition_commit.is_some(), false);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PATH))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t107_3() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PATH.into(), 3));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PATH);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.transaction_id, "bad");
    assert_eq!(progress.definition_commit.is_some(), false);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PATH))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t108_0() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PREF.into(), 0));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PREF);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.target_path, "C:/wrong");
    assert_eq!(progress.definition_commit.is_some(), true);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PREF))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t108_1() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PREF.into(), 1));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PREF);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.committed_digest, digest(b"wrong"));
    assert_eq!(progress.definition_commit.is_some(), true);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PREF))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t108_2() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PREF.into(), 2));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PREF);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.previous_digest, Some(digest(b"wrong")));
    assert_eq!(progress.definition_commit.is_some(), true);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PREF))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

#[test]
fn t108_3() {
    let r = Rig::default();
    let (b, d) = with_prefs(&r);
    r.0.lock().unwrap().receipt_fault = Some((PREF.into(), 3));
    let result = save_definition(&r, &r, &b, None, &d);
    let (reported, progress) = match result {
        Err(DefinitionStoreError::CommitEvidenceMismatch {
            requested_target,
            reported_receipt,
            progress,
        }) => {
            assert_eq!(requested_target, PREF);
            (reported_receipt, progress)
        }
        other => panic!("contradictory receipt must not be success/rollback: {other:?}"),
    };
    assert_eq!(reported.transaction_id, "bad");
    assert_eq!(progress.definition_commit.is_some(), true);
    let log = r.log();
    let at = log
        .iter()
        .position(|s| s == &format!("replace:{}", PREF))
        .expect("fault reached");
    assert!(!log[at + 1..]
        .iter()
        .any(|s| s.starts_with("replace:") || s.starts_with("mkdir:")));
    assert_no_forbidden(&r);
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn skip_creates_only_directory_without_inherited_policy() {
    t051_new_skip();
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn chosen_preset_persists_and_reopens_same_version() {
    t052_preference_commit();
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn importing_makes_independent_copy_without_changing_source() {
    t053_preference_commit();
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn invalid_import_or_unknown_preset_does_not_create_directory() {
    t054_prepare_invalid_preset();
    t055_prepare_invalid_import();
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn existing_file_is_not_deleted_and_existing_directory_is_not_adopted() {
    t057_file();
    t058_empty();
    t059_nonempty();
    t060_race();
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn preference_failure_is_partial_not_success_or_recursive_rollback() {
    t081_failure();
}

// Original creation regression migrated under the adopted S2 contract.
#[test]
fn directory_failure_is_explicit_and_no_policy_is_written() {
    t078_failure();
}

// Exact named value-accessor contract; no normalization or unchecked public seam.
#[test]
fn digest_value_contract() {
    for value in [
        "",
        "sha256:bad",
        "SHA256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    ] {
        assert_eq!(
            RawDefinitionDigest::try_from_text(value),
            None,
            "reject {value:?}"
        );
    }
    let text = digest(b"exact bytes");
    let d = RawDefinitionDigest::try_from_text(&text).unwrap();
    assert_eq!(d.as_str(), text);
}
#[test]
fn preparation_positive_contract() {
    assert_eq!(
        prepare_definition_preferences(PreferenceChoice::Skip),
        Ok(PreparedPreferencePlan::Skip)
    );
    let p = prepare_definition_preferences(PreferenceChoice::Preset("balanced"));
    let bytes = match p {
        Ok(PreparedPreferencePlan::Preset {
            preset_id,
            encoded_bytes,
            digest,
        }) => {
            assert_eq!(preset_id, "balanced");
            assert_eq!(digest.as_str(), self::digest(&encoded_bytes));
            assert_eq!(
                sgenaxis_spec::project_preferences::parse_project_preferences(&encoded_bytes)
                    .unwrap(),
                sgenaxis_spec::project_preferences::preset("balanced").unwrap()
            );
            encoded_bytes
        }
        other => panic!("preset prepare {other:?}"),
    };
    let before = bytes.clone();
    let p = prepare_definition_preferences(PreferenceChoice::Imported(&bytes));
    match p {
        Ok(PreparedPreferencePlan::ImportedCopy {
            captured_source_digest,
            encoded_bytes,
            digest,
        }) => {
            assert_eq!(captured_source_digest.as_str(), self::digest(&before));
            assert_eq!(digest.as_str(), self::digest(&encoded_bytes));
            assert_eq!(
                sgenaxis_spec::project_preferences::parse_project_preferences(&encoded_bytes)
                    .unwrap(),
                sgenaxis_spec::project_preferences::parse_project_preferences(&before).unwrap()
            );
        }
        other => panic!("independent import {other:?}"),
    };
    assert_eq!(bytes, before);
}
