"""PSIDE-05: settings pages for projects, Git, general preferences, and the Agent launch mode."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sgenaxis.core.session import (
    LANGUAGES,
    LAUNCH_MODE_LABELS,
    LAUNCH_MODES,
    UI_STYLES,
    UI_TONES,
    WorkbenchSession,
)

COPY = {
    "zh-Hant": {"title": "設定", "projects": "專案管理", "git": "GIT 設定", "general": "一般", "agent": "Agent 啟動", "save": "儲存帳戶"},
    "zh-Hans": {"title": "设置", "projects": "项目管理", "git": "GIT 设置", "general": "常规", "agent": "Agent 启动", "save": "保存账户"},
    "en": {"title": "Settings", "projects": "Projects", "git": "Git", "general": "General", "agent": "Agent launch", "save": "Save account"},
    "ja": {"title": "設定", "projects": "プロジェクト", "git": "Git", "general": "一般", "agent": "Agent 起動", "save": "アカウントを保存"},
    "ko": {"title": "설정", "projects": "프로젝트", "git": "Git", "general": "일반", "agent": "Agent 실행", "save": "계정 저장"},
}
LAUNCH_HELP = (
    "模擬：不啟動任何程式，在 Agent 頁用「模擬回報」結束一輪。\n"
    "實際：真的啟動 Claude Code／Cursor Agent／Codex，Agent 會修改專案裡的檔案；"
    "只限沙盒資料夾，切換專案後會回到模擬。"
)

STYLE_LABELS = {"dark": "暗", "light": "亮", "gray": "灰"}
TONE_LABELS = {"blue": "藍", "gray": "灰", "beige": "米", "iron": "鐵黑"}
LANG_LABELS = {"zh-Hant": "繁中", "zh-Hans": "简中", "en": "EN", "ja": "日本語", "ko": "한국어"}


class SettingsDialog(QWidget):
    project_open_requested = Signal(str)
    appearance_changed = Signal(str)
    launch_mode_changed = Signal(str)

    def __init__(self, session: WorkbenchSession, parent=None) -> None:
        super().__init__(parent)
        self.session = session
        self.setObjectName("settingsDialog")
        self.resize(760, 480)
        root = QHBoxLayout(self)
        self.nav = QListWidget()
        self.nav.setObjectName("settingsNav")
        self.nav.setFixedWidth(140)
        self.stack = QStackedWidget()
        root.addWidget(self.nav)
        root.addWidget(self.stack, 1)

        self._project_page()
        self._git_page()
        self._general_page()
        self._agent_page()
        self.apply_copy()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

    def show_page(self, page: str) -> None:
        index = {"projects": 0, "git": 1, "general": 2, "agent": 3}[page]
        self.nav.setCurrentRow(index)
        if page == "git":
            self.cloud_url.setFocus()

    def apply_copy(self) -> None:
        text = COPY[self.session.language]
        self.setWindowTitle(text["title"])
        labels = (text["projects"], text["git"], text["general"], text["agent"])
        for index, label in enumerate(labels):
            if self.nav.item(index) is None:
                self.nav.addItem(label)
            else:
                self.nav.item(index).setText(label)
        self.save_account.setText(text["save"])

    def _project_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.project_table = QTableWidget(0, 5)
        self.project_table.setObjectName("projectTable")
        self.project_table.setHorizontalHeaderLabels(["專案", "路徑", "分支", "狀態", "開啟時間"])
        self.project_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.project_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.project_table.verticalHeader().setVisible(False)
        self.project_table.horizontalHeader().setStretchLastSection(True)
        self.project_table.cellDoubleClicked.connect(self._open_selected_row)
        layout.addWidget(self.project_table)
        open_button = QPushButton("開啟")
        open_button.setObjectName("openManagedProject")
        open_button.clicked.connect(self._open_selected_row)
        layout.addWidget(open_button)
        self.stack.addWidget(page)
        self.refresh_projects()

    def refresh_projects(self) -> None:
        rows = self.session.projects
        self.project_table.setRowCount(len(rows))
        for row, project in enumerate(rows):
            values = (project.name, project.path, project.branch, project.access, project.opened)
            for column, value in enumerate(values):
                self.project_table.setItem(row, column, QTableWidgetItem(value))

    def _open_selected_row(self) -> None:
        row = self.project_table.currentRow()
        if row < 0:
            return
        item = self.project_table.item(row, 0)
        if item is not None:
            self.project_open_requested.emit(item.text())

    def _git_page(self) -> None:
        page = QWidget()
        form = QFormLayout(page)
        self.cloud_url = QLineEdit(self.session.cloud_url)
        self.cloud_url.setObjectName("gitCloudUrl")
        self.cloud_url.setPlaceholderText("貼上 https://github.com/org/repo.git 或 git@host:org/repo.git")
        self.remote_url = QLineEdit(self.session.cloud_url)
        self.remote_url.setObjectName("gitRemoteUrl")
        self.remote_url.setReadOnly(True)
        self.clone_url = QLineEdit(self.session.cloud_url)
        self.clone_url.setObjectName("cloneRepoUrl")
        self.clone_url.setReadOnly(True)
        form.addRow("雲端 Git 路徑", self.cloud_url)
        form.addRow("remote.origin.url", self.remote_url)
        form.addRow("Clone URL", self.clone_url)
        save = QPushButton("儲存設定")
        save.setObjectName("saveGitSettings")
        save.clicked.connect(self._save_git)
        form.addRow(save)
        self.cloud_url.textChanged.connect(self._mirror_cloud)
        self.stack.addWidget(page)

    def _mirror_cloud(self, raw: str) -> None:
        cleaned = self.session.apply_cloud_url(raw)
        for field in (self.cloud_url, self.remote_url, self.clone_url):
            if field.text() != cleaned:
                field.blockSignals(True)
                field.setText(cleaned)
                field.blockSignals(False)

    def _save_git(self) -> None:
        self._mirror_cloud(self.cloud_url.text())

    def _general_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        self.lang_group = self._choice_row(layout, "語系", LANG_LABELS, LANGUAGES, self.session.language, self._on_language)
        self.style_group = self._choice_row(layout, "UI 風格", STYLE_LABELS, UI_STYLES, self.session.ui_style, self._on_style)
        self.tone_group = self._choice_row(layout, "色調", TONE_LABELS, UI_TONES, self.session.tone, self._on_tone)
        form = QFormLayout()
        self.family = QLineEdit()
        self.given = QLineEdit()
        self.middle = QLineEdit()
        self.email = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.claude = QLineEdit()
        self.claude.setEchoMode(QLineEdit.Password)
        self.codex = QLineEdit()
        self.codex.setEchoMode(QLineEdit.Password)
        for label, widget, name in (
            ("姓", self.family, "acctFamily"),
            ("名", self.given, "acctGiven"),
            ("中間名", self.middle, "acctMiddle"),
            ("信箱", self.email, "acctEmail"),
            ("密碼", self.password, "acctPassword"),
            ("Claude Code", self.claude, "acctClaude"),
            ("Codex", self.codex, "acctCodex"),
        ):
            widget.setObjectName(name)
            form.addRow(label, widget)
        layout.addLayout(form)
        self.save_account = QPushButton("儲存帳戶")
        self.save_account.setObjectName("saveAccount")
        self.save_account.clicked.connect(self._save_account)
        layout.addWidget(self.save_account)
        layout.addStretch(1)
        self.stack.addWidget(page)

    def _agent_page(self) -> None:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.addWidget(QLabel("Agent 啟動方式（只對目前專案）"))
        row = QHBoxLayout()
        group = QButtonGroup(self)
        group.setExclusive(True)
        self.launch_buttons: dict[str, QPushButton] = {}
        for mode in LAUNCH_MODES:
            button = QPushButton(LAUNCH_MODE_LABELS[mode])
            button.setCheckable(True)
            button.setObjectName(f"launch-{mode}")
            button.setAccessibleName(f"Agent 啟動方式：{LAUNCH_MODE_LABELS[mode]}")
            button.clicked.connect(lambda _checked=False, picked=mode: self._on_launch_mode(picked))
            group.addButton(button)
            self.launch_buttons[mode] = button
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        self.launch_reason = QLabel("")
        self.launch_reason.setObjectName("launchReason")
        self.launch_reason.setWordWrap(True)
        layout.addWidget(self.launch_reason)
        help_text = QLabel(LAUNCH_HELP)
        help_text.setObjectName("muted")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)
        layout.addStretch(1)
        self.stack.addWidget(page)
        self.refresh_launch()

    def refresh_launch(self) -> None:
        for mode, button in self.launch_buttons.items():
            button.setChecked(mode == self.session.launch_mode)
        reason = self.session.real_launch_block_reason()
        if self.session.launch_mode == "real":
            self.launch_reason.setText(f"目前：實際啟動　專案 {self.session.current_path}")
        else:
            self.launch_reason.setText("目前：模擬" + (f"　（不能切到實際：{reason}）" if reason else "　（可切到實際）"))

    def _on_launch_mode(self, mode: str) -> None:
        try:
            self.session.set_launch_mode(mode)
        except ValueError as exc:
            self.refresh_launch()
            self.launch_mode_changed.emit(str(exc))
            return
        self.refresh_launch()
        self.launch_mode_changed.emit(f"Agent 啟動方式：{LAUNCH_MODE_LABELS[mode]}")

    def _choice_row(self, layout, caption, labels, values, current, handler):
        layout.addWidget(QLabel(caption))
        row = QHBoxLayout()
        group = QButtonGroup(self)
        group.setExclusive(True)
        for value in values:
            button = QPushButton(labels[value])
            button.setCheckable(True)
            button.setObjectName(f"choice-{value}")
            button.setChecked(value == current)
            button.clicked.connect(lambda _checked=False, picked=value: handler(picked))
            group.addButton(button)
            row.addWidget(button)
        row.addStretch(1)
        layout.addLayout(row)
        return group

    def _on_language(self, language: str) -> None:
        self.session.set_language(language)
        self.apply_copy()

    def _on_style(self, style: str) -> None:
        self.session.set_appearance(style, self.session.tone)
        self.appearance_changed.emit(f"UI 風格：{STYLE_LABELS[style]}")

    def _on_tone(self, tone: str) -> None:
        self.session.set_appearance(self.session.ui_style, tone)
        self.appearance_changed.emit(f"色調：{TONE_LABELS[tone]}")

    def _save_account(self) -> None:
        self.session.save_account(
            {
                "family": self.family.text(),
                "given": self.given.text(),
                "middle": self.middle.text(),
                "email": self.email.text(),
                "password": self.password.text(),
                "claude": self.claude.text(),
                "codex": self.codex.text(),
            }
        )
