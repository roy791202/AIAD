# PD-GIT-DISCARD-FILE-01 high-tier review (section B)

**Verdict:** `REVIEW_PASS`

Date: 2026-11-14T16:20:00Z. Reviewer did **not** modify product code, TDD assertions, or `.feature` files. Board was **not** set to Done / Blue.

This run is **not** the implementer and **not** the TDD verifier. Identities differ.

## Identity

| Role | Agent id |
|---|---|
| Developer (PR #4) | `bc-860dbeac-55d6-557d-abc4-642c4550bc5a` |
| Independent TDD (this review trusts) | `bc-216e9734-4a2a-52fd-ab2f-b9bbfc929d8d` |
| Prior TDD note on older HEAD `2ff0b90` | `bc-1f54ee7a-209d-538d-8bbe-d749e49e9ba2` |
| High-tier reviewer (this run) | `bc-010ec2c6-ef52-5930-a763-43189ddcd009` |

Implementer PR: https://github.com/roy791202/AIAD/pull/4  
Implementer HEAD reviewed: `f67ef81` (`feature/PD-GIT-DISCARD-FILE-01-discard`)  
Independent TDD evidence: https://github.com/roy791202/AIAD/pull/15 (`feature/PD-GIT-DISCARD-FILE-01-tdd-review`)  
This review branch: `feature/PD-GIT-DISCARD-FILE-01-high-tier-review`

## Independent TDD (section A) — accepted, not re-run as PASS by this reviewer

`bc-216e9734` reported **TDD_PASS** on `f67ef81`:

| Filter | Result |
|---|---|
| `cargo test -p sgenaxis-adapters --lib s_git_write_p2` | PASS (4) |
| `cargo test -p sgenaxis-host --lib discard_file` | PASS (2) |
| `cargo test -p sgenaxis-host --lib ipc::` | PASS (3) |
| `src-tauri` `git_write_discard` | **NOT RUN** (Cargo 1.83 vs `edition2024` / `dlopen2_derive`) |
| UI E2E | **NOT RUN** (no Tauri GUI) |

No skip/`#[ignore]` on the named scenario tests. Section A is not treated as UI PASS. `src-tauri` compile failure is toolchain, not a product-code defect for this Task.

## Architecture

**GitWritePort only.** Mutation is `GitWritePort::discard_file`. UI invokes `git_write_discard_file` after the existing approval modal. Host `perform_git_discard_file` takes `&dyn GitWritePort`. `GatedGitWrite` still returns `PermissionDenied` even if approval is granted. IPC allowlists `git_write_discard_file` and rejects `git_discard_file` / `git_restore` / `git_checkout`. Renderer does not spawn git CLI.

**Approval gate.** Adapter and Fake call `require_approval` / `is_granted()` first. Host returns `approval denied; no mutation` when `approved == false` and never calls the Port with a granted token in that branch. Tauri maps the DTO `approved` flag the same way as stage/unstage-all.

**No force / no `--hard`.** Std adapter argv is `restore --worktree -- <rel>` after path guards. Tests assert HEAD unchanged, index unchanged, untracked `??` remains, merge `ls-files -u` remains. No `reset --hard`, `-f`, or `--force` in the discard path.

**Path safety.** Empty / NUL / newline rejected. `conflict_path_out_of_scope` rejects option-like tokens (`-f`, `--force`, `--`, `.`, `..`, path `..` segments, `\`). `discard_path_escapes_repo` walks components and refuses paths that do not stay under the repo root (including absolute paths outside the repo). Git is invoked as argv (`Command` + `-C` + `--`), not a shell string.

**Layering.** Ports define the contract. Adapters implement CLI. Host use-case is a thin approval + DTO mapping. Tauri command: authorize → resolve repo → writes-enabled gate → host. UI: FILE-DISCARD capture → modal → invoke. No domain rules in the renderer; no Port bypass.

**Coupling.** Reuses `conflict_path_out_of_scope` and the existing GitWrite approval modal. Capture-phase listener in `app.js` only (mock template not used as the live hook after `8d331dd`). No new factories or extra write ports.

## Allowed files vs PR #4

Product files are within the Task allow-list (ports `git.rs`, adapters std/fake/`git_write`, host discard + ipc, src-tauri commands/dto/permissions/`lib.rs` handler, `ui/app.js`, crate tests). Extra: `docs/board.json` (card for Guard), implementer report, independent TDD copy. `.feature` files were not edited. `.ai-hooks` / githooks / workflows were not edited.

## Clean Code

Host use-case is short, named, and uses Result/PortError rather than error codes. Adapter `discard_file` is linear with guard clauses. Product discard path does not `unwrap` on expected git failures (`run` maps spawn/exit to `PortError`).

Suggestion (not blocking): `discard_path_escapes_repo` sits under a leftover comment about identity writes in `std_git_write.rs`. Harmless.

## Production-readiness / security (scoped)

- Command injection: argv, `--` separator, option-like paths refused.
- Untracked delete: `ls-files --error-unmatch` then refuse; Fake marks untracked and refuses.
- Unmerged: `ls-files -u -- path` then refuse; conflict state kept.
- IPC BFLA: unlisted `git_discard_file` / `git_restore` denied.
- Errors: git stderr goes through existing `git_error_redacted`.
- Complexity: O(path components) for escape check; one git restore. No O(n²) on user path length.

## BDD + TDD trace

| Scenario | Tests | Independent TDD |
|---|---|---|
| S-GIT-WRITE-P2-3 | Fake + Std temp-repo + host `s_git_write_p2_3_discard_file` | PASS |
| S-GIT-WRITE-P2-4 | matching `*_p2_4_discard_reject` | PASS |

`docs/bdd/S-GIT-WRITE-P2.feature` is **not** on implementer HEAD (only `S-CI-PR1.feature` in `docs/bdd/`). Mapping used test names + Task scenarios. This is a documentation gap, not an assertion weaken. PR did not delete a `.feature` that existed on this branch.

## Board (this reviewer)

Task `PD-GIT-DISCARD-FILE-01` is In Review, Yellow, tdd Green, parent `S-GIT-WRITE-P2`, `prUrl` PR #4, hours (not story points). **Not** Done / Blue. CI on GitHub for `f67ef81` is still **pending** (no combined statuses). Prior Guard miss (card absent on HEAD) was addressed by `docs(board): attach PD-GIT-DISCARD-FILE-01`. This reviewer does not mark the card complete.

## Must-fix

*(none)*

Product architecture for discard-file meets GitWritePort-only, approval, no force/`--hard`, path safety, layering, and no extra coupling. Independent TDD_PASS on adapters + host discard + ipc stands. Remaining gaps are NOT RUN (src-tauri toolchain, UI E2E) and CI pending — they do not reverse the architecture verdict.

## Suggestions (do not block)

1. Keep UI E2E / src-tauri command tests **NOT RUN**, not PASS, until a desktop/toolchain that can compile edition2024 and drive the modal exists.
2. Land `S-GIT-WRITE-P2.feature` on the line of development that owns Story P2 (preproduction; not this Task).
3. Relabel the leftover identity comment above `discard_path_escapes_repo`.
4. Wait for AI Dev Guard / tests CI on PR #4 before merge; this review does not certify CI Green.

## Completeness

Task scenarios S-GIT-WRITE-P2-3/4 are implemented end-to-end in Port → adapter → host → Tauri command → UI modal. No TODO/skip in the discard-file product path reviewed.

**REVIEW_PASS.** Do not set board Done / Blue from this review. Merge of PR #4 remains a human / Guard + CI decision.
