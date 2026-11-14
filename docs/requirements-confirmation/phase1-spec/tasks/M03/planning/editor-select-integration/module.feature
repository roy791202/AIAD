Feature: Ephemeral Editor selection
  Background:
    Given a current native Editor bound to its document
  Rule: Selection never changes document content

  Scenario: ES-1 select
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-2 clear
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-3 repeat
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-4 request-expected_revision-8
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-5 request-expected_generation-6
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-6 request-binding_ref-00000000-0000-4000-8000-000000000000
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-7 request-node_id-missing
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-8 request-node_id-
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-9 request-expected_revision-18446744073709551616
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-10 request-expected_revision-True
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-11 request-expected_generation-09
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-12 missing-binding_ref
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-13 missing-expected_generation
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-14 missing-expected_revision
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-15 missing-node_id
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-16 provider-role-ui-viewer
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-17 provider-origin-https://evil.invalid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-18 provider-native_live-False
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-19 provider-native_live-true
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-20 provider-ready-False
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-21 provider-ready-false
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-22 provider-outcome-Rejected
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-23 provider-outcome-{}
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-24 provider-capture-{}
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-25 provider-delivery-{}
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-26 foreign-binding_ref
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-27 foreign-document_uuid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-28 foreign-session_uuid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-29 foreign-project_uuid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-30 foreign-root_instance
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-31 foreign-runtime_epoch
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-32 foreign-window_instance
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-33 foreign-generation
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-34 late-binding_ref
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-35 late-document_uuid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-36 late-session_uuid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-37 late-project_uuid
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-38 late-root_instance
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-39 late-runtime_epoch
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-40 late-window_instance
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-41 late-generation
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-42 duplicate-node
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-43 foreign-node
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-44 bad-node-bool
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-45 unknown-request
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-46 root-None
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-47 root-False
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-48 root-[]
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-49 root-{}
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-50 root-''
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation

  Scenario: ES-51 root-0
    Given the declared fixture state
    When the author selects the declared node
    Then the selection result and preserved document match the declared expectation
