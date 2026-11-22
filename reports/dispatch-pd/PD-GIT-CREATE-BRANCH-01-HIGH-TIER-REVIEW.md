# PD-GIT-CREATE-BRANCH-01 — High-tier review (section B)

**Verdict:** **PASS**

Architecture, layering, `GitWriteApproval` gating, `git branch -- <name>` only, never `branch -C` / `--force` / `-D` / `-d`, never switch/checkout, never remote create / `--set-upstream`, and no skip tests all hold on impl PR #49. Independent TDD reported **7/7** `pd_git_create_branch_01_*`. Reviewer did **not** merge, did **not** set Done/Blue, and did **not** change product code or `docs/board.json`.

**Date (UTC):** 2026-11-14  
**Reviewer:** independent high-tier (this agent). **Not** the implementer. **Not** the TDD verifier.  
**Impl PR:** https://github.com/roy791202/AIAD/pull/49  
**Compare:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-CREATE-BRANCH-01-create-branch  
**Implementation branch:** `feature/PD-GIT-CREATE-BRANCH-01-create-branch` @ `260546b7dc6f528ce08325c8da1b6995436de895`  
**Base:** `main` @ `98355b1891b0a3cbe1e4697eeced2df457fe6ef9`  
**Commit:** `feat(git): lock PD-GIT-CREATE-BRANCH-01 create_branch TDD` (Conventional Commits)

## Identity

| Role | Identity | Same as reviewer? |
|------|----------|-------------------|
| Implementer | Cursor Agent on `feature/PD-GIT-CREATE-BRANCH-01-create-branch` (PR #49, `cursor[bot]`) | No |
| TDD verifier | Independent TDD Gate — **PASS** `pd_git_create_branch_01` **7/7** | No |
| High-tier | This review | — |

Acceptance would be invalid if implementer and verifier were the same agent. They are not. This review does not substitute for merge.

## Scope (PR files)

3 files, +177 / −3. **No** `docs/board.json`. **No** `.feature`. **No** `.ai-hooks` / `.githooks` / `.github/workflows`. **No** skip / ignore / `only`.

| Path | Role |
|------|------|
| `sgenaxis-ports/src/git.rs` | Comment-only: tag `create_branch` docs with `PD-GIT-CREATE-BRANCH-01`. Signature unchanged. |
| `sgenaxis-adapters` `tests_git.rs` | Fake + Gated focused TDD (4 tests) |
| `sgenaxis-adapters` `tests_git02.rs` | Std worktree TDD (3 tests) + `remote_branch_list` helper |

Allowed-file set is the TDD-lock slice (port contract comment + adapter tests). Product adapters (`fake.rs`, `std_git_write.rs`, `git_write.rs` / `GatedGitWrite`) were **not** rewritten on this PR; they already implement the contract on `main`. That is in-scope for a lock-TDD task.

## Layering (外 → 內)

| Layer | Artifact | Direction |
|-------|----------|-----------|
| Port | `GitWritePort::create_branch` | Documents `git branch -- <name>`; approval required; never `-C` / `--force` / `-D` / `-d`; never remote create; never `--set-upstream`; never switch/checkout. |
| Adapter (std) | `StdGitWrite::create_branch` | `require_approval` → `require_branch_name` → `run(["branch", "--", branch])` only. |
| Adapter (fake) | `FakeGitWrite::create_branch` | Denied → `PermissionDenied` before any record. Granted → local list + `branch_create` only; does not set `switched` or upstream. |
| Adapter (gated) | `GatedGitWrite::create_branch` | Always `PermissionDenied(GIT_WRITE_GATED_MSG)` even when `granted()`. |

No UI / Tauri / host change on this PR (slice is port + adapter TDD). Domain is not involved. Adapters do not import host/UI. `git -C <repo>` in `StdGitWrite::run` is the CLI working-directory flag, **not** `git branch -C`.

## GitWriteApproval / default-deny

| Case | Evidence |
|------|----------|
| Fake denied | `pd_git_create_branch_01_fake_denied_create_branch_does_not_mutate` — `PermissionDenied`; no `last_branch_create`, empty created list, no switch, no upstream |
| Fake granted | `pd_git_create_branch_01_fake_approved_create_branch_without_switch_or_upstream` — records local name only |
| Gated + granted | `pd_git_create_branch_01_gated_create_branch_always_denied` — still `GIT_WRITE_GATED_MSG` |
| Std denied | `pd_git_create_branch_01_std_denied_create_branch_does_not_mutate` — no local `feature/slot`; HEAD stays `main`; remote list unchanged |

## Never `-C` / `--force` / switch / remote create

Std argv for success path is `["branch", "--", name]`. `--` stops option parse. Out-of-scope names (`-C`, `--force`, `-D`, `-d`, `--set-upstream`, `bad..name`, empty) fail via `branch_name_out_of_scope` as `PortError::Other` before git. Duplicates fail honestly as `PortError::Git` (`already exists`) without `-f`/`-C`.

Std tests assert:

- HEAD remains `main` after approved create and after invalid/duplicate attempts.
- New branch SHA equals current HEAD.
- `upstream_of` empty; `remote_branch_list` unchanged vs before.
- Flag names do not become branches (`-D` not in `local_branch_list`).

Independent TDD: **7/7** named `pd_git_create_branch_01_*` (4 fake/gated + 3 std). No `#[ignore]` / skip in those files for this slice.

## Clean Code / production readiness (slice)

- Guard clauses: approval and name checks before mutation.
- No `unwrap()` on the production `create_branch` path (tests use `expect` / `unwrap` on temp paths only).
- Credential redaction remains in `StdGitWrite::run` for git stderr (unchanged).
- Name length / git-check-ref-format is bounded by git + `branch_name_out_of_scope`; no unbounded extra allocation on this path.

## Board / CI / TDD (process; not architecture defects)

| Item | Observed | Note |
|------|----------|------|
| `docs/board.json` | **Not** in PR #49 | Required for impl PRs of this batch. Guard cannot see a Task card on this PR. |
| Guard @ `260546b` | **failure** | `PR 沒有對應的 Task 卡片：… feature/PD-GIT-CREATE-BRANCH-01-create-branch` — expected while board stays off the impl PR. |
| `tests` / `lint + test subset` | **success** | |
| `rust-windows` | **failure** (4 tests, **not** `pd_git_create_branch_01_*`) | Pre-existing: remote add/url Windows URL/`file://` out-of-scope; `/bin/true` editor on merge/rebase `--continue`. 195 passed; 0 ignored. |
| Independent TDD | **PASS 7/7** | Taken as given from the TDD agent; high-tier did not re-run as implementer. |
| `.feature` | Unchanged | BDD lives in port comments + named tests (same as sibling git-write TDD locks). |

These **block merge / Done**, not this architecture PASS. Board updates belong on a later board-sync / acceptance step, not on PR #49.

## Findings

### Must-fix for this architecture review

None.

### Blocking for merge / Done (not architecture FAIL)

1. AI Dev Guard: no Task card in `docs/board.json` on the impl PR (by design for this slice).  
2. `rust-windows` red on unrelated std git tests (`add_and_remove_remote`, `set_remote_url`, conflict continue/abort editor). Not introduced by `create_branch` TDD.  
3. Do not set Done/Blue from this review.

### Suggestions (non-blocking)

1. Std invalid-name cases use `expect_err` only; Fake asserts `PortError::Other`. Tightening Std to `Other` would match Fake.  
2. Std duplicate/invalid test does not re-assert `remote_branch_list` after failures (approved-create test already does).  
3. Port comment tags the Task ID; behavior was already specified. Fine for TDD lock.

## Decision

**PASS** high-tier architecture review of PD-GIT-CREATE-BRANCH-01 / PR #49.

Do **not** merge. Do **not** set Done/Blue. Independent TDD is already Green for the 7 named tests; Guard/board remain a separate process step.

**Evidence path:** `reports/dispatch-pd/PD-GIT-CREATE-BRANCH-01-HIGH-TIER-REVIEW.md`  
**Compare URL:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-CREATE-BRANCH-01-create-branch
