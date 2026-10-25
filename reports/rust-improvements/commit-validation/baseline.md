# Authorized Rust baseline checkpoint

Owner approved two commits on 2026-10-26 (Asia/Taipei): existing Rust baseline, then the read-only .ess packet. No push.

## Scope

Existing ten-crate Cargo workspace and independent Tauri host; build resources; required tools/pd_report Python helper and fixtures; Rust baseline CI and its tests/evidence. Existing UI modifications, board and unrelated documents remain excluded.

The baseline index removes only the six A-only source/test/fixture/example files, their three module registrations, approved A dependencies and corresponding effective lock entries. Working sources are unchanged.

## Isolated validation

A tree exported from the index was tested outside the working directory, with repository history available for the existing Git integration test. Initial empty temporary Git history caused one environment failure; restoring the actual local history fixed it without changing tests or production.

- baseline-workspace: 262 PASS
- baseline-exec: 56 PASS
- baseline-tauri: 74 PASS
- baseline Python unittest: 2 tests / 5 subtests PASS

Baseline lock separation removed only A-added packages; no dependency versions changed. Historical baseline report inventories describe the earlier full working directory, not this split index.

No packaging, install, live Agent, native UI, remote CI or release validation. Source/architecture findings were reviewed in the prior independent gate. No commit implies owner green or release.
