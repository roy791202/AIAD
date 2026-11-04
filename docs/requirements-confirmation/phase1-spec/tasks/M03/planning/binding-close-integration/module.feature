Feature: Detach a derived design binding safely
  Background:
    Given a live document with one authoritative owner and a trusted attached native view
  Rule: Closing a view preserves the document and revokes that view authority

    @CL-01
    Scenario: CL-01 Authorized editor detaches its own derived binding
      Given the valid attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Closed
      And the document content and history remain unchanged

    @CL-02
    Scenario: CL-02 Viewer cannot close a binding
      Given the viewer attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is UnauthorizedCaller
      And the document content and history remain unchanged

    @CL-03
    Scenario: CL-03 Remote origin cannot close a binding
      Given the remote attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is UnauthorizedCaller
      And the document content and history remain unchanged

    @CL-04
    Scenario: CL-04 Replacement native instance cannot reuse a binding
      Given the replacement attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is UnauthorizedCaller
      And the document content and history remain unchanged

    @CL-05
    Scenario: CL-05 Main cannot arbitrarily detach another editor attachment
      Given the foreign attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is MissingBinding
      And the document content and history remain unchanged

    @CL-06
    Scenario: CL-06 Unknown binding fails closed
      Given the missing attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is MissingBinding
      And the document content and history remain unchanged

    @CL-07
    Scenario: CL-07 Absent M04 integration cannot detach
      Given the dependency attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is DependencyNotReady
      And the document content and history remain unchanged

    @CL-08
    Scenario: CL-08 Stale owner generation preserves attachment
      Given the generation attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is StaleOwner
      And the document content and history remain unchanged

    @CL-09
    Scenario: CL-09 Stale revision preserves attachment
      Given the revision attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is StaleRevision
      And the document content and history remain unchanged

    @CL-10
    Scenario: CL-10 Unconfirmed dirty writer cannot detach
      Given the dirty attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Busy
      And the document content and history remain unchanged

    @CL-11
    Scenario: CL-11 M04 refusal cannot be interpreted as detach
      Given the m04-refusal attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is DependencyNotReady
      And the document content and history remain unchanged

    @CL-12
    Scenario: CL-12 Confirmed writer detach leaves document live and history intact
      Given the writer attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Closed
      And the document content and history remain unchanged

    @CL-13
    Scenario: CL-13 Repeated identical close is idempotent within fixture retention
      Given the repeat attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Closed
      And the document content and history remain unchanged

    @CL-14
    Scenario: CL-14 Changed close capture is not a replay
      Given the changed attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is MissingBinding
      And the document content and history remain unchanged

    @CL-15
    Scenario: CL-15 Full tombstone cache refuses before M04 detach
      Given the capacity attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is CapacityExceeded
      And the document content and history remain unchanged

    @CL-16
    Scenario: CL-16 New runtime epoch cannot disclose old close state
      Given the epoch attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is MissingBinding
      And the document content and history remain unchanged

    @CL-17
    Scenario: CL-17 Closed attachment blocks late get delivery while window lives
      Given the late-get attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-18
    Scenario: CL-18 Closed attachment blocks late mutation result delivery
      Given the late-install attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-19
    Scenario: CL-19 Close does not apply a late formal ACK
      Given the late-ack attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-20
    Scenario: CL-20 Missing current observation blocks delivery
      Given the missing-observation attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-21
    Scenario: CL-21 Caller-forged observation cannot authorize delivery
      Given the forged-observation attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-22
    Scenario: CL-22 Wrong current owner generation blocks delivery
      Given the delivery-generation attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-23
    Scenario: CL-23 Wrong attachment flag type blocks delivery
      Given the typed-observation attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Discarded
      And the document content and history remain unchanged

    @CL-24
    Scenario: CL-24 Close revokes candidates previews and replay disclosure
      Given the revocation attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is Closed
      And the document content and history remain unchanged

    @CL-25
    Scenario: CL-25 Malformed M04 detach observation has no partial effect
      Given the bad-detach attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is ProofMismatch
      And the document content and history remain unchanged

    @CL-26
    Scenario: CL-26 Caller discard flag cannot replace missing M04 dirty decision
      Given the discard-without-owner attachment condition
      When the attachment lifecycle action is requested
      Then the observable outcome is DependencyNotReady
      And the document content and history remain unchanged
