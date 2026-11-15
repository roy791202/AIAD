# PD-GIT-RENAME-REMOTE-01 — High-tier PR review (section B)

**Verdict: CHANGES_REQUIRED**

| Field | Value |
|-------|-------|
| Task | PD-GIT-RENAME-REMOTE-01 |
| PR | https://github.com/roy791202/AIAD/pull/77 |
| Branch | `feature/PD-GIT-RENAME-REMOTE-01-rename-remote` |
| Head SHA (reviewed) | `3dcb2e9f481d50f594dcd73f4c07f4d19b97447a` |
| Developer agent | `cloud-dev-agent-composer-PD-GIT-RENAME-REMOTE-01` (not bc-b06ff876) |
| High-tier reviewer | Independent cloud high-tier reviewer (not developer, not verifier bc-b06ff876) |
| Review date | 2026-11-15T09:30:00+08:00 |

## Dispatch checklist (requested focus)

| Check | Result | Evidence |
|-------|--------|----------|
| No fetch / set-url extra on `rename_remote` path | **PASS** | `StdGitWrite::rename_remote` runs only `git remote rename -- <old> <new>` (`std_git_write.rs`). Scenario tests assert `last_fetch` / `last_remote_set_url` / `push_count` on Fake; Std checks `FETCH_HEAD` absent and URL preserved (`tests_git.rs`, `tests_git02.rs`). BDD scenario 2 explicitly requires “no fetch, set-url extra, or push runs” (`docs/bdd/PD-GIT-RENAME-REMOTE-01.feature`). |
| Board status `In Review` (not `In Review / In QA`) | **PASS** | Task card `PD-GIT-RENAME-REMOTE-01` has `"status": "In Review"` in `docs/board.json`. |
| No Done / blue on Task | **PASS** | Task not `Done`; `light` is `Green`, not `Blue`; no `completedAt`. |
| No BDD weakening | **PASS (content)** | Added `PD-GIT-RENAME-REMOTE-01.feature` retains strict negative and no-side-effect clauses; scenarios were not softened or deleted. |

TDD for this Task was re-run independently: `cargo test pd_git_rename_remote_01` → **5 passed** (matches developer evidence).

## Section B — blocking findings

### 1. AI Dev Guard failed (merge gate)

CI job `guard` on PR #77 failed (7 items), including:

- Task `tdd: Green` while parent Story `S-GIT-WRITE-RENAME-REMOTE-01` BDD entries `PD-GIT-RENAME-REMOTE-01-{1,2,3}` remain `status: "None"`.
- PR adds or changes `.feature` files without `spec-change` label / CODEOWNERS path: `PD-GIT-RENAME-REMOTE-01`, `PD-GIT-SET-REMOTE-URL-01`, `PD-GIT-SET-UPSTREAM-01`, `PD-GIT-UNSET-UPSTREAM-01`.

Per ai-dev-pr-acceptance §B (guard + board): **cannot approve merge** until guard is green.

### 2. PR scope exceeds single Task

One Task PR should cover `PD-GIT-RENAME-REMOTE-01` only. This PR also adds three unrelated batch `.feature` files and bulk Story/Task cards for SET-REMOTE-URL, SET-UPSTREAM, and UNSET-UPSTREAM. Split batch board/BDD commits or justify with approved preproduction dispatch; do not mix into this Task PR.

### 3. Board card incomplete vs workflow

- Missing `prUrl` for PR #77 on `PD-GIT-RENAME-REMOTE-01`.
- `ci: "Pending"` while `guard` already **failed** — lamp should be **Yellow** or **Red** with `lightReason`, not green-at-risk mismatch.
- After verifier pass, Story-level `bdd[].status` must flip to `Green` for all three scenario IDs.

### 4. Developer dispatch report inaccuracy

`reports/dispatch-pd/PD-GIT-RENAME-REMOTE-01.md` states “(`.feature` not edited)” but the PR **adds** `docs/bdd/PD-GIT-RENAME-REMOTE-01.feature` (and three others). Correct the report or move `.feature` additions to an approved spec-change PR.

### 5. Minor test coverage gap (non-blocking suggestion)

`PD-GIT-RENAME-REMOTE-01-2` has Std adapter coverage only; Fake adapter lacks a `pd_git_rename_remote_01_2_*` test. Consider adding Fake parity for faster unit runs; Std path already satisfies BDD.

## Section B — passes (no block)

- **Role separation:** Reviewer is not the listed developer agent.
- **Allowed paths:** No product adapter changes in PR diff; tests only in allowed test modules + board + bdd + reports.
- **Layering:** Tests exercise Port/adapters only; no layer violations in diff.
- **Hooks / CI config:** PR does not modify `.ai-hooks`, `.githooks`, or workflow files.
- **TDD quality:** Scenario-ID test names align with BDD IDs; assertions are substantive (permission, URL preservation, duplicate/mutation guards).

## Required changes before high-tier approval

1. Fix guard failures: sync Story `bdd[].status` to `Green` for scenarios 1–3 when Task TDD is Green, or adjust Task `tdd` until Story reflects reality; resolve `.feature` policy (remove unrelated three features from this PR, or add `spec-change` + owner review for intentional adds).
2. Trim PR scope to Task `PD-GIT-RENAME-REMOTE-01` (or document approved batch exception).
3. Update board: set `prUrl` to PR #77, set `ci` to failure state until guard green, fix `light`/`lightReason` if CI red.
4. Fix dispatch report `.feature` claim.

## Post-fix

After developer addresses the above and CI guard is green, re-request high-tier review. High-tier may then set verdict **PASS** and support merge; **Done / blue** remains only after PR merge per workflow.