"""Workbench session: tasks, Agent dispatch, projects, filters, and local preferences.

This module must stay free of Qt, filesystem writes, and Git I/O. Tasks live
behind the TaskStore port and change only through the board rules; Agent
work goes through the Dispatcher. Opening or creating a project binds that
folder's board through the ProjectBoards port and records it in the
ProjectRegistry, when one is given. The composition root injects
real adapters; without them the session uses the in-memory, dry-run defaults.
"""

from __future__ import annotations

import ntpath
from dataclasses import dataclass, field
from datetime import datetime

from sgenaxis.core import board, timefmt
from sgenaxis.core.board import WorkItem
from sgenaxis.core.dispatcher import Dispatcher
from sgenaxis.core.in_memory import DryRunLauncher, InMemoryReportInbox, InMemoryTaskStore, ManualClock, StaticReleases
from sgenaxis.core.ports import (
    AgentLauncher,
    Clock,
    DispatchStateStore,
    FileInfo,
    FileProbe,
    GitReader,
    GitSnapshot,
    GitUnavailable,
    ProjectBoard,
    ProjectBoards,
    ProjectRegistry,
    ReleaseSource,
    ReportInbox,
    TaskStore,
)
from sgenaxis.core.release import ArtifactCheck, Release

FILTERS = ("overview", "all", "gray", "yellow", "red", "green", "accepted")
SOURCES = ("all", "git", "agent", "manual")
UI_STYLES = ("dark", "light", "gray")
UI_TONES = ("blue", "gray", "beige", "iron")
LANGUAGES = ("zh-Hant", "zh-Hans", "en", "ja", "ko")
SEED_NOW = datetime(2026, 10, 11, 9, 0)
ACCEPT_BLOCKED = {"TASK-Y1": "可重現工具鏈與測試骨架不進入已驗收頁"}
SWITCH_BLOCKED = "Agent 派工中，請先全部停止再切換專案"
DEMO_BOARD = "示範資料（未存檔）"
NOT_OPEN = "未開啟專案：示範資料沒有專案資料夾"
LAUNCH_MODES = ("simulated", "real")
LAUNCH_MODE_LABELS = {"simulated": "模擬", "real": "實際"}
REAL_REPORT_GRACE_SECONDS = 120

SECTION_COPY = {
    "overview": ("總覽", "全部燈號"),
    "all": ("全部", "不含已驗收"),
    "gray": ("灰燈・待辦", "尚未開始"),
    "yellow": ("黃燈・進行中", "進行中的工項"),
    "red": ("紅燈・Bug", "需優先處理的缺陷與阻斷"),
    "green": ("綠燈・已完成", "已完成、尚未驗收"),
    "accepted": ("已驗收", "已驗收工項"),
}

STATUS_LABELS = {
    "gray": "待辦",
    "yellow": "進行中",
    "red": "Bug",
    "green": "已完成",
    "accepted": "已驗收",
    "overview": "總覽",
    "all": "全部",
}


@dataclass
class ProjectRecord:
    name: str
    path: str
    branch: str
    access: str
    opened: str
    in_combo: bool = True
    listed: bool = True


@dataclass
class WorkbenchSession:
    store: TaskStore | None = None
    clock: Clock | None = None
    launcher: AgentLauncher | None = None
    boards: ProjectBoards | None = None
    releases: ReleaseSource | None = None
    registry: ProjectRegistry | None = None
    report_command: str = ""
    real_launcher: AgentLauncher | None = None
    real_launch_roots: tuple[str, ...] = ()
    git_reader: GitReader | None = None
    file_probe: FileProbe | None = None
    projects: list[ProjectRecord] = field(default_factory=list)
    current_name: str = "SGenAxis"
    filter_name: str = "red"
    source: str = "all"
    query: str = ""
    recent: list[str] = field(default_factory=list)
    cloud_url: str = "https://git.local/sgenaxis.git"
    branch: str = "main"
    ui_style: str = "dark"
    tone: str = "blue"
    language: str = "zh-Hant"
    account: dict[str, str] = field(default_factory=dict)
    progress: int = 52
    dispatcher: Dispatcher = field(init=False)

    def __post_init__(self) -> None:
        if self.store is None:
            self.store = InMemoryTaskStore(seed_items())
        if self.clock is None:
            self.clock = ManualClock(SEED_NOW)
        if self.launcher is None:
            self.launcher = DryRunLauncher()
        if self.releases is None:
            self.releases = StaticReleases()
        if not self.projects:
            self.projects = seed_projects()
        self._remembered: set[str] = set()
        self._project_bound = False
        self.launch_mode = "simulated"
        self.registry_error = ""
        if self.registry is not None:
            self._load_registry()
        if not self.recent:
            self.recent = [row.name for row in self.projects if row.in_combo]
        if self.boards is not None:
            for project in self.projects:
                if not self.boards.exists(project.path):
                    project.access = "路徑不存在"
        self._bind(self.store, None, InMemoryReportInbox(), "")

    def _bind(self, store: TaskStore, state: DispatchStateStore | None, inbox: ReportInbox, logs_dir: str) -> None:
        self.store = store
        self.dispatcher = Dispatcher(
            store,
            self.clock,
            self.launcher,
            inbox=inbox,
            state=state,
            repo=self.current_path,
            logs_dir=logs_dir,
            report_command=self.report_command,
            report_grace_seconds=0,
            default_agent="claude",
        )
        self.launch_mode = "simulated"

    def _bind_board(self, project_board: ProjectBoard) -> None:
        self._bind(project_board.store, project_board.state, project_board.inbox, project_board.logs_dir)
        self.releases = project_board.releases
        self._project_bound = True

    def release_list(self) -> list[Release]:
        return self.releases.list()

    # ── read-only project data ─────────────────────────────

    def git_status(self) -> tuple[GitSnapshot | None, str]:
        """Git is read only for a folder SGenAxis created (it has a board folder) with its own repository."""
        if not self._project_bound:
            return None, NOT_OPEN
        if self.git_reader is None:
            return None, "Git 讀取未接上"
        if self.boards is None or not self.boards.managed(self.current_path):
            return None, f"這個資料夾不是 SGenAxis 建立的專案，不讀 Git：{self.current_path}"
        try:
            return self.git_reader.snapshot(self.current_path), ""
        except GitUnavailable as exc:
            return None, str(exc)

    def artifact_checks(self, item: Release) -> list[ArtifactCheck]:
        checks = []
        for artifact in item.artifacts:
            if self.file_probe is None:
                checks.append(ArtifactCheck(artifact.label, artifact.path, artifact.exists, False))
                continue
            info = self.file_probe.stat(artifact.path) if artifact.path else None
            if info is None:
                checks.append(ArtifactCheck(artifact.label, artifact.path, False, True))
            else:
                checks.append(
                    ArtifactCheck(artifact.label, artifact.path, True, True, info.size, info.files, info.is_dir, info.modified)
                )
        return checks

    def dist_listing(self) -> tuple[str, list[FileInfo], str]:
        if not self._project_bound:
            return "", [], NOT_OPEN
        if self.file_probe is None:
            return "", [], "檔案檢查未接上"
        folder = self.current_path.rstrip("\\/") + "\\dist"
        entries = self.file_probe.entries(folder)
        return folder, entries, "" if entries else f"成品資料夾是空的或不存在：{folder}"

    # ── launch mode ────────────────────────────────────────

    def real_launch_block_reason(self) -> str:
        if self.real_launcher is None:
            return "實際啟動未接上"
        if not self._project_bound:
            return "示範資料不能實際啟動，請先開啟或建立專案"
        if not any(_within(self.current_path, root) for root in self.real_launch_roots):
            roots = "、".join(self.real_launch_roots) or "（未設定）"
            return f"實際啟動只限沙盒資料夾：{roots}"
        return ""

    def set_launch_mode(self, mode: str) -> None:
        if mode not in LAUNCH_MODES:
            raise ValueError(f"未知的啟動方式：{mode}")
        if mode == self.launch_mode:
            return
        if mode == "real":
            reason = self.real_launch_block_reason()
            if reason:
                raise ValueError(reason)
            self.dispatcher.use_launcher(self.real_launcher, REAL_REPORT_GRACE_SECONDS)
        else:
            self.dispatcher.use_launcher(self.launcher, 0)
        self.launch_mode = mode

    def _load_registry(self) -> None:
        """Registered projects come first; seed entries with the same name are dropped.
        An unreadable registry is left untouched and not used for this run."""
        try:
            rows = self.registry.load()
        except ValueError as exc:
            self.registry_error = str(exc)
            self.registry = None
            return
        loaded = [
            ProjectRecord(row["name"], row["path"], row.get("branch") or "main", "可存取", row.get("opened") or "—")
            for row in rows
        ]
        names = {record.name for record in loaded}
        self.projects = loaded + [record for record in self.projects if record.name not in names]
        self._remembered = {record.path for record in loaded}

    def _remember_project(self, record: ProjectRecord) -> None:
        if self.registry is None:
            return
        self._remembered.add(record.path)
        self.registry.save(
            [
                {"name": project.name, "path": project.path, "branch": project.branch, "opened": project.opened}
                for project in self.projects
                if project.path in self._remembered
            ]
        )

    @property
    def items(self) -> list[WorkItem]:
        return self.store.list()

    @property
    def board_path(self) -> str | None:
        return self.store.location

    @property
    def project_open(self) -> bool:
        return self._project_bound

    def board_label(self) -> str:
        return self.board_path or DEMO_BOARD

    def shutdown(self) -> None:
        self.dispatcher.shutdown()

    @property
    def agent_running(self) -> int:
        return self.dispatcher.running_count()

    @property
    def current_path(self) -> str:
        project = self.project_by_name(self.current_name)
        if project is None:
            return r"D:\AutoCode"
        return project.path

    def now_text(self) -> str:
        return timefmt.local(self.clock.now()).strftime(timefmt.DISPLAY_FORMAT)

    def now_stamp(self) -> str:
        return timefmt.stamp(self.clock.now())

    def item(self, item_id: str) -> WorkItem:
        found = self.store.get(item_id)
        if found is None:
            raise ValueError("找不到工項")
        return found

    def project_by_name(self, name: str) -> ProjectRecord | None:
        for project in self.projects:
            if project.name == name:
                return project
        return None

    def counts(self) -> dict[str, int]:
        totals = {status: 0 for status in board.STATUSES}
        for item in self.items:
            totals[item.status] += 1
        totals["overview"] = sum(totals.values())
        totals["all"] = totals["overview"] - totals["accepted"]
        return totals

    def set_filter(self, status: str) -> None:
        if status not in FILTERS:
            raise ValueError(status)
        self.filter_name = status

    def set_source(self, source: str) -> None:
        if source not in SOURCES:
            raise ValueError(source)
        self.source = source

    def set_item_status(
        self, item_id: str, status: str, actor: str = "user", expected_version: int | None = None
    ) -> bool:
        if status not in board.STATUSES:
            raise ValueError(status)
        item = self.item(item_id)
        if status == "accepted" and item_id in ACCEPT_BLOCKED:
            raise ValueError(ACCEPT_BLOCKED[item_id])
        changed = board.set_status(item, status, actor, self.now_stamp())
        if changed is item:
            return False
        self.store.commit(changed, item.version if expected_version is None else expected_version)
        return True

    def edit_item(self, item_id: str, fields: dict, actor: str = "user") -> bool:
        item = self.item(item_id)
        changed = board.edit(item, fields, actor, self.now_stamp())
        if changed is item:
            return False
        self.store.commit(changed, item.version)
        return True

    def agent_sync(self, item_id: str, zone: str) -> str:
        """Mirror a card state onto the board without overriding a user decision."""
        item = self.item(item_id)
        if item.zone == zone:
            return "unchanged"
        if not board.agent_may_overwrite(item):
            return "needs-review"
        self.store.commit(board.set_zone(item, zone, "agent", self.now_stamp()), item.version)
        return "updated"

    def visible_items(self) -> list[WorkItem]:
        query = self.query.strip().lower()
        visible: list[WorkItem] = []
        for item in self.items:
            if not _status_matches(self.filter_name, item.status):
                continue
            if self.source != "all" and item.source != self.source:
                continue
            if query and query not in _search_blob(item):
                continue
            visible.append(item)
        return visible

    def section(self) -> tuple[str, str, int]:
        title, hint = SECTION_COPY[self.filter_name]
        return title, hint, len(self.visible_items())

    def remember(self, name: str) -> None:
        self.recent = [name] + [item for item in self.recent if item != name]

    def open_named(self, name: str) -> str:
        project = self.project_by_name(name)
        if project is None or project.access == "路徑不存在":
            raise ValueError("路徑不存在，未開啟")
        if self.boards is not None and not self.boards.exists(project.path):
            project.access = "路徑不存在"
            raise ValueError("路徑不存在，未開啟")
        self._check_switch(project.name)
        self.current_name = project.name
        self.branch = project.branch or "main"
        project.access = "可存取"
        project.opened = self.now_text()
        project.in_combo = True
        if self.boards is not None:
            self._bind_board(self.boards.open(project.path))
        self.dispatcher.repo = project.path
        self.remember(project.name)
        self._remember_project(project)
        return project.path

    def _check_switch(self, name: str) -> None:
        if name != self.current_name and self.dispatcher.running_count():
            raise ValueError(SWITCH_BLOCKED)

    def create_project(self, name: str, root: str) -> ProjectRecord:
        cleaned = name.strip()
        if not cleaned:
            raise ValueError("請輸入專案名稱")
        if self.project_by_name(cleaned) is not None:
            raise ValueError("專案已存在")
        self._check_switch(cleaned)
        folder = root.strip().rstrip("\\/") or r"D:\AIAD"
        path = folder + "\\" + cleaned
        project_board = self.boards.create(path) if self.boards is not None else None
        record = ProjectRecord(cleaned, path, "main", "可存取", self.now_text(), True)
        self.projects.insert(0, record)
        self.current_name = cleaned
        self.branch = "main"
        if project_board is not None:
            self._bind_board(project_board)
        self.dispatcher.repo = path
        self.remember(cleaned)
        self._remember_project(record)
        return record

    def apply_cloud_url(self, raw: str) -> str:
        self.cloud_url = raw.strip()
        return self.cloud_url

    def set_appearance(self, style: str, tone: str) -> None:
        if style not in UI_STYLES:
            raise ValueError(style)
        if tone not in UI_TONES:
            raise ValueError(tone)
        self.ui_style = style
        self.tone = tone

    def set_language(self, language: str) -> None:
        if language not in LANGUAGES:
            raise ValueError(language)
        self.language = language

    def save_account(self, fields: dict[str, str]) -> None:
        self.account = dict(fields)

    def combo_projects(self) -> list[ProjectRecord]:
        return [project for project in self.projects if project.in_combo]


def _within(path: str, root: str) -> bool:
    if not root.strip():
        return False
    folder = ntpath.normcase(ntpath.normpath(path))
    base = ntpath.normcase(ntpath.normpath(root)).rstrip("\\")
    return folder == base or folder.startswith(base + "\\")


def _status_matches(selected: str, item_status: str) -> bool:
    if selected == "overview":
        return True
    if selected == "all":
        return item_status != "accepted"
    if selected in board.STATUSES:
        return item_status == selected
    raise ValueError(selected)


def _search_blob(item: WorkItem) -> str:
    parts = [
        item.item_id,
        item.code,
        item.title,
        item.kind,
        item.source,
        item.bdd,
        item.tdd,
        item.note,
        *item.files,
    ]
    return " ".join(parts).lower()


def seed_projects() -> list[ProjectRecord]:
    return [
        ProjectRecord("SGenAxis", r"D:\AutoCode", "main", "可存取", "2026-10-06 10:23", True),
        ProjectRecord("AutoRig_Core", r"D:\AutoCode\AutoRig_Core", "main", "可存取", "—", True, False),
        ProjectRecord("MayaPipeline_v2", r"D:\AutoCode\MayaPipeline_v2", "main", "可存取", "—", True, False),
        ProjectRecord("HoudiniDCC_Tools", r"D:\AutoCode\HoudiniDCC_Tools", "main", "可存取", "—", True, False),
        ProjectRecord("Sample Project", r"D:\Projects\Sample", "dev", "未開啟", "—", False),
        ProjectRecord("Legacy Demo", r"D:\Archive\Demo", "main", "路徑不存在", "2026-09-28 14:11", False),
    ]


_SINGLE_LIGHTS = {
    "PSIDE-01",
    "PSIDE-02",
    "PSIDE-03",
    "PSIDE-04",
    "PSIDE-05",
    "PSIDE-06",
    "ARCH-01",
    "UID-01",
    "TASK-08",
    "TASK-07",
}


def _seed(
    item_id: str,
    code: str,
    title: str,
    status: str,
    source: str,
    files: tuple[str, ...],
    bdd: str,
    tdd: str,
    created: str,
    completed: str | None,
    note: str,
    kind: str = "task",
) -> WorkItem:
    zone = "green" if status == "accepted" else status
    actor = "user" if source == "manual" else "agent"
    created = _iso(created)
    completed = _iso(completed) if completed else None
    changed = completed or created
    log = (board.ZoneChange(created, "gray", actor),)
    if zone != "gray":
        log += (board.ZoneChange(changed, zone, actor),)
    return WorkItem(
        item_id=item_id,
        code=code,
        title=title,
        zone=zone,
        source=source,
        files=files,
        bdd=bdd,
        tdd=tdd,
        created=created,
        note=note,
        kind=kind,
        started=created if zone == "yellow" else None,
        completed=completed if zone == "green" else None,
        confirmed=status == "accepted",
        by=actor,
        updated=changed,
        updated_by=actor,
        log=log,
        light_mode="single" if item_id in _SINGLE_LIGHTS else "set",
    )


def _iso(text: str) -> str:
    return timefmt.stamp(datetime.strptime(text, "%Y-%m-%d %H:%M"))


def seed_items() -> list[WorkItem]:
    return [
        _seed("TASK-G1", "REAL-GL-WALKTHROUGH-040", "0.4.0 整合後真 GL 桌面走查", "gray", "agent", ("viewport/walkthrough.py",), "—", "—", "2026-10-10 15:12", None, "整合後只有 ctest 與 smoke-test 的證據，沒有在真 GL 桌面手動走過各卡路徑。"),
        _seed("TASK-G2", "VERSION-LABEL-01", "portable 打包的 VERSION.txt 把 MINOR 標成 patch / 修 Bug", "gray", "manual", ("scripts/package-portable.ps1",), "—", "—", "2026-10-10 15:12", None, "scripts/package-portable.ps1 的 ReleaseChannel 一律標 PATCH。版號 version 本身正確，只有標籤不準。", "bug"),
        _seed("TASK-Y1", "HOST-001", "可重現工具鏈與測試骨架", "yellow", "git", ("tools/test/runner.py",), "BDD-HOST-001", "TDD-HOST-001", "2026-10-06 13:57", None, "鎖定依賴與 test:task 入口尚未接上可執行 runner。"),
        _seed("TASK-Y2", "SPEC-001", "ModuleSpec 與子模組骨架", "gray", "agent", ("docs/spec/module-spec.md",), "BDD-SPEC-001", "—", "2026-10-06 14:20", None, "模組架構排後面。規格模型先保留，核准前不可改契約。"),
        _seed("TASK-01", "TASK-01", "Y1 D1/D2 Region presentation", "red", "git", ("regiove.eak", "presentation.diff"), "BDD", "TDD", "2022-03-19 15:12", None, "推播回饋 Region presentation", "bug"),
        _seed("TASK-02", "TASK-02", "Y1 D1/D2 Region presentation", "red", "git", ("regiove.ppp",), "BDD", "TDD", "2022-03-19 15:40", None, "等待測試案例鏈接確認", "bug"),
        _seed("TASK-03", "TASK-03", "Y1 D1/D2 Region presentation", "red", "agent", ("presentation",), "—", "TDD", "2022-03-19 16:02", None, "待對帳執行記錄", "bug"),
        _seed("TASK-04", "TASK-04", "Y1 D1/D2 Region presentation", "red", "git", ("worker.pon",), "BDD", "—", "2022-03-19 16:18", None, "工項阻斷：缺少 RED 斷言", "bug"),
        _seed("TASK-05", "TASK-05", "Y1 D1/D2 Region presentation", "red", "manual", ("hetadel.jog",), "BDD", "TDD", "2022-03-19 16:33", None, "驗證逾時需重試", "bug"),
        _seed("TASK-06", "TASK-06", "Y1 D1/D2 Region presentation", "red", "git", ("presentation.diff",), "BDD", "TDD", "2022-03-19 16:48", None, "待核准工項封包", "bug"),
        _seed("PSIDE-01", "PSIDE-01", "PySide UI：選單與標題列", "green", "manual", ("sgenaxis/ui/main_window.py",), "BDD-PSIDE-01", "TDD-PSIDE-01", "2026-10-11 02:50", "2026-10-11 02:50", "QMenuBar／QToolBar。檔案、最近專案、儲存與專案路徑已接上。"),
        _seed("PSIDE-02", "PSIDE-02", "PySide UI：工項側欄與燈號", "green", "manual", ("sgenaxis/ui/sidebar.py",), "BDD-PSIDE-02", "TDD-PSIDE-02", "2026-10-11 02:50", "2026-10-11 02:50", "總覽、待辦、進行中、Bug、已完成、已驗收。"),
        _seed("PSIDE-03", "PSIDE-03", "PySide UI：工項表", "green", "manual", ("sgenaxis/ui/task_board.py",), "BDD-PSIDE-03", "TDD-PSIDE-03", "2026-10-11 02:50", "2026-10-11 02:50", "狀態、檔案、BDD、TDD、時間與備註。"),
        _seed("PSIDE-04", "PSIDE-04", "PySide UI：Git 操作視窗", "green", "manual", ("sgenaxis/ui/git_dialogs.py",), "BDD-PSIDE-04", "TDD-PSIDE-04", "2026-10-11 02:50", "2026-10-11 02:50", "提交、歷史、分支與 Clone 等操作視窗。不寫入 Git。"),
        _seed("PSIDE-05", "PSIDE-05", "PySide UI：設定視窗", "green", "manual", ("sgenaxis/ui/settings_dialog.py",), "BDD-PSIDE-05", "TDD-PSIDE-05", "2026-10-11 02:50", "2026-10-11 02:50", "專案管理、GIT 設定（含雲端路徑）、一般語系與帳戶。"),
        _seed("PSIDE-06", "PSIDE-06", "PySide UI：狀態列", "green", "manual", ("sgenaxis/ui/statusbar.py",), "BDD-PSIDE-06", "TDD-PSIDE-06", "2026-10-11 02:50", "2026-10-11 02:50", "版本、同步、進度與 Agent 狀態。"),
        _seed("ARCH-01", "ARCH-01", "模組架構圖", "gray", "manual", ("viewArchDag",), "—", "—", "2026-10-11 02:50", None, "排後面。PySide UI 與其他工項先處理。"),
        _seed("UID-01", "UID-01", "UI 設計工具", "gray", "manual", ("viewUiDesign",), "—", "—", "2026-10-11 02:50", None, "排後面。PySide UI 與其他工項先處理。"),
        _seed("TASK-08", "HOST-001", "可重現工具鏈驗收封包", "green", "git", ("worker.clif",), "BDD-HOST-001", "TDD-HOST-001", "2026-10-06 13:57", "2026-10-06 15:30", "測試通過，狀態仍是已完成。改為已驗收後會出現在已驗收頁。"),
        _seed("TASK-07", "TASK-07", "feat(spec): 修正 BDD/TDD 測試鏈", "accepted", "git", ("regiove.eak", "docs/board/tasks.json"), "BDD", "TDD", "2022-03-18 11:05", "2022-03-19 09:40", "已全數通過並標註已驗收"),
    ]
