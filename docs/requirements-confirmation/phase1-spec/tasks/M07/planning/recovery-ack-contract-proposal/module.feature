Feature: Captured recovery acknowledgment
  Background:
    Given a captured document version and immutable publication evidence
  Rule: Only the document owner acknowledges an exact retained recovery capture

    @M07-RA-001
    Scenario: valid captured recovery ACK
      Given the recovery evidence and owner state for M07-RA-001
      When recovery acknowledgment is requested
      Then the observable outcome is CapturedRecoveryAcknowledged
      And the formal baseline and live content are preserved

    @M07-RA-002
    Scenario: newer live revision remains dirty
      Given the recovery evidence and owner state for M07-RA-002
      When recovery acknowledgment is requested
      Then the observable outcome is CapturedRecoveryAcknowledged
      And the formal baseline and live content are preserved

    @M07-RA-003
    Scenario: late older ACK cannot regress recovery baseline
      Given the recovery evidence and owner state for M07-RA-003
      When recovery acknowledgment is requested
      Then the observable outcome is Superseded
      And the formal baseline and live content are preserved

    @M07-RA-004
    Scenario: formal baseline never changes
      Given the recovery evidence and owner state for M07-RA-004
      When recovery acknowledgment is requested
      Then the observable outcome is CapturedRecoveryAcknowledged
      And the formal baseline and live content are preserved

    @M07-RA-005
    Scenario: payload raw is not recovery fingerprint
      Given the recovery evidence and owner state for M07-RA-005
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-006
    Scenario: index raw is not recovery fingerprint
      Given the recovery evidence and owner state for M07-RA-006
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-007
    Scenario: wrong transfer issuer
      Given the recovery evidence and owner state for M07-RA-007
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-008
    Scenario: wrong project context
      Given the recovery evidence and owner state for M07-RA-008
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-009
    Scenario: wrong session
      Given the recovery evidence and owner state for M07-RA-009
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-010
    Scenario: stale generation
      Given the recovery evidence and owner state for M07-RA-010
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-011
    Scenario: root deferred retains local integrity without ACK
      Given the recovery evidence and owner state for M07-RA-011
      When recovery acknowledgment is requested
      Then the observable outcome is Deferred
      And the formal baseline and live content are preserved

    @M07-RA-012
    Scenario: unknown root no ACK no retry
      Given the recovery evidence and owner state for M07-RA-012
      When recovery acknowledgment is requested
      Then the observable outcome is UnverifiedOutcome
      And the formal baseline and live content are preserved

    @M07-RA-013
    Scenario: restart lost issuer proof no ACK retry or release
      Given the recovery evidence and owner state for M07-RA-013
      When recovery acknowledgment is requested
      Then the observable outcome is UnverifiedOutcome
      And the formal baseline and live content are preserved

    @M07-RA-014
    Scenario: wrong material version
      Given the recovery evidence and owner state for M07-RA-014
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-015
    Scenario: wrong attempt
      Given the recovery evidence and owner state for M07-RA-015
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-016
    Scenario: wrong owner handle
      Given the recovery evidence and owner state for M07-RA-016
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-017
    Scenario: unknown request key rejected before lookup
      Given the recovery evidence and owner state for M07-RA-017
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-018
    Scenario: wrong index transaction
      Given the recovery evidence and owner state for M07-RA-018
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-019
    Scenario: wrong snapshot
      Given the recovery evidence and owner state for M07-RA-019
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved

    @M07-RA-020
    Scenario: wrong index evidence hash
      Given the recovery evidence and owner state for M07-RA-020
      When recovery acknowledgment is requested
      Then the observable outcome is Rejected
      And the formal baseline and live content are preserved
