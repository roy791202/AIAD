Feature: Formal save retention handoff
  Background:
    Given a captured formal save with one held retention pin
  Rule: Only matching issuer evidence may establish a transferred root

  @BDD-RH-01
  Scenario: transfer
    Given the immutable save evidence and verified outcome
    When the formal root handoff is evaluated
    Then the observation is Transferred
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-02
  Scenario: replay
    Given the immutable save evidence and same outcome
    When the formal root handoff is evaluated
    Then the observation is SameReceipt
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-03
  Scenario: body-change
    Given the immutable save evidence and changed outcome
    When the formal root handoff is evaluated
    Then the observation is ReplayConflict
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-04
  Scenario: purpose-change
    Given the immutable save evidence and changed-binding outcome
    When the formal root handoff is evaluated
    Then the observation is ProofMismatch
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-05
  Scenario: root-change
    Given the immutable save evidence and changed outcome
    When the formal root handoff is evaluated
    Then the observation is ReplayConflict
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-06
  Scenario: pin-change
    Given the immutable save evidence and changed-binding outcome
    When the formal root handoff is evaluated
    Then the observation is ProofMismatch
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-07
  Scenario: proof-change
    Given the immutable save evidence and changed-binding outcome
    When the formal root handoff is evaluated
    Then the observation is ProofMismatch
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-08
  Scenario: precas-failure
    Given the immutable save evidence and precommit outcome
    When the formal root handoff is evaluated
    Then the observation is Held
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-09
  Scenario: priorcas-unknown
    Given the immutable save evidence and unknown outcome
    When the formal root handoff is evaluated
    Then the observation is Indeterminate
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-10
  Scenario: aftercas-proofloss
    Given the immutable save evidence and prooflost outcome
    When the formal root handoff is evaluated
    Then the observation is Indeterminate
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-11
  Scenario: restart-missing
    Given the immutable save evidence and restart-missing outcome
    When the formal root handoff is evaluated
    Then the observation is UnverifiedOutcome
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-12
  Scenario: restart-verified
    Given the immutable save evidence and restart-verified outcome
    When the formal root handoff is evaluated
    Then the observation is SameReceipt
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-13
  Scenario: issuer-missing
    Given the immutable save evidence and missing outcome
    When the formal root handoff is evaluated
    Then the observation is NOT_PROVEN
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-14
  Scenario: fence-missing
    Given the immutable save evidence and missing outcome
    When the formal root handoff is evaluated
    Then the observation is NOT_PROVEN
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-15
  Scenario: revoked-replay
    Given the immutable save evidence and denied outcome
    When the formal root handoff is evaluated
    Then the observation is PermissionDenied
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-16
  Scenario: wrong-raw
    Given the immutable save evidence and changed-binding outcome
    When the formal root handoff is evaluated
    Then the observation is ProofMismatch
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-17
  Scenario: root-released
    Given the immutable save evidence and changed-binding outcome
    When the formal root handoff is evaluated
    Then the observation is ProofMismatch
    And no automatic release or semantic acknowledgement occurs

  @BDD-RH-18
  Scenario: wrong-purpose
    Given the immutable save evidence and changed-binding outcome
    When the formal root handoff is evaluated
    Then the observation is ProofMismatch
    And no automatic release or semantic acknowledgement occurs
