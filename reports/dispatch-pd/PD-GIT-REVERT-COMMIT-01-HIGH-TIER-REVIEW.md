# PD-GIT-REVERT-COMMIT-01 — High-tier code review

**Verdict:** **FAIL**

**Date (UTC):** 2026-11-14  
**Reviewer:** `independent-high-tier-revert-commit-01` (high-tier; did **not** implement; did **not** run TDD review)  
**Implementer (per PR #42):** cursor-dev / PD-GIT-REVERT-COMMIT-01 dedicated implementation  
**TDD verifier (separate):** `independent-tdd-revert-commit-01` — `reports/dispatch-pd/PD-GIT-REVERT-COMMIT-01-TDD-REVIEW.md` on `feature/PD-GIT-REVERT-COMMIT-01-tdd-review`

**PR:** https://github.com/roy791202/AIAD/pull/42  
**Implementation branch:** `feature/PD-GIT-REVERT-COMMIT-01-revert-commit` @ `2840f9e7f81f6582d6ea1de56b4ad1c560b30f6a`  
**BDD ID:** `BDD-PD-GIT-REVERT-COMMIT-01` — approval-gated `git revert --no-edit -- <sha>`; deny → no mutation; merge commits fail without invented `-m 1`; never `--force` / `reset --hard` / silent `--no-commit`

## Identity separation

| Role | Agent | Valid for acceptance? |
|------|--------|------------------------|
| Implementation | cursor-dev (PR #42) | — |
| TDD re-run | `independent-tdd-revert-commit-01` | **TDD_PASS** — 9/9 `revert_` tests (independently replayed in this review) |
| High-tier review | `independent-high-tier-revert-commit-01` | This document |

Reviewer did **not** modify product code, tests, `.feature`, hooks, or `docs/board.json`. Did **not** merge PR or set Done / blue.

## Independent checks (this review)

| Check | Command / source | Result |
|-------|------------------|--------|
| Slice tests | `cd apps/sgenaxis-desktop && cargo test -p sgenaxis-adapters revert_ --features std-adapters` | **9/9 PASS** (replayed locally) |
| TDD evidence | `feature/PD-GIT-REVERT-COMMIT-01-tdd-review` | **TDD_PASS** — verifier distinct from implementer |
| PR diff scope | 8 files, +658 / −2 on PR #42 | See file-scope section |
| CI @ PR head | GitHub Actions on `2840f9e7` | `tests` + `lint + test subset` **success**; **`guard` failure**; `rust-windows` incomplete at review time |

## Ports vs adapters (hexagonal)

| Layer | Artifact | Assessment |
|-------|----------|------------|
| Port (output) | `GitWritePort::revert_commit` in `sgenaxis-ports/src/git.rs` | Contract documents deny/approve, command shape, merge honesty, and negative guarantees (`--no-commit`, `--force`, `reset --hard`). Dependency **inward** only. **Met** |
| Std adapter | `StdGitWrite::revert_commit` | Approval gate → `require_commit_sha` → `rev_exists` → `is_merge_commit` (`sha^2`) → `run(["revert", "--no-edit", "--", rev])`. No `-m`, `-n`, `force`, or `reset`. **Met** |
| Fake adapter | `FakeGitWrite::revert_commit` | Mirrors port semantics for unit tests; `mark_merge_commit` for merge refusal; credential redaction on injected failures. **Met** |
| Gated adapter | `GatedGitWrite::revert_commit` | Always `PermissionDenied` — consistent with other gated methods. **Met** |

No host/Tauri/UI wire in this slice (explicitly port-only per dispatch report). Layering matches neighboring git-write slices; adapters do not leak CLI into port definitions.

## Safety contract (requested focus)

| Requirement | Evidence | Assessment |
|-------------|----------|------------|
| No `reset --hard` on revert path | `StdGitWrite` only invokes `revert --no-edit`; module docs and port docstring; `commit_sha_out_of_scope` blocks `reset` / `--hard` as sha input | **Met** |
| No `--no-commit` / silent index-only revert | Std argv fixed; `std_revert_approved_creates_new_commit` asserts empty porcelain; fake pushes revert commit onto history | **Met** |
| No `--force` | Not passed; `--force` rejected via `commit_sha_out_of_scope` | **Met** |
| Merge-commit honesty (no invented `-m 1`) | `is_merge_commit` via second parent; fake `mark_merge_commit` + std no-ff merge fixture; errors cite mainline / `-m` | **Met** |
| Denied approval → HEAD unchanged | Fake + std denied tests | **Met** |
| Unknown / flag sha → honest failure | `require_commit_sha`, `rev_exists`, fake unknown sha tests | **Met** |

## File scope (allowed vs PR #42)

**Allowed per task note:** `ports/git.rs`, `adapters` (`git_write.rs`, `std_git_write.rs`, `fake.rs`), focused tests, optional host/Tauri allowlist.

| Path | In allowed slice? | Notes |
|------|-------------------|--------|
| `sgenaxis-ports/src/git.rs` | Yes | Port method + doc |
| `sgenaxis-adapters/src/{git_write,std_git_write,fake,lib}.rs` | Yes | Adapters + gated stub |
| `sgenaxis-adapters/src/tests_git_revert_commit.rs` | Yes | TDD |
| `reports/dispatch-pd/PD-GIT-REVERT-COMMIT-01.md` | Yes (evidence) | Dispatch report |
| `docs/board.json` | **No** / process debt | Large delta: adds **four** automation Task cards (including unrelated `PD-GIT-RESTORE-PATH-01`, `PD-P1-M03-*`, `PD-P1-M08-*`); invalid `scenarioIds`; `PD-GIT-REVERT-COMMIT-01` still **In Progress**, `tdd: None`, no `prUrl` — triggers guard |

Out-of-scope `docs/board.json` edits are the primary driver of **AI Dev Guard** failure, not the revert implementation.

## Clean Code (slice)

- **Strengths:** Small vertical slice; shared `commit_sha_out_of_scope` for flag injection defense; std/fake/gated parity on new trait method; tests named by behavior; comments state negative guarantees at port and adapter.
- **Minor (non-blocking):** `commit_sha_out_of_scope` lists `"--no-edit"` to block sha-as-flag injection (std still passes `--no-edit` to git intentionally) — correct but subtle.
- **Process gap:** No checked-in `docs/bdd/*.feature` for `BDD-PD-GIT-REVERT-COMMIT-01` (TDD review noted); behavior covered only in Rust tests.

## TDD acceptance (from separate verifier + replay)

Accept **TDD_PASS** per `independent-tdd-revert-commit-01` and local replay:

- **9/9** `revert_*` tests green on `sgenaxis-adapters` with `std-adapters`.
- TDD review markdown is **not** on the implementation branch / PR #42 diff — traceability gap for PR-only readers.

High-tier does **not** treat missing TDD file on PR as test failure when independent verifier branch exists.

## CI / merge readiness

| Check | Status | Notes |
|-------|--------|--------|
| AI Dev Guard | **Fail** | `PD-GIT-REVERT-COMMIT-01`: status must be **In Review / In QA** for PR; **TDD not Green**; BDD id not Green; invalid `scenarioIds` on multiple new cards |
| Workspace `tests` / lint subset | Pass | Includes adapter build |
| Board vs CI truth | **Mismatch** | Card shows green light + In Progress while guard rejects PR linkage |

Per ai-dev-pr-acceptance, **guard failure blocks merge** regardless of slice test green.

## Must-fix (blocking PASS / merge)

1. **Board / guard:** On implementation branch, fix `docs/board.json` for `PD-GIT-REVERT-COMMIT-01` only: move to **In Review / In QA**, set `tdd: Green`, `prUrl` → PR #42, valid BDD linkage (or remove invalid `scenarioIds` until `.feature` exists). **Revert or split** unrelated Task cards added in the same commit — they are outside this Task scope and reference non-existent BDD ids.
2. **CI:** Re-run until **AI Dev Guard** is green on PR head.
3. **PR evidence:** Cherry-pick or merge `reports/dispatch-pd/PD-GIT-REVERT-COMMIT-01-TDD-REVIEW.md` onto the implementation branch so PR shows independent TDD sign-off without extra branch hop.

## Should-fix (recommended)

1. Add `docs/bdd` Gherkin for `BDD-PD-GIT-REVERT-COMMIT-01` when preproduction requires formal `.feature` trace.
2. If product needs UI revert, follow-up Task for host IPC + Tauri allowlist (explicitly out of scope here).
3. Confirm `rust-windows` CI completes green on PR head (was in progress at review time).

## What passed (do not rework)

- `GitWritePort::revert_commit` contract and std/fake/gated implementations.
- Command shape `git revert --no-edit -- <sha>` with merge detection and flag rejection.
- No `reset --hard`, `--force`, or `--no-commit` widening on this path.
- Independent TDD verifier separation and **9/9** green replay.

## Outcome

**FAIL** for merge / acceptance — **implementation architecture and git-safety contract are sound**, but **process gates fail**: out-of-scope and incorrect `docs/board.json` changes, **AI Dev Guard red**, and board card not in **In Review** with **TDD Green**. After must-fix items, re-request high-tier review for **PASS** without replan.