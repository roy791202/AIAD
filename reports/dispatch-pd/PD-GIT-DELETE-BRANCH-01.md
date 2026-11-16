# PD-GIT-DELETE-BRANCH-01 — GitWritePort.delete_branch

**Agent:** dev-agent (implementation only; not verifier)  
**Role:** ai-dev-implementation  
**Branch:** `feature/PD-GIT-DELETE-BRANCH-01-delete-branch`  
**BDD:** Given GitWriteApproval When delete_branch Then only `git branch -d -- <name>` if approved.

## Scope

Allowed files only. Did not implement rename/stash/create_branch/G01–G04. Did not set Done/blue. Did not edit `docs/board.json`.

## Contract

- Approved → `git branch -d -- <name>` only.
- Empty, unapproved, current HEAD, unmerged, missing, `-D`, `-r` / `--remotes`, path traversal, remote-only names fail honestly with **no mutation**.
- Never `-D` / `--force` / `-f` fallback.
- Never `-r` remote-tracking delete.
- Never `git push :branch` / remote delete.
- Never switch/checkout.

## TDD

### Red

`fake_git_write_delete_branch_records_when_approved` failed before Fake/Std remote-only guards:

```
thread 'tests_git::fake_git_write_delete_branch_records_when_approved' panicked at crates/sgenaxis-adapters/src/tests_git.rs:755:5:
remote-tracking names must fail honestly without -r: Err(Git("branch 'origin/main' not found"))
test tests_git::fake_git_write_delete_branch_records_when_approved ... FAILED
```

Honesty gap: missing local + existing remote-tracking looked like a generic "not found" instead of refusing remote-only / `-r` delete.

### Green

```
cargo test --package sgenaxis-adapters delete_branch
test tests_git::fake_git_write_delete_branch_records_when_approved ... ok
test tests_git02::std_write_temp::std_write_delete_branch_safe_only_when_approved ... ok

cargo test --package sgenaxis-adapters gated_git_write_blocks_branch_delete
test tests_git::gated_git_write_blocks_branch_delete_even_when_approved ... ok
```

`src-tauri` `git_write_branch_delete_gated_and_allowlisted` could not be compiled in this environment (Cargo 1.83 vs `cssparser-macros` requiring edition2024). Command path still uses `perform_git_write_branch_delete` → `GitWritePort::delete_branch` with the same honesty checks.

## Implementation notes

- `StdGitWrite::delete_branch`: approval → name guards → refuse current HEAD → `show-ref` local `refs/heads/<name>` else remote-only / missing → `git branch -d -- <name>`.
- `FakeGitWrite::delete_branch`: same honesty (including `mark_remote_only`).
- `GatedGitWrite` remains default-deny.
- IPC command `git_write_branch_delete` already allowlisted; `-r` / `--remotes` rejected at command scope.

## Out of scope (not done)

rename_branch / stash / create_branch / G01–G04 / merge / verifier / board.json Done.
