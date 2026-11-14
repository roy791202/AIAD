Feature: Recovery ACK admission correction
  Background:
    Given trusted complete immutable issuer evidence and valid owner state
  Rule: Admission precedes semantic access
    Scenario: RA-C-001 malformed request
      Given an invalid full request or nested required value
      When documentary admission evaluates it
      Then it returns Rejected without exception
      And state is unchanged with no ACK retry or release
    Scenario: RA-C-003 invalid admission has precedence
      Given an invalid request and unavailable proof or unknown or deferred root
      When documentary admission evaluates it
      Then Rejected precedes all proof or root outcomes
  Rule: Valid behavior remains stable
    Scenario: RA-C-002 preserve originals
      Given an original valid request
      When corrected admission evaluates it
      Then its entire output equals the original output
