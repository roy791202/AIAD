Feature: M08 evidence consistency without claiming native execution
  Background:
    Given a synthetic evidence record and matching synthetic observation facts
    And the checker output is limited to schema-unit evidence

  Rule: M08-HR02
  Scenario: BDD-M08-H-N01 Windows10 record claims Windows11 native PASS
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_WIN11_REQUIRED
    And the issue points to /environment/is_Windows11
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR03
  Scenario: BDD-M08-H-N02 actual binary hash differs from manifest executable hash
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_ARTIFACT_DIGEST_MISMATCH
    And the issue points to /artifact/actual_sha256
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR03
  Scenario: BDD-M08-H-N03 HEAD present but source inventory absent
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_SOURCE_INVENTORY_REQUIRED
    And the issue points to /source/dirty_inventory_sha256
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR05
  Scenario: BDD-M08-H-N04 screenshot without matching run/process binding
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_CAPTURE_BINDING
    And the issue points to /evidence/captures/0
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR01
  Scenario: BDD-M08-H-N05 NOT RUN claims PASS; execution error takes priority over leftover PID fields
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_EXECUTION_REQUIRED
    And the issue points to /execution/state
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR03
  Scenario: BDD-M08-H-N06 claimed ELIGIBLE, matching declared hash but no source-build provenance; historical identification cannot suffice
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_BUILD_MANIFEST_REQUIRED
    And the issue points to /source/build_manifest_ref
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR06
  Scenario: BDD-M08-H-N07 caller boolean remains true but supplied canonical ownership proof does not cover lookalike path
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_SANDBOX_OWNERSHIP
    And the issue points to /fixture/canonical_test_roots/0
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR08
  Scenario: BDD-M08-H-N08 PID unchanged but start time differs from run-owned binding
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_PROCESS_BINDING
    And the issue points to /execution/process_started_at
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR10
  Scenario: BDD-M08-H-N09 illustrative sample purports to be actual native PASS
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_ILLUSTRATIVE_NOT_RUNTIME
    And the issue points to /illustrative_only
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR01
  Scenario: BDD-M08-H-N10 required runtime absent while verdict claims PASS
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_UNMET_PREREQUISITES
    And the issue points to /result/unmet_prerequisites
    And the input records remain unchanged
    And no native PASS is produced

  Rule: required recorded_at shape
  Scenario: BDD-M08-H-N11 timestamp lacks timezone
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_TIMESTAMP_OFFSET_REQUIRED
    And the issue points to /recorded_at
    And the input records remain unchanged
    And no native PASS is produced

  Rule: M08-HR10
  Scenario: BDD-M08-H-N12 library probe purports to satisfy portable UI native-layer gate
    Given the base synthetic record with the declared field mutations
    When its evidence claim is checked
    Then it is rejected with code E_EVIDENCE_LAYER_REQUIRED
    And the issue points to /evidence/layer
    And the input records remain unchanged
    And no native PASS is produced

