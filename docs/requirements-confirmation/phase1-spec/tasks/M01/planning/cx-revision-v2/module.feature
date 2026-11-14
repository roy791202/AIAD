Feature: M01-S3 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F3 @BDD-WIRE-EXACT-RR
  Scenario: BDD-WIRE-EXACT-RR
    Given revision decimal string9007199254740993
    When decode and return projection
    Then exact same string with no Number roundtrip

  @RR-F6 @BDD-NATIVE-MISSING-RR
  Scenario: BDD-NATIVE-MISSING-RR
    Given native Windows11 alias fixture not executed
    When evaluate native acceptance
    Then NOT RUN; no product readiness claim
