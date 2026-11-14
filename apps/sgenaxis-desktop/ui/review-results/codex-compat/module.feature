# language: en
# PD-RUST-CODEX-COMPAT-01 — Module BDD draft (PROPOSED; not executable RED)
# Module: agent-compatibility
# Rule: Claude / other Agent PASS does not satisfy any Codex scenario.

@PD-RUST-CODEX-COMPAT-01 @provider-codex @planning-only
Feature: Codex lead-work, execution, and report compatibility
  Verify the same approved contracts on an explicit Codex version and actual host.
  Record permission, cancel, error, report, and evidence. Never inherit another Agent's PASS.

  Background:
    Given module contracts for agent execution and CLI entry are approved
    And a controlled input fixture is bound to the host run identity
    And the Codex target records exact version, path, argv, and host
    And live or fixture execution is owner-authorized for this case
    # Until Background holds: all scenarios remain NOT RUN (planning only).

  @CX-B01 @happy @permission @report @evidence
  Scenario: Controlled Codex run preserves host-bound report and evidence
    Given an approved Codex CLI target on the recorded host
    When the host starts a controlled Codex run with the bound fixture
    Then permission prompts follow the approved never-auto-approve contract
    And captured chunks bind to the host run/task/source fingerprint
    And report submission uses host identity, not child-claimed PASS
    And evidence artifacts record Codex version and host
    And product acceptance remains unchanged by provider exit 0

  @CX-B02 @cancel @lifecycle
  Scenario: Codex cancel acknowledges and drains to one terminal
    Given a controlled Codex run that is running or draining
    When cancellation is requested through the approved host path
    Then the host acknowledges cancel without consuming required tail chunks
    And polling continues until exactly one terminal event
    And the lease releases only at terminal
    And the board does not turn green

  @CX-B03 @error @invalid
  Scenario: Invalid Codex target or stale binding rejects before spawn
    Given a missing Codex path, unapproved live flag, or stale source binding
    When start is requested
    Then the run is rejected before ProcessPort start
    And no Codex process is started
    And no fabricated success evidence is written

  @CX-B04 @error @partial-failure
  Scenario: Nonzero or malformed Codex output cannot accept the task
    Given an authorized Codex run that exits nonzero or emits a malformed claim
    When the host reconciles the terminal
    Then the provider failure or malformed claim is recorded
    And task acceptance / product green does not occur
    And prior authoritative state remains unchanged

  @CX-B05 @inbound-mcp @parity
  Scenario: Inbound MCP Codex path shares report gates with CLI when in scope
    Given inbound MCP contracts are approved and Codex is the claiming agent
    When Codex queries, claims, and submits a report for the same task binding
    Then auth, ownership, and report identity gates match the CLI contract
    And outbound MCP provider semantics are not mutated
    # If inbound MCP is out of this card's owner scope: mark NOT RUN, do not skip silently.

  @CX-B06 @non-inheritance @regression
  Scenario: Another Agent PASS does not mark Codex compatible
    Given Claude Code or another Agent compatibility row is PASS
    And the Codex target row has no independent evidence
    When compatibility status is projected
    Then the Codex row remains NOT RUN or FAIL according to its own evidence
    And no aggregate "agents compatible" PASS is inferred

  @CX-B07 @boundary @state @transaction
  Scenario: Duplicate start and restart keep distinct run identities
    Given an active or draining Codex run
    When a second start is requested for the same work lease
    Then the duplicate is rejected per single-active-run rules
    When a new approved run starts after terminal
    Then the new runId is distinct and prior evidence cannot authorize it
