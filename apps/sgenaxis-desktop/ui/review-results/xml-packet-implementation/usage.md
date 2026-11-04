# .ess read-only packet — usage and implementation evidence

Task PD-RUST-XML-PACKET-IMPL-01; owner decision A. Yellow pending independent review and owner acceptance.

Run from D:/AIAD:

```powershell
C:/Users/g6812/.cargo/bin/cargo.exe run --manifest-path apps/sgenaxis-desktop/Cargo.toml --offline -p sgenaxis-host --example export_ess_packet -- D:/AIAD/apps/sgenaxis-desktop/crates/sgenaxis-host/tests fixtures/module_packet.ess semantic-A TASK-A
```

The example prints JSON only. Captured output: fixture-packet.json. No output-path option, source writes, IPC, Agent run or acceptance mutation. Actual product sample lacking explicit semantic module returns MODULE_NOT_FOUND (exit 1); no inference or repair.

Implementation layering remains HOST -> SPEC/Ports; XML SDK is adapter-only. SPEC validates sections, IDs, global graph/port/dependency references and membership before projecting selected node/task bodies. Layer/semantic Module endpoint edges are boundary context. Source selectors preserve source element ordering; BTreeMap attributes yield deterministic JSON. UI embedded node IDs are context, never claimed ownership. All extractions remain NOT_READY.

Tests run by implementation agent:
- protected focused suite 12/12 PASS (after semantic Module endpoint change).
- adapters 37 + HOST 74 + HOST integration 3 + focused 12 + SPEC 7 =133 PASS (before final semantic Module endpoint addition; independent test owner reruns final state).
- SHA256 abc and deterministic payload verified by protected suite.
- stdout CLI real filesystem fixture PASS.
- existing product sample MODULE_NOT_FOUND PASS as expected.

Limits: byte ceiling after whole-file read; lexical path restrictions do not resolve symlinks/junctions; re-read does not prevent ABA edits. Explicit root is caller-authorized. No authoritative UI ownership/approval/contract resolution. No schema migration, split reader, real Agent, Tauri UI, packaging, install, release or commit/push.

Formatting: installed missing Rust toolchain rustfmt component and formatted only four owned source/example files; no product dependency changes by implementation agent.

Final focused15/15 PASS after reviewer CDATA behavioral RED. Fix maps roxmltree DtdDetected, avoiding false declaration detection in literal BDD/CDATA. Actual DTD test still PASS. Active module.html embeds two A-only views; original broader publication/ready work remains excluded.

Scope clarification: approved skeleton already introduced EssDecoderPort, roxmltree and sha2; implementation added no dependencies or public skeleton expansion beyond those approved additions. Original focused12 plus independent review3 =15.
