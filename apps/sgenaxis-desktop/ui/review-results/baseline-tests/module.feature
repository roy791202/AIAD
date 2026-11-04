Feature: Reproducible formal Rust build gate
  Background:
    Given the formal desktop Rust workspace and independent Tauri host
  Rule: Build outputs never hide engineering sources
    Scenario: Cargo artifacts are excluded from version control
      When Git evaluates workspace and nested Cargo output paths
      Then both output paths are ignored
      And Rust source and both effective lockfiles remain visible
  Rule: Rust checks fail closed on Windows
    Scenario: A pull request checks all formal Rust boundaries
      When the Rust workflow is inspected
      Then pull requests and manual dispatch trigger it
      And Windows runs the locked workspace tests
      And EXEC all-feature library tests run
      And the independent Tauri library tests run with Python available
      And no failing check is allowed to continue as success
