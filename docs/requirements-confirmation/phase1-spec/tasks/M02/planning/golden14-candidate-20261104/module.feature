Feature: Reviewable Golden14 candidate bytes
  Scenario: Render a bound candidate twice
    Given an explicit proposed definition and design fixture
    When the candidate is rendered twice
    Then the exact fourteen declared paths have identical expected bytes
    And no proposal is recorded as adopted
  Scenario: Unbound tokens cannot produce accepted output
    Given a candidate with an unknown placeholder
    When rendering is requested
    Then rendering fails explicitly
