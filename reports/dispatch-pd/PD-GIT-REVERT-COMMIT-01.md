# PD-GIT-REVERT-COMMIT-01 — dispatch report

**Agent:** cursor-dev / PD-GIT-REVERT-COMMIT-01 dedicated implementation  
**BDD:** BDD-PD-GIT-REVERT-COMMIT-01  
**Status:** `READY_FOR_TDD` (implementation agent; not verifier)

## Summary

Added `GitWritePort::revert_commit(repo, sha, approval)`:

| Gate | Behavior |
|------|----------|
| Denied | `PermissionDenied`; no new commit; HEAD unchanged (std + fake) |
| Approved | `git revert --no-edit -- <sha>` via `StdGitWrite`; fake records revert commit |
| Missing / unknown sha | Honest failure; no mutation |
| Merge commit | Detected via `sha^2`; fails without inventing `-m 1` |
| Flags / force / no-commit | Rejected at validation (`commit_sha_out_of_scope`) |

Never `--force`, `reset --hard`, or `--no-commit` on this path. Errors credential-redacted.

## Tests

```text
cargo test -p sgenaxis-adapters revert_ --features std-adapters
# 9 passed (5 fake + 4 std temp-repo)
```

## Files

- `apps/sgenaxis-desktop/crates/sgenaxis-ports/src/git.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/git_write.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/std_git_write.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/fake.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/tests_git_revert_commit.rs`
- `apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/lib.rs`

Host/Tauri command not added (port-only slice; no UI wire in scope).