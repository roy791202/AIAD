# PD-GIT-ADD-REMOTE-01 — High-tier review (section B)

**Verdict:** **CHANGES_REQUIRED**

Ports/Adapters layering, no `-f`/fetch on `add_remote`, allowed-file scope (tests-only product delta), and no skip/ignore on the new TDD slice all look correct. **AI Dev Guard fails** on `docs/board.json` (invalid Task status string, BDD `status` not `Green` while Task `tdd` is `Green`). Fix board/guard before merge. Reviewer did **not** merge, did **not** set Done/Blue, and did **not** change product code.

**Date (UTC):** 2026-11-15  
**Reviewer:** independent high-tier (this agent). **Not** the implementer (`cloud-dev-agent-composer-PD-GIT-ADD-REMOTE-01`).  
**Impl PR:** https://github.com/roy791202/AIAD/pull/68  
**Compare:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-ADD-REMOTE-01-add-remote  
**Implementation branch:** `feature/PD-GIT-ADD-REMOTE-01-add-remote` @ `5401fe50ce7f65953916a90aee365c6903253a42`  
**Base:** `main` @ `98355b1891b0a3cbe1e4697eeced2df457fe6ef9`  
**Review evidence branch:** `feature/PD-GIT-ADD-REMOTE-01-high-tier-review`

## Identity

| Role | Identity | Same as reviewer? |
|------|----------|-------------------|
| Implementer | Cursor Agent / `cloud-dev-agent-composer-PD-GIT-ADD-REMOTE-01` (PR #68) | No |
| High-tier | This review | — |

Independent TDD verifier was not run in this session; high-tier re-ran `pd_git_add_remote_01_*` locally (**5/5** pass, 0 ignored).

## Scope (PR #68 files)

5 files, +358 / −1. **No** `.feature` edits. **No** hook/CI workflow edits.

| Path | In allowed set? | Role |
|------|-----------------|------|
| `sgenaxis-adapters/src/tests_git.rs` | Yes | Fake: scenarios 1 & 3 |
| `sgenaxis-adapters/src/tests_git02.rs` | Yes | Std worktree: scenarios 1–3 |
| `docs/board.json` | Yes (dispatch note) | Task + Story cards |
| `reports/dispatch-pd/PD-GIT-ADD-REMOTE-01.md` | Yes | Dev dispatch |
| `reports/dispatch-pd/PD-GIT-ADD-REMOTE-01-test-output.txt` | Evidence (not listed in task note) | TDD log — acceptable |

**Product adapters** (`std_git_write.rs`, `fake.rs`, `git_write.rs`, `sgenaxis-ports/src/git.rs`): **unchanged on PR**; behavior reviewed on `main` as the contract under test.

## Layering (外 → 內)

| Layer | Artifact | Direction |
|-------|----------|-----------|
| Port | `GitWritePort::add_remote` | Documents `git remote add -- <name> <url>`; approval required; never `-f`, fetch, `set-url`, or push; duplicates fail honestly. |
| Adapter (std) | `StdGitWrite::add_remote` | `require_approval` → trim → `require_remote_name` / `require_remote_url` → `run(["remote","add","--", name, url])` only. Comments state no `-f`/fetch. |
| Adapter (fake) | `FakeGitWrite::add_remote` | Denied → `PermissionDenied` before state change. Granted → in-memory remotes; duplicate → `PortError::Git`; out-of-scope names/URLs via `remote_*_out_of_scope`. |
| Adapter (gated) | `GatedGitWrite::add_remote` | Always `PermissionDenied(GIT_WRITE_GATED_MSG)` (pre-existing on `main`). |

No UI/Tauri/host changes. Adapters depend on port types only; port does not depend on adapters. Tests live in adapter crate (integration-style for Std).

## Never `-f` / fetch / force remote writes

| Check | Evidence |
|-------|----------|
| Std argv | `remote add -- <name> <url>` only (`std_git_write.rs` ~738–754). |
| No fetch side effect | `pd_git_add_remote_01_2_approved_add_records_url_without_fetch`: no `FETCH_HEAD`, no `refs/remotes/upstream`. |
| Flag-like names/URLs rejected | Scenario 3 (Std + Fake): `-f`, `--mirror`, empty name/url, url `-u`; `push_count` 0 on Fake. |
| `remote_name_out_of_scope` | Blocks `-f`, `--force`, `--fetch`, `--mirror`, etc. (`git_write.rs`). |

Independent run: `cargo test pd_git_add_remote_01 --manifest-path apps/sgenaxis-desktop/crates/sgenaxis-adapters/Cargo.toml` → **5 passed**, **0 failed**, **0 ignored**.

## BDD / TDD traceability

| BDD ID | Test(s) | Layers |
|--------|---------|--------|
| PD-GIT-ADD-REMOTE-01-1 | `pd_git_add_remote_01_1_denied_approval_does_not_add_remote` | Fake + Std |
| PD-GIT-ADD-REMOTE-01-2 | `pd_git_add_remote_01_2_approved_add_records_url_without_fetch` | Std only (Fake covered by older `fake_git_write_add_and_remove_remote_*` on `main`) |
| PD-GIT-ADD-REMOTE-01-3 | `pd_git_add_remote_01_3_duplicate_and_option_like_names_fail_honestly` | Fake + Std |

No `#[ignore]`, `#[cfg(skip)]`, or `only` filters on these tests (grep on changed test files).

## CI / board (process — **blocking merge**)

| Item | Observed |
|------|----------|
| `tests` | **success** @ `5401fe5` |
| `lint + test subset` | **success** |
| `guard` | **failure** (8 errors): Task `status` `In Review / In QA` not in schema (`In Review` required); Task `tdd: Green` but Story `bdd[].status` still `None` for all three scenario IDs; PR guard echoes same BDD mismatch. |
| `rust-windows` | **in progress** at review time (not gating this verdict on Windows). |
| Task `ci` on board | `None` vs red guard — inconsistent while guard is red. |
| `prUrl` on Task card | Not set on new card (suggest add PR #68 URL on next board update). |

## Findings

### Must-fix before merge (CHANGES_REQUIRED)

1. **`docs/board.json`:** Change Task `PD-GIT-ADD-REMOTE-01` `status` from `In Review / In QA` to **`In Review`** (guard schema).  
2. **`docs/board.json`:** Set Story `S-GIT-WRITE-ADD-REMOTE-01` `bdd[].status` to **`Green`** for `PD-GIT-ADD-REMOTE-01-{1,2,3}` when Task `tdd` is `Green` (or lower Task `tdd` until verifier signs scenarios).  
3. **Re-run CI `guard`** after board fix; align Task `ci` field with check conclusion.

### Architecture / layering (no code change required on this PR)

None. Pre-existing `StdGitWrite` / `FakeGitWrite` implementations match port contract; PR correctly TDD-locks without widening scope.

### Suggestions (non-blocking)

1. Add a **GatedGitWrite** scenario test for `add_remote` (symmetry with other git-write locks).  
2. Fake scenario 3 uses `PortError::Git` for duplicate and `.is_err()` for flag cases; Std uses `expect_err` with mixed `Git`/`Other` — acceptable; optional tighten assertions.  
3. Set Task `prUrl` to PR #68 on board update.

## Decision

**CHANGES_REQUIRED** for merge/Done: fix board.json guard violations, then re-run **guard** Green.

**PASS** on Ports/Adapters, no fetch/force on `add_remote`, PR file scope, and no skipped scenario tests.

Do **not** merge from this review. Do **not** set Done/Blue.

**Evidence:** `reports/dispatch-pd/PD-GIT-ADD-REMOTE-01-HIGH-TIER-REVIEW.md` (this file).