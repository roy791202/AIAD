Feature: Exact proposed open and get observable cases
  Background:
    Given document attachment policies await independent review and Owner adoption
  Rule: Only the current authorized view receives an unchanged document projection
    Scenario: BG-01-open
      Given the document attachment condition named 01 open
      When the view requests an attachment
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-02-get
      Given the document attachment condition named 02 get
      When the view requests its current projection
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-03-repeat-open
      Given the document attachment condition named 03 repeat open
      When the view requests an attachment
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-04-repeat-get
      Given the document attachment condition named 04 repeat get
      When the view requests its current projection
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-05-missing-integration
      Given the document attachment condition named 05 missing integration
      When the view requests an attachment
      Then DependencyNotReady is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-reference-empty
      Given the document attachment condition named reference empty
      When the view requests an attachment
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-reference-unknown
      Given the document attachment condition named reference unknown
      When the view requests an attachment
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-reference-path
      Given the document attachment condition named reference path
      When the view requests an attachment
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-native-remote
      Given the document attachment condition named native remote
      When the view requests an attachment
      Then UnauthorizedCaller is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-native-port
      Given the document attachment condition named native port
      When the view requests an attachment
      Then UnauthorizedCaller is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-native-dev
      Given the document attachment condition named native dev
      When the view requests an attachment
      Then UnauthorizedCaller is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-native-retired
      Given the document attachment condition named native retired
      When the view requests an attachment
      Then UnauthorizedCaller is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-native-role
      Given the document attachment condition named native role
      When the view requests an attachment
      Then UnauthorizedCaller is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-unknown-field
      Given the document attachment condition named unknown field
      When the view requests an attachment
      Then InvalidRequest is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-missing-field
      Given the document attachment condition named missing field
      When the view requests an attachment
      Then InvalidRequest is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-type-field
      Given the document attachment condition named type field
      When the view requests an attachment
      Then InvalidRequest is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-get-invalid-uuid
      Given the document attachment condition named get invalid uuid
      When the view requests its current projection
      Then InvalidRequest is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-get-unknown-request-id
      Given the document attachment condition named get unknown request id
      When the view requests its current projection
      Then InvalidRequest is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-identity-project
      Given the document attachment condition named identity project
      When the view requests an attachment
      Then IdentityConflict is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-identity-document
      Given the document attachment condition named identity document
      When the view requests an attachment
      Then IdentityConflict is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-no-adoption
      Given the document attachment condition named no adoption
      When the view requests an attachment
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-forged-observation
      Given the document attachment condition named forged observation
      When the view requests an attachment
      Then ProofMismatch is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-unknown-issuer-record
      Given the document attachment condition named unknown issuer record
      When the view requests an attachment
      Then ProofMismatch is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-stale-generation
      Given the document attachment condition named stale generation
      When the view requests its current projection
      Then StaleOwner is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-stale-session
      Given the document attachment condition named stale session
      When the view requests its current projection
      Then StaleOwner is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-projection-mismatch
      Given the document attachment condition named projection mismatch
      When the view requests an attachment
      Then ProofMismatch is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-get-missing
      Given the document attachment condition named get missing
      When the view requests its current projection
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-instance-replaced
      Given the document attachment condition named instance replaced
      When the view requests its current projection
      Then UnauthorizedCaller is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-external-closed
      Given the document attachment condition named external closed
      When the view requests its current projection
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-restart-old-reference
      Given the document attachment condition named restart old reference
      When the view requests its current projection
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-readonly-nonwriter
      Given the document attachment condition named readonly nonwriter
      When the view requests an attachment
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-readonly-unsupported
      Given the document attachment condition named readonly unsupported
      When the view requests an attachment
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-readonly-missing-form
      Given the document attachment condition named readonly missing form
      When the view requests an attachment
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-viewer-explicit-read
      Given the document attachment condition named viewer explicit read
      When the view requests its current projection
      Then the current immutable projection is returned
      And document content, history and baselines remain unchanged
    Scenario: BG-viewer-no-attachment
      Given the document attachment condition named viewer no attachment
      When the view requests its current projection
      Then MissingBinding is reported
      And document content, history and baselines remain unchanged
    Scenario: BG-delivery-current
      Given a projection response is pending for the original view
      And the current view condition is current
      When the response arrives
      Then the delivery decision is InstalledProjectionOnly
      And no document acknowledgement is applied
    Scenario: BG-delivery-newer
      Given a projection response is pending for the original view
      And the current view condition is newer
      When the response arrives
      Then the delivery decision is InstalledProjectionOnly
      And no document acknowledgement is applied
    Scenario: BG-delivery-older
      Given a projection response is pending for the original view
      And the current view condition is older
      When the response arrives
      Then the delivery decision is DiscardOlderProjection
      And no document acknowledgement is applied
    Scenario: BG-delivery-replaced
      Given a projection response is pending for the original view
      And the current view condition is replaced
      When the response arrives
      Then the delivery decision is DiscardRetiredInstance
      And no document acknowledgement is applied
    Scenario: BG-delivery-closed
      Given a projection response is pending for the original view
      And the current view condition is closed
      When the response arrives
      Then the delivery decision is DiscardRetiredInstance
      And no document acknowledgement is applied
    Scenario: BG-delivery-transfer
      Given a projection response is pending for the original view
      And the current view condition is transfer
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: BG-delivery-root-switch
      Given a projection response is pending for the original view
      And the current view condition is root switch
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: BG-delivery-restart-session
      Given a projection response is pending for the original view
      And the current view condition is restart session
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
