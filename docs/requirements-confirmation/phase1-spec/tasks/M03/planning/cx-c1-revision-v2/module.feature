Feature: M03-C1 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F3 @BDD-WIRE-EXACT-RR
  Scenario: BDD-WIRE-EXACT-RR
    Given revision decimal string9007199254740993
    When decode and return projection
    Then exact same string with no Number roundtrip
