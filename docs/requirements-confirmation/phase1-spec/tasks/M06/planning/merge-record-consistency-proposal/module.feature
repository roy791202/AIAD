Feature: Bounded documentary issuer record consistency
  Background:
    Given the retained trusted fixture premise
  Rule: Inconsistent records cannot authorize documentary mutation
    Scenario: RC-1 Valid retained records preserve prior behavior
      When the documented operation is evaluated
      Then its original state and call output is preserved
    Scenario: RC-2 Contradictory record is rejected
      Given a missing unknown mistyped or contradictory retained record field
      When the documented operation is evaluated
      Then rejection occurs before document commit
    Scenario: RC-3 Unknown observations remain unverified
      When a commit observation is unknown
      Then the outcome is unverified without retry or rollback
