"""Document oracle for durable-index-options-20261115. No product runner."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
U64_MAX = 18446744073709551615
PENDING_GATES = ("RA-L1", "RA-L2", "RA-L3", "PH-G2", "PH-G3", "PH-G4")
PENDING_MP = ("MP1", "MP2", "MP3", "MP4")
CLOSED_SPANS = ("RS04", "RS05", "RS06")
REQUIRED_FILES = (
    "candidate.json",
    "module.feature",
    "steps.py",
    "fixtures.json",
    "pending.json",
    "index.html",
)


def load_json(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def admit_ordinal(value):
    if value is None or value == "":
        return "REJECT_EMPTY_ORDINAL"
    if not isinstance(value, str) or not value.isdigit():
        return "REJECT_OUT_OF_RANGE_ORDINAL"
    number = int(value)
    if number > U64_MAX:
        return "REJECT_OUT_OF_RANGE_ORDINAL"
    return "ADMITTED_PENDING_FORMULA"


def reject_published_as_index(flag) -> str:
    if flag:
        return "REJECT_PUBLISHED_AS_DURABLE_INDEX"
    return "KEEP_PUBLISHED_AS_TRUSTED_HOST_EVENT"


def reject_local_baseline_as_replay(flag) -> str:
    if flag:
        return "REJECT_LOCAL_BASELINE_AS_ATOMIC_REPLAY"
    return "KEEP_LOCAL_BASELINE_DISTINCT"


def reject_captured_attempt_formula(value) -> str:
    if value:
        return "REJECT_CAPTURED_ATTEMPT_ORDINAL_FORMULA"
    return "KEEP_NO_ORDINAL_FORMULA"


def reject_false_native_restart(native) -> str:
    status = None
    if isinstance(native, dict):
        status = native.get("restart")
    if status in ("PASS", "GREEN", True):
        return "REJECT_FALSE_NATIVE_RESTART_PASS"
    if status not in (None, "NOT RUN", "NOT_RUN"):
        return "REJECT_FALSE_NATIVE_RESTART_PASS"
    return "NATIVE_RESTART_NOT_RUN"


def evaluate_candidate(candidate: dict) -> list[str]:
    errors = []
    if candidate.get("selected") is not None or candidate.get("product_pass") is True:
        errors.append("false adoption or product_pass")
    if candidate.get("owner_adoption") not in (None,):
        errors.append("owner adoption must remain null")
    ordinal = candidate.get("ordinal_admission") or {}
    if ordinal.get("formula_selected") is not None:
        errors.append("ordinal formula must remain unselected")
    if ordinal.get("empty") != "REJECT" or ordinal.get("out_of_range") != "REJECT":
        errors.append("empty/out-of-range ordinal must reject")
    if ordinal.get("captured_attempt_computes_ordinal") is not False:
        errors.append("CapturedAttempt must not compute ordinal")
    gates = candidate.get("gates") or {}
    for gate in PENDING_GATES:
        if gates.get(gate) is not None:
            errors.append("gate not null: " + gate)
    for bridge in candidate.get("bridges") or []:
        if bridge.get("id") in PENDING_MP and bridge.get("selected") is not None:
            errors.append("MP selected: " + str(bridge.get("id")))
    cites = {row.get("id"): row for row in candidate.get("closed_span_citations") or []}
    for span in CLOSED_SPANS:
        row = cites.get(span)
        if not row or row.get("action") != "CITE_ONLY_NOT_REOPENED":
            errors.append("must cite-only " + span)
    preserved = candidate.get("preserved_closed_packet") or {}
    if preserved.get("reopened") is not False:
        errors.append("closed 20261104 packet must not reopen")
    not_run = set(candidate.get("not_run") or [])
    for item in ("native timer", "native capture", "native restart", "product tests", "build"):
        if item not in not_run:
            errors.append("missing NOT RUN: " + item)
    return errors


def run_fixtures(candidate: dict, fixtures: dict) -> list[dict]:
    results = []
    for case in fixtures["cases"]:
        cid = case["id"]
        if cid == "M07-IDX-01":
            actual = admit_ordinal(case["input"]["ordinal"])
        elif cid == "M07-IDX-02":
            actuals = [admit_ordinal(row["ordinal"]) for row in case["input_mutations"]]
            actual = (
                "REJECT_OUT_OF_RANGE_ORDINAL"
                if actuals and all(item == "REJECT_OUT_OF_RANGE_ORDINAL" for item in actuals)
                else actuals
            )
        elif cid == "M07-IDX-03":
            actual = reject_published_as_index(True)
        elif cid == "M07-IDX-04":
            actual = reject_local_baseline_as_replay(True)
        elif cid == "M07-IDX-05":
            actual = reject_captured_attempt_formula("revision-as-ordinal")
        elif cid == "M07-IDX-06":
            actual = reject_false_native_restart({"restart": "PASS"})
        elif cid == "M07-IDX-07":
            actual = (
                "ALL_PENDING_GATES_NULL"
                if not evaluate_candidate(candidate)
                else "PENDING_GATES_NOT_NULL"
            )
        elif cid == "M07-IDX-08":
            cites = {row.get("id") for row in candidate.get("closed_span_citations") or []}
            actual = (
                "CITE_ONLY_RS04_RS05_RS06"
                if cites == set(CLOSED_SPANS)
                else "SPAN_CITATION_DRIFT"
            )
        else:
            actual = "UNKNOWN_CASE"
        expected = case["expected"]
        results.append(
            {
                "id": cid,
                "expected": expected,
                "actual": actual,
                "pass": actual == expected,
            }
        )
    return results


def main() -> int:
    missing = [name for name in REQUIRED_FILES if not (OUT / name).is_file()]
    if missing:
        print("FAIL missing files " + ",".join(missing))
        return 1
    candidate = load_json("candidate.json")
    fixtures = load_json("fixtures.json")
    pending = load_json("pending.json")
    errors = evaluate_candidate(candidate)
    if pending.get("mp_selection") != {key: None for key in PENDING_MP}:
        errors.append("pending MP selection drift")
    results = run_fixtures(candidate, fixtures)
    failed = [row for row in results if not row["pass"]]
    payload = {
        "verdict": "PASS_DOCUMENT_ORACLE_ONLY" if not errors and not failed else "FAIL",
        "product": "NOT RUN",
        "native": "NOT RUN",
        "build": "NOT RUN",
        "errors": errors,
        "cases": results,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["verdict"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
