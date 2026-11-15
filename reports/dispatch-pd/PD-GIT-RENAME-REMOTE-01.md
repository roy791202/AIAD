# PD-GIT-RENAME-REMOTE-01 — GitWritePort.rename_remote (approval-gated)

**Agent:** Cloud mid-tier dev agent (Composer), role `dev-agent` — not verifier.

**BDD:** `PD-GIT-RENAME-REMOTE-01-1`, `PD-GIT-RENAME-REMOTE-01-2`, `PD-GIT-RENAME-REMOTE-01-3`  
(`.feature` not edited)

## Summary

TDD-locked `GitWritePort.rename_remote`: approval-gated `git remote rename -- <old> <new>` via `StdGitWrite`; mirror rules in `FakeGitWrite`. No fetch, `set-url`, or push on this path.

Implementation already matched the port contract on `main`; this task adds scenario-ID tests and a dispatch report.

## Files touched

| File | Change |
|------|--------|
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git.rs` | `pd_git_rename_remote_01_1_*`, `pd_git_rename_remote_01_3_*` (Fake) |
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git02.rs` | `pd_git_rename_remote_01_{1,2,3}_*` (Std) |
| `docs/board.json` | Task card → In Review / TDD Green |
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

## Blockers

None (`READY_FOR_TDD`). Independent verifier required per AI Dev workflow.