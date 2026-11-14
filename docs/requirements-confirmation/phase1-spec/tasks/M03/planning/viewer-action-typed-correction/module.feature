Feature: Typed observations protect detached Viewer state
  Background:
    Given a detached Viewer with existing sequence and mock state
    And provider authenticity and atomic delivery are explicit unverified premises
  Rule: Malformed observations cannot commit
    Scenario: TYPED-1 Reject missing malformed or unknown observation values
      Given an observation outside the proposed closed typed record
      When a Viewer action is requested
      Then a dependency failure is returned
      And the complete preview state remains unchanged
      And no commit or provider call is recorded
  Rule: Existing legitimate semantics remain intact
    Scenario: TYPED-2 Typed observations preserve existing outcomes
      Given a well typed false stale unknown capability or successful observation
      When a Viewer action is requested
      Then the existing complete response and state semantics are preserved
  Rule: Early admission has explicit proposed precedence
    Scenario: TYPED-3 Malformed observation precedes client and sequence errors
      Given malformed observations and a conflicting request condition
      When a Viewer action is requested
      Then the proposed dependency failure takes precedence
      And the sequence and mock state remain unchanged
