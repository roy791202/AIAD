"""Bottom status line from the HTML workbench footer."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QStatusBar, QWidget


class WorkbenchStatusBar(QStatusBar):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("workbenchStatus")
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(8, 0, 12, 0)
        self.sync_dot = QLabel()
        self.sync_dot.setObjectName("statusSyncDot")
        self.ready = QLabel("DRAFT 0.1 / 即時同步")
        self.ready.setObjectName("statusReady")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("statusProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(52)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedSize(168, 16)
        self.progress_label = QLabel("派工進度")
        self.progress_label.setObjectName("statusProgress")
        self.progress_pct = QLabel("52%")
        self.progress_pct.setObjectName("statusProgressPct")
        self.agent = QLabel("Agent 執行中  0")
        self.agent.setObjectName("statusAgent")
        row.addWidget(self.sync_dot)
        row.addWidget(self.ready)
        row.addSpacing(16)
        row.addWidget(self.progress_bar)
        row.addWidget(self.progress_label)
        row.addWidget(self.progress_pct)
        row.addStretch(1)
        row.addWidget(self.agent)
        self.addWidget(box, 1)

    def set_context(self, project: str, branch: str, opened: str) -> None:
        del project, branch, opened

    def set_activity(self, progress: int, running: int) -> None:
        self.progress_bar.setValue(progress)
        self.progress_pct.setText(f"{progress}%")
        self.agent.setText(f"Agent 執行中  {running}")
