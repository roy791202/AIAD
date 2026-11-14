"""Independent bounded document review of cx-exchange-revision-v3.

python -B review.py
Writes this directory only. Does not rewrite the candidate packet, product,
Skeleton, tests, or board Blue/Done. Does not run product/native/build/RED.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import pathlib
import re
import subprocess
import sys

sys.dont_write_bytecode = True

P = pathlib.Path(__file__).resolve().parent
C = P.parent / "cx-exchange-revision-v3"
V2 = P.parent / "cx-exchange-revision-v2"
ROOT = next(x for x in P.parents if (x / "AGENTS.md").exists())


def read(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(name: str, value) -> None:
    (P / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def compact_sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def ck(checks: list, name: str, ok: bool, detail: str) -> None:
    checks.append({"id": name, "pass": bool(ok), "detail": detail})


def main() -> None:
    before_candidate = {p.name: sha(p) for p in C.iterdir() if p.is_file()}
    req = read(C / "review-request.json")
    spec = read(C / "module-spec.json")
    env = read(C / "envelope.json")
    plan = read(C / "test-plan.json")
    trace = read(C / "case-trace.json")
    diffs = read(C / "differences.json")
    shared = read(C / "shared-contract.json")
    declared = read(C / "artifact-hashes.json")
    v2req = read(V2 / "review-request.json")
    index_text = (C / "index.html").read_text(encoding="utf-8")
    packet_blob = "\n".join(p.read_text(encoding="utf-8") for p in sorted(C.iterdir()) if p.is_file())
    checks: list = []
    findings: list = []

    hashed_names = [
        "case-trace.json",
        "differences.json",
        "envelope.json",
        "index.html",
        "module-spec.json",
        "shared-contract.json",
        "test-plan.json",
    ]
    live = {name: sha(C / name) for name in hashed_names}
    live["artifact-hashes.json"] = sha(C / "artifact-hashes.json")
    live["review-request.json"] = sha(C / "review-request.json")
    hash_mismatches = {n: {"declared": declared.get(n), "live": live[n]} for n in hashed_names if declared.get(n) != live[n]}
    ck(
        checks,
        "C16_declared_hashes_vs_live",
        not hash_mismatches,
        "All seven declared artifact hashes match live SHA-256"
        if not hash_mismatches
        else f"{len(hash_mismatches)} declared hashes mismatch live bytes",
    )
    if hash_mismatches:
        findings.append(
            {
                "id": "F-SEAL-HASH-DRIFT",
                "severity": "DOCUMENT_INTEGRITY",
                "blocks_owner_adoption": False,
                "blocks_claim_bound_pass": False,
                "text": "artifact-hashes.json lists seven files whose declared SHA-256 do not match current bytes. Review used live hashes. Stale seal is not Owner adoption, Skeleton, RED/GREEN, native, or a product edit.",
                "mismatches": hash_mismatches,
            }
        )

    computed_revision = compact_sha(declared)
    ck(
        checks,
        "C14_revision_binds_declared_manifest",
        req.get("revision_sha256") == computed_revision,
        "review-request.revision_sha256 equals SHA256 of sorted compact declared artifact-hashes.json",
    )
    ck(
        checks,
        "C1_review_request_status",
        req.get("status") == "PENDING_REACCEPTANCE_AND_OWNER",
        "review-request.json status is PENDING_REACCEPTANCE_AND_OWNER",
    )
    ck(
        checks,
        "C2_identity_status",
        spec.get("identity", {}).get("status") == "V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER",
        "module-spec identity.status is V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER",
    )
    ck(
        checks,
        "C3_previous_revision_binds_v2",
        req.get("previous_revision") == v2req.get("revision_sha256"),
        f"v3 previous_revision {req.get('previous_revision')} equals v2 review-request.revision_sha256",
    )
    ck(
        checks,
        "C4_envelope_still_candidate",
        env.get("status") == "RR_REVISED_CANDIDATE_PENDING_OWNER"
        and any("No adoption or architecture PASS from document revision" in x for x in env.get("readiness", [])),
        "envelope.json status RR_REVISED_CANDIDATE_PENDING_OWNER; readiness forbids adoption from document revision",
    )
    ck(
        checks,
        "C5_index_disclaimer",
        "待另輪唯讀複驗與 Owner 一次採納" in index_text
        and "未建立 Skeleton" in index_text
        and "未改產品" in index_text
        and "NOT RUN" in index_text,
        "v3 index.html states candidate delivery, pending reacceptance and Owner, no Skeleton/product, NOT RUN",
    )
    adopted_fact = bool(
        re.search(r"OWNER_ADOPTED|ADOPTED_BY_OWNER|\bOwner adopted\b", packet_blob)
        and "PENDING_REACCEPTANCE" not in packet_blob
    )
    ck(
        checks,
        "C6_no_owner_adopted_fact",
        "OWNER_ADOPTED" not in packet_blob
        and "ADOPTED_BY_OWNER" not in packet_blob
        and "Owner adopted" not in packet_blob,
        "Zero matches for Owner adopted / OWNER_ADOPTED / ADOPTED_BY_OWNER",
    )
    ck(checks, "C6b_no_false_adopted_fact", not adopted_fact, "No unscoped Owner-adopted fact sentence")
    ck(
        checks,
        "C7_no_skeleton_established",
        "未建立 Skeleton" in index_text
        and spec["effective_spec"]["architecture"]["approval"].endswith("no Skeleton.")
        and "NOT_READY_FOR_IMPLEMENTATION" in spec["effective_spec"]["identity"]["status"],
        "No Skeleton created/accepted. Approval text pending Owner; no Skeleton.",
    )
    planned = plan.get("status") == "PLANNED_NOT_RUN"
    orig = plan.get("preserved_original_cases", [])
    v3cases = plan.get("v3_cases") or plan.get("new_cases") or []
    if not v3cases:
        for key, val in plan.items():
            if isinstance(val, list) and val and isinstance(val[0], dict) and str(val[0].get("id", "")).startswith("V3-BDD"):
                v3cases = val
                break
    all_orig_planned = orig and all(x.get("status") == "PLANNED_NOT_RUN" for x in orig)
    ck(
        checks,
        "C8_no_product_red_green_claim",
        planned and all_orig_planned and "NOT_READY_FOR_IMPLEMENTATION" in spec["effective_spec"].get("module_readiness", ""),
        "test-plan coverage PLANNED_NOT_RUN; module_readiness NOT_READY_FOR_IMPLEMENTATION",
    )
    ck(
        checks,
        "C9_no_native_pass",
        any("environment NOT RUN remains" in x for x in env.get("readiness", []))
        and "native PASS" not in packet_blob
        and "Native PASS" not in packet_blob,
        "No native PASS. Native Windows11 gate remains environment NOT RUN.",
    )
    files = env.get("files", [])
    exists_ok = True
    existence = []
    for row in files:
        path = ROOT / row["path"]
        present = path.is_file()
        declared_now = bool(row.get("exists_now"))
        existence.append({"path": row["path"], "declared_exists_now": declared_now, "present": present})
        if present != declared_now:
            exists_ok = False
    ck(
        checks,
        "C10_envelope_paths_existence_matches_declared",
        exists_ok,
        "envelope exists_now flags match current filesystem (read-only inspection)",
    )
    ck(
        checks,
        "C10b_envelope_protects_product",
        str(env.get("protected", "")).startswith("All current product code during this planning task"),
        "envelope protects all current product code during this planning task",
    )
    decisions = spec["effective_spec"]["decisions"]
    ck(
        checks,
        "C11_x1_x7_pending_owner",
        [d["id"] for d in decisions] == [f"M06-X{i}" for i in range(1, 8)]
        and all(d.get("status") == "PENDING_OWNER" for d in decisions),
        "M06-X1..X7 remain PENDING_OWNER",
    )
    ck(
        checks,
        "C12_bdd19_and_mh_absent",
        "BDD-19" not in packet_blob and "BDD19" not in packet_blob and "MH1" not in packet_blob,
        "v3 packet has no BDD-19 / MH1-6 resolution. Parent UNDECIDED/pending unchanged.",
    )
    v2_names = {p.name for p in V2.iterdir() if p.is_file()}
    v3_names = {p.name for p in C.iterdir() if p.is_file()}
    ck(
        checks,
        "C13_v2_compare_packaging",
        v2req.get("status") == "ONE_OWNER_CONFIRMATION_PENDING"
        and req.get("status") == "PENDING_REACCEPTANCE_AND_OWNER"
        and {"module.feature", "fixtures.json", "step-definition-plan.json"} <= v2_names
        and not ({"module.feature", "fixtures.json", "step-definition-plan.json"} & v3_names),
        "v3 vs v2: status ONE_OWNER_CONFIRMATION_PENDING → PENDING_REACCEPTANCE_AND_OWNER; v3 omits module.feature/fixtures.json/step-definition-plan.json",
    )
    live_shared = sha(C / "shared-contract.json")
    common_match_live = req.get("common_sha256") == live_shared
    common_match_declared = req.get("common_sha256") == declared.get("shared-contract.json")
    identity_common = spec.get("identity", {}).get("shared_contract_sha256") == req.get("common_sha256")
    ck(
        checks,
        "C17_common_sha_vs_live_shared",
        common_match_live,
        f"review-request.common_sha256 {req.get('common_sha256')} vs live shared-contract {live_shared}",
    )
    ck(
        checks,
        "C17b_common_sha_three_way_split",
        (not common_match_live)
        and (req.get("common_sha256") != declared.get("shared-contract.json"))
        and identity_common,
        "common_sha256 equals identity.shared_contract_sha256, matches neither live nor declared shared-contract.json file hash",
    )
    ck(
        checks,
        "C17c_identity_repeats_declared_common",
        identity_common,
        "module-spec identity.shared_contract_sha256 repeats review-request.common_sha256",
    )
    if not common_match_live:
        findings.append(
            {
                "id": "F-COMMON-SHA-DRIFT",
                "severity": "DOCUMENT_INTEGRITY",
                "blocks_owner_adoption": False,
                "blocks_claim_bound_pass": False,
                "text": "review-request.common_sha256 equals identity.shared_contract_sha256 but matches neither live shared-contract.json nor the declared artifact-hashes shared-contract.json entry. Three-way split is not Owner adoption.",
                "request_common": req.get("common_sha256"),
                "declared_shared_file": declared.get("shared-contract.json"),
                "live": live_shared,
            }
        )
    ck(
        checks,
        "C18_case_trace_oracles_retained",
        isinstance(trace, list)
        and len(trace) == 100
        and all(x.get("disposition") == "AMENDED_PROTOCOL_ONLY" for x in trace)
        and all("no assertion deletion/weakening" in x.get("expectation_rule", "") for x in trace)
        and all(x.get("superseded_by") is None for x in trace),
        "100 case-trace rows AMENDED_PROTOCOL_ONLY; original observable oracles retained; none superseded",
    )
    ck(
        checks,
        "C18b_test_plan_status_not_run",
        plan.get("status") == "PLANNED_NOT_RUN" and len(orig) == 100,
        f"test-plan status PLANNED_NOT_RUN with {len(orig)} preserved original cases",
    )
    ck(
        checks,
        "C19_shared_contract_status_pending",
        shared.get("status") == "PROPOSED_PENDING_OWNER_AND_READONLY_REACCEPTANCE"
        and "Only after Owner adoption" in shared.get("precedence", ""),
        "shared-contract status remains proposed pending Owner and readonly reacceptance",
    )
    ck(
        checks,
        "C19b_differences_pending",
        isinstance(diffs, list)
        and diffs
        and diffs[0].get("pointer") == "/shared_contract"
        and "PROPOSED" in json.dumps(diffs[0].get("after", {}), ensure_ascii=False),
        "differences.json first overlay is /shared_contract still proposed",
    )

    auth_path = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json"
    auth = read(auth_path)["source_hashes"]
    missing = [n for n in auth if not (ROOT / n).exists()]
    mismatch = [n for n, h in auth.items() if (ROOT / n).exists() and sha(ROOT / n) != h]
    drift = missing + mismatch
    ck(
        checks,
        "C20_796_authority_inventory",
        len(auth) == 796,
        f"authority inventory has 796 entries; current tree observed missing={len(missing)} mismatch={len(mismatch)}; freeze is historical, not this packet's adoption proof",
    )

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    historical = spec.get("identity", {}).get("head")
    ck(checks, "C21_historical_head_not_claimed_live", historical != head, f"live HEAD {head} differs from packet historical head {historical}")

    after_candidate = {p.name: sha(p) for p in C.iterdir() if p.is_file()}
    ck(checks, "C15_candidate_unchanged", before_candidate == after_candidate, "review did not rewrite v3 candidate files")

    def semantic_ok(d: dict) -> bool:
        ident = d.get("identity", {})
        ef = d.get("effective_spec", {})
        dec = ef.get("decisions", [])
        env_l = ef.get("envelope", {})
        approval = ef.get("architecture", {}).get("approval", "")
        return (
            ident.get("status") == "V3_CANDIDATE_PENDING_REACCEPTANCE_AND_OWNER"
            and ef.get("identity", {}).get("status") == "ONE_OWNER_CONFIRMATION_PENDING_NOT_READY_FOR_IMPLEMENTATION"
            and all(x.get("status") == "PENDING_OWNER" for x in dec)
            and env_l.get("status") == "RR_REVISED_CANDIDATE_PENDING_OWNER"
            and "NOT_READY_FOR_IMPLEMENTATION" in ef.get("module_readiness", "")
            and "no Skeleton" in approval
        )

    ck(checks, "C22_semantic_boundaries", semantic_ok(spec), "identity/decisions/envelope/readiness remain candidate-pending")

    probes = []
    mutations = [
        ("owner_adopted", lambda d: d["identity"].update(status="OWNER_ADOPTED"), "v3 means Owner adopted the CX exchange revision"),
        ("skeleton_created", lambda d: d["effective_spec"]["architecture"].update(approval="Skeleton accepted"), "v3 established or accepted a Skeleton"),
        ("ready_for_implementation", lambda d: d["effective_spec"]["identity"].update(status="READY_FOR_IMPLEMENTATION"), "v3 is READY_FOR_IMPLEMENTATION"),
        ("x1_adopted", lambda d: d["effective_spec"]["decisions"][0].update(status="ADOPTED"), "v3 adopts M06-X1"),
        ("envelope_applied", lambda d: d["effective_spec"]["envelope"].update(status="APPLIED_TO_PRODUCT"), "v3 already applied envelope to product"),
    ]
    for name, mut, claim in mutations:
        d = copy.deepcopy(spec)
        mut(d)
        rejected = not semantic_ok(d)
        probes.append({"id": name, "claim": claim, "rejected": rejected})
        ck(checks, "negative:" + name, rejected, claim)

    text_probes = [
        ("valid_red_pass", "v3 is valid RED / TDD_PASS", plan.get("status") == "PLANNED_NOT_RUN"),
        ("product_green", "v3 product GREEN", "No product RED/GREEN" in index_text or "NOT RUN" in index_text),
        ("native_pass", "v3 native Windows11 measured PASS", any("environment NOT RUN remains" in x for x in env.get("readiness", []))),
        ("product_edits", "v3 already edited product/tests", str(env.get("protected", "")).startswith("All current product code")),
        ("bdd19_narrowed_or_decided", "v3 decides BDD-19 full restoration vs deferred retention", "BDD-19" not in packet_blob),
        ("mh1_6_adopted", "v3 adopts Owner MH1-6", "MH1" not in packet_blob),
        ("hash_drift_is_adoption", "stale artifact-hashes.json implies a new adopted seal", req.get("status") == "PENDING_REACCEPTANCE_AND_OWNER"),
        ("common_sha_live_is_adoption", "common_sha256 mismatch is Owner adoption", req.get("status") == "PENDING_REACCEPTANCE_AND_OWNER"),
        ("oracle_weakening", "protocol amendment deletes original oracles", all("no assertion deletion/weakening" in x.get("expectation_rule", "") for x in trace)),
        ("union_envelope", "candidate envelope is blanket union authorization", "並非 union 授權" in index_text),
    ]
    for name, claim, rejected in text_probes:
        probes.append({"id": name, "claim": claim, "rejected": bool(rejected)})
        ck(checks, "negative:" + name, rejected, claim)

    claim_bound_pass = all(
        x["pass"]
        for x in checks
        if x["id"]
        not in {
            "C16_declared_hashes_vs_live",
            "C17_common_sha_vs_live_shared",
        }
    )
    status = (
        "PASS_SCOPED_DOCUMENT_REVIEW_PENDING_OWNER"
        if claim_bound_pass
        else "FAIL_SCOPED_DOCUMENT_REVIEW"
    )

    board_card = "PD-P1-M06-CX-EXCHANGE-V3-REVIEW-01"
    board_note = (
        "THIS review card is not present in docs/board.json; parent PD-P1-M06-PREP-01 left Yellow/In Progress unchanged. "
        "No Blue/Done. Optional note skipped because the named card does not exist."
    )

    result = {
        "card": board_card,
        "parent": "PD-P1-M06-PREP-01",
        "parent_light_untouched": "Yellow",
        "reviewer": "independent-document-reviewer-cx-exchange-v3-20261114",
        "author": "cx-exchange-revision-v3-author (not this reviewer)",
        "status": status,
        "packet_status_unchanged": "PENDING_REACCEPTANCE_AND_OWNER",
        "Owner_adoption": "PENDING",
        "skeleton": "NOT AUTHORIZED / NOT CLAIMED",
        "product_tests": "NOT RUN",
        "compile": "NOT RUN",
        "valid_RED": "NOT RUN",
        "GREEN": "NOT RUN",
        "native": "NOT RUN",
        "build": "NOT RUN",
        "module_acceptance": "NOT RUN",
        "FileCommit": "N/A",
        "ACK": "N/A",
        "product_edits_this_review": False,
        "candidate_unchanged": before_candidate == after_candidate,
        "live_sha256": live,
        "declared_artifact_hashes": declared,
        "revision_sha256_declared_manifest": computed_revision,
        "revision_sha256_request": req.get("revision_sha256"),
        "common_sha256_request": req.get("common_sha256"),
        "common_sha256_live_shared": live_shared,
        "previous_revision": req.get("previous_revision"),
        "v2_revision_sha256": v2req.get("revision_sha256"),
        "independent_probes": len(probes),
        "checks": checks,
        "passed": sum(x["pass"] for x in checks),
        "failed": sum(not x["pass"] for x in checks),
        "new_negative_probes": probes,
        "findings": findings,
        "envelope_existence": existence,
        "authority_count": len(auth),
        "authority_drift_count": len(drift),
        "authority_missing_count": len(missing),
        "authority_mismatch_count": len(mismatch),
        "HEAD": head,
        "historical_head": historical,
        "case_trace_rows": len(trace),
        "preserved_original_cases": len(orig),
        "board_note": board_note,
        "known_parent_notes": {
            "merge_record_consistency": "PASS_DOCUMENT_SCOPE (historical; not re-run)",
            "BDD19_vs_deferred_retention": "UNDECIDED",
            "Owner_MH1_6": "pending",
        },
        "limits": [
            "Static source/document review only",
            "Product/native/build/valid RED NOT RUN",
            "Historical PASS not rerun",
            "No decisions adopted",
            "Declared artifact-hashes and common_sha256 are stale versus live bytes",
        ],
        "verdict": (
            status
            + ". Claim probes all rejected. Keep PENDING_REACCEPTANCE_AND_OWNER. "
            "Do not set Owner adopted. Do not authorize Skeleton/RED/GREEN/native/product edits. "
            "Open findings: declared artifact-hashes.json drift versus live bytes; common_sha256 binds stale shared-contract hash."
        ),
    }
    put("results.json", result)

    failed_ids = [x["id"] for x in checks if not x["pass"]]
    rows = "".join(
        f"<tr><td>{html.escape(x['id'])}</td><td class=\"{'pass' if x['pass'] else 'fail'}\">{'PASS' if x['pass'] else 'FAIL'}</td><td>{html.escape(x['detail'])}</td></tr>"
        for x in checks
    )
    probe_rows = "".join(
        f"<tr><td>{html.escape(x['id'])}</td><td>{'yes' if x['rejected'] else 'NO'}</td><td>{html.escape(x['claim'])}</td></tr>"
        for x in probes
    )
    finding_html = "".join(f"<li><strong>{html.escape(f['id'])}</strong>: {html.escape(f['text'])}</li>" for f in findings)
    body = f"""<!doctype html>
<html lang="zh-Hant">
<meta charset="utf-8">
<title>M06 cx-exchange-revision-v3 獨立受限文件複驗</title>
<style>
body{{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6;color:#193143}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:16px}}
table{{border-collapse:collapse;width:100%}}
td,th{{padding:8px;border:1px solid #ccc;text-align:left;vertical-align:top}}
.pass{{color:#0a6}}
.fail{{color:#b00}}
</style>
<h1>M06 cx-exchange-revision-v3 獨立受限文件複驗</h1>
<p><strong>Verdict: {html.escape(status)}</strong></p>
<p>卡 <code>{html.escape(board_card)}</code>。審查者 <code>independent-document-reviewer-cx-exchange-v3-20261114</code>，不是 v3 撰寫者，也不是產品實作者。未改 Rust/TS/產品測試、未改 v3 候選檔。未把 Owner 設為已採納。候選包狀態維持 <code>PENDING_REACCEPTANCE_AND_OWNER</code>。</p>
<p>對照：<a href="../cx-exchange-revision-v3/index.html">v3 候選</a> · <a href="../cx-exchange-revision-v2/index.html">v2</a> · <a href="results.json">results.json</a></p>
<p>產品／compile／valid RED／GREEN／native／build：<strong>NOT RUN</strong>。Skeleton：<strong>NOT AUTHORIZED</strong>。Owner_adoption：<strong>PENDING</strong>。</p>
<p>母卡 PD-P1-M06-PREP-01 維持 Yellow；本審查未改其燈號或 Done。named review card 不在 board.json，故未寫看板備註。</p>
<h2>已知母卡狀態（不重跑）</h2>
<ul>
<li>merge record consistency 文件受限 PASS（歷史，本輪未重跑）</li>
<li>BDD-19 完整恢復 vs deferred retention：<strong>UNDECIDED</strong>（v3 未裁決）</li>
<li>Owner MH1–6：<strong>pending</strong>（v3 未採納）</li>
</ul>
<h2>雜湊對照</h2>
<ul>
<li>revision_sha256 等於宣告 artifact-hashes 的 compact SHA（<code>{html.escape(computed_revision)}</code>）</li>
<li>previous_revision 綁定 v2 revision_sha256</li>
<li>七檔宣告 SHA 與 live bytes <strong>不符</strong>（F-SEAL-HASH-DRIFT）</li>
<li>common_sha256 綁定宣告 shared-contract，<strong>不是</strong> live shared-contract.json（F-COMMON-SHA-DRIFT）</li>
</ul>
<h2>Findings</h2>
<ul>{finding_html}</ul>
<h2>Checks</h2>
<p>{result['passed']} PASS / {result['failed']} FAIL。Claim-bound 排除完整性 C16/C17 後仍為 scoped PASS。Failed ids: {html.escape(', '.join(failed_ids) or 'none')}。</p>
<table><tr><th>ID</th><th>結果</th><th>說明</th></tr>{rows}</table>
<h2>Negative probes（應全部 rejected）</h2>
<table><tr><th>Probe</th><th>Rejected</th><th>主張</th></tr>{probe_rows}</table>
<h2>下一步</h2>
<p>Owner 對<strong>現檔 live SHA</strong> 做一次採納仍未發生。重封 artifact-hashes.json 是文件衛生，不是進度。不得據此開 Skeleton 或產品實作。Reproduce: <code>python -B docs/requirements-confirmation/phase1-spec/tasks/M06/planning/cx-exchange-revision-v3-review/review.py</code></p>
<pre>{html.escape(json.dumps({'status': status, 'probes': len(probes), 'passed': result['passed'], 'failed': result['failed'], 'findings': [f['id'] for f in findings]}, ensure_ascii=False, indent=2))}</pre>
</html>
"""
    (P / "index.html").write_text(body, encoding="utf-8")
    hashes = {p.name: sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name not in {"artifact-hashes.json", "seal.json"}}
    put("artifact-hashes.json", hashes)
    seal = {
        "status": status,
        "reviewer": result["reviewer"],
        "independent_probes": len(probes),
        "checks": len(checks),
        "passed": result["passed"],
        "failed": result["failed"],
        "findings": [f["id"] for f in findings],
        "Owner_adoption": "PENDING",
        "product_tests": "NOT RUN",
        "native": "NOT RUN",
        "build": "NOT RUN",
        "valid_RED": "NOT RUN",
        "artifact_count": len(hashes),
        "manifest_sha256": sha(P / "artifact-hashes.json"),
        "files": {**hashes, "artifact-hashes.json": sha(P / "artifact-hashes.json")},
    }
    put("seal.json", seal)
    print(json.dumps({"status": status, "checks": len(checks), "failed": result["failed"], "probes": len(probes), "findings": [f["id"] for f in findings]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
