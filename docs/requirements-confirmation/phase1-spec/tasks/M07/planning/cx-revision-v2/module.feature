Feature: M07 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F2 @BDD-BOUNDED-READ-RR
  Scenario: BDD-BOUNDED-READ-RR
    Given Held pin covers assetA digest a size3 bytes ABC
    When read with max_bytes3
    Then verified ABC size3; catalog unchanged

  @RR-F3 @BDD-WIRE-EXACT-RR
  Scenario: BDD-WIRE-EXACT-RR
    Given revision decimal string9007199254740993
    When decode and return projection
    Then exact same string with no Number roundtrip

  @RR-F5 @BDD-FOREIGNPROOF-RR
  Scenario: BDD-FOREIGNPROOF-RR
    Given valid receipt from another project or issuer action
    When transfer root or ACK
    Then ProofMismatch; Held retained

  @RR-F6 @BDD-RECOVERY-EDIT-RR
  Scenario: BDD-RECOVERY-EDIT-RR
    Given immutable recovery attempt captures R7 and pin then releases capture fence
    When edit live document while payload copy continues
    Then R8 edit allowed; recovered payload still R7; formal baseline unchanged

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
