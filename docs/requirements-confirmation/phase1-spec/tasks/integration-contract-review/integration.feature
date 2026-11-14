Feature: Cross-module context proof and lifecycle consistency
  Background:
    Given immutable original planning packages and accepted prior scope evidence

  @INT-CX-01
  Scenario: CX-01
    Given Original exact packages and context/receipt fixtures for M03-H2,M04
    When exercise corrected cross-owner boundary after joint adoption
    Then M04 document_owner.rs owns exactly one session per project/document. M03 design_owner.rs is facade over owner token; writer transfer increments common generation, invalidates all M02/M03/M06/M07 plans tied to old generation. Content/history unchanged. No independent session initializer in facade.

  @INT-CX-02
  Scenario: CX-02
    Given Original exact packages and context/receipt fixtures for M03-H2,M04,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then SGA-DESIGN-SEM-v1 is sole proposed design semantic bytes; XML uses M04-EssXmlV1-semantic-v1. All consumers carry {profile,digest}; no cross-profile equality or baseline relabeling. M07 RECOVERY-FP wraps content semantic+asset/binding evidence and ACKs M04 original semantic only. Existing S1 hash APIs unchanged.

  @INT-CX-03
  Scenario: CX-03
    Given Original exact packages and context/receipt fixtures for M01,M02,M03,M04,M05,M06,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then All UI wire revisions/generations/sequences/byte sizes beyond safe range use canonical decimal STRING 0|[1-9][0-9]* ≤u64MAX; no leading plus/zero/space/exponent. HOST parses checked u64; JS retains strings/BigInt for compare. Internal Rust u64 unchanged. Persisted machine schema numbers remain their declared integer contract, not UI parse/re-serialize.

  @INT-CX-04
  Scenario: CX-04
    Given Original exact packages and context/receipt fixtures for M04,M05
    When exercise corrected cross-owner boundary after joint adoption
    Then Save captures content/profile+exact assets→durable Save pin→file commit verified→durable formal-root transfer receipt→ACK captured revision+semantic. Transfer fail after file commit returns CommittedAckDeferred (stage=RetentionTransfer), keeps Held and original file receipt, never retries write blindly. Snapshot baseline untouched.

  @INT-CX-05
  Scenario: CX-05
    Given Original exact packages and context/receipt fixtures for M05,M06,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then PinState=Held|Transferred|Released. PinPurpose=Candidate|Save|Undo|Redo|Recovery|Import|Export. Only verified catalog transition updates state; Transferred/Released immutable terminal metadata. No TTL. Add matching operation results and strict decoder/negative fixtures; old product S1 untouched.

  @INT-CX-06
  Scenario: CX-06
    Given Original exact packages and context/receipt fixtures for M04,M05,M06,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then Normalize app API: resolve(Context,Requests)->ResolutionSnapshot{context,catalog_generation,catalog_raw_digest,snapshot_digest,completeness,assets,bindings}; pin(snapshot,purpose,operation_id)->PinReceipt; validate_pin; read_pinned_version; import_verified_versions(context,verified_bundle,purpose,operation_id); transfer(pin,RootManifest,ExternalCommitProof,operation_id); release(pin,RootBundle,operation_id). Remove root_proof_id from resolve (root observation not asset resolution proof). Versioned receipt types below authoritative proposed overlay.

  @INT-CX-07
  Scenario: CX-07
    Given Original exact packages and context/receipt fixtures for M03,M04,M05,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then M03-C1/M04 codec projectors pure HOST decode+typed entity/reference inventory before runtime owner install. M05 resolves asset IDs/versions using that inventory, never calls M03 Viewer/runtime. Root-provider completeness is separate from material resolution: missing M07 root=>Unknown blocks release/cleanup, not valid pinned install. Build ports/fakes independently after adoption, then providers in order below.

  @INT-CX-08
  Scenario: CX-08
    Given Original exact packages and context/receipt fixtures for M03-H2,M04,M05,M06,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then Common MutationReceipt {context,before_revision,after_revision,content_semantic,pin_id,result:Applied|NoChange|AppliedRetentionDeferred}. Once S1 commit occurred never ErrorUnchanged; retain Held/old+new union roots. M03 edit, M04 clear/undo, M06 merge/undo and M07 restore map tagged deferred result to real changed revision. No automatic rollback after publication.

  @INT-CX-09
  Scenario: CX-09
    Given Original exact packages and context/receipt fixtures for M01-copy,M05,M06
    When exercise corrected cross-owner boundary after joint adoption
    Then Recommended A: exclusive create FINAL directory with authenticated QuarantinedCopy marker; all child/catalog commits use final stable canonical path. Project is not selectable/openable until M01 durable Ready marker commit verified. All official M01 project-open/selection paths reject quarantine (including restart). No rename of any directory containing FileCommit journals. Failed copy retains quarantined diagnostics; no recursive delete. Alternative B publish journal-free initial tree then first index commit at final path requires separate initial-publication receipt and larger schema scope; not recommended here. Never edit/move IO journal to repair.

  @INT-CX-10
  Scenario: CX-10
    Given Original exact packages and context/receipt fixtures for M05,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then Separate LocalIntegrityReady from PublicationAcknowledged. Verified recovery index+payload+ALL asset copies permits explicit restore to authorized new destination even if SOURCE root transfer is pending; label SourceRetentionDeferred, retain original Held/Unknown, no original S1 Published/ACK. Destination import+pin+owner commit still mandatory. Missing/corrupt local bundle always blocks restore. Do not claim source retention proof merely from local readability.

  @INT-CX-11
  Scenario: CX-11
    Given Original exact packages and context/receipt fixtures for M01,M02,M04
    When exercise corrected cross-owner boundary after joint adoption
    Then Add application SourceReadReservation trait validate()->Result<SourceSnapshotId> with lifetime guard; definition/design providers acquire held native read fences compatible with their existing exclusive write protocol BEFORE generation active writer. Approval evidence uses immutable Approved revision plus HOST source-epoch reservation; no domain OS dependency or SPEC source mutation. Add proposed Ports generation_sources.rs, adapter generation_sources.rs/tests and existing M01 dispatch/M04 document_owner provider hooks as explicit child envelope delta; if full writer coverage cannot be proven return DependencyNotReady. Store3traits remain unchanged.

  @INT-CX-12
  Scenario: CX-12
    Given Original exact packages and context/receipt fixtures for M02,IO
    When exercise corrected cross-owner boundary after joint adoption
    Then IO-owned crate-private read guard constructed only after OS shared lock on exact canonical FileCommit sidecar; readonly inspect under that guard validates normalized target/journal terminal state/target raw digest. Generic caller cannot forge guard or clear journal. Signature and native alias/access matrix refined in IO child packet before Skeleton; public FileCommitPort unchanged. Definition-source read coordination treated separate declared consumer, not silently widened active-only helper.

  @INT-CX-13
  Scenario: CX-13
    Given Original exact packages and context/receipt fixtures for M04,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then FormalWriteReservation blocks same-owner content mutations until matching commit completion. RecoveryAttemptReservation blocks only another recovery attempt and unstable capture; after pinned immutable capture, ordinary healthy owner edits may proceed. Shared M05 catalog short transitions do not create global document mutation lock. Both reserve per-target IO as needed; no OS locks held during owner callbacks.

  @INT-CX-14
  Scenario: CX-14
    Given Original exact packages and context/receipt fixtures for M03,M04,M06
    When exercise corrected cross-owner boundary after joint adoption
    Then Inspection may preserve unknown XML. Clear/merge/install require complete format-specific projector; unsupported fields hard-block affected mutation with exact paths. Freeze typed node/edge/parent/binding mapping before M06 Skeleton; no generic recursive ID rewrite, no label guessing. FreshImportedIds only on explicit confirmed preview; no identity changes hidden under codec.

  @INT-CX-15
  Scenario: CX-15
    Given Original exact packages and context/receipt fixtures for M01,M02,M04,M05,M06,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then AuthenticatedExternalProof is server-owned immutable record with issuer module, operation kind, exact context, raw byte/receipt evidence and target identity; callers pass opaque receipt ID and service resolves in trusted registry or revalidates durable owner record. Never trust UI-copied receipt/complete bool. On restart missing owner record=>Unverified/DependencyNotReady; no fabricated ACK. Result phase codes below normalized, original module reason fields retained.

  @INT-CX-16
  Scenario: CX-16
    Given Original exact packages and context/receipt fixtures for M01,M02,M03,M04,M05,M06,M07
    When exercise corrected cross-owner boundary after joint adoption
    Then One integration patch per owned module, explicit owner edits only; serial shared-path queue. Proposed overlay adds source-fence child and replaces M01 copy rename protocol only after Owner adopts. Rebaseline all already-dirty product paths before each Skeleton slice. Old packet hashes remain immutable; regenerated module revision must point central overlay before gate acceptance.

  @INT-CX-17
  Scenario: CX-17
    Given Original exact packages and context/receipt fixtures for M02,M06
    When exercise corrected cross-owner boundary after joint adoption
    Then Central adoption approves contract choices only. Mark BUILD_GOLDEN_REQUIRED / PROJECTOR_FIXTURES_REQUIRED. Exact module packet updates+independent fixture self-checks required before Skeleton/valid RED; no automatic product-ready promotion. Windows11 native remains separate gate.
