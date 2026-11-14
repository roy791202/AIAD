Feature: Complete CLI final output
  The process lifecycle module distinguishes child exit from output completion.

  Background:
    Given a live CLI run using an explicitly approved executable
    And the proposed final-output policy has been approved

  Rule: Child exit alone does not prove complete output
    Scenario: BDD-PROC-01 Late stdout and stderr are delivered
      Given the child has exited with code 0
      And stdout and stderr still have unread final output
      When the output streams finish
      Then all captured final output precedes the single successful terminal event

    Scenario: BDD-PROC-02 An empty read can still have an open stream
      Given the child has exited with code 0
      And stdout is open with no available text
      When the run is polled before its drain deadline
      Then no terminal event is published

  Rule: Incomplete output cannot claim success
    Scenario: BDD-PROC-03 Reader failure preserves captured output
      Given the child has produced "tail-before-error"
      When its stderr reader fails
      Then "tail-before-error" is delivered before a single readable failure
      And success is not reported

    Scenario Outline: BDD-PROC-04 Finite drain deadline
      Given the child exit has first been observed
      And stderr is still open
      When the run is polled <elapsed_ms> milliseconds after that observation
      Then the drain result is "<result>"
      Examples:
        | elapsed_ms | result                  |
        | 1999       | pending                 |
        | 2000       | incomplete output       |
        | 2001       | incomplete output       |

    Scenario: BDD-PROC-04B Completed output wins the deadline tie
      Given the child has exited
      When both streams reach EOF at the 2000 millisecond deadline poll
      Then captured output precedes the terminal event
      And an incomplete-output failure is not reported

  Rule: Cancellation uses the same honest output completion rule
    Scenario: BDD-PROC-05 Cancel retains captured tail
      Given a running child has produced final output
      When cancellation is requested twice
      Then cancellation remains idempotent
      And a single cancelled terminal event follows all captured output after both streams finish

    Scenario: BDD-PROC-06 A descendant holds an inherited pipe
      Given the direct child has exited
      And a descendant keeps stderr open
      When the drain deadline is reached at a poll
      Then the run reports incomplete output
      And polling does not wait for the descendant to exit

  Rule: Existing lifecycle behavior remains explicit
    Scenario: BDD-PROC-07 Nonzero exit still drains output
      Given the child has exited with code 3
      When both streams finish
      Then final output precedes a single unsuccessful exit with code 3
      And the next run can start only after queued events are delivered

    Scenario: BDD-PROC-08 Unrecognized process handle
      Given no process exists for the supplied handle
      When process output is requested
      Then the request reports that the process was not found
      And no success event is produced
