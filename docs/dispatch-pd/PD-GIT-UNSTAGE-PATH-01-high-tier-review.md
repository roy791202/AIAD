# PD-GIT-UNSTAGE-PATH-01 high-tier review (section B)

**Verdict (re-review @ `ee3eb30`): FAIL** — process only. Do **not** merge product PR #17. Card stays **In Review** (not Done / not Blue).

Product FILE-UNSTAGE behavior remains **PASS**. Independent re-TDD **TDD_PASS** (adapters 10, host 2, ipc 3) SHA `ee3eb30`; evidence `reports/dispatch-pd/PD-GIT-UNSTAGE-PATH-01-tdd-review.md` @ `7eea279`.

| Role | Identity |
|---|---|
| Implementer | `bc-9ae9a7a1-13a0-5697-8b53-8a920c9af5ca` |
| Independent TDD verifier | `bc-ec1eadff-734d-5728-a1bf-9fba29d3f770` |
| High-tier reviewer (this document) | `bc-5ef9421f-530e-5fd5-bf7f-7a0d35879b9a` |

This reviewer did not modify product code or TDD.

---

## Re-review @ `ee3eb309d88d8f60c286b97b3db7cd378b1cab17` (2026-11-14)

Follow-up commit: `fix(board): shorten FILE-UNSTAGE scenario ids for AI Dev Guard`. Test **renames only** (`s_git_wp2_fu_*`); assertions kept. Independent TDD re-ran Green.

### Prior must-fix disposition

| Prior item | Status |
|---|---|
| scenarioIds ≤40 + Story `bdd[]` | **Fixed.** Task ids `S-GIT-WP2-FU-1`..`5` (all ≤40). New Story `S-GIT-WP2` holds matching `bdd[].id` with `status: Green`. Guard no longer reports length/missing/not-Green. Task parent now `S-GIT-WP2`. |
| Board `prUrl` / Yellow / `ci` | **Fixed.** `prUrl` = https://github.com/roy791202/AIAD/pull/17 ; Task `light: Yellow` + `lightReason`; `ci: Red`. Status **In Review**. Not Done/Blue. |
| `.feature` `spec-change` | **Still open (process, not product regression).** PR labels still `[]`. Guard on `ee3eb30`: **1 item** — `修改了 BDD 情境（docs/bdd/S-GIT-WRITE-P2.feature），需要核准者加上 spec-change 標籤，並經 CODEOWNERS 審查`. `PR_LABELS` empty. Implementer cannot add the label. |

### Remaining must-fix

1. **Approver adds GitHub label `spec-change` on PR #17 and CODEOWNERS reviews `docs/bdd/S-GIT-WRITE-P2.feature`.** Then re-run Guard. Until Guard is green, **do not merge**. This is the only remaining section-B blocker.

CI snapshot @ `ee3eb30`: `tests` success, `lint + test subset` success, `guard` failure (spec-change only), `rust-windows` failure (same pre-existing `/bin/true` + remote-url tests; FILE-UNSTAGE tests still pass). Yellow + `ci: Red` remains correct. Do not expand this Task to fix rust-windows.

Section B.8: independent TDD_PASS; Given/When/Then unchanged; tags shortened. Weakening assertions: **not found**.

---

## Historical review @ `eadf562` (superseded)

**Verdict then: FAIL.** Kept below for audit. Do **not** merge product PR #17. Card stays **In Review** (not Done / not Blue).

Roles are three distinct agents. This reviewer did not modify product code or TDD.

- Product PR: https://github.com/roy791202/AIAD/pull/17 @ `eadf562` (superseded head `ee3eb30`)
- Branch: `feature/PD-GIT-UNSTAGE-PATH-01-unstage-path`
- Independent TDD: **TDD_PASS** (adapters 10, host 2, ipc 3). `src-tauri` **NOT RUN** (`edition2024`).
- Conventional commit: `feat(git): gated single-path unstage via GitWritePort` — OK.

---

## Must-fix (blocking)

1. **AI Dev Guard failed (12 items)** on `eadf562` (`guard` job conclusion: failure).
   - `scenarioIds` rejected: each id must be a **string ≤ 40 chars**. Current tags exceed that (`s_git_write_p2_file_unstage_conflict_operation_in_progress` = 56, others 42–53).
   - Those ids are **not registered** on any Story `bdd[]` (`scenarioIds … 不存在`).
   - Guard then reports every scenario **不是 Green**.
   - **Fix:** shorten scenario ids (≤40), add matching `bdd[].id` on parent Story (`PD-GIT-02` or a FILE-UNSTAGE Story), set `status: Green` only after independent TDD (already TDD_PASS for these five). Re-run Guard.

2. **`.feature` change without `spec-change`.** PR added `docs/bdd/S-GIT-WRITE-P2.feature`. Guard: needs approver **`spec-change` label** and CODEOWNERS review. Implementer must not invent BDD without that path. Either obtain the label + review, or drop the feature file from the product PR if high-tier already owns the scenarios elsewhere.

3. **Board vs CI (B.10).** Task `PD-GIT-UNSTAGE-PATH-01`: `light: Green`, `ci: None`, **no `prUrl`**. Actual CI: `guard` fail, `rust-windows` fail, `tests` / `lint + test subset` success. Green light with failed CI is invalid. Append history/notes (do not rewrite others). Set `prUrl` to PR #17. Set `ci` to Fail (or None until green) and **Yellow** + `lightReason` while Guard/CI fail. Never Done/Blue.

4. **Do not merge until Guard is green.** Section B: CI AI Dev Guard must pass.

---

## FILE-UNSTAGE behavior (reviewed; not the fail cause)

Reviewed `GitWritePort::unstage_path` on `eadf562`. **Behavior matches the ticket.** Independent TDD_PASS is trusted for adapters/host/ipc.

| Check | Result |
|---|---|
| Mixed `git reset -- <path>` only | **PASS.** `StdGitWrite::unstage_path` runs `["reset", "--", &rel]` from repo (`-C`). No `--hard`, `-f`, `-D`, `add -A`, commit, push. |
| Approval deny | **PASS.** `require_approval` / Fake `!approval.is_granted()` → `PermissionDenied`; no index mutation. Host `perform_git_unstage_path(..., false)` refuses before Port. |
| Path guards | **PASS.** Empty / NUL / newline; `worktree_path_out_of_scope` (`.`, `..`, `-f`, `--all`, traversal, `\\`); absolute `/` and `\\`; `ensure_path_in_repo` via `rev-parse --show-toplevel` + canonicalize prefix; missing path fails honestly. |
| `OPERATION_IN_PROGRESS` | **PASS.** In-progress merge/rebase/cherry-pick/revert **or** `ls-files -u` unmerged → `PortError::Git` containing `OPERATION_IN_PROGRESS`; no reset. |
| No `--hard` | **PASS.** Command vector is mixed pathspec reset only. |
| No unstage_all / hunk / discard creep | **PASS.** New Port method + Fake/Gated/Std + host `git_unstage_path.rs` + IPC allowlist. No hunk stage/unstage, no discard-file, no `unstage_all` rewrite. `lib.rs` re-export sort only. |
| Deny-by-default IPC | **PASS** at host: `git_write_unstage_path` allowlisted; `git_unstage_path` / raw names denied. `is_allowed` is enum parse only. |

`GatedGitWrite` still denies `unstage_path` even when approved.

**`src-tauri`:** command **not** registered in `commands.rs` / `lib.rs` invoke list / `permissions/host.toml`. Independent TDD **NOT RUN** (`edition2024`). Acceptable for this Port-layer slice; desktop invoke stays closed until a later IPC/UI task. Not a must-fix for FILE-UNSTAGE Port.

---

## Section B checklist

| # | Item | Result |
|---|---|---|
| 1 | Quality, architecture, BDD, allowed files, distinct roles | Architecture OK. Guard/board/BDD registry **FAIL**. Files: ports/adapters/host/ipc + board + new `.feature` (11 files). |
| 2 | No hardcoded platform APIs / Port bypass | **PASS.** Git via `Command` adapter; host uses `dyn GitWritePort`. |
| 3 | Layering | **PASS.** Port trait → adapters; host use-case; IPC allowlist. Domain-free write gate. |
| 4 | Clean Code | **PASS** for the new method. `require_conflict_path` now delegates to `require_worktree_path` (shared guards; error text for empty conflict path changed). Suggestion only. |
| 5 | Production-readiness | Path injection guarded; approval gate; conflict lock. No new secrets. |
| 6 | Algorithm / perf | Single-path reset; no unexpected O(n²). |
| 7 | Hooks | Product PR did not disable `.ai-hooks` / githooks / workflows. |
| 8 | BDD + TDD | Independent TDD_PASS for named tests. `.feature` added by implementer **without spec-change**. Scenario ids not on Story `bdd`. **FAIL.** |
| 9 | Completeness of Port slice | Port + Fake + Std + Gated + host + IPC tests present. No skip. |
| 10 | Board | Unique Task, parent `PD-GIT-02`, branch name OK, no storyPoints. **Missing prUrl; ci None vs failed Guard; Green light invalid.** **FAIL.** |
| 11 | Merge | **Do not merge.** |
| Force | Guard + tests | Guard **FAIL**. Ubuntu `tests` job success. `rust-windows` **FAIL** (see below). |
| Version | Not a release | N/A |

### rust-windows (`rust-windows` job fail)

FILE-UNSTAGE tests on that job **passed** (Fake + Std grant/deny/conflict/traversal/other-files). Four **unrelated** failures: remote add/set-url scope, merge/rebase `--continue` spawning `/bin/true`. Treat as **pre-existing Windows CI**, not introduced by `unstage_path`. Still: **CI is not Green** for B.10; do not light Green. Do not expand this Task to fix `/bin/true` unless a separate ticket.

---

## Suggestions (non-blocking)

- Wire `git_write_unstage_path` Tauri command + capability on a later task; keep deny-by-default until then.
- Avoid renaming conflict-path errors unless tests require it.
- `lib.rs` export reorder is noise; keep diffs to the new module if possible.

---

## Outcome

**FAIL (process).** Product FILE-UNSTAGE logic and independent TDD remain acceptable. After `ee3eb30`, merge is blocked **only** by missing `spec-change` + CODEOWNERS on the `.feature` (Guard 1 item). Board/scenario-id must-fixes are done.

Card: **not Done, not Blue.** Do not merge PR #17.
