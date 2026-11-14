Feature: M03 detached Viewer mock intent
  Background:
    Given a trusted native Viewer preview bound to an immutable owner snapshot
  Rule: Mock interaction never changes document content or persistence

    @VA-001
    Scenario: Activate increments detached activation once
      Given the explicit trusted premises and starting state for VA-001
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-001
      And content history and saved state remain unchanged

    @VA-002
    Scenario: SetToggle typed mock only
      Given the explicit trusted premises and starting state for VA-002
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-002
      And content history and saved state remain unchanged

    @VA-003
    Scenario: SetText typed mock only
      Given the explicit trusted premises and starting state for VA-003
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-003
      And content history and saved state remain unchanged

    @VA-004
    Scenario: SetText typed mock only
      Given the explicit trusted premises and starting state for VA-004
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-004
      And content history and saved state remain unchanged

    @VA-005
    Scenario: SetNumber typed mock only
      Given the explicit trusted premises and starting state for VA-005
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-005
      And content history and saved state remain unchanged

    @VA-006
    Scenario: SelectItem typed mock only
      Given the explicit trusted premises and starting state for VA-006
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-006
      And content history and saved state remain unchanged

    @VA-007
    Scenario: trusted_local denial
      Given the explicit trusted premises and starting state for VA-007
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-007
      And content history and saved state remain unchanged

    @VA-008
    Scenario: consumer_matches denial
      Given the explicit trusted premises and starting state for VA-008
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-008
      And content history and saved state remain unchanged

    @VA-009
    Scenario: owner_present denial
      Given the explicit trusted premises and starting state for VA-009
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-009
      And content history and saved state remain unchanged

    @VA-010
    Scenario: document_matches denial
      Given the explicit trusted premises and starting state for VA-010
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-010
      And content history and saved state remain unchanged

    @VA-011
    Scenario: provider_ready denial
      Given the explicit trusted premises and starting state for VA-011
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-011
      And content history and saved state remain unchanged

    @VA-012
    Scenario: Generation retired
      Given the explicit trusted premises and starting state for VA-012
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-012
      And content history and saved state remain unchanged

    @VA-013
    Scenario: Actual owner revision differs
      Given the explicit trusted premises and starting state for VA-013
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-013
      And content history and saved state remain unchanged

    @VA-014
    Scenario: Request revision differs
      Given the explicit trusted premises and starting state for VA-014
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-014
      And content history and saved state remain unchanged

    @VA-015
    Scenario: Missing preview
      Given the explicit trusted premises and starting state for VA-015
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-015
      And content history and saved state remain unchanged

    @VA-016
    Scenario: Closed preview
      Given the explicit trusted premises and starting state for VA-016
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-016
      And content history and saved state remain unchanged

    @VA-017
    Scenario: Wrong sequence 0
      Given the explicit trusted premises and starting state for VA-017
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-017
      And content history and saved state remain unchanged

    @VA-018
    Scenario: Wrong sequence 2
      Given the explicit trusted premises and starting state for VA-018
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-018
      And content history and saved state remain unchanged

    @VA-019
    Scenario: Accepted old sequence replay has no second effect
      Given the explicit trusted premises and starting state for VA-019
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-019
      And content history and saved state remain unchanged

    @VA-020
    Scenario: Maximum sequence closes without mock partial effect
      Given the explicit trusted premises and starting state for VA-020
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-020
      And content history and saved state remain unchanged

    @VA-021
    Scenario: Maximum minus one advances exactly
      Given the explicit trusted premises and starting state for VA-021
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-021
      And content history and saved state remain unchanged

    @VA-022
    Scenario: expected_revision rejects True
      Given the explicit trusted premises and starting state for VA-022
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-022
      And content history and saved state remain unchanged

    @VA-023
    Scenario: expected_revision rejects 1
      Given the explicit trusted premises and starting state for VA-023
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-023
      And content history and saved state remain unchanged

    @VA-024
    Scenario: expected_revision rejects None
      Given the explicit trusted premises and starting state for VA-024
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-024
      And content history and saved state remain unchanged

    @VA-025
    Scenario: expected_revision rejects ''
      Given the explicit trusted premises and starting state for VA-025
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-025
      And content history and saved state remain unchanged

    @VA-026
    Scenario: expected_revision rejects '01'
      Given the explicit trusted premises and starting state for VA-026
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-026
      And content history and saved state remain unchanged

    @VA-027
    Scenario: expected_revision rejects '-1'
      Given the explicit trusted premises and starting state for VA-027
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-027
      And content history and saved state remain unchanged

    @VA-028
    Scenario: expected_revision rejects '1.0'
      Given the explicit trusted premises and starting state for VA-028
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-028
      And content history and saved state remain unchanged

    @VA-029
    Scenario: expected_revision rejects '1e3'
      Given the explicit trusted premises and starting state for VA-029
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-029
      And content history and saved state remain unchanged

    @VA-030
    Scenario: expected_revision rejects '18446744073709551616'
      Given the explicit trusted premises and starting state for VA-030
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-030
      And content history and saved state remain unchanged

    @VA-031
    Scenario: expected_revision rejects '1\n'
      Given the explicit trusted premises and starting state for VA-031
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-031
      And content history and saved state remain unchanged

    @VA-032
    Scenario: sequence rejects True
      Given the explicit trusted premises and starting state for VA-032
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-032
      And content history and saved state remain unchanged

    @VA-033
    Scenario: sequence rejects 1
      Given the explicit trusted premises and starting state for VA-033
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-033
      And content history and saved state remain unchanged

    @VA-034
    Scenario: sequence rejects None
      Given the explicit trusted premises and starting state for VA-034
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-034
      And content history and saved state remain unchanged

    @VA-035
    Scenario: sequence rejects ''
      Given the explicit trusted premises and starting state for VA-035
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-035
      And content history and saved state remain unchanged

    @VA-036
    Scenario: sequence rejects '01'
      Given the explicit trusted premises and starting state for VA-036
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-036
      And content history and saved state remain unchanged

    @VA-037
    Scenario: sequence rejects '-1'
      Given the explicit trusted premises and starting state for VA-037
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-037
      And content history and saved state remain unchanged

    @VA-038
    Scenario: sequence rejects '1.0'
      Given the explicit trusted premises and starting state for VA-038
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-038
      And content history and saved state remain unchanged

    @VA-039
    Scenario: sequence rejects '1e3'
      Given the explicit trusted premises and starting state for VA-039
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-039
      And content history and saved state remain unchanged

    @VA-040
    Scenario: sequence rejects '18446744073709551616'
      Given the explicit trusted premises and starting state for VA-040
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-040
      And content history and saved state remain unchanged

    @VA-041
    Scenario: sequence rejects '1\n'
      Given the explicit trusted premises and starting state for VA-041
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-041
      And content history and saved state remain unchanged

    @VA-042
    Scenario: Closed typed payload Activate
      Given the explicit trusted premises and starting state for VA-042
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-042
      And content history and saved state remain unchanged

    @VA-043
    Scenario: Closed typed payload SetToggle
      Given the explicit trusted premises and starting state for VA-043
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-043
      And content history and saved state remain unchanged

    @VA-044
    Scenario: Closed typed payload SetText
      Given the explicit trusted premises and starting state for VA-044
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-044
      And content history and saved state remain unchanged

    @VA-045
    Scenario: Closed typed payload SetNumber
      Given the explicit trusted premises and starting state for VA-045
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-045
      And content history and saved state remain unchanged

    @VA-046
    Scenario: Closed typed payload SelectItem
      Given the explicit trusted premises and starting state for VA-046
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-046
      And content history and saved state remain unchanged

    @VA-047
    Scenario: Closed typed payload invoke
      Given the explicit trusted premises and starting state for VA-047
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-047
      And content history and saved state remain unchanged

    @VA-048
    Scenario: No client authority injection
      Given the explicit trusted premises and starting state for VA-048
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-048
      And content history and saved state remain unchanged

    @VA-049
    Scenario: Missing action
      Given the explicit trusted premises and starting state for VA-049
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-049
      And content history and saved state remain unchanged

    @VA-050
    Scenario: Unknown stable node
      Given the explicit trusted premises and starting state for VA-050
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-050
      And content history and saved state remain unchanged

    @VA-051
    Scenario: Mismatched node action
      Given the explicit trusted premises and starting state for VA-051
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-051
      And content history and saved state remain unchanged

    @VA-052
    Scenario: Capability rejects scope
      Given the explicit trusted premises and starting state for VA-052
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-052
      And content history and saved state remain unchanged

    @VA-053
    Scenario: Capability rejects allowed_actions
      Given the explicit trusted premises and starting state for VA-053
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-053
      And content history and saved state remain unchanged

    @VA-054
    Scenario: Inert unresolved asset_missing
      Given the explicit trusted premises and starting state for VA-054
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-054
      And content history and saved state remain unchanged

    @VA-055
    Scenario: Inert unresolved target_missing
      Given the explicit trusted premises and starting state for VA-055
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-055
      And content history and saved state remain unchanged

    @VA-056
    Scenario: Item labels cannot substitute stable ID
      Given the explicit trusted premises and starting state for VA-056
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-056
      And content history and saved state remain unchanged

    @VA-057
    Scenario: Unsupported items projection
      Given the explicit trusted premises and starting state for VA-057
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-057
      And content history and saved state remain unchanged

    @VA-058
    Scenario: Text bytes 4096
      Given the explicit trusted premises and starting state for VA-058
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-058
      And content history and saved state remain unchanged

    @VA-059
    Scenario: Text bytes 4097
      Given the explicit trusted premises and starting state for VA-059
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-059
      And content history and saved state remain unchanged

    @VA-060
    Scenario: Multibyte text resource
      Given the explicit trusted premises and starting state for VA-060
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-060
      And content history and saved state remain unchanged

    @VA-061
    Scenario: Node byte resource
      Given the explicit trusted premises and starting state for VA-061
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-061
      And content history and saved state remain unchanged

    @VA-062
    Scenario: Number bytes before numeric guard
      Given the explicit trusted premises and starting state for VA-062
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-062
      And content history and saved state remain unchanged

    @VA-063
    Scenario: Number grammar rejects NaN
      Given the explicit trusted premises and starting state for VA-063
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-063
      And content history and saved state remain unchanged

    @VA-064
    Scenario: Actual C1 rejection
      Given the explicit trusted premises and starting state for VA-064
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-064
      And content history and saved state remain unchanged

    @VA-065
    Scenario: Actual C1 unavailable
      Given the explicit trusted premises and starting state for VA-065
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-065
      And content history and saved state remain unchanged

    @VA-066
    Scenario: Delivery consumer
      Given the explicit trusted premises and starting state for VA-066
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-066
      And content history and saved state remain unchanged

    @VA-067
    Scenario: Delivery document
      Given the explicit trusted premises and starting state for VA-067
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-067
      And content history and saved state remain unchanged

    @VA-068
    Scenario: Delivery generation
      Given the explicit trusted premises and starting state for VA-068
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-068
      And content history and saved state remain unchanged

    @VA-069
    Scenario: Delivery closed
      Given the explicit trusted premises and starting state for VA-069
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-069
      And content history and saved state remain unchanged

    @VA-070
    Scenario: Bounded actual delivery revision '0'
      Given the explicit trusted premises and starting state for VA-070
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-070
      And content history and saved state remain unchanged

    @VA-071
    Scenario: Bounded actual delivery revision '9'
      Given the explicit trusted premises and starting state for VA-071
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-071
      And content history and saved state remain unchanged

    @VA-072
    Scenario: Bounded actual delivery revision '18446744073709551615'
      Given the explicit trusted premises and starting state for VA-072
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-072
      And content history and saved state remain unchanged

    @VA-073
    Scenario: Bounded actual delivery revision '7'
      Given the explicit trusted premises and starting state for VA-073
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-073
      And content history and saved state remain unchanged

    @VA-074
    Scenario: Bounded actual delivery revision None
      Given the explicit trusted premises and starting state for VA-074
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-074
      And content history and saved state remain unchanged

    @VA-075
    Scenario: Bounded actual delivery revision True
      Given the explicit trusted premises and starting state for VA-075
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-075
      And content history and saved state remain unchanged

    @VA-076
    Scenario: Bounded actual delivery revision '18446744073709551616'
      Given the explicit trusted premises and starting state for VA-076
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-076
      And content history and saved state remain unchanged

    @VA-077
    Scenario: Bounded actual delivery revision '9\n'
      Given the explicit trusted premises and starting state for VA-077
      When the Viewer submits the declared mock interaction
      Then the observable result matches VA-077
      And content history and saved state remain unchanged
