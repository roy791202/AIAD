# PD-GIT-RESTORE-PATH-01 — Independent TDD review

**Verdict:** **TDD_PASS**

**Date (UTC):** 2026-11-14  
**Verifier:** `independent-tdd-restore-path-01` (independent verifier agent; did not implement this slice)  
**Implementer (per PR #43):** `dev-agent/cursor-cloud-PD-GIT-RESTORE-PATH-01` — **distinct** from verifier

**Reviewed PR:** https://github.com/roy791202/AIAD/pull/43  
**Reviewed branch / SHA:** `feature/PD-GIT-RESTORE-PATH-01-restore-path` @ `2a851ccdc18057ee28f1e30769e3f3c98ad44682`  
**BDD ID:** `BDD-PD-GIT-RESTORE-PATH-01` (gated restore-path: approval → `git restore --source=HEAD --worktree -- <path>`; deny = no mutation; `OPERATION_IN_PROGRESS` when unmerged/in-progress; never `reset --hard`; never untracked delete)

## Commands (independent re-run)

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| 1 | `cd apps/sgenaxis-desktop && cargo test --package sgenaxis-adapters --features std-adapters restore_path` | **0** | **3 passed**, 0 failed, 191 filtered |

Toolchain at review: `rustc` / `cargo` via workspace build (fresh compile of `sgenaxis-adapters` with `std-adapters`).

```text
running 3 tests
test tests_git::gated_git_write_blocks_restore_path_even_when_approved ... ok
test tests_git::fake_git_write_restore_path_records_when_approved ... ok
test tests_git02::std_write_temp::std_write_restore_path_worktree_from_head_without_hard_reset ... ok

test result: ok. 3 passed; 0 failed; 0 ignored; 0 measured; 191 filtered out
```

## Contract checks (code + tests)

| Requirement | Evidence | Result |
|-------------|----------|--------|
| Denied approval → no mutation | `std_write_restore_path_worktree_from_head_without_hard_reset`: `GitWriteApproval::denied()` leaves `a.txt` / `b.txt` dirty; fake denied → `PermissionDenied`, no `last_restore_path` | **PASS** |
| Approved → `git restore --source=HEAD --worktree -- <path>` only | `StdGitWrite::restore_path` invokes `["restore", "--source=HEAD", "--worktree", "--", rel]`; integration test restores `a.txt` to `HEAD:a.txt` blob | **PASS** |
| Unmerged / in-progress → `OPERATION_IN_PROGRESS` | Std: `require_conflict_kind` + `ls-files -u`; fake: `set_conflict_in_progress`; both tests assert `OPERATION_IN_PROGRESS` substring | **PASS** |
| Never `reset --hard` on restore-path | Mutating call is `git restore` only (no `reset` in `restore_path`); test asserts `HEAD` SHA unchanged before/after | **PASS** |
| Never untracked delete | Std test keeps `new.txt` content and `?? new.txt` in porcelain; restore on untracked path errors; fake `mark_restore_untracked` errors without updating `last_restore_path` | **PASS** |
| Gated adapter default-deny | `gated_git_write_blocks_restore_path_even_when_approved` | **PASS** |
| Scope hygiene (no `.` / `-f` widen) | Fake + std reject option-like path `-f`; fake rejects `.` with `PortError::Other` | **PASS** |

## Test inventory (`restore_path` filter)

| Crate | Test | Result |
|-------|------|--------|
| `sgenaxis-adapters` | `fake_git_write_restore_path_records_when_approved` | PASS |
| `sgenaxis-adapters` | `gated_git_write_blocks_restore_path_even_when_approved` | PASS |
| `sgenaxis-adapters` | `std_write_restore_path_worktree_from_head_without_hard_reset` | PASS |

## Implementer evidence (read, not sole basis)

| Path | Verifier assessment |
|------|---------------------|
| `reports/dispatch-pd/PD-GIT-RESTORE-PATH-01.md` | Consistent with independent 3/3; dev self-check only |

## Gaps and limits

1. **No checked-in `.feature`** for `BDD-PD-GIT-RESTORE-PATH-01` under `docs/bdd/` (behavior asserted via Rust tests and port doc on `GitWritePort::restore_path`).
2. **No host/Tauri IPC test** in this slice (dispatch notes port-only; not required for this TDD pass scope).
3. **Filtered suite only:** verifier re-ran `restore_path` filter (3 tests), not full `sgenaxis-adapters` lib (191 other tests not re-run in this review).

## Integrity checks (verifier)

- Did **not** modify product source, TDD assertions, `.feature`, or `docs/board.json`.
- Did **not** set Done / blue light on board.
- Re-ran tests locally; did not accept implementer self-check as sole evidence.

## Outcome

**TDD_PASS** for independent replay of `cargo test --package sgenaxis-adapters --features std-adapters restore_path` (**3/3** green) and static review of `restore_path` adapters against the slice contract above.