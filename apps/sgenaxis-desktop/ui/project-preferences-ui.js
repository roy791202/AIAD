(function (global) {
  "use strict";
  function toDraft(f) {
    const number = (value, nullable) => {
      if (nullable && String(value).trim() === "") return null;
      const n = Number(value);
      if (!Number.isSafeInteger(n) || n <= 0) throw new Error("請輸入安全範圍內的正整數；空白預算表示尚未配置。");
      return n;
    };
    const ids = f.modelIds.split(",").map(x => x.trim()).filter(Boolean);
    const preferred = f.preferred.trim() || null;
    if (new Set(ids).size !== ids.length || (preferred && !ids.includes(preferred))) throw new Error("模型不可重複，偏好模型必須在允許清單內。");
    const maxTasks=number(f.tasks), maxConcurrent=number(f.concurrent);
    if (maxConcurrent>maxTasks) throw new Error("並行數不可超過每批 Task 上限。");
    return {format:"sgenaxis.project-preferences",formatVersion:1,presetId:"custom",modelPolicy:{allowedModelIds:ids,preferredModelId:preferred},budget:{maxInputTokens:number(f.input,true),maxOutputTokens:number(f.output,true),maxWallTimeSeconds:number(f.seconds,true)},batch:{mode:"suggest",maxTasks,maxConcurrent,onLimit:"block"},workflow:{confirmBeforeRun:true}};
  }
  const invoke = (name,args) => {
    const fn=global.__TAURI__?.core?.invoke || global.__TAURI__?.invoke;
    return fn ? fn(name,args) : Promise.reject(new Error("需要正式 Tauri IPC；瀏覽器不會保存專案偏好。"));
  };
  let panel, root="", digest=null, epoch=0, busy=false, dirty=false;
  const $=id=>panel.querySelector('[data-policy="'+id+'"]');
  const status=message=>{if(panel)$('status').textContent=message;};
  function paint(p) {
    $('modelIds').value=p?.modelPolicy.allowedModelIds.join(", ")||"";
    $('preferred').value=p?.modelPolicy.preferredModelId||"";
    for (const [field,key] of [["input","maxInputTokens"],["output","maxOutputTokens"],["seconds","maxWallTimeSeconds"]]) $(''+field).value=p?.budget[key]??"";
    $('tasks').value=p?.batch.maxTasks??1; $('concurrent').value=p?.batch.maxConcurrent??1;
  }
  function controls() { for (const button of panel.querySelectorAll('button,select,input')) button.disabled=busy||(!root&&button.dataset.policy!=="refresh"); }
  async function refresh() {
    if (!panel) return;
    const seq=++epoch;busy=true;controls();
    try {
      const settings=await invoke("host_get_settings"); if(seq!==epoch)return;
      root=(settings.project_root||"").trim();digest=null;$('project').textContent=root||"尚未開啟專案";
      dirty=false;paint(null);
      if(!root){paint(null);status("先開啟專案；模型與預算不會寫入本機 mock 設定。");return;}
      const view=await invoke("host_project_preferences_load",{expectedProjectRoot:root});if(seq!==epoch)return;
      digest=view.digest;paint(view.preferences);status(view.configured?"已讀取專案偏好。修改後按儲存；執行模式僅建議合批。":"此專案尚未配置偏好。請選方案並設定模型／預算。");
    } catch(error) {if(seq===epoch)status(String(error));}
    finally {if(seq===epoch){busy=false;controls();}}
  }
  async function chooseNewProject() {
    const dialog=document.createElement("dialog");dialog.setAttribute("aria-label","新專案偏好設定");
    dialog.innerHTML='<form method="dialog"><h2>是否套用專案偏好設定？</h2><p>模型與預算隨專案保存。預算未配置時不會自動執行。</p><label>方案 <select name="choice"><option value="skip">暫不套用</option><option value="conservative">保守（1／1）</option><option value="balanced">平衡（4／2）</option><option value="throughput">效率優先（8／4）</option><option value="import">匯入既有偏好檔</option></select></label><p role="status"></p><button value="cancel">取消建立</button><button value="apply">繼續</button></form>';
    document.body.appendChild(dialog);
    return new Promise(resolve=>{
      dialog.addEventListener("close",async()=>{
        const choice=dialog.querySelector("select").value;
        const accepted=dialog.returnValue==="apply";dialog.remove();
        if(!accepted){resolve(null);return;}
        try {
          if(choice==="import"){
            const imported=await invoke("host_project_preferences_pick_import");
            resolve(imported.status==="ok"?{presetId:null,importedJson:imported.json}:null);
          } else resolve({presetId:choice==="skip"?null:choice,importedJson:null});
        } catch(error){global.alert("偏好檔無法套用："+String(error));resolve(null);}
      },{once:true});dialog.showModal();
    });
  }
  function boot() {
    if(panel||!document.querySelector("#settings-ux-root"))return;
    panel=document.createElement("section");panel.id="project-policy-panel";panel.style.cssText="padding:20px;margin:16px 0;border:1px solid var(--line,#777);border-radius:10px";
    panel.innerHTML='<h2>目前專案｜模型與資源政策</h2><p data-policy="project"></p><p>保存至專案 .sgenaxis/preferences.json。預算空白＝尚未配置；不會自動啟動工作。</p><label>系統方案 <select data-policy="preset"><option value="conservative">保守（每批1／並行1）</option><option value="balanced">平衡（每批4／並行2）</option><option value="throughput">效率優先（每批8／並行4）</option></select></label> <button type="button" data-policy="apply">套用方案草稿</button> <button type="button" data-policy="import">匯入偏好草稿</button><div data-policy="fields"></div><p><button type="button" data-policy="save">儲存專案偏好</button> <button type="button" data-policy="refresh">重新載入</button></p><p role="status" aria-live="polite" data-policy="status"></p>';
    document.querySelector("#settings-ux-root").after(panel);
    for(const [id,label,type] of [["modelIds","允許模型（逗號分隔）","text"],["preferred","偏好模型","text"],["input","輸入 token 上限","number"],["output","輸出 token 上限","number"],["seconds","時間上限（秒）","number"],["tasks","每批 Task 上限","number"],["concurrent","並行上限","number"]]){
      const row=document.createElement("label");row.style.cssText="display:inline-flex;flex-direction:column;margin:10px;min-width:180px";row.textContent=label;
      const input=document.createElement("input");input.type=type;input.dataset.policy=id;if(type==="number"){input.min="1";input.step="1";}row.appendChild(input);$('fields').appendChild(row);
    }
    panel.addEventListener('input',event=>{if(event.target.matches('input'))dirty=true;});
    $('refresh').onclick=()=>{if(!dirty||global.confirm('重新載入會捨棄尚未儲存的專案偏好，是否繼續？'))refresh();};
    const draftAction=async action=>{if(busy)return;const bound=root,seq=epoch;busy=true;controls();try{const p=await action();if(root!==bound||seq!==epoch)return;paint(p);dirty=true;status("已載入草稿，尚未保存；請核對模型與預算。");}catch(e){if(seq===epoch)status(String(e));}finally{if(seq===epoch){busy=false;controls();}}};
    $('apply').onclick=()=>draftAction(async()=>{const data=await invoke("host_project_preferences_presets");return data[$('preset').value];});
    $('import').onclick=()=>draftAction(async()=>{const data=await invoke("host_project_preferences_pick_import");if(data.status!=="ok")throw new Error("已取消匯入");return JSON.parse(data.json);});
    $('save').onclick=async()=>{if(busy||!root)return;const seq=epoch,bound=root;busy=true;controls();try{const f={};for(const id of ['modelIds','preferred','input','output','seconds','tasks','concurrent'])f[id]=$(id).value;
      const saved=await invoke("host_project_preferences_save",{expectedProjectRoot:bound,expectedDigest:digest,draftJson:JSON.stringify(toDraft(f))});if(seq!==epoch||bound!==root)return;digest=saved.digest;paint(saved.preferences);dirty=false;status("已保存至目前專案。");
    }catch(e){if(seq===epoch)status("未保存："+String(e));}finally{if(seq===epoch){busy=false;controls();}}};
    refresh();
  }
  const api = { toDraft, refresh, chooseNewProject, boot, hasUnsaved:()=>dirty };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  global.ProjectPreferencesUI = api;
  if(typeof document!=="undefined")document.addEventListener("DOMContentLoaded",boot,{once:true});
})(typeof window !== "undefined" ? window : globalThis);
