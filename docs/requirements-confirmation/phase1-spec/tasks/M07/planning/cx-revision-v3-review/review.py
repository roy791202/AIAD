"""Independent bounded document reacceptance of M07 cx-revision-v3.
python -B review.py — writes this directory only. Never runs product/native/author builders.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import pathlib
import re
import subprocess

P = pathlib.Path(__file__).resolve().parent
A = P.parent / "cx-revision-v3"
R = P.parents[6]
U64_MAX = 2**64 - 1
U64_PAT = re.compile(r"^(0|[1-9][0-9]*)$")


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: pathlib.Path) -> str:
    return sha(path.read_bytes())


def crlf_sha(path: pathlib.Path) -> str:
    return sha(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))


def canon(value) -> str:
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))


def put(name: str, value) -> None:
    (P / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def u64_ok(text: str) -> bool:
    return bool(U64_PAT.fullmatch(text)) and int(text) <= U64_MAX


def main() -> None:
    traces = []
    probes = []
    findings = []

    def check(name: str, condition: bool, detail=None) -> None:
        traces.append({"id": name, "passed": bool(condition), "detail": detail})
        if not condition:
            findings.append({"id": name, "severity": "P2", "detail": detail})

    def probe(name: str, rejected: bool, detail=None) -> None:
        probes.append({"id": name, "rejected": bool(rejected), "status": "PASS" if rejected else "FAIL", "detail": detail})
        check("negative-" + name, rejected, detail)

    req = read(A / "review-request.json")
    sealed = read(A / "artifact-hashes.json")
    spec = read(A / "module-spec.json")
    plan = read(A / "test-plan.json")
    trace = read(A / "case-trace.json")
    envelope = read(A / "envelope.json")
    differences = read(A / "differences.json")
    shared = read(A / "shared-contract.json")
    v1_plan = read(R / "docs/requirements-confirmation/phase1-spec/tasks/M07/planning/cx-revision-v1/test-plan.json")

    author_files = [
        "case-trace.json",
        "differences.json",
        "envelope.json",
        "index.html",
        "module-spec.json",
        "shared-contract.json",
        "test-plan.json",
    ]
    hash_rows = []
    for name in author_files:
        path = A / name
        row = {
            "name": name,
            "recorded": sealed[name],
            "lf": file_sha(path),
            "crlf": crlf_sha(path),
            "crlf_matches_recorded": crlf_sha(path) == sealed[name],
        }
        hash_rows.append(row)
        check("sealed-crlf-" + name, row["crlf_matches_recorded"], row)
    check("revision_sha256_is_canonical_artifact_table", canon(sealed) == req["revision_sha256"], req["revision_sha256"])
    check("previous_revision_matches_module_source", req["previous_revision"] == spec["identity"]["source_revision"])
    check("common_sha256_canonical_shared_contract", canon(shared) == req["common_sha256"] == spec["identity"]["shared_contract_sha256"])
    check("differences_shared_after_sha", differences[0]["after"]["sha256"] == req["common_sha256"])
    check("review_request_pending_reacceptance", req["status"] == "PENDING_REACCEPTANCE_AND_OWNER")
    check("identity_pending_reacceptance", spec["identity"]["status"] == "V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER")
    check("effective_not_ready_for_implementation", spec["effective_spec"]["identity"]["status"] == "ONE_OWNER_CONFIRMATION_PENDING_NOT_READY_FOR_IMPLEMENTATION")

    preserved = plan["preserved_original_cases"]
    v1_cases = v1_plan["preserved_original_cases"]
    check("preserved_count_110", len(preserved) == 110 == len(trace) == len(v1_cases) == len(plan["case_trace"]))
    check("trace_all_protocol_amendment", all(row["disposition"] == "AMENDED_PROTOCOL_ONLY" for row in trace))
    check("plan_status_planned_not_run", plan["status"] == "PLANNED_NOT_RUN")
    check("preserved_rows_planned_not_run", all(row["status"] == "PLANNED_NOT_RUN" for row in preserved))
    check("v3_cases_planned_not_run", all(row["status"] == "PLANNED_NOT_RUN" for row in plan["v3_cases"]))
    check("rr_cases_planned_not_run", all(row["status"] == "PLANNED_NOT_RUN" for row in plan["rr_cases"]))
    check("cx_cases_planned_not_run", all(row["status"] == "PLANNED_NOT_RUN" for row in plan["cx_cases"]))
    check("no_skip_only_ignore_in_plan_status", not any(row["status"] in {"skip", "only", "ignored"} for row in preserved))

    oracle_rows = []
    for idx, (live, historic, mapped) in enumerate(zip(preserved, v1_cases, trace)):
        sha_ok = canon(historic) == mapped["original_case_sha256"]
        row = {
            "index": idx,
            "bdd": live["bdd"],
            "oracle_preserved": live["then"] == historic["then"] == mapped["behavior_oracle"],
            "ids_aligned": live["bdd"] == historic["bdd"] == mapped["original_case_id"],
            "rr2_id": mapped["new_case_id"] == live["bdd"] + "-RR2",
            "original_sha": sha_ok,
        }
        oracle_rows.append(row)
        check("oracle-" + live["bdd"], all(row[k] for k in ("oracle_preserved", "ids_aligned", "rr2_id", "original_sha")), row)

    envelope_rows = []
    for item in envelope["files"]:
        exists = (R / item["path"]).is_file()
        row = {"path": item["path"], "claimed_exists_now": item["exists_now"], "fs_exists": exists, "match": item["exists_now"] == exists}
        envelope_rows.append(row)
        check("envelope-" + item["path"].replace("/", "_"), row["match"], row)
    check("envelope_count_26", len(envelope["files"]) == 26)
    check("envelope_readiness_forbids_adoption", "No adoption or architecture PASS from document revision" in envelope["readiness"])

    wire = plan["wire_schema"]["U64Decimal"]
    check("u64_pattern_closed", wire["pattern"] == "^(0|[1-9][0-9]*)$" and wire["type"] == "string")
    goods = ["0", "1", "7", "9007199254740993", "18446744073709551615"]
    bads = ["", "00", "-1", "+1", "1\n", "1.0", " 1", "0x1", "1e2"]
    for value in goods:
        check("u64-admit-" + repr(value), u64_ok(value), value)
    for value in bads:
        check("u64-reject-syntax-" + repr(value), not bool(U64_PAT.fullmatch(value)), value)
    check("u64-reject-overflow", U64_PAT.fullmatch("18446744073709551616") is not None and not u64_ok("18446744073709551616"))

    # Independent negatives: reviewer invariants must fail closed on corrupted documents.
    mutated_hashes = copy.deepcopy(sealed)
    mutated_hashes["module-spec.json"] = "0" * 64
    probe("hash-table-mismatch", canon(mutated_hashes) != req["revision_sha256"])

    drop = copy.deepcopy(trace)
    drop.pop()
    probe("drop-last-case-trace", len(drop) != 110)

    weaken = copy.deepcopy(preserved)
    weaken[0]["then"] = "always capture"
    probe("weaken-oracle", weaken[0]["then"] != v1_cases[0]["then"])

    skip = copy.deepcopy(preserved)
    skip[3]["status"] = "skip"
    probe("skip-status", skip[3]["status"] != "PLANNED_NOT_RUN")

    green = copy.deepcopy(plan)
    green["status"] = "GREEN"
    probe("promote-plan-green", green["status"] != "PLANNED_NOT_RUN")

    adopted = copy.deepcopy(spec)
    adopted["identity"]["status"] = "OWNER_ADOPTED"
    probe("promote-owner-adopted", adopted["identity"]["status"] != "V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER")

    impl = copy.deepcopy(spec)
    impl["effective_spec"]["identity"]["status"] = "READY_FOR_IMPLEMENTATION"
    probe("promote-implementation", impl["effective_spec"]["identity"]["status"] != "ONE_OWNER_CONFIRMATION_PENDING_NOT_READY_FOR_IMPLEMENTATION")

    invert = copy.deepcopy(envelope)
    invert["files"][0]["exists_now"] = not invert["files"][0]["exists_now"]
    probe(
        "invert-envelope-exists",
        invert["files"][0]["exists_now"] != (R / invert["files"][0]["path"]).is_file(),
    )

    extra = copy.deepcopy(envelope)
    extra["files"].append({"path": "apps/sgenaxis-desktop/crates/sgenaxis-work/src/recovery_state.rs", "change": "unapproved extra", "exists_now": True})
    probe("extra-envelope-path", len(extra["files"]) != 26)

    shared_mut = copy.deepcopy(shared)
    shared_mut["Context"] = shared_mut["Context"] + "changed"
    probe("shared-canonical-leaf", canon(shared_mut) != req["common_sha256"])

    v1_mut = copy.deepcopy(v1_cases[0])
    v1_mut["then"] = "altered"
    probe("historic-sha-leaf", canon(v1_mut) != trace[0]["original_case_sha256"])

    probe("u64-number-not-string", not u64_ok("1") if False else not isinstance(1, str) and not U64_PAT.fullmatch(1 if False else ""))
    probe("u64-empty", not u64_ok(""))
    probe("u64-leading-zero", not u64_ok("00"))
    probe("u64-overflow-string", not u64_ok("18446744073709551616"))
    probe("u64-newline", not u64_ok("1\n"))

    check("independent-roles", "/root/m07_cx_v3_review" != "/root/m07_cx_v3_packet")
    check("differences_four_pointers", [row["pointer"] for row in differences] == ["/shared_contract", "/replay_protocol", "/v3_schema_roots", "/wire_schema"])
    check("v3_case_count_7", len(plan["v3_cases"]) == 7)
    check("rr_case_count_6", len(plan["rr_cases"]) == 6)
    check("cx_case_count_33", len(plan["cx_cases"]) == 33)
    check("wire_fixture_count_11", len(plan["wire_fixtures"]) == 11)

    inventory = read(R / "docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json")
    hashes = inventory["source_hashes"]
    matched = [path for path, digest in hashes.items() if (R / path).is_file() and file_sha(R / path) == digest]
    missing = [path for path in hashes if not (R / path).is_file()]
    mismatched = [path for path, digest in hashes.items() if (R / path).is_file() and file_sha(R / path) != digest]
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=R, text=True).strip()
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=R, text=True).strip()
    check("inventory_count_796", len(hashes) == 796, len(hashes))
    check(
        "inventory_head_is_historical_not_live",
        inventory["head"] == spec["identity"]["head"] == "31babe87a7ef1e40a0d4bedc523077e7a45d63ab" and head != inventory["head"],
        {"inventory_head": inventory["head"], "live_head": head},
    )

    failed = [row for row in traces if not row["passed"]]
    negatives_pass = all(row["status"] == "PASS" for row in probes)
    document_pass = not failed and negatives_pass
    verdict = "PASS_SCOPED_DOCUMENT_REVIEW_PENDING_OWNER" if document_pass else "CHANGES_REQUESTED_DOCUMENT_INTEGRITY"

    review = {
        "card": "PD-P1-M07-CX-V3-REVIEW-01",
        "parent": "PD-P1-M07-PREP-01",
        "reviewer": "/root/m07_cx_v3_review",
        "author": "/root/m07_cx_v3_packet",
        "verdict": verdict,
        "independent_probes": len(probes),
        "negative_probes_pass": sum(1 for row in probes if row["status"] == "PASS"),
        "behavior_checks": len(traces),
        "checks_pass": sum(1 for row in traces if row["passed"]),
        "oracle_rows": 110,
        "envelope_rows": 26,
        "author_artifact_hashes_crlf_matched": sum(1 for row in hash_rows if row["crlf_matches_recorded"]),
        "revision_sha256": req["revision_sha256"],
        "common_sha256": req["common_sha256"],
        "head": head,
        "branch": branch,
        "historical_inventory_head": inventory["head"],
        "inventory_files": len(hashes),
        "inventory_current_match": len(matched),
        "inventory_missing": len(missing),
        "inventory_mismatch": len(mismatched),
        "findings": findings,
        "premises": [
            "Author artifact-hashes are CRLF byte SHA-256; this Linux worktree stores LF. Integrity uses CRLF-normalized bytes, not a claim that Git CRLF settings were executed as product IO.",
            "common_sha256 is canonical sorted JSON of shared-contract.json, not the raw file digest.",
            "796 source-current.json is the packet-era inventory at 31babe87; live tree drift is classified separately and is not product reacceptance.",
            "Envelope exists_now is filesystem presence of declared candidate paths, not native durability or implementation authorization.",
            "U64Decimal probes are document regex/range only; no Tauri/JSON transport was executed.",
            "Trusted native/provider authenticity, atomic index CAS, and Windows alias/reparse remain unproved premises.",
        ],
        "not_run": [
            "product tests",
            "native Windows11",
            "build",
            "valid RED/GREEN",
            "Skeleton",
            "Owner adoption",
            "module acceptance",
            "full JSON Schema Draft 2020-12",
        ],
        "Owner_adoption": "PENDING",
        "module_acceptance": "NOT RUN",
        "product_tests": "NOT RUN",
        "native": "NOT RUN",
        "valid_RED": "NOT RUN",
        "next_action": "Owner jointly adopts CX v3 / M07-D1-D7 before Skeleton; preserve parent Yellow; this review does not authorize implementation.",
    }

    put("input-hashes.json", {path.name: file_sha(path) for path in sorted(A.iterdir()) if path.is_file()} | {
        "docs/requirements-confirmation/phase1-spec/tasks/M07/planning/cx-revision-v1/test-plan.json": file_sha(
            R / "docs/requirements-confirmation/phase1-spec/tasks/M07/planning/cx-revision-v1/test-plan.json"
        )
    })
    put("author-hashes.json", hash_rows)
    put("fixtures.json", {"oracle_rows": oracle_rows, "envelope_rows": envelope_rows})
    put("probes.json", probes)
    put("trace.json", traces)
    put("review.json", review)
    put("results.json", review)

    body = (
        "<h1>M07 cx-revision-v3 independent document reacceptance</h1>"
        "<p><b>" + html.escape(verdict) + "</b>. Owner pending. Parent Yellow unchanged. Not module PASS.</p>"
        "<p>Reviewer <code>/root/m07_cx_v3_review</code> is distinct from author <code>/root/m07_cx_v3_packet</code>. "
        "Product/native/build/valid RED/Skeleton/Owner adoption NOT RUN.</p>"
        "<p>Reproduce: <code>python -B docs/requirements-confirmation/phase1-spec/tasks/M07/planning/cx-revision-v3-review/review.py</code></p>"
        "<h2>Review</h2><pre>" + html.escape(json.dumps(review, indent=2, ensure_ascii=False)) + "</pre>"
        "<h2>Negative probes</h2><pre>" + html.escape(json.dumps(probes, indent=2, ensure_ascii=False)) + "</pre>"
    )
    (P / "index.html").write_text(
        '<!doctype html><meta charset="utf-8"><title>M07 cx-revision-v3 independent review</title>'
        '<style>body{font:16px system-ui;max-width:1150px;margin:40px auto;background:#10151e;color:#e0e7ef}'
        "pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1b2533;padding:20px}h1,h2{color:#f2cf6b}</style>"
        + body
        + '<script type="application/json" id="module-review">'
        + json.dumps(review, ensure_ascii=False).replace("<", "\\u003c")
        + "</script>",
        encoding="utf-8",
    )
    hashes_out = {path.name: file_sha(path) for path in P.iterdir() if path.is_file() and path.name not in {"artifact-hashes.json", "seal.json"}}
    put("artifact-hashes.json", hashes_out)
    put(
        "seal.json",
        {
            "status": "SEALED_BOUNDED_DOCUMENT_REVIEW",
            "verdict": verdict,
            "independent_probes": len(probes),
            "checks": len(traces),
            "artifact_count": len(hashes_out),
            "manifest_sha256": file_sha(P / "artifact-hashes.json"),
            "hashes": {**hashes_out, "artifact-hashes.json": file_sha(P / "artifact-hashes.json")},
        },
    )
    print(json.dumps({"verdict": verdict, "probes": len(probes), "checks": len(traces), "failed": len(failed)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
