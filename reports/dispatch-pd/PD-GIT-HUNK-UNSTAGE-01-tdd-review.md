# Independent TDD review — PD-GIT-HUNK-UNSTAGE-01

| Field | Value |
| --- | --- |
| Task | PD-GIT-HUNK-UNSTAGE-01 |
| Product PR | https://github.com/roy791202/AIAD/pull/14 |
| Product branch | `feature/PD-GIT-HUNK-UNSTAGE-01-hunk-unstage` @ `9729588322f460d27f06821c7cd1d79b2d6e8e01` |
| Evidence branch | `feature/PD-GIT-HUNK-UNSTAGE-01-tdd-review` (this file only; product PR not merged, not force-pushed) |
| Verifier | `bc-6fa151db-2c40-57d6-9a08-2083fc7126b0` (`verifier`, skill section A only) |
| Developer | Prior implementer title **Implement gated HUNK-UNSTAGE**; product PR body cites implementer `bc-924d2778` and a prior TDD note `bc-c8782bb0` **without an evidence PR**. This Gate is a fresh independent re-run, not self-accept. |
| Role | Independent TDD verifier. Did **not** modify product code or TDD assertions. |
| Platform | Linux; `rustc 1.83.0 (90b35a623 2024-11-26)`; `cargo 1.83.0 (5ffbef321 2024-10-29)` |
| Date | 2026-11-14T17:20:00Z |
| Board | Card stays **In Review**. **Not Done / not Blue.** This agent does not set Done/Blue. |

## Verdict

**TDD_PASS** for independently re-run **HUNK-UNSTAGE** automation on product SHA `9729588`.

**NOT RUN (not PASS):** `src-tauri` lib tests (`edition2024` required; Cargo 1.83.0 cannot parse `idna_adapter` manifest). Desktop UI E2E / screenshots / recording: **NOT RUN** (no Tauri window).

## API overlap (SPEC finding — not a test FAIL)

Do **not** merge PR 5 and PR 14 together as-is. Signatures conflict:

| PR | Method | Hunk identity |
| --- | --- | --- |
| [PR 5](https://github.com/roy791202/AIAD/pull/5) HUNK-STAGE (+ unstage on same HEAD) | `GitWritePort::unstage_hunk(path, old_start: u32)` | numeric old-start |
| [PR 14](https://github.com/roy791202/AIAD/pull/14) HUNK-UNSTAGE | `GitWritePort::hunk_unstage(path, hunk_spec: &str)` | text hunk spec (`@@ … @@`) |

This Gate does **not** accept or merge either product PR. Memory prefers PR 5’s `unstage_hunk` if STAGE-01 lands first; high-tier must resolve the Port contract. Recorded here so it is not lost.

## Commands (verifier-run on `9729588`; not author-reported)

Cwd: `apps/sgenaxis-desktop`.

```
cargo test -p sgenaxis-adapters --lib pd_git_hunk_unstage -- --nocapture
# 3 passed; 0 failed; 0 ignored; 191 filtered out
#   tests_git::pd_git_hunk_unstage_01_gated_git_write_blocks_even_when_approved ... ok
#   tests_git::pd_git_hunk_unstage_01_fake_git_write_records_when_approved ... ok
#   tests_git02::std_write_temp::pd_git_hunk_unstage_01_std_write_unstages_one_hunk_only ... ok

cargo test -p sgenaxis-host --lib pd_git_hunk_unstage -- --nocapture
# 3 passed; 0 failed; 0 ignored; 106 filtered out
#   git_hunk_unstage::tests::pd_git_hunk_unstage_01_unapproved_refuses_without_mutation ... ok
#   git_hunk_unstage::tests::pd_git_hunk_unstage_01_in_progress_conflict_fails_honestly ... ok
#   git_hunk_unstage::tests::pd_git_hunk_unstage_01_approved_unstages_only_specified_hunk ... ok

cargo test -p sgenaxis-host --lib ipc::tests -- --nocapture
# 3 passed; 0 failed; 0 ignored; 106 filtered out
#   allowlist_contains_host_commands_only ... ok  (includes git_write_hunk_unstage)
#   authorize_rejects_arbitrary_shell ... ok
#   authorize_accepts_allowlisted ... ok

cargo test --manifest-path src-tauri/Cargo.toml --lib pd_git_hunk_unstage -- --nocapture
# NOT RUN / failed to parse dependency manifest
# feature `edition2024` is required
# Cargo 1.83.0 (5ffbef321 2024-10-29)
```

## Counts

| Suite | Filter | Passed | Failed | Ignored | Status |
| --- | ---: | ---: | ---: | --- | --- |
| adapters | `pd_git_hunk_unstage` | 3 | 0 | 0 | **PASS** |
| host | `pd_git_hunk_unstage` | 3 | 0 | 0 | **PASS** |
| host | `ipc::tests` | 3 | 0 | 0 | **PASS** (allowlist `git_write_hunk_unstage`) |
| **Executed automated** | | **9** | 0 | 0 | **PASS** |
| src-tauri | `pd_git_hunk_unstage` | — | — | — | **NOT RUN** (edition2024 / Cargo 1.83) |
| UI E2E / screenshots | HUNK-UNSTAGE modal | — | — | — | **NOT RUN** (no desktop GUI) |

## Scenario checklist (section A)

| Check | Expected | Result |
| --- | --- | --- |
| Approval deny | no index mutation; `PermissionDenied` | **PASS** (fake + host `unapproved_refuses_without_mutation`) |
| `OPERATION_IN_PROGRESS` | honest Git error; no last_hunk_unstage | **PASS** (fake + host `in_progress_conflict`; std temp repo in adapters test) |
| No `--hard` / `-f` / `--force` | `git apply --cached -R --` only | **PASS** (read `StdGitWrite::hunk_unstage`; comments + argv; no `--hard`/`-f` in this method) |
| Path / hunk-spec guards | empty, newline, NUL, path escape, flag-like spec, binary, missing, not-in-index | **PASS** (`require_hunk_path` / `require_hunk_spec`; fake + std tests) |
| Gated adapter | deny even if approval granted | **PASS** (`gated_git_write_blocks_even_when_approved`) |
| Host approved path | only specified hunk recorded | **PASS** |
| FILE-STAGE / FILE-UNSTAGE / FILE-DISCARD creep | PR 14 must not land those slices | **PASS** as product-file review: new host module is `git_hunk_unstage.rs`; Port method is `hunk_unstage`; IPC `git_write_hunk_unstage`. Extra PR files are `docs/board.json` + unrelated M06 `cx-preflight-revision-v3-review` HTML/JSON — not FILE-STAGE/UNSTAGE/DISCARD adapters. FILE-UNSTAGE lives on PR 17, not this SHA’s hunk tests. |
| src-tauri command | gated + allowlisted | **NOT RUN** |
| UI HUNK-UNSTAGE + approval modal | click, confirm, toast | **NOT RUN** |

No FAIL on tests that executed. Verifier added no skip/ignore.

## UI / interface (section A steps 2–3)

Mock/UI still lists `HUNK-UNSTAGE` in `apps/sgenaxis-desktop/ui/git-ux-mock.js`. This environment has no Tauri WebView. **NOT RUN**. Not recorded as PASS.

## Product files not touched

Verifier did not edit ports, adapters, host, src-tauri, UI, tests, `.feature`, or `docs/board.json`. Evidence file only. Product branch was not force-pushed. Product PRs 5 and 14 were **not** merged.
