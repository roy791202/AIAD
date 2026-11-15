Feature: Approval-gated GitWritePort.rename_remote
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-RENAME-REMOTE-01-1
  Scenario: Denied approval does not rename a remote
    Given a repository with remote origin
    When rename_remote is called with GitWriteApproval denied
    Then the call fails as permission denied
    And git remote still lists origin

  @PD-GIT-RENAME-REMOTE-01-2
  Scenario: Approved rename keeps the URL and does not fetch
    Given a repository with remote origin
    When rename_remote is called from origin to upstream with granted approval
    Then git remote lists upstream with the same URL
    And origin is gone
    And no fetch, set-url extra, or push runs

  @PD-GIT-RENAME-REMOTE-01-3
  Scenario: Unknown old, duplicate new, and invalid names fail honestly
    Given a repository with remotes origin and upstream
    When rename_remote is called for a missing old name, duplicate new name, or option-like names
    Then the call fails without mutating remotes
