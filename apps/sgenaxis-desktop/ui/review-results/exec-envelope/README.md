# Rust execution improvement packets

Documentation only. All three module artifacts are REPLAN_REQUIRED; architecture PROPOSED_NOT_APPROVED, tests NOT RUN.

Dependency order: owner resolves EXEC-R01/R02 -> approve dispatch contracts/skeleton -> intended executable RED -> implementation. Process PROC-R01 lifecycle approval precedes PROC-R02 decoding choice and related tests. FS-R01 is independent but needs transaction/concurrency contract approval and deterministic seam. No live services, production edits, commit or push.

Artifacts: exec-dispatch.html, process-adapter.html, filesystem-adapter.html. Each embeds structured ModuleSpec JSON. Evidence paths are relative to apps/sgenaxis-desktop.
