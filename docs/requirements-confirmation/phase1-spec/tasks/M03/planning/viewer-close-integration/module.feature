Feature: Close only the detached Viewer preview
  Background:
    Given a bound open document with unchanged content and history
    And a detached preview owned by the current native consumer instance

  Rule: Preview closure cannot close or save its document
    @CLOSE-001
    Scenario: Close the current detached preview
      When the user explicitly closes the preview
      Then the preview's mock controls are discarded
      And the document remains bound and open with unchanged content and history

    @CLOSE-002
    Scenario: Close while all preview slots are occupied
      Given four detached previews for the binding
      When the user explicitly closes one preview
      Then exactly one preview slot is released
      And the other previews remain available

  Rule: Only the native owner of a preview may close it
    @CLOSE-003
    Scenario: A different consumer attempts closure
      Given the requesting native instance is different from the preview consumer
      When the user explicitly closes the preview
      Then closure is denied
      And the preview and document remain unchanged

    @CLOSE-004
    Scenario: Invalid preview reference is rejected
      Given an empty preview reference
      When the user explicitly closes the preview
      Then an input error is displayed
      And no preview is closed

  Rule: Closed observations must match the current native lifecycle
    @CLOSE-005
    Scenario: A delayed close response belongs to an old instance
      Given the native consumer was replaced after closure began
      When a delayed closure response arrives
      Then that response is not installed in the replacement instance
      And no retry occurs automatically

    @CLOSE-006
    Scenario: Closure proof is malformed
      Given a closure result without a valid closed observation
      When the result arrives
      Then closure remains visibly uncertain
      And no success is reported
      And no retry occurs automatically

    @CLOSE-007
    Scenario: Repeat closure of a removed preview
      Given the preview reference was removed by a successful closure
      When the user explicitly closes that preview again
      Then the preview is reported closed
      And no second provider closure or replay disclosure occurs

    @CLOSE-008
    Scenario: The provider closes a preview but its response is lost
      Given the provider committed closure and the response was lost
      When the interface observes the missing response
      Then closure remains visibly uncertain
      And the document remains bound and open with unchanged content and history
      And no retry occurs automatically

# Entire precision packet PROPOSED_PENDING_OWNER. Scenarios are planning,
# not product RED or accepted behavior; exact traces live in fixtures.json.
