# XML packet A independent test gate

Status: RED demonstrated; yellow ownership retained. Production implementation not reviewed yet.

Scope: only HOST integration test and new synthetic real-shape fixture. Existing product samples unchanged. Tests frozen after intended RED.

Command: `C:/Users/g6812/.cargo/bin/cargo.exe test -p sgenaxis-host --test module_packet --offline -- --nocapture`

Build: PASS. RED: 12 tests failed, 0 passed; failures are NOT_IMPLEMENTED or empty SHA-256 returned by locked skeleton. No missing dependencies, broken compilation or environment error accounts for RED.

Coverage: moduleId vs slotId, nested source facts/provenance, internal/boundary graph selection, task selection, unrelated node/task/design exclusion, NOT_READY; empty module and absent task diagnostics; explicit paths and pre-read rejection; IO errors; malformed XML/UTF8/DTD/version rejection; identity categories; membership/endpoint errors; resource limit equality/exceeded boundaries; known abc SHA-256; repeatability and payload SHA; expected-hash stale and source-change re-read; freshness project binding.

Evidence: build.txt and red.txt. No production/manifest/skeleton edits, no board updates, commit, push or Live activity.

Formatting: rustfmt not installed; no toolchain installation attempted. Focused GREEN and workspace/EXEC/Tauri regression pending parent implementation completion.

## Final independent validation — 2026-10-25 Asia/Taipei

Verdict: **TDD_PASS yellow / READY_FOR_GREEN yellow**. Owner acceptance remains external.

- Original 12 acceptance cases unchanged after handoff: GREEN.
- Three separate review cases added: semantic Module endpoint boundary, structural validation/selectors, literal DTD text inside BDD CDATA.
- CDATA regression demonstrated RED (13 pass, 1 fail), implementation fixed parser error classification; final **15/15 PASS**.
- Workspace `cargo test --workspace --locked --offline`: **277 PASS** (includes those 15, not additive).
- EXEC `cargo test -p sgenaxis-exec --all-features --lib --locked --offline`: **56 PASS**.
- Tauri isolated manifest `cargo test --lib --locked --offline`: **74 PASS**.
- No failed/skipped/flaky checks in final runs. No production edits by independent reviewer.

Contract review: actual parser and HOST seam exercised; explicit semantic identity vs slot identity; architecture dependencies and nested properties preserved; unrelated bodies excluded; exact hash and stable selectors; no writes; no inferred approval. Every successful packet explicitly NOT_READY.

Meaningful defect found and resolved: raw DTD text detection rejected harmless BDD CDATA. Parser now classifies actual DTD declarations while preserving literal source text. Frozen tests were not weakened.

Evidence files: green.txt, workspace.txt, exec.txt, tauri.txt, structure.txt, source-hashes.txt; original red.txt and review-red.txt retained.

Limits remain those approved: lexical path containment, whole-file read before byte guard, resource policy does not imply bounded IO, no source repair/migration, no authoritative approval resolution, no Live Agent, no Tauri/UI wiring, packaging/install/network NOT RUN. Test doubles do not prove physical filesystem sandboxing. Source-hashes bind final reviewed three implementation bodies and independent suite; Git HEAD alone is insufficient for untracked workspace files.

## Isolated checkout fixture correction — 2026-10-26 Asia/Taipei

Parent isolated checkout revealed a review-added test setup defect: LF-specific string mutation did not apply after Git converted fixture line endings to CRLF. Classified **broken fixture**, not production behavior RED.

Only `extra_structure_validation_and_selectors` setup changed. Empty-ID mutation now targets the node attribute independent of newline; each mutation asserts source target exists and resulting text differs. Structural rejections execute against both LF and CRLF variants. Same INVALID_IDENTITY assertion and original twelve acceptance tests preserved.

Focused final suite: **15/15 PASS**. Evidence: line-ending-fix.txt. Parent will restage and repeat isolated full validation; no production, board, index or commit changes by this reviewer. Prior source-hashes.txt predates this test-only correction.
