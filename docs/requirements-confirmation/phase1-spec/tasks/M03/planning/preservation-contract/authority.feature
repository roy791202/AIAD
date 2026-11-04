Feature: Editor and Viewer have separate mutation authority (H2 proposal)

  Scenario: M03-A01
    Given Editor mode bound to a design revision
    When select an existing stable-ID control
    Then selection only; no mock configured behavior, no dirty/Undo/snapshot revision

  Scenario: M03-A02
    Given explicit Viewer mode with permitted mock intent
    When simulate a control value change
    Then detached mock value changes; original design props/revision/hashes unchanged

  Scenario: M03-A03
    Given message references stale revision/session
    When apply the preview intent
    Then StaleRevision, no source mutation; no automatic refresh/merge/remap

  Scenario: M03-A04
    Given ID mapping missing or ambiguous
    When cross-locate
    Then explicit disabled/unresolved outcome; never guess from label

  Scenario: M03-A05
    Given previous valid preview and failed refresh candidate
    When refresh validation fails
    Then previous preview retained and visibly stale, not reported current
