Feature: M04 captured formal save response handoff
  Background:
    Given one M04 document owner with a captured formal save
  Rule: A file receipt cannot stand in for root and semantic acknowledgement
    Scenario: Mismatched receipt blocks acknowledgement
      Given the reported receipt differs from the captured target
      When the save outcome is reconciled
      Then no material root transfer or semantic acknowledgement occurs
      And the outcome does not claim the previous file is unchanged
    Scenario: Verified file with deferred material root
      Given the captured bytes were verified as committed
      And material retention has not attested transfer
      When the save outcome is reconciled
      Then committed evidence is retained as root deferred
      And no semantic acknowledgement occurs
    Scenario: Captured save completes while live revision is newer
      Given the captured revision is 10 and the live revision is 11
      When the verified file and material root are acknowledged
      Then the formal baseline identifies captured revision 10
      And live revision 11 stays dirty
      And the recovery baseline stays unchanged
    Scenario: A later formal baseline rejects an old acknowledgement
      Given the formal baseline already identifies revision 11
      When captured revision 10 acknowledgement arrives
      Then the newer formal baseline remains unchanged
      And the committed result is semantic acknowledgement deferred
