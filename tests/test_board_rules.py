"""Task rules ported from the Beta board (spec-BOARD-LOCAL-01 INV-BL-1..11)."""

import pytest

from sgenaxis.core import board
from sgenaxis.core.board import VersionConflict, WorkItem
from sgenaxis.core.in_memory import InMemoryTaskStore

T0 = "2026-10-11 09:00"
T1 = "2026-10-11 09:05"
T2 = "2026-10-11 09:10"


def _item(zone: str = "gray", **changes) -> WorkItem:
    fields = dict(
        item_id="FX-55",
        code="FX-55",
        title="刪除相機",
        zone=zone,
        source="manual",
        files=(),
        bdd="",
        tdd="",
        created=T0,
        note="",
        completed=T0 if zone == "green" else None,
        started=T0 if zone == "yellow" else None,
        updated=T0,
    )
    fields.update(changes)
    return WorkItem(**fields)


def test_only_the_four_lights_are_zones():
    assert board.ZONES == ("gray", "yellow", "red", "green")
    with pytest.raises(ValueError):
        board.set_zone(_item(), "blue", "user", T1)


def test_done_time_exists_only_while_green():
    green = board.set_zone(_item(), "green", "user", T1)
    assert green.completed == T1
    back = board.set_zone(green, "red", "user", T2)
    assert back.completed is None


def test_start_time_is_written_once_on_first_yellow():
    first = board.set_zone(_item(), "yellow", "agent", T1)
    assert first.started == T1
    again = board.set_zone(board.set_zone(first, "gray", "agent", T2), "yellow", "agent", "2026-10-11 09:20")
    assert again.started == T1


def test_every_zone_change_is_logged_with_time_and_actor_and_keeps_twenty():
    item = _item()
    for index in range(25):
        item = board.set_zone(item, "yellow" if index % 2 == 0 else "gray", "agent", f"2026-10-11 10:{index:02d}")
    assert len(item.log) == board.LOG_LIMIT
    assert item.log[-1] == board.ZoneChange("2026-10-11 10:24", "yellow", "agent")


def test_every_write_bumps_version_and_records_who():
    changed = board.set_zone(_item(), "red", "agent", T1)
    assert (changed.version, changed.updated, changed.updated_by) == (2, T1, "agent")
    assert board.set_zone(changed, "red", "user", T2) is changed


def test_actor_must_be_user_or_agent():
    with pytest.raises(ValueError):
        board.set_zone(_item(), "red", "cowork", T1)


def test_accepted_is_an_owner_confirmation_on_green():
    accepted = board.set_status(_item("yellow"), "accepted", "user", T1)
    assert (accepted.zone, accepted.confirmed, accepted.status) == ("green", True, "accepted")
    assert accepted.completed == T1
    assert accepted.version == 2
    with pytest.raises(ValueError, match="只有使用者"):
        board.set_status(_item("green"), "accepted", "agent", T1)
    unconfirmed = board.set_status(accepted, "green", "user", T2)
    assert (unconfirmed.zone, unconfirmed.confirmed, unconfirmed.status) == ("green", False, "green")
    left = board.set_status(accepted, "red", "user", T2)
    assert (left.confirmed, left.completed) == (False, None)


def test_edit_only_touches_editable_fields():
    edited = board.edit(_item(), {"bdd": "BDD-FX-55", "note": "等 owner"}, "user", T1)
    assert (edited.bdd, edited.note, edited.version) == ("BDD-FX-55", "等 owner", 2)
    with pytest.raises(ValueError):
        board.edit(_item(), {"zone": "green"}, "user", T1)
    with pytest.raises(ValueError):
        board.edit(_item(), {"kind": "story"}, "user", T1)


def test_invalid_ids_and_broken_invariants_are_rejected():
    with pytest.raises(ValueError):
        board.check(_item(item_id="FX 55"))
    with pytest.raises(ValueError):
        board.check(_item("green", completed=None))
    with pytest.raises(ValueError):
        board.check(_item("red", confirmed=True))


def test_agent_never_overwrites_a_task_the_user_changed():
    assert board.agent_may_overwrite(_item(updated_by="agent"))
    assert not board.agent_may_overwrite(_item(updated_by="user"))


def test_store_rejects_stale_versions_and_keeps_the_stored_task():
    store = InMemoryTaskStore([_item()])
    user = board.set_zone(store.get("FX-55"), "yellow", "user", T1)
    agent = board.set_zone(store.get("FX-55"), "green", "agent", T1)
    store.commit(user, expected_version=1)
    with pytest.raises(VersionConflict):
        store.commit(agent, expected_version=1)
    assert store.get("FX-55") == user


def test_store_rejects_duplicates_and_invalid_writes_without_changing_anything():
    store = InMemoryTaskStore([_item()])
    with pytest.raises(ValueError, match="已存在"):
        store.create(_item())
    broken = _item("green", completed=None, version=2)
    with pytest.raises(ValueError):
        store.commit(broken, expected_version=1)
    assert store.get("FX-55") == _item()
    store.delete("FX-55", expected_version=1)
    assert store.list() == []
