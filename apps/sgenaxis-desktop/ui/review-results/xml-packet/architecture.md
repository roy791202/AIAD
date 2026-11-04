# XML → Module Engineering Packet — PROPOSED

Task PD-RUST-XML-PACKET-ARCH-01; primary module: SPEC projection / packet application capability. Status: PLANNING, yellow; NOT_READY_FOR_IMPLEMENTATION. Owner decision PD-RUST-XML-PACKET-DEC-01 is pending. No production skeleton, RED, architecture approval or acceptance is claimed.

## Grounded current behavior

- `apps/sgenaxis-desktop/ui/app.js:700` sceneDocToSgsXml emits eluslotScene format eluslot.ess v1 with work, architecture, design sections. Work and design are XML inside this container.
- `app.js:3673` archDocToXml and `:3991` archDocFromXml encode/decode eluslotArch. Module slot carries slotId and moduleId (`:3916`); node moduleRef binds module identity. Legacy decoder fills missing moduleId using slot identity (`:4235`), but a new export must disclose that fallback and cannot silently treat it as approved identity.
- `app.js:481` split architecture parsing; split .es and .esui are JSON, .esml XML. Dedicated fixtures/sgenaxis-design/sample.sgendesign is JSON, not XML. app.js:5289 uses uiDefinitionRef, default design/main.sgendesign; design nodes have props, bddHint, tddHint and behaviorHints (`:687`). Hints are not approved BDD or executable logic.
- Architecture includes input/output port metadata, edges, bddSpecs/tddSpecs and Layer module members (`:3860-3960`). Membership, layerRef/moduleRef and edge references must be checked together, not inferred from drawing coordinates.
- SPEC model.rs already owns ModuleSpecDocument, SpecRevision, Contract, approval and evidence validity. Its current fingerprint hashes contracts using FNV-1a; it does not fingerprint full source, UI or packet. It must not be relabeled as a whole-product integrity guarantee.
- WORK owns project/root/lease. GUARD already has implementation request gates and envelopes. EVID already classifies real behavioral RED and binds evidence. Reuse these responsibilities; packet output must not establish a competing registry, approval engine or evidence store.

## A1 System context / A13 external boundary

EluSlot designer saves existing product files. A read-only export request selects one project, one source mode, one module and one task. Export validates and projects into an agent-consumable packet; later CLI, MCP and embedded UI are consumers, not authority owners. No agent execution, network runtime, writeback or automatic green belongs to this slice.

## A2 Hexagonal diagram (PROPOSED)

```text
Designer / CLI / future MCP [driving adapters]
                   |
          ExportModulePacket [input port]
                   v
HOST application: snapshot → decode → validate → scope → project
           |                    |                 |
  source-reader output port    SPEC rules      report output port
           ^                    |                 ^
 filesystem/codec adapter   WORK identity     filesystem adapter
                           GUARD/EVID references
```

## A3 Module dependency / ownership diagram (PROPOSED)

```text
Tauri command / CLI → HOST packet application → SPEC domain projection rules
                              |                  (no IO / Qt / Tauri)
                              +→ WORK project binding [read]
                              +→ SPEC approved revision [read]
                              +→ GUARD envelope [read/reference]
                              +→ EVID binding [read/reference]
                              +→ existing filesystem port ← filesystem adapter
                              +→ codec boundary ← product format decoders

Product source files = design authority; SPEC = approval authority
Packet / HTML = derived snapshots, never write authority
```

## A4 responsibilities; A5–A9 ports/adapters/dependencies

| Role | Responsibility | Ownership / restriction |
|---|---|---|
| HOST packet application | Resolve explicit request, capture bytes, orchestrate validation, return diagnostics/output | Does not approve or repair source |
| SPEC | Pure scope/provenance/readiness rules; reference existing revision/contract model | No filesystem, UI or concrete adapters |
| Input port | ExportModulePacket(request), inspect freshness | Proposed public contract, pending approval |
| Source reader output seam | Read selected paths bounded to WORK project root, expose read errors | Reuse existing filesystem/path capabilities after API review |
| Codec output seam | Decode existing formats preserving IDs and diagnostic provenance | XML framework details stay in adapter; do not create schema migration in exporter |
| Export sink seam | Persist completed packet and HTML safely if requested | Existing atomic-write capability must be verified; concurrency guarantees not assumed |
| Driving adapters | Initial command/CLI, later MCP/panel | All invoke same application path |
| Driven adapters | Local source reader, format codecs, report renderer | No adapter-to-domain mutable state shortcut |

No new crate is justified yet. Candidate placement is HOST orchestration plus SPEC pure rules and adapters for IO/codec. Whether existing interfaces suffice is an explicit skeleton review, not permission to invent ports during implementation.

## A10 ownership / A11 mutation / A12 transaction

Authoritative product document ownership remains unchanged. Export mutates neither designer state, work board, SPEC approval, GUARD envelope nor evidence. Its only optional mutation is a derived output artifact. Read all chosen bytes once into a bounded snapshot, decode and validate in temporary memory, project, recheck sources before publish, then publish complete output or return diagnostics. No partial packet may be marked ready. Source changes after publication invalidate freshness when consumed; two-file input is a captured snapshot, not a promised OS-wide atomic transaction. The read/recheck approach cannot guarantee against transient ABA edits; stronger snapshot semantics require separate architecture approval.

## A14 forbidden dependencies

SPEC → filesystem/OS/Tauri/concrete adapter; UI directly setting approval; packet export modifying source; automatic fallback to another source; silent legacy ID migration; hints promoted to approved BDD; exporter duplicating WORK/GUARD/EVID ownership; Agent success promoted to acceptance; full source graph copied beyond declared module scope without recording adjacent references.

## Source selection and identity contract

Explicit modes: IntegratedEss(path), or SplitProduct(work .es, architecture .esml, design .esui), with an optional explicitly selected dedicated .sgendesign reference. Never discover and merge nearby documents automatically. If selected embedded design and selected dedicated design disagree, return SOURCE_CONFLICT and require owner selection. Standalone architecture-only inspection may return an informative NOT_READY projection, never implementation-ready. Unknown format versions, duplicate identity, missing required reference, malformed input and unsupported shape produce readable diagnostics. No silent codec defaults may erase missing required information.

moduleId is semantic identity; slotId is placement. moduleRef selects nodes, and slot membership must agree. A slotId supplied where moduleId is required is INVALID_IDENTITY. Duplicate moduleId is ambiguous until the current product ownership rule is explicitly confirmed; do not invent union or first-match behavior. Boundary-crossing edges retain explicit external endpoint references; do not recursively absorb adjacent modules. A uiDefinitionRef links the UI document, not automatically a subset of its nodes; absent explicit per-node ownership makes UI scoping unresolved and NOT_READY.

## Proposed minimal packet projection

Identity: project/task/module, explicitly bound root and source mode; sources: relative path, format/version, exact-byte hash, provenance selector (section/node/port ID); selected architecture nodes/ports/internal edges plus external edge references; referenced UI and hints preserving hint classification; approved SPEC revision/contracts, explicit BDD/AC/test/envelope references if available; diagnostics, readiness, fingerprint and origin. Do not include a generated timestamp in deterministic identity; operational timestamp is separate metadata. File bytes use SHA-256 proposal subject to dependency review. Snapshot identity is a versioned canonical encoding of sorted source path/hash pairs plus selection, task and approved revision bindings. Ordered behavioral arrays retain order. Same inputs give byte-identical semantic payload; no path/display-name/slot substitution for module identity.

Missing contracts, approval, BDD, acceptance, scope or required bindings must be displayed as missing; the sample documents are not assumed to contain a complete approved implementation envelope. Packet validity means consistent projection; implementation eligibility additionally requires current SPEC/GUARD/EVID gates. Existing SpecRevision fingerprint stays unchanged.

## Contracts / invariants

- C1: export success never mutates input or approval state.
- C2: every extracted fact traces to exact captured source bytes and selector; derived labels are marked derived.
- C3: scope is selected by moduleId with validated membership; UI scope is explicit or missing.
- C4: malformed/conflicting/unsupported/missing required inputs cannot yield READY.
- C5: hints remain hints; exported XML status/product_pass flags do not confer approval.
- C6: unchanged sources and request produce identical semantic packet; changed bound bytes produce PACKET_STALE even when savedAt-only change is semantically irrelevant (conservative first slice).
- C7: approved SPEC revision and GUARD/EVID references are checked through existing owners; no duplicate approval model.
- C8: failure before publication leaves existing valid output untouched; concurrency guarantees must match declared filesystem contract.

## Proposed public skeleton (NOT APPROVED; no code generated)

```rust
// Candidate placement/signatures only, subject to owner + interface review.
fn export_module_packet(request: ExportRequest) -> ExportOutcome;
fn project_module(snapshot: &CapturedSources, selection: &ModuleSelection,
                  bindings: &ExistingSpecBindings) -> ProjectionOutcome;
fn check_packet_freshness(packet: &PacketProjection,
                         current: &CapturedSources) -> Freshness;
// ExportOutcome = projected artifact with readiness/diagnostics OR typed failure.
// Readiness must distinguish projection completeness from implementation eligibility.
```

## Measurable acceptance and tests

AC1 valid explicit integrated/split fixtures project equal intended module facts with provenance; source bytes unchanged. AC2 every duplicate ID, missing member/port/UI ref, conflict and unsupported version case rejects readiness with actionable path/ID. AC3 identical captured bytes/request give identical payload; any bound source edit yields stale at consume. AC4 hints never satisfy approval/BDD/RED. AC5 module extraction excludes unrelated node bodies while preserving adjacent edge refs. AC6 renderer and structured payload agree on every diagnostic/status. AC7 failed publish preserves previous output. AC8 focused/module/adjacent regressions classified, architecture review and human acceptance recorded before completion.

Test levels: pure projection unit tests; application component with failure injection; L2 module contract through input port; L3 real fixture codec/filesystem round trip; L4 SPEC/WORK/GUARD/EVID regressions. No test executed or valid RED claimed in this planning slice.

Coverage B1 success Applicable; B2 boundary Applicable (zero members/ports, supported version limits, size bound to be decided); B3 invalid Applicable; B4 dependency failure Applicable; B5 partial failure Applicable; B6 state consistency Applicable; B7 transaction Applicable; B8 lifecycle Applicable (freshness/revision); B9 recovery Applicable (old output preservation); B10 cross-module Applicable; B11 compatibility Applicable; B12 regression Applicable. Parser resource limits, entity/DTD rejection, cancellation and publication collision policy require concrete agreed limits before RED.

## Module tasks

1. DEC-01: confirm source selection, identity/UI scoping, provenance hash and readiness/publication semantics.
2. XML-PACKET-SPEC: approved contract/BDD/skeleton and fixture expectations; no production edits.
3. XML-PACKET-RED: build executable module contract tests; demonstrate intended behavioral failure.
4. XML-PACKET-IMPL: fill approved envelope only, then focused/module GREEN.
5. XML-PACKET-VERIFY: integration/adjacent regressions, architecture/acceptance and unified report.

## Owner options / recommendation

A (recommended first slice): explicit integrated .ess export, read-only projection, exact-byte provenance; incomplete specifications visibly NOT_READY. Split formats and dedicated UI links are recognized but unsupported requests return diagnostics until a subsequent approved slice. This minimizes decoder scope and still grounds real product data.
B: implement integrated and split/dedicated readers together with explicit conflicts/UI selection. Larger compatibility surface and more fixture work.
C: first redesign all product schemas/ownership. Not recommended; broad structural migration is unnecessary to validate the packet path.

Approval must explicitly settle module identity duplicates, UI per-node scoping (whole referenced design as context vs explicit subset), source mode scope, exact-byte hashing, source size limits, and publication contract. DEC-01 remains PENDING. Implementation BLOCKED_PENDING_OWNER_DECISION. No build, package, install, Agent/DCC runtime verification or release is claimed (NOT RUN).
