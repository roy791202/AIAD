Feature: Save proof preserves captured document and material identity
  Background:
    Given an authorized caller and a retained immutable save capture
  Rule: Every save result uses the same captured evidence
    Scenario: Coordinated substituted evidence cannot replace a capture
      Given a saved file receipt for the retained capture
      When supplied capture and acknowledgement both name different semantic content
      Then the outcome is unverified
      And no semantic acknowledgement is applied
    Scenario: Reordered material proof preserves identity
      Given a transferred material proof containing the exact captured version pairs
      When the same pairs arrive in a different order
      Then the proof represents the same material set
    Scenario: Duplicate material proof is rejected
      Given a committed document file
      When the material proof repeats a captured version pair
      Then acknowledgement remains deferred
      And committed file evidence remains retained
