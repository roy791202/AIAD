Feature: M02 CX revised module contract
  Background:
    Given the frozen original module revision and proposed common contract

  @BDD-CX-02-normal
  Scenario: BDD-CX-02-normal
    Given Exact current/stale context and issuer-owned proof fixture for M03-H2,M04,M07
    When invoke corrected module input boundary with normal
    Then same typed design profile/digest at all design consumers

  @BDD-CX-02-stale_or_failure
  Scenario: BDD-CX-02-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M03-H2,M04,M07
    When invoke corrected module input boundary with stale_or_failure
    Then ProfileMismatch; zero ACK

  @BDD-CX-02-late_or_replay
  Scenario: BDD-CX-02-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M03-H2,M04,M07
    When invoke corrected module input boundary with late_or_replay
    Then old-profile baseline not relabeled

  @BDD-CX-03-normal
  Scenario: BDD-CX-03-normal
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M03,M04,M05,M06,M07
    When invoke corrected module input boundary with normal
    Then 18446744073709551615 preserved as exact decimal string

  @BDD-CX-03-stale_or_failure
  Scenario: BDD-CX-03-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M03,M04,M05,M06,M07
    When invoke corrected module input boundary with stale_or_failure
    Then InvalidInput for 18446744073709551616 or JSON number

  @BDD-CX-03-late_or_replay
  Scenario: BDD-CX-03-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M03,M04,M05,M06,M07
    When invoke corrected module input boundary with late_or_replay
    Then late DTO cannot overwrite newer exact revision

  @BDD-CX-11-normal
  Scenario: BDD-CX-11-normal
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M04
    When invoke corrected module input boundary with normal
    Then held source reservations precede active lease; release after receipt

  @BDD-CX-11-stale_or_failure
  Scenario: BDD-CX-11-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M04
    When invoke corrected module input boundary with stale_or_failure
    Then producer write Busy while held; incomplete writer coverage unavailable

  @BDD-CX-11-late_or_replay
  Scenario: BDD-CX-11-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M04
    When invoke corrected module input boundary with late_or_replay
    Then cancel after CAS start awaits actual result; old source not relabeled

  @BDD-CX-12-normal
  Scenario: BDD-CX-12-normal
    Given Exact current/stale context and issuer-owned proof fixture for M02,IO
    When invoke corrected module input boundary with normal
    Then shared guard protects terminal journal/read snapshot

  @BDD-CX-12-stale_or_failure
  Scenario: BDD-CX-12-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M02,IO
    When invoke corrected module input boundary with stale_or_failure
    Then forged guard/nonterminal/mismatch rejected; journalWriteCalls0

  @BDD-CX-12-late_or_replay
  Scenario: BDD-CX-12-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M02,IO
    When invoke corrected module input boundary with late_or_replay
    Then writer cannot expose transient active to reader

  @BDD-CX-15-normal
  Scenario: BDD-CX-15-normal
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M04,M05,M06,M07
    When invoke corrected module input boundary with normal
    Then issuer registry proof tag+context matches expected action

  @BDD-CX-15-stale_or_failure
  Scenario: BDD-CX-15-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M04,M05,M06,M07
    When invoke corrected module input boundary with stale_or_failure
    Then UI fabricated receipt/other proof tag denied; ackCalls0

  @BDD-CX-15-late_or_replay
  Scenario: BDD-CX-15-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M04,M05,M06,M07
    When invoke corrected module input boundary with late_or_replay
    Then restart missing issuer proof is Unverified, never fabricated completion

  @BDD-CX-16-normal
  Scenario: BDD-CX-16-normal
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M03,M04,M05,M06,M07
    When invoke corrected module input boundary with normal
    Then one serial patch owns shared path; candidate claims exact

  @BDD-CX-16-stale_or_failure
  Scenario: BDD-CX-16-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M03,M04,M05,M06,M07
    When invoke corrected module input boundary with stale_or_failure
    Then outside adopted child envelope denied

  @BDD-CX-16-late_or_replay
  Scenario: BDD-CX-16-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M01,M02,M03,M04,M05,M06,M07
    When invoke corrected module input boundary with late_or_replay
    Then new shared HEAD/SHA rebaselined before next accepted slice

  @BDD-CX-17-normal
  Scenario: BDD-CX-17-normal
    Given Exact current/stale context and issuer-owned proof fixture for M02,M06
    When invoke corrected module input boundary with normal
    Then golden/projector/native gate status shown accurately

  @BDD-CX-17-stale_or_failure
  Scenario: BDD-CX-17-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M02,M06
    When invoke corrected module input boundary with stale_or_failure
    Then missing fixture/provider is not valid RED or readiness

  @BDD-CX-17-late_or_replay
  Scenario: BDD-CX-17-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M02,M06
    When invoke corrected module input boundary with late_or_replay
    Then document regeneration never promotes product/parent card to green
