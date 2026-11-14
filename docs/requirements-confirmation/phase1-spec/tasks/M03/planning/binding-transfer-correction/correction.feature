Feature: Typed transfer observation seams (PROPOSED)
  Background:
    Given a valid source writer and trusted target consent
  Rule: Undeclared seam values cannot authorize transfer
    Scenario: TR-COR-1 Malformed provider or undeclared outcome
      Given a missing or incorrectly typed transfer observation
      When transfer is requested
      Then no transfer is committed by the document model
      And no authorizing receipt is issued
  Rule: Authority metadata must retain exact types
    Scenario: TR-COR-2 Malformed root or scalar authority metadata
      Given malformed source or target metadata
      When transfer is requested
      Then a typed diagnostic is returned
      And the document model remains unchanged
