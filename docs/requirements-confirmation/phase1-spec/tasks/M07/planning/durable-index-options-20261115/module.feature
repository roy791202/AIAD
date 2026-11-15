Feature: M07 durable index options document packet
  Background:
    Given PD-P1-M07-PREP-01 original-scope planning only
    And the closed provider-source-map-correction-20261104 packet is preserved
    And RA-L1, RA-L2, RA-L3, PH-G2, PH-G3, PH-G4, MP1, MP2, MP3, MP4 remain unselected

  Rule: Ordinal admission rejects empty and out-of-range values without adopting a formula
    @M07-IDX-01
    Scenario: Empty ordinal is rejected
      Given a candidate recovery-index document with ordinal ""
      When the document oracle evaluates ordinal admission
      Then the result is REJECT_EMPTY_ORDINAL
      And no ordinal formula is selected

    @M07-IDX-02
    Scenario: Out-of-range ordinal is rejected
      Given a candidate recovery-index document with ordinal outside admitted decimal u64
      When the document oracle evaluates ordinal admission
      Then the result is REJECT_OUT_OF_RANGE_ORDINAL
      And CapturedAttempt is not treated as an ordinal calculator

  Rule: Published HOST event is not durable index attestation
    @M07-IDX-03
    Scenario: Treating Published as durable index is rejected
      Given CompletionOutcome Published cited from closed RS05
      When a candidate claims Published equals RecoveryIndex attestation
      Then the result is REJECT_PUBLISHED_AS_DURABLE_INDEX
      And RS05 remains cited not reopened

  Rule: Local baseline is not atomic replay or native restart PASS
    @M07-IDX-04
    Scenario: Local baseline is not atomic replay/restart
      Given the local recovery baseline setter cited from closed DE02 meaning
      When a candidate claims that setter is atomic replay/restart
      Then the result is REJECT_LOCAL_BASELINE_AS_ATOMIC_REPLAY

    @M07-IDX-05
    Scenario: CapturedAttempt has no ordinal formula
      Given CapturedAttempt fields cited from closed RS01/RS06
      When a candidate claims an ordinal formula on CapturedAttempt
      Then the result is REJECT_CAPTURED_ATTEMPT_ORDINAL_FORMULA
      And MP1 selected remains null

    @M07-IDX-06
    Scenario: False native restart PASS is rejected
      Given native timer, capture and restart evidence are NOT RUN
      When a candidate records native restart PASS
      Then the result is REJECT_FALSE_NATIVE_RESTART_PASS
      And product, native and build remain NOT RUN

  Rule: Pending gates stay null; closed spans stay closed
    @M07-IDX-07
    Scenario: Pending gates remain null
      Given this options packet
      When Owner adoption is inspected
      Then RA-L1 RA-L2 RA-L3 PH-G2 PH-G3 PH-G4 MP1 MP2 MP3 MP4 selected are null
      And IDX-O1 and IDX-O2 remain PROPOSED_PENDING_OWNER

    @M07-IDX-08
    Scenario: Closed RS04 RS05 RS06 are cited only
      Given provider-source-map-correction-20261104
      When this packet binds elapsed check, Published completion and capture syntax
      Then it cites RS04 RS05 RS06 without changing their sealed ranges
      And product implementation is not authorized
