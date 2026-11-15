Feature: Approval-gated GitWritePort.init_repo
  Background:
    Given GitWritePort adapters

  @PD-GIT-REPO-INIT-01-1
  Scenario: Denied approval does not init
    Given an empty directory
    When init_repo is called with GitWriteApproval denied
    Then the call fails as permission denied
    And the directory has no .git

  @PD-GIT-REPO-INIT-01-2
  Scenario: Approved init creates a non-bare repository
    Given an empty directory
    When init_repo is called with granted approval
    Then a non-bare .git exists
    And no remote is added and no clone runs

  @PD-GIT-REPO-INIT-01-3
  Scenario: Existing repo and option-like paths fail honestly
    Given a directory that is already a git repo or a --bare/--template path
    When init_repo is called
    Then the call fails without adding remotes
