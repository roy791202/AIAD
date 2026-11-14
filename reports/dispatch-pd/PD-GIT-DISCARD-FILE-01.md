# PD-GIT-DISCARD-FILE-01 — implementation report

- **Agent**: `dev-agent` (Cursor cloud implementation; not verifier)
- **Task**: PD-GIT-DISCARD-FILE-01 — GIT：核准後單檔 discard 工作區至 index
- **Story**: S-GIT-WRITE-P2
- **BDD**: `@S-GIT-WRITE-P2-3`, `@S-GIT-WRITE-P2-4`
- **Branch**: `feature/PD-GIT-DISCARD-FILE-01-discard`
- **Outcome**: `READY_FOR_TDD` (this agent does not accept its own work)

## Behavior

Approved `GitWritePort::discard_file` restores **one tracked path** worktree contents to the index (`git restore --worktree -- <path>`). Denied approval does not mutate. Untracked files are not deleted. Option-like paths, paths outside the repo, and unmerged conflict paths fail honestly (no `reset --hard`, no `--force`). UI FILE-DISCARD opens the existing approval modal and invokes `git_write_discard_file`; the UI does not spawn git CLI.

## Tests

```
cargo test -p sgenaxis-adapters --lib s_git_write_p2
# 4 passed: tests_git::s_git_write_p2_{3,4}_*, tests_git02::std_write_temp::s_git_write_p2_{3,4}_*

cargo test -p sgenaxis-host --lib discard_file
# 2 passed: git_discard_file::tests::s_git_write_p2_{3,4}_*

cargo test -p sgenaxis-host --lib ipc::
# 3 passed
```

`src-tauri` `cargo test --lib git_write_discard_file` was **NOT RUN** in this environment: Cargo 1.83 cannot parse `dlopen2_derive` (edition2024) from the registry. Command wrapper and allowlist follow `git_write_unstage_all`; host tests cover the use case.

## Notes

- `docs/board.json` has no `PD-GIT-DISCARD-FILE-01` card; no board rewrite.
- `.feature` files were not edited.
- Adjacent wiring required for a working command: `sgenaxis-host` IPC allowlist, `src-tauri/src/lib.rs` handler registration, `ui/git-ux-mock.js` live `FILE-DISCARD` hook (same pattern as ALL-STAGE).
- TDD is Green for this task’s named tests; **do not treat this as independent acceptance**.
