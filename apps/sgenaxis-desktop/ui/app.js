/**
 * SGenAxis UI — PD-UI-01 shell + PD-CMD-01 + PD-UI-NAV-01 + PD-UI-RUN-01 + PD-GIT-UI-01 + PD-BOARD-LIVE-01 + PD-DEPLOY-UI-01 + PD-SET-UI-01 + PD-SPEC-UI-01 + PD-REPORT-UI-01 + PD-WIRE-DESTUB-01 + PD-REMAIN-WIN-RESET-01.
 * Menu／派工 → invoke Tauri commands only (no OS／CLI／MCP／git／deploy／spec authority from the page).
 * Browser fallback: toast／local chrome only; projection empty until Tauri.
 * Nav order mirrors git_workbench_interactive (PD-SHELL-SIDEBAR-01):
 * Agent → Tasks Status → 佈版 → 架構圖 → UI設計；次要 Git／Spec／Report／Settings／Ports／Listen.
 * Run panel (PD-UI-RUN-01): start_run／poll_chunks／cancel_run — chunk 串流、取消、結束分類 ok｜cancelled｜failed.
 * Git workbench: read-only status／diff／branch via git_workbench_*；writes gated.
 * Board live: load_local_board reads local #board-snapshot (no :8788／write-back).
 * PD-WIRE-ROOT-01: start_run／git_workbench_*／load_local_board share settings.project_root／board_path；never /demo/root；no ProcessPort from JS.
 * PD-WIRE-BOOT-01: bind／啟動且已有設定 → 僅 invoke load_local_board＋git_workbench_summary；空／缺檔／非 git → NOT RUN；禁 JS 直讀檔／git.
 * Deploy panel: deploy_status／deploy_check／list_artifacts；unsupported when Adapter／CMD absent.
 * Ports panel (PD-REMAIN-PORTS-UI-01): ports_status projection；empty ok；no OS enum from UI.
 * Settings: CLI／MCP／DryRun｜Live via host_get_settings／host_set_agent_settings；secrets never projected.
 * PD-WIRE-AGENT-01: Agent 派工 → start_run（選中 work_item_id＋settings provider／dry_run）；Live 未核准／路徑無效→可讀拒；不直呼 adapters.
 * Spec panel: ModuleSpec 唯讀；核准後原地改 → REPLAN；revise 另入口。
 * Report panel: project_pd_report → tools/pd_report；空 evid→NOT RUN；不回寫規格。
 * PD-REMAIN-FILE-SAVE-01: file.save → file_save（Command）持久化 host settings／看板路徑；禁任意路徑／看板寫回；瀏覽器 NOT RUN.
 * PD-REMAIN-FILE-QUIT-01: file.quit → host_request_shutdown（Command）；瀏覽器模式 NOT RUN（無法關閉殼）.
 * PD-REMAIN-EDIT-01: edit.undo／redo／selectAll／clear — all 尚未實作／NOT RUN until
 * UI→Command→DispatchHost→domain selection／history exists; no half-stub local chrome.
 * PD-REMAIN-ARCH-UI-01: arch.refresh → arch_get_projection；空／無 IPC → NOT RUN；禁靜態假圖冒充 live.
 * PD-SHELL-UIDESIGN-VIEW-01: Viewer → uidesign_package_status／open；設計稿≠產品證據／禁正式驗收 PASS.
 * PD-UIDESIGNER-*: Designer 三欄 + .sgendesign save/load + build preview + ask agent；設計≠產品 PASS.
 */
(function () {
  "use strict";

  const PANEL_TITLES = {
    board: "工項看板",
    agent: "Agent 派工",
    deploy: "佈版",
    arch: "模組架構圖",
    uidesign: "UI Editor／Viewer",
    listen: "監聽投影",
    git: "Git 工作台",
    spec: "ModuleSpec",
    report: "模組／系統報告",
    ports: "Ports 檢視",
    settings: "設定",
  };

  /** Workbench four-zone filters (gray／yellow／red／green); overview／accepted also present. */
  const ZONE_FILTERS = ["gray", "yellow", "red", "green"];

  const FILTER_TITLES = {
    overview: "總覽",
    gray: "待辦",
    yellow: "進行中",
    red: "Bug",
    green: "已完成",
    accepted: "已驗收",
  };

  /* PD-WIRE-DESTUB-01 + PD-REMAIN-DESTUB-OPEN-01: 示意 removed only for
   * UI→Command→DispatchHost→domain paths. After WIRE-OPEN, file.open／
   * project.switch are wired (no 尚未實作). Other unwired stay 尚未實作／NOT RUN. */
  const CMD_LABELS = {
    "file.new": "新增專案（輸入名稱 → 選父目錄 → 建立 → host_set_settings）",
    "file.open": "開啟專案（本機目錄 → host_set_settings）",
    "file.save": "儲存設定／看板路徑（file_save → host-settings）",
    "file.quit": "結束（Tauri → host_request_shutdown；瀏覽器 NOT RUN）",
    "scene.save": "儲存場景套件到目前專案 scene/（default.sg＋.sgml＋.sgui）",
    "scene.open": "自目前專案 scene/ 載入場景套件",
    "scene.saveXml": "儲存場景 XML 到目前專案 scene/default.sgs",
    "scene.openXml": "自目前專案 scene/default.sgs 載入",
    "edit.undo": "復原（尚未實作／NOT RUN）",
    "edit.redo": "重做（尚未實作／NOT RUN）",
    "edit.selectAll": "全選變更（尚未實作／NOT RUN）",
    "edit.clear": "清除選取（尚未實作／NOT RUN）",
    "project.switch": "切換專案（場景有異動會先詢問是否存檔）",
    "project.rescan": "重新掃描儲存庫（Git 唯讀投影）",
    "git.refresh": "重新整理 Git 投影",
    "git.commit": "審核式 Commit",
    "git.push": "審核式 Push",
    "nav.git": "切到 Git 工作台",
    "nav.spec": "切到 ModuleSpec",
    "nav.report": "切到模組／系統報告",
    "nav.arch": "切到模組架構圖",
    "arch.saveXml": "匯出架構圖 XML（.sgenarch.xml）",
    "arch.loadXml": "開啟架構圖 XML",
    "win.uiEditor": "視窗 → UI 編輯（獨立 UI 設計工具視窗）",
    "win.uiViewer": "視窗 → UI 預覽（獨立 Viewer 視窗）",
    "nav.listen": "切到監聽投影",
    "nav.settings": "切到設定",
    "nav.ports": "切到 Ports 檢視",
    "ports.refresh": "重新整理 Ports 投影（ports_status）",
    "uidesign.refresh": "重新整理設計包狀態（uidesign_package_status）",
    "uidesign.open": "受控開啟本機設計包（uidesign_open_package）",
    "uidesign.embed": "內嵌載入 docs/ui-design/index.html",
    "uidesign.save": "儲存 .sgendesign（uidesign_save_design）",
    "uidesign.load": "開啟 .sgendesign（uidesign_load_design）",
    "uidesign.build": "Build 溝通預覽 HTML（uidesign_build_preview）",
    "uidesign.ask": "Ask Agent → BDD／工項草稿（uidesign_ask_agent）",
    "listen.refresh": "重新整理監聽投影（listen_get_projection）",
    "spec.load": "載入範例 ModuleSpec（spec_load_fixture）",
    "spec.refresh": "重新整理 Spec 投影（spec_get_projection）",
    "spec.approve": "核准選取修訂（spec_approve）",
    "spec.tryEdit": "嘗試原地改核准契約（應 REPLAN）",
    "spec.revise": "修訂另入口（spec_revise）",
    "report.openEmpty": "開啟空證據報告投影（fixture=not_run → NOT RUN）",
    "report.openHappy": "開啟有證據報告投影（fixture=happy）",
    "work.new": "新增工項",
    "board.load": "載入本機看板投影",
    "work.assign": "指派 Agent（設定 DryRun｜Live）",
    "work.tags": "批次 BDD／TDD 標籤（batch_work_tags）",
    "agent.cancel": "取消 Run",
    "deploy.check": "檢查部署設定（deploy_check）",
    "deploy.refresh": "重新整理佈版投影（deploy_status／list_artifacts）",
    "arch.refresh": "重新整理架構圖（arch_get_projection）",
    "win.reset": "重設佈局（預設 chrome：看板＋Inspector＋Tasks 展開）",
    "win.inspector": "切換 Inspector",
    "help.about": "SGenAxis 0.1.0 — Tauri 2 + Vanilla UI",
    "help.arch": "架構：UI → Tauri command → Core／EXEC（無直接 OS）",
    "settings.activate": "存為作用中（Live）",
    "settings.draft": "僅存草稿（DryRun）",
    "settings.revoke": "切回 DryRun",
    "settings.project": "檢視投影",
  };

  const toastRoot = document.getElementById("toast-root");
  const statusMsg = document.getElementById("status-msg");
  const statusAgent = document.getElementById("status-agent");
  const inspector = document.getElementById("inspector");
  const ipcStatus = document.getElementById("ipc-status");
  const agentLog = document.getElementById("agent-log");
  const btnCancel = document.getElementById("btn-cancel-run");

  let activeRunId = null;
  let runPollGeneration = 0;
  let taskSeq = 0;
  let boardFilter = "overview";
  let lastBoard = null;
  let selectedTaskId = null;
  let lastSpecProj = null;
  let selectedSpecRevisionId = null;
  let lastSpecRevision = null;
  /** Last Command-sourced arch projection (PD-REMAIN-ARCH-UI-01); never UI-static live. */
  let lastArchProj = null;
  let selectedArchModuleId = null;
  /** Cached host settings.project_root (PD-WIRE-ROOT-01); empty = unbound. */
  let cachedProjectRoot = "";
  /** Cached host settings.board_path. */
  let cachedBoardPath = "";
  /** Last work_item_id sent on start_run (PD-WIRE-AGENT-01). */
  let lastDispatchedWorkItemId = null;
  /** Cached DryRun｜Live from host settings (agent_active／run_mode). */
  let cachedAgentActive = false;

  function getInvoke() {
    const g = window.__TAURI__;
    if (g && g.core && typeof g.core.invoke === "function") {
      return g.core.invoke.bind(g.core);
    }
    return null;
  }

  const invoke = getInvoke();
  const hasIpc = !!invoke;

  /** OS 獨立視窗：index.html?standalone=uidesign&mode=…&path=…（可拖出主視窗） */
  function readUiDesignStandaloneQuery() {
    try {
      const q = new URLSearchParams(window.location.search || "");
      if (q.get("standalone") !== "uidesign") return null;
      return {
        mode: q.get("mode") === "viewer" ? "viewer" : "designer",
        path: q.get("path") || "design/main.sgendesign",
      };
    } catch (_e) {
      return null;
    }
  }
  const UIDESIGN_STANDALONE = readUiDesignStandaloneQuery();
  function isUiDesignStandalone() {
    return !!UIDESIGN_STANDALONE;
  }

  function unboundProjectMessage() {
    return "未綁定 project_root — 請先「開啟專案」或於設定寫入專案根（勿使用 /demo/root）";
  }

  function isForbiddenDemoRoot(root) {
    return (root || "").trim() === "/demo/root";
  }

  function updateToolbarBinding(root) {
    const pathEl = document.getElementById("project-path");
    const labelEl = document.getElementById("project-bind-label");
    const dotEl = document.getElementById("project-bind-dot");
    const statusProject = document.getElementById("status-project");
    const bound = !!(root && String(root).trim()) && !isForbiddenDemoRoot(root);
    const display = bound ? String(root).trim() : "";
    if (pathEl) {
      pathEl.textContent = bound
        ? display
        : "（未綁定 project_root — 請開啟專案）";
      pathEl.title = display;
    }
    if (labelEl) labelEl.textContent = bound ? "已綁定" : "未綁定";
    if (dotEl) {
      dotEl.classList.toggle("warn", !bound);
      dotEl.classList.toggle("ok", bound);
    }
    if (statusProject) {
      statusProject.textContent = bound ? "專案：" + display : "專案：未綁定";
    }
  }

  /**
   * 場景打包 .sgb（bin）：預設專案檔名
   * - default.sg（工項 JSON）
   * - default.sgml（架構圖 XML）
   * - default.sgui（UI 設計 JSON）
   */
  const SGB_MAGIC = "SGB1";
  const SGB_ENTRY_WORK = "default.sg";
  const SGB_ENTRY_ARCH = "default.sgml";
  const SGB_ENTRY_DESIGN = "default.sgui";
  const SGB_DEFAULT_NAME = "default.sgb";
  /** 專案內場景相對路徑（僅限 scene/；經 scene_save／scene_load）。 */
  const SCENE_SGS_REL = "scene/default.sgs";
  const SCENE_SG_REL = "scene/default.sg";
  const SCENE_SGML_REL = "scene/default.sgml";
  const SCENE_SGUI_REL = "scene/default.sgui";
  let sgbPathHint = SGB_DEFAULT_NAME;
  let sceneDirty = false;
  let sceneDirtySuppress = false;
  /** UI 設計異動旗標（與 sceneDirty 同步；宣告提前避免 clearSceneDirty TDZ）。 */
  let designDirty = false;

  function utf8Encode(str) {
    return new TextEncoder().encode(String(str == null ? "" : str));
  }

  function utf8Decode(bytes) {
    return new TextDecoder("utf-8").decode(bytes);
  }

  function concatUint8(parts) {
    let n = 0;
    parts.forEach(function (p) {
      n += p.length;
    });
    const out = new Uint8Array(n);
    let o = 0;
    parts.forEach(function (p) {
      out.set(p, o);
      o += p.length;
    });
    return out;
  }

  function packSgbBinary(entries) {
    const chunks = [utf8Encode(SGB_MAGIC)];
    const countBuf = new Uint8Array(2);
    new DataView(countBuf.buffer).setUint16(0, entries.length, true);
    chunks.push(countBuf);
    entries.forEach(function (ent) {
      const nameBytes = utf8Encode(ent.name);
      const dataBytes =
        ent.data instanceof Uint8Array ? ent.data : utf8Encode(ent.data);
      const nh = new Uint8Array(2);
      new DataView(nh.buffer).setUint16(0, nameBytes.length, true);
      const dh = new Uint8Array(4);
      new DataView(dh.buffer).setUint32(0, dataBytes.length, true);
      chunks.push(nh, nameBytes, dh, dataBytes);
    });
    return concatUint8(chunks);
  }

  function unpackSgbBinary(buf) {
    const bytes =
      buf instanceof Uint8Array
        ? buf
        : new Uint8Array(buf);
    if (bytes.length < 6) throw new Error("SGB too short");
    const magic = utf8Decode(bytes.subarray(0, 4));
    if (magic !== SGB_MAGIC) throw new Error("not SGB1 magic");
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    let o = 4;
    const count = view.getUint16(o, true);
    o += 2;
    const map = Object.create(null);
    for (let i = 0; i < count; i++) {
      if (o + 2 > bytes.length) throw new Error("SGB truncated name len");
      const nlen = view.getUint16(o, true);
      o += 2;
      if (o + nlen + 4 > bytes.length) throw new Error("SGB truncated name");
      const name = utf8Decode(bytes.subarray(o, o + nlen));
      o += nlen;
      const dlen = view.getUint32(o, true);
      o += 4;
      if (o + dlen > bytes.length) throw new Error("SGB truncated data");
      map[name] = utf8Decode(bytes.subarray(o, o + dlen));
      o += dlen;
    }
    return map;
  }

  function buildWorkSgJson() {
    const board =
      lastBoard && typeof lastBoard === "object"
        ? lastBoard
        : { tasks: [], active_run_id: null };
    return JSON.stringify(
      {
        format: "sgenaxis.sg",
        formatVersion: 1,
        encoding: "json",
        meta: {
          savedAt: new Date().toISOString(),
          boardFilter: boardFilter || "overview",
          product_pass: false,
        },
        board: board,
      },
      null,
      2
    );
  }

  function buildDesignSguiJson() {
    const doc = designDoc && typeof designDoc === "object" ? designDoc : blankDesignDoc();
    const copy = JSON.parse(JSON.stringify(doc));
    copy.format = "sgenaxis.sgui";
    copy.formatVersion = copy.formatVersion || 1;
    copy.product_pass = false;
    if (!copy.meta) copy.meta = {};
    copy.meta.updatedAt = new Date().toISOString();
    copy.meta.encoding = "json";
    return JSON.stringify(copy, null, 2);
  }

  function buildSceneSgbBytes() {
    const archXml =
      typeof archDocToXml === "function"
        ? archDocToXml(archDoc)
        : '<?xml version="1.0"?><sgenaxisArch/>';
    return packSgbBinary([
      { name: SGB_ENTRY_WORK, data: buildWorkSgJson() },
      { name: SGB_ENTRY_ARCH, data: archXml },
      { name: SGB_ENTRY_DESIGN, data: buildDesignSguiJson() },
    ]);
  }

  function markSceneDirty() {
    if (sceneDirtySuppress) return;
    sceneDirty = true;
    updateSceneDirtyChrome();
  }

  function clearSceneDirty() {
    sceneDirty = false;
    designDirty = false;
    updateSceneDirtyChrome();
  }

  function updateSceneDirtyChrome() {
    const el = document.getElementById("status-scene-dirty");
    if (el) {
      el.hidden = !sceneDirty;
      el.textContent = sceneDirty ? "場景：未存檔" : "";
    }
    document.body.classList.toggle("is-scene-dirty", !!sceneDirty);
  }

  function withSceneDirtySuppressed(fn) {
    sceneDirtySuppress = true;
    try {
      return fn();
    } finally {
      sceneDirtySuppress = false;
    }
  }

  async function invokeSceneSaveText(relPath, text) {
    if (!invoke) {
      throw new Error("場景存檔 NOT RUN — 需 Tauri scene_save（僅限專案）");
    }
    const root = requireBoundProjectRoot();
    return invoke("scene_save", {
      args: {
        project_root: root,
        rel_path: relPath,
        text: String(text == null ? "" : text),
      },
    });
  }

  async function invokeSceneLoadText(relPath) {
    if (!invoke) {
      throw new Error("場景載入 NOT RUN — 需 Tauri scene_load（僅限專案）");
    }
    const root = requireBoundProjectRoot();
    return invoke("scene_load", {
      args: {
        project_root: root,
        rel_path: relPath,
      },
    });
  }

  /**
   * 切換專案前：場景有異動則詢問是否存檔。
   * @returns {"proceed"|"abort"}
   */
  async function confirmLeaveSceneIfDirty() {
    if (!sceneDirty) return "proceed";
    const saveFirst = window.confirm(
      "目前專案場景有未存檔變更。\n\n確定＝先存到目前專案再切換\n取消＝下一步可選擇放棄變更"
    );
    if (saveFirst) {
      try {
        await saveSceneSgsToProject({ quiet: false });
        return "proceed";
      } catch (err) {
        toast("存檔失敗，已取消切換：" + String(err));
        setStatus("切換專案中止：場景存檔失敗");
        return "abort";
      }
    }
    const discard = window.confirm(
      "放棄未存場景變更並切換專案？\n\n確定＝放棄並切換\n取消＝留在目前專案"
    );
    if (!discard) return "abort";
    clearSceneDirty();
    return "proceed";
  }

  function applyWorkSgJson(text) {
    const doc = JSON.parse(String(text || ""));
    if (!doc || (doc.format !== "sgenaxis.sg" && !doc.board)) {
      throw new Error("invalid default.sg");
    }
    if (doc.meta && doc.meta.boardFilter) {
      boardFilter = doc.meta.boardFilter;
    }
    renderBoard(doc.board || null);
  }

  function applyDesignSguiJson(text) {
    const doc = JSON.parse(String(text || ""));
    if (!doc || !Array.isArray(doc.nodes)) {
      throw new Error("invalid default.sgui");
    }
    /* 內部仍走 DesignDoc；format 可為 sgenaxis.sgui 或 sgenaxis.design */
    designDoc = doc;
    if (!designDoc.meta) designDoc.meta = {};
    designDirty = false;
    const g =
      designDoc.meta.gridSize != null
        ? Number(designDoc.meta.gridSize)
        : DESIGN_GRID_DEFAULT;
    setDesignGridPx(g, { quiet: true });
    const root = formRootNode();
    if (root && root.props) {
      setDesignFormSize(root.props.w, root.props.h, { quiet: true });
    }
    renderDesignCanvas();
    fillDesignProps();
  }

  function applySceneBundleTexts(workText, archText, designText, opts) {
    const quiet = opts && opts.quiet;
    withSceneDirtySuppressed(function () {
      applyWorkSgJson(workText);
      const arch = archDocFromXml(archText);
      if (!arch) throw new Error("default.sgml parse failed");
      applyArchDoc(arch, { quiet: true });
      persistArchDraft();
      applyDesignSguiJson(designText);
    });
    clearSceneDirty();
    if (!quiet) {
      toast("已載入專案場景套件");
      setStatus("場景套件：已自專案 scene/ 載入");
    }
  }

  function applySceneSgbBytes(buf, fileName) {
    const map = unpackSgbBinary(buf);
    const workText =
      map[SGB_ENTRY_WORK] || map["work.sg"] || map["project.sg"];
    const archText =
      map[SGB_ENTRY_ARCH] || map["arch.sgml"] || map["architecture.sgml"];
    const designText =
      map[SGB_ENTRY_DESIGN] || map["design.sgui"] || map["ui.sgui"];
    if (!workText || !archText || !designText) {
      throw new Error(
        "SGB missing default.sg／default.sgml／default.sgui"
      );
    }
    if (fileName) sgbPathHint = String(fileName);
    applySceneBundleTexts(workText, archText, designText, { quiet: false });
  }

  async function saveSceneBundleToProject(opts) {
    const quiet = opts && opts.quiet;
    requireBoundProjectRoot();
    const archXml =
      typeof archDocToXml === "function"
        ? archDocToXml(archDoc)
        : '<?xml version="1.0"?><sgenaxisArch/>';
    await invokeSceneSaveText(SCENE_SG_REL, buildWorkSgJson());
    await invokeSceneSaveText(SCENE_SGML_REL, archXml);
    await invokeSceneSaveText(SCENE_SGUI_REL, buildDesignSguiJson());
    persistArchDraft();
    clearSceneDirty();
    if (!quiet) {
      toast("已儲存場景套件到專案 scene/");
      setStatus(
        "場景套件已寫入 " +
          SCENE_SG_REL +
          "＋" +
          SCENE_SGML_REL +
          "＋" +
          SCENE_SGUI_REL
      );
    }
  }

  async function loadSceneBundleFromProject(opts) {
    const quiet = opts && opts.quiet;
    const workDto = await invokeSceneLoadText(SCENE_SG_REL);
    const archDto = await invokeSceneLoadText(SCENE_SGML_REL);
    const designDto = await invokeSceneLoadText(SCENE_SGUI_REL);
    applySceneBundleTexts(workDto.text, archDto.text, designDto.text, {
      quiet: quiet,
    });
  }

  async function downloadSceneSgb() {
    try {
      await saveSceneBundleToProject({ quiet: false });
    } catch (err) {
      toast("儲存場景套件失敗：" + String(err));
      setStatus("場景套件存檔失敗：" + String(err));
    }
  }

  async function openSceneSgbPicker() {
    try {
      await loadSceneBundleFromProject({ quiet: false });
    } catch (err) {
      toast("開啟專案場景套件失敗：" + String(err));
      setStatus("場景套件載入失敗：" + String(err));
    }
  }

  function wireSceneSgbUi() {
    /* 專案範圍存取：不再使用任意路徑 file picker */
  }

  /**
   * 場景 XML .sgs：專案內場景單一 XML（對照 .sgb 三件套）
   * - work（工項／board）
   * - architecture（sgenaxisArch）
   * - design（UI 設計節點）
   */
  const SGS_DEFAULT_NAME = "default.sgs";
  let sgsPathHint = SGS_DEFAULT_NAME;

  function stripXmlDeclaration(xmlText) {
    return String(xmlText || "").replace(/^<\?xml[^?]*\?>\s*/i, "");
  }

  function xmlTextEl(tag, text) {
    if (text == null || text === "") return "";
    return "<" + tag + ">" + escapeXml(text) + "</" + tag + ">\n";
  }

  function tagsToXml(tagName, list) {
    if (!Array.isArray(list) || !list.length) return "";
    let out = "        <" + tagName + ">\n";
    list.forEach(function (item) {
      if (item == null) return;
      if (typeof item === "string" || typeof item === "number" || typeof item === "boolean") {
        out += "          <tag>" + escapeXml(String(item)) + "</tag>\n";
      } else if (typeof item === "object") {
        out +=
          "          <tag" +
          archAttr("id", item.id || "") +
          archAttr("label", item.label || item.title || "") +
          ">" +
          escapeXml(item.body || item.text || item.value || "") +
          "</tag>\n";
      }
    });
    out += "        </" + tagName + ">\n";
    return out;
  }

  function boardTaskToXml(t) {
    if (!t || typeof t !== "object") return "";
    let xml =
      "      <task" +
      archAttr("id", t.id || "") +
      archAttr("title", t.title || "") +
      archAttr("zone", t.zone || "") +
      archAttr("kind", t.kind || "") +
      archAttr("ref", t.ref || "") +
      archAttr("status", t.status || "") +
      ">\n";
    xml += tagsToXml("bdd", t.bdd);
    xml += tagsToXml("tdd", t.tdd);
    if (t.note != null && t.note !== "") {
      xml += xmlTextEl("note", String(t.note));
    }
    /* 其餘欄位保真：JSON payload（仍包在 XML 場景內） */
    const known = {
      id: 1,
      title: 1,
      zone: 1,
      kind: 1,
      ref: 1,
      status: 1,
      bdd: 1,
      tdd: 1,
      note: 1,
    };
    const extra = {};
    Object.keys(t).forEach(function (k) {
      if (!known[k]) extra[k] = t[k];
    });
    if (Object.keys(extra).length) {
      xml +=
        "        <extra encoding=\"json\"><![CDATA[" +
        JSON.stringify(extra) +
        "]]></extra>\n";
    }
    xml += "      </task>\n";
    return xml;
  }

  function designNodeToXml(n) {
    if (!n || typeof n !== "object") return "";
    let xml =
      "      <node" +
      archAttr("id", n.id || "") +
      archAttr("type", n.type || "") +
      archAttr("parentId", n.parentId == null ? "" : String(n.parentId)) +
      ">\n";
    const props = n.props && typeof n.props === "object" ? n.props : {};
    xml += "        <props";
    Object.keys(props).forEach(function (k) {
      const v = props[k];
      if (v == null || typeof v === "object") return;
      xml += archAttr(k, String(v));
    });
    xml += " />\n";
    Object.keys(props).forEach(function (k) {
      const v = props[k];
      if (v == null || typeof v !== "object") return;
      xml +=
        "        <prop" +
        archAttr("name", k) +
        ' encoding="json"><![CDATA[' +
        JSON.stringify(v) +
        "]]></prop>\n";
    });
    if (n.bddHint) xml += xmlTextEl("bddHint", n.bddHint);
    if (n.tddHint) xml += xmlTextEl("tddHint", n.tddHint);
    if (Array.isArray(n.behaviorHints) && n.behaviorHints.length) {
      xml += "        <behaviorHints>\n";
      n.behaviorHints.forEach(function (h) {
        xml += "          <hint>" + escapeXml(String(h)) + "</hint>\n";
      });
      xml += "        </behaviorHints>\n";
    }
    xml += "      </node>\n";
    return xml;
  }

  function sceneDocToSgsXml() {
    const board =
      lastBoard && typeof lastBoard === "object"
        ? lastBoard
        : { tasks: [], active_run_id: null };
    const design =
      designDoc && typeof designDoc === "object" ? designDoc : blankDesignDoc();
    const archXml = stripXmlDeclaration(
      typeof archDocToXml === "function"
        ? archDocToXml(archDoc)
        : "<sgenaxisArch/>"
    );
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml +=
      '<sgenaxisScene format="sgenaxis.sgs" formatVersion="1" encoding="xml">\n';
    xml +=
      "  <meta" +
      archAttr("savedAt", new Date().toISOString()) +
      archAttr("boardFilter", boardFilter || "overview") +
      archAttr("product_pass", "false") +
      archAttr("sgbCompat", "default.sg+default.sgml+default.sgui") +
      " />\n";
    xml += '  <work format="sgenaxis.sg" encoding="xml">\n';
    xml +=
      "    <board" +
      archAttr(
        "active_run_id",
        board.active_run_id == null ? "" : String(board.active_run_id)
      ) +
      ">\n";
    (board.tasks || []).forEach(function (t) {
      xml += boardTaskToXml(t);
    });
    xml += "    </board>\n";
    xml += "  </work>\n";
    xml += '  <architecture encoding="xml">\n';
    xml +=
      archXml
        .split("\n")
        .map(function (line) {
          return line ? "    " + line : line;
        })
        .join("\n") +
      (archXml.endsWith("\n") ? "" : "\n");
    xml += "  </architecture>\n";
    xml += '  <design format="sgenaxis.sgui" encoding="xml">\n';
    const dm = design.meta || {};
    xml +=
      "    <meta" +
      archAttr("title", dm.title || "") +
      archAttr("updatedAt", dm.updatedAt || new Date().toISOString()) +
      archAttr("targetStack", dm.targetStack || "") +
      archAttr(
        "gridSize",
        dm.gridSize != null ? String(dm.gridSize) : ""
      ) +
      archAttr("formSize", dm.formSize || "") +
      " />\n";
    xml += "    <nodes>\n";
    (design.nodes || []).forEach(function (n) {
      xml += designNodeToXml(n);
    });
    xml += "    </nodes>\n";
    if (design.selection) {
      xml += xmlTextEl("selection", design.selection);
    }
    xml +=
      "    <product_pass>" +
      (design.product_pass ? "true" : "false") +
      "</product_pass>\n";
    xml += "  </design>\n";
    xml += "</sgenaxisScene>\n";
    return xml;
  }

  function parseTagsFromXml(parentEl, tagName) {
    if (!parentEl) return [];
    const wrap = parentEl.querySelector(tagName);
    if (!wrap) return [];
    const out = [];
    wrap.querySelectorAll(":scope > tag").forEach(function (el) {
      const id = archXmlAttr(el, "id", "");
      const label = archXmlAttr(el, "label", "");
      const body = (el.textContent || "").trim();
      if (id || label) {
        out.push({ id: id || undefined, label: label || undefined, body: body });
      } else if (body) {
        out.push(body);
      }
    });
    return out;
  }

  function boardFromSgsWork(workEl) {
    const boardEl = workEl && workEl.querySelector("board");
    const tasks = [];
    if (boardEl) {
      boardEl.querySelectorAll(":scope > task").forEach(function (tel) {
        const t = {
          id: archXmlAttr(tel, "id", ""),
          title: archXmlAttr(tel, "title", ""),
          zone: archXmlAttr(tel, "zone", "gray"),
          kind: archXmlAttr(tel, "kind", "") || undefined,
          ref: archXmlAttr(tel, "ref", "") || undefined,
          status: archXmlAttr(tel, "status", "") || undefined,
          bdd: parseTagsFromXml(tel, "bdd"),
          tdd: parseTagsFromXml(tel, "tdd"),
        };
        const noteEl = tel.querySelector(":scope > note");
        if (noteEl) t.note = (noteEl.textContent || "").trim();
        const extraEl = tel.querySelector(':scope > extra[encoding="json"]');
        if (extraEl) {
          try {
            const extra = JSON.parse((extraEl.textContent || "").trim() || "{}");
            Object.keys(extra).forEach(function (k) {
              t[k] = extra[k];
            });
          } catch (_e) {
            /* ignore bad extra */
          }
        }
        if (!t.bdd.length) delete t.bdd;
        if (!t.tdd.length) delete t.tdd;
        tasks.push(t);
      });
    }
    const runRaw = boardEl ? archXmlAttr(boardEl, "active_run_id", "") : "";
    return {
      tasks: tasks,
      active_run_id: runRaw === "" ? null : runRaw,
    };
  }

  function designFromSgsDesign(designEl) {
    const metaEl = designEl && designEl.querySelector(":scope > meta");
    const doc = {
      format: "sgenaxis.sgui",
      formatVersion: 1,
      meta: {
        title: metaEl ? archXmlAttr(metaEl, "title", "Untitled Form") : "Untitled Form",
        updatedAt: metaEl ? archXmlAttr(metaEl, "updatedAt", "") : "",
        targetStack: metaEl
          ? archXmlAttr(metaEl, "targetStack", "vanilla-tauri")
          : "vanilla-tauri",
        gridSize: metaEl
          ? Number(archXmlAttr(metaEl, "gridSize", String(DESIGN_GRID_DEFAULT))) ||
            DESIGN_GRID_DEFAULT
          : DESIGN_GRID_DEFAULT,
        formSize: metaEl ? archXmlAttr(metaEl, "formSize", "800x600") : "800x600",
        encoding: "xml",
      },
      nodes: [],
      selection: "node-form-root",
      product_pass: false,
    };
    if (!designEl) return doc;
    designEl.querySelectorAll(":scope > nodes > node").forEach(function (nel) {
      const node = {
        id: archXmlAttr(nel, "id", ""),
        type: archXmlAttr(nel, "type", "Form"),
        parentId: (function () {
          const p = archXmlAttr(nel, "parentId", "");
          return p === "" ? null : p;
        })(),
        props: {},
        bddHint: "",
        tddHint: "",
        behaviorHints: [],
      };
      const propsEl = nel.querySelector(":scope > props");
      if (propsEl && propsEl.attributes) {
        Array.prototype.forEach.call(propsEl.attributes, function (attr) {
          const name = attr.name;
          const raw = attr.value;
          if (raw === "true" || raw === "false") {
            node.props[name] = raw === "true";
          } else if (raw !== "" && !Number.isNaN(Number(raw)) && /^-?\d+(\.\d+)?$/.test(raw)) {
            node.props[name] = Number(raw);
          } else {
            node.props[name] = raw;
          }
        });
      }
      nel.querySelectorAll(':scope > prop[encoding="json"]').forEach(function (pel) {
        const name = archXmlAttr(pel, "name", "");
        if (!name) return;
        try {
          node.props[name] = JSON.parse((pel.textContent || "").trim() || "null");
        } catch (_e) {
          /* ignore */
        }
      });
      const bddEl = nel.querySelector(":scope > bddHint");
      const tddEl = nel.querySelector(":scope > tddHint");
      if (bddEl) node.bddHint = (bddEl.textContent || "").trim();
      if (tddEl) node.tddHint = (tddEl.textContent || "").trim();
      nel.querySelectorAll(":scope > behaviorHints > hint").forEach(function (h) {
        node.behaviorHints.push((h.textContent || "").trim());
      });
      if (node.id) doc.nodes.push(node);
    });
    const selEl = designEl.querySelector(":scope > selection");
    if (selEl) doc.selection = (selEl.textContent || "").trim() || doc.selection;
    const ppEl = designEl.querySelector(":scope > product_pass");
    if (ppEl) {
      doc.product_pass = (ppEl.textContent || "").trim() === "true";
    }
    if (!doc.nodes.length) {
      return blankDesignDoc();
    }
    return doc;
  }

  function sceneDocFromSgsXml(xmlText) {
    const raw = String(xmlText || "").trim();
    if (!raw) return null;
    let docXml;
    try {
      docXml = new DOMParser().parseFromString(raw, "application/xml");
    } catch (_e) {
      return null;
    }
    if (docXml.querySelector("parsererror")) return null;
    const root =
      docXml.querySelector("sgenaxisScene") || docXml.documentElement;
    if (!root || String(root.tagName || "").toLowerCase() !== "sgenaxisscene") {
      return null;
    }
    const metaEl = root.querySelector(":scope > meta");
    const workEl = root.querySelector(":scope > work");
    const archWrap = root.querySelector(":scope > architecture");
    const designEl = root.querySelector(":scope > design");
    const archRoot =
      (archWrap && archWrap.querySelector("sgenaxisArch")) ||
      root.querySelector("sgenaxisArch");
    if (!archRoot) return null;
    const archXml =
      '<?xml version="1.0" encoding="UTF-8"?>\n' +
      new XMLSerializer().serializeToString(archRoot);
    const arch = archDocFromXml(archXml);
    if (!arch) return null;
    return {
      meta: {
        boardFilter: metaEl
          ? archXmlAttr(metaEl, "boardFilter", "overview")
          : "overview",
        savedAt: metaEl ? archXmlAttr(metaEl, "savedAt", "") : "",
      },
      board: boardFromSgsWork(workEl),
      arch: arch,
      design: designFromSgsDesign(designEl),
    };
  }

  function applySceneSgsXml(text, fileName, opts) {
    const quiet = opts && opts.quiet;
    const scene = sceneDocFromSgsXml(text);
    if (!scene) throw new Error("invalid .sgs（需 sgenaxisScene XML）");
    withSceneDirtySuppressed(function () {
      if (scene.meta && scene.meta.boardFilter) {
        boardFilter = scene.meta.boardFilter;
      }
      renderBoard(scene.board || null);
      applyArchDoc(scene.arch, { quiet: true });
      persistArchDraft();
      designDoc = scene.design;
      if (!designDoc.meta) designDoc.meta = {};
      designDirty = false;
      const g =
        designDoc.meta.gridSize != null
          ? Number(designDoc.meta.gridSize)
          : DESIGN_GRID_DEFAULT;
      setDesignGridPx(g, { quiet: true });
      const root = formRootNode();
      if (root && root.props) {
        setDesignFormSize(root.props.w, root.props.h, { quiet: true });
      }
      renderDesignCanvas();
      fillDesignProps();
    });
    if (fileName) sgsPathHint = String(fileName);
    clearSceneDirty();
    if (!quiet) {
      toast("已載入專案場景 .sgs");
      setStatus("場景 XML：已自專案 " + SCENE_SGS_REL + " 載入");
    }
  }

  async function saveSceneSgsToProject(opts) {
    const quiet = opts && opts.quiet;
    requireBoundProjectRoot();
    const xml = sceneDocToSgsXml();
    const dto = await invokeSceneSaveText(SCENE_SGS_REL, xml);
    persistArchDraft();
    clearSceneDirty();
    sgsPathHint = SCENE_SGS_REL;
    if (!quiet) {
      toast("已儲存場景到專案 " + SCENE_SGS_REL);
      setStatus(
        "場景 XML 已寫入專案：" +
          ((dto && dto.path) || SCENE_SGS_REL)
      );
    }
    return dto;
  }

  async function loadSceneSgsFromProject(opts) {
    const quiet = opts && opts.quiet;
    const dto = await invokeSceneLoadText(SCENE_SGS_REL);
    applySceneSgsXml(dto.text, SCENE_SGS_REL, { quiet: quiet });
    return dto;
  }

  async function downloadSceneSgs() {
    try {
      await saveSceneSgsToProject({ quiet: false });
    } catch (err) {
      toast("儲存 .sgs 失敗：" + String(err));
      setStatus("場景 XML 存檔失敗：" + String(err));
    }
  }

  async function openSceneSgsPicker() {
    try {
      await loadSceneSgsFromProject({ quiet: false });
    } catch (err) {
      toast("開啟專案 .sgs 失敗：" + String(err));
      setStatus("場景 XML 載入失敗：" + String(err));
    }
  }

  function wireSceneSgsUi() {
    /* 專案範圍存取：不再使用任意路徑 file picker */
  }

  /** 綁定專案後嘗試載入 scene/default.sgs（無檔則略過）。 */
  async function tryLoadProjectSceneQuiet() {
    if (!invoke || !cachedProjectRoot) return;
    try {
      await loadSceneSgsFromProject({ quiet: true });
      setStatus("已載入專案場景 " + SCENE_SGS_REL);
    } catch (_err) {
      /* 新專案尚無 scene — 保留目前草稿，不視為錯誤 */
    }
  }

  /**
   * PD-REMAIN-FILE-SAVE-01: UI → file_save Command → HostSettings store only.
   * Persists theme／locale／project_root／board_path. Never arbitrary path; never board HTML write-back.
   * Browser／no IPC: NOT RUN.
   */
  async function cmdFileSave() {
    if (!invoke) {
      const msg = "儲存：NOT RUN — 瀏覽器模式無 IPC（需 Tauri file_save）";
      toast(msg);
      setStatus(msg);
      return;
    }
    const boardPath = readBoardPath();
    const projectRoot = readProjectRoot();
    if (isForbiddenDemoRoot(projectRoot)) {
      toast("拒絕：/demo/root");
      setStatus("file.save 拒絕：禁止 /demo/root");
      return;
    }
    if (!isBoardPathAcceptable(boardPath)) {
      toast("拒絕：無效看板路徑");
      setStatus("file.save 拒絕：看板路徑不可為 http／:8788／:8787");
      return;
    }
    try {
      const cur = await invoke("host_get_settings");
      const result = await invoke("file_save", {
        uiTheme: cur.ui_theme || "system",
        locale: cur.locale || "en",
        boardPath: boardPath,
        projectRoot: projectRoot,
      });
      if (result && result.settings) {
        applyProjectBindingFromDto(result.settings);
      }
      const writeBack = result && result.board_write_back === true;
      if (writeBack) {
        toast("儲存異常：不應寫回看板檔");
        setStatus("file_save 契約違反：board_write_back=true");
        return;
      }
      toast("已儲存設定／看板路徑（file_save）");
      setStatus(
        "file_save ok — " +
          ((result && result.persisted_kind) || "host-settings") +
          "；board_write_back=false"
      );
      if ((projectRoot || "").trim()) {
        await onProjectBound(projectRoot.trim());
      }
    } catch (err) {
      const msg = "儲存失敗：" + String(err);
      toast(msg);
      setStatus(msg);
    }
  }

  /**
   * PD-REMAIN-FILE-QUIT-01: UI → host_request_shutdown（Command）→ lifecycle＋app.exit.
   * Browser／no IPC: NOT RUN — cannot close the Tauri shell from a plain page.
   */
  async function cmdFileQuit() {
    if (!invoke) {
      const msg = "結束：NOT RUN — 瀏覽器模式無法關閉殼（需 Tauri Command）";
      toast(msg);
      setStatus(msg);
      return;
    }
    // PD-HOST-01: confirm before app.exit(0).
    if (
      typeof window.confirm === "function" &&
      !window.confirm("結束 SGenAxis？")
    ) {
      toast("已取消結束");
      setStatus("結束：已取消");
      return;
    }
    try {
      setStatus("結束：host_request_shutdown…");
      await invoke("host_request_shutdown");
      // If exit is deferred, surface a readable status (shell should close).
      toast("正在結束…");
      setStatus("結束：已請求關閉");
    } catch (err) {
      const msg = "結束失敗：" + String(err);
      toast(msg);
      setStatus(msg);
    }
  }

  /**
   * PD-WIRE-OPEN-01: UI → host_pick_project_directory → host_set_settings(project_root)
   * → load_local_board／get_board／git_workbench_summary（command 層；無 JS→FS／Git）.
   */
  async function cmdOpenProject() {
    if (!invoke) {
      toast("開啟專案需 Tauri IPC（無法在瀏覽器選本機目錄）");
      setStatus("開啟專案：無 IPC");
      return;
    }
    try {
      const pick = await invoke("host_pick_project_directory");
      await bindPickedProjectRoot(pick, "開啟專案");
    } catch (err) {
      const msg = "開啟專案失敗：" + String(err);
      toast(msg);
      setStatus(msg);
    }
  }

  /**
   * PD-BUG-FILE-NEW-01: UI → prompt name → host_pick_project_directory (parent)
   * → host_create_project_directory → host_set_settings(project_root). No JS→FS.
   * Avoids save_file residue that blocked create_dir_all.
   */
  async function cmdNewProject() {
    if (!invoke) {
      toast("新增專案需 Tauri IPC（瀏覽器模式無法建立本機目錄／NOT RUN）");
      setStatus("新增專案：無 IPC／NOT RUN");
      return;
    }
    try {
      const nameRaw = window.prompt("新專案資料夾名稱", "NewProject");
      if (nameRaw === null) {
        toast("已取消新增專案");
        setStatus("新增專案：已取消（名稱）");
        return;
      }
      const name = String(nameRaw).trim();
      if (!name) {
        toast("新增專案失敗：名稱不可為空");
        setStatus("新增專案失敗：空名稱");
        return;
      }
      setStatus("新增專案：請選擇父資料夾…");
      const parentPick = await invoke("host_pick_project_directory");
      if (!parentPick || parentPick.status === "cancelled") {
        const msg =
          (parentPick && parentPick.message) || "已取消新增專案（父目錄）";
        toast(msg);
        setStatus(msg);
        return;
      }
      if (parentPick.status !== "ok" || !(parentPick.path || "").trim()) {
        const msg =
          (parentPick && parentPick.message) || "新增專案失敗：父目錄無效";
        toast(msg);
        setStatus(msg);
        return;
      }
      const created = await invoke("host_create_project_directory", {
        args: {
          parent: String(parentPick.path).trim(),
          name: name,
        },
      });
      await bindPickedProjectRoot(created, "新增專案");
    } catch (err) {
      const msg = "新增專案失敗：" + String(err);
      toast(msg);
      setStatus(msg);
    }
  }

  /** Shared bind path for open／new after host dialog (+ create for new). */
  async function bindPickedProjectRoot(pick, actionLabel) {
    if (!pick || pick.status === "cancelled") {
      const msg = (pick && pick.message) || "已取消" + actionLabel;
      toast(msg);
      setStatus(msg);
      return;
    }
    if (pick.status !== "ok" || !(pick.path || "").trim()) {
      const msg = (pick && pick.message) || actionLabel + "失敗";
      toast(msg);
      setStatus(msg);
      return;
    }
    const path = String(pick.path).trim();
    if (isForbiddenDemoRoot(path)) {
      toast("拒絕：不可綁定 /demo/root");
      setStatus(actionLabel + "拒絕：/demo/root");
      return;
    }
    const prevRoot = (cachedProjectRoot || "").trim();
    const switching =
      prevRoot &&
      prevRoot.replace(/\\/g, "/").toLowerCase() !==
        path.replace(/\\/g, "/").toLowerCase();
    if (switching || (prevRoot && sceneDirty)) {
      const leave = await confirmLeaveSceneIfDirty();
      if (leave === "abort") {
        toast("已取消" + actionLabel + "（保留目前專案場景）");
        setStatus(actionLabel + "已取消：場景未決");
        return;
      }
    }
    const cur = await invoke("host_get_settings");
    const dto = await invoke("host_set_settings", {
      uiTheme: cur.ui_theme || "system",
      locale: cur.locale || "en",
      boardPath: cur.board_path || null,
      projectRoot: path,
    });
    applyProjectBindingFromDto(dto);
    applySettingsDto(dto);
    toast("已綁定專案：" + path);
    setStatus("host_set_settings project_root ok");
    await onProjectBound(path);
  }

  function applyProjectBindingFromDto(dto) {
    if (!dto) return;
    cachedProjectRoot = (dto.project_root || "").trim();
    cachedBoardPath = (dto.board_path || "").trim();
    cachedAgentActive = !!(
      dto.agent_active || dto.run_mode === "live"
    );
    if (isForbiddenDemoRoot(cachedProjectRoot)) {
      cachedProjectRoot = "";
    }
    updateToolbarBinding(cachedProjectRoot);
    const rootInput = document.getElementById("settings-project-root");
    if (rootInput && dto.project_root != null) {
      rootInput.value = dto.project_root;
    }
  }

  async function refreshProjectBinding() {
    if (!invoke) {
      updateToolbarBinding("");
      return null;
    }
    const dto = await invoke("host_get_settings");
    applyProjectBindingFromDto(dto);
    return dto;
  }

  /** Require bound settings.project_root for start_run／git／board (PD-WIRE-ROOT-01). */
  function requireBoundProjectRoot() {
    const root = (cachedProjectRoot || "").trim();
    if (!root || isForbiddenDemoRoot(root)) {
      throw new Error(unboundProjectMessage());
    }
    return root;
  }

  function toast(message) {
    if (!toastRoot) return;
    const el = document.createElement("div");
    el.className = "toast";
    el.setAttribute("role", "status");
    el.textContent = message;
    toastRoot.appendChild(el);
    window.setTimeout(function () {
      el.classList.add("fade");
      window.setTimeout(function () {
        el.remove();
      }, 280);
    }, 2200);
  }

  function setStatus(message) {
    if (statusMsg) statusMsg.textContent = message;
  }

  function setAgentStatus(text) {
    if (statusAgent) statusAgent.textContent = text;
  }

  function appendLog(line) {
    if (!agentLog) return;
    agentLog.textContent += line + "\n";
    agentLog.scrollTop = agentLog.scrollHeight;
  }

  function clearLog() {
    if (agentLog) agentLog.textContent = "";
  }

  function selectedProvider() {
    const el = document.querySelector('input[name="provider"]:checked');
    return el && el.value === "mcp" ? "mcp" : "cli";
  }

  function safeNum(v) {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  }

  function boardTasks(board) {
    if (!board || !Array.isArray(board.tasks)) return [];
    return board.tasks.filter(function (t) {
      return t && typeof t === "object";
    });
  }

  function filterTasks(tasks, filter) {
    if (!filter || filter === "overview") return tasks.slice();
    if (filter === "accepted") {
      return tasks.filter(function (t) {
        return t.zone === "accepted" || t.accepted === true;
      });
    }
    return tasks.filter(function (t) {
      return t.zone === filter;
    });
  }

  function updateFilterChrome(filter) {
    const title = document.getElementById("board-section-title");
    const label = FILTER_TITLES[filter] || FILTER_TITLES.overview;
    const zoneActive = ZONE_FILTERS.indexOf(filter) !== -1;
    const tasksSec = document.getElementById("sec-tasks-status");
    if (tasksSec) {
      tasksSec.setAttribute("data-zone-active", zoneActive ? "true" : "false");
    }
    if (title) title.textContent = "工項看板 · " + label;
    const emptyTitle = document.getElementById("board-empty-title");
    const emptyBody = document.getElementById("board-empty-body");
    if (emptyTitle) {
      emptyTitle.textContent =
        filter === "overview" ? "尚無工項" : "此燈號尚無工項";
    }
    if (emptyBody) {
      emptyBody.textContent =
        filter === "overview"
          ? "尚無工項，可隨時追加。載入本機看板（board Command）或新增工項；無真資料／無 IPC 不崩潰。"
          : "此燈號尚無工項，可隨時追加。「" +
            label +
            "」無資料。無真資料／無 IPC 不崩潰。";
    }
    const proj = document.getElementById("board-projection");
    if (proj) proj.setAttribute("data-filter", filter || "overview");
    document.querySelectorAll(".status-item[data-filter]").forEach(function (btn) {
      const on = btn.getAttribute("data-filter") === filter;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  function setSidebarCounts(board) {
    const tasks = boardTasks(board);
    const counts = {
      overview: tasks.length,
      gray: safeNum(board && board.gray),
      blue: safeNum(board && board.blue),
      yellow: safeNum(board && board.yellow),
      red: safeNum(board && board.red),
      green: safeNum(board && board.green),
      accepted: tasks.filter(function (t) {
        return t.zone === "accepted" || t.accepted === true;
      }).length,
    };
    if (!board) {
      counts.gray = counts.yellow = counts.red = counts.green = counts.accepted = 0;
      counts.overview = 0;
    } else if (tasks.length && !(board.gray || board.yellow || board.red || board.green)) {
      counts.gray = tasks.filter(function (t) {
        return t.zone === "gray";
      }).length;
      counts.yellow = tasks.filter(function (t) {
        return t.zone === "yellow";
      }).length;
      counts.red = tasks.filter(function (t) {
        return t.zone === "red";
      }).length;
      counts.green = tasks.filter(function (t) {
        return t.zone === "green";
      }).length;
    }
    Object.keys(counts).forEach(function (key) {
      document.querySelectorAll('[data-count-for="' + key + '"]').forEach(function (el) {
        el.textContent = String(counts[key]);
      });
    });
    const meta = document.getElementById("nav-board-meta");
    if (meta) meta.textContent = String(counts.overview);
    const clearBtn = document.getElementById("btn-clear-status-filter");
    if (clearBtn) {
      clearBtn.setAttribute(
        "title",
        "清除篩選（顯示全部工項 · " + counts.overview + "）"
      );
    }
    const setCnt = function (id, n) {
      const el = document.getElementById(id);
      if (el) el.textContent = String(n);
    };
    setCnt("cnt-gray", counts.gray);
    setCnt("cnt-blue", safeNum(board && board.blue));
    setCnt("cnt-yellow", counts.yellow);
    setCnt("cnt-red", counts.red);
    setCnt("cnt-green", counts.green);
  }

  /** Workbench-aligned zone labels for board table status column. */
  var ZONE_STATUS_LABEL = {
    gray: "待辦",
    blue: "藍",
    yellow: "進行中",
    red: "Bug",
    green: "已完成",
    accepted: "已驗收",
  };

  /** Light-set HTML matching Workbench viewTaskBoard (no fake task payload). */
  function boardLightSetHtml(zone) {
    var z = String(zone || "gray").toLowerCase();
    if (z === "accepted") {
      return '<span class="dot dot-accepted status-light" aria-hidden="true"></span>';
    }
    if (z === "green") {
      return '<span class="dot dot-green status-light" aria-hidden="true"></span>';
    }
    var litGray = z === "gray" || z === "blue" ? " lit" : "";
    var litYellow = z === "yellow" ? " lit" : "";
    var litRed = z === "red" ? " lit" : "";
    return (
      '<span class="light-set" aria-hidden="true">' +
      '<span class="dot dot-gray' +
      litGray +
      '"></span>' +
      '<span class="dot dot-yellow' +
      litYellow +
      '"></span>' +
      '<span class="dot dot-red' +
      litRed +
      '"></span>' +
      '<span class="dot dot-green"></span>' +
      "</span>"
    );
  }

  function boardTagCell(tags) {
    if (!tags || !tags.length) {
      return '<span class="time-sub">—</span>';
    }
    return tags
      .map(function (tag) {
        return '<span class="board-tag">' + escapeHtml(String(tag)) + "</span>";
      })
      .join(" ");
  }

  function boardProjectionDash() {
    // Fields not carried by BoardView/TaskView projection — never invent.
    return '<span class="time-sub">—</span>';
  }

  function showBoardError(message) {
    const empty = document.getElementById("board-empty");
    const err = document.getElementById("board-error");
    const counts = document.getElementById("board-counts");
    const list = document.getElementById("board-tasks");
    const viewport = document.getElementById("board-table-viewport");
    if (empty) empty.hidden = true;
    if (counts) counts.hidden = true;
    if (viewport) viewport.hidden = true;
    if (list) list.innerHTML = "";
    if (err) {
      err.hidden = false;
      const body = document.getElementById("board-error-body");
      if (body) body.textContent = message || "無法取得看板投影。";
    }
  }

  function renderBoard(board) {
    try {
      lastBoard = board && typeof board === "object" ? board : null;
      // PD-EXEC-SINGLE-01: projection carries at most one active Run.
      if (
        lastBoard &&
        Object.prototype.hasOwnProperty.call(lastBoard, "active_run_id")
      ) {
        activeRunId =
          lastBoard.active_run_id == null ? null : lastBoard.active_run_id;
        if (btnCancel) btnCancel.disabled = activeRunId == null;
      }
      const empty = document.getElementById("board-empty");
      const err = document.getElementById("board-error");
      const counts = document.getElementById("board-counts");
      const list = document.getElementById("board-tasks");
      const viewport = document.getElementById("board-table-viewport");
      if (err) err.hidden = true;

      const tasks = boardTasks(lastBoard);
      const visible = filterTasks(tasks, boardFilter);
      setSidebarCounts(lastBoard);
      updateFilterChrome(boardFilter);

      if (visible.length === 0) {
        if (empty) empty.hidden = false;
        if (counts) counts.hidden = true;
        if (viewport) viewport.hidden = true;
        if (list) list.innerHTML = "";
        return;
      }
      if (empty) empty.hidden = true;
      if (counts) counts.hidden = boardFilter !== "overview";
      if (viewport) viewport.hidden = false;
      if (list) {
        list.innerHTML = "";
        visible.forEach(function (t) {
          const zone = t.zone || "gray";
          const tid = t.id || "";
          const tr = document.createElement("tr");
          tr.className =
            "board-task zone-" +
            zone +
            (selectedTaskId && tid === selectedTaskId ? " is-selected selected" : "");
          tr.setAttribute("role", "row");
          tr.tabIndex = 0;
          tr.dataset.taskId = tid;
          tr.dataset.status = zone;
          tr.setAttribute(
            "aria-selected",
            selectedTaskId && tid === selectedTaskId ? "true" : "false"
          );
          const statusLabel = ZONE_STATUS_LABEL[zone] || zone;
          tr.innerHTML =
            '<td class="col-lights">' +
            boardLightSetHtml(zone) +
            '</td><td class="col-status">' +
            escapeHtml(statusLabel) +
            '</td><td class="col-title">' +
            '<div class="task-name">' +
            escapeHtml(t.title || tid || "(untitled)") +
            '</div><div class="task-meta"><span>' +
            escapeHtml(tid) +
            "</span></div></td>" +
            '<td class="col-files">' +
            boardProjectionDash() +
            '</td><td class="col-bdd">' +
            boardTagCell(t.bdd) +
            '</td><td class="col-tdd">' +
            boardTagCell(t.tdd) +
            '</td><td class="col-created">' +
            boardProjectionDash() +
            '</td><td class="col-completed">' +
            boardProjectionDash() +
            '</td><td class="col-note">' +
            boardProjectionDash() +
            "</td>";
          tr.addEventListener("click", function () {
            selectWorkItem(tid, t.title || tid);
          });
          tr.addEventListener("keydown", function (ev) {
            if (ev.key === "Enter" || ev.key === " ") {
              ev.preventDefault();
              selectWorkItem(tid, t.title || tid);
            }
          });
          list.appendChild(tr);
        });
      }
      if (selectedTaskId) {
        refreshEvidenceSummary(selectedTaskId);
      }
    } catch (err) {
      showBoardError("渲染失敗（已攔截）：" + String(err));
      toast("看板渲染已攔截錯誤 — 不崩潰");
    }
  }

  function renderEvidenceEmpty(reason) {
    const overall = document.getElementById("evid-overall");
    const lines = document.getElementById("evid-lines");
    const meta = document.getElementById("evid-meta");
    if (overall) overall.textContent = "NOT RUN／未測";
    if (lines) {
      lines.hidden = true;
      lines.innerHTML = "";
    }
    if (meta) {
      meta.textContent =
        reason ||
        "空證據 — NOT RUN／未測。Provider Success 不自動變產品綠燈。";
    }
  }

  function renderEvidenceSummary(dto) {
    const selTitle = document.getElementById("inspector-sel-title");
    const selBody = document.getElementById("inspector-sel-body");
    const overall = document.getElementById("evid-overall");
    const lines = document.getElementById("evid-lines");
    const meta = document.getElementById("evid-meta");
    if (!dto) {
      renderEvidenceEmpty();
      return;
    }
    if (selTitle) {
      selTitle.textContent = dto.title || dto.work_item_id || "工項";
    }
    if (selBody) {
      selBody.textContent =
        "zone=" +
        (dto.zone || "—") +
        " · lamp_hint=" +
        (dto.product_lamp_hint || "—") +
        (dto.ready_for_green ? " · READY_FOR_GREEN" : "");
    }
    if (overall) {
      overall.textContent =
        (dto.overall_status || "NOT RUN") +
        (dto.provider_success_implies_green
          ? " ⚠"
          : " · Provider≠綠");
    }
    if (lines) {
      lines.innerHTML = "";
      const rows = dto.lines || [];
      if (rows.length === 0) {
        lines.hidden = true;
      } else {
        lines.hidden = false;
        rows.forEach(function (row) {
          const li = document.createElement("li");
          li.textContent =
            (row.bdd_id || "?") + " → " + (row.status_label || "NOT RUN");
          lines.appendChild(li);
        });
      }
    }
    if (meta) {
      meta.textContent =
        "provider=" +
        (dto.provider_terminal || "?") +
        " · implies_green=" +
        String(!!dto.provider_success_implies_green) +
        " · " +
        ((dto.gaps && dto.gaps.length
          ? "gaps: " + dto.gaps.join("; ")
          : "無 gap／或空證據"));
    }
  }

  async function refreshEvidenceSummary(workItemId) {
    if (!workItemId) {
      renderEvidenceEmpty("尚未選取工項。");
      return;
    }
    if (!invoke) {
      renderEvidenceEmpty(
        "瀏覽器模式無 IPC — 顯示 NOT RUN／未測（需 tauri dev 讀 evid 投影）。"
      );
      return;
    }
    try {
      const dto = await invoke("get_evidence_summary", {
        args: { work_item_id: workItemId },
      });
      renderEvidenceSummary(dto);
    } catch (err) {
      renderEvidenceEmpty("get_evidence_summary 失敗：" + String(err));
      toast("證據摘要失敗：" + String(err));
    }
  }

  function selectWorkItem(taskId, title) {
    selectedTaskId = taskId || null;
    const selTitle = document.getElementById("inspector-sel-title");
    const selBody = document.getElementById("inspector-sel-body");
    if (selTitle) selTitle.textContent = title || taskId || "工項";
    if (selBody) {
      selBody.textContent = selectedTaskId
        ? "已選取 " + selectedTaskId + " — 載入證據摘要…"
        : "選中工項後顯示詳情與證據摘要。";
    }
    document.querySelectorAll(".board-task").forEach(function (el) {
      const on = el.dataset.taskId === selectedTaskId;
      el.classList.toggle("is-selected", on);
      el.classList.toggle("selected", on);
      el.setAttribute("aria-selected", on ? "true" : "false");
    });
    refreshEvidenceSummary(selectedTaskId);
    setStatus("選取工項 " + (selectedTaskId || "—") + " → 證據摘要");
  }

  function setBoardFilter(filter) {
    boardFilter = FILTER_TITLES[filter] ? filter : "overview";
    renderBoard(lastBoard);
    showPanel("board", { quiet: true });
    setStatus("篩選：" + (FILTER_TITLES[boardFilter] || boardFilter));
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** BDD-PD-UI-RUN-01／CANCEL-01: host ExitClassification → ok｜cancelled｜crashed｜failed. */
  function mapExitClassification(raw) {
    if (raw == null || raw === "") return null;
    const s = String(raw).toLowerCase();
    if (s === "success" || s === "ok") return "ok";
    if (s === "cancelled" || s === "canceled") return "cancelled";
    if (s === "crashed") return "crashed";
    if (s === "failure" || s === "failed") return "failed";
    return "failed";
  }

  function setRunStatusLine(message, isError) {
    const el = document.getElementById("run-status-line");
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("error", !!isError);
  }

  function setRunClassification(kind, detail) {
    const badge = document.getElementById("run-class-badge");
    const panel = document.getElementById("run-panel");
    const stream = document.getElementById("run-stream");
    const k = kind || "idle";
    if (badge) {
      badge.dataset.class = k;
      badge.textContent = "分類：" + k;
      badge.title =
        "結束分類 ok／cancelled／crashed／failed（對帳後租約釋放；≠工項綠燈）";
    }
    if (panel) panel.setAttribute("data-run-state", k);
    if (stream) {
      stream.hidden = k === "idle";
    }
    const meta = document.getElementById("nav-agent-meta");
    if (meta) {
      meta.textContent =
        k === "running" ? "Running" : k === "idle" ? "Idle" : String(k);
    }
    if (detail) {
      setRunStatusLine(detail, k === "failed" || k === "crashed");
    }
  }

  function formatChunk(c) {
    if (!c || !c.kind) return JSON.stringify(c);
    switch (c.kind) {
      case "started":
        return (
          "[started] run=" +
          c.run_id +
          " provider=" +
          c.provider +
          " dry_run=" +
          c.dry_run
        );
      case "chunk":
        return "[" + c.stream + "] " + c.text;
      case "progress":
        return "[progress] " + c.message;
      case "exited": {
        const mapped = mapExitClassification(c.classification) || c.classification;
        return (
          "[exited] " +
          mapped +
          (c.classification && mapped !== c.classification
            ? " (host=" + c.classification + ")"
            : "") +
          (c.exit_code != null ? " code=" + c.exit_code : "")
        );
      }
      case "failed":
        return "[failed] " + (c.message || "（無訊息）");
      default:
        return JSON.stringify(c);
    }
  }

  function sleepMs(ms) {
    return new Promise(function (resolve) {
      window.setTimeout(resolve, ms);
    });
  }

  /** Progressive chunk reveal so DryRun batches still look like a stream. */
  async function appendChunksStreaming(chunks, gen) {
    const list = chunks || [];
    for (let i = 0; i < list.length; i++) {
      if (gen !== runPollGeneration) return null;
      const c = list[i];
      appendLog(formatChunk(c));
      if (c && c.kind === "exited") {
        return mapExitClassification(c.classification) || "failed";
      }
      if (c && c.kind === "failed") {
        setRunStatusLine(
          "Run 失敗：" + (c.message || "未知錯誤（經 poll_chunks，非直呼 CLI／MCP）"),
          true
        );
        return "failed";
      }
      if (list.length > 1) {
        await sleepMs(28);
      }
    }
    return null;
  }

  function setBoardLiveStatus(message, isError) {
    const el = document.getElementById("board-live-status");
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("error", !!isError);
  }

  function boardPathFromInput() {
    const el = document.getElementById("board-path-input");
    const v = el && el.value ? el.value.trim() : "";
    if (v) return v;
    if (cachedBoardPath) return cachedBoardPath;
    return "docs/PROJECT-BOARD.html";
  }

  async function refreshBoard() {
    if (!invoke) {
      renderBoard(null);
      return;
    }
    try {
      const board = await invoke("get_board");
      renderBoard(board);
    } catch (err) {
      showBoardError("get_board 失敗：" + String(err));
      toast("get_board 失敗（已顯示錯誤空態）");
    }
  }

  async function cmdLoadLocalBoard() {
    if (!invoke) {
      showBoardError("瀏覽器模式無 IPC — 請用 tauri dev 載入本機看板（不依賴 :8788）");
      setBoardLiveStatus("無 IPC", true);
      toast("瀏覽器模式：無 IPC（請用 tauri dev）");
      setStatus("board.load — 需 Tauri IPC");
      return;
    }
    let projectRoot;
    try {
      await refreshProjectBinding();
      projectRoot = requireBoundProjectRoot();
    } catch (err) {
      const msg = String(err.message || err);
      showBoardError(msg);
      setBoardLiveStatus(msg, true);
      toast(msg);
      setStatus("load_local_board — unbound");
      return;
    }
    const path = boardPathFromInput();
    const pathEl = document.getElementById("board-path-input");
    if (pathEl && !pathEl.value.trim()) pathEl.value = path;
    setBoardLiveStatus("載入中…", false);
    try {
      const result = await invoke("load_local_board", {
        args: {
          path: path,
          project_root: projectRoot,
          persist_path: true,
        },
      });
      if (result.write_back) {
        showBoardError("契約違規：write_back 必須為 false");
        setBoardLiveStatus("write_back 違規", true);
        return;
      }
      if (result.status === "error") {
        showBoardError(result.message || "載入本機看板失敗");
        setBoardLiveStatus(result.message || "error", true);
        toast("本機看板載入失敗");
        setStatus("load_local_board error");
        return;
      }
      renderBoard(result.board);
      const n = result.board && result.board.tasks ? result.board.tasks.length : 0;
      const msg =
        (result.status === "empty" ? "空板 — " : "已載入 " + n + " 工項 — ") +
        (result.path || path);
      setBoardLiveStatus(msg, false);
      toast(result.status === "empty" ? "本機看板為空" : "已載入本機看板投影");
      setStatus("load_local_board → " + result.status + " write_back=false");
      showPanel("board", { quiet: true });
    } catch (err) {
      showBoardError("load_local_board 失敗：" + String(err));
      setBoardLiveStatus(String(err), true);
      toast("本機看板載入失敗");
    }
  }

  async function cmdUpsertTask() {
    if (!invoke) {
      toast("瀏覽器模式：無 IPC（請用 tauri dev）");
      setStatus("work.new — 需 Tauri IPC");
      return;
    }
    taskSeq += 1;
    const id = "task-" + taskSeq;
    try {
      const board = await invoke("upsert_task", {
        args: {
          id: id,
          title: "工項 " + taskSeq,
          zone: "gray",
        },
      });
      renderBoard(board);
      toast("已新增 " + id);
      setStatus("upsert_task → Core 投影 gen=" + board.generation);
      showPanel("board");
    } catch (err) {
      toast("upsert_task 失敗：" + String(err));
    }
  }

  /**
   * PD-REMAIN-WORK-TAGS-01: UI → batch_work_tags → DispatchHost → board projection.
   * No adapter／OS. Illegal → readable toast. Browser without IPC → NOT RUN.
   */
  function splitTagInput(raw) {
    if (raw == null) return [];
    return String(raw)
      .split(/[,;\n]/)
      .map(function (s) {
        return s.trim();
      })
      .filter(function (s) {
        return s.length > 0;
      });
  }

  async function cmdBatchWorkTags() {
    if (!invoke) {
      toast("批次標籤：尚未實作／NOT RUN（需 Tauri IPC）");
      setStatus("work.tags — NOT RUN（無 IPC）");
      return;
    }
    let ids = selectedTaskId ? [selectedTaskId] : [];
    if (!ids.length) {
      const prompted = window.prompt(
        "工項 id（逗號分隔；或先在看板選取工項）",
        ""
      );
      if (prompted === null) {
        setStatus("work.tags — 已取消");
        return;
      }
      ids = splitTagInput(prompted);
    }
    if (!ids.length) {
      const msg = "非法批次標籤：未指定工項";
      toast(msg);
      setStatus(msg);
      return;
    }
    const bddRaw = window.prompt("BDD 標籤（逗號分隔，可空）", "");
    if (bddRaw === null) {
      setStatus("work.tags — 已取消");
      return;
    }
    const tddRaw = window.prompt("TDD 標籤（逗號分隔，可空）", "");
    if (tddRaw === null) {
      setStatus("work.tags — 已取消");
      return;
    }
    const bdd = splitTagInput(bddRaw);
    const tdd = splitTagInput(tddRaw);
    if (!bdd.length && !tdd.length) {
      const msg = "非法批次標籤：至少需一個 BDD 或 TDD 標籤";
      toast(msg);
      setStatus(msg);
      return;
    }
    try {
      const board = await invoke("batch_work_tags", {
        args: {
          work_item_ids: ids,
          bdd: bdd,
          tdd: tdd,
        },
      });
      renderBoard(board);
      const summary =
        "已標籤 " +
        ids.join(",") +
        (bdd.length ? " BDD=" + bdd.join(",") : "") +
        (tdd.length ? " TDD=" + tdd.join(",") : "");
      toast(summary);
      setStatus("batch_work_tags → board gen=" + (board.generation || "?"));
      showPanel("board", { quiet: true });
      if (selectedTaskId) {
        refreshEvidenceSummary(selectedTaskId);
      }
    } catch (err) {
      const msg = "批次標籤失敗：" + String(err);
      toast(msg);
      setStatus(msg);
    }
  }

  async function finishRunUi(classification, provider, board, detail) {
    activeRunId = null;
    if (btnCancel) btnCancel.disabled = true;
    if (board) renderBoard(board);
    const cls = classification || "failed";
    setRunClassification(
      cls,
      detail ||
        ("結束分類：" +
          cls +
          (cls === "ok" ? " — Provider Success ≠ 產品綠燈" : ""))
    );
    setAgentStatus(
      cls === "ok"
        ? "Agent：就緒（上輪 " + (provider || "?") + " · ok）"
        : cls === "cancelled"
          ? "Agent：已取消"
          : "Agent：失敗"
    );
    setStatus("Run 結束 → " + cls);
    refreshEvidenceSummary(selectedTaskId || lastDispatchedWorkItemId || "dispatch-demo");
  }

  async function pollRunStream(runId, provider, gen) {
    // Headroom so cancel_run can win before the first DryRun drain.
    await sleepMs(40);
    if (gen !== runPollGeneration || activeRunId !== runId) return;

    let terminal = null;
    let lastBoard = null;
    try {
      while (gen === runPollGeneration && activeRunId === runId) {
        const poll = await invoke("poll_chunks", { runId: runId });
        if (gen !== runPollGeneration) return;
        lastBoard = poll.board || lastBoard;
        if (poll.board) renderBoard(poll.board);
        const fromChunks = await appendChunksStreaming(poll.chunks || [], gen);
        if (fromChunks) {
          terminal = fromChunks;
          break;
        }
        await sleepMs(60);
        if (!(poll.chunks && poll.chunks.length)) {
          break;
        }
      }
    } catch (err) {
      const msg = "poll_chunks 失敗：" + String(err);
      appendLog("ERROR " + msg);
      setRunStatusLine(msg, true);
      toast(msg);
      await finishRunUi("failed", provider, lastBoard, msg);
      return;
    }

    if (gen !== runPollGeneration) return;
    if (activeRunId !== runId) return;
    if (!terminal) {
      terminal = "failed";
      setRunStatusLine(
        "未收到 exited／failed chunk — 視為 failed（可讀錯誤）",
        true
      );
    }
    await finishRunUi(terminal, provider, lastBoard, null);
    toast(
      terminal === "ok"
        ? "Run 結束：ok"
        : terminal === "cancelled"
          ? "Run 結束：cancelled"
          : "Run 結束：failed"
    );
  }

  /**
   * PD-WIRE-AGENT-01: Agent 派工 — UI 只選 provider＋settings，經
   * start_run → DispatchHost → EXEC。帶選中 work_item_id（若有）與設定 dry_run｜Live。
   * Live 未核准／路徑無效 → command 可讀拒絕；秘密不進投影；不直呼 adapters。
   */
  async function cmdStartDryRun() {
    if (!invoke) {
      setRunClassification(
        "idle",
        "瀏覽器模式無 IPC — 請用 tauri dev（不直呼 CLI／MCP）"
      );
      toast("瀏覽器模式：無 IPC（請用 tauri dev）");
      setStatus("work.assign — 需 Tauri IPC");
      return;
    }
    let projectRoot;
    let settings;
    try {
      settings = await refreshProjectBinding();
      projectRoot = requireBoundProjectRoot();
    } catch (err) {
      const msg = String(err.message || err);
      appendLog("ERROR " + msg);
      toast(msg);
      setRunClassification("failed", msg);
      setAgentStatus("Agent：未綁定專案根");
      setStatus("start_run — unbound");
      return;
    }
    const provider = selectedProvider();
    const dryRun = !(
      settings &&
      (settings.agent_active || settings.run_mode === "live")
    );
    const workItemId = selectedTaskId || "dispatch-demo";
    lastDispatchedWorkItemId = workItemId;
    const modeLabel = dryRun ? "DryRun" : "Live";
    const fingerprint = "fp:" + String(projectRoot).replace(/\\/g, "/");
    clearLog();
    runPollGeneration += 1;
    const gen = runPollGeneration;
    const stream = document.getElementById("run-stream");
    if (stream) stream.hidden = false;
    appendLog(
      "invoke start_run { provider: " +
        provider +
        ", dry_run: " +
        dryRun +
        ", project_root: " +
        projectRoot +
        ", work_item_id: " +
        workItemId +
        ", worktree_fingerprint } — UI→Command→DispatchHost→EXEC"
    );
    try {
      const result = await invoke("start_run", {
        args: {
          provider: provider,
          dry_run: dryRun,
          work_item_id: workItemId,
          project_root: projectRoot,
          worktree_fingerprint: fingerprint,
        },
      });
      if (gen !== runPollGeneration) return;
      activeRunId = result.run_id;
      if (btnCancel) btnCancel.disabled = false;
      setRunClassification(
        "running",
        "Run #" +
          result.run_id +
          " 串流中（" +
          provider +
          " · " +
          modeLabel +
          " · " +
          workItemId +
          "）"
      );
      setAgentStatus(
        "Agent：" + modeLabel + " " + provider + " #" + result.run_id
      );
      renderBoard(result.board);
      toast(modeLabel + " 已啟動（" + provider + " · " + workItemId + "）");
      setStatus(
        "start_run → DispatchHost→EXEC " + modeLabel + " #" + result.run_id
      );
      pollRunStream(result.run_id, provider, gen);
    } catch (err) {
      const msg = String(err);
      appendLog("ERROR " + msg);
      toast("start_run 失敗：" + msg);
      activeRunId = null;
      if (btnCancel) btnCancel.disabled = true;
      const liveGate =
        msg.indexOf("Live 未核准") >= 0 ||
        msg.indexOf("路徑無效") >= 0 ||
        msg.indexOf("agent_active") >= 0;
      const busy =
        msg.indexOf("lease") >= 0 ||
        msg.indexOf("blind") >= 0 ||
        msg.indexOf("reconcile") >= 0;
      setRunClassification(
        "failed",
        liveGate
          ? "Live 拒絕（可讀）：" + msg
          : busy
            ? "禁盲目重跑：先前 Run 尚未對帳／租約仍在 — " + msg
            : "start_run 失敗（可讀）：" + msg
      );
      setAgentStatus(
        liveGate ? "Agent：Live 已拒絕" : "Agent：錯誤／待對帳"
      );
    }
  }

  async function cmdCancelRun() {
    if (!invoke || activeRunId == null) {
      toast("無進行中的 Run");
      setRunStatusLine("無進行中的 Run 可取消", false);
      return;
    }
    try {
      const runId = activeRunId;
      runPollGeneration += 1;
      const board = await invoke("cancel_run", { runId: runId });
      appendLog("[cancel] invoke cancel_run run=" + runId);
      await finishRunUi(
        "cancelled",
        null,
        board,
        "結束分類：cancelled（經 cancel_run；WORK 租約已釋放；非直呼 CLI／MCP）"
      );
      toast("已取消 Run");
    } catch (err) {
      const msg = "cancel_run 失敗：" + String(err);
      toast(msg);
      setRunStatusLine(msg, true);
    }
  }

  let selectedGitPath = null;
  let gitWritesEnabled = false;
  let pendingGitWrite = null; // { op: "commit"|"push" }

  function gitRepoArg() {
    const el = document.getElementById("git-repo");
    const v = el && el.value ? el.value.trim() : "";
    if (v) return isForbiddenDemoRoot(v) ? null : v;
    const root = (cachedProjectRoot || "").trim();
    return root && !isForbiddenDemoRoot(root) ? root : null;
  }

  function setGitStatusLine(msg, isError) {
    const el = document.getElementById("git-status-line");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("error", !!isError);
  }

  function applyWriteGate(writesEnabled) {
    gitWritesEnabled = !!writesEnabled;
    const gate = document.getElementById("git-write-gate");
    const commit = document.getElementById("git-commit");
    const push = document.getElementById("git-push");
    const on = gitWritesEnabled;
    if (gate) {
      gate.textContent = on ? "寫入：開啟（需核准）" : "寫入：關閉";
      gate.classList.toggle("on", on);
    }
    // PD-GIT-WRITE-UI-01: buttons enabled only when host wires approving GitWritePort.
    [commit, push].forEach(function (btn) {
      if (!btn) return;
      btn.disabled = !on;
      btn.setAttribute("aria-disabled", on ? "false" : "true");
    });
  }

  function hideGitApprove() {
    const box = document.getElementById("git-approve");
    if (box) box.hidden = true;
    pendingGitWrite = null;
  }

  function showGitApprove(op) {
    if (!gitWritesEnabled) {
      toast("寫入閘門關閉");
      return;
    }
    pendingGitWrite = { op: op };
    const box = document.getElementById("git-approve");
    const title = document.getElementById("git-approve-title");
    const lede = document.getElementById("git-approve-lede");
    const msgWrap = document.getElementById("git-approve-msg-wrap");
    const remoteWrap = document.getElementById("git-approve-remote-wrap");
    const refWrap = document.getElementById("git-approve-refspec-wrap");
    if (title) {
      title.textContent = op === "push" ? "審核 Push" : "審核 Commit";
    }
    if (lede) {
      lede.textContent =
        op === "push"
          ? "核准後經 git_write_push → GitWritePort；拒絕則無突變。不做 force push。"
          : "核准後經 git_write_commit → GitWritePort；拒絕則無突變。";
    }
    if (msgWrap) msgWrap.hidden = op !== "commit";
    if (remoteWrap) remoteWrap.hidden = op !== "push";
    if (refWrap) refWrap.hidden = op !== "push";
    if (box) box.hidden = false;
    if (op === "commit") {
      const msg = document.getElementById("git-approve-message");
      if (msg) {
        msg.focus();
        if (!msg.value) msg.value = "";
      }
    } else {
      const remote = document.getElementById("git-approve-remote");
      if (remote && !remote.value.trim()) remote.value = "origin";
      if (remote) remote.focus();
    }
  }

  async function confirmGitApprove() {
    if (!pendingGitWrite || !invoke) {
      hideGitApprove();
      return;
    }
    const op = pendingGitWrite.op;
    const repo = gitRepoArg();
    try {
      if (op === "commit") {
        const msgEl = document.getElementById("git-approve-message");
        const message = msgEl && msgEl.value ? msgEl.value.trim() : "";
        if (!message) {
          setGitStatusLine("Commit message 不可空白", true);
          toast("請填寫 commit message");
          return;
        }
        const dto = await invoke("git_write_commit", {
          args: { repo: repo, message: message, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("commit 成功（經 GitWritePort）", false);
          toast("Commit 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "commit 失敗：" + ((dto && dto.message) || "unknown"),
            true
          );
          toast("Commit 失敗（本機保留）");
        }
      } else if (op === "push") {
        const remoteEl = document.getElementById("git-approve-remote");
        const refEl = document.getElementById("git-approve-refspec");
        const remote = remoteEl && remoteEl.value ? remoteEl.value.trim() : "";
        const refspec =
          refEl && refEl.value && refEl.value.trim() ? refEl.value.trim() : null;
        if (!remote) {
          setGitStatusLine("Remote 不可空白", true);
          toast("請填寫 remote");
          return;
        }
        if (refspec && refspec.charAt(0) === "+") {
          setGitStatusLine("force push 不在範圍內", true);
          toast("禁止 force push");
          return;
        }
        const dto = await invoke("git_write_push", {
          args: {
            repo: repo,
            remote: remote,
            refspec: refspec,
            approved: true,
          },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("push 成功（經 GitWritePort）", false);
          toast("Push 完成");
          await cmdGitRefresh();
        } else {
          const preserved =
            !dto || dto.local_preserved !== false ? "；本機保留" : "";
          setGitStatusLine(
            "push 失敗：" + ((dto && dto.message) || "unknown") + preserved,
            true
          );
          toast("Push 失敗（本機保留）");
        }
      } else {
        hideGitApprove();
      }
    } catch (err) {
      hideGitApprove();
      setGitStatusLine("寫入失敗：" + String(err), true);
      toast("Git 寫入失敗（本機保留）");
    }
  }

  function cancelGitApprove() {
    // Explicit reject: do not invoke write commands → no mutation.
    const op = pendingGitWrite && pendingGitWrite.op;
    hideGitApprove();
    setGitStatusLine(
      (op || "write") + " 已拒絕 — 無突變（未呼叫 GitWritePort）",
      false
    );
    toast("已拒絕寫入");
  }

  function renderGitSummary(dto) {
    const branchEl = document.getElementById("git-branch");
    const countEl = document.getElementById("git-entry-count");
    const list = document.getElementById("git-entries");
    const empty = document.getElementById("git-empty");
    const diffBody = document.getElementById("git-diff-body");
    const diffTitle = document.getElementById("git-diff-title");
    const repoEl = document.getElementById("git-repo");

    if (repoEl && dto.repo && !repoEl.value.trim()) {
      repoEl.value = dto.repo;
    }
    if (branchEl) {
      branchEl.textContent = "分支：" + (dto.branch || "（分離 HEAD／未知）");
    }
    applyWriteGate(!!dto.writes_enabled);
    if (countEl) countEl.textContent = String(dto.entry_count || 0);

    const entries = dto.entries || [];
    if (list) {
      list.innerHTML = "";
      if (entries.length === 0) {
        list.hidden = true;
        if (empty) empty.hidden = false;
      } else {
        list.hidden = false;
        if (empty) empty.hidden = true;
        entries.forEach(function (e) {
          const li = document.createElement("li");
          li.className = "git-entry kind-" + (e.kind || "other");
          li.setAttribute("role", "button");
          li.tabIndex = 0;
          li.dataset.path = e.path;
          li.innerHTML =
            '<span class="kind">' +
            escapeHtml(e.kind || "?") +
            '</span><span class="path">' +
            escapeHtml(e.path) +
            "</span>";
          const select = function () {
            selectedGitPath = e.path;
            list.querySelectorAll(".git-entry").forEach(function (n) {
              n.classList.toggle("selected", n === li);
            });
            cmdGitDiff(e.path);
          };
          li.addEventListener("click", select);
          li.addEventListener("keydown", function (ev) {
            if (ev.key === "Enter" || ev.key === " ") {
              ev.preventDefault();
              select();
            }
          });
          list.appendChild(li);
        });
      }
    }

    selectedGitPath = null;
    if (diffTitle) diffTitle.textContent = "Diff（全部）";
    if (diffBody) {
      diffBody.textContent = dto.diff_text || "（無 diff）";
    }
    setGitStatusLine(
      "投影 " +
        (dto.repo || "") +
        " · " +
        (dto.entry_count || 0) +
        " 變更 · writes_enabled=" +
        (!!dto.writes_enabled),
      false
    );
  }

  function renderGitNotRun(message) {
    const empty = document.getElementById("git-empty");
    const list = document.getElementById("git-entries");
    const branchEl = document.getElementById("git-branch");
    const countEl = document.getElementById("git-entry-count");
    const diffBody = document.getElementById("git-diff-body");
    const diffTitle = document.getElementById("git-diff-title");
    if (list) {
      list.innerHTML = "";
      list.hidden = true;
    }
    if (empty) {
      empty.hidden = false;
      const strong = empty.querySelector("strong");
      const p = empty.querySelector("p");
      if (strong) strong.textContent = "NOT RUN／未載入";
      if (p) {
        p.textContent =
          message ||
          "非 git／缺檔／未綁定 — 可讀空態，不崩潰。經 git_workbench_summary（無 JS 直呼 git）。";
      }
    }
    if (branchEl) branchEl.textContent = "分支：NOT RUN";
    if (countEl) countEl.textContent = "0";
    if (diffTitle) diffTitle.textContent = "Diff（NOT RUN）";
    if (diffBody) diffBody.textContent = "（NOT RUN）";
    applyWriteGate(false);
    setGitStatusLine(message || "git_workbench_summary → NOT RUN", false);
  }

  async function cmdGitRefresh() {
    if (!invoke) {
      renderGitNotRun("瀏覽器模式：無 IPC → Git NOT RUN");
      toast("Git 投影需 Tauri IPC");
      return;
    }
    try {
      await refreshProjectBinding();
    } catch (_e) {
      /* host soft-fails unbound via status=not_run */
    }
    try {
      const dto = await invoke("git_workbench_summary", {
        repo: gitRepoArg(),
        logLimit: 12,
      });
      if (dto && (dto.status === "not_run" || dto.status === "error")) {
        renderGitNotRun(dto.message || "NOT RUN");
        toast("Git 投影 NOT RUN（可讀空態）");
        setStatus("git_workbench_summary → NOT RUN");
        return;
      }
      renderGitSummary(dto);
      toast("Git 投影已更新");
      setStatus("git_workbench_summary → 唯讀投影");
    } catch (err) {
      renderGitNotRun("git_workbench_summary 失敗：" + String(err));
      toast("Git 投影 NOT RUN（已攔截）");
    }
  }

  /**
   * PD-WIRE-BOOT-01 — boot／bind 自動載入。
   * ONLY via existing Tauri commands → host／DispatchHost projections；no JS file／git.
   */
  async function wireBootLoadProjections(opts) {
    opts = opts || {};
    const reason = opts.reason || "boot";
    const quiet = opts.quiet !== false;
    if (!invoke) {
      showBoardError("無 IPC — 看板空態（需 tauri dev）");
      renderGitNotRun("無 IPC → Git NOT RUN");
      setStatus("wire-boot — 需 Tauri（空態／NOT RUN）");
      return;
    }
    try {
      await refreshProjectBinding();
    } catch (_e) {
      /* continue — commands return readable empty／not_run */
    }

    try {
      const path = boardPathFromInput();
      const pathEl = document.getElementById("board-path-input");
      if (pathEl && !pathEl.value.trim()) pathEl.value = path;
      const args = { path: path, persist_path: false };
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      setBoardLiveStatus("boot 載入看板…", false);
      const result = await invoke("load_local_board", { args: args });
      if (result.write_back) {
        showBoardError("契約違規：write_back 必須為 false");
        setBoardLiveStatus("write_back 違規", true);
      } else if (result.status === "error") {
        if (result.board) renderBoard(result.board);
        else renderBoard(null);
        showBoardError(result.message || "看板載入失敗（可讀空態）");
        setBoardLiveStatus(result.message || "error", true);
      } else {
        renderBoard(result.board);
        const n =
          result.board && result.board.tasks ? result.board.tasks.length : 0;
        setBoardLiveStatus(
          (result.status === "empty" ? "空板 — " : "已載入 " + n + " 工項 — ") +
            (result.path || path || ""),
          false
        );
      }
    } catch (err) {
      renderBoard(null);
      showBoardError("load_local_board 失敗：" + String(err));
      setBoardLiveStatus(String(err), true);
    }

    try {
      const dto = await invoke("git_workbench_summary", {
        repo: gitRepoArg(),
        logLimit: 12,
      });
      if (dto && (dto.status === "not_run" || dto.status === "error")) {
        renderGitNotRun(dto.message || "NOT RUN");
      } else {
        renderGitSummary(dto);
      }
    } catch (err) {
      renderGitNotRun("git_workbench_summary 失敗：" + String(err));
    }

    setStatus(
      "wire-boot (" +
        reason +
        ") → load_local_board＋git_workbench_summary（command only）"
    );
    if (!quiet) toast("已自動載入看板＋Git 投影");
  }

  /** Bind seam for OPEN／settings — then auto-load board＋git＋project scene. */
  async function onProjectBound(root) {
    const trimmed = (root || "").trim();
    if (trimmed && !isForbiddenDemoRoot(trimmed)) {
      cachedProjectRoot = trimmed;
      updateToolbarBinding(cachedProjectRoot);
      const repoEl = document.getElementById("git-repo");
      if (repoEl && !repoEl.value.trim()) repoEl.value = cachedProjectRoot;
      const statusEl = document.getElementById("status-project");
      if (statusEl) statusEl.textContent = "專案：" + cachedProjectRoot;
    } else {
      updateToolbarBinding(cachedProjectRoot || "");
    }
    await wireBootLoadProjections({ reason: "bind", quiet: false });
    await tryLoadProjectSceneQuiet();
  }

  async function cmdGitDiff(pathspec) {
    if (!invoke) return;
    const diffBody = document.getElementById("git-diff-body");
    const diffTitle = document.getElementById("git-diff-title");
    try {
      await refreshProjectBinding();
      requireBoundProjectRoot();
    } catch (err) {
      setGitStatusLine(String(err.message || err), true);
      return;
    }
    try {
      const dto = await invoke("git_workbench_diff", {
        repo: gitRepoArg(),
        pathspec: pathspec || null,
      });
      if (diffTitle) {
        diffTitle.textContent = pathspec
          ? "Diff：" + pathspec
          : "Diff（全部）";
      }
      if (diffBody) {
        diffBody.textContent = dto.diff_text || "（無 diff）";
      }
      setGitStatusLine(
        "diff " + (pathspec || "（全部）") + " via git_workbench_diff",
        false
      );
    } catch (err) {
      setGitStatusLine("git_workbench_diff 失敗：" + String(err), true);
    }
  }

  // —— PD-DEPLOY-UI-01：佈版／部署面板（invoke deploy_*；不直呼 OS）——

  function setDeployStatusLine(msg, isError) {
    const el = document.getElementById("deploy-status-line");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("error", !!isError);
  }

  function setNavDeployMeta(text) {
    const el = document.getElementById("nav-deploy-meta");
    if (el) el.textContent = text || "—";
  }

  function setDeploySupportBadge(text, kind) {
    const el = document.getElementById("deploy-support-badge");
    if (!el) return;
    el.textContent = text || "狀態：—";
    el.classList.remove("ok", "warn", "bad");
    if (kind) el.classList.add(kind);
  }

  function isDeployCmdMissingOrUnsupported(err) {
    const s = String(err || "").toLowerCase();
    return (
      s.indexOf("unsupported") !== -1 ||
      s.indexOf("not supported") !== -1 ||
      s.indexOf("command deploy_") !== -1 ||
      s.indexOf("unknown command") !== -1 ||
      s.indexOf("not found") !== -1 ||
      s.indexOf("does not exist") !== -1 ||
      s.indexOf("no such command") !== -1 ||
      s.indexOf("command not found") !== -1
    );
  }

  function normalizeCapabilities(raw) {
    if (!raw) return [];
    if (!Array.isArray(raw)) return [];
    return raw.map(function (c, i) {
      if (typeof c === "string") {
        return { id: c, label: c, available: true };
      }
      const id = c.id || c.name || c.key || "cap-" + i;
      const label = c.label || c.name || c.id || id;
      const available = c.available !== false && c.supported !== false;
      return { id: String(id), label: String(label), available: !!available };
    });
  }

  function normalizeArtifacts(raw) {
    if (!raw) return [];
    const list = Array.isArray(raw)
      ? raw
      : Array.isArray(raw.artifacts)
        ? raw.artifacts
        : [];
    return list.map(function (a, i) {
      if (typeof a === "string") {
        return { path: a, kind: "artifact", verified: false };
      }
      return {
        path: String(a.path || a.uri || a.name || "artifact-" + i),
        kind: String(a.kind || a.type || "artifact"),
        verified: !!(a.verified || a.ok),
        note: a.note || a.message || "",
      };
    });
  }

  function showDeployUnsupported(title, body, statusMsg) {
    const empty = document.getElementById("deploy-empty");
    const layout = document.getElementById("deploy-layout");
    const titleEl = document.getElementById("deploy-empty-title");
    const bodyEl = document.getElementById("deploy-empty-body");
    if (layout) layout.hidden = true;
    if (empty) {
      empty.hidden = false;
      empty.setAttribute("data-deploy-state", "unsupported");
    }
    if (titleEl) titleEl.textContent = title || "部署適配器未支援";
    if (bodyEl) {
      bodyEl.textContent =
        body ||
        "未接 Adapter 或 deploy_* command 未就緒。檢查走 command，不直呼 OS。";
    }
    setDeploySupportBadge("狀態：未支援", "warn");
    setNavDeployMeta("未支援");
    setDeployStatusLine(statusMsg || "deploy：unsupported", true);
  }

  function showDeployProjection() {
    const empty = document.getElementById("deploy-empty");
    const layout = document.getElementById("deploy-layout");
    if (empty) {
      empty.hidden = true;
      empty.setAttribute("data-deploy-state", "ready");
    }
    if (layout) layout.hidden = false;
  }

  function renderDeployCapabilities(caps) {
    const list = document.getElementById("deploy-capabilities");
    const empty = document.getElementById("deploy-cap-empty");
    const countEl = document.getElementById("deploy-cap-count");
    if (countEl) countEl.textContent = String(caps.length);
    if (!list) return;
    list.innerHTML = "";
    if (caps.length === 0) {
      list.hidden = true;
      if (empty) empty.hidden = false;
      return;
    }
    list.hidden = false;
    if (empty) empty.hidden = true;
    caps.forEach(function (c) {
      const li = document.createElement("li");
      li.className =
        "deploy-cap-item" + (c.available ? "" : " unavailable");
      li.innerHTML =
        '<span class="cap-label">' +
        escapeHtml(c.label) +
        '</span><span class="cap-flag">' +
        escapeHtml(c.available ? "可用" : "不可用") +
        "</span>";
      list.appendChild(li);
    });
  }

  function renderDeployArtifacts(arts) {
    const list = document.getElementById("deploy-artifacts");
    const empty = document.getElementById("deploy-art-empty");
    const countEl = document.getElementById("deploy-art-count");
    if (countEl) countEl.textContent = String(arts.length);
    if (!list) return;
    list.innerHTML = "";
    if (arts.length === 0) {
      list.hidden = true;
      if (empty) empty.hidden = false;
      return;
    }
    list.hidden = false;
    if (empty) empty.hidden = true;
    arts.forEach(function (a) {
      const li = document.createElement("li");
      li.className =
        "deploy-art-item" + (a.verified ? " verified" : "");
      li.innerHTML =
        '<span class="kind">' +
        escapeHtml(a.kind) +
        '</span><span class="path" title="' +
        escapeHtml(a.path) +
        '">' +
        escapeHtml(a.path) +
        '</span><span class="flag">' +
        escapeHtml(a.verified ? "已驗證" : "未驗證") +
        "</span>";
      list.appendChild(li);
    });
  }

  function applyDeployStatusDto(dto) {
    if (!dto || typeof dto !== "object") {
      showDeployUnsupported(
        "無狀態投影",
        "deploy_status 回傳空白。未接 Adapter 時視為未支援。",
        "deploy_status：empty"
      );
      return false;
    }
    const supported =
      dto.supported !== false &&
      String(dto.status || "").toLowerCase() !== "unsupported";
    if (!supported) {
      showDeployUnsupported(
        "部署適配器未支援",
        dto.message ||
          dto.unsupported_reason ||
          "平台／Adapter 回報 Unsupported。",
        "deploy_status：unsupported"
      );
      return false;
    }
    showDeployProjection();
    const caps = normalizeCapabilities(dto.capabilities || dto.caps);
    renderDeployCapabilities(caps);
    const statusLabel = dto.status || "就緒";
    setDeploySupportBadge("狀態：" + statusLabel, "ok");
    setNavDeployMeta(String(statusLabel).slice(0, 12));
    if (dto.last_artifact || dto.last_artifact_path) {
      setDeployStatusLine(
        "deploy_status · last=" +
          (dto.last_artifact || dto.last_artifact_path),
        false
      );
    } else {
      setDeployStatusLine(
        "deploy_status · " +
          (dto.platform ? dto.platform + " · " : "") +
          caps.length +
          " 能力",
        false
      );
    }
    return true;
  }

  async function cmdDeployRefresh() {
    if (!invoke) {
      showDeployUnsupported(
        "無 IPC（瀏覽器模式）",
        "請以 tauri dev／桌面殼載入；佈版投影需 invoke deploy_status／list_artifacts。",
        "瀏覽器模式：無 deploy IPC"
      );
      toast("佈版投影需 Tauri IPC");
      return;
    }
    setDeployStatusLine("載入 deploy_status…", false);
    try {
      const statusDto = await invoke("deploy_status");
      const ok = applyDeployStatusDto(statusDto);
      if (!ok) {
        toast("佈版：未支援");
        return;
      }
      try {
        const artDto = await invoke("list_artifacts");
        renderDeployArtifacts(normalizeArtifacts(artDto));
      } catch (artErr) {
        if (isDeployCmdMissingOrUnsupported(artErr)) {
          renderDeployArtifacts([]);
          setDeployStatusLine(
            "list_artifacts 未就緒／未支援：" + String(artErr),
            true
          );
        } else {
          renderDeployArtifacts([]);
          setDeployStatusLine(
            "list_artifacts 失敗：" + String(artErr),
            true
          );
        }
      }
      toast("佈版投影已更新");
      setStatus("deploy_status／list_artifacts → 投影");
    } catch (err) {
      if (isDeployCmdMissingOrUnsupported(err)) {
        showDeployUnsupported(
          "部署適配器未支援",
          "deploy_status 不可用（command 未就緒或 Adapter 未接）。檢查仍走 deploy_check command。",
          "deploy_status：" + String(err)
        );
        toast("佈版：未支援／command 未就緒");
      } else {
        showDeployUnsupported(
          "部署狀態載入失敗",
          "deploy_status 錯誤（非直呼 OS）：" + String(err),
          "deploy_status 失敗：" + String(err)
        );
        toast("佈版投影失敗");
      }
    }
  }

  async function cmdDeployCheck() {
    if (!invoke) {
      showDeployUnsupported(
        "無 IPC（瀏覽器模式）",
        "檢查按鈕需 Tauri invoke deploy_check；瀏覽器模式不下發 OS。",
        "deploy_check：無 IPC"
      );
      toast("deploy_check 需 Tauri IPC");
      setStatus("deploy_check（無 IPC）");
      return;
    }
    setDeployStatusLine("執行 deploy_check…", false);
    setStatus("invoke deploy_check");
    try {
      const dto = await invoke("deploy_check");
      const supported =
        !dto ||
        (dto.supported !== false &&
          String(dto.status || "").toLowerCase() !== "unsupported");
      if (!supported) {
        showDeployUnsupported(
          "檢查結果：未支援",
          (dto && (dto.message || dto.unsupported_reason)) ||
            "deploy_check 回報 Unsupported。",
          "deploy_check：unsupported"
        );
        toast("deploy_check：未支援");
        return;
      }
      const ok = !dto || dto.ok !== false;
      const msg =
        (dto && (dto.message || dto.summary)) ||
        (ok ? "檢查通過" : "檢查未通過");
      if (dto && dto.capabilities) {
        showDeployProjection();
        renderDeployCapabilities(normalizeCapabilities(dto.capabilities));
      }
      setDeploySupportBadge(
        "狀態：" + (ok ? "檢查通過" : "檢查異常"),
        ok ? "ok" : "bad"
      );
      setNavDeployMeta(ok ? "檢查通過" : "檢查異常");
      setDeployStatusLine("deploy_check → " + msg, !ok);
      toast(ok ? "deploy_check：通過" : "deploy_check：異常");
      // Refresh full projection after check when status command exists
      cmdDeployRefresh();
    } catch (err) {
      if (isDeployCmdMissingOrUnsupported(err)) {
        showDeployUnsupported(
          "部署適配器未支援",
          "deploy_check 不可用（command 未就緒或 Adapter 未接）。未直呼 OS。",
          "deploy_check：" + String(err)
        );
        toast("deploy_check：未支援／未就緒");
      } else {
        setDeployStatusLine("deploy_check 失敗：" + String(err), true);
        toast("deploy_check 失敗");
      }
    }
  }

  function setSpecStatus(message, isError) {
    const el = document.getElementById("spec-status-line");
    if (!el) return;
    el.textContent = message || "";
    el.classList.toggle("error", !!isError);
  }

  function setNavSpecMeta(text) {
    const el = document.getElementById("nav-spec-meta");
    if (el) el.textContent = text || "—";
  }

  function setSpecLockBadge(text, locked) {
    const el = document.getElementById("spec-lock-badge");
    if (!el) return;
    el.textContent = text || "鎖：—";
    el.classList.toggle("locked", !!locked);
  }

  function showSpecEmpty() {
    const empty = document.getElementById("spec-empty");
    const layout = document.getElementById("spec-layout");
    if (empty) empty.hidden = false;
    if (layout) layout.hidden = true;
    const approve = document.getElementById("spec-approve");
    if (approve) approve.disabled = true;
    setSpecLockBadge("鎖：—", false);
    setNavSpecMeta("—");
  }

  function showSpecLayout() {
    const empty = document.getElementById("spec-empty");
    const layout = document.getElementById("spec-layout");
    if (empty) empty.hidden = true;
    if (layout) layout.hidden = false;
  }

  function renderSpecProjection(proj) {
    lastSpecProj = proj || null;
    if (!proj || !proj.loaded) {
      showSpecEmpty();
      setSpecStatus("尚未載入 Spec 投影");
      return;
    }
    showSpecLayout();
    const revs = Array.isArray(proj.revisions) ? proj.revisions : [];
    const revCount = document.getElementById("spec-rev-count");
    if (revCount) revCount.textContent = String(revs.length);
    const list = document.getElementById("spec-revisions");
    const revEmpty = document.getElementById("spec-rev-empty");
    if (list) {
      list.innerHTML = "";
      if (revs.length === 0) {
        list.hidden = true;
        if (revEmpty) revEmpty.hidden = false;
      } else {
        list.hidden = false;
        if (revEmpty) revEmpty.hidden = true;
        if (
          !selectedSpecRevisionId ||
          !revs.some(function (r) {
            return r.id === selectedSpecRevisionId;
          })
        ) {
          selectedSpecRevisionId = revs[0].id;
        }
        revs.forEach(function (r) {
          const li = document.createElement("li");
          li.className =
            "spec-rev-item" +
            (r.id === selectedSpecRevisionId ? " is-selected" : "");
          li.setAttribute("role", "option");
          li.setAttribute(
            "aria-selected",
            r.id === selectedSpecRevisionId ? "true" : "false"
          );
          li.dataset.revisionId = r.id;
          li.innerHTML =
            "<span class=\"rev-id\">" +
            escapeHtml(r.version_label || r.id) +
            "</span>" +
            "<span class=\"rev-status\">" +
            escapeHtml(r.status || "") +
            "</span>" +
            "<span class=\"rev-meta\">" +
            String(r.contract_count || 0) +
            " 契約</span>";
          li.addEventListener("click", function () {
            selectedSpecRevisionId = r.id;
            renderSpecProjection(lastSpecProj);
            cmdSpecSelectRevision(r.id);
          });
          list.appendChild(li);
        });
      }
    }
    const meta = document.getElementById("spec-module-meta");
    if (meta) {
      meta.hidden = false;
      meta.textContent =
        (proj.module_id || "") +
        " · " +
        (proj.module_name || "") +
        " — " +
        (proj.responsibility || "");
    }
    const evidN = proj.evidence_needing_revalidation || 0;
    setNavSpecMeta(
      (proj.module_id || "SPEC") + (evidN ? " · 待重驗 " + evidN : "")
    );
    const approve = document.getElementById("spec-approve");
    if (approve) {
      const sel = revs.find(function (r) {
        return r.id === selectedSpecRevisionId;
      });
      approve.disabled = !sel || sel.status === "approved";
    }
    if (selectedSpecRevisionId) {
      cmdSpecSelectRevision(selectedSpecRevisionId);
    }
    setSpecStatus(
      "投影：" +
        (proj.module_id || "") +
        " · " +
        revs.length +
        " 修訂" +
        (evidN ? " · 證據待重驗 " + evidN : "")
    );
  }

  function renderSpecRevision(rev) {
    lastSpecRevision = rev || null;
    const title = document.getElementById("spec-detail-title");
    const list = document.getElementById("spec-contracts");
    const empty = document.getElementById("spec-contract-empty");
    const mutateBar = document.getElementById("spec-mutate-bar");
    const reviseBox = document.getElementById("spec-revise-box");
    if (!rev) {
      if (title) title.textContent = "契約";
      if (list) {
        list.innerHTML = "";
        list.hidden = true;
      }
      if (empty) empty.hidden = false;
      if (mutateBar) mutateBar.hidden = true;
      if (reviseBox) reviseBox.hidden = true;
      setSpecLockBadge("鎖：—", false);
      return;
    }
    if (title) {
      title.textContent =
        "契約 · " + (rev.version_label || rev.id) + "（" + rev.status + "）";
    }
    const contracts = Array.isArray(rev.contracts) ? rev.contracts : [];
    if (list) {
      list.innerHTML = "";
      if (contracts.length === 0) {
        list.hidden = true;
        if (empty) empty.hidden = false;
      } else {
        list.hidden = false;
        if (empty) empty.hidden = true;
        contracts.forEach(function (c) {
          const li = document.createElement("li");
          li.className = "spec-contract-item";
          li.dataset.contractId = c.id;
          li.innerHTML =
            "<b>" +
            escapeHtml(c.id) +
            "</b> " +
            escapeHtml(c.title || "") +
            "<pre class=\"spec-contract-body\" tabindex=\"0\">" +
            escapeHtml(c.body || "") +
            "</pre>";
          list.appendChild(li);
        });
      }
    }
    const locked = !!rev.immutable || rev.status === "approved";
    setSpecLockBadge(locked ? "鎖：核准（不可原地改）" : "鎖：草稿可改", locked);
    if (mutateBar) mutateBar.hidden = false;
    if (reviseBox) reviseBox.hidden = !locked;
    const approve = document.getElementById("spec-approve");
    if (approve) approve.disabled = locked;
  }

  async function cmdSpecLoad() {
    if (!invoke) {
      showSpecEmpty();
      setSpecStatus("瀏覽器模式：無 IPC；無法載入 Spec（不崩潰）", true);
      toast("無 IPC — Spec 未載入");
      return;
    }
    try {
      const proj = await invoke("spec_load_fixture");
      selectedSpecRevisionId = null;
      renderSpecProjection(proj);
      toast("已載入 ModuleSpec 投影");
    } catch (err) {
      showSpecEmpty();
      setSpecStatus("spec_load_fixture 失敗：" + String(err), true);
      toast("載入 Spec 失敗");
    }
  }

  async function cmdSpecRefresh() {
    if (!invoke) {
      setSpecStatus("瀏覽器模式：無 IPC", true);
      return;
    }
    try {
      const proj = await invoke("spec_get_projection");
      renderSpecProjection(proj);
      toast("Spec 投影已更新");
    } catch (err) {
      setSpecStatus("spec_get_projection 失敗：" + String(err), true);
      toast("Spec 投影失敗");
    }
  }

  async function cmdSpecSelectRevision(revisionId) {
    if (!invoke || !revisionId) return;
    try {
      const rev = await invoke("spec_get_revision", {
        args: { revision_id: revisionId },
      });
      renderSpecRevision(rev);
    } catch (err) {
      renderSpecRevision(null);
      setSpecStatus("spec_get_revision 失敗：" + String(err), true);
    }
  }

  async function cmdSpecApprove() {
    if (!invoke) {
      toast("無 IPC");
      return;
    }
    if (!selectedSpecRevisionId) {
      toast("尚未選取修訂");
      return;
    }
    try {
      const rev = await invoke("spec_approve", {
        args: { revision_id: selectedSpecRevisionId },
      });
      renderSpecRevision(rev);
      await cmdSpecRefresh();
      toast("已核准 " + rev.id + "（不可原地改）");
    } catch (err) {
      setSpecStatus("spec_approve 失敗：" + String(err), true);
      toast("核准失敗：" + String(err));
    }
  }

  async function cmdSpecTryEdit() {
    if (!invoke) {
      toast("無 IPC");
      return;
    }
    if (!selectedSpecRevisionId || !lastSpecRevision) {
      toast("尚未選取修訂");
      return;
    }
    const contracts = lastSpecRevision.contracts || [];
    if (!contracts.length) {
      toast("無契約可改");
      return;
    }
    const bodyEl = document.getElementById("spec-try-body");
    const newBody =
      (bodyEl && bodyEl.value.trim()) || "UI 嘗試原地竄改（應被拒）";
    try {
      const rev = await invoke("spec_try_set_contract", {
        args: {
          revision_id: selectedSpecRevisionId,
          contract_id: contracts[0].id,
          new_body: newBody,
        },
      });
      renderSpecRevision(rev);
      setSpecStatus("草稿已原地更新（未核准）");
      toast("草稿契約已更新");
    } catch (err) {
      const msg = String(err);
      const isReplan = msg.indexOf("REPLAN_REQUIRED") !== -1;
      setSpecStatus(
        isReplan
          ? "拒：核准版不可原地改 → " + msg
          : "spec_try_set_contract 失敗：" + msg,
        true
      );
      toast(isReplan ? "REPLAN_REQUIRED（原地改已拒）" : "原地改失敗");
    }
  }

  async function cmdSpecRevise() {
    if (!invoke) {
      toast("無 IPC");
      return;
    }
    if (!selectedSpecRevisionId) {
      toast("尚未選取基線修訂");
      return;
    }
    const idEl = document.getElementById("spec-revise-id");
    const labelEl = document.getElementById("spec-revise-label");
    const bodyEl = document.getElementById("spec-revise-body");
    const newId = (idEl && idEl.value.trim()) || "rev-v2";
    const newLabel = (labelEl && labelEl.value.trim()) || "v2";
    const bodyOverride = bodyEl && bodyEl.value.trim();
    const contracts = [];
    if (bodyOverride && lastSpecRevision && lastSpecRevision.contracts) {
      lastSpecRevision.contracts.forEach(function (c, i) {
        contracts.push({
          id: c.id,
          title: c.title,
          body: i === 0 ? bodyOverride : c.body,
        });
      });
    }
    try {
      const rev = await invoke("spec_revise", {
        args: {
          from_revision_id: selectedSpecRevisionId,
          new_revision_id: newId,
          new_version_label: newLabel,
          contracts: contracts,
        },
      });
      selectedSpecRevisionId = rev.id;
      await cmdSpecRefresh();
      toast("已建立新修訂 " + rev.id + "（另入口）");
      setSpecStatus("revise 另入口成功 → " + rev.id);
    } catch (err) {
      setSpecStatus("spec_revise 失敗：" + String(err), true);
      toast("修訂失敗：" + String(err));
    }
  }

  // —— PD-REMAIN-ARCH-UI-01 + Arch DAG shell：草稿畫布常駐；live 僅 Command ——

  /**
   * SSOT：docs/節點類型定義整理.pdf（01–10 Node Type）
   * ＋ docs/架構定義與整合-Layer Node.pdf：
   * Layer（packsKind）→ Module Slot（獨立展開／收合）→ Node（橫式，左 I／右 O）。
   * Layer↔Layer 只留一條線；展開／收合不刪 Node、不改資料關係。
   */
  const ARCH_NODE_KINDS = [
    "API",
    "Contract",
    "UI",
    "Command",
    "Query",
    "Application",
    "Domain",
    "Infrastructure",
    "ACL",
    "Custom",
    "WorkItem",
    "Deployment",
    "Layer",
  ];
  const ARCH_PACKABLE_KINDS = ARCH_NODE_KINDS.filter(function (k) {
    return k !== "Layer";
  });
  /** 圖示來源：D:\\AIAD\\icon → 打包於 ui/icons/arch/{Kind}.svg */
  const ARCH_KIND_ICON_BASE = "icons/arch/";
  const ARCH_KIND_ICONS = {
    API: ARCH_KIND_ICON_BASE + "API.svg",
    Contract: ARCH_KIND_ICON_BASE + "Contract.svg",
    UI: ARCH_KIND_ICON_BASE + "UI.svg",
    Command: ARCH_KIND_ICON_BASE + "Command.svg",
    Query: ARCH_KIND_ICON_BASE + "Query.svg",
    Application: ARCH_KIND_ICON_BASE + "Application.svg",
    Domain: ARCH_KIND_ICON_BASE + "Domain.svg",
    Infrastructure: ARCH_KIND_ICON_BASE + "Infrastructure.svg",
    ACL: ARCH_KIND_ICON_BASE + "ACL.svg",
    Custom: ARCH_KIND_ICON_BASE + "Custom.svg",
    WorkItem: ARCH_KIND_ICON_BASE + "WorkItem.svg",
    Deployment: ARCH_KIND_ICON_BASE + "Deployment.svg",
    Layer: ARCH_KIND_ICON_BASE + "Layer.svg",
  };
  /** Tasks Node.html：workflow／test 與 displayLamp 分開 */
  const WORKITEM_WORKFLOW_STATUSES = [
    "NotStarted",
    "InProgress",
    "Blocked",
    "PendingDecision",
    "PendingApproval",
    "Completed",
    "Cancelled",
  ];
  const WORKITEM_TEST_STATUSES = [
    "NotRun",
    "Running",
    "Passed",
    "Failed",
    "Stale",
    "Skipped",
  ];
  const WORKITEM_LAMPS = ["Gray", "Yellow", "Red", "Green", "Orange"];
  /** 佈署.pdf：DeploymentType registry（Inspector／驗證讀同一份定義） */
  const DEPLOYMENT_TYPES = [
    "local",
    "desktop",
    "web",
    "container",
    "server",
    "cloud",
  ];
  const DEPLOYMENT_NODE_REGISTRY = {
    local: { label: "Local", strategies: ["replace"] },
    desktop: { label: "Desktop", strategies: ["replace"] },
    web: { label: "Web", strategies: ["replace", "rolling", "blue-green", "canary"] },
    container: {
      label: "Container",
      strategies: ["replace", "rolling", "blue-green", "canary"],
    },
    server: {
      label: "Server",
      strategies: ["replace", "rolling", "blue-green"],
    },
    cloud: {
      label: "Cloud",
      strategies: ["replace", "rolling", "blue-green", "canary"],
    },
  };
  const DEPLOYMENT_FIELD_KEYS = [
    "deploymentType",
    "targetRef",
    "enabled",
    "inputArtifact",
    "artifactType",
    "version",
    "checksumPolicy",
    "environment",
    "runtime",
    "configProfile",
    "secretRefs",
    "strategy",
    "preDeployChecks",
    "healthCheck",
    "rollbackPolicy",
    "approvalPolicy",
    "timeoutSeconds",
    "retryPolicy",
    "resourceLimits",
    "costBudget",
    "executionStatus",
    "lastRunRef",
  ];
  const ARCH_KIND_ALIASES = { Api: "API", api: "API", ACL: "ACL" };
  const ARCH_KIND_IO = {
    API: {
      role: "Protocol Adapter",
      inLabel: "request",
      outLabel: "response",
    },
    Contract: {
      role: "Schema Definition",
      inLabel: "schema",
      outLabel: "typeDef",
    },
    UI: {
      role: "Presentation Layer",
      inLabel: "viewModel",
      outLabel: "intent",
    },
    Command: {
      role: "Write Operation",
      inLabel: "command",
      outLabel: "result",
    },
    Query: {
      role: "Read Operation",
      inLabel: "filter",
      outLabel: "readDto",
    },
    Application: {
      role: "Use-case Orchestration",
      inLabel: "command",
      outLabel: "result",
    },
    Domain: {
      role: "Business Rules",
      inLabel: "entity",
      outLabel: "state",
    },
    Infrastructure: {
      role: "Persistence / I/O",
      inLabel: "portReq",
      outLabel: "persistResult",
    },
    ACL: {
      role: "External Translation",
      inLabel: "internal",
      outLabel: "external",
    },
    Custom: {
      role: "Extension / Composition",
      inLabel: "manifest",
      outLabel: "capability",
    },
    WorkItem: {
      role: "Work Item · Lamp · Event Log",
      inLabel: "context",
      outLabel: "result",
    },
    Deployment: {
      role: "Deploy Target · Strategy · Status",
      inLabel: "artifact",
      outLabel: "deployResult",
    },
    Layer: {
      role: "Pack same Node Type · inter-Layer 單線",
      inLabel: "in",
      outLabel: "out",
    },
  };
  const ARCH_LAYER_TO_KIND = {
    presentation: "UI",
    ui: "UI",
    ipc: "Command",
    command: "Command",
    host: "Application",
    application: "Application",
    domain: "Domain",
    ports: "Infrastructure",
    adapters: "Infrastructure",
    infrastructure: "Infrastructure",
    contract: "Contract",
    query: "Query",
    api: "API",
    acl: "ACL",
  };
  const ARCH_SNAP_PX = 8;
  const ARCH_LS_KEY = "sgenaxis.arch.draft.v1";
  const ARCH_XML_MIME = "application/xml";
  const ARCH_XML_DEFAULT_NAME = "default.sgml";

  let archDoc = blankArchDoc();
  let archEditMode = false;
  let archGridPx = 8;
  let archZoom = 1;
  let archDrag = null; /* { ids, startX, startY, origins:{id:{x,y}} } */
  let archMarquee = null; /* { x0,y0,x1,y1 } stage coords */
  let archMemberDrag = null; /* { nodeId, layerId, startX, startY } */
  let archTrayDrag = null; /* Unassigned → Module：{ nodeId, startX, startY } */
  /** 未分配 tree：kind 群組展開狀態（預設展開） */
  const archUnassignedTreeOpen = Object.create(null);
  let archLink = null;
  let archSelectedId = null; /* primary（Inspector） */
  let archSelectedIds = []; /* 多選；含 primary */
  let archSeq = 0;
  /** null／"all"＝全部；否則為單一 kind（Layer 篩選含 packs 相符之 Layer） */
  let archKindFilter = "all";
  let archXmlPathHint = ARCH_XML_DEFAULT_NAME;

  function blankArchDoc() {
    return {
      format: "sgenaxis.arch",
      formatVersion: 1,
      meta: {
        formSize: "1280x720",
        gridSize: 8,
        product_pass: false,
        encoding: "xml",
      },
      nodes: [],
      edges: [],
      /* Tasks Node.html：歷史獨立於節點本體 */
      events: [],
    };
  }

  function escapeXml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&apos;");
  }

  function archAttr(name, value) {
    if (value == null || value === "") return "";
    return " " + name + '="' + escapeXml(value) + '"';
  }

  /** SSOT 存取格式：XML（.sgenarch.xml）。 */
  function archDocToXml(doc) {
    const d = doc || archDoc;
    const meta = d.meta || {};
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml +=
      '<sgenaxisArch format="' +
      escapeXml(d.format || "sgenaxis.arch") +
      '" formatVersion="' +
      escapeXml(String(d.formatVersion != null ? d.formatVersion : 1)) +
      '">\n';
    xml +=
      "  <meta" +
      archAttr("formSize", meta.formSize || "1280x720") +
      archAttr("gridSize", meta.gridSize != null ? String(meta.gridSize) : "8") +
      archAttr("product_pass", meta.product_pass ? "true" : "false") +
      archAttr("encoding", "xml") +
      " />\n";
    xml += "  <nodes>\n";
    (d.nodes || []).forEach(function (n) {
      if (!n || !normalizeArchKind(n.kind)) return;
      xml +=
        "    <node" +
        archAttr("id", n.id) +
        archAttr("name", n.name) +
        archAttr("kind", n.kind) +
        archAttr("x", String(Number(n.x) || 0)) +
        archAttr("y", String(Number(n.y) || 0)) +
        archAttr("collapsed", n.collapsed ? "true" : "false") +
        archAttr("role", n.role || "") +
        archAttr("status", n.status || "") +
        archAttr("packsKind", n.packsKind || "") +
        archAttr("projectionLayer", n.projectionLayer || "") +
        archAttr("layerRef", n.layerRef || "") +
        archAttr("moduleRef", n.moduleRef || "") +
        archAttr("order", n.layoutOrder != null ? String(n.layoutOrder) : "") +
        archAttr("uiLayerId", n.kind === "UI" ? n.uiLayerId || n.id : "") +
        archAttr("uiDefinitionRef", n.uiDefinitionRef || "") +
        archAttr("themeRef", n.themeRef || "") +
        archAttr("schemaVersion", n.schemaVersion || "") +
        archAttr("validationStatus", n.validationStatus || "") +
        archAttr("deploymentType", n.deploymentType || "") +
        archAttr("targetRef", n.targetRef || "") +
        archAttr(
          "enabled",
          n.kind === "Deployment"
            ? n.enabled === false
              ? "false"
              : "true"
            : ""
        ) +
        archAttr("inputArtifact", n.inputArtifact || "") +
        archAttr("artifactType", n.artifactType || "") +
        archAttr("version", n.version || "") +
        archAttr("checksumPolicy", n.checksumPolicy || "") +
        archAttr("environment", n.environment || "") +
        archAttr("runtime", n.runtime || "") +
        archAttr("configProfile", n.configProfile || "") +
        archAttr("secretRefs", n.secretRefs || "") +
        archAttr("strategy", n.strategy || "") +
        archAttr("preDeployChecks", n.preDeployChecks || "") +
        archAttr("healthCheck", n.healthCheck || "") +
        archAttr("rollbackPolicy", n.rollbackPolicy || "") +
        archAttr("approvalPolicy", n.approvalPolicy || "") +
        archAttr(
          "timeoutSeconds",
          n.timeoutSeconds != null && n.timeoutSeconds !== ""
            ? String(n.timeoutSeconds)
            : ""
        ) +
        archAttr("retryPolicy", n.retryPolicy || "") +
        archAttr("resourceLimits", n.resourceLimits || "") +
        archAttr("costBudget", n.costBudget || "") +
        archAttr("executionStatus", n.executionStatus || "") +
        archAttr("lastRunRef", n.lastRunRef || "") +
        archAttr("workflowStatus", n.workflowStatus || "") +
        archAttr("testStatus", n.testStatus || "") +
        archAttr("displayLamp", n.displayLamp || "") +
        archAttr("priority", n.priority || "") +
        archAttr("acceptanceCriteria", n.acceptanceCriteria || "") +
        archAttr("buildDate", n.buildDate || "") +
        archAttr("modifiedDate", n.modifiedDate || "") +
        archAttr("completedDate", n.completedDate || "") +
        archAttr("parentNodeId", n.parentNodeId || "") +
        archAttr("parentRefs", n.parentRefs || "") +
        archAttr("dependencyRefs", n.dependencyRefs || "") +
        archAttr("blockerNote", n.blockerNote || "") +
        archAttr(
          "inputTokens",
          n.inputTokens != null && n.inputTokens !== ""
            ? String(n.inputTokens)
            : ""
        ) +
        archAttr(
          "outputTokens",
          n.outputTokens != null && n.outputTokens !== ""
            ? String(n.outputTokens)
            : ""
        ) +
        archAttr("apiCost", n.apiCost || "") +
        ">\n";
      if (n.description) {
        xml +=
          "      <description>" +
          escapeXml(n.description) +
          "</description>\n";
      }
      xml += "      <inputs>\n";
      (n.inputs || []).forEach(function (p) {
        xml +=
          "        <port" +
          archAttr("id", p.id || p.portId) +
          archAttr("name", p.name || p.label || "") +
          archAttr("label", p.label || p.name || "") +
          archAttr("direction", "input") +
          archAttr("dataType", p.dataType || "") +
          archAttr("required", p.required ? "true" : "") +
          " />\n";
      });
      xml += "      </inputs>\n";
      xml += "      <outputs>\n";
      (n.outputs || []).forEach(function (p) {
        xml +=
          "        <port" +
          archAttr("id", p.id || p.portId) +
          archAttr("name", p.name || p.label || "") +
          archAttr("label", p.label || p.name || "") +
          archAttr("direction", "output") +
          archAttr("dataType", p.dataType || "") +
          archAttr("required", p.required ? "true" : "") +
          " />\n";
      });
      xml += "      </outputs>\n";
      if (n.kind === "Layer") {
        const mods = ensureLayerModules(n);
        xml += "      <modules>\n";
        mods.forEach(function (mod, mi) {
          xml +=
            "        <module" +
            archAttr("slotId", mod.slotId) +
            archAttr("name", mod.name || "") +
            archAttr("moduleId", mod.moduleId || "") +
            archAttr("order", String(mi)) +
            archAttr("collapsed", mod.collapsed ? "true" : "false") +
            ">\n";
          sortedModuleMemberIds(mod).forEach(function (mid) {
            xml += "          <member" + archAttr("id", mid) + " />\n";
          });
          xml += "        </module>\n";
        });
        xml += "      </modules>\n";
      }
      xml += "    </node>\n";
    });
    xml += "  </nodes>\n";
    xml += "  <edges>\n";
    (d.edges || []).forEach(function (e) {
      if (!e) return;
      xml +=
        "    <edge" +
        archAttr("id", e.id) +
        archAttr("fromNode", e.fromNode) +
        archAttr("fromPort", e.fromPort) +
        archAttr("toNode", e.toNode) +
        archAttr("toPort", e.toPort) +
        " />\n";
    });
    xml += "  </edges>\n";
    xml += "  <events>\n";
    (d.events || []).forEach(function (ev) {
      if (!ev) return;
      xml +=
        "    <event" +
        archAttr("id", ev.eventId || ev.id) +
        archAttr("entityRef", ev.entityRef || "") +
        archAttr("eventType", ev.eventType || "") +
        archAttr("timestamp", ev.timestamp || "") +
        archAttr("actorType", ev.actorType || "") +
        archAttr("actorRef", ev.actorRef || "") +
        archAttr("correlationId", ev.correlationId || "") +
        archAttr(
          "schemaVersion",
          ev.schemaVersion != null ? String(ev.schemaVersion) : ""
        ) +
        ">\n";
      if (ev.payload != null) {
        let payloadText = "";
        try {
          payloadText =
            typeof ev.payload === "string"
              ? ev.payload
              : JSON.stringify(ev.payload);
        } catch (_e) {
          payloadText = String(ev.payload);
        }
        xml +=
          "      <payload>" + escapeXml(payloadText) + "</payload>\n";
      }
      xml += "    </event>\n";
    });
    xml += "  </events>\n";
    xml += "</sgenaxisArch>\n";
    return xml;
  }

  function archXmlAttr(el, name, fallback) {
    if (!el || !el.getAttribute) return fallback;
    const v = el.getAttribute(name);
    return v == null || v === "" ? fallback : v;
  }

  function archDocFromXml(xmlText) {
    const raw = String(xmlText || "").trim();
    if (!raw) return null;
    let docXml;
    try {
      docXml = new DOMParser().parseFromString(raw, "application/xml");
    } catch (_e) {
      return null;
    }
    const err = docXml.querySelector("parsererror");
    if (err) return null;
    const root =
      docXml.documentElement &&
      docXml.documentElement.localName === "sgenaxisArch"
        ? docXml.documentElement
        : docXml.querySelector("sgenaxisArch");
    if (!root) return null;
    const metaEl = root.querySelector("meta");
    const doc = blankArchDoc();
    doc.format = archXmlAttr(root, "format", "sgenaxis.arch");
    doc.formatVersion = Number(archXmlAttr(root, "formatVersion", "1")) || 1;
    doc.meta = {
      formSize: archXmlAttr(metaEl, "formSize", "1280x720"),
      gridSize: Number(archXmlAttr(metaEl, "gridSize", "8")),
      product_pass: archXmlAttr(metaEl, "product_pass", "false") === "true",
      encoding: "xml",
    };
    doc.nodes = [];
    root.querySelectorAll("nodes > node").forEach(function (nel) {
      const kind = normalizeArchKind(archXmlAttr(nel, "kind", ""));
      if (!kind) return;
      const id = archXmlAttr(nel, "id", "");
      if (!id) return;
      const orderRaw = archXmlAttr(nel, "order", "");
      const descEl = nel.querySelector("description");
      const node = {
        id: id,
        name: archXmlAttr(nel, "name", kind),
        kind: kind,
        x: Number(archXmlAttr(nel, "x", "0")) || 0,
        y: Number(archXmlAttr(nel, "y", "0")) || 0,
        collapsed: archXmlAttr(nel, "collapsed", "false") === "true",
        role: archXmlAttr(nel, "role", ""),
        status: archXmlAttr(nel, "status", ""),
        packsKind: archXmlAttr(nel, "packsKind", "") || null,
        projectionLayer: archXmlAttr(nel, "projectionLayer", "") || null,
        layerRef: archXmlAttr(nel, "layerRef", "") || null,
        moduleRef: archXmlAttr(nel, "moduleRef", "") || null,
        layoutOrder:
          orderRaw === "" ? null : Number(orderRaw) || 0,
        description: descEl ? (descEl.textContent || "").trim() : "",
        uiLayerId: archXmlAttr(nel, "uiLayerId", "") || null,
        uiDefinitionRef: archXmlAttr(nel, "uiDefinitionRef", "") || null,
        themeRef: archXmlAttr(nel, "themeRef", "") || null,
        schemaVersion: archXmlAttr(nel, "schemaVersion", "") || null,
        validationStatus: archXmlAttr(nel, "validationStatus", "") || null,
        deploymentType: archXmlAttr(nel, "deploymentType", "") || null,
        targetRef: archXmlAttr(nel, "targetRef", "") || null,
        enabled:
          kind === "Deployment"
            ? archXmlAttr(nel, "enabled", "true") !== "false"
            : null,
        inputArtifact: archXmlAttr(nel, "inputArtifact", "") || null,
        artifactType: archXmlAttr(nel, "artifactType", "") || null,
        version: archXmlAttr(nel, "version", "") || null,
        checksumPolicy: archXmlAttr(nel, "checksumPolicy", "") || null,
        environment: archXmlAttr(nel, "environment", "") || null,
        runtime: archXmlAttr(nel, "runtime", "") || null,
        configProfile: archXmlAttr(nel, "configProfile", "") || null,
        secretRefs: archXmlAttr(nel, "secretRefs", "") || null,
        strategy: archXmlAttr(nel, "strategy", "") || null,
        preDeployChecks: archXmlAttr(nel, "preDeployChecks", "") || null,
        healthCheck: archXmlAttr(nel, "healthCheck", "") || null,
        rollbackPolicy: archXmlAttr(nel, "rollbackPolicy", "") || null,
        approvalPolicy: archXmlAttr(nel, "approvalPolicy", "") || null,
        timeoutSeconds: (function () {
          const t = archXmlAttr(nel, "timeoutSeconds", "");
          return t === "" ? null : Number(t) || 0;
        })(),
        retryPolicy: archXmlAttr(nel, "retryPolicy", "") || null,
        resourceLimits: archXmlAttr(nel, "resourceLimits", "") || null,
        costBudget: archXmlAttr(nel, "costBudget", "") || null,
        executionStatus: archXmlAttr(nel, "executionStatus", "") || null,
        lastRunRef: archXmlAttr(nel, "lastRunRef", "") || null,
        workflowStatus: archXmlAttr(nel, "workflowStatus", "") || null,
        testStatus: archXmlAttr(nel, "testStatus", "") || null,
        displayLamp: archXmlAttr(nel, "displayLamp", "") || null,
        priority: archXmlAttr(nel, "priority", "") || null,
        acceptanceCriteria:
          archXmlAttr(nel, "acceptanceCriteria", "") || null,
        buildDate: archXmlAttr(nel, "buildDate", "") || null,
        modifiedDate: archXmlAttr(nel, "modifiedDate", "") || null,
        completedDate: archXmlAttr(nel, "completedDate", "") || null,
        parentNodeId: archXmlAttr(nel, "parentNodeId", "") || null,
        parentRefs: archXmlAttr(nel, "parentRefs", "") || null,
        dependencyRefs: archXmlAttr(nel, "dependencyRefs", "") || null,
        blockerNote: archXmlAttr(nel, "blockerNote", "") || null,
        inputTokens: (function () {
          const t = archXmlAttr(nel, "inputTokens", "");
          return t === "" ? null : Number(t) || 0;
        })(),
        outputTokens: (function () {
          const t = archXmlAttr(nel, "outputTokens", "");
          return t === "" ? null : Number(t) || 0;
        })(),
        apiCost: archXmlAttr(nel, "apiCost", "") || null,
        inputs: [],
        outputs: [],
        memberIds: [],
      };
      if (kind === "UI") ensureUiLayerFields(node);
      if (kind === "Deployment") ensureDeploymentFields(node);
      if (kind === "WorkItem") ensureWorkItemFields(node);
      nel.querySelectorAll("inputs > port").forEach(function (p) {
        const label =
          archXmlAttr(p, "label", "") ||
          archXmlAttr(p, "name", "in");
        node.inputs.push({
          id: archXmlAttr(p, "id", id + "-in"),
          portId: archXmlAttr(p, "id", id + "-in"),
          name: archXmlAttr(p, "name", label),
          label: label,
          direction: "input",
          dataType: archXmlAttr(p, "dataType", "") || null,
          required: archXmlAttr(p, "required", "false") === "true",
        });
      });
      nel.querySelectorAll("outputs > port").forEach(function (p) {
        const label =
          archXmlAttr(p, "label", "") ||
          archXmlAttr(p, "name", "out");
        node.outputs.push({
          id: archXmlAttr(p, "id", id + "-out"),
          portId: archXmlAttr(p, "id", id + "-out"),
          name: archXmlAttr(p, "name", label),
          label: label,
          direction: "output",
          dataType: archXmlAttr(p, "dataType", "") || null,
          required: archXmlAttr(p, "required", "false") === "true",
        });
      });
      if (!node.inputs.length || !node.outputs.length) {
        const ports = defaultPortsForArchKind(kind, id);
        if (!node.inputs.length) node.inputs = ports.inputs;
        if (!node.outputs.length) node.outputs = ports.outputs;
        if (!node.role) node.role = ports.role;
      }
      if (kind === "Layer") {
        node.modules = [];
        nel.querySelectorAll("modules > module").forEach(function (mel) {
          const mod = {
            slotId: archXmlAttr(mel, "slotId", id + "-slot-" + (node.modules.length + 1)),
            name: archXmlAttr(mel, "name", "Module Slot"),
            moduleId: archXmlAttr(mel, "moduleId", ""),
            collapsed: archXmlAttr(mel, "collapsed", "false") === "true",
            memberIds: [],
          };
          if (!mod.moduleId) {
            mod.moduleId = mod.slotId || id + "-mod-" + (node.modules.length + 1);
          }
          mel.querySelectorAll("member").forEach(function (m) {
            const mid = archXmlAttr(m, "id", "");
            if (mid) mod.memberIds.push(mid);
          });
          node.modules.push(mod);
        });
        /* 舊版 <members> → 單一 Module Slot */
        if (!node.modules.length) {
          const legacy = [];
          nel.querySelectorAll("members > member").forEach(function (m) {
            const mid = archXmlAttr(m, "id", "");
            if (mid) legacy.push(mid);
          });
          node.memberIds = legacy;
        }
        if (!node.packsKind) node.packsKind = "API";
        ensureLayerModules(node);
      } else {
        delete node.memberIds;
        delete node.packsKind;
        delete node.modules;
      }
      doc.nodes.push(node);
    });
    syncArchAssignmentsFromModules(doc);
    doc.edges = [];
    root.querySelectorAll("edges > edge").forEach(function (eel) {
      doc.edges.push({
        id: archXmlAttr(eel, "id", "e-" + doc.edges.length),
        fromNode: archXmlAttr(eel, "fromNode", ""),
        fromPort: archXmlAttr(eel, "fromPort", ""),
        toNode: archXmlAttr(eel, "toNode", ""),
        toPort: archXmlAttr(eel, "toPort", ""),
      });
    });
    doc.events = [];
    root.querySelectorAll("events > event").forEach(function (eel) {
      const payloadEl = eel.querySelector("payload");
      let payload = {};
      if (payloadEl) {
        const rawPayload = (payloadEl.textContent || "").trim();
        try {
          payload = rawPayload ? JSON.parse(rawPayload) : {};
        } catch (_e) {
          payload = { text: rawPayload };
        }
      }
      doc.events.push({
        eventId: archXmlAttr(eel, "id", "evt-" + doc.events.length),
        entityRef: archXmlAttr(eel, "entityRef", ""),
        eventType: archXmlAttr(eel, "eventType", ""),
        timestamp: archXmlAttr(eel, "timestamp", ""),
        actorType: archXmlAttr(eel, "actorType", "user"),
        actorRef: archXmlAttr(eel, "actorRef", ""),
        correlationId: archXmlAttr(eel, "correlationId", "") || null,
        schemaVersion:
          Number(archXmlAttr(eel, "schemaVersion", "1")) || 1,
        payload: payload,
      });
    });
    return doc;
  }

  function applyArchDoc(doc, opts) {
    if (!doc || !Array.isArray(doc.nodes) || !Array.isArray(doc.edges)) return false;
    doc.nodes = doc.nodes.filter(function (n) {
      return n && normalizeArchKind(n.kind);
    });
    doc.nodes.forEach(function (n) {
      if (n && n.kind === "Layer") ensureLayerModules(n);
      if (n && n.kind === "WorkItem") ensureWorkItemFields(n);
    });
    if (!Array.isArray(doc.events)) doc.events = [];
    if (!doc.meta) doc.meta = {};
    doc.meta.encoding = "xml";
    archDoc = doc;
    archGridPx =
      archDoc.meta.gridSize != null ? Number(archDoc.meta.gridSize) : 8;
    if (!(opts && opts.quiet)) {
      setArchFormSize(
        (archDoc.meta && archDoc.meta.formSize) || "1280x720",
        true
      );
      setArchGridPx(archGridPx, true);
      renderArchDag();
    }
    return true;
  }

  function normalizeArchKind(kind) {
    let k = String(kind || "").trim();
    if (ARCH_KIND_ALIASES[k]) k = ARCH_KIND_ALIASES[k];
    if (ARCH_NODE_KINDS.indexOf(k) >= 0) return k;
    const upper = k.toUpperCase();
    if (upper === "API") return "API";
    if (upper === "ACL") return "ACL";
    return null;
  }

  function defaultPortsForArchKind(kind, nodeId) {
    const io = ARCH_KIND_IO[kind] || ARCH_KIND_IO.Custom;
    return {
      inputs: [{ id: nodeId + "-in", label: io.inLabel }],
      outputs: [{ id: nodeId + "-out", label: io.outLabel }],
      role: io.role,
    };
  }

  function mapLayerToArchKind(layer) {
    const key = String(layer || "")
      .trim()
      .toLowerCase();
    return ARCH_LAYER_TO_KIND[key] || "Custom";
  }

  function setArchStatusLine(msg, isError) {
    const el = document.getElementById("arch-status-line");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("error", !!isError);
  }

  function setArchLiveBadge(text, kind) {
    const el = document.getElementById("arch-live-badge");
    if (!el) return;
    el.textContent = text || "來源：—";
    el.classList.remove("live", "warn");
    if (kind) el.classList.add(kind);
  }

  function setArchBanner(title, body, isError) {
    const empty = document.getElementById("arch-empty");
    if (!empty) return;
    empty.hidden = false;
    empty.classList.toggle("is-error", !!isError);
    const t = document.getElementById("arch-empty-title");
    const b = document.getElementById("arch-empty-body");
    if (t && title) t.textContent = title;
    if (b && body) b.textContent = body;
  }

  function showArchEmpty(title, body, statusMsg, badgeKind) {
    setArchBanner(title, body, true);
    setArchLiveBadge("來源：NOT RUN／空態", badgeKind || "warn");
    setArchStatusLine(statusMsg || "架構：空態／NOT RUN", true);
    lastArchProj = null;
    selectedArchModuleId = null;
    renderArchDag();
  }

  function showArchProjection() {
    setArchBanner(
      "投影已疊加（live）",
      "草稿座標保留；狀態／缺節點由 Command 補齊。禁止靜態假圖冒充 live。",
      false
    );
  }

  function persistArchDraft(opts) {
    try {
      if (!archDoc.meta) archDoc.meta = {};
      archDoc.meta.encoding = "xml";
      localStorage.setItem(ARCH_LS_KEY, archDocToXml(archDoc));
    } catch (_e) {
      /* ignore quota */
    }
    const pathEl = document.getElementById("arch-xml-path");
    if (pathEl) pathEl.textContent = archXmlPathHint || ARCH_XML_DEFAULT_NAME;
    if (!(opts && opts.quiet)) markSceneDirty();
  }

  function loadArchDraft() {
    try {
      const raw = localStorage.getItem(ARCH_LS_KEY);
      if (!raw) return;
      let doc = null;
      const trimmed = String(raw).trim();
      if (trimmed.charAt(0) === "<") {
        doc = archDocFromXml(trimmed);
      } else {
        /* 舊 JSON 草稿 → 遷入 XML SSOT */
        const parsed = JSON.parse(trimmed);
        if (parsed && Array.isArray(parsed.nodes) && Array.isArray(parsed.edges)) {
          doc = parsed;
          if (!doc.meta) doc.meta = {};
          doc.meta.encoding = "xml";
        }
      }
      if (!doc) return;
      applyArchDoc(doc, { quiet: true });
      /* 立刻以 XML 覆寫 LS（載入草稿不算場景異動） */
      persistArchDraft({ quiet: true });
    } catch (_e) {
      /* ignore */
    }
  }

  function downloadArchXml() {
    const xml = archDocToXml(archDoc);
    const blob = new Blob([xml], { type: ARCH_XML_MIME });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = archXmlPathHint || ARCH_XML_DEFAULT_NAME;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 500);
    persistArchDraft();
    toast("已匯出架構 XML（" + (archXmlPathHint || ARCH_XML_DEFAULT_NAME) + "）");
  }

  function importArchXmlText(text, fileName) {
    const doc = archDocFromXml(text);
    if (!doc) {
      toast("拒絕：無法解析架構 XML（需 <sgenaxisArch>）");
      return false;
    }
    if (fileName) archXmlPathHint = String(fileName);
    applyArchDoc(doc, { quiet: false });
    persistArchDraft();
    toast("已載入架構 XML");
    return true;
  }

  function openArchXmlFilePicker() {
    const input = document.getElementById("arch-xml-file");
    if (input) input.click();
  }

  function ensureDefaultArchSeed() {
    if (archDoc.nodes.length) return;
    /* Seed follows PDF dependency sketch: API/UI → Application → Domain → Infra/ACL */
    const seed = [
      { id: "n-api", name: "API", kind: "API", x: 40, y: 80 },
      { id: "n-ui", name: "UI", kind: "UI", x: 40, y: 260 },
      { id: "n-app", name: "Application", kind: "Application", x: 320, y: 160 },
      { id: "n-dom", name: "Domain", kind: "Domain", x: 600, y: 160 },
      { id: "n-infra", name: "Infrastructure", kind: "Infrastructure", x: 880, y: 100 },
      { id: "n-acl", name: "ACL", kind: "ACL", x: 880, y: 280 },
      { id: "n-contract", name: "Contract", kind: "Contract", x: 320, y: 40 },
    ];
    seed.forEach(function (s) {
      const ports = defaultPortsForArchKind(s.kind, s.id);
      const node = {
        id: s.id,
        name: s.kind === "UI" ? "UI Layer" : s.name,
        kind: s.kind,
        x: s.x,
        y: s.y,
        collapsed: false,
        inputs: ports.inputs,
        outputs: ports.outputs,
        role: ports.role,
        status: "未驗證",
        projectionLayer: null,
      };
      if (s.kind === "UI") ensureUiLayerFields(node);
      archDoc.nodes.push(node);
    });
    archDoc.edges = [
      {
        id: "e1",
        fromNode: "n-api",
        fromPort: "n-api-out",
        toNode: "n-app",
        toPort: "n-app-in",
      },
      {
        id: "e2",
        fromNode: "n-ui",
        fromPort: "n-ui-out",
        toNode: "n-app",
        toPort: "n-app-in",
      },
      {
        id: "e3",
        fromNode: "n-app",
        fromPort: "n-app-out",
        toNode: "n-dom",
        toPort: "n-dom-in",
      },
      {
        id: "e4",
        fromNode: "n-dom",
        fromPort: "n-dom-out",
        toNode: "n-infra",
        toPort: "n-infra-in",
      },
      {
        id: "e5",
        fromNode: "n-dom",
        fromPort: "n-dom-out",
        toNode: "n-acl",
        toPort: "n-acl-in",
      },
    ];
  }

  function findArchNode(id) {
    return archDoc.nodes.find(function (n) {
      return n.id === id;
    });
  }

  const ARCH_WORLD_GROW = 320;
  const ARCH_WORLD_MAX = 100000;

  function archStageSize() {
    const stage = document.getElementById("archStage");
    const w = stage ? Number(stage.getAttribute("data-w")) || 1280 : 1280;
    const h = stage ? Number(stage.getAttribute("data-h")) || 720 : 720;
    return { w: w, h: h };
  }

  function archMinFormSize() {
    const tok = (archDoc.meta && archDoc.meta.formSize) || "1280x720";
    const m = String(tok).match(/^(\d+)x(\d+)$/i);
    return {
      w: m ? Math.max(320, Number(m[1])) : 1280,
      h: m ? Math.max(240, Number(m[2])) : 720,
    };
  }

  function applyArchWorldSize(w, h, quiet) {
    const ww = Math.min(
      ARCH_WORLD_MAX,
      Math.max(320, Math.ceil(Number(w) || 0))
    );
    const hh = Math.min(
      ARCH_WORLD_MAX,
      Math.max(240, Math.ceil(Number(h) || 0))
    );
    const stage = document.getElementById("archStage");
    if (stage) {
      stage.style.width = ww + "px";
      stage.style.height = hh + "px";
      stage.setAttribute("data-w", String(ww));
      stage.setAttribute("data-h", String(hh));
      stage.classList.add("is-infinite-grid");
    }
    renderArchRulers(ww, hh);
    if (!quiet) renderArchEdges();
    return { w: ww, h: hh };
  }

  /** Grid 無限延伸：世界隨內容／捲動／拖曳自動長大（formSize＝最小底板）。 */
  function expandArchWorldExtent(opts) {
    const quiet = opts && opts.quiet;
    const margin =
      opts && opts.margin != null ? opts.margin : ARCH_WORLD_GROW;
    const min = archMinFormSize();
    let needW = min.w;
    let needH = min.h;
    archDoc.nodes.forEach(function (n) {
      if (!n) return;
      if (n.kind !== "Layer" && findArchLayerContaining(n.id)) return;
      const el = document.querySelector(
        '.arch-node[data-id="' + n.id + '"]'
      );
      const nw = el ? el.offsetWidth : 200;
      const nh = el ? el.offsetHeight : 88;
      needW = Math.max(needW, (Number(n.x) || 0) + nw + margin);
      needH = Math.max(needH, (Number(n.y) || 0) + nh + margin);
    });
    const shell = document.getElementById("arch-canvas-shell");
    if (shell) {
      needW = Math.max(
        needW,
        shell.scrollLeft / (archZoom || 1) +
          shell.clientWidth / (archZoom || 1) +
          margin
      );
      needH = Math.max(
        needH,
        shell.scrollTop / (archZoom || 1) +
          shell.clientHeight / (archZoom || 1) +
          margin
      );
    }
    const cur = archStageSize();
    if (
      needW > cur.w + 1 ||
      needH > cur.h + 1 ||
      (opts && opts.force)
    ) {
      return applyArchWorldSize(
        Math.max(needW, cur.w),
        Math.max(needH, cur.h),
        quiet
      );
    }
    return cur;
  }

  function setArchFormSize(token, quiet) {
    const m = String(token || "").match(/^(\d+)x(\d+)$/i);
    if (!m) return;
    const w = Math.max(320, Number(m[1]));
    const h = Math.max(240, Number(m[2]));
    if (!archDoc.meta) archDoc.meta = {};
    archDoc.meta.formSize = w + "x" + h;
    const sel = document.getElementById("archFormSize");
    if (sel) {
      const preset = w + "x" + h;
      if ([].some.call(sel.options, function (o) { return o.value === preset; })) {
        sel.value = preset;
      }
    }
    expandArchWorldExtent({ quiet: true, force: true, margin: ARCH_WORLD_GROW });
    if (!quiet) {
      persistArchDraft();
      renderArchEdges();
    }
  }

  function setArchGridPx(px, quiet) {
    let n = Math.round(Number(px));
    if (!isFinite(n) || n < 0) n = 8;
    if (n > 0 && n < 2) n = 2;
    if (n > 64) n = 64;
    archGridPx = n;
    if (!archDoc.meta) archDoc.meta = {};
    archDoc.meta.gridSize = n;
    const board = document.getElementById("archBoard");
    const stage = document.getElementById("archStage");
    if (board) {
      board.setAttribute("data-grid", String(n));
      board.style.setProperty("--grid-size", (n || 8) + "px");
    }
    if (stage) {
      stage.classList.toggle("is-grid-off", n === 0);
      stage.style.setProperty("--grid-size", (n || 8) + "px");
    }
    const sel = document.getElementById("archGridSize");
    if (sel) sel.value = String(n);
    if (!quiet) persistArchDraft();
  }

  function renderArchRulers(rw, rh) {
    const hEl = document.getElementById("archRulerH");
    const vEl = document.getElementById("archRulerV");
    if (!hEl || !vEl) return;
    const pad = 28;
    const hSpan = Math.max(rw + pad, 100);
    const vSpan = Math.max(rh + pad, 100);
    hEl.style.width = hSpan + "px";
    vEl.style.height = vSpan + "px";
    hEl.innerHTML = "";
    vEl.innerHTML = "";
    const major = 50;
    const minor = 10;
    const step = hSpan > 8000 || vSpan > 8000 ? major : minor;
    for (let x = 0; x <= hSpan; x += step) {
      const tick = document.createElement("span");
      tick.className =
        "designer-ruler-tick" + (x % major === 0 ? " is-major" : "");
      tick.style.left = x + "px";
      hEl.appendChild(tick);
      if (x % major === 0) {
        const lab = document.createElement("span");
        lab.className = "designer-ruler-label";
        lab.style.left = x + "px";
        lab.textContent = String(x);
        hEl.appendChild(lab);
      }
    }
    for (let y = 0; y <= vSpan; y += step) {
      const tick = document.createElement("span");
      tick.className =
        "designer-ruler-tick" + (y % major === 0 ? " is-major" : "");
      tick.style.top = y + "px";
      vEl.appendChild(tick);
      if (y % major === 0 && y > 0) {
        const lab = document.createElement("span");
        lab.className = "designer-ruler-label";
        lab.style.top = y + "px";
        lab.textContent = String(y);
        vEl.appendChild(lab);
      }
    }
  }

  function clearArchGuides() {
    const el = document.getElementById("archGuides");
    if (el) el.innerHTML = "";
  }

  function showArchGuides(xs, ys) {
    const el = document.getElementById("archGuides");
    if (!el) return;
    el.innerHTML = "";
    (xs || []).forEach(function (x) {
      const line = document.createElement("div");
      line.className = "arch-guide is-v";
      line.style.left = x + "px";
      el.appendChild(line);
    });
    (ys || []).forEach(function (y) {
      const line = document.createElement("div");
      line.className = "arch-guide is-h";
      line.style.top = y + "px";
      el.appendChild(line);
    });
  }

  function snapArchNode(node) {
    const size = archStageSize();
    const xs = [0, size.w / 2, size.w];
    const ys = [0, size.h / 2, size.h];
    archDoc.nodes.forEach(function (n) {
      if (!n || n.id === node.id) return;
      xs.push(n.x, n.x + 80);
      ys.push(n.y, n.y + 24);
    });
    let bestX = null;
    let bestY = null;
    xs.forEach(function (g) {
      const d = Math.abs(node.x - g);
      if (d <= ARCH_SNAP_PX && (!bestX || d < bestX.d)) bestX = { g: g, d: d };
    });
    ys.forEach(function (g) {
      const d = Math.abs(node.y - g);
      if (d <= ARCH_SNAP_PX && (!bestY || d < bestY.d)) bestY = { g: g, d: d };
    });
    const gpx = archGridPx > 0 ? archGridPx : 0;
    if (bestX) node.x = bestX.g;
    else if (gpx) node.x = Math.round(node.x / gpx) * gpx;
    if (bestY) node.y = bestY.g;
    else if (gpx) node.y = Math.round(node.y / gpx) * gpx;
    /* 不硬夾上界：Grid／世界無限延伸，僅避免負座標 */
    node.x = Math.max(0, node.x);
    node.y = Math.max(0, node.y);
    if (node.x + 48 > size.w - 80 || node.y + 24 > size.h - 80) {
      expandArchWorldExtent({ quiet: true });
    }
    return {
      xs: bestX ? [bestX.g] : [],
      ys: bestY ? [bestY.g] : [],
    };
  }

  function selectArchModule(mod) {
    selectedArchModuleId = mod && mod.id ? mod.id : null;
    document.querySelectorAll(".arch-mod-item").forEach(function (li) {
      li.classList.toggle(
        "selected",
        selectedArchModuleId && li.dataset.moduleId === selectedArchModuleId
      );
    });
    if (mod && mod.id) {
      const n = findArchNode(mod.id) || findArchNode("n-" + String(mod.id).toLowerCase());
      if (n) selectArchNode(n.id);
      else {
        const selTitle = document.getElementById("inspector-sel-title");
        const selBody = document.getElementById("inspector-sel-body");
        if (selTitle) selTitle.textContent = "模組：" + (mod.name || mod.id);
        if (selBody) {
          selBody.textContent =
            "id=" +
            (mod.id || "—") +
            " · layer=" +
            (mod.layer || "—") +
            " · " +
            (mod.role || "");
        }
      }
    }
  }

  /** 一般節點只顯示類別名；UI → UI Layer；WorkItem → Work Item；Node Type 僅 Layer。 */
  function formatArchNodeType(kind, node) {
    const k = normalizeArchKind(kind) || String(kind || "").trim() || "—";
    if (k === "Layer") return "Node Type : Layer";
    if (k === "UI") return "UI Layer";
    if (k === "WorkItem") return "Work Item";
    if (k === "Deployment") return "Deployment";
    return k;
  }

  function isArchUiLayerNode(node) {
    return !!(node && normalizeArchKind(node.kind) === "UI");
  }

  function isArchDeploymentNode(node) {
    return !!(node && normalizeArchKind(node.kind) === "Deployment");
  }

  function isArchWorkItemNode(node) {
    return !!(node && normalizeArchKind(node.kind) === "WorkItem");
  }

  /** Tasks Node.html §08：阻塞＞待決策＞進行中＞綠燈＞灰；Stale／Failed 不得綠燈 */
  function computeDisplayLamp(node) {
    const wf = String((node && node.workflowStatus) || "NotStarted");
    const ts = String((node && node.testStatus) || "NotRun");
    if (wf === "Blocked") return "Red";
    if (wf === "PendingDecision" || wf === "PendingApproval") return "Orange";
    if (wf === "InProgress" || ts === "Running") return "Yellow";
    if (ts === "Passed") return "Green";
    return "Gray";
  }

  function ensureWorkItemFields(node) {
    if (!isArchWorkItemNode(node)) return node;
    if (
      WORKITEM_WORKFLOW_STATUSES.indexOf(node.workflowStatus) < 0
    ) {
      node.workflowStatus = "NotStarted";
    }
    if (WORKITEM_TEST_STATUSES.indexOf(node.testStatus) < 0) {
      node.testStatus = "NotRun";
    }
    if (node.priority == null || node.priority === "") node.priority = "medium";
    if (node.acceptanceCriteria == null) node.acceptanceCriteria = "";
    if (node.buildDate == null) node.buildDate = "";
    if (node.modifiedDate == null) node.modifiedDate = "";
    if (node.completedDate == null) node.completedDate = "";
    if (node.parentRefs == null) node.parentRefs = "";
    if (node.dependencyRefs == null) node.dependencyRefs = "";
    if (node.blockerNote == null) node.blockerNote = "";
    if (node.inputTokens == null) node.inputTokens = 0;
    if (node.outputTokens == null) node.outputTokens = 0;
    if (node.apiCost == null) node.apiCost = "";
    if (!node.schemaVersion) node.schemaVersion = "1";
    if (node.description == null) node.description = "";
    node.displayLamp = computeDisplayLamp(node);
    return node;
  }

  function appendArchEvent(entityRef, eventType, payload) {
    if (!archDoc.events) archDoc.events = [];
    archSeq += 1;
    const evt = {
      eventId: "evt-" + Date.now() + "-" + archSeq,
      entityRef: entityRef || "",
      eventType: eventType || "node.property.updated",
      timestamp: new Date().toISOString(),
      actorType: "user",
      actorRef: "local",
      correlationId: null,
      schemaVersion: 1,
      payload: payload || {},
    };
    archDoc.events.push(evt);
    return evt;
  }

  function listArchEventsForNode(nodeId, limit) {
    const max = limit == null ? 40 : limit;
    return (archDoc.events || [])
      .filter(function (e) {
        return e && e.entityRef === nodeId;
      })
      .slice(-max)
      .reverse();
  }

  function renderArchWorkItemHistory(node) {
    const host = document.getElementById("archWorkItemHistory");
    if (!host) return;
    if (!isArchWorkItemNode(node)) {
      host.hidden = true;
      host.innerHTML = "";
      return;
    }
    host.hidden = false;
    const events = listArchEventsForNode(node.id, 30);
    if (!events.length) {
      host.innerHTML =
        '<p class="hint">尚無事件（編輯屬性後寫入 Event Log，不塞進節點本體）。</p>';
      return;
    }
    host.innerHTML =
      "<b>History（Event Log）</b><ul class=\"arch-event-list\">" +
      events
        .map(function (e) {
          return (
            "<li><code>" +
            escapeHtml(e.eventType || "") +
            "</code> · " +
            escapeHtml((e.timestamp || "").replace("T", " ").slice(0, 19)) +
            "</li>"
          );
        })
        .join("") +
      "</ul>";
  }

  function normalizeDeploymentType(t) {
    const s = String(t || "").trim().toLowerCase();
    return DEPLOYMENT_TYPES.indexOf(s) >= 0 ? s : "desktop";
  }

  function ensureDeploymentFields(node) {
    if (!isArchDeploymentNode(node)) return node;
    node.deploymentType = normalizeDeploymentType(node.deploymentType);
    if (node.targetRef == null) node.targetRef = "";
    if (node.enabled == null) node.enabled = true;
    if (node.inputArtifact == null) node.inputArtifact = "";
    if (!node.artifactType) node.artifactType = "exe";
    if (node.version == null) node.version = "";
    if (!node.checksumPolicy) node.checksumPolicy = "sha256";
    if (!node.environment) node.environment = "development";
    if (node.runtime == null) node.runtime = "";
    if (node.configProfile == null) node.configProfile = "";
    if (node.secretRefs == null) node.secretRefs = "";
    if (!node.strategy) node.strategy = "replace";
    if (node.preDeployChecks == null) node.preDeployChecks = "";
    if (node.healthCheck == null) node.healthCheck = "";
    if (node.rollbackPolicy == null) node.rollbackPolicy = "";
    if (node.approvalPolicy == null) node.approvalPolicy = "";
    if (node.timeoutSeconds == null || node.timeoutSeconds === "") {
      node.timeoutSeconds = 600;
    }
    if (node.retryPolicy == null) node.retryPolicy = "";
    if (node.resourceLimits == null) node.resourceLimits = "";
    if (node.costBudget == null) node.costBudget = "";
    if (!node.executionStatus) node.executionStatus = "Idle";
    if (node.lastRunRef == null) node.lastRunRef = "";
    if (!node.schemaVersion) node.schemaVersion = "1";
    const def = DEPLOYMENT_NODE_REGISTRY[node.deploymentType];
    if (def && def.strategies.indexOf(node.strategy) < 0) {
      node.strategy = def.strategies[0] || "replace";
    }
    return node;
  }

  function syncDeploymentStrategyOptions(deploymentType, selected) {
    const sel = document.getElementById("archDepStrategy");
    if (!sel) return;
    const def =
      DEPLOYMENT_NODE_REGISTRY[normalizeDeploymentType(deploymentType)] ||
      DEPLOYMENT_NODE_REGISTRY.desktop;
    const want = selected || "replace";
    sel.innerHTML = "";
    (def.strategies || ["replace"]).forEach(function (s) {
      const opt = document.createElement("option");
      opt.value = s;
      opt.textContent = s;
      if (s === want) opt.selected = true;
      sel.appendChild(opt);
    });
    if ((def.strategies || []).indexOf(want) < 0 && sel.options.length) {
      sel.selectedIndex = 0;
    }
  }

  function ensureUiLayerFields(node) {
    if (!isArchUiLayerNode(node)) return node;
    if (!node.uiLayerId) node.uiLayerId = node.id;
    if (node.uiDefinitionRef == null || node.uiDefinitionRef === "") {
      node.uiDefinitionRef = "design/main.sgendesign";
    }
    if (node.themeRef == null) node.themeRef = "";
    if (!node.schemaVersion) node.schemaVersion = "1";
    if (!node.validationStatus) node.validationStatus = "unchecked";
    return node;
  }

  function isUiDesignWindowOpen() {
    if (isUiDesignStandalone()) return true;
    const win = document.getElementById("uidesign-window");
    return !!(win && !win.hidden);
  }

  function applyUiDesignStandaloneShell() {
    if (!isUiDesignStandalone()) return;
    document.documentElement.classList.add("is-uidesign-standalone");
    document.body.classList.add("is-uidesign-standalone");
    const app = document.getElementById("app");
    if (app) app.setAttribute("hidden", "");
    const win = document.getElementById("uidesign-window");
    if (win) {
      win.hidden = false;
      win.classList.add("is-os-window");
    }
    const chrome = document.getElementById("uidesign-window-chrome");
    if (chrome) chrome.hidden = true;
  }

  function closeUiDesignWindow() {
    if (isUiDesignStandalone()) {
      const g = window.__TAURI__;
      const getCurrent =
        g &&
        g.webviewWindow &&
        typeof g.webviewWindow.getCurrentWebviewWindow === "function"
          ? g.webviewWindow.getCurrentWebviewWindow
          : null;
      if (getCurrent) {
        try {
          const cur = getCurrent();
          if (cur && typeof cur.close === "function") {
            cur.close();
            return;
          }
        } catch (_e) {
          /* fall through */
        }
      }
      window.close();
      return;
    }
    const win = document.getElementById("uidesign-window");
    if (win) win.hidden = true;
    setDesignInspectorActive(false);
    setUidesignWidgetsVisible(false);
    setStatus("已關閉 UI 設計工具視窗");
  }

  function openUiDesignWindowEmbedded(mode, opts) {
    const win = document.getElementById("uidesign-window");
    const titleEl = document.getElementById("uidesign-window-title");
    const panel = document.getElementById("panel-uidesign");
    const viewer = mode === "viewer";
    const quiet = opts && opts.quiet;
    if (win) win.hidden = false;
    if (panel) {
      panel.classList.add("is-active");
      panel.removeAttribute("hidden");
    }
    if (titleEl && !isUiDesignStandalone()) {
      titleEl.textContent = viewer ? "UI 預覽" : "UI 編輯";
    }
    setUidesignMode(viewer ? "viewer" : "designer");
    if (opts && opts.path) setUidesignPathDisplay(opts.path);
    renderDesignCanvas();
    if (!viewer) {
      fillDesignProps();
      setDesignInspectorActive(true);
    }
    if (!quiet) {
      toast(
        isUiDesignStandalone()
          ? viewer
            ? "UI 預覽（獨立 OS 視窗）"
            : "UI 編輯（獨立 OS 視窗）"
          : viewer
            ? "已開啟 UI 預覽視窗（內嵌；無 Tauri 時）"
            : "已開啟 UI 編輯視窗（內嵌；無 Tauri 時）"
      );
    }
    setStatus(
      viewer ? "UI 預覽視窗" : "UI 編輯視窗"
    );
  }

  function tryOpenUiDesignOsWindow(mode, opts) {
    if (isUiDesignStandalone()) {
      return Promise.resolve(false);
    }
    const g = window.__TAURI__;
    const WW =
      g && g.webviewWindow && g.webviewWindow.WebviewWindow
        ? g.webviewWindow.WebviewWindow
        : null;
    if (!WW) return Promise.resolve(false);
    const viewer = mode === "viewer";
    const label = viewer ? "ui-viewer" : "ui-editor";
    const path =
      (opts && opts.path) ||
      UIDESIGN_DESIGN_REL ||
      "design/main.sgendesign";
    const title = viewer ? "SGenAxis — UI 預覽" : "SGenAxis — UI 編輯";
    const qs = new URLSearchParams();
    qs.set("standalone", "uidesign");
    qs.set("mode", viewer ? "viewer" : "designer");
    qs.set("path", path);

    function focusExisting(existing) {
      return Promise.resolve()
        .then(function () {
          return existing.setTitle ? existing.setTitle(title) : null;
        })
        .catch(function () {
          /* ignore */
        })
        .then(function () {
          return existing.show ? existing.show() : null;
        })
        .catch(function () {
          /* ignore */
        })
        .then(function () {
          return existing.setFocus ? existing.setFocus() : null;
        })
        .catch(function () {
          /* ignore */
        })
        .then(function () {
          toast(viewer ? "已聚焦 UI 預覽視窗" : "已聚焦 UI 編輯視窗");
          setStatus(
            viewer ? "UI 預覽（獨立 OS 視窗）" : "UI 編輯（獨立 OS 視窗）"
          );
          return true;
        });
    }

    return Promise.resolve()
      .then(function () {
        return typeof WW.getByLabel === "function"
          ? WW.getByLabel(label)
          : null;
      })
      .then(function (existing) {
        if (existing) return focusExisting(existing);
        return new Promise(function (resolve) {
          let settled = false;
          function done(ok) {
            if (settled) return;
            settled = true;
            resolve(!!ok);
          }
          try {
            const w = new WW(label, {
              url: "index.html?" + qs.toString(),
              title: title,
              width: 1120,
              height: 780,
              minWidth: 720,
              minHeight: 480,
              center: true,
              focus: true,
              resizable: true,
              decorations: true,
            });
            if (w && typeof w.once === "function") {
              w.once("tauri://created", function () {
                toast(
                  viewer
                    ? "已開啟 UI 預覽（可拖出主視窗）"
                    : "已開啟 UI 編輯（可拖出主視窗）"
                );
                setStatus(
                  viewer
                    ? "UI 預覽（獨立 OS 視窗）"
                    : "UI 編輯（獨立 OS 視窗）"
                );
                done(true);
              });
              w.once("tauri://error", function () {
                done(false);
              });
            }
            setTimeout(function () {
              done(true);
            }, 2000);
          } catch (_err) {
            done(false);
          }
        });
      })
      .catch(function () {
        return false;
      });
  }

  function openUiDesignWindow(mode, opts) {
    opts = opts || {};
    if (isUiDesignStandalone()) {
      openUiDesignWindowEmbedded(mode, opts);
      return;
    }
    tryOpenUiDesignOsWindow(mode, opts).then(function (ok) {
      if (ok) {
        const win = document.getElementById("uidesign-window");
        if (win) win.hidden = true;
        setDesignInspectorActive(false);
        return;
      }
      openUiDesignWindowEmbedded(mode, opts);
    });
  }

  function openArchUiLayer(mode, nodeId) {
    const id = nodeId || archSelectedId;
    const node = findArchNode(id);
    if (!isArchUiLayerNode(node)) {
      toast("請先選取 UI Layer 節點");
      return;
    }
    selectArchNode(node.id);
    ensureUiLayerFields(node);
    const refEl = document.getElementById("archUiDefinitionRef");
    if (refEl && refEl.value.trim()) {
      node.uiDefinitionRef = refEl.value.trim();
    }
    const themeEl = document.getElementById("archUiThemeRef");
    if (themeEl) node.themeRef = themeEl.value.trim();
    persistArchDraft();
    openUiDesignWindow(mode === "viewer" ? "viewer" : "designer", {
      path: node.uiDefinitionRef || "design/main.sgendesign",
    });
    setStatus(
      (mode === "viewer" ? "UI 預覽 ← " : "UI 編輯 ← ") +
        (node.name || node.id) +
        " · " +
        (node.uiDefinitionRef || node.id)
    );
  }

  function formatArchLayerPacks(node) {
    const packs =
      node && normalizeArchKind(node.packsKind)
        ? normalizeArchKind(node.packsKind)
        : node && node.packsKind
          ? String(node.packsKind)
          : "—";
    return "packs : " + packs;
  }

  function blankModuleSlot(layer, index) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const letter = letters[(index || 0) % 26];
    archSeq += 1;
    const base = layer && layer.id ? layer.id : "layer";
    return {
      slotId: base + "-slot-" + archSeq,
      name: "Module Slot " + letter,
      moduleId: base + "-mod-" + archSeq,
      moduleRef: null,
      collapsed: false,
      memberIds: [],
    };
  }

  /** Spec：Layer → Module Slot[]；舊 memberIds 遷入第一個 Slot。moduleId 穩定、name 可改。 */
  function ensureLayerModules(layer) {
    if (!layer || layer.kind !== "Layer") return [];
    if (!Array.isArray(layer.modules)) layer.modules = [];
    if (
      !layer.modules.length &&
      Array.isArray(layer.memberIds) &&
      layer.memberIds.length
    ) {
      const slot = blankModuleSlot(layer, 0);
      slot.name = "Module Slot A";
      slot.memberIds = layer.memberIds.slice();
      layer.modules.push(slot);
      layer.memberIds = [];
    }
    if (!layer.modules.length) {
      layer.modules.push(blankModuleSlot(layer, 0));
    }
    layer.modules.forEach(function (m) {
      if (!Array.isArray(m.memberIds)) m.memberIds = [];
      if (!m.moduleId) m.moduleId = m.slotId || layer.id + "-mod";
    });
    layer.memberIds = [];
    return layer.modules;
  }

  function sortedModuleMemberIds(mod, nodes) {
    const pool = nodes || (archDoc && archDoc.nodes) || [];
    const ids = (mod && mod.memberIds) || [];
    return ids.slice().sort(function (a, b) {
      const na = pool.find(function (x) {
        return x && x.id === a;
      });
      const nb = pool.find(function (x) {
        return x && x.id === b;
      });
      const oa = na && na.layoutOrder != null ? Number(na.layoutOrder) : 0;
      const ob = nb && nb.layoutOrder != null ? Number(nb.layoutOrder) : 0;
      if (oa !== ob) return oa - ob;
      return String(a).localeCompare(String(b));
    });
  }

  /** Architecture Assignment：由 Module 成員回填 layerRef／moduleRef／order。 */
  function syncArchAssignmentsFromModules(doc) {
    const d = doc || archDoc;
    (d.nodes || []).forEach(function (n) {
      if (!n || n.kind === "Layer") return;
      n.layerRef = null;
      n.moduleRef = null;
      delete n.packedIn;
      delete n.packedSlotId;
    });
    const assigned = {};
    (d.nodes || []).forEach(function (L) {
      if (!L || L.kind !== "Layer") return;
      ensureLayerModules(L).forEach(function (mod) {
        sortedModuleMemberIds(mod, d.nodes).forEach(function (mid, idx) {
          const n = (d.nodes || []).find(function (x) {
            return x && x.id === mid;
          });
          if (!n) return;
          assigned[mid] = true;
          n.layerRef = L.id;
          n.moduleRef = mod.moduleId || mod.slotId;
          if (n.layoutOrder == null) n.layoutOrder = idx;
          n.packedIn = L.id;
          n.packedSlotId = mod.slotId;
        });
      });
    });
    (d.nodes || []).forEach(function (n) {
      if (!n || n.kind === "Layer" || assigned[n.id]) return;
      n.layoutOrder = null;
    });
  }

  function clearNodeAssignment(node) {
    if (!node) return;
    delete node.layerRef;
    delete node.moduleRef;
    delete node.layoutOrder;
    delete node.packedIn;
    delete node.packedSlotId;
  }

  function assignNodeToModule(node, layer, mod) {
    if (!node || !layer || !mod) return;
    const order = (mod.memberIds || []).length;
    node.layerRef = layer.id;
    node.moduleRef = mod.moduleId || mod.slotId;
    node.layoutOrder = order;
    node.packedIn = layer.id;
    node.packedSlotId = mod.slotId;
  }

  /** Spec §6：未歸屬 Module 的 Node（草稿允許；拖出不刪）。 */
  function listUnassignedArchNodes() {
    return (archDoc.nodes || []).filter(function (n) {
      if (!n || !normalizeArchKind(n.kind) || n.kind === "Layer") return false;
      return !findArchLayerContaining(n.id);
    });
  }

  function layerAllMemberIds(layer) {
    const ids = [];
    ensureLayerModules(layer).forEach(function (m) {
      (m.memberIds || []).forEach(function (id) {
        ids.push(id);
      });
    });
    return ids;
  }

  function findArchModuleContaining(nodeId) {
    if (!nodeId) return null;
    for (let i = 0; i < archDoc.nodes.length; i++) {
      const L = archDoc.nodes[i];
      if (!L || L.kind !== "Layer") continue;
      const mods = ensureLayerModules(L);
      for (let j = 0; j < mods.length; j++) {
        if ((mods[j].memberIds || []).indexOf(nodeId) >= 0) {
          return { layer: L, module: mods[j] };
        }
      }
    }
    return null;
  }

  function findArchLayerContaining(nodeId) {
    const hit = findArchModuleContaining(nodeId);
    return hit ? hit.layer : null;
  }

  function effectiveArchEndpoint(nodeId) {
    const layer = findArchLayerContaining(nodeId);
    return layer ? layer.id : nodeId;
  }

  function canPackNodeIntoLayer(node, layer) {
    if (!node || !layer || layer.kind !== "Layer") return false;
    if (node.kind === "Layer") return false;
    if (node.id === layer.id) return false;
    const packs = normalizeArchKind(layer.packsKind);
    if (!packs || node.kind !== packs) return false;
    if (findArchLayerContaining(node.id)) return false;
    return true;
  }

  function packNodeIntoModule(node, layer, mod) {
    if (!canPackNodeIntoLayer(node, layer) || !mod) return false;
    ensureLayerModules(layer);
    if ((mod.memberIds || []).indexOf(node.id) >= 0) {
      assignNodeToModule(node, layer, mod);
      return true;
    }
    mod.memberIds.push(node.id);
    assignNodeToModule(node, layer, mod);
    toast(
      "已移入 " +
        (mod.name || mod.slotId) +
        "（moduleRef=" +
        (mod.moduleId || mod.slotId) +
        "）"
    );
    return true;
  }

  function resolveModuleSlot(layer, preferredSlotId) {
    const mods = ensureLayerModules(layer);
    if (preferredSlotId) {
      for (let i = 0; i < mods.length; i++) {
        if (mods[i].slotId === preferredSlotId) return mods[i];
      }
    }
    return (
      mods.find(function (m) {
        return !m.collapsed;
      }) || mods[0]
    );
  }

  function movePackedNodeToSlot(nodeId, targetLayer, preferredSlotId) {
    const hit = findArchModuleContaining(nodeId);
    const node = findArchNode(nodeId);
    if (!hit || !node || !targetLayer || targetLayer.kind !== "Layer") {
      return false;
    }
    if (hit.layer.id !== targetLayer.id) {
      const packs = normalizeArchKind(targetLayer.packsKind);
      if (!packs || node.kind !== packs || targetLayer.kind !== "Layer") {
        return false;
      }
      ensureLayerModules(hit.layer).forEach(function (m) {
        m.memberIds = (m.memberIds || []).filter(function (id) {
          return id !== nodeId;
        });
      });
      delete node.packedIn;
      delete node.packedSlotId;
      return packNodeIntoModule(
        node,
        targetLayer,
        resolveModuleSlot(targetLayer, preferredSlotId)
      );
    }
    const mod = resolveModuleSlot(targetLayer, preferredSlotId);
    if (!mod) return false;
    if ((mod.memberIds || []).indexOf(nodeId) >= 0) return true;
    ensureLayerModules(hit.layer).forEach(function (m) {
      m.memberIds = (m.memberIds || []).filter(function (id) {
        return id !== nodeId;
      });
    });
    mod.memberIds.push(nodeId);
    assignNodeToModule(node, targetLayer, mod);
    toast("已移至 " + (mod.name || mod.slotId));
    return true;
  }

  function packNodeIntoLayer(node, layer, preferredSlotId) {
    if (!canPackNodeIntoLayer(node, layer)) return false;
    return packNodeIntoModule(
      node,
      layer,
      resolveModuleSlot(layer, preferredSlotId)
    );
  }

  function unpackNodeFromLayer(nodeId, layer) {
    const hit = findArchModuleContaining(nodeId);
    const L = layer || (hit && hit.layer);
    const node = findArchNode(nodeId);
    if (!L || !node) return false;
    ensureLayerModules(L).forEach(function (m) {
      m.memberIds = (m.memberIds || []).filter(function (id) {
        return id !== nodeId;
      });
    });
    clearNodeAssignment(node);
    const n = layerAllMemberIds(L).length;
    node.x = (Number(L.x) || 0) + 24;
    node.y = (Number(L.y) || 0) + 48 + (n % 4) * 28;
    toast("已取出 → 草稿（moduleRef=null）");
    return true;
  }

  function addModuleSlotToLayer(layer) {
    if (!layer || layer.kind !== "Layer") return null;
    const mods = ensureLayerModules(layer);
    const slot = blankModuleSlot(layer, mods.length);
    mods.push(slot);
    persistArchDraft();
    renderArchDag();
    selectArchNode(layer.id);
    toast("已新增 " + slot.name);
    return slot;
  }

  function findLayerDropTarget(node, clientX, clientY) {
    const stage = document.getElementById("archStage");
    if (!stage || !node) return null;
    const sr = stage.getBoundingClientRect();
    const zx = archZoom || 1;
    const px = (clientX - sr.left) / zx;
    const py = (clientY - sr.top) / zx;
    let hitLayer = null;
    let hitSlotId = null;
    archDoc.nodes.forEach(function (L) {
      if (!L || L.kind !== "Layer" || L.id === node.id) return;
      const el = document.querySelector('.arch-node[data-id="' + L.id + '"]');
      if (!el) return;
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      const x = Number(L.x) || 0;
      const y = Number(L.y) || 0;
      if (px < x || px > x + w || py < y || py > y + h) return;
      hitLayer = L;
      const slots = el.querySelectorAll(".arch-module-slot");
      slots.forEach(function (slotEl) {
        const r = slotEl.getBoundingClientRect();
        const sx = (r.left - sr.left) / zx;
        const sy = (r.top - sr.top) / zx;
        const sw = r.width / zx;
        const sh = r.height / zx;
        if (px >= sx && px <= sx + sw && py >= sy && py <= sy + sh) {
          hitSlotId = slotEl.getAttribute("data-slot-id");
        }
      });
    });
    if (!hitLayer) return null;
    return { layer: hitLayer, slotId: hitSlotId };
  }

  function fillArchInspector(node) {
    if (!node) return;
    const nameEl = document.getElementById("archNodeName");
    const typeEl = document.getElementById("archNodeType");
    const idEl = document.getElementById("archNodeId");
    const colEl = document.getElementById("archNodeCollapsed");
    const hint = document.getElementById("archNodeHint");
    const inList = document.getElementById("archInList");
    const outList = document.getElementById("archOutList");
    const membersEl = document.getElementById("archLayerMembers");
    const packsRow = document.getElementById("archLayerPacksRow");
    const packsEl = document.getElementById("archNodePacksKind");
    if (nameEl) nameEl.value = node.name || "";
    const typeLabel = document.getElementById("archNodeTypeLabel");
    if (typeLabel) {
      typeLabel.textContent =
        node.kind === "Layer" ? "Node Type :" : "";
    }
    if (typeEl) {
      typeEl.value =
        node.kind === "Layer"
          ? "Layer"
          : formatArchNodeType(node.kind, node);
    }
    if (idEl) idEl.value = node.id || "";
    const descEl = document.getElementById("archNodeDesc");
    const layerRefEl = document.getElementById("archNodeLayerRef");
    const moduleRefEl = document.getElementById("archNodeModuleRef");
    const orderEl = document.getElementById("archNodeOrder");
    if (descEl) descEl.value = node.description || "";
    if (layerRefEl) {
      layerRefEl.value = node.kind === "Layer" ? node.id : node.layerRef || "";
    }
    if (moduleRefEl) moduleRefEl.value = node.moduleRef || "";
    if (orderEl) {
      orderEl.value =
        node.layoutOrder != null ? String(node.layoutOrder) : "";
      orderEl.disabled = node.kind === "Layer" || !node.moduleRef;
    }
    if (colEl) colEl.checked = !!node.collapsed;
    if (packsRow) packsRow.hidden = node.kind !== "Layer";
    if (packsEl && node.kind === "Layer") {
      packsEl.value = normalizeArchKind(node.packsKind) || "API";
      packsEl.disabled = layerAllMemberIds(node).length > 0;
    }
    const uiPanel = document.getElementById("archUiLayerPanel");
    if (uiPanel) {
      const isUi = isArchUiLayerNode(node);
      uiPanel.hidden = !isUi;
      if (isUi) {
        ensureUiLayerFields(node);
        const lid = document.getElementById("archUiLayerId");
        const def = document.getElementById("archUiDefinitionRef");
        const theme = document.getElementById("archUiThemeRef");
        if (lid) lid.value = node.uiLayerId || node.id;
        if (def) def.value = node.uiDefinitionRef || "";
        if (theme) theme.value = node.themeRef || "";
      }
    }
    const wiPanel = document.getElementById("archWorkItemPanel");
    if (wiPanel) {
      const isWi = isArchWorkItemNode(node);
      wiPanel.hidden = !isWi;
      if (isWi) {
        ensureWorkItemFields(node);
        const setVal = function (id, v) {
          const el = document.getElementById(id);
          if (el) el.value = v == null ? "" : String(v);
        };
        setVal("archWiWorkflow", node.workflowStatus);
        setVal("archWiTest", node.testStatus);
        setVal("archWiLamp", node.displayLamp);
        setVal("archWiPriority", node.priority);
        setVal("archWiAcceptance", node.acceptanceCriteria);
        setVal("archWiBuildDate", node.buildDate);
        setVal("archWiModifiedDate", node.modifiedDate);
        setVal("archWiCompletedDate", node.completedDate);
        setVal("archWiParentRefs", node.parentRefs);
        setVal("archWiDepRefs", node.dependencyRefs);
        setVal("archWiBlocker", node.blockerNote);
        setVal("archWiInTok", node.inputTokens);
        setVal("archWiOutTok", node.outputTokens);
        setVal("archWiCost", node.apiCost);
        const lampDot = document.getElementById("archWiLampDot");
        if (lampDot) {
          lampDot.className =
            "arch-lamp-dot lamp-" +
            String(node.displayLamp || "Gray").toLowerCase();
          lampDot.title = node.displayLamp || "Gray";
        }
        renderArchWorkItemHistory(node);
      } else {
        const hist = document.getElementById("archWorkItemHistory");
        if (hist) {
          hist.hidden = true;
          hist.innerHTML = "";
        }
      }
    }
    const depPanel = document.getElementById("archDeploymentPanel");
    if (depPanel) {
      const isDep = isArchDeploymentNode(node);
      depPanel.hidden = !isDep;
      if (isDep) {
        ensureDeploymentFields(node);
        const setVal = function (id, v) {
          const el = document.getElementById(id);
          if (el) el.value = v == null ? "" : String(v);
        };
        setVal("archDepType", node.deploymentType);
        setVal("archDepTargetRef", node.targetRef);
        const en = document.getElementById("archDepEnabled");
        if (en) en.checked = node.enabled !== false;
        setVal("archDepInputArtifact", node.inputArtifact);
        setVal("archDepArtifactType", node.artifactType);
        setVal("archDepVersion", node.version);
        setVal("archDepChecksum", node.checksumPolicy);
        setVal("archDepEnvironment", node.environment);
        setVal("archDepRuntime", node.runtime);
        setVal("archDepConfigProfile", node.configProfile);
        setVal("archDepSecretRefs", node.secretRefs);
        syncDeploymentStrategyOptions(node.deploymentType, node.strategy);
        setVal("archDepPreChecks", node.preDeployChecks);
        setVal("archDepHealth", node.healthCheck);
        setVal("archDepRollback", node.rollbackPolicy);
        setVal("archDepApproval", node.approvalPolicy);
        setVal("archDepTimeout", node.timeoutSeconds);
        setVal("archDepRetry", node.retryPolicy);
        setVal("archDepResources", node.resourceLimits);
        setVal("archDepCost", node.costBudget);
        setVal("archDepExecStatus", node.executionStatus);
        setVal("archDepLastRun", node.lastRunRef);
      }
    }
    if (hint) {
      const io = ARCH_KIND_IO[node.kind];
      const role = node.role || (io && io.role) || "";
      if (node.kind === "Layer") {
        const mods = ensureLayerModules(node);
        const nMem = layerAllMemberIds(node).length;
        hint.textContent =
          formatArchLayerPacks(node) +
          " · Layer→Module Slot→Node · " +
          mods.length +
          " Modules／" +
          nMem +
          " Nodes" +
          (nMem ? "" : " · 空 Layer 可改 packs");
      } else if (isArchUiLayerNode(node)) {
        hint.textContent =
          "UI Layer · Open Editor／Viewer · ref=" +
          (node.uiDefinitionRef || "—");
      } else if (isArchWorkItemNode(node)) {
        hint.textContent =
          "Work Item · lamp=" +
          (node.displayLamp || "Gray") +
          " · wf=" +
          (node.workflowStatus || "NotStarted") +
          " · test=" +
          (node.testStatus || "NotRun");
      } else if (isArchDeploymentNode(node)) {
        hint.textContent =
          "Deployment · " +
          (node.deploymentType || "desktop") +
          " · " +
          (node.executionStatus || "Idle") +
          " · strategy=" +
          (node.strategy || "replace");
      } else {
        hint.textContent =
          (role ? role + " · " : "") +
          (node.moduleRef
            ? "moduleRef=" + node.moduleRef + " · "
            : "未分配 · ") +
          (node.layerRef ? "layerRef=" + node.layerRef + " · " : "") +
          "類別建立後不可改（要換請＋節點）";
      }
    }
    if (membersEl) {
      membersEl.innerHTML = "";
      membersEl.hidden = node.kind !== "Layer";
      if (node.kind === "Layer") {
        const title = document.createElement("b");
        title.textContent = "Module Slots";
        membersEl.appendChild(title);
        const addBtn = document.createElement("button");
        addBtn.type = "button";
        addBtn.className = "tool-btn";
        addBtn.textContent = "＋ Module Slot";
        addBtn.addEventListener("click", function () {
          if (!archEditMode) {
            toast("請先開「編輯草稿」");
            return;
          }
          addModuleSlotToLayer(node);
        });
        membersEl.appendChild(addBtn);
        ensureLayerModules(node).forEach(function (mod) {
          const box = document.createElement("div");
          box.className = "arch-insp-module";
          const head = document.createElement("div");
          head.className = "arch-insp-module-head";
          const nameInp = document.createElement("input");
          nameInp.type = "text";
          nameInp.value = mod.name || "";
          nameInp.title = "改顯示名稱；moduleId 不變";
          nameInp.setAttribute("aria-label", "Module 顯示名稱");
          nameInp.addEventListener("change", function () {
            if (!archEditMode) {
              toast("請先開「編輯草稿」");
              nameInp.value = mod.name || "";
              return;
            }
            mod.name = nameInp.value.trim() || mod.name;
            persistArchDraft();
            renderArchDag();
            selectArchNode(node.id);
          });
          const idSpan = document.createElement("code");
          idSpan.textContent =
            "moduleId=" +
            (mod.moduleId || mod.slotId) +
            " · " +
            (mod.memberIds || []).length +
            " Nodes";
          head.appendChild(nameInp);
          head.appendChild(idSpan);
          box.appendChild(head);
          const ul = document.createElement("ul");
          sortedModuleMemberIds(mod).forEach(function (mid) {
            const m = findArchNode(mid);
            const li = document.createElement("li");
            li.textContent = m
              ? (m.name || m.id) +
                " (" +
                (m.kind || "") +
                ")" +
                (m.layoutOrder != null ? " #" + m.layoutOrder : "")
              : mid;
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "tool-btn";
            btn.textContent = "取出";
            btn.addEventListener("click", function () {
              if (!archEditMode) {
                toast("請先開「編輯草稿」");
                return;
              }
              unpackNodeFromLayer(mid, node);
              persistArchDraft();
              renderArchDag();
              selectArchNode(node.id);
            });
            li.appendChild(btn);
            ul.appendChild(li);
          });
          if (!(mod.memberIds || []).length) {
            const empty = document.createElement("p");
            empty.className = "hint";
            empty.textContent = "尚無 Node；拖入同屬性節點。";
            box.appendChild(empty);
          } else {
            box.appendChild(ul);
          }
          membersEl.appendChild(box);
        });
      }
    }
    if (inList) {
      inList.innerHTML = "";
      (node.inputs || []).forEach(function (p) {
        const li = document.createElement("li");
        li.textContent = (p.label || p.id) + " (" + p.id + ")";
        inList.appendChild(li);
      });
    }
    if (outList) {
      outList.innerHTML = "";
      (node.outputs || []).forEach(function (p) {
        const li = document.createElement("li");
        li.textContent = (p.label || p.id) + " (" + p.id + ")";
        outList.appendChild(li);
      });
    }
    const selTitle = document.getElementById("inspector-sel-title");
    const selBody = document.getElementById("inspector-sel-body");
    if (selTitle) selTitle.textContent = "架構：" + (node.name || node.id);
    if (selBody) {
      selBody.textContent =
        formatArchNodeType(node.kind, node) +
        " · id=" +
        node.id +
        (node.collapsed ? " · 收合" : " · 展開");
    }
  }

  function syncArchDeleteUi() {
    const ids = getArchSelectedIds();
    const hasSel = ids.length > 0;
    const canDel = !!archEditMode && hasSel;
    const canArrange = !!archEditMode && ids.length >= 2;
    const btn = document.getElementById("arch-delete-node");
    const insp = document.getElementById("arch-inspector-delete");
    const focusBtn = document.getElementById("arch-focus-selected");
    const arrangeAuto = document.getElementById("arch-arrange-auto");
    const arrangeH = document.getElementById("arch-arrange-h");
    const arrangeV = document.getElementById("arch-arrange-v");
    if (btn) {
      btn.disabled = !canDel;
      btn.title =
        ids.length > 1
          ? "刪除選取 " + ids.length + " 個節點（Delete）"
          : "刪除選取節點（Delete）";
    }
    if (insp) insp.disabled = !canDel;
    if (focusBtn) focusBtn.disabled = !hasSel;
    if (arrangeAuto) arrangeAuto.disabled = !canArrange;
    if (arrangeH) arrangeH.disabled = !canArrange;
    if (arrangeV) arrangeV.disabled = !canArrange;
  }

  function getArchSelectedIds() {
    return (archSelectedIds || []).filter(function (id) {
      return !!findArchNode(id);
    });
  }

  function refreshArchSelectionChrome() {
    const set = {};
    getArchSelectedIds().forEach(function (id) {
      set[id] = true;
    });
    document.querySelectorAll(".arch-node").forEach(function (el) {
      const id = el.getAttribute("data-id");
      el.classList.toggle("is-selected", !!set[id]);
    });
    syncArchDeleteUi();
  }

  /** 設定多選；primary 供 Inspector。opts.toggle／additive 用於 Ctrl／Shift。 */
  function setArchSelection(ids, primaryId) {
    const uniq = [];
    const seen = {};
    (ids || []).forEach(function (id) {
      if (!id || seen[id] || !findArchNode(id)) return;
      seen[id] = true;
      uniq.push(id);
    });
    archSelectedIds = uniq;
    if (primaryId && seen[primaryId]) {
      archSelectedId = primaryId;
    } else {
      archSelectedId = uniq.length ? uniq[uniq.length - 1] : null;
    }
    refreshArchSelectionChrome();
    const node = findArchNode(archSelectedId);
    if (node) {
      setArchInspectorActive(true);
      fillArchInspector(node);
    } else {
      setArchInspectorActive(false);
    }
  }

  function selectArchNode(id, opts) {
    opts = opts || {};
    if (!id) {
      setArchSelection([], null);
      return;
    }
    if (!findArchNode(id)) {
      setArchSelection(
        getArchSelectedIds().filter(function (x) {
          return x !== id;
        }),
        null
      );
      return;
    }
    if (opts.toggle) {
      const cur = getArchSelectedIds();
      const i = cur.indexOf(id);
      if (i >= 0) {
        cur.splice(i, 1);
        setArchSelection(cur, cur[cur.length - 1] || null);
      } else {
        cur.push(id);
        setArchSelection(cur, id);
      }
      return;
    }
    if (opts.additive) {
      const cur = getArchSelectedIds();
      if (cur.indexOf(id) < 0) cur.push(id);
      setArchSelection(cur, id);
      return;
    }
    if (opts.keepIfSelected && getArchSelectedIds().indexOf(id) >= 0) {
      archSelectedId = id;
      refreshArchSelectionChrome();
      fillArchInspector(findArchNode(id));
      setArchInspectorActive(true);
      return;
    }
    setArchSelection([id], id);
  }

  function clientToArchStage(clientX, clientY) {
    const stage = document.getElementById("archStage");
    if (!stage) return { x: 0, y: 0 };
    const sr = stage.getBoundingClientRect();
    const z = archZoom || 1;
    return {
      x: (clientX - sr.left) / z,
      y: (clientY - sr.top) / z,
    };
  }

  function updateArchMarqueeEl() {
    const el = document.getElementById("archMarquee");
    if (!el || !archMarquee) {
      if (el) el.hidden = true;
      return;
    }
    const x = Math.min(archMarquee.x0, archMarquee.x1);
    const y = Math.min(archMarquee.y0, archMarquee.y1);
    const w = Math.abs(archMarquee.x1 - archMarquee.x0);
    const h = Math.abs(archMarquee.y1 - archMarquee.y0);
    el.hidden = false;
    el.style.left = x + "px";
    el.style.top = y + "px";
    el.style.width = w + "px";
    el.style.height = h + "px";
  }

  function clearArchMarquee() {
    archMarquee = null;
    const el = document.getElementById("archMarquee");
    if (el) {
      el.hidden = true;
      el.style.width = "0";
      el.style.height = "0";
    }
    document.body.classList.remove("is-arch-marquee");
  }

  function archNodeStageRect(n) {
    if (!n) return null;
    const el = document.querySelector('.arch-node[data-id="' + n.id + '"]');
    const w = el ? el.offsetWidth : 160;
    const h = el ? el.offsetHeight : 48;
    const x = Number(n.x) || 0;
    const y = Number(n.y) || 0;
    return { x: x, y: y, w: w, h: h, r: x + w, b: y + h };
  }

  function rectsIntersect(a, b) {
    return !(a.r < b.x || b.r < a.x || a.b < b.y || b.b < a.y);
  }

  function collectArchNodesInMarquee() {
    if (!archMarquee) return [];
    const box = {
      x: Math.min(archMarquee.x0, archMarquee.x1),
      y: Math.min(archMarquee.y0, archMarquee.y1),
      r: Math.max(archMarquee.x0, archMarquee.x1),
      b: Math.max(archMarquee.y0, archMarquee.y1),
    };
    box.w = box.r - box.x;
    box.h = box.b - box.y;
    const hit = [];
    archDoc.nodes.forEach(function (n) {
      if (!normalizeArchKind(n.kind)) return;
      if (n.kind !== "Layer" && findArchLayerContaining(n.id)) return;
      if (!archNodePassesFilter(n)) return;
      const nr = archNodeStageRect(n);
      if (nr && rectsIntersect(box, nr)) hit.push(n.id);
    });
    return hit;
  }

  function archNodePassesFilter(n) {
    if (!n) return false;
    if (!archKindFilter || archKindFilter === "all") return true;
    if (n.kind === archKindFilter) return true;
    if (
      n.kind === "Layer" &&
      normalizeArchKind(n.packsKind) === archKindFilter
    ) {
      return true;
    }
    return false;
  }

  function setArchKindFilter(kind) {
    const k = String(kind || "all");
    if (k === "all" || normalizeArchKind(k)) {
      archKindFilter = k === "all" ? "all" : normalizeArchKind(k);
    } else {
      archKindFilter = "all";
    }
    document.querySelectorAll("[data-arch-filter]").forEach(function (btn) {
      const on = btn.getAttribute("data-arch-filter") === archKindFilter;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    renderArchDag();
  }

  function renderArchKindFilterBar() {
    const host = document.getElementById("arch-kind-filter");
    if (!host) return;
    const allBtn = host.querySelector('[data-arch-filter="all"]');
    host.innerHTML = "";
    const all = document.createElement("button");
    all.type = "button";
    all.className =
      "arch-filter-chip" + (archKindFilter === "all" ? " is-active" : "");
    all.setAttribute("data-arch-filter", "all");
    all.setAttribute("aria-pressed", archKindFilter === "all" ? "true" : "false");
    all.title = "顯示全部";
    all.textContent = "全部";
    all.addEventListener("click", function () {
      setArchKindFilter("all");
    });
    host.appendChild(all);
    if (allBtn) {
      /* rebuilt */
    }
    ARCH_NODE_KINDS.forEach(function (kind) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "arch-filter-chip" +
        (archKindFilter === kind ? " is-active" : "");
      btn.setAttribute("data-arch-filter", kind);
      btn.setAttribute(
        "aria-pressed",
        archKindFilter === kind ? "true" : "false"
      );
      btn.title = "篩選：" + kind;
      const img = document.createElement("img");
      img.src = archKindIconSrc(kind);
      img.alt = "";
      img.width = 16;
      img.height = 16;
      img.decoding = "async";
      const lab = document.createElement("span");
      lab.textContent = kind;
      btn.appendChild(img);
      btn.appendChild(lab);
      btn.addEventListener("click", function () {
        setArchKindFilter(
          archKindFilter === kind ? "all" : kind
        );
      });
      host.appendChild(btn);
    });
  }

  function deleteArchNode(id) {
    if (!archEditMode) {
      toast("請先開「編輯草稿」再刪除");
      return false;
    }
    let ids = id
      ? [id]
      : getArchSelectedIds();
    if (!ids.length && archSelectedId) ids = [archSelectedId];
    ids = ids.filter(function (nid) {
      return !!findArchNode(nid);
    });
    if (!ids.length) {
      toast("未選取節點");
      return false;
    }
    ids.forEach(function (nodeId) {
      const node = findArchNode(nodeId);
      if (!node) return;
      if (node.kind === "Layer") {
        layerAllMemberIds(node).slice().forEach(function (mid) {
          unpackNodeFromLayer(mid, node);
        });
      }
      const parent = findArchLayerContaining(node.id);
      if (parent) unpackNodeFromLayer(node.id, parent);
      archDoc.edges = (archDoc.edges || []).filter(function (e) {
        return e.fromNode !== node.id && e.toNode !== node.id;
      });
      archDoc.nodes = (archDoc.nodes || []).filter(function (n) {
        return n.id !== node.id;
      });
    });
    persistArchDraft();
    renderArchDag();
    setArchSelection([], null);
    toast(ids.length > 1 ? "已刪除 " + ids.length + " 個節點" : "已刪除節點");
    return true;
  }

  function applyArchInspectorInputs() {
    const node = findArchNode(archSelectedId);
    if (!node || !archEditMode) return;
    const nameEl = document.getElementById("archNodeName");
    const colEl = document.getElementById("archNodeCollapsed");
    const packsEl = document.getElementById("archNodePacksKind");
    const descEl = document.getElementById("archNodeDesc");
    const orderEl = document.getElementById("archNodeOrder");
    if (nameEl) node.name = nameEl.value || node.name;
    if (descEl) node.description = descEl.value || "";
    /* Node Type 建立後不可重新定義；要換類型必須＋節點重新新增 */
    if (
      node.kind === "Layer" &&
      packsEl &&
      !layerAllMemberIds(node).length
    ) {
      const packs = normalizeArchKind(packsEl.value);
      if (packs && ARCH_PACKABLE_KINDS.indexOf(packs) >= 0) {
        node.packsKind = packs;
        node.role = "Pack " + packs;
      } else {
        toast("拒絕：Layer packs 必須是 PDF Node Type（非 Layer）");
        packsEl.value = node.packsKind || "API";
      }
    }
    if (colEl) node.collapsed = !!colEl.checked;
    if (orderEl && node.moduleRef && !orderEl.disabled) {
      const o = Number(orderEl.value);
      if (!Number.isNaN(o)) node.layoutOrder = o;
    }
    if (isArchUiLayerNode(node)) {
      ensureUiLayerFields(node);
      const def = document.getElementById("archUiDefinitionRef");
      const theme = document.getElementById("archUiThemeRef");
      if (def) node.uiDefinitionRef = def.value.trim() || node.uiDefinitionRef;
      if (theme) node.themeRef = theme.value.trim();
      node.uiLayerId = node.uiLayerId || node.id;
    }
    if (isArchWorkItemNode(node)) {
      const before = {
        workflowStatus: node.workflowStatus,
        testStatus: node.testStatus,
        displayLamp: node.displayLamp,
        priority: node.priority,
        acceptanceCriteria: node.acceptanceCriteria,
        blockerNote: node.blockerNote,
      };
      const getVal = function (id) {
        const el = document.getElementById(id);
        return el ? el.value.trim() : "";
      };
      node.workflowStatus = getVal("archWiWorkflow") || node.workflowStatus;
      node.testStatus = getVal("archWiTest") || node.testStatus;
      node.priority = getVal("archWiPriority") || node.priority;
      node.acceptanceCriteria = getVal("archWiAcceptance");
      node.buildDate = getVal("archWiBuildDate");
      node.modifiedDate =
        getVal("archWiModifiedDate") || new Date().toISOString().slice(0, 10);
      node.completedDate = getVal("archWiCompletedDate");
      node.parentRefs = getVal("archWiParentRefs");
      node.dependencyRefs = getVal("archWiDepRefs");
      node.blockerNote = getVal("archWiBlocker");
      const it = Number(getVal("archWiInTok"));
      if (!Number.isNaN(it)) node.inputTokens = it;
      const ot = Number(getVal("archWiOutTok"));
      if (!Number.isNaN(ot)) node.outputTokens = ot;
      node.apiCost = getVal("archWiCost");
      ensureWorkItemFields(node);
      const changes = [];
      Object.keys(before).forEach(function (k) {
        if (String(before[k] || "") !== String(node[k] || "")) {
          changes.push({
            field: k,
            before: before[k],
            after: node[k],
          });
        }
      });
      if (changes.length) {
        appendArchEvent(node.id, "node.property.updated", { changes: changes });
      }
    }
    if (isArchDeploymentNode(node)) {
      ensureDeploymentFields(node);
      const getVal = function (id) {
        const el = document.getElementById(id);
        return el ? el.value.trim() : "";
      };
      const typeEl = document.getElementById("archDepType");
      if (typeEl) node.deploymentType = normalizeDeploymentType(typeEl.value);
      node.targetRef = getVal("archDepTargetRef");
      const en = document.getElementById("archDepEnabled");
      if (en) node.enabled = !!en.checked;
      node.inputArtifact = getVal("archDepInputArtifact");
      node.artifactType = getVal("archDepArtifactType") || node.artifactType;
      node.version = getVal("archDepVersion");
      node.checksumPolicy = getVal("archDepChecksum") || node.checksumPolicy;
      node.environment = getVal("archDepEnvironment") || node.environment;
      node.runtime = getVal("archDepRuntime");
      node.configProfile = getVal("archDepConfigProfile");
      node.secretRefs = getVal("archDepSecretRefs");
      node.strategy = getVal("archDepStrategy") || node.strategy;
      node.preDeployChecks = getVal("archDepPreChecks");
      node.healthCheck = getVal("archDepHealth");
      node.rollbackPolicy = getVal("archDepRollback");
      node.approvalPolicy = getVal("archDepApproval");
      const to = Number(getVal("archDepTimeout"));
      if (!Number.isNaN(to)) node.timeoutSeconds = to;
      node.retryPolicy = getVal("archDepRetry");
      node.resourceLimits = getVal("archDepResources");
      node.costBudget = getVal("archDepCost");
      node.executionStatus =
        getVal("archDepExecStatus") || node.executionStatus;
      ensureDeploymentFields(node);
    }
    persistArchDraft();
    renderArchDag();
    selectArchNode(node.id);
  }

  function setArchInspectorTab(tab) {
    const want = tab || "basic";
    document.querySelectorAll("[data-arch-tab]").forEach(function (btn) {
      const on = btn.getAttribute("data-arch-tab") === want;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll("[data-arch-panel]").forEach(function (panel) {
      const on = panel.getAttribute("data-arch-panel") === want;
      panel.classList.toggle("is-active", on);
      panel.hidden = !on;
    });
  }

  /** 與 Node→Layer 相同：packsKind 必須吻合（已打包者可改槽／換 Layer）。 */
  function canAcceptNodeInLayer(node, layer) {
    if (!node || !layer || layer.kind !== "Layer") return false;
    if (node.kind === "Layer" || node.id === layer.id) return false;
    const packs = normalizeArchKind(layer.packsKind);
    return !!(packs && node.kind === packs);
  }

  function clearArchTreeDropHighlights() {
    document
      .querySelectorAll(".arch-tree-drop.is-drop-target")
      .forEach(function (el) {
        el.classList.remove("is-drop-target");
      });
  }

  function findArchTreeDropTarget(clientX, clientY, dragNodeId) {
    const el = document.elementFromPoint(clientX, clientY);
    if (!el || !el.closest) return null;
    const draft = el.closest("[data-tree-draft]");
    if (draft) return { type: "draft", el: draft };
    const mod = el.closest("[data-tree-module]");
    if (mod) {
      const layerId = mod.getAttribute("data-layer-id");
      const slotId = mod.getAttribute("data-slot-id");
      const layer = findArchNode(layerId);
      const node = findArchNode(dragNodeId);
      if (!layer || !node || !canAcceptNodeInLayer(node, layer)) return null;
      return { type: "module", layer: layer, slotId: slotId, el: mod };
    }
    const layerEl = el.closest("[data-tree-layer]");
    if (layerEl) {
      const layerId = layerEl.getAttribute("data-layer-id");
      const layer = findArchNode(layerId);
      const node = findArchNode(dragNodeId);
      if (!layer || !node || !canAcceptNodeInLayer(node, layer)) return null;
      return { type: "layer", layer: layer, el: layerEl };
    }
    return null;
  }

  function applyArchTreeDrop(dragNodeId, drop) {
    const node = findArchNode(dragNodeId);
    if (!node || !drop) return false;
    if (drop.type === "draft") {
      const hit = findArchModuleContaining(dragNodeId);
      if (!hit) return false;
      unpackNodeFromLayer(dragNodeId, hit.layer);
      persistArchDraft();
      return true;
    }
    if (drop.type === "layer" || drop.type === "module") {
      const layer = drop.layer;
      const slotId = drop.type === "module" ? drop.slotId : null;
      if (!canAcceptNodeInLayer(node, layer)) {
        toast(
          "無法移入：Layer 只收 " +
            (layer.packsKind || "?") +
            "（目前 " +
            node.kind +
            "）"
        );
        return false;
      }
      if (findArchLayerContaining(node.id)) {
        movePackedNodeToSlot(node.id, layer, slotId);
      } else {
        packNodeIntoLayer(node, layer, slotId);
      }
      if (layer && layer.id) archUnassignedTreeOpen["layer:" + layer.id] = true;
      if (slotId) archUnassignedTreeOpen["mod:" + slotId] = true;
      persistArchDraft();
      return true;
    }
    return false;
  }

  function wireArchTreeNodeDrag(chip, n) {
    chip.addEventListener("click", function () {
      if (archTrayDrag) return;
      selectArchNode(n.id);
      focusArchSelectedNode();
    });
    chip.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 0) return;
      if (n.kind === "Layer") return;
      ev.preventDefault();
      archTrayDrag = {
        nodeId: n.id,
        startX: ev.clientX,
        startY: ev.clientY,
      };
      document.body.classList.add("is-arch-dragging");
      try {
        chip.setPointerCapture(ev.pointerId);
      } catch (_e) {
        /* ignore */
      }
    });
  }

  function makeArchTreeTwist(key, open, onToggle) {
    const twist = document.createElement("button");
    twist.type = "button";
    twist.className = "arch-tree-twist";
    twist.innerHTML = '<span class="arch-tree-chevron" aria-hidden="true"></span>';
    twist.title = open ? "收合" : "展開";
    twist.addEventListener("click", function (ev) {
      ev.stopPropagation();
      onToggle(!open);
    });
    return twist;
  }

  function makeArchTreeRow(opts) {
    const depth = opts.depth || 0;
    const wrap = document.createElement("div");
    wrap.className =
      "arch-tree-node" + (opts.open ? " is-open" : "");
    wrap.setAttribute("role", "treeitem");
    wrap.setAttribute(
      "aria-expanded",
      opts.hasKids ? (opts.open ? "true" : "false") : "false"
    );
    wrap.style.setProperty("--arch-tree-depth", String(depth));

    const row = document.createElement("div");
    row.className = "arch-tree-row";

    if (opts.hasKids) {
      row.appendChild(
        makeArchTreeTwist(opts.openKey, opts.open, function (next) {
          archUnassignedTreeOpen[opts.openKey] = next;
          renderArchUnassigned();
        })
      );
    } else {
      const spacer = document.createElement("span");
      spacer.className = "arch-tree-twist is-leaf";
      spacer.setAttribute("aria-hidden", "true");
      row.appendChild(spacer);
    }

    const chip = document.createElement("button");
    chip.type = "button";
    chip.className =
      "arch-unassigned-chip arch-tree-leaf arch-tree-drop" +
      (opts.selected ? " is-selected" : "") +
      (opts.dropClass ? " " + opts.dropClass : "");
    Object.keys(opts.attrs || {}).forEach(function (k) {
      chip.setAttribute(k, opts.attrs[k]);
    });
    chip.innerHTML = opts.html || "";
    chip.title = opts.title || "";
    if (opts.onChip) opts.onChip(chip);
    row.appendChild(chip);
    wrap.appendChild(row);

    if (opts.hasKids) {
      const children = document.createElement("div");
      children.className = "arch-tree-children";
      children.setAttribute("role", "group");
      if (!opts.open) children.hidden = true;
      (opts.children || []).forEach(function (childEl) {
        children.appendChild(childEl);
      });
      wrap.appendChild(children);
    }
    return wrap;
  }

  function renderArchTreeMemberRow(n, depth) {
    return makeArchTreeRow({
      depth: depth,
      hasKids: false,
      open: false,
      openKey: "n:" + n.id,
      selected: getArchSelectedIds().indexOf(n.id) >= 0,
      attrs: {
        "data-node-id": n.id,
        "data-tree-node": "1",
      },
      html:
        '<img src="' +
        escapeHtml(archKindIconSrc(n.kind)) +
        '" alt="" width="14" height="14" />' +
        "<span>" +
        escapeHtml(n.name || n.id) +
        '</span><em>' +
        escapeHtml(formatArchNodeType(n.kind) || n.kind || "") +
        "</em>",
      title: "拖到 Layer／Module（須同 packsKind）＝移入；拖到草稿＝取出",
      onChip: function (chip) {
        wireArchTreeNodeDrag(chip, n);
      },
    });
  }

  function renderArchTreeModuleBranch(layer, mod, depth) {
    const memberIds = sortedModuleMemberIds(mod).filter(function (mid) {
      const mn = findArchNode(mid);
      return mn && archNodePassesFilter(mn);
    });
    const openKey = "mod:" + (mod.slotId || mod.moduleId);
    const open =
      archUnassignedTreeOpen[openKey] == null
        ? true
        : !!archUnassignedTreeOpen[openKey];
    const kids = memberIds.map(function (mid) {
      return renderArchTreeMemberRow(findArchNode(mid), depth + 1);
    });
    return makeArchTreeRow({
      depth: depth,
      hasKids: true,
      open: open,
      openKey: openKey,
      selected: false,
      dropClass: "is-module-drop",
      attrs: {
        "data-tree-module": "1",
        "data-layer-id": layer.id,
        "data-slot-id": mod.slotId || "",
      },
      html:
        "<span>" +
        escapeHtml(mod.name || mod.slotId || "Module") +
        '</span><em class="arch-tree-count">' +
        memberIds.length +
        "</em>",
      title:
        "Module Slot（只收 " +
        (layer.packsKind || "?") +
        "）— 拖入 Node 同畫布規則",
      onChip: function (chip) {
        chip.addEventListener("click", function () {
          selectArchNode(layer.id);
        });
      },
      children: kids,
    });
  }

  function renderArchTreeLayerBranch(layer, depth) {
    const mods = ensureLayerModules(layer);
    const openKey = "layer:" + layer.id;
    const open =
      archUnassignedTreeOpen[openKey] == null
        ? true
        : !!archUnassignedTreeOpen[openKey];
    const kids = mods.map(function (mod) {
      return renderArchTreeModuleBranch(layer, mod, depth + 1);
    });
    const nMem = layerAllMemberIds(layer).filter(function (mid) {
      const mn = findArchNode(mid);
      return mn && archNodePassesFilter(mn);
    }).length;
    return makeArchTreeRow({
      depth: depth,
      hasKids: true,
      open: open,
      openKey: openKey,
      selected: getArchSelectedIds().indexOf(layer.id) >= 0,
      dropClass: "is-layer-drop",
      attrs: {
        "data-tree-layer": "1",
        "data-layer-id": layer.id,
      },
      html:
        '<img src="' +
        escapeHtml(archKindIconSrc("Layer")) +
        '" alt="" width="14" height="14" />' +
        "<span>" +
        escapeHtml(layer.name || formatArchLayerPacks(layer) || layer.id) +
        '</span><em>' +
        escapeHtml(formatArchLayerPacks(layer) || "") +
        ' · ' +
        nMem +
        "</em>",
      title:
        "Layer（packs=" +
        (layer.packsKind || "?") +
        "）— 拖入同屬性 Node＝子節點／打包",
      onChip: function (chip) {
        chip.addEventListener("click", function () {
          selectArchNode(layer.id);
          focusArchSelectedNode();
        });
      },
      children: kids,
    });
  }

  function renderArchTreeDraftBranch(draftNodes, depth) {
    const openKey = "draft";
    const open =
      archUnassignedTreeOpen[openKey] == null
        ? true
        : !!archUnassignedTreeOpen[openKey];
    const kids = draftNodes.map(function (n) {
      return renderArchTreeMemberRow(n, depth + 1);
    });
    return makeArchTreeRow({
      depth: depth,
      hasKids: true,
      open: open,
      openKey: openKey,
      selected: false,
      dropClass: "is-draft-drop",
      attrs: {
        "data-tree-draft": "1",
      },
      html:
        "<span>草稿</span><em class=\"arch-tree-count\">" +
        draftNodes.length +
        "</em>",
      title: "尚未歸屬 Module 的 Node；拖到此處＝從 Layer 取出",
      onChip: function () {},
      children: kids,
    });
  }

  function renderArchUnassigned() {
    const list = document.getElementById("arch-unassigned-list");
    const countEl = document.getElementById("arch-unassigned-count");
    if (!list) return;
    syncArchAssignmentsFromModules(archDoc);
    const layers = (archDoc.nodes || []).filter(function (n) {
      return n && n.kind === "Layer" && archNodePassesFilter(n);
    });
    layers.sort(function (a, b) {
      return String(a.name || a.id).localeCompare(String(b.name || b.id));
    });
    const draft = listUnassignedArchNodes().filter(function (n) {
      return archNodePassesFilter(n);
    });
    let total = draft.length;
    layers.forEach(function (L) {
      total += layerAllMemberIds(L).filter(function (mid) {
        const mn = findArchNode(mid);
        return mn && archNodePassesFilter(mn);
      }).length;
    });
    if (countEl) countEl.textContent = String(total);
    list.innerHTML = "";
    list.setAttribute("role", "tree");
    clearArchTreeDropHighlights();
    if (!layers.length && !draft.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "尚無 Layer／節點";
      list.appendChild(empty);
      return;
    }
    layers.forEach(function (L) {
      list.appendChild(renderArchTreeLayerBranch(L, 0));
    });
    list.appendChild(renderArchTreeDraftBranch(draft, 0));
  }

  function portAnchor(node, portId, side) {
    const el = document.querySelector(
      '.arch-node[data-id="' +
        node.id +
        '"] .arch-port[data-port-id="' +
        portId +
        '"]'
    );
    const nodeEl = document.querySelector(
      '.arch-node[data-id="' + node.id + '"]'
    );
    if (node.collapsed || !el || !nodeEl) {
      const w = nodeEl ? nodeEl.offsetWidth : 120;
      const h = nodeEl ? nodeEl.offsetHeight : 10;
      return {
        x: node.x + (side === "out" ? w : 0),
        y: node.y + h / 2,
      };
    }
    const nr = nodeEl.getBoundingClientRect();
    const pr = el.getBoundingClientRect();
    const stage = document.getElementById("archStage");
    const sr = stage.getBoundingClientRect();
    const zx = archZoom || 1;
    return {
      x: (pr.left + pr.width / 2 - sr.left) / zx,
      y: (pr.top + pr.height / 2 - sr.top) / zx,
    };
  }

  function renderArchEdges() {
    const svg = document.getElementById("archEdgesSvg");
    if (!svg) return;
    const size = archStageSize();
    svg.setAttribute("viewBox", "0 0 " + size.w + " " + size.h);
    svg.innerHTML =
      '<defs><marker id="archArrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6a7380"></path></marker></defs>';
    /* 打包後：端點上提至 Layer；同 Layer 內隱藏；不同 Layer 只留一條線；篩選後只畫可見端 */
    const seenPair = Object.create(null);
    archDoc.edges.forEach(function (e) {
      const fromId = effectiveArchEndpoint(e.fromNode);
      const toId = effectiveArchEndpoint(e.toNode);
      if (!fromId || !toId || fromId === toId) return;
      const pairKey = fromId + "\0" + toId;
      if (seenPair[pairKey]) return;
      seenPair[pairKey] = true;
      const from = findArchNode(fromId);
      const to = findArchNode(toId);
      if (!from || !to) return;
      if (!archNodePassesFilter(from) || !archNodePassesFilter(to)) return;
      const fromPort =
        from.kind === "Layer" || fromId !== e.fromNode
          ? (from.outputs && from.outputs[0] && from.outputs[0].id) || e.fromPort
          : e.fromPort;
      const toPort =
        to.kind === "Layer" || toId !== e.toNode
          ? (to.inputs && to.inputs[0] && to.inputs[0].id) || e.toPort
          : e.toPort;
      const a = portAnchor(from, fromPort, "out");
      const b = portAnchor(to, toPort, "in");
      const dx = Math.max(40, (b.x - a.x) / 2);
      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path"
      );
      path.setAttribute(
        "d",
        "M" +
          a.x +
          "," +
          a.y +
          " C" +
          (a.x + dx) +
          "," +
          a.y +
          " " +
          (b.x - dx) +
          "," +
          b.y +
          " " +
          b.x +
          "," +
          b.y
      );
      if (from.kind === "Layer" || to.kind === "Layer") {
        path.setAttribute("class", "arch-edge-layer");
        path.setAttribute("stroke-width", "2.5");
      }
      svg.appendChild(path);
    });
    if (archLink && archLink.start) {
      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path"
      );
      path.setAttribute(
        "d",
        "M" +
          archLink.start.x +
          "," +
          archLink.start.y +
          " L" +
          archLink.cur.x +
          "," +
          archLink.cur.y
      );
      path.setAttribute("stroke-dasharray", "4 3");
      svg.appendChild(path);
    }
  }

  function renderArchDag() {
    const host = document.getElementById("archNodes");
    if (!host) return;
    host.innerHTML = "";
    archDoc.nodes.forEach(function (n) {
      if (!normalizeArchKind(n.kind)) return;
      /* 已打包進 Layer 的節點不單獨繪製（對外只見 Layer 單線） */
      if (n.kind !== "Layer" && findArchLayerContaining(n.id)) return;
      if (!archNodePassesFilter(n)) return;
      const el = document.createElement("div");
      el.className =
        "arch-node" +
        (n.kind === "Layer" ? " is-layer" : "") +
        (n.collapsed ? " is-collapsed" : "") +
        (getArchSelectedIds().indexOf(n.id) >= 0 ? " is-selected" : "");
      el.setAttribute("data-id", n.id);
      el.setAttribute("data-kind", n.kind);
      if (n.kind === "Layer" && n.packsKind) {
        el.setAttribute("data-packs-kind", n.packsKind);
      }
      el.style.left = (Number(n.x) || 0) + "px";
      el.style.top = (Number(n.y) || 0) + "px";
      const inPorts = (n.inputs || [])
        .map(function (p) {
          return (
            '<button type="button" class="arch-port is-in" data-port-id="' +
            escapeHtml(p.id) +
            '" data-side="in">' +
            escapeHtml(p.label || "in") +
            "</button>"
          );
        })
        .join("");
      const outPorts = (n.outputs || [])
        .map(function (p) {
          return (
            '<button type="button" class="arch-port is-out" data-port-id="' +
            escapeHtml(p.id) +
            '" data-side="out">' +
            escapeHtml(p.label || "out") +
            "</button>"
          );
        })
        .join("");
      let membersHtml = "";
      if (n.kind === "Layer") {
        const mods = ensureLayerModules(n);
        const totalNodes = layerAllMemberIds(n).length;
        if (n.collapsed) {
          membersHtml =
            '<div class="arch-layer-members is-compact">' +
            escapeHtml(String(mods.length)) +
            " Modules · " +
            escapeHtml(String(totalNodes)) +
            " Nodes</div>";
        } else {
          const slotsHtml = mods
            .map(function (mod) {
              const memberIds = sortedModuleMemberIds(mod);
              const count = memberIds.length;
              const open = !mod.collapsed;
              const nodesRow = open
                ? memberIds
                    .map(function (mid) {
                      const mn = findArchNode(mid);
                      const label = mn ? mn.name || mn.id : mid;
                      return (
                        '<span class="arch-module-node" data-member-id="' +
                        escapeHtml(mid) +
                        '" title="' +
                        escapeHtml(label) +
                        '"><i class="arch-io">I</i><span>' +
                        escapeHtml(label) +
                        '</span><i class="arch-io">O</i></span>'
                      );
                    })
                    .join("") ||
                  '<span class="arch-layer-drop-hint">拖入同屬性 Node</span>'
                : "";
              return (
                '<div class="arch-module-slot" data-slot-id="' +
                escapeHtml(mod.slotId) +
                '" data-open="' +
                (open ? "true" : "false") +
                '">' +
                '<button type="button" class="arch-module-toggle" data-slot-id="' +
                escapeHtml(mod.slotId) +
                '" aria-expanded="' +
                (open ? "true" : "false") +
                '" title="展開／收合 Module（不刪 Node）">' +
                '<span class="arch-module-chevron">' +
                (open ? "▾" : "▸") +
                '</span><span class="arch-module-title">' +
                escapeHtml(mod.name || mod.slotId) +
                '</span><span class="arch-module-count">' +
                escapeHtml(String(count)) +
                " Nodes</span></button>" +
                (open
                  ? '<div class="arch-module-nodes" aria-label="Module 內 Nodes">' +
                    nodesRow +
                    "</div>"
                  : "") +
                "</div>"
              );
            })
            .join("");
          membersHtml =
            '<div class="arch-layer-modules" aria-label="Module Slots">' +
            slotsHtml +
            '<button type="button" class="tool-btn arch-add-module" data-layer-id="' +
            escapeHtml(n.id) +
            '">＋ Module Slot</button></div>';
        }
      }
      el.innerHTML =
        '<div class="arch-node-line" aria-hidden="true"></div>' +
        '<div class="arch-node-head">' +
        '<img class="arch-node-icon" src="' +
        escapeHtml(archKindIconSrc(n.kind)) +
        '" alt="" width="18" height="18" decoding="async" />' +
        '<div class="arch-node-body">' +
        "<strong>" +
        escapeHtml(n.name || n.id) +
        '</strong><span class="arch-node-kind">' +
        escapeHtml(formatArchNodeType(n.kind, n)) +
        "</span><em>" +
        escapeHtml(
          n.kind === "Layer"
            ? formatArchLayerPacks(n)
            : n.role ||
                (ARCH_KIND_IO[n.kind] && ARCH_KIND_IO[n.kind].role) ||
                ""
        ) +
        "</em><em>" +
        escapeHtml(n.status || "") +
        "</em></div>" +
        (n.kind === "UI"
          ? '<button type="button" class="arch-ui-edit" data-ui-edit="1" title="Edit — 開啟獨立 UI 編輯視窗" aria-label="Edit UI Layer">Edit</button>'
          : "") +
        (n.kind === "WorkItem"
          ? (function () {
              ensureWorkItemFields(n);
              const lamp = n.displayLamp || "Gray";
              return (
                '<span class="arch-lamp-dot lamp-' +
                escapeHtml(String(lamp).toLowerCase()) +
                '" title="displayLamp=' +
                escapeHtml(lamp) +
                '" aria-label="lamp ' +
                escapeHtml(lamp) +
                '"></span>'
              );
            })()
          : "") +
        '<button type="button" class="arch-node-expand" aria-expanded="' +
        (!n.collapsed ? "true" : "false") +
        '" title="' +
        (n.collapsed ? "展開（顯示完整節點）" : "收合（保留類別名）") +
        '" aria-label="' +
        (n.collapsed
          ? "展開節點 " + escapeHtml(n.kind)
          : "收合節點 " + escapeHtml(n.kind)) +
        '">' +
        (n.collapsed ? "▸" : "▾") +
        "</button></div>" +
        membersHtml +
        '<div class="arch-ports"><div class="arch-port-col is-in">' +
        inPorts +
        '</div><div class="arch-port-col is-out">' +
        outPorts +
        "</div></div>";
      el.addEventListener("pointerdown", function (ev) {
        if (ev.button !== 0) return;
        if (
          ev.target.closest(".arch-port") ||
          ev.target.closest(".arch-node-expand") ||
          ev.target.closest(".arch-ui-edit") ||
          ev.target.closest(".arch-module-toggle") ||
          ev.target.closest(".arch-add-module") ||
          ev.target.closest(".arch-module-node")
        ) {
          return;
        }
        clearArchMarquee();
        const additive = !!(ev.ctrlKey || ev.metaKey || ev.shiftKey);
        if (additive) {
          selectArchNode(n.id, { toggle: true });
        } else {
          selectArchNode(n.id, { keepIfSelected: true });
        }
        if (!archEditMode) return;
        ev.preventDefault();
        ev.stopPropagation();
        const ids =
          getArchSelectedIds().indexOf(n.id) >= 0
            ? getArchSelectedIds()
            : [n.id];
        const origins = {};
        ids.forEach(function (id) {
          const node = findArchNode(id);
          if (!node) return;
          origins[id] = {
            x: Number(node.x) || 0,
            y: Number(node.y) || 0,
          };
        });
        archDrag = {
          ids: ids,
          primaryId: n.id,
          startX: ev.clientX,
          startY: ev.clientY,
          origins: origins,
          moved: false,
        };
        document.body.classList.add("is-arch-dragging");
        try {
          el.setPointerCapture(ev.pointerId);
        } catch (_e) {
          /* ignore */
        }
      });
      el.querySelector(".arch-node-expand")?.addEventListener(
        "click",
        function (ev) {
          ev.stopPropagation();
          n.collapsed = !n.collapsed;
          persistArchDraft();
          renderArchDag();
          selectArchNode(n.id);
        }
      );
      el.querySelector(".arch-ui-edit")?.addEventListener(
        "click",
        function (ev) {
          ev.stopPropagation();
          openArchUiLayer("editor", n.id);
        }
      );
      el.querySelectorAll(".arch-module-toggle").forEach(function (btn) {
        btn.addEventListener("click", function (ev) {
          ev.stopPropagation();
          const sid = btn.getAttribute("data-slot-id");
          const mods = ensureLayerModules(n);
          mods.forEach(function (m) {
            if (m.slotId === sid) m.collapsed = !m.collapsed;
          });
          persistArchDraft();
          renderArchDag();
          selectArchNode(n.id);
        });
      });
      el.querySelector(".arch-add-module")?.addEventListener(
        "click",
        function (ev) {
          ev.stopPropagation();
          if (!archEditMode) {
            toast("請先開「編輯草稿」");
            return;
          }
          addModuleSlotToLayer(n);
        }
      );
      el.querySelectorAll(".arch-module-node").forEach(function (chip) {
        chip.addEventListener("pointerdown", function (ev) {
          if (ev.button !== 0 || !archEditMode) return;
          ev.stopPropagation();
          ev.preventDefault();
          const mid = chip.getAttribute("data-member-id");
          if (!mid) return;
          archMemberDrag = {
            nodeId: mid,
            layerId: n.id,
            startX: ev.clientX,
            startY: ev.clientY,
          };
          document.body.classList.add("is-arch-dragging");
          try {
            chip.setPointerCapture(ev.pointerId);
          } catch (_e) {
            /* ignore */
          }
        });
      });
      el.querySelectorAll(".arch-port").forEach(function (btn) {
        btn.addEventListener("pointerdown", function (ev) {
          ev.stopPropagation();
          if (!archEditMode) return;
          if (btn.getAttribute("data-side") !== "out") return;
          const start = portAnchor(n, btn.getAttribute("data-port-id"), "out");
          archLink = {
            fromNode: n.id,
            fromPort: btn.getAttribute("data-port-id"),
            start: start,
            cur: { x: start.x, y: start.y },
          };
          ev.preventDefault();
        });
        btn.addEventListener("pointerup", function (ev) {
          if (!archLink || !archEditMode) return;
          if (btn.getAttribute("data-side") !== "in") return;
          const toNode = n.id;
          const toPort = btn.getAttribute("data-port-id");
          if (toNode === archLink.fromNode) {
            archLink = null;
            renderArchEdges();
            return;
          }
          archDoc.edges.push({
            id: "e-" + Date.now() + "-" + archSeq++,
            fromNode: archLink.fromNode,
            fromPort: archLink.fromPort,
            toNode: toNode,
            toPort: toPort,
          });
          archLink = null;
          persistArchDraft();
          renderArchEdges();
          ev.stopPropagation();
        });
      });
      host.appendChild(el);
    });
    expandArchWorldExtent({ quiet: true });
    renderArchEdges();
    renderArchUnassigned();
  }

  function onArchPointerMove(ev) {
    if (archTrayDrag) {
      const moved =
        Math.abs(ev.clientX - archTrayDrag.startX) +
        Math.abs(ev.clientY - archTrayDrag.startY);
      clearArchTreeDropHighlights();
      if (moved > 6) {
        const t = findArchTreeDropTarget(
          ev.clientX,
          ev.clientY,
          archTrayDrag.nodeId
        );
        if (t && t.el) t.el.classList.add("is-drop-target");
      }
      return;
    }
    if (archMarquee) {
      const p = clientToArchStage(ev.clientX, ev.clientY);
      archMarquee.x1 = p.x;
      archMarquee.y1 = p.y;
      updateArchMarqueeEl();
      return;
    }
    if (archDrag) {
      const dx = (ev.clientX - archDrag.startX) / (archZoom || 1);
      const dy = (ev.clientY - archDrag.startY) / (archZoom || 1);
      if (Math.abs(dx) + Math.abs(dy) > 2) archDrag.moved = true;
      const primaryId = archDrag.primaryId || (archDrag.ids && archDrag.ids[0]);
      const primary = findArchNode(primaryId);
      const origin = primary && archDrag.origins[primaryId];
      if (!primary || !origin) return;
      primary.x = origin.x + dx;
      primary.y = origin.y + dy;
      const g = snapArchNode(primary);
      const adx = primary.x - origin.x;
      const ady = primary.y - origin.y;
      (archDrag.ids || []).forEach(function (id) {
        const node = findArchNode(id);
        const o = archDrag.origins[id];
        if (!node || !o) return;
        if (id !== primaryId) {
          node.x = o.x + adx;
          node.y = o.y + ady;
        }
        const el = document.querySelector(
          '.arch-node[data-id="' + id + '"]'
        );
        if (el) {
          el.style.left = node.x + "px";
          el.style.top = node.y + "px";
        }
      });
      showArchGuides(g.xs, g.ys);
      expandArchWorldExtent({ quiet: true, margin: ARCH_WORLD_GROW });
      renderArchEdges();
      return;
    }
    if (archLink) {
      const stage = document.getElementById("archStage");
      if (!stage) return;
      const sr = stage.getBoundingClientRect();
      archLink.cur = {
        x: (ev.clientX - sr.left) / (archZoom || 1),
        y: (ev.clientY - sr.top) / (archZoom || 1),
      };
      renderArchEdges();
    }
  }

  function onArchPointerUp(ev) {
    if (archTrayDrag) {
      const dragId = archTrayDrag.nodeId;
      const node = findArchNode(dragId);
      const moved =
        Math.abs(ev.clientX - archTrayDrag.startX) +
        Math.abs(ev.clientY - archTrayDrag.startY);
      clearArchTreeDropHighlights();
      if (node && moved > 6) {
        const treeDrop = findArchTreeDropTarget(
          ev.clientX,
          ev.clientY,
          dragId
        );
        if (treeDrop) {
          applyArchTreeDrop(dragId, treeDrop);
        } else if (archEditMode) {
          const drop = findLayerDropTarget(node, ev.clientX, ev.clientY);
          if (drop && drop.layer && canAcceptNodeInLayer(node, drop.layer)) {
            if (findArchLayerContaining(node.id)) {
              movePackedNodeToSlot(node.id, drop.layer, drop.slotId);
            } else if (canPackNodeIntoLayer(node, drop.layer)) {
              packNodeIntoLayer(node, drop.layer, drop.slotId);
            }
            persistArchDraft();
          } else if (drop && drop.layer) {
            toast(
              "無法打包：Layer 只收 " +
                (drop.layer.packsKind || "?") +
                "（目前 " +
                node.kind +
                "）"
            );
          }
        }
      }
      archTrayDrag = null;
      document.body.classList.remove("is-arch-dragging");
      renderArchDag();
      if (archSelectedId) selectArchNode(archSelectedId);
    }
    if (archMemberDrag) {
      const node = findArchNode(archMemberDrag.nodeId);
      const fromLayer = findArchNode(archMemberDrag.layerId);
      const moved =
        Math.abs(ev.clientX - archMemberDrag.startX) +
        Math.abs(ev.clientY - archMemberDrag.startY);
      if (node && fromLayer && moved > 6) {
        const drop = findLayerDropTarget(node, ev.clientX, ev.clientY);
        if (drop && drop.layer) {
          movePackedNodeToSlot(node.id, drop.layer, drop.slotId);
        } else {
          unpackNodeFromLayer(node.id, fromLayer);
        }
        persistArchDraft();
      }
      archMemberDrag = null;
      document.body.classList.remove("is-arch-dragging");
      renderArchDag();
      if (archSelectedId) selectArchNode(archSelectedId);
    }
    if (archMarquee) {
      const hit = collectArchNodesInMarquee();
      const additive = !!(ev.ctrlKey || ev.metaKey || ev.shiftKey);
      if (hit.length) {
        if (additive) {
          const cur = getArchSelectedIds();
          hit.forEach(function (id) {
            if (cur.indexOf(id) < 0) cur.push(id);
          });
          setArchSelection(cur, hit[hit.length - 1]);
        } else {
          setArchSelection(hit, hit[hit.length - 1]);
        }
      } else if (!additive) {
        setArchSelection([], null);
      }
      clearArchMarquee();
    }
    if (archDrag) {
      const ids = (archDrag.ids || []).slice();
      const primaryId = archDrag.primaryId || ids[0];
      const node = findArchNode(primaryId);
      const moved = !!archDrag.moved;
      if (node) {
        ids.forEach(function (id) {
          const n = findArchNode(id);
          if (n) snapArchNode(n);
        });
        expandArchWorldExtent({ quiet: true });
        /* 多選移動不打包；單節點拖入 Module 仍可打包 */
        if (
          moved &&
          ids.length === 1 &&
          node.kind !== "Layer"
        ) {
          const drop = findLayerDropTarget(node, ev.clientX, ev.clientY);
          if (drop && drop.layer && canPackNodeIntoLayer(node, drop.layer)) {
            packNodeIntoLayer(node, drop.layer, drop.slotId);
          } else if (drop && drop.layer) {
            toast(
              "無法打包：Layer 只收 " +
                (drop.layer.packsKind || "?") +
                "（目前 " +
                node.kind +
                "）"
            );
          }
        }
        if (moved) persistArchDraft();
      }
      archDrag = null;
      clearArchGuides();
      document.body.classList.remove("is-arch-dragging");
      renderArchDag();
      setArchSelection(ids.filter(function (id) {
        return !!findArchNode(id);
      }), primaryId && findArchNode(primaryId) ? primaryId : null);
    }
    if (archLink) {
      const t = ev.target && ev.target.closest
        ? ev.target.closest(".arch-port.is-in")
        : null;
      if (t) {
        const nodeEl = t.closest(".arch-node");
        const toNode = nodeEl && nodeEl.getAttribute("data-id");
        const toPort = t.getAttribute("data-port-id");
        if (toNode && toNode !== archLink.fromNode) {
          archDoc.edges.push({
            id: "e-" + Date.now() + "-" + archSeq++,
            fromNode: archLink.fromNode,
            fromPort: archLink.fromPort,
            toNode: toNode,
            toPort: toPort,
          });
          persistArchDraft();
        }
      }
      archLink = null;
      renderArchEdges();
    }
  }

  function addArchNode(kind, packsKind) {
    const k = normalizeArchKind(kind);
    if (!k) {
      toast("拒絕：kind 不在嚴格枚舉 ARCH_NODE_KINDS");
      return;
    }
    if (!archEditMode) {
      setArchEditMode(true);
    }
    archSeq += 1;
    const id = "n-" + k.toLowerCase() + "-" + archSeq;
    const ports = defaultPortsForArchKind(k, id);
    const node = {
      id: id,
      name: k,
      kind: k,
      x: 80 + (archSeq % 6) * 24,
      y: 80 + (archSeq % 5) * 28,
      collapsed: false,
      inputs: ports.inputs,
      outputs: ports.outputs,
      role: ports.role,
      status: "未驗證",
      projectionLayer: null,
      description: "",
      layerRef: null,
      moduleRef: null,
      layoutOrder: null,
    };
    if (k === "Layer") {
      const packs =
        normalizeArchKind(packsKind) ||
        normalizeArchKind(
          (document.getElementById("archLayerPacksKind") || {}).value
        ) ||
        "API";
      if (!packs || ARCH_PACKABLE_KINDS.indexOf(packs) < 0) {
        toast("拒絕：Layer 必須指定 packs（PDF 01–10 類別）");
        return;
      }
      node.packsKind = packs;
      node.memberIds = [];
      node.modules = [];
      node.name = "Layer · " + packs;
      node.role = "Pack " + packs;
      node.collapsed = false;
      ensureLayerModules(node);
    }
    if (k === "UI") {
      node.name = "UI Layer";
      ensureUiLayerFields(node);
    }
    if (k === "WorkItem") {
      node.name = "Work Item";
      ensureWorkItemFields(node);
      appendArchEvent(id, "node.created", { kind: "WorkItem" });
    }
    if (k === "Deployment") {
      node.name = "Deployment";
      ensureDeploymentFields(node);
    }
    archDoc.nodes.push(node);
    persistArchDraft();
    renderArchDag();
    selectArchNode(id);
    toast(
      k === "Layer"
        ? "已新增 Layer（" + formatArchLayerPacks(node) + "）"
        : k === "UI"
          ? "已新增 UI Layer"
          : k === "WorkItem"
            ? "已新增 Work Item"
            : k === "Deployment"
              ? "已新增 Deployment Node"
              : "已新增 " + k
    );
  }

  function setArchEditMode(on) {
    archEditMode = !!on;
    const btn = document.getElementById("arch-edit");
    if (btn) {
      btn.setAttribute("aria-pressed", archEditMode ? "true" : "false");
      btn.classList.toggle("is-active", archEditMode);
    }
    document
      .getElementById("panel-arch")
      ?.classList.toggle("panel-arch-edit", archEditMode);
    syncArchDeleteUi();
    toast(archEditMode ? "草稿編輯：開" : "草稿編輯：關（唯讀）");
  }

  function setArchZoom(z) {
    archZoom = Math.max(0.4, Math.min(2, z));
    const stage = document.getElementById("archStage");
    if (stage) stage.style.transform = "scale(" + archZoom + ")";
  }

  /**
   * 中鍵拖曳＝平移；滾輪向前＝推進（放大）、向後＝後退（縮小）。
   * viewport: overflow 可捲動容器；opts.zoomBy(delta) 可選。
   */
  function wireCanvasMiddleNav(viewport, opts) {
    if (!viewport || viewport.getAttribute("data-mmb-nav") === "1") return;
    viewport.setAttribute("data-mmb-nav", "1");
    viewport.setAttribute(
      "title",
      (viewport.getAttribute("title") || "") +
        " · 中鍵拖曳平移 · 滾輪推進／後退縮放"
    );
    let pan = null;
    viewport.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 1) return;
      ev.preventDefault();
      pan = {
        x: ev.clientX,
        y: ev.clientY,
        sl: viewport.scrollLeft,
        st: viewport.scrollTop,
      };
      viewport.classList.add("is-mmb-panning");
      document.body.classList.add("is-mmb-panning");
      try {
        viewport.setPointerCapture(ev.pointerId);
      } catch (_e) {
        /* ignore */
      }
    });
    viewport.addEventListener("pointermove", function (ev) {
      if (!pan) return;
      viewport.scrollLeft = pan.sl - (ev.clientX - pan.x);
      viewport.scrollTop = pan.st - (ev.clientY - pan.y);
    });
    function endPan() {
      pan = null;
      viewport.classList.remove("is-mmb-panning");
      document.body.classList.remove("is-mmb-panning");
    }
    viewport.addEventListener("pointerup", endPan);
    viewport.addEventListener("pointercancel", endPan);
    viewport.addEventListener(
      "wheel",
      function (ev) {
        if (!opts || typeof opts.zoomBy !== "function") return;
        ev.preventDefault();
        /* deltaY < 0 → 滾輪向前 → 推進（放大） */
        const step = opts.step != null ? opts.step : 0.1;
        opts.zoomBy(ev.deltaY < 0 ? step : -step);
      },
      { passive: false }
    );
    viewport.addEventListener("auxclick", function (ev) {
      if (ev.button === 1) ev.preventDefault();
    });
  }

  function fitArchToView() {
    const wrap = document.getElementById("archStageWrap");
    const stage = document.getElementById("archStage");
    const shell = document.getElementById("arch-canvas-shell");
    if (!wrap || !stage || !shell) return;
    const size = archStageSize();
    const availW = Math.max(200, shell.clientWidth - 48);
    const availH = Math.max(160, shell.clientHeight - 24);
    const zx = availW / size.w;
    const zy = availH / size.h;
    setArchZoom(Math.min(1, zx, zy));
  }

  function archNodeLayoutSize(n) {
    const el = document.querySelector('.arch-node[data-id="' + n.id + '"]');
    return {
      w: el ? el.offsetWidth : n.kind === "Layer" ? 220 : 160,
      h: el ? el.offsetHeight : n.collapsed ? 32 : 72,
    };
  }

  /** 選取節點內邊優先順序（有連線則拓撲；否則依座標）。 */
  function orderArchNodesForArrange(nodes, horizontal) {
    const idSet = {};
    nodes.forEach(function (n) {
      idSet[n.id] = true;
    });
    const indeg = {};
    const outs = {};
    nodes.forEach(function (n) {
      indeg[n.id] = 0;
      outs[n.id] = [];
    });
    (archDoc.edges || []).forEach(function (e) {
      if (!e || !idSet[e.fromNode] || !idSet[e.toNode]) return;
      if (e.fromNode === e.toNode) return;
      outs[e.fromNode].push(e.toNode);
      indeg[e.toNode] = (indeg[e.toNode] || 0) + 1;
    });
    const queue = nodes
      .filter(function (n) {
        return (indeg[n.id] || 0) === 0;
      })
      .sort(function (a, b) {
        if (horizontal) {
          return (a.y - b.y) || (a.x - b.x);
        }
        return (a.x - b.x) || (a.y - b.y);
      });
    const ordered = [];
    const seen = {};
    while (queue.length) {
      const n = queue.shift();
      if (seen[n.id]) continue;
      seen[n.id] = true;
      ordered.push(n);
      (outs[n.id] || []).forEach(function (tid) {
        indeg[tid] -= 1;
        if (indeg[tid] <= 0) {
          const tn = findArchNode(tid);
          if (tn && !seen[tid]) queue.push(tn);
        }
      });
      queue.sort(function (a, b) {
        if (horizontal) {
          return (a.y - b.y) || (a.x - b.x);
        }
        return (a.x - b.x) || (a.y - b.y);
      });
    }
    nodes.forEach(function (n) {
      if (!seen[n.id]) ordered.push(n);
    });
    if (ordered.length < 2) {
      return nodes.slice().sort(function (a, b) {
        if (horizontal) {
          return (a.x - b.x) || (a.y - b.y);
        }
        return (a.y - b.y) || (a.x - b.x);
      });
    }
    return ordered;
  }

  /**
   * 依據選取自動排列。
   * mode: "h" 橫排｜"v" 縱排｜"auto" 依選取包圍盒長寬比。
   */
  function arrangeArchSelection(mode) {
    if (!archEditMode) {
      toast("請先開「編輯草稿」再排列");
      return false;
    }
    const ids = getArchSelectedIds();
    if (ids.length < 2) {
      toast("請先框選或多選至少 2 個節點");
      return false;
    }
    const nodes = ids
      .map(function (id) {
        return findArchNode(id);
      })
      .filter(Boolean);
    if (nodes.length < 2) {
      toast("選取無效");
      return false;
    }
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    nodes.forEach(function (n) {
      const sz = archNodeLayoutSize(n);
      const x = Number(n.x) || 0;
      const y = Number(n.y) || 0;
      minX = Math.min(minX, x);
      minY = Math.min(minY, y);
      maxX = Math.max(maxX, x + sz.w);
      maxY = Math.max(maxY, y + sz.h);
    });
    const boxW = Math.max(1, maxX - minX);
    const boxH = Math.max(1, maxY - minY);
    let dir = mode || "auto";
    if (dir === "auto") {
      dir = boxW >= boxH ? "h" : "v";
    }
    const horizontal = dir === "h";
    const gap = Math.max(16, (archGridPx || 8) * 2);
    const ordered = orderArchNodesForArrange(nodes, horizontal);
    let cursor = horizontal ? minX : minY;
    const align = horizontal ? minY : minX;
    ordered.forEach(function (n) {
      const sz = archNodeLayoutSize(n);
      if (horizontal) {
        n.x = cursor;
        n.y = align;
        cursor += sz.w + gap;
      } else {
        n.x = align;
        n.y = cursor;
        cursor += sz.h + gap;
      }
      snapArchNode(n);
    });
    expandArchWorldExtent({ quiet: true });
    persistArchDraft();
    renderArchDag();
    setArchSelection(
      ordered.map(function (n) {
        return n.id;
      }),
      archSelectedId && findArchNode(archSelectedId)
        ? archSelectedId
        : ordered[0].id
    );
    toast(
      (horizontal ? "橫向" : "縱向") +
        "排列 " +
        ordered.length +
        " 個選取節點"
    );
    return true;
  }

  /** 聚焦選取節點：置中捲動＋適度放大。 */
  function focusArchSelectedNode() {
    const node = findArchNode(archSelectedId);
    const shell = document.getElementById("arch-canvas-shell");
    if (!node || !shell) {
      toast("未選取節點");
      return;
    }
    const el = document.querySelector(
      '.arch-node[data-id="' + node.id + '"]'
    );
    const nw = el ? el.offsetWidth : 160;
    const nh = el ? el.offsetHeight : 72;
    const cx = (Number(node.x) || 0) + nw / 2;
    const cy = (Number(node.y) || 0) + nh / 2;
    /* 目標縮放：節點約佔視窗 1/3～1/2 */
    const targetZ = Math.max(
      0.75,
      Math.min(
        1.6,
        Math.min(
          (shell.clientWidth * 0.45) / Math.max(nw, 80),
          (shell.clientHeight * 0.45) / Math.max(nh, 48)
        )
      )
    );
    setArchZoom(targetZ);
    const zx = archZoom || 1;
    shell.scrollLeft = Math.max(0, cx * zx - shell.clientWidth / 2);
    shell.scrollTop = Math.max(0, cy * zx - shell.clientHeight / 2);
    if (el) {
      el.classList.add("is-focus-flash");
      setTimeout(function () {
        el.classList.remove("is-focus-flash");
      }, 700);
    }
    toast("已聚焦：" + (node.name || node.id));
  }

  function mergeProjectionIntoDraft(dto) {
    const modules = dto.modules || [];
    const edges = dto.edges || [];
    modules.forEach(function (m, i) {
      const id = m.id || "mod-" + i;
      let node = findArchNode(id);
      const kind = mapLayerToArchKind(m.layer);
      if (!node) {
        node = {
          id: id,
          name: m.name || id,
          kind: kind,
          x: 60 + (i % 4) * 200,
          y: 60 + Math.floor(i / 4) * 120,
          collapsed: false,
          inputs: [{ id: id + "-in", label: "in" }],
          outputs: [{ id: id + "-out", label: "out" }],
          status: "投影",
          projectionLayer: m.layer || null,
        };
        archDoc.nodes.push(node);
      } else {
        node.status = "投影";
        node.projectionLayer = m.layer || null;
        if (!normalizeArchKind(node.kind)) node.kind = kind;
      }
    });
    edges.forEach(function (e, i) {
      const from = e.from;
      const to = e.to;
      if (!from || !to) return;
      const exists = archDoc.edges.some(function (x) {
        return x.fromNode === from && x.toNode === to;
      });
      if (exists) return;
      if (!findArchNode(from) || !findArchNode(to)) return;
      archDoc.edges.push({
        id: "proj-e-" + i,
        fromNode: from,
        fromPort: from + "-out",
        toNode: to,
        toPort: to + "-in",
      });
    });
    persistArchDraft();
  }

  function renderArchProjectionLists(dto) {
    const modules = dto.modules || [];
    const edges = dto.edges || [];
    const modCount = document.getElementById("arch-mod-count");
    const edgeCount = document.getElementById("arch-edge-count");
    const modList = document.getElementById("arch-modules");
    const edgeList = document.getElementById("arch-edges");
    if (modCount) modCount.textContent = String(modules.length);
    if (edgeCount) edgeCount.textContent = String(edges.length);
    if (modList) {
      modList.innerHTML = "";
      modList.hidden = modules.length === 0;
      modules.forEach(function (m) {
        const li = document.createElement("li");
        li.className = "arch-mod-item";
        li.dataset.moduleId = m.id || "";
        li.innerHTML =
          '<span class="name">' +
          escapeHtml(m.name || m.id || "—") +
          '</span><span class="id">' +
          escapeHtml(m.id || "") +
          '</span><span class="layer">' +
          escapeHtml(m.layer || "") +
          "</span>";
        li.addEventListener("click", function () {
          selectArchModule(m);
        });
        modList.appendChild(li);
      });
    }
    if (edgeList) {
      edgeList.innerHTML = "";
      edgeList.hidden = edges.length === 0;
      edges.forEach(function (e) {
        const li = document.createElement("li");
        li.className = "arch-edge-item";
        li.innerHTML =
          '<span class="id">' +
          escapeHtml(e.from || "?") +
          " → " +
          escapeHtml(e.to || "?") +
          '</span><span class="layer">' +
          escapeHtml(e.kind || "") +
          "</span>";
        edgeList.appendChild(li);
      });
    }
  }

  function renderArchProjection(dto) {
    if (
      !dto ||
      typeof dto !== "object" ||
      !Array.isArray(dto.modules) ||
      dto.modules.length === 0 ||
      String(dto.status || "").toLowerCase() === "empty" ||
      String(dto.status || "").toLowerCase() === "not_run"
    ) {
      setArchBanner(
        "無 live 投影",
        "Command 空圖／NOT RUN。草稿畫布仍可用；禁止靜態假圖冒充 live。",
        true
      );
      setArchLiveBadge("來源：NOT RUN／空態", "warn");
      setArchStatusLine(
        "arch_get_projection：" + (dto && dto.status ? dto.status : "empty"),
        true
      );
      lastArchProj = null;
      renderArchDag();
      return;
    }
    if (!dto.live) {
      setArchBanner(
        "非 live 投影",
        "禁止以非 Command live 來源冒充即時圖。草稿畫布仍可用。",
        true
      );
      setArchLiveBadge("來源：非 live", "warn");
      setArchStatusLine("arch_get_projection：live=false", true);
      lastArchProj = null;
      renderArchDag();
      return;
    }
    lastArchProj = dto;
    showArchProjection();
    setArchLiveBadge(
      "來源：Command · " + (dto.source || "arch_get_projection"),
      "live"
    );
    mergeProjectionIntoDraft(dto);
    renderArchProjectionLists(dto);
    renderArchDag();
    setArchStatusLine(
      "arch_get_projection · modules=" +
        (dto.modules || []).length +
        " · edges=" +
        (dto.edges || []).length +
        " · gen=" +
        (dto.generation != null ? dto.generation : "—"),
      false
    );
  }

  async function cmdArchRefresh() {
    if (!invoke) {
      setArchBanner(
        "無 IPC（瀏覽器模式）",
        "草稿畫布可用；live 需 Tauri invoke arch_get_projection。禁止靜態假圖冒充 live。",
        true
      );
      setArchLiveBadge("來源：NOT RUN（無 IPC）", "warn");
      setArchStatusLine("瀏覽器模式：架構 NOT RUN", true);
      renderArchDag();
      toast("架構投影需 Tauri IPC（NOT RUN）；草稿可用");
      setStatus("arch.refresh：NOT RUN（無 IPC）");
      return;
    }
    setArchStatusLine("載入 arch_get_projection…", false);
    try {
      const dto = await invoke("arch_get_projection");
      renderArchProjection(dto);
      if (dto && dto.live && dto.modules && dto.modules.length) {
        toast("架構投影已更新");
        setStatus("arch_get_projection → 投影");
      } else {
        toast("架構：空態／NOT RUN（草稿仍可用）");
        setStatus("arch_get_projection：empty／NOT RUN");
      }
    } catch (err) {
      setArchBanner(
        "架構投影失敗",
        "arch_get_projection 錯誤（非直呼 OS／無靜態假圖）：" + String(err),
        true
      );
      setArchLiveBadge("來源：錯誤／ACL", "warn");
      setArchStatusLine("arch_get_projection 失敗：" + String(err), true);
      renderArchDag();
      toast("架構投影失敗；草稿畫布仍可用");
      setStatus("arch.refresh 失敗");
    }
  }

  function wireArchUi() {
    loadArchDraft();
    ensureDefaultArchSeed();
    const sizeTok =
      (archDoc.meta && archDoc.meta.formSize) || "1280x720";
    setArchFormSize(sizeTok, true);
    setArchGridPx(
      archDoc.meta && archDoc.meta.gridSize != null
        ? archDoc.meta.gridSize
        : 8,
      true
    );
    renderArchDag();
    setArchBanner(
      "草稿畫布就緒",
      "投影未載入時可編輯草稿；僅 Command live 可標 live。禁止靜態假圖冒充即時圖。",
      false
    );
    setArchLiveBadge("來源：草稿（非 live）", "warn");
    document.addEventListener("pointermove", onArchPointerMove);
    document.addEventListener("pointerup", onArchPointerUp);
    document.getElementById("archStage")?.addEventListener(
      "pointerdown",
      function (ev) {
        if (ev.button !== 0) return;
        if (
          ev.target.closest(".arch-node") ||
          ev.target.closest(".arch-port") ||
          ev.target.closest(".arch-marquee")
        ) {
          return;
        }
        if (archLink || archDrag || archMemberDrag || archTrayDrag) return;
        const p = clientToArchStage(ev.clientX, ev.clientY);
        archMarquee = { x0: p.x, y0: p.y, x1: p.x, y1: p.y };
        document.body.classList.add("is-arch-marquee");
        updateArchMarqueeEl();
        try {
          ev.currentTarget.setPointerCapture(ev.pointerId);
        } catch (_e) {
          /* ignore */
        }
        ev.preventDefault();
      }
    );
    document.getElementById("arch-edit")?.addEventListener("click", function () {
      setArchEditMode(!archEditMode);
    });
    document.getElementById("arch-fit")?.addEventListener("click", fitArchToView);
    document.getElementById("arch-zoom-in")?.addEventListener("click", function () {
      setArchZoom(archZoom + 0.1);
    });
    document.getElementById("arch-zoom-out")?.addEventListener("click", function () {
      setArchZoom(archZoom - 0.1);
    });
    document
      .getElementById("arch-focus-selected")
      ?.addEventListener("click", function () {
        focusArchSelectedNode();
      });
    document
      .getElementById("arch-arrange-auto")
      ?.addEventListener("click", function () {
        arrangeArchSelection("auto");
      });
    document
      .getElementById("arch-arrange-h")
      ?.addEventListener("click", function () {
        arrangeArchSelection("h");
      });
    document
      .getElementById("arch-arrange-v")
      ?.addEventListener("click", function () {
        arrangeArchSelection("v");
      });
    wireCanvasMiddleNav(document.getElementById("arch-canvas-shell"), {
      zoomBy: function (delta) {
        setArchZoom(archZoom + delta);
      },
      step: 0.1,
    });
    document.getElementById("arch-canvas-shell")?.addEventListener(
      "scroll",
      function () {
        expandArchWorldExtent({ quiet: true });
      },
      { passive: true }
    );
    document.getElementById("archFormSize")?.addEventListener("change", function (ev) {
      setArchFormSize(ev.target.value, false);
    });
    document.getElementById("archGridSize")?.addEventListener("change", function (ev) {
      setArchGridPx(ev.target.value, false);
      renderArchDag();
    });
    wireArchKindPicker();
    renderArchKindFilterBar();
    document.getElementById("arch-save-xml")?.addEventListener("click", function () {
      downloadArchXml();
    });
    document.getElementById("arch-load-xml")?.addEventListener("click", function () {
      openArchXmlFilePicker();
    });
    document.getElementById("arch-xml-file")?.addEventListener("change", function (ev) {
      const file = ev.target.files && ev.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function () {
        importArchXmlText(String(reader.result || ""), file.name);
        ev.target.value = "";
      };
      reader.onerror = function () {
        toast("讀取 XML 失敗");
        ev.target.value = "";
      };
      reader.readAsText(file, "UTF-8");
    });
    document.getElementById("arch-delete-node")?.addEventListener("click", function () {
      deleteArchNode(archSelectedId);
    });
    document
      .getElementById("arch-inspector-delete")
      ?.addEventListener("click", function () {
        deleteArchNode(archSelectedId);
      });
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Delete" && ev.key !== "Backspace") return;
      const panel = document.getElementById("panel-arch");
      if (!panel || !panel.classList.contains("active") || panel.hidden) return;
      const t = ev.target;
      if (
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.tagName === "SELECT" ||
          t.isContentEditable)
      ) {
        return;
      }
      if (!archSelectedId) return;
      ev.preventDefault();
      deleteArchNode(archSelectedId);
    });
    syncArchDeleteUi();
    [
      "archNodeName",
      "archNodeCollapsed",
      "archNodePacksKind",
      "archNodeDesc",
      "archNodeOrder",
      "archUiDefinitionRef",
      "archUiThemeRef",
      "archDepType",
      "archDepTargetRef",
      "archDepEnabled",
      "archDepInputArtifact",
      "archDepArtifactType",
      "archDepVersion",
      "archDepChecksum",
      "archDepEnvironment",
      "archDepRuntime",
      "archDepConfigProfile",
      "archDepSecretRefs",
      "archDepStrategy",
      "archDepPreChecks",
      "archDepHealth",
      "archDepRollback",
      "archDepApproval",
      "archDepTimeout",
      "archDepRetry",
      "archDepResources",
      "archDepCost",
      "archDepExecStatus",
      "archWiWorkflow",
      "archWiTest",
      "archWiPriority",
      "archWiAcceptance",
      "archWiBuildDate",
      "archWiModifiedDate",
      "archWiCompletedDate",
      "archWiParentRefs",
      "archWiDepRefs",
      "archWiBlocker",
      "archWiInTok",
      "archWiOutTok",
      "archWiCost",
    ].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", applyArchInspectorInputs);
    });
    document.getElementById("archDepType")?.addEventListener(
      "change",
      function () {
        const node = findArchNode(archSelectedId);
        const t = normalizeDeploymentType(
          (document.getElementById("archDepType") || {}).value
        );
        syncDeploymentStrategyOptions(
          t,
          node && node.strategy ? node.strategy : "replace"
        );
      }
    );
    document
      .getElementById("arch-open-ui-editor")
      ?.addEventListener("click", function () {
        openArchUiLayer("editor");
      });
    document
      .getElementById("arch-open-ui-viewer")
      ?.addEventListener("click", function () {
        openArchUiLayer("viewer");
      });
    document.querySelectorAll("[data-arch-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setArchInspectorTab(btn.getAttribute("data-arch-tab"));
      });
    });
    setArchInspectorTab("basic");
  }

  function archKindIconSrc(kind) {
    return ARCH_KIND_ICONS[kind] || ARCH_KIND_ICONS.Custom;
  }

  function setArchKindPickerOpen(open) {
    const picker = document.getElementById("arch-kind-picker");
    const btn = document.getElementById("arch-add-node");
    if (!picker) return;
    picker.hidden = !open;
    if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) {
      showArchKindGridStep();
      renderArchKindPickerGrid();
    }
  }

  function showArchKindGridStep() {
    const grid = document.getElementById("arch-kind-grid");
    const packs = document.getElementById("arch-kind-packs");
    const title = document.getElementById("arch-kind-picker-title");
    if (grid) grid.hidden = false;
    if (packs) packs.hidden = true;
    if (title) {
      title.textContent =
        "選擇節點類別（" + ARCH_NODE_KINDS.length + "）";
    }
  }

  function showArchPacksStep() {
    const grid = document.getElementById("arch-kind-grid");
    const packs = document.getElementById("arch-kind-packs");
    const title = document.getElementById("arch-kind-picker-title");
    if (grid) grid.hidden = true;
    if (packs) packs.hidden = false;
    if (title) title.textContent = "Layer · 選擇 packs";
    renderArchPacksPickerGrid();
  }

  function renderArchKindPickerGrid() {
    const host = document.getElementById("arch-kind-grid");
    if (!host) return;
    host.innerHTML = "";
    ARCH_NODE_KINDS.forEach(function (kind, i) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "arch-kind-tile";
      btn.setAttribute("role", "option");
      btn.setAttribute("data-arch-kind", kind);
      btn.title =
        kind === "Layer"
          ? "Layer（打包；需選 packs）"
          : kind === "UI"
            ? "UI Layer（架構入口 → Editor／Viewer）"
            : kind === "WorkItem"
              ? "Work Item（燈號／Event Log）"
              : kind === "Deployment"
                ? "Deployment Node（佈署目標／策略／狀態）"
                : kind;
      const img = document.createElement("img");
      img.src = archKindIconSrc(kind);
      img.alt = "";
      img.width = 28;
      img.height = 28;
      img.decoding = "async";
      const lab = document.createElement("span");
      lab.className = "arch-kind-tile-label";
      lab.textContent =
        kind === "Layer"
          ? "Layer"
          : kind === "UI"
            ? String(i + 1).padStart(2, "0") + " UI Layer"
            : kind === "WorkItem"
              ? String(i + 1).padStart(2, "0") + " Work Item"
              : String(i + 1).padStart(2, "0") + " " + kind;
      btn.appendChild(img);
      btn.appendChild(lab);
      btn.addEventListener("click", function () {
        const kindEl = document.getElementById("archAddKind");
        if (kindEl) kindEl.value = kind;
        if (kind === "Layer") {
          showArchPacksStep();
          return;
        }
        addArchNode(kind);
        setArchKindPickerOpen(false);
      });
      host.appendChild(btn);
    });
  }

  function renderArchPacksPickerGrid() {
    const host = document.getElementById("arch-packs-grid");
    if (!host) return;
    host.innerHTML = "";
    ARCH_PACKABLE_KINDS.forEach(function (kind) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "arch-kind-tile";
      btn.setAttribute("role", "option");
      btn.setAttribute("data-packs-kind", kind);
      btn.title = "packs : " + kind;
      const img = document.createElement("img");
      img.src = archKindIconSrc(kind);
      img.alt = "";
      img.width = 28;
      img.height = 28;
      img.decoding = "async";
      const lab = document.createElement("span");
      lab.className = "arch-kind-tile-label";
      lab.textContent = kind;
      btn.appendChild(img);
      btn.appendChild(lab);
      btn.addEventListener("click", function () {
        const packsEl = document.getElementById("archLayerPacksKind");
        const kindEl = document.getElementById("archAddKind");
        if (packsEl) packsEl.value = kind;
        if (kindEl) kindEl.value = "Layer";
        addArchNode("Layer", kind);
        setArchKindPickerOpen(false);
      });
      host.appendChild(btn);
    });
  }

  function wireArchKindPicker() {
    const addBtn = document.getElementById("arch-add-node");
    const closeBtn = document.getElementById("arch-kind-picker-close");
    const backBtn = document.getElementById("arch-kind-packs-back");
    const wrap = document.getElementById("arch-add-wrap");
    renderArchKindPickerGrid();
    if (addBtn) {
      addBtn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        const picker = document.getElementById("arch-kind-picker");
        const open = picker && picker.hidden;
        setArchKindPickerOpen(!!open);
      });
    }
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        setArchKindPickerOpen(false);
      });
    }
    if (backBtn) {
      backBtn.addEventListener("click", function () {
        showArchKindGridStep();
      });
    }
    document.addEventListener("click", function (ev) {
      const picker = document.getElementById("arch-kind-picker");
      if (!picker || picker.hidden) return;
      if (wrap && wrap.contains(ev.target)) return;
      setArchKindPickerOpen(false);
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      const picker = document.getElementById("arch-kind-picker");
      if (picker && !picker.hidden) setArchKindPickerOpen(false);
    });
  }

  // —— PD-REMAIN-LISTEN-UI-01：監聽投影（Command／bridge only；禁 UI notify）——

  function setListenStatusLine(msg, isError) {
    const el = document.getElementById("listen-status-line");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("error", !!isError);
  }

  function setNavListenMeta(text) {
    const el = document.getElementById("nav-listen-meta");
    if (el) el.textContent = text || "—";
  }

  function setListenStatusBadge(text, kind) {
    const el = document.getElementById("listen-status-badge");
    if (!el) return;
    el.textContent = text || "狀態：—";
    el.classList.remove("ok", "warn", "bad");
    if (kind) el.classList.add(kind);
  }

  function showListenEmpty(title, body, statusMsg) {
    const empty = document.getElementById("listen-empty");
    const layout = document.getElementById("listen-layout");
    if (layout) layout.hidden = true;
    if (empty) {
      empty.hidden = false;
      const strong = empty.querySelector("strong");
      const p = empty.querySelector("p");
      if (strong && title) strong.textContent = title;
      if (p && body) p.textContent = body;
    }
    setListenStatusBadge("狀態：空態／NOT RUN", "warn");
    setNavListenMeta("空");
    setListenStatusLine(statusMsg || "listen：empty", false);
  }

  function renderListenProjection(dto) {
    if (!dto || dto.status === "empty" || !dto.event_count) {
      showListenEmpty(
        "尚無監聽事件",
        "無 DomainEvent。Agent 經 poll_chunks→橋接；宿主 FS／Git watch = " +
          ((dto && dto.host_fs_watch) || "NOT RUN") +
          "／" +
          ((dto && dto.host_git_watch) || "NOT RUN") +
          "。禁 UI notify。",
        "listen_get_projection → empty"
      );
      if (dto) {
        const hostFs = document.getElementById("listen-host-fs");
        // Keep gap fields visible on empty via note only
        setListenStatusLine(
          "empty · host_fs=" +
            (dto.host_fs_watch || "NOT RUN") +
            " · host_git=" +
            (dto.host_git_watch || "NOT RUN") +
            " · agent=" +
            (dto.host_agent_bridge || "?"),
          false
        );
        if (hostFs) {
          /* layout hidden — meta on badge */
        }
      }
      return;
    }
    const empty = document.getElementById("listen-empty");
    const layout = document.getElementById("listen-layout");
    if (empty) empty.hidden = true;
    if (layout) layout.hidden = false;

    function setText(id, val) {
      const el = document.getElementById(id);
      if (el) el.textContent = val == null || val === "" ? "—" : String(val);
    }
    setText("listen-fs-path", dto.last_fs_path);
    setText("listen-fs-burst", dto.last_fs_burst);
    setText("listen-git-root", dto.last_git_root);
    setText("listen-git-burst", dto.last_git_burst);
    setText("listen-agent-run", dto.last_agent_run);
    setText("listen-agent-kind", dto.last_agent_kind);
    setText("listen-agent-class", dto.last_agent_classification);
    setText(
      "listen-reconcile",
      dto.pending_reconcile ? "yes" : "no"
    );
    setText("listen-host-fs", dto.host_fs_watch || "NOT RUN");
    setText("listen-host-git", dto.host_git_watch || "NOT RUN");
    setText("listen-host-agent", dto.host_agent_bridge || "wired");
    setText("listen-generation", dto.generation);

    const note = document.getElementById("listen-note");
    if (note) {
      if (dto.note) {
        note.hidden = false;
        note.textContent = dto.note;
      } else {
        note.hidden = true;
        note.textContent = "";
      }
    }
    setListenStatusBadge("狀態：ok · gen=" + (dto.generation || 0), "ok");
    setNavListenMeta("ok");
    setListenStatusLine(
      "listen_get_projection → ok · events=" +
        (dto.event_count || 0) +
        " · gen=" +
        (dto.generation || 0),
      false
    );
  }

  async function cmdListenRefresh() {
    if (!invoke) {
      showListenEmpty(
        "無 IPC（瀏覽器模式）",
        "需 tauri dev 才可 listen_get_projection。不會在瀏覽器自建 FS／Git／Agent notify。",
        "listen.refresh：NOT RUN（無 IPC）"
      );
      toast("監聽投影需 Tauri IPC（NOT RUN）");
      setStatus("listen.refresh：NOT RUN（無 IPC）");
      return;
    }
    setListenStatusLine("載入 listen_get_projection…", false);
    try {
      const dto = await invoke("listen_get_projection");
      renderListenProjection(dto);
      if (dto && dto.status === "ok" && dto.event_count) {
        toast("監聽投影已更新");
        setStatus("listen_get_projection → ok");
      } else {
        toast("監聽：空態（無事件）");
        setStatus("listen_get_projection → empty");
      }
    } catch (err) {
      showListenEmpty(
        "監聽投影失敗",
        "listen_get_projection 錯誤（非 UI notify）：" + String(err),
        "listen_get_projection 失敗：" + String(err)
      );
      toast("監聽投影失敗");
      setStatus("listen.refresh 失敗");
    }
  }

  // —— PD-REPORT-UI-01：報告面板（invoke project_pd_report → pd_report；不回寫規格）——

  function setReportStatusLine(msg, isError) {
    const el = document.getElementById("report-status-line");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("error", !!isError);
  }

  function setNavReportMeta(text) {
    const el = document.getElementById("nav-report-meta");
    if (el) el.textContent = text || "—";
  }

  function setReportStatusBadge(text, kind) {
    const el = document.getElementById("report-status-badge");
    if (!el) return;
    el.textContent = text || "狀態：—";
    el.classList.remove("ok", "warn", "bad");
    if (kind) el.classList.add(kind);
  }

  function showReportEmpty(title, body, statusMsg) {
    const empty = document.getElementById("report-empty");
    const layout = document.getElementById("report-layout");
    const titleEl = document.getElementById("report-empty-title");
    const bodyEl = document.getElementById("report-empty-body");
    if (layout) layout.hidden = true;
    if (empty) {
      empty.hidden = false;
      empty.setAttribute("data-report-state", "idle");
    }
    if (titleEl) titleEl.textContent = title || "尚未開啟報告投影";
    if (bodyEl) {
      bodyEl.textContent =
        body ||
        "點「開啟空證據報告」驗證空 evid → NOT RUN。不回寫 SPEC／EVID。";
    }
    setReportStatusBadge("狀態：—", null);
    setNavReportMeta("—");
    setReportStatusLine(statusMsg || "", !!statusMsg);
  }

  function renderReportDto(dto) {
    const empty = document.getElementById("report-empty");
    const layout = document.getElementById("report-layout");
    if (empty) {
      empty.hidden = true;
      empty.setAttribute("data-report-state", "ready");
    }
    if (layout) layout.hidden = false;

    const status = dto.evidence_status || "NOT RUN";
    const writeBack = !!dto.write_back;
    const setTxt = function (id, v) {
      const el = document.getElementById(id);
      if (el) el.textContent = v == null || v === "" ? "—" : String(v);
    };
    setTxt("report-evid-status", status);
    setTxt("report-write-back", writeBack ? "true" : "false");
    setTxt("report-fingerprint", dto.fingerprint);
    setTxt("report-html-path", dto.html_path);
    setTxt("report-md-path", dto.md_path);

    const mdEl = document.getElementById("report-md-body");
    if (mdEl) {
      mdEl.textContent = dto.md_body || "（無 markdown 本文）";
    }

    const badgeKind =
      status === "PASS" ? "ok" : status === "NOT RUN" ? "warn" : "bad";
    setReportStatusBadge("狀態：" + status, badgeKind);
    setNavReportMeta(String(status).slice(0, 12));
    setReportStatusLine(
      "project_pd_report → " +
        status +
        " · write_back=" +
        writeBack +
        (dto.html_path ? " · " + dto.html_path : ""),
      writeBack
    );
    if (writeBack) {
      toast("契約違規：write_back 必須為 false");
    }
  }

  async function cmdProjectReport(fixture) {
    const kind = fixture === "happy" ? "happy" : "not_run";
    if (!invoke) {
      showReportEmpty(
        "無 IPC（瀏覽器模式）",
        "空證據視為 NOT RUN／未測。請以 tauri dev 呼叫 project_pd_report → tools/pd_report。不回寫規格。",
        "瀏覽器模式：evidence_status=NOT RUN（無 IPC）"
      );
      setReportStatusBadge("狀態：NOT RUN", "warn");
      setNavReportMeta("NOT RUN");
      toast("報告投影需 Tauri IPC（NOT RUN）");
      setStatus("report.open — 需 Tauri；空態 NOT RUN");
      return;
    }
    setReportStatusLine("呼叫 project_pd_report（fixture=" + kind + "）…", false);
    try {
      const dto = await invoke("project_pd_report", {
        args: {
          spec_path: null,
          evid_path: null,
          out_dir: null,
          fixture: kind,
        },
      });
      if (dto.write_back) {
        showReportEmpty(
          "契約違規",
          "write_back 必須為 false（不得回寫 SPEC／EVID）。",
          "write_back 違規"
        );
        return;
      }
      renderReportDto(dto);
      toast(
        kind === "not_run"
          ? "報告投影：NOT RUN（空 evid）"
          : "報告投影已開啟（" + (dto.evidence_status || "?") + "）"
      );
      setStatus(
        "project_pd_report → " +
          (dto.evidence_status || "?") +
          " write_back=false"
      );
    } catch (err) {
      showReportEmpty(
        "報告投影失敗",
        "project_pd_report 錯誤（呼叫 pd_report 邊界）：" + String(err),
        String(err)
      );
      toast("報告投影失敗");
    }
  }

  // ── PD-REMAIN-PORTS-UI-01 Ports projection ───────────────────────────────

  function setPortsStatusLine(msg, isError) {
    const el = document.getElementById("ports-status-line");
    if (!el) return;
    el.textContent = msg || "";
    el.classList.toggle("error", !!isError);
  }

  function setPortsStatusBadge(text, kind) {
    const el = document.getElementById("ports-status-badge");
    if (!el) return;
    el.textContent = text || "狀態：—";
    el.classList.remove("ok", "warn");
    if (kind === "ok") el.classList.add("ok");
    if (kind === "warn") el.classList.add("warn");
  }

  function setNavPortsMeta(text) {
    const el = document.getElementById("nav-ports-meta");
    if (el) el.textContent = text || "—";
  }

  /** PD-SHELL-UIDESIGN-VIEW-01 — design package viewer (≠ product evidence / not formal PASS). */
  const UIDESIGN_REL_PATH = "docs/ui-design/index.html";
  const UIDESIGN_DESIGN_REL = "design/main.sgendesign";
  let lastUidesignPkg = null;

  /** PD-UIDESIGNER-EDIT — in-memory DesignDoc (format sgenaxis.design v1). */
  const DESIGN_SNAP_PX = 8;
  const DESIGN_GRID_DEFAULT = 8;
  let designGridPx = DESIGN_GRID_DEFAULT;
  let designDrag = null;
  let designDragMoved = false;
  let designZoom = 1;

  function setDesignZoom(z) {
    designZoom = Math.max(0.4, Math.min(2, z));
    const board = document.getElementById("designBoard");
    if (board) {
      board.style.transform = "scale(" + designZoom + ")";
      board.style.transformOrigin = "0 0";
    }
  }
  let designDoc = blankDesignDoc();
  let designPlaceSeq = 0;

  function touchDesignDirty() {
    designDirty = true;
    markSceneDirty();
  }

  function getDesignGridPx() {
    return designGridPx > 0 ? designGridPx : 0;
  }

  const DESIGN_FORM_SIZE_PRESETS = [
    "800x600",
    "800x800",
    "1024x768",
    "1280x720",
    "1366x768",
    "1440x900",
    "1600x900",
    "1920x1080",
    "2560x1440",
  ];

  function parseDesignFormSizeToken(token) {
    const m = String(token || "").match(/^(\d+)\s*[x×]\s*(\d+)$/i);
    if (!m) return null;
    return { w: Number(m[1]), h: Number(m[2]) };
  }

  function designFormSizeToken(w, h) {
    return Math.round(Number(w) || 0) + "x" + Math.round(Number(h) || 0);
  }

  function syncDesFormSizeSelect() {
    const root = formRootNode();
    const sel = document.getElementById("desFormSize");
    if (!sel || !root || !root.props) return;
    const token = designFormSizeToken(root.props.w, root.props.h);
    if (DESIGN_FORM_SIZE_PRESETS.indexOf(token) >= 0) {
      sel.value = token;
    } else {
      sel.value = "custom";
    }
  }

  function setDesignFormSize(w, h, opts) {
    const quiet = opts && opts.quiet;
    const root = formRootNode();
    if (!root) return;
    if (!root.props) root.props = {};
    let ww = Math.round(Number(w));
    let hh = Math.round(Number(h));
    if (!isFinite(ww) || ww < 64) ww = 800;
    if (!isFinite(hh) || hh < 64) hh = 600;
    if (ww > 7680) ww = 7680;
    if (hh > 4320) hh = 4320;
    root.props.w = ww;
    root.props.h = hh;
    if (!designDoc.meta) designDoc.meta = {};
    designDoc.meta.formSize = designFormSizeToken(ww, hh);
    syncDesFormSizeSelect();
    childDesignNodes().forEach(function (n) {
      clampDesignNodeInForm(n);
    });
    if (!quiet) {
      touchDesignDirty();
      renderDesignCanvas();
      fillDesignProps();
    }
  }

  function setDesignGridPx(px, opts) {
    const quiet = opts && opts.quiet;
    let n = Math.round(Number(px));
    if (!isFinite(n) || n < 0) n = DESIGN_GRID_DEFAULT;
    if (n > 0 && n < 2) n = 2;
    if (n > 64) n = 64;
    designGridPx = n;
    if (!designDoc.meta) designDoc.meta = {};
    designDoc.meta.gridSize = n;
    const sel = document.getElementById("desGridSize");
    if (sel && String(sel.value) !== String(n)) sel.value = String(n);
    const board = document.getElementById("designBoard");
    if (board) {
      board.setAttribute("data-grid", String(n));
      board.classList.toggle("is-grid-off", n === 0);
      board.style.setProperty("--grid-size", (n || DESIGN_GRID_DEFAULT) + "px");
    }
    const form = document.getElementById("designForm");
    if (form) {
      form.classList.toggle("is-grid-off", n === 0);
      form.style.setProperty("--grid-size", (n || DESIGN_GRID_DEFAULT) + "px");
    }
    if (!quiet) {
      touchDesignDirty();
      ensureDesignWorldExtent();
    }
  }

  function blankDesignDoc() {
    return {
      format: "sgenaxis.design",
      formatVersion: 1,
      meta: {
        title: "Untitled Form",
        updatedAt: "",
        targetStack: "vanilla-tauri",
        gridSize: DESIGN_GRID_DEFAULT,
        formSize: "800x600",
      },
      nodes: [
        {
          id: "node-form-root",
          type: "Form",
          parentId: null,
          props: { name: "Form", x: 0, y: 0, w: 800, h: 600, zIndex: 0, layout: "none" },
          bddHint: "",
          tddHint: "",
          behaviorHints: [],
        },
      ],
      selection: "node-form-root",
      product_pass: false,
    };
  }

  function formRootNode() {
    return (
      designDoc.nodes.find(function (n) {
        return n.type === "Form" && !n.parentId;
      }) || designDoc.nodes[0]
    );
  }

  function selectedDesignNode() {
    const id = designDoc.selection || "node-form-root";
    return (
      designDoc.nodes.find(function (n) {
        return n.id === id;
      }) || designDoc.nodes[0]
    );
  }

  function childDesignNodes() {
    const root = formRootNode();
    const rid = root ? root.id : null;
    return designDoc.nodes.filter(function (n) {
      return n.parentId === rid;
    });
  }

  function snapDesignValue(v, guides) {
    let best = v;
    let bestDist = DESIGN_SNAP_PX + 1;
    for (let i = 0; i < guides.length; i++) {
      const d = Math.abs(v - guides[i]);
      if (d <= DESIGN_SNAP_PX && d < bestDist) {
        bestDist = d;
        best = guides[i];
      }
    }
    return best;
  }

  function collectDesignAlignGuides(excludeId) {
    const root = formRootNode();
    const xs = [];
    const ys = [];
    if (root && root.props) {
      const rw = Number(root.props.w) || 0;
      const rh = Number(root.props.h) || 0;
      xs.push(0, rw / 2, rw);
      ys.push(0, rh / 2, rh);
    }
    childDesignNodes().forEach(function (n) {
      if (!n.props || n.id === excludeId) return;
      const x = Number(n.props.x) || 0;
      const y = Number(n.props.y) || 0;
      const w = Number(n.props.w) || 0;
      const h = Number(n.props.h) || 0;
      xs.push(x, x + w / 2, x + w);
      ys.push(y, y + h / 2, y + h);
    });
    return { xs: xs, ys: ys };
  }

  function snapNodeToGuides(node, guides) {
    if (!node || !node.props) return { xGuides: [], yGuides: [] };
    const w = Number(node.props.w) || 0;
    const h = Number(node.props.h) || 0;
    let x = Number(node.props.x) || 0;
    let y = Number(node.props.y) || 0;
    const candidatesX = [
      { edge: "l", val: x },
      { edge: "c", val: x + w / 2 },
      { edge: "r", val: x + w },
    ];
    const candidatesY = [
      { edge: "t", val: y },
      { edge: "m", val: y + h / 2 },
      { edge: "b", val: y + h },
    ];
    let bestX = null;
    let bestY = null;
    candidatesX.forEach(function (c) {
      const snapped = snapDesignValue(c.val, guides.xs);
      const dist = Math.abs(snapped - c.val);
      if (dist <= DESIGN_SNAP_PX && (!bestX || dist < bestX.dist)) {
        bestX = { edge: c.edge, guide: snapped, dist: dist };
      }
    });
    candidatesY.forEach(function (c) {
      const snapped = snapDesignValue(c.val, guides.ys);
      const dist = Math.abs(snapped - c.val);
      if (dist <= DESIGN_SNAP_PX && (!bestY || dist < bestY.dist)) {
        bestY = { edge: c.edge, guide: snapped, dist: dist };
      }
    });
    const g = getDesignGridPx();
    if (bestX) {
      if (bestX.edge === "l") x = bestX.guide;
      else if (bestX.edge === "c") x = bestX.guide - w / 2;
      else x = bestX.guide - w;
    } else if (g > 0) {
      x = Math.round(x / g) * g;
    }
    if (bestY) {
      if (bestY.edge === "t") y = bestY.guide;
      else if (bestY.edge === "m") y = bestY.guide - h / 2;
      else y = bestY.guide - h;
    } else if (g > 0) {
      y = Math.round(y / g) * g;
    }
    node.props.x = x;
    node.props.y = y;
    return {
      xGuides: bestX ? [bestX.guide] : [],
      yGuides: bestY ? [bestY.guide] : [],
    };
  }

  function applyDesignSnap(node) {
    const root = formRootNode();
    if (!node || !root || node.id === root.id || !node.props || !root.props) return;
    const layout = root.props.layout || "none";
    if (layout !== "none") return;
    snapNodeToGuides(node, collectDesignAlignGuides(node.id));
  }

  function clearDesignGuides() {
    const el = document.getElementById("designGuides");
    if (el) el.innerHTML = "";
  }

  function showDesignGuides(active) {
    const el = document.getElementById("designGuides");
    if (!el) return;
    el.innerHTML = "";
    (active.xGuides || []).forEach(function (x) {
      const line = document.createElement("div");
      line.className = "design-guide is-v";
      line.style.left = x + "px";
      el.appendChild(line);
    });
    (active.yGuides || []).forEach(function (y) {
      const line = document.createElement("div");
      line.className = "design-guide is-h";
      line.style.top = y + "px";
      el.appendChild(line);
    });
  }

  const DESIGN_WORLD_PAD = 640;
  const DESIGN_WORLD_MAX = 100000;

  /** Grid 無限延伸：artboard 世界隨 Form＋捲動自動長大。 */
  function ensureDesignWorldExtent(opts) {
    const quiet = opts && opts.quiet;
    const art = document.getElementById("designArtboard");
    const board = document.getElementById("designBoard");
    const canvas = document.getElementById("designCanvas");
    const root = formRootNode();
    const fw = (root && root.props && root.props.w) || 800;
    const fh = (root && root.props && root.props.h) || 600;
    const g = getDesignGridPx() || DESIGN_GRID_DEFAULT;
    let w = fw + DESIGN_WORLD_PAD;
    let h = fh + DESIGN_WORLD_PAD;
    if (art) {
      w = Math.max(w, Number(art.dataset.worldW) || 0);
      h = Math.max(h, Number(art.dataset.worldH) || 0);
    }
    if (canvas) {
      const zx = designZoom || 1;
      w = Math.max(w, canvas.scrollLeft / zx + canvas.clientWidth / zx + DESIGN_WORLD_PAD);
      h = Math.max(h, canvas.scrollTop / zx + canvas.clientHeight / zx + DESIGN_WORLD_PAD);
    }
    if (opts && opts.minW) w = Math.max(w, opts.minW);
    if (opts && opts.minH) h = Math.max(h, opts.minH);
    w = Math.min(DESIGN_WORLD_MAX, Math.ceil(w));
    h = Math.min(DESIGN_WORLD_MAX, Math.ceil(h));
    if (board) {
      board.style.setProperty("--grid-size", g + "px");
      board.classList.toggle("is-grid-off", getDesignGridPx() === 0);
      board.classList.add("is-infinite-grid");
    }
    if (art) {
      art.style.minWidth = w + "px";
      art.style.minHeight = h + "px";
      art.dataset.worldW = String(w);
      art.dataset.worldH = String(h);
      art.classList.toggle("is-grid-off", getDesignGridPx() === 0);
      art.classList.add("is-infinite-grid");
      art.style.setProperty("--grid-size", g + "px");
    }
    if (!quiet) renderDesignRulers(w, h);
    else renderDesignRulers(w, h);
    return { w: w, h: h };
  }

  function renderDesignRulers(rw, rh) {
    const board = document.getElementById("designBoard");
    const hEl = document.getElementById("designRulerH");
    const vEl = document.getElementById("designRulerV");
    const g = getDesignGridPx() || DESIGN_GRID_DEFAULT;
    if (board) board.style.setProperty("--grid-size", g + "px");
    if (!hEl || !vEl) return;
    const pad = 28;
    const hSpan = Math.max(rw + pad, 100);
    const vSpan = Math.max(rh + pad, 100);
    hEl.style.width = hSpan + "px";
    vEl.style.height = vSpan + "px";
    hEl.innerHTML = "";
    vEl.innerHTML = "";
    const major = 50;
    const minor = 10;
    /* 量尺 tick 對超大世界抽樣，避免 DOM 爆炸 */
    const step = hSpan > 8000 || vSpan > 8000 ? major : minor;
    for (let x = 0; x <= hSpan; x += step) {
      const tick = document.createElement("span");
      tick.className =
        "designer-ruler-tick" + (x % major === 0 ? " is-major" : "");
      tick.style.left = x + "px";
      hEl.appendChild(tick);
      if (x % major === 0) {
        const lab = document.createElement("span");
        lab.className = "designer-ruler-label";
        lab.style.left = x + "px";
        lab.textContent = String(x);
        hEl.appendChild(lab);
      }
    }
    for (let y = 0; y <= vSpan; y += step) {
      const tick = document.createElement("span");
      tick.className =
        "designer-ruler-tick" + (y % major === 0 ? " is-major" : "");
      tick.style.top = y + "px";
      vEl.appendChild(tick);
      if (y % major === 0 && y > 0) {
        const lab = document.createElement("span");
        lab.className = "designer-ruler-label";
        lab.style.top = y + "px";
        lab.textContent = String(y);
        vEl.appendChild(lab);
      }
    }
  }

  function clampDesignNodeInForm(node) {
    const root = formRootNode();
    if (!node || !node.props || !root || !root.props) return;
    const rw = Number(root.props.w) || 0;
    const rh = Number(root.props.h) || 0;
    const w = Number(node.props.w) || 0;
    const h = Number(node.props.h) || 0;
    node.props.x = Math.max(0, Math.min(Number(node.props.x) || 0, Math.max(0, rw - w)));
    node.props.y = Math.max(0, Math.min(Number(node.props.y) || 0, Math.max(0, rh - h)));
  }

  function updateDesignNodeDom(node) {
    if (!node || !node.props) return;
    const btn = document.querySelector(
      '#designNodes [data-node-id="' + node.id + '"]'
    );
    if (!btn) return;
    btn.style.left = (Number(node.props.x) || 0) + "px";
    btn.style.top = (Number(node.props.y) || 0) + "px";
    btn.style.width = Math.max(8, Number(node.props.w) || 120) + "px";
    btn.style.height = Math.max(8, Number(node.props.h) || 32) + "px";
  }

  function endDesignDrag(commit) {
    if (!designDrag) return;
    const node = designDoc.nodes.find(function (n) {
      return n.id === designDrag.nodeId;
    });
    if (node && commit) {
      clampDesignNodeInForm(node);
      applyDesignSnap(node);
      touchDesignDirty();
      updateDesignNodeDom(node);
      fillDesignProps();
    }
    clearDesignGuides();
    designDrag = null;
    document.body.classList.remove("is-design-dragging");
  }

  function onDesignPointerMove(ev) {
    if (!designDrag) return;
    const node = designDoc.nodes.find(function (n) {
      return n.id === designDrag.nodeId;
    });
    if (!node || !node.props) return;
    const dx = (ev.clientX - designDrag.startX) / (designDrag.scale || 1);
    const dy = (ev.clientY - designDrag.startY) / (designDrag.scale || 1);
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) designDragMoved = true;
    node.props.x = designDrag.originX + dx;
    node.props.y = designDrag.originY + dy;
    clampDesignNodeInForm(node);
    const active = snapNodeToGuides(
      node,
      collectDesignAlignGuides(node.id)
    );
    updateDesignNodeDom(node);
    showDesignGuides(active);
    const xEl = document.getElementById("desX");
    const yEl = document.getElementById("desY");
    if (xEl && document.activeElement !== xEl) xEl.value = String(node.props.x);
    if (yEl && document.activeElement !== yEl) yEl.value = String(node.props.y);
    touchDesignDirty();
  }

  function onDesignPointerUp() {
    endDesignDrag(true);
  }

  function beginDesignDrag(node, ev, el) {
    if (uidesignChromeMode !== "designer") return;
    const root = formRootNode();
    if (!node || !root || node.id === root.id || !node.props) return;
    if (root.props && root.props.layout && root.props.layout !== "none") return;
    designDragMoved = false;
    designDrag = {
      nodeId: node.id,
      startX: ev.clientX,
      startY: ev.clientY,
      originX: Number(node.props.x) || 0,
      originY: Number(node.props.y) || 0,
      scale: 1,
    };
    designDoc.selection = node.id;
    document.querySelectorAll("#designNodes .design-node").forEach(function (b) {
      b.classList.toggle("is-on", b.getAttribute("data-node-id") === node.id);
    });
    const form = document.getElementById("designForm");
    if (form) form.classList.remove("is-selected");
    fillDesignProps();
    if (uidesignChromeMode === "designer") setDesignInspectorActive(true);
    document.body.classList.add("is-design-dragging");
    if (el && el.setPointerCapture) {
      try {
        el.setPointerCapture(ev.pointerId);
      } catch (_e) {
        /* ignore */
      }
    }
  }

  function setUidesignStatusBadge(text, kind) {
    const badge = document.getElementById("uidesign-status-badge");
    if (!badge) return;
    badge.textContent = text;
    badge.classList.remove("ok", "warn", "error");
    if (kind) badge.classList.add(kind);
  }

  function setNavUidesignMeta(text) {
    const meta = document.getElementById("nav-uidesign-meta");
    if (meta) meta.textContent = text || "—";
  }

  function setUidesignStatus(msg, isError) {
    const line = document.getElementById("uidesign-status-line");
    if (!line) return;
    line.textContent = msg || "";
    line.classList.toggle("error", !!isError);
  }

  function setUidesignPathDisplay(path) {
    const el = document.getElementById("uidesign-path");
    if (el) el.textContent = path || UIDESIGN_DESIGN_REL;
  }

  let uidesignChromeMode = "designer";
  let inspectorDisplayBeforeViewer = "";

  function setUidesignWidgetsVisible(show) {
    const widgets = document.getElementById("sec-uidesign-widgets");
    if (widgets) {
      widgets.hidden = !show;
      widgets.classList.toggle("is-hidden", !show);
    }
    document.querySelectorAll(".uidesign-mode-list .status-item").forEach(function (btn) {
      const mode = btn.getAttribute("data-uidesign-mode");
      const on = mode === uidesignChromeMode;
      btn.classList.toggle("active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  function setDesignInspectorActive(active) {
    const designCard = document.getElementById("inspector-design");
    const archCard = document.getElementById("inspector-arch");
    const evidCard = document.getElementById("inspector-evidence");
    if (designCard) designCard.hidden = !active;
    if (active && archCard) archCard.hidden = true;
    if (evidCard) evidCard.hidden = !!active;
  }

  function setArchInspectorActive(active) {
    const archCard = document.getElementById("inspector-arch");
    const designCard = document.getElementById("inspector-design");
    const evidCard = document.getElementById("inspector-evidence");
    if (archCard) archCard.hidden = !active;
    if (active && designCard) designCard.hidden = true;
    if (evidCard) evidCard.hidden = !!active;
  }

  function setUidesignMode(mode) {
    uidesignChromeMode = mode === "viewer" ? "viewer" : "designer";
    const panel = document.getElementById("panel-uidesign");
    const win = document.getElementById("uidesign-window");
    const designer = document.getElementById("uidesign-designer");
    const canvas = document.getElementById("designCanvas");
    const editBar = document.querySelector(
      "#panel-uidesign .uidesign-toolbar"
    );
    const titleEl = document.getElementById("uidesign-window-title");
    const btns = document.querySelectorAll("[data-uidesign-mode]");
    btns.forEach(function (b) {
      const on = b.getAttribute("data-uidesign-mode") === uidesignChromeMode;
      b.classList.toggle("active", on);
      b.classList.toggle("is-active", on);
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    if (designer) designer.hidden = false;
    if (panel) {
      panel.classList.toggle(
        "panel-uidesign-viewer",
        uidesignChromeMode === "viewer"
      );
    }
    if (win) {
      win.classList.toggle(
        "uidesign-window-viewer",
        uidesignChromeMode === "viewer"
      );
    }
    if (titleEl && isUiDesignWindowOpen()) {
      titleEl.textContent =
        uidesignChromeMode === "viewer" ? "UI 預覽" : "UI 編輯";
    }
    if (designer) {
      designer.classList.toggle("is-preview", uidesignChromeMode === "viewer");
    }
    if (canvas) {
      canvas.classList.toggle("is-preview", uidesignChromeMode === "viewer");
    }
    const onUi = isUiDesignWindowOpen();
    if (uidesignChromeMode === "viewer") {
      setUidesignWidgetsVisible(false);
      if (inspector) {
        if (inspectorDisplayBeforeViewer === "") {
          inspectorDisplayBeforeViewer = inspector.style.display || "";
        }
        inspector.style.display = "none";
        document
          .getElementById("shell-body")
          ?.classList.add("is-inspector-collapsed");
      }
      if (editBar) editBar.hidden = true;
      setDesignInspectorActive(false);
    } else {
      setUidesignWidgetsVisible(!!onUi);
      if (inspector) {
        inspector.style.display =
          inspectorDisplayBeforeViewer === "none" ? "none" : "";
        inspectorDisplayBeforeViewer = "";
        if (inspector.style.display === "none") {
          document
            .getElementById("shell-body")
            ?.classList.add("is-inspector-collapsed");
        } else {
          inspector.style.display = "";
          inspector.removeAttribute("hidden");
          document
            .getElementById("shell-body")
            ?.classList.remove("is-inspector-collapsed");
        }
      }
      if (editBar) editBar.hidden = false;
      setDesignInspectorActive(!!onUi);
      if (onUi) {
        fillDesignProps();
        syncDesignSelectionToInspector();
      }
    }
    if (onUi) {
      setUidesignStatusBadge(
        uidesignChromeMode === "viewer"
          ? "狀態：Viewer 預覽（非驗收 PASS）"
          : "狀態：Editor（非驗收 PASS）",
        "ok"
      );
      setNavUidesignMeta(
        uidesignChromeMode === "viewer" ? "Viewer" : "Editor"
      );
    }
  }

  function renderDesignCanvas() {
    const form = document.getElementById("designForm");
    const nodesEl = document.getElementById("designNodes");
    const label = document.getElementById("designStateLabel");
    const tag = document.getElementById("designFormTag");
    if (!nodesEl) return;
    const root = formRootNode();
    const title = (designDoc.meta && designDoc.meta.title) || "Untitled";
    const rw = (root && root.props && root.props.w) || 800;
    const rh = (root && root.props && root.props.h) || 600;
    const layout = (root && root.props && root.props.layout) || "none";
    if (label) {
      label.textContent =
        "目前設計：" +
        title +
        " · " +
        rw +
        "×" +
        rh +
        (designDirty ? " · 未存" : "");
    }
    if (tag) tag.textContent = (root && root.props && root.props.name) || "Form";
    if (form) {
      form.setAttribute("data-node-id", root ? root.id : "node-form-root");
      form.style.width = rw + "px";
      form.style.height = rh + "px";
      form.style.setProperty(
        "--grid-size",
        (getDesignGridPx() || DESIGN_GRID_DEFAULT) + "px"
      );
      form.classList.toggle("is-grid-off", getDesignGridPx() === 0);
      form.classList.toggle(
        "is-selected",
        designDoc.selection === (root && root.id)
      );
      form.classList.remove(
        "is-layout-hbox",
        "is-layout-vbox",
        "is-layout-grid"
      );
      if (layout === "hbox") form.classList.add("is-layout-hbox");
      if (layout === "vbox") form.classList.add("is-layout-vbox");
      if (layout === "grid") form.classList.add("is-layout-grid");
    }
    ensureDesignWorldExtent({ quiet: true });
    if (!designDrag) clearDesignGuides();
    const layEl = document.getElementById("desLayoutMode");
    if (layEl && document.activeElement !== layEl) layEl.value = layout;
    nodesEl.innerHTML = "";
    const kids = childDesignNodes().slice().sort(function (a, b) {
      return (
        (Number(a.props && a.props.zIndex) || 0) -
        (Number(b.props && b.props.zIndex) || 0)
      );
    });
    kids.forEach(function (n) {
      if (!n.props) n.props = {};
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className =
        "design-node" + (designDoc.selection === n.id ? " is-on" : "");
      btn.setAttribute("data-node-id", n.id);
      btn.style.left = (Number(n.props.x) || 0) + "px";
      btn.style.top = (Number(n.props.y) || 0) + "px";
      btn.style.width = Math.max(8, Number(n.props.w) || 120) + "px";
      btn.style.height = Math.max(8, Number(n.props.h) || 32) + "px";
      btn.style.zIndex = String(Number(n.props.zIndex) || 1);
      const name = n.props.name || n.type;
      btn.innerHTML =
        '<span class="tag">' +
        escapeHtml(n.type) +
        '</span><span class="nm">' +
        escapeHtml(String(name)) +
        "</span>";
      btn.addEventListener("pointerdown", function (ev) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        ev.stopPropagation();
        beginDesignDrag(n, ev, btn);
      });
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (designDrag || designDragMoved) {
          designDragMoved = false;
          return;
        }
        selectDesignNode(n.id);
      });
      nodesEl.appendChild(btn);
    });
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function syncDesignSelectionToInspector() {
    const n = selectedDesignNode();
    const selTitle = document.getElementById("inspector-sel-title");
    const selBody = document.getElementById("inspector-sel-body");
    if (!n) return;
    if (selTitle) {
      selTitle.textContent =
        (n.props && n.props.name) || n.type || n.id || "設計節點";
    }
    if (selBody) {
      selBody.textContent =
        "type=" +
        n.type +
        " · id=" +
        n.id +
        " · " +
        ((n.props && n.props.w) || "?") +
        "×" +
        ((n.props && n.props.h) || "?") +
        " · 設計≠產品 PASS";
    }
  }

  function fillDesignProps() {
    const n = selectedDesignNode();
    if (!n) return;
    if (!n.props) n.props = {};
    const setVal = function (id, v) {
      const el = document.getElementById(id);
      if (el) el.value = v == null ? "" : v;
    };
    setVal("desName", n.props.name || n.type);
    setVal("desType", n.type);
    setVal("desId", n.id);
    setVal("desX", n.props.x != null ? n.props.x : 0);
    setVal("desY", n.props.y != null ? n.props.y : 0);
    setVal("desW", n.props.w != null ? n.props.w : "");
    setVal("desH", n.props.h != null ? n.props.h : "");
    setVal("desZ", n.props.zIndex != null ? n.props.zIndex : 0);
    setVal("desBehavior", (n.behaviorHints || []).join(", "));
    setVal("desBdd", n.bddHint || "");
    setVal("desTdd", n.tddHint || "");
    syncDesignSelectionToInspector();
    syncDesFormSizeSelect();
  }

  function selectDesignNode(id) {
    designDoc.selection = id;
    renderDesignCanvas();
    fillDesignProps();
    if (uidesignChromeMode === "designer") {
      setDesignInspectorActive(true);
    }
  }

  function applyPropsFromInputs() {
    const n = selectedDesignNode();
    if (!n) return;
    if (!n.props) n.props = {};
    const nameEl = document.getElementById("desName");
    const xEl = document.getElementById("desX");
    const yEl = document.getElementById("desY");
    const wEl = document.getElementById("desW");
    const hEl = document.getElementById("desH");
    const zEl = document.getElementById("desZ");
    const behEl = document.getElementById("desBehavior");
    const bddEl = document.getElementById("desBdd");
    const tddEl = document.getElementById("desTdd");
    if (nameEl) n.props.name = nameEl.value;
    if (xEl && xEl.value !== "") n.props.x = Number(xEl.value);
    if (yEl && yEl.value !== "") n.props.y = Number(yEl.value);
    if (wEl && wEl.value !== "") n.props.w = Math.max(8, Number(wEl.value));
    if (hEl && hEl.value !== "") n.props.h = Math.max(8, Number(hEl.value));
    if (zEl && zEl.value !== "") n.props.zIndex = Number(zEl.value);
    if (behEl) {
      n.behaviorHints = behEl.value
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean);
    }
    if (bddEl) n.bddHint = bddEl.value;
    if (tddEl) n.tddHint = tddEl.value;
    if (n.type === "Form" && nameEl) {
      if (!designDoc.meta) designDoc.meta = {};
      designDoc.meta.title = nameEl.value || designDoc.meta.title;
      designDoc.meta.formSize = designFormSizeToken(n.props.w, n.props.h);
      childDesignNodes().forEach(function (c) {
        clampDesignNodeInForm(c);
      });
    }
    if (n.type !== "Form") applyDesignSnap(n);
    touchDesignDirty();
    designDoc.product_pass = false;
    renderDesignCanvas();
    fillDesignProps();
  }

  function addPaletteNode(type) {
    if (type === "Form") {
      const root = formRootNode();
      if (root) selectDesignNode(root.id);
      return;
    }
    designPlaceSeq += 1;
    const id =
      "node-" +
      String(type).toLowerCase() +
      "-" +
      Math.random().toString(36).slice(2, 8);
    const root = formRootNode();
    designDoc.nodes.push({
      id: id,
      type: type,
      parentId: root ? root.id : "node-form-root",
      props: {
        name: type,
        x: 24 + (designPlaceSeq % 8) * 16,
        y: 40 + (designPlaceSeq % 8) * 16,
        w: 120,
        h: 32,
        zIndex: designPlaceSeq,
      },
      bddHint: "",
      tddHint: "",
      behaviorHints: [],
    });
    touchDesignDirty();
    selectDesignNode(id);
    setUidesignStatus("已加入 " + type + "（未存 · 非產品 PASS）", false);
  }

  function deleteSelectedDesignNode() {
    const n = selectedDesignNode();
    const root = formRootNode();
    if (!n || !root || n.id === root.id || n.type === "Form") {
      setUidesignStatus("Form 根節點不可刪除", true);
      toast("Form 不可刪除");
      return;
    }
    designDoc.nodes = designDoc.nodes.filter(function (x) {
      return x.id !== n.id;
    });
    touchDesignDirty();
    selectDesignNode(root.id);
    setUidesignStatus("已刪除選取（非產品 PASS）", false);
  }

  function duplicateSelectedDesignNode() {
    const n = selectedDesignNode();
    const root = formRootNode();
    if (!n || !root || n.id === root.id) {
      toast("請選取子元件再複製");
      return;
    }
    designPlaceSeq += 1;
    const id = "node-dup-" + Math.random().toString(36).slice(2, 8);
    const props = Object.assign({}, n.props || {}, {
      x: (Number(n.props.x) || 0) + 16,
      y: (Number(n.props.y) || 0) + 16,
      zIndex: (Number(n.props.zIndex) || 1) + 1,
      name: (n.props.name || n.type) + " 副本",
    });
    designDoc.nodes.push({
      id: id,
      type: n.type,
      parentId: root.id,
      props: props,
      bddHint: n.bddHint || "",
      tddHint: n.tddHint || "",
      behaviorHints: (n.behaviorHints || []).slice(),
    });
    touchDesignDirty();
    selectDesignNode(id);
    toast("已複製");
  }

  function bumpDesignZ(delta) {
    const n = selectedDesignNode();
    const root = formRootNode();
    if (!n || !root || n.id === root.id) return;
    if (!n.props) n.props = {};
    n.props.zIndex = (Number(n.props.zIndex) || 1) + delta;
    touchDesignDirty();
    renderDesignCanvas();
    fillDesignProps();
  }

  function alignSelectedDesign(kind) {
    const n = selectedDesignNode();
    const root = formRootNode();
    if (!n || !root || n.id === root.id || !n.props || !root.props) {
      toast("請選取子元件再對齊");
      return;
    }
    const fw = Number(root.props.w) || 800;
    const fh = Number(root.props.h) || 600;
    const w = Number(n.props.w) || 120;
    const h = Number(n.props.h) || 32;
    if (kind === "left") n.props.x = 0;
    if (kind === "hmid") n.props.x = Math.max(0, (fw - w) / 2);
    if (kind === "right") n.props.x = Math.max(0, fw - w);
    if (kind === "top") n.props.y = 0;
    if (kind === "vmid") n.props.y = Math.max(0, (fh - h) / 2);
    if (kind === "bottom") n.props.y = Math.max(0, fh - h);
    applyDesignSnap(n);
    touchDesignDirty();
    renderDesignCanvas();
    fillDesignProps();
  }

  function wireDesignerUi() {
    document.querySelectorAll("[data-uidesign-mode]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        showPanel("uidesign", { quiet: true });
        setUidesignMode(btn.getAttribute("data-uidesign-mode") || "designer");
      });
    });
    document.addEventListener("pointermove", onDesignPointerMove);
    document.addEventListener("pointerup", onDesignPointerUp);
    document.addEventListener("pointercancel", onDesignPointerUp);
    wireCanvasMiddleNav(document.getElementById("designCanvas"), {
      zoomBy: function (delta) {
        setDesignZoom(designZoom + delta);
      },
      step: 0.1,
    });
    document.getElementById("designCanvas")?.addEventListener(
      "scroll",
      function () {
        ensureDesignWorldExtent({ quiet: true });
      },
      { passive: true }
    );
    document.querySelectorAll("[data-palette]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        if (uidesignChromeMode !== "designer") setUidesignMode("designer");
        showPanel("uidesign", { quiet: true });
        addPaletteNode(btn.getAttribute("data-palette") || "Button");
      });
    });
    document.querySelectorAll("[data-design-tab]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        const tab = btn.getAttribute("data-design-tab");
        const root = document.getElementById("inspector-design") || document;
        root.querySelectorAll("[data-design-tab]").forEach(function (b) {
          b.classList.toggle(
            "is-active",
            b.getAttribute("data-design-tab") === tab
          );
        });
        root.querySelectorAll("[data-tab-panel]").forEach(function (p) {
          const on = p.getAttribute("data-tab-panel") === tab;
          p.hidden = !on;
          p.classList.toggle("is-active", on);
        });
      });
    });
    [
      "desName",
      "desX",
      "desY",
      "desW",
      "desH",
      "desZ",
      "desBehavior",
      "desBdd",
      "desTdd",
    ].forEach(function (id) {
      const el = document.getElementById(id);
      if (!el) return;
      el.addEventListener("change", applyPropsFromInputs);
      el.addEventListener("blur", applyPropsFromInputs);
    });
    document.getElementById("desLayoutMode")?.addEventListener(
      "change",
      function (ev) {
        const root = formRootNode();
        if (!root) return;
        if (!root.props) root.props = {};
        root.props.layout = ev.target.value || "none";
        touchDesignDirty();
        renderDesignCanvas();
      }
    );
    document.getElementById("desGridSize")?.addEventListener(
      "change",
      function (ev) {
        setDesignGridPx(ev.target.value, { quiet: false });
        renderDesignCanvas();
      }
    );
    document.getElementById("desFormSize")?.addEventListener(
      "change",
      function (ev) {
        const v = ev.target.value || "";
        if (v === "custom") {
          const root = formRootNode();
          if (root) selectDesignNode(root.id);
          toast("請在 Inspector 調整 Form 的 W／H");
          return;
        }
        const parsed = parseDesignFormSizeToken(v);
        if (parsed) setDesignFormSize(parsed.w, parsed.h);
      }
    );
    const form = document.getElementById("designForm");
    if (form) {
      form.addEventListener("click", function (ev) {
        if (ev.target === form || ev.target.id === "designFormTag") {
          const root = formRootNode();
          if (root) selectDesignNode(root.id);
        }
      });
    }
    document.addEventListener("keydown", function (ev) {
      const t = ev.target;
      const typing =
        t &&
        (t.tagName === "INPUT" ||
          t.tagName === "TEXTAREA" ||
          t.tagName === "SELECT" ||
          t.isContentEditable);
      if (typing) return;
      if (!isUiDesignWindowOpen()) return;
      if (ev.key === "Delete" || ev.key === "Backspace") {
        ev.preventDefault();
        deleteSelectedDesignNode();
      }
      if ((ev.ctrlKey || ev.metaKey) && (ev.key === "d" || ev.key === "D")) {
        ev.preventDefault();
        duplicateSelectedDesignNode();
      }
    });
    setDesignGridPx(
      (designDoc.meta && designDoc.meta.gridSize) != null
        ? designDoc.meta.gridSize
        : DESIGN_GRID_DEFAULT,
      { quiet: true }
    );
    renderDesignCanvas();
    fillDesignProps();
    setUidesignPathDisplay(UIDESIGN_DESIGN_REL);
    setUidesignStatusBadge("狀態：Editor（非驗收 PASS）", "ok");
    setNavUidesignMeta("Editor");
  }

  async function cmdUidesignSave() {
    applyPropsFromInputs();
    if (!invoke) {
      setUidesignStatus(
        "瀏覽器模式：uidesign_save_design NOT RUN（需 Tauri）",
        true
      );
      toast("儲存 NOT RUN（無 IPC）");
      return;
    }
    try {
      const args = { doc: designDoc, rel_path: UIDESIGN_DESIGN_REL };
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      const dto = await invoke("uidesign_save_design", { args: args });
      if (dto && dto.product_pass === true) {
        setUidesignStatus("契約違反：design 不得 product_pass=true", true);
        return;
      }
      designDirty = false;
      if (dto && dto.path) setUidesignPathDisplay(dto.path);
      setUidesignStatus(
        (dto && dto.message) || "已儲存 .sgendesign（非產品 PASS）",
        false
      );
      setUidesignStatusBadge("狀態：已存（非驗收 PASS）", "ok");
      renderDesignCanvas();
      toast("已儲存 .sgendesign");
    } catch (err) {
      setUidesignStatus("儲存失敗：" + String(err), true);
      toast("儲存失敗");
    }
  }

  async function cmdUidesignLoad() {
    if (!invoke) {
      setUidesignStatus(
        "瀏覽器模式：uidesign_load_design NOT RUN（需 Tauri）",
        true
      );
      toast("開啟 NOT RUN（無 IPC）");
      return;
    }
    try {
      const args = { rel_path: UIDESIGN_DESIGN_REL };
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      const dto = await invoke("uidesign_load_design", { args: args });
      if (!dto || !dto.doc) throw new Error("empty doc");
      if (dto.product_pass === true || dto.doc.product_pass === true) {
        setUidesignStatus("契約違反：design 不得 product_pass=true", true);
        return;
      }
      designDoc = dto.doc;
      designDoc.product_pass = false;
      if (!designDoc.meta) designDoc.meta = {};
      designDirty = false;
      setDesignGridPx(
        designDoc.meta.gridSize != null
          ? designDoc.meta.gridSize
          : DESIGN_GRID_DEFAULT,
        { quiet: true }
      );
      if (dto.path) setUidesignPathDisplay(dto.path);
      renderDesignCanvas();
      fillDesignProps();
      setUidesignMode("designer");
      setUidesignStatus(
        (dto.message || "已載入") + "（非產品 PASS）",
        false
      );
      setUidesignStatusBadge("狀態：已載入（非驗收 PASS）", "ok");
      toast("已開啟 .sgendesign");
    } catch (err) {
      setUidesignStatus("開啟失敗：" + String(err), true);
      toast("開啟失敗");
    }
  }

  async function cmdUidesignBuild() {
    applyPropsFromInputs();
    if (!invoke) {
      setUidesignStatus(
        "瀏覽器模式：uidesign_build_preview NOT RUN（需 Tauri）",
        true
      );
      toast("Build NOT RUN（無 IPC）");
      return;
    }
    try {
      const args = {
        doc: designDoc,
        name: "main",
        open_after: true,
      };
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      const dto = await invoke("uidesign_build_preview", { args: args });
      if (dto && dto.product_pass === true) {
        setUidesignStatus("契約違反：preview 不得 product_pass=true", true);
        return;
      }
      setUidesignStatus(
        ((dto && dto.message) || "已 Build") +
          (dto && dto.path ? " → " + dto.path : "") +
          "（溝通用 · 非正式 PASS）",
        false
      );
      setUidesignStatusBadge("狀態：預覽已建（非驗收 PASS）", "ok");
      toast("已 Build 溝通預覽");
    } catch (err) {
      setUidesignStatus("Build 失敗：" + String(err), true);
      toast("Build 失敗");
    }
  }

  async function cmdUidesignAsk() {
    applyPropsFromInputs();
    const n = selectedDesignNode();
    const noteEl = document.getElementById("desAskNote");
    const outEl = document.getElementById("desAskOut");
    if (!invoke) {
      const local =
        "BDD 草稿（離線）：Given 節點 " +
        (n && n.type) +
        "「" +
        ((n && n.props && n.props.name) || "") +
        "」, When Ask Agent, Then 產出可讀需求草稿。\n（設計草稿≠產品驗收 PASS）\nNOT RUN：無 IPC";
      if (outEl) {
        outEl.hidden = false;
        outEl.textContent = local;
      }
      setUidesignStatus("Ask Agent NOT RUN（瀏覽器無 IPC）", true);
      toast("Ask Agent NOT RUN");
      return;
    }
    try {
      const dto = await invoke("uidesign_ask_agent", {
        args: {
          node: n,
          user_note: noteEl ? noteEl.value : "",
          upsert_gray: true,
        },
      });
      if (dto && dto.product_pass === true) {
        setUidesignStatus("契約違反：Ask 不得 product_pass=true", true);
        return;
      }
      const text =
        (dto.title || "") +
        "\n\n" +
        (dto.bdd_draft || "") +
        (dto.upserted
          ? "\n\n已 upsert 灰燈：" + (dto.work_item_id || "")
          : "");
      if (outEl) {
        outEl.hidden = false;
        outEl.textContent = text;
      }
      setUidesignStatus(
        (dto.message || "Ask Agent 草稿就緒") + "（非產品 PASS）",
        false
      );
      toast(dto.upserted ? "已草稿＋灰燈工項" : "已產出草稿");
    } catch (err) {
      setUidesignStatus("Ask Agent 失敗：" + String(err), true);
      toast("Ask Agent 失敗");
    }
  }

  function showUidesignEmpty(title, body, statusMsg, badgeKind) {
    const empty = document.getElementById("uidesign-empty");
    const layout = document.getElementById("uidesign-layout");
    const frame = document.getElementById("uidesign-frame");
    if (layout) layout.hidden = true;
    if (frame) {
      frame.removeAttribute("src");
      frame.removeAttribute("srcdoc");
    }
    if (empty) {
      empty.hidden = false;
      empty.setAttribute("data-uidesign-state", "empty");
      const t = document.getElementById("uidesign-empty-title");
      const b = document.getElementById("uidesign-empty-body");
      if (t) t.textContent = title || "尚未載入設計包";
      if (b) {
        b.innerHTML =
          body ||
          "預期本機路徑 <code>" +
            UIDESIGN_REL_PATH +
            "</code>。設計稿非產品證據，禁當正式驗收 PASS。";
      }
    }
    setUidesignStatusBadge(
      badgeKind === "warn" ? "狀態：空態／NOT RUN" : "狀態：空態",
      badgeKind || "warn"
    );
    setNavUidesignMeta(badgeKind === "warn" ? "空" : "—");
    if (statusMsg) setUidesignStatus(statusMsg, false);
  }

  function showUidesignEmbed(path, embedUrl) {
    const empty = document.getElementById("uidesign-empty");
    const layout = document.getElementById("uidesign-layout");
    const frame = document.getElementById("uidesign-frame");
    if (empty) empty.hidden = true;
    if (layout) layout.hidden = false;
    if (frame) {
      let src = embedUrl || "";
      if (!src && path) {
        const convert =
          window.__TAURI__ &&
          window.__TAURI__.core &&
          typeof window.__TAURI__.core.convertFileSrc === "function"
            ? window.__TAURI__.core.convertFileSrc
            : null;
        src = convert
          ? convert(path)
          : "file:///" + String(path).replace(/\\/g, "/");
      }
      if (src) frame.setAttribute("src", src);
    }
    setUidesignStatusBadge("狀態：已內嵌（非驗收 PASS）", "ok");
    setNavUidesignMeta("內嵌");
    setUidesignStatus(
      "已內嵌設計包（設計稿 ≠ 產品證據；禁當正式驗收 PASS）：" + (path || ""),
      false
    );
  }

  function applyUidesignPackageDto(dto, preferEmbed) {
    lastUidesignPkg = dto || null;
    if (!dto) {
      showUidesignEmpty(
        "無設計包狀態",
        "尚未取得 <code>uidesign_package_status</code>。",
        "無投影",
        "warn"
      );
      return;
    }
    const path = dto.path || UIDESIGN_REL_PATH;
    setUidesignPathDisplay(path);
    // Hard labels — design package must never be treated as product evidence / formal PASS.
    if (dto.product_evidence === true || dto.formal_acceptance_pass === true) {
      setUidesignStatus(
        "契約違反：設計包不得標 product_evidence／formal_acceptance_pass",
        true
      );
      showUidesignEmpty(
        "投影契約錯誤",
        "設計稿不得標為產品證據或正式驗收 PASS。",
        "契約違反",
        "error"
      );
      return;
    }
    if (dto.status === "unbound" || !dto.exists) {
      const reason =
        dto.message ||
        "找不到 " +
          UIDESIGN_REL_PATH +
          "（相對專案根）。請確認專案已綁定且設計包存在。";
      showUidesignEmpty(
        dto.status === "unbound" ? "未綁定專案根" : "設計包不存在",
        reason + " 設計稿非產品證據，禁當正式驗收 PASS。",
        reason,
        "warn"
      );
      return;
    }
    if (preferEmbed) {
      showUidesignEmbed(path, dto.embed_hint || null);
    } else {
      const empty = document.getElementById("uidesign-empty");
      const layout = document.getElementById("uidesign-layout");
      if (layout) layout.hidden = true;
      if (empty) {
        empty.hidden = false;
        empty.setAttribute("data-uidesign-state", "ready");
        const t = document.getElementById("uidesign-empty-title");
        const b = document.getElementById("uidesign-empty-body");
        if (t) t.textContent = "設計包就緒（尚未內嵌）";
        if (b) {
          b.innerHTML =
            "路徑 <code>" +
            path +
            "</code> 存在。可「內嵌載入」或「開啟設計包」。設計稿 ≠ 產品證據；禁當正式驗收 PASS。";
        }
      }
      setUidesignStatusBadge("狀態：就緒（非驗收 PASS）", "ok");
      setNavUidesignMeta("就緒");
      setUidesignStatus(
        "設計包存在（非產品證據）：" + path,
        false
      );
    }
  }

  async function cmdUidesignRefresh() {
    if (!invoke) {
      setUidesignPathDisplay(
        (cachedProjectRoot
          ? cachedProjectRoot.replace(/[\\/]+$/, "") + "/"
          : "") + UIDESIGN_REL_PATH
      );
      showUidesignEmpty(
        "無 IPC（瀏覽器模式）",
        "UI 設計工具入口就緒；需 Tauri 才呼叫 <code>uidesign_package_status</code>。預期路徑 <code>" +
          UIDESIGN_REL_PATH +
          "</code>。設計稿非產品證據，禁當正式驗收 PASS。",
        "瀏覽器模式：UI 設計 NOT RUN",
        "warn"
      );
      return;
    }
    try {
      const args = {};
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      const dto = await invoke("uidesign_package_status", { args: args });
      applyUidesignPackageDto(dto, false);
    } catch (err) {
      showUidesignEmpty(
        "設計包狀態失敗",
        "uidesign_package_status 錯誤：" + String(err),
        "uidesign_package_status 失敗：" + String(err),
        "warn"
      );
      toast("設計包狀態失敗");
    }
  }

  async function cmdUidesignEmbed() {
    if (!invoke) {
      showUidesignEmpty(
        "無 IPC（瀏覽器模式）",
        "無法內嵌；需 Tauri <code>uidesign_package_status</code>。",
        "瀏覽器模式：內嵌 NOT RUN",
        "warn"
      );
      return;
    }
    try {
      const args = {};
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      const dto = await invoke("uidesign_package_status", { args: args });
      applyUidesignPackageDto(dto, true);
      if (dto && dto.exists) toast("已內嵌設計包（非驗收 PASS）");
      else toast("設計包不存在，無法內嵌");
    } catch (err) {
      setUidesignStatus("內嵌失敗：" + String(err), true);
      toast("內嵌失敗");
    }
  }

  async function cmdUidesignOpen() {
    if (!invoke) {
      showUidesignEmpty(
        "無 IPC（瀏覽器模式）",
        "無法開啟；需 Tauri <code>uidesign_open_package</code>。預期路徑 <code>" +
          UIDESIGN_REL_PATH +
          "</code>。",
        "瀏覽器模式：開啟 NOT RUN",
        "warn"
      );
      return;
    }
    try {
      const args = {};
      if (cachedProjectRoot) args.project_root = cachedProjectRoot;
      const dto = await invoke("uidesign_open_package", { args: args });
      if (dto && dto.path) setUidesignPathDisplay(dto.path);
      if (dto && dto.opened) {
        setUidesignStatus(
          "已受控開啟設計包（非產品證據／非驗收 PASS）：" + (dto.path || ""),
          false
        );
        setUidesignStatusBadge("狀態：已開啟（非驗收 PASS）", "ok");
        setNavUidesignMeta("開啟");
        toast("已開啟設計包（非驗收 PASS）");
      } else {
        const msg = (dto && dto.message) || "開啟失敗或檔案不存在";
        setUidesignStatus(msg, true);
        toast(msg);
        if (!lastUidesignPkg || !lastUidesignPkg.exists) {
          showUidesignEmpty(
            "無法開啟設計包",
            msg + " 預期 <code>" + UIDESIGN_REL_PATH + "</code>。設計稿非產品證據。",
            msg,
            "warn"
          );
        }
      }
    } catch (err) {
      setUidesignStatus("開啟失敗：" + String(err), true);
      toast("開啟設計包失敗");
    }
  }

  function showPortsEmpty(title, body, statusMsg) {
    const empty = document.getElementById("ports-empty");
    const layout = document.getElementById("ports-layout");
    const list = document.getElementById("ports-entries");
    if (layout) layout.hidden = true;
    if (list) {
      list.innerHTML = "";
      list.hidden = true;
    }
    if (empty) {
      empty.hidden = false;
      empty.setAttribute("data-ports-state", "empty");
      const t = document.getElementById("ports-empty-title");
      const b = document.getElementById("ports-empty-body");
      if (t && title) t.textContent = title;
      if (b && body) b.textContent = body;
    }
    const countEl = document.getElementById("ports-entry-count");
    if (countEl) countEl.textContent = "0";
    setPortsStatusBadge("狀態：空", "warn");
    setNavPortsMeta("空");
    setPortsStatusLine(statusMsg || "ports_status：empty", false);
  }

  function showPortsProjection() {
    const empty = document.getElementById("ports-empty");
    const layout = document.getElementById("ports-layout");
    if (empty) {
      empty.hidden = true;
      empty.setAttribute("data-ports-state", "ok");
    }
    if (layout) layout.hidden = false;
  }

  function renderPortsEntries(entries) {
    const list = document.getElementById("ports-entries");
    const countEl = document.getElementById("ports-entry-count");
    const rows = Array.isArray(entries) ? entries : [];
    if (countEl) countEl.textContent = String(rows.length);
    if (!list) return;
    list.innerHTML = "";
    if (rows.length === 0) {
      list.hidden = true;
      return;
    }
    list.hidden = false;
    rows.forEach(function (e) {
      const li = document.createElement("li");
      li.className = "ports-item";
      const status = String((e && e.status) || "empty");
      li.innerHTML =
        '<span class="port-name">' +
        escapeHtml((e && e.port) || "—") +
        '</span><span class="adapter-name">' +
        escapeHtml((e && e.adapter) || "—") +
        '</span><span class="bind-status" data-status="' +
        escapeHtml(status) +
        '">' +
        escapeHtml(status) +
        '</span><span class="bind-detail">' +
        escapeHtml((e && e.detail) || "") +
        "</span>";
      list.appendChild(li);
    });
  }

  function applyPortsStatusDto(dto) {
    if (!dto || typeof dto !== "object") {
      showPortsEmpty(
        "尚無註冊 Port",
        "ports_status 回傳空白。空態可接受；不列 OS。",
        "ports_status：empty"
      );
      return false;
    }
    const entries = Array.isArray(dto.entries) ? dto.entries : [];
    const status = String(dto.status || "").toLowerCase();
    if (status === "empty" || entries.length === 0) {
      showPortsEmpty(
        "尚無註冊 Port",
        dto.message ||
          "無已註冊 Port／adapter。空態可接受；UI 不直列 OS。",
        "ports_status：empty" +
          (dto.message ? " · " + dto.message : "")
      );
      return true;
    }
    showPortsProjection();
    renderPortsEntries(entries);
    setPortsStatusBadge("狀態：" + (dto.status || "ok"), "ok");
    setNavPortsMeta(String(dto.entry_count || entries.length) + " ports");
    setPortsStatusLine(
      "ports_status · " +
        (dto.entry_count || entries.length) +
        " 註冊（Command 投影；非 OS 列舉）",
      false
    );
    return true;
  }

  async function cmdPortsRefresh() {
    if (!invoke) {
      showPortsEmpty(
        "無 IPC（瀏覽器模式）",
        "Ports 入口就緒；空態可接受。需 tauri dev 才 invoke ports_status。不列 OS。",
        "瀏覽器模式：ports_status 無 IPC → empty"
      );
      toast("Ports 投影需 Tauri IPC（空態 OK）");
      setStatus("ports.refresh — 需 Tauri；空態 OK");
      return;
    }
    setPortsStatusLine("載入 ports_status…", false);
    try {
      const dto = await invoke("ports_status");
      applyPortsStatusDto(dto);
      toast("Ports 投影已更新");
      setStatus("ports_status → 投影");
    } catch (err) {
      showPortsEmpty(
        "Ports 投影失敗",
        "ports_status 錯誤（非直列 OS）：" + String(err),
        "ports_status 失敗：" + String(err)
      );
      toast("Ports 投影失敗");
    }
  }

  const SIDE_TAB_BY_PANEL = {
    arch: "diagram",
    board: "tasks",
    git: "git",
    settings: "settings",
  };

  function setSideDrawerOpen(open) {
    const side = document.getElementById("sidebar");
    if (!side) return;
    side.setAttribute("data-drawer-open", open ? "true" : "false");
  }

  function isSideDrawerOpen() {
    const side = document.getElementById("sidebar");
    return !side || side.getAttribute("data-drawer-open") !== "false";
  }

  function syncSideTabs(panelId) {
    const sideKey = SIDE_TAB_BY_PANEL[panelId] || null;
    document
      .querySelectorAll(".side-tab[data-side-tab]")
      .forEach(function (tab) {
        const on =
          sideKey != null && tab.getAttribute("data-side-tab") === sideKey;
        tab.setAttribute("aria-selected", on ? "true" : "false");
      });
    document
      .querySelectorAll(".side-tab-panel[data-side-panel]")
      .forEach(function (panel) {
        const on =
          sideKey != null && panel.getAttribute("data-side-panel") === sideKey;
        if (on) {
          panel.removeAttribute("hidden");
        } else {
          panel.setAttribute("hidden", "");
        }
      });
    const more = document.getElementById("sec-nav-secondary");
    if (more) {
      more.classList.toggle("has-active-secondary", !sideKey && !!panelId);
    }
    if (sideKey) {
      setSideDrawerOpen(true);
      setSideMoreOpen(false);
    }
  }

  function setSideMoreOpen(open) {
    const side = document.getElementById("sidebar");
    const wrap = document.getElementById("sec-nav-secondary");
    const toggle = document.getElementById("side-more-toggle");
    const menu = document.getElementById("side-more-menu");
    if (!toggle || !menu) return;
    const next = !!open;
    if (side) side.classList.toggle("is-more-open", next);
    if (wrap) wrap.classList.toggle("is-open", next);
    toggle.setAttribute("aria-expanded", next ? "true" : "false");
    if (next) {
      menu.removeAttribute("hidden");
      setSideDrawerOpen(true);
      document.querySelectorAll(".side-tab[data-side-tab]").forEach(function (tab) {
        tab.setAttribute("aria-selected", "false");
      });
    } else {
      menu.setAttribute("hidden", "");
    }
  }

  function showPanel(panelId, opts) {
    if (!PANEL_TITLES[panelId]) return;
    /* UI 設計改為獨立視窗：不佔主區 panel，也不從側欄進入 */
    if (panelId === "uidesign") {
      openUiDesignWindow(
        (opts && opts.uidesignMode) || uidesignChromeMode || "designer",
        opts
      );
      return;
    }
    const quiet = opts && opts.quiet;
    document.querySelectorAll(".panel").forEach(function (panel) {
      const match = panel.dataset.panel === panelId;
      panel.classList.toggle("active", match);
      if (match) {
        panel.removeAttribute("hidden");
      } else {
        panel.setAttribute("hidden", "");
      }
    });
    document.querySelectorAll(".nav-item[data-panel]").forEach(function (btn) {
      const selected = btn.dataset.panel === panelId;
      btn.setAttribute("aria-selected", selected ? "true" : "false");
    });
    syncSideTabs(panelId);
    if (SIDE_TAB_BY_PANEL[panelId] && !(opts && opts.keepMoreOpen)) {
      setSideMoreOpen(false);
    }
    // Tasks Status：僅板面篩選
    if (panelId !== "board") {
      document
        .querySelectorAll(".status-item[data-filter]")
        .forEach(function (btn) {
          btn.classList.remove("active");
          btn.setAttribute("aria-selected", "false");
        });
    } else {
      updateFilterChrome(boardFilter);
    }
    const title = PANEL_TITLES[panelId];
    setStatus("主區：" + title);
    if (!quiet) toast("切換至「" + title + "」");
    if (panelId === "settings") {
      cmdLoadSettings();
    }
    if (panelId === "board" && !lastBoard && !invoke) {
      renderBoard(null);
    }
    if (panelId === "git") {
      applyWriteGate(false);
      cmdGitRefresh();
    }
    if (panelId === "deploy") {
      cmdDeployRefresh();
    }
    if (panelId === "ports") {
      cmdPortsRefresh();
    }
    if (panelId === "arch") {
      renderArchDag();
      if (lastArchProj && lastArchProj.live) {
        renderArchProjection(lastArchProj);
      } else if (invoke) {
        cmdArchRefresh();
      } else {
        setArchBanner(
          "無 IPC（瀏覽器模式）",
          "草稿畫布可用；live 需 Tauri。禁止靜態假圖冒充 live。",
          true
        );
        setArchLiveBadge("來源：NOT RUN（無 IPC）", "warn");
        setArchStatusLine("瀏覽器模式：架構 NOT RUN", true);
      }
    } else {
      setArchInspectorActive(false);
    }
    if (panelId === "listen") {
      if (invoke) {
        cmdListenRefresh();
      } else {
        showListenEmpty(
          "無 IPC（瀏覽器模式）",
          "監聽入口就緒；無 Command 投影 → NOT RUN。禁 UI 自建 notify。",
          "瀏覽器模式：監聽 NOT RUN"
        );
      }
    }
    if (panelId === "spec") {
      if (lastSpecProj && lastSpecProj.loaded) {
        renderSpecProjection(lastSpecProj);
      } else if (invoke) {
        cmdSpecRefresh();
      } else {
        showSpecEmpty();
        setSpecStatus("瀏覽器模式：無 IPC；可切換至此空狀態");
      }
    }
    if (panelId === "report" && !invoke) {
      showReportEmpty(
        "無 IPC（瀏覽器模式）",
        "報告入口就緒；空 evid → NOT RUN。需 tauri dev 才呼叫 pd_report。",
        "瀏覽器模式：報告入口就緒"
      );
      setReportStatusBadge("狀態：NOT RUN", "warn");
      setNavReportMeta("NOT RUN");
    }
    if (!isUiDesignWindowOpen()) {
      setDesignInspectorActive(false);
      if (inspector && inspectorDisplayBeforeViewer !== "") {
        inspector.style.display =
          inspectorDisplayBeforeViewer === "none" ? "none" : "";
        inspectorDisplayBeforeViewer = "";
      }
    }
  }

  /** PD-SHELL-SIDEBAR-01: clear Tasks Status filter → overview (Workbench 全部). */
  function clearStatusFilter() {
    setBoardFilter("overview");
    toast("篩選：全部（總覽）");
  }

  function closeMenus() {
    document.querySelectorAll(".menu-wrap.open").forEach(function (wrap) {
      wrap.classList.remove("open");
      const btn = wrap.querySelector(".menu-btn");
      if (btn) btn.setAttribute("aria-expanded", "false");
    });
    setSideMoreOpen(false);
  }

  /**
   * PD-REMAIN-WIN-RESET-01 — default chrome layout (local UI state; no OS／adapter).
   * Restores: Diagram tab, overview filter, Inspector visible, menus closed.
   */
  const DEFAULT_CHROME_LAYOUT = {
    panel: "arch",
    boardFilter: "overview",
    inspectorVisible: true,
    tasksStatusOpen: true,
  };

  function applyDefaultChromeLayout() {
    const appEl = document.getElementById("app");

    closeMenus();
    if (pendingGitWrite) {
      hideGitApprove();
    }

    if (inspector) {
      const bodyEl = document.getElementById("shell-body");
      if (DEFAULT_CHROME_LAYOUT.inspectorVisible) {
        inspector.style.display = "";
        inspector.removeAttribute("hidden");
        if (bodyEl) bodyEl.classList.remove("is-inspector-collapsed");
      } else {
        inspector.style.display = "none";
        if (bodyEl) bodyEl.classList.add("is-inspector-collapsed");
      }
    }
    applyShellColumnWidths(260, 390);
    persistShellLayout();

    boardFilter = FILTER_TITLES[DEFAULT_CHROME_LAYOUT.boardFilter]
      ? DEFAULT_CHROME_LAYOUT.boardFilter
      : "overview";
    showPanel(DEFAULT_CHROME_LAYOUT.panel || "arch", { quiet: true });
    updateFilterChrome(boardFilter);
    if (lastBoard) {
      renderBoard(lastBoard);
    }

    if (appEl) {
      appEl.setAttribute("data-chrome-layout", "default");
    }
  }

  function cmdWinReset() {
    try {
      applyDefaultChromeLayout();
      toast("已重設佈局為預設（看板 · Inspector 顯示 · Tasks 展開）");
      setStatus("win.reset → 預設 chrome 佈局");
    } catch (err) {
      const msg = "重設佈局失敗（可讀）：" + String(err);
      toast(msg);
      setStatus(msg);
      const appEl = document.getElementById("app");
      if (appEl) {
        appEl.setAttribute("data-chrome-layout", "error");
      }
    }
  }

  function toggleMenu(wrap) {
    const wasOpen = wrap.classList.contains("open");
    closeMenus();
    if (!wasOpen) {
      wrap.classList.add("open");
      const btn = wrap.querySelector(".menu-btn");
      if (btn) btn.setAttribute("aria-expanded", "true");
    }
  }

  function setSettingsStatus(message, isError) {
    const el = document.getElementById("settings-status");
    if (el) {
      el.textContent = message;
      el.classList.toggle("error", !!isError);
    }
  }

  function isMcpEndpointActivatable(endpoint) {
    const t = (endpoint || "").trim();
    if (!t) return false;
    if (t.indexOf(":8788") !== -1 || t.indexOf(":8787") !== -1) return false;
    return true;
  }

  function isBoardPathAcceptable(path) {
    const t = (path || "").trim();
    if (!t) return true;
    if (/^https?:\/\//i.test(t)) return false;
    if (t.indexOf(":8788") !== -1 || t.indexOf(":8787") !== -1) return false;
    return true;
  }

  function selectedRunMode() {
    const live = document.getElementById("mode-live");
    if (live && live.checked) return "live";
    return "dry-run";
  }

  function setRunModeRadios(mode) {
    const dry = document.getElementById("mode-dry-run");
    const live = document.getElementById("mode-live");
    const isLive = mode === "live";
    if (dry) dry.checked = !isLive;
    if (live) live.checked = isLive;
  }

  function updateModeBadge(agentActive) {
    const badge = document.getElementById("settings-mode-badge");
    const meta = document.getElementById("settings-active-meta");
    const mode = agentActive ? "live" : "dry-run";
    if (badge) {
      badge.dataset.mode = mode;
      badge.textContent = agentActive ? "Live" : "DryRun";
    }
    if (meta) {
      meta.textContent = "agent_active=" + !!agentActive;
    }
    setRunModeRadios(mode);
  }

  function readAgentFormArgs(activate) {
    const allowRaw = (document.getElementById("mcp-allowlist") || {}).value || "";
    const secret = (document.getElementById("mcp-secret") || {}).value || "";
    return {
      activate: !!activate,
      selected: (document.getElementById("cli-selected") || {}).value || "claude",
      claude_path: (document.getElementById("cli-claude-path") || {}).value || "",
      cursor_agent_path: (document.getElementById("cli-cursor-path") || {}).value || "",
      codex_path: (document.getElementById("cli-codex-path") || {}).value || "",
      antigravity_path: (document.getElementById("cli-antigravity-path") || {}).value || "",
      transport: (document.getElementById("mcp-transport") || {}).value || "stdio",
      server_name: (document.getElementById("mcp-server") || {}).value || "",
      endpoint: (document.getElementById("mcp-endpoint") || {}).value || "",
      approved_tools: allowRaw
        .split(",")
        .map(function (s) {
          return s.trim();
        })
        .filter(Boolean),
      secret_token: secret ? secret : null,
    };
  }

  function readBoardPath() {
    return ((document.getElementById("settings-board-path") || {}).value || "").trim();
  }

  function readProjectRoot() {
    return ((document.getElementById("settings-project-root") || {}).value || "").trim();
  }

  function applySettingsDto(dto) {
    if (!dto) return;
    const setVal = function (id, v) {
      const el = document.getElementById(id);
      if (el && v != null) el.value = v;
    };
    applyProjectBindingFromDto(dto);
    if (dto.project_root != null) {
      setVal("settings-project-root", dto.project_root);
    }
    if (dto.board_path != null) {
      setVal("settings-board-path", dto.board_path);
    }
    if (dto.agent_cli) {
      setVal("cli-selected", dto.agent_cli.selected);
      setVal("cli-claude-path", dto.agent_cli.claude_path);
      setVal("cli-cursor-path", dto.agent_cli.cursor_agent_path);
      setVal("cli-codex-path", dto.agent_cli.codex_path);
      setVal("cli-antigravity-path", dto.agent_cli.antigravity_path);
    }
    if (dto.agent_mcp) {
      setVal("mcp-transport", dto.agent_mcp.transport);
      setVal("mcp-server", dto.agent_mcp.server_name);
      setVal("mcp-endpoint", dto.agent_mcp.endpoint);
      setVal(
        "mcp-allowlist",
        (dto.agent_mcp.approved_tools || []).join(", ")
      );
      // Never fill secret from projection — only has_secret flag.
      const secretEl = document.getElementById("mcp-secret");
      if (secretEl) secretEl.value = "";
      const hint = document.getElementById("mcp-secret-hint");
      if (hint) {
        hint.textContent = dto.agent_mcp.has_secret
          ? "已設定 secret（投影只含 has_secret=true，不回傳值）。勿用 :8788／:8787。"
          : "投影只顯示 has_secret，不回傳 token 值。勿使用 :8788／:8787。";
      }
    }
    const mode =
      dto.run_mode === "live" || dto.agent_active ? "live" : "dry-run";
    updateModeBadge(mode === "live");
  }

  async function cmdPersistBoardPathIfChanged() {
    if (!invoke) return;
    const boardPath = readBoardPath();
    const projectRoot = readProjectRoot();
    if (isForbiddenDemoRoot(projectRoot)) {
      setSettingsStatus("禁止硬編碼 /demo/root 作為 project_root。", true);
      toast("拒絕：/demo/root");
      throw new Error("forbidden demo project_root");
    }
    if (!isBoardPathAcceptable(boardPath)) {
      setSettingsStatus("看板路徑不可為 http／:8788／:8787。", true);
      toast("拒絕：無效看板路徑");
      throw new Error("invalid board_path");
    }
    try {
      const cur = await invoke("host_get_settings");
      const sameBoard = (cur.board_path || "") === boardPath;
      const sameRoot = (cur.project_root || "") === projectRoot;
      if (sameBoard && sameRoot) return;
      const prevRoot = (cur.project_root || "").trim();
      const nextRoot = (projectRoot || "").trim();
      const rootChanging =
        prevRoot.replace(/\\/g, "/").toLowerCase() !==
        nextRoot.replace(/\\/g, "/").toLowerCase();
      if (rootChanging && (sceneDirty || prevRoot)) {
        const leave = await confirmLeaveSceneIfDirty();
        if (leave === "abort") {
          setSettingsStatus("已取消專案根切換（場景未決）", true);
          toast("已取消切換專案");
          throw new Error("scene dirty — project switch aborted");
        }
      }
      const dto = await invoke("host_set_settings", {
        uiTheme: cur.ui_theme || "system",
        locale: cur.locale || "en",
        boardPath: boardPath,
        projectRoot: projectRoot,
      });
      applyProjectBindingFromDto(dto);
      // PD-WIRE-BOOT-01: settings bind／path change → auto board＋git＋scene
      if ((projectRoot || "").trim()) {
        await onProjectBound(projectRoot.trim());
      } else {
        await wireBootLoadProjections({ reason: "bind", quiet: true });
      }
    } catch (err) {
      setSettingsStatus("專案根／看板路徑儲存失敗：" + String(err), true);
      throw err;
    }
  }

  async function cmdLoadSettings() {
    if (!invoke) {
      updateModeBadge(false);
      setSettingsStatus(
        "瀏覽器模式：可編輯表單；真持久化需 Tauri host_get_settings／host_set_agent_settings。",
        false
      );
      return;
    }
    try {
      const dto = await invoke("host_get_settings");
      applySettingsDto(dto);
      setSettingsStatus(
        "已載入 host settings（模式=" +
          (dto.agent_active ? "Live" : "DryRun") +
          "）。",
        false
      );
    } catch (err) {
      setSettingsStatus("host_get_settings 失敗：" + String(err), true);
    }
  }

  async function cmdSaveAgentSettings(activate) {
    // Live radio + activate button both intend agent_active; DryRun／draft revoke live.
    const wantLive = activate || selectedRunMode() === "live";
    const doActivate = !!activate && wantLive;
    const args = readAgentFormArgs(doActivate);
    if (doActivate) {
      const pathKey =
        args.selected === "cursor-agent"
          ? "cursor_agent_path"
          : args.selected === "codex"
            ? "codex_path"
            : args.selected === "antigravity"
              ? "antigravity_path"
              : "claude_path";
      if (!(args[pathKey] || "").trim()) {
        setSettingsStatus("無效路徑不可存為作用中（CLI 路徑空白）。", true);
        toast("拒絕：無效 CLI 路徑");
        return;
      }
      if (!isMcpEndpointActivatable(args.endpoint)) {
        setSettingsStatus("無效端點不可存為作用中（空白或 :8788／:8787）。", true);
        toast("拒絕：無效 MCP 端點");
        return;
      }
    }
    if (!isBoardPathAcceptable(readBoardPath())) {
      setSettingsStatus("看板路徑不可為 http／:8788／:8787。", true);
      toast("拒絕：無效看板路徑");
      return;
    }
    if (!invoke) {
      updateModeBadge(doActivate);
      setSettingsStatus(
        doActivate
          ? "瀏覽器 NOT RUN：通過前端檢查；真持久化需 Tauri host_set_agent_settings。"
          : "瀏覽器 NOT RUN：草稿／DryRun 未真寫入（無 IPC）。",
        false
      );
      toast(
        doActivate
          ? "存為作用中（NOT RUN — 無 IPC）"
          : "草稿／DryRun（NOT RUN — 無 IPC）"
      );
      return;
    }
    try {
      await cmdPersistBoardPathIfChanged();
      const dto = await invoke("host_set_agent_settings", { args: args });
      applySettingsDto(dto);
      setSettingsStatus(
        doActivate
          ? "已存為作用中（Live · host settings）。"
          : "已持久化並維持／切回 DryRun（agent_active=false）。",
        false
      );
      toast(doActivate ? "Live 已核准" : "DryRun／草稿已儲存");
      setStatus("host_set_agent_settings ok");
    } catch (err) {
      setSettingsStatus("儲存失敗：" + String(err), true);
      toast("設定儲存失敗");
    }
  }

  async function cmdRevokeLive() {
    setRunModeRadios("dry-run");
    await cmdSaveAgentSettings(false);
  }

  function cmdProjectSettings() {
    const args = readAgentFormArgs(false);
    const proj = {
      run_mode: selectedRunMode(),
      project_root: readProjectRoot() || cachedProjectRoot || "",
      board_path: readBoardPath(),
      cli: {
        selected: args.selected,
        claude_path: args.claude_path,
        cursor_agent_path: args.cursor_agent_path,
        codex_path: args.codex_path,
        antigravity_path: args.antigravity_path,
      },
      mcp: {
        transport: args.transport,
        server_name: args.server_name,
        endpoint: args.endpoint,
        approved_tools: args.approved_tools,
        has_secret: !!(args.secret_token && args.secret_token.length),
      },
    };
    const text = JSON.stringify(proj);
    if (text.indexOf("secret_token") !== -1 || text.indexOf('"secret"') !== -1) {
      setSettingsStatus("投影錯誤：不得含 secret／secret_token。", true);
      return;
    }
    setSettingsStatus("投影（無 secret）：" + text.slice(0, 220), false);
    toast("投影已產生（無 secret）");
  }

  function runCommand(cmd, panelHint) {
    try {
      if (panelHint) {
        showPanel(panelHint);
      }
      if (cmd === "file.quit") {
        cmdFileQuit();
        return;
      }
      if (cmd === "file.save") {
        cmdFileSave();
        return;
      }
      if (cmd === "scene.save") {
        downloadSceneSgb();
        return;
      }
      if (cmd === "scene.open") {
        openSceneSgbPicker();
        return;
      }
      if (cmd === "scene.saveXml") {
        downloadSceneSgs();
        return;
      }
      if (cmd === "scene.openXml") {
        openSceneSgsPicker();
        return;
      }
      if (cmd === "file.new") {
        cmdNewProject();
        return;
      }
      if (cmd === "file.open" || cmd === "project.switch") {
        cmdOpenProject();
        return;
      }
      if (cmd === "win.reset") {
        cmdWinReset();
        return;
      }
      if (cmd === "win.inspector" && inspector) {
        const bodyEl = document.getElementById("shell-body");
        const hidden = inspector.style.display === "none";
        inspector.style.display = hidden ? "" : "none";
        if (bodyEl) {
          bodyEl.classList.toggle("is-inspector-collapsed", !hidden);
        }
        const appEl = document.getElementById("app");
        if (appEl) appEl.setAttribute("data-chrome-layout", "custom");
        toast(hidden ? "顯示 Inspector" : "隱藏 Inspector");
        setStatus(hidden ? "Inspector：顯示" : "Inspector：隱藏");
        return;
      }
      if (cmd === "work.new") {
        cmdUpsertTask();
        return;
      }
      if (cmd === "board.load") {
        if (!panelHint) showPanel("board", { quiet: true });
        cmdLoadLocalBoard();
        return;
      }
      if (cmd === "work.assign") {
        if (!panelHint) showPanel("agent");
        cmdStartDryRun();
        return;
      }
      if (cmd === "work.tags") {
        if (!panelHint) showPanel("board", { quiet: true });
        cmdBatchWorkTags();
        return;
      }
      if (cmd === "agent.cancel") {
        cmdCancelRun();
        return;
      }
      if (cmd === "settings.activate") {
        setRunModeRadios("live");
        cmdSaveAgentSettings(true);
        return;
      }
      if (cmd === "settings.draft") {
        setRunModeRadios("dry-run");
        cmdSaveAgentSettings(false);
        return;
      }
      if (cmd === "settings.revoke") {
        cmdRevokeLive();
        return;
      }
      if (cmd === "settings.project") {
        cmdProjectSettings();
        return;
      }
      if (cmd === "git.refresh" || cmd === "project.rescan") {
        const onGit = document.querySelector('.panel.active[data-panel="git"]');
        if (!onGit) {
          showPanel("git", { quiet: true });
        } else {
          cmdGitRefresh();
        }
        return;
      }
      if (cmd === "git.commit") {
        showPanel("git", { quiet: true });
        showGitApprove("commit");
        return;
      }
      if (cmd === "git.push") {
        showPanel("git", { quiet: true });
        showGitApprove("push");
        return;
      }
      if (cmd === "deploy.check") {
        const onDeploy = document.querySelector(
          '.panel.active[data-panel="deploy"]'
        );
        if (!onDeploy) {
          // showPanel triggers refresh; still run check via command path
          showPanel("deploy", { quiet: true });
        }
        cmdDeployCheck();
        return;
      }
      if (cmd === "deploy.refresh") {
        const onDeploy = document.querySelector(
          '.panel.active[data-panel="deploy"]'
        );
        if (!onDeploy) {
          showPanel("deploy", { quiet: true });
        } else {
          cmdDeployRefresh();
        }
        return;
      }
      if (cmd === "ports.refresh" || cmd === "nav.ports") {
        const onPorts = document.querySelector(
          '.panel.active[data-panel="ports"]'
        );
        if (!onPorts) {
          showPanel("ports", { quiet: true });
        } else {
          cmdPortsRefresh();
        }
        return;
      }
      if (cmd === "win.uiEditor") {
        openUiDesignWindow("designer");
        return;
      }
      if (cmd === "win.uiViewer") {
        openUiDesignWindow("viewer");
        return;
      }
      if (cmd === "uidesign.refresh") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("viewer");
        else setUidesignMode("viewer");
        cmdUidesignRefresh();
        return;
      }
      if (cmd === "uidesign.embed") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("viewer");
        else setUidesignMode("viewer");
        cmdUidesignEmbed();
        return;
      }
      if (cmd === "uidesign.open") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("viewer");
        else setUidesignMode("viewer");
        cmdUidesignOpen();
        return;
      }
      if (cmd === "uidesign.save") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        cmdUidesignSave();
        return;
      }
      if (cmd === "uidesign.load") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        cmdUidesignLoad();
        return;
      }
      if (cmd === "uidesign.build") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        cmdUidesignBuild();
        return;
      }
      if (cmd === "uidesign.ask") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        cmdUidesignAsk();
        return;
      }
      if (cmd === "uidesign.delete") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        deleteSelectedDesignNode();
        return;
      }
      if (cmd === "uidesign.dup") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        duplicateSelectedDesignNode();
        return;
      }
      if (cmd === "uidesign.raise") {
        setUidesignMode("designer");
        bumpDesignZ(1);
        return;
      }
      if (cmd === "uidesign.lower") {
        setUidesignMode("designer");
        bumpDesignZ(-1);
        return;
      }
      if (cmd.indexOf("uidesign.align.") === 0) {
        const align = cmd.slice("uidesign.align.".length) || "left";
        setUidesignMode("designer");
        alignSelectedDesign(align);
        return;
      }
      if (cmd === "spec.load") {
        const onSpec = document.querySelector(
          '.panel.active[data-panel="spec"]'
        );
        if (!onSpec) showPanel("spec", { quiet: true });
        cmdSpecLoad();
        return;
      }
      if (cmd === "spec.refresh") {
        const onSpec = document.querySelector(
          '.panel.active[data-panel="spec"]'
        );
        if (!onSpec) showPanel("spec", { quiet: true });
        else cmdSpecRefresh();
        return;
      }
      if (cmd === "spec.approve") {
        cmdSpecApprove();
        return;
      }
      if (cmd === "spec.tryEdit") {
        cmdSpecTryEdit();
        return;
      }
      if (cmd === "spec.revise") {
        cmdSpecRevise();
        return;
      }
      if (cmd === "report.openEmpty") {
        const onReport = document.querySelector(
          '.panel.active[data-panel="report"]'
        );
        if (!onReport) showPanel("report", { quiet: true });
        cmdProjectReport("not_run");
        return;
      }
      if (cmd === "report.openHappy") {
        const onReport = document.querySelector(
          '.panel.active[data-panel="report"]'
        );
        if (!onReport) showPanel("report", { quiet: true });
        cmdProjectReport("happy");
        return;
      }
      if (cmd === "arch.refresh") {
        const onArch = document.querySelector(
          '.panel.active[data-panel="arch"]'
        );
        if (!onArch) showPanel("arch", { quiet: true });
        else cmdArchRefresh();
        return;
      }
      if (cmd === "listen.refresh" || cmd === "nav.listen") {
        const onListen = document.querySelector(
          '.panel.active[data-panel="listen"]'
        );
        if (!onListen) showPanel("listen", { quiet: true });
        else cmdListenRefresh();
        return;
      }
      /* PD-REMAIN-EDIT-01: no domain Command for history／selection — all four NOT RUN. */
      if (
        cmd === "edit.undo" ||
        cmd === "edit.redo" ||
        cmd === "edit.selectAll" ||
        cmd === "edit.clear"
      ) {
        const label = CMD_LABELS[cmd] || cmd;
        toast(label);
        setStatus(label);
        return;
      }
      const label = CMD_LABELS[cmd] || cmd;
      toast(label);
      setStatus(label);
    } catch (err) {
      toast("命令已攔截錯誤：" + String(err));
      setStatus("命令錯誤已攔截 — 不崩潰");
    }
  }

  document.querySelectorAll(".menu-wrap").forEach(function (wrap) {
    const btn = wrap.querySelector(".menu-btn");
    if (!btn) return;
    btn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      toggleMenu(wrap);
    });
  });

  document.addEventListener("click", function () {
    closeMenus();
  });

  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape") {
      closeMenus();
      if (pendingGitWrite) cancelGitApprove();
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "o" || ev.key === "O")) {
      ev.preventDefault();
      closeMenus();
      runCommand("file.open");
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "n" || ev.key === "N")) {
      ev.preventDefault();
      closeMenus();
      runCommand("file.new");
    }
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "s" || ev.key === "S")) {
      ev.preventDefault();
      closeMenus();
      runCommand("file.save");
    }
  });

  const gitCommitBtn = document.getElementById("git-commit");
  const gitPushBtn = document.getElementById("git-push");
  if (gitCommitBtn) {
    gitCommitBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      showGitApprove("commit");
    });
  }
  if (gitPushBtn) {
    gitPushBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      showGitApprove("push");
    });
  }
  const gitApproveConfirm = document.getElementById("git-approve-confirm");
  const gitApproveCancel = document.getElementById("git-approve-cancel");
  if (gitApproveConfirm) {
    gitApproveConfirm.addEventListener("click", function (ev) {
      ev.stopPropagation();
      confirmGitApprove();
    });
  }
  if (gitApproveCancel) {
    gitApproveCancel.addEventListener("click", function (ev) {
      ev.stopPropagation();
      cancelGitApprove();
    });
  }

  document.querySelectorAll("[data-cmd]").forEach(function (el) {
    el.addEventListener("click", function (ev) {
      ev.stopPropagation();
      const cmd = el.getAttribute("data-cmd");
      const panel = el.getAttribute("data-panel");
      closeMenus();
      if (cmd) runCommand(cmd, panel || null);
    });
  });

  // Empty-state / cross-panel buttons that only carry data-panel (no data-cmd)
  document.querySelectorAll("[data-empty-action][data-panel]").forEach(function (el) {
    if (el.getAttribute("data-cmd")) return;
    el.addEventListener("click", function (ev) {
      ev.stopPropagation();
      const panel = el.getAttribute("data-panel");
      if (panel) showPanel(panel);
    });
  });

  document.querySelectorAll(".nav-item[data-panel]").forEach(function (btn) {
    btn.addEventListener("click", function (ev) {
      const panel = btn.dataset.panel;
      if (!panel) return;
      /* 直書主分頁：再點一次收合抽屜（DVE／VS Code 行為） */
      if (
        btn.classList.contains("side-tab") &&
        btn.getAttribute("data-side-tab") &&
        btn.getAttribute("aria-selected") === "true" &&
        isSideDrawerOpen() &&
        !document.getElementById("sidebar")?.classList.contains("is-more-open")
      ) {
        ev.stopPropagation();
        setSideDrawerOpen(false);
        return;
      }
      showPanel(panel);
    });
  });

  document.querySelectorAll(".status-item[data-filter]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      const filter = btn.getAttribute("data-filter") || "overview";
      setBoardFilter(filter);
      toast("篩選：「" + (FILTER_TITLES[filter] || filter) + "」");
    });
  });

  const clearStatusBtn = document.getElementById("btn-clear-status-filter");
  if (clearStatusBtn) {
    clearStatusBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      clearStatusFilter();
    });
  }

  const sideMoreToggle = document.getElementById("side-more-toggle");
  if (sideMoreToggle) {
    sideMoreToggle.addEventListener("click", function (ev) {
      ev.stopPropagation();
      const side = document.getElementById("sidebar");
      const open = side && side.classList.contains("is-more-open");
      if (open && isSideDrawerOpen()) {
        setSideMoreOpen(false);
        setSideDrawerOpen(false);
        return;
      }
      setSideMoreOpen(true);
    });
  }
  document.getElementById("side-more-menu")?.addEventListener("click", function (ev) {
    ev.stopPropagation();
  });

  document
    .getElementById("uidesign-window-close")
    ?.addEventListener("click", function () {
      closeUiDesignWindow();
    });
  (function wireUiDesignWindowDrag() {
    const chrome = document.getElementById("uidesign-window-chrome");
    const win = document.getElementById("uidesign-window");
    if (!chrome || !win) return;
    let drag = null;
    chrome.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 0) return;
      if (ev.target.closest(".uidesign-window-close")) return;
      const r = win.getBoundingClientRect();
      drag = {
        ox: ev.clientX - r.left,
        oy: ev.clientY - r.top,
      };
      try {
        chrome.setPointerCapture(ev.pointerId);
      } catch (_e) {
        /* ignore */
      }
      ev.preventDefault();
    });
    chrome.addEventListener("pointermove", function (ev) {
      if (!drag) return;
      win.style.left = Math.max(0, ev.clientX - drag.ox) + "px";
      win.style.top = Math.max(0, ev.clientY - drag.oy) + "px";
      win.style.right = "auto";
      win.style.transform = "none";
    });
    chrome.addEventListener("pointerup", function () {
      drag = null;
    });
  })();

  // btn-board-retry uses data-cmd="board.load" (handled by runCommand)

  if (ipcStatus) {
    ipcStatus.textContent = hasIpc
      ? "Tauri IPC 就緒（invoke）"
      : "瀏覽器模式 — 無 invoke；請 npm run tauri dev";
  }

  // Prefill board path + project_root from host settings (PD-WIRE-ROOT-01)
  async function prefBoardPath() {
    const el = document.getElementById("board-path-input");
    if (!el || !invoke) {
      if (el && !el.value) el.value = "docs/PROJECT-BOARD.html";
      updateToolbarBinding("");
      return null;
    }
    try {
      const dto = await refreshProjectBinding();
      if (dto && dto.board_path) {
        el.value = dto.board_path;
      } else if (!el.value) {
        el.value = "docs/PROJECT-BOARD.html";
      }
      return dto;
    } catch (_e) {
      if (!el.value) el.value = "docs/PROJECT-BOARD.html";
      updateToolbarBinding("");
      return null;
    }
  }

  const SHELL_LAYOUT_LS = "sgenaxis.shell.layout.v1";
  const SHELL_SIDEBAR_MIN = 160;
  const SHELL_SIDEBAR_MAX = 480;
  const SHELL_INSPECTOR_MIN = 220;
  const SHELL_INSPECTOR_MAX = 640;

  function clampShellPx(n, min, max) {
    n = Math.round(Number(n) || 0);
    if (n < min) return min;
    if (n > max) return max;
    return n;
  }

  function applyShellColumnWidths(sidebarPx, inspectorPx) {
    const root = document.documentElement;
    if (sidebarPx != null) {
      root.style.setProperty(
        "--sidebar-w",
        clampShellPx(sidebarPx, SHELL_SIDEBAR_MIN, SHELL_SIDEBAR_MAX) + "px"
      );
    }
    if (inspectorPx != null) {
      root.style.setProperty(
        "--inspector-w",
        clampShellPx(inspectorPx, SHELL_INSPECTOR_MIN, SHELL_INSPECTOR_MAX) +
          "px"
      );
    }
  }

  function persistShellLayout() {
    try {
      const cs = getComputedStyle(document.documentElement);
      localStorage.setItem(
        SHELL_LAYOUT_LS,
        JSON.stringify({
          sidebar: parseInt(cs.getPropertyValue("--sidebar-w"), 10) || 240,
          inspector: parseInt(cs.getPropertyValue("--inspector-w"), 10) || 390,
        })
      );
    } catch (_e) {
      /* ignore */
    }
  }

  function loadShellLayout() {
    try {
      const raw = localStorage.getItem(SHELL_LAYOUT_LS);
      if (!raw) return;
      const o = JSON.parse(raw);
      if (o && (o.sidebar || o.inspector)) {
        applyShellColumnWidths(o.sidebar, o.inspector);
      }
    } catch (_e) {
      /* ignore */
    }
  }

  function wireShellSplitters() {
    loadShellLayout();
    const grips = [
      {
        el: document.getElementById("split-sidebar"),
        kind: "sidebar",
      },
      {
        el: document.getElementById("split-inspector"),
        kind: "inspector",
      },
    ];
    grips.forEach(function (g) {
      if (!g.el) return;
      g.el.addEventListener("pointerdown", function (ev) {
        if (ev.button !== 0) return;
        ev.preventDefault();
        const cs = getComputedStyle(document.documentElement);
        const startX = ev.clientX;
        const startSide =
          parseInt(cs.getPropertyValue("--sidebar-w"), 10) || 240;
        const startInsp =
          parseInt(cs.getPropertyValue("--inspector-w"), 10) || 390;
        g.el.classList.add("is-dragging");
        document.body.classList.add("is-shell-resizing");
        try {
          g.el.setPointerCapture(ev.pointerId);
        } catch (_e) {
          /* ignore */
        }
        function onMove(e) {
          const dx = e.clientX - startX;
          if (g.kind === "sidebar") {
            applyShellColumnWidths(startSide + dx, null);
          } else {
            applyShellColumnWidths(null, startInsp - dx);
          }
        }
        function onUp() {
          g.el.classList.remove("is-dragging");
          document.body.classList.remove("is-shell-resizing");
          document.removeEventListener("pointermove", onMove);
          document.removeEventListener("pointerup", onUp);
          persistShellLayout();
        }
        document.addEventListener("pointermove", onMove);
        document.addEventListener("pointerup", onUp);
      });
      g.el.addEventListener("keydown", function (ev) {
        const step = ev.shiftKey ? 24 : 8;
        const cs = getComputedStyle(document.documentElement);
        const side = parseInt(cs.getPropertyValue("--sidebar-w"), 10) || 240;
        const insp = parseInt(cs.getPropertyValue("--inspector-w"), 10) || 390;
        if (ev.key === "ArrowLeft") {
          ev.preventDefault();
          if (g.kind === "sidebar") applyShellColumnWidths(side - step, null);
          else applyShellColumnWidths(null, insp + step);
          persistShellLayout();
        }
        if (ev.key === "ArrowRight") {
          ev.preventDefault();
          if (g.kind === "sidebar") applyShellColumnWidths(side + step, null);
          else applyShellColumnWidths(null, insp - step);
          persistShellLayout();
        }
      });
    });
  }

  try {
    applyUiDesignStandaloneShell();
  } catch (_standaloneShell) {
    /* ignore */
  }

  // PD-UIDESIGNER: wire Designer shell (palette／props／mode).
  try {
    wireDesignerUi();
  } catch (_wireUi) {
    /* panel may be absent in stripped shells */
  }

  if (UIDESIGN_STANDALONE) {
    try {
      openUiDesignWindowEmbedded(UIDESIGN_STANDALONE.mode, {
        path: UIDESIGN_STANDALONE.path,
        quiet: true,
      });
      setStatus(
        UIDESIGN_STANDALONE.mode === "viewer"
          ? "UI 預覽（獨立 OS 視窗 · 可拖出主視窗）"
          : "UI 編輯（獨立 OS 視窗 · 可拖出主視窗）"
      );
    } catch (_standaloneOpen) {
      /* ignore */
    }
  }

  try {
    wireShellSplitters();
  } catch (_split) {
    /* shell may be stripped */
  }

  // Arch DAG shell（草稿常駐；live 僅 Command）
  try {
    wireArchUi();
  } catch (_wireArch) {
    /* panel may be absent */
  }

  try {
    wireSceneSgbUi();
    wireSceneSgsUi();
  } catch (_sgb) {
    /* scene pack UI optional */
  }

  // PD-WIRE-BOOT-01: 啟動且已有設定 → auto load_local_board＋git_workbench_summary
  try {
    renderBoard(null);
    renderGitNotRun("啟動中…");
    if (hasIpc) {
      setStatus("就緒 — Tauri command 模式（含 PD-WIRE-BOOT-01）");
      setAgentStatus("Agent：就緒");
      prefBoardPath().then(function (dto) {
        const root = dto && (dto.project_root || "").trim();
        const boardPath = dto && (dto.board_path || "").trim();
        const hasSettings =
          (!!root && !isForbiddenDemoRoot(root)) || !!boardPath;
        if (!hasSettings) {
          const msg = unboundProjectMessage();
          showBoardError(msg);
          setBoardLiveStatus(msg, true);
          renderGitNotRun(msg + " — Git NOT RUN");
          setStatus("就緒 — 等待綁定；綁定後自動 load_local_board＋git_workbench_summary");
          return null;
        }
        return wireBootLoadProjections({ reason: "boot", quiet: true });
      });
    } else {
      setStatus("就緒 — 瀏覽器導覽／空態（無 IPC）");
      updateToolbarBinding("");
      renderGitNotRun("瀏覽器模式：無 IPC → Git NOT RUN");
      const el = document.getElementById("board-path-input");
      if (el && !el.value) el.value = "docs/PROJECT-BOARD.html";
    }
  } catch (err) {
    setStatus("初始化已攔截：" + String(err));
    try {
      renderGitNotRun("初始化失敗 → NOT RUN：" + String(err));
    } catch (_e) {
      /* never crash boot */
    }
  }
})();
