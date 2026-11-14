Feature: M03 authoritative design owner and detached Viewer
  Background:
    Given trusted binding and dependency spies record all changes

  Rule: M03-H2-B001 unbound
    Scenario: M03-H2-T001
      Given manifest binding absent
      When binding/edit requested
      Then MissingBinding no session/new UUID/IO

  Rule: M03-H2-B002 duplicate view
    Scenario: M03-H2-T002
      Given same existing trusted document opened twice
      When binding/edit requested
      Then same owner/session, no second DocumentSession

  Rule: M03-H2-B003 forged root
    Scenario: M03-H2-T003
      Given request contains project_root/digest/owner authority
      When binding/edit requested
      Then InvalidRequest, no lookup/mutation

  Rule: M03-H2-B004 identity
    Scenario: M03-H2-T004
      Given document UUID maps another reference
      When binding/edit requested
      Then IdentityConflict no remap

  Rule: M03-H2-B005 writer
    Scenario: M03-H2-T005
      Given viewer requests edit
      When binding/edit requested
      Then WriterRequired or UnauthorizedCaller before candidate/commit

  Rule: M03-H2-B006 unknown
    Scenario: M03-H2-T006
      Given inner raw text unknown schema field
      When candidate prepare
      Then CodecRejected exact C1 pointer

  Rule: M03-H2-B007 duplicate
    Scenario: M03-H2-T007
      Given duplicate raw key
      When candidate prepare
      Then CodecRejected duplicate pointer before typed loss

  Rule: M03-H2-B008 number
    Scenario: M03-H2-T008
      Given raw precise decimal cannot roundtrip
      When candidate prepare
      Then CodecRejected number error before JS decode

  Rule: M03-H2-B009 outer
    Scenario: M03-H2-T009
      Given unknown outer field
      When candidate prepare
      Then InvalidRequest no effects

  Rule: M03-H2-B010 oversize
    Scenario: M03-H2-T010
      Given outer>32MiB or inner>16MiB
      When candidate prepare
      Then ResourceLimit exact outer/inner field before parse

  Rule: M03-H2-B011 numeric revision
    Scenario: M03-H2-T011
      Given revision supplied JS Number
      When candidate prepare
      Then InvalidRequest Type

  Rule: M03-H2-B012 u64 overflow
    Scenario: M03-H2-T012
      Given revision18446744073709551616
      When candidate prepare
      Then InvalidRequest Range

  Rule: M03-H2-B013 valid
    Scenario: M03-H2-T013
      Given valid changed candidate current owner
      When prepare/install/render
      Then exactly one S1 Edit revision+1/history+1

  Rule: M03-H2-B014 same
    Scenario: M03-H2-T014
      Given semantic identical candidate
      When prepare/install/render
      Then changed=false,no S1 commit/revision

  Rule: M03-H2-B015 stale
    Scenario: M03-H2-T015
      Given owner advanced after prepare
      When prepare/install/render
      Then StaleRevision; old content/history/baselines unchanged

  Rule: M03-H2-B016 generation
    Scenario: M03-H2-T016
      Given writer transferred after prepare
      When prepare/install/render
      Then StaleOwner; no install

  Rule: M03-H2-B017 reuse
    Scenario: M03-H2-T017
      Given new request ID targets candidate installed once
      When prepare/install/render
      Then CandidateUsed,no second mutation

  Rule: M03-H2-B018 request collision
    Scenario: M03-H2-T018
      Given same request ID changed raw capture
      When prepare/install/render
      Then RequestConflict

  Rule: M03-H2-B019 duplicate ID
    Scenario: M03-H2-T019
      Given two nodes share stable ID
      When prepare/install/render
      Then AmbiguousStableId, no install

  Rule: M03-H2-B020 parent missing
    Scenario: M03-H2-T020
      Given node parent absent
      When prepare/install/render
      Then ParentMissing,no install

  Rule: M03-H2-B021 cycle
    Scenario: M03-H2-T021
      Given parent graph cycle
      When prepare/install/render
      Then ParentCycle,no install

  Rule: M03-H2-B022 unsupported
    Scenario: M03-H2-T022
      Given unknown node type
      When prepare/install/render
      Then read-only intact node list; edit/mocks/save disabled

  Rule: M03-H2-B023 form absent
    Scenario: M03-H2-T023
      Given no root Form
      When prepare/install/render
      Then read-only no inserted Form

  Rule: M03-H2-B024 grid
    Scenario: M03-H2-T024
      Given fraction/outside display range
      When prepare/install/render
      Then content exact, view fallback only

  Rule: M03-H2-B025 install replay
    Scenario: M03-H2-T025
      Given same request/capture already installed
      When install replayed
      Then original result replayed=true, no second commit, no stale UI projection overwrite

  Rule: M03-H2-B026 undo replay
    Scenario: M03-H2-T026
      Given same undo request/capture already completed
      When undo replayed
      Then original result only, no second Undo

  Rule: M03-H2-B027 capacity
    Scenario: M03-H2-T027
      Given 128 keys binding or1024 runtime full
      When new mutation request
      Then ResourceLimit request_keys before reservation/commit

  Rule: M03-H2-B028 Button Activate
    Scenario: M03-H2-T028
      Given supported immutable node and seq1
      When matching mock payload
      Then only detached value changes; seq2; S1 revision/dirty/history/baselines unchanged

  Rule: M03-H2-B029 CheckBox SetToggle
    Scenario: M03-H2-T029
      Given supported immutable node and seq1
      When matching mock payload
      Then only detached value changes; seq2; S1 revision/dirty/history/baselines unchanged

  Rule: M03-H2-B030 TextBox SetText
    Scenario: M03-H2-T030
      Given supported immutable node and seq1
      When matching mock payload
      Then only detached value changes; seq2; S1 revision/dirty/history/baselines unchanged

  Rule: M03-H2-B031 NumberInput SetNumber
    Scenario: M03-H2-T031
      Given supported immutable node and seq1
      When matching mock payload
      Then only detached value changes; seq2; S1 revision/dirty/history/baselines unchanged

  Rule: M03-H2-B032 ComboBox SelectItem
    Scenario: M03-H2-T032
      Given supported immutable node and seq1
      When matching mock payload
      Then only detached value changes; seq2; S1 revision/dirty/history/baselines unchanged

  Rule: M03-H2-B033 payload mismatch
    Scenario: M03-H2-T033
      Given action Activate with checked payload
      When intent submitted
      Then InvalidRequest InvalidActionPayload; seq unchanged

  Rule: M03-H2-B034 unsupported action
    Scenario: M03-H2-T034
      Given button SetText
      When intent submitted
      Then UnsupportedAction; seq unchanged

  Rule: M03-H2-B035 stale sequence
    Scenario: M03-H2-T035
      Given received seq0 expected1
      When intent submitted
      Then SequenceConflict

  Rule: M03-H2-B036 duplicate replay
    Scenario: M03-H2-T036
      Given same accepted seq1 sent twice
      When intent submitted
      Then one effect then SequenceConflict

  Rule: M03-H2-B037 overflow
    Scenario: M03-H2-T037
      Given expected seq u64max
      When intent submitted
      Then SequenceOverflow close; no partial mock effect

  Rule: M03-H2-B038 text
    Scenario: M03-H2-T038
      Given text<script> executable-looking
      When intent submitted
      Then literal textContent only, no evaluation

  Rule: M03-H2-B039 item
    Scenario: M03-H2-T039
      Given ComboBox item label matches but ID absent
      When intent submitted
      Then UnsupportedAction, no label lookup

  Rule: M03-H2-B040 scope
    Scenario: M03-H2-T040
      Given unknown scope or uiExclusive true
      When intent submitted
      Then no capability elevation

  Rule: M03-H2-B041 material
    Scenario: M03-H2-T041
      Given required asset absent
      When intent submitted
      Then MissingMaterial placeholder/no IO

  Rule: M03-H2-B042 target
    Scenario: M03-H2-T042
      Given declared target binding missing
      When intent submitted
      Then MissingBindingTarget/no guessed binding

  Rule: M03-H2-B043 revision
    Scenario: M03-H2-T043
      Given source edited since preview began
      When intent submitted
      Then StaleRevision no mock update; stale projection badge

  Rule: M03-H2-B044 main
    Scenario: M03-H2-T044
      Given actual main window instance
      When candidate/save invoked
      Then only current main/editor writer allowed; viewer/settings/remote/dev rejected; no fallback typed legacy save

  Rule: M03-H2-B045 ui-editor
    Scenario: M03-H2-T045
      Given actual ui-editor window instance
      When candidate/save invoked
      Then only current main/editor writer allowed; viewer/settings/remote/dev rejected; no fallback typed legacy save

  Rule: M03-H2-B046 ui-viewer
    Scenario: M03-H2-T046
      Given actual ui-viewer window instance
      When candidate/save invoked
      Then only current main/editor writer allowed; viewer/settings/remote/dev rejected; no fallback typed legacy save

  Rule: M03-H2-B047 settings
    Scenario: M03-H2-T047
      Given actual settings window instance
      When candidate/save invoked
      Then only current main/editor writer allowed; viewer/settings/remote/dev rejected; no fallback typed legacy save

  Rule: M03-H2-B048 remote
    Scenario: M03-H2-T048
      Given actual remote window instance
      When candidate/save invoked
      Then only current main/editor writer allowed; viewer/settings/remote/dev rejected; no fallback typed legacy save

  Rule: M03-H2-B049 dev-localhost:1420
    Scenario: M03-H2-T049
      Given actual dev-localhost:1420 window instance
      When candidate/save invoked
      Then only current main/editor writer allowed; viewer/settings/remote/dev rejected; no fallback typed legacy save

  Rule: M03-H2-B050 close
    Scenario: M03-H2-T050
      Given dirty owner discard=false
      When operation completes
      Then owner retained,no autosave

  Rule: M03-H2-B051 destroy
    Scenario: M03-H2-T051
      Given writer instance destroyed
      When operation completes
      Then nonce retired, candidate/previews revoked

  Rule: M03-H2-B052 refresh late
    Scenario: M03-H2-T052
      Given owner changes during refresh
      When operation completes
      Then old projection retained stale,no new owner install

  Rule: M03-H2-B053 transfer
    Scenario: M03-H2-T053
      Given writer grants to trustededitor
      When operation completes
      Then generation+1,no content/history/revision mutation

  Rule: M03-H2-B054 transfer viewer
    Scenario: M03-H2-T054
      Given target ui-viewer
      When operation completes
      Then UnauthorizedCaller/no grant

  Rule: M03-H2-B055 root change
    Scenario: M03-H2-T055
      Given settings root successfully changes
      When operation completes
      Then binding revoked; failed settings save leaves original

  Rule: M03-H2-B056 persistence
    Scenario: M03-H2-T056
      Given M04-S2 unavailable
      When operation completes
      Then DependencyNotReady M04_S2 no FS

  Rule: M03-H2-B057 C1
    Scenario: M03-H2-T057
      Given C1 unavailable
      When operation completes
      Then DependencyNotReady C1_CODEC no lossy fallback

  Rule: M03-H2-B058 uidesign_save_design
    Scenario: M03-H2-T058
      Given legacy typed doc/raw-root args
      When old command invoked
      Then DESIGN_OWNER_REQUIRED; no save/load/build filesystem call

  Rule: M03-H2-B059 uidesign_load_design
    Scenario: M03-H2-T059
      Given legacy typed doc/raw-root args
      When old command invoked
      Then DESIGN_OWNER_REQUIRED; no save/load/build filesystem call

  Rule: M03-H2-B060 uidesign_build_preview
    Scenario: M03-H2-T060
      Given legacy typed doc/raw-root args
      When old command invoked
      Then DESIGN_OWNER_REQUIRED; no save/load/build filesystem call

  Rule: M03-H2-B061 selection
    Scenario: M03-H2-T061
      Given current document
      When Editor selects node
      Then ephemeral only; no S1 Edit/Undo/M07 event

  Rule: M03-H2-B062 undo
    Scenario: M03-H2-T062
      Given one prior accepted edit
      When authorized undo
      Then existing S1 revision/history semantics retained; preview revoked once
