# High-tier review — PD-GIT-HUNK-UNSTAGE-01 (section B)

| Field | Value |
| --- | --- |
| Task | PD-GIT-HUNK-UNSTAGE-01 |
| Product PR | https://github.com/roy791202/AIAD/pull/14 @ `9729588322f460d27f06821c7cd1d79b2d6e8e01` |
| Product branch | `feature/PD-GIT-HUNK-UNSTAGE-01-hunk-unstage` (draft, **dirty** vs `main`) |
| Evidence branch | `feature/PD-GIT-HUNK-UNSTAGE-01-high-tier-review` (this file + `reports/` copy) |
| Reviewer | `bc-35de27d2-be1d-5b48-bb77-3c8f1364cd66` (`high-tier`, section B only) |
| Developer | `bc-924d2778` (`dev-agent`, product PR #14) |
| Independent TDD verifier | `bc-c8782bb0` (named on PR #14 / board; **no** separate TDD evidence PR open at this review) |
| Overlap product | https://github.com/roy791202/AIAD/pull/5 (`unstage_hunk`) |
| Overlap high-tier | https://github.com/roy791202/AIAD/pull/18 |
| Date | 2026-11-14T17:20:00Z |
| Board | Card stays **In Review**. **Not Done / not Blue.** This agent does **not** merge PR 14 or PR 5. |

Identities are three distinct agents. Reviewer is not the implementer and not the TDD verifier. Product code and TDD were not modified. A prior board note claiming high-tier PASS (`bc-924f58d5` on the **product** PR) is **not** this review and is not an evidence PR.

## Verdict

**FAIL** for merging PR 14 as-is.

Product behavior on PR 14’s own contract (`GitWritePort::hunk_unstage(path, hunk_spec: &str)`) matches the Task BDD (gated unstage, approval deny, no `--hard` / extra ops, `OPERATION_IN_PROGRESS`). That slice quality is **not** the blocker.

**Must-fix (blocks merge):** dual Port vs PR 5. Do not land both. Prefer PR 5 `unstage_hunk(path, old_start: u32)` if HUNK-STAGE lands first; **rebase or close PR 14**. Also: PR 14 is `mergeable_state: dirty`; Guard/CI for this SHA is **not recorded** (`ci: None` while the card is Green).

This agent does **not** merge either product PR and does **not** set Done/Blue.

Independent TDD (section A): **accepted as named identity only**. Host 3 + adapters 3 claimed TDD_PASS; `src-tauri` **NOT RUN** (Cargo 1.83 vs `edition2024`). UI E2E **NOT RUN**. No independent TDD docs PR analogous to #16/#15 existed at review time. Neither NOT RUN is treated as PASS.

## Overlap ruling (PR 5 vs PR 14) — MUST-FIX

| | PR 5 (`PD-GIT-HUNK-STAGE-01`) | PR 14 (`PD-GIT-HUNK-UNSTAGE-01`) |
| --- | --- | --- |
| Method | `GitWritePort::unstage_hunk` | `GitWritePort::hunk_unstage` |
| Hunk identity | `old_start: u32` (`@@ -<n>`) | `hunk_spec: &str` (full `@@` line) |
| Apply | `git apply --cached --reverse` | `git apply --cached -R` (same git flag family) |
| Host / IPC | `perform_git_unstage_hunk` / `git_write_unstage_hunk` | `perform_git_hunk_unstage` / `git_write_hunk_unstage` |
| UI | PR 5 wires `HUNK-UNSTAGE` on the live capture path | PR 14 does **not** change `ui/app.js` (mock already has the id) |

**Contracts are not identical.** Dual-land would add two Port methods, two IPC names, and two host modules for one user action. That is **must-fix**. The identical-contract duplicate exception does **not** apply.

**Recommendation:**

1. Do **not** merge PR 5 and PR 14 together as-is.
2. Canonical P2-6 / HUNK-UNSTAGE Port is **one** method: prefer PR 5’s `unstage_hunk(path, old_start: u32)` if STAGE-01 is first land (matches `stage_hunk`, already independently TDD’d on PR 5, already reviewed in PR 18).
3. After STAGE-01 lands: **rebase PR 14 onto that contract or close it as duplicate**. Do not keep `hunk_unstage(&str)` beside `unstage_hunk(u32)`.
4. FILE-STAGE (PRs 9–12) is a different path (`stage_file`); it does not resolve this hunk dual-API.

PR 14 Task note allowed “若尚未合入則只加本方法” for HUNK-STAGE. STAGE is still unmerged, so adding only `hunk_unstage` was in-scope for the slice. **Program merge** still cannot keep both APIs.

## B.1 Architecture / allowed files / identities

Allowed (Task): `sgenaxis-ports` `git.rs`; adapters `std_git_write.rs` / `fake.rs` / `git_write.rs`; host `git_hunk_unstage.rs` + `lib.rs`; `src-tauri` commands/dto; matching tests.

PR 14 also changes `docs/board.json` (Guard card binding) and **M06 preflight review HTML/JSON** (out of this Task; piggyback on the same branch). No `.feature` edits. No `.ai-hooks` / `.githooks` / workflows.

No skip/only observed on the named `pd_git_hunk_unstage_01_*` tests.

## B.2 Coupling / platform

Mutations go through `GitWritePort`. Std adapter: `Command` + `-C` + `apply --cached -R --` with stdin patch. Path via `require_hunk_path` / conflict-path style guards. Gated adapter always `PermissionDenied`. IPC allowlists `git_write_hunk_unstage` and rejects `git_hunk_unstage` / `git_reset_hard`. Renderer does not spawn git in this PR (no `app.js` change).

## B.3 Layering

- Port: `hunk_unstage` + approval + `OPERATION_IN_PROGRESS` docs.
- Adapter: extract cached hunk, `apply --cached -R`, refuse unmerged / binary / missing.
- Host: `approved == false` never calls Port with granted token.
- API: authorize + repo resolve + gated short-circuit (src-tauri command tests **NOT RUN**).
- UI: not delivered on this PR; mock already lists `HUNK-UNSTAGE`.

No ORM leak. Host does not parse patches beyond passing `hunk_spec`.

## B.4 Clean Code

Host module is short, named, Result/DTO. Adapter `hunk_unstage` is linear with guards. Product path does not `unwrap` on expected git failures.

Suggestion (non-blocking): `hunk_spec: &str` vs PR 5 `old_start: u32` is the overlap; do not keep both “for flexibility.”

## B.5 Production-readiness

Default-deny approval; gated adapter deny even if granted; conflict `OPERATION_IN_PROGRESS`; index-only apply; no `reset --hard` / `--force` / `git add -A` on this path. Credentials use existing `git_error_redacted`. Path option-like tokens refused.

`src-tauri` command tests **NOT RUN** (edition2024). Not forged PASS.

## B.6 Algorithm / performance

Hunk extract is a linear scan of `git diff --cached` for one path. Check-then-apply is a handful of git invocations. No O(n²) over the repo. No performance claims.

## B.7 Hooks

PR 14 does not change `.ai-hooks/`, `.githooks`, or `.github/workflows`. Product commits are Conventional (`feat(git):`, `chore(board):`). M06 docs on the same PR are extra scope, not a hook bypass.

## B.8 BDD + TDD

| Scenario | Tests (PR 14) | Independent result |
| --- | --- | --- |
| PD-GIT-HUNK-UNSTAGE-01-1 | Fake + Std + host approved unstage-one-hunk | Claimed TDD_PASS by `bc-c8782bb0`; this reviewer did not re-run |
| PD-GIT-HUNK-UNSTAGE-01-2 | Unapproved zero mutation | Claimed TDD_PASS |
| PD-GIT-HUNK-UNSTAGE-01-3 | Conflict `OPERATION_IN_PROGRESS` | Claimed TDD_PASS |
| src-tauri | `pd_git_hunk_unstage_01_git_write_hunk_unstage_gated_and_allowlisted` | **NOT RUN** |

No in-tree `.feature` for these IDs (board BDD only). PR did not delete `.feature`. Assertions were not weakened by this reviewer.

## B.9 Completeness

Port → Fake/Std → host → IPC allowlist → Tauri command are present for `hunk_unstage`. Live `ui/app.js` hook is **not** in this PR (Task allow-list omitted it). Completeness of **program** HUNK-UNSTAGE vs PR 5 is the overlap hold.

## B.10 Board

Card `PD-GIT-HUNK-UNSTAGE-01`: Task, parent `PD-GIT-02`, branch `feature/PD-GIT-HUNK-UNSTAGE-01-hunk-unstage`, PR #14, In Review, **Green**, `tdd` Green, `ci` **None**, hours (no storyPoints), not Done/Blue.

**Board mismatch:** Green with `ci: None` and no GitHub check runs on `97295883`. Light should not be Green until CI is known. This reviewer does **not** rewrite `docs/board.json`.

Prior note “獨立高階審查 PASS（bc-924f58d5）” on the product PR is a different agent and is not this evidence file.

## B.11 CI / version

| Check @ `97295883` | Conclusion |
| --- | --- |
| Combined status | pending / **zero** statuses |
| Check runs | **none** |
| Workflow runs for this SHA | **none** |

AI Dev Guard cannot be certified Green on this HEAD. rust-windows not observed here. No SemVer/CHANGELOG. Not a deploy.

PR 14 `mergeable_state: dirty` against `main`.

## Punch list (must-fix before merge)

1. **Dual Port:** do not merge PR 14 alongside PR 5. Prefer `unstage_hunk(path, old_start: u32)`. Rebase PR 14 onto that contract **or close PR 14**.
2. **Rebase** PR 14 (dirty vs `main`) after the chosen canonical land — or close without merge.
3. **CI / Guard** must actually run on the surviving HEAD; do not merge with `ci: None`.
4. Do not treat board Green / prior `bc-924f58d5` product-PR note as this independent high-tier evidence.

Non-blocking:

- `src-tauri` / UI E2E remain NOT RUN on Cargo 1.83 / headless Linux.
- Independent TDD should land its own docs PR (like #16) if the batch still requires a paper trail.
- Drop M06 files from a git-write product PR if the branch is kept.
- Wire live `app.js` only after the Port name is unified (PR 5 already does `HUNK-UNSTAGE`).

## Outcome

**FAIL** to merge PR 14 as-is.

Product gated `hunk_unstage` behavior is acceptable **in isolation**. **Overlap with PR 5 is must-fix.** Prefer PR 5 if HUNK-STAGE lands first; rebase/close PR 14 rather than dual APIs.

Reviewer bcId: `bc-35de27d2-be1d-5b48-bb77-3c8f1364cd66`.
