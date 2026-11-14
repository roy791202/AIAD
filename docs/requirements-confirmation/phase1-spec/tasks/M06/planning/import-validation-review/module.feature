@proposal_only
Feature: Safe package inspection and single-document import
  Background:
    Given an author has a local target project
  Rule: Import never destroys original data

    @M06-V01
    Scenario: M06-V01
      Given a valid supported package with all referenced assets
      When inspect import
      Then report exact content and no target mutation

    @M06-V02
    Scenario: M06-V02
      Given unknown format or schema version
      When inspect import
      Then block with unsupported-version reason

    @M06-V03
    Scenario: M06-V03
      Given payload digest or required entry is invalid
      When inspect import
      Then block integrity failure; target remains unchanged

    @M06-V04
    Scenario: M06-V04
      Given external dependency missing but container structurally valid
      When inspect import
      Then request explicit incomplete-import choice; no automatic bypass

    @M06-V05
    Scenario: M06-V05
      Given author explicitly accepts missing external dependency
      When apply validated import
      Then save as incomplete/pending binding and prohibit dependent execution or generation

    @M06-V06
    Scenario: M06-V06
      Given path contains parent traversal, absolute root, drive, UNC or device prefix
      When inspect import
      Then block before creating any target path

    @M06-V07
    Scenario: M06-V07
      Given duplicate entry or case-insensitive destination collision
      When inspect import
      Then block ambiguity; never last-entry-wins

    @M06-V08
    Scenario: M06-V08
      Given file and directory prefix collide
      When inspect import
      Then block unsafe layout

    @M06-V09
    Scenario: M06-V09
      Given archive link/reparse destination escapes target root
      When inspect import
      Then block, including after destination changes before commit

    @M06-V10
    Scenario: M06-V10
      Given declared size, count or expanded bytes exceed approved cap
      When inspect import
      Then block without silent truncation or unbounded extraction

    @M06-V11
    Scenario: M06-V11
      Given input has truncated header/body or trailing unexplained bytes
      When inspect import
      Then block malformed container

    @M06-V12
    Scenario: M06-V12
      Given manifest references absent internal payload
      When inspect import
      Then block completeness failure; do not classify as missing external dependency

    @M06-V13
    Scenario: M06-V13
      Given package identity matches but provenance cannot be established
      When prepare merge
      Then mark conflict and pause affected items; offer skip or copy

    @M06-V14
    Scenario: M06-V14
      Given author chooses new copy for unresolved identity conflict
      When preview copy
      Then show new identities and certain reference adjustment scope before applying

    @M06-V15
    Scenario: M06-V15
      Given reference inside selected copy cannot be resolved
      When prepare copy
      Then mark pending resolution; do not rewrite source or existing data

    @M06-V16
    Scenario: M06-V16
      Given preview was prepared for a document that has changed
      When confirm merge
      Then reject stale preview with no target mutation

    @M06-V17
    Scenario: M06-V17
      Given merge requires changing a second target document
      When prepare merge
      Then block and explain prerequisite; never silently expand scope

    @M06-V18
    Scenario: M06-V18
      Given author cancels a prepared import
      When cancel
      Then preserve source BIN and complete target state; no Undo entry

    @M06-V19
    Scenario: M06-V19
      Given apply fails after one staged change
      When complete operation
      Then restore full before-state; no successful history entry

    @M06-V20
    Scenario: M06-V20
      Given one validated merge succeeds for one document
      When Undo once
      Then restore that document/references/binding restrictions; retain other referenced materials

    @M06-V21
    Scenario: M06-V21
      Given new project name conflicts or destination is nonempty
      When restore BIN as new project
      Then offer rename, other location or cancel; never direct overwrite

    @M06-V22
    Scenario: M06-V22
      Given input package changes after validation
      When confirm import
      Then reject changed source or use previously captured verified bytes; never mix revisions

    @M06-V23
    Scenario: M06-V23
      Given untrusted scripts or executable payload exist
      When inspect or import
      Then never execute package contents or installation hooks

    @M06-V24
    Scenario: M06-V24
      Given a filesystem or decoding dependency fails
      When inspect import
      Then report failure and keep target/source hashes unchanged

    @M06-V25
    Scenario: M06-V25
      Given application closes after failed staging before commit
      When restart
      Then retain diagnostic/recovery evidence and original target; no false success
