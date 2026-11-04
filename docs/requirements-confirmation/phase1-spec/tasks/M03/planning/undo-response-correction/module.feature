Feature: M03 Undo document correction oracle
  Background:
    Given an immutable authorized Undo capture and separate trusted issuer document fixtures
  Rule: Terminal replays preserve diagnostics and require current authority
    Scenario: BDD-F1 Retained rejection replay
      Given a retained typed NoUndo rejection and an authorized matching caller
      When the same Undo request is repeated
      Then the same typed rejection is returned with replay indicated
    Scenario: BDD-F1R Revoked caller cannot receive terminal evidence
      Given a retained rejection and a revoked caller
      When the Undo request is repeated
      Then evidence delivery is denied and retained server evidence is preserved
  Rule: Undo has no successful empty-history outcome
    Scenario: BDD-F2 Empty history
      Given a document with empty Undo history
      When Undo is requested
      Then a typed NoUndo rejection is required and NoChange success is invalid
  Rule: Evidence is bound to the whole operation
    Scenario: BDD-PROOF Coherent forged material evidence
      Given an immutable issuer record restoring material version B
      When presented evidence consistently substitutes another material version
      Then the document oracle rejects the substituted evidence
  Rule: Replay and uncertainty preserve current state
    Scenario: BDD-LIFECYCLE Changed live revision
      Given retained revision 8 and current live revision 11
      When the authorized original request is repeated
      Then revision 8 is delivered as a replay without replacing live revision 11
    Scenario: BDD-UNKNOWN Uncertain commit and pin
      Given commit evidence and actual pin state are unknown
      When an Undo terminal result is considered
      Then the outcome is indeterminate and no release or synthetic Held claim occurs
