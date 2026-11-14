Feature: PD-REL-03 VERIFY-INSTALL contract for WiX MSI
  As a release owner
  I want a silent install/uninstall checklist and runnable hook
  So that exit / log / files / shortcut checks are explicit and not forged green

  Background:
    Given packaging lives under packaging/windows/wix
    And the primary Windows packager is WiX MSI

  @PD-REL-03 @REQ-REL-VERIFY-01
  Scenario: Checklist covers exit log files and shortcut
    Given verify-install.checklist.json exists
    When the checklist is loaded
    Then it declares categories exit, log, files, and shortcut
    And elevated checks require elevation

  @PD-REL-03 @REQ-REL-VERIFY-02
  Scenario: Non-elevated hook marks elevated checks NOT RUN
    Given verify-install.ps1 exists
    And the process is not elevated or -RunElevated is omitted
    When the hook is run
    Then elevated checklist rows have status NOT RUN
    And overall is PARTIAL or NOT RUN
    And no elevated row is forged as PASS

  @PD-REL-03 @REQ-REL-VERIFY-03
  Scenario: Docs align VERIFY-INSTALL to WiX MSI
    Given README.md and packaging.manifest.json exist
    When they are read
    Then they document msiexec /qn silent install and uninstall
    And they reference verify-install.ps1 and the checklist
    And WiX Start Menu shortcut expectations are documented
