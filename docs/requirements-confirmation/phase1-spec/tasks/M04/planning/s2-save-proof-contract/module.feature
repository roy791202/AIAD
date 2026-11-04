Feature: M04 formal-save proof and captured semantic ACK

  Scenario: M04-SP-01 distinct digests
    Given valid receipt, raw C != semantic A
    And same session live R10
    When formal save completes
    Then SavedAcked; ACK(10,A), never ACK(10,C)

  Scenario: M04-SP-02 newer edit
    Given valid receipt forR10
    And same session liveR11 semanticD
    When formal save completes
    Then ACK(10,A), liveR11 untouched and dirty=true

  Scenario: M04-SP-03 wrong target
    Given receipt.target_path differs
    And same owner
    When formal save completes
    Then CommitEvidenceMismatch; ACK calls0

  Scenario: M04-SP-04 wrong previous
    Given receipt.previous_digest differs
    And same owner
    When formal save completes
    Then CommitEvidenceMismatch; ACK calls0

  Scenario: M04-SP-05 wrong raw
    Given receipt.committed_digest differs
    And same owner
    When formal save completes
    Then CommitEvidenceMismatch; ACK calls0

  Scenario: M04-SP-06 empty transaction
    Given receipt.transaction_id empty
    And same owner
    When formal save completes
    Then CommitEvidenceMismatch; ACK calls0

  Scenario: M04-SP-07 owner changed
    Given valid receipt
    And owner generation8
    When formal save completes
    Then CommittedAckDeferred OwnerChanged; ACK calls0

  Scenario: M04-SP-08 session replaced
    Given valid receipt
    And session-B also R10
    When formal save completes
    Then CommittedAckDeferred SessionClosed; ACK calls0

  Scenario: M04-SP-09 ACK rejected
    Given valid receipt
    And S1 existing check_ack rejects stale formal baseline
    When formal save completes
    Then CommittedAckDeferred AckRejected; bytes proof retained

  Scenario: M04-SP-10 replay
    Given same request/capture already terminal
    And same owner
    When formal save completes
    Then same outcome, additional IO/ACK calls0

  Scenario: M04-SP-11 collision
    Given same request key changed capture
    And same owner
    When formal save completes
    Then RequestConflict before IO

  Scenario: M04-SP-12 busy
    Given IO Busy
    And same owner
    When formal save completes
    Then NotCommitted Busy fields unchanged, ACK0

  Scenario: M04-SP-13 recovery
    Given IO RecoveryRequired
    And same owner
    When formal save completes
    Then exact diagnostics retained, ACK0, R4 gating required

  Scenario: M04-SP-14 baselines
    Given formal save ACK succeeds
    And snapshot baseline differs
    When formal save completes
    Then snapshot baseline remains exactly unchanged
