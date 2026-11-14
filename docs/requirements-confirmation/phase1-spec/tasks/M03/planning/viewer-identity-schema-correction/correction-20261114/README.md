# PD-P1-M03-VIEWER-IDENTITY-FIX-01 (bounded document correction)

Author: `PD-P1-M03-VIEWER-IDENTITY-FIX-01-correction-agent`. This agent is not the original packet author `/root/m03_identity_schema_correction` and is not independent-verifier-20261114.

Consumed independent reacceptance: GitHub PR #52 (`feature/PD-P1-M03-VIEWER-IDENTITY-SCHEMA-REVIEW-01-reacceptance`), verdict **FAIL** (seal/preservation hashes are Windows CRLF; git stores LF).

## What this correction does

- Recomputes the 14 parent payload SHA-256 values from **git LF bytes**.
- Recomputes the parent `artifact-hashes.json` digest the same way so `seal.manifest_sha256` in this folder matches LF `corrected-artifact-hashes.json`.
- Re-freezes `preservation.json` against the current tree: `expected` and `actual` are LF SHA-256. `docs/board.json` stays `BOARD_MANAGEMENT_DIFF`. Files that matched neither LF nor CRLF are reclassified to `MATCH` after freeze (listed in `reclassification.json`).
- Does **not** rewrite parent packet files, product source, tests, or `docs/board.json`.
- Does **not** claim native PASS, independent PASS, READY_FOR_IMPLEMENTATION, Owner adoption, Done, or blue.

## Hashing rule

`SHA-256(file bytes as stored in git / POSIX working tree)`. Independent review PR #52 already showed every claimed digest matches LF→CRLF rewrite. This folder stores the LF digests instead.

## Pending

Independent bounded re-review of this correction folder. Native provider, product build, product RED, Draft 2020, module acceptance, and Owner VIS-D1..D5 remain NOT RUN / PENDING. Parent Yellow / REPLAN_REQUIRED unchanged.
