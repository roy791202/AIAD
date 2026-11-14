Feature: Prepare a design candidate without committing content
  Background:
    Given an authorized writer with a current document binding
  Rule: Preparation preserves document revision and history

  Scenario: prepare-success-replaces-slot
    Given the documented prepare-success-replaces-slot preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: unknown-control-is-preserved-not-installable
    Given the documented unknown-control-is-preserved-not-installable preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: number-lexeme-retained
    Given the documented number-lexeme-retained preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: unauthorized
    Given the documented unauthorized preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: closed
    Given the documented closed preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: viewer
    Given the documented viewer preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: owner-generation
    Given the documented owner-generation preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: stale-revision
    Given the documented stale-revision preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: dependency-C1_CODEC
    Given the documented dependency-C1_CODEC preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: dependency-ESS_PROJECTOR
    Given the documented dependency-ESS_PROJECTOR preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: dependency-M04_OWNER_INTEGRATION
    Given the documented dependency-M04_OWNER_INTEGRATION preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: dependency-M05_MATERIAL
    Given the documented dependency-M05_MATERIAL preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: duplicate-inner-key
    Given the documented duplicate-inner-key preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: invalid-size-C1
    Given the documented invalid-size-C1 preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: malformed-inner
    Given the documented malformed-inner preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: unknown-top-level
    Given the documented unknown-top-level preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-PinNotReadable
    Given the documented material-PinNotReadable preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-GrantMismatch
    Given the documented material-GrantMismatch preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-LimitExceeded
    Given the documented material-LimitExceeded preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-BlobMissing
    Given the documented material-BlobMissing preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-SizeMismatch
    Given the documented material-SizeMismatch preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-IntegrityFailure
    Given the documented material-IntegrityFailure preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-IdentityChanged
    Given the documented material-IdentityChanged preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-AliasRejected
    Given the documented material-AliasRejected preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: material-UnsupportedPlatform
    Given the documented material-UnsupportedPlatform preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: pin-proof-mismatch
    Given the documented pin-proof-mismatch preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: late-owner-completion-dropped
    Given the documented late-owner-completion-dropped preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: exact-replay
    Given the documented exact-replay preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: conflicting-replay
    Given the documented conflicting-replay preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: empty-inner
    Given the documented empty-inner preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: null-inner
    Given the documented null-inner preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: replay-after-close
    Given the documented replay-after-close preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: replay-after-transfer
    Given the documented replay-after-transfer preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged

  Scenario: replay-unauthorized
    Given the documented replay-unauthorized preconditions
    When the writer prepares the supplied design
    Then the documented response is observed
    And content revision and history remain unchanged
