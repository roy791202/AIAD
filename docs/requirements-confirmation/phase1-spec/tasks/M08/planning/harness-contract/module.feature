Feature: Trustworthy native acceptance evidence

  @M08-N01
  Scenario: Move portable program
    Given locked phase1-capable artifact and disposable test environment
    When move copied portable folder A to B, launch B
    Then same user recovery sessions visible; executable path is B; original project unchanged

  @M08-N02
  Scenario: Read-only original project
    Given locked phase1-capable artifact and disposable test environment
    When edit isolated project then make original directory read-only
    Then recovery succeeds in approved user area or explicit warning; recovered content saves elsewhere

  @M08-N03
  Scenario: Original project drive offline
    Given locked phase1-capable artifact and disposable test environment
    When make isolated original volume unavailable then recover
    Then unsaved recovery contains required materials and can save at new location

  @M08-N04
  Scenario: Two editing sessions
    Given locked phase1-capable artifact and disposable test environment
    When edit same project in two isolated processes
    Then session namespaces do not overwrite each other

  @M08-N05
  Scenario: Kill after successful snapshot
    Given locked phase1-capable artifact and disposable test environment
    When terminate isolated test process after acknowledged snapshot
    Then restart offers last successful snapshot; never promises later unpersisted edits

  @M08-N06
  Scenario: Kill during payload/index write
    Given locked phase1-capable artifact and disposable test environment
    When interrupt staged write before acknowledgement
    Then previous valid snapshot remains; incomplete version not falsely activated

  @M08-N07
  Scenario: 60-second boundary
    Given locked phase1-capable artifact and disposable test environment
    When check at 59/60/61 seconds with a changed version
    Then no early snapshot; one eligible check at deadline; no duplicate writers

  @M08-N08
  Scenario: UI remains responsive
    Given locked phase1-capable artifact and disposable test environment
    When interact while large permitted snapshot writes
    Then input remains usable and changes stay pending for next capture

  @M08-N09
  Scenario: No content change
    Given locked phase1-capable artifact and disposable test environment
    When move selection and playback without content edits
    Then no new recovery payload; no baseline distortion

  @M08-N10
  Scenario: Required WebView2 unavailable
    Given locked phase1-capable artifact and disposable test environment
    When launch locked portable in controlled missing-runtime environment
    Then clear prerequisite result; no application success fabricated

  @M08-N11
  Scenario: Unwritable recovery location
    Given locked phase1-capable artifact and disposable test environment
    When deny write permission only in disposable recovery root
    Then persistent visible warning and explicit alternative action; no saved claim

  @M08-N12
  Scenario: Corrupt/unknown recovery version
    Given locked phase1-capable artifact and disposable test environment
    When inject corrupt payload or unsupported metadata in disposable data root
    Then safe unavailable reason, no execution and no destructive auto-cleanup

  @M08-N13
  Scenario: Merge/Undo during check
    Given locked phase1-capable artifact and disposable test environment
    When trigger check during single-document merge then Undo
    Then capture only completed or fully rolled-back state; one Undo; shared material preserved

  @M08-N14
  Scenario: Missing-dependency imported content
    Given locked phase1-capable artifact and disposable test environment
    When open explicitly accepted incomplete document
    Then view/save available, dependent execution/generation blocked

  @M08-N15
  Scenario: History removal
    Given locked phase1-capable artifact and disposable test environment
    When remove history item for retained recovery snapshot
    Then history entry removed; document/snapshot/material bytes unchanged

  @M08-N16
  Scenario: Unicode/space portable path
    Given locked phase1-capable artifact and disposable test environment
    When launch from disposable path with spaces and non-ASCII characters
    Then normal startup and same user data root without developer checkout dependency

