Feature: M02 RR revised module behavior
  Background:
    Given the proposed RR contract and trusted current document identity

  @RR-F3 @BDD-WIRE-EXACT-RR
  Scenario: BDD-WIRE-EXACT-RR
    Given revision decimal string9007199254740993
    When decode and return projection
    Then exact same string with no Number roundtrip

  @RR-F6 @BDD-GOLDEN-MISSING-RR
  Scenario: BDD-GOLDEN-MISSING-RR
    Given 14 template resources or standalone full transitive lock golden absent
    When evaluate renderer readiness
    Then BUILD_GOLDEN_REQUIRED; not valid RED
