Feature: Candidate Save retention receipt mapping
  Background:
    Given a trusted immutable document fixture catalog
    And no native issuer or persistence is claimed
  Rule: Only the complete frozen Save tuple permits a candidate transfer

  @RM-001
  Scenario: matching full frozen request
    Given the bounded input fixture "RM-001"
    When its transfer evidence is evaluated
    Then the observable decision is "Transferred"
    And no release retry or acknowledgement occurs

  @RM-002
  Scenario: same key same body replay
    Given the bounded input fixture "RM-002"
    When its transfer evidence is evaluated
    Then the observable decision is "SameReceipt"
    And no release retry or acknowledgement occurs

  @RM-003
  Scenario: same key changed full body conflict
    Given the bounded input fixture "RM-003"
    When its transfer evidence is evaluated
    Then the observable decision is "ReplayConflict"
    And no release retry or acknowledgement occurs

  @RM-004
  Scenario: exact original Import bypass refused
    Given the bounded input fixture "RM-004"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-005
  Scenario: exact original UNTRUSTED label bypass refused
    Given the bounded input fixture "RM-005"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-006
  Scenario: missing request
    Given the bounded input fixture "RM-006"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-007
  Scenario: wrong type request
    Given the bounded input fixture "RM-007"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-008
  Scenario: missing transition_key
    Given the bounded input fixture "RM-008"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-009
  Scenario: wrong type transition_key
    Given the bounded input fixture "RM-009"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-010
  Scenario: missing held_ref
    Given the bounded input fixture "RM-010"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-011
  Scenario: wrong type held_ref
    Given the bounded input fixture "RM-011"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-012
  Scenario: missing formal_ref
    Given the bounded input fixture "RM-012"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-013
  Scenario: wrong type formal_ref
    Given the bounded input fixture "RM-013"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-014
  Scenario: missing catalog_phase
    Given the bounded input fixture "RM-014"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-015
  Scenario: wrong type catalog_phase
    Given the bounded input fixture "RM-015"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-016
  Scenario: missing transport
    Given the bounded input fixture "RM-016"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-017
  Scenario: wrong type transport
    Given the bounded input fixture "RM-017"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-018
  Scenario: missing permission
    Given the bounded input fixture "RM-018"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-019
  Scenario: wrong type permission
    Given the bounded input fixture "RM-019"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-020
  Scenario: unknown root field
    Given the bounded input fixture "RM-020"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-021
  Scenario: unknown request field
    Given the bounded input fixture "RM-021"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-022
  Scenario: numeric generation
    Given the bounded input fixture "RM-022"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-023
  Scenario: u64 overflow
    Given the bounded input fixture "RM-023"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-024
  Scenario: u64 maximum structurally valid but tuple mismatch
    Given the bounded input fixture "RM-024"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-025
  Scenario: u64 zero structurally valid tuple mismatch
    Given the bounded input fixture "RM-025"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-026
  Scenario: leading zero
    Given the bounded input fixture "RM-026"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-027
  Scenario: context project_uuid mismatch
    Given the bounded input fixture "RM-027"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-028
  Scenario: context document_uuid mismatch
    Given the bounded input fixture "RM-028"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-029
  Scenario: context workflow_id mismatch
    Given the bounded input fixture "RM-029"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-030
  Scenario: context owner_generation mismatch
    Given the bounded input fixture "RM-030"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-031
  Scenario: context captured_revision mismatch
    Given the bounded input fixture "RM-031"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-032
  Scenario: context session_id mismatch
    Given the bounded input fixture "RM-032"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-033
  Scenario: full request pin_id mismatch
    Given the bounded input fixture "RM-033"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-034
  Scenario: full request root_manifest mismatch
    Given the bounded input fixture "RM-034"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-035
  Scenario: full request external_proof mismatch
    Given the bounded input fixture "RM-035"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-036
  Scenario: full request store_identity mismatch
    Given the bounded input fixture "RM-036"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-037
  Scenario: root order matters
    Given the bounded input fixture "RM-037"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-038
  Scenario: empty roots remain structural but tuple refused
    Given the bounded input fixture "RM-038"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-039
  Scenario: wrong formal issuer
    Given the bounded input fixture "RM-039"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-040
  Scenario: unknown held receipt
    Given the bounded input fixture "RM-040"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-041
  Scenario: unknown formal receipt
    Given the bounded input fixture "RM-041"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-042
  Scenario: transition tuple mismatch
    Given the bounded input fixture "RM-042"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-043
  Scenario: denied before lookup
    Given the bounded input fixture "RM-043"
    When its transfer evidence is evaluated
    Then the observable decision is "PermissionDenied"
    And no release retry or acknowledgement occurs

  @RM-044
  Scenario: invalid before permission
    Given the bounded input fixture "RM-044"
    When its transfer evidence is evaluated
    Then the observable decision is "InvalidInput"
    And no release retry or acknowledgement occurs

  @RM-045
  Scenario: known pre CAS failure
    Given the bounded input fixture "RM-045"
    When its transfer evidence is evaluated
    Then the observable decision is "Held"
    And no release retry or acknowledgement occurs

  @RM-046
  Scenario: unknown CAS no old state claim
    Given the bounded input fixture "RM-046"
    When its transfer evidence is evaluated
    Then the observable decision is "Indeterminate"
    And no release retry or acknowledgement occurs

  @RM-047
  Scenario: post CAS proof loss no old state claim
    Given the bounded input fixture "RM-047"
    When its transfer evidence is evaluated
    Then the observable decision is "Indeterminate"
    And no release retry or acknowledgement occurs

  @RM-048
  Scenario: prior unknown no retry
    Given the bounded input fixture "RM-048"
    When its transfer evidence is evaluated
    Then the observable decision is "Indeterminate"
    And no release retry or acknowledgement occurs

  @RM-049
  Scenario: restart missing no retry
    Given the bounded input fixture "RM-049"
    When its transfer evidence is evaluated
    Then the observable decision is "UnverifiedOutcome"
    And no release retry or acknowledgement occurs

  @RM-050
  Scenario: Import purpose
    Given the bounded input fixture "RM-050"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-051
  Scenario: released pin
    Given the bounded input fixture "RM-051"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-052
  Scenario: wrong issuer
    Given the bounded input fixture "RM-052"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-053
  Scenario: receipt binding issuer
    Given the bounded input fixture "RM-053"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-054
  Scenario: receipt binding context
    Given the bounded input fixture "RM-054"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-055
  Scenario: receipt binding pin_id
    Given the bounded input fixture "RM-055"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-056
  Scenario: receipt binding asset_pairs
    Given the bounded input fixture "RM-056"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-057
  Scenario: receipt binding root_manifest_ids
    Given the bounded input fixture "RM-057"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-058
  Scenario: receipt binding source_receipt_ids
    Given the bounded input fixture "RM-058"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-059
  Scenario: receipt binding request_digest
    Given the bounded input fixture "RM-059"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs

  @RM-060
  Scenario: formal commit raw digest mismatch
    Given the bounded input fixture "RM-060"
    When its transfer evidence is evaluated
    Then the observable decision is "ProofMismatch"
    And no release retry or acknowledgement occurs
