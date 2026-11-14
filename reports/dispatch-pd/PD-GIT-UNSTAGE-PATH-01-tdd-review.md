# PD-GIT-UNSTAGE-PATH-01 independent TDD review (Section A)

**Verdict: TDD_PASS** (re-run after Guard scenario-id shorten; not Done / not blue)

This is independent verification only. Product code and TDD assertions were not modified. Verifier did not resume the implementer.

| Field | Value |
|---|---|
| Task | PD-GIT-UNSTAGE-PATH-01 FILE-UNSTAGE |
| Parent Story | S-GIT-WP2 |
| Product SHA | `ee3eb309d88d8f60c286b97b3db7cd378b1cab17` |
| Product branch / PR | `feature/PD-GIT-UNSTAGE-PATH-01-unstage-path` / [PR 17](https://github.com/roy791202/AIAD/pull/17) |
| Implementer | `bc-9ae9a7a1-13a0-5697-8b53-8a920c9af5ca` |
| Verifier | `bc-ec1eadff-734d-5728-a1bf-9fba29d3f770` |
| Re-run (UTC) | 2026-11-14 |
| rustc / cargo | 1.83.0 / 1.83.0 |

## Re-run counts (`ee3eb30`)

| Suite | passed | failed | ignored | Result |
|---|---:|---:|---:|---|
| `cargo test -p sgenaxis-adapters --lib s_git_wp2_fu_` | 10 | 0 | 0 | **PASS** |
| `cargo test -p sgenaxis-host --lib s_git_wp2_fu_` | 2 | 0 | 0 | **PASS** |
| `cargo test -p sgenaxis-host --lib ipc::tests` | 3 | 0 | 0 | **PASS** (still relevant: allowlist `git_write_unstage_path`) |
| `src-tauri` `cargo test --lib` | 0 | 0 | 0 | **NOT RUN** — Cargo 1.83.0, `icu_locale_core` requires `edition2024` |
| Desktop GUI E2E | 0 | 0 | 0 | **NOT RUN** |

**Executed: 15 passed, 0 failed, 0 ignored.** src-tauri/GUI not marked PASS.

Adapters (fake + StdGitWrite) named tests:

- `s_git_wp2_fu_1_grant_one_path`
- `s_git_wp2_fu_2_deny_no_mutation`
- `s_git_wp2_fu_3_conflict_operation_in_progress`
- `s_git_wp2_fu_4_path_traversal`
- `s_git_wp2_fu_5_other_files_remain_staged`

Host crate: FU-1 and FU-2 only (same as before rename).

`scenarioIds` on the Task card: `S-GIT-WP2-FU-1` .. `S-GIT-WP2-FU-5` (each **14 characters**, ≤40). Old `s_git_write_p2_file_unstage_*` names are gone from product SHA.

## Remaining Guard / `.feature` / spec-change (not TDD FAIL)

Independent TDD is Green. CI Guard is **not** Green:

1. **spec-change label missing on PR 17** (`labels: []`). Guard job `132508508522` **failure**: `修改了 BDD 情境（docs/bdd/S-GIT-WRITE-P2.feature），需要核准者加上 spec-change 標籤，並經 CODEOWNERS 審查`. `PR_LABELS` was empty. Implementer cannot add GitHub labels.
2. **`.feature` is new vs `main`**: `docs/bdd/S-GIT-WRITE-P2.feature` added (FILE-UNSTAGE scenarios). Merge of that file still needs **spec-change** + CODEOWNERS.
3. **AI Dev Guard / tests** check on `ee3eb30`: **success** (npm/UI subset on Ubuntu). **guard** check: **failure** (item 1). **rust-windows**: **in_progress** at verification time — **NOT RUN** by this verifier; do not treat as PASS.
4. Board on product SHA still records Task `ci: Red`, Story `S-GIT-WP2` yellow (`Guard/CI not Green`). Card remains In Review. Not Done/Blue.

## Verdict rationale

Renamed filters all passed independently on `ee3eb30`. Remaining blockers are process/CI (spec-change label, CODEOWNERS, rust-windows), not failing unit tests.

**TDD_PASS.** Evidence branch only; implementer branch was not force-pushed.

---

## Prior run (eadf562, superseded names)

Previous independent run used `s_git_write_p2_file_unstage_*` (10 + 2 + 3 PASS; src-tauri NOT RUN). That filter no longer exists after the Guard rename. Historical counts: adapters 10, host 2, ipc 3, executed 15/0/0.
