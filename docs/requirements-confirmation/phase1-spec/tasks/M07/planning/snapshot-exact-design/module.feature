Feature: Durable self-contained recovery snapshots
  Background:
    Given an authorized project and a stable document owner

  Rule: Adopt stable capture/SGA-RECOVERY-FP-v1 and exact existing S1 timing/completion mapping, independent baselines.
    @BDD-M07-SNAP-001
    Scenario: 59999ms
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then NotDue no capture

    @BDD-M07-SNAP-002
    Scenario: 60000ms
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then stable changed content requests capture

    @BDD-M07-SNAP-003
    Scenario: 60001ms
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then one request only no catchup burst

    @BDD-M07-SNAP-004
    Scenario: Unchanged
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then SkipUnchanged no pin/IO

    @BDD-M07-SNAP-005
    Scenario: Mutation
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then DeferMutation no intermediate capture

    @BDD-M07-SNAP-006
    Scenario: In flight
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then WaitInFlight no overlapping attempt

    @BDD-M07-SNAP-007
    Scenario: Clock regressed
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then TimeRegressed baseline unchanged

    @BDD-M07-SNAP-008
    Scenario: Capture changed
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then CaptureChanged no mixed manifest

    @BDD-M07-SNAP-009
    Scenario: Asset version only change
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then RECOVERY-FP differs even if XML alias text same

    @BDD-M07-SNAP-010
    Scenario: Selection time only
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then fingerprint unchanged

    @BDD-M07-SNAP-011
    Scenario: Newer edit
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then capturedR7 ACK leavesR8 pending

    @BDD-M07-SNAP-012
    Scenario: Formal save
      Given Fake monotonic clock, stable owner and accepted policy state
      When check/capture
      Then recovery fingerprint/baseline untouched

  Rule: Adopt self-contained immutable payload+material bundle schema/bounds and new native RecoveryStoragePort.
    @BDD-M07-SNAP-013
    Scenario: canonical_payload_bytes=16777215
      Given Expanded independent fixture canonical_payload_bytes exact16777215, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-014
    Scenario: canonical_payload_bytes=16777216
      Given Expanded independent fixture canonical_payload_bytes exact16777216, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-015
    Scenario: canonical_payload_bytes=16777217
      Given Expanded independent fixture canonical_payload_bytes exact16777217, other limits below thresholds
      When validate payload/index/bundle
      Then limit error canonical_payload_bytes observed=16777217 no publication

    @BDD-M07-SNAP-016
    Scenario: encoded_payload_bytes=25165823
      Given Expanded independent fixture encoded_payload_bytes exact25165823, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-017
    Scenario: encoded_payload_bytes=25165824
      Given Expanded independent fixture encoded_payload_bytes exact25165824, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-018
    Scenario: encoded_payload_bytes=25165825
      Given Expanded independent fixture encoded_payload_bytes exact25165825, other limits below thresholds
      When validate payload/index/bundle
      Then limit error encoded_payload_bytes observed=25165825 no publication

    @BDD-M07-SNAP-019
    Scenario: single_asset_bytes=67108863
      Given Expanded independent fixture single_asset_bytes exact67108863, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-020
    Scenario: single_asset_bytes=67108864
      Given Expanded independent fixture single_asset_bytes exact67108864, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-021
    Scenario: single_asset_bytes=67108865
      Given Expanded independent fixture single_asset_bytes exact67108865, other limits below thresholds
      When validate payload/index/bundle
      Then limit error single_asset_bytes observed=67108865 no publication

    @BDD-M07-SNAP-022
    Scenario: bundle_asset_bytes=268435455
      Given Expanded independent fixture bundle_asset_bytes exact268435455, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-023
    Scenario: bundle_asset_bytes=268435456
      Given Expanded independent fixture bundle_asset_bytes exact268435456, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-024
    Scenario: bundle_asset_bytes=268435457
      Given Expanded independent fixture bundle_asset_bytes exact268435457, other limits below thresholds
      When validate payload/index/bundle
      Then limit error bundle_asset_bytes observed=268435457 no publication

    @BDD-M07-SNAP-025
    Scenario: asset_pairs=4095
      Given Expanded independent fixture asset_pairs exact4095, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-026
    Scenario: asset_pairs=4096
      Given Expanded independent fixture asset_pairs exact4096, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-027
    Scenario: asset_pairs=4097
      Given Expanded independent fixture asset_pairs exact4097, other limits below thresholds
      When validate payload/index/bundle
      Then limit error asset_pairs observed=4097 no publication

    @BDD-M07-SNAP-028
    Scenario: index_bytes=16777215
      Given Expanded independent fixture index_bytes exact16777215, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-029
    Scenario: index_bytes=16777216
      Given Expanded independent fixture index_bytes exact16777216, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-030
    Scenario: index_bytes=16777217
      Given Expanded independent fixture index_bytes exact16777217, other limits below thresholds
      When validate payload/index/bundle
      Then limit error index_bytes observed=16777217 no publication

    @BDD-M07-SNAP-031
    Scenario: index_entries=4095
      Given Expanded independent fixture index_entries exact4095, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-032
    Scenario: index_entries=4096
      Given Expanded independent fixture index_entries exact4096, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-033
    Scenario: index_entries=4097
      Given Expanded independent fixture index_entries exact4097, other limits below thresholds
      When validate payload/index/bundle
      Then limit error index_entries observed=4097 no publication

    @BDD-M07-SNAP-034
    Scenario: operation_records=8191
      Given Expanded independent fixture operation_records exact8191, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-035
    Scenario: operation_records=8192
      Given Expanded independent fixture operation_records exact8192, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-036
    Scenario: operation_records=8193
      Given Expanded independent fixture operation_records exact8193, other limits below thresholds
      When validate payload/index/bundle
      Then limit error operation_records observed=8193 no publication

    @BDD-M07-SNAP-037
    Scenario: bindings=4095
      Given Expanded independent fixture bindings exact4095, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-038
    Scenario: bindings=4096
      Given Expanded independent fixture bindings exact4096, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-039
    Scenario: bindings=4097
      Given Expanded independent fixture bindings exact4097, other limits below thresholds
      When validate payload/index/bundle
      Then limit error bindings observed=4097 no publication

    @BDD-M07-SNAP-040
    Scenario: legacy_aliases=4095
      Given Expanded independent fixture legacy_aliases exact4095, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-041
    Scenario: legacy_aliases=4096
      Given Expanded independent fixture legacy_aliases exact4096, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-042
    Scenario: legacy_aliases=4097
      Given Expanded independent fixture legacy_aliases exact4097, other limits below thresholds
      When validate payload/index/bundle
      Then limit error legacy_aliases observed=4097 no publication

    @BDD-M07-SNAP-043
    Scenario: id_utf8_bytes=127
      Given Expanded independent fixture id_utf8_bytes exact127, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-044
    Scenario: id_utf8_bytes=128
      Given Expanded independent fixture id_utf8_bytes exact128, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-045
    Scenario: id_utf8_bytes=129
      Given Expanded independent fixture id_utf8_bytes exact129, other limits below thresholds
      When validate payload/index/bundle
      Then limit error id_utf8_bytes observed=129 no publication

    @BDD-M07-SNAP-046
    Scenario: alias_utf8_bytes=1023
      Given Expanded independent fixture alias_utf8_bytes exact1023, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-047
    Scenario: alias_utf8_bytes=1024
      Given Expanded independent fixture alias_utf8_bytes exact1024, other limits below thresholds
      When validate payload/index/bundle
      Then accepted bound

    @BDD-M07-SNAP-048
    Scenario: alias_utf8_bytes=1025
      Given Expanded independent fixture alias_utf8_bytes exact1025, other limits below thresholds
      When validate payload/index/bundle
      Then limit error alias_utf8_bytes observed=1025 no publication

    @BDD-M07-SNAP-049
    Scenario: Base64 invalid
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then InvalidInput invalid_base64 before destination IO

    @BDD-M07-SNAP-050
    Scenario: Duplicate field
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then raw duplicate rejected before typed decode

    @BDD-M07-SNAP-051
    Scenario: Wrong project
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then integrity rejection no restore

    @BDD-M07-SNAP-052
    Scenario: Missing asset copy
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then no payload/index success

    @BDD-M07-SNAP-053
    Scenario: Original project moved
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then verified self-contained bundle readable without original path

    @BDD-M07-SNAP-054
    Scenario: Corrupt dedup object
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then IntegrityFailure no overwrite

    @BDD-M07-SNAP-055
    Scenario: Payload roundtrip
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then exact canonical bytes+manifest preserved

    @BDD-M07-SNAP-056
    Scenario: Unknown schema
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then no fallback decoder

    @BDD-M07-SNAP-057
    Scenario: Bundle overflow
      Given Known raw payload/material fixtures and independent hashes
      When verify/store snapshot
      Then checked sum rejects before copy

  Rule: Adopt pin→objects→index→root-transfer→Published/ACK sequence and explicit uncertain/deferred outcomes.
    @BDD-M07-SNAP-058
    Scenario: Correct order
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then pin→asset copies→payload→index→root transfer→Published/recovery ACK

    @BDD-M07-SNAP-059
    Scenario: Pin failure
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then zero object/index IO, baseline unchanged

    @BDD-M07-SNAP-060
    Scenario: Copy failure
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then old index unchanged; Held retained

    @BDD-M07-SNAP-061
    Scenario: Payload flush failure
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then old index unchanged; known Failed, Held retained

    @BDD-M07-SNAP-062
    Scenario: Index precommit fails
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then no entry, previous valid index retained

    @BDD-M07-SNAP-063
    Scenario: Index uncertain
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then RecoveryBlocked no Failed/Published claim

    @BDD-M07-SNAP-064
    Scenario: Receipt target mismatch
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then blocked proof retained no baseline ACK

    @BDD-M07-SNAP-065
    Scenario: Receipt prior mismatch
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then blocked proof retained

    @BDD-M07-SNAP-066
    Scenario: Receipt new mismatch
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then blocked proof retained

    @BDD-M07-SNAP-067
    Scenario: Receipt empty transaction
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then blocked proof retained

    @BDD-M07-SNAP-068
    Scenario: Root transfer fails
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then PublishedRetentionDeferred no Published/ACK

    @BDD-M07-SNAP-069
    Scenario: ACK rejects
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then PublishedAckDeferred snapshot retained

    @BDD-M07-SNAP-070
    Scenario: Response lost
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then same proof no duplicate entry

    @BDD-M07-SNAP-071
    Scenario: Replay body differs
      Given CapturedR7 +pin and fake ports injecting named terminal/failure outcome
      When publish snapshot
      Then ReplayConflict no writes

  Rule: Adopt restart verification/reconciliation, root retention and no automatic expiration/deletion/repair.
    @BDD-M07-SNAP-072
    Scenario: Startup unresolved journal
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then existing acquire refuses no publication

    @BDD-M07-SNAP-073
    Scenario: Restart Held
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then retained pin no automatic release

    @BDD-M07-SNAP-074
    Scenario: Index entry missing object
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then PendingVerification no restore/Published

    @BDD-M07-SNAP-075
    Scenario: Root provider missing
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then Unknown roots no release

    @BDD-M07-SNAP-076
    Scenario: Closed completion
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then IgnoreClosedCompletion no new-session ACK

    @BDD-M07-SNAP-077
    Scenario: Project switched
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then late evidence stays source project/session

    @BDD-M07-SNAP-078
    Scenario: Hide history
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then entry/assets/roots retained

    @BDD-M07-SNAP-079
    Scenario: Processed entry
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then still restorable/root retained

    @BDD-M07-SNAP-080
    Scenario: Capacity full
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then new snapshot blocked no eviction

    @BDD-M07-SNAP-081
    Scenario: No delete API
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then zero remove calls

    @BDD-M07-SNAP-082
    Scenario: Reconcile retained proof
      Given Durable entries and fake startup/session events
      When enumerate/reconcile lifecycle
      Then same index entry and roots no payload rewrite

  Rule: Adopt preview/confirmed new-unsaved restore, M05 verified bundle import and post-install deferred statuses.
    @BDD-M07-SNAP-083
    Scenario: Preview no mutation
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then active doc/catalog unchanged

    @BDD-M07-SNAP-084
    Scenario: Preview expiry
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then PlanExpired after60s no install

    @BDD-M07-SNAP-085
    Scenario: Source index changed
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then stale plan rejected

    @BDD-M07-SNAP-086
    Scenario: Destination changed
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then generation mismatch no install

    @BDD-M07-SNAP-087
    Scenario: Destination missing codec
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then DependencyNotReady no raw fallback

    @BDD-M07-SNAP-088
    Scenario: Restore valid
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then new unsaved doc/session R0, no formal/recovery baseline, empty history

    @BDD-M07-SNAP-089
    Scenario: Original path malicious
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then never used as destination authority

    @BDD-M07-SNAP-090
    Scenario: Material import fails
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then active document untouched; orphan retention allowed

    @BDD-M07-SNAP-091
    Scenario: Identity collision
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then reject before install, no silent remap

    @BDD-M07-SNAP-092
    Scenario: Install root transfer fails
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then InstalledRetentionDeferred pin retained

    @BDD-M07-SNAP-093
    Scenario: Mark processed fails
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then RestoreInstalledMarkDeferred source stays Unprocessed

    @BDD-M07-SNAP-094
    Scenario: Repeated confirm
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then same installed receipt no duplicate doc

    @BDD-M07-SNAP-095
    Scenario: Restore no original file write
      Given Verified snapshot bundle and explicit destination selection
      When preview/confirm restore
      Then zero formal file replace calls

  Rule: Adopt explicit joint M04/M05 capture/pin-export/import/proof amendments; old packets frozen and S1 protected.
    @BDD-M07-SNAP-096
    Scenario: M04 semantic distinct
      Given Joint pending interfaces represented by approved future fake seams
      When integrate capture/assets/restore
      Then ACK semantic A not payload B/index C/recovery FP

    @BDD-M07-SNAP-097
    Scenario: M05 export missing
      Given Joint pending interfaces represented by approved future fake seams
      When integrate capture/assets/restore
      Then DependencyNotReady no incomplete asset snapshot

    @BDD-M07-SNAP-098
    Scenario: No second owner
      Given Joint pending interfaces represented by approved future fake seams
      When integrate capture/assets/restore
      Then same M04 registry used for capture/restore

    @BDD-M07-SNAP-099
    Scenario: S1 unchanged
      Given Joint pending interfaces represented by approved future fake seams
      When integrate capture/assets/restore
      Then original policy types/tests preserved

    @BDD-M07-SNAP-100
    Scenario: Bindings Pending
      Given Joint pending interfaces represented by approved future fake seams
      When integrate capture/assets/restore
      Then retain explicit Pending and execution block; no validity fabrication

    @BDD-M07-SNAP-101
    Scenario: Unmapped legacy alias
      Given Joint pending interfaces represented by approved future fake seams
      When integrate capture/assets/restore
      Then DependencyNotReady/invalid reference before publish

  Rule: Adopt closed UI/ACL/errors/replay, candidate envelope and test/readiness gates.
    @BDD-M07-SNAP-102
    Scenario: Viewer denied
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then PermissionDenied before parse/IO

    @BDD-M07-SNAP-103
    Scenario: Forged Published
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then DTO rejected; UI cannot declare success

    @BDD-M07-SNAP-104
    Scenario: Cursor stale
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then index changed result no mixed page

    @BDD-M07-SNAP-105
    Scenario: UI failed preview
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then active draft and focus preserved

    @BDD-M07-SNAP-106
    Scenario: Deferred UI
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then pending state no success toast

    @BDD-M07-SNAP-107
    Scenario: Source unsafe alias
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then native identity rejection

    @BDD-M07-SNAP-108
    Scenario: Cross-process index
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then second lease Busy

    @BDD-M07-SNAP-109
    Scenario: Unsupported OS
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then explicit native unavailable

    @BDD-M07-SNAP-110
    Scenario: No dependency hidden
      Given Trusted/forged caller and deterministic adapter seams
      When invoke command/native boundary
      Then missing provider BLOCKED, not valid RED
