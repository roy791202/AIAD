Feature: Approval-gated GitWritePort.add_remote
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-ADD-REMOTE-01-1
  Scenario: Denied approval does not add a remote
    Given a repository with no remote named upstream
    When add_remote is called with GitWriteApproval denied
    Then the call fails as permission denied
    And git remote still has no upstream

  @PD-GIT-ADD-REMOTE-01-2
  Scenario: Approved add records the URL without fetching
    Given a repository with no remote named upstream
    When add_remote is called with a valid name, URL, and granted approval
    Then git remote -v lists that name and URL
    And no fetch, prune, or push runs

  @PD-GIT-ADD-REMOTE-01-3
  Scenario: Duplicate and option-like names fail honestly
    Given a repository that already has remote origin
    When add_remote is called with duplicate origin or names like -f or --mirror
    Then the call fails without mutating remotes
    And empty names or URLs fail the same way
