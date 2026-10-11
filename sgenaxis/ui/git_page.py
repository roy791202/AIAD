"""已驗收 page from the HTML Git workspace: command toolbar, read-only local changes, accepted table."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLayoutItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core.board import WorkItem
from sgenaxis.core.ports import GitSnapshot
from sgenaxis.ui.icons import icon
from sgenaxis.ui.task_board import ROLE_STATUS, STATUS_OPTIONS, LightSetDelegate

GIT_COMMANDS = (
    ("Pull", "btnOpenPull"),
    ("Push", "btnOpenPush"),
    ("Clone", "btnClone"),
    ("Fetch", "btnOpenFetch"),
    ("Merge", "btnOpenMerge"),
    ("Rebase", "btnOpenRebase"),
    ("Cherry-pick", "btnOpenCherry"),
    ("Revert", "btnOpenRevert"),
    ("Reset", "btnOpenReset"),
    ("Stash", "btnOpenStash"),
    ("Tag", "btnOpenTag"),
    ("Remote", "btnOpenRemote"),
    ("Submodule", "btnOpenSubmodule"),
    ("Worktree", "btnOpenWorktree"),
    ("Clean", "btnOpenClean"),
    ("Blame", "btnOpenBlame"),
    ("衝突與暫存", "btnOpenConflict"),
)
ACCEPT_COLUMNS = ("燈號", "狀態", "工項", "修改的檔案", "備註")


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, spacing: int = 6) -> None:
        super().__init__(parent)
        self._items: list[QLayoutItem] = []
        self._spacing = spacing
        self.setContentsMargins(0, 0, 0, 0)

    def addItem(self, item: QLayoutItem) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int) -> QLayoutItem | None:
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int) -> QLayoutItem | None:
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientations()

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._arrange(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._arrange(rect, apply=True)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        return size

    def _arrange(self, rect: QRect, apply: bool) -> int:
        x, y, line = rect.x(), rect.y(), 0
        for item in self._items:
            hint = item.sizeHint()
            if x + hint.width() > rect.right() + 1 and line > 0:
                x = rect.x()
                y += line + self._spacing
                line = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + self._spacing
            line = max(line, hint.height())
        return y + line - rect.y()


class GitWorkspacePage(QWidget):
    commit_requested = Signal()
    clone_requested = Signal()
    command = Signal(str)
    status_changed = Signal(str, str)
    item_selected = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("gitPage")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.toolbar = self._toolbar()
        layout.addWidget(self.toolbar)
        self.local_panel = self._local_changes()
        layout.addWidget(self.local_panel)
        self.show_git(None, "尚未讀取 Git")
        layout.addLayout(self._section_header())
        self.table = QTableWidget(0, len(ACCEPT_COLUMNS))
        self.table.setObjectName("acceptTable")
        self.table.setHorizontalHeaderLabels(list(ACCEPT_COLUMNS))
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setItemDelegateForColumn(0, LightSetDelegate(self.table))
        self.table.setColumnWidth(0, 52)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 300)
        self.table.setColumnWidth(3, 260)
        self.table.itemSelectionChanged.connect(self._emit_selection)
        layout.addWidget(self.table, 1)
        self.empty = QLabel("尚無已驗收工項。把狀態改為已驗收後會出現在這裡。")
        self.empty.setObjectName("acceptEmpty")
        self.empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty)

    def _toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setObjectName("gitCommandBar")
        outer = QVBoxLayout(bar)
        outer.setContentsMargins(10, 8, 10, 8)
        outer.setSpacing(6)
        row = QHBoxLayout()
        self._local_summary = "未讀取"
        self.local_toggle = QPushButton()
        self.local_toggle.setObjectName("btnToggleLocalChanges")
        self.local_toggle.setCheckable(True)
        self.local_toggle.setToolTip("切換本地檔案變更清單面板（唯讀）")
        self.local_toggle.toggled.connect(self._toggle_local)
        row.addWidget(self.local_toggle)
        row.addStretch(1)
        row.addWidget(QLabel("Source:"))
        self.branch = QComboBox()
        self.branch.setObjectName("selectBranch")
        self.branch.setAccessibleName("目前分支（唯讀）")
        self.branch.setToolTip("唯讀：只顯示目前分支，不會切換")
        self.branch.setEnabled(False)
        row.addWidget(self.branch)
        outer.addLayout(row)

        strip = QWidget()
        strip.setObjectName("gitCommandStrip")
        strip_row = FlowLayout(strip, spacing=6)
        commit = QPushButton(icon("save"), "提交")
        commit.setObjectName("btnCommit")
        commit.setToolTip("開啟提交視窗")
        commit.clicked.connect(self.commit_requested)
        strip_row.addWidget(commit)
        self.command_buttons: dict[str, QPushButton] = {"提交": commit}
        for label, name in GIT_COMMANDS:
            button = QPushButton(icon("open"), label) if name == "btnClone" else QPushButton(label)
            button.setObjectName(name)
            button.setToolTip(label)
            if name == "btnClone":
                button.clicked.connect(self.clone_requested)
            else:
                button.clicked.connect(lambda _checked=False, action=label: self.command.emit(action))
            self.command_buttons[label] = button
            strip_row.addWidget(button)
        outer.addWidget(strip)
        return bar

    def _local_changes(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("localChangesPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 8, 12, 8)
        head = QHBoxLayout()
        self.local_head = QLabel("")
        self.local_head.setObjectName("localChangesHead")
        head.addWidget(self.local_head)
        self.tracking = QLabel("")
        self.tracking.setObjectName("localPendingBadge")
        head.addWidget(self.tracking)
        head.addStretch(1)
        close = QPushButton("✕")
        close.setObjectName("btnCloseLocalChanges")
        close.setAccessibleName("關閉本地變更面板")
        close.setFixedWidth(28)
        close.clicked.connect(lambda: self.local_toggle.setChecked(False))
        head.addWidget(close)
        layout.addLayout(head)
        self.git_message = QLabel("")
        self.git_message.setObjectName("gitReadMessage")
        self.git_message.setWordWrap(True)
        layout.addWidget(self.git_message)
        self.changes_box = QVBoxLayout()
        self.changes_box.setSpacing(2)
        layout.addLayout(self.changes_box)
        self.file_rows: list[QLabel] = []
        return panel

    def show_git(self, snapshot: GitSnapshot | None, message: str) -> None:
        """Read-only view of the project's own repository; nothing here stages or switches."""
        for label in self.file_rows:
            self.changes_box.removeWidget(label)
            label.deleteLater()
        self.file_rows = []
        self.branch.clear()
        if snapshot is None:
            self._local_summary = "無法讀取"
            self.local_head.setText("沒有讀取 Git")
            self.tracking.setText("")
            self.git_message.setText(message)
            self.git_message.setVisible(True)
            self.branch.addItem("Git: —", "")
            self._toggle_local(self.local_toggle.isChecked())
            return
        for name in snapshot.branches:
            self.branch.addItem(f"Git: {name}", name)
        self.branch.setCurrentIndex(max(0, self.branch.findData(snapshot.branch)))
        staged = [change for change in snapshot.changes if change.staged]
        unstaged = [change for change in snapshot.changes if not change.staged]
        files = len({change.path for change in snapshot.changes})
        self._local_summary = f"{files} 個檔案變更"
        self.local_head.setText(f"{files} 個檔案變更　未暫存 {len(unstaged)}　已暫存 {len(staged)}")
        tracking = []
        if snapshot.ahead:
            tracking.append(f"{snapshot.ahead} 待推播")
        if snapshot.behind:
            tracking.append(f"落後 {snapshot.behind}")
        self.tracking.setText("　".join(tracking))
        self.git_message.setText("" if files else "工作目錄沒有變更")
        self.git_message.setVisible(not files)
        for change in unstaged + staged:
            label = QLabel(f"{'已暫存' if change.staged else '未暫存'}　{change.code:<2}　{change.path}")
            label.setObjectName("stagedFileRow" if change.staged else "localFileRow")
            label.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.changes_box.addWidget(label)
            self.file_rows.append(label)
        self._toggle_local(self.local_toggle.isChecked())

    def _section_header(self) -> QHBoxLayout:
        header = QHBoxLayout()
        header.setContentsMargins(12, 10, 12, 8)
        dot = QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet("background: #246bff; border-radius: 5px;")
        title = QLabel("已驗收")
        title.setObjectName("boardSectionTitle")
        self.count = QLabel("0")
        self.count.setObjectName("acceptCount")
        hint = QLabel("狀態改為已驗收的工項會列在這裡")
        hint.setObjectName("muted")
        header.addWidget(dot)
        header.addWidget(title)
        header.addWidget(self.count)
        header.addWidget(hint, 1)
        return header

    def show_accepted(self, items: list[WorkItem]) -> None:
        rows = [item for item in items if item.status == "accepted" and item.item_id != "TASK-Y1"]
        selected = self.selected_id()
        self.count.setText(str(len(rows)))
        self.table.blockSignals(True)
        self.table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            light = QTableWidgetItem("")
            light.setData(Qt.UserRole, item.item_id)
            light.setData(ROLE_STATUS, item.status)
            self.table.setItem(row, 0, light)
            for column, value in (
                (1, ""),
                (2, f"{item.title}\n{item.item_id}  ·  {item.source.capitalize()}"),
                (3, "\n".join(item.files)),
                (4, item.note),
            ):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.UserRole, item.item_id)
                self.table.setItem(row, column, cell)
            self.table.setCellWidget(row, 1, self._status_combo(item))
            self.table.setRowHeight(row, 52)
        self.table.blockSignals(False)
        self.table.setVisible(bool(rows))
        self.empty.setVisible(not rows)
        if rows:
            ids = [item.item_id for item in rows]
            self.table.selectRow(ids.index(selected) if selected in ids else 0)

    def selected_id(self) -> str | None:
        items = self.table.selectedItems()
        return items[0].data(Qt.UserRole) if items else None

    def _status_combo(self, item: WorkItem) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(f"accept-status-{item.item_id}")
        for value, label in STATUS_OPTIONS:
            combo.addItem(label, value)
        combo.setCurrentIndex(max(0, combo.findData(item.status)))
        combo.currentIndexChanged.connect(
            lambda _index, item_id=item.item_id, box=combo: self.status_changed.emit(item_id, box.currentData())
        )
        return combo

    def _emit_selection(self) -> None:
        item_id = self.selected_id()
        if item_id:
            self.item_selected.emit(item_id)

    def _toggle_local(self, shown: bool) -> None:
        self.local_panel.setVisible(shown)
        self.local_toggle.setText(f"本地變更   {self._local_summary} " + ("▴" if shown else "▾"))
