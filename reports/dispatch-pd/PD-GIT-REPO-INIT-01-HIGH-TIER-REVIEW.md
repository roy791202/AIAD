# PD-GIT-REPO-INIT-01 — High-tier review

**Verdict: CHANGES_REQUIRED**

Date: 2026-11-15T10:55:00+08:00  
PR: https://github.com/roy791202/AIAD/pull/90 (`feat(git): gated git init via GitWritePort`)  
Implementation HEAD: `7002a82293161089220f73cbeec56c2cbac0be63`  
TDD review HEAD: `d1e07c4` on `docs/PD-GIT-REPO-INIT-01-tdd-review`

| Role | Identity | Same conversation? |
|---|---|---|
| Implementer | `cursor-cloud-dev-PD-GIT-REPO-INIT-01` | No |
| Independent TDD verifier | `independent-tdd-PD-GIT-REPO-INIT-01` | No |
| Independent high-tier reviewer (this agent) | `cursor-cloud-high-tier-PD-GIT-REPO-INIT-01` | No |

This agent did **not** implement, did **not** run the TDD-verifier session, and did **not** modify product code, tests, `.feature` files, hooks, or `docs/board.json`. Identities differ; acceptance identity rule holds.

Independent TDD report (`reports/dispatch-pd/PD-GIT-REPO-INIT-01-TDD-REVIEW.md`) is **TDD_PASS** for adapter 10/10 and host `git_repo_init` 3/3 plus IPC allowlist. That Green is accepted as scoped workspace evidence only. This review does **not** upgrade `src-tauri` / UI **NOT RUN** to PASS.

## Verdict summary

Port/adapter/host slice is architecturally sound: `GitWritePort.init_repo` is `git init -- <dir>` only (never clone / `--bare` / `--template` / remote / fetch), approval gate, honest failures, inward deps, no skipped tests, board not Done/blue. **Merge is blocked** because the live REPO-INIT path cannot invoke the command under Tauri ACL (`host.toml` has no `git_write_repo_init` permission and `host-default` does not grant it). Same blocking finding as PD-GIT-CHERRY-PICK-01. AI Dev Guard also failed on this PR (`.feature` without `spec-change`).

## Independent checks (this review)

| Check | Source | Result |
|---|---|---|
| Architecture inward deps | `sgenaxis-ports` Cargo.toml empty of OS/Tauri; adapters depend on ports; host composes via `GitWritePort`; src-tauri commands call host | **PASS** |
| `GitWritePort.init_repo` contract | `apps/sgenaxis-desktop/crates/sgenaxis-ports/src/git.rs` | **PASS** — `git init -- <dir>`; never `--bare` / `--template` / `--separate-git-dir`; never `git clone`; never add a remote; never fetch |
| `StdGitWrite::init_repo` | `std_git_write.rs` | **PASS** — `require_approval` then `Command … ["init", "--", dir]` only; post-check non-bare, empty remotes, git dir contained |
| `FakeGitWrite::init_repo` | `fake.rs` | **PASS** — denied / existing / option-like / URL refuse without recording; granted records non-bare (`true`), remotes empty, push 0 |
| `GatedGitWrite` | `git_write.rs` | **PASS** — always `PermissionDenied` even when approved |
| Approval gate | host `perform_git_repo_init` + adapters + UI cancel | **PASS** — `!approved` returns before `write.init_repo`; cancel does not invoke; denied leaves no `.git` |
| Honest failures | Fake + Std tests for existing repo, `--bare`, `--template`, `--separate-git-dir`, HTTPS / `git@` URLs | **PASS** |
| No clone / remote / fetch in init | `spawn_init` argv + `init_repo_path_out_of_scope` + `assert_non_bare_contained` | **PASS** |
| No skipped tests | focused `init_repo` / `pd_git_repo_init` tests have no `#[ignore]` / skip | **PASS** |
| Board not Done / not blue | `docs/board.json` Task `PD-GIT-REPO-INIT-01` | **PASS** — status `In Review`, light Green (not blue) |
| IPC allowlist | `sgenaxis-host::ipc` + `src-tauri` `is_allowed` | **PASS** — `git_write_repo_init` allowed; `git_init` / `git_clone` rejected |
| REPO-INIT UI path | `ui/app.js`, `ui/git-ux-mock.js` | **PASS at code level** — live hook → `showGitApprove("repo-init")` → `invoke("git_write_repo_init")`; cancel never calls the port |
| Tauri capability `host.toml` | `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` + `capabilities/default.json` | **FAIL** — see must-fix #1 |
| No skipped / weakened assertions | PR diff + TDD review | **PASS** for this slice |
| Hooks / CI config | PR file list | **PASS** — no `.ai-hooks` / `.githooks` / workflow edits |
| CI @ PR #90 head | GitHub Actions on `7002a82` | **guard failure**; **rust-windows failure** (unrelated `tests_git02` temps); Ubuntu `tests` + `lint + test subset` success |

## Layering

| Layer | Artifact | Direction |
|---|---|---|
| Port | `GitWritePort::init_repo` | Contract only; no OS ✓ |
| Adapters | `StdGitWrite`, `FakeGitWrite`, `GatedGitWrite` | Implement port; std is the only CLI; fake records; gated denies ✓ |
| Application | `sgenaxis_host::perform_git_repo_init` | Approval then port; no git CLI in host ✓ |
| API / IPC | `git_write_repo_init` + `AllowedIpcCommand::GitWriteRepoInit` | Authorize then host use-case ✓ |
| Tauri ACL | `permissions/host.toml` `host-default` used by `capabilities/default.json` | **Missing command permission** ✗ |
| Rendering | REPO-INIT in `git-ux-mock.js` + `app.js` approve/invoke | Presentation; no git CLI ✓ |

No skip-layer: UI does not call adapters; host product code does not shell out; ports do not import adapters/host/Tauri. Host crate lists `sgenaxis-adapters` as a composition-root dependency (same as sibling git-write slices); `git_repo_init.rs` product code takes `&dyn GitWritePort` only. Fake is test-only.

## Git invocation hygiene

`StdGitWrite::init_repo` / `spawn_init` is a single argv shape:

```text
git init -- <dir>
```

`--` stops option parse. No `clone`, no `--bare`, no `--template`, no `--separate-git-dir`, no `remote add`, no `fetch`. Path rejected first if it looks like an option, clone URL (`://` / `git@`), or contains `clone` / `--bare` / `--template` / `--git-dir` / `--work-tree` path segments.

After success, `assert_non_bare_contained` requires:

- `<dir>/.git` is a directory
- `rev-parse --is-bare-repository` is `false`
- `git remote` is empty
- `--absolute-git-dir` stays inside the chosen directory

Denied approval never reaches `spawn_init`. Existing `.git` / bare-looking `HEAD`+`objects`+`refs` returns `AlreadyExists` without re-init.

## File scope vs PR #90

PR #90 files (19), all in this Task's slice:

- Allowed: `sgenaxis-ports/src/git.rs`, adapters `std_git_write.rs` / `fake.rs` / `git_write.rs` / `tests_git.rs` / `tests_git02.rs`, host `git_repo_init.rs` + `ipc.rs` + `lib.rs`, src-tauri command/dto/lib, `ui/app.js`, `ui/git-ux-mock.js`, `docs/bdd/PD-GIT-REPO-INIT-01.feature`, `docs/board.json`, implementer evidence under `reports/dispatch-pd/`
- **Not present:** `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` (must-fix #1)

No product-code change by this reviewer.

## BDD / TDD trace

BDD: `docs/bdd/PD-GIT-REPO-INIT-01.feature` (01-1 denied leaves no `.git`; 01-2 approved non-bare, no remote/clone, git files inside dir; 01-3 existing / `--bare` / `--template` / option-like / clone URL fail honestly).

| ID | Independent TDD | High-tier code match |
|---|---|---|
| PD-GIT-REPO-INIT-01-1 | HOLD (Fake/Std/host denied; no `.git`) | Holds |
| PD-GIT-REPO-INIT-01-2 | HOLD (Fake/Std/host approved non-bare, remotes empty) | Holds |
| PD-GIT-REPO-INIT-01-3 | HOLD (existing / `--bare` / `--template` / URL / gated) | Holds |

Extra Green (not numbered BDD): `GatedGitWrite`; IPC allow `git_write_repo_init` / reject `git_init` and `git_clone`.

Historical Red-before-Green was **not** independently replayed (same limit as TDD review). `src-tauri` test `git_write_repo_init_gated_and_allowlisted` and desktop REPO-INIT click-path remain **NOT RUN**.

## Board

Task `PD-GIT-REPO-INIT-01`: `In Review`, light Green, `tdd` Green, `ci` Pending, hours 3, no storyPoints. **Not Done. Not blue.** Owner remains the implementer; this reviewer does not set Done.

Mismatch: light is Green while PR CI `guard` and `rust-windows` failed. `ci` is still `Pending`. Per board rules, failed CI with a Green light is a process mismatch — recorded as should-fix, not a Done/blue violation. Card has no `parent` Story link and no `prUrl` (should-fix).

## CI (PR #90, head `7002a82`)

| Job | Conclusion | Notes |
|---|---|---|
| tests | success | Ubuntu subset |
| lint + test subset | success | |
| guard (AI Dev Guard) | **failure** | (1) `docs/bdd/PD-GIT-REPO-INIT-01.feature` added without `spec-change` label; (2) test-disable scan `unterminated JavaScript template` (pre-existing `app.js` parse, also seen on sibling PRs) |
| rust-windows | **failure** | 4 failures in `tests_git02::std_write_temp` (add/remove remote, conflict continue, set-remote-url) — **not** the `init_repo` tests; slice tests in that job were ok |

## Finding: missing `host.toml` capability (blocking, same class as cherry-pick)

`apps/sgenaxis-desktop/src-tauri/permissions/host.toml` has **no** `allow-git-repo-init` (or any) permission whose `commands.allow` includes `git_write_repo_init`. The `host-default` set lists `allow-git-pull-ff` / `allow-git-conflict` / `allow-git-stage-all` / `allow-git-unstage-all` / etc., but not repo-init. `capabilities/default.json` grants only `host-default` plus unrelated sets.

Neighboring git-write slices (stage-all, unstage-all, pull-ff, conflict) added both a permission atom **and** `host-default` membership. Without that, live REPO-INIT `invoke("git_write_repo_init")` is rejected by Tauri ACL even though:

- the command is registered in `src-tauri/src/lib.rs`
- host IPC `is_allowed("git_write_repo_init")` is true
- UI approve → invoke path exists

High-tier treats this as a **must-fix** (expand allow-list / follow-up Task), not a Pass-with-footnote. Same ruling as PD-GIT-CHERRY-PICK-01 missing `git_write_cherry_pick`.

## Must-fix (blocking)

1. **Tauri capability:** Add `allow-git-repo-init` (commands.allow = `git_write_repo_init`) to `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` and append it to `host-default.permissions`. Expand the Task allow-list if needed. Until then live REPO-INIT cannot run in a built app.
2. **AI Dev Guard spec-change:** PR #90 adds `docs/bdd/PD-GIT-REPO-INIT-01.feature`. Add the `spec-change` label and CODEOWNERS review (this file belongs on this Task; do not drop it). Guard currently fails merge.

## Should-fix (non-blocking)

1. Re-run `cargo test -p sgenaxis-desktop --lib git_write_repo_init` where the lockfile toolchain (edition2024) exists; keep NOT RUN until then.
2. rust-windows `tests_git02` failures are pre-existing / out of slice; do not treat as this Task's TDD Red.
3. Board: set `ci` to match Guard failure (Yellow + `lightReason`) until Guard is green; add `prUrl` for PR #90; do not set Done/blue.
4. Investigate test-disable JS parse of `app.js` so Guard is trustworthy (pre-existing; not introduced solely by this diff).
5. Optional: `spawn_init` does not clear `GIT_TEMPLATE_DIR` / `GIT_DIR`; adapter already rejects `--template` / `--git-dir` in the path. Env inheritance is a residual if those variables are set in the host process.

## What passed (do not rework)

- Hexagonal `GitWritePort.init_repo` with Std / Fake / Gated parity.
- Approval denied → no mutation; UI cancel never invokes.
- Std argv is only `init -- <dir>`; tests prove non-bare `.git` inside the chosen directory, no remotes, no clone.
- Existing repo, `--bare`, `--template`, option-like paths, and clone URLs fail honestly.
- Host IPC allowlist + UI REPO-INIT approve/invoke wiring (capability excepted).
- No `#[ignore]` / skip on this slice; board not Done / not blue.
- Reviewer / implementer / TDD verifier are three different agents.

## Outcome

**CHANGES_REQUIRED** — adapter/host/port behavior for PD-GIT-REPO-INIT-01-1/2/3 is sound and independently TDD Green, but the REPO-INIT production invoke is not authorized in `host.toml`, and AI Dev Guard is red on the in-scope `.feature`. After must-fix #1 and #2, high-tier re-review can move to **PASS** without architectural replan. Do not merge. Do not set Done/blue.
