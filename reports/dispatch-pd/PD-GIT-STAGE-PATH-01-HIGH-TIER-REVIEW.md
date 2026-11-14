# PD-GIT-STAGE-PATH-01 — High-tier code review (FILE-STAGE)

**Verdict:** **CHANGES_REQUESTED**

**Date (UTC):** 2026-11-14  
**Reviewer:** `independent-high-tier-pd-git-stage-path-01` (high-tier; did **not** implement; did **not** run TDD review)  
**Implementer (per dispatch):** `implementation (cloud)`  
**TDD verifier (separate):** `independent-tdd-stage-path-01` — report on `origin/feature/PD-GIT-STAGE-PATH-01-tdd-review` (`reports/dispatch-pd/PD-GIT-STAGE-PATH-01-TDD-REVIEW.md`), **not** on this PR branch head

**PR:** https://github.com/roy791202/AIAD/pull/9  
**Implementation branch:** `feature/PD-GIT-STAGE-PATH-01-gated-add` @ `f74d723acd0a8422a0ccf04af930ae68c22738e3`  
**BDD ID:** `BDD-PD-GIT-STAGE-PATH-01` (gated `git add -- <path>` only; deny → no mutation; `OPERATION_IN_PROGRESS`; reject `.` / `-A` / `--force` / traversal / empty / NUL; never commit / push / `reset --hard`)

## Identity separation

| Role | Agent | Valid for acceptance? |
|------|--------|------------------------|
| Implementation | `implementation (cloud)` | — |
| TDD re-run | `independent-tdd-stage-path-01` | Scoped **TDD_PASS** (workspace 7/7; `src-tauri` **NOT RUN**) |
| High-tier review | `independent-high-tier-pd-git-stage-path-01` | This document |

Reviewer did **not** modify product code, tests, `.feature`, hooks, or `docs/board.json`. Did **not** merge PR or set Done.

## Independent checks (this review)

| Check | Command / source | Result |
|-------|------------------|--------|
| Slice tests | `cd apps/sgenaxis-desktop && cargo test bdd_pd_git_stage_path_01` | **7/7 PASS** (4 adapters, 3 host) — replayed locally |
| Tauri IPC test | `git_write_stage_path_gated_and_allowlisted` | **NOT RUN** (Cargo 1.83 / `edition2024` deps; same as TDD review) |
| PR diff scope | 18 files, +826 / −10 | Matches dispatch FILE-STAGE slice |
| CI @ PR head | GitHub Actions | `tests` + `lint + test subset` **success**; **`guard` failure**; **`rust-windows` failure** (4 unrelated adapter git temp tests; slice tests **ok**) |

## BDD alignment (behavior)

| Requirement | Evidence in PR | Assessment |
|-------------|----------------|------------|
| Approval-gated; denied → no mutation | `perform_git_stage_path` short-circuit; fake/std denied tests | **Met** |
| Approved → `git add -- <path>` only | `StdGitWrite::stage_path` → `run(repo, &["add", "--", &rel])` | **Met** — no `-A`, `.`, commit, push, hard, force |
| `OPERATION_IN_PROGRESS` (unmerged / in-progress) | `require_conflict_kind` + `ls-files -u` / fake conflict maps | **Met** |
| Reject empty, `.`, `-A`, `--force`, `..`, NUL | `worktree_path_out_of_scope` + `bdd_pd_git_stage_path_01_rejects_out_of_scope_paths` | **Met** (absolute-outside-repo enforced in std via `ensure_path_in_repo`, not in the seven-name filter loop) |
| Never widen scope via flags | Gated + path validators before adapter call | **Met** |
| UI confirm → IPC → port (mirror ALL-STAGE) | `app.js` `stagePath` / `git_write_stage_path`; host module + Tauri command | **Met** at code level; **native invoke blocked** — see must-fix #1 |

## Layering (ports → adapters → host → Tauri → UI)

| Layer | Artifact | Direction / notes |
|-------|----------|-------------------|
| Port | `GitWritePort::stage_path` in `sgenaxis-ports` | Contract documents constraints; dependency **inward** ✓ |
| Adapters | `StdGitWrite`, `FakeGitWrite`, `GatedGitWrite` | All three implement trait; std performs real git; fake records; gated denies ✓ |
| Application | `sgenaxis-host::git_stage_path::perform_git_stage_path` | UI approval boolean → `GitWriteApproval`; no git CLI in host ✓ |
| API / IPC | `git_write_stage_path`, `AllowedIpcCommand::GitWriteStagePath`, `authorize(...)` | Host IPC allowlist extended ✓ |
| Tauri ACL | `permissions/host.toml` `allow-git-stage-path` | Permission **defined** but **not** wired into `host-default` — **defect** |
| Rendering | `ui/app.js`, `git-ux-mock.js` FILE-STAGE hook | Presentation only; uses existing approve pattern ✓ |

No domain layer violation observed: business rules live in port contract + adapter validation + host gating, consistent with neighboring git write slices.

## ACL / allowlist

- **Host IPC:** `git_write_stage_path` added to `AllowedIpcCommand`, `authorize` tests, and `list_commands` — consistent with `git_write_stage_all`.
- **Tauri capabilities:** `default.json` uses `host-default` set; **`allow-git-stage-path` is missing from `host-default.permissions`** while `allow-git-stage-all` is present. Frontend `invoke("git_write_stage_path", …)` will fail capability checks in a built app until fixed.
- Command registry: `lib.rs` registers handler; permission atom exists — only set membership is wrong.

## Git invocation hygiene

- Single invocation shape: `git add -- <rel>` after trim + scope checks.
- Reuses `conflict_path_out_of_scope` via `worktree_path_out_of_scope` — appropriate dedup with CONFLICT-SAVE; not over-abstracted.
- `ensure_path_in_repo` canonicalizes under `rev-parse --show-toplevel` — good path-traversal defense for std adapter.

## File scope

Touched paths align with `reports/dispatch-pd/PD-GIT-STAGE-PATH-01.md` dispatch list. No changes to `.ai-hooks`, `.githooks`, `.github/workflows`, or `.feature`. Evidence + dispatch markdown only in `reports/dispatch-pd/`.

## Clean Code / production readiness (slice)

- **Strengths:** Mirrors `git_stage_all` module shape; DTO mapping extracted; tests named with BDD id; comments state negative guarantees on port and std adapter.
- **Minor (non-blocking):** `bdd_pd_git_stage_path_01_fake_records_when_approved` leaves `last_stage_path` from a prior success when a later conflict call fails (correct semantics; assertion documents sticky fake state).
- **Gaps (process / docs):** No checked-in `docs/bdd/*.feature` for this id (TDD review noted); `docs/board.json` unchanged — CI guard fails.

## TDD acceptance (scoped, from separate verifier)

Accept **conditional** workspace **TDD_PASS** per `independent-tdd-stage-path-01`:

- **7/7** `bdd_pd_git_stage_path_01_*` green (independently replayed in this review).
- **`git_write_stage_path_gated_and_allowlisted`:** **NOT RUN** (toolchain).
- TDD review file **not** on PR branch; merge/traceability gap for PR evidence.

High-tier does **not** upgrade NOT RUN to PASS.

## CI / merge readiness

| Check | Status | Notes |
|-------|--------|-------|
| AI Dev Guard | **Fail** | No matching Task in `docs/board.json`; test-disable scan error (`unterminated JavaScript template` — not isolated to this diff; still blocks guard) |
| rust-windows full lib | **Fail** | Unrelated failures in `tests_git02::std_write_temp::*`; **slice tests passed** |
| Ubuntu subset tests | Pass | Includes workspace tests |

## Must-fix (blocking merge)

1. **Tauri capability wiring:** Add `"allow-git-stage-path"` to the `host-default` `permissions` array in `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` (same pattern as `allow-git-stage-all`). Without this, FILE-STAGE UI cannot invoke the command in production builds.
2. **Board / guard:** Add or update a Task card in `docs/board.json` for `PD-GIT-STAGE-PATH-01` with PR URL, branch, TDD status (scoped green + `src-tauri` NOT RUN), and **In Review / In QA** — not Done. Guard currently fails PR linkage.
3. **PR evidence:** Include `reports/dispatch-pd/PD-GIT-STAGE-PATH-01-TDD-REVIEW.md` on the implementation branch (or merge `feature/PD-GIT-STAGE-PATH-01-tdd-review`) so PR shows independent TDD sign-off.

## Should-fix (recommended, not blocking architecture)

1. Re-run `cargo test git_write_stage_path_gated` in `src-tauri` on a toolchain that resolves `edition2024` deps; attach log to evidence.
2. Add explicit test for absolute path outside repo in `bdd_pd_git_stage_path_01_*` or document as covered only by std adapter.
3. Investigate guard **test-disable** parse failure (`app.js`) so CI guard is trustworthy; fix only if this PR introduced the break.
4. Optional: add `docs/bdd` Gherkin for `BDD-PD-GIT-STAGE-PATH-01` when preproduction requires formal `.feature` trace.

## What passed (do not rework)

- Hexagonal flow and `GitWritePort` extension with gated/fake/std parity.
- Path rejection and `OPERATION_IN_PROGRESS` behavior covered by named tests.
- `git add` allowlist: no extra flags in std adapter.
- Host IPC allowlist + command implementation pattern matches ALL-STAGE.

## Outcome

**CHANGES_REQUESTED** — implementation quality for the port/host/adapter slice is **sound**, but **Tauri default capabilities omit FILE-STAGE**, and **CI guard / board traceability** are not merge-ready. After must-fix items, high-tier re-review can move to **PASS** without architectural replan.