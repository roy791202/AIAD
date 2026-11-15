# PD-GIT-MERGE-FF-01 — Independent TDD review 2 (after `allow-git-merge-ff`)

**Verdict:** **TDD_PASS** (workspace crates; Tauri `host.toml` ACL **confirmed**; `src-tauri` `--lib` is **NOT RUN**, not PASS)

**Date (UTC):** 2026-11-15T02:43:49Z  
**Verifier:** `independent-tdd-2-PD-GIT-MERGE-FF-01` (second independent TDD agent; did **not** implement this slice; did **not** add the ACL; is **not** `independent-tdd-PD-GIT-MERGE-FF-01` or `independent-high-tier-PD-GIT-MERGE-FF-01`)  
**Implementer (per board):** `cursor-cloud-dev-PD-GIT-MERGE-FF-01` — **distinct** from this verifier  
**ACL follow-up (per board / `6a5ebd1`):** same implementer identity — **distinct** from this verifier  
**Prior TDD:** `independent-tdd-PD-GIT-MERGE-FF-01` @ `docs/PD-GIT-MERGE-FF-01-tdd-review` — **not reused**; tests were re-run here  
**Prior high-tier:** `independent-high-tier-PD-GIT-MERGE-FF-01` — CHANGES_REQUIRED for missing `host.toml` ACL; this re-run is **after** that fix

**Reviewed branch:** `feature/PD-GIT-MERGE-FF-01-merge-ff-only`  
**Reviewed SHA:** `2e19aceb04b0352baaa3d8de83aee6e1d11168fd` (HEAD while tests ran)  
**ACL commit:** `6a5ebd1ad0b6a1451da2cabde642dc9eb270ec6b` `feat(git): add allow-git-merge-ff Tauri capability`  
**PR:** https://github.com/roy791202/AIAD/pull/91  
**BDD:** `docs/bdd/PD-GIT-MERGE-FF-01.feature` — scenarios `PD-GIT-MERGE-FF-01-1` / `01-2` / `01-3`

Implementer TDD Green on the board, prior TDD-REVIEW-1, and high-tier notes are **not accepted** as this run’s evidence. This file records an independent re-run on the post-ACL tree.

This verifier did **not** set Done / blue.

## Why this re-run

High-tier CHANGES_REQUIRED on PR #91 head `1f4c64b`: `permissions/host.toml` had `allow-git-pull-ff` but **no** `allow-git-merge-ff`, so `invoke("git_write_merge_ff_only")` would fail at the Tauri capability layer.

Follow-up `6a5ebd1` added the permission atom and listed it in `host-default`. This agent re-ran the dispatch TDD filters on that tree and **confirmed** the ACL in source (not by trusting the implementer note).

## `host.toml` / `host-default` (confirmed)

File: `apps/sgenaxis-desktop/src-tauri/permissions/host.toml`  
SHA-256 of file at reviewed HEAD: `e7e5088a26316dfee57d7714bd3f240ca70c9ea4b486d1654a3118bcb6c63ba5`

Permission atom (lines 138–141):

```
[[permission]]
identifier = "allow-git-merge-ff"
description = "Approval-gated git merge --ff-only -- local-branch via GitWritePort (never --no-ff/-X/--squash/pull/rebase/push; diverged/missing/remote-tracking fail honestly)"
commands.allow = ["git_write_merge_ff_only"]
```

`[[set]] identifier = "host-default"` permissions list includes `"allow-git-merge-ff"` immediately after `"allow-git-pull-ff"` (line 219).

`apps/sgenaxis-desktop/src-tauri/capabilities/default.json` grants `"host-default"` (line 14).

**ACL result:** **CONFIRMED** — `allow-git-merge-ff` is present, allows `git_write_merge_ff_only`, and is a member of `host-default`. This was the high-tier must-fix. This TDD agent does not re-score high-tier PASS/FAIL; it only records that the ACL is in the tree that was tested.

## Commands (independent re-run)

Toolchain: `rustc 1.83.0 (90b35a623 2024-11-26)`, `cargo 1.83.0 (5ffbef321 2024-10-29)`, `git 2.43.0`.  
Cwd unless noted: `apps/sgenaxis-desktop`.

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| 1 | `cargo test -p sgenaxis-adapters --lib merge_ff_only` | **0** | **2 passed**, 0 failed, 0 ignored |
| 2 | `cargo test -p sgenaxis-host --lib git_merge::` | **0** | **4 passed**, 0 failed, 0 ignored |
| 3 | `cargo test -p sgenaxis-host --lib ipc::tests` | **0** | **3 passed**, 0 failed, 0 ignored (allowlist / authorize for `git_write_merge_ff_only`) |
| 4 | `cd src-tauri && cargo test --lib git_write_merge_ff_only` | **101** (manifest parse) | Cargo **1.83.0** cannot parse `time-core-0.1.9` (`edition2024`). **NOT RUN**, not PASS |
| extra | `cargo test -p sgenaxis-adapters --lib gated_git_write_blocks_fetch_even_when_approved` | **0** | **1 passed** — Gated adapter still denies `merge_ff_only` even when approval is granted |

### Step 1 output (adapters)

```
running 2 tests
test tests_git::fake_git_write_merge_ff_only_denied_diverged_flags_and_ff_success ... ok
test tests_git02::std_write_temp::std_write_merge_ff_only_moves_head_or_refuses_diverged_flags_and_missing ... ok

test result: ok. 2 passed; 0 failed; 0 ignored; 0 measured; 191 filtered out; finished in 0.09s
```

Finished with 1 `dead_code` warning in `conpty_fixture.rs` (`PipeApiError::Unsupported`) — pre-existing, not this slice.

### Step 2 output (host git_merge)

```
running 4 tests
test git_merge::tests::occupying_run_refuses_merge_and_does_not_call_git_write ... ok
test git_merge::tests::unapproved_and_empty_refuse_without_mutation ... ok
test git_merge::tests::approved_merge_succeeds_without_occupying_run ... ok
test git_merge::tests::merge_succeeds_again_after_occupying_run_cleared ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured; 106 filtered out; finished in 0.00s
```

### Step 3 output (host ipc::tests)

```
running 3 tests
test ipc::tests::authorize_rejects_arbitrary_shell ... ok
test ipc::tests::allowlist_contains_host_commands_only ... ok
test ipc::tests::authorize_accepts_allowlisted ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 107 filtered out; finished in 0.00s
```

Relevant assertions in those three tests (verified by reading the source, then re-running):

- `is_allowed("git_write_merge_ff_only")` is true
- `is_allowed("git_merge")` and `is_allowed("git_merge_ff_only")` are false
- `authorize("git_write_merge_ff_only")` → `AllowedIpcCommand::GitWriteMergeFfOnly`
- `authorize("git_merge")` and `authorize("git_merge_ff_only")` are errors

### Step 4 output (src-tauri) — NOT RUN

```
error: failed to parse manifest at `/usr/local/cargo/registry/src/index.crates.io-6f17d22bba15001f/time-core-0.1.9/Cargo.toml`

Caused by:
  feature `edition2024` is required

  The package requires the Cargo feature called `edition2024`, but that feature is not stabilized in this version of Cargo (1.83.0 (5ffbef321 2024-10-29)).
```

`git_write_merge_ff_only_gated_and_allowlisted` in `src-tauri/src/commands.rs` was **not executed**. That is **NOT RUN**, not PASS.

### Extra (gated default-deny)

```
running 1 test
test tests_git::gated_git_write_blocks_fetch_even_when_approved ... ok

test result: ok. 1 passed; 0 failed; 0 ignored; 0 measured; 192 filtered out; finished in 0.00s
```

## Scenario results

| Scenario | Result | Coverage used for this verdict |
|----------|--------|--------------------------------|
| **PD-GIT-MERGE-FF-01-1** Denied approval does not merge | **TDD_PASS** | Fake: `merge_ff_only(..., denied)` errors; `last_merge_ff_only` none; HEAD unchanged; no pull/fetch/push. Std: denied leaves `rev-parse HEAD` unchanged and parent count &lt; 2. Host: `unapproved_and_empty_refuse_without_mutation` does not call GitWritePort. |
| **PD-GIT-MERGE-FF-01-2** Approved `git merge --ff-only -- &lt;local-branch&gt;` moves HEAD | **TDD_PASS** | Std: real `git init` fixture; approved merge moves HEAD to topic tip; parent count &lt; 2 (no merge commit); worktree content is topic tip. Fake: HEAD changes; `last_merge_ff_only` is `topic`; no fetch/pull/push. Host: `approved_merge_succeeds_without_occupying_run`. Std argv in source is `["merge", "--ff-only", "--", name]`. |
| **PD-GIT-MERGE-FF-01-3** Diverged, flags, missing names, remote-tracking, occupying Run | **TDD_PASS** | Fake+Std: `--no-ff` / `-X` error without merging; missing name errors honestly; diverged refuses and HEAD unchanged; remote-tracking name refuses without fetch. Host: occupying Run returns `活動租約禁止合併` and does **not** call GitWritePort; merge succeeds after lease cleared. IPC: raw `git_merge` / `git_merge_ff_only` names stay off the allowlist. |

## Test inventory (dispatch filters)

| Crate | Test | Result |
|-------|------|--------|
| `sgenaxis-adapters` | `fake_git_write_merge_ff_only_denied_diverged_flags_and_ff_success` | PASS |
| `sgenaxis-adapters` | `std_write_merge_ff_only_moves_head_or_refuses_diverged_flags_and_missing` | PASS |
| `sgenaxis-host` | `git_merge::tests::approved_merge_succeeds_without_occupying_run` | PASS |
| `sgenaxis-host` | `git_merge::tests::occupying_run_refuses_merge_and_does_not_call_git_write` | PASS |
| `sgenaxis-host` | `git_merge::tests::merge_succeeds_again_after_occupying_run_cleared` | PASS |
| `sgenaxis-host` | `git_merge::tests::unapproved_and_empty_refuse_without_mutation` | PASS |
| `sgenaxis-host` | `ipc::tests::allowlist_contains_host_commands_only` | PASS |
| `sgenaxis-host` | `ipc::tests::authorize_rejects_arbitrary_shell` | PASS |
| `sgenaxis-host` | `ipc::tests::authorize_accepts_allowlisted` | PASS |
| `sgenaxis-adapters` | `gated_git_write_blocks_fetch_even_when_approved` (extra) | PASS |
| `sgenaxis-desktop` (src-tauri) | `git_write_merge_ff_only_gated_and_allowlisted` | **NOT RUN** (edition2024) |

No `#[ignore]` / skip on these tests. Assertions were not weakened by this verifier (product/TDD sources were not modified).

## Integrity checks (verifier)

- Did **not** modify product source, tests, `.feature`, hooks, CI, or `docs/board.json`.
- Did **not** set Done / blue light on the board.
- Did **not** treat implementer GREEN or TDD-REVIEW-1 as pass evidence.
- Identity is distinct from implementer, ACL follow-up, prior TDD, and prior high-tier.
- Feat `a79f59b` still lands tests and implementation together; there is **no checked-in RED log**. Process gap, not a failing scenario on this re-run.

## CI at reviewed SHA (observation, not this TDD filter)

GitHub Actions on `2e19ace` (PR #91 head while this ran):

| Check | Conclusion |
|-------|------------|
| `tests` | success |
| `lint + test subset` | success |
| `guard` | failure (new `.feature` / spec-change; not a cargo-test fail) |
| `rust-windows` | failure (prior high-tier: unrelated `tests_git02::std_write_temp` remote/conflict; not scored as this slice’s TDD_FAIL) |

CI mix does **not** flip workspace `merge_ff_only` / `git_merge::` results. Guard / Windows full-lib are out of this TDD filter.

## Gaps and limits

1. **`src-tauri` IPC/DTO path** (`git_write_merge_ff_only_gated_and_allowlisted`): **NOT RUN** on rustc/cargo 1.83 (`edition2024` dep; this run failed on `time-core-0.1.9`). Re-run on a newer toolchain before claiming Tauri-layer PASS.
2. **No UI / E2E proof** of BRANCH-MERGE from `ui/app.js` (out of this TDD filter). ACL is confirmed in `host.toml` + `host-default` + `capabilities/default.json`; runtime invoke was not executed.
3. **No committed RED evidence** on the feature branch (tests+impl in one feat commit).
4. Std fixture does not separately assert that the spawned argv is exactly `merge --ff-only -- <name>` (behavior is asserted via HEAD movement, no merge commit, and out-of-scope flag names). Fake records `last_merge_ff_only` only. Source argv was read as `["merge", "--ff-only", "--", name]`.

## Outcome

**TDD_PASS**

- `PD-GIT-MERGE-FF-01-1`: **TDD_PASS**
- `PD-GIT-MERGE-FF-01-2`: **TDD_PASS**
- `PD-GIT-MERGE-FF-01-3`: **TDD_PASS**
- `allow-git-merge-ff` in `host-default`: **CONFIRMED**

`src-tauri` `--lib` remains **NOT RUN** (edition2024). That gap does not flip the three scenario verdicts, and it is not recorded as PASS.

Not Done. Not blue. High-tier re-review is a separate agent.
