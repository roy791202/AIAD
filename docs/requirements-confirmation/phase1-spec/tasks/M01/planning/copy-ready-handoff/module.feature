Feature: Final-path project copy readiness
  Background:
    Given a final-path quarantined copy owned by the existing project wizard
  Rule: Only a fully verified durable copy may become Ready

    Scenario: M01-CR-01 success
      Given the success copy conditions
      When readiness is requested
      Then the outcome is VerifiedPublished

    Scenario: M01-CR-02 target-existing
      Given the target-existing copy conditions
      When readiness is requested
      Then the outcome is RejectedBeforeMutation

    Scenario: M01-CR-03 invalid-identity
      Given the invalid-identity copy conditions
      When readiness is requested
      Then the outcome is RejectedBeforeMutation

    Scenario: M01-CR-04 copy-incomplete
      Given the copy-incomplete copy conditions
      When readiness is requested
      Then the outcome is RejectedBeforeMutation

    Scenario: M01-CR-05 index-unknown
      Given the index-unknown copy conditions
      When readiness is requested
      Then the outcome is DependencyNotReady

    Scenario: M01-CR-06 ready-CAS-unknown
      Given the ready-CAS-unknown copy conditions
      When readiness is requested
      Then the outcome is UncertainPublication

    Scenario: M01-CR-07 owner-loss-after-ready
      Given the owner-loss-after-ready copy conditions
      When readiness is requested
      Then the outcome is DeliveryDeferred

    Scenario: M01-CR-08 source-ACK-deferred
      Given the source-ACK-deferred copy conditions
      When readiness is requested
      Then the outcome is CommittedAckDeferred
