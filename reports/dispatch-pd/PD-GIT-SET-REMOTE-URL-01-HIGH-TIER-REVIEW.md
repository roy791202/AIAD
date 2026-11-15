# PD-GIT-SET-REMOTE-URL-01 — High-tier PR review (Section B)

| Field | Value |
|-------|--------|
| **Verdict** | **CHANGES_REQUIRED** |
| **Subject PR** | https://github.com/roy791202/AIAD/pull/76 |
| **Branch** | `feature/PD-GIT-SET-REMOTE-URL-01-set-url` |
| **Head SHA (reviewed)** | `f411e5729ef13a68dbf9d9abe41fcede462edf38` (PR later at `5d4524e52`; same test delta) |
| **Developer agent** | `cloud-dev-agent-composer-PD-GIT-SET-REMOTE-URL-01` (≠ `bc-e102cbed`) |
| **Reviewer agent** | Independent high-tier cloud agent (Composer), role `high-tier` |
| **Reviewed at** | 2026-11-15T09:20:00+08:00 |

## Scope

High-tier review per `ai-dev-pr-acceptance` §B for task **PD-GIT-SET-REMOTE-URL-01** / story **S-GIT-WRITE-SET-REMOTE-URL-01**. No product adapter or assertion changes in this review artifact. **Did not** set Done / blue on the board.

## Dispatch checklist (requested)

| Check | Result | Evidence |
|-------|--------|----------|
| Architecture: `set_remote_url` must not fetch or use `--push` / `--mirror` / `--add` / `--delete` on this path | **PASS** | PR does not modify adapters; existing `StdGitWrite::set_remote_url` invokes `git remote set-url -- <name> <url>` only (`std_git_write.rs` L773–789). Tests assert no `FETCH_HEAD`, `push_count == 0`, empty tracking refs (Fake). |
| Allowed files only | **PASS** | Diff vs `main`: `tests_git.rs`, `tests_git02.rs`, `docs/board.json`, `reports/dispatch-pd/PD-GIT-SET-REMOTE-URL-01{,-red,-test-output}.md` — within task allow-list (tests + board + dispatch report). |
| No `.feature` edits | **PASS** | No `.feature` in PR diff. |
| Board status token `In Review` (not `In Review / In QA`) | **PASS** | Story + Task `status`: `"In Review"`. |
| Story `bdd[]` rows vs Task `tdd` / `scenarioIds` | **PASS** | Three scenarios `PD-GIT-SET-REMOTE-URL-01-{1,2,3}` on Story all `Green`; Task `tdd`: `Green`; `scenarioIds` match. |
| No Done / blue | **PASS** | Story/Task `light`: `Green`; no `Done` / `Shipped`; no blue completion state. |
| No skip / ignore on new tests | **PASS** | Six `pd_git_set_remote_url_01_*` tests run Green; no `#[ignore]` in added blocks. |

## §B summary

### 1–3 Architecture and scope

- **PASS.** TDD-lock only; port adapter implementation pre-existed on `main`. New coverage is Fake + Std integration-style unit tests with scenario IDs. No new coupling, no port bypass, no platform-hardcoded paths in the PR delta.

### 4 Clean Code

- **PASS.** Tests are focused, name-mapped to BDD IDs, use existing fixtures (`FakeGitWrite`, `make_worktree_with_bare_remote`). No weakened assertions or magic behavior changes.

### 5–7 Production readiness / hooks

- **PASS (task-appropriate).** Git write path validates approval, trims input, rejects option-like names via shared `remote_name_out_of_scope` / `remote_url_out_of_scope`. PR does not touch `.ai-hooks`, `.githooks`, or workflows.

### 8 BDD + TDD

- **PASS.** Trace: each BDD ID → two tests (Fake + Std). RED evidence file present; reviewer re-ran:

  ```text
  cargo test pd_git_set_remote_url_01 --features std-adapters
  → 6 passed; 0 failed; 0 ignored
  ```

### 9 Completeness

- **PASS.** Task delivers scenario TDD lock only; no TODO stubs in scope.

### 10 Board

- **PASS** on requested status token (`In Review`), lights (Green, not blue), and BDD/tdd alignment. **CHANGES_REQUIRED:** missing Task `prUrl`; Task `ci: Pending` while `rust-windows` already **failed** on head SHA (board should reflect Red/Yellow once CI is known).

### 11–12 CI / commits

- **CHANGES_REQUIRED.** Linux: `guard`, `tests`, `lint + test subset` **success** on `f411e572`. **Windows `rust-windows` failed** (job `132653908968`):

  | Test | Failure |
  |------|---------|
  | `pd_git_set_remote_url_01_2_*` (Std) | `approved set-url: Other("fetch/force/set-url/push remote writes are out of scope")` |
  | `pd_git_set_remote_url_01_3_*` (Std) | `missing` remote: expected `PortError::Git(_)`, got out-of-scope / non-Git error |
  | `std_write_set_remote_url_without_fetch_when_approved` | same ghost-remote assertion (pre-existing; same fixture pattern) |

  **Root cause:** `StdGitWrite` uses `remote_url_out_of_scope` (`git_write.rs` L143–157), which treats `\` as out of scope. Windows `std_write_temp` fixtures pass bare-repo paths like `D:\a\_temp\...` as URLs, so legitimate `set-url` is rejected before `git` runs. Fake tests pass on all OS; Std scenario tests are **not** Green on the Windows target platform.

- PR commits use Conventional Commits. No hook/workflow edits in diff.

## Required changes (return to dev agent on PR #76)

1. **Fix Windows Std scenario tests** without skip/ignore: use remote URL forms that satisfy `require_remote_url` on Windows (e.g. `file:///` with forward slashes, or shared helper that normalizes temp bare paths cross-platform). Re-run `rust-windows` until Green.
2. **Board:** add `prUrl`: `https://github.com/roy791202/AIAD/pull/76` on Task `PD-GIT-SET-REMOTE-URL-01`; set Task `ci` to match GitHub after fixes (Yellow/Red if Windows still failing).
3. **Do not** set Done / blue until CI all Green and §A verifier completes.

## What passed (no rework needed)

Dispatch checklist (architecture, allow-list, no `.feature`, `In Review` token, BDD/tdd alignment, no Done/blue, no skip) and Fake-layer TDD lock meet the requested review criteria. Adapter `set_remote_url` on `main` already uses `git remote set-url --` only (no fetch/`--push`).

## Pipeline gates not completed by this review

**Independent mid-tier verification (§A)** is still required and is not replaced by this document.

## Recommendation

**Return PR #76 to implementation** for Windows Std test / fixture fix only (no verifier changes to product assertions from this reviewer). Re-request high-tier review after `rust-windows` Green.