Feature: Source-fenced generation activation handoff
  Background:
    Given a sealed generation and authenticated source observations
  Rule: Activation requires coherent held sources and confirmed active commit
  @AF-01
  Scenario: AF-01 GenerationActivated
    Given immutable observation "AF-01"
    When generation activation is evaluated
    Then the observable outcome is "GenerationActivated"
  @AF-02
  Scenario: AF-02 GenerationActivated
    Given immutable observation "AF-02"
    When generation activation is evaluated
    Then the observable outcome is "GenerationActivated"
  @AF-03
  Scenario: AF-03 GenerationActivated
    Given immutable observation "AF-03"
    When generation activation is evaluated
    Then the observable outcome is "GenerationActivated"
  @AF-04
  Scenario: AF-04 SourceFenceInvalid
    Given immutable observation "AF-04"
    When generation activation is evaluated
    Then the observable outcome is "SourceFenceInvalid"
  @AF-05
  Scenario: AF-05 StaleOwnerBeforeCAS
    Given immutable observation "AF-05"
    When generation activation is evaluated
    Then the observable outcome is "StaleOwnerBeforeCAS"
  @AF-06
  Scenario: AF-06 ActivatedDeliveryDeferred
    Given immutable observation "AF-06"
    When generation activation is evaluated
    Then the observable outcome is "ActivatedDeliveryDeferred"
  @AF-07
  Scenario: AF-07 UncertainPublication
    Given immutable observation "AF-07"
    When generation activation is evaluated
    Then the observable outcome is "UncertainPublication"
  @AF-08
  Scenario: AF-08 UnverifiedOutcome
    Given immutable observation "AF-08"
    When generation activation is evaluated
    Then the observable outcome is "UnverifiedOutcome"
  @AF-09
  Scenario: AF-09 UnverifiedOutcome
    Given immutable observation "AF-09"
    When generation activation is evaluated
    Then the observable outcome is "UnverifiedOutcome"
  @AF-10
  Scenario: AF-10 DesignSaveRequired
    Given immutable observation "AF-10"
    When generation activation is evaluated
    Then the observable outcome is "DesignSaveRequired"
  @AF-11
  Scenario: AF-11 DependencyNotReady
    Given immutable observation "AF-11"
    When generation activation is evaluated
    Then the observable outcome is "DependencyNotReady"
  @AF-12
  Scenario: AF-12 DependencyNotReady
    Given immutable observation "AF-12"
    When generation activation is evaluated
    Then the observable outcome is "DependencyNotReady"
  @AF-13
  Scenario: AF-13 DependencyNotReady
    Given immutable observation "AF-13"
    When generation activation is evaluated
    Then the observable outcome is "DependencyNotReady"
  @AF-14
  Scenario: AF-14 DependencyNotReady
    Given immutable observation "AF-14"
    When generation activation is evaluated
    Then the observable outcome is "DependencyNotReady"
  @AF-15
  Scenario: AF-15 DependencyNotReady
    Given immutable observation "AF-15"
    When generation activation is evaluated
    Then the observable outcome is "DependencyNotReady"
  @AF-16
  Scenario: AF-16 VersionSealedNotActivated
    Given immutable observation "AF-16"
    When generation activation is evaluated
    Then the observable outcome is "VersionSealedNotActivated"
  @AF-17
  Scenario: AF-17 VersionSealedNotActivated
    Given immutable observation "AF-17"
    When generation activation is evaluated
    Then the observable outcome is "VersionSealedNotActivated"
  @AF-18
  Scenario: AF-18 ForbiddenImplicitSave
    Given immutable observation "AF-18"
    When generation activation is evaluated
    Then the observable outcome is "ForbiddenImplicitSave"
  @AF-19
  Scenario: AF-19 ForbiddenAutomaticRetry
    Given immutable observation "AF-19"
    When generation activation is evaluated
    Then the observable outcome is "ForbiddenAutomaticRetry"
  @AF-20
  Scenario: AF-20 SourceFenceInvalid
    Given immutable observation "AF-20"
    When generation activation is evaluated
    Then the observable outcome is "SourceFenceInvalid"
  @AF-21
  Scenario: AF-21 DependencyNotReady
    Given immutable observation "AF-21"
    When generation activation is evaluated
    Then the observable outcome is "DependencyNotReady"
  @AF-22
  Scenario: AF-22 DesignSaveRequired
    Given immutable observation "AF-22"
    When generation activation is evaluated
    Then the observable outcome is "DesignSaveRequired"
