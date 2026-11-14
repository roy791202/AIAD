"""Driven adapter: dispatch runtime state as tools/board/runtime/dispatch.json (BOARD-DISPATCH-01 §2.1, §3.8).

Not task data: runtime state + run history, gitignored. Same transaction shape as JsonFileStore:
lock -> read -> mutate -> tmp + fsync -> os.replace -> unlock.

Schema /2 (parallel lanes, INV-BD-25): {schema, laneSeq, lanes: [lane], history, skipped}.
A /1 file (single agent: top-level state/session/current) is read as one lane L1; it is rewritten as /2
on the next update.
"""
import copy
import os

from . import ports
from .dispatch import new_lane
from .json_store import FileLock, _read_json, atomic_write_json

SCHEMA = "hb-board-dispatch-state/2"
DEFAULT_STATE = {
    "schema": SCHEMA,
    "laneSeq": 0,
    "lanes": [],
    "history": [],
    "skipped": {},
}
_V1_LANE_KEYS = ("state", "stopReason", "error", "session", "current")


def default_state():
    return copy.deepcopy(DEFAULT_STATE)


def migrate(data):
    merged = default_state()
    if "lanes" in data:
        merged.update(data)
        merged["schema"] = SCHEMA
        return merged
    session = data.get("session") or {}
    current = data.get("current") or {}
    agent = session.get("agent") or current.get("agent")
    if agent or data.get("state") not in (None, "idle") or data.get("stopReason") or data.get("error"):
        lane = new_lane("L1", agent, session.get("maxCards"))
        for k in _V1_LANE_KEYS:
            lane[k] = data.get(k, lane[k])
        merged["lanes"] = [lane]
        merged["laneSeq"] = 1
    merged["history"] = list(data.get("history") or [])
    merged["skipped"] = dict(data.get("skipped") or {})
    return merged


class DispatchStateStore:
    def __init__(self, path, lock_timeout=5.0):
        self.path = path
        self.lock_path = path + ".lock"
        self.lock_timeout = lock_timeout

    def _read(self):
        if not os.path.isfile(self.path):
            return default_state()
        data = _read_json(self.path)
        if not isinstance(data, dict):
            raise ports.StoreCorrupt("%s is not a JSON object" % self.path)
        return migrate(data)

    def load(self):
        return self._read()

    def update(self, mutate):
        return self._transact(mutate, self._read)

    def update_as_stored(self, mutate):
        """Same transaction without the /1 -> /2 migration: `board.py report` must not rewrite the file of a
        still-running pre-lane (v2) board server into a shape that server cannot read."""
        return self._transact(mutate, self._read_as_stored)

    def _read_as_stored(self):
        if not os.path.isfile(self.path):
            return default_state()
        data = _read_json(self.path)
        if not isinstance(data, dict):
            raise ports.StoreCorrupt("%s is not a JSON object" % self.path)
        return data

    def _transact(self, mutate, read):
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        with FileLock(self.lock_path, self.lock_timeout):
            new = mutate(read())
            atomic_write_json(self.path, new)
            return new
