"""Bottom execution-log panel shared by every workbench page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

EXEC_LOG = (
    ("INFO", "[10:17:28]", "Health check: waiting for http://10.0.2.15:8080/health ..."),
    ("WARN", "[10:18:28]", "Health check: no response, retry 1/3 (timeout 30s)"),
    ("WARN", "[10:18:58]", "Health check: no response, retry 2/3 (timeout 30s)"),
    ("WARN", "[10:18:58]", "Health check: no response, retry 3/3 (timeout 30s)"),
    ("ERROR", "[10:18:58]", "Health check timeout after 180 seconds"),
    ("ERROR", "[10:18:58]", "Deployment failed: health check did not pass"),
    ("INFO", "[10:18:58]", "See logs at D:\\AutoCode\\logs\\deploy-007\\"),
)


class ExecLogPanel(QFrame):
    notice = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("execLog")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        bar = QHBoxLayout()
        self.tabs: dict[str, QPushButton] = {}
        for key, label in (
            ("log", "執行紀錄"),
            ("problems", "問題  1"),
            ("summary", "變更摘要"),
            ("terminal", "終端機"),
        ):
            button = QPushButton(label)
            button.setObjectName(f"execTab-{key}")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, name=key: self.show_tab(name))
            self.tabs[key] = button
            bar.addWidget(button)
        bar.addStretch(1)
        self.filter = QComboBox()
        self.filter.setObjectName("execLogFilter")
        self.filter.addItems(("全部", "INFO", "WARN", "ERROR"))
        self.filter.currentTextChanged.connect(lambda _text: self.apply_filter())
        self.search = QLineEdit()
        self.search.setObjectName("execLogSearch")
        self.search.setPlaceholderText("搜尋紀錄...")
        self.search.textChanged.connect(lambda _text: self.apply_filter())
        copy = QPushButton("複製")
        copy.setObjectName("btnExecCopy")
        copy.clicked.connect(self.copy_log)
        clear = QPushButton("清除")
        clear.setObjectName("btnExecClear")
        clear.clicked.connect(self.clear_log)
        bar.addWidget(self.filter)
        bar.addWidget(self.search)
        bar.addWidget(copy)
        bar.addWidget(clear)
        layout.addLayout(bar)

        self.lines = QListWidget()
        self.lines.setObjectName("execLogBody")
        self._entries = list(EXEC_LOG)
        self._fill()
        self.problems = QLabel("[10:18:58]  [ERROR]  Health check timeout after 180 seconds")
        self.problems.setObjectName("execProblems")
        self.problems.setWordWrap(True)
        self.summary = QLabel("deploy-007 部署失敗：健康檢查未通過。")
        self.summary.setObjectName("execSummary")
        self.summary.setWordWrap(True)
        self.terminal = QLabel("PS D:\\AutoCode>\nSee logs at D:\\AutoCode\\logs\\deploy-007\\")
        self.terminal.setObjectName("execTerminal")
        self.panels = {
            "log": self.lines,
            "problems": self.problems,
            "summary": self.summary,
            "terminal": self.terminal,
        }
        for widget in (self.problems, self.summary, self.terminal):
            widget.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        for widget in self.panels.values():
            layout.addWidget(widget, 1)
        self.show_tab("log")

    def append(self, level: str, stamp: str, message: str) -> None:
        self._entries.append((level, stamp, message))
        self._fill()
        self.apply_filter()

    def show_tab(self, name: str) -> None:
        for key, button in self.tabs.items():
            button.setChecked(key == name)
        for key, widget in self.panels.items():
            widget.setVisible(key == name)

    def apply_filter(self) -> None:
        level = self.filter.currentText()
        query = self.search.text().strip().lower()
        for row in range(self.lines.count()):
            item = self.lines.item(row)
            level_ok = level == "全部" or item.data(Qt.UserRole) == level
            text_ok = not query or query in item.text().lower()
            item.setHidden(not (level_ok and text_ok))

    def copy_log(self) -> None:
        text = "\n".join(
            self.lines.item(row).text()
            for row in range(self.lines.count())
            if not self.lines.item(row).isHidden()
        )
        if text:
            QApplication.clipboard().setText(text)
        self.notice.emit("已複製執行紀錄" if text else "沒有可複製的紀錄")

    def clear_log(self) -> None:
        self._entries.clear()
        self.lines.clear()
        self.notice.emit("已清除執行紀錄")

    def _fill(self) -> None:
        self.lines.clear()
        for index, (level, stamp, message) in enumerate(self._entries, start=1):
            item = QListWidgetItem(f"{index}  {stamp}  [{level}]  {message}")
            item.setData(Qt.UserRole, level)
            self.lines.addItem(item)
