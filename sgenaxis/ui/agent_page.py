"""Agent dispatch page: lanes, needs-human list, run history, and schedules.

The page only renders dispatcher state and emits requests. MainWindow calls
the dispatcher and refreshes. Agent CLIs are never started from here.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, Qt, QTime, Signal
from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core import schedule, timefmt
from sgenaxis.core.dispatch import AGENT_LABELS
from sgenaxis.core.dispatcher import Dispatcher, HistoryEntry, Lane
from sgenaxis.core.report_channels import CHANNEL_LABELS

_NEXT_LABEL = {"red": "紅燈（Bug）", "yellow": "黃燈（進行中）", "gray": "灰燈（待辦）"}
_NEXT_COLOR = {"red": "#f07979", "yellow": "#f2b544", "gray": "#8b949e"}
STATE_LABELS = {"idle": "閒置", "running": "執行中", "stopping": "停止中", "error": "錯誤"}
REASON_LABELS = {
    "": "—",
    "user": "使用者停止",
    "limit": "達到張數上限",
    "no-candidates": "無卡",
    "auth-error": "登入失敗",
    "launch-error": "啟動失敗",
    "quota-error": "額度用完",
    "fast-fail": "連續快速失敗",
    "orphaned": "上次執行中斷",
    "restart": "程式重新啟動",
}
OUTCOME_LABELS = {
    "done": "完成",
    "blocked": "卡住",
    "no-report": "沒有回報",
    "timeout": "逾時",
    "terminated": "立即終止",
    "server-shutdown": "伺服器關閉",
    "orphaned": "上次未結束",
    "auth-error": "登入失敗",
    "launch-error": "啟動失敗",
    "quota-error": "額度用完",
}
SCHEDULE_RESULTS = {
    "started": "已啟動",
    "skipped-busy": "略過（忙碌）",
    "skipped-paused": "略過（暫停中）",
    "stop-requested": "本張做完後停止",
    "not-started-by-schedule": "非此排程啟動，不停止",
    "idle": "已閒置",
    "no-candidates": "無卡",
    "limit": "達到上限",
}


class LaneCard(QFrame):
    action = Signal(str, str)
    configure = Signal(str, str, object)
    report = Signal(str, str)
    schedule_add = Signal(str, dict)
    schedule_delete = Signal(str, str)
    schedule_toggle = Signal(str, str, bool)

    def __init__(self, lane: Lane, now: datetime, parent=None) -> None:
        super().__init__(parent)
        self.lane_id = lane.lane_id
        self.setObjectName(f"agentLane-{lane.lane_id}")
        self.setProperty("laneCard", "true")
        layout = QVBoxLayout(self)
        layout.addLayout(self._header(lane))
        self.status = QLabel("")
        self.status.setObjectName(f"laneStatus-{lane.lane_id}")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.body = QWidget()
        self.body.setObjectName(f"laneBody-{lane.lane_id}")
        body = QVBoxLayout(self.body)
        body.setContentsMargins(0, 6, 0, 0)
        self.schedule_title = QLabel("排程（0）")
        self.schedule_title.setObjectName("pageTitle")
        body.addWidget(self.schedule_title)
        self.schedule_list = QListWidget()
        self.schedule_list.setObjectName(f"laneSchedules-{lane.lane_id}")
        self.schedule_list.setMaximumHeight(96)
        self.schedule_list.itemChanged.connect(self._schedule_checked)
        body.addWidget(self.schedule_list)
        body.addWidget(self._schedule_form(now))
        layout.addWidget(self.body)
        self._schedule_sig: tuple = ()
        self.show_lane(lane, now, {})

    def _header(self, lane: Lane) -> QHBoxLayout:
        row = QHBoxLayout()
        self.collapse = QPushButton("▾")
        self.collapse.setObjectName(f"laneCollapse-{lane.lane_id}")
        self.collapse.setFixedWidth(28)
        self.collapse.setAccessibleName(f"收合 Agent {lane.lane_id}")
        self.collapse.clicked.connect(self._toggle)
        title = QLabel(f"Agent {lane.lane_id}")
        title.setObjectName("pageTitle")
        self.agent = QComboBox()
        self.agent.setObjectName(f"laneAgent-{lane.lane_id}")
        self.agent.setAccessibleName("CLI")
        for key, label in AGENT_LABELS.items():
            self.agent.addItem(label, key)
        self.max_cards = QSpinBox()
        self.max_cards.setObjectName(f"laneMaxCards-{lane.lane_id}")
        self.max_cards.setAccessibleName("最多幾張")
        self.max_cards.setRange(1, 50)
        self.until_clear = QCheckBox("做到無卡為止")
        self.until_clear.setObjectName(f"laneUntilClear-{lane.lane_id}")
        self.agent.currentIndexChanged.connect(self._emit_config)
        self.max_cards.valueChanged.connect(self._emit_config)
        self.until_clear.toggled.connect(self._emit_config)
        row.addWidget(self.collapse)
        row.addWidget(title)
        row.addWidget(self.agent)
        row.addWidget(QLabel("最多"))
        row.addWidget(self.max_cards)
        row.addWidget(self.until_clear)
        row.addStretch(1)
        self.buttons: dict[str, QPushButton] = {}
        for key, label, role in (
            ("start", "啟動", "primary"),
            ("stop", "停止", ""),
            ("kill", "立即終止", "danger"),
            ("remove", "移除", ""),
        ):
            button = QPushButton(label)
            button.setObjectName(f"lane-{key}-{lane.lane_id}")
            if role:
                button.setProperty("role", role)
            button.clicked.connect(lambda _checked=False, name=key: self.action.emit(self.lane_id, name))
            self.buttons[key] = button
            row.addWidget(button)
        for outcome, label in (("done", "模擬回報：完成"), ("blocked", "模擬回報：卡住")):
            button = QPushButton(label)
            button.setObjectName(f"lane-report-{outcome}-{lane.lane_id}")
            button.setToolTip("Agent 只模擬，不啟動真實 CLI；用這個代替 board report 回報")
            button.clicked.connect(lambda _checked=False, value=outcome: self._report(value))
            self.buttons[f"report-{outcome}"] = button
            row.addWidget(button)
        return row

    def _schedule_form(self, now: datetime) -> QWidget:
        form = QWidget()
        form.setObjectName(f"laneScheduleForm-{self.lane_id}")
        layout = QHBoxLayout(form)
        layout.setContentsMargins(0, 0, 0, 0)
        self.kind = QComboBox()
        self.kind.setObjectName(f"scheduleKind-{self.lane_id}")
        self.kind.setAccessibleName("排程類型")
        for key in schedule.KINDS:
            self.kind.addItem(schedule.KIND_LABELS[key], key)
        self.at = QDateTimeEdit()
        self.at.setObjectName(f"scheduleAt-{self.lane_id}")
        self.at.setAccessibleName("日期時間")
        self.at.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.at.setDateTime(QDateTime.fromString(f"{now + timedelta(hours=1):%Y-%m-%d %H:%M}", "yyyy-MM-dd HH:mm"))
        self.time = QTimeEdit(QTime(9, 0))
        self.time.setObjectName(f"scheduleTime-{self.lane_id}")
        self.time.setAccessibleName("時間")
        self.start = QTimeEdit(QTime(23, 0))
        self.start.setObjectName(f"scheduleStart-{self.lane_id}")
        self.start.setAccessibleName("開始")
        self.end = QTimeEdit(QTime(7, 0))
        self.end.setObjectName(f"scheduleEnd-{self.lane_id}")
        self.end.setAccessibleName("結束")
        for edit in (self.time, self.start, self.end):
            edit.setDisplayFormat("HH:mm")
        self.weekdays = []
        layout.addWidget(self.kind)
        layout.addWidget(self.at)
        layout.addWidget(self.time)
        layout.addWidget(self.start)
        layout.addWidget(self.end)
        for index, label in enumerate(schedule.WEEKDAY_LABELS):
            check = QCheckBox(label[-1])
            check.setObjectName(f"scheduleDay{index}-{self.lane_id}")
            check.setAccessibleName(label)
            self.weekdays.append(check)
            layout.addWidget(check)
        add = QPushButton("新增排程")
        add.setObjectName(f"scheduleAdd-{self.lane_id}")
        add.clicked.connect(self._add_schedule)
        self.remove_schedule = QPushButton("刪除排程")
        self.remove_schedule.setObjectName(f"scheduleDelete-{self.lane_id}")
        self.remove_schedule.clicked.connect(self._delete_schedule)
        layout.addWidget(add)
        layout.addWidget(self.remove_schedule)
        layout.addStretch(1)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self._kind_changed()
        return form

    def show_lane(self, lane: Lane, now: datetime, next_runs: dict) -> None:
        for widget in (self.agent, self.max_cards, self.until_clear):
            widget.blockSignals(True)
        self.agent.setCurrentIndex(max(0, self.agent.findData(lane.agent)))
        self.until_clear.setChecked(lane.max_cards is None)
        self.max_cards.setValue(lane.max_cards or 5)
        self.max_cards.setEnabled(lane.max_cards is not None and not lane.active)
        for widget in (self.agent, self.max_cards, self.until_clear):
            widget.blockSignals(False)
        self.agent.setEnabled(not lane.active)
        self.until_clear.setEnabled(not lane.active)
        self.buttons["start"].setEnabled(not lane.active)
        self.buttons["stop"].setEnabled(lane.state == "running")
        self.buttons["kill"].setEnabled(lane.current is not None)
        self.buttons["remove"].setEnabled(not lane.active)
        for key in ("report-done", "report-blocked"):
            self.buttons[key].setEnabled(lane.current is not None)
        self.status.setText(lane_status(lane, now, next_runs))
        self.status.setProperty("state", lane.state)
        self._show_schedules(lane, next_runs)

    def current_card(self) -> str | None:
        return self.property("currentCard") or None

    def _show_schedules(self, lane: Lane, next_runs: dict) -> None:
        signature = tuple((entry, next_runs.get(entry.schedule_id)) for entry in lane.schedules)
        if signature == self._schedule_sig:
            return
        self._schedule_sig = signature
        self.schedule_title.setText(f"排程（{len(lane.schedules)}）")
        self.schedule_list.blockSignals(True)
        self.schedule_list.clear()
        for entry in lane.schedules:
            upcoming = next_runs.get(entry.schedule_id)
            when = f"下次：{upcoming[0]:%m/%d %H:%M}" + ("（時段結束）" if upcoming[1] == "stop" else "") if upcoming else "下次：—"
            last = f"　上次：{timefmt.display(entry.last_fired)} {SCHEDULE_RESULTS.get(entry.last_result, entry.last_result)}" if entry.last_fired else ""
            row = QListWidgetItem(f"{entry.schedule_id}  {schedule.describe(entry)}　{when}{last}")
            row.setData(Qt.UserRole, entry.schedule_id)
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
            row.setCheckState(Qt.Checked if entry.enabled else Qt.Unchecked)
            self.schedule_list.addItem(row)
        self.schedule_list.blockSignals(False)

    def _toggle(self) -> None:
        self.body.setVisible(not self.body.isVisible())
        self.collapse.setText("▾" if self.body.isVisible() else "▸")

    def _emit_config(self) -> None:
        self.max_cards.setEnabled(not self.until_clear.isChecked())
        limit = None if self.until_clear.isChecked() else self.max_cards.value()
        self.configure.emit(self.lane_id, self.agent.currentData(), limit)

    def _report(self, outcome: str) -> None:
        card = self.current_card()
        if card:
            self.report.emit(card, outcome)

    def _kind_changed(self) -> None:
        kind = self.kind.currentData()
        self.at.setVisible(kind == "once")
        self.time.setVisible(kind == "daily")
        self.start.setVisible(kind == "window")
        self.end.setVisible(kind == "window")
        for check in self.weekdays:
            check.setVisible(kind != "once")

    def _add_schedule(self) -> None:
        kind = self.kind.currentData()
        fields: dict = {"kind": kind}
        if kind == "once":
            fields["at"] = self.at.dateTime().toString("yyyy-MM-ddTHH:mm")
        else:
            fields["weekdays"] = tuple(index for index, check in enumerate(self.weekdays) if check.isChecked())
            if kind == "daily":
                fields["time"] = self.time.time().toString("HH:mm")
            else:
                fields["start"] = self.start.time().toString("HH:mm")
                fields["end"] = self.end.time().toString("HH:mm")
        self.schedule_add.emit(self.lane_id, fields)

    def _delete_schedule(self) -> None:
        row = self.schedule_list.currentItem()
        if row is not None:
            self.schedule_delete.emit(self.lane_id, row.data(Qt.UserRole))

    def _schedule_checked(self, row: QListWidgetItem) -> None:
        self.schedule_toggle.emit(self.lane_id, row.data(Qt.UserRole), row.checkState() == Qt.Checked)


class AgentDispatchPage(QWidget):
    notice = Signal(str)
    add_lane_requested = Signal()
    lane_action = Signal(str, str)
    lane_config = Signal(str, str, object)
    report_requested = Signal(str, str)
    unskip_requested = Signal(str)
    schedule_add = Signal(str, dict)
    schedule_delete = Signal(str, str)
    schedule_toggle = Signal(str, str, bool)
    schedules_paused = Signal(bool)
    stop_all_requested = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("agentPage")
        self.cards: dict[str, LaneCard] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._scroll(), 1)

    def _scroll(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 16, 18, 12)
        layout.setSpacing(12)
        layout.addLayout(self._head_actions())
        self.dry_run = QLabel("模擬派工：只記錄派工與回報，不啟動 Agent CLI、不執行 git。卡片燈號照 Beta 規則改變。")
        self.dry_run.setObjectName("muted")
        self.dry_run.setWordWrap(True)
        layout.addWidget(self.dry_run)
        self.board_hint = QLabel("")
        self.board_hint.setObjectName("boardJsonHint")
        self.board_hint.setWordWrap(True)
        self.board_hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.board_hint)
        self.lane_box = QVBoxLayout()
        self.lane_box.setSpacing(10)
        layout.addLayout(self.lane_box)
        layout.addWidget(self._next_card())
        layout.addLayout(self._lists())
        layout.addWidget(self._title("紀錄內容（點選最近紀錄的一筆）"))
        self.detail = QPlainTextEdit()
        self.detail.setObjectName("dispatchDetail")
        self.detail.setAccessibleName("派工紀錄內容")
        self.detail.setReadOnly(True)
        self.detail.setFont(QFontDatabase.systemFont(QFontDatabase.FixedFont))
        self.detail.setMinimumHeight(180)
        self.detail.setPlaceholderText("選一筆最近紀錄，這裡會顯示派工的提示詞、輸出與回報。")
        layout.addWidget(self.detail)
        layout.addStretch(1)
        scroll.setWidget(body)
        return scroll

    def _head_actions(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.add_button = self._button("+ 新增 Agent", "btnAddAgent", "primary", self.add_lane_requested.emit)
        self.stop_all = self._button("全部停止", "btnStopWork", "danger", self.stop_all_requested.emit)
        self.pause = QCheckBox("暫停所有排程")
        self.pause.setObjectName("checkPauseSchedules")
        self.pause.toggled.connect(self.schedules_paused.emit)
        self.summary = QLabel("")
        self.summary.setObjectName("dispatchSummary")
        row.addWidget(self.add_button)
        row.addWidget(self.stop_all)
        row.addWidget(self.pause)
        row.addStretch(1)
        row.addWidget(self.summary)
        return row

    def _next_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("agentCallout")
        row = QHBoxLayout(card)
        self.next_dot = QLabel()
        self.next_dot.setObjectName("nextCardDot")
        self.next_dot.setFixedSize(10, 10)
        text = QVBoxLayout()
        title = QLabel("下一張（紅 > 黃 > 灰，排除需人工與執行中的卡）")
        title.setObjectName("nextCardTitle")
        self.next_detail = QLabel("")
        self.next_detail.setObjectName("nextCardDetail")
        self.next_detail.setWordWrap(True)
        text.addWidget(title)
        text.addWidget(self.next_detail)
        row.addWidget(self.next_dot, 0, Qt.AlignTop)
        row.addLayout(text, 1)
        return card

    def _lists(self) -> QHBoxLayout:
        row = QHBoxLayout()
        human = QVBoxLayout()
        human.addWidget(self._title("需人工（不會自動再派）"))
        self.needs_human = QListWidget()
        self.needs_human.setObjectName("needsHumanList")
        human.addWidget(self.needs_human)
        self.unskip = self._button("解除，可再派", "btnUnskip", "", self._unskip)
        human.addWidget(self.unskip)
        history = QVBoxLayout()
        history.addWidget(self._title("最近紀錄"))
        self.history = QListWidget()
        self.history.setObjectName("dispatchHistory")
        self.history.setAccessibleName("最近紀錄")
        self.history.currentItemChanged.connect(self._show_detail)
        self._entries: dict[str, HistoryEntry] = {}
        history.addWidget(self.history)
        schedules = QVBoxLayout()
        schedules.addWidget(self._title("排程紀錄"))
        self.schedule_history = QListWidget()
        self.schedule_history.setObjectName("scheduleHistory")
        schedules.addWidget(self.schedule_history)
        for column in (human, history, schedules):
            row.addLayout(column, 1)
        return row

    def show_dispatch(self, dispatcher: Dispatcher, now: datetime, board_label: str = "", launch_label: str = "") -> None:
        if board_label:
            mode = f"　啟動方式：{launch_label}（在設定 › Agent 啟動切換）" if launch_label else ""
            self.board_hint.setText(f"看板 JSON：{board_label}　每張派出的卡都要求 Agent 回報，結果寫回這個檔案。{mode}")
        ids = [lane.lane_id for lane in dispatcher.lanes]
        for lane_id in [key for key in self.cards if key not in ids]:
            card = self.cards.pop(lane_id)
            self.lane_box.removeWidget(card)
            card.deleteLater()
        for lane in dispatcher.lanes:
            card = self.cards.get(lane.lane_id)
            if card is None:
                card = self._lane_card(lane, now)
            next_runs = {entry.schedule_id: dispatcher.next_run(entry) for entry in lane.schedules}
            card.setProperty("currentCard", lane.current.card_id if lane.current else "")
            card.show_lane(lane, now, next_runs)
        self.add_button.setEnabled(len(dispatcher.lanes) < dispatcher.max_lanes)
        self.summary.setText(f"執行中 {dispatcher.running_count()} / {len(dispatcher.lanes)} 條（上限 {dispatcher.max_lanes}）")
        self.pause.blockSignals(True)
        self.pause.setChecked(dispatcher.schedules_paused)
        self.pause.blockSignals(False)
        self._show_next(dispatcher)
        self._fill(self.needs_human, [(card, f"{card}　{OUTCOME_LABELS.get(reason, reason)}") for card, reason in dispatcher.skipped.items()])
        self.unskip.setEnabled(bool(dispatcher.skipped))
        self._entries = {entry.run_id: entry for entry in dispatcher.history}
        self._fill(self.history, [(entry.run_id, history_row(entry)) for entry in dispatcher.history[:20]])
        self._show_detail(self.history.currentItem())
        self._fill(
            self.schedule_history,
            [
                (f"{event.lane_id}-{event.schedule_id}-{event.at}",
                 f"{timefmt.display(event.at)}  {event.lane_id} {event.schedule_id}  {'開始' if event.action == 'start' else '結束'}  {SCHEDULE_RESULTS.get(event.result, event.result)}")
                for event in dispatcher.schedule_history[:20]
            ],
        )

    def _lane_card(self, lane: Lane, now: datetime) -> LaneCard:
        card = LaneCard(lane, now)
        card.action.connect(self.lane_action)
        card.configure.connect(self.lane_config)
        card.report.connect(self.report_requested)
        card.schedule_add.connect(self.schedule_add)
        card.schedule_delete.connect(self.schedule_delete)
        card.schedule_toggle.connect(self.schedule_toggle)
        self.cards[lane.lane_id] = card
        self.lane_box.addWidget(card)
        return card

    def _show_next(self, dispatcher: Dispatcher) -> None:
        chosen = dispatcher.next_card()
        if chosen is None:
            self.next_detail.setText("目前沒有可派的紅、黃、灰工項。")
            self.next_dot.setStyleSheet("background:#8b949e; border-radius:5px;")
            return
        self.next_detail.setText(f"{_NEXT_LABEL[chosen.zone]}　{chosen.item_id}　{chosen.title}")
        self.next_dot.setStyleSheet(f"background:{_NEXT_COLOR[chosen.zone]}; border-radius:5px;")

    def _show_detail(self, row: QListWidgetItem | None, _previous=None) -> None:
        entry = self._entries.get(row.data(Qt.UserRole)) if row is not None else None
        text = history_detail(entry) if entry is not None else ""
        if self.detail.toPlainText() != text:
            self.detail.setPlainText(text)

    def _unskip(self) -> None:
        row = self.needs_human.currentItem() or self.needs_human.item(0)
        if row is not None:
            self.unskip_requested.emit(row.data(Qt.UserRole))

    @staticmethod
    def _fill(widget: QListWidget, rows: list[tuple[str, str]]) -> None:
        selected = widget.currentItem().data(Qt.UserRole) if widget.currentItem() else None
        widget.clear()
        for key, text in rows:
            row = QListWidgetItem(text)
            row.setData(Qt.UserRole, key)
            widget.addItem(row)
            if key == selected:
                widget.setCurrentItem(row)

    @staticmethod
    def _title(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("pageTitle")
        return label

    def _button(self, label: str, name: str, role: str, handler) -> QPushButton:
        button = QPushButton(label)
        button.setObjectName(name)
        if role:
            button.setProperty("role", role)
        button.clicked.connect(handler)
        return button


def history_row(entry: HistoryEntry) -> str:
    text = f"{timefmt.display(entry.at)}  {entry.lane_id}  {entry.card_id}  {OUTCOME_LABELS.get(entry.outcome, entry.outcome)}"
    if entry.channel:
        text += f"（{CHANNEL_LABELS.get(entry.channel, entry.channel)}）"
    if entry.started_by:
        text += f"（排程 {entry.started_by}）"
    return text


def history_detail(entry: HistoryEntry) -> str:
    lines = [
        f"派工編號  {entry.run_id}",
        f"Agent     {entry.lane_id} · {AGENT_LABELS.get(entry.agent, entry.agent)}" + ("（視窗模式）" if entry.detached else ""),
        f"工項      {entry.card_id} {entry.title}",
        f"結果      {OUTCOME_LABELS.get(entry.outcome, entry.outcome)}"
        + (f" · 經由{CHANNEL_LABELS.get(entry.channel, entry.channel)}" if entry.channel else ""),
        f"開始      {timefmt.display(entry.started_at)}",
        f"結束      {timefmt.display(entry.at)}",
    ]
    if entry.started_by:
        lines.append(f"排程      {entry.started_by}")
    if entry.note:
        lines.append(f"說明      {entry.note}")
    if entry.report_error:
        lines.append(f"回報檔錯誤  {entry.report_error}")
    if entry.ignored:
        lines.append("較晚的回報（已忽略）  " + "、".join(CHANNEL_LABELS.get(name, name) for name in entry.ignored))
    lines += ["", "── 輸出 ──", entry.output.rstrip() or "（沒有輸出）", "", "── 提示詞 ──", entry.prompt.rstrip() or "（無）"]
    return "\n".join(lines)


def lane_status(lane: Lane, now: datetime, next_runs: dict) -> str:
    state = STATE_LABELS[lane.state]
    if lane.current is not None:
        elapsed = int((now - lane.current.started_at).total_seconds())
        limit = "不限" if lane.limit is None else str(lane.limit)
        run = lane.current
        origin = f" · 排程啟動（{run.started_by}）" if run.started_by else ""
        mode = f"在 {AGENT_LABELS[run.agent]} 視窗執行（回報才算完成）" if run.detached else "模擬執行，等待回報"
        problem = f" · 回報檔無效：{run.report_error}" if run.report_error else ""
        return (
            f"{state} · 第 {lane.dispatched} 張（{limit}） · {run.card_id} {run.title}"
            f" · 經過 {elapsed // 60:02d}:{elapsed % 60:02d} · {mode}{origin}{problem}"
        )
    if lane.state == "error":
        return f"錯誤 · {REASON_LABELS.get(lane.stop_reason, lane.stop_reason)} · {lane.error}"
    text = f"{state} · 上次停止原因：{REASON_LABELS.get(lane.stop_reason, lane.stop_reason)}"
    upcoming = [value for value in next_runs.values() if value and value[1] == "start"]
    if upcoming:
        text += f" · 下次排程 {min(upcoming)[0]:%m/%d %H:%M}"
    return text
