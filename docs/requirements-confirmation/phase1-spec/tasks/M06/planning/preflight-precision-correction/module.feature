Feature: M06 pure import preflight
  Background:
    Given validation report and target context are immutable input values

  Scenario: M06-PC-001 valid complete
    Given the complete fixture M06-PC-001 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-002 UnsupportedFormat cannot be accepted away
    Given the complete fixture M06-PC-002 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-003 UnsupportedVersion cannot be accepted away
    Given the complete fixture M06-PC-003 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-004 Integrity cannot be accepted away
    Given the complete fixture M06-PC-004 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-005 MissingInternalPayload cannot be accepted away
    Given the complete fixture M06-PC-005 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-006 UnsafePath cannot be accepted away
    Given the complete fixture M06-PC-006 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-007 AmbiguousEntry cannot be accepted away
    Given the complete fixture M06-PC-007 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-008 missing without confirmation
    Given the complete fixture M06-PC-008 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-009 explicit missing acceptance
    Given the complete fixture M06-PC-009 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-010 accepted choice does not invent incomplete
    Given the complete fixture M06-PC-010 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-011 stale source
    Given the complete fixture M06-PC-011 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-012 target ID mismatch
    Given the complete fixture M06-PC-012 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-013 target revision mismatch
    Given the complete fixture M06-PC-013 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-014 cross-document change
    Given the complete fixture M06-PC-014 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-015 blocker before stale source
    Given the complete fixture M06-PC-015 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-016 malformed blocker before stale source
    Given the complete fixture M06-PC-016 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-017 invalid digest before blocker
    Given the complete fixture M06-PC-017 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-018 invalid missing ID before blocker
    Given the complete fixture M06-PC-018 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-019 source before stale target and cross
    Given the complete fixture M06-PC-019 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-020 target before cross
    Given the complete fixture M06-PC-020 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-021 cross before missing acceptance
    Given the complete fixture M06-PC-021 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-022 exact blocker order with duplicates retained
    Given the complete fixture M06-PC-022 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-023 missing UTF8 byte order
    Given the complete fixture M06-PC-023 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-024 /report/target_document_id bytes 0
    Given the complete fixture M06-PC-024 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-025 /report/target_document_id bytes 1
    Given the complete fixture M06-PC-025 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-026 /report/target_document_id bytes 256
    Given the complete fixture M06-PC-026 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-027 /report/target_document_id bytes 257
    Given the complete fixture M06-PC-027 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-028 /report/target_document_id NUL
    Given the complete fixture M06-PC-028 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-029 /context/target_document_id bytes 0
    Given the complete fixture M06-PC-029 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-030 /context/target_document_id bytes 1
    Given the complete fixture M06-PC-030 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-031 /context/target_document_id bytes 256
    Given the complete fixture M06-PC-031 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-032 /context/target_document_id bytes 257
    Given the complete fixture M06-PC-032 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-033 /context/target_document_id NUL
    Given the complete fixture M06-PC-033 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-034 subject bytes 0
    Given the complete fixture M06-PC-034 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-035 subject bytes 1
    Given the complete fixture M06-PC-035 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-036 subject bytes 1024
    Given the complete fixture M06-PC-036 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-037 subject bytes 1025
    Given the complete fixture M06-PC-037 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-038 subject NUL
    Given the complete fixture M06-PC-038 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-039 reason bytes 0
    Given the complete fixture M06-PC-039 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-040 reason bytes 1
    Given the complete fixture M06-PC-040 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-041 reason bytes 4096
    Given the complete fixture M06-PC-041 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-042 reason bytes 4097
    Given the complete fixture M06-PC-042 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-043 reason NUL
    Given the complete fixture M06-PC-043 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-044 missing ID bytes 0
    Given the complete fixture M06-PC-044 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-045 missing ID bytes 1
    Given the complete fixture M06-PC-045 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-046 missing ID bytes 256
    Given the complete fixture M06-PC-046 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-047 missing ID bytes 257
    Given the complete fixture M06-PC-047 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-048 missing ID NUL
    Given the complete fixture M06-PC-048 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-049 multibyte ID 256
    Given the complete fixture M06-PC-049 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-050 multibyte ID 257
    Given the complete fixture M06-PC-050 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-051 blocker count 256
    Given the complete fixture M06-PC-051 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-052 blocker count 257
    Given the complete fixture M06-PC-052 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-053 missing count 4096
    Given the complete fixture M06-PC-053 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-054 missing count 4097
    Given the complete fixture M06-PC-054 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-055 digest /report/source_digest length 0
    Given the complete fixture M06-PC-055 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-056 digest /report/source_digest length 71
    Given the complete fixture M06-PC-056 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-057 digest /report/source_digest length 70
    Given the complete fixture M06-PC-057 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-058 digest /report/source_digest length 72
    Given the complete fixture M06-PC-058 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-059 digest /context/expected_source_digest length 0
    Given the complete fixture M06-PC-059 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-060 digest /context/expected_source_digest length 71
    Given the complete fixture M06-PC-060 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-061 digest /context/expected_source_digest length 70
    Given the complete fixture M06-PC-061 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-062 digest /context/expected_source_digest length 72
    Given the complete fixture M06-PC-062 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-063 u64 max valid equal
    Given the complete fixture M06-PC-063 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged

  Scenario: M06-PC-064 u64 max mismatch
    Given the complete fixture M06-PC-064 from cases.json
    When import preflight is evaluated
    Then result equals its exact recorded oracle
    And source and target values remain unchanged
