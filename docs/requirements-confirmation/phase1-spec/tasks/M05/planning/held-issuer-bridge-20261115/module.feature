Feature: Held issuer bridge remains a document packet, not adoption
  Background:
    Given PD-P1-M05-PREP-01 authorizes M05 planning documents only
    And provider-source-map-20261104 remains an unmodified preserved input
    And H1 through H4 stay PROPOSED_PENDING_OWNER
    And MP1 through MP3 stay selected=null

  Rule: Caller text is not authenticated Held
    Scenario: M05-HELD-01 owned_by_operation is caller text
      Given AssetCandidate.owned_by_operation is an Option of String
      When the Held issuer bridge packet is prepared
      Then the field is classified as caller-supplied string equality against operation_id
      And it is not recorded as an authenticated Held pin, purpose, or issuer lineage

    Scenario: M05-HELD-02 false Held claim is rejected
      Given a mutated packet that labels owned_by_operation as authenticated Held
      When the document oracle is applied
      Then the false Held claim is rejected
      And no Held issuer contract is treated as adopted

  Rule: Projection membership is not durable inclusion or native fence
    Scenario: M05-HELD-03 completeness revision and references stay projections
      Given RootObservation completeness, revision, and references plus EvaluationContext revisions
      When the Held issuer bridge packet is prepared
      Then Complete, matching revision, and reference membership remain owner-supplied projections
      And they are not recorded as durable catalog inclusion or native alias-safe fence

    Scenario: M05-HELD-04 false inclusion or fence claim is rejected
      Given a mutated packet that treats Complete or matching revision as durable inclusion or native fence
      When the document oracle is applied
      Then the false inclusion or fence claim is rejected

  Rule: Eligible identity is not delete authorization
    Scenario: M05-HELD-05 EligibleForCleanup is identity only
      Given RetentionDecision::EligibleForCleanup carries asset_id and content_digest
      When the Held issuer bridge packet is prepared
      Then the result is classified as identity-only eligibility
      And it is not recorded as delete, lease, or physical cleanup authority

    Scenario: M05-HELD-06 false delete-auth claim is rejected
      Given a mutated packet that treats EligibleForCleanup as delete authorization
      When the document oracle is applied
      Then the false delete-auth claim is rejected
      And original S1 no-physical-cleanup remains preserved

  Rule: Raw IO receipt is not semantic transfer
    Scenario: M05-HELD-07 four-field commit receipt stays raw IO
      Given CommitReceipt of target_path, previous_digest, committed_digest, and transaction_id
      When the Held issuer bridge packet is prepared
      Then the receipt is classified as raw single-file IO proof
      And it is not recorded as semantic transfer, catalog generation, or pin-root lineage

    Scenario: M05-HELD-08 false adoption claim is rejected
      Given a mutated packet that sets selected on MP1, MP2, or MP3 or marks H1 through H4 adopted
      When the document oracle is applied
      Then the false adoption claim is rejected
      And product, native, and build remain NOT RUN
      And valid product RED remains N/A
