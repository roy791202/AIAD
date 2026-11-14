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
    Scenario: COR-R2-current
      Given a projection response is pending for the original view
      And the current view condition is COR R2 current
      When the response arrives
      Then the delivery decision is InstalledProjectionOnly
      And no document acknowledgement is applied
    Scenario: COR-R2-older
      Given a projection response is pending for the original view
      And the current view condition is COR R2 older
      When the response arrives
      Then the delivery decision is DiscardOlderProjection
      And no document acknowledgement is applied
    Scenario: COR-R2-external-revoked-live
      Given a projection response is pending for the original view
      And the current view condition is COR R2 external revoked live
      When the response arrives
      Then the delivery decision is DiscardRevokedAttachment
      And no document acknowledgement is applied
    Scenario: COR-R2-retired
      Given a projection response is pending for the original view
      And the current view condition is COR R2 retired
      When the response arrives
      Then the delivery decision is DiscardRetiredInstance
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-instance
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed instance
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-binding_ref
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed binding_ref
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-document_uuid
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed document_uuid
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-session_uuid
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed session_uuid
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-owner_generation
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed owner_generation
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-project_uuid
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed project_uuid
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-root_instance
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed root_instance
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-changed-runtime_epoch
      Given a projection response is pending for the original view
      And the current view condition is COR R2 changed runtime_epoch
      When the response arrives
      Then the delivery decision is DiscardStaleAuthority
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-instance
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing instance
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-instance-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed instance null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-instance-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed instance bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-instance-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed instance number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-instance-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed instance array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-instance-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed instance object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-binding_ref
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing binding_ref
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-binding_ref-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed binding_ref null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-binding_ref-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed binding_ref bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-binding_ref-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed binding_ref number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-binding_ref-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed binding_ref array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-binding_ref-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed binding_ref object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-document_uuid
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing document_uuid
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-document_uuid-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed document_uuid null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-document_uuid-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed document_uuid bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-document_uuid-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed document_uuid number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-document_uuid-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed document_uuid array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-document_uuid-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed document_uuid object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-session_uuid
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing session_uuid
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-session_uuid-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed session_uuid null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-session_uuid-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed session_uuid bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-session_uuid-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed session_uuid number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-session_uuid-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed session_uuid array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-session_uuid-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed session_uuid object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-owner_generation
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing owner_generation
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-owner_generation-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed owner_generation null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-owner_generation-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed owner_generation bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-owner_generation-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed owner_generation number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-owner_generation-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed owner_generation array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-owner_generation-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed owner_generation object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-project_uuid
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing project_uuid
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-project_uuid-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed project_uuid null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-project_uuid-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed project_uuid bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-project_uuid-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed project_uuid number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-project_uuid-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed project_uuid array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-project_uuid-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed project_uuid object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-root_instance
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing root_instance
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-root_instance-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed root_instance null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-root_instance-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed root_instance bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-root_instance-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed root_instance number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-root_instance-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed root_instance array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-root_instance-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed root_instance object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-runtime_epoch
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing runtime_epoch
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-runtime_epoch-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed runtime_epoch null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-runtime_epoch-bool
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed runtime_epoch bool
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-runtime_epoch-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed runtime_epoch number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-runtime_epoch-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed runtime_epoch array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-runtime_epoch-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed runtime_epoch object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-attachment_active
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing attachment_active
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-attachment_active-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed attachment_active null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-attachment_active-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed attachment_active number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-attachment_active-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed attachment_active array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-attachment_active-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed attachment_active object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-attachment_active-stringfalse
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed attachment_active stringfalse
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-missing-native_live
      Given a projection response is pending for the original view
      And the current view condition is COR R2 missing native_live
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-native_live-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed native_live null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-native_live-number
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed native_live number
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-native_live-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed native_live array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-native_live-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed native_live object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-typed-native_live-stringfalse
      Given a projection response is pending for the original view
      And the current view condition is COR R2 typed native_live stringfalse
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-forged
      Given a projection response is pending for the original view
      And the current view condition is COR R2 forged
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-tamper
      Given a projection response is pending for the original view
      And the current view condition is COR R2 tamper
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-root-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context root null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-root-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context root array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-root-string
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context root string
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-ref-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context ref null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-ref-array
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context ref array
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-ref-object
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context ref object
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
    Scenario: COR-R2-context-observation-null
      Given a projection response is pending for the original view
      And the current view condition is COR R2 context observation null
      When the response arrives
      Then the delivery decision is DiscardMissingTrustedObservation
      And no document acknowledgement is applied
