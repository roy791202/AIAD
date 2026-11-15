# PD-GIT-UNSET-UPSTREAM-01 — High-tier review (section B)

**Verdict:** **PASS** (architecture / forbidden-git / board lifecycle). **Merge blocked** until AI Dev Guard sees registered BDD scenarios (see below).

**Date (UTC):** 2026-11-15  
**Reviewer:** independent high-tier (this cloud agent). **Not** implementer `bc-ebcf4a54` / `bc-336992cb`. **Not** a substitute for independent TDD verifier sign-off.  
**Impl PR:** https://github.com/roy791202/AIAD/pull/79  
**Implementation branch:** `feature/PD-GIT-UNSET-UPSTREAM-01-unset-upstream` @ `a1ea272ddbb4778f2252011cdee8aa6b51b9ff06`  
**Base:** `main` @ `98355b1891b0a3cbe1e4697eeced2df457fe6ef9`  
**Commit title:** `test(git): TDD-lock gated unset_upstream (PD-GIT-UNSET-UPSTREAM-01)` (Conventional Commits)

## Identity

| Role | Identity | Same as this reviewer? |
|------|----------|-------------------------|
| Implementer | Cursor cloud dev on PR #79 (`cursor[bot]`); agent ref `bc-ebcf4a54-31f8-4a4b-9c08-53898b8a94de` | No |
| TDD verifier | Not recorded in this repository for this task | No |
| High-tier | This document | — |

This review does **not** set Done / Blue and does **not** merge.

## User-requested checks

| Check | Result | Evidence |
|-------|--------|----------|
| Product `unset_upstream` never uses `checkout` / `reset --hard` | **PASS** | `StdGitWrite::unset_upstream` runs only `git branch --unset-upstream -- <local>` after approval + ref checks (`std_git_write.rs`). Comments explicitly forbid checkout / switch / fetch / pull / push / `reset --hard`. |
| Board card **In Review** (not Done / Shipped) | **PASS** | `docs/board.json` → `PD-GIT-UNSET-UPSTREAM-01.status` = `In Review`. |
| No **Blue** / Done lifecycle on card | **PASS** | `light` = `Green` (not `Blue`). No `completedAt`. History ends at In Review. |
| Reviewer ≠ developer `bc-336992cb` | **PASS** | Independent high-tier agent; implementer per PR footer is `bc-ebcf4a54`. |

## Scope (PR #79)

5 files, +259 / −3.

| Path | Role |
|------|------|
| `sgenaxis-adapters/src/tests_git.rs` | Fake `pd_git_unset_upstream_01_{1,2,3}_*` |
| `sgenaxis-adapters/src/tests_git02.rs` | Std worktree `pd_git_unset_upstream_01_{1,2,3}_*` |
| `sgenaxis-host/src/git_unset_upstream.rs` | Rename host tests to scenario IDs (`01_1`, `01_2`) |
| `docs/board.json` | Task card `PD-GIT-UNSET-UPSTREAM-01` |
| `reports/dispatch-pd/PD-GIT-UNSET-UPSTREAM-01.md` | Developer evidence |

**No** `.feature` edits. **No** `.ai-hooks` / `.githooks` / workflow changes. **No** product adapter logic changes in this PR (impl already on `main`; slice TDD-locks the contract).

## Forbidden operations (checkout / reset --hard)

| Layer | Finding |
|-------|---------|
| `StdGitWrite::unset_upstream` | Single mutating git argv: `branch --unset-upstream -- <local>`. Detached HEAD rejected before git. |
| `FakeGitWrite::unset_upstream` | In-memory upstream map only; flag-like local names rejected via `branch_name_out_of_scope`. |
| `perform_git_unset_upstream` (host) | Approval gate → port call; no git CLI. |
| Integration tests | `tests_git02` uses `git checkout --detach` **only** to seed detached-HEAD scenario **01-3**; `unset_upstream` under test does not invoke checkout. No `reset --hard` in PR diff or adapter implementation path. |

## Layering

| Layer | Artifact |
|-------|----------|
| Port | `GitWritePort::unset_upstream` (existing on `main`) |
| Adapter (std / fake) | Approval → resolve local → verify branch → `--unset-upstream` or in-memory clear |
| Host | `perform_git_unset_upstream` maps errors to DTO; tests use `FakeGitWrite` only |

Dependencies remain adapter → port; host tests do not pull UI/Tauri. No skip/ignore added for this slice.

## Independent TDD re-run (reviewer)

From `apps/sgenaxis-desktop` on branch `feature/PD-GIT-UNSET-UPSTREAM-01-unset-upstream`:

```text
cargo test -p sgenaxis-adapters --features std-adapters pd_git_unset_upstream_01
# 6 passed

cargo test -p sgenaxis-host --lib pd_git_unset_upstream_01
# 2 passed
```

All eight scenario-named tests **Green** (Fake ×3, Std ×3, Host ×2). Scenario **01-3** is not duplicated at host layer (honest failures covered in adapters); acceptable for this thin host wrapper.

## Board / CI (process)

| Item | Observed | Note |
|------|----------|------|
| Card status | `In Review`, `tdd` Green, `ci` Pending | Matches dev READY_FOR_TDD; **not** Done/Blue. |
| `prUrl` on card | Missing | Suggest dev add `https://github.com/roy791202/AIAD/pull/79` on next board touch. |
| `parentId` | `null` | Story link missing; non-architecture debt. |
| AI Dev Guard @ `a1ea272` | **failure** (6 items) | `scenarioIds` `PD-GIT-UNSET-UPSTREAM-01-{1,2,3}` not registered / not Green in guard BDD index. |
| `tests` job | **success** | |
| `lint + test subset` | **success** | |
| `rust-windows` | in progress at review time | Not re-validated here. |

Guard failure is a **merge blocker**, not an architecture FAIL for `unset_upstream` behavior.

## Findings

### Must-fix for architecture review

None.

### Blocking for merge / Done (process)

1. Register BDD scenarios `PD-GIT-UNSET-UPSTREAM-01-1..3` so guard accepts `scenarioIds` (or adjust board linkage per project rules).  
2. AI Dev Guard must be Green before merge.  
3. Do **not** set Done / Blue from this review; only after merge + verifier + guard Green.

### Suggestions (non-blocking)

1. Add `prUrl` and Story `parentId` on the Task card.  
2. Host layer could add an explicit `01_3` refused-when-unapproved test for symmetry; adapters already cover failures.  
3. Board `light` Green while guard is red is acceptable short-term but should flip Yellow with `lightReason` once CI failure is acknowledged.

## Decision

**PASS** high-tier review for PD-GIT-UNSET-UPSTREAM-01 / PR #79 on architecture, forbidden-git constraints (**no checkout / `reset --hard` on the product path**), and board state (**In Review**, not Done/Blue).

**Do not merge** until AI Dev Guard passes. This review artifact is docs-only and does not modify product code or board status.

**Evidence path:** `reports/dispatch-pd/PD-GIT-UNSET-UPSTREAM-01-HIGH-TIER-REVIEW.md`  
**Compare URL:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-UNSET-UPSTREAM-01-unset-upstream