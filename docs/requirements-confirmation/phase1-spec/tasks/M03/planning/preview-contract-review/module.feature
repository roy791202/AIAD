@proposal_only
Feature: Editor and Viewer preserve document authority
  Background:
    Given an author has a local design document
  Rule: Preview interactions never silently change saved content

    @M03-P01
    Scenario: M03-P01
      Given a confirmed target requires UI
      When create project
      Then open linked UI design window under approved user flow

    @M03-P02
    Scenario: M03-P02
      Given a confirmed target has no UI
      When create project
      Then do not open or silently manufacture a UI target

    @M03-P03
    Scenario: M03-P03
      Given Editor shows controls with author-configured behavior
      When select a control
      Then select/edit it without executing its action

    @M03-P04
    Scenario: M03-P04
      Given Viewer has an approved mock interaction
      When activate the control
      Then update isolated preview state without editing authoritative document

    @M03-P05
    Scenario: M03-P05
      Given preview target contains unsupported action or component
      When open Viewer
      Then show unsupported capability reason; no fake successful execution

    @M03-P06
    Scenario: M03-P06
      Given design contains metadata such as guides and interaction hints
      When save then reopen through declared codec
      Then preserve approved content fields and do not silently erase unknown required data

    @M03-P07
    Scenario: M03-P07
      Given selection maps to a valid stable architecture identity
      When request cross-location
      Then highlight the exact corresponding item without mutating content

    @M03-P08
    Scenario: M03-P08
      Given selection binding is missing or ambiguous
      When request cross-location
      Then show unresolved reason; do not guess by label

    @M03-P09
    Scenario: M03-P09
      Given new generation cannot be verified or build failed
      When refresh Viewer
      Then retain last verified preview if available and mark it stale; never label new output successful

    @M03-P10
    Scenario: M03-P10
      Given prepared preview belongs to an earlier document revision
      When confirm action or update
      Then reject stale binding and request refresh

    @M03-P11
    Scenario: M03-P11
      Given preview refresh is in progress
      When close window or switch project
      Then discard obsolete completion without leaking state into another session

    @M03-P12
    Scenario: M03-P12
      Given untrusted preview data requests script, file URL or external resource
      When load preview
      Then reject unsafe behavior and report reason; no privileged filesystem or command access

    @M03-P13
    Scenario: M03-P13
      Given a required material reference is unresolved
      When open or interact with Viewer
      Then show incomplete placeholder and block dependent behavior while keeping edit/save allowed

    @M03-P14
    Scenario: M03-P14
      Given Editor or Viewer has no controls
      When open design view
      Then show meaningful empty state with keyboard navigation, no unusable action

    @M03-P15
    Scenario: M03-P15
      Given document/history/recovery baselines are recorded
      When change selection or preview playback
      Then do not create document Undo or recovery content changes

    @M03-P16
    Scenario: M03-P16
      Given preview is refreshed repeatedly with identical immutable inputs
      When compare outcomes
      Then deterministic projection without extra content mutation or duplicated event delivery
