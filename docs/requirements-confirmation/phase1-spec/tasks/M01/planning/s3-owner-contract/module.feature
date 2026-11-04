Feature: M01 owner-bound native selection
  # Proposed planning cases, not executable RED

  Scenario: S3-OW-01
    Given {"label": "settings", "scheme": "tauri", "host": "localhost", "port": null}
    When begin requested
    Then UNAUTHORIZED_CALLER
    And persistence calls equal 0

  Scenario: S3-OW-02
    Given {"label": "main", "scheme": "https", "host": "example.com", "port": null}
    When begin requested
    Then UNAUTHORIZED_CALLER
    And persistence calls equal 0

  Scenario: S3-OW-03
    Given {"label": "main", "scheme": "http", "host": "localhost", "port": 1420}
    When begin requested
    Then UNAUTHORIZED_CALLER
    And persistence calls equal 0

  Scenario: S3-OW-04
    Given {"label": "main", "scheme": "tauri", "host": "localhost", "port": null}
    When begin requested
    Then CALLER_GATE_ONLY
    And persistence calls equal 0

  Scenario: S3-OW-05
    Given {"label": "main", "scheme": "http", "host": "tauri.localhost", "port": null}
    When begin requested
    Then CALLER_GATE_ONLY
    And persistence calls equal 0

  Scenario: S3-OW-06
    Given {"label": "main", "scheme": "https", "host": "tauri.localhost", "port": null}
    When begin requested
    Then CALLER_GATE_ONLY
    And persistence calls equal 0

  Scenario: S3-OW-07
    Given "no native selection capability"
    When UI submits a parent display path
    Then SELECTION_REQUIRED
    And persistence calls equal 0 additional

  Scenario: S3-OW-08
    Given "selection belongs to another owner"
    When begin requested
    Then SELECTION_OWNER_MISMATCH
    And persistence calls equal 0 additional

  Scenario: S3-OW-09
    Given "selection is existing-project-only"
    When new project begin requested
    Then SELECTION_PURPOSE_MISMATCH
    And persistence calls equal 0 additional

  Scenario: S3-OW-10
    Given "picker captured generation 7, current generation 8"
    When native result returns
    Then STALE_OWNER and generation 8 unchanged
    And persistence calls equal 0 additional

  Scenario: S3-OW-11
    Given "live owner has selection A"
    When picker cancelled
    Then selection A remains; no new ID
    And persistence calls equal 0 additional

  Scenario: S3-OW-12
    Given "save request is already captured"
    When window destroyed
    Then owner revoked, captured request detached
    And persistence calls equal 0 additional

  Scenario: S3-OW-13
    Given "saved draft exists and old capability expired"
    When explicit reopen succeeds
    Then fresh generation and no prior capability revived
    And persistence calls equal 0 additional

  Scenario: S3-OW-14
    Given "existing registered project and lease snapshot"
    When wizard begins
    Then WORK registry/leases and HostSettings unchanged
    And persistence calls equal 0 additional

  Scenario: S3-OW-15
    Given "captured request committed after owner changed"
    When completion delivered
    Then proof retained, no binding or cleanup
    And persistence calls equal 0 additional
