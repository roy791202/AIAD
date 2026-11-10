//! M01-S3 wizard command-bridge RED contract. The bridge wraps the S2
//! project-definition DOMAIN as a step-wise lifecycle (begin → apply → prepare
//! → commit). This test drives the end-to-end bridge and asserts the commit
//! persists the project + `.sgenaxis/` definition.
//!
//! SKELETON: `wizard_commit` is not yet implemented and returns the
//! `NotImplemented` sentinel, so the end-to-end success assertion fails here
//! (valid RED). begin/apply/prepare/cancel are in-flight scaffolding only.

use sgenaxis_host::project_definition::DefinitionAuthorityContext;
use sgenaxis_host::project_definition::DefinitionLocation;
use sgenaxis_host::project_preferences::PreferenceChoice;
use sgenaxis_host::project_wizard::*;
use sgenaxis_ports::{
    CommitError, CommitReceipt, FileCommitPort, FileSystemPort, FileWriteLease, PortError,
};
use std::collections::BTreeMap;
use std::sync::{Arc, Mutex};

const PARENT: &str = "C:/owned-fixture-parent";
const NAME: &str = "Project-A";
const ROOT: &str = "C:/owned-fixture-parent/Project-A";
const PATH: &str = "C:/owned-fixture-parent/Project-A/.sgenaxis/project-definition.json";

// ── Minimal in-memory Port rig (FileSystemPort + FileCommitPort) ─────────────

#[derive(Debug, Clone, PartialEq, Eq)]
enum Node {
    Dir,
    File(Vec<u8>),
}

#[derive(Clone, Default)]
struct Rig(Arc<Mutex<BTreeMap<String, Node>>>);

impl Rig {
    fn tree(&self) -> BTreeMap<String, Node> {
        self.0.lock().unwrap().clone()
    }
}

/// Same digest form the HOST codec verifies receipts against.
fn digest(b: &[u8]) -> String {
    format!("sha256:{}", sgenaxis_spec::packet::source_sha256(b))
}

impl FileSystemPort for Rig {
    fn exists(&self, p: &str) -> Result<bool, PortError> {
        Ok(self.0.lock().unwrap().contains_key(p))
    }
    fn is_file(&self, p: &str) -> Result<bool, PortError> {
        Ok(matches!(self.0.lock().unwrap().get(p), Some(Node::File(_))))
    }
    fn read(&self, p: &str) -> Result<Vec<u8>, PortError> {
        match self.0.lock().unwrap().get(p) {
            Some(Node::File(b)) => Ok(b.clone()),
            _ => Err(PortError::NotFound(p.into())),
        }
    }
    fn read_to_string(&self, p: &str) -> Result<String, PortError> {
        String::from_utf8(self.read(p)?).map_err(|e| PortError::Other(e.to_string()))
    }
    fn write_atomic(&self, p: &str, _: &[u8]) -> Result<(), PortError> {
        Err(PortError::Other(format!("forbidden HOST write: {p}")))
    }
    fn create_dir_all(&self, p: &str) -> Result<(), PortError> {
        Err(PortError::Other(format!("forbidden recursive create: {p}")))
    }
    fn remove_file(&self, p: &str) -> Result<(), PortError> {
        Err(PortError::Other(format!("forbidden delete: {p}")))
    }
}

impl FileCommitPort for Rig {
    fn create_directory_exclusive(&self, parent: &str, name: &str) -> Result<String, CommitError> {
        let p = format!("{}/{name}", parent.trim_end_matches(['/', '\\']));
        let mut tree = self.0.lock().unwrap();
        if tree.contains_key(&p) {
            return Err(CommitError::AlreadyExists { path: p });
        }
        tree.insert(p.clone(), Node::Dir);
        Ok(p)
    }
    fn acquire_write(&self, p: &str) -> Result<Box<dyn FileWriteLease>, CommitError> {
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
        Ok(match self.rig.0.lock().unwrap().get(&self.path) {
            Some(Node::File(b)) => Some(b.clone()),
            _ => None,
        })
    }
    fn replace_checked(
        &mut self,
        expected: Option<&str>,
        bytes: &[u8],
    ) -> Result<CommitReceipt, CommitError> {
        let mut tree = self.rig.0.lock().unwrap();
        let old = match tree.get(&self.path) {
            Some(Node::File(b)) => Some(digest(b)),
            _ => None,
        };
        if old.as_deref() != expected {
            return Err(CommitError::Conflict {
                expected: expected.map(String::from),
                observed: old,
            });
        }
        tree.insert(self.path.clone(), Node::File(bytes.to_vec()));
        Ok(CommitReceipt {
            target_path: self.path.clone(),
            previous_digest: old,
            committed_digest: digest(bytes),
            transaction_id: "0123456789abcdef0123456789abcdef".into(),
        })
    }
}

// ── Fixtures ─────────────────────────────────────────────────────────────────

fn snapshot() -> OwnerWindowSnapshot {
    OwnerWindowSnapshot {
        owner_window: "main".into(),
        selection_id: "selection-A".into(),
        session_id: "session-A".into(),
    }
}

fn authority() -> DefinitionAuthorityContext {
    snapshot_definition_authority(&snapshot()).expect("fixture owner snapshot is authorized")
}

fn new_location() -> DefinitionLocation {
    DefinitionLocation::NewProject {
        canonical_parent: PARENT.into(),
        single_name: NAME.into(),
    }
}

const STEPS: [WizardStepDto; 6] = [
    WizardStepDto::Basics,
    WizardStepDto::Delivery,
    WizardStepDto::Topology,
    WizardStepDto::Requirements,
    WizardStepDto::TechnologyUi,
    WizardStepDto::Preview,
];

// ── RED: end-to-end bridge persists the definition ───────────────────────────

#[test]
fn wizard_bridge_new_project_commit_persists_definition() {
    let rig = Rig::default();
    let mut store = WizardSessionStore::new();

    // begin → opaque token + initial Basics view.
    let begin = wizard_begin(&mut store, authority(), new_location(), NAME, "先保存需求草稿")
        .expect("wizard_begin should open an in-flight draft and return a token");
    assert_eq!(begin.step, WizardStepDto::Basics);
    assert_eq!(begin.view.name, NAME);
    let token = WizardToken::from_raw(&begin.token);
    assert_eq!(store.len(), 1);

    // apply each of the six steps (Basics patch carries name/purpose).
    for step in STEPS {
        let patch = if step == WizardStepDto::Basics {
            WizardDraftPatch {
                name: Some(NAME.into()),
                purpose: Some("先保存需求草稿".into()),
            }
        } else {
            WizardDraftPatch::default()
        };
        let applied = wizard_apply_step(&mut store, &token, step, patch)
            .expect("wizard_apply_step should validate/apply one step");
        assert!(applied.validation.ok, "step {step:?} validation: {applied:?}");
    }

    // prepare preferences (skip plan).
    let plan = wizard_prepare_preferences(&mut store, &token, PreferenceChoice::Skip)
        .expect("wizard_prepare_preferences should wrap the domain preparer");
    assert_eq!(plan.kind, PreferencePlanKind::Skip);

    // commit: GREEN must bind + save, writing root + .sgenaxis/ definition.
    let receipt = wizard_commit(&rig, &rig, &mut store, &token)
        .expect("end-to-end wizard commit should persist the project definition (RED)");

    // Desired GREEN postconditions (unreached while commit returns the sentinel).
    assert_eq!(receipt.project_root, ROOT);
    assert_eq!(receipt.relative_path, ".sgenaxis/project-definition.json");
    assert!(
        matches!(rig.tree().get(ROOT), Some(Node::Dir)),
        "project root created"
    );
    assert!(
        matches!(rig.tree().get(PATH), Some(Node::File(_))),
        "definition persisted under .sgenaxis/"
    );
    assert_eq!(store.len(), 0, "token cleared after commit");
}

// ── Guard: the opaque token is single-use and cleared on commit ──────────────

#[test]
fn wizard_commit_clears_token_and_rejects_reuse() {
    let rig = Rig::default();
    let mut store = WizardSessionStore::new();
    let begin = wizard_begin(&mut store, authority(), new_location(), NAME, "p").expect("begin");
    let token = WizardToken::from_raw(&begin.token);
    for step in STEPS {
        wizard_apply_step(&mut store, &token, step, WizardDraftPatch::default()).expect("apply");
    }
    wizard_prepare_preferences(&mut store, &token, PreferenceChoice::Skip).expect("prepare");

    wizard_commit(&rig, &rig, &mut store, &token).expect("commit should persist the definition");
    assert_eq!(store.len(), 0, "token cleared on commit");

    // A reused token no longer maps to a live session.
    let err = wizard_commit(&rig, &rig, &mut store, &token)
        .expect_err("a reused (single-use) token must be rejected");
    assert!(
        matches!(err, WizardBridgeError::UnknownToken),
        "reused token must be UnknownToken, got {err:?}"
    );
}

// ── cancel drops in-flight state ─────────────────────────────────────────────

#[test]
fn wizard_cancel_drops_in_flight_session() {
    let mut store = WizardSessionStore::new();
    let begin = wizard_begin(&mut store, authority(), new_location(), NAME, "p").expect("begin");
    let token = WizardToken::from_raw(&begin.token);
    assert_eq!(store.len(), 1);
    wizard_cancel(&mut store, &token).expect("cancel");
    assert_eq!(store.len(), 0);
    assert!(matches!(
        wizard_cancel(&mut store, &token),
        Err(WizardBridgeError::UnknownToken)
    ));
}
