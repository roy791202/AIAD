Feature: Full identity observation grammar precision
  Background:
    Given an unchanged complete identity admission contract
  Rule: The proposed schema must describe the same tuple grammar
    Scenario: Reject the six previously overaccepted observations
      Given the six original review counterexamples
      When each complete observation is validated
      Then the corrected schema rejects it
      And admission reports dependency not ready at capture and delivery
    Scenario: Accept canonical boundary representations
      Given complete observations with canonical UUIDs and unsigned 64 bit decimal boundaries
      When their grammar is evaluated
      Then schema and identity grammar decisions agree
    Scenario: Preserve semantic admission rejection
      Given a grammatically valid observation with changed authority identity
      When admission evaluates it
      Then existing semantic rejection remains distinct from malformed input
