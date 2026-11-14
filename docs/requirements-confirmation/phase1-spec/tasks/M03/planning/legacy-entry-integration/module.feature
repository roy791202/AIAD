Feature: Reject legacy authoritative design ingress
  Background:
    Given an existing owner document and persistent design
  Rule: Legacy typed inputs do not confer owner authority
    Scenario Outline: Original B058 through B060 are preserved
      Given the legacy <command> request passes the framework admission boundary
      When the old command is invoked with typed document or raw-root arguments
      Then DESIGN_OWNER_REQUIRED is reported
      And no file is read or written and no preview process is opened
      And owner state and the previous file remain unchanged
      Examples:
        | command |
        | uidesign_save_design |
        | uidesign_load_design |
        | uidesign_build_preview |
  Rule: Admission denial is distinct from owner denial
    Scenario: Caller is refused by the framework
      Given a caller without permission for the legacy command
      When the caller requests that command
      Then the command handler is not entered
      And no owner state or persistent file changes
