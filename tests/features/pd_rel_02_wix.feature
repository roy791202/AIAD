Feature: PD-REL-02 WiX embeds real Tauri release exe
  As a release owner
  I want build-msi to stage sgenaxis-desktop.exe with matching SHA-256
  So that the MSI embeds the verified desktop binary

  Background:
    Given packaging lives under packaging/windows/wix
    And the Tauri release exe exists under apps/sgenaxis-desktop/src-tauri/target/release

  @PD-REL-02 @REQ-REL-WIX-PAYLOAD-01
  Scenario: Manifest declares payload source and SHA-256
    Given packaging.manifest.json has a payload section
    When the manifest is loaded
    Then payload.source_relpath ends with sgenaxis-desktop.exe
    And payload.sha256 is a 64-char hex digest
    And payload.bytes is at least 100000

  @PD-REL-02 @REQ-REL-WIX-PAYLOAD-02
  Scenario: Manifest SHA-256 matches Tauri release on disk
    Given the Tauri release exe exists
    When SHA-256 is computed for the release exe
    Then it equals packaging.manifest.json payload.sha256
    And the file size equals payload.bytes

  @PD-REL-02 @REQ-REL-WIX-PAYLOAD-03
  Scenario: Staged payload matches Tauri release
    Given payload/SGenAxis.exe is staged
    When SHA-256 is computed for the staged exe
    Then it equals the Tauri release digest and payload.sha256

  @PD-REL-02 @REQ-REL-WIX-PAYLOAD-04
  Scenario: build-msi stages Tauri exe and gates on hash
    Given build-msi.ps1 exists
    When the script is read
    Then it references sgenaxis-desktop.exe
    And it verifies SHA-256 against packaging.manifest.json
    And it invokes wix build
    And it does not force msiexec /qn install
