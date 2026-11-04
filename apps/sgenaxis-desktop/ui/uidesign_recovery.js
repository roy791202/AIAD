/* Private UI-local recovery helper for the currently loaded DesignDoc only. */
const UidesignRecovery = (() => {
  const histories = new WeakMap();
  const plans = new WeakMap();

  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function canonical(value) {
    if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
    if (value && typeof value === "object") {
      return "{" + Object.keys(value).sort().map((key) => JSON.stringify(key) + ":" + canonical(value[key])).join(",") + "}";
    }
    return JSON.stringify(value);
  }

  function createHistory() {
    const history = Object.freeze({});
    histories.set(history, null);
    return history;
  }

  function prepare(input) {
    if (!input || !input.projectRoot || !String(input.projectRoot).trim()) return { ok: false, code: "UNBOUND_PROJECT" };
    if (!input.identity || !String(input.identity).trim()) return { ok: false, code: "SCOPE_UNSUPPORTED" };
    if (input.activeRunId != null) return { ok: false, code: "ACTIVE_RUN" };
    if (!input.history || !histories.has(input.history)) return { ok: false, code: "CHECKPOINT_INVALID" };
    if (!input.document || !input.clearedDocument) return { ok: false, code: "CHECKPOINT_INVALID" };
    const before = clone(input.document);
    const after = clone(input.clearedDocument);
    const beforeFingerprint = canonical(before);
    const afterFingerprint = canonical(after);
    const plan = Object.freeze({});
    plans.set(plan, {
      history: input.history,
      identity: String(input.identity),
      projectRoot: String(input.projectRoot).trim(),
      before,
      after,
      beforeFingerprint,
      afterFingerprint,
      beforeDirty: clone(input.dirty || {}),
      changed: beforeFingerprint !== afterFingerprint,
    });
    return { ok: true, plan };
  }

  function confirm(plan, live) {
    const checkpoint = plan && plans.get(plan);
    if (!checkpoint || !live || !live.apply) return { ok: false, code: "CHECKPOINT_INVALID" };
    // A preview token is single-use, including stale or no-op confirmation attempts.
    plans.delete(plan);
    if (!live.history || checkpoint.history !== live.history || !histories.has(live.history)) return { ok: false, code: "CHECKPOINT_INVALID" };
    if (String(live.projectRoot || "").trim() !== checkpoint.projectRoot || live.identity !== checkpoint.identity) return { ok: false, code: "BINDING_STALE" };
    if (live.activeRunId != null) return { ok: false, code: "ACTIVE_RUN" };
    if (canonical(live.document) !== checkpoint.beforeFingerprint) return { ok: false, code: "WORKSPACE_STALE" };
    if (canonical(live.dirty || {}) !== canonical(checkpoint.beforeDirty || {})) return { ok: false, code: "WORKSPACE_STALE" };
    if (!checkpoint.changed) return { ok: true, changed: false };
    const history = live.history;
    if (!history || !histories.has(history)) return { ok: false, code: "CHECKPOINT_INVALID" };
    const afterDirty = { ...(checkpoint.beforeDirty || {}), design: true };
    histories.set(history, {
      identity: checkpoint.identity,
      projectRoot: checkpoint.projectRoot,
      before: clone(checkpoint.before),
      after: clone(checkpoint.after),
      beforeFingerprint: checkpoint.beforeFingerprint,
      afterFingerprint: checkpoint.afterFingerprint,
      beforeDirty: clone(checkpoint.beforeDirty || {}),
      afterDirty,
      applied: true,
    });
    try {
      live.apply(clone(checkpoint.after), clone(afterDirty));
    } catch (_projectionError) {
      // The model commit precedes rendering; retain the checkpoint if projection fails.
      return { ok: false, changed: true, code: "PROJECTION_FAILED" };
    }
    return { ok: true, changed: true };
  }

  function applyHistory(history, live, direction) {
    if (!history || !histories.has(history) || !live || !live.apply) return { ok: false, code: "NOTHING_TO_UNDO" };
    const entry = histories.get(history);
    if (!entry || (direction === "undo" && !entry.applied) || (direction === "redo" && entry.applied)) return { ok: false, code: "NOTHING_TO_UNDO" };
    if (String(live.projectRoot || "").trim() !== entry.projectRoot || live.identity !== entry.identity) {
      histories.set(history, null);
      return { ok: false, code: "BINDING_STALE" };
    }
    if (live.activeRunId != null) return { ok: false, code: "ACTIVE_RUN" };
    const expected = direction === "undo" ? entry.afterFingerprint : entry.beforeFingerprint;
    if (canonical(live.document) !== expected) {
      histories.set(history, null);
      return { ok: false, code: "WORKSPACE_STALE" };
    }
    const expectedDirty = direction === "undo" ? entry.afterDirty : entry.beforeDirty;
    if (canonical(live.dirty || {}) !== canonical(expectedDirty || {})) {
      histories.set(history, null);
      return { ok: false, code: "WORKSPACE_STALE" };
    }
    entry.applied = direction === "redo";
    try {
      live.apply(clone(direction === "undo" ? entry.before : entry.after), clone(direction === "undo" ? entry.beforeDirty : entry.afterDirty));
    } catch (_projectionError) {
      return { ok: false, changed: true, code: "PROJECTION_FAILED" };
    }
    return { ok: true, changed: true };
  }

  function undo(history, live) { return applyHistory(history, live, "undo"); }
  function redo(history, live) { return applyHistory(history, live, "redo"); }
  function canUndo(history) { const entry = history && histories.has(history) ? histories.get(history) : null; return !!(entry && entry.applied); }
  function canRedo(history) { const entry = history && histories.has(history) ? histories.get(history) : null; return !!(entry && !entry.applied); }

  return { createHistory, prepare, confirm, undo, redo, canUndo, canRedo };
})();
