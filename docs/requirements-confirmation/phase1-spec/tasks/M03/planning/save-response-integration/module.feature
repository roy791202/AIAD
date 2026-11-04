Feature: Save outcome distinguishes persistence from acknowledgement
  Background:
    Given an authorized editor bound to the current document owner
  Rule: A verified file commit cannot be reported as unchanged failure
    Scenario: Root delivery fails after the file is committed
      Given revision 7 was captured with a held save pin
      And the destination contains the verified captured bytes
      When formal root delivery fails
      Then CommittedAckDeferred identifies RootTransfer
      And the save pin and evidence are retained
      And no semantic acknowledgement or automatic retry occurs
    Scenario: Receipt evidence does not match the capture
      Given a receipt has a different raw digest from the encoded capture
      When the save result is resolved
      Then UnverifiedOutcome forbids automatic retry
      And no semantic acknowledgement occurs
    Scenario: A captured save finishes with a newer live revision
      Given revision 7 was captured and revision 8 is now live
      When the verified save is acknowledged
      Then only revision 7 and its semantic digest are acknowledged
      And revision 8 remains dirty
      And the recovery baseline remains unchanged
