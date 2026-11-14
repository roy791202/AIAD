#!/usr/bin/env node
// M01-S3 native verification of the six-step project wizard WITHOUT screen coordinates.
// Drives the REAL Tauri window through WebView2 remote debugging (CDP) and the REAL
// wizard_* IPC + filesystem. Isolated: temp LOCALAPPDATA + WebView2 user-data folder +
// a temp project parent dir. Writes nothing to the repo. Usage:
//   node scripts/native_cdp_wizard_verify.cjs --exe <path-to-exe> [--port 9344]
"use strict";
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn, spawnSync } = require("child_process");

const arg = (name, dflt) => { const i = process.argv.indexOf("--" + name); return i > 0 ? process.argv[i + 1] : dflt; };
const EXE = arg("exe"), PORT = Number(arg("port", "9344"));
if (!EXE) { console.error("usage: --exe <exe> [--port N]"); process.exit(2); }

const TMP = fs.mkdtempSync(path.join(os.tmpdir(), "sgenaxis-wizard-"));
const LOCAL = path.join(TMP, "localappdata"), WV2 = path.join(TMP, "wv2"), PARENT = path.join(TMP, "parent");
for (const d of [LOCAL, WV2, PARENT]) fs.mkdirSync(d, { recursive: true });

const results = [];
const record = (id, pass, detail) => { results.push({ id, pass }); console.log(`${pass ? "PASS" : "FAIL"}  ${id}  ${detail || ""}`); };
const sleep = ms => new Promise(r => setTimeout(r, ms));
const defFile = root => path.join(root, ".sgenaxis", "project-definition.json");

let ws, nextId = 1; const pending = new Map();
async function connect() {
  let target;
  for (let i = 0; i < 60 && !target; i++) {
    try { const list = await (await fetch(`http://127.0.0.1:${PORT}/json`)).json(); target = list.find(t => t.type === "page"); } catch { /* app not ready */ }
    if (!target) await sleep(500);
  }
  if (!target) throw new Error("no WebView2 page target on CDP port " + PORT);
  ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error("ws error")); });
  ws.onmessage = ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } };
}
function cdp(method, params) { return new Promise(res => { const id = nextId++; pending.set(id, res); ws.send(JSON.stringify({ id, method, params })); }); }
async function js(expr) {
  const r = await cdp("Runtime.evaluate", { expression: `(async()=>{${expr}})()`, awaitPromise: true, returnByValue: true });
  if (r.result.exceptionDetails) throw new Error("page js: " + JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails.text));
  return r.result.result.value;
}
// Invocation-level drive of the real bridge through the real window.
const ipc = (name, args) => js(`try{return {ok:true,v:await window.__TAURI__.core.invoke(${JSON.stringify(name)},${JSON.stringify(args || {})})}}catch(e){return {ok:false,e:String(e)}}`);

(async () => {
  const env = { ...process.env, LOCALAPPDATA: LOCAL, WEBVIEW2_USER_DATA_FOLDER: WV2, WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS: `--remote-debugging-port=${PORT}` };
  const app = spawn(EXE, [], { env, stdio: "ignore", detached: false });
  const cleanup = () => { try { spawnSync("taskkill", ["/PID", String(app.pid), "/T", "/F"]); } catch { /* gone */ } };
  process.on("exit", cleanup);
  try {
    await connect();
    await sleep(1500);
    const bridgeReady = await js(`return !!(window.__TAURI__&&window.__TAURI__.core&&window.__TAURI__.core.invoke&&window.ProjectWizardUI)`);
    record("ENV native Tauri window + ProjectWizardUI present", bridgeReady, `ready=${bridgeReady}`);
    if (!bridgeReady) throw new Error("bridge/UI not present");

    const name = "WizardProj";
    const root = path.join(PARENT, name);

    // begin
    const begin = await ipc("wizard_begin", { args: { locationKind: "new", parent: PARENT, name, purpose: "" } });
    record("begin returns opaque token + basics step", begin.ok && begin.v && begin.v.token && begin.v.step === "basics", JSON.stringify(begin).slice(0, 160));
    if (!begin.ok) throw new Error("begin failed: " + begin.e);
    const token = begin.v.token;

    // invalid step rejected (reserved device name)
    const bad = await ipc("wizard_apply_step", { args: { token, step: "basics", patch: { name: "CON" } } });
    record("invalid step rejected (validation.ok=false, field=name)", bad.ok && bad.v.validation.ok === false && bad.v.validation.invalidField === "name", JSON.stringify(bad.v && bad.v.validation));

    // apply each step with valid data
    const steps = [
      ["basics", { name, purpose: "native wizard verify" }],
      ["delivery", { deliveryForm: "desktop", deliveryPlatform: "windows", deliveryLanguage: "rust", deliveryFramework: "tauri", deliveryHasUi: true }],
      ["topology", { topology: "single-crate" }],
      ["requirements", { requirementIntent: "build skeleton", requirementAcceptance: "exists\ncompiles" }],
      ["technology-ui", { deliveryHostVersion: "2", deliveryToolchain: "cargo, rustc" }],
      ["preview", {}],
    ];
    let allSteps = true, lastView = null;
    for (const [step, patch] of steps) {
      const r = await ipc("wizard_apply_step", { args: { token, step, patch } });
      if (!r.ok || !r.v.validation.ok) { allSteps = false; console.log("  step", step, JSON.stringify(r).slice(0, 160)); }
      else lastView = r.v.view;
    }
    record("apply each of six steps with valid data (validation.ok)", allSteps, lastView ? `delivery=${lastView.deliveryCount} topology=${lastView.topology} req=${lastView.requirementCount}` : "no view");

    // prepare preferences (skip) + commit
    const prep = await ipc("wizard_prepare_preferences", { args: { token, choice: "skip" } });
    record("prepare preferences (skip)", prep.ok && prep.v.kind === "skip", JSON.stringify(prep.v));
    const commit = await ipc("wizard_commit", { args: { token } });
    console.log("  commit result:", JSON.stringify(commit).slice(0, 400));
    const wroteRoot = fs.existsSync(root);
    const wroteDef = fs.existsSync(defFile(root));
    record("commit writes project root on disk (real FS)", commit.ok && wroteRoot, `root=${wroteRoot} path=${root}`);
    record("commit writes .sgenaxis/ definition on disk", commit.ok && wroteDef && commit.v.relativePath === ".sgenaxis/project-definition.json", `def=${wroteDef} rel=${commit.v && commit.v.relativePath}`);

    // reused token is single-use
    const reuse = await ipc("wizard_commit", { args: { token } });
    record("reused token rejected (single-use cleared on commit)", reuse.ok === false || (reuse.v === undefined), reuse.e || JSON.stringify(reuse).slice(0, 120));

    // cancel drops in-flight state: begin a 2nd session, cancel, then commit must fail
    const b2 = await ipc("wizard_begin", { args: { locationKind: "new", parent: PARENT, name: "Cancelled", purpose: "" } });
    const t2 = b2.ok && b2.v.token;
    await ipc("wizard_cancel", { args: { token: t2 } });
    const afterCancel = await ipc("wizard_commit", { args: { token: t2 } });
    const cancelledNoDir = !fs.existsSync(path.join(PARENT, "Cancelled"));
    record("wizard_cancel drops state (post-cancel commit fails, no dir)", b2.ok && afterCancel.ok === false && cancelledNoDir, `commitFailed=${afterCancel.ok === false} noDir=${cancelledNoDir} err=${afterCancel.e}`);

    const failed = results.filter(r => !r.pass);
    console.log(`\n=== ${results.length - failed.length}/${results.length} PASS ===`);
    process.exit(failed.length ? 1 : 0);
  } catch (e) {
    console.error("HARNESS ERROR:", e.message);
    process.exit(3);
  } finally {
    cleanup();
  }
})();
