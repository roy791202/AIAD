Feature: Exact candidate preparation lexical identity
  Background:
    Given the original candidate preparation policies remain proposed
  Rule: Existing anchored lexical grammars reject additional characters
    Scenario: CP-R1 binding reference with an actual line feed
      Given a complete otherwise valid preparation request
      When its binding reference has a trailing line feed
      Then the document schema rejects the request
    Scenario: CP-R2 request identity with an actual line feed
      Given a complete otherwise valid preparation request
      When its request identity has a trailing line feed
      Then the document schema rejects the request
    Scenario: Audit every reachable lexical occurrence
      Given complete request and response branches and the original lexical ranges and case rules
      When canonical boundary values and malformed lexical values are checked
      Then Python and JavaScript agree with the preserved contracts
