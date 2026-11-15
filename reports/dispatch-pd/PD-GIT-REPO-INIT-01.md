# PD-GIT-REPO-INIT-01 — READY_FOR_TDD

- **Agent identity:** cursor-cloud-dev-PD-GIT-REPO-INIT-01
- **Role:** dev-agent (implementation only; this result is not acceptance)
- **Branch:** `feature/PD-GIT-REPO-INIT-01-git-init`
- **BDD:** `docs/bdd/PD-GIT-REPO-INIT-01.feature` (recreated; missing on main)

## Scenarios

| ID | Result (dev run) | Tests |
|---|---|---|
| PD-GIT-REPO-INIT-01-1 denied leaves no `.git` | Green | `pd_git_repo_init_01_1_*`, `fake_git_write_init_repo_denied_leaves_no_git`, `std_write_init_repo_denied_leaves_no_git` |
| PD-GIT-REPO-INIT-01-2 approved `git init` creates non-bare repo, no remote/clone | Green | `pd_git_repo_init_01_2_*`, `fake_git_write_init_repo_records_non_bare_when_approved`, `std_write_init_repo_creates_non_bare_without_remote_or_clone` |
| PD-GIT-REPO-INIT-01-3 existing repo / `--bare` / `--template` / option-like / clone URL fail honestly | Green | `pd_git_repo_init_01_3_*`, `fake_git_write_init_repo_rejects_existing_bare_template_and_urls`, `std_write_init_repo_rejects_existing_bare_template_and_urls`, `gated_git_write_blocks_init_repo_even_when_approved` |

## Change summary

- Added `GitWritePort::init_repo(dir, approval)`.
- `StdGitWrite` runs `git init -- <dir>` only (never `--bare`, `--template`, `--separate-git-dir`, `git clone`, remote add, fetch). Path must stay inside the chosen directory.
- `FakeGitWrite` records a non-bare local init; denied / existing / option-like / URL paths do not mutate.
- `GatedGitWrite` remains default-deny even when approved.
- Optional HOST/Tauri/UI: `perform_git_repo_init`, `git_write_repo_init`, live `REPO-INIT` approval gate.

## TDD evidence

- Red (stubs, feature not implemented): `reports/dispatch-pd/PD-GIT-REPO-INIT-01-RED.txt` — 6 failed because approved init did not create/record a repo and did not reject existing/`--bare`/`--template`/URLs. Denied paths already refused (4 passed).
- Green (implementation): `reports/dispatch-pd/PD-GIT-REPO-INIT-01-GREEN.txt` — 10 passed / 0 failed.
- Broader adapters git modules: 101 passed.
- Host: `git_repo_init` + IPC allowlist (`git_write_repo_init` allowed; `git_init` / `git_clone` rejected) passed.

## Blockers

- `apps/sgenaxis-desktop/src-tauri` `cargo test --lib` could not be compiled in this environment (`getrandom 0.4.3` requires edition2024 / newer Cargo). Command wrapper mirrors `git_write_unstage_all` and is covered by HOST `perform_git_repo_init` plus the command-module unit test source. Independent verifier should run `cargo test --lib -- git_write_repo_init` from `src-tauri` on a toolchain that matches the lockfile.

## Out of scope / not done

- Did not implement `git clone`, `--bare`, untrusted `--template`, add remote, or fetch.
- Did not set Done / blue lights.
- This agent must not verify or review this task.

## Definition of ready

READY_FOR_TDD. Card is In Review / In QA for an independent verifier.
