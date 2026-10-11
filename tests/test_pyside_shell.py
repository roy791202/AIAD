"""Offscreen checks for the six PySide workbench surfaces."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtWidgets import QApplication, QDialog, QFrame, QLabel, QPushButton

from datetime import datetime

from sgenaxis.adapters import board_seed
from sgenaxis.core.in_memory import DryRunLauncher, InMemoryProjectBoards, StaticFileProbe, StaticGitReader, StaticReleases
from sgenaxis.core.ports import FileInfo, GitChange, GitSnapshot
from sgenaxis.core.release import Artifact, Release
from sgenaxis.core.session import WorkbenchSession
from sgenaxis.ui import theme
from sgenaxis.ui.git_dialogs import CommitDialog
from sgenaxis.ui.icons import icon
from sgenaxis.ui.main_window import MainWindow


def _app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _delete_windows():
    yield
    app = QApplication.instance()
    if app is None:
        return
    for widget in app.topLevelWidgets():
        widget.deleteLater()
    app.sendPostedEvents(None, QEvent.DeferredDelete)


def test_icon_pack_is_used_on_the_chrome():
    _app()
    window = MainWindow(WorkbenchSession())
    assert not window.windowIcon().isNull()
    save = next(action for action in window.menuBar().actions() if action.text() == "檔案").menu().actions()
    labeled = {action.text(): action for action in save}
    assert not labeled["儲存"].icon().isNull()
    assert not labeled["開啟專案..."].icon().isNull()
    assert not window.findChild(type(window.branch_button), "btnSettingsIcon").icon().isNull()
    assert not window.sidebar.buttons["agent"].icon().isNull()
    window.close()


def test_opening_view_matches_the_html_workbench():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    assert window.stack.currentWidget() is window.board_page
    assert window.board.table.rowCount() == 6
    assert window.sidebar.clear_button.text() == "全部 (19)"
    assert window.sidebar.release_button.text() == "佈版"
    assert window.sidebar.arch_button.text() == "模組架構圖"
    assert window.sidebar.ui_button.text() == "UI 設計工具"
    assert window.findChild(type(window.path_label), "repoPathText").text() == r"D:\AutoCode"
    assert window.status.ready.text() == "DRAFT 0.1 / 即時同步"
    assert window.status.progress_bar.value() == 52
    assert window.status.progress_bar.isVisible()
    assert window.status.progress_pct.text() == "52%"
    assert window.status.agent.text() == "Agent 執行中  0"
    assert window.inspector.isHidden()
    assert window.inspector.project_id.text() == "prj-sgenaxis"
    window.close()


def test_task_page_still_opens_on_the_bug_queue():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.tasks_button.click()
    assert window.stack.currentWidget() is window.board_page
    assert window.board.table.rowCount() == 6
    light = window.board.table.item(0, 0)
    assert light.data(Qt.UserRole) == "TASK-01"
    assert light.data(Qt.UserRole + 1) == "red"
    combo = window.board.table.cellWidget(0, 1)
    assert combo.currentData() == "red"
    combo.setCurrentIndex(combo.findData("yellow"))
    assert window.board.table.rowCount() == 5
    moved = next(item for item in window.session.items if item.item_id == "TASK-01")
    assert moved.status == "yellow"
    window.close()


def test_sidebar_filter_switches_to_finished_pyside_tasks():
    _app()
    window = MainWindow(WorkbenchSession())
    window.filter_buttons["green"].click()
    assert window.board.table.rowCount() == 7
    titles = [window.board.table.item(row, 2).text() for row in range(7)]
    assert any("選單與標題列" in title for title in titles)
    window.close()


def test_architecture_page_matches_the_html_dag():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.arch_button.click()
    page = window.arch_page
    assert window.stack.currentWidget() is page
    assert set(page.nodes) == {"UI", "DISP", "STATS", "REL", "SCHED", "LAUNCH", "REPORT", "BOARD", "STORE"}
    assert len(page.edges) == 11
    assert page.code.text() == "DISP"
    assert page.port.text() == "IDispatchCommands"
    assert page.task_table.rowCount() == 2
    page.select_module("LAUNCH")
    assert page.name.text() == "Agent 啟動"
    assert page.task_table.item(0, 0).text() == "INV-BD-15..19"
    page.show_tab("props")
    assert page.prop_port.text() == "IAgentLauncher"
    page.zoom(0.1)
    assert page.scale == 1.1
    page.findChild(QPushButton, "btnOpenModuleSpec").click()
    assert "已開啟 LAUNCH 模組規格" in window.status.currentMessage()
    window.filter_buttons["red"].click()
    assert window.stack.currentWidget() is window.board_page
    assert window.board.table.rowCount() == 6
    window.close()


def test_architecture_nodes_can_move_and_expand():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.arch_button.click()
    page = window.arch_page
    node = page.nodes["DISP"]
    edge = next(item for item in page.edges if item.data(0) == "DISP->LAUNCH")
    before = edge.path().pointAtPercent(0)
    node.setPos(node.pos().x() + 60, node.pos().y() + 80)
    assert edge.path().pointAtPercent(0) != before

    node.set_expanded(True)
    assert node.boundingRect().height() > 86
    assert page.code.text() == "DISP"
    assert "已展開 DISP 模組資訊" in window.status.currentMessage()

    page.findChild(QPushButton, "btnArchResetLayout").click()
    assert not node.expanded
    assert (node.pos().x(), node.pos().y()) == (250, 60)
    edge = next(item for item in page.edges if item.data(0) == "DISP->LAUNCH")
    assert edge.path().pointAtPercent(0) == before
    window.close()


def test_architecture_links_can_be_removed_and_restored():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.arch_button.click()
    page = window.arch_page
    remove = page.findChild(QPushButton, "btnArchRemoveLink")
    assert not remove.isEnabled()
    remove_edge = next(item for item in page.edges if item.data(0) == "UI->REL")
    remove_edge.setSelected(True)
    assert remove.isEnabled()
    remove.click()
    assert len(page.edges) == 10
    assert remove_edge.scene() is None
    assert "已取消接線 UI → REL" in window.status.currentMessage()
    assert not remove.isEnabled()

    page.remove_edge(page.edges[0])
    assert len(page.edges) == 9

    page.findChild(QPushButton, "btnArchResetLayout").click()
    assert len(page.edges) == 11
    window.close()


def test_architecture_port_drag_creates_a_link():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.arch_button.click()
    page = window.arch_page
    rel = page.nodes["REL"]
    assert set(rel.ports()) == {"input", "output"}
    assert rel.port_at(QPointF(0, 43)) == "input"
    assert rel.port_at(QPointF(172, 43)) == "output"
    assert rel.port_at(QPointF(86, 0)) is None

    edge = next(item for item in page.edges if item.data(0) == "UI->REL")
    assert edge.path().pointAtPercent(0) == page.nodes["UI"].port_scene_pos("output")
    assert edge.path().pointAtPercent(1) == rel.port_scene_pos("input")

    page.start_link("REL", "output")
    assert page.draft_wire.isVisible()
    store_center = page.nodes["STORE"].sceneBoundingRect().center()
    page.drag_link(store_center)
    page.finish_link("REL", store_center)
    assert not page.draft_wire.isVisible()
    assert any(edge.data(0) == "REL->STORE" for edge in page.edges)
    assert "已新增接線 REL → STORE" in window.status.currentMessage()

    page.start_link("STORE", "input")
    page.finish_link("STORE", page.nodes["SCHED"].sceneBoundingRect().center())
    assert any(edge.data(0) == "SCHED->STORE" for edge in page.edges)

    page.start_link("REL", "output")
    page.finish_link("REL", store_center)
    assert sum(edge.data(0) == "REL->STORE" for edge in page.edges) == 1
    page.start_link("REL", "output")
    page.finish_link("REL", QPointF(-500, -500))
    assert "接線未建立" in window.status.currentMessage()
    assert len(page.edges) == 13
    window.close()


def test_architecture_inspector_can_move():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.arch_button.click()
    page = window.arch_page
    dock = page.inspector_dock
    assert dock.features() & dock.DockWidgetFeature.DockWidgetMovable
    assert page.inspector_area() == "right"
    page.move_inspector("left")
    assert page.inspector_area() == "left"
    assert "Inspector 已移到左側" in window.status.currentMessage()
    page.move_inspector("floating")
    assert page.inspector_area() == "floating"
    page.move_inspector("right")
    assert page.inspector_area() == "right"
    page.select_module("LAUNCH")
    assert page.code.text() == "LAUNCH"
    window.close()


REL_NEW = Release(
    "v1.1.0", "1.1.0", "portable", "2026-10-10T14:49:00+08:00", "2026-10-10T15:00:00+08:00", "agent",
    artifacts=(
        Artifact("portable ZIP", r"D:\out\app-1.1.0.zip", True, "2026-10-10T15:00:00+08:00"),
        Artifact("安裝程式", r"D:\out\setup-1.1.0.exe", True, "2026-10-10T15:00:00+08:00"),
    ),
    report_md="打 1.1.0 portable",
)
REL_OLD = Release(
    "v1.0.0", "1.0.0", "installer", "2026-08-31T10:00:00+08:00", "2026-08-31T10:00:00+08:00", "user",
    artifacts=(Artifact("安裝程式", r"D:\out\setup-1.0.0.exe", True, "2026-08-31T10:00:00+08:00"),),
)
WHEN = datetime(2026, 10, 11, 12, 0)


def _info(path: str, size: int, is_dir: bool = False, files: int = 0) -> FileInfo:
    return FileInfo(path, path.rsplit("\\", 1)[-1], is_dir, size, WHEN, files)


def test_release_page_shows_board_versions_with_live_artifact_checks():
    app = _app()
    probe = StaticFileProbe([_info(r"D:\out\app-1.1.0.zip", 3 * 1024 * 1024), _info(r"D:\out\setup-1.0.0.exe", 2048)])
    window = MainWindow(WorkbenchSession(releases=StaticReleases([REL_NEW, REL_OLD]), file_probe=probe))
    window.sidebar.release_button.click()
    page = window.release_page
    assert window.stack.currentWidget() is page
    assert [page.version.itemData(index) for index in range(page.version.count())] == ["v1.1.0", "v1.0.0"]
    assert page.hero.text() == "v1.1.0"
    assert [label.text() for label in page.artifact_states] == ["存在  3.0 MB", "找不到"]
    assert "即時檢查" in page.artifact_head.text()
    assert page.report_text.text() == "打 1.1.0 portable"
    assert "未開啟專案" in page.dist_message.text()
    assert len(page.fields) == 7
    assert set(page.channels) == {"ssh", "container", "dcc"}

    page.env_tabs["prod"].click()
    assert page.fields["profile"].currentText() == "windows-prod"

    page.version.setCurrentIndex(1)
    assert page.hero.text() == "v1.0.0"
    assert [label.text() for label in page.artifact_states] == ["存在  2.0 KB"]
    page.copy_buttons[0].click()
    assert app.clipboard().text() == r"D:\out\setup-1.0.0.exe"
    assert "已複製路徑" in window.status.currentMessage()

    window.refresh()
    assert page.hero.text() == "v1.0.0"
    page.report_toggle.click()
    assert page.report_body.isHidden()
    page.findChild(QPushButton, "btnReleaseCheck").click()
    assert "部署尚未接上" in window.status.currentMessage()
    window.close()


def test_release_page_without_records_or_probe_says_so():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    window._show_page("release")
    page = window.release_page
    assert page.hero.text() == "—"
    assert not page.version.isEnabled()
    assert page.release_empty.isVisible()
    assert page.copy_buttons == []
    window.close()


def test_release_page_lists_the_project_dist_folder():
    _app()
    path = r"D:\AIAD\_sandbox\agent-test"
    probe = StaticFileProbe([_info(path + r"\dist\app.zip", 1024), _info(path + r"\dist\portable", 4096, True, 3)])
    session = WorkbenchSession(boards=InMemoryProjectBoards(), file_probe=probe)
    session.create_project("agent-test", r"D:\AIAD\_sandbox")
    window = MainWindow(session)
    window._show_page("release")
    page = window.release_page
    assert [(kind, entry) for kind, entry, _meta in page.dist_rows] == [
        ("檔案", path + r"\dist\app.zip"),
        ("資料夾", path + r"\dist\portable"),
    ]
    assert page.dist_rows[1][2].startswith("4.0 KB／3 檔")
    assert path + r"\dist" in page.dist_head.text()
    window.close()


def test_ui_design_page_matches_the_html_designer():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.ui_button.click()
    page = window.ui_page
    assert window.stack.currentWidget() is page
    assert page.state_label.text() == "目前設計：Form · Form · 800×600 · unset"
    assert page.palette.topLevelItemCount() == 4
    assert page.stats["wires"].text() == "11"
    assert page.stats["files"].text() == "9"
    page.select_node("slider")
    assert page.name.text() == "Slider"
    assert page.w.value() == 420
    page.set_zoom(130)
    assert page.zoom_label.text() == "130%"
    page.set_mode("viewer")
    assert page.canvas.isHidden()
    page.set_mode("designer")
    assert not page.canvas.isHidden()
    page.findChild(QPushButton, "btnAskAgentNode").click()
    assert "已詢問 Agent 關於 Slider" in window.status.currentMessage()
    window.close()


def test_git_settings_paste_trims_into_remote_and_clone():
    _app()
    window = MainWindow(WorkbenchSession())
    window._open_settings("git")
    dialog = window._settings
    assert window.stack.currentWidget() is dialog
    assert not dialog.isWindow()
    assert dialog.nav.currentRow() == 1
    dialog.cloud_url.setText("  https://github.com/sgenaxis/cloud.git\n")
    assert dialog.remote_url.text() == "https://github.com/sgenaxis/cloud.git"
    assert dialog.clone_url.text() == "https://github.com/sgenaxis/cloud.git"
    assert window.session.cloud_url == "https://github.com/sgenaxis/cloud.git"
    window.close()


def test_missing_project_path_keeps_the_toolbar():
    _app()
    window = MainWindow(WorkbenchSession())
    window._open_from_settings("Legacy Demo")
    assert window.session.current_name == "SGenAxis"
    assert window.path_label.text() == r"D:\AutoCode"
    assert "路徑不存在" in window.status.currentMessage()
    window.close()


def test_light_beige_theme_recolors_the_chrome():
    _app()
    window = MainWindow(WorkbenchSession())
    window.session.set_appearance("light", "beige")
    window.apply_theme()
    sheet = QApplication.instance().styleSheet()
    assert "#f4f6f8" in sheet
    assert "#b08968" in sheet
    window.close()


def test_style_and_tone_switch_recolors_every_page():
    _app()
    window = MainWindow(WorkbenchSession())
    window.resize(1440, 900)
    window.show()
    settings = window._settings
    settings.findChild(QPushButton, "choice-light").click()
    assert "UI 風格：亮" in window.status.currentMessage()
    assert theme.current()["window"] == "#f4f6f8"
    sheet = QApplication.instance().styleSheet()
    assert "#101214" not in sheet and "#151719" not in sheet

    window._show_page("arch")
    assert window.arch_page.view.backgroundBrush().color().name() == "#eef1f4"
    for page in ("agent", "arch", "release", "git"):
        window._show_page(page)
        QApplication.processEvents()
        current = window.stack.currentWidget()
        pixel = current.grab().toImage().pixelColor(8, current.height() - 40)
        assert pixel.lightness() > 180, page

    light_icon = icon("save").pixmap(16, 16).toImage()
    settings.findChild(QPushButton, "choice-beige").click()
    assert "色調：米" in window.status.currentMessage()
    assert theme.current()["accent"] == "#b08968"
    assert "QProgressBar#statusProgressBar::chunk { background: #b08968; }" in QApplication.instance().styleSheet()
    window._show_page("arch")
    assert window.arch_page.draft_wire.pen().color().name() == "#b08968"

    settings.findChild(QPushButton, "choice-dark").click()
    dark_icon = icon("save").pixmap(16, 16).toImage()
    assert light_icon != dark_icon
    assert window.arch_page.view.backgroundBrush().color().name() == "#101214"
    window.close()


def test_commit_dialog_requires_a_message_and_does_not_touch_git(tmp_path, monkeypatch):
    _app()
    monkeypatch.chdir(tmp_path)
    dialog = CommitDialog()
    dialog._accept_message()
    assert dialog.result() != QDialog.Accepted
    assert dialog.error.text() == "請輸入提交說明"
    dialog.message.setText("記錄一下")
    dialog._accept_message()
    assert dialog.result() == QDialog.Accepted
    assert list(tmp_path.iterdir()) == []


def _menu_labels(window: MainWindow) -> list[str]:
    labels: list[str] = []
    for entry in window.menuBar().actions():
        menu = entry.menu()
        if menu is None:
            continue
        labels.extend(action.text() for action in menu.actions())
    return labels


def _trigger(window: MainWindow, label: str):
    for entry in window.menuBar().actions():
        menu = entry.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.text() == label:
                action.trigger()
                return
    raise AssertionError(label)


def test_html_menu_commands_stay_in_the_window():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    labels = _menu_labels(window)
    for expected in (
        "全選變更項目",
        "清除全選",
        "✓ SGenAxis (作用中)",
        "重新掃描儲存庫變更",
        "Ports & Contracts 契約檢視",
        "新增工項...",
        "指派 Agent 任務...",
        "批次標註 BDD/TDD 標籤",
        "重設為標準工作台佈局",
        "顯示/隱藏 Inspector 側欄",
        "顯示/隱藏 分支樹態面板",
        "Qt / PySide 架構規格對照",
        "關於 SGenAxis (v0.5.0)...",
        "歷史",
        "GIT 設定",
        "設定",
    ):
        assert expected in labels
    _trigger(window, "全選變更項目")
    assert window.stack.currentWidget() is window.board_page
    assert window.board.table.selectedItems()
    _trigger(window, "清除全選")
    assert not window.board.table.selectedItems()
    _trigger(window, "指派 Agent 任務...")
    assert window.stack.currentWidget() is window.agent_page
    assert not window.agent_page.isWindow()
    _trigger(window, "Ports & Contracts 契約檢視")
    assert window.stack.currentWidget().objectName() == "archPage"
    assert window.breadcrumb.text() == "SGenAxis  /  Ports & Contracts 契約"
    _trigger(window, "Qt / PySide 架構規格對照")
    assert window.stack.currentWidget() is window.qt_page
    assert not window.qt_page.isWindow()
    _trigger(window, "GIT 設定")
    assert window.stack.currentWidget() is window._settings
    assert not window._settings.isWindow()
    _trigger(window, "顯示/隱藏 Inspector 側欄")
    assert not window.inspector.isHidden()
    _trigger(window, "顯示/隱藏 分支樹態面板")
    assert not window.branch_panel.isHidden()
    _trigger(window, "重設為標準工作台佈局")
    assert not window.inspector.isHidden()
    assert window.branch_panel.isHidden()
    assert window.git_bar.isVisible()
    assert "已重設為標準工作台佈局" in window.status.currentMessage()
    window.close()


def test_left_overview_is_the_html_agent_dispatch():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    assert "overview" not in window.sidebar.buttons
    button = window.sidebar.agent_button
    assert button.text() == "Agent 派工  [0/1]"
    assert button.toolTip() == "Idle"
    button.click()
    page = window.agent_page
    assert window.stack.currentWidget() is page
    assert window.breadcrumb.text() == "Agent 派工"
    assert window.inspector.isHidden()
    assert page.findChild(QPushButton, "btnAddAgent").text() == "+ 新增 Agent"
    assert "TASK-01" in page.next_detail.text()
    assert set(page.cards) == {"L1"}
    page.findChild(QPushButton, "lane-start-L1").click()
    assert window.session.agent_running == 1
    assert window.sidebar.agent_button.text() == "Agent 派工  [1/1]"
    status = page.findChild(QLabel, "laneStatus-L1").text()
    assert "執行中" in status and "TASK-01" in status and "模擬" in status
    assert window.session.item("TASK-01").updated_by == "agent"
    assert "TASK-02" in page.next_detail.text()
    assert window.session.launcher.launched[0].card_id == "TASK-01"
    window.close()


def test_agent_lanes_report_stop_and_needs_human():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    window._show_page("agent")
    page = window.agent_page
    page.findChild(QPushButton, "btnAddAgent").click()
    assert set(page.cards) == {"L1", "L2"}
    page.findChild(QPushButton, "lane-start-L1").click()
    page.findChild(QPushButton, "lane-start-L2").click()
    assert {lane.current.card_id for lane in window.session.dispatcher.lanes} == {"TASK-01", "TASK-02"}
    assert window.sidebar.agent_button.text() == "Agent 派工  [2/2]"

    page.findChild(QPushButton, "lane-report-done-L1").click()
    assert window.session.item("TASK-01").status == "green"
    assert "TASK-01 已回報完成" in window.status.currentMessage()
    assert window.session.dispatcher.lane("L1").current.card_id == "TASK-03"

    page.findChild(QPushButton, "lane-kill-L2").click()
    assert page.needs_human.count() == 1
    assert "TASK-02" in page.needs_human.item(0).text()
    assert window.session.dispatcher.lane("L2").state == "idle"
    page.findChild(QPushButton, "btnUnskip").click()
    assert page.needs_human.count() == 0

    page.findChild(QPushButton, "btnAddAgent").click()
    assert not page.findChild(QPushButton, "btnAddAgent").isEnabled()
    assert not page.findChild(QPushButton, "lane-remove-L1").isEnabled()
    page.findChild(QPushButton, "lane-remove-L3").click()
    assert set(page.cards) == {"L1", "L2"}
    assert page.findChild(QPushButton, "btnAddAgent").isEnabled()
    assert page.history.count() == 2
    window.close()


def test_recent_history_doubles_as_the_log_view():
    _app()
    window = MainWindow(WorkbenchSession())
    window._show_page("agent")
    page = window.agent_page
    assert "示範資料（未存檔）" in page.board_hint.text()
    page.findChild(QPushButton, "lane-start-L1").click()
    page.findChild(QPushButton, "lane-report-done-L1").click()
    assert "介面模擬" in page.history.item(0).text()
    page.history.setCurrentRow(0)
    detail = page.detail.toPlainText()
    assert page.detail.isReadOnly()
    assert "TASK-01" in detail and "經由介面模擬" in detail
    assert "## 2. 你的卡" in detail and "看板 JSON（必須更新）" in detail
    assert "[模擬] 未啟動 claude" in detail
    window.close()


def test_closing_the_window_shuts_the_dispatcher_down():
    _app()
    session = WorkbenchSession()
    window = MainWindow(session)
    window.show()
    session.dispatcher.start_lane("L1")
    handle = session.launcher.handles[session.dispatcher.lane("L1").current.run_id]
    window.close()
    assert handle.terminated
    assert session.dispatcher.skipped == {"TASK-01": "server-shutdown"}
    assert not window.dispatch_timer.isActive()


@pytest.mark.skipif(not board_seed.available(), reason="Beta board snapshot is local data, not in the repo")
def test_release_page_shows_the_board_release_records():
    _app()
    window = MainWindow(WorkbenchSession(releases=StaticReleases(board_seed.load_releases())))
    window.show()
    window._show_page("release")
    page = window.release_page
    assert page.version.count() == 1
    assert page.hero.text() == "v0.3.4"
    assert "v0.3.4" in page.record_summary.text()
    assert all(label.text().startswith("記錄：") for label in page.artifact_states)
    assert page.record_text.isReadOnly()
    assert "── CHANGELOG ──" in page.record_text.toPlainText()
    assert not page.record_empty.isVisible()
    window.close()

    empty = MainWindow(WorkbenchSession())
    empty.show()
    empty._show_page("release")
    assert empty.release_page.record_empty.isVisible()
    assert not empty.release_page.record_text.isVisible()
    empty.close()


def test_agent_schedule_is_added_from_the_lane_form():
    _app()
    window = MainWindow(WorkbenchSession())
    window._show_page("agent")
    card = window.agent_page.cards["L1"]
    card.kind.setCurrentIndex(card.kind.findData("daily"))
    card.weekdays[0].setChecked(True)
    card.findChild(QPushButton, "scheduleAdd-L1").click()
    entry = window.session.dispatcher.lane("L1").schedules[0]
    assert (entry.kind, entry.time, entry.weekdays) == ("daily", "09:00", (0,))
    assert card.schedule_list.count() == 1
    assert "每天 09:00（週一）" in card.schedule_list.item(0).text()
    window.agent_page.pause.setChecked(True)
    assert window.session.dispatcher.schedules_paused
    assert "已暫停所有排程" in window.status.currentMessage()
    window.close()


def test_stats_page_shows_periods_and_overall_rate():
    _app()
    window = MainWindow(WorkbenchSession())
    window.sidebar.stats_button.click()
    page = window.stats_page
    assert window.stack.currentWidget() is page
    assert page.overall.value() == 40
    assert page.table.rowCount() > 0
    page.findChild(QPushButton, "statsGran-month").click()
    assert page.table.item(0, 0).text() == "2026-10"
    window.close()


def test_task_board_shows_kind_and_who_changed_it():
    _app()
    window = MainWindow(WorkbenchSession())
    assert "bug" in window.board.table.item(0, 2).text()
    window.board.table.cellWidget(0, 1).setCurrentIndex(window.board.table.cellWidget(0, 1).findData("yellow"))
    window._inspect_item("TASK-01")
    assert "v2" in window.inspector.task_meta.text()
    assert "使用者" in window.inspector.task_meta.text()
    window.close()


def test_agent_page_inspector_stays_hidden():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    window.sidebar.agent_button.click()
    assert window.inspector.isHidden()
    window.sidebar.tasks_button.click()
    assert window.inspector.isHidden()
    window.close()


def test_scroll_areas_use_the_window_color():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    window._show_page("agent")
    sheet = QApplication.instance().styleSheet()
    assert "QWidget#qt_scrollarea_viewport" in sheet
    assert "QScrollArea > QWidget > QWidget" in sheet
    pixel = window.agent_page.grab().toImage().pixelColor(600, 400)
    assert pixel.lightness() < 60
    window.close()


def test_exec_log_replaces_activity_panel_on_every_page():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    assert window.findChild(QFrame, "activityPanel") is None
    assert len(window.findChildren(QFrame, "execLog")) == 1
    log = window.exec_log
    for page in ("tasks", "agent", "arch", "ui", "release", "settings"):
        window._show_page(page)
        assert log.isVisible()
    assert log.lines.count() == 7
    assert log.lines.item(4).text().startswith("5  [10:18:58]  [ERROR]")
    log.filter.setCurrentText("WARN")
    visible = [log.lines.item(row) for row in range(log.lines.count()) if not log.lines.item(row).isHidden()]
    assert len(visible) == 3
    log.show_tab("summary")
    assert log.summary.isVisible()
    assert not log.lines.isVisible()
    log.clear_log()
    assert log.lines.count() == 0
    assert "已清除執行紀錄" in window.status.currentMessage()
    window.close()


def test_accepted_page_shows_the_git_command_bar():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    assert not window.git_bar.isVisible()
    window.filter_buttons["accepted"].click()
    assert window.git_bar.isVisible()
    assert window.board.table.rowCount() == 1
    window.close()


def test_accepted_page_matches_the_html_git_workspace():
    _app()
    window = MainWindow(WorkbenchSession())
    window.show()
    window.sidebar.filter_buttons["accepted"].click()
    page = window.git_page
    assert window.stack.currentWidget() is page
    assert page.table.isVisible()
    assert page.table.rowCount() == 1
    assert page.count.text() == "1"
    headers = [page.table.horizontalHeaderItem(column).text() for column in range(page.table.columnCount())]
    assert headers[:2] == [window.board.table.horizontalHeaderItem(column).text() for column in range(2)]
    assert headers == ["燈號", "狀態", "工項", "修改的檔案", "備註"]
    assert page.table.item(0, 2).text().startswith("feat(spec): 修正 BDD/TDD 測試鏈")
    assert "docs/board/tasks.json" in page.table.item(0, 3).text()
    assert window.inspector.task_title.text() == "feat(spec): 修正 BDD/TDD 測試鏈"
    assert "TASK-07" in window.inspector.task_sub.text()
    for name in ("btnCommit", "btnOpenPull", "btnOpenPush", "btnClone", "btnOpenCherry", "btnOpenBlame", "btnOpenConflict"):
        assert page.findChild(QPushButton, name) is not None
    assert len(page.command_buttons) == 18

    assert not page.local_panel.isVisible()
    page.local_toggle.click()
    assert page.local_panel.isVisible()
    assert page.file_rows == []
    assert "未開啟專案" in page.git_message.text()
    assert not page.branch.isEnabled()

    page.findChild(QPushButton, "btnOpenFetch").click()
    assert "Fetch 尚未寫入 Git" in window.status.currentMessage()

    page.table.cellWidget(0, 1).setCurrentIndex(3)
    assert page.table.rowCount() == 0
    assert page.empty.isVisible()
    assert "已改回工項燈號" in window.status.currentMessage()
    window.close()


def test_git_page_reads_the_created_project_repo_only():
    _app()
    path = r"D:\AIAD\_sandbox\agent-test"
    snap = GitSnapshot(
        "dev",
        ("main", "dev"),
        (GitChange("a.py", "M", True), GitChange("b.py", "M", False), GitChange("new.txt", "??", False)),
        ahead=2,
    )
    reader = StaticGitReader({path: snap})
    session = WorkbenchSession(boards=InMemoryProjectBoards(), git_reader=reader)
    window = MainWindow(session)
    window.show()
    window.sidebar.filter_buttons["accepted"].click()
    assert reader.asked == []
    session.create_project("agent-test", r"D:\AIAD\_sandbox")
    window.refresh()
    page = window.git_page
    assert reader.asked == [path]
    assert [page.branch.itemData(index) for index in range(page.branch.count())] == ["main", "dev"]
    assert page.branch.currentData() == "dev"
    assert "3 個檔案變更" in page.local_toggle.text()
    assert [label.text() for label in page.file_rows] == ["未暫存　M 　b.py", "未暫存　??　new.txt", "已暫存　M 　a.py"]
    assert page.tracking.text() == "2 待推播"
    window._show_page("tasks")
    window.refresh()
    assert reader.asked == [path]
    window.close()


def test_settings_switches_the_launch_mode_only_for_a_sandbox_project():
    _app()
    real = DryRunLauncher()
    session = WorkbenchSession(boards=InMemoryProjectBoards(), real_launcher=real, real_launch_roots=(r"D:\AIAD\_sandbox",))
    window = MainWindow(session)
    window.show()
    window._show_page("settings")
    settings = window._settings
    settings.show_page("agent")
    settings.launch_buttons["real"].click()
    assert session.launch_mode == "simulated"
    assert settings.launch_buttons["simulated"].isChecked()
    assert "示範資料不能實際啟動" in window.status.currentMessage()

    session.create_project("agent-test", r"D:\AIAD\_sandbox")
    window.refresh()
    assert "可切到實際" in settings.launch_reason.text()
    settings.launch_buttons["real"].click()
    assert session.launch_mode == "real"
    assert session.dispatcher.launcher is real
    assert "Agent 啟動方式：實際" in window.status.currentMessage()
    assert window.data_label.text() == "專案資料 · Agent 實際"
    window._show_page("agent")
    assert "啟動方式：實際" in window.agent_page.board_hint.text()
    window.close()
