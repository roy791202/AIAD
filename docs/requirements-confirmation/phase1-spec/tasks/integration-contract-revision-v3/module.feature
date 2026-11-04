Feature: Complete cross-module request identity and public result boundaries
  Background:
    Given the proposed v3 contracts are the review target

  @V2-F1
  Scenario: Full operation body
    Given same transition key with changed pin_id, purpose, root content or metadata
    When submit the changed request
    Then reject conflict before IO and preserve original receipt

  @V2-F1
  Scenario: Unknown body field
    Given an otherwise valid closed role request with an unknown property
    When submit the request
    Then reject InvalidRequest before hash or IO

  @V2-F2
  Scenario: Resolvable schema root
    Given one designated schema file and its local definitions
    When resolve every local reference
    Then every reference resolves within that file

  @V2-F2
  Scenario: Large wire integer
    Given revision 9007199254740993 represented as decimal text
    When transport the revision
    Then preserve exact decimal digits without Number conversion

  @V2-F3
  Scenario: Unknown mutation outcome
    Given runtime request evidence was lost
    When request the previous result
    Then report UnverifiedOutcome without automatic retry or inferred success

  @V2-F3
  Scenario: Committed retention failure
    Given one verified content commit and failed root transfer
    When return the mutation result
    Then report AppliedRetentionDeferred and retain actual revision and Held pin

  @V2-F3
  Scenario: Revoked binding
    Given an old binding after writer transfer or restart
    When query using the old binding
    Then reject binding authority before replay disclosure
