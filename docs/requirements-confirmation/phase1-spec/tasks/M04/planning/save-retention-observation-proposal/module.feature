Feature: Captured save retention observations
  Background:
    Given M04 retains an immutable captured save identity
  Rule: Only M05 evidence establishes material retention
    Scenario: Root failure preserves observed Held evidence
      Given authenticated Held evidence for the captured material versions
      When the committed save cannot verify root transfer
      Then captured material remains observed Held
      And no semantic ACK or release occurs
    Scenario: Released cannot prove transfer
      Given a verified file commit and a Released observation
      When the save response is evaluated
      Then the response is deferred
      And no semantic ACK occurs
