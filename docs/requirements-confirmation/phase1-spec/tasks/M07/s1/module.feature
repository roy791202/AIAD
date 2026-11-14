@Skeleton_RED_only
Feature: Recovery checks preserve unsaved changes
  Rule: Recovery tracks the successfully captured content
    Scenario: Content changes while an older snapshot is saved
      Given an older captured version is being saved and the author continues editing
      When the older snapshot is acknowledged as successfully published
      Then only the captured version becomes the recovery baseline
      And newer changes remain eligible at a later check
    Scenario: A snapshot is already in progress
      Given a recovery attempt is in progress
      When the next sixty-second check occurs
      Then a second attempt is not started
    Scenario: A snapshot fails
      Given a previously successful recovery version exists
      When the next attempt fails
      Then the previous baseline is retained and later checks may retry
