"""Project board folder `<project>/.sgenaxis` and the seed snapshot (spec-BOARD-LOCAL-01 §2.3)."""

import hashlib
import json
import os
from collections import Counter
from datetime import datetime

import pytest

from sgenaxis.adapters import board_seed
from sgenaxis.adapters.json_board import (
    FileLock,
    FileProjectBoards,
    JsonDispatchState,
    JsonProjectRegistry,
    JsonReleaseStore,
    JsonTaskStore,
    user_registry_path,
)
from sgenaxis.core import board, board_json
from sgenaxis.core.board import VersionConflict, WorkItem
from sgenaxis.core.dispatcher import Dispatcher
from sgenaxis.core.in_memory import (
    DryRunLauncher,
    InMemoryProjectBoards,
    InMemoryProjectRegistry,
    ManualClock,
    StaticReleases,
)
from sgenaxis.core.ports import StoreError
from sgenaxis.core.session import SWITCH_BLOCKED, ProjectRecord, WorkbenchSession

T0 = "2026-10-11T09:00:00+08:00"


def _item(item_id: str = "TASK-1", zone: str = "gray") -> WorkItem:
    return WorkItem(
        item_id=item_id,
        code=item_id,
        title="標題",
        zone=zone,
        source="manual",
        files=("a.py",),
        bdd="",
        tdd="",
        created=T0,
        note="",
        updated=T0,
        updated_by="user",
        by="user",
        log=(board.ZoneChange(T0, zone, "user"),),
    )


needs_seed = pytest.mark.skipif(not board_seed.available(), reason="Beta board snapshot is local data, not in the repo")


@needs_seed
def test_seed_snapshot_matches_its_manifest_and_beta_counts():
    items = board_seed.load_items()
    assert len(items) == 80
    assert Counter(item.zone for item in items) == {"green": 31, "gray": 19, "red": 17, "yellow": 13}
    assert len(board_seed.load_releases()) == 1
    manifest = json.loads(open(os.path.join(board_seed.SEED_DIR, "manifest.json"), encoding="utf-8").read())
    for name, digest in manifest["files"].items():
        with open(os.path.join(board_seed.SEED_DIR, name), "rb") as handle:
            assert hashlib.sha256(handle.read()).hexdigest() == digest
    assert "HoneyBadgerCreator" in board_seed.source()


@needs_seed
def test_seed_snapshot_with_a_changed_file_is_refused(tmp_path):
    for name in ("tasks.json", "releases.json", "manifest.json"):
        (tmp_path / name).write_bytes(open(os.path.join(board_seed.SEED_DIR, name), "rb").read())
    (tmp_path / "tasks.json").write_bytes((tmp_path / "tasks.json").read_bytes() + b" ")
    with pytest.raises(StoreError, match="SHA-256"):
        board_seed.load_items(str(tmp_path))


def test_board_json_round_trip_keeps_beta_fields():
    item = _item()
    data = board_json.to_dict(item)
    assert {"id", "ref", "zone", "createdAt", "updatedAt", "updatedBy", "log", "version"} <= set(data)
    assert board_json.from_dict(data) == item
    assert board_json.document([item])["schema"] == "hb-board/1"


def test_store_writes_hb_board_json_and_checks_versions(tmp_path):
    path = tmp_path / ".sgenaxis" / "tasks.json"
    store = JsonTaskStore(str(path))
    assert store.list() == []
    store.create(_item())
    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["schema"] == "hb-board/1" and document["tasks"][0]["id"] == "TASK-1"
    changed = board.set_zone(store.get("TASK-1"), "yellow", "agent", "2026-10-11T10:00:00+08:00")
    store.commit(changed, 1)
    assert JsonTaskStore(str(path)).get("TASK-1").zone == "yellow"
    before = path.read_bytes()
    with pytest.raises(VersionConflict):
        store.commit(board.set_zone(changed, "green", "agent", T0), 1)
    assert path.read_bytes() == before
    assert not (tmp_path / ".sgenaxis" / ".lock").exists()
    assert not (tmp_path / ".sgenaxis" / "tasks.json.tmp").exists()


def test_store_sees_writes_from_another_process(tmp_path):
    path = str(tmp_path / "tasks.json")
    mine, theirs = JsonTaskStore(path), JsonTaskStore(path)
    mine.create(_item("TASK-1"))
    assert theirs.get("TASK-1") is not None
    theirs.create(_item("TASK-2"))
    assert {item.item_id for item in mine.list()} == {"TASK-1", "TASK-2"}


def test_busy_lock_times_out_and_the_file_is_unchanged(tmp_path):
    path = tmp_path / "tasks.json"
    store = JsonTaskStore(str(path), lock_timeout=0.2)
    store.create(_item())
    before = path.read_bytes()
    with FileLock(store.lock_path):
        with pytest.raises(StoreError, match="正被其他程式寫入"):
            store.create(_item("TASK-2"))
    assert path.read_bytes() == before


def test_broken_board_file_raises_a_store_error(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text("{ not json", encoding="utf-8")
    with pytest.raises(StoreError, match="無法解析"):
        JsonTaskStore(str(path)).list()


def test_create_project_writes_an_empty_board_and_open_never_writes(tmp_path):
    boards = FileProjectBoards()
    existing = tmp_path / "Existing"
    existing.mkdir()
    opened = boards.open(str(existing))
    assert opened.store.list() == []
    assert not (existing / ".sgenaxis").exists()
    created = boards.create(str(tmp_path / "Fresh"))
    tasks = tmp_path / "Fresh" / ".sgenaxis" / "tasks.json"
    assert json.loads(tasks.read_text(encoding="utf-8")) == {"schema": "hb-board/1", "tasks": []}
    assert (tmp_path / "Fresh" / ".sgenaxis" / "report-inbox").is_dir()
    assert created.store.location == str(tasks)
    with pytest.raises(StoreError, match="路徑不存在"):
        boards.open(str(tmp_path / "Missing"))


def test_report_inbox_moves_handled_files_and_never_deletes(tmp_path):
    project = FileProjectBoards().create(str(tmp_path / "P"))
    inbox = project.inbox
    assert inbox.read("RUN-1") is None
    with open(inbox.path("RUN-1"), "wb") as handle:
        handle.write(b"{}")
    assert inbox.read("RUN-1") == b"{}"
    target = inbox.archive("RUN-1", "processed")
    assert target.endswith(os.path.join("reports", "processed", "RUN-1.json"))
    assert os.path.isfile(target) and inbox.read("RUN-1") is None


def test_dispatch_state_survives_in_the_project_folder(tmp_path):
    project = FileProjectBoards().create(str(tmp_path / "P"))
    project.store.create(_item("R1", "red"))
    clock = ManualClock(datetime(2026, 10, 11, 9, 0))
    first = Dispatcher(project.store, clock, DryRunLauncher(), state=project.state, inbox=project.inbox)
    lane = first.add_lane("codex", max_cards=3)
    first.start_lane(lane.lane_id)
    first.report("R1", "done", "ok")
    saved = JsonDispatchState(str(tmp_path / "P" / ".sgenaxis" / "dispatch.json")).load()
    assert saved["lanes"][0]["agent"] == "codex"
    again = Dispatcher(project.store, clock, DryRunLauncher(), state=project.state, inbox=project.inbox)
    assert again.history[0].card_id == "R1"
    assert project.store.get("R1").zone == "green"


def _session(boards) -> WorkbenchSession:
    projects = [
        ProjectRecord("Home", r"D:\Home", "main", "可存取", "—"),
        ProjectRecord("Other", r"D:\Other", "main", "可存取", "—"),
    ]
    return WorkbenchSession(boards=boards, projects=projects, current_name="Home")


def test_opening_a_project_binds_its_board_and_dispatcher():
    boards = InMemoryProjectBoards()
    session = _session(boards)
    assert session.board_label() == "示範資料（未存檔）"
    demo_dispatcher = session.dispatcher
    session.open_named("Other")
    assert session.store is boards.boards[r"D:\Other"].store
    assert session.dispatcher is not demo_dispatcher
    assert session.items == []
    assert [lane.agent for lane in session.dispatcher.lanes] == ["claude"]


def test_switching_projects_is_refused_while_an_agent_runs():
    session = _session(InMemoryProjectBoards())
    lane = session.dispatcher.lanes[0]
    session.dispatcher.start_lane(lane.lane_id)
    with pytest.raises(ValueError, match=SWITCH_BLOCKED):
        session.open_named("Other")
    with pytest.raises(ValueError, match=SWITCH_BLOCKED):
        session.create_project("New", r"D:\X")
    assert session.current_name == "Home"


def test_missing_folders_are_marked_and_cannot_be_opened():
    session = _session(InMemoryProjectBoards(missing={r"D:\Other"}))
    assert session.project_by_name("Other").access == "路徑不存在"
    with pytest.raises(ValueError, match="路徑不存在"):
        session.open_named("Other")


@needs_seed
def test_seed_release_record_is_read_as_a_release():
    (release,) = board_seed.load_releases()
    assert (release.release_id, release.version, release.kind) == ("v0.3.4", "0.3.4", "portable")
    assert [artifact.exists for artifact in release.artifacts] == [False, False, False]
    assert release.commits[0].hash == "29ac1ad"
    assert release.report_md.startswith("## @REVIEW 2026-09-05")
    assert ("CHANGELOG", "docs/CHANGELOG.md") in release.sources


def test_project_releases_file_is_optional_and_read_newest_first(tmp_path):
    path = tmp_path / "releases.json"
    store = JsonReleaseStore(str(path))
    assert store.list() == []
    path.write_text(json.dumps({"schema": "hb-board/1", "releases": [
        {"version": "0.1.0", "kind": "portable", "releasedAt": "2026-01-01T00:00:00+08:00"},
        {"version": "0.2.0", "kind": "installer", "releasedAt": "2026-02-01T00:00:00+08:00"},
    ]}), encoding="utf-8")
    assert [item.version for item in store.list()] == ["0.2.0", "0.1.0"]
    path.write_text('{"releases": 3}', encoding="utf-8")
    with pytest.raises(StoreError, match="佈版"):
        store.list()


@needs_seed
def test_opening_a_project_switches_to_its_release_records():
    boards = InMemoryProjectBoards()
    session = WorkbenchSession(
        boards=boards, releases=StaticReleases(board_seed.load_releases()),
        projects=[ProjectRecord("Other", r"D:\Other", "main", "可存取", "—")], current_name="Other",
    )
    assert [item.version for item in session.release_list()] == ["0.3.4"]
    session.open_named("Other")
    assert session.release_list() == []


def test_opened_and_created_projects_are_remembered_across_restarts():
    registry = InMemoryProjectRegistry()
    session = _session(InMemoryProjectBoards())
    session.registry = registry
    session.open_named("Other")
    session.create_project("Fresh", r"D:\Work")
    assert [row["name"] for row in registry.projects] == ["Fresh", "Other"]
    assert registry.projects[1]["path"] == r"D:\Other"
    again = WorkbenchSession(
        boards=InMemoryProjectBoards(missing={r"D:\Work\Fresh"}), registry=registry,
        projects=[ProjectRecord("Other", r"D:\Seed\Other", "main", "可存取", "—")],
    )
    assert [(row.name, row.path) for row in again.projects[:2]] == [("Fresh", r"D:\Work\Fresh"), ("Other", r"D:\Other")]
    assert again.project_by_name("Fresh").access == "路徑不存在"
    assert len(again.projects) == 2


def test_seed_projects_that_were_never_opened_are_not_saved():
    registry = InMemoryProjectRegistry()
    session = _session(InMemoryProjectBoards())
    session.registry = registry
    session.open_named("Other")
    assert [row["name"] for row in registry.projects] == ["Other"]


def test_registry_file_round_trip_and_an_unreadable_file_is_left_alone(tmp_path):
    path = tmp_path / "SGenAxis" / "projects.json"
    registry = JsonProjectRegistry(str(path))
    assert registry.load() == []
    registry.save([{"name": "P", "path": r"D:\P", "branch": "main", "opened": "2026-10-11 09:00"}])
    assert JsonProjectRegistry(str(path)).load()[0]["path"] == r"D:\P"
    path.write_text("{ broken", encoding="utf-8")
    session = WorkbenchSession(registry=JsonProjectRegistry(str(path)))
    assert "無法解析" in session.registry_error
    assert session.registry is None
    assert path.read_text(encoding="utf-8") == "{ broken"
    assert user_registry_path({"APPDATA": r"C:\Users\u\AppData\Roaming"}) == os.path.join(
        r"C:\Users\u\AppData\Roaming", "SGenAxis", "projects.json"
    )


def test_creating_a_project_creates_its_board(tmp_path):
    session = _session(FileProjectBoards())
    record = session.create_project("Fresh", str(tmp_path))
    assert session.board_path == os.path.join(record.path, ".sgenaxis", "tasks.json")
    assert os.path.isfile(session.board_path)
