import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "board"))
sys.path.insert(0, str(ROOT / "docs"))

from board_core import domain, usecases
from board_core.json_store import JsonFileStore
import board_watch

NOW = "2026-10-27T12:00:00+08:00"


def _fields(**extra):
    return {"id": "ORANGE-1", "title": "Decision card", **extra}


def test_orange_create_requires_trimmed_decision_and_allows_legacy_other_zones():
    task = domain.new_task(_fields(zone="orange", decision="  Choose A  "), "user", NOW)
    assert task["decision"] == "Choose A"
    assert task["ownerActions"] == []
    assert domain.new_task(_fields(), "user", NOW)["decision"] == ""
    legacy = domain.new_task(_fields(), "user", NOW)
    legacy.pop("decision")
    assert domain.validate(legacy) is legacy
    for decision in (None, "", " \t ", "x" * 201, 123):
        with pytest.raises(domain.DomainError):
            domain.new_task(_fields(zone="orange", decision=decision), "user", NOW)
    with pytest.raises(domain.DomainError):
        domain.new_task(_fields(decision="x" * 201), "user", NOW)


def test_orange_domain_edit_transition_and_rejection_preserve_input():
    base = domain.new_task(_fields(), "user", NOW)
    before = copy.deepcopy(base)
    with pytest.raises(domain.DomainError, match="decision"):
        domain.apply_zone(base, "orange", "user", NOW)
    assert base == before

    prepared = domain.apply_edit(base, {"decision": " Select an owner "}, "user", NOW)
    moved = domain.apply_zone(prepared, "orange", "user", NOW)
    assert moved["decision"] == "Select an owner"
    assert moved["zone"] == "orange"
    assert moved["doneAt"] is None
    assert moved["version"] == base["version"]
    assert len(moved["log"]) == len(base["log"]) + 1
    with pytest.raises(domain.DomainError, match="decision"):
        domain.apply_edit(moved, {"decision": "  "}, "user", NOW)
    with pytest.raises(domain.DomainError, match="200"):
        domain.apply_edit(moved, {"decision": "x" * 201}, "user", NOW)


def test_store_rejected_orange_transition_keeps_file_bytes_and_version(tmp_path):
    path = tmp_path / "tasks.json"
    store = JsonFileStore(str(path))
    task = domain.new_task(_fields(), "user", NOW)
    store.create(task)
    before = path.read_bytes()
    with pytest.raises(domain.DomainError, match="decision"):
        usecases.set_zone(store, task["id"], "orange", "user", NOW, expected_version=1)
    assert path.read_bytes() == before
    stored = store.get(task["id"])
    assert stored["zone"] == "gray" and stored["version"] == 1
    assert stored["doneAt"] is None and len(stored["log"]) == 1


def test_http_create_and_patch_orange_are_atomic_and_trim_decision():
    data = {"tasks": [], "asOf": "before"}
    before = copy.deepcopy(data)
    with pytest.raises(board_watch.BoardError):
        board_watch.create_task(data, {"id": "ORANGE-1", "title": "Needs choice", "zone": "orange"}, NOW)
    assert data == before

    task = board_watch.create_task(
        data, {"id": "ORANGE-1", "title": "Needs choice", "zone": "orange", "decision": "  Pick owner  "}, NOW
    )
    assert task["decision"] == "Pick owner"
    assert task["version"] == 1
    before_task = copy.deepcopy(task)
    before_asof = data["asOf"]
    with pytest.raises(board_watch.BoardError):
        board_watch.patch_task(data, task["id"], {"fields": {"decision": "  "}}, NOW)
    assert task == before_task and data["asOf"] == before_asof

    moved = board_watch.patch_task(
        data, task["id"], {"zone": "red", "fields": {"decision": "  Need product choice  "}, "expected_version": 1}, NOW
    )
    assert moved["zone"] == "red" and moved["decision"] == "Need product choice"
    assert moved["version"] == 2
    assert len(moved["log"]) == 2
    board_watch.patch_task(data, task["id"], {"zone": "gray", "expected_version": 2}, NOW)
    moved = board_watch.patch_task(data, task["id"], {"fields": {"decision": ""}, "expected_version": 3}, NOW)
    assert moved["decision"] == ""
