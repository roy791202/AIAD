# MCP NOT RUN Architecture Conformance Review

Reviewed-scope PASS; remains yellow pending owner acceptance. No unresolved finding.

HEAD: 31babe87a7ef1e40a0d4bedc523077e7a45d63ab

## Composition — PASS

dispatch.rs:102-110 uses existing StubMcpClient; FakeMcpClient import and only construction are under cfg(test), lines1477-1479/1959-1962.

## Bounded error mapping — PASS

dispatch.rs:545-553 maps only provider MCP + ExecError::RealMcpDisabled to static NOT RUN unavailable diagnostic; all other errors retain e.to_string().

## Transaction and state — PASS

dispatch.rs:541-554 performs existing preflight then fallible EXEC start; unavailable error exits before bind_run556, blue task/FLOW mutations and active-run fields585. Router sets active only after leaf success; MCP Stub connect rejects before session queue/Started creation. Internal run-id allocation and Guard pass are explicitly excluded existing semantics.

## Credential projection — PASS

dispatch.rs:495-502 no longer interpolates raw endpoint; unavailable message547 is constant. Secret token/endpoint credentials cannot enter these two diagnostics.

## Validation and public compatibility — PASS

Diff retains target→busy→binding→WORK preflight→EXEC order. No signatures, DTOs, port definitions, dependencies, CLI branch or DryRun algorithm changed.

## Simulation test preservation — PASS

Original live_mcp_via_dispatch_host_is_not_dry_run_only assertions unchanged. Only explicit test fixture AgentRouter assignment added before settings. Simulation remains available solely as test evidence.

## Independent test coverage audit — PASS

Five tests cover default rejection, repeats and DryRun recovery, guarded implementation no accepted state, credential output, forbidden target with panic-on-contact transport. Tests inspect board, run/lease, provider/FLOW and evidence state. Tests do not weaken original behavior assertions.

## Verification Limits

NOT RUN by architecture reviewer; parent independent test gate owns regression evidence. Actual IPC, WebView rendering and real network transport NOT RUN. This report does not claim regression execution or release acceptance. Guard pass/internal counter behavior remains the declared preexisting exception.

## Source SHA-256

apps/sgenaxis-desktop/src-tauri/src/dispatch.rs 0ae3e2f8063740896a2e3f92552267f2b2bf5954b94c770c453c7e1081ac390c
apps/sgenaxis-desktop/src-tauri/src/mcp_notrun_tests.rs c72fb7486cbfd20cd2aae82ccb73284e4e3cc52b754366c44fd8bf3df1628b8a
reports/rust-improvements/mcp-notrun/architecture.md 55a47f93a55aacdba96c87e9185018529710e07d574e19c3871805534cd76a60
apps/sgenaxis-desktop/crates/sgenaxis-exec/src/mcp.rs a138d694f3da34c3ab1cda3e55137590affe06b9ab86ae01db2203804acbf331
apps/sgenaxis-desktop/crates/sgenaxis-exec/src/mcp_client.rs 073b31c81c71ce40b0249e8317963a64ee97e16a52fd1507c4d07bfbd4018e94
apps/sgenaxis-desktop/crates/sgenaxis-exec/src/router.rs 585b2e66fd51ef2d5e1545604652ac4a6caaffdc4c82a06dd769830b762bb7d2