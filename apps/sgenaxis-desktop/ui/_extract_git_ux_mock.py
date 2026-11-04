# -*- coding: utf-8 -*-
"""One-shot: extract EluSlot_Git_UX.html prototype into scoped desktop mock assets."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]  # AIAD
UX = ROOT / "docs" / "EluSlot_Git_UX.html"
OUT_JS = Path(__file__).resolve().parent / "git-ux-mock.js"
OUT_CSS = Path(__file__).resolve().parent / "git-ux-mock.css"

html = UX.read_text(encoding="utf-8")
style = re.search(r"<style>(.*?)</style>", html, re.S).group(1)
script = re.search(r"<script>(.*?)</script>\s*</body>", html, re.S).group(1)

# Drop doc-only chrome styles that fight the shell; keep prototype UI styles.
# Prefix common prototype class selectors under #panel-git for isolation where needed.
# The mock mounts inside #git-ux-root; use that as scope for body-like rules.

css_header = """\
/* Auto-extracted from docs/EluSlot_Git_UX.html — EluSlot Git mock workbench.
 * Scoped under #git-ux-root. Do not edit by hand; re-run _extract_git_ux_mock.py.
 */
#git-ux-root {
  --git-bg: var(--bg-window, #121319);
  --git-panel: var(--bg-panel, #1c1e27);
  --git-raised: var(--bg-raised, #262835);
  --git-line: var(--border-soft, #363947);
  --git-text: var(--text, #ecebf5);
  --git-muted: var(--text-secondary, #a4a7b9);
  --git-purple: var(--accent, #baa5ff);
  --git-green: var(--green, #8cdcb0);
  --git-red: var(--red, #ffabb4);
  color: var(--git-text);
  font: 14px/1.6 inherit;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
#git-ux-root * { box-sizing: border-box; }
#git-ux-root button,
#git-ux-root input,
#git-ux-root select,
#git-ux-root textarea { font: inherit; color: inherit; }
#git-ux-root button {
  border: 1px solid var(--git-line);
  border-radius: 6px;
  padding: 7px 11px;
  background: var(--git-raised);
  cursor: pointer;
}
#git-ux-root button:hover { background: #383147; border-color: #a58cdd; }
#git-ux-root button:disabled { opacity: .4; cursor: not-allowed; }
#git-ux-root button:focus-visible,
#git-ux-root input:focus-visible,
#git-ux-root textarea:focus-visible,
#git-ux-root select:focus-visible {
  outline: 2px solid var(--git-purple);
  outline-offset: 3px;
}
#git-ux-root input,
#git-ux-root textarea,
#git-ux-root select {
  border: 1px solid #4b4f61;
  border-radius: 5px;
  background: #14151d;
  padding: 9px;
  max-width: 100%;
}
#git-ux-root textarea { width: 100%; min-height: 90px; resize: vertical; }
#git-ux-root input[type=checkbox] { accent-color: #9d7fe9; }
#git-ux-root h1,#git-ux-root h2,#git-ux-root h3,#git-ux-root p { margin-top: 0; }
#git-ux-root h2 { font-size: 19px; }
#git-ux-root h3 { font-size: 14px; }
#git-ux-root small,
#git-ux-root .muted { color: var(--git-muted); }
#git-ux-root a { color: #ccbbff; }
#git-ux-root pre,
#git-ux-root code,
#git-ux-root .mono {
  font-family: Consolas, "Cascadia Code", var(--font-mono, monospace);
  font-size: 12px;
}
#git-ux-root pre {
  padding: 13px;
  background: #12131a;
  border: 1px solid var(--git-line);
  border-radius: 6px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  line-height: 1.8;
}
#git-ux-root .spacer { flex: 1; }
#git-ux-root .row { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
#git-ux-root .primary { background: #8c70d5; border-color: #bda7f0; color: #fff; }
#git-ux-root .danger { color: #ffc1c9; border-color: #884c59; }
#git-ux-root .quiet { background: transparent; }
#git-ux-root .activebtn {
  background: #373047 !important;
  border-color: #ad92e7 !important;
  color: #e4d8ff;
}
#git-ux-root .controls { margin-bottom: 10px; flex-shrink: 0; }
#git-ux-root .app {
  border: 1px solid #424451;
  border-radius: 9px;
  overflow: hidden;
  background: #171820;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
#git-ux-root .repobar {
  padding: 12px;
  border-bottom: 1px solid var(--git-line);
  background: #20212b;
  flex-shrink: 0;
}
#git-ux-root .workspace {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  flex: 1;
  min-height: 0;
}
#git-ux-root .rail {
  padding: 14px 8px;
  background: #1c1d26;
  border-right: 1px solid var(--git-line);
  overflow: auto;
}
#git-ux-root .rail button {
  display: block;
  width: 100%;
  margin-bottom: 5px;
  text-align: left;
  background: transparent;
  border-color: transparent;
  padding: 10px;
}
#git-ux-root .rail .caption {
  padding: 10px;
  color: var(--git-muted);
  font-size: 11px;
  letter-spacing: 1px;
}
#git-ux-root .view {
  padding: 17px;
  min-width: 0;
  overflow: auto;
}
#git-ux-root .viewbar { margin-bottom: 14px; }
#git-ux-root .viewbar h2 { margin: 0; }
#git-ux-root .split {
  display: grid;
  grid-template-columns: 265px minmax(0, 1fr);
  gap: 14px;
}
#git-ux-root .panel {
  border: 1px solid var(--git-line);
  border-radius: 7px;
  overflow: hidden;
  background: #1d202a;
  display: block;
  padding: 0;
  flex: none;
  min-height: 0;
}
#git-ux-root .panelhead {
  padding: 11px;
  background: #252733;
  border-bottom: 1px solid var(--git-line);
  font-size: 13px;
  font-weight: 600;
}
#git-ux-root .file {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 7px;
  border-bottom: 1px solid #303340;
}
#git-ux-root .file.selected { background: #342d46; }
#git-ux-root .file .pick {
  flex: 1;
  min-width: 0;
  text-align: left;
  background: transparent;
  border-color: transparent;
  padding: 6px 2px;
  font-size: 12px;
  overflow-wrap: anywhere;
}
#git-ux-root .file .tiny { padding: 4px 7px; font-size: 12px; }
#git-ux-root .status {
  color: var(--git-purple);
  font: 11px Consolas, monospace;
  padding: 3px;
  border: 1px solid #71608f;
  border-radius: 3px;
}
#git-ux-root .diff { min-height: 300px; overflow: auto; }
#git-ux-root .diffrow {
  display: grid;
  grid-template-columns: 30px 20px minmax(410px, 1fr);
  font: 12px/2 Consolas, monospace;
  white-space: pre;
}
#git-ux-root .diffrow > * { padding: 0 7px; }
#git-ux-root .add { background: #193428; }
#git-ux-root .del { background: #3e2630; }
#git-ux-root .add b { color: var(--git-green); }
#git-ux-root .del b { color: var(--git-red); }
#git-ux-root .num { color: #969fb4; background: #1d222e; }
#git-ux-root .diffparallel {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 3px;
}
#git-ux-root .diffparallel > div { overflow: auto; }
#git-ux-root .commit {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 210px;
  gap: 16px;
  margin-top: 14px;
  padding: 15px;
  border: 1px solid var(--git-line);
  border-radius: 7px;
  background: #20222e;
}
#git-ux-root .commit textarea { min-height: 74px; }
#git-ux-root .commit p { font-size: 12px; }
#git-ux-root .commit .primary { width: 100%; margin-top: 10px; }
#git-ux-root .banner {
  border: 1px solid #60516e;
  background: #292334;
  padding: 12px 14px;
  border-radius: 6px;
  margin-bottom: 13px;
  font-size: 13px;
}
#git-ux-root .banner.error {
  border-color: #995765;
  background: #302029;
}
#git-ux-root .count {
  display: inline-block;
  background: #3a324c;
  color: #e1d0ff;
  border-radius: 4px;
  font-size: 11px;
  padding: 1px 6px;
}
#git-ux-root .empty {
  text-align: center;
  padding: 70px 20px;
  min-height: 280px;
  border: none;
  background: transparent;
}
#git-ux-root .empty p {
  max-width: 550px;
  margin: 12px auto;
  color: var(--git-muted);
}
#git-ux-root .grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
#git-ux-root .card {
  border: 1px solid var(--git-line);
  background: #1c1e27;
  padding: 18px;
  border-radius: 7px;
  margin-bottom: 14px;
}
#git-ux-root .field { display: grid; gap: 7px; margin: 12px 0; }
#git-ux-root .field input,
#git-ux-root .field select { width: 100%; }
#git-ux-root .footer {
  padding: 9px 15px;
  border-top: 1px solid var(--git-line);
  color: var(--git-muted);
  font-size: 12px;
  flex-shrink: 0;
}
#git-ux-root .logs {
  max-height: 140px;
  overflow: auto;
  font: 12px/1.9 Consolas, monospace;
  padding: 12px;
}
#git-ux-root .logwrap { border-top: 1px solid var(--git-line); flex-shrink: 0; }
#git-ux-root summary { cursor: pointer; padding: 11px; }
#git-ux-root .tag { color: var(--git-purple); font-size: 12px; }
#git-ux-root .pass { color: var(--git-green); }
#git-ux-root .fail { color: var(--git-red); }
#git-ux-root .highlight {
  outline: 2px dashed var(--git-purple);
  outline-offset: 3px;
}
#git-ux-root .triple {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 9px;
}
#git-ux-root .triple textarea {
  min-height: 150px;
  font: 12px/1.8 Consolas, monospace;
}
#git-ux-root .historyfilter { min-width: 150px; }
"""

# Append remaining specialized blocks from original style (conflict/history),
# rewriting :root vars and scoping under #git-ux-root.
extra = style
# Strip :root and global resets already covered
extra = re.sub(r":root\{[^}]+\}", "", extra)
extra = re.sub(r"\*\{box-sizing:[^}]+\}", "", extra)
extra = re.sub(r"body\{[^}]+\}", "", extra)
extra = re.sub(r"button,input,select,textarea\{[^}]+\}", "", extra)
extra = re.sub(r"button\{[^}]+\}", "", extra, count=1)
extra = re.sub(r"button:hover\{[^}]+\}", "", extra)
extra = re.sub(r"button:disabled\{[^}]+\}", "", extra)
extra = re.sub(r"button:focus-visible,input:focus-visible,textarea:focus-visible,select:focus-visible,a:focus-visible\{[^}]+\}", "", extra)
extra = re.sub(r"input,textarea,select\{[^}]+\}", "", extra)
extra = re.sub(r"textarea\{[^}]+\}", "", extra, count=1)
extra = re.sub(r"input\[type=checkbox\]\{[^}]+\}", "", extra)
extra = re.sub(r"h1,h2,h3,p\{[^}]+\}", "", extra)
extra = re.sub(r"h1\{[^}]+\}", "", extra)
extra = re.sub(r"h2\{[^}]+\}", "", extra)
extra = re.sub(r"h3\{[^}]+\}", "", extra)
extra = re.sub(r"small,\.muted\{[^}]+\}", "", extra)
extra = re.sub(r"a\{[^}]+\}", "", extra)
extra = re.sub(r"pre,code,\.mono\{[^}]+\}", "", extra)
extra = re.sub(r"pre\{[^}]+\}", "", extra, count=1)
extra = re.sub(r"code\{[^}]+\}", "", extra)
extra = re.sub(r"header\{[^}]+\}", "", extra)
extra = re.sub(r"\.brand\{[^}]+\}", "", extra)
extra = re.sub(r"\.brand span\{[^}]+\}", "", extra)
extra = re.sub(r"\.docnav\{[^}]+\}", "", extra)
extra = re.sub(r"\.intro\{[^}]+\}", "", extra)
extra = re.sub(r"\.intro p\{[^}]+\}", "", extra)
extra = re.sub(r"main\{[^}]+\}", "", extra)
extra = re.sub(r"\.page\{[^}]+\}", "", extra)
extra = re.sub(r"\.page\.active\{[^}]+\}", "", extra)
extra = re.sub(r"dialog\{[^}]+\}", "", extra)
extra = re.sub(r"dialog::backdrop\{[^}]+\}", "", extra)
extra = re.sub(r"\.dialoghead\{[^}]+\}", "", extra)
extra = re.sub(r"\.dialoghead h2\{[^}]+\}", "", extra)
extra = re.sub(r"\.dialogbody\{[^}]+\}", "", extra)
extra = re.sub(r"\.dialogfoot\{[^}]+\}", "", extra)
extra = re.sub(r"\.toast\{[^}]+\}", "", extra)
extra = re.sub(r"\.diagram\{[^}]+\}", "", extra)
extra = re.sub(r"\.diagram>div\{[^}]+\}", "", extra)
extra = re.sub(r"\.flow button\{[^}]+\}", "", extra)
extra = re.sub(r"\.tablewrap\{[^}]+\}", "", extra)
extra = re.sub(r"table\{[^}]+\}", "", extra)
extra = re.sub(r"td,th\{[^}]+\}", "", extra)
extra = re.sub(r"th\{[^}]+\}", "", extra)
extra = re.sub(r"td button\{[^}]+\}", "", extra)
extra = re.sub(r"td \.row\{[^}]+\}", "", extra)
extra = re.sub(r"tr:hover td\{[^}]+\}", "", extra)
extra = re.sub(r"#search\{[^}]+\}", "", extra)
extra = re.sub(r"\.alignright\{[^}]+\}", "", extra)
extra = re.sub(r"@media print\{.*?\}", "", extra, flags=re.S)
# Replace var(--*) already mapped; keep as-is for purple/green/red/line/muted/text/bg
# Scope selectors: prepend #git-ux-root to top-level rules that aren't @media
# Simpler: wrap conflict/history blocks by extracting from .conflictbar onward

m = re.search(r"(\.conflictbar\{.*)$", extra, re.S)
tail = m.group(1) if m else ""
# Also keep .app through .logs from original if our header missed media queries
media = "\n".join(
    re.findall(r"@media[^{]+\{(?:[^{}]|\{[^{}]*\})*\}", extra)
)

def scope_css(block: str) -> str:
    out = []
    i = 0
    while i < len(block):
        if block.startswith("@media", i):
            # find matching brace
            start = i
            brace = block.find("{", i)
            depth = 0
            j = brace
            while j < len(block):
                if block[j] == "{":
                    depth += 1
                elif block[j] == "}":
                    depth -= 1
                    if depth == 0:
                        j += 1
                        break
                j += 1
            chunk = block[start:j]
            # scope inner selectors roughly
            head, body = chunk.split("{", 1)
            body = body.rsplit("}", 1)[0]
            scoped_body = scope_css(body)
            out.append(f"{head}{{{scoped_body}}}")
            i = j
            continue
        # rule
        brace = block.find("{", i)
        if brace < 0:
            break
        sel = block[i:brace].strip()
        depth = 0
        j = brace
        while j < len(block):
            if block[j] == "{":
                depth += 1
            elif block[j] == "}":
                depth -= 1
                if depth == 0:
                    j += 1
                    break
            j += 1
        body = block[brace:j]
        if not sel or sel.startswith("@"):
            out.append(sel + body)
        else:
            parts = [p.strip() for p in sel.split(",") if p.strip()]
            scoped = ", ".join(
                p if p.startswith("#git-ux-root") or p.startswith("@") else f"#git-ux-root {p}"
                for p in parts
            )
            out.append(scoped + body)
        i = j
    return "\n".join(out)

scoped_tail = scope_css(tail) if tail else ""

# Dialog + toast live outside root — global but namespaced ids
dialog_css = """
#git-ux-op-dialog {
  width: min(680px, 94vw);
  max-height: 90vh;
  overflow: auto;
  background: #22242f;
  color: var(--text, #ecebf5);
  border: 1px solid #7f699d;
  border-radius: 11px;
  padding: 0;
  box-shadow: 0 20px 100px #000a;
}
#git-ux-op-dialog::backdrop { background: #0009; }
#git-ux-op-dialog .dialoghead {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 20px;
  border-bottom: 1px solid #363947;
  position: sticky;
  top: 0;
  background: #22242f;
  z-index: 2;
}
#git-ux-op-dialog .dialoghead h2 { font-size: 17px; margin: 0; }
#git-ux-op-dialog .dialogbody { padding: 20px; }
#git-ux-op-dialog .dialogfoot {
  padding: 14px 20px;
  border-top: 1px solid #363947;
  display: flex;
  gap: 7px;
  justify-content: flex-end;
  flex-wrap: wrap;
}
#git-ux-toast {
  position: fixed;
  bottom: 22px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 40;
  background: #3e3353;
  border: 1px solid #ab90dd;
  border-radius: 7px;
  padding: 12px 18px;
  max-width: 90vw;
  color: #ecebf5;
}
"""

OUT_CSS.write_text(css_header + "\n" + scoped_tail + "\n" + dialog_css, encoding="utf-8")

# --- JS adaptation ---
# Replace global $ / $$ with root-scoped helpers; remap dialog/toast/scenario ids;
# remove doc page/registry/flows/export/print/checks; keep OPS + views + execute.

js = script

# Remap DOM ids used by prototype that collide or need namespacing
replacements = {
    "$('#branch')": "$('#git-ux-branch')",
    '$("#branch")': '$("#git-ux-branch")',
    "$('#sync')": "$('#git-ux-sync')",
    "$('#status')": "$('#git-ux-status')",
    "$('#rail')": "$('#git-ux-rail')",
    "$('#view')": "$('#git-ux-view')",
    "$('#logs')": "$('#git-ux-logs')",
    "$('#conflictBar')": "$('#git-ux-conflict-bar')",
    "$('#scenario')": "$('#git-ux-scenario')",
    "$('#reset')": "$('#git-ux-reset')",
    "$('#inspect')": "$('#git-ux-inspect')",
    "$('#toast')": "$('#git-ux-toast')",
    "$('#operation')": "$('#git-ux-op-dialog')",
    "$('#closeDialog')": "$('#git-ux-close-dialog')",
    "$('#dialogTitle')": "$('#git-ux-dialog-title')",
    "$('#dialogBody')": "$('#git-ux-dialog-body')",
    "$('#dialogFoot')": "$('#git-ux-dialog-foot')",
    # prototype uses const dialog=$('#operation')
}
for a, b in replacements.items():
    js = js.replace(a, b)

# Fix locate() references to #prototype / page()
js = js.replace(
    "function page(id){$$('.page').forEach(x=>x.classList.toggle('active',x.id===id));$$('[data-page]').forEach(x=>x.classList.toggle('activebtn',x.dataset.page===id));if(id==='mapping')registry()}",
    "function page(_id){/* desktop mock: no doc pages */}",
)
js = js.replace(
    "function locate(id){close();page('prototype');if(['unbound','noGit','notRepo'].includes(state.scenario)){init();$('#scenario').value='dirty'}if(route(id)==='conflicts'&&!['conflict','rebase'].includes(state.scenario)){init('conflict');$('#scenario').value='conflict'}state.view=route(id);render();if(id==='COMMIT-EXEC'){openOp('COMMIT-REVIEW');return}const el=$(`#view [data-op=\"${id}\"]`)||$(`#prototype [data-op=\"${id}\"]`);if(el){el.classList.add('highlight');el.scrollIntoView({block:'center',behavior:'smooth'});el.focus();setTimeout(()=>el.classList.remove('highlight'),2400)}else openOp(id)}",
    "function locate(id){close();if(['unbound','noGit','notRepo'].includes(state.scenario)){init();$('#git-ux-scenario').value='dirty'}if(route(id)==='conflicts'&&!['conflict','rebase'].includes(state.scenario)){init('conflict');$('#git-ux-scenario').value='conflict'}state.view=route(id);render();if(id==='COMMIT-EXEC'){openOp('COMMIT-REVIEW');return}const el=$(`#git-ux-view [data-op=\"${id}\"]`)||$(`#git-ux-root [data-op=\"${id}\"]`);if(el){el.classList.add('highlight');el.scrollIntoView({block:'center',behavior:'smooth'});el.focus();setTimeout(()=>el.classList.remove('highlight'),2400)}else openOp(id)}",
)

# Also replace leftover $('#scenario') after remap - already done
# Fix $$('#scenario option') etc in checks - we'll strip checks

# Scope $ and $$ to #git-ux-root (+ dialog/toast at document)
js_prefix = r'''
/* EluSlot Git UX mock — ported from docs/EluSlot_Git_UX.html (offline fake data).
 * All mutations are in-memory only; does not spawn git / call Tauri write ports.
 */
(function (global) {
"use strict";
const ROOT_SEL = "#git-ux-root";
function $(s) {
  if (s === "#git-ux-toast" || s === "#git-ux-op-dialog" || s === "#git-ux-close-dialog"
      || s === "#git-ux-dialog-title" || s === "#git-ux-dialog-body" || s === "#git-ux-dialog-foot") {
    return document.querySelector(s);
  }
  const root = document.querySelector(ROOT_SEL);
  if (!root) return null;
  return root.querySelector(s);
}
function $$(s) {
  const root = document.querySelector(ROOT_SEL);
  if (!root) return [];
  return [...root.querySelectorAll(s)];
}
'''

# Remove original const $=... $$=...
js = re.sub(
    r"const \$=s=>document\.querySelector\(s\),\s*\$\$=s=>\[\.\.\.document\.querySelectorAll\(s\)\];",
    "",
    js,
)

# Strip registry / flows / tests / sources / checks / export / print / docnav handlers
# Keep from OPS through init/render/handle/execute; remove trailing doc-only boot.

# Cut at: function registry(
cut = js.find("function registry(")
if cut > 0:
    # Keep handle/execute/openOp which are before registry; but document listeners are after registry
    # Find document.addEventListener('click'
    click_at = js.find("document.addEventListener('click'")
    if click_at < 0:
        click_at = js.find('document.addEventListener("click"')
    # Remove registry through just before document listeners
    # Actually registry is between locate and document listeners.
    # Structure: ... locate; registry; handle; document listeners; ...
    handle_at = js.find("function handle(el)")
    if handle_at > 0 and cut < handle_at:
        # registry is BEFORE handle in the file? Looking at source:
        # locate, registry, handle, document.addEventListener
        js = js[:cut] + js[handle_at:]

# Remove from const flows= to end, replace with our boot
flows_at = js.find("const flows=")
if flows_at < 0:
    flows_at = js.find("const cases=")
if flows_at > 0:
    # Keep keydown/dialog listeners that are before flows
    # Looking at source order:
    # document click, input, change, keydown, dialog cancel, scenario onchange...
    # then flows, cases, docs, checks, export, print, init
    # So we need to keep listeners until before flows, then add boot.
    js = js[:flows_at]

# Fix remaining #view / #prototype / #scenario / #branch in template strings and selectors
js = js.replace("#view ", "#git-ux-view ")
js = js.replace("#view[", "#git-ux-view[")
js = js.replace("`#view ", "`#git-ux-view ")
js = js.replace("$('#view ", "$('#git-ux-view ")
js = js.replace("#prototype ", "#git-ux-root ")
js = js.replace("#scenario", "#git-ux-scenario")
js = js.replace("#branch", "#git-ux-branch")
js = js.replace("#status", "#git-ux-status")
js = js.replace("#logs", "#git-ux-logs")
js = js.replace("#rail", "#git-ux-rail")
js = js.replace("#sync", "#git-ux-sync")
js = js.replace("#conflictBar", "#git-ux-conflict-bar")
js = js.replace("#toast", "#git-ux-toast")
js = js.replace("#operation", "#git-ux-op-dialog")
js = js.replace("#closeDialog", "#git-ux-close-dialog")
js = js.replace("#dialogTitle", "#git-ux-dialog-title")
js = js.replace("#dialogBody", "#git-ux-dialog-body")
js = js.replace("#dialogFoot", "#git-ux-dialog-foot")
js = js.replace("#reset", "#git-ux-reset")
js = js.replace("#inspect", "#git-ux-inspect")
js = js.replace("#message", "#git-ux-message")
# careful: #message in changes() uses id="message" - update the HTML id in renderer
js = js.replace('id="message"', 'id="git-ux-message"')
js = js.replace("e.target.id==='message'", "e.target.id==='git-ux-message'")
js = js.replace("e.target.id==='result'", "e.target.id==='git-ux-result'")
js = js.replace('id="result"', 'id="git-ux-result"')
js = js.replace("e.target.id==='amend'", "e.target.id==='git-ux-amend'")
js = js.replace('id="amend"', 'id="git-ux-amend"')
js = js.replace("e.target.id==='historyFocus'", "e.target.id==='git-ux-history-focus'")
js = js.replace('id="historyFocus"', 'id="git-ux-history-focus"')
js = js.replace("e.target.id==='remotePicker'", "e.target.id==='git-ux-remote-picker'")
js = js.replace('id="remotePicker"', 'id="git-ux-remote-picker"')
js = js.replace('id="remoteUrl"', 'id="git-ux-remote-url"')
js = js.replace("$('#remoteUrl')", "$('#git-ux-remote-url')")
js = js.replace('id="author"', 'id="git-ux-author"')
js = js.replace('id="email"', 'id="git-ux-email"')
js = js.replace('id="ignore"', 'id="git-ux-ignore"')
js = js.replace("$('#author')", "$('#git-ux-author')")
js = js.replace("$('#email')", "$('#git-ux-email')")
js = js.replace("$('#ignore')", "$('#git-ux-ignore')")
js = js.replace('id="mergeParent"', 'id="git-ux-merge-parent"')
js = js.replace("$('#mergeParent')", "$('#git-ux-merge-parent')")

# Fix dialog variable
js = js.replace("const dialog=$('#git-ux-op-dialog');", "const dialog=$('#git-ux-op-dialog');")

# Fix path display in repobar - we'll set via render hook
# Inject path update into render()
js = js.replace(
    "$('#git-ux-branch').textContent=state.branch;$('#git-ux-sync').textContent=`↑${state.ahead} ↓${state.behind}`;",
    "$('#git-ux-branch').textContent=state.branch;$('#git-ux-sync').textContent=`↑${state.ahead} ↓${state.behind}`;const pathEl=$('#git-ux-path');if(pathEl)pathEl.textContent=state.repoPath||'D:/Projects/EluSlot';",
)

# Add repoPath to init state
js = js.replace(
    "state={scenario,view:",
    "state={repoPath:'D:/Projects/EluSlot',scenario,view:",
)

# Wire listeners that referenced #scenario/#reset/#inspect - already remapped
# Strip data-page handling is fine

js_suffix = r'''
function bootGitUxMock(scenario) {
  const root = document.querySelector(ROOT_SEL);
  if (!root) return;
  const dialog = $("#git-ux-op-dialog");
  const closeBtn = $("#git-ux-close-dialog");
  if (closeBtn) closeBtn.onclick = close;
  if (dialog) {
    dialog.addEventListener("cancel", function (e) {
      e.preventDefault();
      close();
    });
  }
  const scenarioEl = $("#git-ux-scenario");
  if (scenarioEl) {
    scenarioEl.onchange = function (e) {
      close();
      init(e.target.value);
    };
  }
  const resetEl = $("#git-ux-reset");
  if (resetEl) {
    resetEl.onclick = function () {
      close();
      init($("#git-ux-scenario").value);
    };
  }
  const inspectEl = $("#git-ux-inspect");
  if (inspectEl) {
    inspectEl.onchange = function (e) {
      document.body.classList.toggle("git-ux-specmode", e.target.checked);
      root.classList.toggle("specmode", e.target.checked);
    };
  }
  if (!bootGitUxMock._wired) {
    document.addEventListener("click", function (e) {
      if (!document.querySelector(ROOT_SEL)) return;
      const el = e.target.closest("button,[data-op]");
      if (!el || el.disabled) return;
      // Only handle events from mock root or its dialog
      const inRoot = el.closest(ROOT_SEL);
      const inDialog = el.closest("#git-ux-op-dialog");
      if (!inRoot && !inDialog) return;
      if (el.dataset.spec) {
        spec(el.dataset.spec);
        return;
      }
      if (el.dataset.locate) {
        locate(el.dataset.locate);
        return;
      }
      if (el.hasAttribute("data-close")) {
        close();
        return;
      }
      if (el.dataset.op) handle(el);
    });
    document.addEventListener("input", function (e) {
      if (!e.target.closest || (!e.target.closest(ROOT_SEL) && !e.target.closest("#git-ux-op-dialog"))) return;
      if (e.target.id === "git-ux-message") {
        state.message = e.target.value;
        state.version++;
      }
      if (e.target.id === "git-ux-result") {
        editConflict(e.target.value);
        const save = $("#git-ux-view [data-op=\"CONFLICT-SAVE\"]");
        if (save) save.disabled = false;
      }
    });
    document.addEventListener("change", function (e) {
      if (!e.target.closest || (!e.target.closest(ROOT_SEL) && !e.target.closest("#git-ux-op-dialog"))) return;
      if (e.target.id === "git-ux-history-focus") {
        state.historyFocus = e.target.value;
        render();
        return;
      }
      if (e.target.id === "git-ux-remote-picker") {
        const r = state.remoteEntries.find(function (x) { return x.name === e.target.value; });
        if (r) {
          state.remote = r.name;
          state.url = r.url;
          state.tested = false;
          render();
        }
        return;
      }
      if (e.target.id === "git-ux-amend") {
        if ($("#git-ux-inspect") && $("#git-ux-inspect").checked) {
          e.target.checked = state.amend;
          return;
        }
        state.amend = e.target.checked;
        state.version++;
        render();
      }
    });
    document.addEventListener("keydown", function (e) {
      const node = e.target.closest && e.target.closest("[data-history-node]");
      if (node && (e.key === "Enter" || e.key === " ") && node.tagName.toLowerCase() === "g") {
        e.preventDefault();
        handle(node);
      }
    });
    bootGitUxMock._wired = true;
  }
  init(scenario || "dirty");
  if (scenarioEl) scenarioEl.value = state.scenario;
}

global.EluSlotGitUxMock = {
  boot: bootGitUxMock,
  init: function (s) { init(s || "dirty"); },
  render: function () { render(); },
  getState: function () { return state; },
};
})(typeof window !== "undefined" ? window : globalThis);
'''

# The original script already has document.addEventListener blocks - strip them if still present
# since we re-wire in bootGitUxMock
for marker in [
    "document.addEventListener('click'",
    'document.addEventListener("click"',
    "document.addEventListener('input'",
    "document.addEventListener('change'",
    "document.addEventListener('keydown'",
    "dialog.addEventListener('cancel'",
    "$('#git-ux-close-dialog').onclick",
    "$('#git-ux-scenario').onchange",
    "$('#git-ux-reset').onclick",
    "$('#git-ux-inspect').onchange",
]:
    idx = js.find(marker)
    if idx > 0:
        # find start of statement (might be dialog.addEventListener after const dialog)
        # Truncate from first document listener we already planned to replace
        pass

# Find and remove original event wiring at end (after handle function body)
# handle ends then document.addEventListener...
m_handle = re.search(r"function handle\(el\)\{.*?\n\}", js, re.S)
if m_handle:
    after = js[m_handle.end():]
    # keep nothing after handle from original listeners
    js = js[: m_handle.end()]

# Fix const dialog=... show/close that reference dialog - keep show/close/spec/openOp
# They use dialog variable - need const dialog at top of show or query each time
js = js.replace(
    "function close(){if(dialog.open)dialog.close();pending=null;if(returnFocus?.isConnected)returnFocus.focus()}",
    "function close(){const dialog=$('#git-ux-op-dialog');if(dialog&&dialog.open)dialog.close();pending=null;if(returnFocus?.isConnected)returnFocus.focus()}",
)
js = js.replace(
    "function show(title,body,foot){returnFocus=document.activeElement;$('#git-ux-dialog-title').textContent=title;$('#git-ux-dialog-body').innerHTML=body;$('#git-ux-dialog-foot').innerHTML=foot;if(!dialog.open)dialog.showModal();$('#git-ux-close-dialog').focus()}",
    "function show(title,body,foot){returnFocus=document.activeElement;const dialog=$('#git-ux-op-dialog');$('#git-ux-dialog-title').textContent=title;$('#git-ux-dialog-body').innerHTML=body;$('#git-ux-dialog-foot').innerHTML=foot;if(dialog&&!dialog.open)dialog.showModal();const cb=$('#git-ux-close-dialog');if(cb)cb.focus()}",
)

# Remove orphan `const dialog=$('#git-ux-op-dialog');` if still there before close
js = re.sub(r"const dialog=\$\('#git-ux-op-dialog'\);\s*", "", js)

# Also remove leftover `$('#git-ux-close-dialog').onclick=close;...` if any remained before truncate
# Already truncated after handle.

OUT_JS.write_text(js_prefix + "\n" + js + "\n" + js_suffix, encoding="utf-8")
print("Wrote", OUT_CSS, "bytes", OUT_CSS.stat().st_size)
print("Wrote", OUT_JS, "bytes", OUT_JS.stat().st_size)
print("JS starts with OPS?", OUT_JS.read_text(encoding="utf-8")[:80])
