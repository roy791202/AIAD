Feature: M01 request replay and detached completion
  # Proposed only; no executable RED or approved new architecture
  Background:
    Given an authenticated owner and an immutable request capture

  Scenario: S3-RQ-01 same_inflight
    Given request record is running
    And caller authority is current
    When the same capture is submitted
    Then result is IN_FLIGHT
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-02 changed_inflight
    Given request record is running
    And caller authority is current
    When the changed capture is submitted
    Then result is REQUEST_ID_CONFLICT
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-03 same_committed
    Given request record is committed
    And caller authority is current
    When the same capture is submitted
    Then result is original committed outcome
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-04 changed_committed
    Given request record is committed
    And caller authority is current
    When the changed capture is submitted
    Then result is REQUEST_ID_CONFLICT
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-05 same_failed
    Given request record is precommit_failed
    And caller authority is current
    When the same capture is submitted
    Then result is original failure
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-06 same_partial
    Given request record is partial
    And caller authority is current
    When the same capture is submitted
    Then result is original partial evidence
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-07 same_recovery
    Given request record is recovery_required
    And caller authority is current
    When the same capture is submitted
    Then result is original recovery evidence
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-08 foreign_owner
    Given request record is committed
    And caller authority is foreign
    When the same capture is submitted
    Then result is UNAUTHORIZED
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-09 stale_epoch
    Given request record is committed
    And caller authority is expired
    When the same capture is submitted
    Then result is STALE_OWNER
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-10 capacity
    Given request record is absent_full
    And caller authority is current
    When the new capture is submitted
    Then result is REQUEST_CAPACITY
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-11 late_committed
    Given request record is completing_commit
    And caller authority is detached
    When the same capture is submitted
    Then result is committed / detached
    And additional persistence calls equal 0
    And no automatic project switch occurs

  Scenario: S3-RQ-12 new_request
    Given request record is absent
    And caller authority is current
    When the new capture is submitted
    Then result is reserve then invoke S2 once
    And additional persistence calls equal 1
    And no automatic project switch occurs
