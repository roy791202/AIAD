# FILE-UNSTAGE only. Product PR merge of this .feature needs GitHub label
# spec-change plus CODEOWNERS; implementers cannot add labels.
Feature: Gated Git write FILE-UNSTAGE
  FILE-UNSTAGE unstages one repo-relative path (`git reset -- <path>`)
  through GitWritePort. Never unstage-all, never --hard.

  @S-GIT-WP2-FU-1
  Scenario: Grant unstages only the requested path
    Given a git worktree with more than one staged path
    And GitWriteApproval is granted
    When unstage_path is called for one path
    Then that path leaves the index
    And the worktree contents of that file remain
    And HEAD is unchanged

  @S-GIT-WP2-FU-2
  Scenario: Deny does not mutate
    Given a git worktree with a staged path
    And GitWriteApproval is denied
    When unstage_path is called
    Then the result is PermissionDenied
    And the index is unchanged

  @S-GIT-WP2-FU-3
  Scenario: In-progress conflict refuses FILE-UNSTAGE
    Given an in-progress merge with unmerged paths
    And GitWriteApproval is granted
    When unstage_path is called
    Then the error contains OPERATION_IN_PROGRESS
    And conflict state is unchanged

  @S-GIT-WP2-FU-4
  Scenario: Path traversal and option-like names fail
    Given a git worktree
    When unstage_path is called with traversal, NUL, option-like, empty, or outside-repo paths
    Then the call fails honestly
    And no index mutation occurs
    And a missing path fails honestly

  @S-GIT-WP2-FU-5
  Scenario: Other staged files remain staged
    Given two staged paths
    When unstage_path is called for one of them
    Then the other path remains staged
    And untracked files stay untracked
    And a clean index for a tracked path is a success no-op
