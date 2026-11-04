Feature: Authenticated deterministic dual-product generation
  Background:
    Given an authorized project and current generation reviewer

  Rule: Retain adopted C+B direction and S1; adopt authenticated source/fence/approval and saved-design input envelope.
    @BDD-M02-GEN-001
    Scenario: Missing decisions
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then SaveDefinitionOnly exact missing paths, zero render/store writes

    @BDD-M02-GEN-002
    Scenario: Approval text forged
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then not authenticated; missing/error no publish

    @BDD-M02-GEN-003
    Scenario: Approved revision hash wrong
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then integrity error before policy/store

    @BDD-M02-GEN-004
    Scenario: Definition changed
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then StalePlan before active update

    @BDD-M02-GEN-005
    Scenario: Approval revoked
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then StalePlan before active update

    @BDD-M02-GEN-006
    Scenario: Template replaced
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then TemplateMismatch/hash error

    @BDD-M02-GEN-007
    Scenario: Design dirty
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then DesignSaveRequired no implicit save

    @BDD-M02-GEN-008
    Scenario: Design ACK deferred
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then DesignSaveRequired no render

    @BDD-M02-GEN-009
    Scenario: Unsupported design
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then exact source path no partial success

    @BDD-M02-GEN-010
    Scenario: Digest prefix
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then HOST explicit conversions, S1 receives sha256: syntax

    @BDD-M02-GEN-011
    Scenario: Fence missing
      Given Trusted source/fake owner evidence with named change
      When prepare/confirm
      Then DependencyNotReady no race-prone publish

  Rule: Adopt deterministic14-resource render recipes/token escaping/unsupported matrix and mandatory template golden+standalone lock gate.
    @BDD-M02-GEN-012
    Scenario: Dual outputs
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then all14 exact paths and both products present

    @BDD-M02-GEN-013
    Scenario: Literal text injection
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then quotes/<script>/backticks stay inert data

    @BDD-M02-GEN-014
    Scenario: Unknown token
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then RenderError unknown_token before FS

    @BDD-M02-GEN-015
    Scenario: Unclosed token
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then RenderError unclosed_token

    @BDD-M02-GEN-016
    Scenario: Recursive substitution
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then inserted {{TOKEN}} not re-expanded

    @BDD-M02-GEN-017
    Scenario: UI schema data
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then no inline executable props/event text

    @BDD-M02-GEN-018
    Scenario: Package identity
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then UUID-derived ASCII identifiers only

    @BDD-M02-GEN-019
    Scenario: Golden absent
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then DependencyNotReady template_golden, no placeholder lock

    @BDD-M02-GEN-020
    Scenario: Version source changed
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then template version/digest required new reference

    @BDD-M02-GEN-021
    Scenario: No business fake success
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then generated behavior explicitly unimplemented

    @BDD-M02-GEN-022
    Scenario: Wrong target
      Given Fixed template sources and raw input fixtures
      When render source preview
      Then existing S1 UnsupportedTarget; no fallback

  Rule: Adopt existing proposed Store3traits/10methods, schema/limits/layout and no-replace sealing; native evidence remains required.
    @BDD-M02-GEN-023
    Scenario: active_bytes 16383
      Given Independent expanded byte/count fixture exactly16383, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-024
    Scenario: active_bytes 16384
      Given Independent expanded byte/count fixture exactly16384, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-025
    Scenario: active_bytes 16385
      Given Independent expanded byte/count fixture exactly16385, other guards valid
      When validate source/store boundary
      Then limit error active_bytes, no activation

    @BDD-M02-GEN-026
    Scenario: store_marker_bytes 4095
      Given Independent expanded byte/count fixture exactly4095, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-027
    Scenario: store_marker_bytes 4096
      Given Independent expanded byte/count fixture exactly4096, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-028
    Scenario: store_marker_bytes 4097
      Given Independent expanded byte/count fixture exactly4097, other guards valid
      When validate source/store boundary
      Then limit error store_marker_bytes, no activation

    @BDD-M02-GEN-029
    Scenario: template_manifest_bytes 262143
      Given Independent expanded byte/count fixture exactly262143, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-030
    Scenario: template_manifest_bytes 262144
      Given Independent expanded byte/count fixture exactly262144, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-031
    Scenario: template_manifest_bytes 262145
      Given Independent expanded byte/count fixture exactly262145, other guards valid
      When validate source/store boundary
      Then limit error template_manifest_bytes, no activation

    @BDD-M02-GEN-032
    Scenario: artifact_manifest_bytes 1048575
      Given Independent expanded byte/count fixture exactly1048575, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-033
    Scenario: artifact_manifest_bytes 1048576
      Given Independent expanded byte/count fixture exactly1048576, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-034
    Scenario: artifact_manifest_bytes 1048577
      Given Independent expanded byte/count fixture exactly1048577, other guards valid
      When validate source/store boundary
      Then limit error artifact_manifest_bytes, no activation

    @BDD-M02-GEN-035
    Scenario: files 127
      Given Independent expanded byte/count fixture exactly127, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-036
    Scenario: files 128
      Given Independent expanded byte/count fixture exactly128, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-037
    Scenario: files 129
      Given Independent expanded byte/count fixture exactly129, other guards valid
      When validate source/store boundary
      Then limit error files, no activation

    @BDD-M02-GEN-038
    Scenario: each_file_bytes 4194303
      Given Independent expanded byte/count fixture exactly4194303, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-039
    Scenario: each_file_bytes 4194304
      Given Independent expanded byte/count fixture exactly4194304, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-040
    Scenario: each_file_bytes 4194305
      Given Independent expanded byte/count fixture exactly4194305, other guards valid
      When validate source/store boundary
      Then limit error each_file_bytes, no activation

    @BDD-M02-GEN-041
    Scenario: total_payload_bytes 33554431
      Given Independent expanded byte/count fixture exactly33554431, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-042
    Scenario: total_payload_bytes 33554432
      Given Independent expanded byte/count fixture exactly33554432, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-043
    Scenario: total_payload_bytes 33554433
      Given Independent expanded byte/count fixture exactly33554433, other guards valid
      When validate source/store boundary
      Then limit error total_payload_bytes, no activation

    @BDD-M02-GEN-044
    Scenario: relative_path_ascii_bytes 239
      Given Independent expanded byte/count fixture exactly239, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-045
    Scenario: relative_path_ascii_bytes 240
      Given Independent expanded byte/count fixture exactly240, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-046
    Scenario: relative_path_ascii_bytes 241
      Given Independent expanded byte/count fixture exactly241, other guards valid
      When validate source/store boundary
      Then limit error relative_path_ascii_bytes, no activation

    @BDD-M02-GEN-047
    Scenario: path_components 15
      Given Independent expanded byte/count fixture exactly15, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-048
    Scenario: path_components 16
      Given Independent expanded byte/count fixture exactly16, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-049
    Scenario: path_components 17
      Given Independent expanded byte/count fixture exactly17, other guards valid
      When validate source/store boundary
      Then limit error path_components, no activation

    @BDD-M02-GEN-050
    Scenario: definition_name_utf8_bytes 1023
      Given Independent expanded byte/count fixture exactly1023, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-051
    Scenario: definition_name_utf8_bytes 1024
      Given Independent expanded byte/count fixture exactly1024, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-052
    Scenario: definition_name_utf8_bytes 1025
      Given Independent expanded byte/count fixture exactly1025, other guards valid
      When validate source/store boundary
      Then limit error definition_name_utf8_bytes, no activation

    @BDD-M02-GEN-053
    Scenario: definition_purpose_utf8_bytes 16383
      Given Independent expanded byte/count fixture exactly16383, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-054
    Scenario: definition_purpose_utf8_bytes 16384
      Given Independent expanded byte/count fixture exactly16384, other guards valid
      When validate source/store boundary
      Then within inclusive limit accepted

    @BDD-M02-GEN-055
    Scenario: definition_purpose_utf8_bytes 16385
      Given Independent expanded byte/count fixture exactly16385, other guards valid
      When validate source/store boundary
      Then limit error definition_purpose_utf8_bytes, no activation

    @BDD-M02-GEN-056
    Scenario: Case collision
      Given Native/fake store stages and exact file table
      When write/seal version
      Then reject before stage

    @BDD-M02-GEN-057
    Scenario: Prefix collision
      Given Native/fake store stages and exact file table
      When write/seal version
      Then file/dir collision rejected

    @BDD-M02-GEN-058
    Scenario: Reserved Windows path
      Given Native/fake store stages and exact file table
      When write/seal version
      Then reject exact path

    @BDD-M02-GEN-059
    Scenario: Bootstrap unknown namespace
      Given Native/fake store stages and exact file table
      When write/seal version
      Then no takeover/cleanup

    @BDD-M02-GEN-060
    Scenario: Bootstrap interrupted
      Given Native/fake store stages and exact file table
      When write/seal version
      Then RecoveryRequired no auto repair

    @BDD-M02-GEN-061
    Scenario: Write failed
      Given Native/fake store stages and exact file table
      When write/seal version
      Then old active untouched; owned stage abort evidence

    @BDD-M02-GEN-062
    Scenario: Seal destination exists
      Given Native/fake store stages and exact file table
      When write/seal version
      Then AlreadyExists even empty; no replace

    @BDD-M02-GEN-063
    Scenario: Extra tree file
      Given Native/fake store stages and exact file table
      When write/seal version
      Then Integrity rejects seal

    @BDD-M02-GEN-064
    Scenario: Corrupt tree
      Given Native/fake store stages and exact file table
      When write/seal version
      Then hash mismatch no activate

    @BDD-M02-GEN-065
    Scenario: Sealed not active
      Given Native/fake store stages and exact file table
      When write/seal version
      Then retain VersionSealedNotActivated

    @BDD-M02-GEN-066
    Scenario: Abort fails
      Given Native/fake store stages and exact file table
      When write/seal version
      Then stage retained diagnostic, no fake cleanup

  Rule: Adopt IO-owned crate-private read-coordination helper scope and exact reader proof lifetime; no public IO/journal change.
    @BDD-M02-GEN-067
    Scenario: Reader writer overlap
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then Busy; no uncommitted active read

    @BDD-M02-GEN-068
    Scenario: Multiple readers
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then same verified immutable version permitted

    @BDD-M02-GEN-069
    Scenario: Missing sidecar
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then reader no create, explicit error

    @BDD-M02-GEN-070
    Scenario: Nonterminal journal
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then reader refuses, no cleanup

    @BDD-M02-GEN-071
    Scenario: Terminal mismatch
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then reader Integrity/RecoveryRequired

    @BDD-M02-GEN-072
    Scenario: Snapshot lifetime
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then lease held until all bytes copied

    @BDD-M02-GEN-073
    Scenario: Read-only project
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then read handle works only existing valid coordination

    @BDD-M02-GEN-074
    Scenario: Alias reparse
      Given Shared read/exclusive writer process fixtures with IO journal states
      When read active/store
      Then native identity reject unsafe root/stage

  Rule: Adopt preview/confirm/activation/cancel/replay/deferred proof lifecycle and source-only completion meaning.
    @BDD-M02-GEN-075
    Scenario: Prepare cancel
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then zero filesystem writes

    @BDD-M02-GEN-076
    Scenario: Plan expired
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then PlanExpired no stage

    @BDD-M02-GEN-077
    Scenario: Preview tampered
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then StalePlan before writer

    @BDD-M02-GEN-078
    Scenario: Active CAS conflict
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then old active not overwritten

    @BDD-M02-GEN-079
    Scenario: Receipt target wrong
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then block proof retain no Activated

    @BDD-M02-GEN-080
    Scenario: Receipt previous wrong
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then block proof retain

    @BDD-M02-GEN-081
    Scenario: Receipt new wrong
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then block proof retain

    @BDD-M02-GEN-082
    Scenario: Receipt transaction empty
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then block proof retain

    @BDD-M02-GEN-083
    Scenario: Cancel after activate starts
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then await actual outcome no false Cancelled

    @BDD-M02-GEN-084
    Scenario: Owner detached commit
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then ActivatedDeliveryDeferred with proof

    @BDD-M02-GEN-085
    Scenario: Same request
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then same proof no second activation

    @BDD-M02-GEN-086
    Scenario: Replay different body
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then ReplayConflict

    @BDD-M02-GEN-087
    Scenario: Restart lost result
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then manual proof reconciliation, no exactly-once claim

    @BDD-M02-GEN-088
    Scenario: Sequence overflow
      Given Preview plan and exact base/manifest/active receipt fixtures
      When confirm/publish
      Then no active update

  Rule: Adopt explicit M01/M03/M04 input/consumer seams without moving definition/design ownership or saving implicitly.
    @BDD-M02-GEN-089
    Scenario: M01 Draft only
      Given Joint source/consumer contracts represented by approved future fakes
      When prepare/consume generation
      Then no invented Defined/approvalRefs

    @BDD-M02-GEN-090
    Scenario: M04 baseline
      Given Joint source/consumer contracts represented by approved future fakes
      When prepare/consume generation
      Then generation changes neither formal nor recovery baseline

    @BDD-M02-GEN-091
    Scenario: M03 preview
      Given Joint source/consumer contracts represented by approved future fakes
      When prepare/consume generation
      Then closed immutable data consumer, no generated-code execution

    @BDD-M02-GEN-092
    Scenario: Saved design later changed
      Given Joint source/consumer contracts represented by approved future fakes
      When prepare/consume generation
      Then new active version tagged outdated, immutable old proof retained

    @BDD-M02-GEN-093
    Scenario: One design owner
      Given Joint source/consumer contracts represented by approved future fakes
      When prepare/consume generation
      Then no competing registry

    @BDD-M02-GEN-094
    Scenario: Missing native provider
      Given Joint source/consumer contracts represented by approved future fakes
      When prepare/consume generation
      Then DependencyNotReady no raw root fallback

  Rule: Adopt closed commands/errors, exact candidate envelope, BDD/TDD and staged acceptance; no Skeleton before readiness gates.
    @BDD-M02-GEN-095
    Scenario: Viewer denied
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then PermissionDenied before IO

    @BDD-M02-GEN-096
    Scenario: UI arbitrary files
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then closed DTO rejects

    @BDD-M02-GEN-097
    Scenario: Capacity full
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then reject before FS no silent eviction

    @BDD-M02-GEN-098
    Scenario: Generation not build
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then UI source-active only; build/release NOT RUN

    @BDD-M02-GEN-099
    Scenario: Refresh Busy
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then prior cache stale tag no current proof

    @BDD-M02-GEN-100
    Scenario: Unknown schema
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then no execute/repair/fallback

    @BDD-M02-GEN-101
    Scenario: No old version deletion
      Given Editor/Viewer binding and deterministic UI/fake backend
      When invoke generation lifecycle
      Then zero sealed-delete calls
