Feature: Trustworthy implementation dispatch
  Background:
    Given a local project with host-owned task and approval state

  Rule: Only current trusted implementation bindings permit execution

    @G01
    Scenario: Current approved implementation starts once
      Given All bindings and behavioral RED match
      When implementation is requested
      Then one execution starts

    @G02
    Scenario: Caller self approval is rejected
      Given no trusted approval exists but caller claims approved and behavioral RED
      When implementation is requested
      Then request rejects and zero executions start

    @G03
    Scenario: Implementation cannot use generic entry
      Given task is authoritatively classified implementation
      When generic execution is requested
      Then request rejects and zero executions start

    @G04
    Scenario: Known generic task retains execution
      Given task is authoritatively classified generic
      When generic execution is requested
      Then existing generic execution remains available

    @G05
    Scenario: Unknown classification rejects
      Given task has no authoritative intent
      When execution is requested
      Then request rejects without implicit generic fallback

    @G06
    Scenario: Changed binding rejects
      Given one bound task project fingerprint architecture BDD skeleton or RED identity changed
      When implementation is requested
      Then request rejects and zero executions start

    @G07
    Scenario: Non behavioral RED rejects
      Given evidence is compilation failure infrastructure failure missing or PASS
      When implementation is requested
      Then request rejects and zero executions start

    @G08
    Scenario: Protected scope rejects
      Given requested changes touch a protected path
      When implementation is requested
      Then request rejects and zero executions start

    @G09
    Scenario: Restart clears approval
      Given session approval was established before restart
      When implementation is requested after restart
      Then fresh confirmation is required

    @G10
    Scenario: Revoked approval rejects
      Given trusted approval was revoked
      When implementation is requested
      Then request rejects and zero executions start
