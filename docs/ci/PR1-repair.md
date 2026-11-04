# CI-PR1-REPAIR-01

Primary module: CI and repository integration (infrastructure).
Author: /root. Verification and review: separately launched agents.
Authorization: Owner explicitly requested PR #1 CI/fixture/five blocked tests repair, independent verification, then main merge. Polling and unrelated dispatch remain PAUSED.

Scope: CI workflow paths/helper setup, versioned baseline fixture and its lookup, platform-neutral dispatcher test fixture, five existing blocked tests, shared test-disable lexical guard, focused guard regression tests, integration Story/Task evidence. No product contracts, pending Owner decisions, roles or gate thresholds are changed.

Contract: actual test disables fail closed; quoted evidence is not executable. Missing required build tools fail the selected suite. All existing behavioral assertions stay in place. Baseline acceptance fixture bytes stay identical. CI executes the real nested Cargo boundaries. Packaging/live smoke results remain scoped and do not establish release/native acceptance.

BDD: docs/bdd/S-CI-PR1.feature. S-CI-PR1-1 maps to baseline/dispatcher/five retained test files and remote workflows; S-CI-PR1-2 maps to tests/test_added_test_disables.py.

RED evidence: reports/commit-batches-20261104/guard-red.txt (executable disables not rejected by initial guard skeleton). Existing PR remote failures independently establish fixture/path/CI defects.

Acceptance: focused tests pass with zero new skips; unchanged assertions and fixture bytes independently reviewed; independent verification; all remote CI checks Green; legitimate In Review integration Task and BDD trace; normal squash merge only after these conditions pass.

Protected: application product behavior, Module/Port/schema/ownership/transaction contracts, .ai-hooks/config.json role, pending GT/DEC choices, all existing 336 card lifecycle/legacy evidence. No --no-verify or force push.

Environment policy: selected packaging smoke requires actual WiX/artifact prerequisites and does not silently pass if missing. Release-report shell preservation uses an isolated fixture, never writes the live legacy board. Optional target NOT RUN semantics in existing Rust live-smoke contracts are preserved and reported separately from live acceptance.


## Observed adjacent product conflict (not repaired)
The expanded Tauri `cargo test --all-targets --locked` gate fails in `new_project_choices_are_explicit_and_do_not_touch_host_binding`: the unchanged integration test expects direct creation success, while `create_project_with_preferences` returns `WizardRequired`. The project-preferences integration binary reported 170 passed / 1 failed. This is SPEC_CONFLICT / REPLAN_REQUIRED, not a missing fixture. Production behavior and the original assertion remain unchanged. Main merge is blocked pending an approved contract reconciliation. Existing workspace/library PASS is not full-target acceptance.

Independent local fixture verification: docs/ci/PR1-independent-verification.json. Final scanner review: docs/ci/PR1-independent-review.json. No installation, release, Live target, or product semantics acceptance is implied.


Full PR guard additionally detects six genuine executable disables outside the five repaired files: `tests/test_pd_rel_03_verify_install.py:136`, `tests/test_pd_smoke_01.py:153`, `tests/test_pd_wire_smoke_01.py:96,143,158`, `tools/board/test_rel_ui_smoke.py:206`. These remain visible blockers; no exclude/skip/label override is used to accept them.
