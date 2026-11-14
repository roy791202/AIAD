Feature: Gated Git write FILE-UNSTAGE
  FILE-UNSTAGE unstages one repo-relative path (`git reset -- <path>`)
  through GitWritePort. Never unstage-all, never --hard.

  @s_git_write_p2_file_unstage_grant_one_path
  Scenario: Grant unstages only the requested path
    Given a git worktree with more than one staged path
    And GitWriteApproval is granted
    When unstage_path is called for one path
    Then that path leaves the index
    And the worktree contents of that file remain
    And HEAD is unchanged

  @s_git_write_p2_file_unstage_deny_no_mutation
  Scenario: Deny does not mutate
    Given a git worktree with a staged path
    And GitWriteApproval is denied
    When unstage_path is called
    Then the result is PermissionDenied
    And the index is unchanged

  @s_git_write_p2_file_unstage_conflict_operation_in_progress
  Scenario: In-progress conflict refuses FILE-UNSTAGE
    Given an in-progress merge with unmerged paths
    And GitWriteApproval is granted
    When unstage_path is called
    Then the error contains OPERATION_IN_PROGRESS
    And conflict state is unchanged

  @s_git_write_p2_file_unstage_path_traversal
  Scenario: Path traversal and option-like names fail
    Given a git worktree
    When unstage_path is called with traversal, NUL, option-like, empty, or outside-repo paths
    Then the call fails honestly
    And no index mutation occurs
    And a missing path fails honestly

  @s_git_write_p2_file_unstage_other_files_remain_staged
  Scenario: Other staged files remain staged
    Given two staged paths
    When unstage_path is called for one of them
    Then the other path remains staged
    And untracked files stay untracked
    And a clean index for a tracked path is a success no-op
