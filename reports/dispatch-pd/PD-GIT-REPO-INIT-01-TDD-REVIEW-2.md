# PD-GIT-REPO-INIT-01 independent TDD re-run (after host.toml follow-up)

**Verdict: TDD_PASS**

Date: 2026-11-15T11:05:00+08:00  
Reviewed HEAD: `28ce7b6cc7a8ec9ba86632fc8a9230b35161ffed` (`docs(board): yellow light and PR #90 for PD-GIT-REPO-INIT-01`)  
Branch under test: `feature/PD-GIT-REPO-INIT-01-git-init`  
Implementation PR: [#90](https://github.com/roy791202/AIAD/pull/90)

This is a **second** independent TDD Gate. It does **not** reuse `docs/PD-GIT-REPO-INIT-01-tdd-review` (HEAD `d1e07c4`, reviewed SHA `7002a82`) which ran **before** `allow-git-repo-init` was added to `host.toml` / `host-default`.

| Role | Identity |
|---|---|
| Original implementer (not this agent) | `cursor-cloud-dev-PD-GIT-REPO-INIT-01` |
| ACL follow-up implementer (not this agent) | `cursor-cloud-dev-PD-GIT-REPO-INIT-01` (`7b5a6d8` host.toml allowlist) |
| Prior TDD verifier (not this agent) | `independent-tdd-PD-GIT-REPO-INIT-01` (`docs/PD-GIT-REPO-INIT-01-tdd-review`, pre-follow-up) |
| Prior high-tier reviewer (not this agent) | `cursor-cloud-high-tier-PD-GIT-REPO-INIT-01` (CHANGES_REQUIRED on PR #90) |
| Independent TDD verifier (this agent) | `cursor-cloud-tdd-PD-GIT-REPO-INIT-01-rerun-2` |

The implementer's `READY_FOR_TDD`, the follow-up agent's "still Green" / yellow-until-re-review claim, the prior TDD_PASS on `7002a82` / `d1e07c4`, and the high-tier CHANGES_REQUIRED on missing ACL were **not trusted** as pass/fail. This agent re-ran the focused adapter and host `init_repo` tests on the post-follow-up tree and independently confirmed `allow-git-repo-init` is in `host-default`. Product code, assertions, fixtures, expected values, `.feature` files, and skip/ignore flags were not modified. Status stays **In Review**. Not Done / not blue.

Follow-up commits included in this re-run:

- `7b5a6d8` `fix(git): allowlist git_write_repo_init in host.toml`
- `28ce7b6` `docs(board): yellow light and PR #90 for PD-GIT-REPO-INIT-01`

Original implementation still in tree: `7002a82` `feat(git): gated local git init via GitWritePort`.

## Commands (cwd `apps/sgenaxis-desktop`)

```
cargo test -p sgenaxis-adapters -- init_repo --nocapture
cargo test -p sgenaxis-adapters -- pd_git_repo_init --nocapture
cargo test -p sgenaxis-host -- git_repo_init --nocapture
cargo test -p sgenaxis-host --lib allowlist_contains_host_commands_only -- --nocapture
cargo test -p sgenaxis-host --lib authorize_accepts_allowlisted -- --nocapture
```

Environment: Linux 6.12, cargo 1.83.0, rustc 1.83.0, git 2.43.0. HEAD `28ce7b6cc7a8ec9ba86632fc8a9230b35161ffed`.

## Counts (this agent, this run)

| Suite | Filter | Result |
|---|---|---|
| `sgenaxis-adapters` lib | `init_repo` | **7 passed; 0 failed; 0 ignored; 0 measured; 194 filtered out** |
| `sgenaxis-adapters` lib | `pd_git_repo_init` | **3 passed; 0 failed; 0 ignored; 0 measured; 198 filtered out** |
| `sgenaxis-host` lib | `git_repo_init` | **3 passed; 0 failed; 0 ignored; 0 measured; 106 filtered out** |
| `sgenaxis-host` lib | `allowlist_contains_host_commands_only` | **1 passed; 0 failed; 0 ignored** |
| `sgenaxis-host` lib | `authorize_accepts_allowlisted` | **1 passed; 0 failed; 0 ignored** |
| `sgenaxis-desktop` src-tauri `--lib git_write_repo_init` | focused Tauri command | **NOT RUN** — Cargo 1.83 cannot parse `time-core 0.1.9` (`edition2024` required); exit 101 |
| UI / E2E / screenshots | live REPO-INIT | **NOT RUN** — no desktop GUI in this environment |

Adapter tests that ran (`init_repo` + `pd_git_repo_init`):

- `tests_git::fake_git_write_init_repo_denied_leaves_no_git` … ok
- `tests_git::fake_git_write_init_repo_records_non_bare_when_approved` … ok
- `tests_git::fake_git_write_init_repo_rejects_existing_bare_template_and_urls` … ok
- `tests_git::gated_git_write_blocks_init_repo_even_when_approved` … ok
- `tests_git::pd_git_repo_init_01_1_denied_leaves_no_git` … ok
- `tests_git::pd_git_repo_init_01_2_approved_git_init_creates_non_bare_repo` … ok
- `tests_git::pd_git_repo_init_01_3_existing_bare_template_option_paths_fail_honestly` … ok
- `tests_git02::std_write_temp::std_write_init_repo_denied_leaves_no_git` … ok
- `tests_git02::std_write_temp::std_write_init_repo_creates_non_bare_without_remote_or_clone` … ok
- `tests_git02::std_write_temp::std_write_init_repo_rejects_existing_bare_template_and_urls` … ok

Host tests that ran:

- `git_repo_init::tests::unapproved_refuses_without_mutation` … ok
- `git_repo_init::tests::approved_init_records_non_bare_without_remote` … ok
- `git_repo_init::tests::existing_and_option_like_paths_fail_honestly` … ok
- `ipc::tests::allowlist_contains_host_commands_only` … ok
- `ipc::tests::authorize_accepts_allowlisted` … ok

Raw adapter `init_repo` result line:

```
test result: ok. 7 passed; 0 failed; 0 ignored; 0 measured; 194 filtered out; finished in 0.02s
```

Raw adapter `pd_git_repo_init` result line:

```
test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 198 filtered out; finished in 0.01s
```

Raw host `git_repo_init` result line:

```
test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 106 filtered out; finished in 0.00s
```

No `#[ignore]`, skip, or `#[cfg(not(...))]` was observed on these focused tests. Assertions were not weakened in this session (verifier does not edit tests).

## Follow-up checks required by high-tier CHANGES_REQUIRED

### `host.toml` `allow-git-repo-init` in `host-default`

**HOLD.** File: `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` at HEAD `28ce7b6`.

- Permission identifier `allow-git-repo-init` exists (line 129).
- `commands.allow = ["git_write_repo_init"]` (line 131).
- `[[set]] identifier = "host-default"` permissions list **includes** `"allow-git-repo-init"` (line 217, between `allow-git-unstage-all` and `allow-git-fetch-prune`).
- `apps/sgenaxis-desktop/src-tauri/capabilities/default.json` grants `host-default` (line 14), so the live capability set includes this permission atom.
- Host crate `is_allowed("git_write_repo_init")` is asserted true and `is_allowed("git_init")` / `is_allowed("git_clone")` are asserted false; `authorize_accepts_allowlisted` maps `git_write_repo_init` → `AllowedIpcCommand::GitWriteRepoInit` and passed on this run.
- Follow-up diff `7b5a6d8` is **only** this six-line `host.toml` addition. No test assertions, fixtures, or `.feature` files were changed by the ACL follow-up.

## Scenarios vs independent run

BDD source: `docs/bdd/PD-GIT-REPO-INIT-01.feature`.

| ID | Scenario | Holds? | Evidence from this run |
|---|---|---|---|
| **PD-GIT-REPO-INIT-01-1** | Denied approval leaves no `.git` | **HOLD** | Fake: `PermissionDenied`, `last_init_repo` none, remotes empty, push 0. Std: no `.git` on disk. Host: `unapproved_refuses_without_mutation` ok. Named test `pd_git_repo_init_01_1_denied_leaves_no_git` ok. |
| **PD-GIT-REPO-INIT-01-2** | Approved `git init` creates a non-bare local repo; no remote / clone | **HOLD** | Fake: `last_init_repo == Some(true)`, remotes empty, push/commit 0. Std: `.git` is a directory inside the chosen dir, `--is-bare-repository` false, `git remote` empty, absolute git-dir contained. Host: `approved_init_records_non_bare_without_remote` ok. Named test `pd_git_repo_init_01_2_approved_git_init_creates_non_bare_repo` ok. |
| **PD-GIT-REPO-INIT-01-3** | Existing repo, `--bare`, `--template`, option-like paths, clone URLs fail honestly | **HOLD** | Fake + Std refuse existing re-init (existing git-dir unchanged on Std); `--bare` / `--template` / `--template=/tmp/evil` / `--separate-git-dir` / HTTPS / `git@` fail without recording init. Fake also refuses `-C`. Host: `existing_and_option_like_paths_fail_honestly` ok. `gated_git_write_blocks_init_repo_even_when_approved` ok. Named test `pd_git_repo_init_01_3_existing_bare_template_option_paths_fail_honestly` ok. |

Extra coverage (not numbered BDD IDs, still Green here): `GatedGitWrite` denies even when approved; host IPC allowlist accepts `git_write_repo_init` and rejects `git_init` / `git_clone`.

## Limits

- Historical RED (test-first failure before implementation) was **not independently replayed**. This review is a current Green re-run only. Implementer RED at `reports/dispatch-pd/PD-GIT-REPO-INIT-01-RED.txt` was inspected as narrative, not re-executed on stubs.
- src-tauri command test `git_write_repo_init_gated_and_allowlisted` is **NOT RUN** (Cargo 1.83 vs `edition2024`). Host crate already covers denied / approved / existing / option-like paths; that does not replace the Tauri command-module unit test.
- Desktop REPO-INIT click-path, screenshots, and recording are **NOT RUN**.
- CI on PR #90 HEAD `28ce7b6` at review time: Ubuntu `tests` success, `lint + test subset` success, `guard` **failure**, `rust-windows` in progress. This agent did **not** claim CI Green and did not treat Guard/Windows as this slice's TDD Red.
- High-tier re-review after the follow-up is **out of scope** for this TDD Gate.

## Integrity checks (verifier)

- Did **not** modify product source, tests, `.feature`, or assertions.
- Did **not** skip tests.
- Did **not** set Done / blue light.
- Re-ran tests locally on `28ce7b6`; did not accept implementer GREEN or prior TDD_PASS as sole evidence.
- Distinct from original implementer, ACL follow-up implementer, prior TDD verifier, and prior high-tier reviewer.

## Board

Task `PD-GIT-REPO-INIT-01` stays **In Review**, light **Yellow** (`lightReason`: independent TDD re-run after `host.toml` `allow-git-repo-init` is Green; high-tier re-review still pending because review returned once), `tdd` **Green** because this verifier personally saw PASS on the focused adapter + host suites for 01-1 / 01-2 / 01-3 **and** confirmed `allow-git-repo-init` in `host-default`. Not Done. Not blue.

## Outcome

**TDD_PASS** for focused adapter + host `init_repo` coverage of **PD-GIT-REPO-INIT-01-1 / 01-2 / 01-3**, including the post-CHANGES_REQUIRED `allow-git-repo-init` membership in `host-default`.

**Conditional:** Tauri-layer test `git_write_repo_init_gated_and_allowlisted` remains **NOT RUN** until a Cargo/Rust toolchain that supports `edition2024` can build `apps/sgenaxis-desktop/src-tauri`.
