# PD-GIT-RENAME-BRANCH-01 — implementation evidence

**Role:** `dev-agent` (ai-dev-implementation). Not a verifier. Board not edited. No Done / blue.

**BDD:** Given `GitWriteApproval` When `rename_branch` Then only `git branch -m -- <old> <new>` if approved.
Empty / unapproved / missing / duplicate / invalid / `-M` fail honestly.
Never remote rename. Never switch/checkout as a separate step.
Occupying Run on current HEAD refuses **before** the port.

**Branch:** `feature/PD-GIT-RENAME-BRANCH-01-rename-branch`

## Scope

Allowed files only. Did not implement `delete_branch` / G01–G04.

| Layer | Behaviour |
|---|---|
| `GitWritePort::rename_branch` | Approval gate; validate names; refuse remote-only / missing / duplicate / `-M`; `git branch -m -- old new` |
| `GatedGitWrite` | PermissionDenied even if approved |
| `FakeGitWrite` | In-memory rename; no switch of non-current; remote-only marked refs refused |
| `StdGitWrite` | `branch -m --` only; never `-M`; never remote rename |
| `git_write_branch_rename` | Soft-gate empty/unapproved; occupying Run on current HEAD refuses before port; allowlisted command |

## TDD

Port + adapters + Tauri helper were already on `main` (`2a3f4f2`). This task:

1. Re-ran existing RED-intent cases (denied / empty / `-M` / missing / duplicate / `.git` / traversal / detached HEAD).
2. Added GREEN-strengthening std cases: empty new name, `--force`, remote-only `refs/remotes/origin/only-remote` (must not create a local branch).

### Adapter (GREEN)

```
cargo test -p sgenaxis-adapters rename_branch
  tests_git::fake_git_write_rename_branch_records_when_approved ... ok
  tests_git02::std_write_temp::std_write_rename_branch_non_force_only_when_approved ... ok

cargo test -p sgenaxis-adapters gated_git_write_blocks_branch_rename
  tests_git::gated_git_write_blocks_branch_rename_even_when_approved ... ok
```

### Occupying Run (host helper used by the command; port not called)

```
cargo test -p sgenaxis-host occupying_run_refuses_rename --lib
  git_rename::tests::occupying_run_refuses_rename_of_current_and_does_not_call_git_write ... ok
```

### Tauri `git_write_branch_rename`

`commands::git_write_branch_rename_gated_and_allowlisted` covers deny / empty / `-M` / `.git` / traversal / lease-on-current / rename-other-with-lease.

`cargo test --lib git_write_branch_rename` from `src-tauri` could not compile in this environment (`time-macros` requires edition2024; Cargo 1.83). Cases exist in `commands.rs` and were not weakened.

## Honesty / safety

- Unapproved / gated: `PermissionDenied`; no recorded rename.
- `-M` / `--force` / leading dash / `.git` / `../`: out of scope, no mutation.
- Duplicate target: Git / `already exists`, no `-M` fallback.
- Missing local: `not found`.
- Remote-only: refuse; no local invent; command is local `-m` only.
- Non-current rename does not switch HEAD (`head_ref` stays `main`).
- Current HEAD rename is adapter-ok when no lease; occupying Run refuses in `perform_git_write_branch_rename` before `GitWritePort`.

## Out of scope

- `delete_branch` / G01–G04 not changed as a feature in this task.
- `docs/board.json` not edited.
- Not merged. Independent verification required.
