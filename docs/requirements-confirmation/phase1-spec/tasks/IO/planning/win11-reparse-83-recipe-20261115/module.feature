# language: en
@planning_only @IO_PREREQ @document_recipe @IO-FX
Feature: Win11 x64 native reparse and 8.3 fixture RECIPE
  Background:
    Given task PD-P1-IO-PREREQ-IMPL-01 remains Yellow pending Win11 x64 and IO-A-F1 reparse/8.3
    And existing Windows 10 build 19045 adapter-slice evidence is retained unchanged
    And no new Owner adoption is required or claimed
    And this host is not a substitute for native Windows 11

  Rule: SUCCESS requires actual Win11 x64 plus live reparse and 8.3 oracles
    @IO-FX-01
    Scenario: IO-FX-01 Windows 11 x64 identity
      Given a candidate host identity capture
      When the OS name, build, and architecture oracles are evaluated
      Then SUCCESS is allowed only when ProductName is Windows 11, CurrentBuildNumber is 22000 or higher, and OSArchitecture is 64-bit
      And Windows 10 build 19045 is not treated as Windows 11
      And a non-Windows 11 host records explicit NOT RUN rather than PASS

    @IO-FX-02
    Scenario: IO-FX-02 real reparse-point oracle
      Given a disposable temporary directory owned by this recipe
      When a directory junction is created with mklink /J and queried with fsutil reparsepoint query
      Then SUCCESS requires a live Reparse Tag on that junction
      And Linux, WSL-without-NTFS-reparse, or skipped junction creation records NOT RUN
      And junction experiments outside a disposable temp directory are forbidden

    @IO-FX-03
    Scenario: IO-FX-03 real 8.3 short-name oracle
      Given 8.3 name generation is queryable on the volume that holds the disposable temp directory
      When a long file name is created and dir /x plus fsutil 8dot3name query return a short-name alias
      Then SUCCESS requires an observed 8.3 alias distinct from the long name
      And a volume with 8.3 disabled, or a non-Windows host, records NOT RUN

    @IO-FX-04
    Scenario: IO-FX-04 combined native gate
      Given IO-FX-01, IO-FX-02, and IO-FX-03 oracles
      When the platform gate for IO-A-F1 remaining reparse/8.3 coverage is scored
      Then SUCCESS holds only if all three oracles actually passed on the same Windows 11 x64 host
      And any missing oracle keeps the gate NOT RUN
      And this recipe does not reopen or rewrite Win10 19045 PASS evidence

  Rule: False platform claims are rejected
    @IO-FX-05
    Scenario: IO-FX-05 claiming Windows 10 as Windows 11 is REJECT
      Given a capture that reports Windows 10 Version 10.0.19045 or otherwise CurrentBuildNumber below 22000
      When a document or log labels that host as Windows 11 PASS
      Then the claim is REJECT
      And lightReason continues to state that Win11/reparse/8.3 are missing

    @IO-FX-06
    Scenario: IO-FX-06 Linux or other non-Win11 authoring host
      Given this packet is authored on Linux 6.12 x86_64 without NTFS reparse or 8.3
      When native commands are considered
      Then every native fixture case is explicit NOT RUN with reason host_is_not_windows11_x64
      And documented cmd.exe commands are recipes only, not executed destructive experiments
      And product, native matrix, and platform PASS remain unclaimed
