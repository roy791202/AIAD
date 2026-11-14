# PD-GIT-RENAME-BRANCH-01 — High-tier review (section B)

**Verdict:** **NOT RUN**

No dedicated implementation pull request exists for PD-GIT-RENAME-BRANCH-01. Architecture PASS / CHANGES_REQUIRED is therefore withheld. Reviewer did **not** merge, did **not** set Done/Blue, and did **not** change product code or `docs/board.json`.

**Date (UTC):** 2026-11-14  
**Reviewer:** independent high-tier (this agent). **Not** the implementer. **Not** the TDD verifier.

## Identity

| Role | Identity | Same as reviewer? |
|------|----------|-------------------|
| Implementer (ticket) | Cloud agent `Implement RENAME-BRANCH` (`bc-4bc78f14-b9af-5063-8874-ed769e9c764e`) still **RUNNING**, no branch/PR recorded | No |
| TDD verifier | Cloud agent `TDD review RENAME-BRANCH` (`bc-52184c07-2967-57af-90f0-26c936433e1c`) | No |
| High-tier | This review | — |

Acceptance would be invalid if implementer and verifier were the same agent. They are not. This review does not substitute for merge.

## Why NOT RUN (impl PR missing)

Searched GitHub `roy791202/AIAD` at review time:

| Query | Result |
|-------|--------|
| PRs mentioning `PD-GIT-RENAME-BRANCH-01` / `rename-branch` / `rename_branch` | **#57** only (`chore(board): next batch delete-branch, rename-branch, CX/M03 document fixes`) — dispatch, not impl |
| Branch `feature/PD-GIT-RENAME-BRANCH-01-*` | **None** (no create-branch / high-tier-review except this docs branch) |
| Open PRs titled `feat(git):` for rename | **None** |
| Commit `2a3f4f2` (`feat(git): gated local branch rename via git branch -m`) | On `main`; landed via mega-merge **PR #1**, not a one-Task PR for this ticket |

Sibling CREATE-BRANCH was reviewed against dedicated impl PR #49 (`feature/PD-GIT-CREATE-BRANCH-01-create-branch`). Rename has no equivalent. Instruction: **if impl PR missing, NOT RUN.**

Do not treat PR #57 or PR #1 as the Task impl PR.

## Ticket axes (not scored — no impl PR)

The following is **context from `main` @ `98355b1`**, not a PASS. Re-run against the Task PR when it exists.

Port (`GitWritePort::rename_branch`): `git branch -m -- <old> <new>`. Never `-M` / `--force` / `-f`. Never remote rename. Never switch/checkout as a separate step. Existing target, missing local, remote-only, invalid names fail honestly.

| Axis | On `main` (informational) |
|------|---------------------------|
| `-M` / `--force` | Std argv is `["branch", "-m", "--", old, new]` only. Names `-M` / `-m` / `--force` fail `branch_name_out_of_scope` as `PortError::Other` **before** git. Existing target: pre-check `refs/heads/<new>` then git `-m` (not `-M`). Fake/std tests cover `-M` as a name. |
| Remote rename | Local `refs/heads/<old>` required. Remote-only `refs/remotes/<old>` → `refusing remote-only name`. Fake `mark_remote_only` + std worktree tests. No `git remote rename`. |
| Switch as side effect | No `checkout` / `switch` in the adapter. Non-current rename: std asserts HEAD stays `main`. Renaming current: git `-m` updates HEAD name (`main`→`trunk`) as git's built-in `-m` of HEAD — **not** a separate switch. Fake only updates `switched` if it already equalled `old`. |
| Occupying Run | **Host** `perform_git_rename_branch`: if renaming current HEAD and `occupying_run` is set, refuse with `ACTIVE_LEASE_BLOCKS_SWITCH` and **do not** call `GitWritePort`. Non-current rename allowed while occupied. Adapter itself has no lease (same split as switch). |

Layering on `main`: UI → Tauri `git_write_branch_rename` → host `perform_git_rename_branch` → `GitWritePort`. Adapters do not import host. `GatedGitWrite::rename_branch` always `PermissionDenied` even if `granted()`.

These notes **do not** upgrade this verdict to PASS. They are for the next high-tier pass on a real Task PR.

## Findings

### Must-fix for this architecture review

1. Open a dedicated impl PR (`feature/PD-GIT-RENAME-BRANCH-01-<slug>`) for this Task, then re-dispatch high-tier. Until then: **NOT RUN**.

### Blocking for merge / Done (not architecture FAIL)

1. No Task-scoped impl PR → cannot attach Guard/TDD/CI evidence to this ticket.  
2. Do not set Done/Blue from this review.  
3. Do not treat `main` already containing `rename_branch` as Task completion.

### Suggestions (non-blocking)

1. When the impl PR is TDD-lock-only (like CREATE-BRANCH #49), still point reviewers at that PR, not at `main`.  
2. Occupying-Run coverage lives in host `git_rename.rs`, not in `StdGitWrite`; keep that split explicit on the Task card.

## Decision

**NOT RUN** — implementation PR for PD-GIT-RENAME-BRANCH-01 is missing.

Do **not** merge this as product work. Do **not** set Done/Blue. Re-review when a dedicated impl PR exists.

**Evidence path:** `reports/dispatch-pd/PD-GIT-RENAME-BRANCH-01-HIGH-TIER-REVIEW.md`  
**Dispatch PR (not impl):** https://github.com/roy791202/AIAD/pull/57
