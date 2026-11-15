#!/usr/bin/env python3
"""Synthetic byte supplier for PD-P1-M03-MEDIA-FIXTURE-01. Does not decode or adopt formats."""
from __future__ import annotations

import hashlib
import json
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIX = ROOT / "fixtures"
OPTIONS_SPEC = (
    ROOT.parent
    / "media-capability-options-20261104"
    / "module-spec.json"
)
REVIEW_RESULTS = (
    ROOT.parent
    / "media-capability-options-review-20261104"
    / "results.json"
)

UNKNOWN_MAGIC = b"UNKN\x00SYNTHETIC-NOT-A-DECODER\x00"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes())


def png_1x1() -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    raw = b"\x00" + bytes([0, 0, 0, 255])
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def jpeg_1x1() -> bytes:
    # Minimal JFIF SOI + APP0 + SOF0 1x1 gray + SOS + one dummy MCU + EOI.
    app0 = b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
    sof = b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
    sos = b"\xff\xda\x00\x08\x01\x01\x00\x00\x3f\x00"
    return b"\xff\xd8" + app0 + sof + sos + b"\x7f\xff\xd9"


def svg_inert() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1">'
        b'<rect width="1" height="1" fill="#000"/>'
        b"</svg>"
    )


def gif_single_frame() -> bytes:
    # GIF89a 1x1, 2-color, one graphic, trailer. Synthetic identity only.
    header = b"GIF89a" + struct.pack("<HH", 1, 1) + b"\x80\x00\x00"
    palette = b"\x00\x00\x00\xff\xff\xff"
    image = b"\x2c" + struct.pack("<HHHH", 0, 0, 1, 1) + b"\x00"
    data = b"\x02\x02\x4c\x01\x00"
    return header + palette + image + data + b"\x3b"


def gif_two_frame_identity() -> bytes:
    # Two identical 1x1 frames + NETSCAPE loop. Timing metadata in provenance only.
    header = b"GIF89a" + struct.pack("<HH", 1, 1) + b"\x80\x00\x00"
    palette = b"\x00\x00\x00\xff\xff\xff"
    netscape = b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
    gce = b"\x21\xf9\x04\x00\x0a\x00\x00\x00"
    image = b"\x2c" + struct.pack("<HHHH", 0, 0, 1, 1) + b"\x00" + b"\x02\x02\x4c\x01\x00"
    return header + palette + netscape + gce + image + gce + image + b"\x3b"


def mp4_ftyp_identity() -> bytes:
    # Container identity only. Codec unselected (null). Not a playable movie.
    ftyp = b"isomiso2mp41"
    size = 8 + 4 + 4 + len(ftyp)
    return struct.pack(">I", size) + b"ftyp" + b"isom" + struct.pack(">I", 0) + ftyp


def wav_silent_pcm() -> bytes:
    # RIFF WAVE PCM 8-bit mono 8000 Hz, one silent sample. Audible vs metadata OPEN.
    fmt = struct.pack("<HHIIHH", 1, 1, 8000, 8000, 1, 8)
    data = b"\x80"
    riff_size = 4 + (8 + len(fmt)) + (8 + len(data))
    return (
        b"RIFF"
        + struct.pack("<I", riff_size)
        + b"WAVE"
        + b"fmt "
        + struct.pack("<I", len(fmt))
        + fmt
        + b"data"
        + struct.pack("<I", len(data))
        + data
    )


def opaque_bytes() -> bytes:
    return b"M03-OPAQUE-SYNTHETIC\x00\x01\x02\x03\x04\x05" + bytes(range(16, 32))


def unresolved_identity() -> bytes:
    payload = {
        "kind": "unresolved-material-binding",
        "materialId": "M03-UNRES-STABLE-01",
        "bytes": None,
        "fetch": False,
        "placeholder": "inert",
        "h2_adopted": False,
        "note": "Identity only. No media body. No network fetch.",
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def communication_preview_identity() -> bytes:
    payload = {
        "kind": "selection-only-communication-preview",
        "docIds": ["DOC-STABLE-A", "DOC-STABLE-B"],
        "duplicateNames": True,
        "product_pass": False,
        "c1_adopted": False,
        "mm08_adopted": False,
        "generatedPath": None,
        "nativeScreenshot": "NOT RUN",
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def truncate_before_header_complete(data: bytes) -> bytes:
    if len(data) <= 4:
        return data[:1] if data else b""
    cut = min(7, max(3, len(data) // 4))
    return data[:cut]


def write_bytes(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return {
        "path": str(path.relative_to(ROOT)).replace("\\", "/"),
        "bytes": len(data),
        "sha256": sha256(data),
    }


def specimen(
    row_id: str,
    family: str,
    format_label: str,
    variant: str,
    filename: str,
    data: bytes,
    parent: dict | None,
    notes: str,
) -> dict:
    rec = write_bytes(FIX / filename, data)
    rec.update(
        {
            "rowId": row_id,
            "family": family,
            "format_label": format_label,
            "format": None,
            "sdk": None,
            "thresholds": None,
            "variant": variant,
            "provenance": "synthetic",
            "native_decode_render": "NOT RUN",
            "imported_format_support": "NOT_PROVEN",
            "owner_selection": None,
            "adopted": False,
            "decoder_proof": False,
            "notes": notes,
            "parent_sha256": parent["sha256"] if parent else None,
            "parent_path": parent["path"] if parent else None,
        }
    )
    return rec


def main() -> None:
    FIX.mkdir(parents=True, exist_ok=True)
    options = json.loads(OPTIONS_SPEC.read_text(encoding="utf-8"))
    review = json.loads(REVIEW_RESULTS.read_text(encoding="utf-8"))
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    rows_meta = {r["id"]: r for r in options["rows"]}
    entries: list[dict] = []

    def triple(row_id, family, format_label, valid_name, valid_bytes, notes_valid, trunc_name, unk_name):
        valid = specimen(row_id, family, format_label, "valid-minimal", valid_name, valid_bytes, None, notes_valid)
        trunc = specimen(
            row_id,
            family,
            format_label,
            "invalid-truncated",
            trunc_name,
            truncate_before_header_complete(valid_bytes),
            valid,
            "Truncated before header completion. Parent digest recorded. Not a decode result.",
        )
        unk = specimen(
            row_id,
            family,
            format_label,
            "unknown-magic",
            unk_name,
            UNKNOWN_MAGIC + row_id.encode("ascii") + b"\x00" + format_label.encode("ascii"),
            None,
            "Unknown magic. Synthetic identity only. Not a decode result.",
        )
        entries.extend([valid, trunc, unk])

    mm01 = rows_meta["MM01"]
    triple(
        "MM01",
        mm01["family"],
        "png-candidate-unselected",
        "mm01-png-valid-minimal.png",
        png_1x1(),
        "Synthetic 1x1 PNG identity. PNG not adopted. Bundled shell PNG is not this specimen.",
        "mm01-png-invalid-truncated.png",
        "mm01-png-unknown-magic.bin",
    )
    triple(
        "MM01",
        mm01["family"],
        "jpeg-candidate-unselected",
        "mm01-jpeg-valid-minimal.jpg",
        jpeg_1x1(),
        "Synthetic 1x1 JPEG identity acquired separately from PNG. JPEG not adopted.",
        "mm01-jpeg-invalid-truncated.jpg",
        "mm01-jpeg-unknown-magic.bin",
    )

    mm02 = rows_meta["MM02"]
    triple(
        "MM02",
        mm02["family"],
        "svg-candidate-unselected",
        "mm02-svg-valid-minimal.svg",
        svg_inert(),
        "Synthetic inert SVG identity. Not shell icon trust. Sanitization/policy unselected.",
        "mm02-svg-invalid-truncated.svg",
        "mm02-svg-unknown-magic.bin",
    )

    mm03 = rows_meta["MM03"]
    gif1 = gif_single_frame()
    valid_gif = specimen(
        "MM03",
        mm03["family"],
        "gif-candidate-unselected",
        "valid-minimal-single-frame",
        "mm03-gif-valid-minimal-single-frame.gif",
        gif1,
        None,
        "Synthetic single-frame GIF identity plus declared timing metadata in provenance. Format not adopted.",
    )
    gif2 = gif_two_frame_identity()
    valid_gif2 = specimen(
        "MM03",
        mm03["family"],
        "gif-candidate-unselected",
        "valid-minimal-multi-frame-identity",
        "mm03-gif-valid-minimal-multi-frame.gif",
        gif2,
        None,
        "Synthetic two-frame identity. Frame delay recorded as metadata only (10 cs). Not native timing proof.",
    )
    trunc = specimen(
        "MM03",
        mm03["family"],
        "gif-candidate-unselected",
        "invalid-truncated",
        "mm03-gif-invalid-truncated.gif",
        truncate_before_header_complete(gif1),
        valid_gif,
        "Truncated before header completion. Parent is single-frame identity.",
    )
    unk = specimen(
        "MM03",
        mm03["family"],
        "gif-candidate-unselected",
        "unknown-magic",
        "mm03-gif-unknown-magic.bin",
        UNKNOWN_MAGIC + b"MM03\x00gif-candidate-unselected",
        None,
        "Unknown magic. Synthetic identity only.",
    )
    valid_gif["timing_metadata"] = {"frame_count": 1, "frame_delay_cs": None, "loop": None}
    valid_gif2["timing_metadata"] = {"frame_count": 2, "frame_delay_cs": 10, "loop": 0}
    entries.extend([valid_gif, valid_gif2, trunc, unk])

    mm04 = rows_meta["MM04"]
    triple(
        "MM04",
        mm04["family"],
        "isom-ftyp-container-candidate-unselected",
        "mm04-mp4-ftyp-valid-minimal.bin",
        mp4_ftyp_identity(),
        "Synthetic ISO BMFF ftyp identity. Container label recorded; codec remains null. Not playback-valid.",
        "mm04-mp4-ftyp-invalid-truncated.bin",
        "mm04-mp4-unknown-magic.bin",
    )

    mm05 = rows_meta["MM05"]
    triple(
        "MM05",
        mm05["family"],
        "wav-pcm-candidate-unselected",
        "mm05-wav-valid-minimal-silent.wav",
        wav_silent_pcm(),
        "Synthetic silent PCM identity. Audible versus metadata-only behavior unselected. Not playback proof.",
        "mm05-wav-invalid-truncated.wav",
        "mm05-wav-unknown-magic.bin",
    )

    mm06 = rows_meta["MM06"]
    opaque = opaque_bytes()
    valid_op = specimen(
        "MM06",
        mm06["family"],
        "opaque-untyped",
        "valid-minimal-opaque",
        "mm06-opaque-valid-minimal.bin",
        opaque,
        None,
        "Arbitrary immutable opaque bytes. Extension/MIME conflict specimens recorded as sibling files.",
    )
    trunc_op = specimen(
        "MM06",
        mm06["family"],
        "opaque-untyped",
        "invalid-truncated",
        "mm06-opaque-invalid-truncated.bin",
        truncate_before_header_complete(opaque),
        valid_op,
        "Truncated opaque body.",
    )
    unk_op = specimen(
        "MM06",
        mm06["family"],
        "opaque-untyped",
        "unknown-magic",
        "mm06-opaque-unknown-magic.bin",
        UNKNOWN_MAGIC + b"MM06\x00opaque-untyped",
        None,
        "Unknown magic opaque identity.",
    )
    conflict_ext = specimen(
        "MM06",
        mm06["family"],
        "opaque-untyped",
        "extension-mime-conflict",
        "mm06-opaque-extension-conflict.png",
        opaque,
        valid_op,
        "Same opaque digest as .bin, PNG-looking extension. MIME unselected. Not a decoder claim. (.exe omitted: repo gitignore.)",
    )
    entries.extend([valid_op, trunc_op, unk_op, conflict_ext])

    mm07 = rows_meta["MM07"]
    ident = unresolved_identity()
    triple(
        "MM07",
        mm07["family"],
        "unresolved-identity-json",
        "mm07-unresolved-valid-minimal.json",
        ident,
        "Stable unresolved binding identity. No media body. H2 not adopted. No fetch fallback.",
        "mm07-unresolved-invalid-truncated.json",
        "mm07-unresolved-unknown-magic.bin",
    )

    mm08 = rows_meta["MM08"]
    preview = communication_preview_identity()
    triple(
        "MM08",
        mm08["family"],
        "communication-preview-identity-json",
        "mm08-preview-valid-minimal.json",
        preview,
        "Selection-only communication identity. C1/MM08 not adopted. product_pass remains false. Native screenshot NOT RUN.",
        "mm08-preview-invalid-truncated.json",
        "mm08-preview-unknown-magic.bin",
    )

    coverage = {}
    for e in entries:
        coverage.setdefault(e["rowId"], set()).add(e["variant"].split("-")[0] if False else e["variant"])
    required = {"valid-minimal", "invalid-truncated", "unknown-magic"}
    # MM01 has two format labels; MM03 extra multi-frame; MM06 extra conflict.
    row_ok = []
    for rid in [f"MM0{i}" for i in range(1, 9)]:
        vars_ = {e["variant"] for e in entries if e["rowId"] == rid}
        has_core = (
            any(v.startswith("valid-minimal") for v in vars_)
            and "invalid-truncated" in vars_
            and "unknown-magic" in vars_
        )
        row_ok.append({"rowId": rid, "variants": sorted(vars_), "core_triple": has_core})

    provenance = {
        "task": "PD-P1-M03-MEDIA-FIXTURE-01",
        "author": "fixture-provider-media-bytes-20261115",
        "reviewer": None,
        "layer": "DOCUMENT_ONLY",
        "status": "SYNTHETIC_BYTES_DELIVERED_PENDING_INDEPENDENT_REVIEW",
        "generated_at": generated_at,
        "scope": "Only this new directory; no product/test/spec/board/hook/role modifications",
        "adopted": {
            "MM01": False,
            "MM02": False,
            "MM03": False,
            "MM04": False,
            "MM05": False,
            "MM06": False,
            "MM07": False,
            "MM08": False,
            "C1": False,
            "H2": False,
        },
        "format": None,
        "sdk": None,
        "thresholds": None,
        "owner_selection": None,
        "approval": None,
        "module_complete": False,
        "imported_format_support": "NOT_PROVEN",
        "native_decode_render": "NOT RUN",
        "product_native_decode_render_build": "NOT RUN",
        "historical_pass_suites": "NOT RERUN",
        "valid_red": "N/A_DOCUMENT_ONLY",
        "tdd": "NOT SELF-GREEN",
        "provenance_kind": "synthetic",
        "decoder_proof": False,
        "options_packet": {
            "path": "docs/requirements-confirmation/phase1-spec/tasks/M03/planning/media-capability-options-20261104/module-spec.json",
            "sha256": file_sha256(OPTIONS_SPEC),
            "status": options.get("status"),
        },
        "options_review": {
            "path": "docs/requirements-confirmation/phase1-spec/tasks/M03/planning/media-capability-options-review-20261104/results.json",
            "sha256": file_sha256(REVIEW_RESULTS),
            "result": review.get("result"),
        },
        "rows": options["rows"],
        "options": options["options"],
        "specimens": entries,
        "coverage": row_ok,
        "limitations": [
            "Bytes are synthetic identities for later independent native verification.",
            "Presence of PNG/JPEG/SVG/GIF/ftyp/WAV-shaped bytes is not native support, SDK reuse, or Owner selection.",
            "MM01 PNG and JPEG remain separately unselected.",
            "MM04 records container identity only; codec stays null.",
            "MM07 supplies unresolved identity JSON, not fake media.",
            "C1 and H2 remain unadopted.",
        ],
    }
    (ROOT / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    module_spec = {
        "module": "M03",
        "task": "PD-P1-M03-MEDIA-FIXTURE-01",
        "author": "fixture-provider-media-bytes-20261115",
        "reviewer": None,
        "status": "SYNTHETIC_BYTES_DELIVERED_PENDING_INDEPENDENT_REVIEW",
        "layer": "DOCUMENT_ONLY",
        "generated_at": generated_at,
        "scope": "Only this new directory; no product/test/spec/board/hook/role modifications",
        "owner_selection": None,
        "format": None,
        "sdk": None,
        "thresholds": None,
        "approval": None,
        "module_complete": False,
        "imported_format_support": "NOT_PROVEN",
        "native_decode_render": "NOT RUN",
        "build_package_install_dcc_regression": "NOT RUN",
        "valid_red": "N/A_DOCUMENT_ONLY",
        "tdd": "NOT SELF-GREEN",
        "adopted_mm01_mm08": False,
        "adopted_c1": False,
        "adopted_h2": False,
        "decoder_proof": False,
        "provenance": "synthetic",
        "options_packet_sha256": file_sha256(OPTIONS_SPEC),
        "options_review_sha256": file_sha256(REVIEW_RESULTS),
        "specimens": [
            {
                "rowId": e["rowId"],
                "format_label": e["format_label"],
                "variant": e["variant"],
                "path": e["path"],
                "sha256": e["sha256"],
                "bytes": e["bytes"],
                "format": None,
                "sdk": None,
                "thresholds": None,
            }
            for e in entries
        ],
        "acceptance": [
            "Each options-packet row has valid-minimal, invalid-truncated, and unknown-magic synthetic bytes",
            "sha256 recorded in provenance.json",
            "provenance is synthetic; not native decoder proof",
            "SDK and threshold fields remain null",
            "MM01-MM08, C1, H2 not adopted",
        ],
    }
    (ROOT / "module-spec.json").write_text(
        json.dumps(module_spec, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    def esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    rows_html = []
    for e in entries:
        rows_html.append(
            "<tr>"
            f"<td>{esc(e['rowId'])}</td>"
            f"<td>{esc(e['format_label'])}</td>"
            f"<td>{esc(e['variant'])}</td>"
            f"<td><a href=\"{esc(e['path'])}\">{esc(e['path'])}</a></td>"
            f"<td><code>{esc(e['sha256'])}</code></td>"
            f"<td>{e['bytes']}</td>"
            "</tr>"
        )

    html = f"""<!doctype html>
<meta charset="utf-8">
<title>M03 synthetic media fixture bytes 20261115</title>
<style>
body{{font:16px system-ui;margin:36px;line-height:1.5;max-width:1200px}}
table{{border-collapse:collapse;width:100%}}
td,th{{padding:8px;border:1px solid #bbb;vertical-align:top;font-size:13px}}
code{{word-break:break-all}}
h1{{color:#805900}}
.banner{{background:#fff3cd;border:1px solid #856404;padding:12px}}
</style>
<h1>M03 synthetic media fixture bytes</h1>
<p class="banner"><b>DOCUMENT ONLY.</b> Provenance = synthetic. Native decode/render <b>NOT RUN</b>.
Imported format support <b>NOT_PROVEN</b>. format/sdk/thresholds = null.
MM01–MM08, C1, H2 <b>not adopted</b>. TDD not self-green.</p>
<p>Task <code>PD-P1-M03-MEDIA-FIXTURE-01</code> · generated_at {esc(generated_at)} ·
author fixture-provider-media-bytes-20261115 · reviewer null</p>
<p>Inputs: options packet
<code>media-capability-options-20261104/module-spec.json</code>
({esc(file_sha256(OPTIONS_SPEC)[:16])}…) · review
<code>results.json</code> ({esc(review.get("result") or "")}).</p>
<h2>Specimens</h2>
<table>
<tr><th>Row</th><th>Format label (unselected)</th><th>Variant</th><th>Path</th><th>sha256</th><th>bytes</th></tr>
{''.join(rows_html)}
</table>
<h2>Structured evidence</h2>
<p><a href="provenance.json">provenance.json</a> · <a href="module-spec.json">module-spec.json</a> · <a href="fixtures/">fixtures/</a></p>
<script type="application/json" id="module-spec">{json.dumps(module_spec, ensure_ascii=False)}</script>
"""
    (ROOT / "index.html").write_text(html, encoding="utf-8")
    print(json.dumps({"specimens": len(entries), "coverage": row_ok}, indent=2))


if __name__ == "__main__":
    main()
