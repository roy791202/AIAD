Feature: Attach and observe a design document
  Background:
    Given the open and get policy is proposed pending independent review and Owner adoption
    And a trusted native caller may request an existing document attachment
  Rule: A view never becomes a second document owner
    Scenario: BG-01 Attach an identity-bound current document
      Given the document already has an authenticated current owner
      When the authorized view opens that document
      Then the view receives the current immutable design projection
      And the document content, history and baselines remain unchanged
    Scenario: BG-02 Read an attached current projection
      Given the current native view has an active attachment
      When the view requests its projection
      Then the current projection is returned without document mutation
    Scenario: BG-05 Missing owner integration
      Given owner attachment integration is unavailable
      When the authorized view opens the trusted document
      Then dependency unavailability is reported
      And no document or attachment is invented
  Rule: Native authority and identity are preserved
    Scenario Outline: Reject an unauthorized or stale request
      Given <condition>
      When a projection is requested
      Then <outcome>
      And document state remains unchanged
      Examples:
        | condition                           | outcome                       |
        | a remote caller                     | caller rejection is reported  |
        | a replaced native window instance   | caller rejection is reported  |
        | an old owner generation             | stale ownership is reported   |
        | an old session                      | stale ownership is reported   |
        | a closed attachment                 | missing binding is reported   |
        | an unknown issuer observation       | proof mismatch is reported    |
        | an empty document reference         | missing binding is reported   |
        | a foreign document identity         | identity conflict is reported |
    Scenario: Existing viewer reads only its explicit attachment
      Given a viewer has a trusted explicit attachment
      When the viewer requests its projection
      Then an immutable read-only projection is returned
    Scenario: Unsupported content remains preserved and inert
      Given a document contains unsupported content
      When an authorized view opens the document
      Then the unsupported content remains present
      And editing remains disabled
  Rule: These commands do not claim mutation replay
    Scenario: An extra request identity is rejected
      Given an otherwise valid document open request
      When an undeclared request identity is included
      Then the request is rejected as an unknown field
      And no owner dependency is called
