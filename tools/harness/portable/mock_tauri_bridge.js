/**
 * SGenAxis portable harness — Mock Tauri invoke (PD-HARNESS-MOCK-01).
 * Inject BEFORE app.js. Fake data only; harness=true; not product evidence.
 */
(function () {
  "use strict";
  const params = new URLSearchParams(location.search);
  const stressN = Math.max(0, parseInt(params.get("stress") || "0", 10) || 0);
  const harness = {
    true: true,
    mode: "portable-mock",
    stressN: stressN,
    startedAt: new Date().toISOString(),
  };

  function zoneCycle(i) {
    return ["gray", "yellow", "red", "green"][i % 4];
  }

  function makeTasks(n) {
    const out = [];
    for (let i = 0; i < n; i++) {
      out.push({
        id: "FAKE-" + String(i + 1).padStart(4, "0"),
        ref: "FAKE-" + String(i + 1).padStart(4, "0"),
        title: "假工項壓力 #" + (i + 1),
        zone: zoneCycle(i),
        kind: "task",
        bdd: "BDD-FAKE-" + (i + 1),
        tdd: "PENDING",
        note: "harness fake — not product evidence",
      });
    }
    return out;
  }

  const baseN = stressN > 0 ? stressN : 24;
  let boardTasks = makeTasks(baseN);
  const settings = {
    project_root: "D:\\\\HarnessFake\\\\SGenAxis",
    board_path: "docs/PROJECT-BOARD.html",
    agent_active: false,
    run_mode: "dry_run",
    theme: "dark",
    locale: "zh-Hant",
    cli_path: "",
    mcp_url: "",
    harness: true,
  };

  const chunks = [];
  let runSeq = 0;

  async function invoke(cmd, args) {
    args = args || {};
    switch (cmd) {
      case "host_get_settings":
        return Object.assign({}, settings);
      case "host_set_settings":
        Object.assign(settings, args.settings || args || {});
        settings.harness = true;
        return Object.assign({}, settings);
      case "host_set_agent_settings":
        Object.assign(settings, args || {});
        settings.harness = true;
        return Object.assign({}, settings);
      case "host_pick_project_directory":
      case "host_new_project_directory":
        return { path: settings.project_root, cancelled: false, harness: true };
      case "file_save":
        return {
          ok: true,
          board_write_back: false,
          harness: true,
          settings: Object.assign({}, settings),
        };
      case "host_request_shutdown":
        console.info("[harness] host_request_shutdown ignored in portable mock");
        return { ok: true, harness: true, ignored: true };
      case "get_board":
      case "load_local_board":
        return {
          asOf: new Date().toISOString(),
          overall: "PARTIAL",
          tasks: boardTasks.slice(),
          harness: true,
        };
      case "upsert_task": {
        const t = args.task || args;
        const id = t.id || "FAKE-NEW";
        const idx = boardTasks.findIndex((x) => x.id === id);
        if (idx >= 0) boardTasks[idx] = Object.assign({}, boardTasks[idx], t);
        else boardTasks.push(Object.assign({ zone: "gray", kind: "task" }, t, { id: id }));
        return { tasks: boardTasks.slice(), harness: true };
      }
      case "batch_work_tags":
        return { ok: true, updated: 0, errors: [], harness: true };
      case "git_workbench_summary":
        return {
          branch: "harness/fake",
          dirty: true,
          ahead: 0,
          behind: 0,
          changes: [
            { path: "fake/a.rs", status: "modified" },
            { path: "fake/b.md", status: "untracked" },
          ],
          harness: true,
          not_run: false,
        };
      case "git_workbench_diff":
        return {
          path: args.path || "fake/a.rs",
          unified: "--- a/fake/a.rs\n+++ b/fake/a.rs\n@@ -1 +1 @@\n-old\n+new harness\n",
          harness: true,
        };
      case "start_run": {
        runSeq += 1;
        const runId = "harness-run-" + runSeq;
        chunks.length = 0;
        for (let i = 0; i < 8; i++) {
          chunks.push({
            seq: i,
            kind: "log",
            text: "[harness] fake chunk " + i + " work=" + (args.work_item_id || "-"),
          });
        }
        chunks.push({ seq: 8, kind: "end", text: "ok", classification: "ok" });
        return {
          run_id: runId,
          dry_run: true,
          started: true,
          harness: true,
        };
      }
      case "poll_chunks": {
        const batch = chunks.splice(0, 3);
        return {
          runId: args.runId,
          chunks: batch,
          done: chunks.length === 0,
          harness: true,
        };
      }
      case "cancel_run":
        chunks.length = 0;
        return { cancelled: true, harness: true };
      case "deploy_status":
      case "deploy_check":
        return {
          supported: false,
          status: "NOT RUN",
          detail: "harness mock — no deploy adapter",
          harness: true,
        };
      case "list_artifacts":
        return { artifacts: [], harness: true, empty: true };
      case "ports_status":
        return {
          ports: [
            { name: "FileSystemPort", adapter: "FakeFs", status: "ok" },
            { name: "GitPort", adapter: "FakeGit", status: "ok" },
            { name: "ProcessPort", adapter: "FakeProc", status: "NOT RUN" },
          ],
          harness: true,
        };
      case "listen_get_projection":
        return {
          status: "ok",
          events: stressN > 0 ? makeListenEvents(Math.min(stressN, 200)) : [],
          host_fs_watch: "NOT RUN",
          host_git_watch: "NOT RUN",
          harness: true,
        };
      case "arch_get_projection":
        return {
          live: true,
          modules: [
            { id: "UI", label: "UI" },
            { id: "CORE", label: "Core" },
            { id: "EXEC", label: "EXEC" },
          ],
          deps: [
            { from: "UI", to: "CORE" },
            { from: "CORE", to: "EXEC" },
          ],
          harness: true,
        };
      case "get_evidence_summary":
        return { status: "PARTIAL", items: [], harness: true };
      case "list_commands":
        return { commands: [], harness: true };
      default:
        console.warn("[harness] unhandled invoke", cmd, args);
        return { ok: false, error: "harness_unhandled:" + cmd, harness: true };
    }
  }

  function makeListenEvents(n) {
    const ev = [];
    for (let i = 0; i < n; i++) {
      ev.push({
        kind: i % 3 === 0 ? "fs" : i % 3 === 1 ? "git" : "agent",
        summary: "fake-event-" + i,
      });
    }
    return ev;
  }

  window.__TAURI__ = {
    core: { invoke: invoke },
  };
  window.__SGENAXIS_HARNESS__ = harness;
  document.documentElement.dataset.harness = "portable-mock";
  console.info("[harness] mock Tauri bridge ready", harness);
})();
