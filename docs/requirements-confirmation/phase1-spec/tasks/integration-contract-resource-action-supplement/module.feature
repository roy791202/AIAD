Feature: Deterministic viewer and resource rejection
  Rule: A rejected action preserves state
    Scenario: A recognized action is unsupported by the selected node
      Given an authorized viewer with a current preview
      And the selected container supports no actions
      When activation is requested
      Then UnsupportedAction identifies the node and Activate action
      And mock state and sequence remain unchanged
    Scenario: An undeclared action is rejected
      Given an authorized viewer with a current preview
      When an undeclared action is requested
      Then InvalidRequest reports InvalidActionPayload
      And content and mock state remain unchanged
