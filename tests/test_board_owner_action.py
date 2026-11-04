import http.client
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "board"))
sys.path.insert(0, str(ROOT / "docs"))

from board_core import domain
import board_watch

NOW = "2026-10-27T13:00:00+08:00"


def _task(zone="orange", decision="Need Owner", version=4, actions=None):
    return {
        "id": "OWNER-1", "ref": "OWNER-1", "title": "Decision", "zone": zone,
        "kind": "task", "decision": decision, "createdAt": NOW, "doneAt": None,
        "startedAt": None, "by": "user", "updatedAt": NOW, "updatedBy": "user",
        "version": version, "log": [{"t": NOW, "zone": zone, "by": "user"}],
        **({"ownerActions": actions} if actions is not None else {}),
    }


def _write_board(path, task):
    snapshot = {"tasks": [task], "releases": [], "asOf": NOW}
    path.write_text('<!doctype html>\n<nav class=\"nav\">Board</nav>\n' + board_watch.SNAPSHOT_OPEN + json.dumps(snapshot) + board_watch.SNAPSHOT_CLOSE + '\n<footer>shell</footer>\n', encoding="utf-8")


def _post(server, path, body):
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("POST", path, json.dumps(body), {"Content-Type": "application/json"})
    response = conn.getresponse()
    raw = response.read().decode("utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        payload = raw
    conn.close()
    return response.status, payload


@pytest.fixture
def disposable_api(tmp_path):
    board = tmp_path / "board.html"
    _write_board(board, _task())
    server = ThreadingHTTPServer(("127.0.0.1", 0), board_watch.build_handler(board, board_watch.StampHub()))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, board
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_approve_records_owner_action_and_cas_transitions_orange_to_gray(disposable_api):
    server, board = disposable_api
    status, result = _post(server, "/api/tasks/OWNER-1/owner-action", {
        "action": "approve", "text": "Proceed with bounded proposal", "expected_version": 4,
        "by": "agent",
    })
    # Client-controlled actor metadata is rejected and cannot turn an agent request into Owner approval.
    assert status == 400
    status, result = _post(server, "/api/tasks/OWNER-1/owner-action", {
        "action": "approve", "text": "Proceed with bounded proposal", "expected_version": 4,
    })
    assert status == 200
    assert result["zone"] == "gray" and result["doneAt"] is None
    assert result["version"] == 5
    assert result["ownerActions"] == [{
        "action": "approve", "text": "Proceed with bounded proposal", "decision": "Need Owner",
        "at": result["ownerActions"][0]["at"], "by": "user",
    }]
    after = board.read_bytes()
    status, _ = _post(server, "/api/tasks/OWNER-1/owner-action", {
        "action": "instruct", "text": "stale", "expected_version": 4,
    })
    assert status == 409 and board.read_bytes() == after


def test_instruct_keeps_zone_and_limits_action_history_to_twenty(disposable_api):
    server, board = disposable_api
    status, result = _post(server, "/api/tasks/OWNER-1/owner-action", {
        "action": "instruct", "text": "Keep working", "expected_version": 4,
    })
    assert status == 200
    assert result["zone"] == "orange" and result["version"] == 5
    assert len(result["ownerActions"]) == 1
    assert result["ownerActions"][0]["action"] == "instruct"
    assert result["ownerActions"][0]["decision"] == "Need Owner"

    task = _task(zone="red", decision="Historical", actions=[{"n": i} for i in range(20)])
    changed = domain.apply_owner_action(task, "instruct", "More", "user", NOW)
    assert changed["zone"] == "red"
    assert len(changed["ownerActions"]) == 20
    assert changed["ownerActions"][0] == {"n": 1}
    assert changed["ownerActions"][-1]["decision"] == "Historical"


def test_invalid_action_and_unqualified_approval_are_atomic(disposable_api):
    server, board = disposable_api
    before = board.read_bytes()
    for body in (
        {"action": "cancel", "text": "ok", "expected_version": 4},
        {"action": "approve", "text": "fake actor", "expected_version": 4, "by": "agent"},
        {"action": "instruct", "text": "   ", "expected_version": 4},
        {"action": "instruct", "text": "x" * 1001, "expected_version": 4},
        {"action": "instruct", "text": "ok"},
    ):
        status, _ = _post(server, "/api/tasks/OWNER-1/owner-action", body)
        assert status in (400, 409)
        assert board.read_bytes() == before

    _write_board(board, _task(zone="red", decision="Needs a choice"))
    before = board.read_bytes()
    status, _ = _post(server, "/api/tasks/OWNER-1/owner-action", {
        "action": "approve", "text": "Not eligible", "expected_version": 4,
    })
    assert status == 400 and board.read_bytes() == before

    task = _task(zone="red", decision="Needs a choice")
    with pytest.raises(domain.DomainError):
        domain.apply_owner_action(task, "approve", "Approved", "user", NOW)
    with pytest.raises(domain.DomainError):
        domain.apply_owner_action(_task(), "approve", "Approved", "agent", NOW)


def test_missing_owner_actions_are_backward_compatible():
    task = _task(actions=None)
    changed = domain.apply_owner_action(task, "instruct", "Use existing option", "user", NOW)
    assert changed["ownerActions"][0]["decision"] == "Need Owner"
    assert len(domain.apply_owner_action(task, "instruct", "x" * 1000, "user", NOW)["ownerActions"][0]["text"]) == 1000


def test_health_advertises_orange_and_owner_action_capabilities(disposable_api):
    server, _board = disposable_api
    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    conn.request("GET", "/api/health")
    response = conn.getresponse()
    health = json.loads(response.read().decode("utf-8"))
    conn.close()
    assert response.status == 200
    assert "orange" in health["zones"]
    assert health["ownerActionsSupported"] is True
