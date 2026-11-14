@proposal_only
Feature: Recovery saves complete stable editing content
  Background:
    Given an author is editing a local project
  Rule: Successful recovery never loses changes made during saving

    @M07-CAP-01
    Scenario: M07-CAP-01
      Given 59 seconds since last check
      When check deadline has not arrived
      Then no capture

    @M07-CAP-02
    Scenario: M07-CAP-02
      Given 60 seconds reached; content equals successful snapshot
      When periodic check runs
      Then no snapshot and no baseline change

    @M07-CAP-03
    Scenario: M07-CAP-03
      Given first check with unsaved content and no recovery baseline
      When periodic check runs
      Then capture current complete content and required materials

    @M07-CAP-04
    Scenario: M07-CAP-04
      Given clear, merge or Undo mutation still in progress
      When check deadline arrives
      Then defer capture until complete commit or full rollback

    @M07-CAP-05
    Scenario: M07-CAP-05
      Given a snapshot is still being written
      When another check deadline arrives
      Then no overlapping writer or queued timer burst

    @M07-CAP-06
    Scenario: M07-CAP-06
      Given snapshot captured R; editor has changed to R+1
      When R finishes successfully
      Then baseline acknowledges only R; R+1 remains pending

    @M07-CAP-07
    Scenario: M07-CAP-07
      Given snapshot captured R; material bytes change before publication
      When publication is attempted
      Then publish only immutable pinned bytes matching R or fail without advancing baseline

    @M07-CAP-08
    Scenario: M07-CAP-08
      Given payload or material write fails
      When snapshot attempt completes
      Then retain previous valid snapshot and pending content

    @M07-CAP-09
    Scenario: M07-CAP-09
      Given payload durable but index publication fails
      When snapshot attempt completes
      Then do not advance baseline or release previous snapshot roots

    @M07-CAP-10
    Scenario: M07-CAP-10
      Given snapshot R succeeded and current content is R+1
      When formal save succeeds
      Then formal baseline alone changes; recovery baseline remains R

    @M07-CAP-11
    Scenario: M07-CAP-11
      Given snapshot R exists
      When formal save fails
      Then retain recovery data and pending states

    @M07-CAP-12
    Scenario: M07-CAP-12
      Given only selection, hover or playback position changed
      When periodic check runs
      Then no content-triggered snapshot

    @M07-CAP-13
    Scenario: M07-CAP-13
      Given content was changed and then restored to last snapshot content
      When periodic check runs
      Then skip equivalent content despite a higher editor revision

    @M07-CAP-14
    Scenario: M07-CAP-14
      Given two sessions edit same stable project identity
      When both reach a check deadline
      Then separate session recovery namespaces and baselines

    @M07-CAP-15
    Scenario: M07-CAP-15
      Given old session closes while its snapshot write finishes
      When completion arrives in a new session
      Then do not apply old completion to new session baseline; retain old recoverable data

    @M07-CAP-16
    Scenario: M07-CAP-16
      Given an attempt already completed
      When duplicate acknowledgement arrives
      Then reject or harmlessly ignore without changing current baseline

    @M07-CAP-17
    Scenario: M07-CAP-17
      Given original project drive is offline
      When complete recovery version is opened
      Then open unsaved content with necessary assets and allow save to another location

    @M07-CAP-18
    Scenario: M07-CAP-18
      Given recovery root cannot be written
      When snapshot attempt fails
      Then persistent visible warning, alternative-location action and no false saved claim

    @M07-CAP-19
    Scenario: M07-CAP-19
      Given history item refers to retained recovery version
      When author removes history item
      Then remove entry only; files and recovery roots remain

    @M07-CAP-20
    Scenario: M07-CAP-20
      Given a recovery index has unsupported schema or incomplete assets
      When recovery versions are enumerated
      Then mark unavailable or incomplete with reason; do not silently activate or discard

    @M07-CAP-21
    Scenario: M07-CAP-21
      Given timer resumes after a long suspended interval
      When deadline is checked
      Then one pending check, not one write per missed interval

    @M07-CAP-22
    Scenario: M07-CAP-22
      Given captured bytes are durable but process dies before index success is known
      When application restarts
      Then previous verified entry remains valid; inspect orphan candidate without treating it as a successful baseline
