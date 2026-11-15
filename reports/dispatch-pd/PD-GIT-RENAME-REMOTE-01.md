# PD-GIT-RENAME-REMOTE-01 — GitWritePort.rename_remote (approval-gated)

**Agent:** Cloud mid-tier dev agent (Composer), role `dev-agent` — not verifier.

**BDD:** `PD-GIT-RENAME-REMOTE-01-1`, `PD-GIT-RENAME-REMOTE-01-2`, `PD-GIT-RENAME-REMOTE-01-3`  
(added `docs/bdd/PD-GIT-RENAME-REMOTE-01.feature` in this PR only; no other `.feature` files)

## Summary

TDD-locked `GitWritePort.rename_remote`: approval-gated `git remote rename -- <old> <new>` via `StdGitWrite`; mirror rules in `FakeGitWrite`. No fetch, `set-url`, or push on this path.

Implementation already matched the port contract on `main`; this task adds scenario-ID tests and a dispatch report.

## Files touched

| File | Change |
|------|--------|
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git.rs` | `pd_git_rename_remote_01_1_*`, `pd_git_rename_remote_01_3_*` (Fake) |
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git02.rs` | `pd_git_rename_remote_01_{1,2,3}_*` (Std) |
| `docs/bdd/PD-GIT-RENAME-REMOTE-01.feature` | BDD scenarios for this Task |
| `docs/board.json` | Story + Task cards (RENAME-REMOTE batch slice only) |
| `reports/dispatch-pd/PD-GIT-RENAME-REMOTE-01.md` | This report |
| `reports/dispatch-pd/PD-GIT-RENAME-REMOTE-01-test-output.txt` | `cargo test` log |

**Read-only / pre-existing:** `std_git_write.rs`, `fake.rs`, `git_write.rs`, `sgenaxis-ports/src/git.rs`.

## TDD

**GREEN:**  
`cargo test pd_git_rename_remote_01 --manifest-path apps/sgenaxis-desktop/crates/sgenaxis-adapters/Cargo.toml --features std-adapters` → **5 passed**.

Evidence: `reports/dispatch-pd/PD-GIT-RENAME-REMOTE-01-test-output.txt`

## Scenario mapping

| BDD ID | Test(s) |
|--------|---------|
| PD-GIT-RENAME-REMOTE-01-1 | `pd_git_rename_remote_01_1_denied_approval_does_not_rename_remote` (Fake + Std) |
| PD-GIT-RENAME-REMOTE-01-2 | `pd_git_rename_remote_01_2_approved_rename_keeps_url_without_fetch` (Std) |
| PD-GIT-RENAME-REMOTE-01-3 | `pd_git_rename_remote_01_3_missing_duplicate_and_option_like_names_fail_honestly` (Fake + Std) |

## Branch

`feature/PD-GIT-RENAME-REMOTE-01-rename-remote`

## PR

https://github.com/roy791202/AIAD/pull/77

## Blockers

None (`READY_FOR_TDD`). High-tier review CHANGES_REQUIRED on scope/board addressed in follow-up commit. Independent verifier required per AI Dev workflow.