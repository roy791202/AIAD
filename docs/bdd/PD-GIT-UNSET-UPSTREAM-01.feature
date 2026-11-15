Feature: Approval-gated GitWritePort.unset_upstream
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-UNSET-UPSTREAM-01-1
  Scenario: Denied approval does not clear upstream
    Given a local branch tracking origin/main
    When unset_upstream is called with GitWriteApproval denied
    Then the call fails as permission denied
    And the local branch still tracks origin/main

  @PD-GIT-UNSET-UPSTREAM-01-2
  Scenario: Approved unset-upstream clears tracking without checkout
    Given a local branch tracking origin/main
    When unset_upstream is called with granted approval
    Then the local branch has no upstream
    And HEAD, remotes, and worktree stay unchanged

  @PD-GIT-UNSET-UPSTREAM-01-3
  Scenario: Missing branch, no upstream, and detached HEAD fail honestly
    Given a local repository
    When unset_upstream is called for a missing local branch, a branch with no upstream, or empty local on detached HEAD
    Then the call fails without mutating other branches
