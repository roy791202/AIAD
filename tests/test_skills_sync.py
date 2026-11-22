"""Skills single-source sync: generated copies match and every link resolves."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("sync_skills", ROOT / "tools" / "skills" / "sync_skills.py")
sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sync)


def test_should_report_in_sync_when_targets_generated():
    assert sync.main(["--check"]) == 0


def test_should_generate_claude_copies_identical_to_sources():
    targets = sync.build_targets()
    local = {p: t for p, t in targets.items() if sync.is_local_only(p)}
    assert local, "應產生 .claude/skills 副本"
    for path, text in local.items():
        src = sync.SRC / path.relative_to(sync.CLAUDE_SKILLS)
        assert src.read_text(encoding="utf-8").replace("\r\n", "\n") == text, path


def test_should_ignore_local_only_targets_when_checking(monkeypatch, tmp_path):
    monkeypatch.setattr(sync, "CLAUDE_SKILLS", tmp_path / "absent" / ".claude" / "skills")
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


def test_should_rewrite_links_relative_to_each_target_folder():
    body = "[a](references/x.md) [b](../ai-dev-pipeline/references/y.md)"
    root = sync.to_repo_links(body, sync.ROOT / "AGENTS.md")
    nested = sync.to_repo_links(body, sync.ROOT / ".windsurf" / "rules" / "r.md")
    assert root == f"[a]({sync.REF_ROOT}x.md) [b]({sync.REF_ROOT}y.md)"
    assert nested == f"[a](../../{sync.REF_ROOT}x.md) [b](../../{sync.REF_ROOT}y.md)"


def test_should_flag_repo_root_link_in_nested_file():
    nested = sync.ROOT / ".clinerules" / "x.md"
    assert sync.broken_links({nested: f"[a]({sync.REF_ROOT}ux.md)"}) != []


def test_should_parse_folded_description():
    meta, body = sync.split_frontmatter("---\nname: n\ndescription: >-\n  第一行\n  第二行\n---\n# B\n")
    assert meta["description"] == "第一行 第二行" and body == "# B\n"


TESTS_ID = "ai-dev-product-tests"


def test_should_register_product_tests_skill():
    assert TESTS_ID in sync.SKILL_IDS


def test_should_copy_product_tests_references_to_claude_skills():
    targets = sync.build_targets()
    refs = sorted(p.name for p in targets if p.parent == sync.CLAUDE_SKILLS / TESTS_ID / "references")
    assert "m01-project-definition.md" in refs and "ui-parameters.md" in refs and len(refs) == 9


def test_should_rewrite_own_references_for_non_index_skill():
    out = sync.to_repo_links("[m](references/m01.md)", sync.ROOT / "AGENTS.md", TESTS_ID)
    assert out == f"[m](.agents/skills/{TESTS_ID}/references/m01.md)"


def test_should_cover_every_delivery_feature_in_product_tests():
    assert sync.product_test_errors(*sync.load_product_test_inputs()) == []


def _ref(skip: str = "") -> str:
    """A reference with F01 inside the scope section, optionally missing one section."""
    sections = [s for s in sync.TEST_REF_SECTIONS if not (skip and skip in s)]
    return sections[0] + "\nF01\n" + "\n".join(sections[1:]) + "\n"


def test_should_flag_feature_missing_from_product_tests():
    errors = sync.product_test_errors(["PD-P1-F01-DELIVERY-01", "PD-P1-F99-DELIVERY-01"], {"m.md": _ref()})
    assert errors == ["F99：沒有出現在任何產品測試參考檔的「1. 範圍與來源」"]


def test_should_flag_reference_missing_required_section():
    errors = sync.product_test_errors(["PD-P1-F01-DELIVERY-01"], {"m.md": _ref(skip="6.")})
    assert errors == ["m.md：缺少段落 ## 6. 驗證段"]


def test_should_ignore_feature_mentioned_outside_scope_section():
    sections = list(sync.TEST_REF_SECTIONS)
    ref = sections[0] + "\n" + "\n".join(sections[1:]) + "\nF01\n"
    assert sync.product_test_errors(["PD-P1-F01-DELIVERY-01"], {"m.md": ref}) != []
