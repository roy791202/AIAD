# language: en
# PD-RUST-CLAUDE-COMPAT-01 — BDD draft (NOT APPROVED / not executable RED)
# Module: agent-compatibility
# Status: DRAFT_NOT_APPROVED · live verification NOT RUN
# Tags: @req-REQ-AGENT-CLAUDE-01 @card-PD-RUST-CLAUDE-COMPAT-01

Feature: Claude Code lead, execute, cancel, error, report, and EVID compatibility
  As the product owner
  I need Claude Code compatibility proven under an approved contract and controlled inputs
  So that lead/exec/cancel/error/report/EVID results cite an explicit version and selected mode
  Without assuming every Agent window shares the same UI

  Background:
    Given module contract approval status is recorded
    And dependency gates for AGENT-LOOP, CLI-ENTRY, and INBOUND-MCP are recorded
    And every evidence row will include claude_code_version, selected_mode_id, and runtime fields
    And unverified Agent UI capability must be classified NOT_RUN or HOST_NOT_VERIFIED

  @CC-B01 @lead @normal
  Scenario: Authorized inbound claim obtains a single lease
    Given an approved work item and ready inbound MCP adapter
    And selected mode is MODE-INBOUND-MCP with a recorded Claude Code version
    When Claude Code claims the work through the approved claim tool
    Then exactly one lease and Run are created
    And the response binds task, revision, and run identity
    And product acceptance remains unchanged

  @CC-B02 @lead @invalid
  Scenario: Unauthorized or stale claim mutates nothing
    Given a work item that is unapproved or bound to a stale revision
    When Claude Code attempts claim
    Then the claim is rejected with a readable error
    And WORK lease and EVID stores are unchanged

  @CC-B03 @exec @normal
  Scenario: Headless CLI exec records version and classifies exit
    Given selected mode MODE-CLI-HEADLESS and owner-approved argv/cwd
    And Claude Code version and path are recorded before start
    When the product starts the controlled Claude CLI run
    Then chunks and exit classification follow the approved HOST-EXEC contract
    And provider success alone does not set product green

  @CC-B04 @cancel @lifecycle
  Scenario: Cancel reaches one terminal and releases lease only then
    Given a running Claude-backed Run under an approved mode
    When cancel is requested
    Then the host acknowledges cancel and continues until exactly one terminal
    And the lease is released only at terminal
    And late chunks before terminal do not create a second terminal

  @CC-B05 @error @dependency_failure
  Scenario: Missing binary or auth-not-ready rejects without start
    Given Claude CLI path is missing or auth_readiness is NOT_READY
    When start or claim is attempted
    Then the attempt is rejected without starting a provider process
    And result_class is FAIL or BLOCKED with runtime fields filled

  @CC-B06 @error @partial_failure
  Scenario: Runtime failure after start yields Failed terminal
    Given a started Claude-backed Run
    When the provider crashes or returns a classified execution failure
    Then the Run ends Failed with prior valid evidence preserved
    And no FLOW acceptance is manufactured

  @CC-B07 @report @transaction
  Scenario: Report under correct identity is stored once
    Given a bound Run and lease for the recorded Claude mode/version
    When SubmitRunReport is submitted with valid identity and idempotency key
    Then evidence is stored according to the EVID contract
    And a duplicate identical replay yields the same receipt without duplicate mutation

  @CC-B08 @report @invalid
  Scenario: Wrong binding or conflicting report is rejected
    Given an approved Run
    When a report with wrong task/run/revision or conflicting body for the same key arrives
    Then the report is rejected
    And preexisting evidence and FLOW state remain unchanged

  @CC-B09 @EVID @regression
  Scenario: EVID and HTML trace are independent of board color
    Given a successful provider report receipt
    When evidence is projected to the card-local HTML/report trace
    Then identities and hashes are visible for independent verification
    And the board zone is not self-greened by this card

  @CC-B10 @boundary @state
  Scenario: Busy single active Run rejects duplicate Assign or claim
    Given one in-flight Claude-backed Run
    When a second Assign or claim is attempted for overlapping work
    Then the second attempt is rejected or queued per approved policy
    And the first Run identity remains authoritative

  @CC-B11 @lifecycle @regression
  Scenario: Restart uses a new run identity
    Given a previous Claude Run reached a terminal and evidence reconciled
    When a new approved Run starts with the same task
    Then the new run id is distinct
    And previous evidence cannot authorize the new Run

  @CC-B12 @MODE-EMBEDDED-UI @NOT_RUN
  Scenario: Embedded Agent UI capability is not assumed
    Given Claude Code MCP tools may work without an Agent-window UI
    When embedded or MCP Apps UI support has not been verified on this host
    Then MODE-EMBEDDED-UI rows are NOT_RUN or HOST_NOT_VERIFIED
    And tools-path scenarios remain independently assertable
