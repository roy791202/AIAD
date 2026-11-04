Feature: M02 source-bound template evidence inventory
  Background:
    Given the adopted first template baseline declares fourteen product paths
    And this task permits document preparation only
  Rule: Document completeness does not imply product proof
    Scenario: M02-G14-01 source-bound complete candidate
      Given the admitted baseline and its source digest
      When the candidate inventory is reviewed
      Then each of the fourteen paths has a source pointer and evidence obligation
    Scenario: M02-G14-02 unsupported adoption rejected
      Given no admitted resource revision approval
      When a candidate claims product approval
      Then that claim is rejected
    Scenario: M02-G14-03 exact path boundary
      Given the fourteen declared baseline paths
      When a candidate replaces one path while keeping fourteen rows
      Then the candidate fails exact baseline comparison
    Scenario: M02-G14-04 missing evidence remains explicit
      Given no admitted resource bytes or standalone lock proof
      When the inventory is prepared
      Then their evidence status remains MISSING
      And product verification remains NOT RUN
