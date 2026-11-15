# PD-GIT-REPO-INIT-01 — Independent TDD review

**Verdict:** **TDD_PASS** (workspace adapter + host; see gaps for `src-tauri`)

**Date (UTC):** 2026-11-15  
**Verifier:** `independent-tdd-PD-GIT-REPO-INIT-01` (independent TDD agent; did **not** implement this slice)  
**Implementer (per board / dispatch):** `cursor-cloud-dev-PD-GIT-REPO-INIT-01` — **distinct** from verifier  

**Reviewed branch:** `feature/PD-GIT-REPO-INIT-01-git-init`  
**Reviewed SHA:** `7002a82293161089220f73cbeec56c2cbac0be63`  
**BDD:** `docs/bdd/PD-GIT-REPO-INIT-01.feature` — scenarios **PD-GIT-REPO-INIT-01-1 / 01-2 / 01-3**

Implementer self-marked board `tdd: Green` is **not acceptance**. This run independently re-executed focused adapter/host `init_repo` tests. Because this verifier personally saw **PASS**, board `tdd` Green is **kept**. Done / blue were **not** set.

## Commands (independent re-run)

Toolchain: `rustc 1.83.0 (90b35a623 2024-11-26)`, `cargo 1.83.0 (5ffbef321 2024-10-29)`, cwd `apps/sgenaxis-desktop` unless noted.

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| 1 | `cargo test -p sgenaxis-adapters -- init_repo --nocapture` | **0** | **7 passed**, 0 failed, 0 ignored |
| 2 | `cargo test -p sgenaxis-adapters -- pd_git_repo_init --nocapture` | **0** | **3 passed** (`pd_git_repo_init_01_{1,2,3}_*`) |
| 3 | `cargo test -p sgenaxis-host -- git_repo_init --nocapture` | **0** | **3 passed** in `git_repo_init::tests` |
| 4 | `cargo test -p sgenaxis-host --lib allowlist_contains_host_commands_only` | **0** | IPC: `git_write_repo_init` allowed; `git_init` / `git_clone` rejected |
| 5 | `cargo test -p sgenaxis-host --lib authorize_accepts_allowlisted` | **0** | `authorize("git_write_repo_init")` → `GitWriteRepoInit` |
| 6 | `cd src-tauri && cargo test --lib -- git_write_repo_init --nocapture` | **101** | Cargo 1.83 cannot parse `time-core 0.1.9` (`edition2024` required) |

## Implementer evidence (read, not trusted for pass/fail)

| Phase | Path | Verifier assessment |
|-------|------|---------------------|
| RED | `reports/dispatch-pd/PD-GIT-REPO-INIT-01-RED.txt` | **Valid RED narrative:** approved init was still a stub (no `.git` / no `last_init_repo`; existing / `--bare` / `--template` / URL not rejected). Denied paths already refused. Historical RED inspected, not independently replayed on stubs. |
| GREEN | `reports/dispatch-pd/PD-GIT-REPO-INIT-01-GREEN.txt` | Matches independent steps 1–2 (10 adapter tests). Not used as sole evidence. |
| READY | `reports/dispatch-pd/PD-GIT-REPO-INIT-01.md` | Implementer correctly flagged `src-tauri` compile gap and that their result is not acceptance. |

**RED → GREEN narrative:** Credible. RED is missing behavior (stub `init_repo`), not assertion weakening. GREEN is independently replayed on adapter + host.

## Scenario results

| Scenario | Coverage (tests this verifier ran) | Result |
|----------|--------------------------------------|--------|
| **PD-GIT-REPO-INIT-01-1** Denied approval leaves no `.git` | `pd_git_repo_init_01_1_denied_leaves_no_git`; `fake_git_write_init_repo_denied_leaves_no_git` (`PermissionDenied`, no `last_init_repo`, no remotes); `std_write_init_repo_denied_leaves_no_git` (no `.git` on disk); host `unapproved_refuses_without_mutation` | **PASS** |
| **PD-GIT-REPO-INIT-01-2** Approved `git init` creates a non-bare local repo | `pd_git_repo_init_01_2_approved_git_init_creates_non_bare_repo`; `fake_git_write_init_repo_records_non_bare_when_approved` (`last_init_repo == Some(true)`, remotes empty, push/commit 0); `std_write_init_repo_creates_non_bare_without_remote_or_clone` (`.git` is dir, `--is-bare-repository` false, empty remotes, git dir contained); host `approved_init_records_non_bare_without_remote` | **PASS** |
| **PD-GIT-REPO-INIT-01-3** Existing repo / `--bare` / `--template` / option-like / clone URL fail honestly | `pd_git_repo_init_01_3_existing_bare_template_option_paths_fail_honestly`; `fake_git_write_init_repo_rejects_existing_bare_template_and_urls`; `std_write_init_repo_rejects_existing_bare_template_and_urls` (existing unchanged; `--bare`, `--template`, `--template=/tmp/evil`, `--separate-git-dir`, HTTPS, `git@` fail); `gated_git_write_blocks_init_repo_even_when_approved`; host `existing_and_option_like_paths_fail_honestly` | **PASS** |
| Tauri IPC: allowlist + `git_write_repo_init_gated_and_allowlisted` | `src-tauri/src/commands.rs` unit test | **NOT RUN** (toolchain compile failure; **not PASS**) |

## Test inventory (focused adapter / host)

| Crate | Test | Result |
|-------|------|--------|
| `sgenaxis-adapters` | `pd_git_repo_init_01_1_denied_leaves_no_git` | PASS |
| `sgenaxis-adapters` | `pd_git_repo_init_01_2_approved_git_init_creates_non_bare_repo` | PASS |
| `sgenaxis-adapters` | `pd_git_repo_init_01_3_existing_bare_template_option_paths_fail_honestly` | PASS |
| `sgenaxis-adapters` | `fake_git_write_init_repo_denied_leaves_no_git` | PASS |
| `sgenaxis-adapters` | `fake_git_write_init_repo_records_non_bare_when_approved` | PASS |
| `sgenaxis-adapters` | `fake_git_write_init_repo_rejects_existing_bare_template_and_urls` | PASS |
| `sgenaxis-adapters` | `gated_git_write_blocks_init_repo_even_when_approved` | PASS |
| `sgenaxis-adapters` | `std_write_init_repo_denied_leaves_no_git` | PASS |
| `sgenaxis-adapters` | `std_write_init_repo_creates_non_bare_without_remote_or_clone` | PASS |
| `sgenaxis-adapters` | `std_write_init_repo_rejects_existing_bare_template_and_urls` | PASS |
| `sgenaxis-host` | `git_repo_init::tests::unapproved_refuses_without_mutation` | PASS |
| `sgenaxis-host` | `git_repo_init::tests::approved_init_records_non_bare_without_remote` | PASS |
| `sgenaxis-host` | `git_repo_init::tests::existing_and_option_like_paths_fail_honestly` | PASS |
| `sgenaxis-host` | `ipc::tests::allowlist_contains_host_commands_only` | PASS |
| `sgenaxis-host` | `ipc::tests::authorize_accepts_allowlisted` | PASS |
| `src-tauri` | `git_write_repo_init_gated_and_allowlisted` | **NOT RUN** |

No skip / ignore on these tests. Assertions were not weakened by this verifier (product tests were not modified).

## Independent stdout (lib tests only)

Adapter `init_repo` (7):

```
test tests_git02::std_write_temp::std_write_init_repo_denied_leaves_no_git ... ok
test tests_git::fake_git_write_init_repo_denied_leaves_no_git ... ok
test tests_git::fake_git_write_init_repo_records_non_bare_when_approved ... ok
test tests_git::fake_git_write_init_repo_rejects_existing_bare_template_and_urls ... ok
test tests_git::gated_git_write_blocks_init_repo_even_when_approved ... ok
test tests_git02::std_write_temp::std_write_init_repo_creates_non_bare_without_remote_or_clone ... ok
test tests_git02::std_write_temp::std_write_init_repo_rejects_existing_bare_template_and_urls ... ok
test result: ok. 7 passed; 0 failed; 0 ignored
```

Adapter `pd_git_repo_init` (3):

```
test tests_git::pd_git_repo_init_01_1_denied_leaves_no_git ... ok
test tests_git::pd_git_repo_init_01_3_existing_bare_template_option_paths_fail_honestly ... ok
test tests_git::pd_git_repo_init_01_2_approved_git_init_creates_non_bare_repo ... ok
test result: ok. 3 passed; 0 failed; 0 ignored
```

Host `git_repo_init` (3):

```
test git_repo_init::tests::existing_and_option_like_paths_fail_honestly ... ok
test git_repo_init::tests::unapproved_refuses_without_mutation ... ok
test git_repo_init::tests::approved_init_records_non_bare_without_remote ... ok
test result: ok. 3 passed; 0 failed; 0 ignored
```

`src-tauri` (NOT RUN):

```
error: failed to parse manifest at .../time-core-0.1.9/Cargo.toml
Caused by:
  feature `edition2024` is required
  The package requires the Cargo feature called `edition2024`, but that feature is not stabilized in this version of Cargo (1.83.0 ...)
```

Exit **101**. Classified **NOT RUN**, not PASS, not FAIL.

## Gaps and limits

1. **`src-tauri` / `git_write_repo_init_gated_and_allowlisted`:** **NOT RUN** on this VM (Cargo 1.83 vs crates requiring `edition2024`). Re-run required on a toolchain that matches the lockfile. Host `perform_git_repo_init` + IPC allowlist passed; that does not replace the Tauri command-module unit test.
2. **No E2E / UI manual proof** for live `REPO-INIT` invoke from `ui/app.js`.
3. **Std adapter `--template` / clone URL** cases assert honest `Err` and no remote on the seeded repo; they do not spawn `git clone`.

## Integrity checks (verifier)

- Did **not** modify product source, tests, `.feature`, or assertions.
- Did **not** skip tests.
- Did **not** set Done / blue light.
- Re-ran tests locally; did not accept implementer GREEN as sole evidence.
- Implementer `tdd: Green` was invalid until this independent PASS; Green is kept only because this verifier saw PASS.

## Outcome

**TDD_PASS** for focused adapter + host `init_repo` coverage of **PD-GIT-REPO-INIT-01-1 / 01-2 / 01-3**.

**Conditional:** Tauri-layer test `git_write_repo_init_gated_and_allowlisted` remains **NOT RUN** until a Cargo/Rust toolchain that supports `edition2024` can build `apps/sgenaxis-desktop/src-tauri`.
