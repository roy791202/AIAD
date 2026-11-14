# PD-GIT-UNSTAGE-PATH-01 independent TDD review (Section A)

**Verdict: TDD_PASS**

This is independent verification only. Product code and TDD assertions were not modified. Card was not moved to Done / blue.

| Field | Value |
|---|---|
| Task | PD-GIT-UNSTAGE-PATH-01 FILE-UNSTAGE: gated `GitWritePort::unstage_path` |
| Parent | PD-GIT-02 |
| Product commit | `eadf562f78d88e9288b7d377b4ca398c60a86353` on `feature/PD-GIT-UNSTAGE-PATH-01-unstage-path` |
| Implementer | `bc-9ae9a7a1-13a0-5697-8b53-8a920c9af5ca` |
| Verifier | `bc-ec1eadff-734d-5728-a1bf-9fba29d3f770` |
| Date (UTC) | 2026-11-14 |
| Platform | Linux x86_64 (cloud agent) |
| rustc | 1.83.0 (90b35a623 2024-11-26) |
| cargo | 1.83.0 (5ffbef321 2024-10-29) |
| Default toolchain | 1.83.0-x86_64-unknown-linux-gnu |

Verifier ≠ implementer. This run did not resume the implementer session.

## Scope

BDD: `docs/bdd/S-GIT-WRITE-P2.feature` (FILE-UNSTAGE). Scenarios:

- `s_git_write_p2_file_unstage_grant_one_path`
- `s_git_write_p2_file_unstage_deny_no_mutation`
- `s_git_write_p2_file_unstage_conflict_operation_in_progress`
- `s_git_write_p2_file_unstage_path_traversal`
- `s_git_write_p2_file_unstage_other_files_remain_staged`

Independent re-run was performed against product commit `eadf562` (cwd `apps/sgenaxis-desktop`). This evidence branch is from `main` and contains only this report.

## Automated TDD (re-run)

### 1. `cargo test -p sgenaxis-adapters --lib s_git_write_p2_file_unstage_`

**PASS** — exit 0.

```
running 10 tests
test tests_git02::std_write_temp::s_git_write_p2_file_unstage_deny_no_mutation ... ok
test tests_git02::std_write_temp::s_git_write_p2_file_unstage_conflict_operation_in_progress ... ok
test tests_git::s_git_write_p2_file_unstage_conflict_operation_in_progress ... ok
test tests_git::s_git_write_p2_file_unstage_deny_no_mutation ... ok
test tests_git::s_git_write_p2_file_unstage_grant_one_path ... ok
test tests_git::s_git_write_p2_file_unstage_other_files_remain_staged ... ok
test tests_git::s_git_write_p2_file_unstage_path_traversal ... ok
test tests_git02::std_write_temp::s_git_write_p2_file_unstage_grant_one_path ... ok
test tests_git02::std_write_temp::s_git_write_p2_file_unstage_other_files_remain_staged ... ok
test tests_git02::std_write_temp::s_git_write_p2_file_unstage_path_traversal ... ok

test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 192 filtered out
```

Fake (`tests_git`) and StdGitWrite temp-repo (`tests_git02`) each cover all five scenario IDs.

### 2. `cargo test -p sgenaxis-host --lib s_git_write_p2_file_unstage_`

**PASS** — exit 0.

```
running 2 tests
test git_unstage_path::tests::s_git_write_p2_file_unstage_grant_one_path ... ok
test git_unstage_path::tests::s_git_write_p2_file_unstage_deny_no_mutation ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 106 filtered out
```

Host crate only names grant + deny. Conflict, traversal, and other-files remain covered by adapters (fake + std).

### 3. `cargo test -p sgenaxis-host --lib ipc::tests`

**PASS** — exit 0.

```
running 3 tests
test ipc::tests::authorize_rejects_arbitrary_shell ... ok
test ipc::tests::allowlist_contains_host_commands_only ... ok
test ipc::tests::authorize_accepts_allowlisted ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 105 filtered out
```

Allowlist includes `git_write_unstage_path` and rejects `git_unstage_path`.

### 4. `apps/sgenaxis-desktop/src-tauri` `cargo test --lib`

**NOT RUN** — not PASS.

Toolchain/edition mismatch: Cargo 1.83.0 cannot parse a Tauri dependency that requires unstable `edition2024`.

```
error: failed to parse manifest at
  /usr/local/cargo/registry/src/index.crates.io-6f17d22bba15001f/icu_locale_core-2.4.0/Cargo.toml

Caused by:
  feature `edition2024` is required

  The package requires the Cargo feature called `edition2024`, but that feature is
  not stabilized in this version of Cargo (1.83.0 (5ffbef321 2024-10-29)).
```

No src-tauri tests executed. Result is **NOT RUN**, not a product test failure.

## Scenario checklist (observable behavior vs BDD)

| Scenario | Fake adapters | StdGitWrite adapters | Host | UI / Tauri | Result |
|---|---|---|---|---|---|
| grant_one_path | PASS | PASS | PASS | NOT RUN | PASS (lib) |
| deny_no_mutation | PASS | PASS | PASS | NOT RUN | PASS (lib) |
| conflict OPERATION_IN_PROGRESS | PASS | PASS | n/a (no host test name) | NOT RUN | PASS (lib) |
| path_traversal | PASS | PASS | n/a | NOT RUN | PASS (lib) |
| other_files_remain_staged | PASS | PASS | n/a | NOT RUN | PASS (lib) |

## Interface / GUI

Desktop UI and Tauri command surface were **not** exercised with screenshots or recording: src-tauri cannot compile on this toolchain (`edition2024`). Recorded **NOT RUN**, not PASS.

Linux-only this run. Windows / macOS **NOT RUN**.

## Counts

| Suite | passed | failed | ignored | NOT RUN |
|---|---:|---:|---:|---|
| sgenaxis-adapters `s_git_write_p2_file_unstage_` | 10 | 0 | 0 | — |
| sgenaxis-host `s_git_write_p2_file_unstage_` | 2 | 0 | 0 | — |
| sgenaxis-host `ipc::tests` | 3 | 0 | 0 | — |
| src-tauri `--lib` | 0 | 0 | 0 | edition2024 / rustc 1.83.0 |
| Desktop GUI E2E | 0 | 0 | 0 | no runnable Tauri host |
| **Total executed** | **15** | **0** | **0** | src-tauri + GUI |

## Verdict rationale

All independently re-run, executable TDD filters for this task passed (15/15, 0 failed, 0 ignored). src-tauri and GUI are documented NOT RUN because of Cargo `edition2024` vs rustc/cargo 1.83.0. That absence is not treated as PASS.

**TDD_PASS.** Not Done. Not blue. Product PR remains the orchestrator's job against `main`. Implementer branch was not force-pushed.

Evidence path: `reports/dispatch-pd/PD-GIT-UNSTAGE-PATH-01-tdd-review.md` on `feature/PD-GIT-UNSTAGE-PATH-01-tdd-review`.
