# PD-P1-M03-VIEWER-IDENTITY-SCHEMA-REVIEW-01

Independent bounded document reacceptance. Developer author `/root/m03_identity_schema_correction` is not this verifier (`independent-verifier-20261114`).

Repo `reports/` is gitignored; this file is the tracked dispatch record.

## Verdict

**FAIL**

Not claimed: native PASS, READY_FOR_IMPLEMENTATION, Done, or blue.

## Check counts

| Independent checks | 2202 |
| Passed | 1655 |
| Failed | 547 |
| Payload SHA-256 vs `artifact-hashes.json` (git LF bytes) | 0/14 |
| Payload SHA-256 vs `artifact-hashes.json` (CRLF-normalized) | 14/14 |
| `seal.manifest_sha256` vs `artifact-hashes.json` LF | fail |
| `seal.manifest_sha256` vs `artifact-hashes.json` CRLF | pass |
| `schema-diff.json` vs reconstructed diff | pass (5 property domains) |
| `preservation.json` rows | 513 |
| Claimed actual = current LF | 49 |
| Claimed actual = current CRLF only | 451 |
| Claimed actual matches neither | 13 (board + 12 MATCH rows) |
| Sibling `preserved-hashes.json` LF-or-CRLF | 81/81 |

## Scope

Read-only reacceptance of `docs/requirements-confirmation/phase1-spec/tasks/M03/planning/viewer-identity-schema-correction/`. Product code, `.feature` scenarios, and `docs/board.json` were not modified. Author `checker.py` was not executed (it rewrites artifacts). Native provider, product build, product RED, and full Draft 2020 validation were not run.

## Findings

1. **Seal vs payload bytes.** The 14 hashed payloads plus `seal.json` `manifest_sha256` agree with Windows CRLF bytes. Git stores LF; working-tree SHA-256 does not match the manifest. Bounded reconstruction (LF→CRLF) recovers every listed digest.
2. **schema-diff vs observation.schema.json.** Rebuilt before/after from `viewer-identity-seam-proposal/observation.schema.json`. Diff is exactly generation plus `project_uuid` / `document_uuid` / `session_uuid` / `preview_session`. Restoring those five properties makes the candidate schema equal to the proposal schema, including root `required` / `additionalProperties`. Patterns use `(?![\\s\\S])` and contain no `$`. UUID and unsigned-64 domains equal the resolved `viewer-refresh-integration/request.schema.json` `preview_session` and `expected_revision` definitions.
3. **preservation.json.** Packet claims 512 MATCH and one BOARD_MANAGEMENT_DIFF. On current HEAD that board-only claim fails: 12 MATCH-classified files have claimed `actual` digests that match neither LF nor CRLF of current bytes. `docs/board.json` is already classified as board-management difference and has moved again. Most remaining MATCH rows only match after CRLF rewrite.
4. **Head / pending gates.** Author recorded HEAD `5b709343…`. Current HEAD differs. Author `results.json` still has independent / native / build / product / `valid_RED` = NOT RUN and `state` = REPLAN_REQUIRED.

## Required follow-up (author, not this verifier)

Regenerate `artifact-hashes.json` / `seal.json` against git-stored LF bytes, or store CRLF payloads. Re-freeze `preservation.json` against current tree and reclassify any non-board drift. Independent bounded review still does not grant implementation.

## Evidence

- this directory
