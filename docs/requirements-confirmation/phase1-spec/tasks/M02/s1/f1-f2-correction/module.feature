@M02_S1_F1_F2 @approved_contract
Feature: Precise missing decisions and structural validation priority
  Background:
    Given a local definition and a verified template candidate
  Rule: Missing-decision explanations identify the actual absent decision
    Scenario: Confirmed topology is not an approval substitute
      Given topology is confirmed but required approval is not verified
      When generation planning is requested
      Then the missing approval cause is reported without falsely reporting topology
  Rule: Invalid structure is rejected before offering definition-only continuation
    Scenario: Unsafe artifact path with missing approval
      Given an artifact escapes its allowed relative path and approval is missing
      When generation planning is requested
      Then the unsafe path is rejected instead of returning a missing-approval continuation
    Scenario: Invalid identity with missing topology
      Given project identity is invalid and topology is unresolved
      When generation planning is requested
      Then invalid identity is reported before missing topology
    Scenario: Duplicate target identity with unresolved requirement
      Given target identity is duplicated and a requirement is unresolved
      When generation planning is requested
      Then duplicate target identity is reported before missing requirements
