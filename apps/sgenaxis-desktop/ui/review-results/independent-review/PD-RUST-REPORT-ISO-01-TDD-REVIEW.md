# PD-RUST-REPORT-ISO-01 independent TDD review

Verdict: **TDD_PASS — yellow; owner acceptance pending.** Date: 2026-10-25 Asia/Taipei.

Reviewed actual working `src-tauri/src/pd_report_call.rs`, report feature and RED evidence. Rust sources are untracked; no committed pre-change diff exists. Producer's recorded RED builds then fails distinct-path assertion with both results using `Temp/sgenaxis-pd-report/report.html`. This deterministic assertion detects the old shared destination even if subprocess scheduling happens serially. Historical RED was inspected, not independently replayed.

Current default path reservation uses PID plus atomic sequence and exclusive `create_dir`, retrying existing names. Cross-process PID reuse cannot reuse an existing directory. Explicit caller out_dir semantics and DTO/API remain unchanged. Fixed subprocess argv, source-byte mutation checks and write_back=false contract remain. Existing test early returns became required expect/assert failures, strengthening evidence rather than silently skipping unavailable dependencies.

Independent execution from `D:/AIAD/apps/sgenaxis-desktop/src-tauri`, using `C:/Users/g6812/.cargo/bin/cargo.exe`:

- `test --lib --locked --offline`: exit 0, **74 passed, 0 failed/ignored** with default concurrent runner.
- `test --lib --locked --offline pd_report_call::tests::concurrent_default_reports_keep_independent_artifacts -- --exact`: exit 0, **1 passed, 73 filtered**.

Concurrency case checks distinct HTML/Markdown paths, returned statuses, no writeback, persisted bytes equal returned bodies and fingerprints present in both formats. Existing before/after source-byte checks execute inside both report requests. No assertion weakening identified.

Limits: explicit identical out_dir remains caller-controlled and is not isolated by this slice. Default artifacts are retained after ordinary calls; retention policy is a follow-up. The report source's own PASS/NOT RUN labels are fixture evidence, not product green, real transport or release acceptance. Full module completeness, failed subprocess lifecycle, packaging and desktop rendering remain outside this proof.

Planning envelope review: EXEC/process/filesystem documents consistently mark REPLAN_REQUIRED, architecture PROPOSED_NOT_APPROVED and tests NOT RUN; owner approvals were not invented. Fake MCP success remains simulation, with external transport NOT RUN.
