"""Period statistics page from the Beta board (期間統計)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core import stats
from sgenaxis.core.board import WorkItem

COLUMNS = ("期間", "新增工項", "完成工項（以完成時間計）", "同期新增已完成率", "累計完成率")
PERIOD_LIMIT = 12


class StatsPage(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("statsPage")
        self.granularity = "week"
        self._items: list[WorkItem] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 18, 12)
        layout.setSpacing(10)
        title = QLabel("期間統計")
        title.setObjectName("pageTitle")
        layout.addWidget(title)
        overall = QHBoxLayout()
        overall.addWidget(QLabel("整體完成率（綠 ÷ 全部工項）"))
        self.overall = QProgressBar()
        self.overall.setObjectName("statsOverall")
        self.overall.setRange(0, 100)
        overall.addWidget(self.overall, 1)
        layout.addLayout(overall)
        row = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        group = QButtonGroup(self)
        group.setExclusive(True)
        for key in stats.GRANULARITIES:
            button = QPushButton(stats.GRANULARITY_LABELS[key])
            button.setObjectName(f"statsGran-{key}")
            button.setCheckable(True)
            button.setChecked(key == self.granularity)
            button.clicked.connect(lambda _checked=False, name=key: self.set_granularity(name))
            group.addButton(button)
            self.buttons[key] = button
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("statsTable")
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        hint = QLabel(
            "「同期新增已完成率」＝該期間建立的工項中、目前已是綠燈的比例；"
            "「累計完成率」＝到該期間結束為止已完成的工項 ÷ 已建立的工項。只列最近 12 期。"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

    def show_stats(self, items: list[WorkItem]) -> None:
        self._items = list(items)
        self.overall.setValue(round(stats.completion_rate(self._items) * 100))
        rows = stats.periods(self._items, self.granularity, PERIOD_LIMIT)
        self.table.setRowCount(len(rows))
        for index, period in enumerate(reversed(rows)):
            for column, value in enumerate(
                (
                    period.label,
                    str(period.created),
                    str(period.done),
                    _percent(period.created_done_rate) if period.created else "—",
                    _percent(period.cumulative_rate),
                )
            ):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(Qt.AlignVCenter | (Qt.AlignLeft if column == 0 else Qt.AlignRight))
                self.table.setItem(index, column, cell)

    def set_granularity(self, granularity: str) -> None:
        if granularity not in stats.GRANULARITIES:
            raise ValueError(granularity)
        self.granularity = granularity
        self.buttons[granularity].setChecked(True)
        self.show_stats(self._items)


def _percent(value: float) -> str:
    return f"{value * 100:.0f}%"
