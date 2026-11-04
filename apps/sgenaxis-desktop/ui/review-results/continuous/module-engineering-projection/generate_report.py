"""Generate unified Module HTML projection from approved packets (read-only sources).

Does not invent ModuleSpec / packet schema SSOT. SPEC model.rs + approved-a-contract
remain authority; this folder is a derived human/engineering surface with stale detection.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))

# Approved / dependency packets — read only.
SOURCES = [
    "reports/rust-improvements/continuous/product-documents/module.json",
    "reports/rust-improvements/continuous/product-documents/module.html",
    "reports/rust-improvements/xml-packet/approved-a-contract.md",
    "reports/rust-improvements/xml-packet-implementation/fixture-packet.json",
    "reports/rust-improvements/xml-packet-implementation/module.html",
    "reports/rust-improvements/xml-packet-tests/module.md",
    "apps/sgenaxis-desktop/crates/sgenaxis-spec/src/model.rs",
    "apps/sgenaxis-desktop/crates/sgenaxis-spec/src/packet.rs",
    "apps/sgenaxis-desktop/crates/sgenaxis-spec/fixtures/sample_module_spec.json",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def fnv1a64_hex(payload: str) -> str:
    """Match SPEC SpecRevision::fingerprint (FNV-1a 64) for contract binding demo."""
    h = 0xCBF29CE484222325
    for b in payload.encode("utf-8"):
        h ^= b
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    return f"{h:016x}"


def classify_source_review_verdict(verdict: str | None) -> str:
    """Map parsed source-review verdict text to a non-authoritative review_class.

    Never infer PASS merely because a verdict line parses. Negative/unknown
    verdicts stay non-PASS independent of card TDD_NOT_RUN posture.
    Positive matches require exact token equality after known prefix strip
    (TDD_/REVIEW_/GATE_) — never naive endswith(_PASS|_APPROVED), so
    NOT_PASS / NOT_APPROVED stay non-PASS.
    """
    if not verdict:
        return "UNPARSEABLE"
    token = verdict.strip().upper().replace(" ", "_")
    # Strip common prefixes so "TDD_FAIL" / "FAIL" / "Verdict: FAIL" collapse.
    for prefix in ("TDD_", "REVIEW_", "GATE_"):
        if token.startswith(prefix):
            token = token[len(prefix) :]
            break
    negative = {
        "FAIL",
        "FAILED",
        "FAILURE",
        "REJECT",
        "REJECTED",
        "ERROR",
        "BLOCKED",
        "GRAY_REWORK",
        "REWORK",
        "NEGATIVE",
    }
    positive = {
        "PASS",
        "PASSED",
        "OK",
        "SUCCESS",
        "APPROVED",
        "POSITIVE",
    }
    unknown = {
        "UNKNOWN",
        "UNCLEAR",
        "INCONCLUSIVE",
        "PENDING",
        "NOT_RUN",
        "SKIP",
        "SKIPPED",
    }
    # Known posture tokens first (e.g. NOT_RUN) before NOT_* negation.
    if token in unknown:
        return "SOURCE_REVIEW_UNKNOWN"
    # Explicit negation — never PASS-class (NOT_PASS, NOT_APPROVED, UNAPPROVED…).
    if (
        token.startswith("NOT_")
        or token.startswith("NON_")
        or (token.startswith("UN") and not token.startswith("UNKNOWN"))
    ):
        return "SOURCE_REVIEW_NEGATIVE"
    if token in negative or any(token.endswith(f"_{n}") or token.startswith(f"{n}_") for n in negative):
        return "SOURCE_REVIEW_NEGATIVE"
    # Exact positive tokens only after honest normalize — no endswith/startswith.
    if token in positive:
        return "REVIEW_PASS_STATIC_AUDIT"
    # Parsed but unrecognized — do not default to PASS.
    return "SOURCE_REVIEW_UNKNOWN"


def live_source_review_pointer(rel: str, *, card_tdd_posture: str) -> dict:
    """Plain review pointer — no invented EvidenceValidity / authority.

    Reads the pointed file when present and reports exact verdict text found.
    Does not promote planning/audit reviews to EVID-valid TDD_PASS.
    Negative/unknown source verdicts keep non-PASS review_class even when the
    card TDD posture is NOT RUN.
    """
    path = ROOT / rel
    out: dict = {
        "pointer": rel,
        "pointer_present": path.is_file(),
        "pointer_sha256": None,
        "reported_verdict_line": None,
        "card_tdd_posture": card_tdd_posture,
        "honest_status": None,
        "review_class": None,
        "authority": "none — plain source-review reference; not an EvidenceRef",
    }
    if not path.is_file():
        out["honest_status"] = "POINTER_MISSING"
        out["review_class"] = "UNRESOLVED"
        return out
    out["pointer_sha256"] = sha256_file(path)
    text = path.read_text(encoding="utf-8")
    m = re.search(r"\*\*Verdict\*\*\s*\|\s*\*\*([^*]+)\*\*", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\|\s*\*\*Verdict\*\*\s*\|\s*\*\*([^*]+)\*\*", text, re.IGNORECASE)
    if m:
        out["reported_verdict_line"] = m.group(1).strip()
    posture = (card_tdd_posture or "").strip().upper()
    review_class = classify_source_review_verdict(out["reported_verdict_line"])
    if posture.startswith("NOT RUN"):
        # Planning/audit cards: keep honest TDD posture as NOT RUN; classify
        # the pointed file's verdict honestly (FAIL ≠ PASS-class audit).
        out["honest_status"] = "TDD_NOT_RUN"
        out["review_class"] = review_class
    elif out["reported_verdict_line"]:
        out["honest_status"] = out["reported_verdict_line"]
        # Non-NOT-RUN posture: keep pointer class; still surface negatives.
        if review_class in ("SOURCE_REVIEW_NEGATIVE", "SOURCE_REVIEW_UNKNOWN", "UNPARSEABLE"):
            out["review_class"] = review_class
        else:
            out["review_class"] = "SOURCE_REVIEW_POINTER"
    else:
        out["honest_status"] = "UNPARSEABLE"
        out["review_class"] = "UNPARSEABLE"
    return out


def build_trace_rows(packet: dict, doc: dict) -> list[dict]:
    rows: list[dict] = []
    # From approved A fixture: captured BDD/TDD facts on selected nodes.
    for node in packet.get("nodes", []):
        attrs = node.get("attributes") or {}
        bdd_texts: list[str] = []
        tdd_texts: list[str] = []
        for child in node.get("children") or []:
            name = child.get("name")
            if name == "bddSpecs":
                bdd_texts = [
                    (c.get("text") or "").strip()
                    for c in (child.get("children") or [])
                    if (c.get("text") or "").strip()
                ]
            if name == "tddSpecs":
                tdd_texts = [
                    (c.get("text") or "").strip()
                    for c in (child.get("children") or [])
                    if (c.get("text") or "").strip()
                ]
        if bdd_texts or tdd_texts:
            rows.append(
                {
                    "task_id": packet.get("task_id"),
                    "module_id": (packet.get("module") or {}).get("module_id"),
                    "node_id": attrs.get("id"),
                    "bdd": bdd_texts,
                    "tdd": tdd_texts,
                    "result": packet.get("readiness"),
                    "source_sha256": (packet.get("source") or {}).get("sha256"),
                    "payload_sha256": packet.get("payload_sha256"),
                    "source_path": (packet.get("source") or {}).get("relative_path"),
                    "origin": "xml-packet-implementation/fixture-packet.json",
                }
            )
    # Document-contract BDD inventory → planned TDD categories (no new behavior claimed).
    for item in doc.get("current_behavior_BDD_inventory") or []:
        rows.append(
            {
                "task_id": "PD-RUST-DOCUMENT-CONTRACT-01",
                "module_id": "product-documents",
                "node_id": item.get("id"),
                "bdd": [item.get("meaning")],
                "tdd": [
                    "NOT RUN — characterization after DOCUMENT-DEC; "
                    f"evidence pointer: {item.get('evidence')}"
                ],
                "result": "AUDIT_ONLY",
                "source_sha256": None,
                "payload_sha256": None,
                "source_path": item.get("evidence"),
                "origin": "continuous/product-documents/module.json",
            }
        )
    return rows


def build_spec(source_hashes: dict[str, str], packet: dict, doc: dict) -> dict:
    generated_at = datetime.now(TZ).isoformat(timespec="seconds")
    contracts = [
        {
            "id": "CTR-PROJ-001",
            "title": "No competing SSOT",
            "body": (
                "Module HTML / module.json here are derived projections. "
                "Authoritative ModuleSpec shape remains sgenaxis-spec model.rs; "
                "A packet contract remains xml-packet/approved-a-contract.md; "
                "document format inventory remains product-documents/module.json."
            ),
        },
        {
            "id": "CTR-PROJ-002",
            "title": "BDD↔TDD/task/result/sourcehash linkage",
            "body": (
                "Each projected row binds task_id, module_id, BDD text, TDD text, "
                "result/readiness, and exact source/payload SHA-256 when available. "
                "Hints never become approval."
            ),
        },
        {
            "id": "CTR-PROJ-003",
            "title": "Stale detection",
            "body": (
                "bound_source_sha256 must match current bytes of SOURCES. "
                "Mismatch ⇒ PACKET_STALE / PROJECTION_STALE; do not treat HTML as current."
            ),
        },
        {
            "id": "CTR-PROJ-004",
            "title": "SPEC/GUARD/EVID ownership preserved",
            "body": (
                "Projection may reference SPEC revision/contracts, GUARD envelope and "
                "EVID bindings but must not approve, mutate GUARD, or invent evidence validity. "
                "A slice readiness stays NOT_READY until those owners resolve."
            ),
        },
        {
            "id": "CTR-A-REF",
            "title": "Approved A envelope (reference)",
            "body": (
                "Read-only .ess → module packet; SHA-256 provenance; PACKET_STALE on "
                "source change; diagnostics APPROVAL_UNRESOLVED / APPROVED_BEHAVIOR_UNRESOLVED; "
                "see approved-a-contract.md AC-A01..A08."
            ),
        },
    ]
    contract_fingerprint = fnv1a64_hex(json.dumps(contracts, ensure_ascii=False, separators=(",", ":")))
    module_spec_document = {
        "module_id": "module-engineering-projection",
        "module_name": "模組工程投影（統一 Module HTML）",
        "responsibility": (
            "Derive unified Module HTML from approved XML/SPEC packet + document-contract "
            "packets; expose BDD↔TDD/task/result/sourcehash; detect stale sources. "
            "Does not own approval, GUARD, or EVID stores."
        ),
        "revisions": [
            {
                "id": "rev-proj-v0",
                "module_id": "module-engineering-projection",
                "version_label": "v0-projection",
                "status": "draft",
                "content_hash": None,
                "contracts": contracts,
                "note": (
                    "Draft projection revision. Fingerprint of contracts (FNV-1a, SPEC algorithm) "
                    f"= {contract_fingerprint}; not an Approved SpecRevision."
                ),
            }
        ],
        # Empty unless owner-provided EvidenceRef records exist (CTR-PROJ-004).
        # External reviews live under top-level `evidence` as plain pointers only.
        "evidence_refs": [],
    }

    diagram_a = """Designer / CLI [driving]
        |
   (read-only) Export / Project Module HTML
        v
HOST application (orchestration only)
   |              |               |
FS read      SPEC model.rs    report render
   ^         (ModuleSpec)          ^
product .ess   packet.rs      this module.html
               GUARD/EVID [reference only — unresolved in A]
Product files = design authority; SPEC = approval authority;
Packet/HTML = derived; never write authority."""

    diagram_b = """Ownership / stale chain
product-documents/module.json  ──┐
approved-a-contract.md         ──┼─► bound_source_sha256
fixture-packet.json            ──┤         │
model.rs / packet.rs           ──┘         v
                                   regenerate → compare hashes
                                   match: CURRENT
                                   mismatch: PROJECTION_STALE
BDD text ← node bddSpecs ← source selector ← source.sha256
TDD text ← node tddSpecs ← same binding
task_id / module_id / readiness / payload_sha256 stay on packet envelope."""

    bdd_tdd_trace = build_trace_rows(packet, doc)

    tests_plan = {
        "status": "NOT RUN (planning definitions for TDD Gate)",
        "categories": {
            "normal": "Regenerate HTML from unchanged approved sources → CURRENT; embed ModuleSpec draft + trace rows.",
            "boundary": "Empty BDD/TDD on a node → row omitted or explicit empty arrays; missing optional work/design still projects.",
            "invalid": "Missing required source path in SOURCES list → generator fails closed; no partial READY claim.",
            "dependency_failure": "Unreadable approved packet → hard error; do not invent inventory.",
            "partial_failure": (
                "One source unreadable → whole projection fails (no half-current HTML). "
                "If module.html write fails after module.json write, roll back JSON to prior pair."
            ),
            "state": "Draft revision never auto-flips to approved; readiness of referenced packet stays NOT_READY.",
            "transaction": (
                "Publish module.json + module.html as a pair: backup prior bytes, write both, "
                "on any write failure restore prior pair (no new-JSON/old-HTML)."
            ),
            "lifecycle": (
                "Refresh after source edit → PROJECTION_STALE until regenerate; "
                "evidence_refs stay empty until owner EVID; plain pointers under evidence."
            ),
            "regression": "SPEC sample_module_spec.json still loads; A fixture payload_sha256 unchanged; no production edits.",
        },
        "intended_red": (
            "Independent TDD may add a compile-able check that fails when bound_source_sha256 "
            "mismatches current bytes or when HTML lacks contracts/tests/scope/evidence/risk/diagrams."
        ),
    }

    risks = [
        "HTML mistaken for approval/SSOT — mitigated by draft status + CTR-PROJ-001.",
        "Stale HTML after packet refresh — mitigated by bound hashes + check_stale().",
        "Document-contract BDD inventory is audit-level, not executable GREEN.",
        "GUARD/EVID remain unresolved on A packets; projection must not clear diagnostics.",
        "Native UI / Live Agent / packaging NOT RUN.",
    ]

    return {
        "identity": {
            "module": "module-engineering-projection",
            "task": "PD-RUST-MODULE-HTML-01",
            "parent": "PD-RUST-IMPROVE-20261025",
            "dependencies": [
                "PD-RUST-DOCUMENT-CONTRACT-01",
                "PD-RUST-XML-PACKET-IMPL-01",
            ],
            "date": "2026-10-26 Asia/Taipei",
            "generated_at": generated_at,
            "head": "31babe87a7ef1e40a0d4bedc523077e7a45d63ab",
            "branch": "cursor/ui-bhv-arch-layer-editor",
            "state": "UNIFIED_HTML_PROJECTION_READY_FOR_TDD",
            "architecture_status": "DERIVED_FROM_APPROVED_A_AND_DOCUMENT_AUDIT",
            "implementation": "REPORT_ONLY — no production schema/API changes",
            "behavior_verification": "NOT RUN",
            "board": "yellow; implementer does not green",
        },
        "executive_meaning": (
            "Refresh a single Module HTML that projects existing ModuleSpec shape and "
            "approved continuous/rust-improvements packets into contracts, tests, scope, "
            "evidence, risk, two diagrams, and BDD↔TDD/task/result/sourcehash rows — "
            "without inventing a competing schema SSOT."
        ),
        "diagram_a_hexagonal": diagram_a,
        "diagram_b_ownership_stale": diagram_b,
        "module_spec_document": module_spec_document,
        "contracts": contracts,
        "bdd_tdd_task_result_sourcehash": bdd_tdd_trace,
        "scope": {
            "allowed_write": [
                "reports/rust-improvements/continuous/module-engineering-projection/**",
                "reports/dispatch-pd/PD-RUST-MODULE-HTML-01.md",
            ],
            "read_only_sources": SOURCES,
            "protected": [
                "production schema/API/Ports",
                "unapproved GUARD/DOCUMENT decisions",
                "board green / commit / push",
                "other module WIP",
            ],
            "packet_readiness_referenced": packet.get("readiness"),
            "document_decision": "PENDING PD-RUST-DOCUMENT-DEC-01",
        },
        "tests": tests_plan,
        "evidence": {
            "xml_packet_impl_review": live_source_review_pointer(
                "reports/dispatch-pd/PD-RUST-XML-PACKET-IMPL-01-TDD-REVIEW.md",
                card_tdd_posture="EXECUTED_GATE",
            ),
            "document_contract_review": live_source_review_pointer(
                "reports/dispatch-pd/PD-RUST-DOCUMENT-CONTRACT-01-TDD-REVIEW.md",
                card_tdd_posture="NOT RUN — planning/audit only",
            ),
            "fixture_packet": "reports/rust-improvements/xml-packet-implementation/fixture-packet.json",
            "approved_contract": "reports/rust-improvements/xml-packet/approved-a-contract.md",
            "product_documents": "reports/rust-improvements/continuous/product-documents/module.json",
            "spec_model": "apps/sgenaxis-desktop/crates/sgenaxis-spec/src/model.rs",
            "fixture_payload_sha256": packet.get("payload_sha256"),
            "fixture_source_sha256": (packet.get("source") or {}).get("sha256"),
            "packet_diagnostics": packet.get("diagnostics"),
            "module_spec_evidence_refs": (
                "empty — no owner-issued EvidenceRef for draft rev-proj-v0; "
                "do not invent validity=valid"
            ),
        },
        "risk": risks,
        "stale_detection": {
            "algorithm": "sha256 of each path in SOURCES vs bound_source_sha256",
            "bound_source_sha256": source_hashes,
            "status_at_generation": "CURRENT",
            "stale_codes": ["PROJECTION_STALE", "PACKET_STALE", "SOURCE_CHANGED"],
        },
        "acceptance": [
            "AC-HTML-01 HTML embeds two diagrams (hexagonal + ownership/stale).",
            "AC-HTML-02 HTML sections include contracts, tests, scope, evidence, risk.",
            "AC-HTML-03 Embedded ModuleSpecDocument matches existing SPEC field names; status draft.",
            "AC-HTML-04 BDD↔TDD/task/result/sourcehash rows derived from approved fixture + document audit.",
            "AC-HTML-05 bound_source_sha256 enables stale detection without new SSOT.",
            "AC-HTML-06 No production/schema edits; no board green; READY_FOR_TDD report only.",
        ],
        "status": {
            "projection": "Generated",
            "behavior_tests": "NOT RUN",
            "native_UI": "NOT RUN",
            "owner_acceptance": "PENDING",
            "commit_push": "NOT RUN",
        },
    }


def check_stale(bound: dict[str, str]) -> dict:
    mismatches = []
    for rel, expected in bound.items():
        path = ROOT / rel
        if not path.is_file():
            mismatches.append({"path": rel, "reason": "MISSING"})
            continue
        actual = sha256_file(path)
        if actual != expected:
            mismatches.append({"path": rel, "expected": expected, "actual": actual})
    return {
        "status": "CURRENT" if not mismatches else "PROJECTION_STALE",
        "mismatches": mismatches,
    }


def render_value(v) -> str:
    if isinstance(v, dict):
        return (
            "<dl>"
            + "".join(
                f"<dt>{html.escape(str(k))}</dt><dd>{render_value(x)}</dd>" for k, x in v.items()
            )
            + "</dl>"
        )
    if isinstance(v, list):
        return "<ul>" + "".join(f"<li>{render_value(x)}</li>" for x in v) + "</ul>"
    return "<pre>" + html.escape(str(v)) + "</pre>"


def render_html(data: dict) -> str:
    stale = check_stale(data["stale_detection"]["bound_source_sha256"])
    badge = "CURRENT" if stale["status"] == "CURRENT" else "PROJECTION_STALE"
    sections = [
        ("identity", data["identity"]),
        ("executive_meaning", data["executive_meaning"]),
        ("diagram_a_hexagonal", data["diagram_a_hexagonal"]),
        ("diagram_b_ownership_stale", data["diagram_b_ownership_stale"]),
        ("contracts", data["contracts"]),
        ("module_spec_document", data["module_spec_document"]),
        ("bdd_tdd_task_result_sourcehash", data["bdd_tdd_task_result_sourcehash"]),
        ("tests", data["tests"]),
        ("scope", data["scope"]),
        ("evidence", data["evidence"]),
        ("risk", data["risk"]),
        ("stale_detection", {**data["stale_detection"], "live_check": stale}),
        ("acceptance", data["acceptance"]),
        ("status", data["status"]),
    ]
    body = [
        "<!doctype html><html lang='zh-Hant'><meta charset='utf-8'>",
        "<title>Module engineering projection — unified Module HTML</title>",
        "<style>body{font:16px/1.65 system-ui;max-width:1120px;margin:32px auto;padding:0 24px;"
        "background:#0f1720;color:#e7eef6}h1,h2,dt{color:#8ec8ff}pre{white-space:pre-wrap;"
        "overflow-wrap:anywhere;background:#182230;padding:16px;border-radius:8px}"
        "section{border:1px solid #314356;padding:16px;margin:18px 0;border-radius:8px}"
        ".badge{padding:14px;background:#3b2f14;border-left:6px solid #e0b34c;margin:16px 0}"
        ".ok{border-left-color:#5dcea0;background:#143028}.stale{border-left-color:#e07070;"
        "background:#3a1818}a{color:#9fd0ff}</style>",
        "<h1>統一模組 HTML — ModuleSpec 工程投影</h1>",
        f"<p class='badge {'ok' if badge == 'CURRENT' else 'stale'}'>PD-RUST-MODULE-HTML-01 · "
        f"stale check: <b>{html.escape(badge)}</b> · derived projection only · "
        "SPEC/GUARD/EVID ownership unchanged · 不自改綠</p>",
        "<p>來源：已核准 continuous/product-documents 與 xml-packet A 封包（唯讀）。"
        "不新增競爭 schema SSOT。</p>",
        "<nav><a href='#diagram_a_hexagonal'>圖 A</a> · "
        "<a href='#diagram_b_ownership_stale'>圖 B</a> · "
        "<a href='#contracts'>contracts</a> · <a href='#tests'>tests</a> · "
        "<a href='#scope'>scope</a> · <a href='#evidence'>evidence</a> · "
        "<a href='#risk'>risk</a></nav>",
    ]
    for key, val in sections:
        body.append(f"<section id='{html.escape(key)}'><h2>{html.escape(key)}</h2>")
        body.append(render_value(val))
        body.append("</section>")
    body.append(
        '<script type="application/json" id="module-spec">'
        + json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
        + "</script></html>"
    )
    return "".join(body)


class OutputPairRecoveryError(RuntimeError):
    """Primary write failed and at least one independent restore/cleanup failed.

    Preserves the primary cause; recovery outcomes are listed separately.
    Does not claim durability when the OS denies restore.
    """

    def __init__(self, primary: BaseException, recovery_errors: list[tuple[str, BaseException]]):
        self.primary = primary
        self.recovery_errors = list(recovery_errors)
        parts = [f"primary={type(primary).__name__}: {primary}"]
        for label, err in self.recovery_errors:
            parts.append(f"recovery:{label}={type(err).__name__}: {err}")
        super().__init__("; ".join(parts))


def _restore_or_cleanup(
    path: Path,
    backup: bytes | None,
    *,
    label: str,
    recovery_errors: list[tuple[str, BaseException]],
    recovery_attempted: list[str],
) -> None:
    """Independently restore prior bytes or remove absent-prior residue."""
    recovery_attempted.append(label)
    try:
        if backup is not None:
            path.write_bytes(backup)
        elif path.exists():
            path.unlink()
    except Exception as err:  # noqa: BLE001 — classify recovery; keep primary
        recovery_errors.append((label, err))


def write_output_pair(json_text: str, html_text: str) -> None:
    """Write module.json + module.html; on failure restore/clean both independently.

    Satisfies @partial_failure / @transaction: HTML write failure must not leave
    new JSON + old HTML. Absent-prior partial residues are cleaned. Restore of
    each output is attempted even if the other restore raises; recovery failure
    is classified separately while preserving the primary cause.
    """
    json_path = HERE / "module.json"
    html_path = HERE / "module.html"
    backup_json = json_path.read_bytes() if json_path.is_file() else None
    backup_html = html_path.read_bytes() if html_path.is_file() else None
    try:
        json_path.write_text(json_text, encoding="utf-8")
        html_path.write_text(html_text, encoding="utf-8")
    except Exception as primary:
        recovery_errors: list[tuple[str, BaseException]] = []
        recovery_attempted: list[str] = []
        # Always attempt both restores independently (HTML even if JSON restore fails).
        _restore_or_cleanup(
            json_path,
            backup_json,
            label="json_restore",
            recovery_errors=recovery_errors,
            recovery_attempted=recovery_attempted,
        )
        _restore_or_cleanup(
            html_path,
            backup_html,
            label="html_restore",
            recovery_errors=recovery_errors,
            recovery_attempted=recovery_attempted,
        )
        # Attach attempt markers for gate harnesses without claiming durability.
        primary.output_pair_recovery_attempted = list(recovery_attempted)  # type: ignore[attr-defined]
        primary.output_pair_recovery_errors = list(recovery_errors)  # type: ignore[attr-defined]
        if recovery_errors:
            raise OutputPairRecoveryError(primary, recovery_errors) from primary
        raise


def main() -> None:
    source_hashes: dict[str, str] = {}
    for rel in SOURCES:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"Missing approved source: {rel}")
        source_hashes[rel] = sha256_file(path)

    packet = load_json(
        "reports/rust-improvements/xml-packet-implementation/fixture-packet.json"
    )
    doc = load_json(
        "reports/rust-improvements/continuous/product-documents/module.json"
    )
    data = build_spec(source_hashes, packet, doc)
    write_output_pair(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        render_html(data),
    )
    stale = check_stale(source_hashes)
    print(
        json.dumps(
            {
                "wrote": [
                    str(HERE / "module.json"),
                    str(HERE / "module.html"),
                ],
                "stale_check": stale["status"],
                "source_count": len(source_hashes),
                "trace_rows": len(data["bdd_tdd_task_result_sourcehash"]),
                "evidence_refs_count": len(
                    data["module_spec_document"].get("evidence_refs") or []
                ),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
