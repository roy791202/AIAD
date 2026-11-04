# -*- coding: utf-8 -*-
"""Extract EluSlot_Settings.html into scoped desktop mock assets."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
UX = ROOT / "docs" / "Final-2026-10-25" / "EluSlot_Settings.html"
OUT_JS = Path(__file__).resolve().parent / "settings-ux-mock.js"
OUT_CSS = Path(__file__).resolve().parent / "settings-ux-mock.css"

html = UX.read_text(encoding="utf-8")
style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
script = re.search(r"<script>(.*?)</script>\s*</body>", html, re.S).group(1)

style = re.sub(r":root\{[^}]+\}", "", style, count=1)
style = re.sub(r"\*\{box-sizing:[^}]+\}", "", style)
style = re.sub(r"body\{[^}]+\}", "", style)
style = re.sub(r"body\[data-theme=lavender\]\{[^}]+\}", "", style)
style = re.sub(r"body\[data-theme=light\]\{[^}]+\}", "", style)
style = re.sub(r"body\[data-density=compact\]\{[^}]+\}", "", style)


def scope_css(block: str) -> str:
    out = []
    i = 0
    n = len(block)
    while i < n:
        while i < n and block[i].isspace():
            i += 1
        if i >= n:
            break
        if block.startswith("@media", i):
            brace = block.find("{", i)
            depth = 0
            j = brace
            while j < n:
                if block[j] == "{":
                    depth += 1
                elif block[j] == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            head = block[i:brace]
            inner = block[brace + 1 : j - 1]
            out.append(f"{head}{{{scope_css(inner)}}}")
            i = j
            continue
        brace = block.find("{", i)
        if brace < 0:
            break
        sel = block[i:brace].strip()
        depth = 0
        j = brace
        while j < n:
            if block[j] == "{":
                depth += 1
            elif block[j] == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        body = block[brace:j]
        if not sel:
            i = j
            continue
        if sel.startswith("dialog"):
            sel = sel.replace("dialog", "#settings-ux-dialog", 1)
            out.append(sel + body)
        elif sel.startswith(".toast"):
            sel = sel.replace(".toast", "#settings-ux-toast", 1)
            out.append(sel + body)
        elif sel.startswith(".sr"):
            out.append(f"#settings-ux-root {sel}, #settings-ux-dialog {sel}" + body)
        else:
            parts = [p.strip() for p in sel.split(",") if p.strip()]
            scoped = []
            for p in parts:
                if p.startswith("#settings-ux-root") or p.startswith("@"):
                    scoped.append(p)
                elif p.startswith("body"):
                    scoped.append(p.replace("body", "#settings-ux-root", 1))
                else:
                    scoped.append(f"#settings-ux-root {p}")
            out.append(", ".join(scoped) + body)
        i = j
    return "\n".join(out)


css_header = """\
/* From docs/Final-2026-10-25/EluSlot_Settings.html — scoped under #settings-ux-root */
#settings-ux-root {
  --bg: var(--bg-window, #111217);
  --surface: var(--bg-panel, #191b22);
  --raised: var(--bg-raised, #23252e);
  --input: #15171d;
  --line: var(--border-soft, #333640);
  --text: var(--text, #ececf5);
  --muted: var(--text-secondary, #a0a5b8);
  --accent: var(--accent, #baa3f0);
  --accentbg: #332b45;
  --success: var(--green, #8ed5b0);
  --danger: var(--red, #f1a4b5);
  --font: 14px;
  --rowspace: 18px;
  color: var(--text);
  font: var(--font)/1.6 inherit;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--bg);
}
#settings-ux-root[data-theme="lavender"] {
  --bg: #17141f; --surface: #201c29; --raised: #2b2536; --input: #191620; --line: #40364c;
}
#settings-ux-root[data-theme="light"] {
  color-scheme: light;
  --bg: #f4f4f8; --surface: #fff; --raised: #eeeef5; --input: #fafafd; --line: #d9d9e5;
  --text: #292434; --muted: #686277; --accent: #7752b4; --accentbg: #eee6f9;
  --success: #2c7d55; --danger: #b43b5c;
}
#settings-ux-root[data-density="compact"] { --rowspace: 11px; }
#settings-ux-root * { box-sizing: border-box; }
#settings-ux-root .shell { flex: 1; min-height: 0; height: auto !important; }
#settings-ux-root .sidebar,
#settings-ux-root .inspector { height: auto !important; max-height: 100%; }
#panel-settings { padding: 0; overflow: hidden; }
#panel-settings.active { display: flex; flex-direction: column; }
#settings-ux-dialog button, #settings-ux-dialog input, #settings-ux-dialog select, #settings-ux-dialog textarea {
  font: inherit; color: inherit;
}
#settings-ux-dialog button {
  cursor: pointer; border: 1px solid #333640; border-radius: 6px; padding: 7px 12px; background: #23252e;
}
#settings-ux-dialog button.primary { background: #baa3f0; border-color: #baa3f0; color: #21192c; font-weight: 650; }
#settings-ux-dialog button.danger { color: #f1a4b5; border-color: #f1a4b5; }
#settings-ux-dialog .quiet { background: transparent; }
"""

OUT_CSS.write_text(css_header + "\n" + scope_css(style), encoding="utf-8")

# Drop original $ / $$ / esc line — we provide our own
script_body = re.sub(
    r"const \$=s=>document\.querySelector\(s\),\s*\$\$=s=>\[\.\.\.document\.querySelectorAll\(s\)\],esc=s=>String\(s\?\?''\)\.replace\(/\[&<>\"'\]/g,c=>\(\{'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',\"'\":'&#39;'\}\[c\]\)\);\s*",
    "",
    script,
    count=1,
)

# ID remaps (string form used in $() and HTML templates)
pairs = [
    ("'#toast'", "'#settings-ux-toast'"),
    ('"#toast"', '"#settings-ux-toast"'),
    ("'#dialog'", "'#settings-ux-dialog'"),
    ("'#dialogTitle'", "'#settings-ux-dialog-title'"),
    ("'#dialogBody'", "'#settings-ux-dialog-body'"),
    ("'#dialogFoot'", "'#settings-ux-dialog-foot'"),
    ("'#closeDialog'", "'#settings-ux-close-dialog'"),
    ("'#search'", "'#settings-ux-search'"),
    ("'#categories'", "'#settings-ux-categories'"),
    ("'#breadcrumb'", "'#settings-ux-breadcrumb'"),
    ("'#title'", "'#settings-ux-title'"),
    ("'#description'", "'#settings-ux-description'"),
    ("'#scopeHint'", "'#settings-ux-scope-hint'"),
    ("'#content'", "'#settings-ux-content'"),
    ("'#saveStatus'", "'#settings-ux-save-status'"),
    ("'#pageDirty'", "'#settings-ux-page-dirty'"),
    ("'#save'", "'#settings-ux-save'"),
    ("'#review'", "'#settings-ux-review'"),
    ("'#resetPage'", "'#settings-ux-reset-page'"),
    ("'#revert'", "'#settings-ux-revert'"),
    ("'#export'", "'#settings-ux-export'"),
    ("'#importFile'", "'#settings-ux-import-file'"),
    ("'#inspector'", "'#settings-ux-inspector'"),
    ("'#guide'", "'#settings-ux-guide'"),
    ('id="search"', 'id="settings-ux-search"'),
    ('id="serverSelect"', 'id="settings-ux-server-select"'),
    ('id="test-cli"', 'id="settings-ux-test-cli"'),
    ('id="test-mcp"', 'id="settings-ux-test-mcp"'),
    ('id="result-cli"', 'id="settings-ux-result-cli"'),
    ('id="result-mcp"', 'id="settings-ux-result-mcp"'),
    ("el.id==='serverSelect'", "el.id==='settings-ux-server-select'"),
    ("'#test-'+kind", "'#settings-ux-test-'+kind"),
    ("'#result-'+kind", "'#settings-ux-result-'+kind"),
    ("'[id=\"result-cli\"],[id=\"result-mcp\"]'", "'[id=\"settings-ux-result-cli\"],[id=\"settings-ux-result-mcp\"]'"),
    ("KEY='EluSlot.Settings.Prototype.v1'", "KEY='EluSlot.Settings.DesktopMock.v1'"),
    ("document.body.dataset.theme", "(__settingsRoot=document.querySelector('#settings-ux-root'))&&(__settingsRoot.dataset.theme"),
]

# Fix preview more carefully
script_body = script_body.replace(
    "function preview(){const t=get('ui.theme','session'),a=get('ui.accent','session');document.body.dataset.theme=t;document.body.dataset.density=get('ui.density','session');const colors=",
    "function preview(){const root=document.querySelector('#settings-ux-root');if(!root)return;const t=get('ui.theme','session'),a=get('ui.accent','session');root.dataset.theme=t;root.dataset.density=get('ui.density','session');const colors=",
)

for a, b in pairs:
    script_body = script_body.replace(a, b)

# Cut off document event wiring + load();render(); — reimplemented in boot
cut = script_body.find("document.addEventListener('click'")
if cut < 0:
    cut = script_body.find('document.addEventListener("click"')
if cut > 0:
    script_body = script_body[:cut]

prefix = r'''/* EluSlot Settings UX mock — docs/Final-2026-10-25/EluSlot_Settings.html */
(function (global) {
"use strict";
const ROOT_SEL = "#settings-ux-root";
function $(s) {
  const globals = {
    "#settings-ux-toast": 1,
    "#settings-ux-dialog": 1,
    "#settings-ux-dialog-title": 1,
    "#settings-ux-dialog-body": 1,
    "#settings-ux-dialog-foot": 1,
    "#settings-ux-close-dialog": 1,
    "#settings-ux-import-file": 1,
  };
  if (globals[s]) return document.querySelector(s);
  const root = document.querySelector(ROOT_SEL);
  if (!root) return null;
  return root.querySelector(s);
}
function $$(s) {
  const root = document.querySelector(ROOT_SEL);
  return root ? [...root.querySelectorAll(s)] : [];
}
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
'''

suffix = r'''
function syncHostBridge() {
  try {
    const setVal = (id, v) => {
      const el = document.getElementById(id);
      if (el && v != null) el.value = String(v);
    };
    setVal("settings-project-root", get("project.root", "project"));
    setVal("settings-board-path", get("project.board", "project"));
    setVal("cli-claude-path", get("agent.claudePath", "personal"));
    setVal("cli-cursor-path", get("agent.cursorPath", "personal"));
    setVal("cli-codex-path", get("agent.codexPath", "personal"));
    setVal("cli-antigravity-path", get("agent.antigravityPath", "personal"));
    const provider = get("agent.provider", "project");
    const sel = document.getElementById("cli-selected");
    if (sel) {
      sel.value =
        { claude: "claude", cursor: "cursor-agent", codex: "codex", antigravity: "antigravity" }[
          provider
        ] || "claude";
    }
    const mode = get("advanced.mode", "session");
    const dry = document.getElementById("mode-dry-run");
    const live = document.getElementById("mode-live");
    if (dry && live) {
      dry.checked = mode !== "live";
      live.checked = mode === "live";
    }
    const badge = document.getElementById("settings-mode-badge");
    if (badge) {
      badge.textContent = mode === "live" ? "Live" : "DryRun";
      badge.dataset.mode = mode === "live" ? "live" : "dry-run";
    }
  } catch (_e) {}
}

const __render = render;
render = function () {
  __render();
  syncHostBridge();
};

function bootSettingsUxMock() {
  if (!document.querySelector(ROOT_SEL)) return;
  if (!bootSettingsUxMock._wired) {
    document.addEventListener("click", function (e) {
      const el = e.target.closest("button");
      if (!el || el.disabled) return;
      const inRoot = el.closest(ROOT_SEL);
      const inDialog = el.closest("#settings-ux-dialog");
      if (!inRoot && !inDialog) return;
      if (el.dataset.category) {
        category = el.dataset.category;
        search = "";
        const s = $("#settings-ux-search");
        if (s) s.value = "";
        render();
        return;
      }
      if (el.dataset.scope) {
        scope = el.dataset.scope;
        lastTest = {};
        render();
        return;
      }
      if (el.dataset.key && byKey[el.dataset.key] && byKey[el.dataset.key].type === "toggle") {
        const key = el.dataset.key;
        updateField(key, !get(key));
        render();
        document.getElementById("f-" + key)?.focus();
        return;
      }
      if (el.dataset.inherit) {
        delete draft[scope][el.dataset.inherit];
        render();
        return;
      }
      if (el.dataset.info) {
        selectedKey = el.dataset.info;
        paintInspector();
        show(byKey[selectedKey].label, inspectorHTML(byKey[selectedKey]));
        return;
      }
      if (el.dataset.test) {
        test(el.dataset.test);
        return;
      }
      if (el.dataset.action) {
        action(el.dataset.action);
        return;
      }
      if (el.hasAttribute("data-close")) {
        close();
        return;
      }
      if (el.hasAttribute("data-confirm")) {
        const fn = dialogAction;
        if (fn) fn();
      }
    });
    document.addEventListener("focusin", function (e) {
      if (!e.target.closest || !e.target.closest(ROOT_SEL)) return;
      const key =
        e.target.dataset.key || e.target.closest("[data-setting]")?.dataset.setting;
      if (key && byKey[key]) {
        selectedKey = key;
        paintInspector();
      }
    });
    document.addEventListener("input", function (e) {
      const el = e.target;
      if (!el.closest || (!el.closest(ROOT_SEL) && !el.closest("#settings-ux-dialog")))
        return;
      if (el.dataset.key && el.tagName !== "SELECT" && byKey[el.dataset.key].type !== "toggle")
        updateField(
          el.dataset.key,
          byKey[el.dataset.key].type === "number"
            ? el.value === ""
              ? null
              : Number(el.value)
            : el.value
        );
      if (
        el.dataset.server &&
        el.tagName !== "SELECT" &&
        el.type !== "checkbox"
      )
        serverChange(el.dataset.server, el.value);
    });
    document.addEventListener("change", function (e) {
      const el = e.target;
      if (!el.closest || (!el.closest(ROOT_SEL) && !el.closest("#settings-ux-dialog")))
        return;
      if (el.dataset.key && el.tagName === "SELECT") {
        updateField(el.dataset.key, el.value);
        render();
      }
      if (el.dataset.server && (el.tagName === "SELECT" || el.type === "checkbox")) {
        serverChange(el.dataset.server, el.type === "checkbox" ? el.checked : el.value);
        render();
      }
      if (el.id === "settings-ux-server-select") {
        selectedServer = el.value;
        lastTest = {};
        render();
      }
    });
    const bind = (id, fn) => {
      const el = $(id);
      if (el) el.onclick = fn;
    };
    const searchEl = $("#settings-ux-search");
    if (searchEl)
      searchEl.oninput = function (e) {
        search = e.target.value.trim();
        render();
      };
    bind("#settings-ux-save", save);
    bind("#settings-ux-review", showReview);
    bind("#settings-ux-reset-page", function () {
      confirmReset(false);
    });
    bind("#settings-ux-revert", function () {
      dialogAction = function () {
        draft[scope] = clone(saved[scope]);
        lastTest = {};
        close();
        render();
        toast("已放棄目前範圍的未儲存變更。");
      };
      show(
        "放棄變更",
        "<p>只放棄「" + scopeNames[scope] + "」尚未儲存的變更；其他範圍會保留。</p>",
        '<button data-close>返回</button><button data-confirm class="danger">放棄此範圍變更</button>'
      );
    });
    bind("#settings-ux-export", download);
    bind("#settings-ux-close-dialog", close);
    bind("#settings-ux-guide", function () {
      show(
        "使用指引",
        "<p>左側分類／搜尋 → 個人／專案／工作階段覆寫 → 儲存。外觀即時預覽；CLI／MCP 僅模擬。密鑰不在此頁輸入。</p>"
      );
    });
    const dialog = $("#settings-ux-dialog");
    if (dialog)
      dialog.addEventListener("cancel", function (e) {
        e.preventDefault();
        close();
      });
    const importFile = $("#settings-ux-import-file");
    if (importFile)
      importFile.onchange = function (e) {
        const file = e.target.files && e.target.files[0];
        if (!file) return;
        if (file.size > 1024 * 1024) {
          show("無法匯入", "<p>設定檔超過 1 MiB。</p>");
          return;
        }
        const reader = new FileReader();
        reader.onload = function () {
          importText(String(reader.result));
        };
        reader.onerror = function () {
          show("無法讀取設定檔", "<p>請重新選擇檔案。</p>");
        };
        reader.readAsText(file);
        e.target.value = "";
      };
    bootSettingsUxMock._wired = true;
  }
  load();
  render();
}

global.EluSlotSettingsUxMock = {
  boot: bootSettingsUxMock,
  render: function () {
    render();
  },
  getDraft: function () {
    return draft;
  },
};
})(typeof window !== "undefined" ? window : globalThis);
'''

OUT_JS.write_text(prefix + "\n" + script_body + "\n" + suffix, encoding="utf-8")
print("OK CSS", OUT_CSS.stat().st_size, "JS", OUT_JS.stat().st_size)
