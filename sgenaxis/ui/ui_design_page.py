"""UI design tool page matching the HTML Designer view."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

PALETTE = (
    ("文件", ("文件", "表單", "分隔（左右）", "分隔（上下）", "停靠工作區")),
    ("輸入", ("按鈕", "工具列", "輸入框", "多行文字", "下拉", "數值", "小數", "核取", "選單", "日期時間", "純文字", "字型", "顏色", "單選", "滑桿", "旋轉", "連結按鈕")),
    ("顯示", ("標籤", "進度條", "數字顯示", "顯示", "文字清單", "分隔線", "垂直分隔", "群組容器")),
    ("DCC", ("檢視器", "曲線", "節點樹", "層", "時間軸")),
)

NODES = {
    "form": {"name": "Form", "type": "Form", "palette": "表單", "w": 800, "h": 600, "x": 0, "y": 0},
    "transport": {"name": "Transport", "type": "工具列", "palette": "工具列", "w": 220, "h": 32, "x": 24, "y": 520},
    "slider": {"name": "Slider", "type": "滑桿", "palette": "滑桿", "w": 420, "h": 18, "x": 260, "y": 528},
}


class DesignCanvas(QFrame):
    node_clicked = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("designForm")
        self.setMinimumSize(520, 340)
        layout = QVBoxLayout(self)
        self.tag = QLabel("Form")
        self.tag.setObjectName("designFormTag")
        layout.addWidget(self.tag, 0, Qt.AlignLeft)
        layout.addStretch(1)
        bottom = QHBoxLayout()
        self.transport = QFrame()
        self.transport.setObjectName("designTransport")
        transport_row = QHBoxLayout(self.transport)
        transport_row.setContentsMargins(4, 2, 4, 2)
        for glyph, name in (("|◄", "上一格"), ("▶", "播放"), ("❚❚", "暫停"), ("■", "停止"), ("►|", "下一格")):
            button = QPushButton(glyph)
            button.setToolTip(name)
            button.setFixedWidth(34)
            button.clicked.connect(lambda _checked=False: self.node_clicked.emit("transport"))
            transport_row.addWidget(button)
        self.slider = QPushButton("")
        self.slider.setObjectName("designSlider")
        self.slider.setToolTip("滑桿")
        self.slider.setFixedHeight(14)
        self.slider.clicked.connect(lambda: self.node_clicked.emit("slider"))
        bottom.addWidget(self.transport)
        bottom.addWidget(self.slider, 1)
        layout.addLayout(bottom)

    def mousePressEvent(self, event) -> None:
        self.node_clicked.emit("form")
        event.accept()

    def set_selected(self, node: str) -> None:
        self.setProperty("selected", node == "form")
        self.transport.setProperty("selected", node == "transport")
        self.slider.setProperty("selected", node == "slider")
        for widget in (self, self.transport, self.slider):
            widget.style().unpolish(widget)
            widget.style().polish(widget)


class UiDesignPage(QWidget):
    notice = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("uiPage")
        self.zoom = 100
        self.selection = "form"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        modes = QHBoxLayout()
        modes.setContentsMargins(12, 8, 12, 0)
        self.mode_buttons: dict[str, QPushButton] = {}
        for key, label in (("viewer", "UI Viewer"), ("designer", "Designer")):
            button = QPushButton(label)
            button.setObjectName(f"designMode-{key}")
            button.setCheckable(True)
            button.setChecked(key == "designer")
            button.clicked.connect(lambda _checked=False, name=key: self.set_mode(name))
            self.mode_buttons[key] = button
            modes.addWidget(button)
        modes.addStretch(1)
        layout.addLayout(modes)
        body = QHBoxLayout()
        body.setSpacing(0)
        body.addWidget(self._palette())
        body.addWidget(self._stage(), 1)
        body.addWidget(self._properties())
        layout.addLayout(body, 1)
        self.select_node("form")

    def _palette(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("designerPalette")
        panel.setFixedWidth(190)
        layout = QVBoxLayout(panel)
        title = QLabel("元件")
        title.setObjectName("archSectionHead")
        layout.addWidget(title)
        self.palette = QTreeWidget()
        self.palette.setObjectName("designerTree")
        self.palette.setHeaderHidden(True)
        for group, items in PALETTE:
            parent = QTreeWidgetItem([group])
            for name in items:
                child = QTreeWidgetItem([name])
                child.setData(0, Qt.UserRole, name)
                parent.addChild(child)
            self.palette.addTopLevelItem(parent)
            parent.setExpanded(True)
        self.palette.itemClicked.connect(self._palette_clicked)
        layout.addWidget(self.palette, 1)
        return panel

    def _stage(self) -> QWidget:
        stage = QWidget()
        layout = QVBoxLayout(stage)
        bar = QHBoxLayout()
        self.state_label = QLabel("目前設計：Form · 800×600")
        self.state_label.setObjectName("designStateLabel")
        bar.addWidget(self.state_label)
        bar.addStretch(1)
        bar.addWidget(QLabel("視圖"))
        self.view_mode = QComboBox()
        self.view_mode.setObjectName("designerViewMode")
        self.view_mode.addItem("Form", "design")
        self.view_mode.addItem("預覽", "preview")
        self.view_mode.currentIndexChanged.connect(self._view_mode_changed)
        bar.addWidget(self.view_mode)
        zoom_out = QPushButton("-")
        zoom_out.setObjectName("btnDesignZoomOut")
        zoom_out.clicked.connect(lambda: self.set_zoom(self.zoom - 10))
        self.zoom_label = QLabel("100%")
        self.zoom_label.setObjectName("designerZoomLabel")
        zoom_in = QPushButton("+")
        zoom_in.setObjectName("btnDesignZoomIn")
        zoom_in.clicked.connect(lambda: self.set_zoom(self.zoom + 10))
        bar.addWidget(zoom_out)
        bar.addWidget(self.zoom_label)
        bar.addWidget(zoom_in)
        layout.addLayout(bar)
        stats = QHBoxLayout()
        self.stats: dict[str, QLabel] = {}
        for key, label in (("windows", "視窗"), ("menus", "選單"), ("buttons", "按鈕"), ("files", "程式檔案"), ("wires", "接線")):
            value = QLabel("0")
            value.setObjectName(f"stat-{key}")
            self.stats[key] = value
            stats.addWidget(QLabel(label))
            stats.addWidget(value)
        stats.addStretch(1)
        layout.addLayout(stats)
        self.canvas = DesignCanvas()
        self.canvas.node_clicked.connect(self.select_node)
        self.mode_note = QLabel("")
        self.mode_note.setObjectName("designerModeNote")
        self.mode_note.setWordWrap(True)
        self.mode_note.setVisible(False)
        holder = QScrollArea()
        holder.setWidgetResizable(True)
        holder.setWidget(self.canvas)
        layout.addWidget(holder, 1)
        layout.addWidget(self.mode_note)
        return stage

    def _properties(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("designerProps")
        panel.setFixedWidth(300)
        layout = QVBoxLayout(panel)
        tabs = QHBoxLayout()
        self.tab_buttons: dict[str, QPushButton] = {}
        for key, label in (("props", "Properties"), ("behavior", "Behavior"), ("testing", "Testing")):
            button = QPushButton(label)
            button.setObjectName(f"designTab-{key}")
            button.setCheckable(True)
            button.setChecked(key == "props")
            button.clicked.connect(lambda _checked=False, name=key: self.show_tab(name))
            self.tab_buttons[key] = button
            tabs.addWidget(button)
        layout.addLayout(tabs)
        self.tabs = QStackedWidget()
        self.tabs.addWidget(self._props_tab())
        behavior = QLabel("尚無行為綁定。可在此接上 click、change 與值變更。")
        behavior.setWordWrap(True)
        self.tabs.addWidget(behavior)
        testing = QLabel("BDD Status　—\nTDD Status　—\n尚無測試案例。")
        testing.setObjectName("designTesting")
        self.tabs.addWidget(testing)
        layout.addWidget(self.tabs, 1)
        ask = QPushButton("Ask Agent About This Node")
        ask.setObjectName("btnAskAgentNode")
        ask.clicked.connect(lambda: self.notice.emit(f"已詢問 Agent 關於 {self.name.text() or '節點'}"))
        layout.addWidget(ask)
        pattern = QLabel("Design Pattern Statistics\nNo design pattern links in scope")
        pattern.setObjectName("muted")
        layout.addWidget(pattern)
        return panel

    def _props_tab(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        body = QWidget()
        form = QFormLayout(body)
        self.name = QLineEdit()
        self.name.setObjectName("desName")
        self.type = QLineEdit()
        self.type.setObjectName("desType")
        self.type.setReadOnly(True)
        self.uuid = QLineEdit("c51a0ec5-0a89-4c06-9a45-8a2fd7090209")
        self.uuid.setReadOnly(True)
        self.status = QLineEdit("unset")
        self.status.setReadOnly(True)
        self.priority = QLineEdit()
        self.path = QLineEdit()
        form.addRow(_head("基本"))
        form.addRow("Name", self.name)
        form.addRow("Type", self.type)
        form.addRow("UUID", self.uuid)
        form.addRow("Status", self.status)
        form.addRow("Priority", self.priority)
        form.addRow("Path", self.path)
        form.addRow(_head("版面"))
        layer = QHBoxLayout()
        self.layer_buttons: dict[str, QPushButton] = {}
        for key, label in (("stack", "分層"), ("auto", "疊加 (Auto)")):
            button = QPushButton(label)
            button.setCheckable(True)
            button.setChecked(key == "auto")
            button.clicked.connect(lambda _checked=False, name=key: self._set_layer(name))
            self.layer_buttons[key] = button
            layer.addWidget(button)
        form.addRow(layer)
        self.x = _spin()
        self.y = _spin()
        self.w = _spin()
        self.h = _spin()
        self.x.setObjectName("desX")
        self.y.setObjectName("desY")
        self.w.setObjectName("desW")
        self.h.setObjectName("desH")
        form.addRow("X", self.x)
        form.addRow("Y", self.y)
        form.addRow("寬", self.w)
        form.addRow("高", self.h)
        form.addRow(_head("外觀"))
        self.title = QLineEdit()
        self.free = QCheckBox("自由")
        form.addRow("標題", self.title)
        form.addRow(self.free)
        form.addRow(_head("樣式"))
        self.background = QLineEdit("#0d0d0b")
        self.foreground = QLineEdit("#0d0d0b")
        self.font_size = _spin()
        self.border = _spin()
        self.font = QComboBox()
        self.font.addItems(("Default", "Segoe UI", "Microsoft JhengHei"))
        style_lib = QPushButton("從樣式庫...")
        style_lib.setObjectName("btnDesignStyleLib")
        style_lib.clicked.connect(lambda: self.notice.emit("已開啟樣式庫"))
        form.addRow("背景色", self.background)
        form.addRow("文字色", self.foreground)
        form.addRow("字級", self.font_size)
        form.addRow("框線", self.border)
        form.addRow("字型", self.font)
        form.addRow(style_lib)
        form.addRow(_head("控制"))
        self.visible = QComboBox()
        self.visible.addItems(("不隱藏", "隱藏", "僅設計時"))
        form.addRow("顯示狀態", self.visible)
        form.addRow(_head("群組"))
        form.addRow("BDD Status", QLabel("—"))
        form.addRow("TDD Status", QLabel("—"))
        for spin in (self.w, self.h):
            spin.valueChanged.connect(self._size_changed)
        scroll.setWidget(body)
        return scroll

    def set_stats(self, windows: int, menus: int, buttons: int, files: int, wires: int) -> None:
        for key, value in zip(("windows", "menus", "buttons", "files", "wires"), (windows, menus, buttons, files, wires)):
            self.stats[key].setText(str(value))

    def show_tab(self, name: str) -> None:
        for key, button in self.tab_buttons.items():
            button.setChecked(key == name)
        self.tabs.setCurrentIndex(("props", "behavior", "testing").index(name))

    def set_mode(self, mode: str) -> None:
        for key, button in self.mode_buttons.items():
            button.setChecked(key == mode)
        viewer = mode == "viewer"
        self.canvas.setVisible(not viewer)
        self.mode_note.setVisible(viewer)
        self.mode_note.setText("UI Viewer：檢視已完成的畫面，切回 Designer 可編修。" if viewer else "")

    def set_zoom(self, value: int) -> None:
        self.zoom = max(50, min(200, value))
        self.zoom_label.setText(f"{self.zoom}%")

    def select_node(self, node: str) -> None:
        entry = NODES[node]
        self.selection = node
        self.canvas.set_selected(node)
        self.name.setText(entry["name"])
        self.type.setText(entry["type"])
        for spin, key in ((self.x, "x"), (self.y, "y"), (self.w, "w"), (self.h, "h")):
            spin.blockSignals(True)
            spin.setValue(entry[key])
            spin.blockSignals(False)
        self._update_state_label()
        self._highlight_palette(entry["palette"])

    def _update_state_label(self) -> None:
        entry = NODES[self.selection]
        self.state_label.setText(
            f"目前設計：{self.name.text()} · {entry['type']} · {self.w.value()}×{self.h.value()} · {self.status.text() or 'unset'}"
        )

    def _size_changed(self) -> None:
        self._update_state_label()

    def _highlight_palette(self, name: str) -> None:
        for group_index in range(self.palette.topLevelItemCount()):
            group = self.palette.topLevelItem(group_index)
            for child_index in range(group.childCount()):
                child = group.child(child_index)
                child.setSelected(child.data(0, Qt.UserRole) == name)

    def _palette_clicked(self, item: QTreeWidgetItem) -> None:
        name = item.data(0, Qt.UserRole)
        if name:
            self.notice.emit(f"已選取元件：{name}")

    def _view_mode_changed(self) -> None:
        preview = self.view_mode.currentData() == "preview"
        self.canvas.tag.setVisible(not preview)
        self.notice.emit("已切換為預覽" if preview else "已切換為 Form")

    def _set_layer(self, name: str) -> None:
        for key, button in self.layer_buttons.items():
            button.setChecked(key == name)


def _spin() -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(0, 4000)
    return spin


def _head(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("archSectionHead")
    return label
