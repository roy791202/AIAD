# A slice — recommended draft (not locked)

Status: **PROPOSED / PENDING_PD-RUST-XML-PACKET-DEC-01**. This document is the
recommended first-slice envelope drafted under PD-RUST-XML-PACKET-ARCH-01. It is
**not** owner-locked skeleton approval and does **not** claim production
implementation, independent review, or Workspace/EXEC/Tauri GREEN.

Architecture SSOT for this packet remains `architecture.md` and
`module.html#module-spec`: PLANNING · NOT_READY_FOR_IMPLEMENTATION · DEC-01
PENDING · implementation BLOCKED · test_result NOT RUN. Executable RED/impl
evidence belongs on sibling IMPL/RED cards, not this ARCH packet.

Recommendation (slice A): explicit integrated `.ess` read-only packet; split
input, publication, schema migration, Agent execution and new UI/IPC stay out of
scope until a later approved slice. Existing product files and
SPEC/FLOW/GUARD/EVID state stay unchanged.

## Envelope and responsibilities (proposed)

- SPEC `src/packet.rs`: plain captured facts/packet DTOs, decoder output trait,
  pure validation/projection and SHA-256. No XML SDK, filesystem or host types.
- Adapters `src/ess_codec.rs`: `ProductEssDecoder` implements `EssDecoderPort`;
  use a real read-only XML parser, prohibit DTD/entity expansion, bound depth and
  element count. No IO, source repair, inferred approval or schema migration.
- HOST `src/module_packet.rs`: existing `FileSystemPort` and supplied decoder;
  explicit project-root, relative `.ess` path, `module_id`, `task_id`; capture,
  validate/project and re-read to detect changes before returning an in-memory
  packet. FileSystemPort reads whole files; byte limit is a post-read parse guard,
  not a bounded IO guarantee. Existing path validation is lexical, not a physical
  symlink/junction sandbox. Stronger path/IO guarantees remain separate work.
- Optional HOST example CLI only prints the packet JSON. No output file,
  Tauri command, UI flow, source write or Agent call belongs to this slice.

Dependencies are toward SPEC abstractions. `roxmltree =0.20.0` (reported MSRV1.60)
is confined to Adapters; `sha2 0.10.9` is pure deterministic hashing in SPEC.
Existing SPEC FNV revision fingerprints are untouched. Both effective Cargo
locks must resolve the new dependencies; no unrelated dependency upgrades.
Concrete crate paths/signatures remain candidates until DEC-01 and a subsequent
SPEC/skeleton card approve them.

## Proposed skeleton (NOT APPROVED; no code generated here)

Candidate public DTOs/trait/signatures for a later SPEC/IMPL card. This ARCH
packet does not generate production bodies or claim a pre-RED checkpoint.
No new crate, ownership manager, mutable global state, public signature or existing
public API changes are authorized by this document alone. If the skeleton is
insufficient after approval, report ARCHITECTURE_GAP on the implementing card.

## Input and format contract

Only explicitly chosen project-relative `.ess` paths. No automatic discovery or
fallback. Empty project/module/task/path, rooted paths, drive/ADS components and
parent traversal reject before filesystem reads. Do not infer module from slot,
display name, layer name or drawing location. Reject malformed XML, non-UTF8,
DTD, unsupported format/version/namespace shape and exceeded limits.

Root is `eluslotScene format="eluslot.ess" formatVersion="1" encoding="xml"`.
Exactly one architecture section with one `eluslotArch` of format `eluslot.esml`
v1 is required. Work/design sections are optional captured context; duplicates
are malformed/ambiguous. Validate any present section's declared encoding/format
against the product's current integrated XML output. Missing work task or UI
ownership is diagnostic, never invented data.

Default parse guards are 8MiB source bytes, depth128, 100000 elements; callers may
supply stricter or larger positive values through `PacketLimits`. Zero limits
are invalid. These limits bound decoding/projection resource policy, not product
file schema or valid authoring capabilities.

## Identity, references and scope

Each architectural node/edge/port/module/slot ID must be nonempty and unique in
its identity category; moduleId and slotId are separate namespaces. Validate
module slot membership against each node's moduleRef/layerRef, including dangling
references. A moduleId duplicated across slots is ambiguous in this first slice
and rejects; do not union views. Unassigned ordinary nodes remain permissible.
Module slots must be declared under Layer nodes. All graph endpoints must refer
to existing architecture nodes and their actual direction-specific ports.

Output selected module member nodes only. Preserve attributes, nested specProps,
input/output fields, dependencies and BDD/TDD text as captured source facts.
Edges entirely inside selected members are internal; edges with exactly one
selected endpoint are boundary references. Do not copy unrelated node bodies or
automatically follow adjacent modules. Module/Layer boundary edges are included
when their endpoint is the selected semantic container, without importing bodies.
Only the explicitly selected work task may be included.

For selected UI nodes, expose uiDefinitionRef and embedded design node IDs as
context references only. A document reference does not assign individual UI nodes
to this module. Never copy the whole unrelated design or guess its node scope.
Report UI_SCOPE_UNRESOLVED (and UI_DOCUMENT_UNRESOLVED when absent), rather than
inventing a mapping. Empty modules and absent tasks have explicit diagnostics.

## Readiness, provenance, determinism and failure

The A projection has only `NOT_READY`: it does not resolve authoritative approval,
contract/BDD/AC, GUARD or EVID bindings. Successful extraction is not implementation
eligibility. Diagnostics always explain at least absent approval and approved
behavior; UI and missing task/module-content diagnostics are additional. XML
product_pass/status and plain hints never grant approval or green.

Source provenance is exact-byte SHA-256, path, format/version; each selected fact
has a stable source selector. Payload SHA-256 is over the deterministic serialized
packet with payload_sha256 empty (no generated timestamp). Repeated unchanged
requests produce byte-identical semantic output. Expected source-hash mismatch,
or changed source between capture and recheck, returns PACKET_STALE/SOURCE_CHANGED.
Freshness check compares current exact source bytes and bound project; it neither
approves execution nor guarantees against ABA edits. Missing source errors remain
readable. Errors never return a partial ready packet or mutate anything.

Stable error codes: INVALID_REQUEST, INVALID_PATH, UNSUPPORTED_SOURCE,
SOURCE_READ_FAILED, SOURCE_TOO_LARGE, XML_LIMIT_EXCEEDED, XML_DTD_FORBIDDEN,
INVALID_XML, UNSUPPORTED_FORMAT, INVALID_DOCUMENT, DUPLICATE_ID, MODULE_NOT_FOUND,
INVALID_IDENTITY, MISSING_REFERENCE, MEMBERSHIP_MISMATCH, SOURCE_CHANGED,
PACKET_STALE, SOURCE_BINDING_MISMATCH. Diagnostics are structured code/subject/message.

## Acceptance and test levels (proposed; NOT RUN on this card)

AC-A01 real well-formed product fixture selects explicit semantic module and task.
AC-A02 attributes/ports/spec hints and external-edge references preserved with provenance.
AC-A03 unrelated node/work/UI bodies excluded; ambiguous identities/references rejected.
AC-A04 no writes/approval mutations; malformed source, bad path, IO failure and limits observable.
AC-A05 exact known SHA-256, deterministic bytes and stale/source-change checks proven.
AC-A06 all successful projections remain NOT_READY with explicit missing information.
AC-A07 focused, host/adapter/SPEC and existing workspace/Tauri regressions pass or classified.
AC-A08 independent review and actual CLI fixture output included; no Live/packaging claims.

Independent tests belong on sibling RED/IMPL cards after DEC-01 / SPEC approval.
This ARCH packet claims neither executable RED nor GREEN regression counts.
