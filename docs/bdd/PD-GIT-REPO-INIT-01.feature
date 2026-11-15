Feature: Gated local git init (PD-GIT-REPO-INIT-01)
  GitWritePort.init_repo creates a non-bare repository inside a chosen
  empty directory after explicit approval. Denied writes leave no .git.
  Existing repos, --bare, --template, option-like paths, and clone URLs
  fail honestly. Never git clone, never add a remote, never fetch.

  @PD-GIT-REPO-INIT-01-1
  Scenario: Denied approval leaves no .git
    Given an empty chosen directory that is not a git repository
    And git write approval is denied
    When init_repo is invoked on that directory
    Then the command fails with permission denied
    And the directory still has no .git
    And no remote is added
    And git clone is not used

  @PD-GIT-REPO-INIT-01-2
  Scenario: Approved git init creates a non-bare local repository
    Given an empty chosen directory that is not a git repository
    And git write approval is granted
    When init_repo is invoked on that directory
    Then a non-bare git repository exists inside that directory
    And no remote is configured
    And git clone is not used
    And git files stay inside the chosen directory

  @PD-GIT-REPO-INIT-01-3
  Scenario: Existing repo, --bare, --template, and option-like paths fail honestly
    Given a directory that is already a git repository
    Or a path that looks like --bare, --template, a clone URL, or another git option
    And git write approval is granted
    When init_repo is invoked
    Then the command fails honestly without cloning
    And no --bare or untrusted --template repository is created
    And an existing repository is left unchanged
