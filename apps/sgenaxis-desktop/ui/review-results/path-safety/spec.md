# Path safety slice
Primary module: project document persistence (HOST application façade).
Intent: enforce existing scene_doc module contract: writes only relative paths inside the bound project; no arbitrary UI filesystem paths.
Existing skeleton: scene save/load/exists -> normalize_scene_rel -> join_project_rel -> FileSystemPort. Design save/load/preview -> join_project_rel -> FileSystemPort. Filesystem adapter implements the port. Existing project state remains caller-owned; no new state/ports/API introduced.
Invariant: reject lexical drive/root/parent escapes before any filesystem call. Ordinary nested project paths remain supported. Invalid requests do not write or create directories. Transaction: validate path before mkdir/write; actual atomic write remains delegated to existing port.
Classification: contract-preserving validation fix inside existing function signatures. No new architecture approval claimed. Symlink/junction resolution is outside this slice and is NOT RUN.
AC-01: embedded drive, drive-relative, root/UNC and stream paths rejected.
AC-02: normal scene/design nested roundtrips pass.
AC-03: invalid scene save performs no write; existing text unchanged.
AC-04: full HOST module tests pass, no public contracts or ports changed.
BDD B1 success applicable; B2 boundary applicable; B3 invalid applicable; B4 dependency failure unchanged; B5 partial failure unchanged; B6 consistency applicable; B7 validation-before-IO applicable; B8 lifecycle unchanged; B9 rollback not applicable before IO; B10 scene/design shared helper applicable; B11 Windows path compatibility applicable; B12 regression applicable.
RED observed: cargo test -p sgenaxis-host project_paths_reject --locked --offline; builds, 1 failed because accepted scene/C:/outside.ess. Production not yet changed.

## BDD companion artifacts and pending automation
- `step_definitions_pending.py` contains explicit unimplemented Gherkin binding stubs; they are not registered with a BDD runner and are NOT RUN.
- `fixtures.json` supplies deterministic sample paths and prior scene text; paths are fixture-only, not live filesystem targets.
- Pending: wire Gherkin runner to existing Rust public HOST boundaries without introducing production ports/APIs.
- Pending: recording FileSystemPort evidence of zero mkdir/write/read/exists calls for rejected paths. Current Rust tests prove rejection and preservation of existing content; before-IO ordering is also visible in source but not claimed as independently instrumented runtime proof.
- Pending: full-system UI integration and cross-platform execution. Junction/symlink containment requires a separately approved filesystem contract.

## Assumptions and open questions
- Bound project root is supplied by the existing project binding authority; this slice validates document-relative requests rather than changing root binding policy.
- Both slash styles are interpreted as separators, and Windows drive/stream syntax is disallowed consistently across platforms.
- Rooted requests violate the existing project-relative contract, even though earlier normalization silently stripped their leading separator.
- No new retry, rollback, undo, schema, lifecycle or ownership semantics are authorized.
- No unresolved architecture question blocks this lexical validation slice. Filesystem reparse-point guarantees remain a follow-up architecture decision.
