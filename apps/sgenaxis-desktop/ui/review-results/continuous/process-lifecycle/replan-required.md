# REPLAN_REQUIRED — process lifecycle integration

**RESOLVED BY OWNER, 2026-10-26:** exact answer `核准這個必要的最小整合`. Candidate A below is now approved. Current execution stage is SKELETON_PENDING_RED; the following gap report remains historical rationale, not an outstanding approval request. Public enum re-export makes the final envelope seven existing production files. No approval beyond the stated process/host/UI cancellation and empty-poll slice is implied.

Trigger: approved asynchronous output drain needs repeated polls after direct-child exit and cancellation, but current host/UI consumers assume terminal completion earlier.

Current implementation task: PD-RUST-PROC-IMPL-01; source implementation has NOT STARTED. Owner approved the core Open/EOF/Error + 2,000 ms policy, not the newly discovered cross-module behavior changes below.

## Required behavior and current skeleton

- `app.js:2125-2185 pollRunStream` breaks on an empty `chunks` batch (`:2145-2147`), then reports failure and clears activeRunId. Empty output does not mean child exit or EOF. This affects normal runs as well as cancellation.
- `src-tauri/src/dispatch.rs:675-682 cancel_run` calls EXEC cancel, performs exactly one poll, discards that poll's chunks, and returns only BoardView. A second delayed drain cannot happen through this operation. If chunks/terminal were produced, consuming them also prevents the UI from seeing them.
- `app.js:2287-2314 cmdCancelRun` increments polling generation before invoke, then calls finishRunUi and claims WORK lease released. With asynchronous drain, no terminal may yet exist; lease is released only by HOST `poll_chunks` terminal reconciliation (`dispatch.rs:626-649`).

## Affected design

- Architecture: existing CLI application-to-HOST/UI event-consumer boundary, no new architecture layer required.
- Business logic: cancel acknowledgment becomes a request accepted, not proof of completion; silence remains running/draining until an explicit terminal event.
- Contracts/invariants: INV-PROC-02,03,05,07; event preservation, terminal exactly once, truthful lease/busy projection.
- BDD: extend module cancellation/empty-output scenarios to HOST/UI integration; approval required before expectation changes.
- Skeleton: existing four-file core is insufficient. Minimum scope adds `src-tauri/src/dispatch.rs` and `ui/app.js` functions only, with integration tests.

Classification: structural cross-module seam/observable lifecycle change; implementation status **BLOCKED_PENDING_REPLAN**.

## Smallest candidate A — recommended, not approved

1. Keep all public DTO shapes and event variants unchanged.
2. HOST `cancel_run` requests EXEC cancel and returns current BoardView **without calling poll_chunks**. Pending cancellation keeps WORK lease and active run until a subsequent existing poll sees the real Exited/Failed terminal; no private event queue is added.
3. UI normal poll loop continues across empty batches at its existing 60 ms cadence. It stops only on actual terminal/error or deliberate run-generation replacement. It does not infer terminal from silence.
4. UI cancel keeps current runId and poll generation, changes visible text to `取消中，正在收尾輸出`, optionally disables repeated button action, and does not call finishRunUi. Existing poll loop receives chunks and terminal and then displays cancelled or failed truthfully.
5. Browser/native tests prove empty polls preserve activity; cancellation tail arrives once; host retains lease until terminal and releases exactly once; dry-run/CLI/MCP cancellation remains coherent. Existing tests whose expected cancel return implies immediate completion need an explicitly approved revised contract, never silent weakening.

No session manager, new event queue, new endpoint/DTO, descendant policy, buffer policy or new frontend framework. Production cost is **7 existing files**: process.rs, ports/lib.rs (one-line enum re-export), std_process.rs, fake.rs, exec/cli.rs, src-tauri/dispatch.rs and ui/app.js. The earlier 4-core/6-total estimate omitted the necessary enum re-export from the private process module; this correction adds no API beyond the already approved enum. +0 production files/dependencies/classes. Host/UI changes are estimated 15–40 lines plus tests; exact count is not an acceptance target.

## UI schema — existing controls only, proposed behavior

| Component/control | Trigger | Pending state | Terminal/error state |
|---|---|---|---|
| Existing run stream/status | Empty poll batch | Keep runId, show existing running/draining status, continue existing 60 ms poll cadence | Finish only on Exited/Failed; transport error remains readable failure/reconciliation concern |
| Existing cancel button | Active run cancel click | Show `取消中，正在收尾輸出`; retain runId/generation and current poll; disable duplicate click | Actual cancelled/failed terminal determines final status, clears active run and updates returned board |
| Existing log | Late stdout/stderr after cancel request | Append captured chunks exactly once | Final classification after chunks; no fabricated `WORK 租約已釋放` before terminal |
| Existing new-run action | Pending active run/drain | Existing Busy/lease gate still prevents a second run | Next run permitted only after terminal reconciles and queued events drain |
| Empty state | No active run | Existing cancel-disabled behavior | No active run manufactured |

Role: existing local project operator. No new fields, markup, validation model, keyboard flow or visual design. Accessible existing button/status text is retained; no new inaccessible control is introduced. Cancellation request failure must remain visible and must not silently stop the existing poll or claim a terminal result.

## Integration BDD and focused test plan

```gherkin
Feature: Truthful CLI drain in the existing host and UI
  Scenario: Empty poll is not terminal
    Given an active run with an empty output batch
    When the run is polled again
    Then the UI retains the active run until its explicit terminal event

  Scenario: Cancel acknowledges a request without consuming output
    Given an active run with pending final output
    When cancellation is requested
    Then the host returns the current board without consuming output events
    And the UI displays cancellation pending and keeps polling

  Scenario: Late cancellation tail reaches the operator
    Given cancellation is pending and the output readers have not finished
    When final chunks and an explicit terminal event become available
    Then the UI displays those chunks exactly once before the terminal classification
    And the host releases the lease once at terminal reconciliation

  Scenario: Incomplete cancellation output is a failure
    Given cancellation is pending and a pipe remains open beyond the drain deadline
    When the existing Failed event is received
    Then the UI reports incomplete output rather than cancelled success
```

1. HOST counting/scripted AgentPort: cancel does not invoke poll, acknowledgment board retains active run/lease, subsequent poll outputs all chunks and terminal exactly once and releases lease. Test no hidden tail swallowing. Repeat with DryRun cancellation and provider MCP compatibility.
2. Update existing cancel-specific HOST assertions (dispatch.rs current tests around 2155/2236/2434) only after approval: first assert acknowledgment pending, explicitly poll, then retain original no-green/yellow/restart/evidence assertions. This is a declared cancellation contract revision, not removal or weakening. Noncancel/DryRun success expectations remain unchanged.
3. Focused **real browser, mocked IPC** harness loads actual app.js/index.html and injects `__TAURI__.core.invoke` before app initialization. Existing project/settings/board queries get deterministic fixtures; start_run returns run 101. poll_chunks sequence is Started -> empty -> empty -> tail -> terminal. Capture invoke calls and actual DOM/log/status. Assert no failed completion on empty batches, no second run while pending, final tail once.
4. Browser cancel case pauses mock output at a controlled gate; actual cancel button invokes existing cancel_run returning pending BoardView. Assert the UI stays active, does not claim released lease, then release mock tail/terminal and assert the real UI completes. Test Failed timeout/read-error and cancel invoke rejection retaining poll. Avoid timing-only sleeps; use controlled promises plus bounded test timeouts.
5. This browser proof is **actual frontend + simulated IPC**, not native Tauri, real process or Agent proof. Native WebView verification remains NOT RUN until executed. If no existing browser harness is available, select the smallest available local browser tool before creating tests; do not add a frontend framework merely for this slice.

All integration tests, UI schema and changed cancel acknowledgment semantics require owner selection of A before source edits.

## Alternatives

- B: synchronously block inside EXEC cancel until both EOF or 2,000 ms. Rejected recommendation: blocks cancel/UI host path, violates chosen asynchronous drain design, still cannot fix normal-flow empty-poll termination, and host still discards chunks.
- C: return PollResult from cancel_run or maintain a host backlog for consumed events. More public/API or state cost than candidate A; no requirement justifies it.

## Exact owner question

是否核准最小整合 A：保留既有 DTO，HOST `cancel_run` 只提出取消、不吞掉 poll 事件；UI 遇空批次繼續輪詢，取消後保留輪詢並顯示「取消中，正在收尾輸出」，真正收到 Exited／Failed 才結束、釋放租約？範圍在已核准四個核心檔案外，僅增加既有 `dispatch.rs`／`app.js` 對應函式與獨立測試。

No source/test changes were made by this report. Core owner approval remains valid; integration approval is separately pending.
