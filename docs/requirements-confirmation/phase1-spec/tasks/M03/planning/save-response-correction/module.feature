Feature: Save proof evidence controls acknowledgement
  Background:
    Given a verified captured file save
  Rule: Only matching owner and root evidence permits semantic acknowledgement
    Scenario: Root receipt belongs to another request
      Given the root receipt belongs to another request
      When acknowledgement eligibility is evaluated
      Then CommittedAckDeferred reports ProofMismatch
      And no semantic acknowledgement occurs
    Scenario: Current owner changed
      Given the current owner differs from the captured owner
      When acknowledgement eligibility is evaluated
      Then evidence is retained as deferred
      And no proof is delivered to the replacement caller
    Scenario: Request revision exceeds unsigned 64 bit range
      Given the request revision is 18446744073709551616
      When the complete request is validated
      Then validation rejects the request before IO
