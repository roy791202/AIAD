Feature: Keep the active run when Assign is pressed again
  Scenario: Duplicate assignment cannot discard ongoing polling
    Given an active run with final output still pending
    When Assign is pressed again
    Then no duplicate start request is sent
    And the active run continues polling
    And its final output appears once before its terminal result
    And a new run may start after completion
