/**
 * SGenAxis UI — PD-UI-01 shell + PD-CMD-01 + PD-UI-NAV-01 + PD-UI-RUN-01 + PD-GIT-UI-01 + PD-BOARD-LIVE-01 + PD-DEPLOY-UI-01 + PD-SET-UI-01 + PD-SPEC-UI-01 + PD-REPORT-UI-01 + PD-WIRE-DESTUB-01 + PD-REMAIN-WIN-RESET-01.
 * Menu／派工 → invoke Tauri commands only (no OS／CLI／MCP／git／deploy／spec authority from the page).
 * Browser fallback: toast／local chrome only; projection empty until Tauri.
 * Nav：頂部分頁 Diagram／Tasks／Git／Setting；Agent／佈版／監聽／報告在 Tasks 抽屜。
 * Run panel (PD-UI-RUN-01): start_run／poll_chunks／cancel_run — chunk 串流、取消、結束分類 ok｜cancelled｜failed.
 * Git workbench: read-only status／diff／branch via git_workbench_*；writes gated.
 * Board live: load_local_board reads local #board-snapshot (no :8788／write-back).
 * PD-WIRE-ROOT-01: start_run／git_workbench_*／load_local_board share settings.project_root／board_path；never /demo/root；no ProcessPort from JS.
 * PD-WIRE-BOOT-01: bind／啟動且已有設定 → 僅 invoke load_local_board＋git_workbench_summary；空／缺檔／非 git → NOT RUN；禁 JS 直讀檔／git.
 * Deploy panel: deploy_status／deploy_check／list_artifacts；unsupported when Adapter／CMD absent.
 * Settings: CLI／MCP／DryRun｜Live via host_get_settings／host_set_agent_settings；secrets never projected.
 * PD-WIRE-AGENT-01: Agent 派工 → start_run（選中 work_item_id＋settings provider／dry_run）；Live 未核准／路徑無效→可讀拒；不直呼 adapters.
 * Report panel: project_pd_report → tools/pd_report；空 evid→NOT RUN；不回寫規格。
 * PD-REMAIN-FILE-SAVE-01: file.save → file_save（Command）持久化 host settings／看板路徑；禁任意路徑／看板寫回；瀏覽器 NOT RUN.
 * PD-REMAIN-FILE-QUIT-01: file.quit → host_request_shutdown（Command）；瀏覽器模式 NOT RUN（無法關閉殼）.
 * PD-REMAIN-EDIT-01 path C: edit.undo／redo／selectAll／clear →
 * invoke edit_* → DispatchHost → Core EditSession（選取／歷史；宇宙＝看板工項 id）。
 * PD-REMAIN-ARCH-UI-01: arch.refresh → arch_get_projection；空／無 IPC → NOT RUN；禁靜態假圖冒充 live.
 * PD-SHELL-UIDESIGN-VIEW-01: Viewer → uidesign_package_status／open；設計稿≠產品證據／禁正式驗收 PASS.
 * PD-UIDESIGNER-*: Designer 三欄 + .sgendesign save/load + build preview + ask agent；設計≠產品 PASS.
 */
(function () {
  "use strict";

  // DOC-UI-02 controller begin
  function createDocumentIdentityController(options) {
    let context = null, reference = "", busy = false, generation = 0;
    let status = "請先準備目前專案，再選擇要登記的文件。";
    const root = () => String(options.getRoot() || "");
    const validReference = () => {
      const p = reference.replace(/\\/g, "/");
      return !!p && !p.startsWith("/") && !p.includes(":") && !p.includes("\0") &&
        !p.split("/").some(x => x === ".." || x === "." || x === "") && /\.(ess|sgendesign)$/i.test(p);
    };
    const executionBusy = () => !!(options.getBusy && options.getBusy());
    const view = () => ({ root: root(), context: context ? { ...context } : null, reference, busy: busy || executionBusy(),
      status: !options.invoke ? "請在桌面產品中開啟專案後操作。" : !root() ? "尚未綁定專案，請先從檔案選單開啟專案目錄。" : executionBusy() ? "目前有工作執行中，文件身分操作暫停；請待工作結束後再準備。" : status,
      canPrepare: !!options.invoke && !!root() && !busy && !executionBusy(),
      canAdopt: !!options.invoke && !!context && context.project_root === root() && validReference() && !busy && !executionBusy() });
    const emit = () => options.render(view());
    const errorText = e => e && e.code ? e.code + (e.detail ? ": " + (typeof e.detail === "string" ? e.detail : e.detail.reason || "") : "") : String(e);
    const invalidate = () => { generation++; context = null; status = "專案或對話框已變更，請重新準備。"; emit(); };
    const setReference = value => { if (!busy) { reference = String(value || "").trim(); emit(); } };
    async function prepare() {
      if (!view().canPrepare) return;
      const expected = root(), token = ++generation;
      context = null; busy = true; status = "正在準備目前專案…"; emit();
      try {
        const result = await options.invoke("project_document_prepare", { args: { expected_project_root: expected } });
        if (token !== generation || expected !== root()) return;
        if (!result || result.project_root !== expected || typeof result.project_id !== "string" || !result.project_id) {
          throw new Error("準備結果與目前專案不符");
        }
        context = { project_id: result.project_id, project_root: result.project_root };
        status = "專案已準備，請選擇專案內文件。";
      } catch (e) {
        if (token === generation && expected === root()) status = "準備失敗：" + errorText(e);
      } finally { busy = false; emit(); }
    }
    async function adopt() {
      if (!view().canAdopt) return;
      const expected = root(), token = generation, selectedReference = reference, projectId = context.project_id;
      busy = true; status = "正在登記文件身分…"; emit();
      try {
        const result = await options.invoke("project_document_adopt", { args: { expected_project_id: projectId, reference: selectedReference } });
        if (token !== generation || expected !== root()) return;
        if (!result || !["Adopted", "AlreadyAdopted"].includes(result.outcome) || !result.document_id) throw new Error("登記結果無效");
        status = result.outcome + " · " + result.document_id + " · " + (result.revision_id || "");
      } catch (e) {
        if (token === generation && expected === root()) status = "登記失敗：" + errorText(e);
      } finally { busy = false; emit(); }
    }
    return { view, prepare, adopt, invalidate, setReference };
  }
  // DOC-UI-02 controller end

  const PANEL_TITLES = {
    board: "工項看板",
    agent: "Agent 派工",
    deploy: "佈版",
    arch: "模組架構圖",
    uidesign: "UI Editor／Viewer",
    listen: "監聽投影",
    git: "Git 工作台",
    report: "模組／系統報告",
    settings: "設定",
  };

  /** Zone filters（灰／黃／橙待核准／紅／綠）；overview／accepted 另計。 */
  const ZONE_FILTERS = ["gray", "yellow", "orange", "red", "green"];

  /** Startup splash — 第二張素材 icons/brand/splash.png；最短顯示後淡出 */
  const SPLASH_MIN_MS = 900;
  const SPLASH_MAX_MS = 5000;
  const splashStartedAt = Date.now();
  let splashDismissed = false;

  function dismissAppSplash(opts) {
    if (splashDismissed) return;
    splashDismissed = true;
    const el = document.getElementById("app-splash");
    if (!el) return;
    const caption = document.getElementById("app-splash-caption");
    if (caption && opts && opts.caption) caption.textContent = opts.caption;
    el.classList.add("is-finishing");
    el.setAttribute("aria-busy", "false");
    const wait = Math.max(0, SPLASH_MIN_MS - (Date.now() - splashStartedAt));
    window.setTimeout(function () {
      el.classList.add("is-done");
      window.setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 320);
    }, wait + 140);
  }

  window.setTimeout(function () {
    dismissAppSplash({ caption: "Ready" });
  }, SPLASH_MAX_MS);

  const FILTER_TITLES = {
    overview: "總覽",
    gray: "待辦",
    yellow: "進行中",
    orange: "待核准",
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
    "scene.save": "儲存場景套件到目前專案 scene/（default.es＋.esml＋.esui）",
    "scene.open": "自目前專案 scene/ 載入場景套件",
    "scene.saveXml": "儲存場景 XML 到目前專案 scene/default.ess",
    "scene.openXml": "自目前專案 scene/default.ess 載入",
    "edit.undo": "復原選取（edit_undo → Core EditSession）",
    "edit.redo": "重做選取（edit_redo → Core EditSession）",
    "edit.selectAll": "全選變更（edit_select_all → 看板工項宇宙）",
    "edit.clear": "清除選取（edit_clear → Core EditSession）",
    "project.switch": "切換專案（場景有異動會先詢問是否存檔）",
    "project.rescan": "重新掃描儲存庫（Git 唯讀投影）",
    "git.refresh": "重新整理 Git 投影",
    "git.commit": "審核式 Commit",
    "git.push": "審核式 Push",
    "nav.git": "切到 Git 工作台",
    "nav.report": "切到模組／系統報告",
    "nav.arch": "切到模組架構圖",
    "arch.saveXml": "匯出架構圖 XML（.sgenarch.xml）",
    "arch.loadXml": "開啟架構圖 XML",
    "win.uiEditor": "視窗 → UI 編輯（獨立 UI 設計工具視窗）",
    "win.uiViewer": "視窗 → UI 預覽（獨立 Viewer 視窗）",
    "nav.listen": "切到監聽投影",
    "nav.settings": "切到設定",
    "uidesign.refresh": "重新整理設計包狀態（uidesign_package_status）",
    "uidesign.open": "受控開啟本機設計包（uidesign_open_package）",
    "uidesign.embed": "內嵌載入 docs/ui-design/index.html",
    "uidesign.save": "儲存 .sgendesign（uidesign_save_design）",
    "uidesign.load": "開啟 .sgendesign（uidesign_load_design）",
    "uidesign.recovery.clear": "預覽並清空目前 UI 設計文件（工作階段內可復原）",
    "uidesign.recovery.undo": "復原 UI 設計文件清空",
    "uidesign.recovery.redo": "重做 UI 設計文件清空",
    "uidesign.recovery.confirm": "確認清空目前 UI 設計文件",
    "uidesign.recovery.cancel": "取消清空 UI 設計文件",
    "uidesign.build": "Build 溝通預覽 HTML（uidesign_build_preview）",
    "uidesign.ask": "Ask Agent → BDD／工項草稿（uidesign_ask_agent）",
    "listen.refresh": "重新整理監聽投影（listen_get_projection）",
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
    "help.about": "EluSlot 0.1.0 — Tauri 2 + Vanilla UI",
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

  function renderDocumentIdentity(view) {
    const root = document.getElementById("document-identity-root");
    const status = document.getElementById("document-identity-status");
    const prepare = document.getElementById("document-identity-prepare");
    const adopt = document.getElementById("document-identity-adopt");
    const reference = document.getElementById("document-identity-reference");
    if (root) root.textContent = view.root || "尚未開啟專案";
    if (status) status.textContent = hasIpc ? view.status : "請在桌面產品中開啟專案後操作。";
    if (prepare) prepare.disabled = !view.canPrepare;
    if (adopt) adopt.disabled = !view.canAdopt;
    if (reference) reference.disabled = view.busy;
  }
  const documentIdentityController = createDocumentIdentityController({ invoke, getRoot: () => cachedProjectRoot, getBusy: () => activeRunId != null, render: renderDocumentIdentity });
  renderDocumentIdentity(documentIdentityController.view());
  document.getElementById("document-identity-reference")?.addEventListener("input", event => documentIdentityController.setReference(event.target.value));
  document.getElementById("document-identity-prepare")?.addEventListener("click", () => documentIdentityController.prepare());
  document.getElementById("document-identity-adopt")?.addEventListener("click", () => documentIdentityController.adopt());
  document.getElementById("document-identity-dialog")?.addEventListener("close", () => documentIdentityController.invalidate());
  document.getElementById("document-identity-close")?.addEventListener("click", () => {
    const dialog = document.getElementById("document-identity-dialog");
    if (dialog && typeof dialog.close === "function") dialog.close();
    else { dialog?.removeAttribute("open"); documentIdentityController.invalidate(); }
  });
  function openDocumentIdentity() {
    const dialog = document.getElementById("document-identity-dialog");
    const reference = document.getElementById("document-identity-reference");
    documentIdentityController.invalidate();
    if (reference) reference.value = "";
    documentIdentityController.setReference("");
    if (dialog && typeof dialog.showModal === "function") dialog.showModal();
    else dialog?.setAttribute("open", "");
  }

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
  let gitIndexCommitRootSync = null;
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
    if (gitIndexCommitRootSync) gitIndexCommitRootSync(display);
  }

  /**
   * 場景打包 .sgb（bin）：預設專案檔名（EluSlot）
   * - default.es（工項 JSON）
   * - default.esml（架構圖 XML）
   * - default.esui（UI 設計 JSON）
   */
  const SGB_MAGIC = "SGB1";
  const SGB_ENTRY_WORK = "default.es";
  const SGB_ENTRY_ARCH = "default.esml";
  const SGB_ENTRY_DESIGN = "default.esui";
  const SGB_DEFAULT_NAME = "default.sgb";
  /** 專案內場景相對路徑（僅限 scene/；經 scene_save／scene_load）。 */
  const SCENE_SGS_REL = "scene/default.ess";
  const SCENE_SG_REL = "scene/default.es";
  const SCENE_SGML_REL = "scene/default.esml";
  const SCENE_SGUI_REL = "scene/default.esui";
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
        format: "eluslot.es",
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
    copy.format = "eluslot.esui";
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
        : '<?xml version="1.0"?><eluslotArch/>';
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
    if (!doc || (doc.format !== "eluslot.es" && doc.format !== "sgenaxis.sg" && !doc.board)) {
      throw new Error("invalid default.es");
    }
    if (doc.meta && doc.meta.boardFilter) {
      boardFilter = doc.meta.boardFilter;
    }
    renderBoard(doc.board || null);
  }

  function applyDesignSguiJson(text) {
    const doc = JSON.parse(String(text || ""));
    if (!doc || !Array.isArray(doc.nodes)) {
      throw new Error("invalid default.esui");
    }
    /* 內部仍走 DesignDoc；format 可為 eluslot.esui／sgenaxis.sgui／sgenaxis.design */
    designDoc = retainUiExclusiveNodes(doc);
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
      if (!arch) throw new Error("default.esml parse failed");
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
      map[SGB_ENTRY_WORK] ||
      map["default.sg"] ||
      map["work.es"] ||
      map["work.sg"] ||
      map["project.sg"];
    const archText =
      map[SGB_ENTRY_ARCH] ||
      map["default.sgml"] ||
      map["arch.esml"] ||
      map["arch.sgml"] ||
      map["architecture.sgml"];
    const designText =
      map[SGB_ENTRY_DESIGN] ||
      map["default.sgui"] ||
      map["design.esui"] ||
      map["design.sgui"] ||
      map["ui.sgui"];
    if (!workText || !archText || !designText) {
      throw new Error(
        "SGB missing default.es／default.esml／default.esui"
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
        : '<?xml version="1.0"?><eluslotArch/>';
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
   * 場景 XML .ess：專案內場景單一 XML（對照 .es＋.esml＋.esui 套件）
   * - work（工項／board）
   * - architecture（eluslotArch）
   * - design（UI 設計節點）
   */
  const SGS_DEFAULT_NAME = "default.ess";
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
        : "<eluslotArch/>"
    );
    let xml = '<?xml version="1.0" encoding="UTF-8"?>\n';
    xml +=
      '<eluslotScene format="eluslot.ess" formatVersion="1" encoding="xml">\n';
    xml +=
      "  <meta" +
      archAttr("savedAt", new Date().toISOString()) +
      archAttr("boardFilter", boardFilter || "overview") +
      archAttr("product_pass", "false") +
      archAttr("sgbCompat", "default.es+default.esml+default.esui") +
      " />\n";
    xml += '  <work format="eluslot.es" encoding="xml">\n';
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
    xml += '  <design format="eluslot.esui" encoding="xml">\n';
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
    xml += "</eluslotScene>\n";
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
      format: "eluslot.esui",
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
      if (node.id && isUiExclusiveNodeType(node.type)) {
        node.scope = "ui";
        node.uiExclusive = true;
        doc.nodes.push(node);
      }
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
      docXml.querySelector("eluslotScene") ||
      docXml.querySelector("sgenaxisScene") ||
      docXml.documentElement;
    const rootTag = String(root && root.tagName ? root.tagName : "").toLowerCase();
    if (!root || (rootTag !== "eluslotscene" && rootTag !== "sgenaxisscene")) {
      return null;
    }
    const metaEl = root.querySelector(":scope > meta");
    const workEl = root.querySelector(":scope > work");
    const archWrap = root.querySelector(":scope > architecture");
    const designEl = root.querySelector(":scope > design");
    const archRoot =
      (archWrap &&
        (archWrap.querySelector("eluslotArch") ||
          archWrap.querySelector("sgenaxisArch"))) ||
      root.querySelector("eluslotArch") ||
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
    if (!scene) throw new Error("invalid .ess（需 eluslotScene XML）");
    withSceneDirtySuppressed(function () {
      if (scene.meta && scene.meta.boardFilter) {
        boardFilter = scene.meta.boardFilter;
      }
      renderBoard(scene.board || null);
      applyArchDoc(scene.arch, { quiet: true });
      persistArchDraft();
      designDoc = retainUiExclusiveNodes(scene.design);
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
      toast("已載入專案場景 .ess");
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
      toast("儲存 .ess 失敗：" + String(err));
      setStatus("場景 XML 存檔失敗：" + String(err));
    }
  }

  async function openSceneSgsPicker() {
    try {
      await loadSceneSgsFromProject({ quiet: false });
    } catch (err) {
      toast("開啟專案 .ess 失敗：" + String(err));
      setStatus("場景 XML 載入失敗：" + String(err));
    }
  }

  function wireSceneSgsUi() {
    /* 專案範圍存取：不再使用任意路徑 file picker */
  }

  /** 綁定專案後嘗試載入 scene/default.ess（無檔則試舊 .sgs；皆無則略過）。 */
  async function tryLoadProjectSceneQuiet() {
    if (!invoke || !cachedProjectRoot) return;
    try {
      await loadSceneSgsFromProject({ quiet: true });
      setStatus("已載入專案場景 " + SCENE_SGS_REL);
    } catch (_err) {
      try {
        const dto = await invokeSceneLoadText("scene/default.sgs");
        applySceneSgsXml(dto.text, "scene/default.sgs", { quiet: true });
        setStatus("已載入專案場景 scene/default.sgs（舊副檔名）");
      } catch (_legacy) {
        /* 新專案尚無 scene — 保留目前草稿，不視為錯誤 */
      }
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
      !window.confirm("結束 EluSlot？")
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
      // PD-M01-S3: create through the six-step wizard command bridge
      // (wizard_begin → wizard_apply_step × steps → wizard_prepare_preferences →
      // wizard_commit). The wizard reuses ProjectPreferencesUI.chooseNewProject()
      // for the preference step. Replaces the deprecated
      // host_create_project_with_preferences path (now WIZARD_REQUIRED).
      if (!window.ProjectWizardUI || !window.ProjectWizardUI.run) {
        const msg = "新增專案失敗：專案精靈未載入";
        toast(msg);
        setStatus(msg);
        return;
      }
      setStatus("新增專案：請依精靈填寫六個步驟…");
      const created = await window.ProjectWizardUI.run({
        parent: String(parentPick.path).trim(),
        name: name,
      });
      if (!created) {
        toast("已取消新增專案（精靈）");
        setStatus("新增專案：已取消（精靈）");
        return;
      }
      try {
        await bindPickedProjectRoot(created, "新增專案");
      } catch (bindError) {
        const msg = "專案已建立，但未完成專案綁定：" + String(bindError);
        toast(msg);
        setStatus(msg);
      }
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
    if (window.ProjectPreferencesUI?.hasUnsaved() &&
        !window.confirm("切換專案會捨棄尚未儲存的專案偏好，是否繼續？")) {
      toast(actionLabel === "新增專案" ? "目錄已建立；已取消切換，保留目前專案與偏好草稿。" : "已取消切換專案，保留偏好草稿。");
      return;
    }
    const dto = await invoke("host_set_settings", {
      uiTheme: cur.ui_theme || "system",
      locale: cur.locale || "en",
      boardPath: cur.board_path || null,
      projectRoot: path,
    });
    applyProjectBindingFromDto(dto);
    applySettingsDto(dto);
    if (window.ProjectPreferencesUI) window.ProjectPreferencesUI.refresh();
    toast("已綁定專案：" + path);
    setStatus("host_set_settings project_root ok");
    await onProjectBound(path);
  }

  function applyProjectBindingFromDto(dto) {
    if (!dto) return;
    const previousDocumentRoot = cachedProjectRoot;
    cachedProjectRoot = (dto.project_root || "").trim();
    cachedBoardPath = (dto.board_path || "").trim();
    cachedAgentActive = !!(
      dto.agent_active || dto.run_mode === "live"
    );
    if (isForbiddenDemoRoot(cachedProjectRoot)) {
      cachedProjectRoot = "";
    }
    if (previousDocumentRoot !== cachedProjectRoot) documentIdentityController.invalidate();
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
    if (filter === "orange") {
      return tasks.filter(function (t) {
        const z = String(t.zone || "").toLowerCase();
        return (
          z === "orange" ||
          z === "pending" ||
          z === "pending_approval" ||
          t.pending_approval === true
        );
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
      orange: safeNum(board && board.orange),
      red: safeNum(board && board.red),
      green: safeNum(board && board.green),
      accepted: tasks.filter(function (t) {
        return t.zone === "accepted" || t.accepted === true;
      }).length,
    };
    if (!board) {
      counts.gray =
        counts.yellow =
        counts.orange =
        counts.red =
        counts.green =
        counts.accepted =
          0;
      counts.overview = 0;
    } else {
      if (tasks.length && !(board.gray || board.yellow || board.red || board.green)) {
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
      if (!board.orange) {
        counts.orange = tasks.filter(function (t) {
          const z = String(t.zone || "").toLowerCase();
          return (
            z === "orange" ||
            z === "pending" ||
            z === "pending_approval" ||
            t.pending_approval === true
          );
        }).length;
      }
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
    orange: "待核准",
    pending: "待核准",
    pending_approval: "待核准",
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
    if (z === "orange" || z === "pending" || z === "pending_approval") {
      return '<span class="dot dot-orange status-light" aria-hidden="true"></span>';
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
    /* 工項表保留為主畫面；錯誤改 toast，不蓋掉表單 */
    if (viewport) viewport.hidden = false;
    if (list) list.innerHTML = "";
    if (err) {
      err.hidden = true;
      const body = document.getElementById("board-error-body");
      if (body) body.textContent = message || "無法取得看板投影。";
    }
    toast(message || "無法取得看板投影。");
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
      renderDocumentIdentity(documentIdentityController.view());
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
        /* 空清單：保留工項表（主功能），不展開空態／錯誤卡 */
        if (empty) empty.hidden = true;
        if (counts) counts.hidden = true;
        if (viewport) viewport.hidden = false;
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
    // Rendering the terminal board clears activeRunId before this continuation.
    if (activeRunId !== runId && !terminal) return;
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
    if (activeRunId != null) {
      toast("Run #" + activeRunId + " 仍在執行或收尾，請等待結束");
      setStatus("派工 Busy：目前 Run 尚未結束");
      return;
    }
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
    const runId = activeRunId;
    const gen = runPollGeneration;
    if (btnCancel) btnCancel.disabled = true;
    setRunClassification("running", "取消中，正在收尾輸出");
    try {
      const board = await invoke("cancel_run", { runId: runId });
      appendLog("[cancel] invoke cancel_run run=" + runId);
      if (activeRunId !== runId || gen !== runPollGeneration) return;
      if (board) renderBoard(board);
      toast("已提出取消，正在收尾輸出");
    } catch (err) {
      if (activeRunId !== runId || gen !== runPollGeneration) return;
      if (btnCancel) btnCancel.disabled = false;
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

  function showGitApprove(op, extra) {
    if (!gitWritesEnabled) {
      toast("寫入閘門關閉");
      return;
    }
    const payload = extra && typeof extra === "object" ? extra : { branch: extra };
    pendingGitWrite = {
      op: op,
      branch: payload.branch,
      stash: payload.stash,
      message: payload.message,
      name: payload.name,
      url: payload.url,
      path: payload.path,
      contents: payload.contents,
    };
    const box = document.getElementById("git-approve");
    const title = document.getElementById("git-approve-title");
    const lede = document.getElementById("git-approve-lede");
    const msgWrap = document.getElementById("git-approve-msg-wrap");
    const remoteWrap = document.getElementById("git-approve-remote-wrap");
    const refWrap = document.getElementById("git-approve-refspec-wrap");
    const authorWrap = document.getElementById("git-approve-author-wrap");
    const emailWrap = document.getElementById("git-approve-email-wrap");
    const ignoreWrap = document.getElementById("git-approve-ignore-wrap");
    const tagWrap = document.getElementById("git-approve-tag-wrap");
    const branchWrap = document.getElementById("git-approve-branch-wrap");
    const remoteNameWrap = document.getElementById("git-approve-remote-name-wrap");
    const remoteUrlWrap = document.getElementById("git-approve-remote-url-wrap");
    if (title) {
      title.textContent =
        op === "push"
          ? "審核 Push"
          : op === "switch"
          ? "審核 Switch"
          : op === "identity"
          ? "審核提交作者"
          : op === "ignore"
          ? "審核 .gitignore"
          : op === "stash-apply"
          ? "審核 Stash Apply"
          : op === "stash-pop"
          ? "審核 Stash Pop"
          : op === "stash-drop"
          ? "審核 Stash Drop"
          : op === "stash-create"
          ? "審核 Stash Create"
          : op === "tag-create"
          ? "審核 Tag Create"
          : op === "tag-delete"
          ? "審核 Tag Delete"
          : op === "branch-create"
          ? "審核 Branch Create"
          : op === "branch-delete"
          ? "審核 Branch Delete"
          : op === "remote-add"
          ? "審核 Remote Add"
          : op === "remote-set-url"
          ? "審核 Remote Set URL"
          : op === "remote-remove"
          ? "審核 Remote Remove"
          : op === "conflict-save"
          ? "審核 Conflict Save"
          : op === "conflict-continue"
          ? "審核 Conflict Continue"
          : op === "conflict-abort"
          ? "審核 Conflict Abort"
          : "審核 Commit";
    }
    if (lede) {
      lede.textContent =
        op === "push"
          ? "核准後經 git_write_push → GitWritePort；拒絕則無突變。不做 force push。"
          : op === "switch"
          ? "核准後經 git_switch_branch → GitWritePort；切換到 " +
            (payload.branch || "") +
            "。拒絕則無突變。"
          : op === "identity"
          ? "核准後經 git_write_identity → GitWritePort；只寫本儲存庫 user.name／user.email。拒絕則無突變。"
          : op === "ignore"
          ? "核准後經 git_write_ignore → GitWritePort；只寫根目錄 .gitignore，不停止追蹤既有檔案。拒絕則無突變。"
          : op === "stash-apply"
          ? "核准後經 git_write_stash_apply → GitWritePort；套用 " +
            (payload.stash || "") +
            " 並保留 Stash。衝突時不假裝成功。拒絕則無突變。"
          : op === "stash-pop"
          ? "核准後經 git_write_stash_pop → GitWritePort；套用並移除 " +
            (payload.stash || "") +
            "。衝突時保留 Stash，不假裝成功。拒絕則無突變。"
          : op === "stash-drop"
          ? "核准後經 git_write_stash_drop → GitWritePort；刪除 " +
            (payload.stash || "") +
            "。缺漏的 Stash 會誠實失敗，不執行 stash clear。拒絕則無突變。"
          : op === "stash-create"
          ? "核准後經 git_write_stash_push → GitWritePort；只保存已追蹤變更（不加 -u／--all）。拒絕則無突變。"
          : op === "tag-create"
          ? "核准後經 git_write_tag → GitWritePort；本機建立標籤。空白訊息＝lightweight；有訊息＝annotated。重名誠實失敗。不刪除、不推送、不加 -f。拒絕則無突變。"
          : op === "tag-delete"
          ? "核准後經 git_write_tag_delete → GitWritePort；只刪本機標籤 " +
            (payload.name || "") +
            "。缺漏的標籤會誠實失敗。不推送、不加 -f、不刪遠端。拒絕則無突變。"
          : op === "branch-create"
          ? "核准後經 git_write_branch_create → GitWritePort；本機建立分支（git branch -- name），不切換、不設 upstream、不加 -C／-D。重名與無效名稱誠實失敗。拒絕則無突變。"
          : op === "branch-delete"
          ? "核准後經 git_write_branch_delete → GitWritePort；只刪本機分支 " +
            (payload.name || "") +
            "（git branch -d -- name）。不刪目前 HEAD。未合併會誠實失敗，不加 -D／--force／-r，不刪遠端。拒絕則無突變。"
          : op === "remote-add"
          ? "核准後經 git_write_remote_add → GitWritePort；只新增本機遠端設定（git remote add -- name url），不 fetch、不加 -f、不 set-url、不 push。重名與無效名稱／URL 誠實失敗。拒絕則無突變。"
          : op === "remote-set-url"
          ? "核准後經 git_write_remote_set_url → GitWritePort；只更新既有本機遠端 URL（git remote set-url -- name url），不 fetch、不加 --add／--delete／--push／--mirror、不 push。未知遠端與無效名稱／URL 誠實失敗。拒絕則無突變。"
          : op === "remote-remove"
          ? "核准後經 git_write_remote_remove → GitWritePort；只移除本機遠端設定 " +
            (payload.name || "") +
            "（git remote remove -- name）。缺漏的遠端會誠實失敗。不 prune、不 fetch。拒絕則無突變。"
          : op === "conflict-save"
          ? "核准後經 git_write_conflict_save → GitWritePort；寫入 " +
            (payload.path || "") +
            " 後 git add -- path。殘留衝突標記會誠實失敗。不加 -A／.。拒絕則無突變。"
          : op === "conflict-continue"
          ? "核准後經 git_write_conflict_continue → GitWritePort；依偵測狀態執行 merge／rebase／cherry-pick --continue。不加 --skip、不加 -X theirs／ours。拒絕則無突變。"
          : op === "conflict-abort"
          ? "核准後經 git_write_conflict_abort → GitWritePort；依偵測狀態執行 --abort。不做 reset --hard。拒絕則無突變。"
          : "核准後經 git_write_commit → GitWritePort；拒絕則無突變。";
    }
    if (msgWrap) {
      msgWrap.hidden = op !== "commit" && op !== "stash-create" && op !== "tag-create";
      const span = msgWrap.querySelector("span");
      const input = document.getElementById("git-approve-message");
      if (span) {
        span.textContent =
          op === "stash-create"
            ? "Stash 說明"
            : op === "tag-create"
            ? "標籤訊息（選填）"
            : "Commit message";
      }
      if (input) {
        input.setAttribute(
          "aria-label",
          op === "stash-create"
            ? "Stash message"
            : op === "tag-create"
            ? "Tag message (optional)"
            : "Commit message"
        );
      }
    }
    if (remoteWrap) remoteWrap.hidden = op !== "push";
    if (refWrap) refWrap.hidden = op !== "push";
    if (authorWrap) authorWrap.hidden = op !== "identity";
    if (emailWrap) emailWrap.hidden = op !== "identity";
    if (ignoreWrap) ignoreWrap.hidden = op !== "ignore";
    if (tagWrap) tagWrap.hidden = op !== "tag-create";
    if (branchWrap) branchWrap.hidden = op !== "branch-create";
    if (remoteNameWrap) remoteNameWrap.hidden = op !== "remote-add" && op !== "remote-set-url";
    if (remoteUrlWrap) remoteUrlWrap.hidden = op !== "remote-add" && op !== "remote-set-url";
    if (box) box.hidden = false;
    if (op === "commit" || op === "stash-create") {
      const msg = document.getElementById("git-approve-message");
      if (msg) {
        msg.focus();
        if (op === "stash-create") {
          msg.value = payload.message != null ? String(payload.message) : "";
        } else if (!msg.value) {
          msg.value = "";
        }
      }
    } else if (op === "tag-create") {
      const tag = document.getElementById("git-approve-tag");
      const msg = document.getElementById("git-approve-message");
      if (tag) {
        tag.value = payload.name != null ? String(payload.name) : "";
        tag.focus();
      }
      if (msg) {
        msg.value = payload.message != null ? String(payload.message) : "";
      }
    } else if (op === "branch-create") {
      const branch = document.getElementById("git-approve-branch");
      if (branch) {
        branch.value = payload.name != null ? String(payload.name) : "";
        branch.focus();
      }
    } else if (op === "remote-add" || op === "remote-set-url") {
      const nameEl = document.getElementById("git-approve-remote-name");
      const urlEl = document.getElementById("git-approve-remote-url");
      if (nameEl) {
        nameEl.value = payload.name != null ? String(payload.name) : "";
        if (op === "remote-add") nameEl.focus();
      }
      if (urlEl) {
        urlEl.value = payload.url != null ? String(payload.url) : "";
        if (op === "remote-set-url") urlEl.focus();
      }
    } else if (op === "push") {
      const remote = document.getElementById("git-approve-remote");
      if (remote && !remote.value.trim()) remote.value = "origin";
      if (remote) remote.focus();
    } else if (op === "identity") {
      const author = document.getElementById("git-approve-author");
      const email = document.getElementById("git-approve-email");
      if (author) author.value = payload.author || "";
      if (email) email.value = payload.email || "";
      if (author) author.focus();
    } else if (op === "ignore") {
      const ignore = document.getElementById("git-approve-ignore");
      if (ignore) {
        ignore.value = payload.ignore != null ? String(payload.ignore) : "";
        ignore.focus();
      }
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
      } else if (op === "switch") {
        const branch = pendingGitWrite.branch;
        if (!branch) {
          hideGitApprove();
          setGitStatusLine("未指定分支，未切換", true);
          return;
        }
        const dto = await invoke("git_switch_branch", {
          args: { repo: repo, branch: branch, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已切換到 " + branch + "（經 GitWritePort）", false);
          toast("切換完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "切換失敗：" + ((dto && dto.message) || "unknown"),
            true
          );
          toast("切換失敗");
        }
      } else if (op === "identity") {
        const authorEl = document.getElementById("git-approve-author");
        const emailEl = document.getElementById("git-approve-email");
        const author = authorEl && authorEl.value ? authorEl.value.trim() : "";
        const email = emailEl && emailEl.value ? emailEl.value.trim() : "";
        if (!author || !email) {
          setGitStatusLine("user.name 與 user.email 不可空白", true);
          toast("請填寫本儲存庫作者");
          return;
        }
        const dto = await invoke("git_write_identity", {
          args: { repo: repo, author: author, email: email, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已寫入本儲存庫 user.name／user.email（經 GitWritePort）", false);
          toast("作者設定已儲存");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "作者設定失敗：" + ((dto && dto.message) || "unknown"),
            true
          );
          toast("作者設定失敗");
        }
      } else if (op === "ignore") {
        const ignoreEl = document.getElementById("git-approve-ignore");
        const ignore = ignoreEl && ignoreEl.value != null ? ignoreEl.value : "";
        const dto = await invoke("git_write_ignore", {
          args: { repo: repo, ignore: ignore, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已寫入根目錄 .gitignore（經 GitWritePort；未停止追蹤）", false);
          toast(".gitignore 已儲存");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            ".gitignore 失敗：" + ((dto && dto.message) || "unknown"),
            true
          );
          toast(".gitignore 失敗");
        }
      } else if (op === "stash-apply" || op === "stash-pop" || op === "stash-drop") {
        const stash = pendingGitWrite.stash;
        const cmd =
          op === "stash-pop"
            ? "git_write_stash_pop"
            : op === "stash-drop"
            ? "git_write_stash_drop"
            : "git_write_stash_apply";
        if (!stash) {
          hideGitApprove();
          setGitStatusLine("未指定 Stash，未執行", true);
          return;
        }
        const dto = await invoke(cmd, {
          args: { repo: repo, stash: stash, approved: true },
        });
        hideGitApprove();
        const verb =
          op === "stash-pop" ? "pop" : op === "stash-drop" ? "drop" : "apply";
        if (dto && dto.ok) {
          setGitStatusLine("已 " + verb + " " + stash + "（經 GitWritePort）", false);
          toast("Stash " + verb + " 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            verb +
              " 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（Stash／工作樹依 Git 真實結果保留）",
            true
          );
          toast("Stash " + verb + " 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "stash-create") {
        const msgEl = document.getElementById("git-approve-message");
        const message = msgEl && msgEl.value ? msgEl.value.trim() : "";
        if (!message) {
          setGitStatusLine("Stash 說明不可空白", true);
          toast("請填寫 Stash 說明");
          return;
        }
        const dto = await invoke("git_write_stash_push", {
          args: { repo: repo, message: message, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已建立 Stash（經 GitWritePort；僅已追蹤變更）", false);
          toast("Stash create 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "create 失敗：" + ((dto && dto.message) || "unknown") + "（工作樹依 Git 真實結果保留）",
            true
          );
          toast("Stash create 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "tag-create") {
        const tagEl = document.getElementById("git-approve-tag");
        const name = tagEl && tagEl.value ? tagEl.value.trim() : "";
        if (!name) {
          setGitStatusLine("標籤名稱不可空白", true);
          toast("請填寫標籤名稱");
          return;
        }
        const msgEl = document.getElementById("git-approve-message");
        const message = msgEl && msgEl.value ? msgEl.value.trim() : "";
        const dto = await invoke("git_write_tag", {
          args: { repo: repo, name: name, message: message, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine(
            "已建立標籤 " + name + "（經 GitWritePort；" + (message ? "annotated" : "lightweight") + "）",
            false
          );
          toast("Tag create 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "tag 失敗：" + ((dto && dto.message) || "unknown") + "（本機標籤依 Git 真實結果保留）",
            true
          );
          toast("Tag create 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "tag-delete") {
        const name = pendingGitWrite.name;
        if (!name) {
          hideGitApprove();
          setGitStatusLine("未指定標籤，未刪除", true);
          return;
        }
        const dto = await invoke("git_write_tag_delete", {
          args: { repo: repo, name: name, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已刪除本機標籤 " + name + "（經 GitWritePort；未推送）", false);
          toast("Tag delete 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "tag delete 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（本機標籤依 Git 真實結果保留）",
            true
          );
          toast("Tag delete 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "branch-create") {
        const branchEl = document.getElementById("git-approve-branch");
        const name = branchEl && branchEl.value ? branchEl.value.trim() : "";
        if (!name) {
          setGitStatusLine("分支名稱不可空白", true);
          toast("請填寫本機分支名稱");
          return;
        }
        const dto = await invoke("git_write_branch_create", {
          args: { repo: repo, name: name, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine(
            "已建立本機分支 " + name + "（經 GitWritePort；未切換）",
            false
          );
          toast("Branch create 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "branch 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（目前 HEAD 與本機分支依 Git 真實結果保留）",
            true
          );
          toast("Branch create 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "branch-delete") {
        const name = pendingGitWrite.name;
        if (!name) {
          hideGitApprove();
          setGitStatusLine("未指定分支，未刪除", true);
          return;
        }
        const dto = await invoke("git_write_branch_delete", {
          args: { repo: repo, name: name, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine(
            "已刪除本機分支 " + name + "（經 GitWritePort；git branch -d；未切換）",
            false
          );
          toast("Branch delete 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "branch delete 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（目前 HEAD 與本機分支依 Git 真實結果保留）",
            true
          );
          toast("Branch delete 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "remote-add") {
        const nameEl = document.getElementById("git-approve-remote-name");
        const urlEl = document.getElementById("git-approve-remote-url");
        const name = nameEl && nameEl.value ? nameEl.value.trim() : "";
        const url = urlEl && urlEl.value ? urlEl.value.trim() : "";
        if (!name || !url) {
          setGitStatusLine("遠端名稱與 URL 不可空白", true);
          toast("請填寫遠端名稱與 URL");
          return;
        }
        const dto = await invoke("git_write_remote_add", {
          args: { repo: repo, name: name, url: url, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine(
            "已新增本機遠端 " + name + "（經 GitWritePort；未 fetch／未 push）",
            false
          );
          toast("Remote add 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "remote add 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（本機遠端設定依 Git 真實結果保留）",
            true
          );
          toast("Remote add 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "remote-set-url") {
        const nameEl = document.getElementById("git-approve-remote-name");
        const urlEl = document.getElementById("git-approve-remote-url");
        const name = nameEl && nameEl.value ? nameEl.value.trim() : "";
        const url = urlEl && urlEl.value ? urlEl.value.trim() : "";
        if (!name || !url) {
          setGitStatusLine("遠端名稱與 URL 不可空白", true);
          toast("請填寫遠端名稱與 URL");
          return;
        }
        const dto = await invoke("git_write_remote_set_url", {
          args: { repo: repo, name: name, url: url, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine(
            "已更新本機遠端 " + name + " 的 URL（經 GitWritePort；未 fetch／未 push）",
            false
          );
          toast("Remote set-url 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "remote set-url 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（本機遠端設定依 Git 真實結果保留）",
            true
          );
          toast("Remote set-url 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "remote-remove") {
        const name = pendingGitWrite.name;
        if (!name) {
          hideGitApprove();
          setGitStatusLine("未指定遠端，未移除", true);
          return;
        }
        const dto = await invoke("git_write_remote_remove", {
          args: { repo: repo, name: name, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已移除本機遠端 " + name + "（經 GitWritePort；未 prune／未 fetch）", false);
          toast("Remote remove 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "remote remove 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（本機遠端設定依 Git 真實結果保留）",
            true
          );
          toast("Remote remove 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "conflict-save") {
        const path = pendingGitWrite.path;
        if (!path) {
          hideGitApprove();
          setGitStatusLine("未指定衝突路徑，未儲存", true);
          return;
        }
        const dto = await invoke("git_write_conflict_save", {
          args: {
            repo: repo,
            path: path,
            contents: pendingGitWrite.contents || "",
            approved: true,
          },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已儲存並暫存 " + path + "（經 GitWritePort；git add -- path）", false);
          toast("Conflict save 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "conflict save 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（衝突狀態依 Git 真實結果保留）",
            true
          );
          toast("Conflict save 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "conflict-continue") {
        const dto = await invoke("git_write_conflict_continue", {
          args: { repo: repo, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已繼續目前衝突操作（經 GitWritePort；未 --skip）", false);
          toast("Conflict continue 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "conflict continue 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（操作狀態依 Git 真實結果保留）",
            true
          );
          toast("Conflict continue 失敗（未假裝成功）");
          await cmdGitRefresh();
        }
      } else if (op === "conflict-abort") {
        const dto = await invoke("git_write_conflict_abort", {
          args: { repo: repo, approved: true },
        });
        hideGitApprove();
        if (dto && dto.ok) {
          setGitStatusLine("已中止目前衝突操作（經 GitWritePort；--abort）", false);
          toast("Conflict abort 完成");
          await cmdGitRefresh();
        } else {
          setGitStatusLine(
            "conflict abort 失敗：" +
              ((dto && dto.message) || "unknown") +
              "（操作狀態依 Git 真實結果保留）",
            true
          );
          toast("Conflict abort 失敗（未假裝成功）");
          await cmdGitRefresh();
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

  let activeGitView = "changes";

  function setGitView(view) {
    const next = view || "changes";
    activeGitView = next;
    document.querySelectorAll(".git-rail-btn[data-git-view]").forEach(function (btn) {
      const on = btn.getAttribute("data-git-view") === next;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-pressed", on ? "true" : "false");
    });
    document.querySelectorAll(".git-view-pane[data-git-pane]").forEach(function (pane) {
      const on = pane.getAttribute("data-git-pane") === next;
      pane.classList.toggle("is-active", on);
      pane.hidden = !on;
    });
  }

  function renderGitHistory(commits) {
    const list = document.getElementById("git-history-list");
    const empty = document.getElementById("git-history-empty");
    if (!list) return;
    list.innerHTML = "";
    const rows = commits || [];
    if (rows.length === 0) {
      list.hidden = true;
      if (empty) empty.hidden = false;
      return;
    }
    list.hidden = false;
    if (empty) empty.hidden = true;
    rows.forEach(function (c) {
      const li = document.createElement("li");
      li.className = "git-history-item";
      const hash = (c && c.hash) || "";
      const subject = (c && c.subject) || "";
      li.innerHTML =
        '<span class="hash">' +
        escapeHtml(hash.slice(0, 7) || "—") +
        '</span><span class="subject">' +
        escapeHtml(subject || "（無主旨）") +
        "</span>";
      list.appendChild(li);
    });
  }

  function renderGitSummary(dto) {
    if (isGitUxMockMode()) {
      const emptyStub = document.getElementById("git-empty");
      if (emptyStub) {
        emptyStub.hidden = true;
        emptyStub.setAttribute("aria-hidden", "true");
      }
      return;
    }
    const branchEl = document.getElementById("git-branch");
    const countEl = document.getElementById("git-entry-count");
    const countSub = document.getElementById("git-entry-count-sub");
    const syncEl = document.getElementById("git-sync-count");
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
    if (syncEl) {
      // ahead/behind 已進 GitWorkbenchDto（G2）— 顯示分歧數
      const hasUpstream = dto.upstream != null && dto.upstream !== "";
      const ahead = dto.ahead || 0;
      const behind = dto.behind || 0;
      if (hasUpstream) {
        syncEl.textContent = "↑" + ahead + " ↓" + behind;
        syncEl.title =
          "ahead " + ahead + " / behind " + behind + "（上游 " + dto.upstream + "）";
      } else {
        syncEl.textContent = "↑— ↓—";
        syncEl.title = "未追蹤上游分支";
      }
    }
    applyWriteGate(!!dto.writes_enabled);
    const n = String(dto.entry_count || 0);
    if (countEl) countEl.textContent = n;
    if (countSub) countSub.textContent = n;

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

    renderGitHistory(dto.recent_commits || []);

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
    if (
      window.EluSlotGitUxMock &&
      window.EluSlotGitUxMock.applyLive &&
      document.getElementById("git-ux-root")
    ) {
      const uxRoot = document.getElementById("git-ux-root");
      if (uxRoot) uxRoot.hidden = false;
      window.EluSlotGitUxMock.applyLive(dto);
    }
  }

  function renderGitNotRun(message) {
    /* EluSlot_Git_UX 假資料主區自有空態／情境；不顯示舊 NOT RUN 卡 */
    if (isGitUxMockMode()) {
      const emptyStub = document.getElementById("git-empty");
      if (emptyStub) {
        emptyStub.hidden = true;
        emptyStub.setAttribute("aria-hidden", "true");
      }
      return;
    }
    const empty = document.getElementById("git-empty");
    const list = document.getElementById("git-entries");
    const branchEl = document.getElementById("git-branch");
    const countEl = document.getElementById("git-entry-count");
    const countSub = document.getElementById("git-entry-count-sub");
    const syncEl = document.getElementById("git-sync-count");
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
    if (countSub) countSub.textContent = "0";
    if (syncEl) syncEl.textContent = "↑— ↓—";
    if (diffTitle) diffTitle.textContent = "Diff（NOT RUN）";
    if (diffBody) diffBody.textContent = "（NOT RUN）";
    renderGitHistory([]);
    applyWriteGate(false);
    setGitStatusLine(message || "git_workbench_summary → NOT RUN", false);
    if (
      window.EluSlotGitUxMock &&
      window.EluSlotGitUxMock.applyLive &&
      document.getElementById("git-ux-root")
    ) {
      window.EluSlotGitUxMock.applyLive({
        entries: [],
        recent_commits: [],
        ahead: 0,
        behind: 0,
        branch: null,
        upstream: null,
      });
    }
  }

  // PD-ELU-GIT-ARCH-01 A1 controller begin
  function createGitIndexCommitUiController(options) {
    const getProjectRoot = options.getProjectRoot;
    const invokeCommand = options.invoke;
    const onStatus = options.onStatus || function () {};
    const onRefresh = options.onRefresh || async function () {};
    let root = String(getProjectRoot() || "").trim();
    let preview = null;
    let confirmedGeneration = null;
    let message = "";
    let status = "NOT RUN — 尚未預覽已暫存的 Index";
    let busy = false;
    let requestEpoch = 0;

    function publish(nextStatus) {
      status = nextStatus;
      onStatus(status);
    }
    function getView() {
      const sameRoot = !!preview && preview.project_root === root;
      const canConfirm = sameRoot && !busy && confirmedGeneration === preview.generation && !!message.trim();
      return {
        root,
        preview: preview ? {
          preview_id: preview.preview_id,
          generation: preview.generation,
          head_oid: preview.head_oid,
          index_tree_oid: preview.index_tree_oid,
          paths: preview.paths.slice(),
        } : null,
        confirmed: !!(preview && confirmedGeneration === preview.generation),
        confirmedGeneration,
        message,
        status,
        busy,
        canPreview: !!root && !busy,
        canConfirm,
      };
    }
    function syncProjectRoot(projectRoot) {
      if (arguments.length === 0) return getView();
      const nextRoot = String(projectRoot || "").trim();
      if (nextRoot !== root) {
        root = nextRoot;
        requestEpoch += 1;
        busy = false;
        preview = null;
        confirmedGeneration = null;
        publish(root ? "專案已切換；請重新預覽" : "NOT RUN — 尚未綁定專案");
      }
      return getView();
    }
    function setMessage(value) {
      message = String(value == null ? "" : value);
      return getView();
    }
    function setConfirmed(value, generation) {
      confirmedGeneration = value && preview && generation === preview.generation ? generation : null;
      return getView();
    }
    async function runPreview() {
      if (!root || busy) {
        publish(root ? "操作進行中" : "InvalidInput — 尚未綁定專案");
        return null;
      }
      const requestRoot = root;
      const epoch = ++requestEpoch;
      preview = null;
      confirmedGeneration = null;
      busy = true;
      publish("正在讀取已暫存的 Index…");
      try {
        const dto = await invokeCommand("git_index_commit_preview", { repo: requestRoot });
        if (epoch !== requestEpoch || requestRoot !== root) return null;
        const fingerprint = dto && dto.fingerprint;
        if (!dto || !dto.preview_id || !Number.isInteger(dto.generation) || !fingerprint) {
          publish("InvalidPreview — Host 回傳的預覽資料不完整");
          return null;
        }
        preview = {
          preview_id: dto.preview_id,
          generation: dto.generation,
          // Bind the UI confirmation to the exact request root; the backend
          // independently validates and displays its canonical project root.
          project_root: requestRoot,
          head_oid: fingerprint.head_oid || "（尚無 HEAD）",
          index_tree_oid: fingerprint.index_tree_oid,
          paths: Array.isArray(dto.display_paths) ? dto.display_paths.slice() : [],
        };
        publish("預覽就緒；確認此 generation 後才可提交 Index");
        return getView().preview;
      } catch (error) {
        if (epoch !== requestEpoch) return null;
        publish(formatGitIndexCommitError(error));
        return null;
      } finally {
        if (epoch === requestEpoch) busy = false;
        onStatus(status);
      }
    }
    async function confirm() {
      const current = getView();
      if (!current.canConfirm) {
        publish(!current.preview ? "InvalidPreview — 請先重新預覽" : "ApprovalRequired — 請核對 generation、訊息並勾選確認");
        return null;
      }
      const token = preview;
      const requestRoot = root;
      const epoch = ++requestEpoch;
      busy = true;
      publish("正在確認預覽並提交已暫存的 Index…");
      try {
        const outcome = await invokeCommand("git_index_commit_confirm", {
          request: {
            preview_id: token.preview_id,
            generation: token.generation,
            message: message,
            confirmed: true,
          },
        });
        if (epoch !== requestEpoch || requestRoot !== root) return null;
        if (outcome && outcome.state === "Committed") {
          preview = null;
          confirmedGeneration = null;
          publish("Committed — 僅提交預覽中的 Index；工作目錄由本操作保留");
          await onRefresh();
          return outcome;
        }
        const requiresFresh = !!(outcome && outcome.retry_requires_new_preview);
        if (requiresFresh) {
          preview = null;
          confirmedGeneration = null;
        }
        publish(formatGitIndexCommitError(outcome || { code: "OutcomeUnknown", diagnostic: "Host 未回傳提交結果" }));
        return outcome;
      } catch (error) {
        if (epoch !== requestEpoch) return null;
        const knownPreInvocationFailure = error &&
          error.mutation_started === false && error.requires_new_preview === false;
        if (!knownPreInvocationFailure) {
          preview = null;
          confirmedGeneration = null;
        }
        publish(error && error.code
          ? formatGitIndexCommitError(error)
          : "OutcomeUnknown — 提交命令未能回報是否已啟動；請重新預覽後再操作");
        return null;
      } finally {
        if (epoch === requestEpoch) busy = false;
        onStatus(status);
      }
    }
    return { getView, syncProjectRoot, setMessage, setConfirmed, preview: runPreview, confirm };
  }

  function formatGitIndexCommitError(error) {
    if (!error) return "OutcomeUnknown — 未取得 Host 回覆";
    const code = error.code || error.state || "Unavailable";
    const diagnostic = error.diagnostic || error.message || String(error);
    return String(code) + " — " + String(diagnostic);
  }

  function mountGitIndexCommitUi(options) {
    const documentRef = options.document;
    const parent = options.parent;
    const rootValue = options.getProjectRoot;
    const invokeCommand = options.invoke;
    const refresh = options.onRefresh;
    const section = documentRef.createElement("section");
    section.id = "git-index-commit-a1";
    section.setAttribute("aria-labelledby", "git-index-commit-title");
    const title = documentRef.createElement("h2");
    title.id = "git-index-commit-title";
    title.textContent = "提交已暫存的 Index（A1）";
    const intro = documentRef.createElement("p");
    intro.textContent = "唯讀預覽後，明確確認同一代預覽；不會替你 stage、push 或修改工作目錄。";
    const rootLabel = documentRef.createElement("p");
    const rootOutput = documentRef.createElement("code");
    rootOutput.id = "git-index-commit-project-root";
    rootLabel.appendChild(documentRef.createTextNode("專案根目錄："));
    rootLabel.appendChild(rootOutput);
    const snapshot = documentRef.createElement("dl");
    const headTerm = documentRef.createElement("dt"); headTerm.textContent = "HEAD";
    const headValue = documentRef.createElement("dd"); headValue.id = "git-index-commit-head";
    const treeTerm = documentRef.createElement("dt"); treeTerm.textContent = "已暫存 Index tree";
    const treeValue = documentRef.createElement("dd"); treeValue.id = "git-index-commit-tree";
    snapshot.append(headTerm, headValue, treeTerm, treeValue);
    const pathsLabel = documentRef.createElement("strong"); pathsLabel.textContent = "預覽路徑";
    const paths = documentRef.createElement("ul"); paths.id = "git-index-commit-paths";
    const messageLabel = documentRef.createElement("label");
    messageLabel.textContent = "Commit message";
    const message = documentRef.createElement("textarea");
    message.id = "git-index-commit-message";
    message.rows = 3;
    messageLabel.appendChild(message);
    const confirmLabel = documentRef.createElement("label");
    const checkbox = documentRef.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = "git-index-commit-confirmed";
    confirmLabel.appendChild(checkbox);
    const confirmText = documentRef.createElement("span");
    confirmLabel.appendChild(confirmText);
    const previewButton = documentRef.createElement("button");
    previewButton.type = "button";
    previewButton.id = "git-index-commit-preview";
    previewButton.textContent = "重新預覽 Index";
    const commitButton = documentRef.createElement("button");
    commitButton.type = "button";
    commitButton.id = "git-index-commit-submit";
    commitButton.textContent = "確認並提交 Index";
    const status = documentRef.createElement("p");
    status.id = "git-index-commit-status";
    status.setAttribute("role", "status");
    section.append(title, intro, rootLabel, snapshot, pathsLabel, paths, messageLabel, confirmLabel, previewButton, commitButton, status);
    parent.appendChild(section);
    const controller = createGitIndexCommitUiController({
      getProjectRoot: rootValue,
      invoke: invokeCommand,
      onRefresh: refresh,
      onStatus: (text) => { status.textContent = text; render(); },
    });
    function render() {
      const view = controller.getView();
      rootOutput.textContent = view.root || "（未綁定）";
      headValue.textContent = view.preview ? view.preview.head_oid : "NOT RUN";
      treeValue.textContent = view.preview ? view.preview.index_tree_oid : "NOT RUN";
      paths.replaceChildren();
      (view.preview ? view.preview.paths : []).forEach((path) => {
        const item = documentRef.createElement("li"); item.textContent = path; paths.appendChild(item);
      });
      confirmText.textContent = view.preview
        ? "我已核對預覽第 " + view.preview.generation + " 代；只提交上述已暫存內容。"
        : "請先建立預覽";
      checkbox.checked = view.confirmed;
      checkbox.disabled = !view.preview || view.busy;
      previewButton.disabled = !view.canPreview;
      commitButton.disabled = !view.canConfirm;
      if (message.value !== view.message) message.value = view.message;
    }
    message.addEventListener("input", () => { controller.setMessage(message.value); render(); });
    checkbox.addEventListener("change", () => { controller.setConfirmed(checkbox.checked, controller.getView().preview?.generation); render(); });
    previewButton.addEventListener("click", async () => { await controller.preview(); render(); });
    commitButton.addEventListener("click", async () => { await controller.confirm(); render(); });
    controller.syncProjectRoot();
    render();
    return controller;
  }
  // PD-ELU-GIT-ARCH-01 A1 controller end

  /** EluSlot_Git_UX 假資料模式（優先）：不呼叫真實 git／IPC。 */
  function isGitUxMockMode() {
    return !!(
      !invoke &&
      window.EluSlotGitUxMock &&
      document.getElementById("git-ux-root")
    );
  }

  function wireGitIndexCommitUi() {
    if (!invoke || typeof document === "undefined") return null;
    const panel = document.getElementById("panel-git");
    if (!panel || panel.querySelector("#git-index-commit-a1")) return null;
    const mockRoot = document.getElementById("git-ux-root");
    if (mockRoot) mockRoot.hidden = false;
    if (mockRoot && window.EluSlotGitUxMock && window.EluSlotGitUxMock.mountLive) {
      window.EluSlotGitUxMock.mountLive({
        refresh: cmdGitRefresh,
        switchBranch: function (branch) { showGitApprove("switch", { branch: branch }); },
        saveIdentity: function () {
          const authorEl = document.getElementById("git-ux-author");
          const emailEl = document.getElementById("git-ux-email");
          showGitApprove("identity", {
            author: authorEl ? authorEl.value : "",
            email: emailEl ? emailEl.value : "",
          });
        },
        saveIgnore: function () {
          const ignoreEl = document.getElementById("git-ux-ignore");
          showGitApprove("ignore", {
            ignore: ignoreEl ? ignoreEl.value : "",
          });
        },
        stashApply: function (stash) { showGitApprove("stash-apply", { stash: stash }); },
        stashPop: function (stash) { showGitApprove("stash-pop", { stash: stash }); },
        stashDrop: function (stash) { showGitApprove("stash-drop", { stash: stash }); },
        stashCreate: function () { showGitApprove("stash-create", {}); },
        tagCreate: function () { showGitApprove("tag-create", {}); },
        tagDelete: function (name) { showGitApprove("tag-delete", { name: name }); },
        branchCreate: function () { showGitApprove("branch-create", {}); },
        branchDelete: function (name) { showGitApprove("branch-delete", { name: name }); },
        remoteAdd: function () {
          const urlEl = document.getElementById("git-ux-remote-url");
          showGitApprove("remote-add", {
            name: "",
            url: urlEl && urlEl.value ? urlEl.value : "",
          });
        },
        remoteSetUrl: function (name) {
          const picker = document.getElementById("git-ux-remote-picker");
          const urlEl = document.getElementById("git-ux-remote-url");
          showGitApprove("remote-set-url", {
            name: name || (picker && picker.value) || "",
            url: urlEl && urlEl.value ? urlEl.value : "",
          });
        },
        remoteRemove: function (name) {
          const picker = document.getElementById("git-ux-remote-picker");
          showGitApprove("remote-remove", {
            name: name || (picker && picker.value) || "",
          });
        },
        conflictSave: function (path, contents) {
          showGitApprove("conflict-save", {
            path: path || "",
            contents: contents || "",
          });
        },
        conflictContinue: function () {
          showGitApprove("conflict-continue", {});
        },
        conflictAbort: function () {
          showGitApprove("conflict-abort", {});
        },
        fetchDiff: async function (pathspec) {
          const d = await invoke("git_workbench_diff", {
            repo: gitRepoArg(),
            pathspec: pathspec || null,
          });
          return d && d.diff_text != null ? d.diff_text : "";
        },
      });
    }
    const controller = mountGitIndexCommitUi({
      document,
      parent: panel,
      getProjectRoot: () => cachedProjectRoot,
      invoke,
      onRefresh: cmdGitRefresh,
    });
    gitIndexCommitRootSync = (root) => controller.syncProjectRoot(root);
    return controller;
  }

  function bootGitUxMockIfPresent(scenario) {
    if (invoke) return false;
    if (!window.EluSlotGitUxMock || !window.EluSlotGitUxMock.boot) return false;
    window.EluSlotGitUxMock.boot(scenario || "dirty");
    setStatus("Git 工作台 · 假資料模式（EluSlot_Git_UX）");
    return true;
  }

  function bootSettingsUxMockIfPresent() {
    if (!window.EluSlotSettingsUxMock || !window.EluSlotSettingsUxMock.boot)
      return false;
    window.EluSlotSettingsUxMock.boot();
    return true;
  }

  async function cmdGitRefresh() {
    if (isGitUxMockMode()) {
      const st =
        window.EluSlotGitUxMock.getState &&
        window.EluSlotGitUxMock.getState();
      const scenario = (st && st.scenario) || "dirty";
      window.EluSlotGitUxMock.init(scenario);
      toast("已重新整理假資料快照");
      setStatus("git.mock.refresh → " + scenario);
      return;
    }
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
  if (typeof window !== "undefined") {
    window.__eluGitRefresh = cmdGitRefresh;
  }

  async function wireBootLoadProjections(opts) {
    opts = opts || {};
    const reason = opts.reason || "boot";
    const quiet = opts.quiet !== false;
    if (!invoke) {
      showBoardError("無 IPC — 看板空態（需 tauri dev）");
      if (isGitUxMockMode()) {
        bootGitUxMockIfPresent("dirty");
        setStatus("wire-boot — 瀏覽器＋Git 假資料（無 IPC）");
      } else {
        renderGitNotRun("無 IPC → Git NOT RUN");
        setStatus("wire-boot — 需 Tauri（空態／NOT RUN）");
      }
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

    if (isGitUxMockMode()) {
      bootGitUxMockIfPresent("dirty");
    } else {
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
    }

    setStatus(
      "wire-boot (" +
        reason +
        ") → load_local_board＋" +
        (isGitUxMockMode() ? "git-ux-mock" : "git_workbench_summary")
    );
    if (!quiet) toast("已自動載入看板＋Git 投影");
  }

  /** Bind seam for OPEN／settings — then auto-load board＋git＋project scene. */
  async function onProjectBound(root) {
    const trimmed = (root || "").trim();
    if (trimmed && !isForbiddenDemoRoot(trimmed)) {
      const previousDocumentRoot = cachedProjectRoot;
      cachedProjectRoot = trimmed;
      if (previousDocumentRoot !== cachedProjectRoot) documentIdentityController.invalidate();
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

  // —— PD-REMAIN-ARCH-UI-01 + Arch DAG shell：草稿畫布常駐；live 僅 Command ——

  /**
   * SSOT：docs/節點類型定義整理.pdf（01–10 Node Type）
   * ＋ docs/架構定義與整合-Layer Node.pdf：
   * Layer → Module Slot → Node；Layer.packsKind 由子物件推導（如丟入 API → Layer.API）。
   * 全系統物件 id 以 UUID 維持唯一性。
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
    "CodeFile",
    "Test",
    "Build",
    "AITask",
    "Layer",
  ];
  const ARCH_PACKABLE_KINDS = ARCH_NODE_KINDS.filter(function (k) {
    return k !== "Layer";
  });

  /** RFC4122 UUID；無 crypto.randomUUID 時退回可攜實作。 */
  function newArchUuid() {
    if (
      typeof crypto !== "undefined" &&
      typeof crypto.randomUUID === "function"
    ) {
      return crypto.randomUUID();
    }
    let d = Date.now();
    if (
      typeof performance !== "undefined" &&
      typeof performance.now === "function"
    ) {
      d += performance.now();
    }
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      const r = (d + Math.random() * 16) % 16 | 0;
      d = Math.floor(d / 16);
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  /** 確保 doc 內 node／module／edge／event id 皆為唯一 UUID（缺漏或衝突則補發）。 */
  function ensureArchDocUuids(doc) {
    if (!doc) return doc;
    const used = Object.create(null);
    function claim(id) {
      const s = id != null ? String(id).trim() : "";
      if (s && !used[s]) {
        used[s] = true;
        return s;
      }
      let u;
      do {
        u = newArchUuid();
      } while (used[u]);
      used[u] = true;
      return u;
    }
    (doc.nodes || []).forEach(function (n) {
      if (!n) return;
      n.id = claim(n.id);
      if (n.kind === "Layer" && Array.isArray(n.modules)) {
        n.modules.forEach(function (m) {
          if (!m) return;
          m.slotId = claim(m.slotId);
          m.moduleId = claim(m.moduleId);
        });
      }
    });
    (doc.edges || []).forEach(function (e) {
      if (!e) return;
      e.id = claim(e.id);
    });
    (doc.events || []).forEach(function (ev) {
      if (!ev) return;
      ev.eventId = claim(ev.eventId);
    });
    return doc;
  }
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
    CodeFile: ARCH_KIND_ICON_BASE + "CodeFile.svg",
    Test: ARCH_KIND_ICON_BASE + "Test.svg",
    Build: ARCH_KIND_ICON_BASE + "Build.svg",
    AITask: ARCH_KIND_ICON_BASE + "AITask.svg",
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
    CodeFile: {
      role: "Source File",
      inLabel: "spec",
      outLabel: "file",
    },
    Test: {
      role: "Test Suite",
      inLabel: "target",
      outLabel: "result",
    },
    Build: {
      role: "Build",
      inLabel: "inputs",
      outLabel: "artifact",
    },
    AITask: {
      role: "AI Task",
      inLabel: "context",
      outLabel: "output",
    },
    Layer: {
      role: "Pack same Node Type · inter-Layer 單線",
      inLabel: "in",
      outLabel: "out",
    },
  };
  /** Tasks Node.html：DEC-4 A。不含 Module，不含 workflowStatus／testStatus。 */
  const ARCH_EXTRA_KIND_FIELDS = {
    CodeFile: [
      "filePath",
      "language",
      "contentHash",
      "repositoryRef",
      "commitRef",
    ],
    Test: ["testSuiteRef", "testFramework", "testVersion", "resultSummary"],
    Build: ["buildProfile", "inputRefs", "artifactRefs", "buildResult"],
    AITask: ["modelPolicy", "promptVersion", "contextRefs", "budgetPolicy"],
  };

  function archExtraKindAttrs(node) {
    const keys = ARCH_EXTRA_KIND_FIELDS[node && node.kind];
    if (!keys) return "";
    let extra = "";
    keys.forEach(function (key) {
      if (key === "contentHash") return;
      extra += archAttr(key, node[key] != null ? String(node[key]) : "");
    });
    return extra;
  }

  /** SGGenAxis Node Architecture Specification §3 專屬屬性（規劃書）。 */
  const ARCH_SPEC_FIELDS = {
    API: [
      ["httpMethod", "httpMethod"],
      ["route", "route"],
      ["requestSchemaRef", "requestSchemaRef"],
      ["responseSchemaRef", "responseSchemaRef"],
      ["authPolicyRef", "authPolicyRef"],
      ["errorMapping", "errorMapping"],
      ["rateLimitPolicy", "rateLimitPolicy"],
    ],
    Contract: [
      ["contractKind", "contractKind"],
      ["schemaDefinition", "schemaDefinition"],
      ["requiredFields", "requiredFields"],
      ["constraints", "constraints"],
      ["compatibilityPolicy", "compatibilityPolicy"],
      ["contractVersion", "contractVersion"],
    ],
    UI: [
      ["componentType", "componentType"],
      ["layoutSpec", "layoutSpec"],
      ["dataBindings", "dataBindings"],
      ["actions", "actions"],
      ["stateDefinition", "stateDefinition"],
      ["validationRules", "validationRules"],
      ["accessibilitySpec", "accessibilitySpec"],
    ],
    Command: [
      ["commandName", "commandName"],
      ["inputSchemaRef", "inputSchemaRef"],
      ["preconditions", "preconditions"],
      ["effects", "effects"],
      ["transactionPolicy", "transactionPolicy"],
      ["idempotencyPolicy", "idempotencyPolicy"],
      ["failurePolicy", "failurePolicy"],
    ],
    Query: [
      ["queryName", "queryName"],
      ["sourceRefs", "sourceRefs"],
      ["filterSchema", "filterSchema"],
      ["sortRules", "sortRules"],
      ["paginationPolicy", "paginationPolicy"],
      ["projectionSchemaRef", "projectionSchemaRef"],
      ["consistencyPolicy", "consistencyPolicy"],
    ],
    Application: [
      ["useCaseName", "useCaseName"],
      ["steps", "steps"],
      ["orchestrationMode", "orchestrationMode"],
      ["branchRules", "branchRules"],
      ["timeoutPolicy", "timeoutPolicy"],
      ["retryPolicy", "retryPolicy"],
      ["compensationFlow", "compensationFlow"],
    ],
    Domain: [
      ["domainKind", "domainKind"],
      ["properties", "properties"],
      ["invariants", "invariants"],
      ["domainOperations", "domainOperations"],
      ["domainEvents", "domainEvents"],
      ["identityPolicy", "identityPolicy"],
      ["lifecycleRules", "lifecycleRules"],
    ],
    Infrastructure: [
      ["adapterKind", "adapterKind"],
      ["implementsRef", "implementsRef"],
      ["provider", "provider"],
      ["connectionRef", "connectionRef"],
      ["mappingRules", "mappingRules"],
      ["timeoutPolicy", "timeoutPolicy"],
      ["resiliencePolicy", "resiliencePolicy"],
    ],
    ACL: [
      ["externalContractRef", "externalContractRef"],
      ["internalContractRef", "internalContractRef"],
      ["translationRules", "translationRules"],
      ["enumMappings", "enumMappings"],
      ["errorTranslationRules", "errorTranslationRules"],
      ["versionMappingPolicy", "versionMappingPolicy"],
      ["fallbackPolicy", "fallbackPolicy"],
    ],
    Custom: [
      ["customTypeId", "customTypeId"],
      ["schemaRef", "schemaRef"],
      ["inputSchema", "inputSchema"],
      ["outputSchema", "outputSchema"],
      ["executionHandlerRef", "executionHandlerRef"],
      ["validationRules", "validationRules"],
      ["capabilities", "capabilities"],
      ["permissionPolicy", "permissionPolicy"],
    ],
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
  const ARCH_XML_DEFAULT_NAME = "default.esml";

  let archDoc = blankArchDoc();
  let archEditMode = true;
  let archGridPx = 8;
  let archZoom = 1;
  let archDrag = null; /* { ids, startX, startY, origins:{id:{x,y}} } */
  let archMarquee = null; /* { x0,y0,x1,y1 } stage coords */
  let archMemberDrag = null; /* { nodeId, layerId, startX, startY } */
  let archTrayDrag = null; /* Unassigned → Module：{ nodeId, startX, startY } */
  let archTreeMarquee = null; /* tree pane box-select { x0,y0,x1,y1 } client */
  /** 未分配 tree：kind 群組展開狀態（預設展開） */
  const archUnassignedTreeOpen = Object.create(null);
  let archLink = null;
  let archSelectedId = null; /* primary（Inspector） */
  let archSelectedIds = []; /* 多選；含 primary */
  /** 內層點到的 Module Slot（非 arch node） */
  let archSelectedModuleSlotId = null;
  /** 進入 Layer 內層的堆疊；空＝Root 畫布 */
  let archLayerStack = [];
  let archInteriorDrag = null;
  /** 中鍵平移進行中：暫停依捲動長大世界，避免視角被撐走 */
  let archMmbPanActive = false;
  /** 每一層畫布的中鍵平移位置與縮放。key＝root 或 layer id */
  const archViewportMemory = Object.create(null);
  /** 畫布連線選取：effective fromId + "\\0" + toId；Delete 可清除 */
  let archSelectedEdgeKey = null;
  let archConnectRows = [];
  let archSeq = 0;
  /** null／"all"＝全部；否則為單一 kind（Layer 篩選含 packs 相符之 Layer） */
  let archKindFilter = "all";
  /** 節點視窗專用關鍵字（與架構樹關鍵字獨立） */
  let archCanvasKeyword = "";
  /** 架構樹專用：關鍵字＋類別打勾（true＝顯示） */
  let archTreeKeyword = "";
  const archTreeKindVisible = Object.create(null);
  ARCH_NODE_KINDS.forEach(function (k) {
    archTreeKindVisible[k] = true;
  });
  let archXmlPathHint = ARCH_XML_DEFAULT_NAME;

  function blankArchDoc() {
    return {
      format: "eluslot.esml",
      formatVersion: 1,
      meta: {
        formSize: "1280x720",
        gridSize: 8,
        product_pass: false,
        encoding: "xml",
        viewports: {},
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
      '<eluslotArch format="' +
      escapeXml(d.format || "eluslot.esml") +
      '" formatVersion="' +
      escapeXml(String(d.formatVersion != null ? d.formatVersion : 1)) +
      '">\n';
    const viewports =
      meta.viewports && typeof meta.viewports === "object" ? meta.viewports : {};
    xml +=
      "  <meta" +
      archAttr("formSize", meta.formSize || "1280x720") +
      archAttr("gridSize", meta.gridSize != null ? String(meta.gridSize) : "8") +
      archAttr("product_pass", meta.product_pass ? "true" : "false") +
      archAttr("encoding", "xml") +
      ">\n";
    xml += "    <viewports>\n";
    Object.keys(viewports).forEach(function (key) {
      const view = viewports[key] || {};
      xml +=
        "      <viewport" +
        archAttr("key", key) +
        archAttr("zoom", view.zoom != null ? String(view.zoom) : "1") +
        archAttr(
          "scrollLeft",
          view.scrollLeft != null ? String(view.scrollLeft) : "0"
        ) +
        archAttr(
          "scrollTop",
          view.scrollTop != null ? String(view.scrollTop) : "0"
        ) +
        " />\n";
    });
    xml += "    </viewports>\n";
    xml += "  </meta>\n";
    xml += "  <nodes>\n";
    (d.nodes || []).forEach(function (n) {
      if (!n || !normalizeArchKind(n.kind)) return;
      ensureArchCommonAttrs(n);
      if (isArchUiLayerNode(n)) ensureUiLayerFields(n);
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
        archAttr("createdAt", n.createdAt || "") +
        archAttr("updatedAt", n.updatedAt || "") +
        archAttr(
          "contentHash",
          n.contentHash != null ? String(n.contentHash) : ""
        ) +
        archAttr("rootNodeId", n.rootNodeId || "") +
        archAttr(
          "width",
          n.width != null && n.width !== "" ? String(n.width) : ""
        ) +
        archAttr(
          "height",
          n.height != null && n.height !== "" ? String(n.height) : ""
        ) +
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
        archAttr("implementationRef", n.implementationRef || "") +
        archAttr("specVersion", n.specVersion || "") +
        archAttr(
          "innerX",
          n.innerX != null && n.innerX !== "" ? String(n.innerX) : ""
        ) +
        archAttr(
          "innerY",
          n.innerY != null && n.innerY !== "" ? String(n.innerY) : ""
        ) +
        archExtraKindAttrs(n) +
        ">\n";
      if (n.description) {
        xml +=
          "      <description>" +
          escapeXml(n.description) +
          "</description>\n";
      }
      const specObj = n.spec && typeof n.spec === "object" ? n.spec : {};
      const specKeys = Object.keys(specObj).filter(function (k) {
        return specObj[k] != null && String(specObj[k]) !== "";
      });
      if (specKeys.length) {
        xml += "      <specProps>\n";
        specKeys.forEach(function (k) {
          xml +=
            "        <prop" +
            archAttr("key", k) +
            ">" +
            escapeXml(specObj[k]) +
            "</prop>\n";
        });
        xml += "      </specProps>\n";
      }
      xml += "      <dependencies>\n";
      (n.dependencies || []).forEach(function (dep) {
        if (!dep) return;
        xml +=
          "        <dependency" +
          archAttr("target", dep.target || "") +
          archAttr("dependencyType", dep.dependencyType || "") +
          archAttr("required", dep.required ? "true" : "false") +
          " />\n";
      });
      xml += "      </dependencies>\n";
      xml += "      <bddSpecs>\n";
      (n.bddSpecs || []).forEach(function (spec) {
        xml += "        <bddSpec>" + escapeXml(spec) + "</bddSpec>\n";
      });
      xml += "      </bddSpecs>\n";
      xml += "      <tddSpecs>\n";
      (n.tddSpecs || []).forEach(function (spec) {
        xml += "        <tddSpec>" + escapeXml(spec) + "</tddSpec>\n";
      });
      xml += "      </tddSpecs>\n";
      if (isArchUiLayerNode(n)) {
        xml += "      <assetRefs>\n";
        (n.assetRefs || []).forEach(function (ref) {
          xml += "        <assetRef>" + escapeXml(ref) + "</assetRef>\n";
        });
        xml += "      </assetRefs>\n";
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
          archAttr("schemaRef", p.schemaRef || "") +
          archAttr("required", p.required ? "true" : "") +
          archAttr("cardinality", p.cardinality || "") +
          archAttr("constraints", p.constraints || "") +
          archAttr("defaultValue", p.defaultValue || "") +
          archAttr("errorTypeRefs", p.errorTypeRefs || "") +
          archAttr("description", p.description || "") +
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
          archAttr("schemaRef", p.schemaRef || "") +
          archAttr("required", p.required ? "true" : "") +
          archAttr("cardinality", p.cardinality || "") +
          archAttr("constraints", p.constraints || "") +
          archAttr("defaultValue", p.defaultValue || "") +
          archAttr("errorTypeRefs", p.errorTypeRefs || "") +
          archAttr("description", p.description || "") +
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
            archAttr("slotLetter", mod.slotLetter || "") +
            archAttr("name", mod.name || "") +
            archAttr("moduleId", mod.moduleId || "") +
            archAttr("order", String(mi)) +
            archAttr("collapsed", mod.collapsed ? "true" : "false") +
            archAttr("x", mod.x != null && mod.x !== "" ? String(mod.x) : "") +
            archAttr("y", mod.y != null && mod.y !== "" ? String(mod.y) : "") +
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
    xml += "</eluslotArch>\n";
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
    const rootName =
      docXml.documentElement && docXml.documentElement.localName
        ? String(docXml.documentElement.localName)
        : "";
    const root =
      rootName === "eluslotArch" || rootName === "sgenaxisArch"
        ? docXml.documentElement
        : docXml.querySelector("eluslotArch") ||
          docXml.querySelector("sgenaxisArch");
    if (!root) return null;
    const metaEl = root.querySelector("meta");
    const doc = blankArchDoc();
    doc.format = archXmlAttr(root, "format", "eluslot.esml");
    doc.formatVersion = Number(archXmlAttr(root, "formatVersion", "1")) || 1;
    doc.meta = {
      formSize: archXmlAttr(metaEl, "formSize", "1280x720"),
      gridSize: Number(archXmlAttr(metaEl, "gridSize", "8")),
      product_pass: archXmlAttr(metaEl, "product_pass", "false") === "true",
      encoding: "xml",
      viewports: {},
    };
    if (metaEl) {
      metaEl.querySelectorAll("viewports > viewport").forEach(function (vel) {
        const key = archXmlAttr(vel, "key", "");
        if (!key) return;
        doc.meta.viewports[key] = {
          zoom: Number(archXmlAttr(vel, "zoom", "1")) || 1,
          scrollLeft: Number(archXmlAttr(vel, "scrollLeft", "0")) || 0,
          scrollTop: Number(archXmlAttr(vel, "scrollTop", "0")) || 0,
        };
      });
    }
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
        createdAt: archXmlAttr(nel, "createdAt", ""),
        updatedAt: archXmlAttr(nel, "updatedAt", ""),
        contentHash: archXmlAttr(nel, "contentHash", ""),
        rootNodeId: archXmlAttr(nel, "rootNodeId", ""),
        width: (function () {
          const w = archXmlAttr(nel, "width", "");
          return w === "" ? "" : Number(w) || "";
        })(),
        height: (function () {
          const h = archXmlAttr(nel, "height", "");
          return h === "" ? "" : Number(h) || "";
        })(),
        dependencies: [],
        bddSpecs: [],
        tddSpecs: [],
        assetRefs: [],
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
        implementationRef: archXmlAttr(nel, "implementationRef", "") || "",
        specVersion: archXmlAttr(nel, "specVersion", "") || "",
        spec: {},
        inputs: [],
        outputs: [],
        memberIds: [],
      };
      const innerXRaw = archXmlAttr(nel, "innerX", "");
      const innerYRaw = archXmlAttr(nel, "innerY", "");
      if (innerXRaw !== "") node.innerX = Number(innerXRaw) || 0;
      if (innerYRaw !== "") node.innerY = Number(innerYRaw) || 0;
      nel.querySelectorAll("specProps > prop").forEach(function (pel) {
        const key = archXmlAttr(pel, "key", "");
        if (!key) return;
        node.spec[key] = (pel.textContent || "").trim();
      });
      nel.querySelectorAll("dependencies > dependency").forEach(function (del) {
        node.dependencies.push({
          target: archXmlAttr(del, "target", ""),
          dependencyType: archXmlAttr(del, "dependencyType", ""),
          required: archXmlAttr(del, "required", "false") === "true",
        });
      });
      nel.querySelectorAll("bddSpecs > bddSpec").forEach(function (sel) {
        const text = (sel.textContent || "").trim();
        if (text) node.bddSpecs.push(text);
      });
      nel.querySelectorAll("tddSpecs > tddSpec").forEach(function (sel) {
        const text = (sel.textContent || "").trim();
        if (text) node.tddSpecs.push(text);
      });
      nel.querySelectorAll("assetRefs > assetRef").forEach(function (ael) {
        const text = (ael.textContent || "").trim();
        if (text) node.assetRefs.push(text);
      });
      if (kind === "UI") ensureUiLayerFields(node);
      if (kind === "Deployment") ensureDeploymentFields(node);
      if (kind === "WorkItem") ensureWorkItemFields(node);
      if (ARCH_EXTRA_KIND_FIELDS[kind]) {
        ARCH_EXTRA_KIND_FIELDS[kind].forEach(function (key) {
          if (key === "contentHash") return;
          node[key] = archXmlAttr(nel, key, "") || "";
        });
        ensureArchExtraKindFields(node);
      }
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
          dataType: archXmlAttr(p, "dataType", ""),
          schemaRef: archXmlAttr(p, "schemaRef", ""),
          required: archXmlAttr(p, "required", "false") === "true",
          cardinality: archXmlAttr(p, "cardinality", ""),
          constraints: archXmlAttr(p, "constraints", ""),
          defaultValue: archXmlAttr(p, "defaultValue", ""),
          errorTypeRefs: archXmlAttr(p, "errorTypeRefs", ""),
          description: archXmlAttr(p, "description", ""),
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
          dataType: archXmlAttr(p, "dataType", ""),
          schemaRef: archXmlAttr(p, "schemaRef", ""),
          required: archXmlAttr(p, "required", "false") === "true",
          cardinality: archXmlAttr(p, "cardinality", ""),
          constraints: archXmlAttr(p, "constraints", ""),
          defaultValue: archXmlAttr(p, "defaultValue", ""),
          errorTypeRefs: archXmlAttr(p, "errorTypeRefs", ""),
          description: archXmlAttr(p, "description", ""),
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
          const modX = archXmlAttr(mel, "x", "");
          const modY = archXmlAttr(mel, "y", "");
          const mod = {
            slotId: archXmlAttr(mel, "slotId", id + "-slot-" + (node.modules.length + 1)),
            slotLetter: archXmlAttr(mel, "slotLetter", ""),
            name: archXmlAttr(mel, "name", "Module"),
            moduleId: archXmlAttr(mel, "moduleId", ""),
            collapsed: archXmlAttr(mel, "collapsed", "false") === "true",
            x: modX === "" ? null : Number(modX) || 0,
            y: modY === "" ? null : Number(modY) || 0,
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
        ensureLayerModules(node);
        /* packsKind 留空亦可；稍後由成員推導 */
      } else {
        delete node.memberIds;
        delete node.packsKind;
        delete node.modules;
      }
      ensureArchCommonAttrs(node);
      if (isArchUiLayerNode(node)) ensureUiLayerFields(node);
      doc.nodes.push(node);
    });
    syncArchAssignmentsFromModules(doc);
    ensureArchDocUuids(doc);
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
    ensureArchDocUuids(doc);
    doc.nodes.forEach(function (n) {
      if (!n) return;
      ensureArchCommonAttrs(n);
      if (n.kind === "Layer") ensureLayerModules(n);
      if (isArchUiLayerNode(n)) ensureUiLayerFields(n);
      if (n.kind === "WorkItem") ensureWorkItemFields(n);
    });
    if (!Array.isArray(doc.events)) doc.events = [];
    if (!doc.meta) doc.meta = {};
    doc.meta.encoding = "xml";
    if (!doc.meta.viewports || typeof doc.meta.viewports !== "object") {
      doc.meta.viewports = {};
    }
    archDoc = doc;
    hydrateArchViewportMemory(doc);
    doc.nodes.forEach(function (n) {
      if (n && n.kind === "Layer") {
        syncLayerIdentityFromMembers(n, doc.nodes, { quiet: true });
      }
    });
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
    recallArchViewport(archViewportKey());
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

  function blankArchPort(id, label) {
    return {
      id: id,
      label: label || "",
      dataType: "",
      schemaRef: "",
      required: false,
      cardinality: "",
      constraints: "",
      defaultValue: "",
      errorTypeRefs: "",
      description: "",
    };
  }

  function ensureArchPort(port, fallbackId, fallbackLabel) {
    const p =
      port && typeof port === "object"
        ? port
        : blankArchPort(fallbackId, fallbackLabel);
    if (!p.id) p.id = fallbackId || "";
    if (p.label == null || p.label === "") p.label = p.name || fallbackLabel || "";
    if (p.dataType == null) p.dataType = "";
    if (p.schemaRef == null) p.schemaRef = "";
    if (p.required == null || p.required === "") {
      p.required = false;
    } else if (typeof p.required === "string") {
      const req = p.required.toLowerCase();
      p.required = req === "true" || req === "1" || req === "yes";
    } else {
      p.required = !!p.required;
    }
    if (p.cardinality == null) p.cardinality = "";
    if (p.constraints == null) p.constraints = "";
    if (p.defaultValue == null) p.defaultValue = "";
    if (p.errorTypeRefs == null) p.errorTypeRefs = "";
    if (p.description == null) p.description = "";
    return p;
  }

  function defaultPortsForArchKind(kind, nodeId) {
    const io = ARCH_KIND_IO[kind] || ARCH_KIND_IO.Custom;
    return {
      inputs: [blankArchPort(nodeId + "-in", io.inLabel)],
      outputs: [blankArchPort(nodeId + "-out", io.outLabel)],
      role: io.role,
    };
  }

  function normalizeArchDependency(raw) {
    if (raw == null) return null;
    if (typeof raw === "string") {
      const line = raw.trim();
      if (!line) return null;
      const parts = line.split("|");
      raw = {
        target: parts[0] || "",
        dependencyType: parts[1] || "",
        required: parts[2] || "",
      };
    }
    if (typeof raw !== "object") return null;
    const req = raw.required;
    const dep = {
      target: raw.target != null ? String(raw.target).trim() : "",
      dependencyType:
        raw.dependencyType != null ? String(raw.dependencyType).trim() : "",
      required:
        req === true ||
        req === "true" ||
        req === "1" ||
        req === 1 ||
        req === "yes",
    };
    if (!dep.target && !dep.dependencyType && !dep.required) return null;
    return dep;
  }

  function parseArchLineList(text) {
    return String(text || "")
      .split(/\r?\n/)
      .map(function (line) {
        return line.trim();
      })
      .filter(function (line) {
        return !!line;
      });
  }

  function formatArchDependencyLines(list) {
    return (list || [])
      .map(function (dep) {
        if (!dep) return "";
        return (
          (dep.target || "") +
          "|" +
          (dep.dependencyType || "") +
          "|" +
          (dep.required ? "true" : "false")
        );
      })
      .filter(function (line) {
        return !!line;
      })
      .join("\n");
  }

  function formatArchPortLine(p) {
    const port = p || {};
    return [
      port.label || "",
      port.dataType || "",
      port.schemaRef || "",
      port.required ? "true" : "false",
      port.cardinality || "",
      port.constraints || "",
      port.defaultValue || "",
      port.errorTypeRefs || "",
      port.description || "",
    ].join("|");
  }

  function applyArchPortLine(port, line) {
    const parts = String(line || "").split("|");
    function at(i) {
      return parts[i] != null ? String(parts[i]).trim() : "";
    }
    port.label = at(0);
    port.name = port.label || port.name || "";
    port.dataType = at(1);
    port.schemaRef = at(2);
    const req = at(3).toLowerCase();
    port.required = req === "true" || req === "1" || req === "yes";
    port.cardinality = at(4);
    port.constraints = at(5);
    port.defaultValue = at(6);
    port.errorTypeRefs = at(7);
    port.description = at(8);
    return port;
  }

  function archExplicitNodeSize(n) {
    function num(v) {
      if (v == null || String(v).trim() === "") return null;
      const x = Number(v);
      if (!Number.isFinite(x) || x <= 0) return null;
      return x;
    }
    return {
      w: num(n && n.width),
      h: num(n && n.height),
    };
  }

  /**
   * 架構節點共用屬性。
   * opts.fresh：新建節點才寫 createdAt＝現在。
   * 既有節點缺 createdAt 時不用「現在」覆蓋舊時間；空值只補一次並保持。
   */
  function ensureArchCommonAttrs(node, opts) {
    if (!node) return node;
    const fresh = !!(opts && opts.fresh);
    if (fresh) {
      if (node.createdAt == null || String(node.createdAt).trim() === "") {
        node.createdAt = new Date().toISOString();
      }
    } else if (node.createdAt == null) {
      node.createdAt = "";
    }
    if (node.updatedAt == null) node.updatedAt = "";
    if (node.contentHash == null) node.contentHash = "";
    if (!node.schemaVersion) node.schemaVersion = "1";
    if (!Array.isArray(node.dependencies)) node.dependencies = [];
    node.dependencies = node.dependencies
      .map(function (dep) {
        return normalizeArchDependency(dep);
      })
      .filter(function (dep) {
        return !!dep;
      });
    if (!Array.isArray(node.bddSpecs)) node.bddSpecs = [];
    node.bddSpecs = node.bddSpecs
      .map(function (s) {
        return s == null ? "" : String(s).trim();
      })
      .filter(function (s) {
        return !!s;
      });
    if (!Array.isArray(node.tddSpecs)) node.tddSpecs = [];
    node.tddSpecs = node.tddSpecs
      .map(function (s) {
        return s == null ? "" : String(s).trim();
      })
      .filter(function (s) {
        return !!s;
      });
    (node.inputs || []).forEach(function (p, i) {
      ensureArchPort(p, (node.id || "n") + "-in-" + i, "in");
    });
    (node.outputs || []).forEach(function (p, i) {
      ensureArchPort(p, (node.id || "n") + "-out-" + i, "out");
    });
    if (node.width == null) node.width = "";
    if (node.height == null) node.height = "";
    return node;
  }

  function touchArchNodeUpdatedAt(node) {
    if (!node) return;
    node.updatedAt = new Date().toISOString();
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
      if (!archDoc.meta.viewports || typeof archDoc.meta.viewports !== "object") {
        archDoc.meta.viewports = {};
      }
      rememberArchViewport(archViewportKey());
      ensureArchDocUuids(archDoc);
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
      toast("拒絕：無法解析架構 XML（需 <eluslotArch>）");
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
      ensureArchCommonAttrs(node, { fresh: true });
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
    syncArchZoomBox();
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
    const z = archZoom || 1;
    const hSpan = Math.max(rw + pad, 100);
    const vSpan = Math.max(rh + pad, 100);
    hEl.style.width = Math.ceil(hSpan * z) + "px";
    vEl.style.height = Math.ceil(vSpan * z) + "px";
    hEl.innerHTML = "";
    vEl.innerHTML = "";
    const major = 50;
    const minor = 10;
    const step = hSpan > 8000 || vSpan > 8000 ? major : minor;
    for (let x = 0; x <= hSpan; x += step) {
      const tick = document.createElement("span");
      tick.className =
        "designer-ruler-tick" + (x % major === 0 ? " is-major" : "");
      tick.style.left = x * z + "px";
      hEl.appendChild(tick);
      if (x % major === 0) {
        const lab = document.createElement("span");
        lab.className = "designer-ruler-label";
        lab.style.left = x * z + "px";
        lab.textContent = String(x);
        hEl.appendChild(lab);
      }
    }
    for (let y = 0; y <= vSpan; y += step) {
      const tick = document.createElement("span");
      tick.className =
        "designer-ruler-tick" + (y % major === 0 ? " is-major" : "");
      tick.style.top = y * z + "px";
      vEl.appendChild(tick);
      if (y % major === 0 && y > 0) {
        const lab = document.createElement("span");
        lab.className = "designer-ruler-label";
        lab.style.top = y * z + "px";
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
    if (k === "CodeFile") return "Code File";
    if (k === "AITask") return "AI Task";
    return k;
  }

  function isArchUiLayerNode(node) {
    if (!node) return false;
    if (normalizeArchKind(node.kind) === "UI") return true;
    return (
      node.kind === "Layer" && normalizeArchKind(node.packsKind) === "UI"
    );
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
    const evt = {
      eventId: newArchUuid(),
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

  function isArchExtraKindNode(node) {
    return !!(
      node && ARCH_EXTRA_KIND_FIELDS[normalizeArchKind(node.kind)]
    );
  }

  function ensureArchExtraKindFields(node) {
    if (!isArchExtraKindNode(node)) return node;
    const keys = ARCH_EXTRA_KIND_FIELDS[node.kind];
    keys.forEach(function (key) {
      if (node[key] == null) node[key] = "";
    });
    return node;
  }

  function renderArchExtraKindPanel(node) {
    const panel = document.getElementById("archExtraKindPanel");
    const host = document.getElementById("archExtraKindFields");
    const title = document.getElementById("archExtraKindTitle");
    if (!panel || !host) return;
    const show = isArchExtraKindNode(node);
    panel.hidden = !show;
    if (!show) {
      host.innerHTML = "";
      return;
    }
    ensureArchExtraKindFields(node);
    if (title) title.textContent = formatArchNodeType(node.kind, node);
    host.innerHTML = "";
    ARCH_EXTRA_KIND_FIELDS[node.kind].forEach(function (key) {
      const label = document.createElement("label");
      label.className = "designer-row";
      label.appendChild(document.createTextNode(key));
      const input = document.createElement("input");
      input.type = "text";
      input.setAttribute("data-arch-extra-key", key);
      input.setAttribute("aria-label", key);
      input.value = node[key] == null ? "" : String(node[key]);
      input.addEventListener("change", applyArchInspectorInputs);
      label.appendChild(input);
      host.appendChild(label);
    });
  }

  function readArchExtraKindPanel(node) {
    if (!isArchExtraKindNode(node)) return;
    ensureArchExtraKindFields(node);
    document
      .querySelectorAll("#archExtraKindFields [data-arch-extra-key]")
      .forEach(function (el) {
        const key = el.getAttribute("data-arch-extra-key") || "";
        if (!key || ARCH_EXTRA_KIND_FIELDS[node.kind].indexOf(key) < 0) return;
        if (key === "contentHash") {
          const common = document.getElementById("archNodeContentHash");
          if (common && document.activeElement === common) return;
        }
        node[key] = el.value;
        if (key === "contentHash") {
          const common = document.getElementById("archNodeContentHash");
          if (common && document.activeElement !== common) common.value = el.value;
        }
      });
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
    if (node.rootNodeId == null) node.rootNodeId = "";
    if (!Array.isArray(node.assetRefs)) node.assetRefs = [];
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
    dismissAppSplash({ caption: "Ready" });
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
      renderUiBhvPalette();
      ensureUiWidgetPaletteVisible();
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
    const title = viewer ? "EluSlot — UI 預覽" : "EluSlot — UI 編輯";
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
    const packs = node && normalizeArchKind(node.packsKind);
    if (packs) return "Layer." + packs;
    return "Layer（由子物件定義）";
  }

  /** Layer 類別由子物件推導：空＝未定；有成員＝取首個子物件 kind（同質）。 */
  function syncLayerIdentityFromMembers(layer, nodesOpt, opts) {
    if (!layer || layer.kind !== "Layer") return;
    const nodes =
      nodesOpt ||
      (archDoc && Array.isArray(archDoc.nodes) ? archDoc.nodes : []);
    function lookup(id) {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i] && nodes[i].id === id) return nodes[i];
      }
      return null;
    }
    const members = layerAllMemberIds(layer)
      .map(lookup)
      .filter(function (n) {
        return n && normalizeArchKind(n.kind);
      });
    if (!members.length) {
      layer.packsKind = null;
      layer.role = "Pack unset";
      if (
        !layer.name ||
        layer.name === "Layer" ||
        /^Layer(\.| · )/.test(String(layer.name))
      ) {
        layer.name = "Layer";
      }
      return;
    }
    const prevPacks = normalizeArchKind(layer.packsKind);
    const packs = normalizeArchKind(members[0].kind);
    layer.packsKind = packs;
    layer.role = "Pack " + packs;
    if (
      packs === "UI" &&
      prevPacks !== "UI" &&
      !(opts && opts.quiet)
    ) {
      openArchUiLayer("editor", layer.id);
    }
    if (
      !layer.name ||
      layer.name === "Layer" ||
      /^Layer(\.| · )/.test(String(layer.name))
    ) {
      layer.name = "Layer." + packs;
    }
  }

  function blankModuleSlot(layer, index) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const letter = letters[(index || 0) % 26];
    return {
      slotId: newArchUuid(),
      slotLetter: letter,
      name: "Module",
      moduleId: newArchUuid(),
      moduleRef: null,
      collapsed: false,
      x: null,
      y: null,
      memberIds: [],
    };
  }

  /** 顯示：slot A : Module name（moduleId 不變；name 是模組名）。 */
  function formatModuleSlotLabel(mod, index) {
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    const letter =
      (mod && mod.slotLetter) || letters[(index || 0) % 26] || "A";
    const raw = mod && mod.name != null ? String(mod.name).trim() : "";
    const legacy = raw.match(/^Module Slot ([A-Z])$/);
    const name = !raw || legacy ? "Module" : raw;
    return "slot " + (legacy ? legacy[1] : letter) + " : " + name;
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
      slot.memberIds = layer.memberIds.slice();
      layer.modules.push(slot);
      layer.memberIds = [];
    }
    if (!layer.modules.length) {
      layer.modules.push(blankModuleSlot(layer, 0));
    }
    const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    layer.modules.forEach(function (m, mi) {
      if (!Array.isArray(m.memberIds)) m.memberIds = [];
      if (!m.moduleId) m.moduleId = m.slotId || layer.id + "-mod";
      const legacy = String(m.name || "").match(/^Module Slot ([A-Z])$/);
      if (!m.slotLetter) {
        m.slotLetter = legacy ? legacy[1] : letters[mi % 26];
      }
      if (!m.name || legacy) m.name = "Module";
    });
    layer.memberIds = [];
    return layer.modules;
  }

  function currentArchFocusLayer() {
    const id = archLayerStack.length
      ? archLayerStack[archLayerStack.length - 1]
      : null;
    const n = id ? findArchNode(id) : null;
    if (!n || n.kind !== "Layer") return null;
    return n;
  }

  function pruneArchLayerStack() {
    archLayerStack = (archLayerStack || []).filter(function (id) {
      const n = findArchNode(id);
      return !!(n && n.kind === "Layer");
    });
  }

  function syncArchLayerNav() {
    const bar = document.getElementById("arch-layer-nav");
    const crumb = document.getElementById("arch-layer-crumb");
    const fab = document.getElementById("arch-layer-back-fab");
    const layer = currentArchFocusLayer();
    if (bar) bar.hidden = !layer;
    if (fab) fab.hidden = !layer;
    if (!crumb) return;
    if (!layer) {
      crumb.textContent = "";
      return;
    }
    const parts = ["Root"];
    archLayerStack.forEach(function (id) {
      const n = findArchNode(id);
      parts.push(n ? n.name || n.id : id);
    });
    crumb.textContent = parts.join(" / ");
  }

  function snapInteriorCoord(v) {
    const gpx = archGridPx > 0 ? archGridPx : 0;
    let n = Number(v) || 0;
    if (gpx) n = Math.round(n / gpx) * gpx;
    return Math.max(0, n);
  }

  function archDisplayedOrigin(node) {
    const focus = currentArchFocusLayer();
    const parent = node && node.kind !== "Layer" ? findArchLayerContaining(node.id) : null;
    if (focus && parent && parent.id === focus.id) {
      return {
        x: Number(node.innerX) || 0,
        y: Number(node.innerY) || 0,
      };
    }
    return {
      x: Number(node && node.x) || 0,
      y: Number(node && node.y) || 0,
    };
  }

  function ensureInteriorLayout(layer) {
    if (!layer || layer.kind !== "Layer") return;
    ensureLayerModules(layer).forEach(function (mod, i) {
      if (mod.x == null || mod.x === "") mod.x = 40;
      if (mod.y == null || mod.y === "") mod.y = 40 + i * 188;
      sortedModuleMemberIds(mod).forEach(function (mid, oi) {
        const n = findArchNode(mid);
        if (!n) return;
        if (n.innerX == null || n.innerX === "") {
          n.innerX = (Number(mod.x) || 40) + 240 + oi * 200;
        }
        if (n.innerY == null || n.innerY === "") {
          n.innerY = (Number(mod.y) || 40) + 16;
        }
      });
    });
  }

  function enterArchLayer(layerId) {
    const layer = findArchNode(layerId);
    if (!layer || layer.kind !== "Layer") {
      toast("請選取 Layer 再進入內層");
      return;
    }
    if (isArchUiLayerNode(layer)) {
      openArchUiLayer("editor", layer.id);
      return;
    }
    ensureInteriorLayout(layer);
    rememberArchViewport(archViewportKey());
    if (archLayerStack[archLayerStack.length - 1] !== layer.id) {
      archLayerStack.push(layer.id);
    }
    archSelectedModuleSlotId = null;
    recallArchViewport(layer.id);
    renderArchDag();
    recallArchViewport(layer.id);
    setStatus(
      "Layer 內層 · " +
        (layer.name || layer.id) +
        " · 返回上一層可回到外層"
    );
  }

  function leaveArchLayer() {
    if (!archLayerStack.length) return;
    rememberArchViewport(archViewportKey());
    const leftId = archLayerStack.pop();
    archSelectedModuleSlotId = null;
    recallArchViewport(archViewportKey());
    renderArchDag();
    recallArchViewport(archViewportKey());
    if (findArchNode(leftId)) selectArchNode(leftId);
    setStatus(archLayerStack.length ? "已返回上一層" : "已返回 Root");
  }

  function archViewportKey() {
    const layer = currentArchFocusLayer();
    return layer ? layer.id : "root";
  }

  /** 記下目前節點工作視窗的中鍵平移位置，並寫入 meta.viewports。 */
  function rememberArchViewport(key) {
    const shell = document.getElementById("arch-canvas-shell");
    if (!shell || !key) return;
    const view = {
      scrollLeft: shell.scrollLeft || 0,
      scrollTop: shell.scrollTop || 0,
      zoom: archZoom || 1,
    };
    archViewportMemory[key] = view;
    if (!archDoc.meta) archDoc.meta = {};
    if (!archDoc.meta.viewports || typeof archDoc.meta.viewports !== "object") {
      archDoc.meta.viewports = {};
    }
    archDoc.meta.viewports[key] = {
      zoom: view.zoom,
      scrollLeft: view.scrollLeft,
      scrollTop: view.scrollTop,
    };
  }

  /** 載入 XML 後把 meta.viewports 接上當次畫面的 archViewportMemory。 */
  function hydrateArchViewportMemory(doc) {
    Object.keys(archViewportMemory).forEach(function (k) {
      delete archViewportMemory[k];
    });
    const views = doc && doc.meta && doc.meta.viewports;
    if (!views || typeof views !== "object") return;
    Object.keys(views).forEach(function (k) {
      const v = views[k];
      if (!v || typeof v !== "object") return;
      archViewportMemory[k] = {
        zoom: Number(v.zoom) || 1,
        scrollLeft: Number(v.scrollLeft) || 0,
        scrollTop: Number(v.scrollTop) || 0,
      };
    });
  }

  /** 還原該層的平移位置；第一次進入則回到原點。 */
  function recallArchViewport(key) {
    const shell = document.getElementById("arch-canvas-shell");
    if (!shell) return;
    const view = key ? archViewportMemory[key] : null;
    const zoom = view ? view.zoom || 1 : 1;
    archZoom = Math.max(0.4, Math.min(2, zoom));
    syncArchZoomBox();
    const size = archStageSize();
    renderArchRulers(size.w, size.h);
    shell.scrollLeft = view ? view.scrollLeft || 0 : 0;
    shell.scrollTop = view ? view.scrollTop || 0 : 0;
  }

  function selectArchModuleSlot(layer, slotId) {
    if (!layer || !slotId) return;
    setArchSelection([], null);
    archSelectedModuleSlotId = slotId;
    refreshArchSelectionChrome();
    const mod = ensureLayerModules(layer).find(function (m) {
      return m.slotId === slotId;
    });
    if (mod) fillArchModuleSlotInspector(layer, mod);
  }

  function fillArchModuleSlotInspector(layer, mod) {
    if (!layer || !mod) return;
    setArchInspectorActive(true);
    const nameEl = document.getElementById("archNodeName");
    if (nameEl) nameEl.value = mod.name || "Module";
    const typeLabel = document.getElementById("archNodeTypeLabel");
    if (typeLabel) typeLabel.textContent = "";
    const typeEl = document.getElementById("archNodeType");
    if (typeEl) typeEl.value = "Module Slot";
    const idEl = document.getElementById("archNodeId");
    if (idEl) idEl.value = mod.moduleId || mod.slotId || "";
    const descEl = document.getElementById("archNodeDesc");
    if (descEl) descEl.value = "";
    const hint = document.getElementById("archNodeHint");
    if (hint) {
      hint.textContent =
        formatModuleSlotLabel(mod) +
        " · 點選子節點可看規劃書屬性 · 可匯入程式檔";
    }
    const packsRow = document.getElementById("archLayerPacksRow");
    if (packsRow) packsRow.hidden = true;
    ["archUiLayerPanel", "archWorkItemPanel", "archDeploymentPanel", "archExtraKindPanel"].forEach(
      function (id) {
        const el = document.getElementById(id);
        if (el) el.hidden = true;
      }
    );
    const membersEl = document.getElementById("archLayerMembers");
    if (membersEl) membersEl.hidden = true;
    renderArchSpecPanel(null);
    clearArchCommonInspector();
  }

  function ensureNodeSpec(node) {
    if (!node) return node;
    if (!node.spec || typeof node.spec !== "object") node.spec = {};
    if (node.implementationRef == null) node.implementationRef = "";
    if (!node.specVersion) node.specVersion = "1";
    return node;
  }

  function specFieldRow(key, label, value, readonly) {
    return (
      '<label class="designer-row">' +
      escapeHtml(label) +
      '<input data-spec-input="1" data-spec-key="' +
      escapeHtml(key) +
      '" type="text" value="' +
      escapeHtml(value == null ? "" : String(value)) +
      '"' +
      (readonly ? " readonly" : "") +
      " /></label>"
    );
  }

  function renderArchSpecPanel(node) {
    const host = document.getElementById("archSpecPanel");
    if (!host) return;
    if (!node) {
      host.innerHTML =
        '<p class="hint">點選 Layer 內的子節點可看規劃書屬性，或匯入程式檔成為子節點。</p>';
      return;
    }
    if (node.kind === "Layer") {
      host.innerHTML =
        '<p class="hint">按 Edit 打開 Layer 內層。點選子節點可編輯規劃書屬性（Node Architecture Specification）。</p>';
      return;
    }
    ensureNodeSpec(node);
    const fields = ARCH_SPEC_FIELDS[node.kind] || [];
    let html =
      "<b>規劃書屬性</b>" +
      specFieldRow(
        "implementationRef",
        "implementationRef",
        node.implementationRef,
        false
      ) +
      specFieldRow("specVersion", "specVersion", node.specVersion, false) +
      specFieldRow(
        "validationStatus",
        "validationStatus",
        node.validationStatus || "unchecked",
        true
      );
    if (!fields.length) {
      html +=
        '<p class="hint">此類型的專屬欄位在 Basic；上面是規劃書共用欄位。</p>';
    } else {
      html += "<b>Type Properties</b>";
      fields.forEach(function (pair) {
        html += specFieldRow(
          "spec:" + pair[0],
          pair[1],
          node.spec[pair[0]] || "",
          false
        );
      });
    }
    host.innerHTML = html;
    host.querySelectorAll("[data-spec-input]").forEach(function (el) {
      el.addEventListener("change", function () {
        if (!archEditMode) {
          toast("請先開「編輯草稿」");
          const cur = findArchNode(archSelectedId);
          if (cur) renderArchSpecPanel(cur);
          return;
        }
        applyArchInspectorInputs();
      });
    });
  }

  function programFileIdentity(file, usedNames) {
    const rel = String(
      (file && (file.webkitRelativePath || file.name)) || "program"
    );
    const parts = rel.split(/[/\\]/).filter(Boolean);
    const filename = parts.length ? parts[parts.length - 1] : "program";
    const base = filename.replace(/\.[^.]+$/, "") || "program";
    const parent = parts.length > 1 ? parts[parts.length - 2] : "";
    let name = base;
    if (usedNames[name]) {
      name = parent ? base + " (" + parent + ")" : base + " 2";
      let n = 2;
      while (usedNames[name]) {
        name = parent
          ? base + " (" + parent + " " + n + ")"
          : base + " " + n;
        n += 1;
      }
    }
    usedNames[name] = true;
    return { name: name, ref: rel };
  }

  /** 匯入一個程式檔到目前 Layer。成功回傳節點 id；quiet 時不寫檔、不重繪。 */
  function importArchProgramFile(file, opts) {
    const quiet = !!(opts && opts.quiet);
    const usedNames = (opts && opts.usedNames) || Object.create(null);
    const layer = currentArchFocusLayer();
    if (!layer) {
      if (!quiet) toast("請先進入 Layer 內層再匯入程式");
      return null;
    }
    if (!archEditMode) {
      if (!quiet) toast("請先開「編輯草稿」");
      return null;
    }
    const packs = normalizeArchKind(layer.packsKind);
    const kind = packs || "Custom";
    if (ARCH_PACKABLE_KINDS.indexOf(kind) < 0) {
      if (!quiet) toast("此 Layer 不可再加入子節點");
      return null;
    }
    const mods = ensureLayerModules(layer);
    let mod = null;
    if (archSelectedModuleSlotId) {
      mod = mods.find(function (m) {
        return m.slotId === archSelectedModuleSlotId;
      });
    }
    if (!mod) mod = mods[0];
    const rel = String(
      (file && (file.webkitRelativePath || file.name)) || ""
    );
    const existing = (mod.memberIds || []).some(function (mid) {
      const n = findArchNode(mid);
      return n && rel && n.implementationRef === rel;
    });
    if (existing) {
      if (opts) opts.lastSkip = "dup";
      return null;
    }
    const ident = programFileIdentity(file, usedNames);
    const id = newArchUuid();
    const ports = defaultPortsForArchKind(kind, id);
    const order = (mod.memberIds || []).length;
    const col = order % 6;
    const row = (order / 6) | 0;
    const node = {
      id: id,
      name: ident.name,
      kind: kind,
      x: (Number(layer.x) || 0) + 24,
      y: (Number(layer.y) || 0) + 48 + (order % 4) * 28,
      innerX: (Number(mod.x) || 40) + 240 + col * 200,
      innerY: (Number(mod.y) || 40) + 16 + row * 140,
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
      implementationRef: ident.ref,
      specVersion: "1",
      spec: {},
    };
    ensureArchCommonAttrs(node, { fresh: true });
    if (isArchUiLayerNode(node)) ensureUiLayerFields(node);
    archDoc.nodes.push(node);
    if (!packNodeIntoModule(node, layer, mod, { quiet: true })) {
      archDoc.nodes = archDoc.nodes.filter(function (n) {
        return n.id !== id;
      });
      delete usedNames[ident.name];
      if (opts) opts.lastSkip = "reject";
      if (!quiet) toast("無法匯入：Layer 只收 " + (layer.packsKind || kind));
      return null;
    }
    if (!quiet) {
      persistArchDraft();
      renderArchDag();
      selectArchNode(id);
      setArchInspectorTab("spec");
      toast(
        "已匯入程式為子節點 " +
          ident.name +
          "（" +
          kind +
          " · " +
          formatModuleSlotLabel(mod) +
          "）"
      );
    }
    return id;
  }

  /** 批量匯入：選取的檔案，或資料夾內含子目錄的全部檔案。 */
  function importArchProgramFiles(files) {
    const layer = currentArchFocusLayer();
    if (!layer) {
      toast("請先進入 Layer 內層再匯入程式");
      return;
    }
    if (!archEditMode) {
      toast("請先開「編輯草稿」");
      return;
    }
    const list = [];
    const src = files || [];
    for (let i = 0; i < src.length; i++) {
      if (src[i] && src[i].name) list.push(src[i]);
    }
    if (!list.length) {
      toast("沒有可匯入的檔案");
      return;
    }
    const usedNames = Object.create(null);
    (ensureLayerModules(layer) || []).forEach(function (mod) {
      (mod.memberIds || []).forEach(function (mid) {
        const n = findArchNode(mid);
        if (n && n.name) usedNames[n.name] = true;
      });
    });
    let added = 0;
    let skipped = 0;
    let rejected = 0;
    let lastId = null;
    list.forEach(function (file) {
      const bag = { quiet: true, usedNames: usedNames, lastSkip: "" };
      const id = importArchProgramFile(file, bag);
      if (id) {
        added += 1;
        lastId = id;
      } else if (bag.lastSkip === "dup") {
        skipped += 1;
      } else {
        rejected += 1;
      }
    });
    if (!added) {
      toast(
        skipped && !rejected
          ? "這些檔案已在此 Layer，未再匯入"
          : "無法匯入：Layer 只收同一類別的程式檔"
      );
      return;
    }
    persistArchDraft();
    renderArchDag();
    selectArchNode(lastId);
    setArchInspectorTab("spec");
    const extra = [];
    if (skipped) extra.push("略過 " + skipped);
    if (rejected) extra.push("不符 " + rejected);
    toast(
      "已匯入 " +
        added +
        " 個程式為子節點" +
        (extra.length ? "（" + extra.join("，") + "）" : "")
    );
  }

  function appendArchInteriorSlotNodes(host, layer) {
    if (!host || !layer) return;
    ensureLayerModules(layer).forEach(function (mod, index) {
      const el = document.createElement("div");
      const selected = archSelectedModuleSlotId === mod.slotId;
      el.className = "arch-node is-module-slot" + (selected ? " is-selected" : "");
      el.setAttribute("data-slot-id", mod.slotId);
      el.setAttribute("data-layer-id", layer.id);
      el.setAttribute("data-kind", "ModuleSlot");
      el.style.left = (Number(mod.x) || 0) + "px";
      el.style.top = (Number(mod.y) || 0) + "px";
      const count = (mod.memberIds || []).length;
      el.innerHTML =
        '<div class="arch-node-head"><div class="arch-node-body"><strong>' +
        escapeHtml(formatModuleSlotLabel(mod, index)) +
        '</strong><span class="arch-node-kind">Module Slot</span><em>' +
        escapeHtml(String(count)) +
        " Nodes</em></div></div>";
      el.addEventListener("pointerdown", function (ev) {
        if (ev.button !== 0) return;
        ev.stopPropagation();
        selectArchModuleSlot(layer, mod.slotId);
        if (!archEditMode) return;
        ev.preventDefault();
        archInteriorDrag = {
          kind: "slot",
          id: mod.slotId,
          startX: ev.clientX,
          startY: ev.clientY,
          ox: Number(mod.x) || 0,
          oy: Number(mod.y) || 0,
          moved: false,
        };
        document.body.classList.add("is-arch-dragging");
        try {
          el.setPointerCapture(ev.pointerId);
        } catch (_e) {
          /* ignore */
        }
      });
      host.appendChild(el);
    });
  }

  function boxSideAnchor(selector, side) {
    const el = document.querySelector(selector);
    const stage = document.getElementById("archStage");
    if (!el || !stage) return null;
    const sr = stage.getBoundingClientRect();
    const r = el.getBoundingClientRect();
    const zx = archZoom || 1;
    return {
      x: ((side === "out" ? r.right : r.left) - sr.left) / zx,
      y: (r.top + r.height / 2 - sr.top) / zx,
    };
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
    if (findArchLayerContaining(node.id)) return false;
    const nk = normalizeArchKind(node.kind);
    if (!nk || ARCH_PACKABLE_KINDS.indexOf(nk) < 0) return false;
    const packs = normalizeArchKind(layer.packsKind);
    /* 空 Layer：第一個子物件定義類別；已定類別則必須同質 */
    if (!packs) return true;
    return nk === packs;
  }

  function packNodeIntoModule(node, layer, mod, opts) {
    if (!canPackNodeIntoLayer(node, layer) || !mod) return false;
    ensureLayerModules(layer);
    if ((mod.memberIds || []).indexOf(node.id) >= 0) {
      assignNodeToModule(node, layer, mod);
      syncLayerIdentityFromMembers(layer);
      return true;
    }
    mod.memberIds.push(node.id);
    assignNodeToModule(node, layer, mod);
    syncLayerIdentityFromMembers(layer);
    if (!(opts && opts.quiet)) {
      toast(
        "已移入 " +
          formatModuleSlotLabel(mod) +
          " → " +
          formatArchLayerPacks(layer)
      );
    }
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
      if (!canAcceptNodeInLayer(node, targetLayer)) {
        return false;
      }
      const fromLayer = hit.layer;
      ensureLayerModules(fromLayer).forEach(function (m) {
        m.memberIds = (m.memberIds || []).filter(function (id) {
          return id !== nodeId;
        });
      });
      delete node.packedIn;
      delete node.packedSlotId;
      const ok = packNodeIntoModule(
        node,
        targetLayer,
        resolveModuleSlot(targetLayer, preferredSlotId)
      );
      syncLayerIdentityFromMembers(fromLayer);
      return ok;
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
    syncLayerIdentityFromMembers(targetLayer);
    toast("已移至 " + formatModuleSlotLabel(mod));
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
    syncLayerIdentityFromMembers(L);
    const n = layerAllMemberIds(L).length;
    node.x = (Number(L.x) || 0) + 24;
    node.y = (Number(L.y) || 0) + 48 + (n % 4) * 28;
    toast("已取出 → Root（離開父層）");
    return true;
  }

  function archUnparentSelected() {
    const ids = getArchSelectedIds();
    let n = 0;
    ids.forEach(function (id) {
      const hit = findArchModuleContaining(id);
      if (hit && unpackNodeFromLayer(id, hit.layer)) n += 1;
    });
    if (!n) {
      toast("選取中沒有可 Unparent 的子節點");
      return false;
    }
    persistArchDraft();
    renderArchDag();
    setArchSelection(ids.filter(function (id) {
      return !!findArchNode(id);
    }), archSelectedId);
    return true;
  }

  function archParentSelectedToLast() {
    const ids = getArchSelectedIds();
    const parentId = archSelectedId;
    const parent = findArchNode(parentId);
    if (!parent || parent.kind !== "Layer") {
      toast("Parent：最後選取須為 Layer（父層）");
      return false;
    }
    let n = 0;
    ids.forEach(function (id) {
      if (id === parentId) return;
      const node = findArchNode(id);
      if (!node || node.kind === "Layer") return;
      if (!canAcceptNodeInLayer(node, parent)) {
        toast(
          "略過 " +
            (node.name || id) +
            "：Layer 只收 " +
            (parent.packsKind || "?")
        );
        return;
      }
      if (findArchLayerContaining(id)) {
        if (movePackedNodeToSlot(id, parent, null)) n += 1;
      } else if (packNodeIntoLayer(node, parent, null)) {
        n += 1;
      }
    });
    if (!n) {
      toast("沒有節點可 Parent 到選取 Layer");
      return false;
    }
    archUnassignedTreeOpen["layer:" + parent.id] = true;
    persistArchDraft();
    renderArchDag();
    setArchSelection(ids.filter(function (id) {
      return !!findArchNode(id);
    }), parentId);
    toast("已 Parent → " + (parent.name || parent.id) + "（" + n + "）");
    return true;
  }

  function archAddSelectionToNewLayer() {
    const ids = getArchSelectedIds().filter(function (id) {
      const n = findArchNode(id);
      return n && n.kind !== "Layer";
    });
    if (!ids.length) {
      toast("Add to Layer：請先選取可打包的節點");
      return false;
    }
    const kinds = [];
    const seen = {};
    ids.forEach(function (id) {
      const n = findArchNode(id);
      const k = n && normalizeArchKind(n.kind);
      if (k && !seen[k]) {
        seen[k] = true;
        kinds.push(k);
      }
    });
    if (kinds.length !== 1) {
      toast("Add to Layer：選取須為同一 Node Type（子物件定義 Layer 類別）");
      return false;
    }
    const packs = kinds[0];
    if (ARCH_PACKABLE_KINDS.indexOf(packs) < 0) {
      toast("Add to Layer：此類型不可打包進 Layer（" + packs + "）");
      return false;
    }
    if (!archEditMode) setArchEditMode(true);
    const layerId = newArchUuid();
    const ports = defaultPortsForArchKind("Layer", layerId);
    const layer = {
      id: layerId,
      name: "Layer",
      kind: "Layer",
      x: 80 + (Math.random() * 120) | 0,
      y: 80 + (Math.random() * 100) | 0,
      collapsed: false,
      inputs: ports.inputs,
      outputs: ports.outputs,
      role: "Pack unset",
      status: "未驗證",
      projectionLayer: null,
      description: "",
      layerRef: null,
      moduleRef: null,
      layoutOrder: null,
      packsKind: null,
      memberIds: [],
      modules: [],
    };
    ensureLayerModules(layer);
    ensureArchCommonAttrs(layer, { fresh: true });
    archDoc.nodes.push(layer);
    let packed = 0;
    ids.forEach(function (id) {
      const node = findArchNode(id);
      if (!node) return;
      if (findArchLayerContaining(id)) {
        if (movePackedNodeToSlot(id, layer, null)) packed += 1;
      } else if (packNodeIntoLayer(node, layer, null)) {
        packed += 1;
      }
    });
    syncLayerIdentityFromMembers(layer);
    archUnassignedTreeOpen["layer:" + layer.id] = true;
    persistArchDraft();
    renderArchDag();
    setArchSelection([layer.id].concat(ids), layer.id);
    toast(
      "已新增 " +
        formatArchLayerPacks(layer) +
        " 並收納 " +
        packed +
        " 個節點"
    );
    return true;
  }

  function addModuleSlotToLayer(layer) {
    if (!layer || layer.kind !== "Layer") return null;
    const mods = ensureLayerModules(layer);
    const slot = blankModuleSlot(layer, mods.length);
    mods.push(slot);
    persistArchDraft();
    renderArchDag();
    if (
      currentArchFocusLayer() &&
      currentArchFocusLayer().id === layer.id
    ) {
      selectArchModuleSlot(layer, slot.slotId);
    } else {
      selectArchNode(layer.id);
    }
    toast("已新增 " + formatModuleSlotLabel(slot));
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

  function renderArchCommonInspector(node) {
    if (!node) return;
    ensureArchCommonAttrs(node);
    const setVal = function (id, v) {
      const el = document.getElementById(id);
      if (el) el.value = v == null ? "" : String(v);
    };
    setVal("archNodeCreatedAt", node.createdAt || "");
    setVal("archNodeUpdatedAt", node.updatedAt || "");
    setVal("archNodeContentHash", node.contentHash || "");
    setVal("archNodeSchemaVersion", node.schemaVersion || "1");
    setVal("archNodeDependencies", formatArchDependencyLines(node.dependencies));
    setVal("archNodeBddSpecs", (node.bddSpecs || []).join("\n"));
    setVal("archNodeTddSpecs", (node.tddSpecs || []).join("\n"));
    setVal(
      "archNodeWidth",
      node.width != null && node.width !== "" ? String(node.width) : ""
    );
    setVal(
      "archNodeHeight",
      node.height != null && node.height !== "" ? String(node.height) : ""
    );
  }

  function clearArchCommonInspector() {
    [
      "archNodeCreatedAt",
      "archNodeUpdatedAt",
      "archNodeContentHash",
      "archNodeSchemaVersion",
      "archNodeDependencies",
      "archNodeBddSpecs",
      "archNodeTddSpecs",
      "archNodeWidth",
      "archNodeHeight",
      "archUiRootNodeId",
      "archUiAssetRefs",
    ].forEach(function (id) {
      const el = document.getElementById(id);
      if (el) el.value = "";
    });
  }

  function readArchCommonInspector(node) {
    if (!node) return;
    ensureArchCommonAttrs(node);
    const val = function (id) {
      const el = document.getElementById(id);
      return el ? el.value : null;
    };
    const hash = val("archNodeContentHash");
    if (hash != null) node.contentHash = hash;
    const schema = val("archNodeSchemaVersion");
    if (schema != null) node.schemaVersion = schema.trim() || "1";
    const deps = val("archNodeDependencies");
    if (deps != null) {
      node.dependencies = parseArchLineList(deps)
        .map(normalizeArchDependency)
        .filter(function (dep) {
          return !!dep;
        });
    }
    const bdd = val("archNodeBddSpecs");
    if (bdd != null) node.bddSpecs = parseArchLineList(bdd);
    const tdd = val("archNodeTddSpecs");
    if (tdd != null) node.tddSpecs = parseArchLineList(tdd);
    const width = val("archNodeWidth");
    if (width != null) {
      node.width = width.trim() === "" ? "" : Number(width) || "";
    }
    const height = val("archNodeHeight");
    if (height != null) {
      node.height = height.trim() === "" ? "" : Number(height) || "";
    }
    document
      .querySelectorAll(
        "#archInList [data-arch-port-line], #archOutList [data-arch-port-line]"
      )
      .forEach(function (input) {
        const pid = input.getAttribute("data-port-id") || "";
        const side = input.getAttribute("data-arch-port-line");
        const ports = side === "output" ? node.outputs : node.inputs;
        const port = (ports || []).find(function (p) {
          return p && p.id === pid;
        });
        if (port) applyArchPortLine(port, input.value);
      });
    if (isArchUiLayerNode(node)) {
      ensureUiLayerFields(node);
      const root = val("archUiRootNodeId");
      if (root != null) node.rootNodeId = root.trim();
      const assets = val("archUiAssetRefs");
      if (assets != null) node.assetRefs = parseArchLineList(assets);
    }
    touchArchNodeUpdatedAt(node);
  }

  function fillArchPortInspectorList(listEl, ports, side) {
    if (!listEl) return;
    listEl.innerHTML = "";
    (ports || []).forEach(function (p) {
      ensureArchPort(p, p && p.id, side === "output" ? "out" : "in");
      const li = document.createElement("li");
      li.className = "arch-port-line";
      const idSpan = document.createElement("code");
      idSpan.textContent = p.id || "";
      const input = document.createElement("input");
      input.type = "text";
      input.value = formatArchPortLine(p);
      input.setAttribute("data-arch-port-line", side);
      input.setAttribute("data-port-id", p.id || "");
      input.title =
        "label|dataType|schemaRef|required|cardinality|constraints|defaultValue|errorTypeRefs|description";
      input.setAttribute("aria-label", (side || "port") + " " + (p.id || ""));
      input.addEventListener("change", applyArchInspectorInputs);
      li.appendChild(idSpan);
      li.appendChild(input);
      listEl.appendChild(li);
    });
  }

  function fillArchInspector(node) {
    if (!node) return;
    renderArchCommonInspector(node);
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
    const clearPacksBtn = document.getElementById("arch-clear-layer-packs");
    if (packsEl && node.kind === "Layer") {
      const packs = normalizeArchKind(node.packsKind);
      packsEl.value = packs || "";
      packsEl.disabled = true;
      packsEl.title = packs
        ? "由子物件定義：Layer." + packs
        : "尚未有子物件 — 丟入後定義為 Layer.<Kind>";
    }
    if (clearPacksBtn) {
      const nMem =
        node.kind === "Layer" ? layerAllMemberIds(node).length : 0;
      clearPacksBtn.hidden = node.kind !== "Layer";
      clearPacksBtn.disabled = !archEditMode || !nMem;
      clearPacksBtn.title = nMem
        ? "清除 Layer 類別（卸下 " + nMem + " 個子物件）"
        : "無子物件可清除";
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
        const rootEl = document.getElementById("archUiRootNodeId");
        const assetsEl = document.getElementById("archUiAssetRefs");
        if (rootEl) rootEl.value = node.rootNodeId || "";
        if (assetsEl) assetsEl.value = (node.assetRefs || []).join("\n");
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
    renderArchExtraKindPanel(node);
    if (hint) {
      const io = ARCH_KIND_IO[node.kind];
      const role = node.role || (io && io.role) || "";
      if (node.kind === "Layer") {
        const mods = ensureLayerModules(node);
        const nMem = layerAllMemberIds(node).length;
        hint.textContent = isArchUiLayerNode(node)
          ? formatArchLayerPacks(node) +
            " · 已開啟 UI 工具視窗 · 內含 UI 專屬節點"
          : formatArchLayerPacks(node) +
            " · 進入內層編輯 Module Slot 與子節點 · " +
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
          const letterLab = document.createElement("span");
          letterLab.className = "arch-slot-prefix";
          letterLab.textContent = "slot " + (mod.slotLetter || "A") + " :";
          const nameInp = document.createElement("input");
          nameInp.type = "text";
          nameInp.value = mod.name || "Module";
          nameInp.title = "Module name；moduleId 不變。畫布顯示 slot A : Module name";
          nameInp.setAttribute("aria-label", "Module name");
          nameInp.addEventListener("change", function () {
            if (!archEditMode) {
              toast("請先開「編輯草稿」");
              nameInp.value = mod.name || "";
              return;
            }
            mod.name = nameInp.value.trim() || mod.name;
            touchArchNodeUpdatedAt(node);
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
          head.appendChild(letterLab);
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
            li.title = "點選查看規劃書屬性";
            li.addEventListener("click", function (ev) {
              if (ev.target && ev.target.closest && ev.target.closest("button")) {
                return;
              }
              if (
                !currentArchFocusLayer() ||
                currentArchFocusLayer().id !== node.id
              ) {
                enterArchLayer(node.id);
              }
              selectArchNode(mid);
              setArchInspectorTab("spec");
            });
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
    fillArchPortInspectorList(inList, node.inputs, "input");
    fillArchPortInspectorList(outList, node.outputs, "output");
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
    renderArchSpecPanel(node);
  }

  function syncArchTreeParentActions() {
    const ids = getArchSelectedIds();
    const canUnparent = ids.some(function (id) {
      return !!findArchLayerContaining(id);
    });
    const parent = findArchNode(archSelectedId);
    const canParent =
      !!parent &&
      parent.kind === "Layer" &&
      ids.some(function (id) {
        return id !== parent.id && !!findArchNode(id);
      });
    const packable = ids.filter(function (id) {
      const n = findArchNode(id);
      return n && n.kind !== "Layer";
    });
    const parentBtn = document.getElementById("arch-tree-parent");
    const unparentBtn = document.getElementById("arch-tree-unparent");
    const addLayerBtn = document.getElementById("arch-tree-add-layer");
    if (parentBtn) parentBtn.disabled = !canParent;
    if (unparentBtn) unparentBtn.disabled = !canUnparent;
    if (addLayerBtn) addLayerBtn.disabled = packable.length === 0;
  }

  function syncArchDeleteUi() {
    const ids = getArchSelectedIds();
    const hasSel = ids.length > 0;
    const hasEdge = !!archSelectedEdgeKey;
    const canDel = !!archEditMode && (hasSel || hasEdge);
    const canArrange = !!archEditMode && ids.length >= 2;
    const btn = document.getElementById("arch-delete-node");
    const insp = document.getElementById("arch-inspector-delete");
    const focusBtn = document.getElementById("arch-focus-selected");
    const arrangeAuto = document.getElementById("arch-arrange-auto");
    const arrangeH = document.getElementById("arch-arrange-h");
    const arrangeV = document.getElementById("arch-arrange-v");
    if (btn) {
      btn.disabled = !canDel;
      if (hasEdge && !hasSel) {
        btn.title = "刪除選取連線（Delete）";
      } else {
        btn.title =
          ids.length > 1
            ? "刪除選取 " + ids.length + " 個節點（Delete）"
            : "刪除選取節點（Delete）";
      }
    }
    if (insp) insp.disabled = !canDel || (hasEdge && !hasSel);
    if (focusBtn) focusBtn.disabled = !hasSel;
    if (arrangeAuto) arrangeAuto.disabled = !canArrange;
    if (arrangeH) arrangeH.disabled = !canArrange;
    if (arrangeV) arrangeV.disabled = !canArrange;
    syncArchTreeParentActions();
  }

  function clearArchEdgeSelection(opts) {
    const quiet = opts && opts.quiet;
    if (!archSelectedEdgeKey) return;
    archSelectedEdgeKey = null;
    if (!quiet) {
      renderArchEdges();
      syncArchDeleteUi();
    }
  }

  function selectArchEdge(edgeKey) {
    if (!edgeKey) {
      clearArchEdgeSelection();
      return;
    }
    archSelectedEdgeKey = edgeKey;
    archSelectedIds = [];
    archSelectedId = null;
    refreshArchSelectionChrome();
    setArchInspectorActive(false);
    renderArchEdges();
    syncArchDeleteUi();
  }

  function deleteArchSelectedEdge() {
    if (!archEditMode) {
      toast("請先開「編輯草稿」再刪除連線");
      return false;
    }
    if (!archSelectedEdgeKey) {
      toast("未選取連線");
      return false;
    }
    const parts = String(archSelectedEdgeKey).split("\0");
    const fromId = parts[0];
    const toId = parts[1];
    if (!fromId || !toId) {
      clearArchEdgeSelection();
      return false;
    }
    const before = (archDoc.edges || []).length;
    const selectedKey = archSelectedEdgeKey;
    archDoc.edges = (archDoc.edges || []).filter(function (e) {
      if (e.fromNode + "\0" + e.toNode === selectedKey) return false;
      const a = effectiveArchEndpoint(e.fromNode);
      const b = effectiveArchEndpoint(e.toNode);
      return !(a === fromId && b === toId);
    });
    const removed = before - archDoc.edges.length;
    archSelectedEdgeKey = null;
    persistArchDraft();
    renderArchEdges();
    syncArchDeleteUi();
    toast(removed ? "已清除連線" : "沒有可清除的連線");
    return removed > 0;
  }

  function archChannelLabel(node, port) {
    const nodeName = (node && (node.name || node.kind)) || "?";
    const portName = (port && (port.label || port.id)) || "?";
    return nodeName + "." + portName;
  }

  function archConnectChannelRows(a, b) {
    const rows = [];
    function pushDir(from, to) {
      (from.outputs || []).forEach(function (outp) {
        (to.inputs || []).forEach(function (inp) {
          const exists = (archDoc.edges || []).some(function (e) {
            return (
              e.fromNode === from.id &&
              e.fromPort === outp.id &&
              e.toNode === to.id &&
              e.toPort === inp.id
            );
          });
          rows.push({
            fromId: from.id,
            fromPort: outp.id,
            toId: to.id,
            toPort: inp.id,
            fromLabel: archChannelLabel(from, outp),
            toLabel: archChannelLabel(to, inp),
            exists: exists,
          });
        });
      });
    }
    pushDir(a, b);
    pushDir(b, a);
    return rows;
  }

  function closeArchConnectMenu() {
    const menu = document.getElementById("arch-connect-menu");
    if (menu) menu.hidden = true;
    archConnectRows = [];
  }

  function applyArchConnectChannel(row) {
    if (!row || row.exists) return false;
    if (!archEditMode) {
      toast("請先開「編輯草稿」");
      return false;
    }
    archDoc.edges.push({
      id: newArchUuid(),
      fromNode: row.fromId,
      fromPort: row.fromPort,
      toNode: row.toId,
      toPort: row.toPort,
    });
    persistArchDraft();
    renderArchEdges();
    closeArchConnectMenu();
    toast("已連接 " + row.fromLabel + " → " + row.toLabel);
    return true;
  }

  /** 兩個已選節點：右鍵 Connect，下面是通道連結清單。 */
  function openArchConnectMenu(clientX, clientY) {
    const ids = getArchSelectedIds();
    if (ids.length !== 2) return;
    if (!archEditMode) {
      toast("請先開「編輯草稿」再連接");
      return;
    }
    const a = findArchNode(ids[0]);
    const b = findArchNode(ids[1]);
    const menu = document.getElementById("arch-connect-menu");
    const list = document.getElementById("arch-connect-list");
    if (!a || !b || !menu || !list) return;
    archConnectRows = archConnectChannelRows(a, b);
    list.innerHTML = "";
    if (!archConnectRows.length) {
      const empty = document.createElement("li");
      empty.className = "arch-connect-empty";
      empty.textContent = "這兩個節點沒有可連的通道";
      list.appendChild(empty);
    }
    archConnectRows.forEach(function (row, i) {
      const li = document.createElement("li");
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-connect-index", String(i));
      btn.textContent = row.fromLabel + " → " + row.toLabel;
      if (row.exists) {
        btn.disabled = true;
        btn.textContent += "（已連）";
      }
      btn.addEventListener("click", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        applyArchConnectChannel(row);
      });
      li.appendChild(btn);
      list.appendChild(li);
    });
    menu.hidden = false;
    menu.style.left = clientX + "px";
    menu.style.top = clientY + "px";
    const rect = menu.getBoundingClientRect();
    const pad = 8;
    let left = clientX;
    let top = clientY;
    if (rect.right > window.innerWidth - pad) {
      left = Math.max(pad, window.innerWidth - rect.width - pad);
    }
    if (rect.bottom > window.innerHeight - pad) {
      top = Math.max(pad, window.innerHeight - rect.height - pad);
    }
    menu.style.left = left + "px";
    menu.style.top = top + "px";
  }

  /** 清除 Layer 類別：卸下全部子物件 → packsKind 回到未定。 */
  function clearArchLayerPacks(layerId) {
    if (!archEditMode) {
      toast("請先開「編輯草稿」再清除 Layer 類別");
      return false;
    }
    const layer = findArchNode(layerId || archSelectedId);
    if (!layer || layer.kind !== "Layer") {
      toast("請先選取 Layer");
      return false;
    }
    const members = layerAllMemberIds(layer).slice();
    members.forEach(function (mid) {
      unpackNodeFromLayer(mid, layer);
    });
    syncLayerIdentityFromMembers(layer);
    persistArchDraft();
    renderArchDag();
    selectArchNode(layer.id);
    toast(
      members.length
        ? "已清除 Layer 類別（卸下 " + members.length + " 個子物件）"
        : "Layer 類別已是未定"
    );
    return true;
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
      const slotId = el.getAttribute("data-slot-id");
      const selectedNode = !!(id && set[id]);
      const selectedSlot =
        !id && !!(slotId && slotId === archSelectedModuleSlotId);
      el.classList.toggle("is-selected", selectedNode || selectedSlot);
    });
    document
      .querySelectorAll("#arch-unassigned-list .arch-tree-leaf")
      .forEach(function (el) {
        const id =
          el.getAttribute("data-node-id") || el.getAttribute("data-layer-id");
        el.classList.toggle("is-selected", !!(id && set[id]));
      });
    syncArchDeleteUi();
  }

  /** 設定多選；primary 供 Inspector。opts.toggle／additive 用於 Ctrl／Shift。 */
  function setArchSelection(ids, primaryId) {
    const hadEdge = !!archSelectedEdgeKey;
    archSelectedEdgeKey = null;
    const uniq = [];
    const seen = {};
    (ids || []).forEach(function (id) {
      if (!id || seen[id] || !findArchNode(id)) return;
      seen[id] = true;
      uniq.push(id);
    });
    archSelectedIds = uniq;
    if (uniq.length) archSelectedModuleSlotId = null;
    if (hadEdge) renderArchEdges();
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

  function ensureArchTreeMarqueeEl() {
    const list = document.getElementById("arch-unassigned-list");
    if (!list) return null;
    let el = document.getElementById("archTreeMarquee");
    if (!el) {
      el = document.createElement("div");
      el.id = "archTreeMarquee";
      el.className = "arch-tree-marquee";
      el.hidden = true;
      list.appendChild(el);
    }
    return el;
  }

  function updateArchTreeMarqueeEl() {
    const el = ensureArchTreeMarqueeEl();
    const list = document.getElementById("arch-unassigned-list");
    if (!el || !list || !archTreeMarquee) {
      if (el) el.hidden = true;
      return;
    }
    const lr = list.getBoundingClientRect();
    const x0 = Math.min(archTreeMarquee.x0, archTreeMarquee.x1) - lr.left + list.scrollLeft;
    const y0 = Math.min(archTreeMarquee.y0, archTreeMarquee.y1) - lr.top + list.scrollTop;
    const x1 = Math.max(archTreeMarquee.x0, archTreeMarquee.x1) - lr.left + list.scrollLeft;
    const y1 = Math.max(archTreeMarquee.y0, archTreeMarquee.y1) - lr.top + list.scrollTop;
    el.hidden = false;
    el.style.left = x0 + "px";
    el.style.top = y0 + "px";
    el.style.width = Math.max(1, x1 - x0) + "px";
    el.style.height = Math.max(1, y1 - y0) + "px";
  }

  function clearArchTreeMarquee() {
    archTreeMarquee = null;
    const el = document.getElementById("archTreeMarquee");
    if (el) {
      el.hidden = true;
      el.style.width = "0";
      el.style.height = "0";
    }
    document.body.classList.remove("is-arch-tree-marquee");
  }

  function collectArchTreeNodesInMarquee() {
    if (!archTreeMarquee) return [];
    const box = {
      left: Math.min(archTreeMarquee.x0, archTreeMarquee.x1),
      top: Math.min(archTreeMarquee.y0, archTreeMarquee.y1),
      right: Math.max(archTreeMarquee.x0, archTreeMarquee.x1),
      bottom: Math.max(archTreeMarquee.y0, archTreeMarquee.y1),
    };
    const hit = [];
    document
      .querySelectorAll(
        "#arch-unassigned-list .arch-tree-leaf[data-node-id], #arch-unassigned-list .arch-tree-leaf[data-tree-layer]"
      )
      .forEach(function (el) {
        const id =
          el.getAttribute("data-node-id") || el.getAttribute("data-layer-id");
        if (!id || !findArchNode(id)) return;
        const r = el.getBoundingClientRect();
        if (
          r.right < box.left ||
          r.left > box.right ||
          r.bottom < box.top ||
          r.top > box.bottom
        ) {
          return;
        }
        if (hit.indexOf(id) < 0) hit.push(id);
      });
    return hit;
  }

  function finishArchTreeMarquee(ev) {
    if (!archTreeMarquee) return;
    if (!archTreeMarquee.active) {
      const x = archTreeMarquee.x0;
      const y = archTreeMarquee.y0;
      clearArchTreeMarquee();
      const under = document.elementFromPoint(x, y);
      const chip =
        under &&
        under.closest &&
        under.closest(
          "#arch-unassigned-list .arch-tree-leaf[data-node-id], #arch-unassigned-list .arch-tree-leaf[data-tree-layer]"
        );
      if (chip) {
        const id =
          chip.getAttribute("data-node-id") ||
          chip.getAttribute("data-layer-id");
        if (id) selectArchNode(id, { additive: true });
      }
      return;
    }
    const hit = collectArchTreeNodesInMarquee();
    const additive = !!(ev && (ev.ctrlKey || ev.metaKey));
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
    clearArchTreeMarquee();
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

  function archNodeKindPassesFilter(n) {
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

  function archNodeKeywordHay(n) {
    return [
      n.name,
      n.id,
      n.kind,
      n.packsKind,
      n.kind === "Layer" ? formatArchLayerPacks(n) : "",
      n.description,
      n.role,
    ]
      .join(" ")
      .toLowerCase();
  }

  function archNodeKeywordPasses(n) {
    const q = String(archCanvasKeyword || "")
      .trim()
      .toLowerCase();
    if (!q) return true;
    if (!n) return false;
    if (archNodeKeywordHay(n).indexOf(q) >= 0) return true;
    /* Layer：任一子節點命中關鍵字也顯示 */
    if (n.kind === "Layer") {
      return layerAllMemberIds(n).some(function (mid) {
        const mn = findArchNode(mid);
        return mn && archNodeKeywordHay(mn).indexOf(q) >= 0;
      });
    }
    return false;
  }

  function archNodePassesFilter(n) {
    return archNodeKindPassesFilter(n) && archNodeKeywordPasses(n);
  }

  function archTreeKindAllowed(kind) {
    const k = normalizeArchKind(kind);
    if (!k) return false;
    return archTreeKindVisible[k] !== false;
  }

  /** 架構樹篩選：關鍵字＋類別打勾（打勾顯示／沒打勾不顯示）。 */
  function archTreeNodePassesFilter(n) {
    if (!n) return false;
    const kind = normalizeArchKind(n.kind);
    if (!kind) return false;
    let kindOk = false;
    if (kind === "Layer") {
      const packs = normalizeArchKind(n.packsKind);
      kindOk =
        archTreeKindAllowed("Layer") ||
        (!!packs && archTreeKindAllowed(packs));
    } else {
      kindOk = archTreeKindAllowed(kind);
    }
    if (!kindOk) return false;
    const q = String(archTreeKeyword || "")
      .trim()
      .toLowerCase();
    if (!q) return true;
    const hay = [
      n.name,
      n.id,
      n.kind,
      n.packsKind,
      kind === "Layer" ? formatArchLayerPacks(n) : "",
      n.description,
    ]
      .join(" ")
      .toLowerCase();
    return hay.indexOf(q) >= 0;
  }

  function archTreeLayerVisible(layer) {
    if (!layer || layer.kind !== "Layer") return false;
    if (archTreeNodePassesFilter(layer)) return true;
    return layerAllMemberIds(layer).some(function (mid) {
      const mn = findArchNode(mid);
      return mn && archTreeNodePassesFilter(mn);
    });
  }

  function setArchTreeKindVisible(kind, on) {
    const k = normalizeArchKind(kind);
    if (!k) return;
    archTreeKindVisible[k] = !!on;
    const cb = document.querySelector(
      '#arch-tree-kind-menu-list input[data-arch-tree-kind="' + k + '"]'
    );
    if (cb) cb.checked = !!on;
    renderArchUnassigned();
  }

  function setArchTreeKindMenuOpen(open) {
    const menu = document.getElementById("arch-tree-kind-menu");
    const btn = document.getElementById("arch-tree-kind-toggle");
    if (!menu || !btn) return;
    menu.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
  }

  function renderArchTreeKindMenu() {
    const host = document.getElementById("arch-tree-kind-menu-list");
    if (!host) return;
    host.innerHTML = "";
    ARCH_NODE_KINDS.forEach(function (kind) {
      const lab = document.createElement("label");
      lab.className = "arch-tree-kind-item";
      lab.setAttribute("role", "menuitemcheckbox");
      lab.setAttribute(
        "aria-checked",
        archTreeKindAllowed(kind) ? "true" : "false"
      );
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.setAttribute("data-arch-tree-kind", kind);
      cb.checked = archTreeKindAllowed(kind);
      cb.addEventListener("change", function () {
        setArchTreeKindVisible(kind, cb.checked);
        lab.setAttribute("aria-checked", cb.checked ? "true" : "false");
      });
      const img = document.createElement("img");
      img.src = archKindIconSrc(kind);
      img.alt = "";
      img.width = 14;
      img.height = 14;
      const span = document.createElement("span");
      span.textContent =
        kind === "Layer"
          ? "Layer"
          : kind === "WorkItem"
            ? "Work Item"
            : kind === "Deployment"
              ? "Deployment"
              : kind === "CodeFile"
                ? "Code File"
                : kind === "AITask"
                  ? "AI Task"
                  : kind;
      lab.appendChild(cb);
      lab.appendChild(img);
      lab.appendChild(span);
      host.appendChild(lab);
    });
  }

  function wireArchCanvasFilters() {
    const qEl = document.getElementById("arch-canvas-filter-q");
    if (!qEl || qEl.dataset.wired === "1") return;
    qEl.dataset.wired = "1";
    qEl.addEventListener("input", function () {
      archCanvasKeyword = qEl.value || "";
      renderArchDag();
    });
  }

  function wireArchTreeFilters() {
    const qEl = document.getElementById("arch-tree-filter-q");
    const toggle = document.getElementById("arch-tree-kind-toggle");
    const menu = document.getElementById("arch-tree-kind-menu");
    const allBtn = document.getElementById("arch-tree-kind-all");
    const noneBtn = document.getElementById("arch-tree-kind-none");
    renderArchTreeKindMenu();
    wireArchCanvasFilters();
    if (qEl) {
      qEl.addEventListener("input", function () {
        archTreeKeyword = qEl.value || "";
        renderArchUnassigned();
      });
    }
    if (toggle && menu) {
      toggle.addEventListener("click", function (ev) {
        ev.stopPropagation();
        setArchTreeKindMenuOpen(!!menu.hidden);
      });
      menu.addEventListener("click", function (ev) {
        ev.stopPropagation();
      });
    }
    if (allBtn) {
      allBtn.addEventListener("click", function () {
        ARCH_NODE_KINDS.forEach(function (k) {
          archTreeKindVisible[k] = true;
        });
        renderArchTreeKindMenu();
        renderArchUnassigned();
      });
    }
    if (noneBtn) {
      noneBtn.addEventListener("click", function () {
        ARCH_NODE_KINDS.forEach(function (k) {
          archTreeKindVisible[k] = false;
        });
        renderArchTreeKindMenu();
        renderArchUnassigned();
      });
    }
    document.addEventListener("click", function () {
      setArchTreeKindMenuOpen(false);
    });
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
    if (!archEditMode) return;
    const focusLayer = currentArchFocusLayer();
    if (
      focusLayer &&
      archSelectedModuleSlotId &&
      !findArchNode(archSelectedId)
    ) {
      const mod = ensureLayerModules(focusLayer).find(function (m) {
        return m.slotId === archSelectedModuleSlotId;
      });
      const nameEl = document.getElementById("archNodeName");
        if (mod && nameEl) {
        mod.name = nameEl.value.trim() || mod.name || "Module";
        touchArchNodeUpdatedAt(focusLayer);
        persistArchDraft();
        renderArchDag();
        selectArchModuleSlot(focusLayer, mod.slotId);
      }
      return;
    }
    const node = findArchNode(archSelectedId);
    if (!node) return;
    const nameEl = document.getElementById("archNodeName");
    const colEl = document.getElementById("archNodeCollapsed");
    const packsEl = document.getElementById("archNodePacksKind");
    const descEl = document.getElementById("archNodeDesc");
    const orderEl = document.getElementById("archNodeOrder");
    if (nameEl) node.name = nameEl.value || node.name;
    if (descEl) node.description = descEl.value || "";
    /* Layer.packsKind 只由子物件推導，不可手動改 */
    if (node.kind === "Layer") {
      syncLayerIdentityFromMembers(node);
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
    ensureNodeSpec(node);
    document.querySelectorAll("#archSpecPanel [data-spec-input]").forEach(
      function (el) {
        if (el.readOnly) return;
        const key = el.getAttribute("data-spec-key") || "";
        if (key === "implementationRef") node.implementationRef = el.value.trim();
        else if (key === "specVersion") {
          node.specVersion = el.value.trim() || "1";
        } else if (key.indexOf("spec:") === 0) {
          node.spec[key.slice(5)] = el.value.trim();
        }
      }
    );
    readArchCommonInspector(node);
    readArchExtraKindPanel(node);
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

  /** 與 Node→Layer 相同：空 Layer 接受首個子物件定義類別；已定則 packsKind 必須吻合。 */
  function canAcceptNodeInLayer(node, layer) {
    if (!node || !layer || layer.kind !== "Layer") return false;
    if (node.kind === "Layer" || node.id === layer.id) return false;
    const nk = normalizeArchKind(node.kind);
    if (!nk || ARCH_PACKABLE_KINDS.indexOf(nk) < 0) return false;
    const packs = normalizeArchKind(layer.packsKind);
    if (!packs) return true;
    return nk === packs;
  }

  function clearArchTreeDropHighlights() {
    document
      .querySelectorAll(
        ".arch-tree-drop.is-drop-target, .arch-module-slot.is-drop-target, .arch-node.is-drop-hover"
      )
      .forEach(function (el) {
        el.classList.remove("is-drop-target");
        el.classList.remove("is-drop-hover");
      });
  }

  /** 畫布拖曳時：Slot／Layer 高光回饋（可放入才亮）。 */
  function updateArchCanvasDropHighlight(node, clientX, clientY) {
    clearArchTreeDropHighlights();
    if (!node || node.kind === "Layer") return null;
    const drop = findLayerDropTarget(node, clientX, clientY);
    if (!drop || !drop.layer || !canAcceptNodeInLayer(node, drop.layer)) {
      return drop;
    }
    const layerEl = document.querySelector(
      '.arch-node[data-id="' + drop.layer.id + '"]'
    );
    if (layerEl) layerEl.classList.add("is-drop-hover");
    if (drop.slotId && layerEl) {
      const slotEl = layerEl.querySelector(
        '.arch-module-slot[data-slot-id="' + drop.slotId + '"]'
      );
      if (slotEl) slotEl.classList.add("is-drop-target");
    }
    return drop;
  }

  function findArchTreeDropTarget(clientX, clientY, dragNodeId) {
    const el = document.elementFromPoint(clientX, clientY);
    if (!el || !el.closest) return null;
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
    const rootChip = el.closest(".arch-tree-drop[data-tree-root]");
    if (rootChip) return { type: "root", el: rootChip };
    return null;
  }

  function applyArchTreeDrop(dragNodeId, drop) {
    const node = findArchNode(dragNodeId);
    if (!node || !drop) return false;
    if (drop.type === "root" || drop.type === "draft") {
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

  function wireArchTreeNodeSelect(chip, n) {
    chip.addEventListener("click", function (ev) {
      if (archTrayDrag && archTrayDrag.moved) return;
      if (ev.ctrlKey || ev.metaKey) {
        selectArchNode(n.id, { toggle: true });
      } else if (ev.shiftKey) {
        selectArchNode(n.id, { additive: true });
      } else {
        selectArchNode(n.id);
      }
      focusArchSelectedNode();
    });
    chip.addEventListener("contextmenu", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      if (getArchSelectedIds().indexOf(n.id) < 0) {
        selectArchNode(n.id);
      }
      showArchTreeContextMenu(ev.clientX, ev.clientY);
    });
    chip.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 0) return;
      if (ev.shiftKey || ev.ctrlKey || ev.metaKey) return;
      if (n.kind === "Layer") return;
      archTrayDrag = {
        nodeId: n.id,
        startX: ev.clientX,
        startY: ev.clientY,
        moved: false,
      };
      try {
        chip.setPointerCapture(ev.pointerId);
      } catch (_e) {
        /* ignore */
      }
    });
  }

  function hideArchTreeContextMenu() {
    const el = document.getElementById("arch-tree-ctx");
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  function showArchTreeContextMenu(clientX, clientY) {
    hideArchTreeContextMenu();
    const ids = getArchSelectedIds();
    const canUnparent = ids.some(function (id) {
      return !!findArchLayerContaining(id);
    });
    const parent = findArchNode(archSelectedId);
    const canParent =
      !!parent &&
      parent.kind === "Layer" &&
      ids.some(function (id) {
        return id !== parent.id && !!findArchNode(id);
      });
    const packable = ids.filter(function (id) {
      const n = findArchNode(id);
      return n && n.kind !== "Layer";
    });
    const menu = document.createElement("div");
    menu.id = "arch-tree-ctx";
    menu.className = "arch-tree-ctx";
    menu.setAttribute("role", "menu");
    function addItem(label, enabled, onClick) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("role", "menuitem");
      btn.textContent = label;
      btn.disabled = !enabled;
      btn.addEventListener("click", function (ev) {
        ev.stopPropagation();
        hideArchTreeContextMenu();
        if (enabled) onClick();
      });
      menu.appendChild(btn);
    }
    addItem("Unparent", canUnparent, function () {
      archUnparentSelected();
    });
    addItem(
      "Parent（最後選取為父層）",
      canParent,
      function () {
        archParentSelectedToLast();
      }
    );
    addItem(
      "Add to Layer",
      packable.length > 0,
      function () {
        archAddSelectionToNewLayer();
      }
    );
    document.body.appendChild(menu);
    const pad = 6;
    const mw = menu.offsetWidth || 168;
    const mh = menu.offsetHeight || 96;
    let left = clientX;
    let top = clientY;
    if (left + mw > window.innerWidth - pad) left = window.innerWidth - mw - pad;
    if (top + mh > window.innerHeight - pad) top = window.innerHeight - mh - pad;
    menu.style.left = Math.max(pad, left) + "px";
    menu.style.top = Math.max(pad, top) + "px";
  }

  /** 設定節點展開狀態；deep=true 時一併套用所有子層（Layer→Module／Root→全部）。 */
  function setArchTreeOpenState(openKey, next, deep) {
    if (!openKey) return;
    archUnassignedTreeOpen[openKey] = !!next;
    if (!deep) return;
    if (openKey === "root") {
      (archDoc.nodes || []).forEach(function (n) {
        if (!n || n.kind !== "Layer") return;
        archUnassignedTreeOpen["layer:" + n.id] = !!next;
        ensureLayerModules(n).forEach(function (mod) {
          const mk = "mod:" + (mod.slotId || mod.moduleId || "");
          if (mk !== "mod:") archUnassignedTreeOpen[mk] = !!next;
        });
      });
      return;
    }
    if (openKey.indexOf("layer:") === 0) {
      const layer = findArchNode(openKey.slice("layer:".length));
      if (!layer || layer.kind !== "Layer") return;
      ensureLayerModules(layer).forEach(function (mod) {
        const mk = "mod:" + (mod.slotId || mod.moduleId || "");
        if (mk !== "mod:") archUnassignedTreeOpen[mk] = !!next;
      });
    }
  }

  function makeArchTreeTwist(key, open) {
    const twist = document.createElement("button");
    twist.type = "button";
    twist.className = "arch-tree-twist";
    twist.innerHTML = '<span class="arch-tree-chevron" aria-hidden="true"></span>';
    twist.title = open
      ? "收合（Shift+左鍵＝含所有子層）"
      : "展開（Shift+左鍵＝含所有子層）";
    twist.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      setArchTreeOpenState(key, !open, !!ev.shiftKey);
      renderArchUnassigned();
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
      row.appendChild(makeArchTreeTwist(opts.openKey, opts.open));
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
      title: "拖到 Layer／Module＝移入（空 Layer 由首個子物件定義類別）；拖到 Root＝Unparent",
      onChip: function (chip) {
        wireArchTreeNodeSelect(chip, n);
      },
    });
  }

  function renderArchTreeModuleBranch(layer, mod, depth) {
    const memberIds = sortedModuleMemberIds(mod).filter(function (mid) {
      const mn = findArchNode(mid);
      return mn && archTreeNodePassesFilter(mn);
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
        escapeHtml(formatModuleSlotLabel(mod)) +
        '</span><em class="arch-tree-count">' +
        memberIds.length +
        "</em>",
      title:
        "Module Slot（只收 " +
        (layer.packsKind || "?") +
        "）— 拖入 Node 同畫布規則",
      onChip: function (chip) {
        chip.addEventListener("click", function (ev) {
          if (ev.ctrlKey || ev.metaKey) {
            selectArchNode(layer.id, { toggle: true });
          } else if (ev.shiftKey) {
            selectArchNode(layer.id, { additive: true });
          } else {
            selectArchNode(layer.id);
          }
        });
        chip.addEventListener("contextmenu", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          if (getArchSelectedIds().indexOf(layer.id) < 0) {
            selectArchNode(layer.id);
          }
          showArchTreeContextMenu(ev.clientX, ev.clientY);
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
      return mn && archTreeNodePassesFilter(mn);
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
        layer.packsKind
          ? "Layer." +
            layer.packsKind +
            " — 拖入同類型 Node"
          : "Layer（未定）— 拖入子物件後定義為 Layer.<Kind>",
      onChip: function (chip) {
        chip.addEventListener("click", function (ev) {
          if (ev.ctrlKey || ev.metaKey) {
            selectArchNode(layer.id, { toggle: true });
          } else if (ev.shiftKey) {
            selectArchNode(layer.id, { additive: true });
          } else {
            selectArchNode(layer.id);
          }
          focusArchSelectedNode();
        });
        chip.addEventListener("contextmenu", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          if (getArchSelectedIds().indexOf(layer.id) < 0) {
            selectArchNode(layer.id);
          }
          showArchTreeContextMenu(ev.clientX, ev.clientY);
        });
      },
      children: kids,
    });
  }

  function renderArchTreeRootBranch(layers, orphanNodes) {
    const openKey = "root";
    const open =
      archUnassignedTreeOpen[openKey] == null
        ? true
        : !!archUnassignedTreeOpen[openKey];
    const kids = [];
    layers.forEach(function (L) {
      kids.push(renderArchTreeLayerBranch(L, 1));
    });
    orphanNodes.forEach(function (n) {
      kids.push(renderArchTreeMemberRow(n, 1));
    });
    const childCount = layers.length + orphanNodes.length;
    return makeArchTreeRow({
      depth: 0,
      hasKids: true,
      open: open,
      openKey: openKey,
      selected: false,
      dropClass: "is-root-drop is-draft-drop",
      attrs: {
        "data-tree-root": "1",
        "data-tree-draft": "1",
      },
      html:
        "<span>Root</span><em class=\"arch-tree-count\">" +
        childCount +
        "</em>",
      title: "Root — 無歸類節點放此；拖入＝Unparent（離開父層）",
      onChip: function (chip) {
        chip.addEventListener("contextmenu", function (ev) {
          ev.preventDefault();
          ev.stopPropagation();
          showArchTreeContextMenu(ev.clientX, ev.clientY);
        });
      },
      children: kids,
    });
  }

  function renderArchUnassigned() {
    const list = document.getElementById("arch-unassigned-list");
    const countEl = document.getElementById("arch-unassigned-count");
    if (!list) return;
    syncArchAssignmentsFromModules(archDoc);
    const layers = (archDoc.nodes || []).filter(function (n) {
      return n && n.kind === "Layer" && archTreeLayerVisible(n);
    });
    layers.sort(function (a, b) {
      return String(a.name || a.id).localeCompare(String(b.name || b.id));
    });
    const orphans = listUnassignedArchNodes().filter(function (n) {
      return archTreeNodePassesFilter(n) && n.kind !== "Layer";
    });
    let total = orphans.length + layers.length;
    layers.forEach(function (L) {
      total += layerAllMemberIds(L).filter(function (mid) {
        const mn = findArchNode(mid);
        return mn && archTreeNodePassesFilter(mn);
      }).length;
    });
    if (countEl) countEl.textContent = String(total);
    list.innerHTML = "";
    list.setAttribute("role", "tree");
    clearArchTreeDropHighlights();
    list.appendChild(renderArchTreeRootBranch(layers, orphans));
    refreshArchSelectionChrome();
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
      const origin = archDisplayedOrigin(node);
      return {
        x: origin.x + (side === "out" ? w : 0),
        y: origin.y + h / 2,
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
      '<defs><marker id="archArrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6a7380"></path></marker>' +
      '<marker id="archArrowSel" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L6,3 L0,6 Z" fill="#6ea8fe"></path></marker></defs>';
    /* Root：打包後端點上提至 Layer；同 Layer 內隱藏。內層：畫子節點實際連線。 */
    const focus = currentArchFocusLayer();
    const seenPair = Object.create(null);
    archDoc.edges.forEach(function (e) {
      let fromId;
      let toId;
      if (focus) {
        const fp = findArchLayerContaining(e.fromNode);
        const tp = findArchLayerContaining(e.toNode);
        if (!fp || !tp || fp.id !== focus.id || tp.id !== focus.id) return;
        fromId = e.fromNode;
        toId = e.toNode;
      } else {
        fromId = effectiveArchEndpoint(e.fromNode);
        toId = effectiveArchEndpoint(e.toNode);
      }
      if (!fromId || !toId || fromId === toId) return;
      const pairKey = fromId + "\0" + toId;
      if (seenPair[pairKey]) return;
      seenPair[pairKey] = true;
      const from = findArchNode(fromId);
      const to = findArchNode(toId);
      if (!from || !to) return;
      if (!archNodePassesFilter(from) || !archNodePassesFilter(to)) return;
      const fromPort =
        !focus && (from.kind === "Layer" || fromId !== e.fromNode)
          ? (from.outputs && from.outputs[0] && from.outputs[0].id) || e.fromPort
          : e.fromPort;
      const toPort =
        !focus && (to.kind === "Layer" || toId !== e.toNode)
          ? (to.inputs && to.inputs[0] && to.inputs[0].id) || e.toPort
          : e.toPort;
      const a = portAnchor(from, fromPort, "out");
      const b = portAnchor(to, toPort, "in");
      const dx = Math.max(40, (b.x - a.x) / 2);
      const d =
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
        b.y;
      const selected = archSelectedEdgeKey === pairKey;
      const hit = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path"
      );
      hit.setAttribute("d", d);
      hit.setAttribute("class", "arch-edge-hit");
      hit.setAttribute("data-edge-key", pairKey);
      hit.setAttribute("tabindex", "-1");
      hit.setAttribute(
        "aria-label",
        "連線 " + (from.name || fromId) + " → " + (to.name || toId)
      );
      hit.addEventListener("pointerdown", function (ev) {
        if (ev.button !== 0) return;
        ev.stopPropagation();
        selectArchEdge(pairKey);
      });
      hit.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        selectArchEdge(pairKey);
      });
      hit.addEventListener("pointerdown", function (ev) {
        if (ev.button !== 2) return;
        ev.preventDefault();
        ev.stopPropagation();
        selectArchEdge(pairKey);
      });
      svg.appendChild(hit);
      const path = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path"
      );
      path.setAttribute("d", d);
      path.setAttribute("data-edge-key", pairKey);
      path.setAttribute(
        "class",
        "arch-edge-path" +
          (from.kind === "Layer" || to.kind === "Layer"
            ? " arch-edge-layer"
            : "") +
          (selected ? " is-selected" : "")
      );
      if (from.kind === "Layer" || to.kind === "Layer") {
        path.setAttribute("stroke-width", selected ? "3" : "2.5");
      }
      if (selected) {
        path.setAttribute("marker-end", "url(#archArrowSel)");
      }
      path.style.pointerEvents = "none";
      svg.appendChild(path);
    });
    if (focus) {
      ensureLayerModules(focus).forEach(function (mod) {
        (mod.memberIds || []).forEach(function (mid) {
          const child = findArchNode(mid);
          if (!child || !archNodePassesFilter(child)) return;
          const a = boxSideAnchor(
            '.arch-node[data-slot-id="' + mod.slotId + '"]',
            "out"
          );
          const b = boxSideAnchor(
            '.arch-node[data-id="' + mid + '"]',
            "in"
          );
          if (!a || !b) return;
          const dx = Math.max(36, (b.x - a.x) / 2);
          const d =
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
            b.y;
          const mem = document.createElementNS(
            "http://www.w3.org/2000/svg",
            "path"
          );
          mem.setAttribute("d", d);
          mem.setAttribute("class", "arch-edge-path is-member");
          mem.style.pointerEvents = "none";
          svg.appendChild(mem);
        });
      });
    }
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
      path.style.pointerEvents = "none";
      svg.appendChild(path);
    }
  }

  function renderArchDag() {
    const host = document.getElementById("archNodes");
    pruneArchLayerStack();
    const focusLayer = currentArchFocusLayer();
    if (focusLayer) ensureInteriorLayout(focusLayer);
    syncArchLayerNav();
    if (!host) return;
    host.innerHTML = "";
    archDoc.nodes.forEach(function (n) {
      if (!normalizeArchKind(n.kind)) return;
      if (focusLayer) {
        if (n.kind === "Layer") return;
        const parent = findArchLayerContaining(n.id);
        if (!parent || parent.id !== focusLayer.id) return;
      } else if (n.kind !== "Layer" && findArchLayerContaining(n.id)) {
        /* 外層：已打包節點不單獨繪製（對外只見 Layer 單線） */
        return;
      }
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
      const origin = archDisplayedOrigin(n);
      el.style.left = origin.x + "px";
      el.style.top = origin.y + "px";
      const explicit = archExplicitNodeSize(n);
      if (explicit.w) {
        el.style.width = explicit.w + "px";
        el.style.minWidth = explicit.w + "px";
        el.style.maxWidth = explicit.w + "px";
      }
      if (explicit.h) {
        el.style.height = explicit.h + "px";
        el.style.minHeight = explicit.h + "px";
        el.style.overflow = "auto";
      }
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
                escapeHtml(formatModuleSlotLabel(mod)) +
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
        (n.kind === "UI" || n.kind === "Layer"
          ? '<button type="button" class="arch-ui-edit" data-ui-edit="1" title="' +
            (n.kind === "Layer"
              ? isArchUiLayerNode(n)
                ? "Edit — 開啟 UI 工具視窗"
                : "Edit — 進入 Layer 內層（Module Slot 與子節點）"
              : "Edit — 開啟獨立 UI 編輯視窗") +
            '" aria-label="Edit">Edit</button>'
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
      el.addEventListener("contextmenu", function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (getArchSelectedIds().length === 2) {
          openArchConnectMenu(ev.clientX, ev.clientY);
        }
      });
      el.addEventListener("pointerdown", function (ev) {
        if (ev.button === 2) {
          ev.preventDefault();
          ev.stopPropagation();
          if (getArchSelectedIds().length === 2) {
            openArchConnectMenu(ev.clientX, ev.clientY);
          }
          return;
        }
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
        if (focusLayer) setArchInspectorTab("spec");
        if (!archEditMode) return;
        if (focusLayer) {
          ev.preventDefault();
          ev.stopPropagation();
          archInteriorDrag = {
            kind: "node",
            id: n.id,
            startX: ev.clientX,
            startY: ev.clientY,
            ox: Number(n.innerX) || 0,
            oy: Number(n.innerY) || 0,
            moved: false,
          };
          document.body.classList.add("is-arch-dragging");
          try {
            el.setPointerCapture(ev.pointerId);
          } catch (_eInterior) {
            /* ignore */
          }
          return;
        }
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
          if (n.kind === "Layer") enterArchLayer(n.id);
          else openArchUiLayer("editor", n.id);
        }
      );
      el.addEventListener("dblclick", function (ev) {
        if (n.kind !== "Layer") return;
        if (
          ev.target.closest(".arch-port") ||
          ev.target.closest(".arch-module-node") ||
          ev.target.closest(".arch-module-toggle") ||
          ev.target.closest(".arch-add-module")
        ) {
          return;
        }
        ev.stopPropagation();
        enterArchLayer(n.id);
      });
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
            id: newArchUuid(),
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
    if (focusLayer) appendArchInteriorSlotNodes(host, focusLayer);
    expandArchWorldExtent({ quiet: true });
    renderArchEdges();
    renderArchUnassigned();
  }

  function onArchPointerMove(ev) {
    if (archInteriorDrag) {
      const dx = (ev.clientX - archInteriorDrag.startX) / (archZoom || 1);
      const dy = (ev.clientY - archInteriorDrag.startY) / (archZoom || 1);
      if (Math.abs(dx) + Math.abs(dy) > 2) archInteriorDrag.moved = true;
      const x = Math.max(0, archInteriorDrag.ox + dx);
      const y = Math.max(0, archInteriorDrag.oy + dy);
      let el = null;
      if (archInteriorDrag.kind === "slot") {
        const layer = currentArchFocusLayer();
        const mod =
          layer &&
          ensureLayerModules(layer).find(function (m) {
            return m.slotId === archInteriorDrag.id;
          });
        if (mod) {
          mod.x = x;
          mod.y = y;
        }
        el = document.querySelector(
          '.arch-node[data-slot-id="' + archInteriorDrag.id + '"]'
        );
      } else {
        const node = findArchNode(archInteriorDrag.id);
        if (node) {
          node.innerX = x;
          node.innerY = y;
        }
        el = document.querySelector(
          '.arch-node[data-id="' + archInteriorDrag.id + '"]'
        );
      }
      if (el) {
        el.style.left = x + "px";
        el.style.top = y + "px";
      }
      renderArchEdges();
      return;
    }
    if (archTrayDrag) {
      const moved =
        Math.abs(ev.clientX - archTrayDrag.startX) +
        Math.abs(ev.clientY - archTrayDrag.startY);
      clearArchTreeDropHighlights();
      if (moved > 6) {
        archTrayDrag.moved = true;
        document.body.classList.add("is-arch-dragging");
        const t = findArchTreeDropTarget(
          ev.clientX,
          ev.clientY,
          archTrayDrag.nodeId
        );
        if (t && t.el) {
          t.el.classList.add("is-drop-target");
        } else {
          updateArchCanvasDropHighlight(
            findArchNode(archTrayDrag.nodeId),
            ev.clientX,
            ev.clientY
          );
        }
      }
      return;
    }
    if (archTreeMarquee) {
      archTreeMarquee.x1 = ev.clientX;
      archTreeMarquee.y1 = ev.clientY;
      const moved =
        Math.abs(ev.clientX - archTreeMarquee.x0) +
        Math.abs(ev.clientY - archTreeMarquee.y0);
      if (moved > 6) archTreeMarquee.active = true;
      if (archTreeMarquee.active) updateArchTreeMarqueeEl();
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
      if (
        archDrag.moved &&
        (archDrag.ids || []).length === 1 &&
        primary.kind !== "Layer"
      ) {
        updateArchCanvasDropHighlight(primary, ev.clientX, ev.clientY);
      } else {
        clearArchTreeDropHighlights();
      }
      return;
    }
    if (archMemberDrag) {
      const memNode = findArchNode(archMemberDrag.nodeId);
      if (memNode) {
        updateArchCanvasDropHighlight(memNode, ev.clientX, ev.clientY);
      } else {
        clearArchTreeDropHighlights();
      }
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
    if (archInteriorDrag) {
      const drag = archInteriorDrag;
      archInteriorDrag = null;
      document.body.classList.remove("is-arch-dragging");
      if (drag.moved) {
        if (drag.kind === "slot") {
          const layer = currentArchFocusLayer();
          const mod =
            layer &&
            ensureLayerModules(layer).find(function (m) {
              return m.slotId === drag.id;
            });
          if (mod) {
            mod.x = snapInteriorCoord(mod.x);
            mod.y = snapInteriorCoord(mod.y);
          }
          persistArchDraft();
          renderArchDag();
          if (layer && mod) selectArchModuleSlot(layer, mod.slotId);
        } else {
          const node = findArchNode(drag.id);
          if (node) {
            node.innerX = snapInteriorCoord(node.innerX);
            node.innerY = snapInteriorCoord(node.innerY);
          }
          persistArchDraft();
          renderArchDag();
          selectArchNode(drag.id);
          setArchInspectorTab("spec");
        }
      }
    }
    if (archTrayDrag) {
      const dragId = archTrayDrag.nodeId;
      const node = findArchNode(dragId);
      const moved =
        !!archTrayDrag.moved ||
        Math.abs(ev.clientX - archTrayDrag.startX) +
          Math.abs(ev.clientY - archTrayDrag.startY) >
          6;
      clearArchTreeDropHighlights();
      if (node && moved) {
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
        renderArchDag();
        if (archSelectedId) selectArchNode(archSelectedId);
      }
      archTrayDrag = null;
      document.body.classList.remove("is-arch-dragging");
    }
    if (archTreeMarquee) {
      finishArchTreeMarquee(ev);
    }
    if (archMemberDrag) {
      clearArchTreeDropHighlights();
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
      clearArchTreeDropHighlights();
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
            id: newArchUuid(),
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

  function addArchNode(kind) {
    const k = normalizeArchKind(kind);
    if (!k) {
      toast("拒絕：kind 不在嚴格枚舉 ARCH_NODE_KINDS");
      return;
    }
    if (!archEditMode) {
      setArchEditMode(true);
    }
    const id = newArchUuid();
    const ports = defaultPortsForArchKind(k, id);
    const node = {
      id: id,
      name: k,
      kind: k,
      x: 80 + ((Math.random() * 144) | 0),
      y: 80 + ((Math.random() * 120) | 0),
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
      /* packsKind 不預設；由第一個子物件定義 → Layer.<Kind> */
      node.packsKind = null;
      node.memberIds = [];
      node.modules = [];
      node.name = "Layer";
      node.role = "Pack unset";
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
    if (ARCH_EXTRA_KIND_FIELDS[k]) {
      if (k === "CodeFile") node.name = "Code File";
      if (k === "AITask") node.name = "AI Task";
      ensureArchExtraKindFields(node);
    }
    ensureArchCommonAttrs(node, { fresh: true });
    archDoc.nodes.push(node);
    persistArchDraft();
    renderArchDag();
    selectArchNode(id);
    toast(
      k === "Layer"
        ? "已新增 Layer（類別由子物件定義）"
        : k === "UI"
          ? "已新增 UI Layer"
          : k === "WorkItem"
            ? "已新增 Work Item"
            : k === "Deployment"
            ? "已新增 Deployment Node"
            : k === "CodeFile"
              ? "已新增 Code File"
              : k === "AITask"
                ? "已新增 AI Task"
                : "已新增 " + k
    );
  }

  function setArchEditMode(_on) {
    archEditMode = true;
    syncArchDeleteUi();
  }

  /** 捲動盒＝縮放後的視覺大小，中鍵平移 1px 對螢幕 1px。 */
  function syncArchZoomBox() {
    const stage = document.getElementById("archStage");
    const wrap = document.getElementById("archStageWrap");
    if (!stage) return;
    const z = archZoom || 1;
    const w = Number(stage.getAttribute("data-w")) || 1280;
    const h = Number(stage.getAttribute("data-h")) || 720;
    stage.style.width = w + "px";
    stage.style.height = h + "px";
    stage.style.transformOrigin = "0 0";
    stage.style.transform = "scale(" + z + ")";
    if (wrap) {
      wrap.style.width = Math.ceil(w * z) + "px";
      wrap.style.height = Math.ceil(h * z) + "px";
    }
  }

  /**
   * 改變縮放並保住錨點下的世界座標。
   * anchor：相對 arch-canvas-shell 的螢幕座標；省略則以視窗中心為準。
   */
  function setArchZoom(z, anchor) {
    const shell = document.getElementById("arch-canvas-shell");
    const prev = archZoom || 1;
    const next = Math.max(0.4, Math.min(2, Number(z) || 1));
    let ax = shell ? shell.clientWidth / 2 : 0;
    let ay = shell ? shell.clientHeight / 2 : 0;
    if (anchor && anchor.x != null && anchor.y != null) {
      ax = anchor.x;
      ay = anchor.y;
    }
    const worldX = shell ? (shell.scrollLeft + ax) / prev : 0;
    const worldY = shell ? (shell.scrollTop + ay) / prev : 0;
    archZoom = next;
    syncArchZoomBox();
    const size = archStageSize();
    renderArchRulers(size.w, size.h);
    if (shell) {
      shell.scrollLeft = Math.max(0, worldX * next - ax);
      shell.scrollTop = Math.max(0, worldY * next - ay);
    }
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
    const isArchShell = viewport.id === "arch-canvas-shell";
    viewport.addEventListener(
      "mousedown",
      function (ev) {
        if (ev.button !== 1) return;
        ev.preventDefault();
      },
      true
    );
    viewport.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 1) return;
      ev.preventDefault();
      pan = {
        x: ev.clientX,
        y: ev.clientY,
        sl: viewport.scrollLeft,
        st: viewport.scrollTop,
      };
      if (isArchShell) archMmbPanActive = true;
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
      const was = !!pan;
      pan = null;
      if (isArchShell) archMmbPanActive = false;
      viewport.classList.remove("is-mmb-panning");
      document.body.classList.remove("is-mmb-panning");
      if (was && isArchShell) {
        expandArchWorldExtent({ quiet: true });
        rememberArchViewport(archViewportKey());
      }
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
        opts.zoomBy(ev.deltaY < 0 ? step : -step, ev);
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
    const explicit = archExplicitNodeSize(n);
    const el = document.querySelector('.arch-node[data-id="' + n.id + '"]');
    return {
      w: explicit.w || (el ? el.offsetWidth : n.kind === "Layer" ? 220 : 160),
      h: explicit.h || (el ? el.offsetHeight : n.collapsed ? 32 : 72),
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
    const origin = archDisplayedOrigin(node);
    const cx = origin.x + nw / 2;
    const cy = origin.y + nh / 2;
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
          inputs: [blankArchPort(id + "-in", "in")],
          outputs: [blankArchPort(id + "-out", "out")],
          status: "投影",
          projectionLayer: m.layer || null,
        };
        ensureArchCommonAttrs(node, { fresh: true });
        archDoc.nodes.push(node);
      } else {
        node.status = "投影";
        node.projectionLayer = m.layer || null;
        if (!normalizeArchKind(node.kind)) node.kind = kind;
        ensureArchCommonAttrs(node);
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
    document.addEventListener("pointercancel", function () {
      if (archTreeMarquee) clearArchTreeMarquee();
      hideArchTreeContextMenu();
    });
    document.addEventListener(
      "click",
      function () {
        hideArchTreeContextMenu();
      },
      true
    );
    document.getElementById("arch-tree-parent")?.addEventListener(
      "click",
      function (ev) {
        ev.stopPropagation();
        archParentSelectedToLast();
      }
    );
    document.getElementById("arch-tree-unparent")?.addEventListener(
      "click",
      function (ev) {
        ev.stopPropagation();
        archUnparentSelected();
      }
    );
    document.getElementById("arch-tree-add-layer")?.addEventListener(
      "click",
      function (ev) {
        ev.stopPropagation();
        archAddSelectionToNewLayer();
      }
    );
    document.getElementById("arch-unassigned-list")?.addEventListener(
      "pointerdown",
      function (ev) {
        if (ev.button !== 0 || !ev.shiftKey) return;
        if (ev.target.closest(".arch-tree-twist:not(.is-leaf)")) return;
        if (archLink || archDrag || archMemberDrag || archTrayDrag) return;
        hideArchTreeContextMenu();
        archTreeMarquee = {
          x0: ev.clientX,
          y0: ev.clientY,
          x1: ev.clientX,
          y1: ev.clientY,
          active: false,
        };
        document.body.classList.add("is-arch-tree-marquee");
        try {
          ev.currentTarget.setPointerCapture(ev.pointerId);
        } catch (_e) {
          /* ignore */
        }
        ev.preventDefault();
      }
    );
    document.getElementById("arch-unassigned-list")?.addEventListener(
      "contextmenu",
      function (ev) {
        if (ev.target.closest(".arch-tree-leaf")) return;
        ev.preventDefault();
        showArchTreeContextMenu(ev.clientX, ev.clientY);
      }
    );
    document.getElementById("archStage")?.addEventListener(
      "pointerdown",
      function (ev) {
        if (ev.button !== 0) return;
        if (
          ev.target.closest(".arch-node") ||
          ev.target.closest(".arch-port") ||
          ev.target.closest(".arch-edge-hit") ||
          ev.target.closest(".arch-marquee")
        ) {
          return;
        }
        if (
          archLink ||
          archDrag ||
          archMemberDrag ||
          archTrayDrag ||
          archTreeMarquee
        ) {
          return;
        }
        clearArchEdgeSelection();
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
      zoomBy: function (delta, ev) {
        const shell = document.getElementById("arch-canvas-shell");
        let anchor = null;
        if (shell && ev) {
          const r = shell.getBoundingClientRect();
          anchor = { x: ev.clientX - r.left, y: ev.clientY - r.top };
        }
        setArchZoom(archZoom + delta, anchor);
      },
      step: 0.1,
    });
    document.getElementById("arch-canvas-shell")?.addEventListener(
      "scroll",
      function () {
        if (archMmbPanActive) return;
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
    wireArchTreeFilters();
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
      if (archSelectedEdgeKey && !getArchSelectedIds().length) {
        deleteArchSelectedEdge();
        return;
      }
      deleteArchNode();
    });
    document
      .getElementById("arch-inspector-delete")
      ?.addEventListener("click", function () {
        if (archSelectedEdgeKey && !getArchSelectedIds().length) {
          deleteArchSelectedEdge();
          return;
        }
        deleteArchNode();
      });
    document
      .getElementById("arch-clear-layer-packs")
      ?.addEventListener("click", function () {
        clearArchLayerPacks(archSelectedId);
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
      if (archSelectedEdgeKey && !getArchSelectedIds().length) {
        ev.preventDefault();
        deleteArchSelectedEdge();
        return;
      }
      if (!getArchSelectedIds().length) return;
      ev.preventDefault();
      deleteArchNode();
    });
    const archShell = document.getElementById("arch-canvas-shell");
    archShell?.addEventListener(
      "pointerdown",
      function (ev) {
        if (ev.button !== 2) return;
        if (ev.target.closest && ev.target.closest(".arch-edge-hit")) return;
        if (ev.target.closest && ev.target.closest(".arch-node")) return;
        if (getArchSelectedIds().length !== 2) return;
        ev.preventDefault();
        openArchConnectMenu(ev.clientX, ev.clientY);
      },
      true
    );
    archShell?.addEventListener("contextmenu", function (ev) {
      if (ev.target.closest && ev.target.closest(".arch-edge-hit")) return;
      ev.preventDefault();
      if (getArchSelectedIds().length === 2) {
        openArchConnectMenu(ev.clientX, ev.clientY);
      }
    });
    document.addEventListener("pointerup", function (ev) {
      if (ev.button !== 2) return;
      const menu = document.getElementById("arch-connect-menu");
      if (!menu || menu.hidden) return;
      const hit = document.elementFromPoint(ev.clientX, ev.clientY);
      const btn = hit && hit.closest ? hit.closest("[data-connect-index]") : null;
      if (!btn || btn.disabled) return;
      const row = archConnectRows[Number(btn.getAttribute("data-connect-index"))];
      if (row) applyArchConnectChannel(row);
    });
    document.addEventListener("pointermove", function (ev) {
      const menu = document.getElementById("arch-connect-menu");
      if (!menu || menu.hidden) return;
      menu.querySelectorAll("[data-connect-index]").forEach(function (el) {
        el.classList.remove("is-hot");
      });
      const hit = document.elementFromPoint(ev.clientX, ev.clientY);
      const btn = hit && hit.closest ? hit.closest("[data-connect-index]") : null;
      if (btn && !btn.disabled) btn.classList.add("is-hot");
    });
    document.addEventListener("pointerdown", function (ev) {
      const menu = document.getElementById("arch-connect-menu");
      if (!menu || menu.hidden) return;
      if (menu.contains(ev.target)) return;
      if (ev.button === 2) return;
      closeArchConnectMenu();
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key !== "Escape") return;
      closeArchConnectMenu();
    });
    syncArchDeleteUi();
    [
      "archNodeName",
      "archNodeCollapsed",
      "archNodePacksKind",
      "archNodeDesc",
      "archNodeOrder",
      "archNodeContentHash",
      "archNodeSchemaVersion",
      "archNodeDependencies",
      "archNodeBddSpecs",
      "archNodeTddSpecs",
      "archNodeWidth",
      "archNodeHeight",
      "archUiDefinitionRef",
      "archUiThemeRef",
      "archUiRootNodeId",
      "archUiAssetRefs",
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
      .getElementById("arch-layer-back")
      ?.addEventListener("click", leaveArchLayer);
    document
      .getElementById("arch-layer-back-fab")
      ?.addEventListener("click", leaveArchLayer);
    document
      .getElementById("arch-layer-add-slot")
      ?.addEventListener("click", function () {
        const layer = currentArchFocusLayer();
        if (!layer) return;
        if (!archEditMode) {
          toast("請先開「編輯草稿」");
          return;
        }
        addModuleSlotToLayer(layer);
      });
    function closeArchImportMenu() {
      const menu = document.getElementById("arch-import-menu");
      const btn = document.getElementById("arch-import-program");
      if (menu) menu.hidden = true;
      if (btn) btn.setAttribute("aria-expanded", "false");
    }
    function openArchProgramPicker(inputId) {
      closeArchImportMenu();
      if (!currentArchFocusLayer()) {
        toast("請先進入 Layer 內層");
        return;
      }
      if (!archEditMode) {
        toast("請先開「編輯草稿」");
        return;
      }
      const input = document.getElementById(inputId);
      if (!input) return;
      input.value = "";
      input.click();
    }
    document
      .getElementById("arch-import-program")
      ?.addEventListener("click", function (ev) {
        ev.stopPropagation();
        if (!currentArchFocusLayer()) {
          toast("請先進入 Layer 內層");
          return;
        }
        const menu = document.getElementById("arch-import-menu");
        const btn = document.getElementById("arch-import-program");
        if (!menu) return;
        const open = menu.hidden;
        menu.hidden = !open;
        if (btn) btn.setAttribute("aria-expanded", open ? "true" : "false");
      });
    const importPreviewDialog = document.getElementById("arch-import-preview-dialog");
    const importPreviewPaths = document.getElementById("arch-import-preview-paths");
    const importPreviewStatus = document.getElementById("arch-import-preview-status");
    const importPreviewResults = document.getElementById("arch-import-preview-results");
    const importPreviewRun = document.getElementById("arch-import-preview-run");
    let importPreviewGeneration = 0;
    function importPreviewPathLines() {
      return String((importPreviewPaths && importPreviewPaths.value) || "")
        .split(/\r?\n/).map(function (path) { return path.trim(); }).filter(Boolean);
    }
    if (importPreviewRun) importPreviewRun.disabled = true;
    importPreviewPaths?.addEventListener("input", function () {
      importPreviewGeneration += 1;
      if (importPreviewRun) importPreviewRun.disabled = importPreviewPathLines().length === 0;
    });
    function clearImportPreviewResults() {
      if (importPreviewResults) importPreviewResults.replaceChildren();
    }
    function resetImportPreviewSession() {
      importPreviewGeneration += 1;
      clearImportPreviewResults();
      if (importPreviewPaths) importPreviewPaths.value = "";
      if (importPreviewRun) importPreviewRun.disabled = true;
      if (importPreviewStatus) {
        importPreviewStatus.textContent = "輸入一個或多個專案內相對 .rs 路徑。";
        importPreviewStatus.classList.remove("error");
      }
    }
    function importPreviewText(tag, text, className) {
      const el = document.createElement(tag);
      el.textContent = String(text == null ? "" : text);
      if (className) el.className = className;
      return el;
    }
    function renderImportPreview(dto) {
      clearImportPreviewResults();
      const files = Array.isArray(dto && dto.files) ? dto.files : [];
      if (importPreviewStatus) {
        importPreviewStatus.textContent =
          "預覽完成：" + files.length + " 個檔案。此語法候選不會套用到架構圖。";
        importPreviewStatus.classList.remove("error");
      }
      files.forEach(function (file) {
        const section = document.createElement("section");
        section.className = "arch-import-preview-file";
        section.appendChild(importPreviewText("h3", file.relative_path || "(unknown file)"));
        section.appendChild(importPreviewText("p", "Parser: " + (dto.parser_version || "unknown")));
        section.appendChild(importPreviewText("p", "SHA-256: " + (file.source_sha256 || ""), "arch-import-preview-hash"));
        const symbols = Array.isArray(file.symbols) ? file.symbols : [];
        const symbolList = document.createElement("ul");
        symbolList.setAttribute("aria-label", "Syntax symbols");
        symbols.forEach(function (symbol) {
          const span = symbol.span;
          const location = span && span.start_line
            ? " · L" + span.start_line + ":C" + (Number(span.start_column || 0) + 1)
            : "";
          symbolList.appendChild(importPreviewText("li", (symbol.kind || "syntax") + " · " + (symbol.name || "") + location));
        });
        if (!symbols.length) symbolList.appendChild(importPreviewText("li", "沒有可顯示的語法符號"));
        section.appendChild(symbolList);
        const refs = Array.isArray(file.unresolved_references) ? file.unresolved_references : [];
        section.appendChild(importPreviewText("h4", "未解析語法參照（不是已解析相依圖）"));
        const refList = document.createElement("ul");
        refs.forEach(function (ref) {
          const span = ref.span;
          const location = span && span.start_line
            ? " · L" + span.start_line + ":C" + (Number(span.start_column || 0) + 1)
            : "";
          refList.appendChild(importPreviewText("li", (ref.expression || "syntax reference") + location + " · " + (ref.reason || "unresolved")));
        });
        if (!refs.length) refList.appendChild(importPreviewText("li", "沒有可顯示的呼叫語法參照；不代表語意關係完整"));
        section.appendChild(refList);
        importPreviewResults.appendChild(section);
      });
    }
    document.getElementById("arch-import-preview")?.addEventListener("click", function () {
      closeArchImportMenu();
      if (!currentArchFocusLayer()) {
        toast("請先進入 Layer 內層");
        return;
      }
      if (!importPreviewDialog) return;
      resetImportPreviewSession();
      if (typeof importPreviewDialog.showModal === "function") importPreviewDialog.showModal();
      else importPreviewDialog.setAttribute("open", "open");
      if (importPreviewPaths) importPreviewPaths.focus();
    });
    importPreviewRun?.addEventListener("click", async function () {
      const requestGeneration = ++importPreviewGeneration;
      const paths = importPreviewPathLines();
      clearImportPreviewResults();
      if (!paths.length) {
        if (importPreviewStatus) {
          importPreviewStatus.textContent = "請輸入至少一個專案內相對 .rs 路徑。";
          importPreviewStatus.classList.remove("error");
        }
        return;
      }
      if (!invoke) {
        if (importPreviewStatus) {
          importPreviewStatus.textContent = "HOST IPC 不可用；目前未執行預覽。";
          importPreviewStatus.classList.add("error");
        }
        return;
      }
      importPreviewRun.disabled = true;
      if (importPreviewStatus) {
        importPreviewStatus.textContent = "正在透過已綁定專案根目錄讀取並解析…";
        importPreviewStatus.classList.remove("error");
      }
      try {
        const dto = await invoke("import_preview", { request: { relative_paths: paths } });
        if (requestGeneration === importPreviewGeneration) renderImportPreview(dto);
      } catch (error) {
        if (requestGeneration === importPreviewGeneration) {
          clearImportPreviewResults();
          if (importPreviewStatus) {
            importPreviewStatus.textContent = "預覽失敗：" + String(error);
            importPreviewStatus.classList.add("error");
          }
        }
      } finally {
        if (requestGeneration === importPreviewGeneration) {
          importPreviewRun.disabled = paths.length === 0;
        }
      }
    });
    document.getElementById("arch-import-preview-cancel")?.addEventListener("click", function () {
      resetImportPreviewSession();
      if (importPreviewDialog && typeof importPreviewDialog.close === "function") importPreviewDialog.close();
      else if (importPreviewDialog) importPreviewDialog.removeAttribute("open");
    });
    importPreviewDialog?.addEventListener("close", function () {
      resetImportPreviewSession();
    });
    document
      .getElementById("arch-import-files")
      ?.addEventListener("click", function () {
        openArchProgramPicker("arch-program-file");
      });
    document
      .getElementById("arch-import-dir")
      ?.addEventListener("click", function () {
        openArchProgramPicker("arch-program-dir");
      });
    document.addEventListener("pointerdown", function (ev) {
      const wrap = document.getElementById("arch-import-wrap");
      if (wrap && wrap.contains(ev.target)) return;
      closeArchImportMenu();
    });
    function onArchProgramFilesPicked(ev) {
      const files = Array.prototype.slice.call(ev.target.files || []);
      ev.target.value = "";
      if (files.length) importArchProgramFiles(files);
    }
    document
      .getElementById("arch-program-file")
      ?.addEventListener("change", onArchProgramFilesPicked);
    document
      .getElementById("arch-program-dir")
      ?.addEventListener("change", onArchProgramFilesPicked);
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

  function archKindShortLabel(kind, i) {
    if (kind === "Layer") return "Layer";
    if (kind === "UI") return "UI";
    if (kind === "WorkItem") return "Work";
    if (kind === "Deployment") return "Deploy";
    if (kind === "Infrastructure") return "Infra";
    if (kind === "Application") return "App";
    if (kind === "CodeFile") return "Code";
    if (kind === "AITask") return "AI";
    return kind;
  }

  function archKindTitle(kind) {
    if (kind === "Layer")
      return "Layer（空殼；丟入子物件後成為 Layer.<Kind>）";
    if (kind === "UI") return "UI Layer（架構入口 → Editor／Viewer）";
    if (kind === "WorkItem") return "Work Item（燈號／Event Log）";
    if (kind === "Deployment") return "Deployment Node（佈署目標／策略／狀態）";
    if (kind === "CodeFile") return "Code File（檔案路徑／語言／版本參照）";
    if (kind === "Test") return "Test（測試套件／框架／結果）";
    if (kind === "Build") return "Build（設定檔／輸入／產物）";
    if (kind === "AITask") return "AI Task（模型／提示／預算）";
    return kind;
  }

  function renderArchNodeStrip() {
    const host = document.getElementById("arch-node-strip-grid");
    if (!host) return;
    host.innerHTML = "";
    ARCH_NODE_KINDS.forEach(function (kind, i) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "arch-node-strip-tile";
      btn.setAttribute("role", "option");
      btn.setAttribute("data-arch-kind", kind);
      btn.title = archKindTitle(kind);
      const img = document.createElement("img");
      img.src = archKindIconSrc(kind);
      img.alt = "";
      img.width = 14;
      img.height = 14;
      img.decoding = "async";
      const lab = document.createElement("span");
      lab.className = "arch-node-strip-tile-label";
      lab.textContent = archKindShortLabel(kind, i);
      btn.appendChild(img);
      btn.appendChild(lab);
      btn.addEventListener("click", function () {
        const kindEl = document.getElementById("archAddKind");
        if (kindEl) kindEl.value = kind;
        addArchNode(kind);
      });
      host.appendChild(btn);
    });
  }

  function wireArchKindPicker() {
    renderArchNodeStrip();
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

  /** PD-SHELL-UIDESIGN-VIEW-01 — design package viewer (≠ product evidence / not formal PASS). */
  const UIDESIGN_REL_PATH = "docs/ui-design/index.html";
  const UIDESIGN_DESIGN_REL = "design/main.sgendesign";
  let lastUidesignPkg = null;

  /** PD-UIDESIGNER-EDIT — in-memory DesignDoc (format sgenaxis.design v1). */
  /** UI-bhv.html §7。Dropdown／Select 是同一列。ComboBox 規格沒有，保留為舊型別。 */
  const UI_BHV_SECTIONS = [
    {
      title: "Root / Window / Page",
      kinds: [
        ["Window", ["title", "windowMode", "resizable", "minSize", "maxSize", "modal", "closePolicy"]],
        ["Page", ["routeId", "pageTitle", "navigationPolicy", "keepAlive"]],
        ["Dialog", ["modal", "dismissible", "confirmPolicy", "escapeToClose"]],
        ["Overlay", ["overlayMode", "backdrop", "dismissPolicy", "zIndex"]],
        ["Component", ["componentDefinitionRef", "exposedProperties", "exposedEvents"]],
      ],
    },
    {
      title: "Layout / Container",
      kinds: [
        ["Panel", ["border", "padding", "background", "clipContent"]],
        ["Group", ["groupTitle", "collapsible", "collapsed"]],
        ["Layout", ["layoutMode", "gap", "alignment", "distribution"]],
        ["Row", ["gap", "wrap", "verticalAlignment"]],
        ["Column", ["gap", "horizontalAlignment"]],
        ["Grid", ["columns", "rows", "columnGap", "rowGap", "cellSizing"]],
        ["ScrollView", ["scrollDirection", "scrollbarPolicy", "overscroll"]],
        ["Splitter", ["orientation", "initialRatio", "minPaneSize", "resizable"]],
        ["Spacer", ["flex", "minSize", "maxSize"]],
        ["Separator", ["orientation", "thickness", "style", "color"]],
      ],
    },
    {
      title: "Navigation",
      kinds: [
        ["MenuBar", ["menus", "overflowPolicy", "activationMode"]],
        ["Menu", ["items", "placement", "dismissOnSelect"]],
        ["MenuItem", ["commandRef", "shortcut", "checked", "disabledReason"]],
        ["Toolbar", ["orientation", "itemSpacing", "overflowPolicy"]],
        ["TabView", ["tabs", "activeTabId", "tabPosition", "closableTabs"]],
        ["TabItem", ["tabId", "title", "iconAssetId", "closeable"]],
        ["Breadcrumb", ["items", "separator", "maxVisibleItems"]],
        ["TreeView", ["dataSourceRef", "selectionMode", "expandPolicy", "virtualization"]],
        ["TreeItem", ["itemId", "label", "iconAssetId", "expanded", "selectable"]],
        ["Pagination", ["pageSize", "currentPage", "totalCount", "pageSizeOptions"]],
      ],
    },
    {
      title: "Basic",
      kinds: [
        ["Label", ["text", "fontRef", "fontSize", "fontWeight", "color", "textAlign", "wrapping"]],
        ["Button", ["text", "iconAssetId", "variant", "size", "loading", "disabled", "commandRef"]],
        ["Icon", ["assetId", "iconSize", "tintColor", "fitMode"]],
        ["Image", ["assetId", "fitMode", "aspectRatio", "alignment", "placeholderAssetId"]],
        ["Link", ["text", "target", "navigationRef", "externalLinkPolicy"]],
        ["Badge", ["text", "variant", "color", "size"]],
        ["Divider", ["orientation", "thickness", "color", "style"]],
      ],
    },
    {
      title: "Input / Form",
      kinds: [
        ["TextInput", ["value", "placeholder", "maxLength", "inputMode", "readOnly", "clearable"]],
        ["TextArea", ["value", "rows", "maxRows", "maxLength", "resizeMode"]],
        ["NumberInput", ["value", "min", "max", "step", "precision", "unit"]],
        ["Checkbox", ["checked", "indeterminate", "label", "triState"]],
        ["RadioGroup", ["options", "value", "orientation", "selectionRequired"]],
        ["Dropdown", ["options", "value", "placeholder", "searchable", "multiSelect"]],
        ["Slider", ["value", "min", "max", "step", "orientation", "showValue"]],
        ["ColorPicker", ["colorValue", "colorSpace", "alphaEnabled", "paletteRef"]],
        ["DatePicker", ["value", "minDate", "maxDate", "format", "calendarMode"]],
        ["Form", ["fieldRefs", "validationMode", "submitPolicy", "resetPolicy"]],
        ["FormField", ["fieldName", "label", "required", "helpText", "errorText"]],
        ["FilePicker", ["acceptedTypes", "multiple", "maxFileSize", "selectionMode"]],
      ],
    },
    {
      title: "Data Display",
      kinds: [
        ["Table", ["columns", "dataSourceRef", "sorting", "filtering", "selectionMode"]],
        ["ListView", ["itemTemplateRef", "dataSourceRef", "selectionMode", "virtualization"]],
        ["DataGrid", ["columns", "rowKey", "editingMode", "sorting", "filtering", "pagination"]],
        ["PropertyGrid", ["schemaRef", "selectedObjectRef", "categoryGrouping", "readOnly"]],
        ["TextView", ["content", "format", "wrapping", "selectable"]],
        ["CodeView", ["language", "contentRef", "lineNumbers", "readOnly", "syntaxHighlighting"]],
        ["LogView", ["dataSourceRef", "severityFilter", "autoScroll", "maxEntries"]],
        ["Chart", ["chartType", "dataSourceRef", "series", "axes", "legend", "interactionMode"]],
      ],
    },
    {
      title: "3D / Visualization",
      kinds: [
        ["Viewport3D", ["sceneRef", "cameraRef", "navigationMode", "renderMode", "gridVisible", "gizmoVisible"]],
        ["SceneView", ["sceneRef", "selectionPolicy", "overlayRefs", "updatePolicy"]],
        ["Gizmo", ["gizmoType", "targetRef", "axisVisibility", "interactionMode"]],
        ["Timeline", ["startTime", "endTime", "currentTime", "frameRate", "tracksRef"]],
        ["GraphView", ["graphRef", "nodeKinds", "connectionPolicy", "autoLayout"]],
        ["NodeCanvas", ["graphRef", "zoomRange", "gridMode", "selectionMode", "snapToGrid"]],
        ["PropertyInspector", ["targetRef", "schemaRef", "groupingMode", "editPolicy"]],
        ["AssetBrowser", ["assetQuery", "filterKinds", "thumbnailMode", "sortMode"]],
      ],
    },
    {
      title: "Feedback / Progress",
      kinds: [
        ["ProgressBar", ["value", "min", "max", "indeterminate", "showLabel"]],
        ["Spinner", ["active", "size", "label"]],
        ["Toast", ["message", "severity", "duration", "dismissible"]],
        ["Alert", ["title", "message", "severity", "actions", "dismissible"]],
        ["Tooltip", ["content", "placement", "delay", "triggerMode"]],
        ["StatusIndicator", ["status", "label", "iconAssetId", "severityMapping"]],
        ["NotificationCenter", ["sourceRef", "maxItems", "grouping", "retentionPolicy"]],
      ],
    },
    {
      title: "Overlay / Floating",
      kinds: [
        ["Popover", ["anchorNodeId", "placement", "dismissPolicy", "triggerMode"]],
        ["ContextMenu", ["items", "targetKinds", "placement", "dismissPolicy"]],
        ["Drawer", ["placement", "modal", "size", "dismissible"]],
        ["FloatingPanel", ["anchorMode", "position", "draggable", "resizable"]],
        ["TooltipOverlay", ["targetNodeId", "content", "placement", "delay"]],
        ["ModalOverlay", ["backdrop", "blocking", "dismissPolicy", "focusTrap"]],
      ],
    },
    {
      title: "Interaction / Behavior",
      kinds: [
        ["ShortcutBinding", ["keySequence", "modifiers", "scope", "commandRef"]],
        ["CommandBinding", ["commandRef", "inputMapping", "executionPolicy"]],
        ["DragHandle", ["dragMode", "allowedTargets", "constraints", "payloadMapping"]],
        ["DropTarget", ["acceptedKinds", "dropPolicy", "validationRuleRef"]],
        ["SelectionModel", ["selectionMode", "selectedRefs", "selectionChangedEvent"]],
        ["StateController", ["stateSchemaRef", "initialState", "transitionRules"]],
      ],
    },
    {
      title: "Specialized Containers",
      kinds: [
        ["DockWorkspace", ["dockAreas", "layoutState", "allowedDockTargets"]],
        ["DocumentWorkspace", ["documentRefs", "activeDocumentId", "tabPolicy"]],
        ["EditorWorkspace", ["panelLayoutRef", "toolContext", "workspaceProfile"]],
        ["AssetWorkspace", ["assetQuery", "previewMode", "importQueueRef"]],
        ["ViewportWorkspace", ["viewportRefs", "activeViewportId", "syncPolicy"]],
        ["DebugWorkspace", ["logSourceRefs", "traceRef", "breakpointPolicy"]],
      ],
    },
  ];
  const UI_BHV_PROPS = Object.create(null);
  UI_BHV_SECTIONS.forEach(function (sec) {
    (sec.kinds || []).forEach(function (pair) {
      UI_BHV_PROPS[pair[0]] = pair[1];
    });
  });
  const UI_TYPE_ALIASES = {
    LineEdit: "TextInput",
    CheckBox: "Checkbox",
    Select: "Dropdown",
  };
  const UI_NODE_TYPES = Object.keys(UI_BHV_PROPS).concat(
    Object.keys(UI_TYPE_ALIASES),
    ["ComboBox"]
  );
  const DESIGN_SNAP_PX = 8;

  function isUiExclusiveNodeType(type) {
    return UI_NODE_TYPES.indexOf(String(type || "")) >= 0;
  }

  function canonicalUiType(type) {
    const t = String(type || "");
    return UI_TYPE_ALIASES[t] || t;
  }

  function uiKindFieldNames(type) {
    return UI_BHV_PROPS[canonicalUiType(type)] || [];
  }

  function ensureUiKindProperties(node) {
    if (!node) return node;
    if (
      !node.properties ||
      typeof node.properties !== "object" ||
      Array.isArray(node.properties)
    ) {
      node.properties = {};
    }
    uiKindFieldNames(node.type).forEach(function (key) {
      if (node.properties[key] == null) node.properties[key] = "";
    });
    return node;
  }

  function stampUiExclusiveNode(node) {
    if (!node || !isUiExclusiveNodeType(node.type)) return node;
    node.scope = "ui";
    node.uiExclusive = true;
    ensureUiKindProperties(node);
    return node;
  }

  /** 顯示 Widget Box；各分類 <details> 可各自收闔。 */
  function ensureUiWidgetPaletteVisible() {
    const host = document.getElementById("sec-uidesign-widgets");
    if (!host) return;
    host.dataset.open = "true";
    host.removeAttribute("hidden");
    host.classList.remove("is-hidden");
  }

  function renderUiBhvPalette() {
    const host = document.getElementById("sec-uidesign-widgets");
    if (!host) return;
    if (host.dataset.uiBhvPalette !== "1") {
      host.dataset.uiBhvPalette = "1";
      UI_BHV_SECTIONS.forEach(function (sec) {
        const missing = (sec.kinds || []).filter(function (pair) {
          return !host.querySelector(
            '[data-palette="' + pair[0] + '"]'
          );
        });
        if (!missing.length) return;
        const det = document.createElement("details");
        det.className = "uidesign-cat";
        det.open = true;
        const sum = document.createElement("summary");
        sum.textContent = sec.title;
        det.appendChild(sum);
        missing.forEach(function (pair) {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.className = "designer-item";
          btn.setAttribute("data-palette", pair[0]);
          btn.textContent =
            pair[0] === "Dropdown" ? "Dropdown / Select" : pair[0];
          det.appendChild(btn);
        });
        host.appendChild(det);
      });
    }
    ensureUiWidgetPaletteVisible();
  }

  function renderUiKindPropertyFields(node) {
    const host = document.getElementById("desKindProps");
    if (!host) return;
    host.innerHTML = "";
    if (!node) return;
    ensureUiKindProperties(node);
    const names = uiKindFieldNames(node.type);
    if (!names.length) return;
    const title = document.createElement("b");
    title.textContent = canonicalUiType(node.type) + " 屬性";
    host.appendChild(title);
    names.forEach(function (key) {
      const label = document.createElement("label");
      label.className = "designer-row";
      label.appendChild(document.createTextNode(key));
      const input = document.createElement("input");
      input.type = "text";
      input.setAttribute("data-ui-prop", key);
      input.setAttribute("aria-label", key);
      input.value =
        node.properties[key] == null ? "" : String(node.properties[key]);
      input.addEventListener("change", applyPropsFromInputs);
      label.appendChild(input);
      host.appendChild(label);
    });
  }

  /** 工具視窗只留 UI 專屬節點；架構節點類別不進這張畫布。 */
  function retainUiExclusiveNodes(doc) {
    const d = doc || designDoc;
    if (!d || !Array.isArray(d.nodes)) return d;
    d.nodes = d.nodes.filter(function (n) {
      return n && isUiExclusiveNodeType(n.type);
    });
    d.nodes.forEach(stampUiExclusiveNode);
    if (
      !d.nodes.some(function (n) {
        return n.type === "Form" && !n.parentId;
      })
    ) {
      d.nodes.unshift(blankDesignDoc().nodes[0]);
    }
    return d;
  }
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
  // One private, volatile checkpoint for the currently loaded design/main.sgendesign.
  const designRecoveryHistory = UidesignRecovery.createHistory();
  let designRecoveryPlan = null;
  let designPlaceSeq = 0;

  function touchDesignDirty() {
    designDirty = true;
    markSceneDirty();
  }

  function designRecoveryLive() {
    return {
      document: designDoc,
      identity: UIDESIGN_DESIGN_REL,
      projectRoot: cachedProjectRoot,
      activeRunId: activeRunId,
      dirty: { design: designDirty },
      history: designRecoveryHistory,
      apply: applyDesignRecoveryState,
    };
  }

  function applyDesignRecoveryState(doc, dirty) {
    designDoc = doc;
    designDirty = !!dirty.design;
    // sceneDirty is aggregate workspace state; never restore it from a document-only checkpoint.
    markSceneDirty();
    setDesignGridPx(
      (designDoc.meta && designDoc.meta.gridSize) != null
        ? designDoc.meta.gridSize
        : DESIGN_GRID_DEFAULT,
      { quiet: true }
    );
    renderDesignCanvas();
    fillDesignProps();
    updateDesignRecoveryButtons();
  }

  function updateDesignRecoveryButtons() {
    const undo = document.getElementById("uidesign-recovery-undo");
    const redo = document.getElementById("uidesign-recovery-redo");
    if (undo) undo.disabled = !UidesignRecovery.canUndo(designRecoveryHistory);
    if (redo) redo.disabled = !UidesignRecovery.canRedo(designRecoveryHistory);
  }

  function cmdUidesignRecoveryPreview() {
    const dialog = document.getElementById("uidesign-recovery-dialog");
    const summary = document.getElementById("uidesign-recovery-preview");
    const cleared = blankDesignDoc();
    // Match the renderer's UI-node projection on the detached candidate so later
    // render passes cannot silently change the checkpoint's after revision.
    retainUiExclusiveNodes(cleared);
    const prepared = UidesignRecovery.prepare({
      document: designDoc,
      clearedDocument: cleared,
      identity: UIDESIGN_DESIGN_REL,
      projectRoot: cachedProjectRoot,
      activeRunId: activeRunId,
      history: designRecoveryHistory,
      dirty: { design: designDirty },
    });
    if (!prepared.ok) {
      toast(prepared.code === "ACTIVE_RUN" ? "Run 執行或收尾中，無法清空文件" : "請先綁定專案後再清空文件");
      return;
    }
    designRecoveryPlan = prepared.plan;
    const beforeIds = new Set((designDoc.nodes || []).map((node) => node.id));
    const afterIds = new Set((cleared.nodes || []).map((node) => node.id));
    const removed = Array.from(beforeIds).filter((id) => !afterIds.has(id));
    if (summary) summary.textContent =
      "文件：" + UIDESIGN_DESIGN_REL + "；節點 " + beforeIds.size + " → " + afterIds.size + "；移除 ID：" + (removed.length ? removed.join("、") : "無") + "。預覽未修改文件；Architecture、設定、來源檔與磁碟內容不變。";
    if (dialog && typeof dialog.showModal === "function") dialog.showModal();
  }

  function cmdUidesignRecoveryConfirm() {
    if (!designRecoveryPlan) return;
    const result = UidesignRecovery.confirm(designRecoveryPlan, designRecoveryLive());
    designRecoveryPlan = null;
    const dialog = document.getElementById("uidesign-recovery-dialog");
    if (dialog && dialog.open) dialog.close();
    if (!result.ok) {
      updateDesignRecoveryButtons();
      if (result.code === "PROJECTION_FAILED") {
        toast("文件已變更；預覽更新失敗，復原記錄仍保留");
        return;
      }
      toast(result.code === "ACTIVE_RUN" ? "Run 執行或收尾中，沒有變更" : "文件或專案已變更，預覽已失效");
      return;
    }
    if (!result.changed) {
      toast("文件已是空白，沒有新增復原記錄");
      return;
    }
    updateDesignRecoveryButtons();
    toast("已清空目前文件；可在本工作階段復原（未寫入磁碟）");
  }

  function cmdUidesignRecoveryUndo() {
    const result = UidesignRecovery.undo(designRecoveryHistory, designRecoveryLive());
    if (!result.ok) {
      updateDesignRecoveryButtons();
      if (result.code === "PROJECTION_FAILED") { toast("文件狀態已復原；畫面更新失敗，復原記錄仍保留"); return; }
      toast(result.code === "WORKSPACE_STALE" || result.code === "BINDING_STALE" ? "復原失敗：文件或專案已變更" : "目前沒有可復原的文件清空");
      return;
    }
    updateDesignRecoveryButtons();
    toast("已復原文件清空");
  }

  function cmdUidesignRecoveryRedo() {
    const result = UidesignRecovery.redo(designRecoveryHistory, designRecoveryLive());
    if (!result.ok) {
      updateDesignRecoveryButtons();
      if (result.code === "PROJECTION_FAILED") { toast("文件狀態已重做；畫面更新失敗，復原記錄仍保留"); return; }
      toast(result.code === "WORKSPACE_STALE" || result.code === "BINDING_STALE" ? "重做失敗：文件或專案已變更" : "目前沒有可重做的文件清空");
      return;
    }
    updateDesignRecoveryButtons();
    toast("已重做文件清空");
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
        guides: { v: [], h: [] },
      },
      nodes: [
        {
          id: "node-form-root",
          type: "Form",
          scope: "ui",
          uiExclusive: true,
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

  function ensureDesignGuidesMeta() {
    if (!designDoc.meta) designDoc.meta = {};
    if (!designDoc.meta.guides || typeof designDoc.meta.guides !== "object") {
      designDoc.meta.guides = { v: [], h: [] };
    }
    if (!Array.isArray(designDoc.meta.guides.v)) designDoc.meta.guides.v = [];
    if (!Array.isArray(designDoc.meta.guides.h)) designDoc.meta.guides.h = [];
    return designDoc.meta.guides;
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
    const ug = ensureDesignGuidesMeta();
    (ug.v || []).forEach(function (x) {
      xs.push(Number(x) || 0);
    });
    (ug.h || []).forEach(function (y) {
      ys.push(Number(y) || 0);
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

  /** 從量尺拉出／拖曳的持久參考線（Form 座標）。 */
  let guideDrag = null;

  function clientToFormLocal(clientX, clientY) {
    const form = document.getElementById("designForm");
    if (!form) return { x: 0, y: 0, inForm: false };
    const r = form.getBoundingClientRect();
    const sx = r.width / (form.offsetWidth || 1) || 1;
    const sy = r.height / (form.offsetHeight || 1) || 1;
    const x = (clientX - r.left) / sx;
    const y = (clientY - r.top) / sy;
    return {
      x: x,
      y: y,
      inForm:
        clientX >= r.left &&
        clientX <= r.right &&
        clientY >= r.top &&
        clientY <= r.bottom,
      formRect: r,
    };
  }

  function snapGuidePos(v, axis) {
    const g = getDesignGridPx();
    let out = v;
    if (g > 0) out = Math.round(v / g) * g;
    const guides = collectDesignAlignGuides(null);
    const pool = axis === "v" ? guides.xs : guides.ys;
    const snapped = snapDesignValue(out, pool);
    if (Math.abs(snapped - out) <= DESIGN_SNAP_PX) out = snapped;
    return out;
  }

  function renderUserGuides() {
    const host = document.getElementById("designUserGuides");
    if (!host) return;
    const ug = ensureDesignGuidesMeta();
    const root = formRootNode();
    const rw = (root && root.props && Number(root.props.w)) || 800;
    const rh = (root && root.props && Number(root.props.h)) || 600;
    host.innerHTML = "";
    (ug.v || []).forEach(function (x, idx) {
      const xv = Number(x);
      if (!isFinite(xv)) return;
      const line = document.createElement("div");
      line.className = "design-user-guide is-v";
      line.style.left = xv + "px";
      line.dataset.axis = "v";
      line.dataset.index = String(idx);
      line.title = "垂直參考線 x=" + Math.round(xv) + "（拖曳移動；拖回量尺或雙擊刪除）";
      host.appendChild(line);
    });
    (ug.h || []).forEach(function (y, idx) {
      const yv = Number(y);
      if (!isFinite(yv)) return;
      const line = document.createElement("div");
      line.className = "design-user-guide is-h";
      line.style.top = yv + "px";
      line.dataset.axis = "h";
      line.dataset.index = String(idx);
      line.title = "水平參考線 y=" + Math.round(yv) + "（拖曳移動；拖回量尺或雙擊刪除）";
      host.appendChild(line);
    });
    void rw;
    void rh;
  }

  function removeGuidePreview() {
    document.querySelectorAll(".design-guide-preview").forEach(function (el) {
      el.remove();
    });
  }

  function updateGuidePreview(axis, clientX, clientY) {
    removeGuidePreview();
    const prev = document.createElement("div");
    prev.className =
      "design-guide-preview " + (axis === "v" ? "is-v" : "is-h");
    if (axis === "v") prev.style.left = clientX + "px";
    else prev.style.top = clientY + "px";
    document.body.appendChild(prev);
  }

  function beginGuideDragFromRuler(axis, ev) {
    if (uidesignChromeMode !== "designer") return;
    if (ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    guideDrag = {
      mode: "create",
      axis: axis,
      index: -1,
    };
    document.body.classList.add("is-guide-dragging");
    updateGuidePreview(axis, ev.clientX, ev.clientY);
  }

  function beginGuideDragExisting(axis, index, ev) {
    if (uidesignChromeMode !== "designer") return;
    if (ev.button !== 0) return;
    ev.preventDefault();
    ev.stopPropagation();
    guideDrag = {
      mode: "move",
      axis: axis,
      index: index,
    };
    document.body.classList.add("is-guide-dragging");
    updateGuidePreview(axis, ev.clientX, ev.clientY);
  }

  function onGuidePointerMove(ev) {
    if (!guideDrag) return;
    updateGuidePreview(guideDrag.axis, ev.clientX, ev.clientY);
    const local = clientToFormLocal(ev.clientX, ev.clientY);
    const ug = ensureDesignGuidesMeta();
    if (guideDrag.mode === "move" && guideDrag.index >= 0) {
      const list = guideDrag.axis === "v" ? ug.v : ug.h;
      if (guideDrag.index < list.length) {
        const pos =
          guideDrag.axis === "v"
            ? snapGuidePos(local.x, "v")
            : snapGuidePos(local.y, "h");
        list[guideDrag.index] = pos;
        renderUserGuides();
      }
    }
  }

  function endGuideDrag(ev) {
    if (!guideDrag) return;
    const axis = guideDrag.axis;
    const mode = guideDrag.mode;
    const index = guideDrag.index;
    const local = clientToFormLocal(ev.clientX, ev.clientY);
    const ug = ensureDesignGuidesMeta();
    const list = axis === "v" ? ug.v : ug.h;
    const deleteGuide = !local.inForm;
    if (mode === "create") {
      if (local.inForm) {
        const pos =
          axis === "v"
            ? snapGuidePos(local.x, "v")
            : snapGuidePos(local.y, "h");
        list.push(pos);
        touchDesignDirty();
        toast(
          (axis === "v" ? "垂直" : "水平") +
            "參考線 @" +
            Math.round(pos) +
            "px"
        );
      }
    } else if (mode === "move" && index >= 0) {
      if (deleteGuide) {
        if (index < list.length) {
          list.splice(index, 1);
          touchDesignDirty();
          toast("已刪除參考線");
        }
      } else {
        const pos =
          axis === "v"
            ? snapGuidePos(local.x, "v")
            : snapGuidePos(local.y, "h");
        if (index < list.length) {
          list[index] = pos;
          touchDesignDirty();
        }
      }
    }
    guideDrag = null;
    document.body.classList.remove("is-guide-dragging");
    removeGuidePreview();
    renderUserGuides();
  }

  function wireDesignGuidePull() {
    const hRuler = document.getElementById("designRulerH");
    const vRuler = document.getElementById("designRulerV");
    if (hRuler && hRuler.dataset.guidePull !== "1") {
      hRuler.dataset.guidePull = "1";
      hRuler.addEventListener("pointerdown", function (ev) {
        beginGuideDragFromRuler("v", ev);
      });
    }
    if (vRuler && vRuler.dataset.guidePull !== "1") {
      vRuler.dataset.guidePull = "1";
      vRuler.addEventListener("pointerdown", function (ev) {
        beginGuideDragFromRuler("h", ev);
      });
    }
    const host = document.getElementById("designUserGuides");
    if (host && host.dataset.guideWire !== "1") {
      host.dataset.guideWire = "1";
      host.addEventListener("pointerdown", function (ev) {
        const line = ev.target.closest(".design-user-guide");
        if (!line) return;
        const axis = line.dataset.axis;
        const index = Number(line.dataset.index);
        if (!axis || !isFinite(index)) return;
        beginGuideDragExisting(axis, index, ev);
      });
      host.addEventListener("dblclick", function (ev) {
        const line = ev.target.closest(".design-user-guide");
        if (!line) return;
        ev.preventDefault();
        const axis = line.dataset.axis;
        const index = Number(line.dataset.index);
        const ug = ensureDesignGuidesMeta();
        const list = axis === "v" ? ug.v : ug.h;
        if (index >= 0 && index < list.length) {
          list.splice(index, 1);
          touchDesignDirty();
          renderUserGuides();
          toast("已刪除參考線");
        }
      });
    }
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
    if (guideDrag) {
      onGuidePointerMove(ev);
      return;
    }
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

  function onDesignPointerUp(ev) {
    if (guideDrag) {
      endGuideDrag(ev || { clientX: 0, clientY: 0, target: null });
      return;
    }
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
      if (show) {
        renderUiBhvPalette();
        ensureUiWidgetPaletteVisible();
      }
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
    retainUiExclusiveNodes(designDoc);
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
        "design-node is-ui-node" +
        (designDoc.selection === n.id ? " is-on" : "");
      btn.setAttribute("data-node-id", n.id);
      btn.setAttribute("data-ui-exclusive", "1");
      btn.setAttribute("data-ui-type", n.type || "");
      btn.style.left = (Number(n.props.x) || 0) + "px";
      btn.style.top = (Number(n.props.y) || 0) + "px";
      btn.style.width = Math.max(8, Number(n.props.w) || 120) + "px";
      btn.style.height = Math.max(8, Number(n.props.h) || 32) + "px";
      btn.style.zIndex = String(Number(n.props.zIndex) || 1);
      const name = n.props.name || n.type;
      btn.innerHTML =
        '<span class="tag">' +
        escapeHtml("UI · " + (n.type || "")) +
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
    ensureDesignGuidesMeta();
    renderUserGuides();
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
        "UI 專屬節點 · type=" +
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
    renderUiKindPropertyFields(n);
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
    ensureUiKindProperties(n);
    document.querySelectorAll("#desKindProps [data-ui-prop]").forEach(
      function (el) {
        const key = el.getAttribute("data-ui-prop") || "";
        if (!key) return;
        n.properties[key] = el.value;
      }
    );
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
    if (!isUiExclusiveNodeType(type)) {
      toast("UI 工具視窗只接受 UI 專屬節點");
      return;
    }
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
    designDoc.nodes.push(stampUiExclusiveNode({
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
    }));
    touchDesignDirty();
    selectDesignNode(id);
    setUidesignStatus("已加入 UI 專屬節點 " + type + "（未存 · 非產品 PASS）", false);
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
    designDoc.nodes.push(stampUiExclusiveNode({
      id: id,
      type: n.type,
      parentId: root.id,
      props: props,
      bddHint: n.bddHint || "",
      tddHint: n.tddHint || "",
      behaviorHints: (n.behaviorHints || []).slice(),
      properties: Object.assign({}, n.properties || {}),
    }));
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
    renderUiBhvPalette();
    wireDesignGuidePull();
    const recoveryDialog = document.getElementById("uidesign-recovery-dialog");
    if (recoveryDialog) recoveryDialog.addEventListener("close", function () { designRecoveryPlan = null; });
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
      designDoc = retainUiExclusiveNodes(dto.doc);
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

  const SIDE_TAB_BY_PANEL = {
    arch: "diagram",
    board: "tasks",
    agent: "tasks", /* Agent 派工：Tasks 左側最上方 */
    deploy: "tasks", /* 佈版 */
    listen: "tasks", /* 監聽 */
    report: "tasks", /* 報告：Tasks 左側最下方 */
    git: "git",
    settings: "settings",
  };

  function setSideDrawerOpen(open) {
    const side = document.getElementById("sidebar");
    if (!side) return;
    side.setAttribute("data-drawer-open", open ? "true" : "false");
    const bodyEl = document.getElementById("shell-body");
    if (bodyEl) {
      bodyEl.classList.toggle("is-sidebar-collapsed", !open);
    }
  }

  function isSideDrawerOpen() {
    const side = document.getElementById("sidebar");
    return !side || side.getAttribute("data-drawer-open") !== "false";
  }

  function syncSideTabs(panelId) {
    const sideKey = SIDE_TAB_BY_PANEL[panelId] || null;
    /* Diagram／Git／Settings 無側欄抽屜：內容已在主區 */
    const drawerless =
      sideKey === "diagram" || sideKey === "git" || sideKey === "settings";
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
        const key = panel.getAttribute("data-side-panel");
        const on = !drawerless && sideKey != null && key === sideKey;
        if (on) {
          panel.removeAttribute("hidden");
        } else {
          panel.setAttribute("hidden", "");
        }
      });
    if (drawerless) {
      setSideDrawerOpen(false);
      return;
    }
    if (sideKey) {
      setSideDrawerOpen(true);
    }
  }

  // Git 工作台不需要右側 Inspector：切到 git 時收合，離開時還原先前狀態。
  let inspectorHiddenBeforeGit = false;
  let gitInspectorForced = false;
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
    // Git 工作台不需要右側 Inspector
    if (inspector) {
      const bodyElGit = document.getElementById("shell-body");
      if (panelId === "git") {
        if (!gitInspectorForced) {
          inspectorHiddenBeforeGit = inspector.style.display === "none";
          gitInspectorForced = true;
        }
        inspector.style.display = "none";
        if (bodyElGit) bodyElGit.classList.add("is-inspector-collapsed");
      } else if (gitInspectorForced) {
        gitInspectorForced = false;
        if (!inspectorHiddenBeforeGit) {
          inspector.style.display = "";
          if (bodyElGit) bodyElGit.classList.remove("is-inspector-collapsed");
        }
      }
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
      bootSettingsUxMockIfPresent();
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
    if (panelId === "arch") {
      renderArchDag();
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

  /** Apply EditSession projection to board chrome (primary = first selected). */
  function applyEditProjection(dto) {
    if (!dto || typeof dto !== "object") return;
    const ids = Array.isArray(dto.selected) ? dto.selected : [];
    if (ids.length === 0) {
      selectWorkItem(null, null);
    } else {
      const primary = ids[ids.length - 1];
      let title = primary;
      const boardList = boardTasks(lastBoard);
      const hit = boardList.find(function (t) {
        return t && t.id === primary;
      });
      if (hit && hit.title) title = hit.title;
      selectWorkItem(primary, title);
      document.querySelectorAll(".board-task").forEach(function (el) {
        const on = ids.indexOf(el.dataset.taskId) !== -1;
        el.classList.toggle("is-selected", on);
        el.classList.toggle("selected", on);
        el.setAttribute("aria-selected", on ? "true" : "false");
      });
    }
  }

  async function cmdEditInvoke(invokeName, emptyToast) {
    if (!invoke) {
      toast((emptyToast || "編輯") + " — 需 Tauri IPC（瀏覽器模式 NOT RUN）");
      setStatus("edit.* — 需 Tauri；領域選取經 Command");
      return null;
    }
    try {
      const dto = await invoke(invokeName);
      applyEditProjection(dto);
      const msg =
        (dto && dto.message) ||
        invokeName +
          " · 選取 " +
          ((dto && dto.selected_count) || 0) +
          "／宇宙 " +
          ((dto && dto.universe_count) || 0);
      toast(msg);
      setStatus(msg);
      return dto;
    } catch (err) {
      toast(String(err));
      setStatus(String(err));
      return null;
    }
  }

  function cmdEditUndo() {
    return cmdEditInvoke("edit_undo", "復原");
  }
  function cmdEditRedo() {
    return cmdEditInvoke("edit_redo", "重做");
  }
  function cmdEditSelectAll() {
    return cmdEditInvoke("edit_select_all", "全選變更");
  }
  function cmdEditClear() {
    return cmdEditInvoke("edit_clear", "清除選取");
  }

  function runCommand(cmd, panelHint) {
    try {
      if (cmd === "document.identity") { openDocumentIdentity(); return; }
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
      if (cmd === "uidesign.recovery.clear") {
        if (!isUiDesignWindowOpen()) openUiDesignWindow("designer");
        else setUidesignMode("designer");
        cmdUidesignRecoveryPreview();
        return;
      }
      if (cmd === "uidesign.recovery.confirm") { cmdUidesignRecoveryConfirm(); return; }
      if (cmd === "uidesign.recovery.cancel") {
        designRecoveryPlan = null;
        const recoveryDialog = document.getElementById("uidesign-recovery-dialog");
        if (recoveryDialog && recoveryDialog.open) recoveryDialog.close();
        return;
      }
      if (cmd === "uidesign.recovery.undo") { cmdUidesignRecoveryUndo(); return; }
      if (cmd === "uidesign.recovery.redo") { cmdUidesignRecoveryRedo(); return; }
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
      /* PD-REMAIN-EDIT-01 path C: UI → edit_* Command → DispatchHost → Core. */
      if (cmd === "edit.undo") {
        cmdEditUndo();
        return;
      }
      if (cmd === "edit.redo") {
        cmdEditRedo();
        return;
      }
      if (cmd === "edit.selectAll") {
        cmdEditSelectAll();
        return;
      }
      if (cmd === "edit.clear") {
        cmdEditClear();
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
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "z" || ev.key === "Z") && !ev.shiftKey) {
      ev.preventDefault();
      closeMenus();
      runCommand("edit.undo");
    }
    if (
      ((ev.ctrlKey || ev.metaKey) && (ev.key === "y" || ev.key === "Y")) ||
      ((ev.ctrlKey || ev.metaKey) && ev.shiftKey && (ev.key === "z" || ev.key === "Z"))
    ) {
      ev.preventDefault();
      closeMenus();
      runCommand("edit.redo");
    }
  });

  bootGitUxMockIfPresent("dirty");
  bootSettingsUxMockIfPresent();

  const gitCommitBtn = document.getElementById("git-commit");
  const gitPushBtn = document.getElementById("git-push");
  if (gitCommitBtn && !isGitUxMockMode()) {
    gitCommitBtn.addEventListener("click", function (ev) {
      ev.stopPropagation();
      showGitApprove("commit");
    });
  }
  if (gitPushBtn && !isGitUxMockMode()) {
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
        isSideDrawerOpen()
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

  const ARCH_TREE_W_LS = "sgenaxis.arch.tree.w.v1";
  const ARCH_TREE_W_MIN = 160;
  const ARCH_TREE_W_MAX = 560;
  const ARCH_TREE_W_DEFAULT = 260;

  function archTreeMaxForBody() {
    const body = document.getElementById("arch-panel-body");
    const bw = body ? body.getBoundingClientRect().width : 0;
    if (!bw || bw < 320) return ARCH_TREE_W_MAX;
    /* 至少留給畫布約 200px＋分隔條 */
    return Math.max(
      ARCH_TREE_W_MIN,
      Math.min(ARCH_TREE_W_MAX, Math.floor(bw - 200 - 5))
    );
  }

  function applyArchTreeWidth(px) {
    const max = archTreeMaxForBody();
    const next = clampShellPx(px, ARCH_TREE_W_MIN, max);
    document.documentElement.style.setProperty("--arch-tree-w", next + "px");
    return next;
  }

  function persistArchTreeWidth() {
    try {
      const cs = getComputedStyle(document.documentElement);
      const w =
        parseInt(cs.getPropertyValue("--arch-tree-w"), 10) || ARCH_TREE_W_DEFAULT;
      localStorage.setItem(ARCH_TREE_W_LS, String(w));
    } catch (_e) {
      /* ignore */
    }
  }

  function loadArchTreeWidth() {
    try {
      const raw = localStorage.getItem(ARCH_TREE_W_LS);
      if (!raw) return;
      const n = parseInt(raw, 10);
      if (n) applyArchTreeWidth(n);
    } catch (_e) {
      /* ignore */
    }
  }

  function wireArchTreeSplitter() {
    loadArchTreeWidth();
    const el = document.getElementById("split-arch-tree");
    if (!el) return;
    el.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 0) return;
      ev.preventDefault();
      const cs = getComputedStyle(document.documentElement);
      const startX = ev.clientX;
      const startW =
        parseInt(cs.getPropertyValue("--arch-tree-w"), 10) || ARCH_TREE_W_DEFAULT;
      el.classList.add("is-dragging");
      document.body.classList.add("is-shell-resizing");
      try {
        el.setPointerCapture(ev.pointerId);
      } catch (_e) {
        /* ignore */
      }
      function onMove(e) {
        applyArchTreeWidth(startW + (e.clientX - startX));
      }
      function onUp() {
        el.classList.remove("is-dragging");
        document.body.classList.remove("is-shell-resizing");
        document.removeEventListener("pointermove", onMove);
        document.removeEventListener("pointerup", onUp);
        persistArchTreeWidth();
      }
      document.addEventListener("pointermove", onMove);
      document.addEventListener("pointerup", onUp);
    });
    el.addEventListener("keydown", function (ev) {
      const step = ev.shiftKey ? 24 : 8;
      const cs = getComputedStyle(document.documentElement);
      const w =
        parseInt(cs.getPropertyValue("--arch-tree-w"), 10) || ARCH_TREE_W_DEFAULT;
      if (ev.key === "ArrowLeft") {
        ev.preventDefault();
        applyArchTreeWidth(w - step);
        persistArchTreeWidth();
      }
      if (ev.key === "ArrowRight") {
        ev.preventDefault();
        applyArchTreeWidth(w + step);
        persistArchTreeWidth();
      }
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

  try {
    wireArchTreeSplitter();
  } catch (_archSplit) {
    /* arch panel may be absent */
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

  // PD-WIRE-BOOT-01: 啟動且已有設定 → auto load_local_board＋git（假資料優先）
  try {
    renderBoard(null);
    wireGitIndexCommitUi();
    bootGitUxMockIfPresent("dirty");
    if (!isGitUxMockMode()) {
      renderGitNotRun("啟動中…");
    }
    if (hasIpc) {
      setStatus("就緒 — Tauri command 模式（含 PD-WIRE-BOOT-01）");
      setAgentStatus("Agent：就緒");
      prefBoardPath()
        .then(function (dto) {
          const root = dto && (dto.project_root || "").trim();
          const boardPath = dto && (dto.board_path || "").trim();
          const hasSettings =
            (!!root && !isForbiddenDemoRoot(root)) || !!boardPath;
          if (!hasSettings) {
            const msg = unboundProjectMessage();
            showBoardError(msg);
            setBoardLiveStatus(msg, true);
            if (isGitUxMockMode()) {
              bootGitUxMockIfPresent("dirty");
            } else {
              renderGitNotRun(msg + " — Git NOT RUN");
            }
            setStatus("就緒 — 等待綁定；綁定後自動 load_local_board＋git");
            return null;
          }
          return wireBootLoadProjections({ reason: "boot", quiet: true });
        })
        .catch(function () {
          /* splash still dismisses in finally */
        })
        .then(function () {
          dismissAppSplash({ caption: "Ready" });
        });
    } else {
      setStatus(
        isGitUxMockMode()
          ? "就緒 — 瀏覽器＋Git 假資料（無 IPC）"
          : "就緒 — 瀏覽器導覽／空態（無 IPC）"
      );
      updateToolbarBinding("");
      if (!isGitUxMockMode()) {
        renderGitNotRun("瀏覽器模式：無 IPC → Git NOT RUN");
      }
      const el = document.getElementById("board-path-input");
      if (el && !el.value) el.value = "docs/PROJECT-BOARD.html";
      dismissAppSplash({ caption: "Ready" });
    }
  } catch (err) {
    setStatus("初始化已攔截：" + String(err));
    try {
      if (!isGitUxMockMode()) {
        renderGitNotRun("初始化失敗 → NOT RUN：" + String(err));
      }
    } catch (_e) {
      /* never crash boot */
    }
    dismissAppSplash({ caption: "Ready" });
  }
})();
