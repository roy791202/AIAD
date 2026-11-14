Feature: M04 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F1 @BDD-ONE-OWNER-RR
  Scenario: BDD-ONE-OWNER-RR
    Given two views of same trusted document at revision7
    When open through facade then apply one accepted edit
    Then both projections revision8 and one owner/session; history depth1

  @RR-F3 @BDD-WIRE-EXACT-RR
  Scenario: BDD-WIRE-EXACT-RR
    Given revision decimal string9007199254740993
    When decode and return projection
    Then exact same string with no Number roundtrip

  @RR-F3 @BDD-WIRE-OVERFLOW-RR
  Scenario: BDD-WIRE-OVERFLOW-RR
    Given expected_revision string18446744073709551616
    When submit save
    Then InvalidRequest Range; no reservation/IO

  @RR-F3 @BDD-WIRE-NUMBER-RR
  Scenario: BDD-WIRE-NUMBER-RR
    Given expected_revision JSON number7
    When submit save
    Then InvalidRequest Type; no owner mutation

  @RR-F4 @BDD-DEFERRED-RR
  Scenario: BDD-DEFERRED-RR
    Given candidate pinned at R7 and Live root transfer fails after commit
    When install candidate
    Then AppliedRetentionDeferred R8 history1 Held retained

  @RR-F4 @BDD-REPLAY-RR
  Scenario: BDD-REPLAY-RR
    Given retained result of installed request R8
    When retry identical request
    Then same AppliedRetentionDeferred receipt; no second commit

  @RR-F4 @BDD-NOCHANGE-RR
  Scenario: BDD-NOCHANGE-RR
    Given candidate semantically equals R7
    When install candidate
    Then NoChange revision7 history unchanged

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

  @RR-F6 @BDD-FORMAL-BUSY-RR
  Scenario: BDD-FORMAL-BUSY-RR
    Given formal write reservation at R7 before IO completion
    When submit edit
    Then Busy and revision7 unchanged

  @RR-F6 @BDD-LATE-ACK-RR
  Scenario: BDD-LATE-ACK-RR
    Given R7 file receipt verified; reservation released on IO completion; roots pending; Healthy edit advances R8
    When finish captured R7 root transfer and semantic ACK
    Then formal baseline R7; live R8 dirty; no rollback

  @RR-F6 @BDD-RECOVERY-EDIT-RR
  Scenario: BDD-RECOVERY-EDIT-RR
    Given immutable recovery attempt captures R7 and pin then releases capture fence
    When edit live document while payload copy continues
    Then R8 edit allowed; recovered payload still R7; formal baseline unchanged

  @RR-F6 @BDD-PROJECTOR-MISSING-RR
  Scenario: BDD-PROJECTOR-MISSING-RR
    Given unknown reference-bearing ESS field outside typed projector
    When prepare clear or merge
    Then UnsupportedProjection before mutation
