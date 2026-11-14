Feature: Transfer derived design writer attachment
  Background:
    Given one M04-owned live document and one current native writer
  Rule: Transfer preserves the document and retires prior writer authority

    Scenario: TR-01 success
      Given the success transfer condition
      When the current writer requests transfer
      Then the observable outcome is Transferred
      And document content and history remain intact

    Scenario: TR-02 editor-source
      Given the editor-source transfer condition
      When the current writer requests transfer
      Then the observable outcome is Transferred
      And document content and history remain intact

    Scenario: TR-03 numeric-caller-live
      Given the numeric-caller-live transfer condition
      When the current writer requests transfer
      Then the observable outcome is UnauthorizedCaller
      And document content and history remain intact

    Scenario: TR-04 viewer
      Given the viewer transfer condition
      When the current writer requests transfer
      Then the observable outcome is UnauthorizedCaller
      And document content and history remain intact

    Scenario: TR-05 remote
      Given the remote transfer condition
      When the current writer requests transfer
      Then the observable outcome is UnauthorizedCaller
      And document content and history remain intact

    Scenario: TR-06 forged-label
      Given the forged-label transfer condition
      When the current writer requests transfer
      Then the observable outcome is UnauthorizedCaller
      And document content and history remain intact

    Scenario: TR-07 provider
      Given the provider transfer condition
      When the current writer requests transfer
      Then the observable outcome is DependencyNotReady
      And document content and history remain intact

    Scenario: TR-08 identity
      Given the identity transfer condition
      When the current writer requests transfer
      Then the observable outcome is IdentityConflict
      And document content and history remain intact

    Scenario: TR-09 duplicate-owner
      Given the duplicate-owner transfer condition
      When the current writer requests transfer
      Then the observable outcome is IdentityConflict
      And document content and history remain intact

    Scenario: TR-10 generation
      Given the generation transfer condition
      When the current writer requests transfer
      Then the observable outcome is StaleOwner
      And document content and history remain intact

    Scenario: TR-11 revision
      Given the revision transfer condition
      When the current writer requests transfer
      Then the observable outcome is StaleRevision
      And document content and history remain intact

    Scenario: TR-12 missing-binding
      Given the missing-binding transfer condition
      When the current writer requests transfer
      Then the observable outcome is MissingBinding
      And document content and history remain intact

    Scenario: TR-13 ambiguous-target
      Given the ambiguous-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is DependencyNotReady
      And document content and history remain intact

    Scenario: TR-14 changed-target-instance
      Given the changed-target-instance transfer condition
      When the current writer requests transfer
      Then the observable outcome is DependencyNotReady
      And document content and history remain intact

    Scenario: TR-15 target-dead-after-commit
      Given the target-dead-after-commit transfer condition
      When the current writer requests transfer
      Then the observable outcome is TransferredTargetUnavailable
      And document content and history remain intact

    Scenario: TR-16 missing-target
      Given the missing-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is MissingBinding
      And document content and history remain intact

    Scenario: TR-17 revoked-target
      Given the revoked-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is MissingBinding
      And document content and history remain intact

    Scenario: TR-18 unready-target
      Given the unready-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is DependencyNotReady
      And document content and history remain intact

    Scenario: TR-19 no-consent
      Given the no-consent transfer condition
      When the current writer requests transfer
      Then the observable outcome is DependencyNotReady
      And document content and history remain intact

    Scenario: TR-20 viewer-target
      Given the viewer-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is UnauthorizedCaller
      And document content and history remain intact

    Scenario: TR-21 dirty-target
      Given the dirty-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is Busy
      And document content and history remain intact

    Scenario: TR-22 discard-target
      Given the discard-target transfer condition
      When the current writer requests transfer
      Then the observable outcome is Transferred
      And document content and history remain intact

    Scenario: TR-23 typed-false
      Given the typed-false transfer condition
      When the current writer requests transfer
      Then the observable outcome is ProofMismatch
      And document content and history remain intact

    Scenario: TR-24 overflow
      Given the overflow transfer condition
      When the current writer requests transfer
      Then the observable outcome is RevisionOverflow
      And document content and history remain intact

    Scenario: TR-25 capacity
      Given the capacity transfer condition
      When the current writer requests transfer
      Then the observable outcome is CapacityExceeded
      And document content and history remain intact

    Scenario: TR-26 rollback
      Given the rollback transfer condition
      When the current writer requests transfer
      Then the observable outcome is IoFailure
      And document content and history remain intact

    Scenario: TR-27 unknown
      Given the unknown transfer condition
      When the current writer requests transfer
      Then the observable outcome is Indeterminate
      And document content and history remain intact

    Scenario: TR-28 ack-lost
      Given the ack-lost transfer condition
      When the current writer requests transfer
      Then the observable outcome is TransferredAckDeferred
      And document content and history remain intact

    Scenario: TR-29 forged-proof
      Given the forged-proof transfer condition
      When the current writer requests transfer
      Then the observable outcome is ProofMismatch
      And document content and history remain intact

    Scenario: TR-30 repeat
      Given the repeat transfer condition
      When the current writer requests transfer
      Then the observable outcome is StaleOwner
      And document content and history remain intact

    Scenario: TR-31 late-install
      Given the late-install transfer condition
      When the current writer requests transfer
      Then the observable outcome is Discarded
      And document content and history remain intact

    Scenario: TR-32 late-ack
      Given the late-ack transfer condition
      When the current writer requests transfer
      Then the observable outcome is Discarded
      And document content and history remain intact

    Scenario: TR-33 late-get
      Given the late-get transfer condition
      When the current writer requests transfer
      Then the observable outcome is Discarded
      And document content and history remain intact
