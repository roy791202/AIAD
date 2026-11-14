Feature: M01 six-step project definition wizard
  Background:
    Given native authority and storage doubles record every side effect

  Rule: M01-S3-B001 local
    Scenario: M01-S3-T001
      Given main+tauri://localhost
      When start/begin requested
      Then caller passes only, no selection authority inferred

  Rule: M01-S3-B002 foreign
    Scenario: M01-S3-T002
      Given settings local window
      When start/begin requested
      Then UnauthorizedCaller, zero native/store calls

  Rule: M01-S3-B003 remote
    Scenario: M01-S3-T003
      Given main https://example.com
      When start/begin requested
      Then UnauthorizedCaller, zero effects

  Rule: M01-S3-B004 dev
    Scenario: M01-S3-T004
      Given main http://localhost:1420
      When start/begin requested
      Then UnauthorizedCaller, zero effects

  Rule: M01-S3-B005 forged
    Scenario: M01-S3-T005
      Given JSON includes owner_window/root/digest
      When start/begin requested
      Then InvalidRequest unknown field before authority use

  Rule: M01-S3-B006 cancel
    Scenario: M01-S3-T006
      Given native picker returns None
      When location captured or revalidated
      Then cancelled, previous selection intact

  Rule: M01-S3-B007 directory
    Scenario: M01-S3-T007
      Given fixed local directory with no reparse components
      When location captured or revalidated
      Then selected capability, no write

  Rule: M01-S3-B008 UNC
    Scenario: M01-S3-T008
      Given UNC selected
      When location captured or revalidated
      Then UnsupportedLocation

  Rule: M01-S3-B009 relative
    Scenario: M01-S3-T009
      Given drive-relative or dotdot path
      When location captured or revalidated
      Then UnsupportedLocation

  Rule: M01-S3-B010 ADS
    Scenario: M01-S3-T010
      Given ADS path
      When location captured or revalidated
      Then UnsupportedLocation

  Rule: M01-S3-B011 junction
    Scenario: M01-S3-T011
      Given ancestor junction observed
      When location captured or revalidated
      Then ReparseRejected, all acquired handles closed

  Rule: M01-S3-B012 symlink
    Scenario: M01-S3-T012
      Given leaf directory symlink
      When location captured or revalidated
      Then ReparseRejected

  Rule: M01-S3-B013 short
    Scenario: M01-S3-T013
      Given 8.3 spelling differs from long native name
      When location captured or revalidated
      Then AliasRejected

  Rule: M01-S3-B014 case
    Scenario: M01-S3-T014
      Given case-only spelling difference same native identity
      When location captured or revalidated
      Then accepted canonical selection

  Rule: M01-S3-B015 identity
    Scenario: M01-S3-T015
      Given reopened path file-id changed
      When location captured or revalidated
      Then LocationChanged, zero S2 calls

  Rule: M01-S3-B016 denied
    Scenario: M01-S3-T016
      Given component read-attributes denied
      When location captured or revalidated
      Then NativeAccessDenied, zero store calls

  Rule: M01-S3-B017 infofail
    Scenario: M01-S3-T017
      Given identity query fails
      When location captured or revalidated
      Then NativeObservationFailed stage identity, zero store calls

  Rule: M01-S3-B018 platform
    Scenario: M01-S3-T018
      Given non-Windows adapter
      When location captured or revalidated
      Then UnsupportedPlatform

  Rule: M01-S3-B019 handle
    Scenario: M01-S3-T019
      Given capture fails after third component open
      When location captured or revalidated
      Then exactly all 3 owned handles close; none leaked

  Rule: M01-S3-B020 S3-OW-07
    Scenario: M01-S3-T020
      Given no native selection capability
      When UI submits a parent display path
      Then SELECTION_REQUIRED

  Rule: M01-S3-B021 S3-OW-08
    Scenario: M01-S3-T021
      Given selection belongs to another owner
      When begin requested
      Then SELECTION_OWNER_MISMATCH

  Rule: M01-S3-B022 S3-OW-09
    Scenario: M01-S3-T022
      Given selection is existing-project-only
      When new project begin requested
      Then SELECTION_PURPOSE_MISMATCH

  Rule: M01-S3-B023 S3-OW-10
    Scenario: M01-S3-T023
      Given picker captured generation 7, current generation 8
      When native result returns
      Then STALE_OWNER and generation 8 unchanged

  Rule: M01-S3-B024 S3-OW-11
    Scenario: M01-S3-T024
      Given live owner has selection A
      When picker cancelled
      Then selection A remains; no new ID

  Rule: M01-S3-B025 S3-OW-12
    Scenario: M01-S3-T025
      Given save request is already captured
      When window destroyed
      Then owner revoked, captured request detached

  Rule: M01-S3-B026 S3-OW-13
    Scenario: M01-S3-T026
      Given saved draft exists and old capability expired
      When explicit reopen succeeds
      Then fresh generation and no prior capability revived

  Rule: M01-S3-B027 S3-OW-14
    Scenario: M01-S3-T027
      Given existing registered project and lease snapshot
      When wizard begins
      Then WORK registry/leases and HostSettings unchanged

  Rule: M01-S3-B028 S3-OW-15
    Scenario: M01-S3-T028
      Given captured request committed after owner changed
      When completion delivered
      Then proof retained, no binding or cleanup

  Rule: M01-S3-B029 S3-RQ-01
    Scenario: M01-S3-T029
      Given {'case': 'same_inflight', 'capture': 'same', 'record': 'running', 'authority': 'current'}
      When request submitted
      Then {'result': 'IN_FLIGHT', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B030 S3-RQ-02
    Scenario: M01-S3-T030
      Given {'case': 'changed_inflight', 'capture': 'changed', 'record': 'running', 'authority': 'current'}
      When request submitted
      Then {'result': 'REQUEST_ID_CONFLICT', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B031 S3-RQ-03
    Scenario: M01-S3-T031
      Given {'case': 'same_committed', 'capture': 'same', 'record': 'committed', 'authority': 'current'}
      When request submitted
      Then {'result': 'original committed outcome', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B032 S3-RQ-04
    Scenario: M01-S3-T032
      Given {'case': 'changed_committed', 'capture': 'changed', 'record': 'committed', 'authority': 'current'}
      When request submitted
      Then {'result': 'REQUEST_ID_CONFLICT', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B033 S3-RQ-05
    Scenario: M01-S3-T033
      Given {'case': 'same_failed', 'capture': 'same', 'record': 'precommit_failed', 'authority': 'current'}
      When request submitted
      Then {'result': 'original failure', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B034 S3-RQ-06
    Scenario: M01-S3-T034
      Given {'case': 'same_partial', 'capture': 'same', 'record': 'partial', 'authority': 'current'}
      When request submitted
      Then {'result': 'original partial evidence', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B035 S3-RQ-07
    Scenario: M01-S3-T035
      Given {'case': 'same_recovery', 'capture': 'same', 'record': 'recovery_required', 'authority': 'current'}
      When request submitted
      Then {'result': 'original recovery evidence', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B036 S3-RQ-08
    Scenario: M01-S3-T036
      Given {'case': 'foreign_owner', 'capture': 'same', 'record': 'committed', 'authority': 'foreign'}
      When request submitted
      Then {'result': 'UNAUTHORIZED', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B037 S3-RQ-09
    Scenario: M01-S3-T037
      Given {'case': 'stale_epoch', 'capture': 'same', 'record': 'committed', 'authority': 'expired'}
      When request submitted
      Then {'result': 'STALE_OWNER', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B038 S3-RQ-10
    Scenario: M01-S3-T038
      Given {'case': 'capacity', 'capture': 'new', 'record': 'absent_full', 'authority': 'current'}
      When request submitted
      Then {'result': 'REQUEST_CAPACITY', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B039 S3-RQ-11
    Scenario: M01-S3-T039
      Given {'case': 'late_committed', 'capture': 'same', 'record': 'completing_commit', 'authority': 'detached'}
      When request submitted
      Then {'result': 'committed / detached', 'additional_store_calls': 0, 'automatic_project_switch': False}

  Rule: M01-S3-B040 S3-RQ-12
    Scenario: M01-S3-T040
      Given {'case': 'new_request', 'capture': 'new', 'record': 'absent', 'authority': 'current'}
      When request submitted
      Then {'result': 'reserve then invoke S2 once', 'additional_store_calls': 1, 'automatic_project_switch': False}

  Rule: M01-S3-B041 NotBound
    Scenario: M01-S3-T041
      Given S2 returns NotBound
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B042 InvalidInput
    Scenario: M01-S3-T042
      Given S2 returns InvalidInput
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B043 Codec
    Scenario: M01-S3-T043
      Given S2 returns Codec
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B044 UnsupportedSchema
    Scenario: M01-S3-T044
      Given S2 returns UnsupportedSchema
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B045 ExistingTarget
    Scenario: M01-S3-T045
      Given S2 returns ExistingTarget
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B046 IdentityConflict
    Scenario: M01-S3-T046
      Given S2 returns IdentityConflict
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B047 RevisionConflict
    Scenario: M01-S3-T047
      Given S2 returns RevisionConflict
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B048 Busy
    Scenario: M01-S3-T048
      Given S2 returns Busy
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B049 StorageFailure
    Scenario: M01-S3-T049
      Given S2 returns StorageFailure
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B050 PartialProjectCreated
    Scenario: M01-S3-T050
      Given S2 returns PartialProjectCreated
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B051 RecoveryRequired
    Scenario: M01-S3-T051
      Given S2 returns RecoveryRequired
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B052 InvalidLocation
    Scenario: M01-S3-T052
      Given S2 returns InvalidLocation
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B053 CommitEvidenceMismatch
    Scenario: M01-S3-T053
      Given S2 returns CommitEvidenceMismatch
      When result mapped
      Then exact tag and all fields retained; no success/binding; no additional IO

  Rule: M01-S3-B054 preset
    Scenario: M01-S3-T054
      Given valid existing preset ID
      When set_preferences
      Then one revision increment and server prepared plan installed; no disk creation

  Rule: M01-S3-B055 bad_import
    Scenario: M01-S3-T055
      Given malformed imported JSON
      When set_preferences
      Then field error, previous revision/plan/draft unchanged

  Rule: M01-S3-B056 plan_forge
    Scenario: M01-S3-T056
      Given update preferenceSource differs from server prepared plan
      When update
      Then InvalidRequest preference_plan_mismatch; zero store calls

  Rule: M01-S3-B057 precision
    Scenario: M01-S3-T057
      Given revision 9007199254740993
      When DTO roundtrip
      Then decimal string unchanged

  Rule: M01-S3-B058 max
    Scenario: M01-S3-T058
      Given revision 18446744073709551615
      When update
      Then RevisionOverflow no mutation

  Rule: M01-S3-B059 shape
    Scenario: M01-S3-T059
      Given unknown nested request property
      When decode
      Then InvalidRequest exact JSON pointer

  Rule: M01-S3-B060 proof
    Scenario: M01-S3-T060
      Given definition committed but settings persist fails
      When completion mapped
      Then committed_unbound with original proof, current binding unchanged

  Rule: M01-S3-B061 late
    Scenario: M01-S3-T061
      Given owner changed after successful store
      When completion delivered
      Then detached with proof and no new root bind

  Rule: M01-S3-B062 basics draft save
    Scenario: M01-S3-T062
      Given valid structural draft at basics
      When Save Draft
      Then update acknowledged then one save, last_step basics restored on reopen; unresolved decisions retained

  Rule: M01-S3-B063 basics validation
    Scenario: M01-S3-T063
      Given invalid edited field at basics
      When Next/Save clicked
      Then field error + focus summary; original server draft/revision unchanged; no store

  Rule: M01-S3-B064 delivery draft save
    Scenario: M01-S3-T064
      Given valid structural draft at delivery
      When Save Draft
      Then update acknowledged then one save, last_step delivery restored on reopen; unresolved decisions retained

  Rule: M01-S3-B065 delivery validation
    Scenario: M01-S3-T065
      Given invalid edited field at delivery
      When Next/Save clicked
      Then field error + focus summary; original server draft/revision unchanged; no store

  Rule: M01-S3-B066 topology draft save
    Scenario: M01-S3-T066
      Given valid structural draft at topology
      When Save Draft
      Then update acknowledged then one save, last_step topology restored on reopen; unresolved decisions retained

  Rule: M01-S3-B067 topology validation
    Scenario: M01-S3-T067
      Given invalid edited field at topology
      When Next/Save clicked
      Then field error + focus summary; original server draft/revision unchanged; no store

  Rule: M01-S3-B068 requirements draft save
    Scenario: M01-S3-T068
      Given valid structural draft at requirements
      When Save Draft
      Then update acknowledged then one save, last_step requirements restored on reopen; unresolved decisions retained

  Rule: M01-S3-B069 requirements validation
    Scenario: M01-S3-T069
      Given invalid edited field at requirements
      When Next/Save clicked
      Then field error + focus summary; original server draft/revision unchanged; no store

  Rule: M01-S3-B070 technology_ui draft save
    Scenario: M01-S3-T070
      Given valid structural draft at technology_ui
      When Save Draft
      Then update acknowledged then one save, last_step technology_ui restored on reopen; unresolved decisions retained

  Rule: M01-S3-B071 technology_ui validation
    Scenario: M01-S3-T071
      Given invalid edited field at technology_ui
      When Next/Save clicked
      Then field error + focus summary; original server draft/revision unchanged; no store

  Rule: M01-S3-B072 preview draft save
    Scenario: M01-S3-T072
      Given valid structural draft at preview
      When Save Draft
      Then update acknowledged then one save, last_step preview restored on reopen; unresolved decisions retained

  Rule: M01-S3-B073 preview validation
    Scenario: M01-S3-T073
      Given invalid edited field at preview
      When Next/Save clicked
      Then field error + focus summary; original server draft/revision unchanged; no store

  Rule: M01-S3-B074 host_new_project_directory
    Scenario: M01-S3-T074
      Given sentinel existing file/directory and legacy invocation
      When old API invoked
      Then WIZARD_REQUIRED, zero writes/deletes and no current-project switch

  Rule: M01-S3-B075 host_create_project_directory
    Scenario: M01-S3-T075
      Given sentinel existing file/directory and legacy invocation
      When old API invoked
      Then WIZARD_REQUIRED, zero writes/deletes and no current-project switch

  Rule: M01-S3-B076 host_create_project_with_preferences
    Scenario: M01-S3-T076
      Given sentinel existing file/directory and legacy invocation
      When old API invoked
      Then WIZARD_REQUIRED, zero writes/deletes and no current-project switch

  Rule: M01-S3-B077 menu
    Scenario: M01-S3-T077
      Given current project A
      When new action via menu
      Then one wizard opened, no deprecated creator invoke; cancellation leaves A

  Rule: M01-S3-B078 toolbar
    Scenario: M01-S3-T078
      Given current project A
      When new action via toolbar
      Then one wizard opened, no deprecated creator invoke; cancellation leaves A

  Rule: M01-S3-B079 keyboard
    Scenario: M01-S3-T079
      Given current project A
      When new action via keyboard
      Then one wizard opened, no deprecated creator invoke; cancellation leaves A

  Rule: M01-S3-B080 close
    Scenario: M01-S3-T080
      Given unsaved dirty draft
      When close cancelled
      Then same draft and owner remain

  Rule: M01-S3-B081 detach
    Scenario: M01-S3-T081
      Given request in-flight
      When confirmed close
      Then owner revoked, request finishes detached; no rollback

  Rule: M01-S3-B082 reload
    Scenario: M01-S3-T082
      Given old generation live
      When main UI initializes new instance
      Then old owner/capabilities revoked, no implicit save

  Rule: M01-S3-B083 rootchange
    Scenario: M01-S3-T083
      Given settings save successful changes root
      When binding installed
      Then old generation invalidated

  Rule: M01-S3-B084 rootfail
    Scenario: M01-S3-T084
      Given settings save failed
      When root bind attempted
      Then old owner/root remain

  Rule: M01-S3-B085 lock
    Scenario: M01-S3-T085
      Given native picker/IO blocks at barrier
      When other projection requested
      Then no HostState/AppState lock held during blocking call

  Rule: M01-S3-B086 no trusted approvals
    Scenario: M01-S3-T086
      Given all visible decisions complete but refs untrusted/absent
      When finish review
      Then DraftSavedMissingDecisions includes approvalRefs; saved mode Draft, generation_allowed=false, no generator calls

  Rule: M01-S3-B087 forged approval
    Scenario: M01-S3-T087
      Given UI supplies approvalRefs/mode Defined
      When update/finalize
      Then unknown field rejection; no mode promotion

  Rule: M01-S3-B088 legacy adopt
    Scenario: M01-S3-T088
      Given legacy root with ESS/preferences/manifest sentinel hashes
      When explicit adopt
      Then new definition only; legacy hashes unchanged; exclusive target conflict blocks

  Rule: M01-S3-B089 UUID collision
    Scenario: M01-S3-T089
      Given selected root has UUID already mapped to another root
      When open
      Then IdentityConflict; no automatic registration/remap/copy
