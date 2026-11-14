# PD-GIT-STAGE-PATH-01 — 審核式單檔暫存（FILE-STAGE）

**Status:** READY_FOR_TDD  
**Branch:** `feature/PD-GIT-STAGE-PATH-01-gated-add`  
**Agent:** implementation (cloud)

## Summary

Mirrors ALL-STAGE: UI confirm → `git_write_stage_path` → `perform_git_stage_path` → `GitWritePort::stage_path` → `git add -- <path>` only. Denied approval does not mutate. Unmerged / in-progress operations return `OPERATION_IN_PROGRESS`. Out-of-scope paths (empty, `.`, `-A`, `--force`, traversal, NUL, absolute outside repo) fail honestly. Never commit, push, `git add -A`, `git add .`, `reset --hard`, or `--force`.

## Tests

```bash
cd apps/sgenaxis-desktop
cargo test bdd_pd_git_stage_path_01
cargo test git_write_stage_path_gated   # in src-tauri when toolchain builds Tauri crate
```

**Result (workspace crates):** 7 passed (`sgenaxis-adapters` 4, `sgenaxis-host` 3). Tauri package test not run in this VM (Cargo 1.83 vs `edition2024` dependency on `dlopen2_derive`).

## Evidence

| Phase | Path |
|-------|------|
| RED | `reports/dispatch-pd/evidence/PD-GIT-STAGE-PATH-01/red.txt` |
| GREEN | `reports/dispatch-pd/evidence/PD-GIT-STAGE-PATH-01/green.txt` |

## Files touched

- `crates/sgenaxis-ports/src/git.rs` — `stage_path` on `GitWritePort`
- `crates/sgenaxis-adapters/src/{std_git_write,git_write,fake}.rs` + `tests_git.rs`, `tests_git02.rs`
- `crates/sgenaxis-host/src/git_stage_path.rs`, `ipc.rs`, `lib.rs`
- `src-tauri/src/{commands,dto,lib}.rs`, `permissions/host.toml`
- `ui/{app.js,git-ux-mock.js}`

## Out of scope (not implemented)

FILE-UNSTAGE, FILE-DISCARD, hunk, merge, rebase slices; `docs/board.json` unchanged per task.