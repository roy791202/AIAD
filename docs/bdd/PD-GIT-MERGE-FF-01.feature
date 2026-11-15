Feature: Approval-gated fast-forward merge of a local branch
  Default-deny GitWritePort.merge_ff_only. Occupying Run/lease refuses
  at HOST. Local branches only; never merge a remote-tracking name as a fetch.

  @PD-GIT-MERGE-FF-01-1
  Scenario: Denied approval does not merge
    Given a local topic branch that is a fast-forward of HEAD
    When merge_ff_only is called with GitWriteApproval denied
    Then the call fails with PermissionDenied
    And HEAD is unchanged
    And no merge commit is created
    And git is not invoked with pull, rebase, push, --no-ff, or -X

  @PD-GIT-MERGE-FF-01-2
  Scenario: Approved git merge --ff-only -- local-branch moves HEAD
    Given a local topic branch that is a fast-forward of HEAD
    And no occupying workspace Run/lease
    When merge_ff_only is called with GitWriteApproval granted
    Then the adapter runs git merge --ff-only -- <local-branch>
    And HEAD moves to the topic tip
    And there is no merge commit
    And the command does not use --no-ff, -X theirs/ours, --squash, pull, rebase, or push

  @PD-GIT-MERGE-FF-01-3
  Scenario: Diverged histories, flags, and missing names fail honestly
    Given a repository with local branches
    When merge_ff_only is called on diverged histories
    Then the call fails honestly and HEAD is unchanged
    When merge_ff_only is called with --no-ff or -X as the branch name
    Then the call fails as out of scope without merging
    When merge_ff_only is called with a missing local name
    Then the call fails honestly without inventing a branch
    When merge_ff_only is called with a remote-tracking name
    Then the call fails honestly and does not fetch
    When an occupying Run/lease is present
    Then HOST refuses merge_ff_only and GitWritePort is not called
