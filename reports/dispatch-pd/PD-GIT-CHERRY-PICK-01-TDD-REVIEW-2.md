# PD-GIT-CHERRY-PICK-01 independent TDD re-run (after host.toml follow-up)

**Verdict: TDD_PASS**

Date: 2026-11-15T11:05:00+08:00  
Reviewed HEAD: `3b306049be4a24d173a3f0f000f49f1cb165fe8b` (`chore(board): note CHERRY-PICK high-tier CHANGES_REQUIRED follow-up`)  
Branch under test: `feature/PD-GIT-CHERRY-PICK-01-cherry-pick`  
Implementation PR: [#88](https://github.com/roy791202/AIAD/pull/88)

This is a **second** independent TDD Gate. It does **not** reuse PR #89 (`docs/PD-GIT-CHERRY-PICK-01-tdd-review`, HEAD `e49b53e`) which ran **before** the host.toml / extra-feature follow-up.

| Role | Identity |
|---|---|
| Original implementer (not this agent) | `cursor-cloud-dev-PD-GIT-CHERRY-PICK-01` |
| Follow-up implementer (not this agent) | `cursor-cloud-dev-PD-GIT-CHERRY-PICK-01-followup` |
| Prior TDD verifier (not this agent) | `cursor-cloud-tdd-PD-GIT-CHERRY-PICK-01` (PR #89, pre-follow-up) |
| Prior high-tier reviewer (not this agent) | high-tier CHANGES_REQUIRED on PR #88 |
| Independent TDD verifier (this agent) | `cursor-cloud-tdd-PD-GIT-CHERRY-PICK-01-rerun-2` |

The implementer's `READY_FOR_TDD`, the follow-up agent's "still Green" claim, and the prior TDD_PASS on `e49b53e` were **not trusted**. This agent re-ran the focused adapter and host tests on the post-follow-up tree. Product code, assertions, fixtures, expected values, `.feature` files, and skip/ignore flags were not modified. Status stays **In Review**. Not Done / not blue.

Follow-up commits included in this re-run:

- `4f5abde` `fix(git): add cherry-pick host permission and reuse adapter oid check`
- `096ffeb` `chore(bdd): keep only PD-GIT-CHERRY-PICK-01 feature on this PR`
- `3b30604` `chore(board): note CHERRY-PICK high-tier CHANGES_REQUIRED follow-up`

## Commands (cwd `apps/sgenaxis-desktop`)

```
cargo test -p sgenaxis-adapters cherry_pick -- --nocapture
cargo test -p sgenaxis-host cherry_pick -- --nocapture
cargo test -p sgenaxis-host --lib allowlist_contains_host_commands_only -- --nocapture
cargo test -p sgenaxis-host --lib authorize_accepts_allowlisted -- --nocapture
```

Environment: Linux 6.12, cargo 1.83.0, rustc 1.83.0, git 2.43.0.

## Counts (this agent, this run)

| Suite | Filter | Result |
|---|---|---|
| `sgenaxis-adapters` lib | `cherry_pick` | **3 passed; 0 failed; 0 ignored; 0 measured; 191 filtered out** |
| `sgenaxis-host` lib | `cherry_pick` | **5 passed; 0 failed; 0 ignored; 0 measured; 106 filtered out** |
| `sgenaxis-host` lib | `allowlist_contains_host_commands_only` | **1 passed; 0 failed; 0 ignored** |
| `sgenaxis-host` lib | `authorize_accepts_allowlisted` | **1 passed; 0 failed; 0 ignored** |
| `sgenaxis-desktop` src-tauri `--lib git_write_cherry_pick` | focused Tauri command | **NOT RUN** — `webkit2gtk-4.1` and `gtk+-3.0` missing; `tauri` crate not present for offline resolve |
| UI / E2E / screenshots | ADV-CHERRY desktop | **NOT RUN** — no desktop GUI / WebKit in this environment |

Adapter tests that ran:

- `tests_git::fake_git_write_cherry_pick_denied_approved_and_honest_failures` … ok
- `tests_git::gated_git_write_blocks_cherry_pick_even_when_approved` … ok
- `tests_git02::std_write_temp::std_write_cherry_pick_applies_commit_or_refuses_missing_dirty_and_flags` … ok

Host tests that ran:

- `git_cherry_pick::tests::denied_does_not_call_git_write` … ok
- `git_cherry_pick::tests::occupying_run_refuses_before_git_write` … ok
- `git_cherry_pick::tests::approved_cherry_pick_records_without_push_or_ff` … ok
- `git_cherry_pick::tests::option_like_names_fail_honestly` … ok
- `git_cherry_pick::tests::missing_oid_fails_without_mutation` … ok

Raw adapter result line:

```
test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 191 filtered out; finished in 0.08s
```

Raw host cherry_pick result line:

```
test result: ok. 5 passed; 0 failed; 0 ignored; 0 measured; 106 filtered out; finished in 0.00s
```

No `#[ignore]`, skip, or `#[cfg(not(...))]` was observed on these focused tests. Assertions were not weakened in this session (verifier does not edit tests).

## Follow-up checks required by high-tier CHANGES_REQUIRED

### `host.toml` `allow-git-cherry-pick` in `host-default`

**HOLD.** File: `apps/sgenaxis-desktop/src-tauri/permissions/host.toml`.

- Permission identifier `allow-git-cherry-pick` exists and allows command `git_write_cherry_pick`.
- `[[set]] identifier = "host-default"` permissions list **includes** `"allow-git-cherry-pick"` (between `allow-git-pull-ff` and `allow-git-conflict`).
- Host crate `is_allowed("git_write_cherry_pick")` is asserted true and `is_allowed("git_cherry_pick")` is asserted false; `authorize_accepts_allowlisted` passed on this run.
- Host `perform_git_cherry_pick` now calls `sgenaxis_adapters::cherry_pick_oid_out_of_scope` (reused adapter check from `4f5abde`), not a weaker host-local duplicate.

### MERGE / INIT feature files gone from this branch

**HOLD.** On HEAD `3b30604`:

- `docs/bdd/` contains only `PD-GIT-CHERRY-PICK-01.feature` among `PD-GIT-{CHERRY,MERGE,REPO-INIT}*`.
- `git ls-tree -r HEAD --name-only` matches **none** of `PD-GIT-MERGE-FF` / `PD-GIT-REPO-INIT`.
- Diff vs `origin/main` for `docs/bdd/` is **A** `docs/bdd/PD-GIT-CHERRY-PICK-01.feature` only.
- Commit `096ffeb` deleted `docs/bdd/PD-GIT-MERGE-FF-01.feature` and `docs/bdd/PD-GIT-REPO-INIT-01.feature` so this Task PR stays one Task.

## Scenarios vs independent run

BDD source: `docs/bdd/PD-GIT-CHERRY-PICK-01.feature`.

| ID | Scenario | Holds? | Evidence from this run |
|---|---|---|---|
| **PD-GIT-CHERRY-PICK-01-1** | Denied approval does not cherry-pick; HEAD/worktree unchanged | **HOLD** | Fake: denied call leaves `last_cherry_pick` none, HEAD and commit count unchanged, `push_count` 0. Std: denied leaves HEAD unchanged, `b.txt` absent, no `CHERRY_PICK_HEAD` / `rebase-merge`. Host: `denied_does_not_call_git_write` ok. |
| **PD-GIT-CHERRY-PICK-01-2** | Approved cherry-pick applies one commit; no rebase / push / `--ff` | **HOLD** | Fake: granted records oid, commit count +1, subject `feat: picked`, HEAD changes, no push / pull-ff / branch switch. Std: new HEAD ≠ source (no `--ff` shortcut), `b.txt` applied, `c.txt` preserved, single-parent commit, no rebase dirs. Host: `approved_cherry_pick_records_without_push_or_ff` ok. |
| **PD-GIT-CHERRY-PICK-01-3** | Missing oid, dirty overwrite, option-like names fail without mutating HEAD | **HOLD** | Fake + Std refuse `-n` / `--ff` / continue (and Fake also `--skip` / `--abort` / `--no-commit`); missing oid → Git error (`bad revision` on Fake/host); dirty overwrite → Git error, HEAD/worktree preserved. Host: `option_like_names_fail_honestly` + `missing_oid_fails_without_mutation` ok. |

Extra coverage (not numbered BDD IDs, still Green here): occupying Run/lease refuses before GitWritePort; `GatedGitWrite` denies even when approved; host IPC allowlist accepts `git_write_cherry_pick` and rejects `git_cherry_pick`.

## Limits

- Historical RED (test-first failure before implementation) was **not independently replayed**. This review is a current Green re-run only.
- src-tauri command test `git_write_cherry_pick_gated_and_allowlisted` is **NOT RUN** (GTK/WebKit absent; Tauri crate unresolved offline). Host crate already covers occupying-before-port + honest fail + approved record.
- Desktop ADV-CHERRY click-path, screenshots, and recording are **NOT RUN**.
- CI status remains whatever the board already had (`None`); this agent did not claim CI Green.
- High-tier re-review after the follow-up is **out of scope** for this TDD Gate.

## Board

Task `PD-GIT-CHERRY-PICK-01` stays **In Review**, light **Yellow** (`lightReason`: independent TDD re-run after follow-up is Green; high-tier re-review still pending because review returned once), `tdd` **Green** because this verifier personally saw PASS on the focused adapter + host suites for 01-1 / 01-2 / 01-3 **and** confirmed `allow-git-cherry-pick` in `host-default` plus MERGE/INIT `.feature` files gone. Not Done. Not blue.
