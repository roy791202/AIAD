"""SGenAxis main window. Menus and toolbar are PSIDE-01."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core.board import VersionConflict
from sgenaxis.core.dispatcher import DispatchError
from sgenaxis.core.session import LAUNCH_MODE_LABELS, WorkbenchSession
from sgenaxis.ui.agent_page import AgentDispatchPage
from sgenaxis.ui.arch_page import LINKS as ARCH_LINKS
from sgenaxis.ui.arch_page import MODULES as ARCH_MODULES
from sgenaxis.ui.arch_page import ArchPage
from sgenaxis.ui.exec_log import ExecLogPanel
from sgenaxis.ui.ui_design_page import UiDesignPage
from sgenaxis.ui.git_dialogs import CloneDialog, CommitDialog, HistoryDialog
from sgenaxis.ui.git_page import GitWorkspacePage
from sgenaxis.ui.icons import icon
from sgenaxis.ui.project_page import InspectorPanel, ProjectPage
from sgenaxis.ui.release_page import ReleasePage
from sgenaxis.ui.settings_dialog import SettingsDialog
from sgenaxis.ui.sidebar import TaskSidebar
from sgenaxis.ui.stats_page import StatsPage
from sgenaxis.ui.statusbar import WorkbenchStatusBar
from sgenaxis.ui.task_board import DOT_COLORS, TaskBoard, status_dot_icon
from sgenaxis.ui.theme import set_current, theme_qss


class MainWindow(QMainWindow):
    def __init__(self, session: WorkbenchSession | None = None) -> None:
        super().__init__()
        self.session = session or WorkbenchSession()
        self._inspector_user_hidden = False
        self.setWindowTitle("SGenAxis — Git 管理工作台")
        self.setWindowIcon(icon("app"))
        self.resize(1440, 900)
        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_status()
        self.apply_theme()
        self._show_page("tasks")
        self.dispatch_timer = QTimer(self)
        self.dispatch_timer.setInterval(1000)
        self.dispatch_timer.timeout.connect(self.tick_dispatch)
        self.dispatch_timer.start()
        if self.session.registry_error:
            self._note(f"專案清單無法讀取，本次不會記住開過的專案：{self.session.registry_error}")

    def tick_dispatch(self) -> None:
        before = self._dispatch_signature()
        try:
            self.session.dispatcher.tick()
        except ValueError as exc:
            self._note(str(exc))
        if self._dispatch_signature() != before:
            self.refresh()
        elif self.stack.currentWidget() is self.agent_page:
            self._show_dispatch()

    def closeEvent(self, event) -> None:
        self.dispatch_timer.stop()
        try:
            self.session.shutdown()
        except ValueError as exc:
            self._note(str(exc))
        super().closeEvent(event)

    def _dispatch_signature(self) -> tuple:
        dispatcher = self.session.dispatcher
        lanes = tuple((lane.state, lane.current.run_id if lane.current else "") for lane in dispatcher.lanes)
        return lanes, len(dispatcher.history), len(dispatcher.schedule_history), len(dispatcher.skipped)

    def apply_theme(self) -> None:
        set_current(self.session.ui_style, self.session.tone)
        sheet = theme_qss(self.session.ui_style, self.session.tone)
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(sheet)
        self.folder_glyph.setPixmap(icon("open").pixmap(14, 14))
        self.arch_page.apply_theme()
        self.update()
        for widget in self.findChildren(QWidget):
            widget.update()

    def _appearance_changed(self, message: str) -> None:
        self.apply_theme()
        self._note(message)

    def _launch_mode_changed(self, message: str) -> None:
        self.refresh()
        self._note(message)

    def _show_dispatch(self) -> None:
        self.agent_page.show_dispatch(
            self.session.dispatcher,
            self.session.clock.now(),
            self.session.board_label(),
            LAUNCH_MODE_LABELS[self.session.launch_mode],
        )

    def _refresh_release(self) -> None:
        try:
            releases = self.session.release_list()
        except ValueError as exc:
            releases = []
            self._note(str(exc))
        checks = {item.release_id: self.session.artifact_checks(item) for item in releases}
        self.release_page.show_data(releases, checks, self.session.dist_listing(), self.session.now_text())

    def refresh(self) -> None:
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for project in self.session.combo_projects():
            self.project_combo.addItem(project.name)
        index = self.project_combo.findText(self.session.current_name)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)
        self.project_combo.blockSignals(False)
        self.path_label.setText(self.session.current_path)
        self.branch_button.setText(self.session.branch)
        self._rebuild_recent()
        title, hint, _count = self.session.section()
        self.board.show_items(self.session.visible_items(), title, hint, self.session.filter_name)
        self._refresh_filter_counts()
        self.git_bar.setVisible(self.session.filter_name == "accepted")
        self.git_page.show_accepted(self.session.items)
        current = self.session.project_by_name(self.session.current_name)
        listed = [project for project in self.session.projects if project.listed]
        self.projects.set_projects(listed, self.session.current_name)
        remote = "未設定" if self.session.cloud_url == "https://git.local/sgenaxis.git" else self.session.cloud_url
        self.inspector.show_project(current, remote, self.session.agent_running)
        self.status.set_context(
            self.session.current_name,
            self.session.branch,
            "" if current is None else current.opened,
        )
        self.status.set_activity(self.session.progress, self.session.agent_running)
        self._show_dispatch()
        self.stats_page.show_stats(self.session.items)
        page = self.stack.currentWidget()
        if page is self.release_page:
            self._refresh_release()
        elif page is self.git_page:
            self.git_page.show_git(*self.session.git_status())
        self._settings.refresh_launch()
        self.data_label.setText(
            f"專案資料 · Agent {LAUNCH_MODE_LABELS[self.session.launch_mode]}"
            if self.session.project_open
            else "設計預覽 · 示範資料"
        )
        self.sidebar.set_agent_state(self.session.agent_running, len(self.session.dispatcher.lanes))
        self.sidebar.set_counts(self.session.counts())
        self._rebuild_project_menu()

    def _build_menu(self) -> None:
        brand = QLabel("SGenAxis")
        brand.setObjectName("brandLogo")
        self.menuBar().setCornerWidget(brand, Qt.TopLeftCorner)
        self.data_label = QLabel("設計預覽 · 示範資料")
        self.data_label.setObjectName("muted")
        self.menuBar().setCornerWidget(self.data_label, Qt.TopRightCorner)
        file_menu = self.menuBar().addMenu("檔案")
        self._action(file_menu, "新增專案...", self._create_project, QKeySequence.New, "new")
        self._action(file_menu, "開啟專案...", self._open_project, QKeySequence.Open, "open")
        self.recent_menu = file_menu.addMenu("最近專案")
        self.recent_menu.setIcon(icon("open"))
        file_menu.addSeparator()
        self._action(file_menu, "儲存", self._save, QKeySequence.Save, "save")
        save_as = QKeySequence("Ctrl+Shift+S")
        self._action(file_menu, "另存新檔", self._save_as, save_as, "save_as")
        file_menu.addSeparator()
        self._action(file_menu, "結束 SGenAxis", self.close, QKeySequence.Quit, "close")

        edit_menu = self.menuBar().addMenu("編輯")
        self._action(edit_menu, "復原 (Undo)", lambda: self._note("復原尚無紀錄"), QKeySequence.Undo, "undo")
        self._action(edit_menu, "重做 (Redo)", lambda: self._note("重做尚無紀錄"), QKeySequence.Redo, "redo")
        edit_menu.addSeparator()
        self._action(edit_menu, "全選變更項目", self._select_all_changes, QKeySequence.SelectAll)
        self._action(edit_menu, "清除全選", self._clear_selection, QKeySequence(Qt.Key_Escape))

        self.project_menu = self.menuBar().addMenu("專案")
        self._project_menu_break = self.project_menu.addSeparator()
        self._action(self.project_menu, "建立專案...", self._create_project)
        self.project_menu.addSeparator()
        self._action(self.project_menu, "重新掃描儲存庫變更", self._rescan, QKeySequence("F5"))

        module_menu = self.menuBar().addMenu("模組")
        self._action(module_menu, "已驗收（分支與變更）", lambda: self._choose_filter("accepted"), None, "history")
        self._action(module_menu, "模組架構圖 (UI-04 DAG)", lambda: self._show_page("arch"), None, "module")
        self._action(module_menu, "UI 設計工具 (14 頁面總覽)", lambda: self._show_page("ui"), None, "design")
        module_menu.addSeparator()
        self._action(module_menu, "Ports & Contracts 契約檢視", self._open_ports)
        module_menu.addSeparator()
        self._action(module_menu, "歷史", self._show_history, None, "history")
        self._action(module_menu, "GIT 設定", lambda: self._open_settings("git"), None, "settings")

        task_menu = self.menuBar().addMenu("工項")
        self._action(task_menu, "新增工項...", self._add_task, QKeySequence("Ctrl+T"))
        self._action(task_menu, "指派 Agent 任務...", self._dispatch_agent)
        task_menu.addSeparator()
        self._action(task_menu, "批次標註 BDD/TDD 標籤", self._batch_bdd)

        window_menu = self.menuBar().addMenu("視窗")
        self._action(window_menu, "重設為標準工作台佈局", self._reset_layout)
        self._action(window_menu, "顯示/隱藏 Inspector 側欄", self._toggle_inspector)
        self._action(window_menu, "顯示/隱藏 分支樹態面板", self._toggle_branch_tree)
        window_menu.addSeparator()
        self._action(window_menu, "設定", lambda: self._open_settings("general"), None, "settings")

        help_menu = self.menuBar().addMenu("說明")
        self._action(help_menu, "Qt / PySide 架構規格對照", self._show_qt_spec, None, "app")
        help_menu.addSeparator()
        self._action(help_menu, "關於 SGenAxis (v0.5.0)...", self._about, None, "help")

    def _action(self, menu, label: str, handler, shortcut: QKeySequence | None = None, icon_name: str | None = None) -> QAction:
        action = QAction(label, self)
        if icon_name is not None:
            action.setIcon(icon(icon_name, size=16))
        if shortcut is not None:
            action.setShortcut(shortcut)
        action.triggered.connect(handler)
        menu.addAction(action)
        return action

    def _build_toolbar(self) -> None:
        bar = QToolBar("專案")
        bar.setObjectName("projectToolbar")
        bar.setMovable(False)
        bar.setIconSize(QSize(16, 16))
        self.addToolBar(bar)
        project_label = QLabel("專案：")
        project_label.setObjectName("muted")
        bar.addWidget(project_label)
        self.project_combo = QComboBox()
        self.project_combo.setObjectName("projectCombo")
        self.project_combo.currentTextChanged.connect(self._combo_changed)
        bar.addWidget(self.project_combo)
        path_box = QWidget()
        path_box.setObjectName("pathBox")
        path_row = QHBoxLayout(path_box)
        path_row.setContentsMargins(8, 2, 10, 2)
        path_row.setSpacing(6)
        self.folder_glyph = QLabel()
        self.path_label = QLabel(self.session.current_path)
        self.path_label.setObjectName("repoPathText")
        path_row.addWidget(self.folder_glyph)
        path_row.addWidget(self.path_label)
        bar.addWidget(path_box)
        self.branch_button = QPushButton(icon("branch"), self.session.branch)
        self.branch_button.setObjectName("branchButton")
        self.branch_button.clicked.connect(self._toggle_branch_tree)
        bar.addWidget(self.branch_button)
        history = QPushButton("歷史")
        history.setObjectName("btnOpenLog")
        history.clicked.connect(self._show_history)
        git_settings = QPushButton(icon("settings"), "GIT 設定")
        git_settings.setObjectName("btnOpenSettings")
        git_settings.clicked.connect(lambda: self._open_settings("git"))
        bar.addWidget(history)
        bar.addWidget(git_settings)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bar.addWidget(spacer)
        qt_map = QPushButton(icon("app"), "Qt / PySide 對照")
        qt_map.setObjectName("btnQtMap")
        qt_map.clicked.connect(self._show_qt_spec)
        settings_button = QPushButton(icon("settings"), "")
        settings_button.setObjectName("btnSettingsIcon")
        settings_button.setToolTip("設定")
        settings_button.clicked.connect(lambda: self._open_settings("general"))
        help_button = QPushButton(icon("help"), "")
        help_button.setObjectName("btnHelpIcon")
        help_button.setToolTip("說明")
        help_button.clicked.connect(self._show_qt_spec)
        bar.addWidget(qt_map)
        bar.addWidget(settings_button)
        bar.addWidget(help_button)
        self.breadcrumb = QLabel("工項")
        self.breadcrumb.setObjectName("breadcrumb")
        find_task = QAction("搜尋", self)
        find_task.setShortcut(QKeySequence("Ctrl+K"))
        find_task.triggered.connect(self._focus_board_search)
        self.addAction(find_task)

    def _build_body(self) -> None:
        splitter = QSplitter()
        splitter.setObjectName("bodySplitter")
        self.sidebar = TaskSidebar()
        self.sidebar.page_chosen.connect(self._show_page)
        self.sidebar.filter_chosen.connect(self._choose_filter)
        self.filter_buttons = self.sidebar.filter_buttons
        self.stack = QStackedWidget()
        self.stack.setObjectName("mainStack")
        self.projects = ProjectPage()
        self.projects.selection_changed.connect(self._inspect_project)
        self.projects.open_requested.connect(self._open_from_table)
        self.projects.create_requested.connect(self._create_project)
        self.projects.clone_requested.connect(self._show_clone)
        self.board_page = QWidget()
        board_layout = QVBoxLayout(self.board_page)
        board_layout.setContentsMargins(0, 0, 0, 0)
        self.board = TaskBoard()
        self.board.add_task.clicked.connect(self._add_task)
        self.board.search.textChanged.connect(self._query_changed)
        self.board.source.currentIndexChanged.connect(self._source_changed)
        self.board.status_changed.connect(self._change_task_status)
        board_layout.addWidget(self.board, 1)
        self.stack.addWidget(self.projects)
        self.stack.addWidget(self.board_page)
        self.agent_page = AgentDispatchPage()
        self.agent_page.notice.connect(self._note)
        self._wire_dispatch(self.agent_page)
        self.stats_page = StatsPage()
        self.arch_page = ArchPage()
        self.arch_page.notice.connect(self._note)
        self.arch_page.open_ui_design.connect(lambda: self._show_page("ui"))
        self.schedule_page = self._info_page("schedulePage", "依賴排程", "排後面。")
        self.runlog_page = self._info_page("runlogPage", "執行紀錄", "活動紀錄顯示在下方面板。")
        self.git_page = GitWorkspacePage()
        self.git_page.commit_requested.connect(self._show_commit)
        self.git_page.clone_requested.connect(self._show_clone)
        self.git_page.command.connect(lambda action: self._note(f"{action} 尚未寫入 Git"))
        self.git_page.status_changed.connect(self._change_accepted_status)
        self.git_page.item_selected.connect(self._inspect_item)
        self.git_bar = self.git_page.toolbar
        self.release_page = ReleasePage()
        self.release_page.notice.connect(self._note)
        self.report_page = self._info_page("reportPage", "報告", "尚無報告。")
        self.standard_page = self._info_page("standardPage", "標準", "標準檢查排在工項之後。")
        self.ui_page = UiDesignPage()
        self.ui_page.notice.connect(self._note)
        self._settings = SettingsDialog(self.session, self.stack)
        self._settings.project_open_requested.connect(self._open_from_settings)
        self._settings.appearance_changed.connect(self._appearance_changed)
        self._settings.launch_mode_changed.connect(self._launch_mode_changed)
        for page in (
            self.agent_page, self.arch_page, self.schedule_page, self.runlog_page,
            self.git_page, self.release_page, self.report_page, self.standard_page, self.ui_page,
            self.stats_page, self._settings,
        ):
            self.stack.addWidget(page)
        self._pages = {
            "projects": self.projects,
            "agent": self.agent_page,
            "stats": self.stats_page,
            "tasks": self.board_page,
            "arch": self.arch_page,
            "schedule": self.schedule_page,
            "runlog": self.runlog_page,
            "git": self.git_page,
            "release": self.release_page,
            "report": self.report_page,
            "standard": self.standard_page,
            "ui": self.ui_page,
            "settings": self._settings,
        }
        self._crumbs = {
            "projects": "專案管理  ›  專案清單",
            "agent": "Agent 派工",
            "stats": "期間統計",
            "tasks": "工項",
            "arch": "模組架構",
            "schedule": "依賴排程",
            "runlog": "執行紀錄",
            "git": "Git",
            "release": "部署",
            "report": "報告",
            "standard": "標準",
            "ui": "UI 設計工具",
            "settings": "設定",
        }
        self.qt_page = self._info_page(
            "qtSpecPage",
            "Qt / PySide 架構規格對照",
            "QMainWindow 選單與工具列、左側導覽、中央工作區、Inspector 與底部活動紀錄。"
            "模組架構圖與 UI 設計工具維持後續工項。",
        )
        self.stack.addWidget(self.qt_page)
        self.branch_panel = self._branch_panel()
        center = QSplitter(Qt.Vertical)
        center.addWidget(self.stack)
        center.addWidget(self.branch_panel)
        self.exec_log = ExecLogPanel()
        self.exec_log.notice.connect(self._note)
        center.addWidget(self.exec_log)
        center.setSizes([600, 0, 220])
        self.center_splitter = center
        self.inspector = InspectorPanel()
        splitter.addWidget(self.sidebar)
        splitter.addWidget(center)
        splitter.addWidget(self.inspector)
        splitter.setSizes([196, 900, 300])
        self.body_splitter = splitter
        self.setCentralWidget(splitter)

    def _task_filters(self) -> QWidget:
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(12, 8, 12, 0)
        self.filter_buttons: dict[str, QPushButton] = {}
        self._filter_labels = {
            "overview": "總覽",
            "gray": "待辦",
            "yellow": "進行中",
            "red": "Bug",
            "green": "已完成",
            "accepted": "已驗收",
        }
        dot_colors = {
            "overview": ("#8b949e", "#f2b544", "#f07979", "#5bc98b", "#246bff"),
            "gray": (DOT_COLORS["gray"],),
            "yellow": (DOT_COLORS["yellow"],),
            "red": (DOT_COLORS["red"],),
            "green": (DOT_COLORS["green"],),
            "accepted": (DOT_COLORS["accepted"],),
        }
        for status, label in self._filter_labels.items():
            button = QPushButton(status_dot_icon(dot_colors[status]), label)
            button.setObjectName(f"filter-{status}")
            button.setCheckable(True)
            button.setChecked(status == "red")
            button.clicked.connect(lambda _checked=False, name=status: self._choose_filter(name))
            self.filter_buttons[status] = button
            row.addWidget(button)
        row.addStretch(1)
        return box

    def _refresh_filter_counts(self) -> None:
        self.sidebar.set_counts(self.session.counts())
        current = self.stack.currentWidget()
        if current is self.board_page:
            self.sidebar.set_filter(self.session.filter_name)
        elif current is self.git_page:
            self.sidebar.set_filter("accepted")

    def _branch_panel(self) -> QFrame:
        panel = QFrame()
        panel.setObjectName("branchPanel")
        panel.setVisible(False)
        layout = QVBoxLayout(panel)
        title = QLabel("分支與版本樹態")
        title.setObjectName("branchPanelTitle")
        layout.addWidget(title)
        body = QLabel(
            "main — 本地與遠端一致\n"
            "feature/spec-01 — 1 待推播\n"
            "refactor/worker — 本地分支"
        )
        body.setObjectName("branchPanelBody")
        layout.addWidget(body)
        layout.addStretch(1)
        return panel

    def _info_page(self, object_name: str, title: str, body: str) -> QWidget:
        page = QWidget()
        page.setObjectName(object_name)
        layout = QVBoxLayout(page)
        heading = QLabel(title)
        heading.setObjectName(object_name + "Title")
        layout.addWidget(heading)
        layout.addWidget(QLabel(body))
        layout.addStretch(1)
        return page

    def _build_status(self) -> None:
        self.status = WorkbenchStatusBar()
        self.setStatusBar(self.status)

    def _change_task_status(self, item_id: str, status: str) -> None:
        try:
            changed = self.session.set_item_status(item_id, status)
        except ValueError as exc:
            self._note(str(exc))
            self.refresh()
            return
        if changed and status == "accepted":
            self._note("已標註驗收，可在已驗收頁查看此工項")
        self.refresh()

    def _change_accepted_status(self, item_id: str, status: str) -> None:
        self._change_task_status(item_id, status)
        if status != "accepted":
            self._note("已改回工項燈號")

    def _inspect_item(self, item_id: str) -> None:
        self.inspector.show_task(next((item for item in self.session.items if item.item_id == item_id), None))

    def _choose_filter(self, status: str) -> None:
        self.session.set_filter(status)
        if status == "accepted":
            self._show_page("git")
            self._note("已開啟已驗收頁")
            return
        self._show_page("tasks")
        title, _hint, count = self.session.section()
        self._note(f"已開啟{title}（{count} 筆）")

    def _focus_board_search(self) -> None:
        self._show_page("tasks")
        self.board.search.setFocus()

    def _show_page(self, page: str) -> None:
        target = self._pages[page]
        self.stack.setCurrentWidget(target)
        self.sidebar.set_current(page)
        self.breadcrumb.setText(self._crumbs[page])
        if page == "arch":
            self.arch_page.set_heading("模組架構")
            self._note("已切換至【模組架構圖 (UI-04)】：依賴 DAG 畫布")
        elif page == "ui":
            self._refresh_design_stats()
            self._note("已切換至【UI 設計工具】：Designer")
        elif page == "schedule":
            self._note("排後面")
        self.refresh()
        self._apply_inspector(page)

    def _toolbar_query(self, text: str) -> None:
        if self.stack.currentWidget() is self.projects:
            self.projects.search.setText(text)
        elif self.stack.currentWidget() is self.board_page:
            self.board.search.setText(text)

    def _inspect_project(self, name: str) -> None:
        project = self.session.project_by_name(name)
        remote = "未設定" if self.session.cloud_url == "https://git.local/sgenaxis.git" else self.session.cloud_url
        self.inspector.show_project(project, remote, self.session.agent_running)

    def _open_from_table(self, name: str) -> None:
        self._open_from_settings(name)

    def _query_changed(self, text: str) -> None:
        self.session.query = text
        self.refresh()

    def _source_changed(self) -> None:
        self.session.set_source(self.board.source.currentData())
        self.refresh()

    def _combo_changed(self, name: str) -> None:
        if not name or name == self.session.current_name:
            return
        try:
            self.session.open_named(name)
        except ValueError as exc:
            self._note(str(exc))
        self.refresh()

    def _rebuild_recent(self) -> None:
        self.recent_menu.clear()
        for name in self.session.recent:
            project = self.session.project_by_name(name)
            label = project.path if project is not None else name
            action = self.recent_menu.addAction(label)
            action.triggered.connect(lambda _checked=False, picked=name: self._open_recent(picked))

    def _open_recent(self, name: str) -> None:
        try:
            self.session.open_named(name)
        except ValueError as exc:
            self._note(str(exc))
            return
        self.refresh()
        self._note(f"已開啟 {name}")

    def _create_project(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("建立專案")
        name = QLineEdit()
        name.setObjectName("skelName")
        root = QLineEdit(r"D:\AIAD")
        root.setObjectName("skelRoot")
        form = QFormLayout(dialog)
        form.addRow("名稱", name)
        form.addRow("根目錄", root)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        try:
            created = self.session.create_project(name.text(), root.text())
        except ValueError as exc:
            self._note(str(exc))
            return
        self.refresh()
        self._note(f"已建立 {created.name}")

    def _open_project(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("開啟專案")
        dialog.setObjectName("openProjModal")
        layout = QVBoxLayout(dialog)
        combo = QComboBox()
        combo.setObjectName("openProjList")
        for project in self.session.projects:
            combo.addItem(f"{project.name}  {project.path}", project.name)
        path = QLabel("")
        path.setObjectName("openProjPath")

        def show_path() -> None:
            project = self.session.project_by_name(combo.currentData())
            path.setText("" if project is None else project.path)

        combo.currentIndexChanged.connect(show_path)
        show_path()
        layout.addWidget(combo)
        layout.addWidget(path)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        if dialog.exec() != QDialog.Accepted:
            return
        self._open_recent(combo.currentData())

    def _save(self) -> None:
        self._note("已儲存工作台狀態")

    def _save_as(self) -> None:
        self._note("已另存工作台狀態")

    def _open_settings(self, page: str) -> None:
        self._show_page("settings")
        self._settings.refresh_projects()
        self._settings.show_page(page)

    def _open_from_settings(self, name: str) -> None:
        try:
            self.session.open_named(name)
        except ValueError as exc:
            self._note(str(exc))
            return
        self.refresh()
        if self._settings is not None:
            self._settings.refresh_projects()
        self._note(f"已開啟 {name}")

    def _show_history(self) -> None:
        HistoryDialog(self.session.branch, self).exec()
        self._note("已重新載入歷史")

    def _show_commit(self) -> None:
        dialog = CommitDialog(self)
        if dialog.exec() == QDialog.Accepted:
            self._note("已記錄提交說明，尚未寫入 Git")

    def _show_clone(self) -> None:
        dialog = CloneDialog(self.session.cloud_url, self)
        if dialog.exec() == QDialog.Accepted:
            self.session.apply_cloud_url(dialog.url.text())
            self._note("已記錄 Clone URL，尚未執行 git clone")

    def _wire_dispatch(self, page: AgentDispatchPage) -> None:
        session = self.session
        page.add_lane_requested.connect(
            lambda: self._dispatch(lambda: session.dispatcher.add_lane("claude"), "已新增一條 Agent")
        )
        page.stop_all_requested.connect(self._stop_all_lanes)
        page.lane_action.connect(self._lane_action)
        page.lane_config.connect(
            lambda lane_id, agent, limit: self._dispatch(lambda: session.dispatcher.configure_lane(lane_id, agent, limit), "")
        )
        page.report_requested.connect(self._simulated_report)
        page.unskip_requested.connect(
            lambda card: self._dispatch(lambda: session.dispatcher.unskip(card), f"{card} 已解除需人工，可再派")
        )
        page.schedule_add.connect(self._add_schedule)
        page.schedule_delete.connect(
            lambda lane_id, sid: self._dispatch(lambda: session.dispatcher.delete_schedule(lane_id, sid), f"已刪除排程 {sid}")
        )
        page.schedule_toggle.connect(
            lambda lane_id, sid, on: self._dispatch(
                lambda: session.dispatcher.set_schedule_enabled(lane_id, sid, on), f"排程 {sid} 已{'啟用' if on else '停用'}"
            )
        )
        page.schedules_paused.connect(
            lambda paused: self._dispatch(
                lambda: session.dispatcher.set_schedules_paused(paused), "已暫停所有排程" if paused else "已恢復排程"
            )
        )

    def _dispatch(self, action, message: str) -> None:
        try:
            action()
        except (DispatchError, VersionConflict, ValueError) as exc:
            self._note(str(exc))
        else:
            if message:
                self._note(message)
        self.refresh()

    def _lane_action(self, lane_id: str, action: str) -> None:
        dispatcher = self.session.dispatcher
        handlers = {
            "start": (lambda: dispatcher.start_lane(lane_id), f"Agent {lane_id} 已啟動（模擬）"),
            "stop": (lambda: dispatcher.stop_lane(lane_id, "after-current"), f"Agent {lane_id} 會在目前這張做完後停止"),
            "kill": (lambda: dispatcher.stop_lane(lane_id, "now"), f"Agent {lane_id} 已立即終止，該卡列入需人工"),
            "remove": (lambda: dispatcher.remove_lane(lane_id), f"已從派工移除 Agent {lane_id}"),
        }
        action_fn, message = handlers[action]
        self._dispatch(action_fn, message)

    def _stop_all_lanes(self) -> None:
        dispatcher = self.session.dispatcher

        def stop_all() -> None:
            for lane in dispatcher.lanes:
                dispatcher.stop_lane(lane.lane_id, "after-current")

        self._dispatch(stop_all, "所有 Agent 會在目前這張做完後停止")

    def _simulated_report(self, card_id: str, outcome: str) -> None:
        label = "完成" if outcome == "done" else "卡住"
        self._dispatch(
            lambda: self.session.dispatcher.report(card_id, outcome, f"模擬回報：{label}", channel="ui"),
            f"{card_id} 已回報{label}",
        )

    def _add_schedule(self, lane_id: str, fields: dict) -> None:
        fields = dict(fields)
        kind = fields.pop("kind")
        self._dispatch(
            lambda: self.session.dispatcher.add_schedule(lane_id, kind, **fields),
            f"Agent {lane_id} 已新增排程（只在程式開著時生效，錯過不補跑）",
        )

    def _apply_inspector(self, page: str) -> None:
        if self._inspector_user_hidden:
            self.inspector.setVisible(False)
            return
        self.inspector.setVisible(page == "git")

    def _about(self) -> None:
        self._note("SGenAxis Workbench v0.5.0 — DCC & Git Pipeline (PySide6 / C++ 架構原型)")

    def _rebuild_project_menu(self) -> None:
        for action in list(self.project_menu.actions()):
            if action == self._project_menu_break:
                break
            self.project_menu.removeAction(action)
        for project in self.session.combo_projects():
            mark = "✓ " if project.name == self.session.current_name else ""
            suffix = " (作用中)" if project.name == self.session.current_name else ""
            action = QAction(f"{mark}{project.name}{suffix}", self)
            action.triggered.connect(lambda _checked=False, name=project.name: self._switch_project(name))
            self.project_menu.insertAction(self._project_menu_break, action)

    def _switch_project(self, name: str) -> None:
        if name == self.session.current_name:
            self.refresh()
            return
        self.project_combo.blockSignals(True)
        self.project_combo.setCurrentText(name)
        self.project_combo.blockSignals(False)
        self._combo_changed(name)

    def _rescan(self) -> None:
        self.refresh()
        self._note("已重新掃描工作區")

    def _select_all_changes(self) -> None:
        self._show_page("tasks")
        self.board.table.selectAll()
        self._note("已全選所有工項變更項目 (Select All)")

    def _clear_selection(self) -> None:
        focus = QApplication.focusWidget()
        if isinstance(focus, QLineEdit):
            return
        self.board.table.clearSelection()
        self.projects.table.clearSelection()
        self._note("已取消選取全部變更項目")

    def _add_task(self) -> None:
        self._show_page("tasks")
        self._note("開啟工項建立精靈 (UI-03 / UI-05 介面連動)")

    def _dispatch_agent(self) -> None:
        self._show_page("agent")

    def _batch_bdd(self) -> None:
        selected = {
            item.data(Qt.UserRole)
            for item in self.board.table.selectedItems()
            if item.data(Qt.UserRole)
        }
        marked = 0
        for row in self.session.items:
            if row.item_id not in selected:
                continue
            fields = {}
            if row.bdd in ("", "—"):
                fields["bdd"] = f"BDD-{row.code}"
            if row.tdd in ("", "—"):
                fields["tdd"] = f"TDD-{row.code}"
            self.session.edit_item(row.item_id, fields)
            marked += 1
        self.refresh()
        self._note("已批次標註 BDD/TDD 標籤" if marked else "已觸發功能：批次標註 BDD/TDD 標籤")

    def _refresh_design_stats(self) -> None:
        menus = sum(1 for action in self.menuBar().actions() if action.menu() is not None)
        buttons = len(self.findChildren(QPushButton))
        self.ui_page.set_stats(1, menus, buttons, len(ARCH_MODULES), len(ARCH_LINKS))

    def _open_ports(self) -> None:
        self._show_page("arch")
        self.arch_page.set_heading("Ports & Contracts 契約")
        self.breadcrumb.setText("SGenAxis  /  Ports & Contracts 契約")
        self._note("Ports & Contracts 契約檢視")

    def _show_qt_spec(self) -> None:
        self.stack.setCurrentWidget(self.qt_page)
        self.sidebar.set_current("")
        self.breadcrumb.setText("SGenAxis  /  Qt / PySide 架構規格對照")
        self._apply_inspector("qt")

    def _toggle_inspector(self) -> None:
        visible = self.inspector.isHidden()
        self._inspector_user_hidden = not visible
        self.inspector.setVisible(visible)
        if visible:
            self.body_splitter.setSizes([196, 900, 300])
        self._note("已顯示 Inspector 側欄" if visible else "已隱藏 Inspector 側欄")

    def _toggle_branch_tree(self) -> None:
        visible = self.branch_panel.isHidden()
        self.branch_panel.setVisible(visible)
        self.center_splitter.setSizes([440, 160, 220] if visible else [600, 0, 220])
        self._note("已顯示分支樹態面板" if visible else "已隱藏分支樹態面板")

    def _reset_layout(self) -> None:
        self._inspector_user_hidden = False
        self.inspector.setVisible(True)
        self.branch_panel.setVisible(False)
        self.body_splitter.setSizes([196, 900, 300])
        self.center_splitter.setSizes([600, 0, 220])
        self.session.filter_name = "accepted"
        self._show_page("git")
        self._note("已重設為標準工作台佈局")

    def _note(self, text: str) -> None:
        self.status.showMessage(text, 4000)
