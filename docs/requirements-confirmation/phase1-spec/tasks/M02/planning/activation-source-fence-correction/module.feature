Feature: Bound activation evidence
  Background:
    Given an immutable saved activation preview for the current project
  Rule: Only coherent evidence authorizes activation
    Scenario: Matching evidence
      Given all source and saved proof bodies match the preview
      When activation evidence is evaluated
      Then activation may be reported
    Scenario: Mismatched evidence
      Given one source or saved proof body differs from the preview
      When activation evidence is evaluated
      Then activation is not reported
  Rule: Invalid input is rejected before action
    Scenario: Unknown activation outcome
      Given an unrecognized activation outcome
      When activation evidence is evaluated
      Then the evidence is rejected without mutation
