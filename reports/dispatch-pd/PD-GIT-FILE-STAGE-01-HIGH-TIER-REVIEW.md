# PD-GIT-FILE-STAGE-01 — High-tier review (section B)

**Verdict:** **PASS**

Architecture, layering, FILE-STAGE vs CONFLICT-SAVE vs ALL-STAGE, path guards, no `git add -A` / `git add -- .` on this op, no `--force`, and UI → GitWritePort (not UI→CLI) all hold on PR #27.

This is **not** merge / Done approval. Independent TDD remains open; AI Dev Guard currently fails because the Task card `tdd` is not Green. Reviewer did **not** merge, did **not** set Done/Blue, and did **not** change product code.

**Date (UTC):** 2026-11-14  
**Reviewer:** independent high-tier (this agent). **Not** implementer `bc-618e75df`. **Not** the TDD agent.  
**PR:** https://github.com/roy791202/AIAD/pull/27  
**Implementation branch:** `feature/PD-GIT-FILE-STAGE-01-file-stage` @ `58b2e62f6396618aa00cc5ff21544deb38ebed3b`  
**Base:** `main` @ `98355b1891b0a3cbe1e4697eeced2df457fe6ef9`  
**Commit:** `feat(git): gated file-stage via GitWritePort` (Conventional Commits)

## Identity

| Role | Identity | Same as reviewer? |
|------|----------|-------------------|
| Implementer | `bc-618e75df-6cea-5fbe-a610-f49d8fe8b722` (PR body) | No |
| TDD verifier | Independent TDD Gate (still required; not this run) | No |
| High-tier | This review | — |

Acceptance remains invalid until a **separate** TDD agent re-runs tests. Reviewer did not treat implementer “local green” as TDD Green.

## Scope (PR files vs FILE-STAGE slice)

16 files, +553 / −6. No `.feature`, `.ai-hooks`, `.githooks`, or `.github/workflows` edits.

| Path | Role |
|------|------|
| `sgenaxis-ports/src/git.rs` | `GitWritePort::stage_file` contract |
| `sgenaxis-adapters` `git_write.rs` / `std_git_write.rs` / `fake.rs` | Guard, std `git add -- <path>`, fake record |
| `sgenaxis-adapters` `tests_git.rs` / `tests_git02.rs` | Fake/gated + std worktree tests |
| `sgenaxis-host/src/git_stage_file.rs` (+ `lib.rs` / `ipc.rs`) | Application gate + IPC allowlist |
| `src-tauri` `commands.rs` / `dto.rs` / `lib.rs` / `permissions/host.toml` | Thin command, DTO, ACL `allow-git-stage-file` in `host-default` |
| `ui/app.js`, `ui/git-ux-mock.js` | Confirm → `invoke("git_write_stage_file")`; FILE-STAGE hook |
| `docs/board.json` | Task In Review (dev-agent); not Done/Blue |

Allowed-file set matches neighboring git-write slices (ports → adapters → host → Tauri → UI + board). No extra product modules.

## Layering (外 → 內)

| Layer | Artifact | Direction |
|-------|----------|-----------|
| Render | `app.js` `showGitApprove("stage-file")` then `invoke("git_write_stage_file")`; mock `FILE-STAGE` → `liveHooks.stageFile` | Presentation + confirm only. No `git` spawn in UI. |
| API | `git_write_stage_file` → `authorize` → `perform_git_write_stage_file` | Allowlist + DTO; path refuse before port. |
| Application | `perform_git_stage_file` | `approved: false` never calls port; granted → `GitWritePort::stage_file`. |
| Port | `GitWritePort::stage_file` | Documents `git add -- <path>`, never `-A` / `.` / commit / push / hard / force. |
| Adapter | `StdGitWrite` / `FakeGitWrite` / `GatedGitWrite` | Std runs git; fake records; gated always denies. |

Host production path depends on the port trait, not `StdGitWrite`. Host unit tests inject `FakeGitWrite` (same pattern as ALL-STAGE). Tauri does not call adapters’ git CLI except through the port.

## `stage_file` vs `conflict_save` vs `stage_all`

| Op | When | Git | In-progress merge/rebase/cherry-pick/revert |
|----|------|-----|-----------------------------------------------|
| `stage_file` (this task) | One worktree path after approval | `["add", "--", rel]` only | **Fail** `OPERATION_IN_PROGRESS` (`require_conflict_kind` **or** `ls-files -u`). Must **not** mark conflicts resolved. |
| `stage_all` (unchanged) | Entire worktree | `["add", "--", "."]` | Same honest fail; never used by FILE-STAGE. |
| `conflict_save` (unchanged) | One **unmerged** path after markers gone | `["add", "--", rel]` | **Requires** conflict kind; missing conflict fails honestly. |

Std test `std_write_stage_file_adds_one_path_without_commit_or_add_all` asserts `a.txt` staged, `?? new.txt` left, HEAD unchanged, merge worktree still unmerged.

Fake records `last_stage_file` separately from `last_stage_all` / `conflict_save`. Gated adapter still denies `stage_file` even when approved.

## Path guards / no widen

`stage_file_path_out_of_scope` = `conflict_path_out_of_scope` plus absolute / Unix `/` / Windows drive-letter. Rejects empty (adapter), `.`, `..`, `*`, `-…`, NUL/newline/backslash, path parts `.`/`..`, `-A` / `--all` / `--force` / `-f` / `--`.

Std + fake tests cover `-A`, `--all`, `.`, `..`, `../escape`, `/tmp/escape`. Command layer repeats conflict/absolute refuse before host.

**Never in `stage_file`:** `add -A`, `add -- .`, `add --all`, commit, push, `reset --hard`, `--force`. (`commit` still uses `add -A` on that **other** method; FILE-STAGE does not call it.)

## No force / no UI→CLI

- No `--force` / `-f` on FILE-STAGE argv.  
- UI invokes Tauri `git_write_stage_file` only. `git_stage_file` is **not** allowlisted.  
- ACL: `allow-git-stage-file` is in `host-default.permissions` (unlike the earlier STAGE-PATH ACL miss).

## Clean Code / production readiness (slice)

- Mirrors ALL-STAGE host module; functions stay small; approval is a guard clause.  
- Path checks duplicated in Tauri vs adapters (same as conflict-save); not a layering break.  
- Error strings stay generic (`OPERATION_IN_PROGRESS`, out-of-scope); no stack/path leak in the DTO mapping.

## Board / CI / TDD (process; not architecture defects)

| Item | Observed | Note |
|------|----------|------|
| Card | `PD-GIT-FILE-STAGE-01` In Review, light Green, `tdd` **None**, `ci` **None** | Implementer must not set Done/Blue; light Green while TDD/CI None is **optimistic**. Guard: `PD-GIT-FILE-STAGE-01 的 TDD 不是 Green`. |
| `parentId` | `null` | No Story parent on the card. |
| CI @ `58b2e62` | `tests` success; `lint + test subset` success; **`guard` failure**; `rust-windows` in progress at review time | Guard also: `Test-disable guard could not inspect source: unterminated JavaScript template` (pre-existing scan vs `app.js` templates; not introduced as skip/ignore). |
| Implementer evidence | PR cites `reports/dispatch-pd/PD-GIT-FILE-STAGE-01.md` | **Not** in the 16-file PR diff. |
| `.feature` | Unchanged | OK for this slice if BDD lives in port comments + tests (same as sibling git-write tasks). |

These **block merge / Done**, not this architecture PASS. Independent TDD must still re-run and mark Green before acceptance.

## Findings

### Blocking for merge / Done (not architecture FAIL)

1. Independent TDD not Green (`tdd: None`; Guard fail).  
2. Board CI/TDD fields and Green light do not match Guard.  
3. Implementer evidence markdown not on the PR.

### Architecture (PASS)

1. FILE-STAGE is `git add -- <path>` only; ALL-STAGE remains `git add -- .`; CONFLICT-SAVE still requires conflict state.  
2. Deny / gated adapter: no mutation.  
3. Unmerged / in-progress ops: `OPERATION_IN_PROGRESS`, conflicts not resolved.  
4. Option-like, `.`, traversal, absolute paths rejected.  
5. UI → allowlisted command → host → `GitWritePort`; no UI CLI; no `--force` on this op.  
6. `allow-git-stage-file` present on `host-default`.

### Non-blocking

- Task `parentId` is null.  
- Command-layer empty path is not in `conflict_path_out_of_scope`; adapter still rejects empty.  
- Fake `last_stage_file` is last successful path only (same sticky-map pattern as other fakes).

## Decision

**PASS** high-tier architecture review of PD-GIT-FILE-STAGE-01 / PR #27.

Do **not** merge. Do **not** set Done/Blue. Wait for independent TDD Green and Guard Green, then a later acceptance pass.

**Evidence:** this file on `feature/PD-GIT-FILE-STAGE-01-high-tier-review`.
