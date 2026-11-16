# PD-P1-CX-V3-INTEGRATION-REVIEW-01

Independent readonly reacceptance of `docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3/`.

| Field | Value |
|---|---|
| Verifier | independent-verifier-PD-P1-CX-V3-INTEGRATION-REVIEW-01 |
| Author of package | CX-V2-F1-F3-CORRECTION-v3 (branch `cursor/ui-bhv-arch-layer-editor`; not this agent) |
| Verdict | **CHANGES_REQUIRED** |
| Date | 2026-11-14 |

This agent did not author the v3 package. Product code, `.feature` files, and `docs/board.json` were not modified.

This review does **not** claim READY_FOR_IMPLEMENTATION, Skeleton, native PASS, Done, or blue light.

## Verdict

**CHANGES_REQUIRED**

Prior independent package `integration-contract-reacceptance-v3` already recorded `CHANGES_REQUIRED_V3_SCHEMA_AND_ERROR_MAPPING_ONLY` (V3-F1, V3-F2). Those defects are still present on the candidate schemas. In addition, declared artifact SHA-256 values do not match git/LF payload bytes (they match CRLF reconstructions only).

Bounded static pointer and case-count checks pass. That is not package adoption and not PASS_BOUNDED.

## Check counts

| | Pass | Fail | Total |
|---|---:|---:|---:|
| Rollup checks | 12 | 6 | 18 |
| Atomic units | 2418 | 152 | 2570 |

Failing rollups: H1 (52/52 git-LF hashes), H6 (63/63 child git-LF hashes), F1 (26 H2 response Error variants), F2 (11 MaterialError codes).

Passing rollups: H2 CRLF reconstruction 52/52; H3 package revision digest 1/1; H4 common_sha256 1/1; H5 child revision digests 9/9; H7 child CRLF 63/63; H8 vector SHA 173/173; H9 vector hex 173/173; S1 schema roots 38/38; S2 local `$ref` 1079/1079; C1 original cases 769/769; C2 u64 vectors 8/8; P1/P2 pending statuses; B1 no board/product/.feature edits.

Atomic formula is recorded in `independent-reacceptance-20261114/checks.json`.

## Findings that require change

1. **V3-F1 (still open).** `h2-*-response.schema.json` `$defs/Error` still types `UnsupportedDocument.details.nodes` as `string` and `InvalidRequest.details.reason` as unrestricted `string`. Closed node-array and reason enum from `h2-error-lifecycle.json` are not encoded. Witness from prior review still applies: a typed node array fails `oneOf`; `"nodes": "not a node list"` and an undeclared reason string are accepted.

2. **V3-F2 (still open).** Lifecycle mapping includes `StaleRoots` but not `StaleRoot`. Unmapped MaterialError codes: `CatalogInvalid`, `InvalidBinding`, `InvalidInput`, `MaterialRecoveryBlocked`, `MissingVersion`, `PermissionDenied`, `PinConflict`, `StaleCatalog`, `StaleRoot`, `Storage`, `UnmappedReference`.

3. **Hash domain vs git payload.** `artifact-hashes.json` records SHA-256 of CRLF bytes. Repository working tree and `git show` blobs are LF. Independent `sha256(read_bytes())` mismatches all 52 package files and all 63 child hashed files. CRLF reconstruction matches 100%. `revision_sha256` correctly digests the hash map; `common_sha256` correctly digests the shared-contract object. Re-pin hashes to repository bytes (or declare CRLF as the hash domain in-repo) before treating the manifest as payload-authentic.

## Explicitly not ready

- Owner confirmation still pending (`ONE_OWNER_CONFIRMATION_PENDING`).
- `tests_build_RED_GREEN_native`: NOT RUN.
- Full JSON Schema draft 2020-12 validator: NOT RUN.
- Skeleton / valid RED / product GREEN: not present and not claimed.

## Evidence paths

- `docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3/independent-reacceptance-20261114/verdict.json`
- `docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3/independent-reacceptance-20261114/checks.json`
- `docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3/independent-reacceptance-20261114/PD-P1-CX-V3-INTEGRATION-REVIEW-01.md`
- Working copy also written to gitignored `reports/dispatch-pd/PD-P1-CX-V3-INTEGRATION-REVIEW-01.md` (not tracked; `.gitignore` has `reports/`).
- Prior review (unchanged, not this delivery): `docs/requirements-confirmation/phase1-spec/tasks/integration-contract-reacceptance-v3/findings.json`
