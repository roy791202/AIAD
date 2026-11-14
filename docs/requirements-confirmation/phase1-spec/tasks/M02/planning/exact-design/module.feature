@proposal_only @M02_EXACT_CB_v1
Feature: Safe generation planning and immutable publication
  Background:
    Given an author has opened an authorized local project

  Rule: A new version becomes usable only after verified activation

    @M02-T01
    Scenario: Complete confirmed definition
      Given a complete definition and an available approved template
      When the author prepares generation
      Then the preview contains both program and UI design skeletons and the definition is unchanged

    @M02-T02
    Scenario: Missing decisions
      Given a definition with required decisions still missing
      When the author prepares generation
      Then the missing decisions are listed and no artifacts are generated

    @M02-T07
    Scenario: Stale preview
      Given a prepared preview whose definition has since changed
      When the author confirms that preview
      Then generation is refused and a fresh preview is requested

    @M02-T16
    Scenario: Cancel preview
      Given an author reviewing a generation preview
      When the author cancels
      Then the project files remain unchanged

    @M02-T18
    Scenario: Failure before activation
      Given a project with a previously usable generated version
      When preparing the replacement files fails
      Then the previously active version remains usable

    @M02-T19
    Scenario: Uncertain activation
      Given a project with a previously usable generated version
      When activating a replacement reports that recovery is required
      Then the author sees the recovery requirement and no unverified version is presented as usable

    @M02-T20
    Scenario: Late cancellation
      Given activation has already started
      When the author requests cancellation
      Then the final activation result is shown without falsely claiming cancellation

    @M02-T33
    Scenario: Refresh while publishing
      Given the preview displays a previously verified version
      When a refresh cannot obtain a verified replacement
      Then the previous preview remains visible and the refresh failure is explained
