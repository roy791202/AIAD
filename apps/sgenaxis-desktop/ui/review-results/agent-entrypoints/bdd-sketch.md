# BDD sketch — agent-integration (PROPOSED · not executable RED)

**Card:** `PD-RUST-AGENT-ENTRYPOINTS-01`  
**Module BDD tag family:** `BDD-AE-*`  
**State:** Sketch only. Formal `.feature` / steps / fixtures / intended RED are **NOT STARTED** until architecture + AGENT-LOOP gates clear.

```gherkin
Feature: Agent entrypoint integration index
  Background:
    Given the first closed-loop task/run/report contracts are the shared authority
    And this module does not own a second SSOT

  @BDD-AE-01 @routing
  Scenario: Capability maps to an owner card
    Given a known capability id (cli-entry, inbound-mcp, claude-compat, codex-compat, embedded, agent-hosted-ui)
    When the integration index is queried
    Then exactly one primary owner card is named
    And no parallel acceptance path is advertised

  @BDD-AE-02 @status
  Scenario: Missing provider target is NOT RUN or NOT_SUPPORTED
    Given Claude Code or Codex installation inputs are absent
    When a compatibility status is requested
    Then the row status is NOT RUN or NOT_SUPPORTED
    And the status is not PASS

  @BDD-AE-03 @independence
  Scenario: Claude PASS does not imply Codex PASS
    Given Claude compatibility evidence is PASS for a named version
    And Codex target inputs remain unspecified
    When Codex compatibility status is read
    Then Codex remains NOT RUN or BLOCKED independently

  @BDD-AE-04 @blockers
  Scenario: Open architecture gates block implementation readiness
    Given PD-RUST-AGENT-LOOP-01 architecture/contract/BDD is not approved
    Or an open DEC blocks a delivery card
    When implementation readiness is evaluated for this module
    Then the result is NOT_READY_FOR_IMPLEMENTATION
    And Skeleton/RED are not claimed started

  @BDD-AE-05 @no-silent-pty
  Scenario: Interactive requirement cannot silently widen CLI ProcessPort
    Given a provider contract requires interactive stdin or PTY
    And only the noninteractive CLI path is authorized
    When launch readiness is evaluated
    Then the result is an explicit capability failure or ARCHITECTURE_GAP
    And ProcessPort is not silently extended

  @BDD-AE-06 @inbound-vs-outbound
  Scenario: Inbound MCP is distinct from outbound provider
    Given an inbound MCP claim/report adapter is described
    When ownership is inspected
    Then it is a driving adapter into the shared Application
    And it does not inherit outbound AgentProvider spawn semantics

  @BDD-AE-07 @acceptance
  Scenario: Provider success never greens product work
    Given any entrypoint reports provider process or session success
    When product acceptance is evaluated
    Then Host/EVID/human gates remain required
    And board green is not automatic
```

## Pending automation

- Formal feature file under approved test tree — **pending architecture**
- Step stubs / fixtures — **pending**
- Intended RED producer — **NOT RUN** (card backlog only)
- Adjacent regression mapping to CLI-ENTRY / INBOUND-MCP / COMPAT / EMBEDDED — **after** those cards produce evidence

## Acceptance sketch (planning packet only)

| AC | Statement |
|---|---|
| AC1 | Packet documents routing table, diagrams, invariants, BDD sketch, risks, blockers |
| AC2 | Explicit `NOT_READY_FOR_IMPLEMENTATION` + architecture `PROPOSED_NOT_APPROVED` |
| AC3 | No production crate edits; no architecture approval claim; zone stays yellow |
| AC4 | Capability rows list version/scope/compat/unsupported fields even when UNKNOWN |
| AC5 | Dependencies on AGENT-LOOP and EMBEDDED-AGENT-PLAN named as blockers until gated |
