# PD-GIT-DISCARD-FILE-01 independent TDD 实测

**Verdict:** `TDD_PASS`

Date: 2026-11-14 (UTC). Platform: Linux (cloud agent). Crate tests only; Tauri GUI not driven.

## Identity (must differ)

| Role | Agent id |
|---|---|
| Developer (must not verify) | `bc-860dbeac-55d6-557d-abc4-642c4550bc5a` |
| Independent verifier (this run) | `bc-1f54ee7a-209d-538d-8bbe-d749e49e9ba2` |

Identities are **not** the same. This run did **not** modify product code, tests, or `.feature` files. Board was **not** set to Done / Blue.

PR: https://github.com/roy791202/AIAD/pull/4  
Branch: `feature/PD-GIT-DISCARD-FILE-01-discard`  
HEAD observed: `2ff0b90 feat(git): gated discard-file via GitWritePort`

## BDD

`docs/bdd/S-GIT-WRITE-P2.feature` is **missing on this branch** (only `docs/bdd/S-CI-PR1.feature` is present). Scenarios were taken from the verification prompt:

- **S-GIT-WRITE-P2-3:** approve discard of one tracked dirty file restores worktree to index; deny leaves worktree unchanged; untracked files not deleted.
- **S-GIT-WRITE-P2-4:** out-of-repo / option-like / unmerged conflict path fails honestly; no `reset --hard` / `--force`.

## Commands re-run by verifier (do not trust author)

Working directory: `apps/sgenaxis-desktop`. Full transcript: `reports/dispatch-pd/PD-GIT-DISCARD-FILE-01-tdd-rerun.log`.

| Command | Result |
|---|---|
| `cargo test -p sgenaxis-adapters --lib s_git_write_p2` | **PASS** — 4 passed, 0 failed, 0 ignored (Fake + StdGitWrite temp repos) |
| `cargo test -p sgenaxis-host --lib discard_file` | **PASS** — 2 passed, 0 failed, 0 ignored |
| `cargo test -p sgenaxis-host --lib ipc::` | **PASS** — 3 passed, 0 failed, 0 ignored (`git_write_discard_file` allowlisted; `git_discard_file` rejected) |

No `#[ignore]` / skip on the matching tests.

## Scenario mapping

| Scenario | Tests (this branch) | Observed |
|---|---|---|
| S-GIT-WRITE-P2-3 | `tests_git::s_git_write_p2_3_discard_file`, `tests_git02::std_write_temp::s_git_write_p2_3_discard_file`, `git_discard_file::tests::s_git_write_p2_3_discard_file` | PASS. Std adapter: dirty `a.txt` restored to index (`staged\n`); `?? new.txt` still present; HEAD unchanged. Deny is covered in P2-4 tests. |
| S-GIT-WRITE-P2-4 | `*_p2_4_discard_reject` (Fake + Std + host) | PASS. Denied approval does not mutate; `-f` / `--force` / `../outside.txt` fail; untracked `new.txt` not deleted; unmerged conflict path errors with `unmerged` / `OPERATION_IN_PROGRESS`; merge state (`ls-files -u`) remains. Std implementation uses `git restore --worktree -- <path>` after path guards; not `reset --hard`. |

IPC: `is_allowed("git_write_discard_file")` true; `git_discard_file` / raw `git_restore` not allowed.

## UI E2E

**NOT RUN.** Reason: this is a Tauri desktop command (`git_write_discard_file` + `window.confirm` in `ui/app.js`). No native desktop GUI / confirmation dialog could be driven in this Linux cloud session. A live Tauri window with a real worktree was not started. **Not recorded as PASS.**

Attempt to compile the full `src-tauri` package for extra command tests failed on this toolchain (`edition2024` required by a crates.io dep under Cargo 1.83). That extra compile is **NOT RUN**; it is outside the three required crate filters.

## Limits

- Feature file not on this branch; mapping used prompt text + tests named `s_git_write_p2_*`.
- Section B (architecture / Clean Code review) is **not** this run; this is section A 实测 only.
- TDD_PASS here is **not** Story Done and does **not** authorize board Blue.

## Evidence paths

- `reports/dispatch-pd/PD-GIT-DISCARD-FILE-01-TDD-REVIEW.md` (required path; gitignored `reports/`)
- `reports/dispatch-pd/PD-GIT-DISCARD-FILE-01-tdd-rerun.log`
- `apps/sgenaxis-desktop/ui/review-results/independent-review/PD-GIT-DISCARD-FILE-01-TDD-REVIEW.md` (tracked copy)
- `apps/sgenaxis-desktop/ui/review-results/independent-review/PD-GIT-DISCARD-FILE-01-tdd-rerun.log`
