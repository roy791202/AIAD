Feature: Snapshot publication handoff
  Background:
    Given an immutable captured recovery attempt and trusted issuer fixtures
  Rule: Local integrity and source acknowledgement are separate

  Scenario: M07-PH-001 success
    Given the full publication fixture M07-PH-001
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is PublicationAcknowledged

  Scenario: M07-PH-002 index-failure
    Given the full publication fixture M07-PH-002
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is NotReady

  Scenario: M07-PH-003 index-unknown
    Given the full publication fixture M07-PH-003
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is UncertainPublication

  Scenario: M07-PH-004 root-deferred
    Given the full publication fixture M07-PH-004
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is SourceRetentionDeferred

  Scenario: M07-PH-005 stale-owner
    Given the full publication fixture M07-PH-005
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is CommittedAckDeferred

  Scenario: M07-PH-006 newer-live-capture
    Given the full publication fixture M07-PH-006
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is PublicationAcknowledged

  Scenario: M07-PH-007 captured-ack-only
    Given the full publication fixture M07-PH-007
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is PublicationAcknowledged

  Scenario: M07-PH-008 restart-proof-loss
    Given the full publication fixture M07-PH-008
    When the snapshot publication outcome is reconciled
    Then the observable handoff status is UnverifiedOutcome
