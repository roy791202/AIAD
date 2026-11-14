Feature: M05 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F2 @BDD-BOUNDED-READ-RR
  Scenario: BDD-BOUNDED-READ-RR
    Given Held pin covers assetA digest a size3 bytes ABC
    When read with max_bytes3
    Then verified ABC size3; catalog unchanged

  @RR-F2 @BDD-RELEASED-RR
  Scenario: BDD-RELEASED-RR
    Given Released pin and same immutable bytes exist
    When read through closed material input
    Then PinNotReadable; zero blob reads

  @RR-F2 @BDD-OVERSIZE-RR
  Scenario: BDD-OVERSIZE-RR
    Given grant size3 and max_bytes2
    When request pinned bytes
    Then LimitExceeded before allocation/read

  @RR-F2 @BDD-CORRUPT-RR
  Scenario: BDD-CORRUPT-RR
    Given grant size3 digest of ABC but object ABD
    When read pinned bytes
    Then IntegrityFailure; no consumer commit or repair

  @RR-F2 @BDD-ROOT-EPOCH-RR
  Scenario: BDD-ROOT-EPOCH-RR
    Given registered Live provider epoch8
    When publish epoch7 manifest
    Then StaleRoots and previous observation retained

  @RR-F3 @BDD-WIRE-EXACT-RR
  Scenario: BDD-WIRE-EXACT-RR
    Given revision decimal string9007199254740993
    When decode and return projection
    Then exact same string with no Number roundtrip

  @RR-F4 @BDD-DEFERRED-RR
  Scenario: BDD-DEFERRED-RR
    Given candidate pinned at R7 and Live root transfer fails after commit
    When install candidate
    Then AppliedRetentionDeferred R8 history1 Held retained

  @RR-F5 @BDD-TRANSITION-KEYS-RR
  Scenario: BDD-TRANSITION-KEYS-RR
    Given one workflow and pin/import/transfer distinct roles ordinal0
    When execute authorized transitions
    Then three distinct operation UUIDs same context workflow; no ReplayConflict

  @RR-F5 @BDD-REPLAY-CONFLICT-RR
  Scenario: BDD-REPLAY-CONFLICT-RR
    Given persisted operation key request digestA
    When reuse same key with digestB
    Then ReplayConflict before catalog write

  @RR-F5 @BDD-RESTART-RR
  Scenario: BDD-RESTART-RR
    Given catalog includes terminal transferred receipt under native store identity
    When resolve receipt after restart
    Then same receipt revalidated; no repeated transfer

  @RR-F5 @BDD-RUNTIME-LOSS-RR
  Scenario: BDD-RUNTIME-LOSS-RR
    Given runtime mutation record lost but pin persists
    When request mutation completion after restart
    Then UnverifiedOutcome Held retained; no synthetic ACK

  @RR-F5 @BDD-FOREIGNPROOF-RR
  Scenario: BDD-FOREIGNPROOF-RR
    Given valid receipt from another project or issuer action
    When transfer root or ACK
    Then ProofMismatch; Held retained

  @RR-F6 @BDD-PROVIDER-UNKNOWN-RR
  Scenario: BDD-PROVIDER-UNKNOWN-RR
    Given all material pairs resolved and pinned but Recovery root provider Unknown
    When install candidate then request release
    Then install permitted; release RetainedReasons UnknownRoots

  @RR-F6 @BDD-NATIVE-MISSING-RR
  Scenario: BDD-NATIVE-MISSING-RR
    Given native Windows11 alias fixture not executed
    When evaluate native acceptance
    Then NOT RUN; no product readiness claim
