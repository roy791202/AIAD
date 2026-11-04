Feature: Strict bounded decimal admission in the candidate install document
  Background:
    Given an otherwise valid candidate install request or response
  Rule: Numeric decimal fields admit only canonical unsigned 64-bit strings
    Scenario: Reject an actual terminal line feed
      When a numeric decimal contains "1" followed by an actual line feed
      Then the complete document is rejected
    Scenario: Admit the upper bound
      When a numeric decimal is "18446744073709551615"
      Then its numeric schema admits the complete document
    Scenario: Reject overflow
      When a numeric decimal is "18446744073709551616"
      Then the complete document is rejected
