Feature: M03-H2 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F1 @BDD-ONE-OWNER-RR
  Scenario: BDD-ONE-OWNER-RR
    Given two views of same trusted document at revision7
    When open through facade then apply one accepted edit
    Then both projections revision8 and one owner/session; history depth1

  @RR-F1 @BDD-DEPENDENCY-RR
  Scenario: BDD-DEPENDENCY-RR
    Given owner provider unavailable
    When open design binding
    Then DependencyNotReady; zero session constructors in facade

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
