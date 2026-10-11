"""PSIDE-03: task table. The default view is the bug queue."""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core import timefmt
from sgenaxis.core.board import WorkItem
from sgenaxis.ui import theme
from sgenaxis.ui.icons import icon

COLUMNS = ("燈號", "狀態", "工項", "修改的檔案", "BDD", "TDD", "建立時間", "完成時間", "備註")
DOT_COLORS = {
    "gray": "#8b949e",
    "yellow": "#f2b544",
    "red": "#f07979",
    "green": "#5bc98b",
    "accepted": "#246bff",
}
ROLE_STATUS = Qt.UserRole + 1
ACTOR_TAGS = {"user": "使用者", "agent": "Agent"}
STATUS_OPTIONS = (
    ("gray", "待辦"),
    ("yellow", "進行中"),
    ("red", "Bug"),
    ("green", "已完成"),
    ("accepted", "已驗收"),
)


def status_dot_icon(colors: tuple[str, ...] | list[str], diameter: int = 9) -> QIcon:
    gap = 3
    width = max(16, len(colors) * diameter + max(0, len(colors) - 1) * gap)
    image = QImage(width, 16, QImage.Format_ARGB32_Premultiplied)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(Qt.NoPen)
    y = (16 - diameter) // 2
    for index, color in enumerate(colors):
        painter.setBrush(QColor(color))
        painter.drawEllipse(index * (diameter + gap), y, diameter, diameter)
    painter.end()
    return QIcon(QPixmap.fromImage(image))


class LightSetDelegate(QStyledItemDelegate):
    """One filled status light. Its color follows the row status."""

    def paint(self, painter: QPainter, option, index) -> None:
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        if option.state & QStyle.State_Selected:
            selected = QColor(theme.current()["accent"])
            selected.setAlpha(56)
            painter.fillRect(option.rect, selected)
        status = index.data(ROLE_STATUS) or "gray"
        color = QColor(DOT_COLORS.get(status, "#8b949e"))
        diameter = 10
        rect = option.rect
        x = rect.x() + 12
        y = rect.y() + (rect.height() - diameter) // 2
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QRect(x, y, diameter, diameter))
        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(36, 36)


class TaskBoard(QWidget):
    status_changed = Signal(str, str)
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tools = QHBoxLayout()
        tools.setContentsMargins(12, 10, 12, 10)
        self.search = QLineEdit()
        self.search.setObjectName("boardSearch")
        self.search.setPlaceholderText("搜尋編號、名稱、BDD、TDD、備註")
        self.search.setMinimumWidth(220)
        self.search.setMaximumWidth(320)
        search_action = QAction(icon("search"), "", self.search)
        self.search.addAction(search_action, QLineEdit.LeadingPosition)
        self.source = QComboBox()
        self.source.setObjectName("boardSource")
        self.source.addItem("全部來源", "all")
        self.source.addItem("Git", "git")
        self.source.addItem("Agent", "agent")
        self.source.addItem("手動", "manual")
        self.sync_hint = QLabel("地端即時同步中：資料存在 docs/board/tasks.json，頁面與 CLI 共用同一份。")
        self.sync_hint.setObjectName("muted")
        tools.addWidget(self.search, 0)
        tools.addWidget(self.source)
        tools.addWidget(self.sync_hint, 1)
        layout.addLayout(tools)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        self.section_dot = QLabel()
        self.section_dot.setObjectName("boardSectionDot")
        self.section_dot.setFixedSize(10, 10)
        self.section_title = QLabel("紅燈・Bug")
        self.section_title.setObjectName("boardSectionTitle")
        self.section_count = QLabel("0")
        self.section_count.setObjectName("boardSectionCount")
        self.section_hint = QLabel("")
        self.section_hint.setObjectName("muted")
        header.addWidget(self.section_dot)
        header.addWidget(self.section_title)
        header.addWidget(self.section_count)
        header.addWidget(self.section_hint, 1)
        self.add_task = QPushButton("+ 新增工項")
        self.add_task.setObjectName("btnBoardAddTask")
        header.addWidget(self.add_task)
        layout.addLayout(header)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("taskTable")
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setItemDelegateForColumn(0, LightSetDelegate(self.table))
        self.table.setColumnWidth(0, 52)
        self.table.setColumnWidth(1, 120)
        layout.addWidget(self.table, 1)

    def show_items(self, items: list[WorkItem], title: str, hint: str, active: str = "red") -> None:
        self.section_title.setText(title)
        self.section_count.setText(str(len(items)))
        self.section_hint.setText(hint)
        dot = DOT_COLORS.get(active, "#8b949e")
        self.section_dot.setStyleSheet(f"background: {dot}; border-radius: 5px;")
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            light = QTableWidgetItem("")
            light.setData(Qt.UserRole, item.item_id)
            light.setData(ROLE_STATUS, item.status)
            self.table.setItem(row, 0, light)
            status_cell = QTableWidgetItem("")
            status_cell.setData(Qt.UserRole, item.item_id)
            self.table.setItem(row, 1, status_cell)
            self.table.setCellWidget(row, 1, self._status_combo(item))
            values = (
                f"{item.title}\n{item.code} · {item.kind} · {ACTOR_TAGS[item.updated_by]}",
                ", ".join(item.files),
                item.bdd,
                item.tdd,
                timefmt.display(item.created),
                timefmt.display(item.completed),
                item.note,
            )
            for column, value in enumerate(values, start=2):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.UserRole, item.item_id)
                self.table.setItem(row, column, cell)
            self.table.setRowHeight(row, 46)
        if items:
            self.table.selectRow(0)

    def _status_combo(self, item: WorkItem) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(f"status-{item.item_id}")
        for value, label in STATUS_OPTIONS:
            combo.addItem(label, value)
        combo.blockSignals(True)
        combo.setCurrentIndex(max(0, combo.findData(item.status)))
        combo.blockSignals(False)
        combo.currentIndexChanged.connect(
            lambda _index, item_id=item.item_id, box=combo: self.status_changed.emit(item_id, box.currentData())
        )
        return combo
