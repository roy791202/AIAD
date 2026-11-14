Feature: Copy readiness at the final target
  Background:
    Given project copy readiness is planned for one final target
    And native authenticity and issuer durability remain unverified document premises

  Rule: success
    @BDD-CC-01
    Scenario: success
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then VerifiedPublished

  Rule: target-existing
    @BDD-CC-02
    Scenario: target-existing
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then RejectedBeforeMutation

  Rule: invalid-identity
    @BDD-CC-03
    Scenario: invalid-identity
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then RejectedBeforeMutation

  Rule: copy-incomplete
    @BDD-CC-04
    Scenario: copy-incomplete
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then RejectedBeforeMutation

  Rule: index-unknown
    @BDD-CC-05
    Scenario: index-unknown
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then DependencyNotReady

  Rule: ready-CAS-unknown
    @BDD-CC-06
    Scenario: ready-CAS-unknown
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then UncertainPublication

  Rule: owner-loss-after-ready
    @BDD-CC-07
    Scenario: owner-loss-after-ready
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then DeliveryDeferred

  Rule: source-ACK-deferred
    @BDD-CC-08
    Scenario: source-ACK-deferred
      Given A copy prepared at its final target with declared immutable document authority premises
      When Readiness is evaluated
      Then CommittedAckDeferred

  Rule: Resealing changed copy evidence cannot create issuer authority
    @BDD-CC-09
    Scenario: Resealing changed copy evidence cannot create issuer authority
      Given Trusted copy evidence for the captured request
      When Changed project bytes, path, catalog generation, source snapshot or lease are submitted
      Then Readiness is rejected without changing project state

  Rule: Malformed or incomplete requests are rejected safely
    @BDD-CC-10
    Scenario: Malformed or incomplete requests are rejected safely
      Given A copy whose current project state is unchanged
      When A request has missing, unknown, empty or incorrectly typed fields
      Then Readiness is rejected before issuer lookup or state changes

  Rule: A coherent different copy is accepted under its own evidence premise
    @BDD-CC-11
    Scenario: A coherent different copy is accepted under its own evidence premise
      Given A different coherent copy and its matching immutable document evidence
      When Readiness is evaluated
      Then Readiness is verified in the document model

  Rule: Uncertain Ready has priority over delivery loss
    @BDD-CC-12
    Scenario: Uncertain Ready has priority over delivery loss
      Given Unknown Ready outcome and owner delivery unavailable
      When Readiness is evaluated
      Then Publication remains uncertain without retry or cleanup

  Rule: Owner loss has priority over ACK loss after Ready
    @BDD-CC-13
    Scenario: Owner loss has priority over ACK loss after Ready
      Given Verified Ready while both owner and ACK are unavailable
      When Readiness is evaluated
      Then Delivery is deferred and Ready evidence retained
