"""Application layer. Every write is one store transaction; adapters never touch files.

`by` is chosen by the driving adapter (web = user, CLI / board_sync = agent; INV-BL-6).
`now` is an ISO string supplied by the caller. expected_version=None means "whatever is current"
(CLI / sync convenience); the HTTP adapter always passes the version the page saw.
"""
from . import dispatch, domain


def list_tasks(store):
    return store.load()


def get_task(store, task_id):
    return store.get(task_id)


def create_task(store, fields, by, now):
    return store.create(domain.new_task(fields, by, now))


def set_zone(store, task_id, zone, by, now, expected_version=None):
    return store.update(task_id, expected_version, lambda cur: domain.apply_zone(cur, zone, by, now))


def edit_field(store, task_id, patch, by, now, expected_version=None):
    return store.update(task_id, expected_version, lambda cur: domain.apply_edit(cur, patch, by, now))


def delete_task(store, task_id):
    store.remove(task_id)


def list_releases(release_store):
    return release_store.load()


def report_outcome(store, task_id, outcome, note, by, now, expected_version=None):
    """BOARD-DISPATCH-01 INV-BD-6: done -> green / blocked -> red plus a note line, in one transaction."""
    zone = dispatch.report_zone(outcome)

    def mutate(cur):
        moved = domain.apply_zone(cur, zone, by, now)
        line = dispatch.report_line(outcome, note, now)
        return domain.apply_edit(moved, {"note": dispatch.append_note(moved.get("note"), line)}, by, now)
    return store.update(task_id, expected_version, mutate)


def append_task_note(store, task_id, line, by, now):
    return store.update(task_id, None, lambda cur: domain.apply_edit(
        cur, {"note": dispatch.append_note(cur.get("note"), line)}, by, now))


def record_dispatch_report(state_store, card_id, run_id, outcome, note, now):
    """Attach a report to the lane whose running round is that card (and run, when given) — INV-BD-28.

    A file without `lanes` belongs to a pre-lane board server that may still be running; it is updated in
    its own shape (top-level `current`) so that server still sees the report.
    """
    matched = {"ok": False}
    report = {"outcome": outcome, "note": note or "", "at": now}

    def mutate(state):
        if "lanes" not in state:
            cur = state.get("current")
            if not cur or cur.get("cardId") != card_id or (run_id and cur.get("runId") != run_id):
                return state
            matched["ok"] = True
            return dict(state, current=dict(cur, report=report))
        lanes = []
        for lane in state.get("lanes") or []:
            cur = lane.get("current")
            if not matched["ok"] and cur and cur.get("cardId") == card_id and (not run_id or cur.get("runId") == run_id):
                matched["ok"] = True
                lane = dict(lane, current=dict(cur, report=report))
            lanes.append(lane)
        return dict(state, lanes=lanes) if matched["ok"] else state
    state_store.update_as_stored(mutate)
    return matched["ok"]
