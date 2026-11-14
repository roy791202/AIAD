Feature: Viewer identity composition proposal
  Background:
    Given a live authorized viewer at generation "3" and revision "9007199254740993"
    And preview operations cannot change the authoritative document or its history
  Rule: Preview lifecycle remains tied to the complete native identity
    @BDD-VIS-1
    Scenario: Refresh replaces one preview before action and close
      Given a preview with a detached mock and one occupied slot
      When the preview is refreshed then acted on and closed
      Then the retired handle rejects actions with PreviewClosed
      And the replacement accepts an action before close
      And close removes the one slot and discards its mock
    @BDD-VIS-2
    Scenario: A changed identity cannot act on another preview
      Given a changed caller, window, project, root, epoch, document, session, generation or handle
      When the viewer operation is admitted at capture or delivery
      Then the operation is rejected without installing a cross-identity result
    @BDD-VIS-3
    Scenario: Invalid identity observation fails closed
      Given an observation with a missing, unknown or incorrectly typed field
      When a viewer operation is admitted
      Then DependencyNotReady is reported
    @BDD-VIS-4
    Scenario: Refresh failure preserves the existing preview slot
      Given a live preview with an existing mock
      When refresh fails before replacement commits
      Then the old handle, mock and slot remain
      And actions are disabled until a fresh preview is admitted
    @BDD-VIS-5
    Scenario: Close acknowledgement is lost after retirement
      Given the provider retired the preview but acknowledgement is lost
      When close completes without trustworthy confirmation
      Then the UI remains CloseUncertain without automatic retry
      And retirement is not falsely rolled back
    @BDD-VIS-6
    Scenario: A late result cannot update a changed root
      Given close committed and the runtime epoch changed before delivery
      When the close result is delivered
      Then the old result is not installed in the UI
      And committed retirement remains
