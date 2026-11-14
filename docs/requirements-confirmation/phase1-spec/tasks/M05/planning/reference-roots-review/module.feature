@proposal_only
Feature: Referenced materials survive cleanup
  Background:
    Given a local project contains immutable material versions
  Rule: Cleanup cannot destroy retained work

    @M05-ROOT-R01
    Scenario: M05-ROOT-R01
      Given candidate referenced by the current document
      When evaluate cleanup for a named immutable asset version
      Then retain with document reason

    @M05-ROOT-R02
    Scenario: M05-ROOT-R02
      Given candidate referenced only by another project document
      When evaluate cleanup for a named immutable asset version
      Then retain; current-document scan is insufficient

    @M05-ROOT-R03
    Scenario: M05-ROOT-R03
      Given candidate absent from live document but retained in Undo
      When evaluate cleanup for a named immutable asset version
      Then retain until owning history explicitly releases it

    @M05-ROOT-R04
    Scenario: M05-ROOT-R04
      Given undo moves candidate into redo-only reachability
      When evaluate cleanup for a named immutable asset version
      Then retain; do not treat Undo as permanent disposal

    @M05-ROOT-R05
    Scenario: M05-ROOT-R05
      Given candidate referenced by a retained recovery version
      When evaluate cleanup for a named immutable asset version
      Then retain even after formal save or Undo

    @M05-ROOT-R06
    Scenario: M05-ROOT-R06
      Given snapshot is unresolved and retention threshold exceeded
      When evaluate cleanup for a named immutable asset version
      Then retain; numeric retention defaults do not authorize deletion

    @M05-ROOT-R07
    Scenario: M05-ROOT-R07
      Given candidate staged for import or single-document merge
      When evaluate cleanup for a named immutable asset version
      Then retain while transaction ownership exists

    @M05-ROOT-R08
    Scenario: M05-ROOT-R08
      Given root provider unavailable or schema unsupported
      When evaluate cleanup for a named immutable asset version
      Then retain with root-incomplete warning

    @M05-ROOT-R09
    Scenario: M05-ROOT-R09
      Given complete root set is empty versus a provider omitted
      When evaluate cleanup for a named immutable asset version
      Then only complete empty set permits eligibility; omitted provider retains

    @M05-ROOT-R10
    Scenario: M05-ROOT-R10
      Given reference revision changes after cleanup preview
      When evaluate cleanup for a named immutable asset version
      Then reject stale evaluation; recollect before destructive action

    @M05-ROOT-R11
    Scenario: M05-ROOT-R11
      Given this transaction created a verified orphan and every root is complete
      When evaluate cleanup for a named immutable asset version
      Then eligible for later authorized cleanup; planning itself deletes nothing

    @M05-ROOT-R12
    Scenario: M05-ROOT-R12
      Given candidate has another logical or physical owner
      When evaluate cleanup for a named immutable asset version
      Then retain; no deleting shared bytes after Undo

    @M05-ROOT-R13
    Scenario: M05-ROOT-R13
      Given same asset id points to an unresolved differing version
      When evaluate cleanup for a named immutable asset version
      Then retain and surface conflict; no name guessing

    @M05-ROOT-R14
    Scenario: M05-ROOT-R14
      Given catalog cannot prove content identity or path ownership
      When evaluate cleanup for a named immutable asset version
      Then retain and report integrity failure

    @M05-ROOT-R15
    Scenario: M05-ROOT-R15
      Given new bytes staged but document commit fails
      When evaluate cleanup for a named immutable asset version
      Then old references and old bytes preserved; classify new owned orphan

    @M05-ROOT-R16
    Scenario: M05-ROOT-R16
      Given an eligible file cannot be removed
      When evaluate cleanup for a named immutable asset version
      Then report retained cleanup debt; no false success or dropped catalog entry

    @M05-ROOT-R17
    Scenario: M05-ROOT-R17
      Given session history closes but retained snapshot remains
      When evaluate cleanup for a named immutable asset version
      Then release history root only; snapshot root remains

    @M05-ROOT-R18
    Scenario: M05-ROOT-R18
      Given cleanup would require changing another document
      When evaluate cleanup for a named immutable asset version
      Then do not mutate it; retain asset and report dependency
