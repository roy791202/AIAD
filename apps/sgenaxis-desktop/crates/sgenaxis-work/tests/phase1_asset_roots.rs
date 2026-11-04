//! M05-S1 executable contracts. Fixtures are raw data, not target-policy results.
use sgenaxis_work::asset_reference::*;

const KINDS: [RootKind; 5] = [
    RootKind::LiveDocuments,
    RootKind::UndoHistory,
    RootKind::RedoHistory,
    RootKind::RecoverySnapshots,
    RootKind::InFlightTransactions,
];
fn digest(c: char) -> String {
    format!("sha256:{}", c.to_string().repeat(64))
}
fn fixture() -> (AssetCandidate, RootSnapshot, EvaluationContext) {
    (
        AssetCandidate {
            asset_id: "asset-1".into(),
            content_digest: digest('a'),
            owned_by_operation: Some("operation-1".into()),
        },
        RootSnapshot {
            project_id: "project-1".into(),
            session_id: "session-1".into(),
            observations: KINDS
                .iter()
                .map(|&kind| RootObservation {
                    kind,
                    revision: "revision-1".into(),
                    completeness: Completeness::Complete,
                    references: vec![],
                })
                .collect(),
        },
        EvaluationContext {
            project_id: "project-1".into(),
            session_id: "session-1".into(),
            operation_id: "operation-1".into(),
            expected_root_revisions: KINDS
                .iter()
                .map(|&kind| (kind, "revision-1".into()))
                .collect(),
        },
    )
}
fn reference(owner: &str) -> RootReference {
    RootReference {
        asset_id: "asset-1".into(),
        content_digest: digest('a'),
        owner_id: owner.into(),
    }
}
fn eligible(c: &AssetCandidate) -> RetentionDecision {
    RetentionDecision::EligibleForCleanup {
        asset_id: c.asset_id.clone(),
        content_digest: c.content_digest.clone(),
    }
}
fn assert_decision(
    c: &AssetCandidate,
    r: &RootSnapshot,
    x: &EvaluationContext,
    expected: RetentionDecision,
) {
    let before = (c.clone(), r.clone(), x.clone());
    assert_eq!(evaluate_asset_retention(c, r, x), Ok(expected));
    assert_eq!(
        (c.clone(), r.clone(), x.clone()),
        before,
        "pure boundary must not mutate inputs"
    );
}
#[test]
fn fixture_has_exactly_five_complete_roots_and_matching_revisions() {
    let (c, r, x) = fixture();
    assert_eq!(r.observations.len(), 5);
    assert_eq!(x.expected_root_revisions.len(), 5);
    for (i, k) in KINDS.iter().enumerate() {
        assert_eq!(r.observations[i].kind, *k);
        assert_eq!(r.observations[i].completeness, Completeness::Complete);
        assert_eq!(
            x.expected_root_revisions[i],
            (*k, r.observations[i].revision.clone())
        );
    }
    assert_eq!(c.owned_by_operation.as_ref(), Some(&x.operation_id));
    assert_eq!(digest('a').len(), 71);
}
#[test]
fn m05_empty_complete_roots_yield_identity_only_eligibility() {
    let (c, r, x) = fixture();
    assert_decision(&c, &r, &x, eligible(&c));
}
macro_rules! root_retains {
    ($name:ident,$index:expr,$owner:expr) => {
        #[test]
        fn $name() {
            let (c, mut r, x) = fixture();
            r.observations[$index].references.push(reference($owner));
            assert_decision(
                &c,
                &r,
                &x,
                RetentionDecision::Retain {
                    reasons: vec![RetentionReason::Referenced {
                        kind: KINDS[$index],
                        owner_id: $owner.into(),
                    }],
                },
            );
        }
    };
}
root_retains!(m05_live_document_reference_retains, 0, "document-current");
root_retains!(m05_other_document_reference_retains, 0, "document-other");
root_retains!(m05_undo_history_retains, 1, "history-undo");
root_retains!(m05_redo_history_retains, 2, "history-redo");
root_retains!(m05_retained_snapshot_retains, 3, "snapshot-retained");
root_retains!(m05_unprocessed_snapshot_retains, 3, "snapshot-unprocessed");
root_retains!(m05_inflight_transaction_retains, 4, "transaction-pending");
macro_rules! unknown_root {
    ($name:ident,$i:expr) => {
        #[test]
        fn $name() {
            let (c, mut r, x) = fixture();
            r.observations[$i].completeness = Completeness::Unknown;
            assert_decision(
                &c,
                &r,
                &x,
                RetentionDecision::Retain {
                    reasons: vec![RetentionReason::RootsIncomplete { kind: KINDS[$i] }],
                },
            );
        }
    };
}
unknown_root!(m05_unknown_live_documents_retains, 0);
unknown_root!(m05_unknown_undo_retains, 1);
unknown_root!(m05_unknown_redo_retains, 2);
unknown_root!(m05_unknown_snapshot_retains, 3);
unknown_root!(m05_unknown_transaction_retains, 4);
#[test]
fn m05_missing_provider_is_not_complete_empty() {
    let (c, mut r, x) = fixture();
    r.observations.remove(3);
    assert_decision(
        &c,
        &r,
        &x,
        RetentionDecision::Retain {
            reasons: vec![RetentionReason::RootsIncomplete {
                kind: RootKind::RecoverySnapshots,
            }],
        },
    );
}
#[test]
fn m05_stale_root_revision_retains() {
    let (c, mut r, x) = fixture();
    r.observations[1].revision = "revision-2".into();
    assert_decision(
        &c,
        &r,
        &x,
        RetentionDecision::Retain {
            reasons: vec![RetentionReason::StaleRoots {
                kind: RootKind::UndoHistory,
            }],
        },
    );
}
#[test]
fn m05_unowned_candidate_retains() {
    let (mut c, r, x) = fixture();
    c.owned_by_operation = None;
    assert_decision(
        &c,
        &r,
        &x,
        RetentionDecision::Retain {
            reasons: vec![RetentionReason::NotOwnedByOperation],
        },
    );
}
#[test]
fn m05_other_operation_candidate_retains() {
    let (mut c, r, x) = fixture();
    c.owned_by_operation = Some("other-operation".into());
    assert_decision(
        &c,
        &r,
        &x,
        RetentionDecision::Retain {
            reasons: vec![RetentionReason::NotOwnedByOperation],
        },
    );
}
#[test]
fn m05_same_asset_id_conflicting_digest_retains() {
    let (c, mut r, x) = fixture();
    let mut v = reference("other-document");
    v.content_digest = digest('b');
    r.observations[0].references.push(v);
    assert_decision(
        &c,
        &r,
        &x,
        RetentionDecision::Retain {
            reasons: vec![RetentionReason::IdentityConflict {
                asset_id: c.asset_id.clone(),
            }],
        },
    );
}
#[test]
fn m05_other_asset_does_not_pin_candidate() {
    let (c, mut r, x) = fixture();
    let mut v = reference("other-document");
    v.asset_id = "other-asset".into();
    r.observations[0].references.push(v);
    assert_decision(&c, &r, &x, eligible(&c));
}
#[test]
fn m05_reasons_sorted_by_root_then_owner_and_deduplicated() {
    let (c, mut r, x) = fixture();
    r.observations[3].references = vec![reference("snapshot")];
    r.observations[0].references = vec![
        reference("z-document"),
        reference("a-document"),
        reference("a-document"),
    ];
    r.observations.reverse();
    let expected = RetentionDecision::Retain {
        reasons: vec![
            RetentionReason::Referenced {
                kind: RootKind::LiveDocuments,
                owner_id: "a-document".into(),
            },
            RetentionReason::Referenced {
                kind: RootKind::LiveDocuments,
                owner_id: "z-document".into(),
            },
            RetentionReason::Referenced {
                kind: RootKind::RecoverySnapshots,
                owner_id: "snapshot".into(),
            },
        ],
    };
    assert_decision(&c, &r, &x, expected.clone());
    r.observations.reverse();
    assert_decision(&c, &r, &x, expected);
}
macro_rules! invalid {
    ($name:ident,$change:expr) => {
        #[test]
        fn $name() {
            let (mut c, mut r, mut x) = fixture();
            ($change)(&mut c, &mut r, &mut x);
            let before = (c.clone(), r.clone(), x.clone());
            match evaluate_asset_retention(&c, &r, &x) {
                Err(RetentionError::InvalidInput { field, reason }) => {
                    assert!(!field.is_empty());
                    assert!(!reason.is_empty());
                }
                other => panic!("expected typed malformed-input rejection: {other:?}"),
            };
            assert_eq!((c, r, x), before);
        }
    };
}
invalid!(
    m05_empty_asset_id,
    |c: &mut AssetCandidate, _: &mut RootSnapshot, _: &mut EvaluationContext| c.asset_id.clear()
);
invalid!(
    m05_asset_id_257_bytes,
    |c: &mut AssetCandidate, _: &mut RootSnapshot, _: &mut EvaluationContext| c.asset_id =
        "a".repeat(257)
);
invalid!(
    m05_asset_id_utf8_exceeds_bytes,
    |c: &mut AssetCandidate, _: &mut RootSnapshot, _: &mut EvaluationContext| c.asset_id =
        "\u{00e9}".repeat(129)
);
invalid!(
    m05_nul_asset_id,
    |c: &mut AssetCandidate, _: &mut RootSnapshot, _: &mut EvaluationContext| c.asset_id =
        "a\0b".into()
);
invalid!(
    m05_bad_digest,
    |c: &mut AssetCandidate, _: &mut RootSnapshot, _: &mut EvaluationContext| c.content_digest =
        "bad".into()
);
invalid!(
    m05_uppercase_digest,
    |c: &mut AssetCandidate, _: &mut RootSnapshot, _: &mut EvaluationContext| c.content_digest =
        digest('A')
);
invalid!(
    m05_duplicate_root_kind,
    |_: &mut AssetCandidate, r: &mut RootSnapshot, _: &mut EvaluationContext| r
        .observations
        .push(r.observations[0].clone())
);
invalid!(
    m05_duplicate_expected_revision,
    |_: &mut AssetCandidate, _: &mut RootSnapshot, x: &mut EvaluationContext| x
        .expected_root_revisions
        .push(x.expected_root_revisions[0].clone())
);
invalid!(
    m05_project_identity_mismatch,
    |_: &mut AssetCandidate, r: &mut RootSnapshot, _: &mut EvaluationContext| r.project_id =
        "other-project".into()
);
invalid!(
    m05_session_identity_mismatch,
    |_: &mut AssetCandidate, r: &mut RootSnapshot, _: &mut EvaluationContext| r.session_id =
        "other-session".into()
);
invalid!(
    m05_empty_root_revision,
    |_: &mut AssetCandidate, r: &mut RootSnapshot, _: &mut EvaluationContext| r.observations[0]
        .revision
        .clear()
);
fn irrelevant(n: usize) -> Vec<RootReference> {
    (0..n)
        .map(|i| RootReference {
            asset_id: format!("other-{i}"),
            content_digest: digest('b'),
            owner_id: format!("owner-{i}"),
        })
        .collect()
}
macro_rules! valid_id {
    ($name:ident,$value:expr) => {
        #[test]
        fn $name() {
            let (mut c, r, x) = fixture();
            c.asset_id = $value;
            assert_decision(&c, &r, &x, eligible(&c));
        }
    };
}
valid_id!(m05_asset_id_one_byte, "a".into());
valid_id!(m05_asset_id_256_bytes, "a".repeat(256));
valid_id!(m05_asset_id_256_utf8_bytes, "\u{00e9}".repeat(128));
macro_rules! count_boundary {
    ($name:ident,$n:expr,$valid:expr) => {
        #[test]
        fn $name() {
            let (c, mut r, x) = fixture();
            r.observations[0].references = irrelevant($n);
            if $valid {
                assert_decision(&c, &r, &x, eligible(&c));
            } else {
                assert!(matches!(
                    evaluate_asset_retention(&c, &r, &x),
                    Err(RetentionError::InvalidInput { .. })
                ));
            }
        }
    };
}
count_boundary!(m05_reference_count_4095, 4095, true);
count_boundary!(m05_reference_count_4096, 4096, true);
count_boundary!(m05_reference_count_4097, 4097, false);
macro_rules! total_boundary {
    ($name:ident,$total:expr,$valid:expr) => {
        #[test]
        fn $name() {
            let (c, mut r, x) = fixture();
            let mut left = $total;
            for o in &mut r.observations {
                let n = left.min(4096);
                o.references = irrelevant(n);
                left -= n;
            }
            assert_eq!(left, 0);
            if $valid {
                assert_decision(&c, &r, &x, eligible(&c));
            } else {
                assert!(matches!(
                    evaluate_asset_retention(&c, &r, &x),
                    Err(RetentionError::InvalidInput { .. })
                ));
            }
        }
    };
}
total_boundary!(m05_total_references_16383, 16383, true);
total_boundary!(m05_total_references_16384, 16384, true);
total_boundary!(m05_total_references_16385, 16385, false);
