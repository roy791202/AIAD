# M03 cx-h2-revision-v3 — independent document reacceptance

**Verdict:** `FAIL_DOCUMENT_REACCEPTANCE`

**Reviewer:** `independent-verifier/cursor-cloud-agent-bc-10fee6e5` (distinct from package author)

## Summary

- Re-hashed all seven payload files listed in `artifact-hashes.json` at repo `HEAD`; **all seven diverge** from the manifest.
- `review-request.revision_sha256` (`4db8e6c6…`) does **not** match `dig(actual_hashes)` (`3f005ea6…`) using the same `build_documents.py` convention (`ensure_ascii=False`, sorted keys).
- **Status gates hold:** `PENDING_REACCEPTANCE_AND_OWNER`, `RR_REVISED_CANDIDATE_PENDING_OWNER`, `V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER`, and `NOT_READY_FOR_IMPLEMENTATION` remain declared in the candidate packet.
- **62** `case-trace.json` rows; all `AMENDED_PROTOCOL_ONLY`.
- Product code / `.feature` scenarios **not** modified; native / RED / GREEN **NOT RUN**; no `READY_FOR_IMPLEMENTATION` claim.

## Required correction (author)

Re-seal `artifact-hashes.json` and `review-request.json` to match committed bytes, then refresh downstream bindings that still cite the stale hashes (e.g. integration reacceptance preserved hashes).

## Artifacts

- `findings.json` — machine-readable audit
- `reviewed-input-hashes.json` — independent SHA-256 at review time
- `index.html` — human summary