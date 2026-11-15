Feature: Independent reacceptance of M03 viewer-refresh-review
  Background:
    Given the sealed documents under docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-refresh-review/

  @PD-P1-M03-VIEWER-REFRESH-REVIEW-01-1
  Scenario: Read-only review records hashes without changing product code
    Given a clean checkout of main
    When an independent reviewer inspects the viewer-refresh-review packet
    Then a review result is written under reports/dispatch-pd/
    And product crates and tests are unchanged
    And the packet is not treated as Owner adoption
