Feature: Independent reacceptance of M03 viewer-close-review
  Background:
    Given the sealed documents under docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-close-review/

  @PD-P1-M03-VIEWER-CLOSE-REVIEW-01-1
  Scenario: Read-only review records hashes without changing product code
    Given a clean checkout of main
    When an independent reviewer inspects the viewer-close-review packet
    Then a review result is written under reports/dispatch-pd/
    And product crates and tests are unchanged
    And the packet is not treated as Owner adoption
