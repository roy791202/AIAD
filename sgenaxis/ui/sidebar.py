"""Left sidebar from the HTML workbench: Agent, task status, release, architecture, UI."""

from __future__ import annotations

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from sgenaxis.ui.icons import icon
from sgenaxis.ui.task_board import DOT_COLORS, status_dot_icon

FILTERS = (
    ("overview", "總覽", ("#8b949e", "#f2b544", "#f07979", "#5bc98b", "#246bff")),
    ("gray", "待辦", (DOT_COLORS["gray"],)),
    ("yellow", "進行中", (DOT_COLORS["yellow"],)),
    ("red", "Bug", (DOT_COLORS["red"],)),
    ("green", "已完成", (DOT_COLORS["green"],)),
    ("accepted", "已驗收", (DOT_COLORS["accepted"],)),
)


class TaskSidebar(QFrame):
    filter_chosen = Signal(str)
    page_chosen = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setMinimumWidth(210)
        self.setMaximumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        self.buttons: dict[str, QPushButton] = {}
        self.filter_buttons: dict[str, QPushButton] = {}
        self._page_group = QButtonGroup(self)
        self._page_group.setExclusive(True)
        self._filter_group = QButtonGroup(self)
        self._filter_group.setExclusive(True)

        agent_row = QHBoxLayout()
        self.agent_button = self._page_button("agent", "Agent 派工", "btnAgentNav", "agent")
        self.agent_badge = QLabel("Idle")
        self.agent_badge.setObjectName("agentStateBadge")
        agent_row.addWidget(self.agent_button, 1)
        agent_row.addWidget(self.agent_badge)
        layout.addLayout(agent_row)

        self._task_header(layout)
        self._task_body = QWidget()
        body = QVBoxLayout(self._task_body)
        body.setContentsMargins(4, 0, 0, 0)
        body.setSpacing(2)
        for key, label, colors in FILTERS:
            button = QPushButton(status_dot_icon(colors), label)
            button.setObjectName(f"filter-{key}")
            button.setProperty("nav", "true")
            button.setCheckable(True)
            button.setChecked(key == "red")
            button.clicked.connect(lambda _checked=False, name=key: self.filter_chosen.emit(name))
            self._filter_group.addButton(button)
            self.filter_buttons[key] = button
            body.addWidget(button)
        layout.addWidget(self._task_body)

        self.release_button = self._page_button("release", "佈版", "btnReleaseNav", "deploy")
        self.release_badge = QLabel("v0.4.0")
        self.release_badge.setObjectName("agentStateBadge")
        release_row = QHBoxLayout()
        release_row.addWidget(self.release_button, 1)
        release_row.addWidget(self.release_badge)
        layout.addLayout(release_row)
        self.stats_button = self._page_button("stats", "期間統計", "btnStatsNav", "history")
        layout.addWidget(self.stats_button)

        self.arch_button = self._page_button("arch", "模組架構圖", "btnArchNav", "module")
        self._later(layout, self.arch_button)
        self.ui_button = self._page_button("ui", "UI 設計工具", "btnUiNav", "design")
        self._later(layout, self.ui_button)
        layout.addStretch(1)

        self.tasks_button = self.filter_buttons["red"]
        self.settings_button = self.agent_button

    def _page_button(self, page: str, label: str, object_name: str, icon_name: str) -> QPushButton:
        button = QPushButton(icon(icon_name), label)
        button.setObjectName(object_name)
        button.setProperty("nav", "true")
        button.setIconSize(QSize(16, 16))
        button.setCheckable(True)
        button.clicked.connect(lambda _checked=False, name=page: self.page_chosen.emit(name))
        self._page_group.addButton(button)
        self.buttons[page] = button
        return button

    def _later(self, layout: QVBoxLayout, button: QPushButton) -> None:
        row = QHBoxLayout()
        badge = QLabel("稍後")
        badge.setObjectName("agentStateBadge")
        row.addWidget(button, 1)
        row.addWidget(badge)
        layout.addLayout(row)

    def _task_header(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.tasks_header = QPushButton("Tasks Status")
        self.tasks_header.setObjectName("tasksStatusHeader")
        self.tasks_header.setProperty("nav", "true")
        self.tasks_header.clicked.connect(self._toggle_tasks)
        self.clear_button = QPushButton("全部 (19)")
        self.clear_button.setObjectName("btnClearStatusFilter")
        self.clear_button.setToolTip("清除篩選 (顯示全部工項)")
        self.clear_button.clicked.connect(lambda: self.filter_chosen.emit("all"))
        row.addWidget(self.tasks_header, 1)
        row.addWidget(self.clear_button)
        layout.addLayout(row)

    def _toggle_tasks(self) -> None:
        self._task_body.setVisible(not self._task_body.isVisible())

    def set_agent_state(self, running: int, total: int = 1) -> None:
        self.agent_button.setText(f"Agent 派工  [{running}/{total}]")
        state = "執行中" if running else "Idle"
        self.agent_badge.setText(state)
        self.agent_button.setToolTip(state)

    def set_counts(self, counts: dict[str, int]) -> None:
        labels = {key: label for key, label, _colors in FILTERS}
        for key, button in self.filter_buttons.items():
            button.setText(f"{labels[key]}  {counts[key]}")
        open_count = counts["gray"] + counts["yellow"] + counts["red"] + counts["green"]
        self.clear_button.setText(f"全部 ({open_count})")

    def set_filter(self, name: str) -> None:
        self._set_checks(self._filter_group, self.filter_buttons, name)
        if name:
            self._set_checks(self._page_group, self.buttons, "")

    def set_current(self, page: str) -> None:
        if page in ("tasks", "git"):
            return
        self._set_checks(self._page_group, self.buttons, page)
        self._set_checks(self._filter_group, self.filter_buttons, "")

    def _set_checks(self, group: QButtonGroup, buttons: dict[str, QPushButton], selected: str) -> None:
        group.setExclusive(False)
        for key, button in buttons.items():
            button.setChecked(key == selected)
        group.setExclusive(True)
