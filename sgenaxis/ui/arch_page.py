"""Module architecture DAG page matching the HTML workbench view."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QFont,
    QFontMetricsF,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
)
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMenu,
    QStyle,
    QComboBox,
    QFormLayout,
    QFrame,
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.ui import theme


@dataclass(frozen=True)
class ArchModule:
    code: str
    name: str
    kind: str
    status: str
    tone: str
    port: str
    desc: str
    tasks: tuple[tuple[str, str, str], ...]
    x: int
    y: int


MODULES = (
    ArchModule("UI", "工程控制台", "介面", "已驗證", "ok", "IWorkbenchCommands", "PySide6 桌面控制台。頁面只發訊號，MainWindow 呼叫 Session／Dispatcher 再重繪。", (("PSIDE-01..06", "選單、側欄、工項表、Git、設定、狀態列", "已驗證"),), 16, 230),
    ArchModule("DISP", "Agent 派工", "應用", "已驗證", "ok", "IDispatchCommands", "多條 Agent 並行，每條一次一張；紅 > 黃 > 灰；需人工清單、逾時、快速失敗與排程觸發。", (("INV-BD-1..14", "選卡與狀態機", "已驗證"), ("INV-BD-25..34", "多條並行與錯誤停機", "已驗證")), 250, 60),
    ArchModule("STATS", "期間統計", "查詢", "已驗證", "ok", "IStatsQuery", "日／週／月的新增、完成、同期新增已完成率與累計完成率。", (("BOARD-01", "期間統計", "已驗證"),), 250, 340),
    ArchModule("REL", "部署與發布", "發布", "資料已接", "run", "IReleaseStore · IFileProbe", "版本來自看板佈版紀錄；成品與 dist/ 即時檢查（不存在就如實顯示）、佈版報告與 CHANGELOG。部署尚未接上。", (("BOARD-05", "最近佈版資料", "已驗證"), ("DEPLOY", "部署", "未開始")), 250, 456),
    ArchModule("SCHED", "排程", "領域", "已驗證", "ok", "ISchedule", "單次／每天／時段（可跨午夜）；只在程式開著時生效，錯過不補跑。", (("INV-BD-48..51", "排程規則", "已驗證"),), 500, 16),
    ArchModule("LAUNCH", "Agent 啟動", "Port", "模擬", "run", "IAgentLauncher", "argv 只來自 Agent 規格，卡片文字不進命令列，安全字元檢查並禁止權限繞過旗標；帶固定環境變數。視窗模式（Antigravity）只看回報。預設 DryRun；沙盒專案可在設定切到實際啟動。", (("INV-BD-15..19", "啟動安全與環境變數", "已驗證"), ("INV-BD-39..42", "視窗模式", "已驗證"), ("AC-BD-4", "真實啟動（沙盒）", "已驗證")), 500, 126),
    ArchModule("REPORT", "回報管道", "Port", "已驗證", "ok", "IReportInbox", "回報檔（.sgenaxis/report-inbox）為主、輸出標記與回報指令為備援，先到先贏；無效回報檔移到 rejected。", (("INV-BD-43..47", "三個回報管道", "已驗證"),), 500, 236),
    ArchModule("BOARD", "工項燈號", "領域", "已驗證", "ok", "ITaskRules", "四燈號、完成時間只在綠燈、首次進黃記開始、20 筆燈號紀錄、版本衝突、使用者優先、驗收＝綠燈＋owner 確認。", (("INV-BL-1..11", "工項規則", "已驗證"),), 500, 346),
    ArchModule("STORE", "工項儲存", "Port", "已驗證", "ok", "ITaskStore", "工項的唯一真相：<專案>/.sgenaxis/tasks.json（hb-board/1）。鎖檔＋暫存檔＋os.replace，版本不符時檔案不變；派工狀態另存 dispatch.json。", (("INV-BL-5/8", "版本檢查與原子寫入", "已驗證"), ("INV-BL-10", "hb-board/1 格式", "已驗證")), 748, 346),
)
LINKS = (
    ("UI", "DISP"),
    ("UI", "BOARD"),
    ("UI", "STATS"),
    ("UI", "REL"),
    ("DISP", "SCHED"),
    ("DISP", "LAUNCH"),
    ("DISP", "REPORT"),
    ("DISP", "BOARD"),
    ("REPORT", "BOARD"),
    ("STATS", "BOARD"),
    ("BOARD", "STORE"),
)
TONE_COLORS = {"": "#8b949e", "run": "#f2b544", "review": "#c084fc", "fail": "#f07979", "ok": "#5bc98b"}
KINDS = ("介面", "應用", "查詢", "發布", "領域", "Port")
NODE_W = 172
NODE_H = 86
PORT_R = 5
PORT_COLORS = {"input": "#8b949e", "output": "#5bc98b"}


class ArchNode(QGraphicsObject):
    clicked = Signal(str)
    moved = Signal(str)
    expanded_changed = Signal(str, bool)
    link_started = Signal(str, str)
    link_dragged = Signal(QPointF)
    link_finished = Signal(str, QPointF)

    def __init__(self, module: ArchModule) -> None:
        super().__init__()
        self.module = module
        self.selected = False
        self.expanded = False
        self._press_pos = QPointF()
        self._double_click = False
        self._linking = False
        self.hover_port: str | None = None
        self.setPos(module.x, module.y)
        self.setCursor(Qt.OpenHandCursor)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setToolTip(f"{module.code} {module.name}\n拖曳移動位置，按 ▸ 或雙擊展開資訊\n左球 input、右球 output：按住球拖到其他節點可新增接線")

    def height(self) -> float:
        return NODE_H + self._detail_height() if self.expanded else NODE_H

    def body_rect(self) -> QRectF:
        return QRectF(0, 0, NODE_W, self.height())

    def boundingRect(self) -> QRectF:
        return self.body_rect().adjusted(-PORT_R - 1, -PORT_R - 1, PORT_R + 1, PORT_R + 1)

    def ports(self) -> dict[str, QPointF]:
        return {"input": QPointF(0, NODE_H / 2), "output": QPointF(NODE_W, NODE_H / 2)}

    def port_at(self, pos: QPointF) -> str | None:
        for side, center in self.ports().items():
            if (pos - center).manhattanLength() <= PORT_R + 5:
                return side
        return None

    def port_scene_pos(self, side: str) -> QPointF:
        return self.mapToScene(self.ports()[side])

    def toggle_rect(self) -> QRectF:
        return QRectF(NODE_W - 28, 8, 20, 20)

    def _detail_lines(self) -> list[tuple[str, str]]:
        lines = [("類型", self.module.kind), ("Input Port", self.module.port), ("描述", self.module.desc)]
        lines.append(("相關工項", f"{len(self.module.tasks)} 筆"))
        lines.extend((task_id, f"{name} · {status}") for task_id, name, status in self.module.tasks)
        return lines

    def _detail_height(self) -> float:
        metrics = QFontMetricsF(QFont("Microsoft JhengHei", 8))
        total = 10.0
        for label, value in self._detail_lines():
            total += metrics.height()
            total += metrics.boundingRect(QRectF(0, 0, NODE_W - 28, 400), Qt.TextWordWrap, value).height() + 4
        return total

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        t = theme.current()
        painter.setRenderHint(QPainter.Antialiasing, True)
        border = QColor(t["accent"]) if self.selected else QColor(t["border"])
        painter.setPen(QPen(border, 2 if self.selected else 1))
        painter.setBrush(QColor(t["surface"]))
        painter.drawRoundedRect(self.body_rect().adjusted(1, 1, -1, -1), 6, 6)
        painter.setPen(QColor(t["text"]))
        bold = QFont("Segoe UI", 10)
        bold.setBold(True)
        painter.setFont(bold)
        painter.drawText(QRectF(14, 12, NODE_W - 44, 20), Qt.AlignLeft, self.module.code)
        painter.setPen(QColor(t["faint"]))
        painter.drawText(self.toggle_rect(), Qt.AlignCenter, "▾" if self.expanded else "▸")
        painter.setFont(QFont("Microsoft JhengHei", 9))
        painter.setPen(QColor(t["muted"]))
        painter.drawText(QRectF(14, 34, NODE_W - 28, 20), Qt.AlignLeft, self.module.name)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(TONE_COLORS[self.module.tone]))
        painter.drawEllipse(QRectF(14, 62, 8, 8))
        painter.setPen(QColor(t["muted"]))
        painter.drawText(QRectF(28, 56, NODE_W - 40, 20), Qt.AlignLeft | Qt.AlignVCenter, self.module.status)
        if self.expanded:
            self._paint_details(painter)
        self._paint_ports(painter)

    def _paint_ports(self, painter: QPainter) -> None:
        t = theme.current()
        for kind, center in self.ports().items():
            active = kind == self.hover_port
            color = QColor(t["accent"]) if active else QColor(PORT_COLORS[kind])
            painter.setPen(QPen(color, 1.5))
            painter.setBrush(color if kind == "output" or active else QColor(t["port_hole"]))
            radius = PORT_R + 1 if active else PORT_R
            painter.drawEllipse(center, radius, radius)

    def _paint_details(self, painter: QPainter) -> None:
        t = theme.current()
        painter.setPen(QPen(QColor(t["node_divider"]), 1))
        painter.drawLine(QPointF(10, NODE_H - 2), QPointF(NODE_W - 10, NODE_H - 2))
        small = QFont("Microsoft JhengHei", 8)
        metrics = QFontMetricsF(small)
        painter.setFont(small)
        y = NODE_H + 6.0
        for label, value in self._detail_lines():
            painter.setPen(QColor(t["faint"]))
            painter.drawText(QRectF(14, y, NODE_W - 28, metrics.height()), Qt.AlignLeft, label)
            y += metrics.height()
            box = metrics.boundingRect(QRectF(0, 0, NODE_W - 28, 400), Qt.TextWordWrap, value)
            painter.setPen(QColor(t["node_detail"]))
            painter.drawText(QRectF(14, y, NODE_W - 28, box.height()), Qt.AlignLeft | Qt.TextWordWrap, value)
            y += box.height() + 4

    def set_selected(self, selected: bool) -> None:
        self.selected = selected
        self.update()

    def set_expanded(self, expanded: bool) -> None:
        if expanded == self.expanded:
            return
        self.prepareGeometryChange()
        self.expanded = expanded
        self.setZValue(1 if expanded else 0)
        self.update()
        self.expanded_changed.emit(self.module.code, expanded)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self.moved.emit(self.module.code)
        return super().itemChange(change, value)

    def hoverMoveEvent(self, event) -> None:
        port = self.port_at(event.pos())
        if port != self.hover_port:
            self.hover_port = port
            self.setCursor(Qt.CrossCursor if port else Qt.OpenHandCursor)
            self.update()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.hover_port = None
        self.setCursor(Qt.OpenHandCursor)
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self._press_pos = event.scenePos()
        port = self.port_at(event.pos()) if event.button() == Qt.LeftButton else None
        if port:
            self._linking = True
            self.link_started.emit(self.module.code, port)
            event.accept()
            return
        self.setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._linking:
            self.link_dragged.emit(event.scenePos())
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._linking:
            self._linking = False
            self.link_finished.emit(self.module.code, event.scenePos())
            event.accept()
            return
        self.setCursor(Qt.OpenHandCursor)
        super().mouseReleaseEvent(event)
        if self._double_click:
            self._double_click = False
            return
        if (event.scenePos() - self._press_pos).manhattanLength() > 4:
            return
        if self.toggle_rect().contains(event.pos()):
            self.set_expanded(not self.expanded)
            return
        self.clicked.emit(self.module.code)

    def mouseDoubleClickEvent(self, event) -> None:
        self._double_click = True
        self.set_expanded(not self.expanded)
        event.accept()


class ArchEdge(QGraphicsPathItem):
    def __init__(self, source: str, target: str, on_remove: Callable[["ArchEdge"], None]) -> None:
        super().__init__()
        self.source = source
        self.target = target
        self._on_remove = on_remove
        self.setData(0, f"{source}->{target}")
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{source} → {target}\n點選後按 Delete 或右鍵取消接線")
        self._hover = False
        self.restyle()

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self.path())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            self.restyle()
        return super().itemChange(change, value)

    def hoverEnterEvent(self, event) -> None:
        self._hover = True
        self.restyle()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hover = False
        self.restyle()
        super().hoverLeaveEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.setSelected(True)
        menu = QMenu()
        remove = menu.addAction(f"取消接線  {self.source} → {self.target}")
        if menu.exec(event.screenPos()) is remove:
            self._on_remove(self)
        event.accept()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        option.state &= ~QStyle.State_Selected
        super().paint(painter, option, widget)

    def restyle(self) -> None:
        t = theme.current()
        if self.isSelected():
            self.setPen(QPen(QColor(t["accent"]), 2.5))
        elif self._hover:
            self.setPen(QPen(QColor(t["edge_hover"]), 2))
        else:
            self.setPen(QPen(QColor(t["edge"]), 1.25))


class ArchPage(QWidget):
    notice = Signal(str)
    open_ui_design = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("archPage")
        self.selected = "DISP"
        self.scale = 1.0
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self.dock_host = QMainWindow()
        self.dock_host.setObjectName("archDockHost")
        self.dock_host.setWindowFlags(Qt.Widget)
        self.dock_host.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowTabbedDocks)
        self.dock_host.setCentralWidget(self._main())
        self.inspector_dock = QDockWidget("Inspector", self.dock_host)
        self.inspector_dock.setObjectName("archInspectorDock")
        self.inspector_dock.setToolTip("拖曳標題列可移到左側、右側或浮動；雙擊標題列切換浮動")
        self.inspector_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.inspector_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        self.inspector_dock.setWidget(self._inspector())
        self.inspector_dock.dockLocationChanged.connect(self._inspector_docked)
        self.inspector_dock.topLevelChanged.connect(self._inspector_floated)
        self.dock_host.addDockWidget(Qt.RightDockWidgetArea, self.inspector_dock)
        self.dock_host.resizeDocks([self.inspector_dock], [300], Qt.Horizontal)
        row.addWidget(self.dock_host)
        self.select_module("DISP")

    def inspector_area(self) -> str:
        if self.inspector_dock.isFloating():
            return "floating"
        area = self.dock_host.dockWidgetArea(self.inspector_dock)
        return "left" if area == Qt.LeftDockWidgetArea else "right"

    def move_inspector(self, where: str) -> None:
        if where == "floating":
            self.inspector_dock.setFloating(True)
            return
        self.inspector_dock.setFloating(False)
        area = Qt.LeftDockWidgetArea if where == "left" else Qt.RightDockWidgetArea
        self.dock_host.addDockWidget(area, self.inspector_dock)

    def _inspector_docked(self, area) -> None:
        self.notice.emit("Inspector 已移到左側" if area == Qt.LeftDockWidgetArea else "Inspector 已移到右側")

    def _inspector_floated(self, floating: bool) -> None:
        if floating:
            self.notice.emit("Inspector 已浮動，拖回左右側或雙擊標題列可停靠")

    def _main(self) -> QWidget:
        main = QWidget()
        layout = QVBoxLayout(main)
        layout.setContentsMargins(16, 14, 16, 12)
        self.title = QLabel("模組架構")
        self.title.setObjectName("archPageTitle")
        sub = QLabel("檢視模組責任與依賴方向。")
        sub.setObjectName("muted")
        layout.addWidget(self.title)
        layout.addWidget(sub)
        tools = QHBoxLayout()
        self.edit_button = QPushButton("編輯草稿")
        self.edit_button.setObjectName("btnArchEdit")
        self.edit_button.setCheckable(True)
        self.edit_button.toggled.connect(self._toggle_edit)
        tools.addWidget(self.edit_button)
        for label, name, handler in (
            ("適合視窗", "btnArchFit", self.fit),
            ("放大", "btnArchZoomIn", lambda: self.zoom(0.1)),
            ("縮小", "btnArchZoomOut", lambda: self.zoom(-0.1)),
            ("重設位置與接線", "btnArchResetLayout", self.reset_layout),
        ):
            button = QPushButton(label)
            button.setObjectName(name)
            button.clicked.connect(handler)
            tools.addWidget(button)
        self.remove_link_button = QPushButton("取消接線")
        self.remove_link_button.setObjectName("btnArchRemoveLink")
        self.remove_link_button.setToolTip("先點選一條接線，再按此鈕或 Delete")
        self.remove_link_button.setEnabled(False)
        self.remove_link_button.clicked.connect(lambda: self.remove_edge())
        tools.addWidget(self.remove_link_button)
        tools.addStretch(1)
        legend = QLabel("A → B 表示 A 依賴 B　● 未開始　● 模擬　● 待核准　● 失敗　● 已驗證")
        legend.setObjectName("muted")
        tools.addWidget(legend)
        layout.addLayout(tools)
        self.scene = QGraphicsScene(0, 0, 940, 560)
        self.nodes: dict[str, ArchNode] = {}
        for module in MODULES:
            node = ArchNode(module)
            node.clicked.connect(self._node_clicked)
            node.moved.connect(lambda _code: self._update_edges())
            node.expanded_changed.connect(self._node_expanded)
            node.link_started.connect(self.start_link)
            node.link_dragged.connect(self.drag_link)
            node.link_finished.connect(self.finish_link)
            self.scene.addItem(node)
            self.nodes[module.code] = node
        self.edges = self._draw_edges()
        self.draft_wire = QGraphicsPathItem()
        self.draft_wire.setZValue(2)
        self.draft_wire.setVisible(False)
        self.scene.addItem(self.draft_wire)
        self._draft_start = QPointF()
        self._draft_port = "output"
        self.view = QGraphicsView(self.scene)
        self.view.setObjectName("archStage")
        self.view.setRenderHint(QPainter.Antialiasing, True)
        self.apply_theme()
        self.scene.selectionChanged.connect(self._sync_link_button)
        delete = QAction("取消接線", self.view)
        delete.setShortcuts([QKeySequence(Qt.Key_Delete), QKeySequence(Qt.Key_Backspace)])
        delete.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        delete.triggered.connect(self._delete_pressed)
        self.view.addAction(delete)
        layout.addWidget(self.view, 1)
        return main

    def _draw_edges(self) -> list[ArchEdge]:
        items: list[ArchEdge] = []
        for source, target in LINKS:
            item = ArchEdge(source, target, self.remove_edge)
            self.scene.addItem(item)
            items.append(item)
        self._update_edges(items)
        return items

    def _update_edges(self, items: list[ArchEdge] | None = None) -> None:
        for item in items if items is not None else self.edges:
            item.setPath(_edge_path(self.nodes[item.source], self.nodes[item.target]))
        bounds = self.scene.itemsBoundingRect().adjusted(-40, -40, 40, 40)
        self.scene.setSceneRect(bounds.united(QRectF(0, 0, 940, 500)))

    def apply_theme(self) -> None:
        t = theme.current()
        self.view.setBackgroundBrush(QBrush(QColor(t["canvas"])))
        self.draft_wire.setPen(QPen(QColor(t["accent"]), 2, Qt.DashLine))
        for edge in self.edges:
            edge.restyle()
        self.scene.update()

    def start_link(self, code: str, port: str) -> None:
        self.scene.clearSelection()
        self._draft_port = port
        self._draft_start = self.nodes[code].port_scene_pos(port)
        self.drag_link(self._draft_start)
        self.draft_wire.setVisible(True)
        if port == "output":
            self.notice.emit(f"從 {code} output 拉出接線，放到目標節點的 input")
        else:
            self.notice.emit(f"從 {code} input 拉出接線，放到來源節點的 output")

    def drag_link(self, point: QPointF) -> None:
        if self._draft_port == "output":
            self.draft_wire.setPath(_wire_path(self._draft_start, point))
        else:
            self.draft_wire.setPath(_wire_path(point, self._draft_start))

    def node_at(self, point: QPointF) -> ArchNode | None:
        for node in sorted(self.nodes.values(), key=lambda item: -item.zValue()):
            if node.boundingRect().contains(node.mapFromScene(point)):
                return node
        return None

    def finish_link(self, code: str, point: QPointF) -> None:
        self.draft_wire.setVisible(False)
        other_node = self.node_at(point)
        if other_node is None:
            self.notice.emit("未放到節點上，接線未建立")
            return
        other = other_node.module.code
        if other == code:
            self.notice.emit("不能連到自己")
            return
        source, target = (code, other) if self._draft_port == "output" else (other, code)
        if any({edge.source, edge.target} == {source, target} for edge in self.edges):
            self.notice.emit(f"{source} 與 {target} 已有接線")
            return
        edge = ArchEdge(source, target, self.remove_edge)
        self.scene.addItem(edge)
        self.edges.append(edge)
        self._update_edges([edge])
        self.notice.emit(f"已新增接線 {source} → {target}")

    def selected_edge(self) -> ArchEdge | None:
        return next((item for item in self.edges if item.isSelected()), None)

    def remove_edge(self, edge: ArchEdge | None = None) -> None:
        edge = edge or self.selected_edge()
        if edge is None:
            self.notice.emit("請先點選要取消的接線")
            return
        self.edges.remove(edge)
        self.scene.removeItem(edge)
        self._sync_link_button()
        self.notice.emit(f"已取消接線 {edge.source} → {edge.target}")

    def _sync_link_button(self) -> None:
        self.remove_link_button.setEnabled(self.selected_edge() is not None)

    def _node_expanded(self, code: str, expanded: bool) -> None:
        self._update_edges()
        self.select_module(code)
        self.notice.emit(f"已展開 {code} 模組資訊" if expanded else f"已收合 {code} 模組資訊")

    def reset_layout(self) -> None:
        for node in self.nodes.values():
            node.set_expanded(False)
            node.setPos(node.module.x, node.module.y)
        for edge in self.edges:
            self.scene.removeItem(edge)
        self.edges = self._draw_edges()
        self._sync_link_button()
        self.notice.emit("已重設模組位置與接線")

    def _inspector(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("archInspector")
        panel.setMinimumWidth(260)
        layout = QVBoxLayout(panel)
        tabs = QHBoxLayout()
        self.tab_buttons: dict[str, QPushButton] = {}
        self.tabs = QStackedWidget()
        for key, label in (("inspector", "Inspector"), ("props", "屬性")):
            button = QPushButton(label)
            button.setObjectName(f"archTab-{key}")
            button.setCheckable(True)
            button.setChecked(key == "inspector")
            button.clicked.connect(lambda _checked=False, name=key: self.show_tab(name))
            self.tab_buttons[key] = button
            tabs.addWidget(button)
        layout.addLayout(tabs)

        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.addWidget(_section("模組資訊"))
        form = QFormLayout()
        self.code = QLabel()
        self.code.setObjectName("archCode")
        self.name = QLabel()
        self.name.setObjectName("archName")
        self.kind = QComboBox()
        self.kind.setObjectName("archType")
        self.kind.addItems(KINDS)
        self.status = QLabel()
        self.status.setObjectName("archStatus")
        self.port = QLabel()
        self.port.setObjectName("archPort")
        self.desc = QLabel()
        self.desc.setObjectName("archDesc")
        self.desc.setWordWrap(True)
        form.addRow("模組代號", self.code)
        form.addRow("模組名稱", self.name)
        form.addRow("模組類型", self.kind)
        form.addRow("狀態", self.status)
        form.addRow("Input Port", self.port)
        form.addRow("模組描述", self.desc)
        info_layout.addLayout(form)
        open_spec = QPushButton("開啟模組規格")
        open_spec.setObjectName("btnOpenModuleSpec")
        open_spec.setProperty("role", "primary")
        open_spec.clicked.connect(lambda: self.notice.emit(f"已開啟 {self.selected} 模組規格"))
        info_layout.addWidget(open_spec)
        self.task_heading = _section("相關工項 (0)")
        info_layout.addWidget(self.task_heading)
        self.task_table = QTableWidget(0, 3)
        self.task_table.setObjectName("archTaskBody")
        self.task_table.setHorizontalHeaderLabels(["ID", "名稱", "狀態"])
        self.task_table.verticalHeader().setVisible(False)
        self.task_table.horizontalHeader().setStretchLastSection(True)
        info_layout.addWidget(self.task_table)
        info_layout.addWidget(_section("架構文件"))
        doc = QFormLayout()
        doc.addRow("版本", QLabel("DRAFT-0.1"))
        doc.addRow("最後更新", QLabel("2026-10-06 10:23"))
        info_layout.addLayout(doc)
        info_layout.addStretch(1)

        props = QWidget()
        props_form = QFormLayout(props)
        self.prop_code = QLabel()
        self.prop_name = QLabel()
        self.prop_kind = QLabel()
        self.prop_status = QLabel()
        self.prop_port = QLabel()
        self.prop_desc = QLabel()
        self.prop_desc.setWordWrap(True)
        for label, widget in (
            ("代號", self.prop_code),
            ("名稱", self.prop_name),
            ("類型", self.prop_kind),
            ("狀態", self.prop_status),
            ("Input Port", self.prop_port),
            ("描述", self.prop_desc),
        ):
            props_form.addRow(label, widget)
        self.tabs.addWidget(info)
        self.tabs.addWidget(props)
        layout.addWidget(self.tabs, 1)
        return panel

    def show_tab(self, name: str) -> None:
        for key, button in self.tab_buttons.items():
            button.setChecked(key == name)
        self.tabs.setCurrentIndex(0 if name == "inspector" else 1)

    def select_module(self, code: str) -> None:
        module = next(item for item in MODULES if item.code == code)
        self.selected = code
        for key, node in self.nodes.items():
            node.set_selected(key == code)
        self.code.setText(module.code)
        self.name.setText(module.name)
        self.kind.setCurrentText(module.kind)
        self.status.setText(module.status)
        self.port.setText(module.port)
        self.desc.setText(module.desc)
        self.task_heading.setText(f"相關工項 ({len(module.tasks)})")
        self.task_table.setRowCount(len(module.tasks))
        for row, values in enumerate(module.tasks):
            for column, value in enumerate(values):
                self.task_table.setItem(row, column, QTableWidgetItem(value))
        self.prop_code.setText(module.code)
        self.prop_name.setText(module.name)
        self.prop_kind.setText(module.kind)
        self.prop_status.setText(module.status)
        self.prop_port.setText(module.port)
        self.prop_desc.setText(module.desc)

    def set_heading(self, text: str) -> None:
        self.title.setText(text)

    def zoom(self, step: float) -> None:
        self.scale = max(0.6, min(1.6, round((self.scale + step) * 10) / 10))
        self.view.resetTransform()
        self.view.scale(self.scale, self.scale)

    def fit(self) -> None:
        self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.scale = self.view.transform().m11()

    def _delete_pressed(self) -> None:
        if self.selected_edge() is not None:
            self.remove_edge()

    def _node_clicked(self, code: str) -> None:
        self.scene.clearSelection()
        if code == "UI" and self.selected == "UI":
            self.open_ui_design.emit()
            return
        self.select_module(code)

    def _toggle_edit(self, enabled: bool) -> None:
        self.edit_button.setText("結束編輯" if enabled else "編輯草稿")
        self.notice.emit("已進入架構草稿編輯" if enabled else "已結束架構草稿編輯")


def _wire_path(start: QPointF, end: QPointF) -> QPainterPath:
    reach = max(abs(end.x() - start.x()) / 2, 60.0)
    path = QPainterPath(start)
    path.cubicTo(QPointF(start.x() + reach, start.y()), QPointF(end.x() - reach, end.y()), end)
    return path


def _edge_path(a: ArchNode, b: ArchNode) -> QPainterPath:
    return _wire_path(a.port_scene_pos("output"), b.port_scene_pos("input"))


def _section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("archSectionHead")
    return label
