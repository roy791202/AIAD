# PD-GIT-DELETE-BRANCH-01 — High-tier code review (GitWritePort.delete_branch)

**Verdict:** **PASS**

**Date (UTC):** 2026-11-14  
**Reviewer:** `independent-high-tier-pd-git-delete-branch-01` (high-tier; did **not** implement; did **not** write product or TDD code)  
**Implementer:** original gated-write author on `d68f743` (`feat(git-workbench): gated local branch delete`), merged to `main` via historical batch (not this dispatch)  
**TDD verifier (separate):** **NOT RUN** — no `feature/PD-GIT-DELETE-BRANCH-01-tdd-review` branch or `PD-GIT-DELETE-BRANCH-01-TDD-REVIEW.md` at review time

**Implementation PR:** **NOT RUN**  
No dedicated `feature/PD-GIT-DELETE-BRANCH-01-*` implementation PR exists. GitHub search (`PD-GIT-DELETE-BRANCH-01`, `gated local branch delete`) returned only dispatch PR https://github.com/roy791202/AIAD/pull/57 (`chore(board): next batch delete-branch…`), which is **not** the product impl. Behavior under review is already on `origin/main`.

**Reviewed ref:** `origin/main` @ `98355b1` (contains `d68f743`)  
**BDD / contract:** `GitWritePort::delete_branch` — approval-gated `git branch -d -- <name>`; never `-D` / `--force` / `-f`; never `-r`; never remote delete; never switch/checkout; current HEAD, missing names, and unmerged branches fail honestly.

This review does **not** set Done / blue and does **not** edit `docs/board.json`.

## Identity separation

| Role | Agent | Valid for acceptance? |
|------|--------|------------------------|
| Implementation | Historical `d68f743` (not this reviewer) | Product already on `main` |
| TDD re-run | Dedicated TDD agent for this ticket | **NOT RUN** (no report) |
| High-tier review | `independent-high-tier-pd-git-delete-branch-01` | This document |

High-tier replayed adapter tests locally; that is **not** a substitute for an independent TDD-acceptance report.

## Independent checks (this review)

| Check | Source | Result |
|-------|--------|--------|
| Fake delete | `cargo test -p sgenaxis-adapters --lib fake_git_write_delete` | **PASS** (`fake_git_write_delete_branch_records_when_approved`) |
| Gated deny | `cargo test -p sgenaxis-adapters --lib branch_delete` | **PASS** (`gated_git_write_blocks_branch_delete_even_when_approved`) |
| Std real git | `cargo test -p sgenaxis-adapters --lib std_write_delete_branch_safe` | **PASS** (`std_write_temp::std_write_delete_branch_safe_only_when_approved`) |
| Tauri IPC unit | `git_write_branch_delete_gated_and_allowlisted` | **NOT RUN** this session (code-read only) |
| Dedicated impl PR | GitHub PR search | **NOT RUN** |
| Independent TDD report | `reports/dispatch-pd/*TDD-REVIEW*` | **NOT RUN** |
| `.feature` / hooks / CI edits | Product tree vs this docs-only branch | N/A (this PR is review markdown only) |

## Force / switch / remote-delete leaks

| Risk | Mechanism | Assessment |
|------|-----------|------------|
| Force delete (`-D` / `--force` / `-f`) | Std argv is **only** `["branch", "-d", "--", branch]`. Names starting with `-` or matching `-D`/`--force`/`-f` fail `branch_name_out_of_scope` **before** git. Command layer `reject_branch_scope` fails closed (String error, no mutation). Tests: `-D` on fake, std, and Tauri perform. | **No leak** |
| Switch / checkout | Std runs `rev-parse --abbrev-ref HEAD` then `branch -d`. No `checkout` / `switch` in argv. Fake asserts `switched_branch` stays `None`. Std asserts `head_ref` remains `main` after success and after unmerged/HEAD failures. | **No leak** |
| Remote-tracking delete (`-r`) | `-r` is rejected as a name (`starts_with('-')` + command tests). No `-r` in argv. | **No leak** |
| Remote delete (`git push --delete` / `git push origin :branch`) | `delete_branch` never calls `push`. Tag/push adapters are separate methods. | **No leak** |
| Option injection after `--` | `--` stops option parse; flag-shaped names never reach git. Path `../evil` rejected (`..`). | **No leak** |

## Honesty of unmerged / HEAD / missing failures

| Case | Behavior | Assessment |
|------|----------|------------|
| Current HEAD | Std compares `rev-parse --abbrev-ref HEAD` to the name and returns `PortError::Other("cannot delete the current HEAD branch")` **before** `-d`. Git would also refuse; no fallback to another branch or `-D`. Tests: `main` while on `main`; fake after `switch_branch`. | **Honest** |
| Unmerged | Std relies on git `-d` (no `-D` retry). Failure mapped via `git_error_redacted` → `PortError::Git` including stderr (`not fully merged`). Branch remains. Fake returns the same Git error string. | **Honest** |
| Missing name | Std/fake `PortError::Git` `not found`; no create-then-delete, no remote fallback. | **Honest** |
| Denied / gated | Denied → `PermissionDenied`, no mutation. `GatedGitWrite` denies even when approved. | **Honest** |

Detached HEAD: `abbrev-ref` is `HEAD`; a real branch name is not treated as current HEAD; deleting `head` as a name is out of scope (`lower == "head"`). Acceptable fail-closed.

## Layering

| Layer | Artifact | Direction |
|-------|----------|-----------|
| Port | `sgenaxis-ports::GitWritePort::delete_branch` | Contract documents `-d` only and honest failures ✓ |
| Adapters | `StdGitWrite`, `FakeGitWrite`, `GatedGitWrite` | CLI only in std adapter; fake in-memory; gated deny ✓ |
| API / IPC | `perform_git_write_branch_delete` + `git_write_branch_delete`; `AllowedIpcCommand::GitWriteBranchDelete` | Approval boolean → `GitWriteApproval`; no git CLI in UI ✓ |
| Tauri ACL | `allow-git-branch-create` includes `git_write_branch_delete`; set `host-default` lists `allow-git-branch-create` | Wired (unlike FILE-STAGE’s missing host-default atom) ✓ |
| Rendering | `ui/app.js` approve → `invoke("git_write_branch_delete")`; copy states `-d`, no `-D`/`-r`, no HEAD delete | Presentation only ✓ |

No domain-layer git CLI. No jump from UI to adapter. Duplicate name filters in command vs adapter are defense in depth, consistent with sibling GitWrite slices — not a coupling defect.

## Clean Code / production readiness (slice)

- Guard clauses: approval → trim → `require_branch_name` → HEAD check → `-d`.
- No `unwrap`/`panic` on expected git failures; `PortError` + redacted stderr.
- Bounded names (no spaces, no `@{`, no `.git` tricks).
- Credential redaction on git errors.
- Function length and argv construction stay small; not over-abstracted.

**Non-blocking:** fake unit tests do not separately assert `-r` (std + command tests do). No fixture asserting `refs/remotes/*` remain after a local `-d` (argv and `-r` rejection make a remote-tracking delete unreachable).

## Must-fix (blocking)

None for `GitWritePort::delete_branch` behavior, layering, or leak surface on `main`.

## Should-fix (not blocking this PASS)

1. Open a dedicated impl PR only if process requires one Task ↔ one PR for **this** ticket ID; product behavior is already merged.
2. Independent TDD agent should attach `PD-GIT-DELETE-BRANCH-01-TDD-REVIEW.md` (replay std/fake/gated + Tauri `git_write_branch_delete_gated_and_allowlisted`).
3. Optional: std fixture that a remote-tracking ref is unchanged after local delete (documentation of the `-r` ban).

## Outcome

**PASS** — `delete_branch` is approval-gated safe local `-d` only; force, switch, and remote-delete paths are not reachable; HEAD / unmerged / missing failures stay honest and non-mutating. Dedicated **implementation PR = NOT RUN**; **independent TDD report = NOT RUN**. Do not mark the Task Done / blue from this review.
