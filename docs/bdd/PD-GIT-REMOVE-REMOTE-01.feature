Feature: Approval-gated GitWritePort.remove_remote
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-REMOVE-REMOTE-01-1
  Scenario: Denied approval does not remove a remote
    Given a repository with remote upstream
    When remove_remote is called with GitWriteApproval denied
    Then the call fails as permission denied
    And git remote still lists upstream

  @PD-GIT-REMOVE-REMOTE-01-2
  Scenario: Approved remove deletes only that remote
    Given a repository with remotes origin and upstream
    When remove_remote is called for upstream with granted approval
    Then git remote no longer lists upstream
    And origin remains
    And no fetch, prune, or push runs

  @PD-GIT-REMOVE-REMOTE-01-3
  Scenario: Missing and option-like names fail honestly
    Given a repository with remote origin
    When remove_remote is called for a missing name or a name like --prune
    Then the call fails without mutating remotes
