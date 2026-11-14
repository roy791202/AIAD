use sgenaxis_host::packet_admission::{
    authorize_packet_bound_start, derive_packet_admission, PacketAdmissionRejection as Reject,
    PacketAdmissionVerdict as Verdict, PacketBoundStartError, PacketBoundStartRequest as Request,
    VerifiedPacketFacts as Facts,
};
use sgenaxis_host::{EnvelopeDto, GuardPacketDto, RedKindDto};

// The admission logic compares normalized ABSOLUTE project roots, so the
// fixture root must be absolute on the running OS: a drive-anchored path on
// Windows, a POSIX-absolute path elsewhere. (See
// root_comparison_is_absolute_and_platform_normalized for the semantics.)
fn project_root() -> &'static str {
    if cfg!(windows) { "D:/work/project" } else { "/work/project" }
}
fn other_root() -> &'static str {
    if cfg!(windows) { "D:/other" } else { "/other" }
}

fn make_request() -> Request {
    Request {
        expected_project_root: project_root().into(),
        source_path: "design/main.ess".into(),
        task_id: "TASK-1".into(),
        module_id: "MODULE-1".into(),
        expected_source_sha256: "a".repeat(64),
        approved_spec_revision: "spec-r7".into(),
    }
}

fn verified_facts() -> Facts {
    Facts {
        normalized_project_root: project_root().into(),
        source_path: "design/main.ess".into(),
        task_id: "TASK-1".into(),
        module_id: "MODULE-1".into(),
        source_sha256: "a".repeat(64),
        spec_revision: "spec-r7".into(),
        spec_module_id: "MODULE-1".into(),
        spec_approved: true,
        spec_content_hash: Some("spec-hash-7".into()),
        task_in_approved_envelope: true,
        module_in_approved_envelope: true,
        envelope_complete: true,
        qualified_red: true,
        ui_references_resolved: true,
    }
}

fn approved_guard() -> GuardPacketDto {
    GuardPacketDto {
        envelope: EnvelopeDto {
            id: "ENV-1".into(),
            approved: true,
            primary_module: "MODULE-1".into(),
            integration_modules: vec![],
            allowed_paths: vec!["design/**".into()],
            protected_paths: vec!["docs/approved/**".into()],
            module_path_prefixes: vec![],
        },
        red: RedKindDto::Behavioral,
        change_paths: vec![],
    }
}

#[test]
fn complete_host_verified_binding_is_admissible_even_though_legacy_packet_stays_not_ready() {
    assert_eq!(
        derive_packet_admission(&make_request(), &verified_facts()),
        Verdict::Admissible
    );
}

#[test]
fn unresolved_ui_reference_rejects_with_a_typed_reason() {
    let mut facts = verified_facts();
    facts.ui_references_resolved = false;
    assert_eq!(
        derive_packet_admission(&make_request(), &facts),
        Verdict::Rejected(Reject::UiReferenceUnresolved)
    );
}

#[test]
fn every_identity_and_authority_binding_fails_closed() {
    let cases: Vec<(fn(&mut Request, &mut Facts), Reject)> = vec![
        (
            |_request, facts| facts.normalized_project_root = other_root().into(),
            Reject::ProjectRootMismatch,
        ),
        (
            |request, _facts| request.source_path = "../outside.ess".into(),
            Reject::SourcePathOutsideProject,
        ),
        (
            |_request, facts| facts.source_sha256 = "b".repeat(64),
            Reject::SourceChanged,
        ),
        (
            |_request, facts| facts.task_in_approved_envelope = false,
            Reject::TaskNotInApprovedSpec,
        ),
        (
            |_request, facts| facts.module_in_approved_envelope = false,
            Reject::ModuleNotInApprovedSpec,
        ),
        (
            |_request, facts| facts.spec_approved = false,
            Reject::SpecRevisionMismatch,
        ),
        (
            |_request, facts| facts.envelope_complete = false,
            Reject::EnvelopeIncomplete,
        ),
        (
            |_request, facts| facts.qualified_red = false,
            Reject::ReadinessEvidenceMissing,
        ),
    ];
    for (mutate, expected) in cases {
        let mut request = make_request();
        let mut facts = verified_facts();
        mutate(&mut request, &mut facts);
        assert_eq!(
            derive_packet_admission(&request, &facts),
            Verdict::Rejected(expected)
        );
    }
}

#[test]
fn mismatched_task_module_and_spec_revision_reject_independently() {
    let mut request = make_request();
    let facts = verified_facts();
    request.task_id = "TASK-OTHER".into();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::TaskNotInApprovedSpec)
    );

    let mut request = make_request();
    request.module_id = "MODULE-OTHER".into();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::ModuleNotInApprovedSpec)
    );

    let mut request = make_request();
    request.approved_spec_revision = "spec-old".into();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::SpecRevisionMismatch)
    );
}

#[test]
fn missing_approved_spec_fingerprint_and_malformed_source_hash_reject() {
    let mut facts = verified_facts();
    facts.spec_content_hash = None;
    assert_eq!(
        derive_packet_admission(&make_request(), &facts),
        Verdict::Rejected(Reject::ReadinessEvidenceMissing)
    );

    let mut request = make_request();
    request.expected_source_sha256 = "not-a-sha".into();
    assert_eq!(
        derive_packet_admission(&request, &verified_facts()),
        Verdict::Rejected(Reject::SourceChanged)
    );
}

#[test]
fn empty_identity_fields_never_admit_even_when_presence_flags_are_claimed() {
    let mut request = make_request();
    let mut facts = verified_facts();
    request.task_id.clear();
    facts.task_id.clear();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::TaskNotInApprovedSpec)
    );

    let mut request = make_request();
    let mut facts = verified_facts();
    request.module_id.clear();
    facts.module_id.clear();
    facts.spec_module_id.clear();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::ModuleNotInApprovedSpec)
    );

    let mut request = make_request();
    let mut facts = verified_facts();
    request.approved_spec_revision.clear();
    facts.spec_revision.clear();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::SpecRevisionMismatch)
    );
}

#[test]
fn root_comparison_is_absolute_and_platform_normalized() {
    let mut request = make_request();
    let mut facts = verified_facts();
    if cfg!(windows) {
        request.expected_project_root = "d:\\WORK\\Project\\".into();
        facts.normalized_project_root = "D:/work/project".into();
        assert_eq!(
            derive_packet_admission(&request, &facts),
            Verdict::Admissible
        );
    }

    request.expected_project_root = "relative/project".into();
    facts.normalized_project_root = "relative/project".into();
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::ProjectRootMismatch)
    );

    let mut request = make_request();
    let mut facts = verified_facts();
    if cfg!(windows) {
        request.expected_project_root = "D:/Work/Project".into();
        facts.normalized_project_root = "D:/work/Other".into();
    } else {
        request.expected_project_root = "/Work/Project".into();
        facts.normalized_project_root = "/work/project".into();
    }
    assert_eq!(
        derive_packet_admission(&request, &facts),
        Verdict::Rejected(Reject::ProjectRootMismatch)
    );

    if cfg!(windows) {
        let mut request = make_request();
        let mut facts = verified_facts();
        request.expected_project_root = r"\\server\share\..\..\other\share".into();
        facts.normalized_project_root = r"\\other\share".into();
        assert_eq!(
            derive_packet_admission(&request, &facts),
            Verdict::Rejected(Reject::ProjectRootMismatch),
            "UNC parent traversal must not escape the server/share anchor"
        );

        let mut request = make_request();
        let mut facts = verified_facts();
        request.expected_project_root = r"\\SERVER\SHARE\folder\..".into();
        facts.normalized_project_root = r"\\server\share".into();
        assert_eq!(
            derive_packet_admission(&request, &facts),
            Verdict::Admissible,
            "normalization inside a UNC share may reduce to its anchor"
        );
    }
}

#[test]
fn controlled_start_authorization_requires_admission_and_independent_guard() {
    let pass = authorize_packet_bound_start(&make_request(), &verified_facts(), &approved_guard())
        .expect("both independent predicates allow");
    assert_eq!(pass.work_item_id.as_deref(), Some("TASK-1"));

    let mut guard = approved_guard();
    guard.envelope.approved = false;
    assert!(matches!(
        authorize_packet_bound_start(&make_request(), &verified_facts(), &guard),
        Err(PacketBoundStartError::GuardDenied(_))
    ));

    let mut facts = verified_facts();
    facts.ui_references_resolved = false;
    assert_eq!(
        authorize_packet_bound_start(&make_request(), &facts, &approved_guard()),
        Err(PacketBoundStartError::Admission(
            Reject::UiReferenceUnresolved
        ))
    );
}

#[test]
fn guard_primary_module_mismatch_rejects_packet_bound_start() {
    let mut guard = approved_guard();
    guard.envelope.primary_module = "MODULE-OTHER".into();
    assert!(matches!(
        authorize_packet_bound_start(&make_request(), &verified_facts(), &guard),
        Err(PacketBoundStartError::GuardDenied(_))
    ));
}
