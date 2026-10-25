Feature: Source-bound module engineering packet
  Background:
    Given an explicitly selected EluSlot project and source mode
    And a selected module and task

  Rule: Export is a read-only projection with traceable scope
    Scenario: Export a consistent integrated document
      Given an integrated document with an unambiguous module and complete approved bindings
      When the module packet is requested
      Then its facts identify their source and selected module
      And the source and approval state remain unchanged

    Scenario: Preserve external connections without importing another module
      Given the selected module connects to a different module
      When the module packet is requested
      Then the connection identifies the external endpoint
      And unrelated module contents are excluded

    Scenario: Empty module has no invented behavior
      Given the selected module has no members
      When the module packet is requested
      Then the packet reports its missing implementation requirements
      And it invents no nodes or behavior

  Rule: Ambiguous or incomplete specifications cannot authorize implementation
    Scenario Outline: Reject an invalid source binding
      Given the source has <defect>
      When the module packet is requested
      Then the result is not ready for implementation
      And the diagnostic identifies <subject>
      Examples:
        | defect                    | subject          |
        | duplicate module identity | module identity  |
        | missing member            | member reference |
        | missing connection port   | port reference   |
        | unresolved UI document    | UI reference     |
        | conflicting UI sources    | source selection |
        | unsupported format        | format version   |
        | malformed document        | source path      |
        | empty source              | source path      |

    Scenario: Hints do not establish approved behavior
      Given the source contains only behavior hints without approved scenarios
      When the module packet is requested
      Then the hints remain labeled as hints
      And implementation readiness is not granted

    Scenario: Source outside the bound project
      Given the selected source escapes the bound project
      When the module packet is requested
      Then the request is rejected before reading that source

  Rule: A packet remains bound to the captured specification
    Scenario: Repeating an unchanged request
      Given identical source bytes and specification bindings
      When the same module packet is requested again
      Then its semantic payload and fingerprint are identical

    Scenario: A bound source changes
      Given an existing packet whose bound source was changed
      When packet freshness is checked
      Then the packet reports PACKET_STALE
      And it cannot authorize implementation

    Scenario: Publication fails
      Given a previous valid exported packet
      And the new output cannot be published
      When a new module packet is exported
      Then the previous packet remains intact
      And the export reports failure
