# Independent reacceptance 2026-11-14

Task: PD-P1-M03-VIEWER-IDENTITY-SCHEMA-REVIEW-01

Verifier: independent-verifier-20261114 (not the author `/root/m03_identity_schema_correction`)

Verdict: **FAIL**

Not claimed: native PASS, READY_FOR_IMPLEMENTATION, Done, blue.

## Check counts

| | count |
|---|---|
| Independent checks total | 2202 |
| Passed | 1655 |
| Failed | 547 |
| Payload hashes LF vs artifact-hashes.json | 0/14 |
| Payload hashes CRLF-normalized vs artifact-hashes.json | 14/14 |
| schema-diff reconstructed entries | 5 |
| preservation rows | 513 |
| preservation claimed actual matches LF | 49 |
| preservation claimed actual matches CRLF only | 451 |
| preservation claimed actual matches neither | 13 |
| MATCH-classified files with neither hash | 12 |

## Method

Recomputed SHA-256 of payload file bytes. Repeated with LF→CRLF rewrite because the author environment was Windows. Rebuilt schema-diff from `viewer-identity-seam-proposal/observation.schema.json` vs this folder's `observation.schema.json`. Rehashed every `preservation.json` path against the current tree. Did not execute author `checker.py` (it rewrites artifacts). Did not run native/product tests.

## Findings

1. Seal and artifact-hashes are consistent with CRLF payloads, not with git LF objects.
2. Schema-diff matches the observation schema; only generation + four UUID properties change; root/required/additionalProperties and other properties preserved; UUID/u64 domains match resolved `viewer-refresh-integration/request.schema.json` definitions.
3. Preservation board-only MATCH claim fails on current HEAD: 12 non-board files classified MATCH have claimed actual hashes that match neither LF nor CRLF of current bytes. `docs/board.json` remains a classified board-management difference and has moved further.
4. Author packet still labels independent/native/build/product/valid_RED as NOT RUN and state REPLAN_REQUIRED.

## Evidence

- `summary.json`
- `failed-checks.json`
- `check-groups.json`
- `PD-P1-M03-VIEWER-IDENTITY-SCHEMA-REVIEW-01.md` (tracked; repo `reports/` is gitignored)
