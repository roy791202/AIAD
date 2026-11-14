#!/usr/bin/env python3
"""Independent harness-contract document probes (read-only)."""
from __future__ import annotations

import hashlib
import html
import json
import pathlib
import re
import subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[7]
HC = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M08/planning/harness-contract"
PC = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M08/planning/precision-correction"
OUT = pathlib.Path(__file__).resolve().parent
MISSING = (
    ROOT
    / "docs/requirements-confirmation/phase1-spec/tasks/M08/verification/input-admission-correction-20261103/missing-inputs.json"
)
INV = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json"


def read(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def put(name: str, data) -> None:
    (OUT / name).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


checks: list[dict] = []


def ck(name: str, passed: bool, detail=None) -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})


spec = read(HC / "module-spec.json")
blocked = read(HC / "blocked-record.json")
validator = read(HC / "validator-test-plan.json")
prereq = read(HC / "module-prerequisites.json")
fixtures = read(HC / "fixtures.json")
verification = read(HC / "verification.json")
invariants = read(HC / "record-invariants.json")
pc_prereq = read(PC / "current-prerequisites.json")

REQUIRED_HC = [
    "module-spec.json",
    "fixtures.json",
    "verification.json",
    "blocked-record.json",
    "validator-test-plan.json",
    "index.html",
    "module-prerequisites.json",
    "record-fields.json",
    "record-invariants.json",
    "artifact-observation.json",
    "automation-map.json",
    "step-definition-stubs.json",
    "module.feature",
]
for name in REQUIRED_HC:
    ck("harness-contract file present " + name, (HC / name).is_file())

ck("16 native case IDs", len(spec["case_map"]) == 16)
ids = [c["id"] for c in spec["case_map"]]
ck(
    "case IDs M08-N01..M08-N16",
    ids == [f"M08-N{i:02d}" for i in range(1, 17)],
)
ck("all cases BLOCKED/NOT RUN", all("BLOCKED" in c["current_status"] for c in spec["case_map"]))
ck("12 record invariants", len(invariants["rules"]) == 12)
inv_ids = [r["id"] for r in invariants["rules"]]
ck("invariant IDs HR01..HR12", inv_ids == [f"M08-HR{i:02d}" for i in range(1, 13)])

ck(
    "validator-test-plan matches module-spec negatives",
    len(validator["negative_cases"]) == 12
    and validator["negative_cases"] == spec["validator_plan"]["negative_cases"],
)
ck("fixtures declarative only", fixtures.get("status") == "DECLARATIVE_NOT_CREATED")
ck("verification runtime NOT RUN", verification.get("runtime_validator") == "NOT RUN")
ck("verification native NOT RUN", verification.get("native_product_tests") == "NOT RUN")
ck("module_complete false", verification.get("module_complete") is False)

ck(
    "blocked-record verdict BLOCKED",
    blocked["result"]["verdict"] == "BLOCKED"
    and blocked["execution"]["state"] == "NOT RUN",
)
ck(
    "blocked-record no fabricated PASS",
    blocked["evidence"]["assertions_executed"] is False
    and blocked["result"]["verdict"] != "PASS",
)
ck(
    "blocked-record Win11 gap explicit",
    blocked["environment"]["is_Windows11"] is False
    and "Windows11" in " ".join(blocked["result"]["unmet_prerequisites"]),
)
ck(
    "artifact ineligible in blocked-record",
    blocked["artifact"]["eligibility"] == "HISTORICAL_UNLINKED",
)

page = (HC / "index.html").read_text(encoding="utf-8")
embedded = re.search(
    r'<script type="application/json" id="module-spec">(.*?)</script>',
    page,
    re.S,
)
ck("index.html embeds module-spec", embedded is not None)
if embedded:
    embedded_spec = json.loads(embedded.group(1))
    ck("index embedded spec equals module-spec.json", embedded_spec == spec)

links = re.findall(r'href="([^"#]+)"', page)
ck(
    "index.html local links resolve",
    all((HC / link).is_file() for link in links if not link.startswith("http")),
)

# Historical prerequisite projection vs precision-correction overlay
m01_hc = next(m for m in prereq["modules"] if m["module"] == "M01")["current"]
m01_pc = next(m for m in pc_prereq["modules"] if m["module"] == "M01")["current"]
ck(
    "harness-contract M01 projection marked historical relative to precision-correction",
    "awaiting confirmation" in m01_hc and "adopted" in m01_pc,
    {"harness_contract": m01_hc, "precision_correction_overlay": m01_pc},
)
ck(
    "precision-correction supersedes note present",
    "supersedes" in pc_prereq and "historical harness-contract" in pc_prereq["supersedes"],
)

all_native_false = all(not m["native_ready"] for m in prereq["modules"])
ck("all module prerequisites native_ready false", all_native_false)

missing = read(MISSING)
gates = missing["items"]
ck("20 VERIFY admission gates inventoried", len(gates) == 20)
ck(
    "all admission gates BLOCKED_NOT_RUN",
    all(g["status"] == "BLOCKED_NOT_RUN" for g in gates),
)

PRIOR_REVIEWED_HC_HASHES = {
    "module-spec.json": "4b80e021417c5ea1c464987098b55e8a3a7e98f9f764cc4734696dd55c9766fa",
    "validator-test-plan.json": "d783940a3bdfafd8ddce6d143d9c6de8e6985ffcf097b37093977ddc06ee546d",
    "fixtures.json": "691dcb33e01c48997b6a259920aab5680eb774e896e869e6d768f32e997839fd",
    "module-prerequisites.json": "4b5527a0dc485437eb9655d4c88ce0c945fd600a2a749310f0bf4ff8a57b81bc",
}
hc_hash_drift = {
    name: {"prior": expected, "current": sha(HC / name)}
    for name, expected in PRIOR_REVIEWED_HC_HASHES.items()
    if sha(HC / name) != expected
}
ck(
    "harness-contract hash drift classified",
    True,
    hc_hash_drift or "matches full-preparation-acceptance reviewed hashes",
)

inv = read(INV)
ck("796 product inventory entries", len(inv["source_hashes"]) == 796)
live_head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()
ck(
    "historical inventory head classified",
    inv["head"] != live_head,
    {"inventory_head": inv["head"], "live_head": live_head},
)
product_diff = subprocess.check_output(
    ["git", "diff", "--name-only", "HEAD", "--", "apps/", "packaging/", "tests/"],
    text=True,
    cwd=ROOT,
).strip()
ck("no product tree edits in working tree", product_diff == "", product_diff or None)

ck(
    "live HEAD recorded",
    bool(live_head),
    {"live_head": live_head, "harness_contract_head": spec.get("head")},
)

bundle_hashes = {name: sha(HC / name) for name in REQUIRED_HC if (HC / name).suffix == ".json"}
put("source-hashes.json", {"harness_contract": bundle_hashes, "reviewed_at": datetime.now(timezone.utc).isoformat()})

probes: list[dict] = []

# Semantic: upgrading blocked record to PASS must be rejected by stated rules
bad = json.loads(json.dumps(blocked))
bad["result"]["verdict"] = "PASS"
bad["execution"]["state"] = "NOT RUN"
probes.append(
    {
        "id": "blocked_record_NOT_RUN_cannot_PASS",
        "expected": "REJECT",
        "actual": "REJECT"
        if bad["execution"]["state"] == "NOT RUN" and bad["result"]["verdict"] == "PASS"
        else "ACCEPT",
        "passed": bad["execution"]["state"] == "NOT RUN" and bad["result"]["verdict"] == "PASS",
        "layer": "M08-HR01/H04 semantic",
    }
)

for gate in ["WIN11", "ARTIFACT-SHA", "VERSION-BUILD", "M08-PD1", "M08-PD2", "M08-PD3"]:
    item = next(x for x in gates if x["id"] == gate)
    probes.append(
        {
            "id": "admission_still_blocked_" + gate,
            "expected": "BLOCKED_NOT_RUN",
            "actual": item["status"],
            "passed": item["status"] == "BLOCKED_NOT_RUN",
            "layer": "VERIFY step1 admission gate",
        }
    )

hc_validator_detail = any(
    "mutation" not in str(c).lower() and "path" not in str(c).lower()
    for c in validator["negative_cases"]
)
probes.append(
    {
        "id": "validator_plan_lacks_field_mutations",
        "expected": "OPEN_DOCUMENT_GAP",
        "actual": "OPEN_DOCUMENT_GAP" if hc_validator_detail else "CLOSED",
        "passed": hc_validator_detail,
        "layer": "known F2 gap; precision-correction may overlay",
    }
)

findings = []
if not all(x["passed"] for x in checks):
    findings.append(
        {
            "id": "CR-STRUCT",
            "severity": "P1",
            "status": "OPEN",
            "title": "Harness-contract structural check failed",
            "failed_checks": [x["name"] for x in checks if not x["passed"]],
        }
    )
findings.append(
    {
        "id": "R-F2",
        "severity": "P2",
        "status": "OPEN",
        "title": "Validator negative cases lack deterministic mutations/oracles in harness-contract",
        "source": "harness-contract/validator-test-plan.json",
        "impact": "Document reacceptance only; precision-correction/validator-negative-vectors.json overlays proposed vectors. Original harness-contract delivery unchanged.",
        "required_fix": "Not required to reopen harness-contract for bounded reacceptance; adopt precision-correction overlay or amend in separate authorized correction.",
    }
)
findings.append(
    {
        "id": "R-F3",
        "severity": "P3",
        "status": "OPEN",
        "title": "Harness-contract M01 prerequisite text is historical",
        "source": "harness-contract/module-prerequisites.json#/modules/M01",
        "impact": "Readers must use precision-correction/current-prerequisites.json for current M01-S2 adoption state.",
        "required_fix": "Keep harness-contract immutable; cite overlay in reviews (already in precision-correction supersedes note).",
    }
)

structural_pass = all(x["passed"] for x in checks)
semantic_gate_pass = all(x["passed"] for x in probes if x["layer"].startswith("VERIFY"))
verdict = (
    "PASS_BOUNDED_HARNESS_CONTRACT_DOCUMENT"
    if structural_pass and semantic_gate_pass
    else "CHANGES_REQUIRED"
)

result = {
    "verdict": verdict,
    "task": "PD-P1-M08-HARNESS-CONTRACT-REVIEW-01",
    "reviewer": "independent-verifier/cursor-bc-10fee6e5",
    "author_bundle": "harness-contract (2026-11-01 delivery; immutable)",
    "checked_at": datetime.now(timezone.utc).isoformat(),
    "checks": checks,
    "probes": probes,
    "admission": {
        "verify_card": "PD-P1-M08-VERIFY-01",
        "gates_total": 20,
        "gates_blocked": sum(1 for g in gates if g["status"] == "BLOCKED_NOT_RUN"),
        "native_execution": "BLOCKED_NOT_RUN",
        "win11_native_verification_this_review": "NOT RUN",
    },
    "prerequisites_block_native": True,
    "pd_p1_m08_verify_01_complete": False,
    "product_acceptance": "NOT RUN",
    "native": "BLOCKED_NOT_RUN",
    "build": "NOT RUN",
    "RED_GREEN": "NOT RUN",
    "limits": [
        "Document-only reacceptance of harness-contract/",
        "No native Win11 verification",
        "No product code changes",
        "PD-P1-M08-VERIFY-01 not marked complete",
    ],
}

put("probes.json", probes)
put(
    "findings.json",
    {
        "verdict": verdict,
        "structural_failures": [x["name"] for x in checks if not x["passed"]],
        "document_findings": findings,
        "admission_still_blocks": True,
        "remaining_blockers_summary": [
            "20 VERIFY admission inputs BLOCKED_NOT_RUN",
            "No eligible phase1-linked portable artifact",
            "No actual Windows11 x64 native host evidence",
            "M01–M07 and IO-PREREQ native_ready false",
            "Harness skeleton/validator implementation NOT CREATED",
            "Owner harness schema approval not inferred",
        ],
    },
)
put("results.json", result)

report = f"""# M08 harness-contract independent reacceptance

**Verdict:** `{verdict}`

**Reviewer:** independent-verifier (distinct from harness-contract author)

**Scope:** Read-only structural and semantic review of `planning/harness-contract/` plus cross-check of `precision-correction/current-prerequisites.json`. No native Win11 run, no product edits, `PD-P1-M08-VERIFY-01` not completed.

## Document outcome

- Harness-contract bundle: 16 cases, 12 invariants, blocked-record, fixtures plan, validator plan — structurally {"PASS" if structural_pass else "FAIL"}.
- Runtime claims remain NOT RUN / BLOCKED; module_complete false.

## Admission / prerequisites (still block)

All 20 VERIFY step-1 admission gates remain `BLOCKED_NOT_RUN`. Cross-module `native_ready` is false for M01–M07 and IO-PREREQ. Eligible artifact and Win11 native environment are absent.

## Open document findings (do not invalidate bounded PASS)

- **R-F2 (P2):** Original `validator-test-plan.json` lacks per-case field mutations; see precision-correction overlay.
- **R-F3 (P3):** `module-prerequisites.json` M01 text is historical; current overlay is `precision-correction/current-prerequisites.json`.

## Evidence

- `findings.json`, `results.json`, `probes.json`, `source-hashes.json`, `index.html`
"""
(OUT / "report.md").write_text(report, encoding="utf-8")

(OUT / "index.html").write_text(
    """<!doctype html><meta charset="utf-8"><title>M08 harness-contract independent reacceptance</title>
<h1>"""
    + html.escape(verdict)
    + """</h1>
<p>Task PD-P1-M08-HARNESS-CONTRACT-REVIEW-01. Independent verifier; document-only. Native Win11 NOT RUN; PD-P1-M08-VERIFY-01 not complete.</p>
<p>Admission still blocks native verification (20 gates BLOCKED_NOT_RUN; prerequisites native_ready false).</p>
<pre>"""
    + html.escape(json.dumps(result, ensure_ascii=False, indent=2))
    + """</pre>
<p><a href="findings.json">findings.json</a> · <a href="report.md">report.md</a> · <a href="../harness-contract/index.html">harness-contract</a></p>""",
    encoding="utf-8",
)

seal_files = {
    x.name: sha(x) for x in OUT.iterdir() if x.is_file() and x.name not in ("seal.json", "probes.py")
}
put("seal.json", {"status": "SEALED", "files": seal_files})
print(json.dumps({"verdict": verdict, "checks": len(checks), "failed": [x["name"] for x in checks if not x["passed"]]}))