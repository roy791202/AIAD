# Independent architecture and code review — approved A

Owner status: YELLOW. Review snapshot 2026-10-25, local working tree; no commit or release approval.

## Outcome

P0/P1: none found. P2: one reproduced issue RESOLVED and independently reverified. P3/P4: none raised. No open actionable findings in reviewed scope.

### P2 — Literal XML declaration text is incorrectly rejected as a DTD

Source: apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/ess_codec.rs:21.
The raw substring check rejects well-formed CDATA or comments containing `<!DOCTYPE` or `<!ENTITY`. A BDD/TDD hint may legitimately contain this text; no declaration or entity expansion occurs. This violates preservation of captured specification text and unnecessarily prevents extraction.

Reproduction fixture: literal-dtd.ess in this directory. It differs from the independent fixture only by replacing the BDD text with `<![CDATA[Given literal <!DOCTYPE example>]]>`.

Command (cwd apps/sgenaxis-desktop):
`C:/Users/g6812/.cargo/bin/cargo.exe run --offline -q -p sgenaxis-host --example export_ess_packet -- D:/AIAD reports/rust-improvements/xml-packet-review/literal-dtd.ess semantic-A TASK-A`

Observed: exit 1, `XML_DTD_FORBIDDEN: DTD and entity declarations are forbidden`.
Expected: successful NOT_READY projection preserving literal BDD text. Reject actual declarations using parser-aware detection; keep actual DTD regression coverage. No API or architecture change required.

## Independently verified

`cargo test --offline -p sgenaxis-host --test module_packet`: 12 passed, 0 failed. Test expectations unchanged by reviewer.

Read actual stable source bodies, approved-a-contract.md, initial skeleton, acceptance fixture/tests, relevant product serializer and example CLI. SPEC has pure data/hash/projection only; XML SDK confined to Adapters; host receives FileSystemPort and EssDecoderPort. Public DTO/trait/function signatures match the originally inspected skeleton. No source writes, mutable global state, new authoritative approval, automatic eligibility or unrelated production changes found in reviewed slice.

Reviewed identity categories, slot/module distinction, membership consistency, directional graph endpoints, selected-node/task projection, semantic container edges, unresolved UI context, required NOT_READY diagnostics, deterministic serialization and exact-byte hashing, expected-hash rejection, capture/recheck and freshness project binding, lexical pre-read path checks and stable errors.

## Explicit limits

This is local source review plus focused tests and one example-CLI reproduction, not full workspace/Tauri regression, native UI, real Agent, live MCP, installer, remote CI or release proof. Filesystem byte guard is post-read; no physical symlink/junction containment, ABA resistance or snapshot guarantee. Element/depth guards run after the XML parser allocates its document and before recursive capture; do not claim preparse allocation limits. Caller-supplied larger limits can increase stack/memory use. These were already outside the stronger guarantees of approved A and are not presented as new blockers.

Successful extraction remains NOT_READY and owner yellow; passing tests do not grant execution or completion approval.

## Final narrow re-audit

Parser-aware DtdDetected mapping now replaces raw substring detection. Independently reran full focused suite: 15 passed, 0 failed, including real DTD rejection, CDATA preservation, semantic Module endpoint and structure/provenance cases. Actual literal-dtd.ess CLI reproduction now exits 0 and captured BDD text is Given literal <!DOCTYPE example>; readiness remains NOT_READY. Evidence literal-dtd-result.json. Initial discovery above is retained as historical RED evidence. Owner YELLOW; no acceptance or release authority inferred.

