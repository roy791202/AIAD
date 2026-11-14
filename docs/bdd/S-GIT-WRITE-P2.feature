Feature: Gated Git worktree writes after commit/push
  Background:
    Given a local git workbench with GitWritePort wired through GitWriteApproval
    And the UI never invokes git CLI directly

  @S-GIT-WRITE-P2-1
  Scenario: Approve staging a single tracked path
    Given a dirty tracked file under the repo root
    When the user approves git_write_stage_file for that path
    Then the path is staged and the worktree content is unchanged
    And a denied approval leaves the index and worktree unchanged

  @S-GIT-WRITE-P2-2
  Scenario: Approve unstaging a single path
    Given a staged tracked file under the repo root
    When the user approves git_write_unstage_file for that path
    Then the path is unstaged and the worktree content is unchanged
    And in-progress merge or rebase with unmerged paths fails honestly

  @S-GIT-WRITE-P2-3
  Scenario: Approve discarding one worktree file to the index
    Given a dirty tracked file that is not in an unmerged conflict state
    When the user approves git_write_discard_file for that path
    Then the worktree file matches the index
    And a denied approval leaves the worktree unchanged
    And untracked files are not deleted by discard

  @S-GIT-WRITE-P2-4
  Scenario: Reject discard of a path outside the repo or during conflict
    Given a path that is outside the repo or is an unmerged conflict path
    When discard is requested even with approval
    Then the operation fails honestly
    And no force checkout or reset --hard is used

  @S-GIT-WRITE-P2-5
  Scenario: Approve staging one selected hunk
    Given a dirty tracked file with more than one hunk
    When the user approves git_write_stage_hunk for the selected hunk only
    Then only that hunk is staged
    And a denied approval leaves the index unchanged

  @S-GIT-WRITE-P2-6
  Scenario: Approve unstaging one selected hunk
    Given a staged hunk and remaining unstaged hunks on the same file
    When the user approves git_write_unstage_hunk for the selected hunk
    Then only that hunk is unstaged
    And in-progress conflict operations fail honestly without --force
