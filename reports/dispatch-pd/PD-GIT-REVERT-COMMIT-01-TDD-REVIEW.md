# PD-GIT-REVERT-COMMIT-01 — Independent TDD review

**Verdict:** **TDD_PASS**

**Date (UTC):** 2026-11-14  
**Verifier:** `independent-tdd-revert-commit-01` (independent verifier agent; did not implement this slice)  
**Implementer (per PR):** cursor-dev — **distinct** from verifier

**Reviewed PR:** https://github.com/roy791202/AIAD/pull/42  
**Reviewed branch:** `feature/PD-GIT-REVERT-COMMIT-01-revert-commit`  
**Reviewed commit:** `2840f9e7f81f6582d6ea1de56b4ad1c560b30f6a` (at verification time, local `HEAD` on that branch)  
**BDD ID:** `BDD-PD-GIT-REVERT-COMMIT-01` — approval-gated `git revert --no-edit -- <sha>`; deny → no mutation; merge commits fail without invented `-m 1`; never `--force` / `reset --hard` / silent `--no-commit`; credential redaction on errors

## Commands (independent re-run)

| Step | Command | Exit | Notes |
|------|---------|------|-------|
| 1 | `cd apps/sgenaxis-desktop && cargo test -p sgenaxis-adapters revert_ --features std-adapters` | **0** | **9 passed**, 0 failed |

**Toolchain:** `rustc 1.83.0`, `cargo 1.83.0`

### Full command output (step 1)

```text
warning: variant `Unsupported` is never constructed
   --> crates/sgenaxis-adapters/src/conpty_fixture.rs:273:21
    |
273 | enum PipeApiError { Unsupported, Create, Transfer, Close }
    |      ------------   ^^^^^^^^^^^
    |      |
    |      variant in this enum
    |
    = note: `PipeApiError` has derived impls for the traits `Debug` and `Clone`, but these are intentionally ignored during dead code analysis
    = note: `#[warn(dead_code)]` on by default

warning: `sgenaxis-adapters` (lib test) generated 1 warning
    Finished `test` profile [unoptimized + debuginfo] target(s) in 0.03s
     Running unittests src/lib.rs (target/debug/deps/sgenaxis_adapters-bcf63be808cfd8ce)

running 9 tests
test tests_git_revert_commit::fake_revert_failure_redacts_credentials ... ok
test tests_git_revert_commit::fake_revert_denied_without_approval_no_new_commit ... ok
test tests_git_revert_commit::fake_revert_approved_records_revert_commit ... ok
test tests_git_revert_commit::fake_revert_merge_commit_fails_without_invented_m1 ... ok
test tests_git_revert_commit::fake_revert_missing_sha_fails_honestly ... ok
test tests_git_revert_commit::std_revert_temp::std_revert_denied_leaves_head_unchanged ... ok
test tests_git_revert_commit::std_revert_temp::std_revert_unknown_sha_and_flags_fail_honestly ... ok
test tests_git_revert_commit::std_revert_temp::std_revert_approved_creates_new_commit ... ok
test tests_git_revert_commit::std_revert_temp::std_revert_merge_commit_fails_without_m1 ... ok

test result: ok. 9 passed; 0 failed; 0 ignored; 0 measured; 191 filtered out; finished in 0.04s

     Running tests/phase1_file_commit.rs (target/debug/deps/phase1_file_commit-5cf1e9bd5fab7de6)

running 0 tests

test result: ok. 0 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out; finished in 0.00s
```

## Contract checks (code read + tests)

| Requirement | Evidence | Result |
|-------------|----------|--------|
| Denied approval → no mutation | `fake_revert_denied_without_approval_no_new_commit`; `std_revert_denied_leaves_head_unchanged` | **PASS** |
| Approved → `git revert --no-edit -- <sha>` | `StdGitWrite::revert_commit` invokes `["revert", "--no-edit", "--", rev]`; `std_revert_approved_creates_new_commit` (new HEAD, Revert subject, clean porcelain) | **PASS** |
| Merge commits fail without `-m 1` | `is_merge_commit` via `sha^2`; fake + std tests assert `mainline` in error; HEAD unchanged | **PASS** |
| No `--force` / `reset --hard` / `--no-commit` on path | `commit_sha_out_of_scope` rejects flags; std never passes `-n`/`--force`; approved test asserts porcelain empty (not index-only revert) | **PASS** |
| Unknown / missing sha fails honestly | `fake_revert_missing_sha_fails_honestly`; `std_revert_unknown_sha_and_flags_fail_honestly` | **PASS** |
| Credential redaction on revert errors | `fake_revert_failure_redacts_credentials`; fake/std errors via `redact_credentials` / `git_error_redacted` | **PASS** |

## Test inventory (`revert_` filter)

| Test | Result |
|------|--------|
| `fake_revert_denied_without_approval_no_new_commit` | PASS |
| `fake_revert_approved_records_revert_commit` | PASS |
| `fake_revert_missing_sha_fails_honestly` | PASS |
| `fake_revert_merge_commit_fails_without_invented_m1` | PASS |
| `fake_revert_failure_redacts_credentials` | PASS |
| `std_revert_denied_leaves_head_unchanged` | PASS |
| `std_revert_approved_creates_new_commit` | PASS |
| `std_revert_unknown_sha_and_flags_fail_honestly` | PASS |
| `std_revert_merge_commit_fails_without_m1` | PASS |

## Gaps and limits

1. **Port-only slice:** No Tauri IPC / host command for `revert_commit` in this PR (consistent with implementer dispatch report).
2. **No checked-in `.feature`** file located for `BDD-PD-GIT-REVERT-COMMIT-01` under `docs/bdd/`; behavior asserted via `tests_git_revert_commit.rs`.
3. **`src-tauri` integration tests:** Not in scope for the mandated command filter (`revert_` on `sgenaxis-adapters` only).

## Integrity checks (verifier)

- Did **not** modify product source, tests, `.feature`, or `docs/board.json`.
- Did **not** set Done / blue light on board.
- Re-ran tests locally; did not accept implementer self-report as sole evidence.
- Did **not** open product-code fix PR on contract failure (N/A — contract satisfied).

## Outcome

**TDD_PASS** — `cargo test -p sgenaxis-adapters revert_ --features std-adapters`: **9/9 green**.