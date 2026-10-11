"""Application entry. Offscreen tests construct MainWindow without calling main."""

from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication

from sgenaxis.adapters import board_seed
from sgenaxis.adapters.file_probe import LocalFileProbe
from sgenaxis.adapters.git_reader import GitCliReader
from sgenaxis.adapters.json_board import FileProjectBoards, JsonProjectRegistry, user_registry_path
from sgenaxis.adapters.process_launcher import ProcessLauncher
from sgenaxis.adapters.system_clock import SystemClock
from sgenaxis.core.in_memory import InMemoryTaskStore, StaticReleases
from sgenaxis.core.session import WorkbenchSession
from sgenaxis.ui.main_window import MainWindow
from sgenaxis.ui.theme import theme_qss

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_COMMAND = f'python "{os.path.join(APP_ROOT, "sgenaxis_report.py")}"'
SANDBOX_ROOT = os.path.join(APP_ROOT, "_sandbox")


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SGenAxis")
    seeded = board_seed.available()
    session = WorkbenchSession(
        store=InMemoryTaskStore(board_seed.load_items()) if seeded else None,
        clock=SystemClock(),
        boards=FileProjectBoards(),
        releases=StaticReleases(board_seed.load_releases()) if seeded else None,
        registry=JsonProjectRegistry(user_registry_path()),
        report_command=REPORT_COMMAND,
        real_launcher=ProcessLauncher(),
        real_launch_roots=(SANDBOX_ROOT,),
        git_reader=GitCliReader(),
        file_probe=LocalFileProbe(),
    )
    app.setStyleSheet(theme_qss(session.ui_style, session.tone))
    window = MainWindow(session)
    window.show()
    return app.exec()
