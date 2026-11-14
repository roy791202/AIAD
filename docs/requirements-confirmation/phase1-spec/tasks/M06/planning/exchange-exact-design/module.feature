Feature: Verified independent document exchange and single-document merge
  Background:
    Given an authorized project and trusted immutable source

  Rule: Adopt framed uncompressed BIN-v1 A and strict manifest/table/closure limits; ZIP/SGB compatibility separate; ESS internal-material export RequiresBin choice explicit.
    @BDD-M06-EX-001
    Scenario: Valid BIN
      Given Independent exact framed source fixture
      When validate/export
      Then exact full document+assets/refs verified

    @BDD-M06-EX-002
    Scenario: Zero bytes
      Given Independent exact framed source fixture
      When validate/export
      Then ArchiveInvalid magic/header no target IO

    @BDD-M06-EX-003
    Scenario: Truncated header
      Given Independent exact framed source fixture
      When validate/export
      Then reject every header length1..15

    @BDD-M06-EX-004
    Scenario: Manifest zero
      Given Independent exact framed source fixture
      When validate/export
      Then manifest_length error

    @BDD-M06-EX-005
    Scenario: u64 addition overflow
      Given Independent exact framed source fixture
      When validate/export
      Then integer_overflow before range read

    @BDD-M06-EX-006
    Scenario: Entry overlap
      Given Independent exact framed source fixture
      When validate/export
      Then overlap hard blocker

    @BDD-M06-EX-007
    Scenario: Entry gap
      Given Independent exact framed source fixture
      When validate/export
      Then entry_range hard blocker

    @BDD-M06-EX-008
    Scenario: Trailing bytes
      Given Independent exact framed source fixture
      When validate/export
      Then trailing_bytes hard blocker

    @BDD-M06-EX-009
    Scenario: Duplicate key
      Given Independent exact framed source fixture
      When validate/export
      Then duplicate_field before typed decode

    @BDD-M06-EX-010
    Scenario: Duplicate entry
      Given Independent exact framed source fixture
      When validate/export
      Then duplicate_entry never last-wins

    @BDD-M06-EX-011
    Scenario: Unsafe path
      Given Independent exact framed source fixture
      When validate/export
      Then unsafe_key no extraction

    @BDD-M06-EX-012
    Scenario: Missing document
      Given Independent exact framed source fixture
      When validate/export
      Then missing_document hard blocker

    @BDD-M06-EX-013
    Scenario: Missing internal asset
      Given Independent exact framed source fixture
      When validate/export
      Then missing_internal cannot accept incomplete

    @BDD-M06-EX-014
    Scenario: Corrupt asset
      Given Independent exact framed source fixture
      When validate/export
      Then digest_mismatch hard blocker

    @BDD-M06-EX-015
    Scenario: Unused entry
      Given Independent exact framed source fixture
      When validate/export
      Then unused_entry rejected

    @BDD-M06-EX-016
    Scenario: Legacy SGB1
      Given Independent exact framed source fixture
      When validate/export
      Then UnsupportedFormat no conversion

    @BDD-M06-EX-017
    Scenario: ZIP signature
      Given Independent exact framed source fixture
      When validate/export
      Then unsupported format no decoder

    @BDD-M06-EX-018
    Scenario: ESS referenced assets
      Given Independent exact framed source fixture
      When validate/export
      Then RequiresBin no incomplete standalone export

    @BDD-M06-EX-019
    Scenario: Deterministic bytes
      Given Independent exact framed source fixture
      When validate/export
      Then same content+refs produces same framing bytes

    @BDD-M06-EX-020
    Scenario: archive_bytes 536870911
      Given Independent recipe counts archive_bytes exactly 536870911, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-021
    Scenario: archive_bytes 536870912
      Given Independent recipe counts archive_bytes exactly 536870912, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-022
    Scenario: archive_bytes 536870913
      Given Independent recipe counts archive_bytes exactly 536870913, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error archive_bytes, no target mutation

    @BDD-M06-EX-023
    Scenario: manifest_bytes 2097151
      Given Independent recipe counts manifest_bytes exactly 2097151, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-024
    Scenario: manifest_bytes 2097152
      Given Independent recipe counts manifest_bytes exactly 2097152, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-025
    Scenario: manifest_bytes 2097153
      Given Independent recipe counts manifest_bytes exactly 2097153, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error manifest_bytes, no target mutation

    @BDD-M06-EX-026
    Scenario: document_bytes 16777215
      Given Independent recipe counts document_bytes exactly 16777215, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-027
    Scenario: document_bytes 16777216
      Given Independent recipe counts document_bytes exactly 16777216, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-028
    Scenario: document_bytes 16777217
      Given Independent recipe counts document_bytes exactly 16777217, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error document_bytes, no target mutation

    @BDD-M06-EX-029
    Scenario: asset_bytes_each 67108863
      Given Independent recipe counts asset_bytes_each exactly 67108863, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-030
    Scenario: asset_bytes_each 67108864
      Given Independent recipe counts asset_bytes_each exactly 67108864, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-031
    Scenario: asset_bytes_each 67108865
      Given Independent recipe counts asset_bytes_each exactly 67108865, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error asset_bytes_each, no target mutation

    @BDD-M06-EX-032
    Scenario: asset_bytes_total 268435455
      Given Independent recipe counts asset_bytes_total exactly 268435455, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-033
    Scenario: asset_bytes_total 268435456
      Given Independent recipe counts asset_bytes_total exactly 268435456, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-034
    Scenario: asset_bytes_total 268435457
      Given Independent recipe counts asset_bytes_total exactly 268435457, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error asset_bytes_total, no target mutation

    @BDD-M06-EX-035
    Scenario: entries 4096
      Given Independent recipe counts entries exactly 4096, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-036
    Scenario: entries 4097
      Given Independent recipe counts entries exactly 4097, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-037
    Scenario: entries 4098
      Given Independent recipe counts entries exactly 4098, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error entries, no target mutation

    @BDD-M06-EX-038
    Scenario: references 4095
      Given Independent recipe counts references exactly 4095, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-039
    Scenario: references 4096
      Given Independent recipe counts references exactly 4096, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-040
    Scenario: references 4097
      Given Independent recipe counts references exactly 4097, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error references, no target mutation

    @BDD-M06-EX-041
    Scenario: external_dependencies 4095
      Given Independent recipe counts external_dependencies exactly 4095, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-042
    Scenario: external_dependencies 4096
      Given Independent recipe counts external_dependencies exactly 4096, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-043
    Scenario: external_dependencies 4097
      Given Independent recipe counts external_dependencies exactly 4097, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error external_dependencies, no target mutation

    @BDD-M06-EX-044
    Scenario: alias_utf8_bytes 1023
      Given Independent recipe counts alias_utf8_bytes exactly 1023, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-045
    Scenario: alias_utf8_bytes 1024
      Given Independent recipe counts alias_utf8_bytes exactly 1024, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-046
    Scenario: alias_utf8_bytes 1025
      Given Independent recipe counts alias_utf8_bytes exactly 1025, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error alias_utf8_bytes, no target mutation

    @BDD-M06-EX-047
    Scenario: id_utf8_bytes 127
      Given Independent recipe counts id_utf8_bytes exactly 127, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-048
    Scenario: id_utf8_bytes 128
      Given Independent recipe counts id_utf8_bytes exactly 128, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-049
    Scenario: id_utf8_bytes 129
      Given Independent recipe counts id_utf8_bytes exactly 129, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error id_utf8_bytes, no target mutation

    @BDD-M06-EX-050
    Scenario: json_depth 63
      Given Independent recipe counts json_depth exactly 63, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-051
    Scenario: json_depth 64
      Given Independent recipe counts json_depth exactly 64, checked before parse/semantic validity
      When evaluate named resource guard
      Then named guard passes (later format rules still independently apply)

    @BDD-M06-EX-052
    Scenario: json_depth 65
      Given Independent recipe counts json_depth exactly 65, checked before parse/semantic validity
      When evaluate named resource guard
      Then limit error json_depth, no target mutation

  Rule: Adopt immutable source/export Ports and native no-replace publication; no imported execution/extraction/dependency downloads.
    @BDD-M06-EX-053
    Scenario: Source changed
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then SourceChanged no stale import

    @BDD-M06-EX-054
    Scenario: Source alias
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then UnsafeIdentity native reject

    @BDD-M06-EX-055
    Scenario: Existing destination
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then AlreadyExists no overwrite even empty

    @BDD-M06-EX-056
    Scenario: Export write failure
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then old destination/source unchanged, owned stage evidence

    @BDD-M06-EX-057
    Scenario: Flush fails
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then no ExportPublished

    @BDD-M06-EX-058
    Scenario: Publish uncertain
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then retained diagnostic blocked no fake Cancelled

    @BDD-M06-EX-059
    Scenario: Drop stage
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then handles close no implicit recursive deletion

    @BDD-M06-EX-060
    Scenario: Export response lost
      Given Native/fake trusted source+destination handles
      When capture/publish archive
      Then proof query delivery-deferred not second export

  Rule: Adopt exact preflight R1-R4 plus already document-accepted F1-F3 without semantic weakening; hard blockers never bypassed.
    @BDD-M06-EX-061
    Scenario: Hard block accept external
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then Blocked remains, no apply

    @BDD-M06-EX-062
    Scenario: External not confirmed
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then NeedsDependencyConfirmation

    @BDD-M06-EX-063
    Scenario: External explicitly accepted
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then AllowedIncomplete exact Pending and blocked capabilities

    @BDD-M06-EX-064
    Scenario: Stale source
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then preflight StaleSource

    @BDD-M06-EX-065
    Scenario: Stale target
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then preflight StaleTarget

    @BDD-M06-EX-066
    Scenario: Cross doc dependency
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then CrossDocumentChangeRequired

    @BDD-M06-EX-067
    Scenario: Original64oracles
      Given Decoder-derived trusted report, never UI safety claim
      When evaluate preflight
      Then trace to frozen accepted document correction; no rerun or changed expectations

  Rule: Adopt explicit preview FreshImportedIds mapping and one-document M04 Merge/Undo, no label matching/hidden cross-document edits.
    @BDD-M06-EX-068
    Scenario: Fresh identity mapping
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then complete explicit preview old→new, no same-name match

    @BDD-M06-EX-069
    Scenario: Ambiguous mapping
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then IdentityConflict before candidate commit

    @BDD-M06-EX-070
    Scenario: Unsupported hidden reference
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then reject, no silent remap/drop

    @BDD-M06-EX-071
    Scenario: Full ESS aggregate
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then one candidate includes all affected sections

    @BDD-M06-EX-072
    Scenario: Single merge
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then one revision/one Undo before+after assets union

    @BDD-M06-EX-073
    Scenario: Merge no-op
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then no new revision/history

    @BDD-M06-EX-074
    Scenario: Failure before commit
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then target content/history/baselines exact unchanged

    @BDD-M06-EX-075
    Scenario: Cancel preview
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then no target/catalog mutation

    @BDD-M06-EX-076
    Scenario: Expired plan
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then PlanExpired

    @BDD-M06-EX-077
    Scenario: Late owner generation
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then StalePlan no replacement apply

    @BDD-M06-EX-078
    Scenario: Undo restore
      Given TargetR7 and exact candidate/mapping/source proof
      When confirm merge/undo
      Then complete before target restored once; source unchanged

  Rule: Adopt M05 verified import/export pins (new Export purpose), roots and postcommit deferred statuses; separate M07 preservation.
    @BDD-M06-EX-079
    Scenario: Pin before merge
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then no content commit before durable pin

    @BDD-M06-EX-080
    Scenario: Asset import fails
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then target unchanged, retained orphan allowed

    @BDD-M06-EX-081
    Scenario: Postcommit roots fail
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then MergeAppliedRetentionDeferred actual revision+Held, no fake rollback

    @BDD-M06-EX-082
    Scenario: Undo roots fail
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then UndoAppliedRetentionDeferred union retained

    @BDD-M06-EX-083
    Scenario: Other doc references
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then material never deleted

    @BDD-M06-EX-084
    Scenario: M07 recovery references
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then snapshots untouched/root retains version

    @BDD-M06-EX-085
    Scenario: Export pin remains unknown
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then release denied conservatively

    @BDD-M06-EX-086
    Scenario: Formal save separate
      Given Catalog/pin/root provider failure fixtures
      When import/export/apply handoff
      Then neither formal nor recovery baseline ACKed

  Rule: Adopt explicit M01 new-project copy seam/new identities/provenance and partial-publication blocked outcomes; no inherited approval or cross-document Undo.
    @BDD-M06-EX-087
    Scenario: New project IDs
      Given Verified source+explicit trusted destination selection
      When confirm project copy
      Then new project/document identities, source provenance only

    @BDD-M06-EX-088
    Scenario: No source approvals
      Given Verified source+explicit trusted destination selection
      When confirm project copy
      Then new project Draft/no inherited Defined

    @BDD-M06-EX-089
    Scenario: Project create prepublish fails
      Given Verified source+explicit trusted destination selection
      When confirm project copy
      Then no selectable completed project; retained staging diagnostic

    @BDD-M06-EX-090
    Scenario: Project copy uncertain
      Given Verified source+explicit trusted destination selection
      When confirm project copy
      Then ProjectCopyDeferred blocked, no false success

    @BDD-M06-EX-091
    Scenario: Copy no Undo
      Given Verified source+explicit trusted destination selection
      When confirm project copy
      Then no cross-document history

    @BDD-M06-EX-092
    Scenario: Missing M01 provider
      Given Verified source+explicit trusted destination selection
      When confirm project copy
      Then DependencyNotReady no mkdir/adopt fallback

  Rule: Adopt commands/errors/replay/cancel/envelope and acceptance gates; product remains not ready before dependencies/Skeleton/RED.
    @BDD-M06-EX-093
    Scenario: Viewer denied
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then permission error before source read

    @BDD-M06-EX-094
    Scenario: Fake safe flag
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then closed DTO rejects

    @BDD-M06-EX-095
    Scenario: Replay same body
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then same apply receipt no second Undo

    @BDD-M06-EX-096
    Scenario: Replay changed body
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then ReplayConflict

    @BDD-M06-EX-097
    Scenario: Close during commit
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then await actual outcome no false Cancelled

    @BDD-M06-EX-098
    Scenario: No restart replay
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then fresh session cannot replay lost target commit

    @BDD-M06-EX-099
    Scenario: Pending UI
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then clear warning dependent capabilities blocked

    @BDD-M06-EX-100
    Scenario: Applied deferred UI
      Given Trusted Editor/Viewer bindings and operation evidence
      When invoke exchange command
      Then shows actual changed revision not unchanged failure
