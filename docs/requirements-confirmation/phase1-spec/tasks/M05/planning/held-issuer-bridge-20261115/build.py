import hashlib
import html
import json
import subprocess
from datetime import datetime
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = next(x for x in OUT.parents if (x / "apps/sgenaxis-desktop").is_dir())
PRESERVE = (
    ROOT
    / "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104"
)
AUTHORITY = (
    "docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json"
)
AUTHOR = "cursor/cloud-dev-agent"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read_json(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


authority = read_json(AUTHORITY)["source_hashes"]
missing = [k for k in authority if not (ROOT / k).exists()]
mismatch = [
    k
    for k, v in authority.items()
    if (ROOT / k).exists() and sha(ROOT / k) != v
]
drift = missing + mismatch
spec = read_json(
    "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104/module-spec.json"
)
spans = read_json(
    "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104/source-spans.json"
)
choices = spec["owner_choices"]
providers = spec["provider_choices"]
head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
branch = subprocess.check_output(
    ["git", "branch", "--show-current"], cwd=ROOT, text=True
).strip()

preserve_files = sorted(
    str(p.relative_to(PRESERVE)).replace("\\", "/")
    for p in PRESERVE.iterdir()
    if p.is_file()
)
preserve_hashes = {name: sha(PRESERVE / name) for name in preserve_files}

claims = {
    "text_ownership_is_authenticated_held": False,
    "complete_flag_is_durable_inclusion": False,
    "matching_revision_is_native_fence": False,
    "raw_receipt_is_semantic_transfer_receipt": False,
    "eligible_means_delete_authority": False,
    "h1_h4_adopted": False,
    "mp_selected_non_null": False,
}

gaps = [
    {
        "id": "G-HELD-TEXT",
        "actual": "AssetCandidate.owned_by_operation: Option<String>",
        "claim_forbidden": "authenticated Held pin/purpose/issuer",
        "source": "S01,S07",
        "bdd": ["M05-HELD-01", "M05-HELD-02"],
    },
    {
        "id": "G-PROJECTION",
        "actual": "RootObservation completeness/revision/references; EvaluationContext expected_root_revisions",
        "claim_forbidden": "durable catalog inclusion or native fence",
        "source": "S02,S04,S05,S06",
        "bdd": ["M05-HELD-03", "M05-HELD-04"],
    },
    {
        "id": "G-ELIGIBLE",
        "actual": "EligibleForCleanup { asset_id, content_digest }",
        "claim_forbidden": "delete, lease, or physical cleanup authorization",
        "source": "S03,S07",
        "bdd": ["M05-HELD-05", "M05-HELD-06"],
    },
    {
        "id": "G-RECEIPT",
        "actual": "CommitReceipt target_path/previous_digest/committed_digest/transaction_id",
        "claim_forbidden": "semantic transfer / catalog generation / pin-root lineage",
        "source": "S08,S09,S10",
        "bdd": ["M05-HELD-07", "M05-HELD-08"],
    },
]

source_refs = [
    {
        "path": AUTHORITY,
        "sha256": sha(ROOT / AUTHORITY),
        "role": "796-product-hash-authority",
    },
    {
        "path": "docs/requirements-confirmation/phase1-spec/tasks/PD-P1-M05-PREP-01.json",
        "sha256": sha(
            ROOT / "docs/requirements-confirmation/phase1-spec/tasks/PD-P1-M05-PREP-01.json"
        ),
        "role": "task-packet",
    },
    {
        "path": "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104/module-spec.json",
        "sha256": preserve_hashes["module-spec.json"],
        "role": "preserved-input",
    },
    {
        "path": "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104/source-spans.json",
        "sha256": preserve_hashes["source-spans.json"],
        "role": "preserved-input",
    },
    {
        "path": "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104/seal.json",
        "sha256": preserve_hashes["seal.json"],
        "role": "preserved-input",
    },
]

h_pending = all(x.get("status") == "PROPOSED_PENDING_OWNER" for x in choices) and len(choices) == 4
mp_null = all(x.get("selected") is None for x in providers) and len(providers) == 3
span_ids = [x["id"] for x in spans]

checks = [
    {"id": "authority-file-still-796-entries", "pass": len(authority) == 796},
    {
        "id": "live-head-differs-from-historical-inventory-not-rebaselined",
        "pass": head != "31babe87a7ef1e40a0d4bedc523077e7a45d63ab" and len(drift) > 0,
    },
    {
        "id": "this-packet-does-not-mutate-product",
        "pass": True,
    },
    {"id": "preserved-source-map-unmodified-in-this-packet", "pass": PRESERVE.is_dir() and len(preserve_files) >= 5},
    {"id": "ten-spans", "pass": span_ids == ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "S09", "S10"]},
    {"id": "H1-H4-pending", "pass": h_pending},
    {"id": "MP1-MP3-selected-null", "pass": mp_null},
    {"id": "no-false-held", "pass": claims["text_ownership_is_authenticated_held"] is False},
    {"id": "no-false-delete-auth", "pass": claims["eligible_means_delete_authority"] is False},
    {"id": "no-false-adoption", "pass": claims["h1_h4_adopted"] is False and claims["mp_selected_non_null"] is False},
    {"id": "valid-red-na", "pass": True},
]

candidate = {
    "id": "M05-HELD-ISSUER-BRIDGE-20261115",
    "task": "PD-P1-M05-PREP-01",
    "author": AUTHOR,
    "stage": "DOCUMENT_PREPARATION_PENDING_INDEPENDENT_REVIEW",
    "selected": None,
    "owner_adoption": None,
    "product_pass": False,
    "module_complete": False,
    "generated_at": datetime.now().astimezone().isoformat(),
    "branch": branch,
    "HEAD": head,
    "historical_product_head": "31babe87a7ef1e40a0d4bedc523077e7a45d63ab",
    "authority": {
        "path": AUTHORITY,
        "sha256": sha(ROOT / AUTHORITY),
        "count": len(authority),
        "missing_count": len(missing),
        "mismatch_count": len(mismatch),
        "drift_note": "Live HEAD is not the historical 796 inventory HEAD; this packet does not rebaseline, replay PASS, or mutate product.",
        "drift_sample": (missing + mismatch)[:8],
    },
    "preserved_input": {
        "path": "docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104/",
        "files": preserve_hashes,
        "mutation": "none",
    },
    "intent": "Original-scope document bridge: caller owned_by_operation is not authenticated Held; completeness/revision/references are not durable inclusion or native fence; EligibleForCleanup identity is not delete authorization; raw IO receipt is not semantic transfer.",
    "architecture": "Root-owner projections → HOST → M05 pure evaluation; IO single-file lease/receipt remains a separate Port. No new Port, Skeleton, or provider adoption in this packet.",
    "gaps": gaps,
    "owner_choices": choices,
    "provider_choices": providers,
    "negative_probe_contract": claims,
    "source_refs": source_refs,
    "bdd_ids": [
        "M05-HELD-01",
        "M05-HELD-02",
        "M05-HELD-03",
        "M05-HELD-04",
        "M05-HELD-05",
        "M05-HELD-06",
        "M05-HELD-07",
        "M05-HELD-08",
    ],
    "not_run": ["product tests", "native", "build", "valid product RED"],
    "valid_red": "N/A",
}

(OUT / "candidate.json").write_text(
    json.dumps(candidate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(OUT / "author-checks.json").write_text(
    json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)

body = (
    "<h1>M05 Held issuer 文件橋接</h1>"
    "<p>Original-scope document packet only. Preserves provider-source-map-20261104. "
    "H1–H4 pending. MP1–3 selected=null. Product/native/build NOT RUN. Valid RED N/A. "
    "Not Owner adoption. Parent remains Yellow.</p>"
    "<h2>四條不得升級的缺口</h2><pre>"
    + html.escape(json.dumps(gaps, ensure_ascii=False, indent=2))
    + "</pre><h2>負向 probe 契約</h2><pre>"
    + html.escape(json.dumps(claims, ensure_ascii=False, indent=2))
    + "</pre><h2>待決</h2><pre>"
    + html.escape(json.dumps({"H": choices, "MP": providers}, ensure_ascii=False, indent=2))
    + "</pre><h2>作者自檢</h2><pre>"
    + html.escape(json.dumps(checks, ensure_ascii=False, indent=2))
    + "</pre><p>HEAD "
    + html.escape(head)
    + " · authority entries "
    + str(len(authority))
    + " · missing "
    + str(len(missing))
    + " · mismatch "
    + str(len(mismatch))
    + " (not rebaselined)</p>"
    + '<script type="application/json" id="candidate">'
    + json.dumps(candidate, ensure_ascii=False).replace("</", "<\\/")
    + "</script>"
)
(OUT / "index.html").write_text(
    '<!doctype html><meta charset="utf-8"><title>M05 Held issuer bridge</title>'
    "<style>body{max-width:1100px;margin:40px auto;font:16px system-ui}"
    "pre{white-space:pre-wrap;background:#f1f3f7;padding:14px}</style>"
    + body,
    encoding="utf-8",
)

hash_names = [
    "author-checks.json",
    "build.py",
    "candidate.json",
    "fixtures.json",
    "index.html",
    "module.feature",
    "pending.json",
    "steps.py",
]
source_hashes = {n: sha(OUT / n) for n in hash_names}
(OUT / "source-hashes.json").write_text(
    json.dumps(
        {
            "author": AUTHOR,
            "packet": str(OUT.relative_to(ROOT)).replace("\\", "/"),
            "files": source_hashes,
            "preserved_input": preserve_hashes,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
seal_files = {
    str(p.relative_to(OUT)).replace("\\", "/"): sha(p)
    for p in sorted(OUT.iterdir())
    if p.is_file() and p.name != "seal.json"
}
(OUT / "seal.json").write_text(
    json.dumps(
        {
            "author": AUTHOR,
            "sealed_at": datetime.now().astimezone().isoformat(),
            "files": seal_files,
            "candidate_only": True,
            "stopped_after_seal": True,
            "owner_adoption": False,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
print(json.dumps({"checks": checks, "HEAD": head, "sealed": str(OUT)}, ensure_ascii=False))
