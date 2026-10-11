"""佈版 page: board release records, live artifact checks, the project's dist folder, deployment rail.

Everything above the rail is read-only data handed in by the main window. The deployment
rail is not connected to any deploy port yet and says so.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core import timefmt
from sgenaxis.core.ports import FileInfo
from sgenaxis.core.release import ArtifactCheck, Release

ENVS = {
    "test": {"label": "測試環境", "profile": "windows-test", "target": "測試 VM，待設定", "os": "待確認"},
    "prod": {"label": "正式環境", "profile": "windows-prod", "target": "正式機，待設定", "os": "Windows 10 x64"},
}

RAIL_FIELDS = (
    ("profile", "Profile", ("windows-test", "windows-prod")),
    ("health", "健康檢查", ("未設定", "/health")),
    ("method", "部署方式", ("Windows Installer", "portable ZIP")),
    ("rollback", "復原策略", ("未設定", "保留上一版")),
    ("target", "目標環境", ("測試 VM，待設定", "正式機，待設定")),
    ("cred", "憑證", ("僅引用", "本機")),
    ("os", "目標 OS 版本", ("待確認", "Windows 10 x64")),
)

CHANNELS = (
    ("ssh", "SSH", "使用 SSH 進行遠端部署"),
    ("container", "Container", "以容器映像部署"),
    ("dcc", "DCC", "整合 DCC 平台部署"),
)

DEPLOY_NOT_CONNECTED = "部署尚未接上：這裡的設定只是示意，不會檢查或部署任何東西"


def _label(text: str, name: str, wrap: bool = False) -> QLabel:
    label = QLabel(text)
    label.setObjectName(name)
    label.setWordWrap(wrap)
    return label


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"


def check_text(check: ArtifactCheck) -> str:
    if not check.live:
        return "記錄：存在" if check.exists else "記錄：找不到"
    if not check.exists:
        return "找不到"
    size = human_size(check.size) + (f"／{check.files} 檔" if check.is_dir else "")
    return f"存在  {size}"


def entry_meta(entry: FileInfo) -> str:
    when = timefmt.display(timefmt.stamp(entry.modified))
    if entry.is_dir:
        return f"{human_size(entry.size)}／{entry.files} 檔\n{when}"
    return f"{human_size(entry.size)}\n{when}"


class ReleasePage(QWidget):
    notice = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("releasePage")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.copy_buttons: list[QPushButton] = []
        self._records: list[Release] = []
        self._checks: dict[str, list[ArtifactCheck]] = {}
        self._dist_widgets: list[QWidget] = []

        scroll = QScrollArea()
        scroll.setObjectName("releaseScroll")
        scroll.setWidgetResizable(True)
        content = QWidget()
        body = QVBoxLayout(content)
        body.setContentsMargins(18, 16, 18, 20)
        body.setSpacing(12)
        body.addLayout(self._head())
        body.addLayout(self._tabs())
        body.addWidget(self._recent_card())
        body.addWidget(self._report_card())
        body.addWidget(self._records_card())
        body.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        layout.addWidget(self._rail())
        self.set_env("test")
        self.show_data([], {}, ("", [], "尚未讀取"), "")

    # ── layout ─────────────────────────────────────────────

    def _head(self) -> QHBoxLayout:
        row = QHBoxLayout()
        titles = QVBoxLayout()
        titles.addWidget(_label("佈版", "releaseTitle"))
        titles.addWidget(_label("成品在哪、這次打了什麼，以及要部署到哪。", "releaseSub"))
        row.addLayout(titles, 1)
        field = QVBoxLayout()
        field.addWidget(_label("版本", "releaseFieldLabel"))
        self.version = QComboBox()
        self.version.setObjectName("releaseVersion")
        self.version.setAccessibleName("版本")
        self.version.currentIndexChanged.connect(self._show_selected)
        field.addWidget(self.version)
        row.addLayout(field)
        return row

    def _tabs(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        self.env_tabs: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key, env in ENVS.items():
            tab = QPushButton(env["label"])
            tab.setObjectName(f"releaseTab-{key}")
            tab.setCheckable(True)
            tab.clicked.connect(lambda _checked=False, name=key: self.set_env(name))
            group.addButton(tab)
            self.env_tabs[key] = tab
            row.addWidget(tab)
        row.addStretch(1)
        return row

    def _recent_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("releaseCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(_label("最近佈版（看板紀錄）", "releaseKicker"))
        hero = QHBoxLayout()
        self.hero = _label("", "releaseHero")
        hero.addWidget(self.hero)
        self.kind = _label("", "releaseChip")
        hero.addWidget(self.kind)
        self.when = _label("", "releaseWhen")
        hero.addWidget(self.when)
        hero.addStretch(1)
        layout.addLayout(hero)
        self.release_empty = _label("這個看板沒有佈版紀錄。", "releaseMeta")
        self.release_empty.setObjectName("releaseEmpty")
        layout.addWidget(self.release_empty)

        self.artifact_head = _label("成品與檔案路徑", "releaseTableHead")
        layout.addWidget(self.artifact_head)
        self.artifact_grid = QGridLayout()
        self.artifact_grid.setHorizontalSpacing(10)
        self.artifact_grid.setColumnStretch(1, 1)
        layout.addLayout(self.artifact_grid)
        self.artifact_widgets: list[QWidget] = []
        self.artifact_states: list[QLabel] = []

        self.dist_head = _label("成品資料夾", "releaseKicker")
        layout.addWidget(self.dist_head)
        self.dist_message = _label("", "releaseMeta", wrap=True)
        self.dist_message.setObjectName("releaseDistMessage")
        layout.addWidget(self.dist_message)
        self.dist_grid = QGridLayout()
        self.dist_grid.setHorizontalSpacing(10)
        self.dist_grid.setColumnStretch(1, 1)
        layout.addLayout(self.dist_grid)
        self.dist_rows: list[tuple[str, str, str]] = []
        return card

    def _report_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("releaseCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        self.report_toggle = QPushButton("佈版報告  ▾")
        self.report_toggle.setObjectName("btnReleaseReport")
        self.report_toggle.setCheckable(True)
        self.report_toggle.setChecked(True)
        self.report_toggle.clicked.connect(self.toggle_report)
        layout.addWidget(self.report_toggle)
        self.report_body = QWidget()
        self.report_body.setObjectName("releaseReportBody")
        report = QVBoxLayout(self.report_body)
        report.setContentsMargins(0, 6, 0, 0)
        self.report_text = _label("", "releaseReportText", wrap=True)
        self.report_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        report.addWidget(self.report_text)
        layout.addWidget(self.report_body)
        return card

    def _records_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("releaseCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.addWidget(_label("看板佈版紀錄（唯讀）", "releaseKicker"))
        self.record_empty = _label("這個看板沒有佈版紀錄。", "releaseMeta")
        self.record_empty.setObjectName("releaseRecordEmpty")
        layout.addWidget(self.record_empty)
        self.record_summary = _label("", "releaseWhen", wrap=True)
        self.record_summary.setObjectName("releaseRecordSummary")
        layout.addWidget(self.record_summary)
        self.record_text = QPlainTextEdit()
        self.record_text.setObjectName("releaseRecordReport")
        self.record_text.setAccessibleName("CHANGELOG、commit 與來源")
        self.record_text.setReadOnly(True)
        self.record_text.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.record_text.setMinimumHeight(220)
        layout.addWidget(self.record_text)
        return card

    def _rail(self) -> QFrame:
        rail = QFrame()
        rail.setObjectName("releaseRail")
        rail.setFixedWidth(300)
        layout = QVBoxLayout(rail)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.addWidget(_label("部署設定（未接上，僅示意）", "releaseKicker"))
        self.fields: dict[str, QComboBox] = {}
        for key, label, options in RAIL_FIELDS:
            layout.addWidget(_label(label, "releaseFieldLabel"))
            combo = QComboBox()
            combo.setObjectName(f"rel-{key}")
            combo.setAccessibleName(label)
            combo.addItems(options)
            self.fields[key] = combo
            layout.addWidget(combo)
        layout.addWidget(_label("部署方式（其他）", "releaseKicker"))
        self.channels: dict[str, QRadioButton] = {}
        channel_group = QButtonGroup(self)
        for key, name, hint in CHANNELS:
            box = QFrame()
            box.setObjectName("releaseMethod")
            box_layout = QVBoxLayout(box)
            box_layout.setContentsMargins(8, 6, 8, 6)
            radio = QRadioButton(name)
            radio.setObjectName(f"relChannel-{key}")
            channel_group.addButton(radio)
            self.channels[key] = radio
            box_layout.addWidget(radio)
            box_layout.addWidget(_label(hint, "releaseMeta"))
            layout.addWidget(box)
        layout.addStretch(1)
        actions = QHBoxLayout()
        actions.addStretch(1)
        check = QPushButton("檢查部署設定")
        check.setObjectName("btnReleaseCheck")
        check.setProperty("role", "primary")
        check.clicked.connect(lambda: self.notice.emit(DEPLOY_NOT_CONNECTED))
        start = QPushButton("開始部署")
        start.setObjectName("btnReleaseStart")
        start.clicked.connect(lambda: self.notice.emit(DEPLOY_NOT_CONNECTED))
        actions.addWidget(check)
        actions.addWidget(start)
        layout.addLayout(actions)
        return rail

    # ── data ───────────────────────────────────────────────

    def show_data(
        self,
        releases: list[Release],
        checks: dict[str, list[ArtifactCheck]],
        dist: tuple[str, list[FileInfo], str],
        checked_at: str,
    ) -> None:
        selected = self.version.currentData()
        self._records = list(releases)
        self._checks = dict(checks)
        self.version.blockSignals(True)
        self.version.clear()
        for item in self._records:
            self.version.addItem(f"v{item.version}（{item.kind}）" if item.kind else f"v{item.version}", item.release_id)
        if not self._records:
            self.version.addItem("沒有佈版紀錄", "")
        index = self.version.findData(selected)
        self.version.setCurrentIndex(index if index >= 0 else 0)
        self.version.blockSignals(False)
        self.version.setEnabled(bool(self._records))
        self.artifact_head.setText(f"成品與檔案路徑（{checked_at} 即時檢查）" if checked_at else "成品與檔案路徑")
        self._show_dist(*dist, checked_at)
        self._show_selected(self.version.currentIndex())

    def _show_selected(self, index: int) -> None:
        item = self._records[index] if 0 <= index < len(self._records) else None
        has = item is not None
        self.release_empty.setVisible(not has)
        self.record_empty.setVisible(not has)
        for widget in (self.kind, self.artifact_head, self.record_summary, self.record_text):
            widget.setVisible(has)
        self._clear_artifacts()
        if item is None:
            self.hero.setText("—")
            self.when.setText("")
            self.report_text.setText("（沒有佈版報告）")
            self.record_summary.setText("")
            self.record_text.setPlainText("")
            return
        self.hero.setText(f"v{item.version}")
        self.kind.setText(item.kind or "—")
        self.when.setText(f"{timefmt.display(item.released_at)} 發布")
        for row, check in enumerate(self._checks.get(item.release_id, [])):
            self._artifact_row(row, check)
        if not self._checks.get(item.release_id):
            empty = _label("沒有記錄成品", "releaseMeta")
            self.artifact_grid.addWidget(empty, 0, 0, 1, 4)
            self.artifact_widgets.append(empty)
        self.report_text.setText(item.report_md.strip() or "（沒有佈版報告）")
        self.record_summary.setText(
            f"v{item.version}（{item.kind or '—'}）　發布 {timefmt.display(item.released_at)}"
            f"　記錄 {timefmt.display(item.recorded_at)}（{item.recorded_by or '—'}）　{len(item.commits)} 個 commit"
        )
        commits = "\n".join(f"{commit.hash}  {timefmt.display(commit.at)}  {commit.subject}" for commit in item.commits)
        sources = "\n".join(f"{label}：{path}" for label, path in item.sources)
        parts = [
            "── CHANGELOG ──",
            item.changelog_md.strip() or "（沒有 CHANGELOG）",
            "── Commits ──",
            commits or "（無）",
            "── 來源 ──",
            sources or "（無）",
        ]
        self.record_text.setPlainText("\n\n".join(parts))

    def _clear_artifacts(self) -> None:
        for widget in self.artifact_widgets:
            self.artifact_grid.removeWidget(widget)
            widget.deleteLater()
        self.artifact_widgets = []
        self.artifact_states = []
        self.copy_buttons = []

    def _artifact_row(self, row: int, check: ArtifactCheck) -> None:
        name = QLabel(check.label)
        path = _label(check.path, "releasePath", wrap=True)
        path.setTextInteractionFlags(Qt.TextSelectableByMouse)
        copy = QPushButton("複製")
        copy.setObjectName("releaseCopy")
        copy.setAccessibleName(f"複製 {check.label} 路徑")
        copy.setProperty("copyPath", check.path)
        copy.clicked.connect(lambda _checked=False, button=copy: self.copy_path(button.property("copyPath")))
        state = _label(check_text(check), "releaseOk" if check.exists else "releaseMiss")
        state.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        for column, widget in enumerate((name, path, copy, state)):
            self.artifact_grid.addWidget(widget, row, column)
            self.artifact_widgets.append(widget)
        self.copy_buttons.append(copy)
        self.artifact_states.append(state)

    def _show_dist(self, folder: str, entries: list[FileInfo], message: str, checked_at: str) -> None:
        for widget in self._dist_widgets:
            self.dist_grid.removeWidget(widget)
            widget.deleteLater()
        self._dist_widgets = []
        self.dist_rows = []
        when = f"（{checked_at} 檢查）" if checked_at else ""
        self.dist_head.setText(f"成品資料夾現在實際有的東西{when}：{folder}" if folder else "成品資料夾")
        self.dist_message.setText(message)
        self.dist_message.setVisible(bool(message))
        for row, entry in enumerate(entries):
            kind = "資料夾" if entry.is_dir else "檔案"
            meta = entry_meta(entry)
            self.dist_rows.append((kind, entry.path, meta))
            meta_label = _label(meta, "releaseMeta")
            meta_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            for column, widget in enumerate((QLabel(kind), _label(entry.path, "releasePath", wrap=True), meta_label)):
                self.dist_grid.addWidget(widget, row, column)
                self._dist_widgets.append(widget)

    # ── actions ────────────────────────────────────────────

    def set_env(self, name: str) -> None:
        env = ENVS[name]
        for key, tab in self.env_tabs.items():
            tab.setChecked(key == name)
        self.fields["profile"].setCurrentText(env["profile"])
        self.fields["target"].setCurrentText(env["target"])
        self.fields["os"].setCurrentText(env["os"])

    def copy_path(self, path: str) -> None:
        if path:
            QApplication.clipboard().setText(path)
        self.notice.emit("已複製路徑" if path else "沒有路徑")

    def toggle_report(self) -> None:
        shown = self.report_toggle.isChecked()
        self.report_body.setVisible(shown)
        self.report_toggle.setText("佈版報告  " + ("▾" if shown else "▸"))
