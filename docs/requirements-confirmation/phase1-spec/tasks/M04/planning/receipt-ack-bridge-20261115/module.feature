Feature: Exact receipt, root-transfer and semantic ACK provider mapping
  Background:
    Given PD-P1-M04-PREP-01 remains Yellow with save/retention observation already PASS as documents
    And existing packets provider-source-map-20261104, save-retention-observation-proposal and save-response-handoff stay unmodified
    And Owner G1 through G4 plus three bridge options remain unselected
    And original BDD-19 complete restoration at any commit failure is not reinterpreted

  Rule: A filesystem path or four-field file receipt is not a semantic ACK
    Scenario: M04-ACK-1 Path from FileSystemPort.write_atomic is not ACK
      Given HOST scene save helper returns a path from FileSystemPort.write_atomic
      When the document mapping is evaluated
      Then the observed outcome is REJECT_PATH_IS_NOT_ACK
      And no semantic ACK, authenticated Held or root-transfer is recorded

    Scenario: M04-ACK-2 Four-field CommitReceipt is not ACK
      Given a CommitReceipt with only target_path, previous_digest, committed_digest and transaction_id
      When the document mapping is evaluated
      Then the observed outcome is REJECT_RECEIPT_IS_NOT_ACK
      And raw committed_digest is not treated as document semantic digest

  Rule: Missing issuer or replay cannot mint Held, root-transfer or ACK
    Scenario: M04-ACK-3 Missing issuer cannot prove Held or root-transfer
      Given captured file evidence without an authenticated M05 issuer receipt
      When the document mapping is evaluated
      Then the observed outcome is REJECT_MISSING_ISSUER
      And Held and root-transfer remain unproven

    Scenario: M04-ACK-4 Replay of a prior receipt or ACK is rejected
      Given a previously consumed receipt or ACK tuple is presented again
      When the document mapping is evaluated
      Then the observed outcome is REJECT_REPLAY
      And formal baseline is not rewritten from the replay

  Rule: Newer formal revision and false adoption stay rejected
    Scenario: M04-ACK-5 Stale captured ACK cannot replace a newer formal revision
      Given captured revision 10 and an existing formal baseline at revision 11
      When the document mapping is evaluated
      Then the observed outcome is REJECT_NEWER_REVISION
      And the newer formal baseline remains the observed document fact

    Scenario: M04-ACK-6 False adoption or false ACK claim is rejected
      Given a candidate that marks G1 through G4 selected or claims path receipt as adopted ACK
      When the document mapping is evaluated
      Then the observed outcome is REJECT_FALSE_ADOPTION
      And Owner decisions remain null

  Rule: M05 retention policy is not delete authorization or root-transfer
    Scenario: M04-ACK-7 EligibleForCleanup is not delete authorization
      Given M05-S1 returns EligibleForCleanup identity only
      When the document mapping is evaluated
      Then the observed outcome is REJECT_RETENTION_IS_NOT_DELETE_AUTH
      And no cleanup lease or root-transfer is inferred

    Scenario: M04-ACK-8 Mapping lists providers without claiming ACK success
      Given the three field-bridge gaps with selected null
      When the document mapping is evaluated
      Then the observed outcome is PASS_DOCUMENT_MAPPING_ONLY
      And no product, native, build or valid RED run is claimed
