# PD-GIT-RESTORE-PATH-01

**Agent:** cursor/cloud dev-agent (PD-GIT-RESTORE-PATH-01)  
**BDD:** BDD-PD-GIT-RESTORE-PATH-01  
**Status:** READY_FOR_TDD (dev self-check)

## Summary

Adds `GitWritePort::restore_path(repo, path, approval)` with approval gating,
`git restore --source=HEAD --worktree -- <path>` semantics (worktree only),
`OPERATION_IN_PROGRESS` when merge/rebase/cherry-pick/revert has unmerged paths,
and honest failures for denied/missing/untracked/option-like paths.

## Tests run (dev)

```text
cargo test --lib restore_path   → 3/3 PASS
```

## Files changed

- `apps/sgenaxis-desktop/crates/sgenaxis-ports/src/git.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/std_git_write.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/git_write.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/fake.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git02.rs`

## Notes

- No host/Tauri command added (not required for port contract slice).
- `GatedGitWrite` remains default-deny for restore-path.