Feature: Safe concurrent file persistence
  Background:
    Given an isolated writable local directory
  Rule: Each writer owns its preparation and commits a complete payload
    Scenario: Replace an existing file
      Given a file containing old bytes
      When new bytes are saved successfully
      Then the file contains exactly the new bytes
    Scenario: Concurrent saves commit complete payloads
      Given two saves are preparing different complete payloads for one file
      When both saves commit successfully in a controlled order
      Then the file contains exactly the last committed payload
    Scenario: Failure before commit preserves old bytes
      Given a file containing old bytes
      When saving fails before commit
      Then the file still contains exactly the old bytes
    Scenario: One failed save cannot damage another preparing save
      Given two saves are preparing independent payloads for one file
      When one save fails before commit and the other succeeds
      Then the file contains exactly the successful payload
    Scenario: Existing preparation collision is preserved
      Given an existing file conflicts with a preparation candidate
      When new bytes are saved successfully using another candidate
      Then the existing conflicting file remains unchanged
    Scenario: Empty payload is valid
      Given a file containing old bytes
      When an empty payload is saved successfully
      Then the file contains zero bytes
    Scenario: Replacement is denied
      Given replacement of the existing destination is denied
      When a save is attempted
      Then saving reports failure
      And the previous destination remains unchanged
