# Historical frozen skeleton — process lifecycle

Current delivery state: **READY_FOR_GREEN yellow, owner acceptance pending**. Independent RED/GREEN, regressions and architecture review have completed; see module.html and ../process-tests/module.html. The following records the earlier frozen **SKELETON_PENDING_RED** handoff, not the current implementation status. Owner approved core policy and integration A (`核准這個必要的最小整合`).

## Public schema, locked

```rust
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub enum StreamCompletion {
    #[default] Open,
    Eof,
    Error(String),
}

pub struct ProcessOutput {
    pub stdout: String,
    pub stderr: String,
    pub stdout_completion: StreamCompletion,
    pub stderr_completion: StreamCompletion,
}
```

ProcessOutput retains its existing derives; is_empty remains text-only. ProcessPort signatures unchanged. Existing ports/lib.rs explicitly re-exports StreamCompletion. No other DTO/event change is permitted.

## Private ownership and test seams, locked

- StdProcess `PipeCapture { bytes: Vec<u8>, completion: StreamCompletion }` under `Arc<Mutex<PipeCapture>>` for each stream. `spawn_pipe_reader(pipe: impl Read + Send + 'static, buf: Arc<Mutex<PipeCapture>>)` is controllable by an independent test Read implementation. Current skeleton records bytes but leaves completion Open.
- `take_utf8(buf: &Arc<Mutex<PipeCapture>>) -> (String, StreamCompletion)` drains bytes and snapshots state together. Implementation may return Result for poison handling using existing PortError; private helper shape is not public API, but coordinate independent tests first if it changes.
- EXEC existing private RunPhase::Live adds `observed_exit: Option<i32>`, `exit_observed_at: Option<Instant>`, `cancel_requested: bool`.
- EXEC private `poll_chunks_at(&mut self, run: RunId, now: Instant) -> Result<Vec<AgentChunk>, ExecError>`; public AgentPort::poll_chunks calls this with Instant::now. Exact deadline tests call the private seam in a child test module. No ClockPort, public test-only API or sleeps needed.
- `poll_live_if_needed(process: &mut dyn ProcessPort, run: &mut ActiveRun, now: Instant)` receives controlled time. Skeleton ignores now and still uses the old final drain, so EOF/deadline assertions fail behaviorally.
- FakeProcess skeleton fills added completion fields with Open. GREEN will make existing finish/cancel report settled streams coherently; independent scripted doubles model exit before EOF.
- HOST `cancel_run` and UI `pollRunStream` / `cmdCancelRun` signatures already exist and remain unchanged. Only their approved bodies may change after valid RED.

## Locked observable ordering for implementation after RED

1. Capture available stdout then stderr from a poll and enqueue nonempty chunks. Preserve each stream's captured ordering; no cross-stream wall-clock order guarantee.
2. Stream Error yields one Failed (`PROCESS_OUTPUT_READ_FAILED`) after captured chunks; attempt current direct-child cancel once if still running. No new tree-kill policy.
3. Observe direct-child exit with unchanged try_wait meaning. Save first observed code/time; do not reset deadline on later polls/chunks.
4. If both EOF and child exited, enqueue one Exited with code classification or approved cancellation intent. EOF completion wins at exact 2,000 ms.
5. Otherwise if first-exit elapsed >=2,000 ms, enqueue one Failed (`PROCESS_OUTPUT_INCOMPLETE`) naming open streams; retain captured data and do not emit Exited.
6. Cancel request is idempotent, marks intent after successful existing process cancel, and does not finish/emit terminal prematurely. If exit was already observed before cancel, preserve natural exit classification.
7. HOST cancel acknowledges only and must not consume a poll. Existing subsequent poll terminal performs lease reconciliation once.
8. UI empty poll continues existing cadence; cancel keeps active run/generation and says pending/draining. Only actual terminal finishes UI. A rejected cancel must leave ongoing poll intact.

## Envelope and verification

Seven production files only: ports/process.rs, ports/lib.rs, adapters/std_process.rs, adapters/fake.rs, exec/cli.rs, src-tauri/dispatch.rs, ui/app.js (two named functions). Preserve all other UI WIP, MCP NOT RUN and FS changes. Independent test-only module includes may be added by the tester.

Skeleton compile evidence (2026-10-26):
- cwd apps/sgenaxis-desktop: `cargo check --workspace --offline` PASS.
- cwd apps/sgenaxis-desktop/src-tauri: `cargo check --lib --offline` PASS; existing CaseResult/RunCapture unused import warning only.

This is not GREEN or acceptance. Production behavior implementation waits for independently compiled, intended behavioral RED.
