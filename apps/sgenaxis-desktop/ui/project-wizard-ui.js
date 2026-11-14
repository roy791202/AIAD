(function (global) {
  "use strict";

  // Six-step project wizard UI (M01-S3). Drives the host `wizard_*` command
  // bridge: wizard_begin -> wizard_apply_step (per step) -> wizard_prepare_preferences
  // -> wizard_commit, carrying the opaque token across steps; wizard_cancel on abort.
  // Same invoke/dialog idiom as project-preferences-ui.js. No JS -> FS; the host
  // owns all filesystem effects and the owner-authority snapshot.

  const invoke = (name, args) => {
    const fn = global.__TAURI__?.core?.invoke || global.__TAURI__?.invoke;
    return fn
      ? fn(name, args)
      : Promise.reject(new Error("新專案精靈需要正式 Tauri IPC；瀏覽器模式不會建立本機專案。"));
  };
  const hasInvoke = () => !!(global.__TAURI__?.core?.invoke || global.__TAURI__?.invoke);

  // Step contract derived from the WORK domain (WizardStep + ProjectDefinition
  // fields exercised by validate_definition / missing_generation_requirements).
  // `key` is the WizardStepDto kebab-case discriminant the host expects.
  const STEPS = [
    {
      key: "basics",
      title: "1／6 基本資料",
      fields: [
        { name: "name", label: "專案名稱（必填）", type: "text" },
        { name: "purpose", label: "專案目的", type: "textarea" },
      ],
    },
    {
      key: "delivery",
      title: "2／6 交付目標",
      fields: [
        { name: "deliveryForm", label: "形式（如 desktop）", type: "text" },
        { name: "deliveryPlatform", label: "平台（如 windows）", type: "text" },
        { name: "deliveryLanguage", label: "語言（如 rust）", type: "text" },
        { name: "deliveryFramework", label: "框架（如 tauri）", type: "text" },
        { name: "deliveryHasUi", label: "包含使用者介面", type: "checkbox" },
      ],
    },
    {
      key: "topology",
      title: "3／6 專案結構",
      fields: [{ name: "topology", label: "結構（如 single-crate）", type: "text" }],
    },
    {
      key: "requirements",
      title: "4／6 需求",
      fields: [
        { name: "requirementIntent", label: "需求意圖", type: "text" },
        { name: "requirementAcceptance", label: "驗收標準（每行一項）", type: "textarea" },
      ],
    },
    {
      key: "technology-ui",
      title: "5／6 技術與 UI",
      fields: [
        { name: "deliveryHost", label: "宿主（如 tauri）", type: "text" },
        { name: "deliveryHostVersion", label: "宿主版本", type: "text" },
        { name: "deliveryToolchain", label: "工具鏈（逗號分隔）", type: "text" },
      ],
    },
    { key: "preview", title: "6／6 預覽與建立", fields: [] },
  ];

  const trimmed = (value) => (value === undefined || value === null ? "" : String(value).trim());

  // Build the per-step WizardDraftPatch (camelCase; host maps by step). Empty
  // text fields are omitted so a blank step is a no-op; `name` is always sent so
  // the host validator runs on the real value.
  function buildPatch(stepKey, collected) {
    const patch = {};
    const put = (key) => {
      const v = trimmed(collected[key]);
      if (v) patch[key] = v;
    };
    if (stepKey === "basics") {
      patch.name = trimmed(collected.name);
      put("purpose");
    } else if (stepKey === "delivery") {
      ["deliveryForm", "deliveryPlatform", "deliveryLanguage", "deliveryFramework"].forEach(put);
      if (collected.deliveryHasUi) patch.deliveryHasUi = true;
    } else if (stepKey === "topology") {
      put("topology");
    } else if (stepKey === "requirements") {
      if (trimmed(collected.requirementIntent)) {
        put("requirementIntent");
        put("requirementAcceptance");
      }
    } else if (stepKey === "technology-ui") {
      ["deliveryHost", "deliveryHostVersion", "deliveryToolchain"].forEach(put);
    }
    return patch;
  }

  function previewText(view) {
    if (!view) return "";
    const lines = [
      "名稱：" + (view.name || "（未命名）"),
      "目的：" + (view.purpose || "（無）"),
      "交付目標：" + (view.deliveryCount || 0) + " 個",
      "結構：" + (view.topology || "（未設定）"),
      "需求：" + (view.requirementCount || 0) + " 項",
    ];
    const missing = view.missingGenerationRequirements || [];
    lines.push(
      missing.length
        ? "尚缺（供後續生成，不影響建立）：" + missing.join("、")
        : "生成所需欄位皆已齊備。"
    );
    return lines.join("\n");
  }

  // Present the modal and drive the lifecycle. Resolves to {status:"ok",path}
  // on commit, or null if the user aborts (host in-flight state is released).
  function presentWizard(token, initialName) {
    const collected = { name: initialName || "" };
    let index = 0;
    let busy = false;
    let lastView = null;

    const dialog = document.createElement("dialog");
    dialog.id = "project-wizard-dialog";
    dialog.setAttribute("aria-label", "新專案精靈");
    dialog.style.cssText = "min-width:420px;max-width:92vw;padding:20px;border:1px solid var(--line,#777);border-radius:12px";
    dialog.innerHTML =
      '<form method="dialog">' +
      '<h2 data-wiz="title" style="margin-top:0"></h2>' +
      '<div data-wiz="fields"></div>' +
      '<pre data-wiz="preview" style="white-space:pre-wrap;background:var(--panel,#1b1b1b);padding:10px;border-radius:8px;display:none"></pre>' +
      '<p role="status" aria-live="polite" data-wiz="status" style="min-height:1.4em;color:var(--accent,#8cf)"></p>' +
      '<menu style="display:flex;gap:8px;justify-content:flex-end;border:0;padding:0;margin:0">' +
      '<button type="button" data-wiz="cancel">取消建立</button>' +
      '<button type="button" data-wiz="back">上一步</button>' +
      '<button type="button" data-wiz="next">下一步</button>' +
      "</menu>" +
      "</form>";
    document.body.appendChild(dialog);

    const q = (sel) => dialog.querySelector('[data-wiz="' + sel + '"]');
    const field = (name) => dialog.querySelector('[data-field="' + name + '"]');
    const setStatus = (msg) => {
      q("status").textContent = msg || "";
    };

    function readFields() {
      for (const f of STEPS[index].fields) {
        const el = field(f.name);
        if (!el) continue;
        collected[f.name] = f.type === "checkbox" ? el.checked : el.value;
      }
    }

    function controls() {
      q("back").disabled = busy || index === 0;
      q("cancel").disabled = busy;
      q("next").disabled = busy;
      const last = index === STEPS.length - 1;
      q("next").textContent = last ? "建立專案" : "下一步";
    }

    function render() {
      const step = STEPS[index];
      q("title").textContent = step.title;
      const fieldsHost = q("fields");
      fieldsHost.innerHTML = "";
      for (const f of step.fields) {
        const row = document.createElement("label");
        row.style.cssText = "display:flex;flex-direction:column;margin:10px 0;gap:4px";
        row.textContent = f.label;
        let el;
        if (f.type === "textarea") {
          el = document.createElement("textarea");
          el.rows = 3;
        } else if (f.type === "checkbox") {
          row.style.flexDirection = "row";
          row.style.alignItems = "center";
          el = document.createElement("input");
          el.type = "checkbox";
          el.checked = !!collected[f.name];
        } else {
          el = document.createElement("input");
          el.type = "text";
        }
        el.dataset.field = f.name;
        if (f.type !== "checkbox") el.value = collected[f.name] || "";
        row.appendChild(el);
        fieldsHost.appendChild(row);
      }
      const preview = q("preview");
      if (step.key === "preview") {
        preview.style.display = "block";
        preview.textContent = previewText(lastView);
      } else {
        preview.style.display = "none";
      }
      setStatus("");
      controls();
    }

    return new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        dialog.close();
        dialog.remove();
        resolve(value);
      };

      async function abort(reason) {
        if (busy) return;
        busy = true;
        controls();
        try {
          await invoke("wizard_cancel", { args: { token } });
        } catch (_) {
          /* best-effort release; host drops unknown tokens anyway */
        }
        if (reason) setStatus(reason);
        finish(null);
      }

      async function applyCurrentStep() {
        readFields();
        const step = STEPS[index];
        const patch = buildPatch(step.key, collected);
        const res = await invoke("wizard_apply_step", {
          args: { token, step: step.key, patch },
        });
        lastView = res.view;
        return res;
      }

      async function commit() {
        // Preferences reuse the existing new-project chooser (skip/preset/import).
        const chooser = global.ProjectPreferencesUI && global.ProjectPreferencesUI.chooseNewProject;
        let choice = { presetId: null, importedJson: null };
        if (chooser) {
          const picked = await chooser();
          if (!picked) {
            setStatus("已取消偏好設定，尚未建立專案。");
            return null;
          }
          choice = picked;
        }
        const prepareArgs = { token };
        if (choice.importedJson) {
          prepareArgs.choice = "import";
          prepareArgs.importedJson = choice.importedJson;
        } else if (choice.presetId) {
          prepareArgs.choice = "preset";
          prepareArgs.presetId = choice.presetId;
        } else {
          prepareArgs.choice = "skip";
        }
        await invoke("wizard_prepare_preferences", { args: prepareArgs });
        const receipt = await invoke("wizard_commit", { args: { token } });
        return { status: "ok", path: receipt.projectRoot };
      }

      async function onNext() {
        if (busy) return;
        busy = true;
        controls();
        try {
          const res = await applyCurrentStep();
          const last = index === STEPS.length - 1;
          if (!res.validation.ok) {
            const bad = res.validation.invalidField || "輸入";
            setStatus("此步驟驗證未通過（" + bad + "）。請修正後再繼續。");
            // Basics name is required; other steps may still advance with partial data.
            if (STEPS[index].key === "basics") {
              busy = false;
              controls();
              return;
            }
          }
          if (last) {
            const result = await commit();
            if (result) {
              finish(result);
              return;
            }
          } else {
            index += 1;
            render();
          }
        } catch (err) {
          setStatus("步驟失敗：" + String(err));
        } finally {
          if (!settled) {
            busy = false;
            controls();
          }
        }
      }

      q("next").onclick = onNext;
      q("back").onclick = () => {
        if (busy || index === 0) return;
        readFields();
        index -= 1;
        render();
      };
      q("cancel").onclick = () => abort("已取消新增專案。");
      dialog.addEventListener("cancel", (e) => {
        // Esc / native dismiss → treat as abort (release host state).
        e.preventDefault();
        abort("已取消新增專案。");
      });

      render();
      dialog.showModal();
    });
  }

  /**
   * Launch the six-step wizard for a new project under `parent` with the given
   * `name`. Returns {status:"ok", path} after a successful commit, or null if
   * the user cancels. The caller (app.js) binds the returned path like any
   * open/new project pick.
   */
  async function run(opts) {
    const parent = trimmed(opts && opts.parent);
    const name = trimmed(opts && opts.name);
    if (!hasInvoke()) {
      global.alert("新專案精靈需要正式 Tauri IPC（瀏覽器模式無法建立本機專案）。");
      return null;
    }
    if (!parent || !name) {
      global.alert("新增專案需要父資料夾與專案名稱。");
      return null;
    }
    let begin;
    try {
      begin = await invoke("wizard_begin", {
        args: { locationKind: "new", parent, name, purpose: "" },
      });
    } catch (err) {
      global.alert("無法開始新專案精靈：" + String(err));
      return null;
    }
    return presentWizard(begin.token, name);
  }

  const api = { run, buildPatch, previewText, STEPS };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  global.ProjectWizardUI = api;
})(typeof window !== "undefined" ? window : globalThis);
