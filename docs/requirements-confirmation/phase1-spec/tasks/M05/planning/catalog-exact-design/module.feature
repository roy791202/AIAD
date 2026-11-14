Feature: Immutable material versions and conservative reference retention
  Background:
    Given an authorized project and current document owner

  Rule: Adopt catalog schema, bounds and immutable explicit version/alias identity; raw catalog hash distinct from semantic fingerprints.
    @BDD-M05-CAT-001
    Scenario: Initialize
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then missing index +explicit initialization yields generation0 empty catalog then one checked transition

    @BDD-M05-CAT-002
    Scenario: Duplicate ID
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then CatalogInvalid duplicate_asset before publication

    @BDD-M05-CAT-003
    Scenario: Duplicate alias
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then CatalogInvalid duplicate_alias; old index unchanged

    @BDD-M05-CAT-004
    Scenario: Unknown key
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then InvalidInput unknown_field exact JSON pointer

    @BDD-M05-CAT-005
    Scenario: Raw duplicate field
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then InvalidInput duplicate_field before typed decode

    @BDD-M05-CAT-006
    Scenario: Wrong project
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then CatalogInvalid project_mismatch

    @BDD-M05-CAT-007
    Scenario: Corrupt blob
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then IntegrityFailure blob_digest, no resolution

    @BDD-M05-CAT-008
    Scenario: Missing version
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then MissingVersion digest_missing, no latest fallback

    @BDD-M05-CAT-009
    Scenario: Legacy exact alias
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then only exact registered string maps; whitespace/case variants UnmappedReference

    @BDD-M05-CAT-010
    Scenario: Repeated pair
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then same immutable pair dedup only after request count check

    @BDD-M05-CAT-011
    Scenario: ID digest conflict
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then different versions remain explicit; conflicting request mapping rejected

    @BDD-M05-CAT-012
    Scenario: Empty reference proof
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then Complete empty only with complete projector; unknown properties block

    @BDD-M05-CAT-013
    Scenario: Media opaque
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then import does not execute/preview content

    @BDD-M05-CAT-014
    Scenario: Generation overflow
      Given Validated base catalog or exact malformed raw fixture
      When validate/resolve catalog
      Then generation u64max rejects next transition

    @BDD-M05-CAT-015
    Scenario: catalog_bytes 16777215
      Given Independent expanded fixture counts catalog_bytes exactly 16777215; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-016
    Scenario: catalog_bytes 16777216
      Given Independent expanded fixture counts catalog_bytes exactly 16777216; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-017
    Scenario: catalog_bytes 16777217
      Given Independent expanded fixture counts catalog_bytes exactly 16777217; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput catalog_bytes limit=16777216 observed=16777217; no index IO

    @BDD-M05-CAT-018
    Scenario: blob_bytes 67108863
      Given Independent expanded fixture counts blob_bytes exactly 67108863; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-019
    Scenario: blob_bytes 67108864
      Given Independent expanded fixture counts blob_bytes exactly 67108864; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-020
    Scenario: blob_bytes 67108865
      Given Independent expanded fixture counts blob_bytes exactly 67108865; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput blob_bytes limit=67108864 observed=67108865; no index IO

    @BDD-M05-CAT-021
    Scenario: assets 4095
      Given Independent expanded fixture counts assets exactly 4095; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-022
    Scenario: assets 4096
      Given Independent expanded fixture counts assets exactly 4096; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-023
    Scenario: assets 4097
      Given Independent expanded fixture counts assets exactly 4097; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput assets limit=4096 observed=4097; no index IO

    @BDD-M05-CAT-024
    Scenario: versions_total 16383
      Given Independent expanded fixture counts versions_total exactly 16383; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-025
    Scenario: versions_total 16384
      Given Independent expanded fixture counts versions_total exactly 16384; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-026
    Scenario: versions_total 16385
      Given Independent expanded fixture counts versions_total exactly 16385; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput versions_total limit=16384 observed=16385; no index IO

    @BDD-M05-CAT-027
    Scenario: pins 8191
      Given Independent expanded fixture counts pins exactly 8191; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-028
    Scenario: pins 8192
      Given Independent expanded fixture counts pins exactly 8192; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-029
    Scenario: pins 8193
      Given Independent expanded fixture counts pins exactly 8193; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput pins limit=8192 observed=8193; no index IO

    @BDD-M05-CAT-030
    Scenario: root_manifests 4095
      Given Independent expanded fixture counts root_manifests exactly 4095; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-031
    Scenario: root_manifests 4096
      Given Independent expanded fixture counts root_manifests exactly 4096; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-032
    Scenario: root_manifests 4097
      Given Independent expanded fixture counts root_manifests exactly 4097; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput root_manifests limit=4096 observed=4097; no index IO

    @BDD-M05-CAT-033
    Scenario: references_per_manifest 4095
      Given Independent expanded fixture counts references_per_manifest exactly 4095; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-034
    Scenario: references_per_manifest 4096
      Given Independent expanded fixture counts references_per_manifest exactly 4096; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-035
    Scenario: references_per_manifest 4097
      Given Independent expanded fixture counts references_per_manifest exactly 4097; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput references_per_manifest limit=4096 observed=4097; no index IO

    @BDD-M05-CAT-036
    Scenario: references_total 32767
      Given Independent expanded fixture counts references_total exactly 32767; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-037
    Scenario: references_total 32768
      Given Independent expanded fixture counts references_total exactly 32768; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-038
    Scenario: references_total 32769
      Given Independent expanded fixture counts references_total exactly 32769; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput references_total limit=32768 observed=32769; no index IO

    @BDD-M05-CAT-039
    Scenario: operations 8191
      Given Independent expanded fixture counts operations exactly 8191; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-040
    Scenario: operations 8192
      Given Independent expanded fixture counts operations exactly 8192; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-041
    Scenario: operations 8193
      Given Independent expanded fixture counts operations exactly 8193; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput operations limit=8192 observed=8193; no index IO

    @BDD-M05-CAT-042
    Scenario: request_references 4095
      Given Independent expanded fixture counts request_references exactly 4095; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-043
    Scenario: request_references 4096
      Given Independent expanded fixture counts request_references exactly 4096; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-044
    Scenario: request_references 4097
      Given Independent expanded fixture counts request_references exactly 4097; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput request_references limit=4096 observed=4097; no index IO

    @BDD-M05-CAT-045
    Scenario: id_utf8_bytes 127
      Given Independent expanded fixture counts id_utf8_bytes exactly 127; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-046
    Scenario: id_utf8_bytes 128
      Given Independent expanded fixture counts id_utf8_bytes exactly 128; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-047
    Scenario: id_utf8_bytes 129
      Given Independent expanded fixture counts id_utf8_bytes exactly 129; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput id_utf8_bytes limit=128 observed=129; no index IO

    @BDD-M05-CAT-048
    Scenario: legacy_alias_utf8_bytes 1023
      Given Independent expanded fixture counts legacy_alias_utf8_bytes exactly 1023; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-049
    Scenario: legacy_alias_utf8_bytes 1024
      Given Independent expanded fixture counts legacy_alias_utf8_bytes exactly 1024; every other guard below limit
      When validate relevant boundary
      Then within limit accepted

    @BDD-M05-CAT-050
    Scenario: legacy_alias_utf8_bytes 1025
      Given Independent expanded fixture counts legacy_alias_utf8_bytes exactly 1025; every other guard below limit
      When validate relevant boundary
      Then Capacity/InvalidInput legacy_alias_utf8_bytes limit=1024 observed=1025; no index IO

  Rule: Adopt MaterialStorePort and Windows adapter +existing FileCommit index transaction; no generic FS bypass or IO journal change.
    @BDD-M05-CAT-051
    Scenario: Blob created
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then blob flush+durable publication completes before index IO

    @BDD-M05-CAT-052
    Scenario: Blob exists
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then verify exact content/size then reuse; never overwrite

    @BDD-M05-CAT-053
    Scenario: Source empty
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then InvalidInput byte_limit; zero catalog writes

    @BDD-M05-CAT-054
    Scenario: Copy failure
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then Storage Copy; old index unchanged

    @BDD-M05-CAT-055
    Scenario: Flush failure
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then Storage Flush; old index unchanged

    @BDD-M05-CAT-056
    Scenario: Index fails precommit
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then old index preserved; orphan retained, not Published

    @BDD-M05-CAT-057
    Scenario: Index uncertain
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then MaterialRecoveryBlocked and all blob/index proof retained

    @BDD-M05-CAT-058
    Scenario: Receipt mismatch
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then IntegrityFailure receipt_mismatch blocks mutations

    @BDD-M05-CAT-059
    Scenario: Two processes
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then second catalog lease Busy; no process-local-only exclusion

    @BDD-M05-CAT-060
    Scenario: Native alias
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then reparse/8.3/hardlink unsafe identities rejected

    @BDD-M05-CAT-061
    Scenario: Response lost
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then replay returns original Published version/pin no duplicate

    @BDD-M05-CAT-062
    Scenario: Unsupported OS
      Given Safe source selection and store plus deterministic adapter failure seam
      When import/publish version
      Then UnsupportedPlatform no store mutation

  Rule: Adopt durable pin-before-reference and receipt-bearing transfer/release with no timeout expiry.
    @BDD-M05-CAT-063
    Scenario: Pin before install
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then no document mutation before durable Held receipt

    @BDD-M05-CAT-064
    Scenario: Snapshot stale
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then StaleCatalog before pin write

    @BDD-M05-CAT-065
    Scenario: Wrong owner
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then PinConflict before transfer

    @BDD-M05-CAT-066
    Scenario: Wrong version set
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then PinConflict proof_mismatch before transfer

    @BDD-M05-CAT-067
    Scenario: Timeout
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then Held survives, no expiry release

    @BDD-M05-CAT-068
    Scenario: Crash reopen
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then durable Held reconstructed; no auto deletion

    @BDD-M05-CAT-069
    Scenario: Pin full
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then CapacityExceeded pins; no document commit

    @BDD-M05-CAT-070
    Scenario: Transfer replay
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then same immutable receipt; no double transition

    @BDD-M05-CAT-071
    Scenario: Release unknown roots
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then Retained Unknown; pin still Held

    @BDD-M05-CAT-072
    Scenario: Release current roots
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then only temporary metadata released; zero blob delete calls

    @BDD-M05-CAT-073
    Scenario: Root transfer failure
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then Held remains after document commit; deferred status

    @BDD-M05-CAT-074
    Scenario: Replay body changed
      Given Catalog generation7 and pin owner/versions tied to captured revision
      When pin/transfer/release
      Then ReplayConflict before IO

  Rule: Adopt all five provider aggregation/epoch/fence lifecycle, persisted formal-document roots and Unknown conservative behavior; preserve accepted S1.
    @BDD-M05-CAT-075
    Scenario: LiveDocuments Missing
      Given All other four kinds Complete empty; named provider Missing
      When evaluate roots/release
      Then retain candidate; Missing root reason; no physical delete

    @BDD-M05-CAT-076
    Scenario: LiveDocuments Unknown
      Given All other four kinds Complete empty; named provider Unknown
      When evaluate roots/release
      Then retain candidate; Unknown root reason; no physical delete

    @BDD-M05-CAT-077
    Scenario: LiveDocuments Stale
      Given All other four kinds Complete empty; named provider Stale
      When evaluate roots/release
      Then retain candidate; Stale root reason; no physical delete

    @BDD-M05-CAT-078
    Scenario: LiveDocuments CompleteReferenced
      Given All other four kinds Complete empty; named provider CompleteReferenced
      When evaluate roots/release
      Then retain candidate; Referenced LiveDocuments; no physical delete

    @BDD-M05-CAT-079
    Scenario: UndoHistory Missing
      Given All other four kinds Complete empty; named provider Missing
      When evaluate roots/release
      Then retain candidate; Missing root reason; no physical delete

    @BDD-M05-CAT-080
    Scenario: UndoHistory Unknown
      Given All other four kinds Complete empty; named provider Unknown
      When evaluate roots/release
      Then retain candidate; Unknown root reason; no physical delete

    @BDD-M05-CAT-081
    Scenario: UndoHistory Stale
      Given All other four kinds Complete empty; named provider Stale
      When evaluate roots/release
      Then retain candidate; Stale root reason; no physical delete

    @BDD-M05-CAT-082
    Scenario: UndoHistory CompleteReferenced
      Given All other four kinds Complete empty; named provider CompleteReferenced
      When evaluate roots/release
      Then retain candidate; Referenced UndoHistory; no physical delete

    @BDD-M05-CAT-083
    Scenario: RedoHistory Missing
      Given All other four kinds Complete empty; named provider Missing
      When evaluate roots/release
      Then retain candidate; Missing root reason; no physical delete

    @BDD-M05-CAT-084
    Scenario: RedoHistory Unknown
      Given All other four kinds Complete empty; named provider Unknown
      When evaluate roots/release
      Then retain candidate; Unknown root reason; no physical delete

    @BDD-M05-CAT-085
    Scenario: RedoHistory Stale
      Given All other four kinds Complete empty; named provider Stale
      When evaluate roots/release
      Then retain candidate; Stale root reason; no physical delete

    @BDD-M05-CAT-086
    Scenario: RedoHistory CompleteReferenced
      Given All other four kinds Complete empty; named provider CompleteReferenced
      When evaluate roots/release
      Then retain candidate; Referenced RedoHistory; no physical delete

    @BDD-M05-CAT-087
    Scenario: RecoverySnapshots Missing
      Given All other four kinds Complete empty; named provider Missing
      When evaluate roots/release
      Then retain candidate; Missing root reason; no physical delete

    @BDD-M05-CAT-088
    Scenario: RecoverySnapshots Unknown
      Given All other four kinds Complete empty; named provider Unknown
      When evaluate roots/release
      Then retain candidate; Unknown root reason; no physical delete

    @BDD-M05-CAT-089
    Scenario: RecoverySnapshots Stale
      Given All other four kinds Complete empty; named provider Stale
      When evaluate roots/release
      Then retain candidate; Stale root reason; no physical delete

    @BDD-M05-CAT-090
    Scenario: RecoverySnapshots CompleteReferenced
      Given All other four kinds Complete empty; named provider CompleteReferenced
      When evaluate roots/release
      Then retain candidate; Referenced RecoverySnapshots; no physical delete

    @BDD-M05-CAT-091
    Scenario: InFlightTransactions Missing
      Given All other four kinds Complete empty; named provider Missing
      When evaluate roots/release
      Then retain candidate; Missing root reason; no physical delete

    @BDD-M05-CAT-092
    Scenario: InFlightTransactions Unknown
      Given All other four kinds Complete empty; named provider Unknown
      When evaluate roots/release
      Then retain candidate; Unknown root reason; no physical delete

    @BDD-M05-CAT-093
    Scenario: InFlightTransactions Stale
      Given All other four kinds Complete empty; named provider Stale
      When evaluate roots/release
      Then retain candidate; Stale root reason; no physical delete

    @BDD-M05-CAT-094
    Scenario: InFlightTransactions CompleteReferenced
      Given All other four kinds Complete empty; named provider CompleteReferenced
      When evaluate roots/release
      Then retain candidate; Referenced InFlightTransactions; no physical delete

    @BDD-M05-CAT-095
    Scenario: All documents
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then closed persisted document ref retained; current-window scan insufficient

    @BDD-M05-CAT-096
    Scenario: Epoch revoked
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then old window roots cannot replace new owner epoch

    @BDD-M05-CAT-097
    Scenario: Lock ordering
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then collect provider fences before catalog lease; no owner callback while index lock held

    @BDD-M05-CAT-098
    Scenario: Provider disappears
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then kind Unknown; old root not silently removed

    @BDD-M05-CAT-099
    Scenario: Undo only
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then before-version retained across live edit

    @BDD-M05-CAT-100
    Scenario: Redo only
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then redo-version retained until authoritative replacement proof

    @BDD-M05-CAT-101
    Scenario: Recovery absent
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then Unknown RecoverySnapshots; cannot assume empty

    @BDD-M05-CAT-102
    Scenario: S1 retained
      Given Registered full provider inventory and exact revisions
      When publish/evaluate root bundle
      Then existing five-kind domain behavior/tests unchanged

  Rule: Adopt proposed M03/M04 amendments for candidate deferred retention and save promotion-before-ACK, explicit binding projector contract.
    @BDD-M05-CAT-103
    Scenario: Candidate commit then root fails
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then InstalledRetentionDeferred; content installed, Held retained; no false rollback

    @BDD-M05-CAT-104
    Scenario: Save transfer succeeds
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then file receipt → catalog transfer receipt → semantic ACK; exact call order

    @BDD-M05-CAT-105
    Scenario: Save transfer fails
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then CommittedAckDeferred; file remains committed, Held retained, no ACK

    @BDD-M05-CAT-106
    Scenario: Semantic raw distinct
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then semantic A/raw B/catalog C never substituted

    @BDD-M05-CAT-107
    Scenario: Newer document revision
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then ACK captured revision only; newer live dirty remains

    @BDD-M05-CAT-108
    Scenario: Explicit Pending
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then binding Pending retained, execution blocked; pinned save allowed

    @BDD-M05-CAT-109
    Scenario: Missing target
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then InvalidBinding missing_target; no install

    @BDD-M05-CAT-110
    Scenario: Viewer ephemeral
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then mock/selection makes no content pins/root writes

    @BDD-M05-CAT-111
    Scenario: Lost owner after file commit
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then deferred proof remains bound to original generation

    @BDD-M05-CAT-112
    Scenario: M07 publish fails
      Given M03/M04 fake owner+store with capture and exact reference proof
      When install/save/transfer
      Then Recovery Held retained; no snapshot baseline ACK

  Rule: Adopt no physical GC/repair/automatic media execution in this slice; retain requirements as separate tasks, not module-complete.
    @BDD-M05-CAT-113
    Scenario: No delete surface
      Given Retained/orphan versions and diagnostic inspection
      When request cleanup/reopen
      Then policy no remove API/command exposed

    @BDD-M05-CAT-114
    Scenario: GC eligibility
      Given Retained/orphan versions and diagnostic inspection
      When request cleanup/reopen
      Then policy S1 EligibleForCleanup causes zero physical deletion

    @BDD-M05-CAT-115
    Scenario: Orphan retained
      Given Retained/orphan versions and diagnostic inspection
      When request cleanup/reopen
      Then policy no startup orphan sweep

    @BDD-M05-CAT-116
    Scenario: Repair blocked
      Given Retained/orphan versions and diagnostic inspection
      When request cleanup/reopen
      Then policy uncertain journal cannot clear via reopen success alone

  Rule: Adopt closed UI/internal ACL, error/replay/capacity policies and exact candidate envelope/test gates.
    @BDD-M05-CAT-117
    Scenario: Viewer denied
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then PermissionDenied before inner parse/IO

    @BDD-M05-CAT-118
    Scenario: Forged project
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then PermissionDenied no OS path leakage

    @BDD-M05-CAT-119
    Scenario: Unknown DTO field
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then InvalidInput unknown_field

    @BDD-M05-CAT-120
    Scenario: Cursor stale
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then StaleCatalog before returning mixed-generation page

    @BDD-M05-CAT-121
    Scenario: Version selection
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then explicit immutable pair sent to document edit, no auto latest

    @BDD-M05-CAT-122
    Scenario: Import failed UI
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then previous list/selection preserved; failure status

    @BDD-M05-CAT-123
    Scenario: Capacity no eviction
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then operations full rejects new operation before writes

    @BDD-M05-CAT-124
    Scenario: Revoked replay caller
      Given Editor/Viewer trusted instances and captured catalog generation
      When invoke material action
      Then PermissionDenied before cached receipt return
