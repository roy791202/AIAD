"""Disposable TDD Gate live harness for PD-RUST-MODULE-HTML-01. Delete after run."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("generate_report", HERE / "generate_report.py")
gr = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(gr)

results: dict = {}
failed: list[str] = []

data = json.loads((HERE / "module.json").read_text(encoding="utf-8"))
bound = data["stale_detection"]["bound_source_sha256"]
stale = gr.check_stale(bound)
results["check_stale"] = stale
if stale["status"] != "CURRENT" or stale["mismatches"]:
    failed.append(f"baseline check_stale: {stale}")

html = (HERE / "module.html").read_text(encoding="utf-8")
for need in [
    "diagram_a_hexagonal",
    "diagram_b_ownership_stale",
    "id='contracts'",
    "id='tests'",
    "id='scope'",
    "id='evidence'",
    "id='risk'",
]:
    if need not in html:
        failed.append(f"missing HTML section/marker: {need}")

trace = data["bdd_tdd_task_result_sourcehash"]
results["trace_rows"] = len(trace)
if len(trace) != 9:
    failed.append(f"trace_rows={len(trace)} expected 9")

ms = data["module_spec_document"]
results["module_spec_status"] = ms["revisions"][0]["status"]
results["evidence_refs"] = ms["evidence_refs"]
if ms["revisions"][0]["status"] != "draft":
    failed.append("module_spec not draft")
if ms["evidence_refs"] != []:
    failed.append(f"evidence_refs not empty: {ms['evidence_refs']}")

results["bound_keys"] = list(bound.keys())
flip_rel = None
for rel in bound:
    p = gr.ROOT / rel
    if p.is_file():
        flip_rel = rel
        break
if not flip_rel:
    failed.append("no bound source to flip")
else:
    flip_path = gr.ROOT / flip_rel
    original = flip_path.read_bytes()
    try:
        flip_path.write_bytes(original + b"\x00")
        stale2 = gr.check_stale(bound)
        results["after_flip"] = stale2["status"]
        if stale2["status"] != "PROJECTION_STALE":
            failed.append(f"after flip expected PROJECTION_STALE got {stale2}")
    finally:
        flip_path.write_bytes(original)
    stale3 = gr.check_stale(bound)
    results["after_restore"] = stale3["status"]
    if stale3["status"] != "CURRENT":
        failed.append(f"after restore expected CURRENT got {stale3}")

inj = HERE / "_tdd_gate_inject_fail.md"
inj.write_text("# inject\n| **Verdict** | **TDD_FAIL** |\n", encoding="utf-8")
try:
    rel = str(inj.relative_to(gr.ROOT)).replace("\\", "/")
    ptr = gr.live_source_review_pointer(rel, card_tdd_posture="NOT RUN（待辦）")
    results["HTML-R1"] = ptr
    if ptr.get("honest_status") != "TDD_NOT_RUN":
        failed.append(f"HTML-R1 honest_status={ptr.get('honest_status')}")
    if ptr.get("review_class") != "SOURCE_REVIEW_NEGATIVE":
        failed.append(
            f"HTML-R1 review_class={ptr.get('review_class')} (must be SOURCE_REVIEW_NEGATIVE)"
        )
    if ptr.get("review_class") == "REVIEW_PASS_STATIC_AUDIT":
        failed.append("HTML-R1 incorrectly REVIEW_PASS_STATIC_AUDIT")
finally:
    inj.unlink(missing_ok=True)

inj2 = HERE / "_tdd_gate_inject_pass.md"
inj2.write_text("# inject\n| **Verdict** | **TDD_PASS** |\n", encoding="utf-8")
try:
    rel2 = str(inj2.relative_to(gr.ROOT)).replace("\\", "/")
    ptr2 = gr.live_source_review_pointer(rel2, card_tdd_posture="NOT RUN")
    results["HTML-R1_PASS_path"] = ptr2
    if ptr2.get("review_class") != "REVIEW_PASS_STATIC_AUDIT":
        failed.append(f"HTML-R1 positive path review_class={ptr2.get('review_class')}")
    if ptr2.get("honest_status") != "TDD_NOT_RUN":
        failed.append(f"HTML-R1 positive honest_status={ptr2.get('honest_status')}")
finally:
    inj2.unlink(missing_ok=True)

if gr.classify_source_review_verdict("TDD_FAIL") != "SOURCE_REVIEW_NEGATIVE":
    failed.append("classifier TDD_FAIL mapping wrong")
if gr.classify_source_review_verdict("TDD_PASS") != "REVIEW_PASS_STATIC_AUDIT":
    failed.append("classifier TDD_PASS mapping wrong")
results["classifier_ok"] = True

json_path = HERE / "module.json"
html_path = HERE / "module.html"
bak_json = json_path.read_bytes()
bak_html = html_path.read_bytes()


def r2_absent_prior_partial() -> dict:
    jtmp = HERE / "_gate_j.bak"
    htmp = HERE / "_gate_h.bak"
    jtmp.write_bytes(bak_json)
    htmp.write_bytes(bak_html)
    json_path.unlink()
    html_path.unlink()
    out: dict
    try:
        real_write_text = Path.write_text

        def flaky(self, *a, **k):  # type: ignore[no-untyped-def]
            if self == html_path:
                raise OSError("simulated html write fail")
            return real_write_text(self, *a, **k)

        with patch.object(Path, "write_text", flaky):
            try:
                gr.write_output_pair('{"x":1}\n', "<html/>")
                out = {"raised": False}
            except OSError as e:
                out = {
                    "raised": True,
                    "type": type(e).__name__,
                    "json_exists": json_path.exists(),
                    "html_exists": html_path.exists(),
                    "attempted": getattr(e, "output_pair_recovery_attempted", None),
                }
    finally:
        json_path.write_bytes(jtmp.read_bytes())
        html_path.write_bytes(htmp.read_bytes())
        jtmp.unlink(missing_ok=True)
        htmp.unlink(missing_ok=True)
    return out


r2a = r2_absent_prior_partial()
results["HTML-R2_absent_prior"] = r2a
if not r2a.get("raised"):
    failed.append("HTML-R2 absent-prior did not raise")
if r2a.get("json_exists") is not False:
    failed.append(f"HTML-R2 absent-prior json residual: {r2a}")
if r2a.get("html_exists") is not False:
    failed.append(f"HTML-R2 absent-prior html residual: {r2a}")
if set(r2a.get("attempted") or []) != {"json_restore", "html_restore"}:
    failed.append(f"HTML-R2 absent-prior attempted={r2a.get('attempted')}")


def r2_restore_denied() -> dict:
    real_write_bytes = Path.write_bytes
    real_write_text = Path.write_text
    state = {"json_restore_calls": 0, "html_restore_calls": 0}

    def flaky_text(self, *a, **k):  # type: ignore[no-untyped-def]
        if self == html_path:
            raise OSError("primary html fail")
        return real_write_text(self, *a, **k)

    def flaky_bytes(self, data):  # type: ignore[no-untyped-def]
        if self == json_path:
            state["json_restore_calls"] += 1
            raise OSError("json restore denied")
        if self == html_path:
            state["html_restore_calls"] += 1
        return real_write_bytes(self, data)

    out: dict
    try:
        with patch.object(Path, "write_text", flaky_text), patch.object(
            Path, "write_bytes", flaky_bytes
        ):
            try:
                gr.write_output_pair('{"broken":true}\n', "<broken/>")
                out = {"raised": None, **state}
            except Exception as e:  # noqa: BLE001 — classify gate outcomes
                primary = e.primary if isinstance(e, gr.OutputPairRecoveryError) else e
                out = {
                    "raised": type(e).__name__,
                    "is_recovery": isinstance(e, gr.OutputPairRecoveryError),
                    "primary_type": type(primary).__name__,
                    "primary_msg": str(primary),
                    "recovery_labels": [
                        lab
                        for lab, _ in (
                            e.recovery_errors
                            if isinstance(e, gr.OutputPairRecoveryError)
                            else []
                        )
                    ],
                    "attempted": getattr(
                        primary,
                        "output_pair_recovery_attempted",
                        getattr(e, "output_pair_recovery_attempted", None),
                    ),
                    **state,
                }
    finally:
        json_path.write_bytes(bak_json)
        html_path.write_bytes(bak_html)
    return out


r2b = r2_restore_denied()
results["HTML-R2_restore_denied"] = r2b
if r2b.get("raised") != "OutputPairRecoveryError":
    failed.append(f"HTML-R2 restore-denied raised={r2b.get('raised')}")
if not r2b.get("is_recovery"):
    failed.append("HTML-R2 not OutputPairRecoveryError")
if r2b.get("primary_type") != "OSError" or "primary html fail" not in (
    r2b.get("primary_msg") or ""
):
    failed.append(f"HTML-R2 primary not preserved: {r2b}")
if "json_restore" not in (r2b.get("recovery_labels") or []):
    failed.append(f"HTML-R2 missing json_restore in recovery_errors: {r2b}")
attempted = r2b.get("attempted") or []
if "html_restore" not in attempted or "json_restore" not in attempted:
    failed.append(f"HTML-R2 restore-denied attempted={attempted}")
if r2b.get("html_restore_calls", 0) < 1:
    failed.append(f"HTML-R2 html_restore not attempted independently: {r2b}")


def r2_complete_pair_rollback() -> dict:
    real_write_text = Path.write_text

    def flaky(self, *a, **k):  # type: ignore[no-untyped-def]
        if self == html_path:
            raise OSError("html fail clean")
        return real_write_text(self, *a, **k)

    raised = False
    err = None
    with patch.object(Path, "write_text", flaky):
        try:
            gr.write_output_pair('{"new":1}\n', "<new/>")
        except OSError as e:
            raised = True
            err = str(e)
    j_ok = json_path.read_bytes() == bak_json
    h_ok = html_path.read_bytes() == bak_html
    json_path.write_bytes(bak_json)
    html_path.write_bytes(bak_html)
    return {
        "raised": raised,
        "err": err,
        "json_preserved": j_ok,
        "html_preserved": h_ok,
    }


r2c = r2_complete_pair_rollback()
results["HTML-R2_complete_pair"] = r2c
if not r2c["raised"] or not r2c["json_preserved"] or not r2c["html_preserved"]:
    failed.append(f"HTML-R2 complete-pair rollback failed: {r2c}")

stale_final = gr.check_stale(bound)
results["final_stale"] = stale_final["status"]
if stale_final["status"] != "CURRENT":
    failed.append(f"final stale not CURRENT: {stale_final}")
if json_path.read_bytes() != bak_json or html_path.read_bytes() != bak_html:
    failed.append("output pair bytes drifted after tests")

results["failed"] = failed
results["verdict"] = "TDD_PASS" if not failed else "TDD_FAIL"
print(json.dumps(results, ensure_ascii=False, indent=2, default=str))
sys.exit(0 if not failed else 1)
