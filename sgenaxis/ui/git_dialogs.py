"""PSIDE-04: Git operation dialogs. They record intent and do not run Git."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
)


class HistoryDialog(QDialog):
    def __init__(self, branch: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("歷史")
        self.setObjectName("historyDialog")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"範圍 {branch}"))
        log = QPlainTextEdit()
        log.setReadOnly(True)
        log.setPlainText(
            "2022-03-19  a1b2c3d  feat(spec): 修正 BDD/TDD 測試收錄鏈路徑\n"
            "2022-03-18  9f8e7d6  chore: 鎖定測試骨架"
        )
        layout.addWidget(log)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class CommitDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("提交")
        self.setObjectName("commitDialog")
        self.message = QLineEdit()
        self.message.setObjectName("commitMessage")
        self.message.setPlaceholderText("提交說明")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("此視窗不會執行 git commit。"))
        layout.addWidget(self.message)
        self.error = QLabel("")
        self.error.setObjectName("commitError")
        layout.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept_message)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_message(self) -> None:
        if not self.message.text().strip():
            self.error.setText("請輸入提交說明")
            return
        self.accept()


class CloneDialog(QDialog):
    def __init__(self, url: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Clone 儲存庫")
        self.setObjectName("cloneDialog")
        self.url = QLineEdit(url)
        self.url.setObjectName("cloneUrl")
        form = QFormLayout()
        form.addRow("URL", self.url)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("此視窗不會執行 git clone。"))
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
