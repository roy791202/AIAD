# PD-GIT-REMOVE-REMOTE-01 — GitWritePort.remove_remote

**Agent:** `cloud-dev-agent-pd-git-remove-remote-01` (dev; not verifier)  
**Branch:** `feature/PD-GIT-REMOVE-REMOTE-01-remove-remote`  
**BDD:** `docs/bdd/PD-GIT-REMOVE-REMOTE-01.feature` (on scheduling branch; scenarios referenced by ID)

## Scope

TDD-lock approval-gated `git remote remove -- <name>` on `FakeGitWrite` and `StdGitWrite`. Never prune, fetch, or push. Denied approval leaves remotes unchanged. Missing names and option-like names (`--prune`) fail without mutation. Removing one remote leaves others.

## BDD → TDD mapping

| Scenario | Fake test | Std test |
| --- | --- | --- |
| PD-GIT-REMOVE-REMOTE-01-1 | `pd_git_remove_remote_01_1_denied_approval_does_not_remove_remote` | `pd_git_remove_remote_01_1_std_denied_approval_does_not_remove_remote` |
| PD-GIT-REMOVE-REMOTE-01-2 | `pd_git_remove_remote_01_2_approved_remove_deletes_only_that_remote` | `pd_git_remove_remote_01_2_std_approved_remove_deletes_only_that_remote` |
| PD-GIT-REMOVE-REMOTE-01-3 | `pd_git_remove_remote_01_3_missing_and_option_like_names_fail_honestly` | `pd_git_remove_remote_01_3_std_missing_and_option_like_names_fail_honestly` |

## Files touched

- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git02.rs`
- `docs/board.json` (task `PD-GIT-REMOVE-REMOTE-01` only)

Existing adapter implementations (`std_git_write.rs`, `fake.rs`, port `git.rs`) already matched the port contract; no product behavior changes in this task.

## Test command & result

```bash
cd apps/sgenaxis-desktop/crates/sgenaxis-adapters
cargo test --features std-adapters pd_git_remove_remote
```

```
running 6 tests
... 6 passed; 0 failed
```

## Status

`READY_FOR_TDD` — independent verifier should re-run the above filter and full `sgenaxis-adapters` suite. Card left **In Review** (not Done / not blue).