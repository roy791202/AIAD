# PD-GIT-RENAME-BRANCH-01 — High-tier review (section B)

**Verdict:** **PASS**

Architecture, layering, `GitWriteApproval` gating, `git branch -m -- <old> <new>` only, never `-M` / `--force` / `-f`, never remote rename, never switch/checkout as a separate step, occupying Run on current HEAD refusing **before** the port, and no skip tests all hold on impl PR **#59** (contract on `main` + TDD lock on the PR). Independent TDD (#58, re-run after #59 existed) reported **TDD_PASS** (adapters rename 2/2 + gated 1/1 + host `git_rename` 4/4; 0 failed). Reviewer did **not** merge, did **not** set Done/Blue, and did **not** change product code or `docs/board.json`.

Prior verdict on this docs PR (#65) was **NOT RUN** because no Task impl PR existed. That is superseded.

**Date (UTC):** 2026-11-14  
**Reviewer:** independent high-tier (this agent). **Not** the implementer. **Not** the TDD verifier.  
**Impl PR:** https://github.com/roy791202/AIAD/pull/59  
**Compare:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-RENAME-BRANCH-01-rename-branch  
**Implementation branch:** `feature/PD-GIT-RENAME-BRANCH-01-rename-branch` @ `f314160b5450fd1866d23a8c0479fdc40f639b09`  
**Base:** `main` @ `98355b1891b0a3cbe1e4697eeced2df457fe6ef9`  
**Commit:** `test(git): cover remote-only branch rename refusal` (Conventional Commits)  
**Docs PR:** https://github.com/roy791202/AIAD/pull/65

## Identity

| Role | Identity | Same as reviewer? |
|------|----------|-------------------|
| Implementer | Cursor Agent on `feature/PD-GIT-RENAME-BRANCH-01-rename-branch` (PR #59, `cursor[bot]` / `bc-4bc78f14-…`) | No |
| TDD verifier | Independent TDD Gate `bc-52184c07-…` — **TDD_PASS** on SHA `f314160` after PR existed (PR #58 updated) | No |
| High-tier | This review | — |

Acceptance would be invalid if implementer and verifier were the same agent. They are not. This review does not substitute for merge.

## Scope (PR #59 files)

2 files, +99 / −0. **No** `docs/board.json`. **No** `.feature`. **No** `.ai-hooks` / `.githooks` / `.github/workflows`. **No** skip / ignore / `only`.

| Path | Role |
|------|------|
| `sgenaxis-adapters` `tests_git02.rs` | Std worktree TDD lock: empty new name, `--force` name, remote-only `refs/remotes/origin/only-remote` (must not invent a local branch) |
| `reports/dispatch-pd/PD-GIT-RENAME-BRANCH-01.md` | Implementer evidence (not product) |

Allowed-file set is the TDD-lock slice. Product adapters (`fake.rs`, `std_git_write.rs`, `GatedGitWrite`), port, host `git_rename.rs`, and Tauri `git_write_branch_rename` were **not** rewritten on this PR; they already implement the contract on `main` (`2a3f4f2`). That is in-scope for a lock-TDD task (same pattern as CREATE-BRANCH #49). Architecture review therefore covers **PR #59 + inherited `main` contract**, not `main` alone.

## Layering (外 → 內)

| Layer | Artifact | Direction |
|-------|----------|-----------|
| Rendering / API | UI `invoke("git_write_branch_rename")` → Tauri ACL `allow-git-write-branch-rename` → `authorize()` | No business rules in UI beyond approval modal |
| Command | `git_write_branch_rename` → `perform_git_write_branch_rename` | Soft-gate names via `reject_branch_scope`; occupying Run from dispatch |
| Application | Host `perform_git_rename_branch` | Empty / unapproved / detached HEAD / occupying Run on **current** HEAD refuse **before** `GitWritePort` |
| Port | `GitWritePort::rename_branch` | Documents `git branch -m -- <old> <new>`; never `-M` / `--force` / `-f`; never remote rename; never switch as a separate step |
| Adapter (std) | `StdGitWrite::rename_branch` | `require_approval` → `require_branch_name` both sides → local `refs/heads/<old>` (else remote-only or not found) → refuse existing `refs/heads/<new>` → `run(["branch", "-m", "--", old, new])` only |
| Adapter (fake) | `FakeGitWrite::rename_branch` | Denied → `PermissionDenied` before record. Granted → local list rename; remote-only marked refs refused; does not set `switched` unless already equal to old |
| Adapter (gated) | `GatedGitWrite::rename_branch` | Always `PermissionDenied(GIT_WRITE_GATED_MSG)` even when `granted()` |

Adapters do not import host/UI. Domain is not involved. `git -C <repo>` in `StdGitWrite::run` is the CLI working-directory flag, **not** `git branch -C` / `-M`.

## GitWriteApproval / default-deny

| Case | Evidence |
|------|----------|
| Fake denied | `fake_git_write_rename_branch_records_when_approved` — `PermissionDenied`; no `last_branch_rename`; local list unchanged |
| Fake granted | Same test — records local old→new only |
| Gated + granted | `gated_git_write_blocks_branch_rename_even_when_approved` — still `GIT_WRITE_GATED_MSG` |
| Std denied | `std_write_rename_branch_non_force_only_when_approved` (PR #59) — `feature/slot` remains; no `feature/renamed` |

## Never `-M` / `--force`; never remote rename; never switch as a side step; occupying Run

Std argv for success is `["branch", "-m", "--", old, new]`. `--` stops option parse. `-M` / `--force` / leading dash names fail `branch_name_out_of_scope` as `PortError::Other` **before** git. Duplicate target: pre-check `refs/heads/<new>` then git `-m` (not `-M`).

PR #59 adds std assertions:

- Empty **new** name fails.
- `--force` as a name is out of scope.
- Remote-only `refs/remotes/origin/only-remote` fails honestly; no local `from-remote` invented.

Inherited (main + Fake, still required for the Task):

- Non-current rename: std `head_ref` stays `main`; Fake `switched_branch` stays `None`.
- Renaming current with **no** lease: git `-m` of HEAD updates the current name (`main`→`trunk`) — git’s built-in `-m` of the checked-out branch, **not** a separate `checkout`/`switch`.
- Occupying Run: host `occupying_run_refuses_rename_of_current_and_does_not_call_git_write`; Tauri helper lease case uses the same `ACTIVE_LEASE_BLOCKS_SWITCH` / 「活動租約禁止切換」 contract. Non-current rename allowed while occupied.

Independent TDD: **TDD_PASS** — 2 adapter rename + 1 gated + 4 host `git_rename`. Filter `pd_git_rename_branch_01` matches **0** tests (names are not prefixed). Tauri command tests **NOT RUN** (edition2024 / Cargo 1.83), not FAIL. No `#[ignore]` / skip on this slice.

## Clean Code / production readiness (slice)

- Guard clauses: approval, name checks, local-ref verify, duplicate target, then git.
- No `unwrap()` on the production `rename_branch` path (tests use `expect` / `unwrap` on temp paths only).
- Credential redaction remains in `StdGitWrite::run` for git stderr (unchanged).
- Name length / git-check-ref-format bounded by git + `branch_name_out_of_scope`.

## Board / CI / TDD (process; not architecture defects)

| Item | Observed | Note |
|------|----------|------|
| `docs/board.json` | **Not** in PR #59 | Guard cannot see a Task card on this PR |
| Guard @ `f314160` | **failure** | Same class as CREATE-BRANCH: no Task card for `feature/PD-GIT-RENAME-BRANCH-01-rename-branch` |
| `tests` / `lint + test subset` | **success** | |
| `rust-windows` | **failure** | Pre-existing sibling std git tests (remote URL / editor); not introduced by this TDD lock |
| Independent TDD | **TDD_PASS** (#58 re-run) | High-tier did not re-run as implementer |
| `.feature` | Unchanged | BDD lives in port comments + named tests |

These **block merge / Done**, not this architecture PASS. Board updates belong on a later board-sync / acceptance step, not on PR #59.

## Findings

### Must-fix for this architecture review

None.

### Blocking for merge / Done (not architecture FAIL)

1. AI Dev Guard: no Task card in `docs/board.json` on the impl PR (by design for this slice).  
2. `rust-windows` red on unrelated std git tests.  
3. Tests are not named `pd_git_rename_branch_01_*`; TDD used `rename_branch` / `git_rename` filters.  
4. Tauri `git_write_branch_rename` lib tests remain **NOT RUN** in verifier environments (Cargo edition).  
5. Do not set Done/Blue from this review.

### Suggestions (non-blocking)

1. Rename std/fake tests to `pd_git_rename_branch_01_*` so the Task filter matches.  
2. Std remote-only assertion allows `not found` **or** `remote`; tightening to the `refusing remote-only name` message would match Fake.

## Decision

**PASS** high-tier architecture review of PD-GIT-RENAME-BRANCH-01 / impl PR **#59**.

Do **not** merge. Do **not** set Done/Blue. Independent TDD is Green for the runnable adapter/host cases; Guard/board remain a separate process step.

**Evidence path:** `reports/dispatch-pd/PD-GIT-RENAME-BRANCH-01-HIGH-TIER-REVIEW.md`  
**Compare URL:** https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-RENAME-BRANCH-01-rename-branch
