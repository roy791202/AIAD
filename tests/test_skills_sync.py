"""Skills single-source sync: generated copies match and every link resolves."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("sync_skills", ROOT / "tools" / "skills" / "sync_skills.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def test_should_report_in_sync_when_targets_generated():
    assert sync.main(["--check"]) == 0


def test_should_resolve_every_link_in_sources_and_targets():
    targets = sync.build_targets()
    sources = {p: p.read_text(encoding="utf-8") for p in sync.SRC.rglob("*.md")}
    assert sync.broken_links({**sources, **targets}) == []


def test_should_flag_broken_link_when_reference_missing(tmp_path):
    fake = tmp_path / "x.md"
    assert sync.broken_links({fake: "[a](missing.md)"}) == [f"{fake}: 連結不存在 missing.md"]


def test_should_keep_always_loaded_files_small():
    for name in ("AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md", "CLAUDE.md"):
        assert (ROOT / name).stat().st_size < 12_000, name


def test_should_not_touch_frozen_requirements_snapshot():
    assert not any("AI_INSTRUCTIONS" in str(p) for p in sync.build_targets())


def test_should_rewrite_relative_links_to_repo_paths():
    out = sync.to_repo_links("[a](references/x.md) [b](../ai-dev-pipeline/references/y.md)")
    assert out == f"[a]({sync.REF_ROOT}x.md) [b]({sync.REF_ROOT}y.md)"


def test_should_parse_folded_description():
    meta, body = sync.split_frontmatter("---\nname: n\ndescription: >-\n  第一行\n  第二行\n---\n# B\n")
    assert meta["description"] == "第一行 第二行" and body == "# B\n"
