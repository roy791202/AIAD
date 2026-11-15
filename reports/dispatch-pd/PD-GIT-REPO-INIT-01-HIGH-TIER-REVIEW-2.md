# PD-GIT-REPO-INIT-01 — High-tier re-review 2

**Verdict: PASS**

Date: 2026-11-15T11:20:00+08:00  
PR: https://github.com/roy791202/AIAD/pull/90 (`feat(git): gated git init via GitWritePort`)  
Implementation HEAD (re-reviewed): `28ce7b6cc7a8ec9ba86632fc8a9230b35161ffed`  
Prior high-tier: **CHANGES_REQUIRED** @ `7002a82293161089220f73cbeec56c2cbac0be63` (`docs/PD-GIT-REPO-INIT-01-high-tier-review`)  
Independent TDD: **TDD_PASS** @ `7002a82` (`docs/PD-GIT-REPO-INIT-01-tdd-review`)

| Role | Identity | Same conversation? |
|---|---|---|
| Original implementer | `cursor-cloud-dev-PD-GIT-REPO-INIT-01` | No |
| ACL follow-up implementer | `cursor-cloud-dev-PD-GIT-REPO-INIT-01` (board note 10:50) | No |
| Independent TDD verifier | `independent-tdd-PD-GIT-REPO-INIT-01` | No |
| Prior high-tier reviewer | `cursor-cloud-high-tier-PD-GIT-REPO-INIT-01` | No |
| This high-tier re-reviewer | `cursor-cloud-high-tier-PD-GIT-REPO-INIT-01-rereview-2` | No |

This agent did **not** implement, did **not** apply the ACL follow-up, did **not** run the original TDD-verifier session, and did **not** modify product code, tests, `.feature` files, hooks, or `docs/board.json`. Identities differ; acceptance identity rule holds. **Not Done. Not blue.**

Follow-up commits on PR #90 after CHANGES_REQUIRED:

- `7b5a6d8` `fix(git): allowlist git_write_repo_init in host.toml`
- `28ce7b6` `docs(board): yellow light and PR #90 for PD-GIT-REPO-INIT-01`

## Prior must-fix / should-fix — disk verification @ `28ce7b6`

| # | Prior finding | On-disk check | Result |
|---|---|---|---|
| Must-fix 1 | Add `allow-git-repo-init` (`commands.allow = ["git_write_repo_init"]`) to `host.toml` **and** `host-default.permissions` | `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` lines 128–131 (atom) and line 217 (in `host-default`). `capabilities/default.json` already grants `host-default`. `uidesign-window.json` also grants `host-default`. | **SATISFIED** |
| Must-fix 2 | Add `spec-change` for `docs/bdd/PD-GIT-REPO-INIT-01.feature`; do **not** drop the file | `git diff --name-only origin/main...HEAD -- '*.feature'` = only `docs/bdd/PD-GIT-REPO-INIT-01.feature`. PR file list keeps that one `.feature`. Scenarios 01-1 / 01-2 / 01-3 unchanged. | **SATISFIED** (file kept). Remaining Guard `spec-change` is an **approver** action, not a new product-code must-fix. |
| Board | No Done / no blue | Task `PD-GIT-REPO-INIT-01`: status `In Review`, light `Yellow`, `tdd` Green, hours 3, no storyPoints, `prUrl` = PR #90. | **SATISFIED** |

## Independent re-run (this review)

| Suite | Command | Result |
|---|---|---|
| `sgenaxis-host` lib `git_repo_init` | `cargo test -p sgenaxis-host --lib git_repo_init -- --nocapture` (cwd `apps/sgenaxis-desktop`) | **3 passed; 0 failed; 0 ignored** — denied no mutation; approved non-bare no remote; existing / `--bare` / URL fail honestly |
| `sgenaxis-desktop` `--lib git_write_repo_init` | not re-run | **NOT RUN** — same edition2024 / Cargo 1.83 limit as TDD review; not upgraded to PASS |
| UI / E2E REPO-INIT | not re-run | **NOT RUN** |

This re-run confirms host use-case Green after the ACL-only follow-up (follow-up did not touch adapters/host product logic). Prior independent TDD_PASS (adapter 10/10 + host 3/3 + IPC allowlist @ `7002a82`) is accepted for the unchanged adapter slice.

## Architecture / ACL (re-checked)

| Check | Result |
|---|---|
| Inward deps (ports ← adapters ← host ← src-tauri) | **PASS** — host still composes `GitWritePort`; no git CLI in host |
| `StdGitWrite::init_repo` argv | **PASS** — still `git init -- <dir>` only (follow-up did not touch `std_git_write.rs`) |
| Approval denied → no `.git` | **PASS** |
| Honest failures (existing / `--bare` / `--template` / option-like / clone URL) | **PASS** |
| Never clone / remote / fetch | **PASS** |
| Tauri ACL live path | **PASS** — `allow-git-repo-init` in `host-default`; `default.json` uses `host-default` |
| Feature file kept | **PASS** — this PR carries only `PD-GIT-REPO-INIT-01.feature` |
| Board not Done / not blue | **PASS** — `In Review` / Yellow (review returned once) |
| No skip / ignore on this slice | **PASS** |
| Hooks / workflow files | **PASS** — not in PR file list |
| Command registered | **PASS** — `git_write_repo_init` in `generate_handler`, `list_commands`, host IPC allowlist; `git_init` / `git_clone` rejected |

## File scope @ PR #90 HEAD `28ce7b6` (20 files)

Allowed / in-slice: ports `git.rs`; adapters `fake.rs` / `git_write.rs` / `std_git_write.rs` / `tests_git.rs` / `tests_git02.rs`; host `git_repo_init.rs` / `ipc.rs` / `lib.rs`; src-tauri `permissions/host.toml` / `commands.rs` / `dto.rs` / `lib.rs`; UI `app.js` / `git-ux-mock.js`; `docs/bdd/PD-GIT-REPO-INIT-01.feature`; `docs/board.json`; implementer evidence under `reports/dispatch-pd/`.

**Now present (was missing at prior review HEAD `7002a82`):** `apps/sgenaxis-desktop/src-tauri/permissions/host.toml`.

## CI @ PR #90 HEAD `28ce7b6` (observed, not blocking this PASS)

| Job | Conclusion | Notes |
|---|---|---|
| tests | success | Ubuntu |
| lint + test subset | success | |
| guard (AI Dev Guard) | **failure** | Board linkage ok (`對應卡片：PD-GIT-REPO-INIT-01`). Remaining: (1) this Task’s own `PD-GIT-REPO-INIT-01.feature` still needs approver `spec-change` + CODEOWNERS (implementer cannot add labels; file was **kept**); (2) pre-existing test-disable `unterminated JavaScript template` in `app.js` (sibling PRs, not introduced by the ACL one-liner) |
| rust-windows | **failure** | Prior review: out-of-slice `tests_git02` temps; `init_repo` tests were ok |

Same as sibling git-write high-tier re-reviews: remaining Guard `spec-change` is an **approver** action before merge, not a new product-code must-fix. The in-scope `.feature` belongs on this Task and must stay.

## Residual recommendations (non-blocking)

1. Approver: add `spec-change` on PR #90 and CODEOWNERS-review the single Task `.feature`.
2. Keep `src-tauri` `git_write_repo_init_gated_and_allowlisted` as **NOT RUN** until a toolchain that supports `edition2024` exists.
3. rust-windows `tests_git02` failures remain out of this slice.
4. Optional: `spawn_init` does not clear `GIT_TEMPLATE_DIR` / `GIT_DIR`; adapter already rejects `--template` / `--git-dir` in the path.
5. Do **not** set Done / blue until PR merge by high-tier or user.

## Outcome

**PASS** — prior high-tier **CHANGES_REQUIRED** must-fix items are verified on disk at `28ce7b6`: `allow-git-repo-init` (`commands.allow = git_write_repo_init`) is in `host-default`; `docs/bdd/PD-GIT-REPO-INIT-01.feature` is **kept**; board is **In Review** / Yellow, **not Done / not blue**. Independent host `git_repo_init` replay is 3/3 Green. Do not merge from this docs branch. Do not set Done/blue.
