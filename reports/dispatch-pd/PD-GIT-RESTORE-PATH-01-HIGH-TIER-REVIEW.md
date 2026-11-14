# PD-GIT-RESTORE-PATH-01 — High-tier code review

**Verdict:** **FAIL**

**Date (UTC):** 2026-11-14  
**Reviewer:** `independent-high-tier-pd-git-restore-path-01` (high-tier; did **not** implement; did **not** run TDD review)  
**Implementer (per PR #43):** `dev-agent/cursor-cloud-PD-GIT-RESTORE-PATH-01`  
**TDD verifier (separate):** `independent-tdd-restore-path-01` — report on `origin/feature/PD-GIT-RESTORE-PATH-01-tdd-review` (`reports/dispatch-pd/PD-GIT-RESTORE-PATH-01-TDD-REVIEW.md`), **TDD_PASS**, not merged into PR branch

**PR:** https://github.com/roy791202/AIAD/pull/43  
**Implementation branch:** `feature/PD-GIT-RESTORE-PATH-01-restore-path` @ `2a851ccdc18057ee28f1e30769e3f3c98ad44682`  
**BDD ID:** `BDD-PD-GIT-RESTORE-PATH-01` (gated worktree restore from HEAD; deny = no mutation; `OPERATION_IN_PROGRESS` when unmerged/in-progress; never `reset --hard`; never untracked delete)

## Identity separation

| Role | Agent | Valid for acceptance? |
|------|--------|------------------------|
| Implementation | `dev-agent/cursor-cloud-PD-GIT-RESTORE-PATH-01` | — |
| TDD re-run | `independent-tdd-restore-path-01` | **TDD_PASS** (3/3 `restore_path` filter) |
| High-tier review | `independent-high-tier-pd-git-restore-path-01` | This document |

Reviewer did **not** modify product code, tests, `.feature`, hooks, or `docs/board.json`. Did **not** merge PR or set Done / blue.

## Independent checks (this review)

| Check | Command / source | Result |
|-------|------------------|--------|
| Slice tests | `cd apps/sgenaxis-desktop && cargo test --package sgenaxis-adapters --features std-adapters restore_path` | **3/3 PASS** (replayed locally) |
| TDD evidence | `feature/PD-GIT-RESTORE-PATH-01-tdd-review` report | **TDD_PASS** (read + replay; distinct verifier) |
| PR diff scope | 8 files, +517 / −1 | See file-scope section |
| CI @ PR head | GitHub Actions | `tests` + `lint + test subset` **success**; **`guard` failure**; **`rust-windows` failure** (unrelated `std_write_temp` tests; slice **ok**) |

## Contract focus (requested gates)

| Requirement | Evidence | Assessment |
|-------------|----------|------------|
| Worktree-only restore from `HEAD` | `StdGitWrite::restore_path` → `git restore --source=HEAD --worktree -- <rel>`; integration test matches `HEAD:a.txt` blob; sibling `b.txt` dirty; staged index survives worktree-only restore | **Met** |
| Never `reset --hard` on restore-path | Mutating git invocation is `restore` only; test asserts `HEAD` SHA unchanged; no `reset` in `restore_path` body | **Met** |
| Unmerged / in-progress → fail | `require_conflict_kind` + `ls-files -u`; fake `set_conflict_in_progress`; both assert `OPERATION_IN_PROGRESS` | **Met** |
| Untracked not deleted | Std test retains `new.txt` + `??` in porcelain; `ls-files --error-unmatch` rejects untracked before restore; fake `mark_restore_untracked` errors without recording restore | **Met** |
| Denied → no mutation | Std + fake `PermissionDenied`; dirty content unchanged when denied | **Met** |
| Gated adapter default-deny | `GatedGitWrite::restore_path` → `GIT_WRITE_GATED_MSG` | **Met** |
| Path scope (no `.` / flags) | `require_conflict_path` / `conflict_path_out_of_scope`; fake rejects `.` and `-f` | **Met** |

## Layering (ports → adapters)

| Layer | Artifact | Assessment |
|-------|----------|------------|
| Port | `GitWritePort::restore_path` in `sgenaxis-ports/src/git.rs` | Contract documents negative guarantees; dependency inward ✓ |
| Adapters | `StdGitWrite`, `FakeGitWrite`, `GatedGitWrite` | Parity with neighboring git-write slices; std performs single scoped `git restore` ✓ |
| Host / Tauri / UI | Not in this PR | Consistent with dispatch “port-only slice”; no IPC gap for this task scope ✓ |

No skip-layer coupling: adapters do not bypass approval or widen paths.

## File scope (task allow-list)

**Allowed (per board note):** `sgenaxis-ports/src/git.rs`, adapter `git_write.rs` / `std_git_write.rs` / `fake.rs`, `tests_git*.rs`, optional host/Tauri if command required.

| Path | In allow-list? | Notes |
|------|----------------|-------|
| `crates/sgenaxis-ports/src/git.rs` | Yes | Port method + doc |
| `crates/sgenaxis-adapters/src/{std_git_write,git_write,fake}.rs` | Yes | Implementations |
| `crates/sgenaxis-adapters/src/tests_git{,02}.rs` | Yes | TDD |
| `reports/dispatch-pd/PD-GIT-RESTORE-PATH-01.md` | Evidence | Acceptable |
| `docs/board.json` | Process | **Partial:** card for this task is expected, but PR also inserts **unrelated** Task cards (`PD-GIT-REVERT-COMMIT-01`, `PD-P1-M03-CX-H2-V3-REVIEW-01`, `PD-P1-M08-HARNESS-CONTRACT-REVIEW-01`) — **out of slice scope** |

No changes to `.ai-hooks`, `.githooks`, `.github/workflows`, or `.feature`.

## Clean Code / production readiness (slice)

- **Strengths:** Mirrors `stage_path` / `unstage_path` guard pattern; explicit comment on worktree-only semantics; fake records last path without simulating `reset`; integration test covers deny, partial restore, index vs worktree layering, conflict repo.
- **Minor (non-blocking code):** Untracked detection relies on `ls-files --error-unmatch` (correct for tracked-only restore); no `ensure_path_in_repo` on std path (same as some sibling slices — document-only gap).
- **Process gaps:** No checked-in `docs/bdd/*.feature` for `BDD-PD-GIT-RESTORE-PATH-01`; independent TDD report not on implementation branch.

## TDD acceptance (from separate verifier)

Accept **TDD_PASS** for scoped `restore_path` **3/3** (independently replayed in this review). High-tier does not treat implementer self-check as sole evidence.

## CI / board / merge readiness

| Check | Status | Blocking? |
|-------|--------|-----------|
| AI Dev Guard | **Fail** | **Yes** — invalid Task `status` (`In Review / In QA` vs guard enum `In Review`); `scenarioIds` reference non-existent BDD registry entries; guard rejects BDD Green linkage for listed scenarios; extra board cards amplify failures |
| `rust-windows` full lib | **Fail** | No for this slice (unrelated temp git tests; slice passed) |
| Ubuntu `tests` / lint subset | Pass | — |

**Board card (`PD-GIT-RESTORE-PATH-01`):** Green (not blue) / `In Review / In QA` — implementer did not set Done ✓. Missing `prUrl` and guard-valid `status` / scenario registry alignment ✗.

## Must-fix (blocking high-tier PASS)

1. **Narrow `docs/board.json` diff** to this task (remove unrelated Task cards from PR #43 or move them to separate commits/branches).
2. **Fix board guard fields** for `PD-GIT-RESTORE-PATH-01`: use guard-valid `status` (`In Review`), attach `prUrl` for PR #43, align `scenarioIds` with registered BDD or guard-approved workflow.
3. **Attach independent TDD sign-off** on the implementation branch (merge or cherry-pick `reports/dispatch-pd/PD-GIT-RESTORE-PATH-01-TDD-REVIEW.md` from `feature/PD-GIT-RESTORE-PATH-01-tdd-review`).

## Should-fix (recommended)

1. Re-run full `sgenaxis-adapters` lib on Windows when toolchain flakiness in unrelated `std_write_temp` tests is resolved.
2. Add `docs/bdd` Gherkin for `BDD-PD-GIT-RESTORE-PATH-01` when preproduction requires formal `.feature` trace.
3. Optional: std adapter `ensure_path_in_repo` for restore-path parity with FILE-STAGE traversal defense.

## What passed (do not rework)

- Hexagonal `GitWritePort::restore_path` with gated/fake/std parity.
- Exact `git restore --source=HEAD --worktree -- <path>` semantics and negative guarantees (no hard reset, no untracked delete, no widen).
- `OPERATION_IN_PROGRESS` behavior and honest errors for missing/untracked/denied paths.
- Focused TDD naming and integration coverage of worktree vs index separation.

## Outcome

**FAIL** — the **git restore-path adapter slice is architecturally sound** and meets the worktree / no-hard-reset / unmerged / untracked contract with **3/3** independent TDD replay, but **PR #43 is not merge-ready** due to **board.json scope creep**, **AI Dev Guard** validation failures, and **missing PR-branch TDD evidence**. After must-fix items, high-tier re-review can move to **PASS** without replan.