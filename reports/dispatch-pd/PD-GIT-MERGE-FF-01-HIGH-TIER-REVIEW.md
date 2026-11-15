# PD-GIT-MERGE-FF-01 — Independent high-tier review

**Verdict:** **CHANGES_REQUIRED**

**Date (UTC):** 2026-11-15T02:40:00Z  
**Reviewer:** `independent-high-tier-PD-GIT-MERGE-FF-01` (high-tier; did **not** implement; did **not** run TDD verification)  
**Implementer (per board):** `cursor-cloud-dev-PD-GIT-MERGE-FF-01`  
**TDD verifier (separate):** `independent-tdd-PD-GIT-MERGE-FF-01` — `reports/dispatch-pd/PD-GIT-MERGE-FF-01-TDD-REVIEW.md` on `docs/PD-GIT-MERGE-FF-01-tdd-review` @ `9dc150f`

**PR:** https://github.com/roy791202/AIAD/pull/91  
**Implementation branch:** `feature/PD-GIT-MERGE-FF-01-merge-ff-only` @ `1f4c64bc9e0e156a14a0b0fef217eadb32708be5` (feat `a79f59b`)  
**TDD branch:** `docs/PD-GIT-MERGE-FF-01-tdd-review` @ `9dc150f` (review file only; product sources unchanged)  
**BDD:** `docs/bdd/PD-GIT-MERGE-FF-01.feature` — `PD-GIT-MERGE-FF-01-1` / `01-2` / `01-3`

Reviewer did **not** modify product code, tests, `.feature`, hooks, CI, or `docs/board.json`. Did **not** merge PR or set Done / blue.

## Identity separation

| Role | Agent | Valid for acceptance? |
|------|--------|------------------------|
| Implementation | `cursor-cloud-dev-PD-GIT-MERGE-FF-01` | — |
| TDD re-run | `independent-tdd-PD-GIT-MERGE-FF-01` | Workspace **TDD_PASS**; `src-tauri` **NOT RUN** |
| High-tier review | `independent-high-tier-PD-GIT-MERGE-FF-01` | This document |

Three identities are distinct. Independent TDD is accepted as workspace evidence only; implementer self-GREEN is **not** used as pass evidence.

## Independent checks (this review)

| Check | Source | Result |
|-------|--------|--------|
| PR #91 files | 16 files, +866 / −11 | Port/adapter/host/Tauri/UI + `.feature` + board. **`permissions/host.toml` not in the diff** |
| `StdGitWrite::merge_ff_only` argv | `std_git_write.rs` | `run(repo, &["merge", "--ff-only", "--", name])` only |
| Local `refs/heads` | `reject_remote_tracking_source` | `show-ref --verify --quiet refs/heads/{branch}`; remote-tracking / `origin/…` refuse without fetch |
| Occupying lease | `git_merge.rs` + Tauri command | HOST refuses with `活動租約禁止合併` **before** `GitWritePort` |
| Approval | Fake/Std/Gated + HOST | Denied → `PermissionDenied` / refuse DTO; gated adapter denies even when granted |
| Honest failures | Fake + Std tests | Diverged, `--no-ff`, `-X`, missing name, remote-tracking: error, HEAD unchanged |
| Tauri ACL | `src-tauri/permissions/host.toml` | **Missing** `git_write_merge_ff_only` — **CHANGES_REQUIRED** |
| Board | `docs/board.json` `PD-GIT-MERGE-FF-01` | **In Review / Green**; **not** Done / blue |
| Independent TDD | TDD review file | 01-1 / 01-2 / 01-3 **TDD_PASS**; `src-tauri` **NOT RUN** |
| CI @ PR head `1f4c64b` | GitHub Actions | `tests` + `lint + test subset` success; **`guard` failure**; **`rust-windows` failure** (unrelated 4 tests) |

## BDD alignment (behavior)

| Requirement | Evidence | Assessment |
|-------------|----------|------------|
| Denied approval does not merge (01-1) | `require_approval`; Fake `last_merge_ff_only` none; Std HEAD unchanged, parent count &lt; 2; HOST unapproved path never calls port | **Met** |
| Approved `git merge --ff-only -- &lt;local-branch&gt;` moves HEAD (01-2) | Std argv is exactly that tuple; HEAD equals topic tip; parent count &lt; 2 | **Met** in adapters/host |
| Never `--no-ff` / `-X` / `--squash` / pull / rebase / push | Name validators (`merge_branch_out_of_scope`, `branch_name_out_of_scope` starts with `-`); argv has no extra flags; Fake asserts no fetch/pull/push | **Met** |
| Local `refs/heads` only; remote-tracking does not fetch | `refs/heads/{name}` verify first; else refuse `remote-tracking` / not found | **Met** |
| Occupying Run/lease refuses at HOST; port not called (01-3) | `perform_git_merge_ff_only` returns `ACTIVE_LEASE_BLOCKS_MERGE` before `write.merge_ff_only`; tests assert `last_merge_ff_only` none | **Met** |
| Honest failures: diverged, flags, missing names | Fake+Std expect_err; HEAD unchanged; no invented branch | **Met** |
| UI BRANCH-MERGE → `git_write_merge_ff_only` | `app.js` confirm + invoke | Code-level **Met**; **runtime invoke blocked by missing ACL** |

## Layering (ports → adapters → host → Tauri → UI)

| Layer | Artifact | Direction / notes |
|-------|----------|-------------------|
| Port | `GitWritePort::merge_ff_only` | Contract: ff-only local branch; never `--no-ff`/`-X`/squash/pull/rebase/push/fetch. Inward ✓ |
| Adapters | `StdGitWrite`, `FakeGitWrite`, `GatedGitWrite` | Std runs git; Fake records; Gated default-deny even when approved ✓ |
| Application | `sgenaxis-host::git_merge::perform_git_merge_ff_only` | Empty / unapproved / occupying short-circuit; no git CLI in host ✓ |
| API / IPC | `AllowedIpcCommand::GitWriteMergeFfOnly`; `authorize("git_write_merge_ff_only")` | Host allowlist extended; raw `git_merge` / `git_merge_ff_only` rejected ✓ |
| Tauri ACL | `permissions/host.toml` `host-default` | **No** `allow-git-merge-ff` (or equivalent) and **no** `git_write_merge_ff_only` in any `commands.allow`. Neighbor `allow-git-pull-ff` **is** present. **Defect** |
| Rendering | `ui/app.js` BRANCH-MERGE | Presentation + existing approve pattern; no business rules beyond client-side flag reject ✓ |

No skip-layer or domain-in-UI violation. Host does not spawn git. Occupying lease is injected from WORK projection / dispatch, not from the adapter.

## ACL / allowlist

- **Host IPC:** `git_write_merge_ff_only` is on `AllowedIpcCommand`, `is_allowed`, and `authorize`. Tests assert the raw names `git_merge` and `git_merge_ff_only` stay off the list.
- **Tauri capabilities:** `capabilities/default.json` grants `host-default`. That set includes `allow-git-pull-ff` (`git_write_pull_ff_only`) and does **not** include any permission whose `commands.allow` lists `git_write_merge_ff_only`. PR #91 does not touch `host.toml`.
- **Consequence:** A built app will refuse `invoke("git_write_merge_ff_only", …)` at the capability layer even though the handler is registered in `lib.rs`. **Missing ACL is CHANGES_REQUIRED.**

Required fix (implementer, not this review): add a permission atom (mirror `allow-git-pull-ff`), e.g. `allow-git-merge-ff` with `commands.allow = ["git_write_merge_ff_only"]`, and append that identifier to `host-default.permissions`.

## Git invocation hygiene

- Single write argv after approval + local-ref checks: `git -C <repo> merge --ff-only -- <name>` via `Command::new` (no shell).
- `--` stops option parse; names starting with `-` (`--no-ff`, `-X`) are rejected before spawn.
- Probe commands used for local-vs-tracking (`show-ref --verify --quiet`, `remote`) are read-only; they are not pull/rebase/push/`--no-ff`/`-X`/`--squash`.
- Gated adapter never reaches git.

## File scope

PR #91 paths: adapters (`fake`, `git_write`, `std_git_write`, tests), host (`git_merge.rs` new, `ipc`, `lib`), ports `git.rs`, Tauri `commands`/`dto`/`lib`, UI `app.js`/`git-ux-mock.js`, `docs/bdd/PD-GIT-MERGE-FF-01.feature`, `docs/board.json`.

No edits to `.ai-hooks`, `.githooks`, or `.github/workflows`. `.feature` is **new** (guard requires `spec-change`). `host.toml` was **not** updated.

## Clean Code / production readiness (slice)

- **Strengths:** Mirrors pull-ff / branch-create shape; occupying lease stays in HOST; DTO `GitWriteMergeFfOnlyArgs` documents negatives; errors are `Result` / refuse DTO (no fake success); credential redaction reused on `run`.
- **Minor (non-blocking):** Std tests assert HEAD / parent-count rather than spawned argv (source argv is still exact). Fake `last_merge_ff_only` records the name, not argv. Tauri `reject_merge_source_scope` duplicates adapter scope checks (defense in depth, not over-design).
- **Process:** Feat commit lands tests+impl together; no checked-in RED log (TDD review already flagged). Board `ci` is `None` while GitHub CI has mixed results; `prUrl` is unset.

## TDD acceptance (from separate verifier)

Accept workspace **TDD_PASS** per `independent-tdd-PD-GIT-MERGE-FF-01`:

- adapters `merge_ff_only` **2/2**
- host `git_merge::` **4/4**
- host `ipc::tests` **3/3** (allowlist includes `git_write_merge_ff_only`)
- extra gated deny **1/1**
- `src-tauri` `git_write_merge_ff_only_gated_and_allowlisted`: **NOT RUN** (Cargo 1.83 / `edition2024`)

High-tier does **not** upgrade NOT RUN to PASS. TDD review file is on `docs/PD-GIT-MERGE-FF-01-tdd-review`, not on PR #91 head.

## Board

| Field | Value | Assessment |
|-------|--------|------------|
| status | In Review | Allowed for READY_FOR_TDD; developer did not set Done ✓ |
| light | Green | Not blue ✓ |
| tdd | Green | Implementer self-mark; independent TDD is the evidence |
| ci | None | Stale vs GitHub (guard fail) — note only |
| prUrl | absent | Should-fix |
| storyPoints | absent | Task uses hours ✓ |
| parentId | PD-GIT-02 | Present ✓ |

**Board is not Done / not blue.** This check does **not** drive the verdict.

## CI / merge readiness

| Check | Status | Notes |
|-------|--------|-------|
| AI Dev Guard | **Fail** | New `.feature` without `spec-change` label; test-disable scan `unterminated JavaScript template` (app.js; not shown to be unique to this slice) |
| rust-windows full lib | **Fail** | Unrelated `tests_git02::std_write_temp` remote/conflict tests (`/bin/true` editor); **not** `merge_ff_only` |
| Ubuntu tests / lint subset | Pass | |

## Must-fix (blocking)

1. **Tauri `host.toml` ACL for `git_write_merge_ff_only`.** Add a permission whose `commands.allow` lists `git_write_merge_ff_only` and include it in `host-default`. Missing ACL is **CHANGES_REQUIRED**. Without this, BRANCH-MERGE cannot invoke the command in a capability-enforced build.
2. **Guard / spec-change:** PR adds `docs/bdd/PD-GIT-MERGE-FF-01.feature`. Apply the `spec-change` label (and CODEOWNERS review) or Guard stays red.

## Should-fix (not architecture)

1. Re-run `src-tauri` `git_write_merge_ff_only_gated_and_allowlisted` on a toolchain that parses `edition2024`; attach log. Do not treat NOT RUN as PASS.
2. Set board `prUrl` to PR #91 and `ci` to match GitHub (guard fail until #2). Stay In Review / not Done / not blue.
3. Put independent TDD review on the implementation PR (or merge the docs TDD branch) so PR evidence is self-contained.
4. Optional: RED-before-GREEN log or split test/impl commits on a follow-up.

## What passed (do not rework)

- `GitWritePort.merge_ff_only` argv is `git merge --ff-only -- <local-branch>` only.
- No `--no-ff`, `-X`, squash, pull, rebase, or push in the write path.
- Local `refs/heads` only; remote-tracking names refuse without fetch.
- Occupying lease refused in HOST before the port.
- Approval gate and honest failures (diverged / flags / missing / remote-tracking).
- Hexagonal layering; gated default-deny; board not Done/blue.
- Independent TDD workspace GREEN for 01-1 / 01-2 / 01-3.

## Outcome

**CHANGES_REQUIRED** — adapter/host behavior for the three BDD scenarios is sound, but **Tauri `host.toml` does not allow `git_write_merge_ff_only`**. After the ACL (and spec-change label) are fixed by the implementer, high-tier re-review can move to **PASS** without architectural replan.
