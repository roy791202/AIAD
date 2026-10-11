"""Qt-free checks for the workbench queue, projects, and local prefs."""

from pathlib import Path

import pytest

from sgenaxis.core.board import VersionConflict
from sgenaxis.core.in_memory import DryRunLauncher
from sgenaxis.core.session import WorkbenchSession


def test_status_choice_moves_the_light_and_blocks_toolchain_acceptance():
    session = WorkbenchSession()
    assert session.set_item_status("TASK-01", "green") is True
    moved = session.item("TASK-01")
    assert (moved.status, moved.updated_by, moved.log[-1].zone) == ("green", "user", "green")
    with pytest.raises(ValueError, match="不進入已驗收頁"):
        session.set_item_status("TASK-Y1", "accepted")
    assert session.item("TASK-Y1").status == "yellow"


def test_accepting_is_an_owner_confirmation_on_green():
    session = WorkbenchSession()
    assert session.set_item_status("TASK-08", "accepted") is True
    item = session.item("TASK-08")
    assert (item.zone, item.confirmed, item.status) == ("green", True, "accepted")
    assert session.counts()["accepted"] == 2
    assert session.set_item_status("TASK-08", "green") is True
    assert session.item("TASK-08").status == "green"


def test_stale_writes_are_rejected_and_keep_the_newer_change():
    session = WorkbenchSession()
    stale = session.item("TASK-01").version
    session.set_item_status("TASK-01", "yellow")
    with pytest.raises(VersionConflict):
        session.set_item_status("TASK-01", "green", expected_version=stale)
    assert session.item("TASK-01").zone == "yellow"


def test_agent_sync_never_overwrites_a_user_decision():
    session = WorkbenchSession()
    session.set_item_status("TASK-01", "yellow")
    assert session.agent_sync("TASK-01", "green") == "needs-review"
    assert session.item("TASK-01").zone == "yellow"
    assert session.agent_sync("TASK-G1", "yellow") == "updated"
    assert session.item("TASK-G1").updated_by == "agent"
    assert session.agent_sync("TASK-G1", "yellow") == "unchanged"


def test_edit_item_goes_through_the_rules():
    session = WorkbenchSession()
    before = session.item("TASK-03").version
    session.edit_item("TASK-03", {"bdd": "BDD-TASK-03"})
    item = session.item("TASK-03")
    assert (item.bdd, item.version, item.updated_by) == ("BDD-TASK-03", before + 1, "user")


def test_session_dispatch_is_simulated_and_counts_running_lanes():
    session = WorkbenchSession()
    assert isinstance(session.launcher, DryRunLauncher)
    lane = session.dispatcher.lane("L1")
    assert (lane.agent, lane.max_cards, lane.state) == ("claude", 5, "idle")
    session.dispatcher.start_lane(lane.lane_id)
    assert lane.current.card_id == "TASK-01"
    assert session.agent_running == 1
    session.dispatcher.report("TASK-01", "done", "模擬回報")
    assert session.item("TASK-01").status == "green"
    assert lane.current.card_id == "TASK-02"


def test_default_queue_is_the_six_bugs():
    session = WorkbenchSession()
    visible = session.visible_items()
    assert session.filter_name == "red"
    assert [item.item_id for item in visible] == [
        "TASK-01",
        "TASK-02",
        "TASK-03",
        "TASK-04",
        "TASK-05",
        "TASK-06",
    ]


def test_counts_match_the_scheduled_board():
    counts = WorkbenchSession().counts()
    assert counts == {
        "gray": 5,
        "yellow": 1,
        "red": 6,
        "green": 7,
        "accepted": 1,
        "overview": 20,
        "all": 19,
    }


def test_overview_includes_accepted_and_all_hides_it():
    session = WorkbenchSession()
    session.set_filter("overview")
    assert len(session.visible_items()) == 20
    session.set_filter("all")
    assert all(item.status != "accepted" for item in session.visible_items())
    assert len(session.visible_items()) == 19


def test_unknown_filter_is_rejected():
    session = WorkbenchSession()
    with pytest.raises(ValueError):
        session.set_filter("blue")


def test_search_and_source_narrow_the_green_pyside_tasks():
    session = WorkbenchSession()
    session.set_filter("green")
    session.query = "pyside"
    assert len(session.visible_items()) == 6
    session.set_source("agent")
    session.set_filter("gray")
    session.query = ""
    assert [item.item_id for item in session.visible_items()] == ["TASK-G1", "TASK-Y2"]


def test_deferred_architecture_and_ui_design_stay_gray():
    items = {item.item_id: item for item in WorkbenchSession().items}
    assert items["ARCH-01"].status == "gray"
    assert items["UID-01"].status == "gray"
    assert "排後面" in items["ARCH-01"].note
    assert "排後面" in items["UID-01"].note


def test_open_named_project_updates_path_and_recent_order():
    session = WorkbenchSession()
    path = session.open_named("AutoRig_Core")
    assert path == r"D:\AutoCode\AutoRig_Core"
    assert session.current_name == "AutoRig_Core"
    assert session.current_path == path
    assert session.recent[0] == "AutoRig_Core"


def test_missing_path_does_not_switch_the_current_project():
    session = WorkbenchSession()
    with pytest.raises(ValueError, match="路徑不存在"):
        session.open_named("Legacy Demo")
    assert session.current_name == "SGenAxis"
    assert session.current_path == r"D:\AutoCode"


def test_create_project_rejects_blank_and_duplicate_names():
    session = WorkbenchSession()
    with pytest.raises(ValueError, match="請輸入專案名稱"):
        session.create_project("  ", r"D:\AIAD")
    with pytest.raises(ValueError, match="專案已存在"):
        session.create_project("SGenAxis", r"D:\AIAD")


def test_create_project_becomes_current_and_recent():
    session = WorkbenchSession()
    created = session.create_project("RigTools", r"D:\AIAD")
    assert created.path == r"D:\AIAD\RigTools"
    assert session.current_name == "RigTools"
    assert session.recent[0] == "RigTools"
    assert session.combo_projects()[0].name == "RigTools"


def test_cloud_url_trims_whitespace():
    session = WorkbenchSession()
    applied = session.apply_cloud_url("  https://github.com/sgenaxis/cloud.git\n")
    assert applied == "https://github.com/sgenaxis/cloud.git"
    assert session.cloud_url == applied


def test_appearance_and_language_reject_unknown_values():
    session = WorkbenchSession()
    session.set_appearance("light", "beige")
    session.set_language("en")
    assert (session.ui_style, session.tone, session.language) == ("light", "beige", "en")
    with pytest.raises(ValueError):
        session.set_appearance("neon", "blue")
    with pytest.raises(ValueError):
        session.set_language("fr")


def test_save_account_stays_in_memory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    session = WorkbenchSession()
    session.save_account({"email": "a@b.c", "password": "secret", "claude": "token"})
    assert session.account["password"] == "secret"
    assert list(tmp_path.iterdir()) == []
