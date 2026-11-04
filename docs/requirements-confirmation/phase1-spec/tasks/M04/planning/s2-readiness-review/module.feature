Feature: M04 formal persistence preserves captured content and proof (proposal)

  Scenario: M04-S2-P01
    Given Captured semantic hash A differs from raw encoded hash E; current document advanced R to R+1
    When Verified receipt commits E for exact target
    Then HOST acknowledges captured R with A; formal baseline advances only to A, currentR+1 dirty, recovery baseline/history unchanged

  Scenario: M04-S2-P02
    Given Codec returns unrepresentable-content rejection
    When Save requested
    Then No acquire/create/write/ACK; source and both baselines/Undo unchanged

  Scenario: M04-S2-P03
    Given Success receipt has wrong target/digest/previous digest/txid
    When Validate completion
    Then Retain reported proof as evidence mismatch; no ACK or further write, no fabricated rollback/journal diagnostics

  Scenario: M04-S2-P04
    Given Native commit ordinary Storage failure with verified old-byte preservation
    When Handle save completion
    Then No baseline or history acknowledgement; original raw bytes and both baselines unchanged

  Scenario: M04-S2-P05
    Given Native RecoveryRequired returns exact target/journal/old/new paths
    When Handle save completion
    Then Copy exact diagnostics; proposed safety gate blocks destructive entry points; no clean rollback claim

  Scenario: M04-S2-P06
    Given Disk committed but owner/session closed or changed before ACK
    When Handle late completion
    Then Retain committed proof; do not mutate new owner/session or misreport failed-unchanged

  Scenario: M04-S2-P07
    Given Old ACK arrives after newer formal baseline
    When Apply completion
    Then No baseline regression; retained persistence evidence and explicit stale/out-of-order ACK outcome

  Scenario: M04-S2-P08
    Given Recovered content and formal baseline differ
    When Formal save succeeds
    Then Recovery baseline and retained snapshots are not reset or cleared

  Scenario: M04-S2-P09
    Given Source disk bytes externally reformatted or replaced
    When Save under cooperating lease
    Then Compare raw baseline before replacing; stale raw bytes conflict even if semantic content appears equal

  Scenario: M04-S2-P10
    Given ESS embeds work/architecture/design and unknown supported extension data
    When Decode/encode verified candidate
    Then Preserve all supported composite content or refuse before persistence; no second standalone design write
