"""專案管理 page: list, inspector fields, and the reference layout."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core import timefmt
from sgenaxis.core.board import WorkItem
from sgenaxis.core.session import ProjectRecord
from sgenaxis.ui.icons import icon
from sgenaxis.ui.task_board import STATUS_OPTIONS

STATUS_LABELS = dict(STATUS_OPTIONS)
ACTOR_LABELS = {"user": "使用者", "agent": "Agent"}

STATUS_COLOR = {
    "可存取": "#3ddc84",
    "未開啟": "#8b949e",
    "路徑不存在": "#f2b544",
}

DESCRIPTIONS = {
    "SGenAxis": "SGenAxis 主要開發專案。",
    "Sample Project": "範例專案。",
    "Legacy Demo": "示範用舊專案，路徑目前不存在。",
}


def project_id(name: str) -> str:
    slug = name.lower().replace(" ", "-").replace("_", "-")
    return f"prj-{slug}"


class ProjectPage(QWidget):
    selection_changed = Signal(str)
    open_requested = Signal(str)
    create_requested = Signal()
    clone_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("projectPage")
        self._rows: list[ProjectRecord] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 8)
        layout.setSpacing(10)
        title = QLabel("專案管理")
        title.setObjectName("pageTitle")
        lead = QLabel("管理本機專案、開啟現有專案或加入新的程式庫。")
        lead.setObjectName("muted")
        layout.addWidget(title)
        layout.addWidget(lead)

        tools = QHBoxLayout()
        add = QPushButton(icon("new"), "加入專案")
        add.setObjectName("btnPrimary")
        add.clicked.connect(self.create_requested.emit)
        clone = QPushButton(icon("open"), "Clone 程式庫")
        clone.setObjectName("btnCloneRepo")
        clone.clicked.connect(self.clone_requested.emit)
        self.search = QLineEdit()
        self.search.setObjectName("projectSearch")
        self.search.setPlaceholderText("搜尋專案名稱或路徑…")
        self.search.textChanged.connect(self._apply_query)
        tools.addWidget(add)
        tools.addWidget(clone)
        tools.addStretch(1)
        tools.addWidget(self.search)
        layout.addLayout(tools)

        self.table = QTableWidget(0, 5)
        self.table.setObjectName("projectTable")
        self.table.setHorizontalHeaderLabels(["名稱", "路徑", "分支", "狀態", "最後開啟時間"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemSelectionChanged.connect(self._emit_selection)
        self.table.cellDoubleClicked.connect(lambda _row, _col: self._emit_open())
        layout.addWidget(self.table, 1)
        self.count_label = QLabel("共 0 個專案")
        self.count_label.setObjectName("muted")
        layout.addWidget(self.count_label)
        self.query = ""

    def set_projects(self, projects: list[ProjectRecord], selected: str) -> None:
        self._rows = list(projects)
        self._selected = selected
        self._apply_query()

    def _apply_query(self, text: str | None = None) -> None:
        if text is not None:
            self.query = text.strip().lower()
        visible = [
            row for row in self._rows
            if not self.query or self.query in f"{row.name} {row.path}".lower()
        ]
        self.table.blockSignals(True)
        self.table.setRowCount(len(visible))
        for index, project in enumerate(visible):
            name = QTableWidgetItem(project.name)
            name.setData(Qt.UserRole, project.name)
            path = QTableWidgetItem(project.path)
            branch = QTableWidgetItem(project.branch)
            status = QTableWidgetItem(f"●  {project.access}")
            status.setForeground(QBrush(QColor(STATUS_COLOR.get(project.access, "#c5ccd4"))))
            opened = QTableWidgetItem(project.opened)
            for column, cell in enumerate((name, path, branch, status, opened)):
                self.table.setItem(index, column, cell)
            if project.name == getattr(self, "_selected", ""):
                self.table.selectRow(index)
        self.table.blockSignals(False)
        self.count_label.setText(f"共 {len(visible)} 個專案")
        if self.current_name():
            self.selection_changed.emit(self.current_name())

    def _emit_selection(self) -> None:
        name = self.current_name()
        if name:
            self.selection_changed.emit(name)

    def _emit_open(self) -> None:
        name = self.current_name()
        if name:
            self.open_requested.emit(name)

    def current_name(self) -> str:
        row = self.table.currentRow()
        if row < 0:
            return ""
        item = self.table.item(row, 0)
        return "" if item is None else str(item.data(Qt.UserRole))


class InspectorPanel(QFrame):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("inspector")
        self.setMinimumWidth(260)
        self.setMaximumWidth(420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        heading = QLabel("Git 變更詳情 / Inspector")
        heading.setObjectName("inspectorHeading")
        layout.addWidget(heading)
        task_section = QLabel("工項")
        task_section.setObjectName("pageTitle")
        layout.addWidget(task_section)
        self.task_title = QLabel("—")
        self.task_title.setObjectName("inspectorTitle")
        self.task_title.setWordWrap(True)
        self.task_sub = QLabel("—")
        self.task_sub.setObjectName("inspectorSub")
        self.task_files = QLabel("")
        self.task_files.setObjectName("muted")
        self.task_files.setWordWrap(True)
        self.task_note = QLabel("")
        self.task_note.setObjectName("muted")
        self.task_note.setWordWrap(True)
        self.task_meta = QLabel("")
        self.task_meta.setObjectName("inspectorTaskMeta")
        self.task_meta.setWordWrap(True)
        self.task_log = QLabel("")
        self.task_log.setObjectName("inspectorTaskLog")
        self.task_log.setWordWrap(True)
        for widget in (self.task_title, self.task_sub, self.task_files, self.task_note, self.task_meta, self.task_log):
            layout.addWidget(widget)
        section = QLabel("專案資訊")
        section.setObjectName("pageTitle")
        layout.addWidget(section)
        form = QFormLayout()
        self.name = QLabel("—")
        self.project_id = QLabel("—")
        self.project_id.setObjectName("inspectorProjectId")
        self.root = QLabel("—")
        self.branch = QLabel("—")
        self.remote = QLabel("未設定")
        self.status = QLabel("—")
        self.runs = QLabel("0")
        self.opened = QLabel("—")
        for label, widget in (
            ("名稱", self.name),
            ("專案 ID", self.project_id),
            ("根目錄", self.root),
            ("分支", self.branch),
            ("Git Remote", self.remote),
            ("狀態", self.status),
            ("活躍執行數", self.runs),
            ("最後開啟時間", self.opened),
        ):
            form.addRow(label, widget)
        layout.addLayout(form)
        self.description = QLabel("")
        self.description.setWordWrap(True)
        self.description.setObjectName("muted")
        layout.addWidget(QLabel("描述"))
        layout.addWidget(self.description)
        layout.addStretch(1)

    def show_task(self, item: WorkItem | None) -> None:
        if item is None:
            self.task_title.setText("—")
            self.task_sub.setText("—")
            self.task_files.setText("")
            self.task_note.setText("")
            self.task_meta.setText("")
            self.task_log.setText("")
            return
        self.task_title.setText(item.title)
        self.task_sub.setText(f"● {item.item_id}  ·  {STATUS_LABELS.get(item.status, item.status)}  ·  {item.kind}")
        self.task_files.setText("修改的檔案：" + "、".join(item.files))
        self.task_note.setText(item.note)
        self.task_meta.setText(
            f"建立 {timefmt.display(item.created)}（{ACTOR_LABELS[item.by]}）　開始 {timefmt.display(item.started)}"
            f"　完成 {timefmt.display(item.completed)}\n"
            f"最後修改 {timefmt.display(item.updated)}（{ACTOR_LABELS[item.updated_by]}）　版本 v{item.version}"
        )
        self.task_log.setText(
            "燈號紀錄：" + "　".join(f"{change.at} {STATUS_LABELS.get(change.zone, change.zone)}·{ACTOR_LABELS[change.by]}" for change in item.log[-5:])
        )

    def show_project(self, project: ProjectRecord | None, remote: str, runs: int) -> None:
        if project is None:
            return
        self.name.setText(project.name)
        self.project_id.setText(project_id(project.name))
        self.root.setText(project.path)
        self.branch.setText(project.branch)
        self.remote.setText(remote)
        self.status.setText(project.access)
        self.runs.setText(str(runs))
        self.opened.setText(project.opened)
        self.description.setText(DESCRIPTIONS.get(project.name, "本機專案。"))
