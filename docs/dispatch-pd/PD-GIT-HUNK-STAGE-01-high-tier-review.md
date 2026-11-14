# High-tier review — PD-GIT-HUNK-STAGE-01 (section B)

| Field | Value |
| --- | --- |
| Task | PD-GIT-HUNK-STAGE-01 |
| Product PR | https://github.com/roy791202/AIAD/pull/5 @ `f276e364794be0ec7b6a1f623871302c9d4fbb43` |
| Product branch | `feature/PD-GIT-HUNK-STAGE-01-hunk` |
| Evidence branch | `feature/PD-GIT-HUNK-STAGE-01-high-tier-review` (this file only) |
| Reviewer | `bc-e7065619-5654-5e6d-b6ae-7fa2535fe3ae` (`high-tier`, section B only) |
| Developer | `bc-e55e5ce8-c7e5-535e-b575-74036005e9ff` (`dev-agent`) |
| Independent TDD verifier | `bc-fa497e3c-51ba-543e-a4ef-48bc6cd37477` (`verifier`, section A) |
| TDD evidence | `reports/dispatch-pd/PD-GIT-HUNK-STAGE-01-tdd-review.md` on `feature/PD-GIT-HUNK-STAGE-01-tdd-review` |
| Date | 2026-11-14T16:30:00Z |
| Board | Card stays **In Review**. **Not Done / not Blue.** This agent does not merge PR 5 or PR 14. |

Identities are three distinct agents. Reviewer is not the implementer and not the TDD verifier. Product code and TDD were not modified.

## Verdict

**REVIEW_PASS** for PD-GIT-HUNK-STAGE-01 product quality against Task card S-GIT-WRITE-P2-5/6, subject to the overlap **merge hold** below.

Independent TDD: **TDD_PASS** for HUNK-STAGE automation only. `src-tauri` **NOT RUN** (Cargo 1.83 vs `edition2024`). UI E2E **NOT RUN**. Neither is treated as PASS.

This agent does **not** merge either PR and does **not** set Done/Blue.

## Overlap ruling (PR 5 vs PR 14)

| | PR 5 (`PD-GIT-HUNK-STAGE-01`) | PR 14 (`PD-GIT-HUNK-UNSTAGE-01`) |
| --- | --- | --- |
| Method | `GitWritePort::unstage_hunk` | `GitWritePort::hunk_unstage` |
| Hunk identity | `old_start: u32` (`@@ -<n>`) | `hunk_spec: &str` |
| Apply | `git apply --cached --reverse` | `git apply --cached -R` (equivalent git flag) |
| Host / IPC / UI | `perform_git_unstage_hunk` / `git_write_unstage_hunk` / `HUNK-UNSTAGE` | separate `hunk_unstage` surface |

**Contracts are not identical.** Dual-land would add two Port methods with different signatures for the same user action. That is **must-fix at merge / slice level**, not “acceptable identical contract.”

**Not a must-fix punch list against PR 5’s own Task card.** `PD-GIT-HUNK-STAGE-01` title and `scenarioIds` explicitly include **S-GIT-WRITE-P2-5 and S-GIT-WRITE-P2-6**. Landing `unstage_hunk` on PR 5 is in-scope for this Task (pre-production slice), not an out-of-scope sneak.

**Merge hold (program):**

1. Do **not** merge PR 5 and PR 14 as-is.
2. Canonical Port for P2-6 should be **one** method. Prefer PR 5’s `unstage_hunk(path, old_start: u32)` if STAGE-01 is the first land, because it matches the existing stage-hunk identity (`old_start`) and independent TDD already Green’d `s_git_write_p2_6_unstage_hunk` on that HEAD.
3. PR 14 must rebase/retarget onto that contract **or** be closed as duplicate after STAGE-01 merge. High-tier for UNSTAGE-01 is a different agent; this file does not accept PR 14.
4. Identical-contract duplicate would have been acceptable to keep on STAGE-01 and no-op UNSTAGE. **That exception does not apply here.**

## B.1 Architecture / allowed files / evidence / identities

Allowed surfaces used: `sgenaxis-ports` `GitWritePort`, adapters (`StdGitWrite`, `FakeGitWrite`, `GatedGitWrite`), host (`git_stage_hunk` / `git_unstage_hunk` / IPC allowlist), Tauri commands/DTO/permissions, `ui/app.js`. `docs/board.json` copy on the product PR is Guard binding, not product logic.

No `.feature` edits. No skip/only. No `--force` / `reset --hard` / `git add -A` on the hunk path.

TDD evidence is the independent verifier file (not author cargo logs). `src-tauri` NOT RUN recorded honestly.

## B.2 Coupling / platform

Git mutations go through `GitWritePort`. Adapter uses `Command` + `-C` + `apply --cached` with stdin patch; no UI shell. Path refused when empty or `conflict_path_out_of_scope`. Patch size capped (`MAX_GITIGNORE_BYTES`). Credentials redacted on git errors (existing helper).

## B.3 Layering

- Domain/port: trait docs + `GitWriteApproval`.
- Adapter: apply/extract hunk.
- Host: approval bool → Port granted/denied; DTO-shaped result.
- API: authorize + repo resolve + gated-adapter short-circuit.
- UI: existing git-approve modal; capture listener for `HUNK-STAGE` / `HUNK-UNSTAGE`.

No ORM leak. No business rule in CSS. Host does not parse patches.

## B.4 Clean Code

Host stage/unstage modules are small and parallel to other git-write hosts. Adapter `apply_selected_hunk` is denser than 20 lines but one operation (select hunk + check + apply). Fake lock `.expect` matches existing FakeGitWrite. Suggestion (non-blocking): UI capture takes the **first** `@@ -<n>` in the livediff; multi-hunk files should pass `data-` old_start from the clicked hunk when the mock/UI exposes it.

## B.5 Production-readiness

Approval default-deny; gated adapter always `PermissionDenied`; conflict `OPERATION_IN_PROGRESS`; tracked-file only; no worktree rewrite in tests. Tauri capabilities listed in `host.toml`. No new secrets. No unbounded stdin beyond existing ignore-byte cap.

Coverage of src-tauri unstage/stage command tests: **NOT RUN** here (edition2024). Not forged PASS.

## B.6 Algorithm / performance

Hunk extract is one linear scan of the path diff (O(n) lines of that file’s diff). Check-then-apply is two `git apply` calls. No O(n²) over the repo. No performance claims.

## B.7 Hooks

PR 5 does not change `.ai-hooks/`, `.githooks`, or `.github/workflows`. Commits are Conventional (`feat(git):`, `docs(board):`).

## B.8 BDD + TDD

| Scenario | Tests | Independent result |
| --- | --- | --- |
| S-GIT-WRITE-P2-5 | `s_git_write_p2_5_stage_hunk` fake + std; gated stage; host `git_stage_hunk` (3) | **TDD_PASS** |
| S-GIT-WRITE-P2-6 | `s_git_write_p2_6_unstage_hunk` fake + std; gated unstage; host `git_unstage_hunk` (3) | Green on PR 5 HEAD; overlap with PR 14 (see ruling) |
| src-tauri | `git_write_stage_hunk_gated_and_allowlisted` | **NOT RUN** |

No `.feature` files exist for these IDs in-tree (Story lives on the board). Assertions were not weakened by this reviewer.

## B.9 Completeness

PR 5 delivers the Task’s listed scenarios (stage + unstage hunk). No TODO stubs in the new host modules. Completeness of **program** P2-6 vs UNSTAGE-01 is the overlap hold, not an incomplete STAGE-01 PR.

## B.10 Board

Card `PD-GIT-HUNK-STAGE-01`: Task, parent `S-GIT-WRITE-P2`, branch `feature/PD-GIT-HUNK-STAGE-01-hunk`, PR #5, In Review, Yellow, `tdd` Green, hours estimate (no storyPoints), not Done/Blue. `ci` Pending matches rust-windows red + Guard green. Light reason present.

## B.11 CI / version

| Check @ `f276e364` | Conclusion |
| --- | --- |
| AI Dev Guard `guard` | success |
| AI Dev Guard `tests` | success |
| lint + test subset | success |
| rust-windows | **failure** (4 tests: remotes add/set-url; conflict continue editor `/bin/true` missing on Windows). Failures are **not** `s_git_write_p2_5/6`. Pre-existing editor/remote issues; not a STAGE punch list. |

No SemVer/CHANGELOG/release in this PR. Not a deploy.

## Punch list

Must-fix **before merging both hunk PRs** (not a STAGE-01 code revert):

- Unify `unstage_hunk(old_start: u32)` vs `hunk_unstage(hunk_spec: &str)` to a single Port contract; close or rebase PR 14.

Non-blocking:

- src-tauri / UI E2E still NOT RUN on Cargo 1.83 / headless Linux.
- rust-windows `/bin/true` editor and remote tests remain red on Windows CI; track separately if they are not already owned.
- UI first-`@@` heuristic for `oldStart`.

## Outcome

**PASS** for high-tier review of PD-GIT-HUNK-STAGE-01.

**Overlap:** **must-fix (non-identical contract / dual Port)** for merging PR 5 with PR 14. **Not** “acceptable identical contract.” STAGE-01 including P2-6 is **in-scope for this Task**.

Reviewer bcId: `bc-e7065619-5654-5e6d-b6ae-7fa2535fe3ae`.
