Feature: Approval-gated GitWritePort.set_upstream
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-SET-UPSTREAM-01-1
  Scenario: Denied approval does not set upstream
    Given a local branch with a known remote-tracking ref
    When set_upstream is called with GitWriteApproval denied
    Then the call fails as permission denied
    And the local branch has no upstream

  @PD-GIT-SET-UPSTREAM-01-2
  Scenario: Approved set-upstream records tracking without fetch or checkout
    Given a local branch and remote-tracking ref origin/main
    When set_upstream is called with granted approval
    Then the local branch tracks origin/main
    And no fetch, pull, push, or checkout runs

  @PD-GIT-SET-UPSTREAM-01-3
  Scenario: Unknown remotes, missing tracking refs, and invalid names fail honestly
    Given a local repository
    When set_upstream is called with a missing remote, missing tracking ref, or option-like names
    Then the call fails without creating remotes or branches
