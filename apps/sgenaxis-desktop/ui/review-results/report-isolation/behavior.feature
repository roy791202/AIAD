Feature: Independent default report projections
  Background:
    Given the required report projector and source fixtures are available
  Rule: Default report requests preserve their own artifacts
    Scenario: Concurrent report requests remain independent
      Given an empty-evidence report and a passing-evidence report
      When both reports are requested concurrently using default destinations
      Then each report has distinct HTML and Markdown paths
      And each report content matches its returned status and source fingerprint
      And the source specifications and evidence remain unchanged
