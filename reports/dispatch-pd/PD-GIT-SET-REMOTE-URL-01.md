# PD-GIT-SET-REMOTE-URL-01 — GitWritePort.set_remote_url (approval-gated)

**Agent:** Cloud mid-tier dev agent (Composer), role `dev-agent` — not verifier.

**BDD:** `PD-GIT-SET-REMOTE-URL-01-1`, `PD-GIT-SET-REMOTE-URL-01-2`, `PD-GIT-SET-REMOTE-URL-01-3`  
(feature spec on `cursor/next-batch-set-rename-remote-upstream-0111`; `.feature` not edited)

## Summary

TDD-locked `GitWritePort.set_remote_url`: approval-gated `git remote set-url -- <name> <url>` via `StdGitWrite`; mirror rules in `FakeGitWrite`. No `--add` / `--delete` / `--push` / `--mirror` / fetch on this path.

Implementation already matched the port contract on `main`; this task adds scenario-ID tests and a dispatch report.

## Files touched

| File | Change |
|------|--------|
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git.rs` | `pd_git_set_remote_url_01_{1,2,3}_*` (Fake) |
| `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git02.rs` | `pd_git_set_remote_url_01_{1,2,3}_*` (Std) |
| `docs/board.json` | Story + Task cards → In Review / TDD Green |
| `reports/dispatch-pd/PD-GIT-SET-REMOTE-URL-01.md` | This report |

**Read-only / pre-existing:** `std_git_write.rs`, `fake.rs`, `git_write.rs`, `sgenaxis-ports/src/git.rs`.

## TDD

**RED (recorded):** `reports/dispatch-pd/PD-GIT-SET-REMOTE-URL-01-red.txt` — zero tests matched filter before scenario tests; stub check failed _1/_2 when set-url was a no-op success.

**GREEN:**  
`cargo test pd_git_set_remote_url_01 --manifest-path apps/sgenaxis-desktop/crates/sgenaxis-adapters/Cargo.toml --features std-adapters` → **6 passed**.  
Full output: `reports/dispatch-pd/PD-GIT-SET-REMOTE-URL-01-test-output.txt`

## Scenario mapping

| BDD ID | Test(s) |
|--------|---------|
| PD-GIT-SET-REMOTE-URL-01-1 | `pd_git_set_remote_url_01_1_denied_approval_does_not_change_url` (Fake + Std) |
| PD-GIT-SET-REMOTE-URL-01-2 | `pd_git_set_remote_url_01_2_approved_set_url_updates_without_fetch_side_effects` (Fake + Std) |
| PD-GIT-SET-REMOTE-URL-01-3 | `pd_git_set_remote_url_01_3_ghost_and_option_like_inputs_fail_honestly` (Fake + Std) |

## Branch

`feature/PD-GIT-SET-REMOTE-URL-01-set-url`

## Blockers

None (`READY_FOR_TDD`). Independent verifier required per AI Dev workflow.