"""Load glyphs from D:\\AIAD\\icon and tint them with the current theme icon color."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QRect, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from sgenaxis.ui import theme

ROOT = Path(__file__).resolve().parents[2] / "icon"
ACTIONS = ROOT / "qt_all_ui_svg_pack" / "actions"
ENGINE = ROOT / "engine_100_svg_icons"

PATHS = {
    "app": ROOT / "qt_ui_icon.svg",
    "new": ACTIONS / "new_file.svg",
    "open": ACTIONS / "open.svg",
    "save": ACTIONS / "save.svg",
    "save_as": ACTIONS / "save_as.svg",
    "settings": ACTIONS / "settings.svg",
    "help": ACTIONS / "help.svg",
    "search": ACTIONS / "search.svg",
    "close": ACTIONS / "close.svg",
    "undo": ACTIONS / "undo.svg",
    "redo": ACTIONS / "redo.svg",
    "edit": ACTIONS / "edit.svg",
    "agent": ENGINE / "ai" / "agent.svg",
    "deploy": ENGINE / "runtime" / "deploy.svg",
    "module": ENGINE / "core" / "module.svg",
    "design": ENGINE / "render" / "shader.svg",
    "history": ENGINE / "debug" / "log.svg",
    "branch": ENGINE / "runtime" / "graph.svg",
    "play": ENGINE / "tools" / "play.svg",
    "stop": ENGINE / "tools" / "stop.svg",
}

_CACHE: dict[tuple[str, str | None], QIcon] = {}


class _TintedSvgEngine(QIconEngine):
    def __init__(self, svg: str, color: str | None) -> None:
        super().__init__()
        self._svg = svg
        self._color = color

    def clone(self) -> QIconEngine:
        return _TintedSvgEngine(self._svg, self._color)

    def _render(self, size: QSize, mode: QIcon.Mode) -> QImage:
        color = self._color or theme.current()["icon"]
        if mode == QIcon.Disabled:
            color = theme.current()["faint"]
        renderer = QSvgRenderer(QByteArray(self._svg.replace("currentColor", color).encode("utf-8")))
        image = QImage(size, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        painter = QPainter(image)
        renderer.render(painter)
        painter.end()
        return image

    def paint(self, painter: QPainter, rect: QRect, mode: QIcon.Mode, state: QIcon.State) -> None:
        painter.drawImage(rect, self._render(rect.size(), mode))

    def pixmap(self, size: QSize, mode: QIcon.Mode, state: QIcon.State) -> QPixmap:
        return QPixmap.fromImage(self._render(size, mode))


def icon(name: str, color: str | None = None, size: int = 16) -> QIcon:
    """Without an explicit color the glyph re-tints whenever the theme changes."""
    del size
    key = (name, color)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    path = PATHS[name]
    if not path.is_file():
        raise FileNotFoundError(path)
    if name == "app":
        loaded = QIcon(str(path))
    else:
        loaded = QIcon(_TintedSvgEngine(path.read_text(encoding="utf-8"), color))
    _CACHE[key] = loaded
    return loaded
