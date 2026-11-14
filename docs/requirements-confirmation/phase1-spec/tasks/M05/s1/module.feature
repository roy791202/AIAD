@Skeleton_RED_only
Feature: Referenced materials remain retained
  Rule: Incomplete reference knowledge never permits cleanup
    Scenario: Missing snapshot roots
      Given the snapshot reference provider is unavailable
      When a material is evaluated for retention
      Then it is retained with an incomplete-snapshot-root reason
    Scenario: Complete unreferenced operation-owned material
      Given every reference root is complete and the material belongs to this operation
      When retention is evaluated
      Then the result is only a cleanup candidate identity and no file is deleted
    Scenario: A shared material remains referenced
      Given another document or Undo or recovery snapshot references a material
      When retention is evaluated
      Then the material is retained with the exact referencing root and owner
