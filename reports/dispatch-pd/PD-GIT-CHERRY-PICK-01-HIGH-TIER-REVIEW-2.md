# PD-GIT-CHERRY-PICK-01 — High-tier re-review 2

**Verdict: PASS**

Date: 2026-11-15T11:10:00+08:00  
PR: https://github.com/roy791202/AIAD/pull/88 (`feat(git): gated cherry-pick via GitWritePort`)  
Implementation HEAD (re-reviewed): `3b306049be4a24d173a3f0f000f49f1cb165fe8b`  
Prior high-tier: **CHANGES_REQUIRED** @ `e49b53ea88b52b2d88486b35cef7b9af2f65f276` (`docs/PD-GIT-CHERRY-PICK-01-high-tier-review`)  
Independent TDD: **TDD_PASS** @ `e49b53e` (`docs/PD-GIT-CHERRY-PICK-01-tdd-review`)

| Role | Identity | Same conversation? |
|---|---|---|
| Original implementer | `cursor-cloud-dev-PD-GIT-CHERRY-PICK-01` | No |
| Follow-up implementer | `cursor-cloud-dev-PD-GIT-CHERRY-PICK-01-followup` | No |
| Independent TDD verifier | `cursor-cloud-tdd-PD-GIT-CHERRY-PICK-01` | No |
| Prior high-tier reviewer | `cursor-cloud-high-tier-PD-GIT-CHERRY-PICK-01` | No |
| This high-tier re-reviewer | `cursor-cloud-high-tier-PD-GIT-CHERRY-PICK-01-rereview-2` | No |

This agent did **not** implement, did **not** apply the follow-up, did **not** run the original TDD-verifier session, and did **not** modify product code, tests, `.feature` files, hooks, or `docs/board.json`. Identities differ; acceptance identity rule holds. **Not Done. Not blue.**

Follow-up commits on PR #88 after CHANGES_REQUIRED:

- `4f5abde` `fix(git): add cherry-pick host permission and reuse adapter oid check`
- `096ffeb` `chore(bdd): keep only PD-GIT-CHERRY-PICK-01 feature on this PR`
- `3b30604` `chore(board): note CHERRY-PICK high-tier CHANGES_REQUIRED follow-up`

## Prior must-fix / should-fix — disk verification @ `3b30604`

| # | Prior finding | On-disk check | Result |
|---|---|---|---|
| Must-fix 1 | Add `allow-git-cherry-pick` (`commands.allow = ["git_write_cherry_pick"]`) to `host.toml` **and** `host-default.permissions` | `apps/sgenaxis-desktop/src-tauri/permissions/host.toml` lines 139–141 (atom) and line 219 (in `host-default`). `capabilities/default.json` already grants `host-default`. | **SATISFIED** |
| Must-fix 2 | Add `spec-change` **or** drop extra `PD-GIT-MERGE-FF-01.feature` / `PD-GIT-REPO-INIT-01.feature` so this PR maps to one Task | `git diff --name-only origin/main...HEAD -- '*.feature'` = only `docs/bdd/PD-GIT-CHERRY-PICK-01.feature`. PR file list (18 files) has that one `.feature`. Follow-up `096ffeb` deleted the two extras. | **SATISFIED** |
| Should-fix 1 | Host must reuse adapter `cherry_pick_oid_out_of_scope` (not a weaker local duplicate) | Host local `fn cherry_pick_oid_out_of_scope` removed. `git_cherry_pick.rs` `use sgenaxis_adapters::cherry_pick_oid_out_of_scope`. Adapters `lib.rs` re-exports it. Host tests now refuse `abc1234..def` and `HEAD~1`. | **SATISFIED** |
| Board | No Done / no blue | Task `PD-GIT-CHERRY-PICK-01`: status `In Review`, light `Yellow`, `tdd` Green, hours 4, no storyPoints. Story `S-GIT-WRITE-CHERRY-PICK-01` stays `Todo` / Gray. | **SATISFIED** |

## Independent re-run (this review)

| Suite | Command | Result |
|---|---|---|
| `sgenaxis-host` lib `cherry_pick` | `cargo test -p sgenaxis-host cherry_pick -- --nocapture` (cwd `apps/sgenaxis-desktop`) | **5 passed; 0 failed; 0 ignored** — denied, occupying-before-port, approved no push/ff, option-like (`--ff` / `-n` / `..` / `HEAD~1`), missing oid |
| `sgenaxis-desktop` `--lib git_write_cherry_pick` | not re-run | **NOT RUN** — same GTK/WebKit limit as TDD review; not upgraded to PASS |
| UI / E2E ADV-CHERRY | not re-run | **NOT RUN** |

This re-run confirms the stronger host fail-fast after helper reuse. Prior independent TDD_PASS (adapter 3/3 + host 5/5 @ `e49b53e`) is accepted for the unchanged adapter slice.

## Architecture / ACL (re-checked)

| Check | Result |
|---|---|
| Inward deps (ports ← adapters ← host ← src-tauri) | **PASS** — host still composes `GitWritePort`; no git CLI in host |
| `StdGitWrite::cherry_pick` argv | **PASS** — still `git cherry-pick -- <oid>` only (follow-up did not touch `std_git_write.rs` behavior) |
| Occupying lease before port | **PASS** — host test Green |
| Approval denied → no mutation | **PASS** |
| Honest failures (missing / dirty / option-like / range / tilde) | **PASS** |
| Tauri ACL live path | **PASS** — `allow-git-cherry-pick` in `host-default`; `default.json` uses `host-default` |
| One Task / one `.feature` on this PR | **PASS** |
| Board not Done / not blue | **PASS** — `In Review` / Yellow (review returned once) |
| No skip / ignore on this slice | **PASS** |
| Hooks / workflow files | **PASS** — not in PR file list |

## File scope @ PR #88 HEAD `3b30604` (18 files)

Allowed / in-slice: ports `git.rs`; adapters `fake.rs` / `git_write.rs` / `lib.rs` / `std_git_write.rs` / `tests_git.rs` / `tests_git02.rs`; host `git_cherry_pick.rs` / `ipc.rs` / `lib.rs`; src-tauri `permissions/host.toml` / `commands.rs` / `dto.rs` / `lib.rs`; UI `app.js` / `git-ux-mock.js`; `docs/bdd/PD-GIT-CHERRY-PICK-01.feature`; `docs/board.json`.

**No longer on this PR:** `docs/bdd/PD-GIT-MERGE-FF-01.feature`, `docs/bdd/PD-GIT-REPO-INIT-01.feature`.

## CI @ PR #88 HEAD `3b30604` (observed, not blocking this PASS)

| Job | Conclusion | Notes |
|---|---|---|
| tests | success | Ubuntu |
| lint + test subset | success | |
| guard (AI Dev Guard) | **failure** | Board linkage ok (`對應卡片：PD-GIT-CHERRY-PICK-01`). Remaining: (1) this Task’s own `PD-GIT-CHERRY-PICK-01.feature` still needs approver `spec-change` + CODEOWNERS (implementer cannot add labels; extra MERGE/INIT features are gone); (2) pre-existing test-disable `unterminated JavaScript template` in `app.js` (sibling PRs, not introduced by the ACL one-liner) |
| rust-windows | in progress at review time | Prior review: out-of-slice `tests_git02` temps; cherry_pick tests were ok |

Same as sibling git-write high-tier re-reviews: remaining Guard `spec-change` is an **approver** action before merge, not a new product-code must-fix. Extra-task `.feature` files that previously mixed Tasks on this PR are gone.

## Residual recommendations (non-blocking)

1. Approver: add `spec-change` on PR #88 and CODEOWNERS-review the single Task `.feature`.
2. Keep `src-tauri` `git_write_cherry_pick_gated_and_allowlisted` as **NOT RUN** until WebKit/GTK (or edition2024) exists.
3. rust-windows `tests_git02` failures remain out of this slice.
4. Optional: attach implementer evidence `reports/dispatch-pd/PD-GIT-CHERRY-PICK-01.md` on the implementation branch (still absent on PR head).
5. Do **not** set Done / blue until PR merge by high-tier or user.

## Outcome

**PASS** — prior high-tier **CHANGES_REQUIRED** must-fix items are verified on disk at `3b30604`: `allow-git-cherry-pick` is in `host-default`; this PR carries only `PD-GIT-CHERRY-PICK-01.feature`; host reuses adapter `cherry_pick_oid_out_of_scope`; board is **In Review** / Yellow, **not Done / not blue**. Independent host cherry_pick replay is 5/5 Green. Do not merge from this docs branch. Do not set Done/blue.
