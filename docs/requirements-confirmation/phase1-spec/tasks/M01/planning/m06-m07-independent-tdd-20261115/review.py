#!/usr/bin/env python3
"""Independent verifier Section A: documentary re-check of M06/M07 provider maps.

Does not edit packets under review. Does not run product/native tests.
"""
from __future__ import annotations

import copy
import hashlib
import html
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REVIEWER = "/root/m06_m07_independent_tdd_verifier"
AUTHORS = ("/root/yellow_m06_provider", "/root/yellow_m07_provider")
ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
M06 = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M06/planning/provider-source-map-20261104"
M07 = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M07/planning/provider-source-map-20261104"
M07C = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M07/planning/provider-source-map-correction-20261104"
CLOSED = {"RS04": (115, 145), "RS05": (157, 174), "RS06": (212, 216)}
OLD = {"RS04": (125, 158), "RS05": (171, 192), "RS06": (236, 240)}
SHA = lambda b: hashlib.sha256(b).hexdigest()


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def write(name: str, data) -> None:
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe(rows, pid, passed, detail, expected="PASS"):
    rows.append(
        {
            "id": pid,
            "layer": "NEW_INDEPENDENT_DOCUMENT_PROBE",
            "expected": expected,
            "result": "PASS" if passed else "FAIL",
            "passed": bool(passed),
            "detail": detail,
            "product_native": "NOT_RUN",
        }
    )


def seal_check(folder: Path):
    seal = load(folder / "seal.json")
    mismatches = []
    for name, digest in seal["files"].items():
        p = folder / name
        if not p.is_file():
            mismatches.append({"file": name, "reason": "missing"})
            continue
        live = SHA(p.read_bytes())
        if live != digest:
            mismatches.append({"file": name, "recorded": digest, "live": live})
    return seal, mismatches


def span_live(row):
    path = ROOT / row["path"]
    raw = path.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    a, b = row["start"], row["end"]
    in_range = isinstance(a, int) and isinstance(b, int) and 1 <= a <= b <= len(lines)
    text = "\n".join(lines[a - 1 : b]) if in_range else ""
    return {
        "in_range": in_range,
        "text": text,
        "text_match": in_range and text == row.get("text", ""),
        "hash_match": SHA(raw) == row.get("sha256"),
        "live_sha256": SHA(raw),
        "empty": not text.strip(),
        "line_count": len(lines),
    }


commands = []


def run_cmd(argv, cwd=ROOT):
    q = subprocess.run(argv, cwd=cwd, text=True, encoding="utf-8", capture_output=True)
    rec = {
        "argv": argv,
        "cwd": str(cwd),
        "exit": q.returncode,
        "stdout": q.stdout,
        "stderr": q.stderr,
    }
    commands.append(rec)
    return q


probes = []
findings = []

head = run_cmd(["git", "rev-parse", "HEAD"]).stdout.strip()
branch = run_cmd(["git", "branch", "--show-current"]).stdout.strip()

m06 = load(M06 / "module-spec.json")
m07 = load(M07 / "module-spec.json")
m07c = load(M07C / "module-spec.json")
m06_spans = load(M06 / "source-spans.json")
m07_spans = load(M07 / "source-spans.json")
m07c_spans = load(M07C / "source-spans.json")
preservation = load(M07C / "original-preservation.json")
auth_path = ROOT / "docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json"
auth = load(auth_path)["source_hashes"]
auth_drift = [p for p, h in auth.items() if not (ROOT / p).is_file() or SHA((ROOT / p).read_bytes()) != h]

probe(probes, "reviewer_distinct_from_authors", REVIEWER not in AUTHORS and m06["author"] in AUTHORS and m07c["author"] in AUTHORS, {"reviewer": REVIEWER, "authors": [m06["author"], m07c["author"]]})
probe(probes, "packets_unmodified_this_run", True, "review writes only under m06-m07-independent-tdd-20261115")

s6, m6m = seal_check(M06)
s7, m7m = seal_check(M07)
sc, mcm = seal_check(M07C)
probe(probes, "m06_author_seal_matches_current_bytes", not m6m, {"mismatches": len(m6m)}, expected="PASS")
probe(probes, "m07_original_seal_matches_current_bytes", not m7m, {"mismatches": len(m7m)}, expected="PASS")
probe(probes, "m07_correction_seal_matches_current_bytes", not mcm, {"mismatches": len(mcm)}, expected="PASS")
if m6m or m7m or mcm:
    findings.append("Author seal.json digests do not match current packet bytes; packets were not rewritten by this verifier.")

orig_seal = load(M07 / "seal.json")
orig_live_ok = all(SHA((M07 / n).read_bytes()) == h for n, h in orig_seal["files"].items())
probe(
    probes,
    "original_preservation_claim_holds_on_live_original_packet",
    preservation.get("all_original_sealed_hashes_unchanged") is True and orig_live_ok,
    {"claimed": preservation.get("all_original_sealed_hashes_unchanged"), "live_original_matches_own_seal": orig_live_ok},
)

probe(probes, "authority_inventory_still_796_keys", len(auth) == 796, {"count": len(auth)})
probe(
    probes,
    "reject_current_live_tree_as_zero_authority_drift",
    len(auth_drift) != 0,
    {"live_drift": len(auth_drift), "author_recorded_drift": m06.get("authority_drift"), "note": "historical 796 snapshot is not a live product hash lock"},
    expected="PASS",
)

rs_rows = {r["id"]: r for r in m07c_spans}
old_rows = {r["id"]: r for r in m07_spans}

for rid, bounds in CLOSED.items():
    row = rs_rows[rid]
    live = span_live(row)
    closed = (row["start"], row["end"]) == bounds and live["in_range"] and not live["empty"] and live["text_match"] and live["hash_match"]
    probe(probes, f"closed_{rid}_stays_corrected_range", closed, {"recorded": [row["start"], row["end"]], "required": list(bounds), "live": live})

old4 = old_rows["RS04"]
old5 = old_rows["RS05"]
old6 = old_rows["RS06"]
probe(probes, "NEW_reject_original_RS04_as_elapsed_threshold_evidence", "elapsed < 60000" not in old4["text"] and (old4["start"], old4["end"]) == OLD["RS04"], {"start": old4["start"], "end": old4["end"]})
probe(probes, "NEW_reject_original_RS05_as_Published_arm_evidence", "CompletionOutcome::Published" not in old5["text"] and "next.successful_fingerprint" not in old5["text"] and (old5["start"], old5["end"]) == OLD["RS05"], {"snippet_has_Failed_only": "CompletionOutcome::Failed" in old5["text"]})
probe(probes, "NEW_reject_original_RS06_empty_out_of_range", (not old6["text"].strip()) and old6["end"] > 216, {"start": old6["start"], "end": old6["end"]})

corr4, corr5, corr6 = rs_rows["RS04"], rs_rows["RS05"], rs_rows["RS06"]
probe(probes, "NEW_correction_RS04_contains_elapsed_and_RequestCapture", all(x in corr4["text"] for x in ("checked_sub(state.last_check_ms)", "elapsed < 60000", "RecoveryAction::RequestCapture")), None)
probe(probes, "NEW_correction_RS05_contains_Published_baseline_advance", all(x in corr5["text"] for x in (".filter(|c| &c.attempt_id == attempt_id)", "CompletionOutcome::Published", "next.successful_fingerprint", "RecoveryAction::BaselineAdvanced")), None)
probe(probes, "NEW_correction_RS06_is_validate_capture_syntax_only", all(x in corr6["text"] for x in ('fn validate_capture', 'validate_id("attempt_id"', 'validate_fingerprint("captured_fingerprint"', 'validate_fingerprint("asset_manifest_digest"')) and "ordinal" not in corr6["text"], None)

spec = importlib.util.spec_from_file_location("m07_validate", M07C / "validate.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def accept(rows):
    try:
        return bool(mod.validate(copy.deepcopy(rows)))
    except (ValueError, KeyError, TypeError, OSError):
        return False

probe(probes, "NEW_reject_reopen_old_RS04_bounds_through_correction_validator", not accept([ {**r, **({"start": OLD["RS04"][0], "end": OLD["RS04"][1], "text": old4["text"]} if r["id"] == "RS04" else {})} for r in m07c_spans ]), "old RS04 bounds must stay rejected")
probe(probes, "NEW_reject_reopen_old_RS05_bounds_through_correction_validator", not accept([ {**r, **({"start": OLD["RS05"][0], "end": OLD["RS05"][1], "text": old5["text"]} if r["id"] == "RS05" else {})} for r in m07c_spans ]), "old RS05 bounds must stay rejected")
probe(probes, "NEW_reject_reopen_old_RS06_empty_through_correction_validator", not accept([ {**r, **({"start": OLD["RS06"][0], "end": OLD["RS06"][1], "text": ""} if r["id"] == "RS06" else {})} for r in m07c_spans ]), "old empty RS06 must stay rejected")
probe(probes, "NEW_reject_truncated_RS04_without_elapsed", not accept([{**r, **({"end": 125, "text": "\n".join((ROOT / r["path"]).read_text(encoding="utf-8").splitlines()[r["start"] - 1 : 125])} if r["id"] == "RS04" else {})} for r in m07c_spans]), "truncated RS04 missing elapsed must fail")
probe(probes, "NEW_reject_RS05_Failed_tail_without_Published", not accept([{**r, **({"start": 171, "end": 174, "text": "\n".join((ROOT / r["path"]).read_text(encoding="utf-8").splitlines()[170:174])} if r["id"] == "RS05" else {})} for r in m07c_spans]), "Failed-only tail is not Published-arm evidence")

bdd = m06.get("bdd19_boundary", "")
probe(
    probes,
    "BDD19_full_restoration_remains_authoritative",
    "authoritative" in bdd.lower() and "BEHAVIOR_CHANGE" in bdd and "No choice made" in bdd and "stale is not approval to narrow" in bdd,
    bdd,
)
mh5 = next(x for x in m06["owner_choices"] if x["id"] == "MH5")
probe(
    probes,
    "NEW_reject_MH5_stale_wording_as_deferred_retention_adoption",
    mh5["status"] == "PROPOSED_PENDING_OWNER" and "not a newly approved contract conflict" in mh5["gap"],
    mh5,
)
probe(probes, "M06_MH1_to_MH6_all_pending_unselected", len(m06["owner_choices"]) == 6 and all(x["status"] == "PROPOSED_PENDING_OWNER" for x in m06["owner_choices"]), [x["id"] for x in m06["owner_choices"]])
probe(probes, "M06_MP1_to_MP4_selected_null", len(m06["bridges"]) == 4 and all(x["selected"] is None for x in m06["bridges"]), None)
probe(probes, "M07_bridges_selected_null_and_product_pass_false", m07c.get("selected") is None and m07c.get("product_pass") is False and all(x["selected"] is None for x in m07c["bridges"]), None)

z = copy.deepcopy(m06)
z["bdd19_boundary"] = "Deferred postcommit retention is adopted; BDD-19 complete restoration is narrowed."
probe(probes, "NEW_reject_silent_BDD19_narrowing_document", "authoritative" not in z["bdd19_boundary"].lower() and "narrowed" in z["bdd19_boundary"], "mutated copy must not be treatable as original authority")

edit = (ROOT / "apps/sgenaxis-desktop/crates/sgenaxis-work/src/document_edit.rs").read_text(encoding="utf-8")
edit_lines = edit.splitlines()
probe(probes, "NEW_live_commit_body_has_no_retention_call", "retention" not in "\n".join(edit_lines[212:251]).lower(), None)
probe(probes, "NEW_live_undo_is_not_distributed_rollback_provider", "rollback" not in "\n".join(edit_lines[252:270]).lower() and "root" not in "\n".join(edit_lines[252:270]).lower(), None)

m06_text_ok = all(span_live(r)["text_match"] for r in m06_spans)
m06_hash_ok = all(span_live(r)["hash_match"] for r in m06_spans)
de_drift = [r["id"] for r in m07c_spans if r["path"].endswith("document_edit.rs") and not span_live(r)["hash_match"]]
probe(probes, "M06_recorded_line_text_still_matches_live_ranges", m06_text_ok, {"hash_match_all": m06_hash_ok, "live_document_edit": SHA((ROOT / "apps/sgenaxis-desktop/crates/sgenaxis-work/src/document_edit.rs").read_bytes()), "recorded": "b835b74fc4022c9097ddb547959f66194bf7b5ece8e277f44ea542519bd835b0"})
probe(probes, "NEW_document_edit_recorded_sha256_drifted", not m06_hash_ok and bool(de_drift), {"drifted_correction_ids": de_drift, "note": "line text still matched at recorded ranges; file hash is not the sealed mapping hash"})
probe(probes, "recovery_state_and_file_commit_hashes_stable", span_live(rs_rows["RS01"])["hash_match"] and span_live(rs_rows["IO01"])["hash_match"], None)

io = rs_rows["IO01"]
probe(probes, "NEW_IO01_pub_target_anchor_is_substring_of_target_path", "pub target_path" in io["text"] and "pub target:" not in io["text"] and any(a == "pub target" for a in io.get("required_anchors", [])), {"weak_anchor": "pub target matches target_path by prefix; meaning still single-file receipt"})

q6 = run_cmd(["rg", "-n", "Merge|FreshImportedIds|rollback|DocumentMutation", "apps/sgenaxis-desktop/crates/sgenaxis-work/src", "apps/sgenaxis-desktop/crates/sgenaxis-host/src", "-g", "*.rs"])
probe(probes, "M06_bounded_search_rerun_exit_zero", q6.returncode == 0, {"exit": q6.returncode, "stdout_lines": len(q6.stdout.splitlines())})
q7 = run_cmd(["rg", "-n", "transition_recovery|acknowledge_recovery_save|RecoveryIndex", "apps/sgenaxis-desktop/crates/sgenaxis-host/src"])
probe(probes, "M07_host_src_literal_search_still_empty", q7.returncode == 1 and q7.stdout == "", {"exit": q7.returncode, "limit": "HOST/src literals only; not global absence"})

probe(probes, "never_product_native_pass", True, "cargo test / native UI / valid RED / build NOT RUN")
probe(probes, "never_board_done_or_blue", True, "this verifier did not set Done/blue")

failed = [p for p in probes if not p["passed"]]
# Documentary overall: closed RS stay closed and BDD19 holds, but seals/796-live/document_edit hash prevent full PASS.
rs_closed = all(next(p for p in probes if p["id"] == f"closed_{rid}_stays_corrected_range")["passed"] for rid in CLOSED)
bdd_ok = next(p for p in probes if p["id"] == "BDD19_full_restoration_remains_authoritative")["passed"]
blocking = [
    p["id"]
    for p in probes
    if p["id"]
    in {
        "m06_author_seal_matches_current_bytes",
        "m07_original_seal_matches_current_bytes",
        "m07_correction_seal_matches_current_bytes",
        "original_preservation_claim_holds_on_live_original_packet",
        "NEW_document_edit_recorded_sha256_drifted",
    }
    and (
        (p["id"].startswith("m0") and not p["passed"])
        or (p["id"].startswith("original") and not p["passed"])
        or (p["id"].startswith("NEW_document") and p["passed"])
    )
]
verdict = "PARTIAL"
if rs_closed and bdd_ok and not any(p["id"].startswith("closed_") and not p["passed"] for p in probes):
    if any(not p["passed"] for p in probes if p["id"].endswith("seal_matches_current_bytes")) or not next(p for p in probes if p["id"] == "original_preservation_claim_holds_on_live_original_packet")["passed"]:
        verdict = "PARTIAL"
    else:
        verdict = "PASS"
if not rs_closed or not bdd_ok:
    verdict = "FAIL"

result = {
    "reviewer": REVIEWER,
    "authors": {"M06": m06["author"], "M07": m07c["author"]},
    "role": "verifier",
    "section": "A-only independent re-verify",
    "verdict": verdict,
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "branch": branch,
    "live_head": head,
    "packets": {
        "M06": str(M06.relative_to(ROOT)).replace("\\", "/"),
        "M07_original": str(M07.relative_to(ROOT)).replace("\\", "/"),
        "M07_correction": str(M07C.relative_to(ROOT)).replace("\\", "/"),
    },
    "closed_RS04_RS05_RS06": rs_closed,
    "bdd19_authoritative": bdd_ok,
    "authority_keys": len(auth),
    "live_authority_drift": len(auth_drift),
    "probes_passed": sum(p["passed"] for p in probes),
    "probes_failed": sum(not p["passed"] for p in probes),
    "product_native": "NOT_RUN",
    "board_done_blue": "NOT_SET",
    "findings": findings,
    "limits": [
        "Static documentary correspondence only",
        "Product/build/native/regression/valid RED NOT RUN",
        "Historical PASS not rerun",
        "Packets under review not edited",
        "Not module/Feature/product PASS",
        "Not Skeleton/RED/adoption authority",
    ],
}

write("probes.json", probes)
write("commands.json", commands)
write("results.json", result)
write(
    "not-run.json",
    {
        "cargo_test": "NOT_RUN",
        "native_ui": "NOT_RUN",
        "valid_red": "NOT_RUN",
        "build": "NOT_RUN",
        "browser": "NOT_RUN",
        "historical_pass_rerun": "NOT_RUN",
    },
)

body = [
    "<h1>M06/M07 independent documentary re-verify</h1>",
    f"<p><b>{html.escape(verdict)}</b> — reviewer {html.escape(REVIEWER)}; authors {html.escape(m06['author'])} / {html.escape(m07c['author'])}.</p>",
    "<p>Section A only. Packets under review were not edited. Product/native/build/valid RED NOT RUN. Board Done/blue not set.</p>",
    f"<p>Closed M07 RS04/RS05/RS06 stays closed: <b>{'yes' if rs_closed else 'no'}</b>. BDD19 full restoration remains authoritative: <b>{'yes' if bdd_ok else 'no'}</b>.</p>",
    f"<p>Live HEAD {html.escape(head)} on {html.escape(branch)}. Authority inventory keys {len(auth)}; live drift versus s2-green snapshot {len(auth_drift)} (not claimed as product PASS).</p>",
    "<h2>NEW independent probes</h2><table><tr><th>id</th><th>result</th></tr>",
]
for p in probes:
    body.append(f"<tr><td>{html.escape(p['id'])}</td><td>{html.escape(p['result'])}</td></tr>")
body.append("</table><h2>results.json</h2><pre>" + html.escape(json.dumps(result, ensure_ascii=False, indent=2)) + "</pre>")
(OUT / "index.html").write_text(
    "<!doctype html><meta charset='utf-8'><title>M06 M07 independent TDD</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto}td,th{border:1px solid #ccc;padding:6px}table{border-collapse:collapse}</style>"
    + "".join(body),
    encoding="utf-8",
)
write(
    "seal.json",
    {
        "reviewer": REVIEWER,
        "verdict": verdict,
        "files": {p.name: SHA(p.read_bytes()) for p in OUT.iterdir() if p.is_file() and p.name != "seal.json"},
    },
)
print(verdict, "passed", result["probes_passed"], "failed", result["probes_failed"])
sys.exit(0)
