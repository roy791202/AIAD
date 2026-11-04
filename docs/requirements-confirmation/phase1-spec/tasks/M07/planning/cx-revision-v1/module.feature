Feature: M07 CX revised module contract
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

  @BDD-CX-06-normal
  Scenario: BDD-CX-06-normal
    Given Exact current/stale context and issuer-owned proof fixture for M04,M05,M06,M07
    When invoke corrected module input boundary with normal
    Then exact context/asset set resolves then durable pin issued

  @BDD-CX-06-stale_or_failure
  Scenario: BDD-CX-06-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M04,M05,M06,M07
    When invoke corrected module input boundary with stale_or_failure
    Then extra/missing response reference rejected; commitCalls0

  @BDD-CX-06-late_or_replay
  Scenario: BDD-CX-06-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M04,M05,M06,M07
    When invoke corrected module input boundary with late_or_replay
    Then stale catalog snapshot requires explicit re-resolve; no silent mapping

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

  @BDD-CX-08-normal
  Scenario: BDD-CX-08-normal
    Given Exact current/stale context and issuer-owned proof fixture for M03-H2,M04,M05,M06,M07
    When invoke corrected module input boundary with normal
    Then one S1 commit yields Applied and one history entry

  @BDD-CX-08-stale_or_failure
  Scenario: BDD-CX-08-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M03-H2,M04,M05,M06,M07
    When invoke corrected module input boundary with stale_or_failure
    Then postcommit root failure yields AppliedRetentionDeferred at actual R8

  @BDD-CX-08-late_or_replay
  Scenario: BDD-CX-08-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M03-H2,M04,M05,M06,M07
    When invoke corrected module input boundary with late_or_replay
    Then replay same mutation keeps revisionR8/history count1

  @BDD-CX-09-normal
  Scenario: BDD-CX-09-normal
    Given Exact current/stale context and issuer-owned proof fixture for M01-copy,M05,M06
    When invoke corrected module input boundary with normal
    Then children/catalog written at FINAL canonical paths then Ready receipt

  @BDD-CX-09-stale_or_failure
  Scenario: BDD-CX-09-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M01-copy,M05,M06
    When invoke corrected module input boundary with stale_or_failure
    Then Quarantined copy denied by every official open path

  @BDD-CX-09-late_or_replay
  Scenario: BDD-CX-09-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M01-copy,M05,M06
    When invoke corrected module input boundary with late_or_replay
    Then restart never relocates/rewrites journal; marker uncertain stays blocked

  @BDD-CX-10-normal
  Scenario: BDD-CX-10-normal
    Given Exact current/stale context and issuer-owned proof fixture for M05,M07
    When invoke corrected module input boundary with normal
    Then LocalIntegrityReady restore allowed with destination pin

  @BDD-CX-10-stale_or_failure
  Scenario: BDD-CX-10-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M05,M07
    When invoke corrected module input boundary with stale_or_failure
    Then missing local asset blocks restore even if source proof claims success

  @BDD-CX-10-late_or_replay
  Scenario: BDD-CX-10-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M05,M07
    When invoke corrected module input boundary with late_or_replay
    Then source root transfer pending remains Unknown/Held; no original Published ACK

  @BDD-CX-13-normal
  Scenario: BDD-CX-13-normal
    Given Exact current/stale context and issuer-owned proof fixture for M04,M07
    When invoke corrected module input boundary with normal
    Then live edit permitted after stable recovery capture+pin

  @BDD-CX-13-stale_or_failure
  Scenario: BDD-CX-13-stale_or_failure
    Given Exact current/stale context and issuer-owned proof fixture for M04,M07
    When invoke corrected module input boundary with stale_or_failure
    Then formal WriteInFlight rejects same-owner edit Busy

  @BDD-CX-13-late_or_replay
  Scenario: BDD-CX-13-late_or_replay
    Given Exact current/stale context and issuer-owned proof fixture for M04,M07
    When invoke corrected module input boundary with late_or_replay
    Then old recovery ACK leaves newer revision pending; formal baseline untouched

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
