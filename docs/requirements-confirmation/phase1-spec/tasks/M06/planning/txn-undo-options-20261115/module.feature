Feature: M06 original-scope transaction and Undo option packet
  Background:
    Given PD-P1-M06-PREP-01 authorizes bounded planning documents only
    And provider-source-map-20261104 remains preserved and unrewritten
    And MH1 through MH6 remain PROPOSED_PENDING_OWNER
    And MP1 through MP4 selected remain null
    And product native build and valid RED remain NOT RUN

  Rule: Local session seams are not authenticated providers
    @M06-TXN-01
    Scenario: M06-TXN-01 local MutationPlan is not authenticated issuer
      Given a local MutationPlan and four-field CommitProjection
      When the candidate maps that plan to an authenticated issuer receipt
      Then the mapping is rejected as MP1 gap
      And no M04 issuer or M05 same-CAS inclusion is claimed

    @M06-TXN-02
    Scenario: M06-TXN-02 asset union is not Held or root CAS
      Given prepare unions before and after asset versions
      When the candidate treats that union as Undo-purpose Held or registered-root CAS
      Then the claim is rejected as MP2 gap
      And LiveDocuments UndoHistory RedoHistory fences remain missing

    @M06-TXN-03
    Scenario: M06-TXN-03 local Undo is not cross-module rollback
      Given a local session undo vector after a failed root transfer
      When the candidate claims full cross-module rollback success
      Then the claim is rejected as MP3 gap
      And local undo is not distributed compensation

    @M06-TXN-04
    Scenario: M06-TXN-04 digest guard is not ESS projector
      Given DocumentContent from_parts and a semantic digest guard
      When the candidate claims complete typed ESS entity parent edge binding rewrite
      Then the claim is rejected as MP4 gap
      And unknown reference-bearing fields must not silently pass

  Rule: Original BDD-19 stays intact; deferred retention is not adopted
    @M06-TXN-05
    Scenario: M06-TXN-05 BDD19 full restore remains authoritative
      Given phase1.feature BDD-19 verbatim 合併失敗回復
      When any candidate option is presented
      Then the original Given When Then remain unchanged
      And full restore at any commit-stage failure stays the authoritative obligation

    @M06-TXN-06
    Scenario: M06-TXN-06 reject false adoption of deferred retention
      Given OPT-B-DEFERRED-RETENTION described as MergeAppliedRetentionDeferred
      When a packet copy marks OPT-B selected approved or adopted without Owner BEHAVIOR_CHANGE
      Then the false adoption is rejected
      And the option remains BEHAVIOR_CHANGE_PENDING
      And BDD-19 is not narrowed

    @M06-TXN-07
    Scenario: M06-TXN-07 MH1 through MH6 stay pending
      Given MH1 MH2 MH3 MH4 MH5 MH6
      When the packet is checked
      Then each status is PROPOSED_PENDING_OWNER
      And none is selected

    @M06-TXN-08
    Scenario: M06-TXN-08 MP1 through MP4 selected remain null
      Given MP1 MP2 MP3 MP4 from the preserved source map
      When the packet is checked
      Then each selected value is null
      And facts are restated not replaced

    @M06-TXN-09
    Scenario: M06-TXN-09 preserve provider source map folder
      Given docs/requirements-confirmation/phase1-spec/tasks/M06/planning/provider-source-map-20261104/
      When this packet is delivered
      Then that folder content and hashes remain unchanged

    @M06-TXN-10
    Scenario: M06-TXN-10 product native build not run
      Given this document packet
      When evidence layers are listed
      Then product tests native UI build package valid RED and module PASS are NOT RUN
      And no Skeleton or implementation authority is granted
