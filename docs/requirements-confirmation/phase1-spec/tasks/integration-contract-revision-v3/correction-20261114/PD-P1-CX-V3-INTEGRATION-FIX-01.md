# PD-P1-CX-V3-INTEGRATION-FIX-01

Bounded document correction: re-seal SHA-256 values on **git blob / LF** bytes as stored in git.

| Field | Value |
|---|---|
| Task | PD-P1-CX-V3-INTEGRATION-FIX-01 |
| Author | dev-agent-PD-P1-CX-V3-INTEGRATION-FIX-01 |
| Consumed review | [PR 51](https://github.com/roy791202/AIAD/pull/51) verdict **CHANGES_REQUIRED** (hash/LF vs CRLF) |
| Date | 2026-11-14 |

This agent did not edit `docs/board.json`, product source, or tests. This packet does **not** claim Owner adoption, native PASS, product GREEN, READY_FOR_IMPLEMENTATION, Skeleton, Done, or blue light.

## What changed

Independent reacceptance (PR 51) found every declared package SHA-256 (H1, 52/52) and child SHA-256 (H6, 63/63) is the hash of Windows CRLF reconstruction, while `git cat-file -p` payloads are LF.

This folder records a **git/LF reseal**:

- `artifact-hashes-git-lf.json` — 52 package files, SHA-256 of git LF blobs
- `child-artifact-hashes-git-lf.json` — 63 child hashed files, same domain (child trees were not rewritten)
- `revision-digest.json` — `revision_sha256` of the LF hash map via `build_documents.py` `canon()`/`dig()`

The original v3 candidate files and their CRLF-era `artifact-hashes.json` are left in place so this correction stays bounded. The prior CRLF seal remains reconstructible (`\n` → `\r\n` matches all 52 prior package hashes).

## Explicitly still open

- **V3-F1** and **V3-F2** from PR 51 / prior reacceptance are **out of scope** and remain open.
- Owner confirmation remains `ONE_OWNER_CONFIRMATION_PENDING`.
- `tests_build_RED_GREEN_native`: NOT RUN.

## Evidence

- `method.json`
- `consumed-reacceptance.json`
- `status.json`
- `scope.json`
- `revision-digest.json`
- `artifact-hashes-git-lf.json`
- `child-artifact-hashes-git-lf.json`
- `package-hash-evidence.json`
- `child-hash-evidence.json`
