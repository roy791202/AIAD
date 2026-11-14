Feature: Wizard-only project creation contract alignment
  Background:
    Given a recorded isolated filesystem state
  Rule: Deprecated entry points cannot create a project
    @LEGACY-01
    Scenario: Direct creation with skipped preferences is rejected
      When direct creation with skipped preferences is requested
      Then WizardRequired is reported
      And no filesystem access occurs
    @LEGACY-02
    Scenario: Direct creation with a preset is rejected
      When direct creation with the balanced preset is requested
      Then WizardRequired is reported
      And no filesystem access occurs
    @LEGACY-03
    Scenario: Direct creation with conflicting preference choices is rejected
      When direct creation selects both a preset and imported preferences
      Then CHOOSE_PRESET_OR_IMPORT is reported
      And no filesystem access occurs
      And the requested target remains absent
  Rule: Successful creation belongs to the accepted wizard flow
    @WIZARD-01
    Scenario: Wizard explicitly skips preferences
      Given a valid completed wizard definition selecting no preferences
      When project creation is confirmed
      Then the project is created with no preferences file
    @WIZARD-02
    Scenario: Wizard explicitly selects a preset
      Given a valid completed wizard definition selecting the balanced preset
      When project creation is confirmed
      Then the project and matching balanced preferences are created
    @WIZARD-03
    Scenario: Conflicting preference choices are rejected
      Given a wizard definition selecting both a preset and imported preferences
      When project creation is confirmed
      Then the conflict is reported
      And the filesystem and current project binding are unchanged
