Feature: Preserve domain rejection details
  Background:
    Given an authorized caller with a valid document binding
  Rule: Domain rejection preserves the declared variant and fields
    Scenario: Preserve invalid input field
      Given a document operation rejected an invalid document identity
      When the rejection is presented to the caller
      Then the rejection contains InvalidInput and the exact field value
    Scenario: Reject undeclared rejection fields
      Given a rejection representation contains an undeclared field
      When its document contract is checked
      Then the representation is rejected
