Feature: Owner-controlled document Undo
  Background:
    Given an authorized document binding exists
  Rule: Undo never claims rollback after a confirmed mutation

  @UNDO-B1
  Scenario: Restore prior state
    Given a writable document at revision 7 with two Undo entries
    When the owner requests Undo once
    Then the prior content becomes revision 8 and one entry moves to Redo

  @UNDO-B2
  Scenario: Retain committed outcome
    Given Undo has changed content to revision 8
    When retention of the outgoing history fails
    Then revision 8 remains active with retention pending and the actual evidence is retained

  @UNDO-B3
  Scenario: Replay without mutation
    Given an authorized Undo request has a retained terminal outcome
    When the identical request is repeated
    Then the original outcome is returned and no further Undo occurs

  @UNDO-B4
  Scenario: Reject stale input
    Given an active revision differs from the requested revision
    When a new Undo request is submitted
    Then the request is rejected and content and history remain unchanged

  @UNDO-B5
  Scenario: Reject unauthorized caller
    Given a viewer lacks writer authority
    When the viewer requests Undo
    Then the request is denied without private proof disclosure

  @UNDO-B6
  Scenario: Handle empty history
    Given a writable document has no Undo history
    When Undo is requested
    Then the request is rejected as NoUndo and content and history remain unchanged

  @UNDO-B7
  Scenario: Reject forged proof
    Given a request contains a client supplied proof field
    When Undo is requested
    Then the malformed request is rejected before mutation

  @UNDO-B8
  Scenario: Preserve no-save boundary
    Given a document has Undo history
    When Undo is requested
    Then no formal file save or formal save acknowledgement occurs
