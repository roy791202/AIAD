Feature: M01 wizard entry and lifecycle preparation
  # PLANNED: not executable RED and not an approved new S3 contract

  Scenario: S3-ENTRY-01
    Given native picker cancelled
    When begin requested
    Then no draft persistence or current-project switch

  Scenario: S3-ENTRY-02
    Given raw path or another window selection
    When begin requested
    Then explicit rejection and zero store calls

  Scenario: S3-ENTRY-03
    Given draft belongs to another session
    When update requested
    Then owner rejection and unchanged revision

  Scenario: S3-ENTRY-04
    Given captured revision is stale
    When save requested
    Then conflict without store call

  Scenario: S3-ENTRY-05
    Given same request ID and identical payload
    When save repeated
    Then one commit and same correlated terminal result

  Scenario: S3-ENTRY-06
    Given same request ID and different payload
    When save requested
    Then explicit request conflict and no second commit

  Scenario: S3-ENTRY-07
    Given owner changes while commit is pending
    When old completion arrives
    Then persisted proof retained and current project unchanged

  Scenario: S3-ENTRY-08
    Given store returns Partial or RecoveryRequired
    When save completes
    Then structured non-success result and no current-project switch

  Scenario: S3-ENTRY-09
    Given each of three old entry routes
    When user starts creation
    Then wizard route only; no deprecated direct-create bypass

  Scenario: S3-ENTRY-10
    Given unfinished decisions exist
    When user saves draft at any of six steps
    Then draft resumable without falsely finalizing or generating
