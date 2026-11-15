# PD-GIT-CHERRY-PICK-01 — High-tier review

**Verdict: CHANGES_REQUIRED**

Date: 2026-11-15T10:45:00+08:00  
PR: https://github.com/roy791202/AIAD/pull/88 (`feat(git): gated cherry-pick via GitWritePort`)  
Implementation HEAD: `e49b53ea88b52b2d88486b35cef7b9af2f65f276`  
TDD review HEAD: `ea35629` on `docs/PD-GIT-CHERRY-PICK-01-tdd-review`

| Role | Identity | Same conversation? |
|---|---|---|
| Implementer | `cursor-cloud-dev-PD-GIT-CHERRY-PICK-01` | No |
| Independent TDD verifier | `cursor-cloud-tdd-PD-GIT-CHERRY-PICK-01` | No |
| Independent high-tier reviewer (this agent) | `cursor-cloud-high-tier-PD-GIT-CHERRY-PICK-01` | No |

This agent did **not** implement, did **not** run the TDD-verifier session, and did **not** modify product code, tests, `.feature` files, hooks, or `docs/board.json`. Identities differ; acceptance identity rule holds.

Independent TDD report (`reports/dispatch-pd/PD-GIT-CHERRY-PICK-01-TDD-REVIEW.md`) is **TDD_PASS** for adapter 3/3 and host 5/5. That Green is accepted as scoped workspace evidence only. This review does **not** upgrade `src-tauri` / UI **NOT RUN** to PASS.

## Verdict summary

Port/adapter/host slice is architecturally sound: approval gate, occupying lease before `GitWritePort`, `git cherry-pick -- <oid>` only, honest failures, no skipped tests, board not Done/blue. **Merge is blocked** because the in-scope ADV-CHERRY live path cannot invoke the command under Tauri ACL (`host.toml` has no `git_write_cherry_pick` permission and `host-default` does not grant it). AI Dev Guard also failed on this PR.

## Independent checks (this review)

| Check | Source | Result |
|---|---|---|
| Architecture inward deps | `sgenaxis-ports` Cargo.toml empty of OS/Tauri; adapters depend on ports; host composes adapters; src-tauri commands call host | **PASS** |
| `GitWritePort.cherry_pick` contract | `apps/sgenaxis-desktop/crates/sgenaxis-ports/src/git.rs` | **PASS** — `git cherry-pick -- <oid>`; never `--ff` / `-n` / `--no-commit` / `--continue` / `--skip` / `--abort` / `-x` / `--force`; never rebase; never push |
| `StdGitWrite::cherry_pick` | `std_git_write.rs` | **PASS** — `require_approval` then `run(repo, &["cherry-pick", "--", source])` only |
| `FakeGitWrite::cherry_pick` | `fake.rs` | **PASS** — denied / missing / dirty / option-like refuse without recording; granted records oid + one commit, `push_count` 0 |
| `GatedGitWrite` | `git_write.rs` | **PASS** — always `PermissionDenied` even when approved |
| Occupying lease before port | `git_cherry_pick.rs` + host tests + `commands::git_write_cherry_pick` | **PASS** — occupying Run refuses before `write.cherry_pick`; `last_cherry_pick` stays none |
| Approval gate | host `perform_git_cherry_pick` + adapters | **PASS** — denied never mutates |
| Honest failures | Fake + Std tests for missing oid, dirty overwrite, `-n` / `--ff` / `--continue` | **PASS** |
| No skipped tests | focused cherry_pick tests have no `#[ignore]` / skip | **PASS** |
| Board not Done / not blue | `docs/board.json` Task `PD-GIT-CHERRY-PICK-01` | **PASS** — status `In Review`, light Green, Story `Todo`/Gray |
| IPC allowlist | `sgenaxis-host::ipc` + `src-tauri` `is_allowed` | **PASS** — `git_write_cherry_pick` allowed; `git_cherry_pick` rejected |
| ADV-CHERRY UI path | `ui/app.js`, `ui/git-ux-mock.js` | **PASS at code level** — live hook → `showGitApprove("cherry-pick")` → `invoke("git_write_cherry_pick")`; mock rejects option-like oids |
| Tauri capability `host.toml` | `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` + `capabilities/default.json` | **FAIL** — see must-fix #1 |
| No skipped / weakened assertions | PR diff + TDD review | **PASS** for this slice |
| Hooks / CI config | PR file list | **PASS** — no `.ai-hooks` / `.githooks` / workflow edits |
| CI @ PR #88 head | GitHub Actions on `e49b53e` | **guard failure**; **rust-windows failure** (unrelated `tests_git02` temps); Ubuntu `tests` + `lint + test subset` success |

## Layering

| Layer | Artifact | Direction |
|---|---|---|
| Port | `GitWritePort::cherry_pick` | Contract only; no OS ✓ |
| Adapters | `StdGitWrite`, `FakeGitWrite`, `GatedGitWrite` | Implement port; std is the only CLI; fake records; gated denies ✓ |
| Application | `sgenaxis_host::perform_git_cherry_pick` | Occupying + approval + oid scope; no git CLI in host ✓ |
| API / IPC | `git_write_cherry_pick` + `AllowedIpcCommand::GitWriteCherryPick` | Authorize then host use-case ✓ |
| Tauri ACL | `permissions/host.toml` `host-default` used by `capabilities/default.json` | **Missing command permission** ✗ |
| Rendering | ADV-CHERRY in `git-ux-mock.js` + `app.js` approve/invoke | Presentation; no git CLI ✓ |

No skip-layer: UI does not call adapters; host does not shell out; ports do not import adapters/host/Tauri.

## Git invocation hygiene

`StdGitWrite::cherry_pick` is a single argv shape:

```text
git -C <repo> cherry-pick -- <oid>
```

`--` stops option parse. No `--ff`, `-n`, `--no-commit`, `--continue`, `--skip`, `--abort`, `-x`, `--force`, rebase, or push. Std integration test asserts new HEAD ≠ source (no `--ff` shortcut), single-parent commit (not a merge), no `rebase-merge` / `rebase-apply` / leftover `CHERRY_PICK_HEAD`, dirty overwrite fails with worktree preserved.

Host occupying check uses `occupying_run_for_git_switch()` (WORK projection / active run / lease) and returns `活動租約禁止 cherry-pick` **before** the port. Denied approval also never calls the port.

## File scope vs dispatch allow-list

PR #88 files (18):

- Allowed: `sgenaxis-ports/src/git.rs`, adapters `std_git_write.rs` / `fake.rs` / `git_write.rs` / `tests_git.rs` / `tests_git02.rs`, host `git_cherry_pick.rs` + `ipc.rs` + `lib.rs`, src-tauri command/dto/lib, `ui/app.js`, `ui/git-ux-mock.js`, `docs/bdd/PD-GIT-CHERRY-PICK-01.feature`, `docs/board.json`
- **Out of this Task's unique slice (from dispatch commit `d8ec940` also on the PR):** `docs/bdd/PD-GIT-MERGE-FF-01.feature`, `docs/bdd/PD-GIT-REPO-INIT-01.feature`
- **Not present:** `reports/dispatch-pd/PD-GIT-CHERRY-PICK-01.md` (implementer evidence); `host.toml` (explicitly outside allow-list — see finding)

No product-code change by this reviewer.

## BDD / TDD trace

BDD: `docs/bdd/PD-GIT-CHERRY-PICK-01.feature` (01-1 denied; 01-2 approved one commit, no rebase/push/--ff; 01-3 missing oid / dirty overwrite / option-like fail without mutation).

| ID | Independent TDD | High-tier code match |
|---|---|---|
| PD-GIT-CHERRY-PICK-01-1 | HOLD (Fake/Std/host denied) | Holds |
| PD-GIT-CHERRY-PICK-01-2 | HOLD (Fake/Std/host approved, no push/ff/rebase) | Holds |
| PD-GIT-CHERRY-PICK-01-3 | HOLD (missing / dirty / `-n` `--ff` `--continue`) | Holds |

Extra Green (not numbered BDD): occupying lease; `GatedGitWrite`; IPC allow `git_write_cherry_pick` / reject `git_cherry_pick`.

Historical Red-before-Green was **not** independently replayed (same limit as TDD review). `src-tauri` test `git_write_cherry_pick_gated_and_allowlisted` and desktop ADV-CHERRY click-path remain **NOT RUN**.

## Board

Task `PD-GIT-CHERRY-PICK-01`: `In Review`, light Green, `tdd` Green, `ci` None, hours 4, no storyPoints, parent `S-GIT-WRITE-CHERRY-PICK-01`. Story stays Todo/Gray. **Not Done. Not blue.** Owner remains the implementer; this reviewer does not set Done.

Mismatch: light is Green while PR CI `guard` and `rust-windows` failed. `ci` is still `None` (TDD verifier did not claim CI Green). Per board rules, failed CI with a Green light is a process mismatch — recorded as should-fix, not a Done/blue violation.

## CI (PR #88, head `e49b53e`)

| Job | Conclusion | Notes |
|---|---|---|
| tests | success | Ubuntu subset |
| lint + test subset | success | |
| guard (AI Dev Guard) | **failure** | (1) `.feature` files added without `spec-change` label — includes this Task **and** MERGE-FF / REPO-INIT from the queue commit; (2) test-disable scan `unterminated JavaScript template` (pre-existing `app.js` parse, also seen on sibling PRs) |
| rust-windows | **failure** | 4 failures in `tests_git02::std_write_temp` (add/remove remote, conflict continue, set-remote-url) — **not** the cherry_pick test; slice tests in that job were ok |

## Finding: missing `host.toml` capability (still true)

`apps/sgenaxis-desktop/src-tauri/permissions/host.toml` has **no** `allow-git-cherry-pick` (or any) permission whose `commands.allow` includes `git_write_cherry_pick`. The `host-default` set lists `allow-git-pull-ff` / `allow-git-conflict` / etc., but not cherry-pick. `capabilities/default.json` grants only `host-default` plus unrelated sets.

Neighboring git-write slices (stage-all, unstage-all, pull-ff, conflict) added both a permission atom **and** `host-default` membership. Without that, live ADV-CHERRY `invoke("git_write_cherry_pick")` is rejected by Tauri ACL even though:

- the command is registered in `src-tauri/src/lib.rs`
- host IPC `is_allowed("git_write_cherry_pick")` is true
- UI approve → invoke path exists

Dispatch allow-list omitted `host.toml`, so the implementer correctly did not edit it. That does **not** make the desktop path complete. High-tier treats this as a **must-fix** (expand allow-list / follow-up Task), not a Pass-with-footnote.

## Must-fix (blocking)

1. **Tauri capability:** Add `allow-git-cherry-pick` (commands.allow = `git_write_cherry_pick`) to `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` and append it to `host-default.permissions`. Expand the Task allow-list if needed. Until then ADV-CHERRY cannot run in a built app.
2. **AI Dev Guard spec-change:** PR #88 adds `.feature` files. Either add the `spec-change` label and CODEOWNERS review, or drop `PD-GIT-MERGE-FF-01.feature` / `PD-GIT-REPO-INIT-01.feature` from this PR so it maps to a single Task. Guard currently fails merge.

## Should-fix (non-blocking)

1. Host `cherry_pick_oid_out_of_scope` is a weaker duplicate of `git_write::cherry_pick_oid_out_of_scope` (missing `..` / `@{` / glob / `~^:`). Adapter still refuses; unify or reuse the adapter helper so host fail-fast matches.
2. Attach implementer evidence `reports/dispatch-pd/PD-GIT-CHERRY-PICK-01.md` on the implementation branch (404 on PR head).
3. Re-run `cargo test -p sgenaxis-desktop --lib git_write_cherry_pick` where WebKit/GTK exist; keep NOT RUN until then.
4. rust-windows `tests_git02` failures are pre-existing / out of slice; do not treat as this Task's TDD Red.
5. Board: set `ci` to match Guard failure (Yellow + `lightReason`) until Guard is green; do not set Done/blue.
6. Investigate test-disable JS parse of `app.js` so Guard is trustworthy (pre-existing; not introduced solely by this diff).

## What passed (do not rework)

- Hexagonal `GitWritePort.cherry_pick` with Std / Fake / Gated parity.
- Approval denied → no mutation; occupying lease refuses before the port.
- Std argv is only `cherry-pick -- <oid>`; tests prove no `--ff` shortcut, no rebase dirs, no push.
- Missing oid, dirty overwrite, and option-like names fail honestly.
- Host IPC allowlist + UI ADV-CHERRY approve/invoke wiring (capability excepted).
- No `#[ignore]` / skip on this slice; board not Done / not blue.
- Reviewer / implementer / TDD verifier are three different agents.

## Outcome

**CHANGES_REQUIRED** — adapter/host/port behavior for PD-GIT-CHERRY-PICK-01-1/2/3 is sound and independently TDD Green, but the ADV-CHERRY production invoke is not authorized in `host.toml`, and AI Dev Guard is red. After must-fix #1 and #2, high-tier re-review can move to **PASS** without architectural replan. Do not merge. Do not set Done/blue.
