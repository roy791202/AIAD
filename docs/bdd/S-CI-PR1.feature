Feature: Reproducible PR integration without weakening acceptance
  Background:
    Given a clean checkout of PR 1 with its declared fixtures

  @S-CI-PR1-1
  Scenario: Execute the declared CI suites from a clean checkout
    Given required tools and native fixture helpers are available
    When the CI verification is executed
    Then all original behavioral assertions are evaluated
    And missing prerequisites are failures rather than successful verification

  @S-CI-PR1-2
  Scenario: Reject an executable test disable while accepting quoted evidence
    Given a staged change containing test code or review evidence
    When the test-disable guard inspects the staged source
    Then newly executable test disables are rejected
    And quoted anti-disable assertions are accepted
