@M02_S1 @approved_DX1_DX7
Feature: Pure generation planning
  Background:
    Given an author has a local project definition and a verified template selection
  Rule: Planning preserves the definition and generates no files

    @M02-T01
    Scenario: Complete approved definition
      Given the required project decisions and approvals are complete
      When the author prepares a generation plan
      Then the plan contains program and UI design artifact intents

    @M02-T02
    Scenario: Incomplete definition
      Given required decisions are missing
      When the author prepares a generation plan
      Then the missing decisions are listed in a stable unique order without generation

    @M02-T03
    Scenario: Approval required
      Given approval names exist but approval has not been verified
      When the author prepares a generation plan
      Then the plan cannot authorize generation

    @M02-T04
    Scenario: Exact selection binding
      Given the selected template identity or version differs from the prepared selection
      When the author prepares a generation plan
      Then the mismatch is reported without a plan

    @M02-T05
    Scenario: Supported targets only
      Given the selected delivery target is unsupported
      When the author prepares a generation plan
      Then unsupported target is reported without silently changing the selection

    @M02-T06
    Scenario: Safe unique artifact paths
      Given an artifact path escapes the allowed grammar or conflicts with another
      When the author prepares a generation plan
      Then the invalid or conflicting path is rejected

    @M02-T07
    Scenario: Stale plan
      Given a binding value has changed since a plan was prepared
      When the author checks that plan
      Then the changed binding field is reported

    @M02-T08
    Scenario: Bounded artifacts
      Given an artifact list or path is at an approved boundary
      When the author prepares a generation plan
      Then the exact limits and both required products are enforced

    @M02-T09
    Scenario: Stable identity
      Given project identity or unique target identifiers are invalid
      When the author prepares a generation plan
      Then the invalid identity is rejected without guessing by name

    @M02-T10
    Scenario: Deterministic plan
      Given the same immutable definition and verified selection are available
      When the author prepares the plan repeatedly
      Then the same ordered plan is returned without modifying the inputs
