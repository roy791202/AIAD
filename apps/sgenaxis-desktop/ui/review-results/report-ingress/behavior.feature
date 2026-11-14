Feature: Bound execution report ingestion
  Reports from CLI, HTTP and MCP share one application boundary.

  Background:
    Given a Rust-owned task and run with a declared specification and envelope
    And report ingestion is proposed and has no acceptance authority

  Rule: Only current authorized reports may be committed atomically

    @RI-01
    Scenario: Record progress through any supported transport
      Given an authorized current report for sequence 1
      When the report is submitted
      Then one progress record is committed and acceptance remains unchanged

    @RI-02
    Scenario: Retry an identical report
      Given sequence 1 has already been committed
      When the same report identity and payload are submitted again
      Then the original receipt is returned without another mutation

    @RI-03
    Scenario: Reject a conflicting duplicate
      Given sequence 1 has already been committed
      When the same report identity with a different payload is submitted
      Then a conflict is returned and all authoritative state remains unchanged

    @RI-04
    Scenario: Reject an out of order report
      Given the committed sequence is 1
      When sequence 3 is submitted
      Then a sequence gap is returned with expected sequence 2 and no mutation

    @RI-05
    Scenario: Reject an obsolete execution attempt
      Given attempt 2 owns the active lease
      When attempt 1 submits a completion report
      Then the report is rejected as stale and no task state changes

    @RI-06
    Scenario: Reject an identity mismatch
      Given the active lease binds project P and worktree W
      When a report bound to another project or worktree is submitted
      Then the report is rejected without mutation

    @RI-07
    Scenario: Completion is not acceptance
      Given a current run has valid reporting authority
      When the agent reports execution finished with evidence references
      Then execution is recorded as finished and acceptance and task green remain unchanged

    @RI-08
    Scenario: Preserve state on commit failure
      Given the report store is configured to fail before commit
      When a valid report is submitted
      Then an unavailable result is returned and neither receipt nor report nor task projection is committed

    @RI-09
    Scenario: Reconnect with expired authority
      Given a reporting lease has expired
      When the agent reconnects and submits a new report
      Then the report is rejected and reconnection does not renew authority

    @RI-10
    Scenario: Reject reports after cancellation
      Given cancellation has been committed for the run
      When a new completion report is submitted
      Then the report is rejected as cancelled and cancellation remains authoritative

    @RI-11
    Scenario: Reject excessive or empty input
      Given a current reporting identity exists
      When an empty report or payload above the declared limit is submitted
      Then validation fails without mutation

    @RI-12
    Scenario: Reject unauthorized reporting
      Given the reporter lacks authority for the bound run
      When a completion report is submitted
      Then authorization fails without changing the run or task

    @RI-13
    Scenario: Retry after a lost acknowledgement
      Given sequence 1 was committed but its receipt was not delivered
      When the identical report is submitted after reconnecting with valid authority
      Then the original receipt is returned and no duplicate evidence is attached

    @RI-14
    Scenario: Reject changed specification binding
      Given the active run is bound to specification revision S1 and envelope E1
      When a report claiming revision S2 or envelope E2 is submitted
      Then the report is rejected without accepting changed implementation authority
