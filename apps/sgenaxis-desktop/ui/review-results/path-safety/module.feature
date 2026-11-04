Feature: Project scoped scene and design paths
  Rule: File requests cannot override the bound project
    Scenario: Reject an embedded Windows drive path
      Given a bound project with existing scene data
      When a scene is saved using scene/C:/outside.ess
      Then saving fails before filesystem mutation
      And existing scene data is unchanged
    Scenario: Preserve ordinary relative file requests
      Given a bound project
      When a scene is saved using scene/nested/main.ess
      Then it is saved below the bound project
