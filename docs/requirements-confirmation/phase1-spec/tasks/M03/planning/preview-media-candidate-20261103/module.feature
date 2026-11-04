Feature: Source-bound M03 preview and media candidate preparation
  Background:
    Given the original M03 planning packet authorizes six document outputs only
    And the media support decisions remain unselected

  Rule: Preparation explains candidates without adopting runtime behavior
    Scenario: M03-DOC-01 Complete source-bound candidate
      Given the admitted media matrix and preview source observation
      When the candidate document is prepared
      Then each dimension shows its source identity and observable evidence obligation
      And static observations are distinguished from proposed capabilities

    Scenario: M03-DOC-02 Unsupported approval claim is rejected
      Given a candidate copy claiming an approved decoder without Owner disposition
      When the document is checked against the planning authority
      Then the approval claim is rejected
      And no product implementation is authorized

    Scenario: M03-DOC-03 Exactly eight dimensions
      Given the eight declared media review dimensions
      When the candidate coverage is compared with that baseline
      Then every declared dimension appears exactly once
      And missing or duplicate dimensions are rejected

    Scenario: M03-DOC-04 Missing evidence remains visible
      Given no admitted native decoder or Viewer success evidence
      When the candidate is presented for review
      Then the missing evidence is marked NOT RUN
      And format SDK and threshold decisions remain unselected
