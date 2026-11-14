Feature: One document Merge and explicit Undo retention handoff
  Background:
    Given one authorized target document and an immutable imported candidate
    And the original to fresh identity mapping is confirmed
  Rule: Applied content cannot be reported as unchanged because retention is deferred

    @BDD-M06-MH-001
    Scenario: known precommit failure
      Given the bounded known precommit failure fixture preconditions
      When the authorized handoff is requested
      Then the observable result is RejectedBeforeMutation
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-002
    Scenario: merge root failure
      Given the bounded merge root failure fixture preconditions
      When the authorized handoff is requested
      Then the observable result is MergeAppliedRetentionDeferred
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-003
    Scenario: undo root failure
      Given the bounded undo root failure fixture preconditions
      When the authorized handoff is requested
      Then the observable result is UndoAppliedRetentionDeferred
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-004
    Scenario: all verified
      Given the bounded all verified fixture preconditions
      When the authorized handoff is requested
      Then the observable result is UndoApplied
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-005
    Scenario: unknown commit
      Given the bounded unknown commit fixture preconditions
      When the authorized handoff is requested
      Then the observable result is UnverifiedOutcome
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-006
    Scenario: wrong target
      Given the bounded wrong target fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-007
    Scenario: wrong context
      Given the bounded wrong context fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-008
    Scenario: wrong digest
      Given the bounded wrong digest fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-009
    Scenario: wrong import map
      Given the bounded wrong import map fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-010
    Scenario: wrong issuer
      Given the bounded wrong issuer fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-011
    Scenario: formal proof is not mutation
      Given the bounded formal proof is not mutation fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-012
    Scenario: stale provider
      Given the bounded stale provider fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-013
    Scenario: import receipt wrong issuer
      Given the bounded import receipt wrong issuer fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-014
    Scenario: unknown body field
      Given the bounded unknown body field fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs

    @BDD-M06-MH-015
    Scenario: wrong source bytes
      Given the bounded wrong source bytes fixture preconditions
      When the authorized handoff is requested
      Then the observable result is ProofMismatch
      And no automatic retry, release, rollback, or formal save occurs
