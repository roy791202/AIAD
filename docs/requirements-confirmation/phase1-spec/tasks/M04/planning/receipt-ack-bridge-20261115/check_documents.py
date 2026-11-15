"""Bounded document checks for receipt/ACK mapping. Not product RED or module acceptance."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

D = Path(__file__).resolve().parent
W = next(p for p in D.parents if (p / "AGENTS.md").exists())

PRESERVED = {
    "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/provider-source-map-20261104/module-spec.json": "94b438eb8ec521f3f3dff32955a2513256cac36879ea46c6dbc4a37f2fe723c6",
    "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/provider-source-map-20261104/source-spans.json": "21f49e5ada881d742f816f408447a24c530b855054a0eccb33c539923b7a7d0a",
    "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-retention-observation-proposal/module-spec.json": "a480bed69787d93b6c467251b8dee73fc962c7c765c172bab60488eef9077a07",
    "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-retention-observation-proposal/module.feature": "2bc2027d220c15a7ed97d6e7dba90df830494ca0329bedbf6acbe7246aba28f1",
    "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-response-handoff/module-spec.json": "38e3abd71ef5bcf390a2a903aceac4aee2951df334ab0b0e19f3630af7df3d32",
    "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-response-handoff/module.feature": "5e776e6aefff1b177e39602a4bb2f6e165e8a01f9246f5a18e2fcbcd98fea225",
}

BDD_IDS = [f"M04-ACK-{n}" for n in range(1, 9)]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str):
    return json.loads((D / name).read_text(encoding="utf-8"))


def classify(case: dict) -> str:
    evidence = case["evidence"]
    claim = case["claim"]
    if evidence.get("claims_owner_adoption") or evidence.get("selected_g_non_null"):
        return "REJECT_FALSE_ADOPTION"
    if evidence.get("m05_as_delete_auth") or (
        evidence.get("m05_eligible_for_cleanup")
        and claim in {"delete_authorization", "root_transfer"}
    ):
        return "REJECT_RETENTION_IS_NOT_DELETE_AUTH"
    if evidence.get("replay"):
        return "REJECT_REPLAY"
    captured = evidence.get("captured_revision")
    formal = evidence.get("formal_revision")
    if (
        captured is not None
        and formal is not None
        and captured < formal
        and claim == "semantic_ACK"
    ):
        return "REJECT_NEWER_REVISION"
    if evidence.get("host_write_atomic_path") and claim in {
        "semantic_ACK",
        "Held",
        "root_transfer",
    }:
        return "REJECT_PATH_IS_NOT_ACK"
    if evidence.get("commit_receipt_four_fields") and claim == "semantic_ACK":
        return "REJECT_RECEIPT_IS_NOT_ACK"
    if not evidence.get("issuer") and claim in {"Held", "root_transfer", "semantic_ACK"}:
        return "REJECT_MISSING_ISSUER"
    if claim == "provider_mapping_document" and evidence.get("bridges_pending"):
        return "PASS_DOCUMENT_MAPPING_ONLY"
    return "REJECT_UNMAPPED"


def main() -> None:
    candidate = read("candidate.json")
    pending = read("pending.json")
    fixtures = read("fixtures.json")
    feature = (D / "module.feature").read_text(encoding="utf-8")
    html = (D / "index.html").read_text(encoding="utf-8")
    steps = (D / "steps.py").read_text(encoding="utf-8")

    assert candidate["selected"] is None
    assert candidate["approval"] is None
    assert candidate["valid_red"] == "N/A"
    assert all(g["selected"] is None for g in candidate["owner_gates"])
    assert all(g["selected"] is None for g in candidate["field_bridge_gaps"])
    assert "BDD-19" in candidate["bdd19"] or "complete restoration" in candidate["bdd19"]

    questions = pending["open_questions"]
    assert {q["id"] for q in questions} == {
        "G1",
        "G2",
        "G3",
        "G4",
        "BRIDGE-1",
        "BRIDGE-2",
        "BRIDGE-3",
    }
    assert all(q["selected"] is None for q in questions)
    assert pending["bdd19"]["selected"] is None
    assert pending["bdd19"]["status"] == "UNCHANGED"

    for token in ("Feature:", "Background:", "Rule:", "Scenario:", "Given ", "When ", "Then "):
        assert token in feature, token
    for bdd_id in BDD_IDS:
        assert bdd_id in feature
        assert bdd_id in steps
        assert bdd_id in html
    assert "BDD-19" in feature

    rows = []
    for case in fixtures["cases"]:
        got = classify(case)
        assert got == case["expected"], (case["id"], got, case["expected"])
        rows.append({"id": case["id"], "kind": case["kind"], "observed": got})
    assert [c["id"] for c in fixtures["cases"]] == BDD_IDS
    kinds = {c["kind"] for c in fixtures["cases"]}
    assert {"success", "failure", "boundary", "negative", "negative_false_approval"} <= kinds

    preserved_drift = [p for p, h in PRESERVED.items() if sha(W / p) != h]
    assert not preserved_drift, preserved_drift

    source_hashes = read("source-hashes.json")
    assert source_hashes["preserved_packets"] == PRESERVED
    live_drift = [
        p
        for p, h in source_hashes["packet_files"].items()
        if p != "seal.json" and sha(D / p) != h
    ]
    assert not live_drift, live_drift

    seal = read("seal.json")
    for name, digest in seal["artifacts"].items():
        assert sha(D / name) == digest, name

    embedded = re.search(
        r'<script type="application/json" id="candidate">(.*?)</script>',
        html,
        re.S,
    )
    assert embedded, "candidate embed missing"
    assert json.loads(embedded.group(1)) == candidate

    print(
        json.dumps(
            {
                "status": "PASS_DOCUMENT_MAPPING_ONLY",
                "fixtures": len(rows),
                "rows": rows,
                "preserved_packet_drift": preserved_drift,
                "valid_red": "N/A",
                "not_run": pending["not_run"],
                "independent_review": "NOT RUN",
                "selected_null": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
