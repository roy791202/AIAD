Feature: Approval-gated GitWritePort.merge_ff_only
  Background:
    Given a local git repository and GitWritePort adapters

  @PD-GIT-MERGE-FF-01-1
  Scenario: Denied approval does not merge
    Given a local branch that is a fast-forward of HEAD
    When merge_ff_only is called with GitWriteApproval denied
    Then the call fails as permission denied
    And HEAD stays on the original commit

  @PD-GIT-MERGE-FF-01-2
  Scenario: Approved ff-only merge moves HEAD without a merge commit
    Given a local branch that is a fast-forward of HEAD
    When merge_ff_only is called with granted approval
    Then HEAD matches that branch
    And no merge commit, -X, pull, rebase, or push runs

  @PD-GIT-MERGE-FF-01-3
  Scenario: Diverged histories and option-like names fail honestly
    Given a diverged local branch
    When merge_ff_only is called for that branch, --no-ff, -X, or a missing name
    Then the call fails without mutating HEAD
