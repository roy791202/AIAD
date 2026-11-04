Feature: Native snapshot responsiveness acceptance profile (proposed, not run)
  Scenario: BDD-M08-N08-PROPOSED responsive selection during an observed write
    Given an eligible locked artifact on actual Windows11 x64 in a disposable profile
    And timestamp uncertainty is at most 20milliseconds
    And at least 3 inputs overlap a verifiable snapshot write interval
    When 30 ordinary selection inputs are issued over 30seconds
    Then every acknowledgement matches its input object identity
    And conservative nearest-rank p95 latency is at most 250milliseconds
    And maximum conservative latency is at most 1000milliseconds
    And source content and pending-edit accounting remain consistent

  Scenario: BDD-M08-N08-OBSERVATION missing write interval
    Given no verifiable snapshot write interval is available
    When responsiveness observations are evaluated
    Then the observation is classified as blocked
    And no native PASS or product failure is inferred from insufficient observation
