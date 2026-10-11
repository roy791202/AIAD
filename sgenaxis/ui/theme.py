"""QSS for the workbench. Every surface follows the UI style; the accent follows the tone."""

from __future__ import annotations

PALETTES = {
    "dark": {
        "window": "#101112",
        "sidebar": "#141618",
        "panel": "#1b1d1f",
        "hover": "#282c32",
        "border": "#34383e",
        "text": "#eef0f3",
        "secondary": "#c5ccd4",
        "muted": "#aeb5bf",
        "faint": "#8b949e",
        "input": "#1a1d22",
        "menubar": "#101215",
        "toolbar": "#14171c",
        "statusbar": "#0c0e11",
        "surface": "#151719",
        "deep": "#101214",
        "canvas": "#101214",
        "code": "#121417",
        "node_detail": "#d6dae0",
        "node_divider": "#2a2e33",
        "port_hole": "#1d2024",
        "edge": "#8b939e",
        "edge_hover": "#c9d1d9",
        "icon": "#c5ccd4",
    },
    "light": {
        "window": "#f4f6f8",
        "sidebar": "#e7ebf0",
        "panel": "#ffffff",
        "hover": "#e4e8ee",
        "border": "#d3d8e0",
        "text": "#1c2128",
        "secondary": "#4e5864",
        "muted": "#6d7682",
        "faint": "#8a929c",
        "input": "#ffffff",
        "menubar": "#ffffff",
        "toolbar": "#ffffff",
        "statusbar": "#ffffff",
        "surface": "#ffffff",
        "deep": "#f9fafb",
        "canvas": "#eef1f4",
        "code": "#f4f6f8",
        "node_detail": "#2f3742",
        "node_divider": "#e1e5ea",
        "port_hole": "#ffffff",
        "edge": "#8a929c",
        "edge_hover": "#4e5864",
        "icon": "#4e5864",
    },
    "gray": {
        "window": "#2b3036",
        "sidebar": "#343a42",
        "panel": "#3b424b",
        "hover": "#4a525c",
        "border": "#5b6470",
        "text": "#f3f5f7",
        "secondary": "#c5ccd4",
        "muted": "#9aa3ad",
        "faint": "#9aa3ad",
        "input": "#2b3036",
        "menubar": "#3b424b",
        "toolbar": "#3b424b",
        "statusbar": "#3b424b",
        "surface": "#343a42",
        "deep": "#2b3036",
        "canvas": "#2b3036",
        "code": "#2b3036",
        "node_detail": "#e3e7ec",
        "node_divider": "#4a525c",
        "port_hole": "#2b3036",
        "edge": "#9aa3ad",
        "edge_hover": "#e3e7ec",
        "icon": "#d5dae0",
    },
}

ACCENTS = {
    "blue": {"accent": "#246bff", "hover": "#3b7cff", "subtle": "rgba(36, 107, 255, 0.22)", "text": "#8bb8ff"},
    "gray": {"accent": "#7d8694", "hover": "#949eac", "subtle": "rgba(125, 134, 148, 0.22)", "text": "#b6bec9"},
    "beige": {"accent": "#b08968", "hover": "#c4a484", "subtle": "rgba(176, 137, 104, 0.24)", "text": "#d4b896"},
    "iron": {"accent": "#5e6d7c", "hover": "#7d8c9b", "subtle": "rgba(94, 109, 124, 0.28)", "text": "#9fb0c1"},
}


def theme_tokens(style: str, tone: str) -> dict[str, str]:
    tokens = dict(PALETTES[style])
    accent = ACCENTS[tone]
    tokens["accent"] = accent["accent"]
    tokens["accent_hover"] = accent["hover"]
    tokens["accent_subtle"] = accent["subtle"]
    tokens["accent_text"] = accent["accent"] if style == "light" else accent["text"]
    return tokens


_current: dict[str, str] = theme_tokens("dark", "blue")


def set_current(style: str, tone: str) -> dict[str, str]:
    """Self-painted widgets (graph, delegates, icons) read colors from here; Qt paints on the GUI thread only."""
    _current.clear()
    _current.update(theme_tokens(style, tone))
    return _current


def current() -> dict[str, str]:
    return _current


def theme_qss(style: str, tone: str) -> str:
    t = theme_tokens(style, tone)
    return f"""
    QMainWindow, QDialog {{
        background: {t["window"]};
        color: {t["text"]};
    }}
    QWidget {{
        color: {t["text"]};
        font-family: "Segoe UI", "Microsoft JhengHei";
        font-size: 12px;
    }}
    QStackedWidget#mainStack, QScrollArea, QWidget#qt_scrollarea_viewport,
    QScrollArea > QWidget > QWidget {{
        background: {t["window"]};
        border: none;
    }}
    QScrollBar:vertical {{ background: {t["window"]}; width: 10px; margin: 0; border: none; }}
    QScrollBar:horizontal {{ background: {t["window"]}; height: 10px; margin: 0; border: none; }}
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
        background: {t["border"]};
        border-radius: 4px;
        min-height: 24px;
        min-width: 24px;
        margin: 2px;
    }}
    QScrollBar::handle:hover {{ background: {t["faint"]}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
    QDateTimeEdit {{
        background: {t["input"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        border-radius: 3px;
        padding: 4px 6px;
    }}
    QMenuBar {{
        background: {t["menubar"]};
        color: {t["secondary"]};
        border-bottom: 1px solid {t["border"]};
        padding: 2px 4px;
    }}
    QLabel#brandLogo {{
        color: {t["text"]};
        font-weight: 700;
        font-size: 13px;
        padding-right: 8px;
    }}
    QMenuBar::item:selected {{ background: {t["hover"]}; }}
    QMenu {{
        background: {t["panel"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
    }}
    QMenu::item:selected {{ background: {t["accent"]}; color: white; }}
    QToolBar {{
        background: {t["toolbar"]};
        border-bottom: 1px solid {t["border"]};
        spacing: 8px;
        padding: 4px 8px;
        min-height: 44px;
    }}
    QStatusBar {{
        background: {t["statusbar"]};
        color: {t["secondary"]};
        border-top: 1px solid {t["border"]};
        min-height: 48px;
    }}
    QLabel#statusSyncDot {{
        background: #3ddc84;
        border-radius: 5px;
        min-width: 10px;
        max-width: 10px;
        min-height: 10px;
        max-height: 10px;
    }}
    QLabel#statusAgentDot {{
        background: {t["accent"]};
        border-radius: 5px;
        min-width: 10px;
        max-width: 10px;
        min-height: 10px;
        max-height: 10px;
    }}
    QFrame#pathBox {{
        background: {t["input"]};
        border: 1px solid {t["border"]};
        border-radius: 5px;
    }}
    QLabel#repoPathText {{
        background: transparent;
        border: none;
        color: {t["secondary"]};
        font-family: Consolas, "Cascadia Code";
    }}
    QTableWidget, QTreeWidget, QListWidget, QPlainTextEdit {{
        background: {t["panel"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        gridline-color: {t["border"]};
        selection-background-color: {t["accent_subtle"]};
        selection-color: {t["text"]};
    }}
    QHeaderView::section {{
        background: {t["sidebar"]};
        color: {t["muted"]};
        border: none;
        border-bottom: 1px solid {t["border"]};
        padding: 4px;
    }}
    QLineEdit, QComboBox, QSpinBox {{
        background: {t["input"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        border-radius: 3px;
        padding: 4px 6px;
        min-height: 22px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{ border-color: {t["accent"]}; }}
    QComboBox QAbstractItemView {{
        background: {t["panel"]};
        color: {t["text"]};
        selection-background-color: {t["accent"]};
        selection-color: white;
    }}
    QCheckBox, QRadioButton {{ color: {t["text"]}; spacing: 6px; }}
    QPushButton {{
        background: {t["panel"]};
        color: {t["text"]};
        border: 1px solid {t["border"]};
        border-radius: 3px;
        padding: 5px 10px;
    }}
    QPushButton:hover {{ background: {t["hover"]}; }}
    QPushButton:checked {{
        border-color: {t["accent"]};
        background: {t["accent_subtle"]};
    }}
    QPushButton:disabled {{ color: {t["faint"]}; }}
    QPushButton#btnPrimary {{
        background: {t["accent"]};
        border-color: {t["accent"]};
        color: white;
    }}
    QPushButton#btnPrimary:hover {{ background: {t["accent_hover"]}; }}
    QPushButton#btnOpenLog, QPushButton#btnOpenSettings, QPushButton#branchButton,
    QPushButton#btnQtMap, QPushButton#btnCommit, QPushButton#btnHistory, QPushButton#btnClone {{
        background: transparent;
        border: 1px solid {t["border"]};
        color: {t["muted"]};
    }}
    QLabel#pageTitle {{ font-size: 18px; font-weight: 650; }}
    QLabel#inspectorHeading {{ color: {t["accent_text"]}; font-weight: 650; }}
    QFrame#inspector {{
        background: {t["sidebar"]};
        border-left: 1px solid {t["border"]};
    }}
    QFrame#activityPanel, QFrame#branchPanel {{
        background: {t["deep"]};
        border-top: 1px solid {t["border"]};
    }}
    QPushButton[nav="true"] {{
        text-align: left;
        background: transparent;
        border: none;
        border-radius: 4px;
        padding: 8px 10px;
        color: {t["text"]};
    }}
    QPushButton[nav="true"]:hover {{ background: {t["hover"]}; }}
    QPushButton[nav="true"]:checked {{
        background: {t["accent_subtle"]};
        color: {t["text"]};
    }}
    QLabel#muted, QLabel#agentStateBadge {{ color: {t["muted"]}; }}
    QLabel#agentStateBadge {{
        border: 1px solid {t["border"]};
        border-radius: 8px;
        padding: 1px 6px;
    }}
    QFrame#sidebar {{
        background: {t["sidebar"]};
        border-right: 1px solid {t["border"]};
    }}
    QProgressBar {{
        background: {t["input"]};
        border: 1px solid {t["border"]};
        border-radius: 3px;
        text-align: center;
        min-width: 120px;
        max-height: 14px;
    }}
    QProgressBar::chunk {{ background: {t["accent"]}; }}
    QProgressBar#statusProgressBar {{
        min-width: 168px;
        max-width: 168px;
        min-height: 16px;
        max-height: 16px;
        background: {t["input"]};
        border: 1px solid {t["border"]};
        border-radius: 3px;
    }}
    QProgressBar#statusProgressBar::chunk {{ background: {t["accent"]}; }}
    QLabel#statusProgressPct {{ color: {t["accent_text"]}; font-weight: 600; font-family: Consolas, "Cascadia Code"; }}
    QPushButton[role="primary"] {{
        background: {t["accent"]};
        border-color: {t["accent"]};
        color: white;
    }}
    QPushButton[role="primary"]:hover {{ background: {t["accent_hover"]}; }}
    QPushButton[role="danger"] {{
        background: transparent;
        color: #f07979;
        border-color: #f07979;
    }}
    QFrame#agentCard, QFrame#agentCallout, QFrame[laneCard="true"] {{
        background: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 8px;
    }}
    QLabel[state="running"] {{ color: #f2b544; }}
    QLabel[state="error"] {{ color: #f07979; }}
    QListWidget#agentTerminalBody, QListWidget#execLogBody {{
        background: {t["deep"]};
        color: {t["secondary"]};
        border: 1px solid {t["border"]};
    }}
    QFrame#archInspector, QFrame#designerPalette, QFrame#designerProps {{
        background: {t["sidebar"]};
        border-left: 1px solid {t["border"]};
        border-right: 1px solid {t["border"]};
    }}
    QLabel#archPageTitle {{ font-size: 16px; font-weight: 650; }}
    QLabel#archSectionHead {{ color: {t["accent_text"]}; font-weight: 650; padding-top: 8px; }}
    QFrame#designForm {{
        background: {t["canvas"]};
        border: 1px dashed {t["border"]};
    }}
    QFrame#designForm[selected="true"], QFrame#designTransport[selected="true"],
    QPushButton#designSlider[selected="true"] {{
        border: 2px solid {t["accent"]};
    }}
    QPushButton#designSlider {{ background: {t["hover"]}; border-radius: 7px; }}
    QFrame#execLog {{
        background: {t["deep"]};
        border-top: 1px solid {t["border"]};
    }}
    QWidget#gitCommandBar {{ background: {t["sidebar"]}; border-bottom: 1px solid {t["border"]}; }}
    QWidget#gitCommandStrip {{ background: {t["sidebar"]}; }}
    QPushButton#btnToggleLocalChanges {{ color: #d99a1e; }}
    QPushButton#btnToggleLocalChanges:checked {{ border-color: #f2b544; }}
    QFrame#localChangesPanel {{
        background: {t["surface"]};
        border-bottom: 1px solid {t["border"]};
    }}
    QLabel#localModifiedBadge, QLabel#localPendingBadge {{
        color: #d99a1e;
        border: 1px solid rgba(242, 181, 68, 110);
        border-radius: 8px;
        padding: 0 6px;
        font-size: 11px;
    }}
    QLabel#gitStatusM {{ color: #d99a1e; font-weight: 650; padding-right: 6px; }}
    QLabel#acceptCount {{ color: {t["accent_text"]}; font-weight: 650; }}
    QLabel#acceptEmpty {{ color: {t["muted"]}; padding: 40px; }}
    QLabel#inspectorTitle {{ font-size: 13px; font-weight: 650; }}
    QLabel#inspectorSub {{ color: {t["accent_text"]}; }}
    QMainWindow#archDockHost {{ background: {t["window"]}; }}
    QDockWidget#archInspectorDock {{ color: {t["text"]}; }}
    QDockWidget#archInspectorDock::title {{
        background: {t["hover"]};
        border-left: 1px solid {t["border"]};
        border-bottom: 1px solid {t["border"]};
        padding: 6px 8px;
        text-align: left;
    }}
    QMainWindow#archDockHost::separator {{ background: {t["border"]}; width: 3px; }}
    QMainWindow#archDockHost::separator:hover {{ background: {t["accent"]}; }}
    QLabel#releaseTitle {{ font-size: 16px; font-weight: 650; }}
    QLabel#releaseSub, QLabel#releaseKicker, QLabel#releaseFieldLabel {{ color: {t["muted"]}; font-size: 12px; }}
    QLabel#releaseKicker {{ padding-top: 6px; }}
    QPushButton[objectName^="releaseTab-"] {{
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        border-radius: 0;
        color: {t["muted"]};
        padding: 8px 2px;
    }}
    QPushButton[objectName^="releaseTab-"]:checked {{ color: {t["text"]}; border-bottom-color: {t["accent"]}; }}
    QFrame#releaseCard {{
        background: {t["surface"]};
        border: 1px solid {t["border"]};
        border-radius: 8px;
    }}
    QLabel#releaseHero {{ font-size: 28px; font-weight: 650; }}
    QLabel#releaseChip {{
        border: 1px solid {t["border"]};
        border-radius: 9px;
        padding: 1px 8px;
        color: {t["muted"]};
        font-size: 11px;
    }}
    QLabel#releaseWhen, QLabel#releaseMeta, QLabel#releaseTableHead {{ color: {t["faint"]}; font-size: 11px; }}
    QLabel#releasePath {{ font-family: Consolas, monospace; font-size: 11px; }}
    QPushButton#releaseCopy {{ background: transparent; font-size: 11px; padding: 2px 8px; }}
    QLabel#releaseOk, QLabel#releaseMiss {{ border-radius: 9px; padding: 2px 8px; font-size: 11px; }}
    QLabel#releaseOk {{ color: #3fae6f; border: 1px solid rgba(91, 201, 139, 115); }}
    QLabel#releaseMiss {{ color: #e05d5d; border: 1px solid rgba(240, 121, 121, 128); }}
    QPushButton#btnReleaseReport {{
        background: transparent;
        border: none;
        color: {t["muted"]};
        text-align: left;
        padding: 0;
    }}
    QLabel#releaseReportTitle {{ font-size: 13px; font-weight: 650; }}
    QLabel#releaseReportText {{ color: {t["muted"]}; font-size: 12px; }}
    QLabel#releaseVerify {{
        background: {t["code"]};
        border: 1px solid {t["border"]};
        border-radius: 6px;
        padding: 8px 10px;
        font-family: Consolas, monospace;
        font-size: 11px;
    }}
    QFrame#releaseRail {{
        background: {t["surface"]};
        border-left: 1px solid {t["border"]};
    }}
    QFrame#releaseMethod {{ border: 1px solid {t["border"]}; border-radius: 6px; }}
    QPushButton#btnReleaseBuild {{ background: transparent; border: none; color: {t["accent_text"]}; }}
    """
