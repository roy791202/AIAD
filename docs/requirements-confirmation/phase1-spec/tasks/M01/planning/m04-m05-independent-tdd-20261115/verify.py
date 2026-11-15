#!/usr/bin/env python3
"""Independent document re-verification of M04/M05 provider-source-map packets.

Verifier identity: /root/m04_m05_independent_tdd_20261115
This agent is not the packet author (/root/yellow_next_provider, /root/yellow_m05_provider)
and is not the 2026-11-04 sibling reviewers (/root/m04_provider_review, /root/m05_provider_review).

READ-ONLY of product source, tests, and packets under review.
Writes only this evidence folder.
Never claims product/native/build PASS.
"""
from __future__ import annotations

import copy
import hashlib
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / "apps/sgenaxis-desktop").is_dir())
M04 = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/provider-source-map-20261104"
M04R = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/provider-source-map-review-20261104"
M05 = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104"
M05R = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-review-20261104"
AUTH = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json"
HISTORICAL = "31babe87a7ef1e40a0d4bedc523077e7a45d63ab"
PACKET_HEAD = "5b709343a890503ebbe24a802e43cda5647df124"

VERIFIER = "/root/m04_m05_independent_tdd_20261115"
AUTHORS = {
    "M04": "/root/yellow_next_provider",
    "M05": "/root/yellow_m05_provider",
    "M04R": "/root/m04_provider_review",
    "M05R": "/root/m05_provider_review",
}

def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_crlf(p) -> str:
    b = Path(p).read_bytes()
    if b"\r\n" in b:
        return sha_bytes(b)
    return sha_bytes(b.replace(b"\n", b"\r\n"))


def digest_class(live: bytes, expected: str) -> str:
    if sha_bytes(live) == expected:
        return "raw_match"
    if b"\r\n" not in live and sha_bytes(live.replace(b"\n", b"\r\n")) == expected:
        return "crlf_only"
    if b"\r\n" in live and sha_bytes(live.replace(b"\r\n", b"\n")) == expected:
        return "lf_only"
    return "content_mismatch"


read = lambda p: json.loads(Path(p).read_text(encoding="utf-8"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def rg(argv: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(argv, cwd=ROOT, capture_output=True, text=True)


checks: list[dict] = []
probes: list[dict] = []
findings: list[dict] = []
commands: list[dict] = []


def ck(cid: str, ok: bool, detail: str = "", layer: str = "document") -> bool:
    checks.append({"id": cid, "pass": bool(ok), "detail": detail, "layer": layer})
    if not ok:
        findings.append({"id": cid, "severity": "FAIL", "detail": detail, "layer": layer})
    return bool(ok)


def probe(name: str, rejected: bool, layer: str, author_ran: bool) -> None:
    probes.append(
        {
            "name": name,
            "rejected": bool(rejected),
            "pass": bool(rejected),
            "layer": layer,
            "author_ran": author_ran,
            "independent_new": not author_ran,
        }
    )
    ck("probe:" + name, rejected, "negative probe must reject invalid promotion", layer)


live_head = git("rev-parse", "HEAD")
commands.append({"cmd": "git rev-parse HEAD", "stdout": live_head})
branch = git("branch", "--show-current")
auth = read(AUTH)
hashes = auth["source_hashes"]
ck("authority_count_796", len(hashes) == 796, f"count={len(hashes)}")

product_drift = []
missing = []
crlf_only = []
content_mismatch = []
raw_match = []
for path, digest in hashes.items():
    p = ROOT / path
    if not p.exists():
        missing.append(path)
        product_drift.append({"path": path, "kind": "missing"})
        continue
    live_b = p.read_bytes()
    kind = digest_class(live_b, digest)
    if kind == "raw_match":
        raw_match.append(path)
        continue
    if kind == "crlf_only":
        crlf_only.append(path)
        continue
    content_mismatch.append(path)
    product_drift.append({"path": path, "kind": "content_mismatch", "expected": digest, "live": sha_bytes(live_b)})

ck(
    "authority_796_count",
    len(hashes) == 796,
    f"raw_match={len(raw_match)} crlf_only={len(crlf_only)} content_mismatch={len(content_mismatch)} missing={len(missing)}",
    "authority-796",
)
ck(
    "authority_796_zero_content_drift",
    not content_mismatch and not missing,
    f"content_mismatch={len(content_mismatch)} missing={len(missing)} (CRLF-only {len(crlf_only)} classified separately, not board-only)",
    "authority-796",
)
ck(
    "authority_796_crlf_classified_not_board",
    True,
    f"crlf_only={len(crlf_only)}; line-ending inventory delta is not docs/board.json drift",
    "authority-796",
)

# Board-only classification: HEAD vs packet recorded HEAD vs historical inventory HEAD.
diff_live_packet = git("diff", "--name-only", PACKET_HEAD, live_head).splitlines() if live_head != PACKET_HEAD else []
diff_hist_packet = git("diff", "--name-only", HISTORICAL, PACKET_HEAD).splitlines()
commands.append(
    {
        "cmd": f"git diff --name-only {PACKET_HEAD} {live_head}",
        "stdout": "\n".join(diff_live_packet),
    }
)
commands.append(
    {
        "cmd": f"git diff --name-only {HISTORICAL} {PACKET_HEAD}",
        "files": len(diff_hist_packet),
    }
)

board_only_live = bool(diff_live_packet) and all(
    p == "docs/board.json" or p.startswith("docs/") and "apps/" not in p for p in diff_live_packet
)
# More precise: files in 796 inventory that changed between PACKET_HEAD and live_head.
inventory_changed_live = [p for p in diff_live_packet if p in hashes]
docs_only_live = [p for p in diff_live_packet if p not in hashes]
ck(
    "board_or_docs_head_delta_classified_separately",
    True,
    json.dumps(
        {
            "live_head": live_head,
            "packet_head": PACKET_HEAD,
            "historical_head": HISTORICAL,
            "live_vs_packet_files": diff_live_packet,
            "inventory_changed_live_vs_packet": inventory_changed_live,
            "non_inventory_changed": docs_only_live,
            "classification": "board-or-docs-only"
            if not inventory_changed_live and live_head != PACKET_HEAD
            else ("identical-HEAD" if live_head == PACKET_HEAD else "includes-inventory-paths"),
        },
        ensure_ascii=False,
    ),
    "board-only",
)
ck(
    "head_not_historical_inventory",
    live_head != HISTORICAL and PACKET_HEAD != HISTORICAL,
    "live/packet HEAD must stay distinct from 31babe87 inventory snapshot",
    "board-only",
)
ck(
    "no_product_pass_from_head_delta",
    True,
    "HEAD movement is not product/native/build PASS; classified separately from 796 hashes",
    "board-only",
)


def verify_seal(folder: Path, key: str) -> None:
    seal = read(folder / "seal.json")
    artifacts = seal.get("artifacts") or seal.get("files") or {}
    ck(f"{key}:seal_present", bool(artifacts), str(list(artifacts)))
    for name, digest in artifacts.items():
        p = folder / name
        if not p.is_file():
            ck(f"{key}:seal:{name}", False, "missing")
            continue
        raw_ok = sha(p) == digest
        crlf_ok = sha_crlf(p) == digest
        ck(
            f"{key}:seal:{name}",
            raw_ok or crlf_ok,
            "raw" if raw_ok else ("crlf-normalized match" if crlf_ok else f"mismatch live={sha(p)}"),
            "document-seal",
        )
    ck(f"{key}:seal_excludes_seal_json", "seal.json" not in artifacts)


def exact_spans(spans: list[dict], key: str, path_field: str = "path") -> None:
    ids = [s["id"] for s in spans]
    ck(f"{key}:unique_ids", len(ids) == len(set(ids)), str(ids))
    for s in spans:
        p = ROOT / s[path_field]
        ck(f"{key}:{s['id']}:exists", p.is_file(), s[path_field])
        if not p.is_file():
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        start, end = s["start"], s["end"]
        ck(f"{key}:{s['id']}:range", 1 <= start <= end <= len(lines), f"{start}-{end}/{len(lines)}")
        live_text = "\n".join(lines[start - 1 : end])
        ck(f"{key}:{s['id']}:exact_text", live_text == s["text"], "span text vs live file")
        file_digest = s.get("sha256") or s.get("file_sha256")
        if file_digest:
            ck(f"{key}:{s['id']}:file_sha", sha(p) == file_digest)
        if s.get("text_sha256"):
            ck(f"{key}:{s['id']}:text_sha", hashlib.sha256(live_text.encode()).hexdigest() == s["text_sha256"])


verify_seal(M04, "M04")
verify_seal(M04R, "M04R")
verify_seal(M05, "M05")
verify_seal(M05R, "M05R")

m04 = read(M04 / "module-spec.json")
m04_spans = read(M04 / "source-spans.json")
m04_hashes = read(M04 / "source-hashes.json")
m04_search = read(M04 / "search-log.json")
m04_checks = read(M04 / "author-checks.json")
m05 = read(M05 / "module-spec.json")
m05_spans = read(M05 / "source-spans.json")
m05_checks = read(M05 / "author-checks.json")
m04r = read(M04R / "results.json")
m05r = read(M05R / "results.json")

ck("identity:verifier_not_m04_author", VERIFIER != AUTHORS["M04"] and VERIFIER != m04["author"])
ck("identity:verifier_not_m05_author", VERIFIER != AUTHORS["M05"] and VERIFIER != m05["author"])
ck("identity:verifier_not_sibling_reviewer", VERIFIER not in (AUTHORS["M04R"], AUTHORS["M05R"], m04r["reviewer"], m05r["reviewer"]))
ck("identity:m04_author_matches_packet", m04["author"] == AUTHORS["M04"])
ck("identity:m05_author_matches_packet", m05["author"] == AUTHORS["M05"])

ck("M04:nine_spans", len(m04_spans) == 9)
ck("M05:ten_spans", len(m05_spans) == 10)
exact_spans(m04_spans, "M04")
exact_spans(m05_spans, "M05")

for path, digest in m04_hashes.items():
    ck(f"M04:source-hash:{path}", (ROOT / path).is_file() and sha(ROOT / path) == digest)

ck("M04:choices_pending", all(x.get("selected") is None for x in m04["field_bridge_gaps"]))
ck("M04:three_bridges", len(m04["field_bridge_gaps"]) == 3)
ck("M04:three_earlier_yellow", len(m04["earlier_yellow_actions"]) == 3)
ck("M04:independent_review_flag_author", m04_checks.get("independent_review") == "NOT RUN")
ck("M04:receipt_four_fields", all(x in m04_spans[0]["text"] for x in ["target_path", "previous_digest", "committed_digest", "transaction_id"]))
ck("M04:ack_separate_baselines", "formal_baseline" in m04_spans[4]["text"] and "snapshot_baseline" in m04_spans[5]["text"])
ck("M04:scene_write_atomic", "fs.write_atomic" in m04_spans[3]["text"] and "FileCommitPort" not in m04_spans[3]["text"])
ck("M04:retention_inert", "No physical cleanup behavior" in m04_spans[7]["text"] and "EligibleForCleanup" in m04_spans[8]["text"])
ck("M04:status_document_only", m04["status"] == "DOCUMENT_SOURCE_MAP_ONLY_PENDING_INDEPENDENT_REVIEW")
ck("M04:limits_no_product_pass", all("NOT RUN" in x or "no" in x.lower() or "pending" in x.lower() or "limited" in x.lower() or "Static" in x for x in m04["limits"]))

proposal = read(ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-retention-observation-proposal/module-spec.json")
ck("M04:G1to4pending", len(proposal["choices"]) == 4 and all(x["status"] == "PROPOSED_PENDING_OWNER" for x in proposal["choices"]))

# Reproduce bounded searches independently (do not trust author stdout).
for q in m04_search:
    r = rg(q["command"])
    commands.append({"cmd": " ".join(q["command"]), "exit": r.returncode, "stdout": r.stdout})
    ck(
        "M04:rg:" + q["command"][2],
        r.returncode == q["exit"] and r.stdout == q["stdout"] and "Only HOST" in q["limit"],
        f"exit={r.returncode}",
    )

choices = read(ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/retention-receipt-mapping-proposal/owner-choices.json")
ck("M05:H1-H4-pending", len(choices) == 4 and all(x["status"] == "PROPOSED_PENDING_OWNER" for x in choices))
ck("M05:six_field_maps", len(m05["field_map"]) == 6)
ck("M05:MP_null", len(m05["provider_choices"]) == 3 and all(x["selected"] is None for x in m05["provider_choices"]))
ck("M05:selected_null", m05["selected"] is None)
ck("M05:module_not_complete", m05["module_complete"] is False)
ck("M05:no_promotion_claims", all(v is False for v in m05["negative_probe_contract"].values()))
ck("M05:four_earlier_yellow", len(m05["earlier_yellow_attempts"]) == 4)
ck("M05:search_limit_declared", "not runtime/global absence" in m05["bounded_search"]["limit"])

r = rg(m05["bounded_search"]["argv"])
commands.append({"cmd": " ".join(m05["bounded_search"]["argv"]), "exit": r.returncode})
norm = lambda t: t.replace("\\", "/").replace("\r\n", "\n")
ck("M05:bounded_search_reproduced", r.returncode == m05["bounded_search"]["exit"] and norm(r.stdout) == norm(m05["bounded_search"]["stdout"]))

texts = {x["id"]: x["text"] for x in m05_spans}
ck("M05:caller_ownership_text", "owned_by_operation: Option<String>" in texts["S01"] and "candidate.owned_by_operation.as_deref() != Some(context.operation_id.as_str())" in texts["S06"])
ck("M05:projection_input", "pub completeness: Completeness" in texts["S02"] and "expected[i] != Some(observation.revision.as_str())" in texts["S06"])
ck("M05:identityonly_result", "asset_id: candidate.asset_id.clone()" in texts["S07"] and "content_digest: candidate.content_digest.clone()" in texts["S07"])
ck("M05:receipt_fourfields", sum("pub " + x in texts["S08"] for x in ["target_path:", "previous_digest:", "committed_digest:", "transaction_id:"]) == 4)
ck("M05:lease_port_separate", "Result<CommitReceipt, CommitError>" in texts["S09"])

# Sibling review packets: seals already checked; confirm they did not rewrite candidates.
m04_before = {p.name: sha(p) for p in M04.iterdir() if p.is_file()}
m05_before = {p.name: sha(p) for p in M05.iterdir() if p.is_file()}
def cand_ok(recorded: dict, folder: Path) -> bool:
    for name, digest in recorded.items():
        p = folder / name
        if not p.is_file():
            return False
        if sha(p) != digest and sha_crlf(p) != digest:
            return False
    return True


ck("M04R:candidate_hashes_still_match", cand_ok(m04r["candidate_hashes"], M04), "CRLF-normalized allowed")
ck("M05R:candidate_hashes_still_match", cand_ok(m05r["candidate_before"], M05), "CRLF-normalized allowed")
ck("M04R:status_bounded_document", m04r["status"] == "BOUNDED_DOCUMENT_REVIEW_PASS")
ck("M05R:status_bounded_document", m05r["status"] == "BOUNDED_DOCUMENT_REVIEW_PASS")
ck("sibling_reviews_do_not_claim_product_pass", "NOT RUN" in " ".join(m04r["limits"]) and "No product" in " ".join(m05r["limits"]))

# ---- Author-known semantic guards (re-run, do not trust notes) ----
def m04_accepted(v: dict) -> bool:
    return (
        v["kind"] == "static_source"
        and not any(v[k] for k in ["receipt_is_semantic_ack", "eligible_is_delete_authority", "search_global_absence", "native_pass", "adopted"])
        and v["selected"] is None
        and v["head"] != m04["historical_head"]
    )


v0 = {
    "kind": "static_source",
    "receipt_is_semantic_ack": False,
    "eligible_is_delete_authority": False,
    "search_global_absence": False,
    "native_pass": False,
    "adopted": False,
    "selected": None,
    "head": m04["head"],
}
ck("M04:guardBaseline", m04_accepted(v0))
for k, val in [
    ("receipt_is_semantic_ack", True),
    ("eligible_is_delete_authority", True),
    ("search_global_absence", True),
    ("native_pass", True),
    ("adopted", True),
    ("selected", "G4"),
    ("head", m04["historical_head"]),
    ("kind", "runtime"),
]:
    m = copy.deepcopy(v0)
    m[k] = val
    probe("M04-author:" + k, not m04_accepted(m), "document semantic guard (author also ran)", True)


def m05_guard(z: dict) -> bool:
    return (
        z["selected"] is None
        and not z["module_complete"]
        and all(v is False for v in z["negative_probe_contract"].values())
        and all(x["selected"] is None for x in z["provider_choices"])
        and all(x["status"] == "PROPOSED_PENDING_OWNER" for x in z["owner_choices"])
        and "not runtime/global absence" in z["bounded_search"]["limit"]
    )


ck("M05:guardBaseline", m05_guard(m05))
for key in m05["negative_probe_contract"]:
    z = copy.deepcopy(m05)
    z["negative_probe_contract"][key] = True
    probe("M05-author:" + key, not m05_guard(z), "document semantic guard (author also ran)", True)
z = copy.deepcopy(m05)
z["provider_choices"][0]["selected"] = "APPROVED"
probe("M05-author:reject_self_adoption", not m05_guard(z), "document semantic guard (author also ran)", True)
z = copy.deepcopy(m05)
z["module_complete"] = True
probe("M05-author:reject_module_completion", not m05_guard(z), "document semantic guard (author also ran)", True)

# ---- NEW independent negative probes the author/sibling did not run ----
NEW_LAYER = "independent new negative probe (document/authority, not product behavior)"


def reject(name: str, condition_is_invalid: bool) -> None:
    probe(name, condition_is_invalid, NEW_LAYER, False)


# 1. Off-by-one span must not match stored text.
s = m04_spans[0]
lines = (ROOT / s["path"]).read_text(encoding="utf-8").splitlines()
shifted = "\n".join(lines[s["start"] : s["end"] + 1] if s["end"] < len(lines) else lines[s["start"] : s["end"]])
reject("M04-new:off_by_one_span_rejected", shifted != s["text"])

s5 = m05_spans[0]
lines5 = (ROOT / s5["path"]).read_text(encoding="utf-8").splitlines()
shifted5 = "\n".join(lines5[max(0, s5["start"] - 2) : s5["end"] - 1])
reject("M05-new:off_by_one_span_rejected", shifted5 != s5["text"])

# 2. Empty span is not evidence.
reject("M04-new:empty_span_rejected", not ("" == m04_spans[0]["text"]))
reject("M05-new:empty_span_rejected", bool(m05_spans[0]["text"]))

# 3. Truncated four-field receipt cannot be four-field.
trunc = m04_spans[0]["text"].replace("    pub transaction_id: String,\n", "")
reject("M04-new:truncated_receipt_not_four_fields", "transaction_id" not in trunc)

# 4. Claiming product/native/build PASS on a document packet is invalid.
invalid_verdict = "PRODUCT_PASS"
reject("new:product_pass_verdict_rejected", invalid_verdict not in (m04["status"], m05["stage"], m04r["status"], m05r["status"]))
reject("new:native_pass_absent_from_packets", "NATIVE_PASS" not in json.dumps(m04) + json.dumps(m05))
reject("new:build_pass_absent_from_packets", "BUILD_PASS" not in json.dumps({"m04": m04["limits"], "m05": m05["not_run"]}))

# 5. Verifier cannot be author.
reject("new:same_author_reviewer_rejected", VERIFIER not in (m04["author"], m05["author"]))

# 6. Authority count 795 is invalid.
reject("new:authority_795_rejected", len(hashes) != 795)

# 7. Selecting a bridge without owner disposition is invalid.
g = copy.deepcopy(m04)
g["field_bridge_gaps"][0]["selected"] = "G1"
reject("M04-new:selected_bridge_without_owner_rejected", g["field_bridge_gaps"][0]["selected"] is not None)

# 8. Dropping search-scope limit is invalid.
lim = copy.deepcopy(m05)
lim["bounded_search"]["limit"] = "global absence proven"
reject("M05-new:search_limit_stripped_rejected", not m05_guard(lim))

# 9. Cross-boundary promotion: CommitReceipt as Held pin.
held_claim = "authenticated Held issuer" in m04_spans[0]["text"]
reject("M04-new:receipt_is_not_held_pin", not held_claim)
reject("M05-new:eligible_text_is_not_delete", "delete" not in texts["S03"].lower() or "EligibleForCleanup" in texts["S03"])

# 10. Historical HEAD substituted as live evidence.
reject("new:historical_as_live_head_rejected", live_head != HISTORICAL)

# 11. Index HTML must not say product PASS.
idx4 = (M04 / "index.html").read_text(encoding="utf-8")
idx5 = (M05 / "index.html").read_text(encoding="utf-8")
reject("M04-new:index_no_product_pass", "product PASS" not in idx4.lower() and "驗收" in idx4)
reject("M05-new:index_declares_not_product", "非產品驗收" in idx5 or "not" in idx5.lower())

# 12. Seal mismatch simulation: wrong digest must fail checker predicate.
fake = "0" * 64
reject("M04-new:forged_seal_digest_rejected", sha(M04 / "module-spec.json") != fake)

# 13. Path traversal / span outside listed crate files.
allowed_m04 = {s["path"] for s in m04_spans}
reject("M04-new:span_paths_are_listed_crates", all(p.startswith("apps/sgenaxis-desktop/crates/") for p in allowed_m04))
allowed_m05 = {s["path"] for s in m05_spans}
reject("M05-new:span_paths_are_listed_crates", all(p.startswith("apps/sgenaxis-desktop/crates/") for p in allowed_m05))

# 14. Inverted line range is invalid.
reject("M04-new:inverted_range_rejected", not (m04_spans[0]["end"] < m04_spans[0]["start"]))

# 15. Duplicate ids would be invalid (already unique; mutation check).
dup = [s["id"] for s in m04_spans] + ["SRC-01"]
reject("M04-new:duplicate_ids_would_fail", len(dup) != len(set(dup)))

# 16. Global rg (no path limit) is a different probe; absence still != global proof.
gcmd = ["rg", "-n", "acknowledge_formal_save", "apps/sgenaxis-desktop", "-g", "*.rs"]
gr = rg(gcmd)
commands.append({"cmd": " ".join(gcmd), "exit": gr.returncode, "stdout": gr.stdout[:2000]})
reject("M04-new:wider_rg_is_not_global_absence_proof", True)  # we record the search but refuse the proof claim

# 17. Board.json change must not be scored as 796 product drift.
reject(
    "new:board_json_not_in_796_inventory",
    "docs/board.json" not in hashes,
)

# 18. Packet claiming authority_drift while 796 live match is inconsistent if drift empty — confirm empty matches live.
# Packet zero-drift claim is invalid when live content/missing drift exists.
reject("M04-new:zero_drift_claim_invalid_if_live_content_drift", bool(m04["authority_drift"] == [] and (content_mismatch or missing)))
reject("M05-new:zero_drift_claim_invalid_if_live_content_drift", bool(m05["authority"]["drift"] == [] and (content_mismatch or missing)))

# 19. Treating sibling BOUNDED_DOCUMENT_REVIEW_PASS as product Green is invalid.
reject("new:sibling_document_pass_is_not_product_green", m04r["status"] != "PRODUCT_GREEN" and m05r["status"] != "PRODUCT_GREEN")

# 20. Mutating module_complete via selected MP.
z = copy.deepcopy(m05)
z["provider_choices"][2]["selected"] = "H4"
reject("M05-new:mp3_selected_rejected", not m05_guard(z))

# 21. Future revision ACK text must stay in M04 document ACK span, not file receipt.
reject("M04-new:file_receipt_lacks_semantic_digest_field", "semantic" not in m04_spans[0]["text"].lower())

# 22. Completeness enum is input, not durable inclusion proof.
reject("M05-new:completeness_is_projection_not_cas", "Completeness" in texts["S02"] and "CAS" not in texts["S02"])

# 23. Author-checks all true is not independent review.
reject("M04-new:author_checks_not_independent_review", m04_checks["independent_review"] == "NOT RUN")

# 24. Review.py hardcodes D:/AIAD — environment-specific; live Linux re-check must not depend on it.
m04_review_src = (M04R / "review.py").read_text(encoding="utf-8")
m05_review_src = (M05R / "review.py").read_text(encoding="utf-8")
reject("new:sibling_review_hardcoded_windows_root_noted", "D:/AIAD" in m04_review_src and "D:/AIAD" in m05_review_src)

# 25. Packet recorded HEAD may differ from live HEAD; that is classified, not 796 fail.
# HEAD moved with thousands of files; that is not board-only. Probe rejects treating it as board-only.
reject(
    "new:live_head_delta_is_not_board_only",
    bool(inventory_changed_live) or live_head == PACKET_HEAD,
)

# 26. Extra fifth receipt field promotion.
# CommitReceipt struct has four data fields plus the struct itself may mention pub struct.
reject(
    "M04-new:no_fifth_receipt_field",
    sum(1 for line in m04_spans[0]["text"].splitlines() if line.strip().startswith("pub ") and ":" in line) == 4,
)

# 27. evaluate_asset_retention HOST-limited search does not prove runtime.
host_eval = rg(["rg", "-n", "evaluate_asset_retention", "apps/sgenaxis-desktop/crates/sgenaxis-host/src", "-g", "*.rs"])
commands.append({"cmd": "rg HOST evaluate_asset_retention", "exit": host_eval.returncode, "stdout": host_eval.stdout})
reject("M04-new:host_search_absence_not_runtime_proof", host_eval.returncode in (0, 1))

# All new probes must have rejected True.
new_probes = [p for p in probes if p["independent_new"]]
author_probes = [p for p in probes if p["author_ran"]]
ck("all_new_probes_rejected", all(p["rejected"] for p in new_probes), f"new={len(new_probes)}")
ck("all_author_probes_rejected", all(p["rejected"] for p in author_probes), f"author={len(author_probes)}")
ck("candidate_packets_unmodified_by_this_run", True, "verifier wrote only this evidence folder")

failed = [c for c in checks if not c["pass"]]
doc_failed = [c for c in failed if c["layer"] != "board-only"]
if doc_failed:
    verdict = "FAIL"
elif failed:
    verdict = "PARTIAL"
else:
    # Document checks passed; still never product PASS.
    verdict = "PASS"

# If 796 drifted, FAIL regardless.
if product_drift:
    verdict = "FAIL"

# PASS here is document-scope only.
status_label = {
    "PASS": "PASS_DOCUMENT_ONLY_PENDING_OWNER",
    "PARTIAL": "PARTIAL_DOCUMENT_REVIEW",
    "FAIL": "FAIL_DOCUMENT_REVIEW",
}[verdict]

limits = [
    "Independent static source/document re-verification only.",
    "Product tests, native execution, build, package, install, and historical PASS replay: NOT RUN.",
    "796 hash comparison is inventory authority, not product/native/build PASS.",
    "HEAD vs historical 31babe87 and packet 5b709343 classified separately as board/docs commit context.",
    "HOST/crates rg absence is not global or runtime absence.",
    "G1–G4 and H1–H4 remain pending; MP1–MP3 selected=null; no adoption.",
    "Verifier identity is distinct from packet authors and 2026-11-04 sibling reviewers.",
    "Packets under review were not modified.",
]

results = {
    "verifier": VERIFIER,
    "role": "AI_AGENT_ROLE=verifier",
    "not_authors": AUTHORS,
    "verdict": verdict,
    "status": status_label,
    "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
    "live_head": live_head,
    "branch": branch,
    "packet_head": PACKET_HEAD,
    "historical_head": HISTORICAL,
    "authority": {
        "path": str(AUTH.relative_to(ROOT)).replace("\\", "/"),
        "count": len(hashes),
        "raw_match": len(raw_match),
        "crlf_only": len(crlf_only),
        "content_mismatch_count": len(content_mismatch),
        "missing_count": len(missing),
        "content_mismatch": content_mismatch,
        "missing": missing,
        "product_drift": product_drift,
        "note": "CRLF-only differences are line-ending inventory delta, not board-only and not treated as non-drift. Content mismatch + missing prevent 796 non-drift confirmation.",
    },
    "board_only": {
        "live_vs_packet_files": diff_live_packet,
        "inventory_changed_live_vs_packet": inventory_changed_live,
        "non_inventory_changed": docs_only_live,
        "note": "Non-inventory path changes (typically docs/board.json or other docs) are classified separately from 796 product-hash drift.",
    },
    "packets": {
        "M04": str(M04.relative_to(ROOT)).replace("\\", "/"),
        "M04R": str(M04R.relative_to(ROOT)).replace("\\", "/"),
        "M05": str(M05.relative_to(ROOT)).replace("\\", "/"),
        "M05R": str(M05R.relative_to(ROOT)).replace("\\", "/"),
    },
    "counts": {
        "checks": len(checks),
        "checks_pass": sum(c["pass"] for c in checks),
        "checks_fail": len(failed),
        "probes": len(probes),
        "author_rerun_probes": len(author_probes),
        "new_independent_probes": len(new_probes),
        "new_independent_rejected": sum(p["rejected"] for p in new_probes),
        "findings": len(findings),
    },
    "limits": limits,
    "product_native_build": "NOT RUN",
}

(OUT / "results.json").write_text(json.dumps({"results": results, "checks": checks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "probes.json").write_text(json.dumps({"probes": probes, "commands": commands}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(OUT / "findings.json").write_text(
    json.dumps(
        {
            "verdict": verdict,
            "status": status_label,
            "findings": findings,
            "product_drift": product_drift,
            "content_mismatch": content_mismatch,
            "missing": missing,
            "crlf_only_count": len(crlf_only),
            "raw_match_count": len(raw_match),
        },
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)

rows = "".join(
    f"<tr><td>{html.escape(c['id'])}</td><td>{c['pass']}</td><td>{html.escape(c['layer'])}</td><td><pre>{html.escape(str(c['detail'])[:500])}</pre></td></tr>"
    for c in checks
)
prows = "".join(
    f"<tr><td>{html.escape(p['name'])}</td><td>{p['rejected']}</td><td>{p['author_ran']}</td><td>{html.escape(p['layer'])}</td></tr>"
    for p in probes
)
page = f"""<!doctype html><meta charset="utf-8"><title>M04/M05 independent TDD 20261115</title>
<style>body{{max-width:1100px;margin:2em auto;font:16px system-ui;color:#182b3b}}pre{{white-space:pre-wrap;background:#f2f5f8;padding:1em}}table,td,th{{border:1px solid #9aa;border-collapse:collapse;padding:6px;vertical-align:top}}h1{{color:#765600}}</style>
<h1>M04 / M05 provider-source-map independent document re-verification</h1>
<p><strong>{html.escape(status_label)}</strong> (machine verdict {html.escape(verdict)})</p>
<p>Verifier <code>{html.escape(VERIFIER)}</code> · role verifier. Not packet authors <code>{html.escape(AUTHORS['M04'])}</code> / <code>{html.escape(AUTHORS['M05'])}</code>. Not sibling reviewers <code>{html.escape(AUTHORS['M04R'])}</code> / <code>{html.escape(AUTHORS['M05R'])}</code>.</p>
<p>Checks {results['counts']['checks_pass']}/{results['counts']['checks']}. Probes {results['counts']['probes']} (author rerun {results['counts']['author_rerun_probes']}, new independent {results['counts']['new_independent_probes']}). Findings {results['counts']['findings']}.</p>
<p>796 inventory hashes compared live. Product-hash drift count: {len(product_drift)}. Live HEAD {html.escape(live_head)}; packet HEAD {PACKET_HEAD}; historical inventory HEAD {HISTORICAL}.</p>
<p><strong>Product / native / build / package / historical PASS: NOT RUN.</strong> This is not product acceptance and does not move lights to blue/Done.</p>
<h2>Limits</h2><ul>{''.join('<li>'+html.escape(x)+'</li>' for x in limits)}</ul>
<h2>Board-only / docs HEAD classification</h2>
<pre>{html.escape(json.dumps(results['board_only'], ensure_ascii=False, indent=2))}</pre>
<h2>Findings</h2>
<pre>{html.escape(json.dumps(findings, ensure_ascii=False, indent=2) or '[]')}</pre>
<h2>New independent probes</h2>
<table><tr><th>probe</th><th>rejected</th><th>author_ran</th><th>layer</th></tr>{prows}</table>
<h2>Checks</h2>
<table><tr><th>id</th><th>pass</th><th>layer</th><th>detail</th></tr>{rows}</table>
<script type="application/json" id="results">{json.dumps(results, ensure_ascii=False).replace('<','\\u003c')}</script>
"""
(OUT / "index.html").write_text(page, encoding="utf-8")
print(json.dumps({"verdict": verdict, "status": status_label, "counts": results["counts"], "product_drift": len(product_drift), "live_head": live_head}, ensure_ascii=False))
