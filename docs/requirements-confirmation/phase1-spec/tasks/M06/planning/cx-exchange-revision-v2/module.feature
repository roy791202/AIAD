Feature: M06 RR revised module behavior
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

  @RR-F6 @BDD-PROJECTOR-MISSING-RR
  Scenario: BDD-PROJECTOR-MISSING-RR
    Given unknown reference-bearing ESS field outside typed projector
    When prepare clear or merge
    Then UnsupportedProjection before mutation
