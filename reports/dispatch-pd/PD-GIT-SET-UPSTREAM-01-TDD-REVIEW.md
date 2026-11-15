# PD-GIT-SET-UPSTREAM-01 independent TDD review

**Verdict: TDD_PASS**

- Task: `PD-GIT-SET-UPSTREAM-01`
- Implementation PR: https://github.com/roy791202/AIAD/pull/78
- Implementation branch: `feature/PD-GIT-SET-UPSTREAM-01-set-upstream` @ `1924b56986bc6a72b93475995e0326a94267b117`
- Evidence branch: `feature/PD-GIT-SET-UPSTREAM-01-tdd-review`
- Date: 2026-11-15T01:20:00Z
- Developer: `cloud-dev-agent-cursor` / Cursor automation (`bc-ebcf4a54`; PR opened by `cursor[bot]`)
- Verifier (this run): independent TDD verifier `bc-321ccf88` (not the implementer; not Done / not blue)

## Command

```bash
cd apps/sgenaxis-desktop
cargo test --features std-adapters pd_git_set_upstream_01
```

Exit code: **0**

Environment: Linux `cursor` 6.12.113+; `rustc 1.83.0`; `git 2.43.0`.

## Counts (exact)

Lib unit tests in `sgenaxis-adapters` matching `pd_git_set_upstream_01`:

- **3 passed**
- **0 failed**
- **0 ignored**
- **0 measured**
- **191 filtered out**
- finished in ~0.05s

Task filter total used for verdict: **3/3 GREEN**.

## Matched tests (all ok)

1. `git_set_upstream::pd_git_set_upstream_01_1_denied_no_upstream`
2. `git_set_upstream::pd_git_set_upstream_01_2_granted_tracks_without_fetch`
3. `git_set_upstream::pd_git_set_upstream_01_3_missing_remote_and_invalid_names_fail`

## BDD trace

| BDD ID | Test |
|---|---|
| PD-GIT-SET-UPSTREAM-01-1 | `pd_git_set_upstream_01_1_denied_no_upstream` |
| PD-GIT-SET-UPSTREAM-01-2 | `pd_git_set_upstream_01_2_granted_tracks_without_fetch` |
| PD-GIT-SET-UPSTREAM-01-3 | `pd_git_set_upstream_01_3_missing_remote_and_invalid_names_fail` |

Feature file: `docs/bdd/PD-GIT-SET-UPSTREAM-01.feature` (added on implementation branch).

## Assertion / scope checks

- Tests were **not** weakened, skipped, or rewritten by this verifier.
- Product adapter sources (`std_git_write.rs`, `fake.rs`, etc.) were **not** modified on PR #78; this PR is a TDD-lock + BDD + board slice only.
- `docs/board.json` was **not** edited by the verifier.
- Task card was **not** set Done / blue.

Assertions exercised (spot-check, no modification):

- Denied approval → `PermissionDenied`, no upstream, no fetch/push/switch side effects (Fake + `StdGitWrite` temp repo under `std-adapters`).
- Granted → tracks `origin/main`, no fetch/push/checkout (Fake + Std).
- Missing remote/ref/local and option-like names → honest errors without creating remotes/branches.

## Placement flag — adapter-only scenario tests

**FLAG:** All three `pd_git_set_upstream_01_*` scenario-ID tests live only in  
`apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/git_set_upstream.rs`  
(registered via `lib.rs` `mod git_set_upstream` under `#[cfg(test)]`).

There are **no** matching `pd_git_set_upstream_01_*` tests in `sgenaxis-host`.

`sgenaxis-host/src/git_set_upstream.rs` already contains separate unit tests  
(`approved_set_upstream_succeeds`, `unapproved_and_validation_refuse_without_mutation`) that use `FakeGitWrite` against `perform_git_set_upstream` but **do not** carry BDD scenario IDs and were **not** changed in PR #78. That matches the task note allowing optional host tests, but it means BDD scenario locking is **adapter-port-only** for this slice—not host/use-case layer.

Comparable git TDD locks (e.g. PD-GIT-CREATE-BRANCH-01) placed scenario-ID tests in `tests_git.rs` / `tests_git02.rs` instead of a dedicated module file; this task chose a standalone `git_set_upstream.rs` test module instead.

## Other gaps (non-blocking for TDD_PASS)

- Developer cited `reports/dispatch-pd/PD-GIT-SET-UPSTREAM-01.md` on the board; that file is **not** present on PR #78 (only BDD, board, adapter test module, `lib.rs` hook).
- Independent verifier did **not** replay historical RED; only independent GREEN re-run is recorded here.
- PR #78 CI: `tests` and `lint + test subset` **success**; `guard` **failure** (board Story BDD entries not Green while Task `tdd` is Green; new `.feature` without `spec-change` label). Out of verifier scope but noted for merge gate.

## Warning observed (not a test failure)

`sgenaxis-adapters` lib test compiled with 1 `dead_code` warning: unused `PipeApiError::Unsupported` in `conpty_fixture.rs`. Unrelated to this task filter.

## Compare URLs

- Implementation PR: https://github.com/roy791202/AIAD/pull/78
- Implementation compare: https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-SET-UPSTREAM-01-set-upstream
- Evidence compare: https://github.com/roy791202/AIAD/compare/main...feature/PD-GIT-SET-UPSTREAM-01-tdd-review