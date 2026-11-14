"""Unit tests for BDD-PD-M4-PACK-SPEC-01 (tools/board/pack_spec.py)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import build_result as br
import pack_spec as ps
import release_report


class TestFieldContract(unittest.TestCase):
    def test_required_fields_present(self):
        row = ps.build_pack_artifact(
            os="win",
            arch="amd64",
            path="packaging/windows/wix/out/x.msi",
            sha256="",
            status="NOT RUN",
        )
        for key in ("os", "arch", "path", "sha256", "status"):
            self.assertIn(key, row)
        self.assertEqual(row["os"], "windows")
        self.assertEqual(row["arch"], "x64")

    def test_status_vocabulary(self):
        for s in ("PASS", "FAIL", "BLOCKED", "NOT RUN", "PARTIAL"):
            self.assertEqual(ps.normalize_status(s), s)
        with self.assertRaises(ps.PackSpecError):
            ps.normalize_status("GREEN")
        with self.assertRaises(ps.PackSpecError):
            ps.normalize_status("success")

    def test_os_arch_aliases_and_reject(self):
        self.assertEqual(ps.normalize_os("darwin"), "macos")
        self.assertEqual(ps.normalize_os("linux"), "linux")
        self.assertEqual(ps.normalize_arch("aarch64"), "arm64")
        with self.assertRaises(ps.PackSpecError):
            ps.normalize_os("freebsd")
        with self.assertRaises(ps.PackSpecError):
            ps.normalize_arch("mips")

    def test_sha256_validation(self):
        good = "a" * 64
        self.assertEqual(ps.normalize_sha256(good), good)
        self.assertEqual(ps.normalize_sha256(""), "")
        with self.assertRaises(ps.PackSpecError):
            ps.normalize_sha256("deadbeef")


class TestNoForgedPass(unittest.TestCase):
    def test_missing_path_cannot_stay_pass(self):
        row = ps.build_pack_artifact(
            os="macos",
            arch="universal",
            path="packaging/macos/out/missing.dmg",
            status="PASS",
            sha256="",
        )
        with tempfile.TemporaryDirectory() as tmp:
            resolved = ps.resolve_artifact_file(row, repo=Path(tmp), status_if_missing="NOT RUN")
        self.assertEqual(resolved["status"], "NOT RUN")
        self.assertFalse(resolved["exists"])

    def test_sha_mismatch_is_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            f = root / "out" / "a.msi"
            f.parent.mkdir(parents=True)
            f.write_bytes(b"hello-pack-spec")
            row = ps.build_pack_artifact(
                os="windows",
                arch="x64",
                path="out/a.msi",
                sha256="0" * 64,
                status="PARTIAL",
            )
            resolved = ps.resolve_artifact_file(row, repo=root)
        self.assertEqual(resolved["status"], "FAIL")
        self.assertEqual(len(resolved["sha256"]), 64)


class TestHangBuildResultAndRelease(unittest.TestCase):
    def test_apply_to_build_result(self):
        spec = ps.default_matrix_v010(generated_at="2026-10-24T12:00:00+08:00")
        result = br.build_result(
            version="0.1.0",
            summary="hang pack",
            artifacts=[{"label": "prior", "path": "other.bin", "exists": False}],
            verification=[{"name": "unit", "status": "PASS"}],
            status="PASS",
            signing_status="NOT RUN",
        )
        # Force PASS then hang — pack NOT RUN/PARTIAL must worsen rollup.
        result["status"] = "PASS"
        ps.apply_to_build_result(result, spec)
        self.assertIn("packSpec", result)
        self.assertEqual(result["packSpec"]["schema"], ps.SCHEMA_ID)
        self.assertIn(ps.BDD_ID, result["requirementTraceability"])
        self.assertEqual(len(result["targetMatrix"]), 3)
        os_set = {r["os"] for r in result["targetMatrix"]}
        self.assertEqual(os_set, {"windows", "macos", "linux"})
        # Worst of PASS + PARTIAL + NOT RUN → at least NOT RUN/PARTIAL (not PASS).
        self.assertNotEqual(result["status"], "PASS")
        paths = {a["path"] for a in result["artifacts"]}
        self.assertIn("other.bin", paths)
        self.assertTrue(any(a.get("os") == "windows" for a in result["artifacts"]))

    def test_to_release_artifacts_shape(self):
        spec = ps.default_matrix_v010()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            arts = ps.to_release_artifacts(spec["artifacts"], repo=root, checked_at="2026-10-24T12:00:00+08:00")
        self.assertEqual(len(arts), 3)
        for a in arts:
            self.assertIn("label", a)
            self.assertIn("path", a)
            self.assertIn("os", a)
            self.assertIn("arch", a)
            self.assertIn("packStatus", a)
            self.assertIn(a["packStatus"], ps.VALID_STATUSES)

    def test_hang_pack_spec_to_release(self):
        snap = {"asOf": "2026-10-24T00:00:00+08:00", "tasks": [], "releases": []}
        html = (
            "<!DOCTYPE html>\n<html><head><title>t</title></head>"
            '<body><div class="nav">導覽</div>'
            '<script type="application/json" id="board-snapshot">\n'
            + json.dumps(snap, ensure_ascii=False, indent=2)
            + "\n</script>\n<script>/* runtime */</script></body></html>\n"
        )
        spec = ps.default_matrix_v010(generated_at="2026-10-24T12:00:00+08:00")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            board = root / "PROJECT-BOARD.html"
            board.write_text(html, encoding="utf-8", newline="\n")
            stored = ps.hang_pack_spec_to_release(
                board,
                spec,
                report_path="reports/dispatch-pd/PD-M4-PACK-SPEC-01.md",
                repo=root,
            )
            self.assertEqual(stored.get("version"), "0.1.0")
            self.assertEqual(stored.get("packSpecStatus"), spec["status"])
            self.assertEqual(stored.get("packSpecSchema"), ps.SCHEMA_ID)
            rels = release_report.list_releases(board)
            self.assertEqual(len(rels), 1)
            self.assertEqual(len(rels[0]["artifacts"]), 3)


class TestSchemaAndDefaultMatrix(unittest.TestCase):
    def test_schema_requires_five_fields(self):
        doc = ps.schema_document()
        self.assertEqual(doc["properties"]["schema"]["const"], ps.SCHEMA_ID)
        required = doc["properties"]["artifacts"]["items"]["required"]
        self.assertEqual(set(required), set(ps.REQUIRED_ARTIFACT_FIELDS))
        self.assertEqual(
            set(doc["properties"]["artifacts"]["items"]["properties"]["status"]["enum"]),
            set(ps.VALID_STATUSES),
        )

    def test_validate_roundtrip_write(self):
        spec = ps.default_matrix_v010(generated_at="2026-10-24T12:00:00+08:00")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pack-spec.v1.json"
            ps.write_pack_spec(spec, path)
            loaded = ps.load_pack_spec(path)
        self.assertEqual(loaded["schema"], ps.SCHEMA_ID)
        self.assertEqual(len(loaded["artifacts"]), 3)
        statuses = {a["status"] for a in loaded["artifacts"]}
        self.assertIn("NOT RUN", statuses)
        # Default matrix must not claim all-PASS.
        self.assertNotEqual(loaded["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
