Feature: Preserve supported M03 design content or explicitly reject unrepresentable input
  Background:
    Given an isolated design input and unchanged original source bytes

  Scenario: M03-C1-B01 legacy supported baseline remains compatible
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then existing normalized domain/field values equal; no new optional keys synthesized
    And original source content remains unchanged

  Scenario: M03-C1-B02 nested props positive control remains supported
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then nested props tree including array order retained
    And original source content remains unchanged

  Scenario: M03-C1-B03 all five currently lost UI fields are present
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then gridSize/formSize/guides and every node scope/uiExclusive semantically equal; all9 previously missing probe paths retained
    And original source content remains unchanged

  Scenario: M03-C1-B04 grid disabled explicitly
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then 0 retained, never default8
    And original source content remains unchanged

  Scenario: M03-C1-B05 node declared non-exclusive explicitly
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then false retained, never default true
    And original source content remains unchanged

  Scenario: M03-C1-B06 guides arrays empty
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then both empty arrays retained
    And original source content remains unchanged

  Scenario: M03-C1-B07 new optional fields absent in old file
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then None fields omitted on serialize; no default field creation
    And original source content remains unchanged

  Scenario: M03-C1-B08 new field has wrong explicit type
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_INVALID_FIELD:/meta/gridSize
    And original source content remains unchanged

  Scenario: M03-C1-B09 new field has wrong explicit type
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_INVALID_FIELD:/meta/guides
    And original source content remains unchanged

  Scenario: M03-C1-B10 new field has wrong explicit type
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_INVALID_FIELD:/nodes/1/uiExclusive
    And original source content remains unchanged

  Scenario: M03-C1-B11 new field has wrong explicit type
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_INVALID_FIELD:/nodes/1/scope
    And original source content remains unchanged

  Scenario: M03-C1-B12 unknown named schema member cannot be discarded
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_UNKNOWN_FIELD:/futureRoot
    And original source content remains unchanged

  Scenario: M03-C1-B13 unknown named schema member cannot be discarded
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_UNKNOWN_FIELD:/meta/futureMeta
    And original source content remains unchanged

  Scenario: M03-C1-B14 unknown named schema member cannot be discarded
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_UNKNOWN_FIELD:/nodes/1/futureNode
    And original source content remains unchanged

  Scenario: M03-C1-B15 unknown named schema member cannot be discarded
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then HostError::Settings prefix DESIGN_CODEC_UNKNOWN_FIELD:/meta/guides/future
    And original source content remains unchanged

  Scenario: M03-C1-B16 duplicate JSON keys at root or nested props
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then reject duplicate with precise pointer; dictionary construction cannot produce this fixture
    And original source content remains unchanged

  Scenario: M03-C1-B17 unrepresentable integer for JS consumer
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then DESIGN_NUMBER_UNREPRESENTABLE:/nodes/1/props/customNumber
    And original source content remains unchanged

  Scenario: M03-C1-B18 precision-losing decimal
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then DESIGN_NUMBER_UNREPRESENTABLE:/nodes/1/props/customNumber
    And original source content remains unchanged

  Scenario: M03-C1-B19 safe numeric spelling can canonicalize without value loss
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then canonical decimal value equal; raw spelling need not match
    And original source content remains unchanged

  Scenario: M03-C1-B20 product acceptance flag is forbidden
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then existing readable product_pass rejection; no preview/product PASS
    And original source content remains unchanged

  Scenario: M03-C1-B21 input byte cap boundary
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then <=16777216 accepted;16777217 DESIGN_CODEC_RESOURCE_LIMIT input bytes
    And original source content remains unchanged

  Scenario: M03-C1-B22 depth guard boundary, not serde default recursion failure
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then 63/64 accepted;65/129 explicit depth resource error
    And original source content remains unchanged

  Scenario: M03-C1-B23 node/string/number resource boundaries
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then each resource at max valid if numeric representation is otherwise supported; max+1 resource rejection before typed mapping; do not mislabel invalid number fixtures as resource RED
    And original source content remains unchanged

  Scenario: M03-C1-B24 codec cannot mutate source bytes or caller-owned state
    Given the declared fixture and mutation
    When the design representation is decoded and round-tripped
    Then full source/candidate snapshot unchanged on failure; no file/owner/Undo calls from pure codec
    And original source content remains unchanged
