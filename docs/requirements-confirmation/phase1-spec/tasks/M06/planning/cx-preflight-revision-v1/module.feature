Feature: M06-preflight CX revised module contract
  Background:
    Given the frozen original module revision and proposed common contract

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

  @BDD-CX-07-normal
  Scenario: BDD-CX-07-normal
    Given Exact current/stale context and issuer-owned proof fixture for M03,M04,M05,M07
    When invoke corrected module input boundary with normal
    Then Complete material pin permits install despite Unknown RecoverySnapshots roots

  @BDD-CX-07-stale_or_failure
  Scenario: BDD-CX-07-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M03,M04,M05,M07
    When invoke corrected module input boundary with stale_or_failure
    Then missing asset blocks install; Unknown roots blocks release

  @BDD-CX-07-late_or_replay
  Scenario: BDD-CX-07-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M03,M04,M05,M07
    When invoke corrected module input boundary with late_or_replay
    Then late root observation from old epoch rejected

  @BDD-CX-14-normal
  Scenario: BDD-CX-14-normal
    Given Exact current/stale context and issuer-owned proof fixture for M03,M04,M06
    When invoke corrected module input boundary with normal
    Then complete typed mapping updates all declared references once

  @BDD-CX-14-stale_or_failure
  Scenario: BDD-CX-14-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M03,M04,M06
    When invoke corrected module input boundary with stale_or_failure
    Then unknown reference-bearing field hard-blocks; commitCalls0

  @BDD-CX-14-late_or_replay
  Scenario: BDD-CX-14-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M03,M04,M06
    When invoke corrected module input boundary with late_or_replay
    Then stale preview mapping cannot apply to new target revision

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
