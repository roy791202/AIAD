Feature: Read-only Viewer entry
  Background:
    Given a trusted document owner and isolated preview consumer
  Rule: Entering Viewer cannot mutate authoritative document state

    @PB-01
    Scenario: supported snapshot seeds detached typed mocks
      Given document fixture PB-01
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-02
    Scenario: empty supported Form is read-only
      Given document fixture PB-02
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-03
    Scenario: capacity min+one below maximum succeeds
      Given document fixture PB-03
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-04
    Scenario: unauthorized native caller rejected
      Given document fixture PB-04
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-05
    Scenario: binding missing
      Given document fixture PB-05
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-06
    Scenario: stale generation
      Given document fixture PB-06
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-07
    Scenario: stale revision
      Given document fixture PB-07
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-08
    Scenario: owner provider unavailable
      Given document fixture PB-08
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-09
    Scenario: preview capacity four
      Given document fixture PB-09
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-10
    Scenario: trusted projector rejects UnsupportedDocument
      Given document fixture PB-10
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-11
    Scenario: trusted projector rejects CodecRejected
      Given document fixture PB-11
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-12
    Scenario: trusted projector rejects AmbiguousStableId
      Given document fixture PB-12
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-13
    Scenario: trusted projector rejects ParentMissing
      Given document fixture PB-13
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-14
    Scenario: trusted projector rejects ParentCycle
      Given document fixture PB-14
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-15
    Scenario: trusted projector rejects DependencyNotReady
      Given document fixture PB-15
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-16
    Scenario: late delivery generation
      Given document fixture PB-16
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-17
    Scenario: late delivery revision
      Given document fixture PB-17
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-18
    Scenario: late delivery consumer_instance
      Given document fixture PB-18
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-19
    Scenario: late delivery document_identity
      Given document fixture PB-19
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-20
    Scenario: late delivery closed
      Given document fixture PB-20
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-21
    Scenario: u64 max revision preserved
      Given document fixture PB-21
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-22
    Scenario: missing request input
      Given document fixture PB-22
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed

    @PB-23
    Scenario: unknown request field
      Given document fixture PB-23
      When the consumer enters Viewer
      Then the declared result and unchanged document state are observed
