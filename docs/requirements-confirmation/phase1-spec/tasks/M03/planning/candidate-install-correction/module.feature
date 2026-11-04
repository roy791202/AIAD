Feature: Install a prepared design candidate safely
  Background:
    Given one authoritative document owner and a trusted current writer
    And a supported candidate prepared through the validated codec
  Rule: Candidate installation respects owner authority and retained outcomes

    @CI-01-applied
    Scenario: CI-01-applied
      Given the declared document and candidate preconditions for "CI-01-applied"
      When the writer requests installation once
      Then the observable outcome is "Applied"
      And formal persistence and save acknowledgement are not performed

    @CI-02-UnauthorizedCaller
    Scenario: CI-02-UnauthorizedCaller
      Given the declared document and candidate preconditions for "CI-02-UnauthorizedCaller"
      When the writer requests installation once
      Then the observable outcome is "UnauthorizedCaller"
      And formal persistence and save acknowledgement are not performed

    @CI-03-WriterRequired
    Scenario: CI-03-WriterRequired
      Given the declared document and candidate preconditions for "CI-03-WriterRequired"
      When the writer requests installation once
      Then the observable outcome is "WriterRequired"
      And formal persistence and save acknowledgement are not performed

    @CI-04-MissingBinding
    Scenario: CI-04-MissingBinding
      Given the declared document and candidate preconditions for "CI-04-MissingBinding"
      When the writer requests installation once
      Then the observable outcome is "MissingBinding"
      And formal persistence and save acknowledgement are not performed

    @CI-05-StaleOwner
    Scenario: CI-05-StaleOwner
      Given the declared document and candidate preconditions for "CI-05-StaleOwner"
      When the writer requests installation once
      Then the observable outcome is "StaleOwner"
      And formal persistence and save acknowledgement are not performed

    @CI-06-CandidateMissing
    Scenario: CI-06-CandidateMissing
      Given the declared document and candidate preconditions for "CI-06-CandidateMissing"
      When the writer requests installation once
      Then the observable outcome is "CandidateMissing"
      And formal persistence and save acknowledgement are not performed

    @CI-07-CandidateUsed
    Scenario: CI-07-CandidateUsed
      Given the declared document and candidate preconditions for "CI-07-CandidateUsed"
      When the writer requests installation once
      Then the observable outcome is "CandidateUsed"
      And formal persistence and save acknowledgement are not performed

    @CI-08-StaleOwner
    Scenario: CI-08-StaleOwner
      Given the declared document and candidate preconditions for "CI-08-StaleOwner"
      When the writer requests installation once
      Then the observable outcome is "StaleOwner"
      And formal persistence and save acknowledgement are not performed

    @CI-09-StaleRevision
    Scenario: CI-09-StaleRevision
      Given the declared document and candidate preconditions for "CI-09-StaleRevision"
      When the writer requests installation once
      Then the observable outcome is "StaleRevision"
      And formal persistence and save acknowledgement are not performed

    @CI-10-StaleRevision
    Scenario: CI-10-StaleRevision
      Given the declared document and candidate preconditions for "CI-10-StaleRevision"
      When the writer requests installation once
      Then the observable outcome is "StaleRevision"
      And formal persistence and save acknowledgement are not performed

    @CI-11-DependencyNotReady
    Scenario: CI-11-DependencyNotReady
      Given the declared document and candidate preconditions for "CI-11-DependencyNotReady"
      When the writer requests installation once
      Then the observable outcome is "DependencyNotReady"
      And formal persistence and save acknowledgement are not performed

    @CI-12-DependencyNotReady
    Scenario: CI-12-DependencyNotReady
      Given the declared document and candidate preconditions for "CI-12-DependencyNotReady"
      When the writer requests installation once
      Then the observable outcome is "DependencyNotReady"
      And formal persistence and save acknowledgement are not performed

    @CI-13-DependencyNotReady
    Scenario: CI-13-DependencyNotReady
      Given the declared document and candidate preconditions for "CI-13-DependencyNotReady"
      When the writer requests installation once
      Then the observable outcome is "DependencyNotReady"
      And formal persistence and save acknowledgement are not performed

    @CI-14-Indeterminate
    Scenario: CI-14-Indeterminate
      Given the declared document and candidate preconditions for "CI-14-Indeterminate"
      When the writer requests installation once
      Then the observable outcome is "Indeterminate"
      And formal persistence and save acknowledgement are not performed

    @CI-15-UnverifiedOutcome
    Scenario: CI-15-UnverifiedOutcome
      Given the declared document and candidate preconditions for "CI-15-UnverifiedOutcome"
      When the writer requests installation once
      Then the observable outcome is "UnverifiedOutcome"
      And formal persistence and save acknowledgement are not performed

    @CI-16-deferred-LiveRoots
    Scenario: CI-16-deferred-LiveRoots
      Given the declared document and candidate preconditions for "CI-16-deferred-LiveRoots"
      When the writer requests installation once
      Then the observable outcome is "AppliedRetentionDeferred"
      And formal persistence and save acknowledgement are not performed

    @CI-17-deferred-UndoRoots
    Scenario: CI-17-deferred-UndoRoots
      Given the declared document and candidate preconditions for "CI-17-deferred-UndoRoots"
      When the writer requests installation once
      Then the observable outcome is "AppliedRetentionDeferred"
      And formal persistence and save acknowledgement are not performed

    @CI-18-deferred-RedoRoots
    Scenario: CI-18-deferred-RedoRoots
      Given the declared document and candidate preconditions for "CI-18-deferred-RedoRoots"
      When the writer requests installation once
      Then the observable outcome is "AppliedRetentionDeferred"
      And formal persistence and save acknowledgement are not performed

    @CI-19-retained-newer-live
    Scenario: CI-19-retained-newer-live
      Given the declared document and candidate preconditions for "CI-19-retained-newer-live"
      When the writer requests installation once
      Then the observable outcome is "Applied"
      And formal persistence and save acknowledgement are not performed

    @CI-20-retained-newer-live
    Scenario: CI-20-retained-newer-live
      Given the declared document and candidate preconditions for "CI-20-retained-newer-live"
      When the writer requests installation once
      Then the observable outcome is "Applied"
      And formal persistence and save acknowledgement are not performed

    @CI-21-retained-newer-live
    Scenario: CI-21-retained-newer-live
      Given the declared document and candidate preconditions for "CI-21-retained-newer-live"
      When the writer requests installation once
      Then the observable outcome is "Applied"
      And formal persistence and save acknowledgement are not performed

    @CI-22-late-owner-before-replay
    Scenario: CI-22-late-owner-before-replay
      Given the declared document and candidate preconditions for "CI-22-late-owner-before-replay"
      When the writer requests installation once
      Then the observable outcome is "StaleOwner"
      And formal persistence and save acknowledgement are not performed

    @CI-23-replay-conflict
    Scenario: CI-23-replay-conflict
      Given the declared document and candidate preconditions for "CI-23-replay-conflict"
      When the writer requests installation once
      Then the observable outcome is "RequestConflict"
      And formal persistence and save acknowledgement are not performed

    @CI-24-uncertain-pin
    Scenario: CI-24-uncertain-pin
      Given the declared document and candidate preconditions for "CI-24-uncertain-pin"
      When the writer requests installation once
      Then the observable outcome is "Indeterminate"
      And formal persistence and save acknowledgement are not performed

    @CI-25-overflow
    Scenario: CI-25-overflow
      Given the declared document and candidate preconditions for "CI-25-overflow"
      When the writer requests installation once
      Then the observable outcome is "RevisionOverflow"
      And formal persistence and save acknowledgement are not performed

    @CI-26-NoChange
    Scenario: CI-26-NoChange
      Given the declared document and candidate preconditions for "CI-26-NoChange"
      When the writer requests installation once
      Then the observable outcome is "NoChange"
      And formal persistence and save acknowledgement are not performed

    @CI-replay-deferred-LiveRoots
    Scenario: CI-replay-deferred-LiveRoots
      Given the declared document and candidate preconditions for "CI-replay-deferred-LiveRoots"
      When the writer requests installation once
      Then the observable outcome is "AppliedRetentionDeferred"
      And formal persistence and save acknowledgement are not performed

    @CI-replay-deferred-UndoRoots
    Scenario: CI-replay-deferred-UndoRoots
      Given the declared document and candidate preconditions for "CI-replay-deferred-UndoRoots"
      When the writer requests installation once
      Then the observable outcome is "AppliedRetentionDeferred"
      And formal persistence and save acknowledgement are not performed

    @CI-replay-deferred-RedoRoots
    Scenario: CI-replay-deferred-RedoRoots
      Given the declared document and candidate preconditions for "CI-replay-deferred-RedoRoots"
      When the writer requests installation once
      Then the observable outcome is "AppliedRetentionDeferred"
      And formal persistence and save acknowledgement are not performed

    @CI-replay-NoChange
    Scenario: CI-replay-NoChange
      Given the declared document and candidate preconditions for "CI-replay-NoChange"
      When the writer requests installation once
      Then the observable outcome is "NoChange"
      And formal persistence and save acknowledgement are not performed
