Feature: Honest MCP execution availability
  Background:
    Given the production host has no real MCP transport
  Rule: Simulation cannot be reported as production Live execution
    Scenario: Live request with an otherwise valid target
      Given an activatable target and approved tool
      When MCP Live execution is requested
      Then the request reports NOT RUN with an unavailable transport reason
      And no accepted run, lease, running task or successful evidence is created
    Scenario: Rejection does not block later simulation
      Given an MCP Live request was rejected because transport was unavailable
      When explicit MCP DryRun execution is requested
      Then the simulation starts and completes normally
    Scenario: Repeated requests remain unexecuted
      Given an activatable target and approved tool
      When MCP Live execution is requested again after an unavailable rejection
      Then the request reports NOT RUN without an active-run lock
    Scenario Outline: Unsafe targets remain inactive
      Given the MCP target is <target>
      When MCP Live execution is requested
      Then the request reports NOT RUN
      And no transport operation occurs
      Examples:
        | target |
        | empty |
        | reserved port 8788 |
        | reserved port 8787 |
    Scenario: Failure does not disclose credentials
      Given settings contain a secret token and endpoint credentials
      When an unavailable or prohibited MCP Live request is rejected
      Then the failure contains no secret token or raw endpoint credentials
    Scenario: Explicit simulation fixtures preserve adapter coverage
      Given a test explicitly supplies a simulated MCP transport
      When its approved MCP execution is requested
      Then the simulated response remains testable as simulation evidence
