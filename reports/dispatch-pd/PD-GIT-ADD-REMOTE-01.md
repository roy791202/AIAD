# PD-GIT-ADD-REMOTE-01 — GitWritePort.add_remote (approval-gated)

**Agent:** Cloud mid-tier dev agent (Composer), role `dev-agent` — not verifier.

**BDD:** `PD-GIT-ADD-REMOTE-01-1`, `PD-GIT-ADD-REMOTE-01-2`, `PD-GIT-ADD-REMOTE-01-3`  
(feature spec on `cursor/subagent-direct-batch-scheduling-1879`; `.feature` not edited)

## Summary

TDD-locked `GitWritePort.add_remote`: approval-gated `git remote add -- <name> <url>` via `StdGitWrite`; mirror rules in `FakeGitWrite`. No `-f`, fetch, `set-url`, or push on this path.

Implementation already matched the port contract on `main`; this task adds scenario-ID tests and a dispatch report.

## Files touched

| File | Change |
|------|--------|
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git.rs` | `pd_git_add_remote_01_1_*`, `pd_git_add_remote_01_3_*` (Fake) |
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git02.rs` | `pd_git_add_remote_01_{1,2,3}_*` (Std) |
| `docs/board.json` | Task card → In Review / TDD Green |
| `reports/dispatch-pd/PD-GIT-ADD-REMOTE-01.md` | This report |

**Read-only / pre-existing:** `std_git_write.rs`, `fake.rs`, `git_write.rs`, `sgenaxis-ports/src/git.rs`.

## TDD

**RED (recorded):** New scenario tests fail if `StdGitWrite::add_remote` / `FakeGitWrite::add_remote` return `Ok(())` unconditionally (verified by temporary stub during dev).

**GREEN:**  
`cargo test pd_git_add_remote_01 --manifest-path apps/sgenaxis-desktop/crates/sgenaxis-adapters/Cargo.toml` → **5 passed**.

## Scenario mapping

| BDD ID | Test(s) |
|--------|---------|
| PD-GIT-ADD-REMOTE-01-1 | `pd_git_add_remote_01_1_denied_approval_does_not_add_remote` (Fake + Std) |
| PD-GIT-ADD-REMOTE-01-2 | `pd_git_add_remote_01_2_approved_add_records_url_without_fetch` (Std) |
| PD-GIT-ADD-REMOTE-01-3 | `pd_git_add_remote_01_3_duplicate_and_option_like_names_fail_honestly` (Fake + Std) |

## Branch

`feature/PD-GIT-ADD-REMOTE-01-add-remote`

## Blockers

None (`READY_FOR_TDD`). Independent verifier required per AI Dev workflow.