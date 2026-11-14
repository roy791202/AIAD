"""PD-SHELL-CSS-01 — static token asserts vs Workbench :root.

BDD-PD-SHELL-CSS-01: styles.css tokens align with Workbench (color / type /
sidebar width / Inspector width); main∶Inspector ratio near prototype;
a11y focus retained. Does not rewrite Workbench HTML.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSS = ROOT / "apps" / "sgenaxis-desktop" / "ui" / "styles.css"
WORKBENCH = ROOT / "git_workbench_interactive.html"

# Tokens that must match Workbench :root by name + value.
SHARED_TOKENS = (
    "--bg-window",
    "--bg-sidebar",
    "--bg-panel",
    "--bg-hover",
    "--text-secondary",
    "--text-muted",
    "--font-ui",
    "--font-mono",
    "--sidebar-w",
    "--inspector-w",
)

# Workbench names that must exist in styles.css (aliases) with same values.
WORKBENCH_ALIASES = (
    "--bg-panel-raised",
    "--bg-panel-active",
    "--border-color",
    "--border-focus",
    "--text-primary",
    "--color-blue",
    "--color-blue-hover",
    "--color-green",
    "--color-red",
    "--color-yellow",
    "--status-gray",
)


def _root_block(text: str) -> str:
    m = re.search(r":root\s*\{", text)
    assert m, ":root block missing"
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
        i += 1
    return text[start : i - 1]


def _parse_vars(block: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for m in re.finditer(
        r"(--[a-z0-9-]+)\s*:\s*([^;]+);", block, flags=re.IGNORECASE
    ):
        found[m.group(1).lower()] = re.sub(r"\s+", " ", m.group(2).strip())
    return found


def _resolve(vars_map: dict[str, str], name: str, _seen: set[str] | None = None) -> str:
    """Resolve simple var(--x) chains to a concrete value."""
    seen = _seen or set()
    key = name.lower()
    assert key in vars_map, f"missing token {name}"
    val = vars_map[key]
    m = re.fullmatch(r"var\(\s*(--[a-z0-9-]+)\s*\)", val, flags=re.IGNORECASE)
    if not m:
        return val
    ref = m.group(1).lower()
    assert ref not in seen, f"cycle resolving {name}"
    seen.add(ref)
    return _resolve(vars_map, ref, seen)


def test_assets_exist():
    assert CSS.is_file(), f"missing {CSS}"
    assert WORKBENCH.is_file(), f"missing {WORKBENCH}"


def test_shared_tokens_match_workbench_root():
    wb = _parse_vars(_root_block(WORKBENCH.read_text(encoding="utf-8")))
    shell = _parse_vars(_root_block(CSS.read_text(encoding="utf-8")))
    for name in SHARED_TOKENS:
        assert name in wb, f"Workbench missing {name}"
        assert name in shell, f"styles.css missing {name}"
        assert _resolve(shell, name) == wb[name], (
            f"{name}: shell={_resolve(shell, name)!r} workbench={wb[name]!r}"
        )


def test_workbench_alias_tokens_present_and_aligned():
    wb = _parse_vars(_root_block(WORKBENCH.read_text(encoding="utf-8")))
    shell = _parse_vars(_root_block(CSS.read_text(encoding="utf-8")))
    for name in WORKBENCH_ALIASES:
        assert name in wb, f"Workbench missing {name}"
        assert name in shell, f"styles.css missing Workbench alias {name}"
        assert _resolve(shell, name) == wb[name], (
            f"{name}: shell={_resolve(shell, name)!r} workbench={wb[name]!r}"
        )


def test_sidebar_and_inspector_widths_are_workbench_density():
    shell = _parse_vars(_root_block(CSS.read_text(encoding="utf-8")))
    assert _resolve(shell, "--sidebar-w") == "240px"
    assert _resolve(shell, "--inspector-w") == "390px"


def test_body_uses_workbench_type_scale():
    css = CSS.read_text(encoding="utf-8")
    # Density: base UI type matches Workbench body (13px / 1.45).
    assert re.search(
        r"body\s*\{[^}]*font-size:\s*13px", css, flags=re.DOTALL
    ), "body font-size must be 13px (Workbench)"
    assert re.search(
        r"body\s*\{[^}]*line-height:\s*1\.45", css, flags=re.DOTALL
    ), "body line-height must be 1.45 (Workbench)"


def test_main_inspector_grid_uses_token_widths():
    css = CSS.read_text(encoding="utf-8")
    # Main∶Inspector ratio via tokens (240 / 390 ≈ Workbench), not hardcoded px.
    assert re.search(
        r"grid-template-columns:\s*var\(--sidebar-w\)(?:\s+var\(--split-grip\))?\s+minmax\(0,\s*1fr\)",
        css,
    ), ".body grid must use --sidebar-w (+ optional split-grip) / fr"


def test_a11y_focus_visible_retained():
    css = CSS.read_text(encoding="utf-8")
    assert "focus-visible" in css
    assert re.search(
        r":focus-visible\s*\{[^}]*outline:\s*2px\s+solid\s+var\(--(?:accent|border-focus|color-blue)\)",
        css,
        flags=re.DOTALL,
    ), "keyboard focus ring must remain visible (accent / border-focus)"
