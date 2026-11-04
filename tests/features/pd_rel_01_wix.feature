Feature: PD-REL-01 Windows WiX packaging scaffold
  As a release owner
  I want a WiX MSI packager contract for SGenAxis
  So that Windows installs are silent-verifiable and artifact hashes are traceable

  Background:
    Given packaging lives under packaging/windows/wix
    And the primary Windows packager is WiX (not NSIS or Inno)

  @PD-REL-01 @REQ-REL-WIX-01
  Scenario: Packager manifest declares WiX primary and unsupported OS
    Given packaging.manifest.json exists
    When the manifest is loaded
    Then packager.primary is "wix"
    And forbidden_primary includes "nsis" and "inno"
    And targets.windows.status is "supported"
    And targets.macos.status is "unsupported"
    And targets.linux.status is "unsupported"

  @PD-REL-01 @REQ-REL-WIX-02
  Scenario: Template and script hashes match the manifest
    Given packaging.manifest.json lists tracked file digests
    When SHA-256 is computed for each listed path
    Then every digest matches the file bytes on disk

  @PD-REL-01 @REQ-REL-WIX-03
  Scenario: WiX source names SGenAxis and carries a stable UpgradeCode
    Given SGenAxis.wxs exists
    When the WiX source is parsed as text
    Then it declares Package Name SGenAxis
    And it declares a fixed UpgradeCode GUID
    And it does not reference NSIS or Inno as the installer engine

  @PD-REL-01 @REQ-REL-WIX-06
  Scenario: MajorUpgrade removes prior install including same-version rebuilds
    Given SGenAxis.wxs exists
    When the WiX source is parsed as text
    Then it declares MajorUpgrade with AllowSameVersionUpgrades yes
    And it schedules RemoveExistingProducts afterInstallInitialize

  @PD-REL-01 @REQ-REL-WIX-04
  Scenario: README documents silent install and uninstall
    Given README.md exists in the WiX packaging folder
    When the README is read
    Then it documents msiexec /i silent install
    And it documents msiexec /x silent uninstall
    And it notes VERIFY-INSTALL checks (exit code, files, uninstall)

  @PD-REL-01 @REQ-REL-WIX-05
  Scenario: Build script prefers wix build over candle/light or NSIS
    Given build-msi.ps1 exists
    When the script is read
    Then it invokes wix build (WiX v4+)
    And it does not call makensis or iscc as the primary builder
