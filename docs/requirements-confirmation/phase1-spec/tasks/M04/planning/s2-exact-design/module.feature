Feature: M04 whole-document lifecycle and safe persistence
  Background:
    Given an authorized project and a current document writer

  @BDD-M04-S2-001 @D1
  Scenario: XML output escape
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then text <&>CR and attribute quote/TAB/LF/CR roundtrip exactly; deterministic entities as contract

  @BDD-M04-S2-002 @D1
  Scenario: XML attribute order
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then same tree different attr order yields identical output bytes

  @BDD-M04-S2-003 @D1
  Scenario: XML comments/text
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then decoded ordered comments/text retained, no inserted indentation

  @BDD-M04-S2-004 @D1
  Scenario: XML empty element
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then empty children emits self-close, empty vs absent attr distinct

  @BDD-M04-S2-005 @D1
  Scenario: XML invalid comment
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then OutputInvalid at exact comment path, no IO

  @BDD-M04-S2-006 @D1
  Scenario: XML invalid scalar
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then OutputInvalid invalid_character before IO

  @BDD-M04-S2-007 @D1
  Scenario: XML aggregate roundtrip
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then work+architecture+design all retained

  @BDD-M04-S2-008 @D1
  Scenario: XML semantic attr strings
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then 1 != 1.0 and false string preserved

  @BDD-M04-S2-009 @D1
  Scenario: Unsupported projection
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then inspection allowed; trusted install/save/clear rejected

  @BDD-M04-S2-010 @D1
  Scenario: Encode digest mismatch
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then SemanticMismatch, zero writes

  @BDD-M04-S2-011 @D1
  Scenario: JSON C1 unavailable
    Given Valid normalized XML/JSON candidate and unchanged active document
    When encode or install candidate
    Then DependencyNotReady codec, no typed fallback

  @BDD-M04-S2-012 @D1
  Scenario: XML serialized output 16777215 bytes
    Given Typed tree with 17 text padding chunks each <=1MiB; escaped independent reference serialization length verified
    When encode candidate
    Then success exact bytes

  @BDD-M04-S2-013 @D1
  Scenario: XML serialized output 16777216 bytes
    Given Typed tree with 17 text padding chunks each <=1MiB; escaped independent reference serialization length verified
    When encode candidate
    Then success exact bytes

  @BDD-M04-S2-014 @D1
  Scenario: XML serialized output 16777217 bytes
    Given Typed tree with 17 text padding chunks each <=1MiB; escaped independent reference serialization length verified
    When encode candidate
    Then ResourceLimit output_bytes path=/ limit=16777216 observed=16777217; zero IO

  @BDD-M04-S2-015 @D2
  Scenario: Design vectors
    Given Guard-valid fixture; fixed expected bytes/hash
    When compute fingerprint
    Then all 13 frozen exact semantic bytes+sha vectors match

  @BDD-M04-S2-016 @D2
  Scenario: Decimal equivalence
    Given Guard-valid fixture; fixed expected bytes/hash
    When compute fingerprint
    Then 0=-0;1=1.00=1e0; string 1 differs number1

  @BDD-M04-S2-017 @D2
  Scenario: Exact exclusions
    Given Guard-valid fixture; fixed expected bytes/hash
    When compute fingerprint
    Then only listed volatile paths excluded; nested same-name keys included

  @BDD-M04-S2-018 @D2
  Scenario: Profile mismatch
    Given Guard-valid fixture; fixed expected bytes/hash
    When compute fingerprint
    Then fresh reopen required; old baseline never silently rehashed

  @BDD-M04-S2-019 @D2
  Scenario: XML mixed whitespace
    Given Guard-valid fixture; fixed expected bytes/hash
    When compute fingerprint
    Then mixed content spaces preserved; element-only indentation semantic ignored

  @BDD-M04-S2-020 @D3
  Scenario: No references
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then Complete empty only after complete projector proves absence

  @BDD-M04-S2-021 @D3
  Scenario: Legacy string unmapped
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then InvalidDependency unmapped_reference at assetRef path; no install

  @BDD-M04-S2-022 @D3
  Scenario: Version missing
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then InvalidDependency missing_asset; no fabricated digest

  @BDD-M04-S2-023 @D3
  Scenario: ID digest conflict
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then digest_conflict, active content unchanged

  @BDD-M04-S2-024 @D3
  Scenario: Duplicate response path
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then proof_mismatch before install

  @BDD-M04-S2-025 @D3
  Scenario: Wrong owner echo
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then proof_mismatch before install

  @BDD-M04-S2-026 @D3
  Scenario: Stale catalog
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then StaleDependency before commit

  @BDD-M04-S2-027 @D3
  Scenario: Pending authored binding
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then Pending preserved; execute/build blocked; save allowed with pinned Complete proof

  @BDD-M04-S2-028 @D3
  Scenario: Missing target
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then InvalidDependency missing_target unless explicitly authored Pending

  @BDD-M04-S2-029 @D3
  Scenario: Unknown props reference
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then unsupported projection, never guess string identity

  @BDD-M04-S2-030 @D3
  Scenario: Provider absent
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then DependencyNotReady material_resolver

  @BDD-M04-S2-031 @D3
  Scenario: Pins unavailable
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then DependencyNotReady pin_provider

  @BDD-M04-S2-032 @D3
  Scenario: Undo roots
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then before+after pinned versions retained through Undo/in-flight

  @BDD-M04-S2-033 @D3
  Scenario: Invalid binding
    Given Candidate and resolver fixture tied to R7/generation3
    When resolve and revalidate candidate
    Then inspection only, trusted install rejected

  @BDD-M04-S2-034 @D4
  Scenario: ESS clear aggregate
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then tasks, arch nodes/edges and all design nodes removed; metadata/scaffolds retained

  @BDD-M04-S2-035 @D4
  Scenario: ESS unknown attribute
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then UnsupportedProjection exact path; no deletion

  @BDD-M04-S2-036 @D4
  Scenario: Standalone clear
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then one Form retained with optional fields0/false/[]; other nodes removed

  @BDD-M04-S2-037 @D4
  Scenario: Ambiguous Form
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then Structure error, unchanged content

  @BDD-M04-S2-038 @D4
  Scenario: Clear one Undo
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then exact prior complete content restored once

  @BDD-M04-S2-039 @D4
  Scenario: Clear no-op
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then no revision increment or Undo

  @BDD-M04-S2-040 @D4
  Scenario: Expired plan
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then PlanExpired after60s; unchanged

  @BDD-M04-S2-041 @D4
  Scenario: Revision changed
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then RevisionConflict; no clear

  @BDD-M04-S2-042 @D4
  Scenario: Generation changed
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then OwnerMismatch; no replacement install

  @BDD-M04-S2-043 @D4
  Scenario: Catalog changed
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then StaleDependency; no clear

  @BDD-M04-S2-044 @D4
  Scenario: Replay clear
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then identical request returns same result no second Undo

  @BDD-M04-S2-045 @D4
  Scenario: Clear unsaved
    Given Clear plan captures R7 generation3, fake monotonic clock and full before digest
    When prepare or confirm clear
    Then does not touch disk/formal/snapshot baseline

  @BDD-M04-S2-046 @D5
  Scenario: Semantic A raw B C
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then ACK A; previous B; encoded/receipt C all intentionally distinct

  @BDD-M04-S2-047 @D5
  Scenario: Receipt target mismatch
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then RecoveryBlocked proof retained no ACK

  @BDD-M04-S2-048 @D5
  Scenario: Receipt prior mismatch
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then RecoveryBlocked proof retained no ACK

  @BDD-M04-S2-049 @D5
  Scenario: Receipt new mismatch
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then RecoveryBlocked proof retained no ACK

  @BDD-M04-S2-050 @D5
  Scenario: Receipt empty transaction
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then RecoveryBlocked proof retained no ACK

  @BDD-M04-S2-051 @D5
  Scenario: Late newer revision
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then ACK capturedR7 leavesR8 dirty; snapshot baseline unchanged

  @BDD-M04-S2-052 @D5
  Scenario: Detached after commit
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then CommittedAckDeferred proof; never ordinary unchanged failure

  @BDD-M04-S2-053 @D5
  Scenario: ACK rejected
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then CommittedAckDeferred with original receipt retained

  @BDD-M04-S2-054 @D5
  Scenario: IO conflict
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then exact expected/observed preserved; no ACK

  @BDD-M04-S2-055 @D5
  Scenario: Cache full
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then CapacityExceeded before IO

  @BDD-M04-S2-056 @D5
  Scenario: Request collision
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then ReplayConflict before IO

  @BDD-M04-S2-057 @D5
  Scenario: Same request replay
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then same proof; replace_checked called once

  @BDD-M04-S2-058 @D5
  Scenario: Timeout IO
    Given Capture R7 semantic A, disk raw B, encoded raw C; fake lease/owner lifecycle
    When save current capture
    Then pending reservation retained until matching completion

  @BDD-M04-S2-059 @D6
  Scenario: In-flight edits
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then Busy for edit/clear/undo/save/snapshot; queries allowed

  @BDD-M04-S2-060 @D6
  Scenario: IO RecoveryRequired
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then target-scoped block and all original journal/version paths retained

  @BDD-M04-S2-061 @D6
  Scenario: Detach block
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then target evidence remains, no bypass through new session

  @BDD-M04-S2-062 @D6
  Scenario: Startup nonterminal journal
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then existing adapter refuses acquire; no session install

  @BDD-M04-S2-063 @D6
  Scenario: Startup valid terminal
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then lease read/decode/resolve then fresh session baseline

  @BDD-M04-S2-064 @D6
  Scenario: Reacquire uncertain
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then runtime prior receipt mismatch remains blocked

  @BDD-M04-S2-065 @D6
  Scenario: No clear-health
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then no unblock command registered

  @BDD-M04-S2-066 @D6
  Scenario: Lock sidecar
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then acquire may create lock; not zero-write claim

  @BDD-M04-S2-067 @D6
  Scenario: Reopen parse fails
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then lease released, old session remains

  @BDD-M04-S2-068 @D6
  Scenario: Reopen resolver fails
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then lease released, no baseline

  @BDD-M04-S2-069 @D6
  Scenario: Alias busy
    Given Target-bound session/lease; fake guard or gated Windows11 native fixture
    When save/detach/reopen
    Then same file via hardlink/case/reparse/8.3 cannot gain second writer

  @BDD-M04-S2-070 @D7
  Scenario: One registry
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then M03 edit and M04 save observe identical session/revision

  @BDD-M04-S2-071 @D7
  Scenario: No target provider
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then DependencyNotReady target_identity before acquire

  @BDD-M04-S2-072 @D8
  Scenario: Forged caller
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then PermissionDenied before inner parse/IO

  @BDD-M04-S2-073 @D7
  Scenario: Stale writer
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then OwnerMismatch; no content installation

  @BDD-M04-S2-074 @D8
  Scenario: Viewer denied
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then all ten document commands denied to Viewer

  @BDD-M04-S2-075 @D8
  Scenario: Leave save fails
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then owner remains attached; error shown

  @BDD-M04-S2-076 @D8
  Scenario: Leave ACK deferred
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then stay open with proof, no false clean

  @BDD-M04-S2-077 @D8
  Scenario: Leave newer edit
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then do not close dirty newer revision

  @BDD-M04-S2-078 @D8
  Scenario: Cancel leave
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then no mutation/IO

  @BDD-M04-S2-079 @D8
  Scenario: Discard generation
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then only exact captured generation detached

  @BDD-M04-S2-080 @D8
  Scenario: Raw duplicate key
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then C1 guard rejects before typed decode

  @BDD-M04-S2-081 @D8
  Scenario: Legacy save route
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then DOCUMENT_OWNER_REQUIRED no FS fallback

  @BDD-M04-S2-082 @D8
  Scenario: UI load normalization
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then projection load does not clamp/stamp/filter active content

  @BDD-M04-S2-083 @D8
  Scenario: Replay revoked caller
    Given Trusted project and Editor/Viewer instances with fixed binding/token
    When invoke document action
    Then permission check before cached response
