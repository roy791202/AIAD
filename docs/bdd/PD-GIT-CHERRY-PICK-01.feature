Feature: Approval-gated GitWritePort.cherry_pick
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-CHERRY-PICK-01-1
  Scenario: Denied approval does not cherry-pick
    Given a reachable local commit oid
    When cherry_pick is called with GitWriteApproval denied
    Then the call fails as permission denied
    And HEAD and the worktree stay unchanged

  @PD-GIT-CHERRY-PICK-01-2
  Scenario: Approved cherry-pick applies one commit
    Given a reachable local commit oid
    When cherry_pick is called with granted approval
    Then a new commit with that changeset is on HEAD
    And no rebase, push, or --ff shortcut runs

  @PD-GIT-CHERRY-PICK-01-3
  Scenario: Missing oid, dirty overwrite, and option-like names fail honestly
    Given a local repository
    When cherry_pick is called for a missing oid, -n, --ff, or option-like names
    Then the call fails without mutating HEAD
