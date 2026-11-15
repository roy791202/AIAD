Feature: Approval-gated GitWritePort.set_remote_url
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-SET-REMOTE-URL-01-1
  Scenario: Denied approval does not change a remote URL
    Given a repository with remote origin pointing at an old URL
    When set_remote_url is called with GitWriteApproval denied
    Then the call fails as permission denied
    And git remote still lists the old URL

  @PD-GIT-SET-REMOTE-URL-01-2
  Scenario: Approved set-url updates the URL without fetching
    Given a repository with remote origin
    When set_remote_url is called with a valid name, URL, and granted approval
    Then git remote -v lists that name with the new URL
    And no fetch, prune, or push runs

  @PD-GIT-SET-REMOTE-URL-01-3
  Scenario: Unknown remotes and option-like names fail honestly
    Given a repository with remote origin
    When set_remote_url is called for ghost, empty, -f, --push, or --mirror
    Then the call fails without mutating remotes
    And empty URLs fail the same way
