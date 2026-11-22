"""Generate every tool-specific copy of the AI dev skills from one source.

Source of truth: .agents/skills/<id>/SKILL.md (+ <id>/references/), tracked in git.
Targets: .claude/skills (gitignored, local copy for Claude Code), .clinerules, .windsurf/rules, AGENTS.md, GEMINI.md,
.github/copilot-instructions.md, CLAUDE.md.
AI_INSTRUCTIONS/ is a frozen requirements snapshot and is never touched.

Usage:
  python tools/skills/sync_skills.py          # write targets
  python tools/skills/sync_skills.py --check  # exit 1 if any target is stale or a link is broken
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / ".agents" / "skills"
CLAUDE_SKILLS = ROOT / ".claude" / "skills"
INDEX_ID = "ai-dev-pipeline"
SKILL_IDS = (
    "ai-dev-pipeline",
    "ai-dev-preproduction",
    "ai-dev-implementation",
    "ai-dev-pr-acceptance",
    "ai-dev-production-readiness",
    "ai-dev-product-tests",
)
TESTS_ID = "ai-dev-product-tests"
MANIFEST = ROOT / "docs" / "requirements-confirmation" / "phase1-spec" / "tasks" / "manifest.json"
TEST_REF_SECTIONS = (
    "## 1. 範圍與來源",
    "## 2. 業務規則",
    "## 3. 已有測試對照",
    "## 4. 測試矩陣",
    "## 5. 開發段（RED）",
    "## 6. 驗證段",
    "## 7. 已知衝突",
)
DELIVERY_RE = re.compile(r"^PD-P1-(F\d{2})-DELIVERY-\d{2}$")
REF_ROOT = f".agents/skills/{INDEX_ID}/references/"
GENERATED_NOTE = "<!-- 由 tools/skills/sync_skills.py 自 .agents/skills 產生；請改來源後重跑，不要直接編輯 -->"
LINK_RE = re.compile(r"\]\(([^)#\s]+\.md)(#[^)]*)?\)")


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md 缺少 frontmatter")
    head, body = text[4:].split("\n---\n", 1)
    meta: dict[str, str] = {}
    key = None
    for line in head.splitlines():
        if line.startswith((" ", "\t")) and key:
            meta[key] = (meta[key] + " " + line.strip()).strip()
            continue
        key, _, value = line.partition(":")
        value = value.strip()
        meta[key] = "" if value in (">-", ">", "|", "|-") else value.strip('"')
    return meta, body.lstrip("\n")


def to_repo_links(body: str, target: Path, sid: str = INDEX_ID) -> str:
    """Rewrite skill-relative links (`references/…`, `../<skill>/…`) so they resolve from `target`'s own folder."""
    def rel(path: Path) -> str:
        return os.path.relpath(path, target.parent).replace(os.sep, "/") + "/"
    for other in SKILL_IDS:
        body = body.replace(f"](../{other}/", f"]({rel(SRC / other)}")
    return body.replace("](references/", f"]({rel(SRC / sid / 'references')}")


def load_sources() -> dict[str, tuple[dict[str, str], str, str]]:
    out = {}
    for sid in SKILL_IDS:
        raw = (SRC / sid / "SKILL.md").read_text(encoding="utf-8").replace("\r\n", "\n")
        meta, body = split_frontmatter(raw)
        out[sid] = (meta, body, raw)
    return out


def skill_index(sources) -> str:
    lines = ["## 技能索引", ""]
    for sid in SKILL_IDS:
        lines.append(f"- **{sid}**（`.agents/skills/{sid}/SKILL.md`）：{sources[sid][0]['description']}")
    return "\n".join(lines)


def build_targets() -> dict[Path, str]:
    sources = load_sources()
    targets: dict[Path, str] = {}
    for sid, (meta, body, raw) in sources.items():
        targets[CLAUDE_SKILLS / sid / "SKILL.md"] = raw
        cline = ROOT / ".clinerules" / f"{sid}.md"
        targets[cline] = to_repo_links(body, cline, sid)
        windsurf = ROOT / ".windsurf" / "rules" / f"{sid}.md"
        desc = meta["description"].replace('"', '\\"')
        targets[windsurf] = (
            f'---\ntrigger: model_decision\ndescription: "{desc}"\n---\n{to_repo_links(body, windsurf, sid)}'
        )
        for ref in sorted((SRC / sid / "references").glob("*.md")):
            targets[CLAUDE_SKILLS / sid / "references" / ref.name] = (
                ref.read_text(encoding="utf-8").replace("\r\n", "\n")
            )

    for name in ("AGENTS.md", "GEMINI.md", ".github/copilot-instructions.md"):
        path = ROOT / name
        index_body = to_repo_links(sources[INDEX_ID][1], path)
        targets[path] = "\n\n".join([
            GENERATED_NOTE,
            "# AI 開發流程規則（AI Dev Skills）",
            "> 驗證角色絕對不可以是開發程式角色。本檔只放主索引；各階段與技術細節在下列檔案，需要時才讀。",
            skill_index(sources),
            index_body.replace("# AI 開發主索引", "# 主索引內容", 1),
        ]) + "\n"

    targets[ROOT / "CLAUDE.md"] = "\n\n".join([
        GENERATED_NOTE,
        "# AI 開發流程規則（AI Dev Skills）",
        "> 驗證角色絕對不可以是開發程式角色。",
        skill_index(sources),
        "開工前先載入 `ai-dev-pipeline`（主索引）；它的路由表會指出何時讀 "
        f"`{REF_ROOT}` 底下哪一份技術參考。不要一次讀完全部。",
        "來源在 `.agents/skills`（進版控）；`.claude/skills` 是本機產生的副本（被 gitignore）。"
        "新 clone 或改了來源後執行 `python tools/skills/sync_skills.py`。",
    ]) + "\n"
    return targets


def broken_links(files: dict[Path, str]) -> list[str]:
    errors = []
    resolved = {p.resolve() for p in files}
    for path, text in files.items():
        for m in LINK_RE.finditer(text):
            link = m.group(1)
            if "://" in link:
                continue
            target = (path.parent / link).resolve()  # strict: relative to the file, as GitHub renders it
            if target not in resolved and not target.is_file():
                shown = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
                errors.append(f"{shown}: 連結不存在 {link}")
    return errors


def load_product_test_inputs() -> tuple[list[str], dict[str, str]]:
    ids = json.loads(MANIFEST.read_text(encoding="utf-8"))["ids"]
    refs = {p.name: p.read_text(encoding="utf-8") for p in sorted((SRC / TESTS_ID / "references").glob("*.md"))}
    return ids, refs


def product_test_errors(manifest_ids: list[str], refs: dict[str, str]) -> list[str]:
    """Every reference has all fixed sections; every delivery feature appears in some scope section."""
    errors = []
    scopes = []
    for name, text in refs.items():
        errors += [f"{name}：缺少段落 {s}" for s in TEST_REF_SECTIONS if s not in text]
        if TEST_REF_SECTIONS[0] in text and TEST_REF_SECTIONS[1] in text:
            scopes.append(text.split(TEST_REF_SECTIONS[0], 1)[1].split(TEST_REF_SECTIONS[1], 1)[0])
    for mid in manifest_ids:
        m = DELIVERY_RE.match(mid)
        if m and not any(re.search(rf"\b{m.group(1)}\b", s) for s in scopes):
            errors.append(f"{m.group(1)}：沒有出現在任何產品測試參考檔的「1. 範圍與來源」")
    return errors


MAP_ROW_RE = re.compile(r"^\|[^|\n]*\|([^|\n]*)\|\s*\[[^\]]*\]\(references/([^)]+\.md)\)\s*\|", re.M)


def load_product_test_index() -> str:
    return (SRC / TESTS_ID / "SKILL.md").read_text(encoding="utf-8")


def mapping_errors(manifest_ids: list[str], index_text: str, refs: dict[str, str]) -> list[str]:
    """The SKILL.md mapping table names a primary reference for every delivery feature, and that file exists."""
    rows = MAP_ROW_RE.findall(index_text)
    mapped = {f for features, _ in rows for f in re.findall(r"F\d{2}", features)}
    files = [name for _, name in rows]
    errors = [f"{name}：對照表指向的參考檔不存在" for name in files if name not in refs]
    errors += [f"{name}：沒有列在對照表" for name in refs if name not in files]
    for mid in manifest_ids:
        m = DELIVERY_RE.match(mid)
        if m and m.group(1) not in mapped:
            errors.append(f"{m.group(1)}：對照表沒有對應的參考檔")
    return errors


def is_local_only(path: Path) -> bool:
    return path.is_relative_to(CLAUDE_SKILLS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="只檢查，不寫入；有過期或壞連結回傳 1")
    args = parser.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    targets = build_targets()
    sources = {p: p.read_text(encoding="utf-8") for p in SRC.rglob("*.md")}
    errors = broken_links({**sources, **targets})
    ids, refs = load_product_test_inputs()
    errors += product_test_errors(ids, refs)
    errors += mapping_errors(ids, load_product_test_index(), refs)

    stale = [p for p, text in targets.items()
             if not p.is_file() or p.read_text(encoding="utf-8").replace("\r\n", "\n") != text]
    if args.check:
        # .claude/skills is gitignored and generated per machine; --check covers tracked targets only.
        tracked_stale = [p for p in stale if not is_local_only(p)]
        errors += [f"{p.relative_to(ROOT)}: 與來源不同步" for p in tracked_stale]
        checked = sum(1 for p in targets if not is_local_only(p))
    else:
        for p in stale:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(targets[p], encoding="utf-8", newline="\n")
            print(f"寫入 {p.relative_to(ROOT)}")

    for e in errors:
        print(e, file=sys.stderr)
    if not errors:
        print(f"OK：{checked} 個進版控目標與來源一致" if args.check else f"完成：更新 {len(stale)} 個檔案")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
