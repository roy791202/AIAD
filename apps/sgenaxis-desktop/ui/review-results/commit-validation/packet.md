# Read-only .ess packet commit verification

Date: 2026-10-26 Asia/Taipei. Owner authorized commit of the existing Rust baseline followed by this feature; no push.

Baseline commit: `a3cdc3bf6e0c031a450b9f19c012e6d107782b41`.
Tested staged source tree before final documentation updates: `8f76d0ec3af07e7f7f56b0041be440199e8efed0`.

## Result

- Isolated Windows Git export/checkout workspace: 277 PASS (includes focused15).
- EXEC all features: 56 PASS.
- Independent Tauri library: 74 PASS.
- Stdout CLI executed twice: byte-identical output, exact source SHA-256, unchanged source bytes, NOT_READY.
- Original12 acceptance tests and all production bodies unchanged from prior independent review.

## Classified failure and correction

An isolated Windows checkout converted fixture LF to CRLF, exposing a review-added test setup defect: a newline-specific replacement failed to create invalid input. This was a broken fixture, not valid production RED. The correction changes only that review case's setup, preserves INVALID_IDENTITY, asserts the mutation applied, and exercises both LF/CRLF. Original12 scenarios and assertions remain unchanged. Initial failure evidence and final complete runs are retained here.

## Scope and limits

Only approved A source, dependencies, test fixture, CLI example, specifications and review evidence belong to this commit. Existing UI, board, unrelated fixtures/documents and work remain outside the index. No production architecture, contracts, readiness or source-write behavior changed during commit preparation. Historical source-hashes.txt predates the test-setup correction; latest index hashes follow.

No packaging, install, native UI, live Agent, remote CI or release claim. Packet eligibility remains NOT_READY. Commit authorization does not change board green/release authority.
