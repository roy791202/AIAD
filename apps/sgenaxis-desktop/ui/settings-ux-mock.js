/* EluSlot Settings UX mock — docs/Final-2026-10-25/EluSlot_Settings.html */
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


const CATEGORIES=[
{id:'general',label:'一般與外觀',description:'調整閱讀、操作密度與啟動方式。',icon:'appearance'},
{id:'project',label:'專案與儲存',description:'設定專案位置、自動儲存與備份行為。',icon:'folder'},
{id:'agent',label:'AI Agent',description:'選擇預設工具，並管理本機執行檔與執行限制。',icon:'robot'},
{id:'permissions',label:'Agent 操作權限',description:'清楚定義 Agent 可以執行的動作及確認方式。',icon:'shield'},
{id:'mcp',label:'MCP 連線',description:'管理工具伺服器、連線方式與驗證資料參照。',icon:'plug'},
{id:'editor',label:'節點與 Slot',description:'調整畫布、節點、插槽與連線的編輯體驗。',icon:'nodes'},
{id:'git',label:'Git 與版本控制',description:'設定版本紀錄、Diff、分支圖與衝突處理偏好。',icon:'git'},
{id:'runtime',label:'Tasks 與 Runtime',description:'管理工作並行、逾時與執行日誌。',icon:'tasks'},
{id:'shortcuts',label:'快捷鍵與通知',description:'依工作習慣調整操作與提醒。',icon:'keyboard'},
{id:'advanced',label:'進階與診斷',description:'執行模式、診斷資訊與設定交換。',icon:'sliders'}];
const FIELDS=[];
function field(cat,group,key,label,type,def,help='',options=[],extra={}){FIELDS.push({cat,group,key,label,type,default:def,help,options,scopes:['personal','project','session'],...extra})}
const personal={scopes:['personal']},local={scopes:['personal','session']};
field('general','外觀','ui.theme','色彩主題','select','graphite','會立即預覽；儲存後於下次開啟保留。',[['graphite','石墨深色'],['lavender','薰衣草深色'],['light','淺色']],personal);
field('general','外觀','ui.accent','強調色','select','lavender','用於選取、焦點與主要操作。',[['lavender','淡紫'],['blue','冷藍'],['mint','薄荷']],personal);
field('general','外觀','ui.fontSize','介面字體大小','select','14','文字與控制項同步調整。',[['13','13 px'],['14','14 px'],['15','15 px'],['16','16 px']],personal);
field('general','外觀','ui.density','介面密度','select','comfortable','緊湊適合資訊密集的工作；舒適保留較多間距。',[['comfortable','舒適'],['compact','緊湊']],personal);
field('general','啟動與語言','ui.language','介面語言','select','zh-TW','本原型提供選項；完整介面翻譯由正式版接入。',[['zh-TW','繁體中文'],['en','English']],personal);
field('general','啟動與語言','ui.restoreWorkspace','恢復上次工作階段','toggle',true,'正式版可恢復開啟的專案、分頁與視窗位置。',[],personal);
field('general','啟動與語言','ui.startPage','啟動頁面','select','recent','未恢復工作階段時使用此設定。',[['recent','最近專案'],['empty','空白專案'],['welcome','歡迎頁']],personal);
field('project','位置','project.root','專案根目錄','text','D:/Projects/EluSlot','此原型只保存文字；正式版由桌面 Host 驗證目錄與權限。',[],{required:true,scopes:['project']});
field('project','位置','project.board','看板檔案位置','text','PROJECT-BOARD.xml','可使用相對專案根目錄的路徑；不接受 URL。',[],{required:true,scopes:['project']});
field('project','位置','project.defaultFolder','新專案預設資料夾','text','D:/Projects','本機偏好，不隨專案分享。',[],personal);
field('project','自動儲存與備份','storage.autosave','自動儲存','toggle',true,'正式版只對可儲存的專案文件生效。');
field('project','自動儲存與備份','storage.interval','自動儲存間隔','number',60,'單位：秒。',[],{min:10,max:3600,depends:'storage.autosave'});
field('project','自動儲存與備份','storage.backup','建立本地備份','toggle',true,'備份與 Git 提交分別管理。');
field('project','自動儲存與備份','storage.backupCount','保留備份數量','number',10,'保留最近幾個版本；原型不會操作備份檔。',[],{min:1,max:100,depends:'storage.backup'});
field('agent','預設 Agent','agent.provider','預設工具','select','claude','工具名稱沿用目前產品設定。選擇後可模擬測試該執行檔。',[['claude','Claude'],['cursor','Cursor Agent'],['codex','Codex'],['antigravity','Antigravity']]);
field('agent','本機執行檔','agent.claudePath','Claude 執行檔','text','claude','可填 PATH 中的命令，或完整執行檔路徑。',[],{...local,required:true});
field('agent','本機執行檔','agent.cursorPath','Cursor Agent 執行檔','text','cursor-agent','正式版以 argv 呼叫；不在路徑欄輸入 shell 腳本。',[],{...local,required:true});
field('agent','本機執行檔','agent.codexPath','Codex 執行檔','text','codex','路徑屬於本機設定；專案只指定工具偏好。',[],{...local,required:true});
field('agent','本機執行檔','agent.antigravityPath','Antigravity 執行檔','text','antigravity','可留用目前安裝的命令名稱。',[],{...local,required:true});
field('agent','執行限制','agent.timeout','單次工作逾時','number',300,'單位：秒；逾時後由 Host 回報實際完成狀態。',[],{min:10,max:7200});
field('agent','執行限制','agent.maxSteps','單次工作步驟上限','number',30,'到達上限後停止並顯示目前進度。',[],{min:1,max:200});
field('agent','執行限制','agent.reviewChanges','完成後開啟變更檢視','toggle',true,'在正式版檢查 Agent 修改的檔案與架構。');
field('permissions','檔案與工作區','permissions.readScope','允許讀取範圍','select','project','設定只描述產品權限政策；原型不讀取任何目錄。',[['project','目前專案'],['allowlist','指定目錄清單']]);
field('permissions','檔案與工作區','permissions.readPaths','額外允許目錄','textarea','','每行一個本機目錄；正式版還須檢查根目錄與 symlink。',[],{dependsValue:['permissions.readScope','allowlist']});
field('permissions','檔案與工作區','permissions.write','修改檔案','select','ask','此權限與 Git 提交權限分開。',[['deny','禁止'],['ask','每次核對'],['project','允許專案內修改']]);
field('permissions','命令與連線','permissions.commands','執行命令','select','ask','正式版須列出命令、工作目錄與影響範圍。',[['deny','禁止'],['ask','每次核對']]);
field('permissions','命令與連線','permissions.network','允許連網','toggle',false,'原型不會連線；正式版交由 Host 與 Agent 共同執行政策。');
field('permissions','命令與連線','permissions.gitWrite','Agent 執行 Git 寫入','select','ask','Push、歷史重寫等仍需各自核對；設定不會略過衝突檢查。',[['deny','禁止'],['ask','每次核對']]);
field('mcp','工具伺服器','mcp.servers','伺服器連線清單','servers',[{id:'local-agent',name:'Local Agent',transport:'stdio',command:'local-agent',args:'',url:'',credentialRef:'',enabled:true}],'可新增多組連線；驗證資料只保存系統憑證參照名稱。');
field('mcp','連線行為','mcp.timeout','連線逾時','number',30,'單位：秒。',[],{min:1,max:300});
field('mcp','連線行為','mcp.probeOnConnect','連線後探測工具','toggle',true,'正式版載入工具清單與能力，探測失敗須顯示原因。');
field('editor','畫布','editor.grid','顯示格線','toggle',true,'右側小型畫布會立即預覽。');
field('editor','畫布','editor.snap','節點吸附格線','toggle',true,'不改變專案的節點語意。');
field('editor','畫布','editor.gridSize','格線間距','number',20,'單位：畫布座標。',[],{min:8,max:100});
field('editor','畫布','editor.zoom','滑鼠縮放速度','select','normal','正式版可依滑鼠或觸控板操作習慣調整。',[['slow','慢'],['normal','標準'],['fast','快']]);
field('editor','Slot 與連線','editor.expandDepth','預設展開層級','number',1,'0 表示預設收合；不改變實際巢狀結構。',[],{min:0,max:6});
field('editor','Slot 與連線','editor.connection','連線樣式','select','curve','右側連線預覽會同步更新。',[['curve','曲線'],['elbow','直角'],['straight','直線']]);
field('editor','Slot 與連線','editor.minimap','顯示小地圖','toggle',true,'正式版用於快速定位大型節點架構。');
field('git','提交與同步','git.author','提交作者名稱','text','Example Developer','正式版寫入本儲存庫的 user.name。',[],{required:true});
field('git','提交與同步','git.email','提交作者 Email','text','dev@example.invalid','作者與遠端帳號驗證是不同設定。',[],{required:true,email:true});
field('git','提交與同步','git.fetchInterval','自動 Fetch 間隔','number',5,'單位：分鐘；0 表示關閉。不自動 Pull 或 Push。',[],{min:0,max:120});
field('git','提交與同步','git.messageTemplate','提交訊息範本','textarea','feat: \n\n','原型保存範本；正式版帶入提交草稿，不自動提交。');
field('git','提交紀錄與分支圖','git.historyScope','預設歷史範圍','select','all','影響提交圖預設視角。',[['all','全部分支'],['current','目前分支']]);
field('git','提交紀錄與分支圖','git.showRemotes','顯示遠端分支標籤','toggle',true,'保留 HEAD 與父提交關係，不用隱藏節點改寫拓撲。');
field('git','提交紀錄與分支圖','git.showTags','顯示 Tag','toggle',true,'顯示目前 ref 指向的標籤。');
field('git','提交紀錄與分支圖','git.graphSpacing','分支圖行距','select','normal','在資訊量與閱讀空間之間切換。',[['compact','緊湊'],['normal','標準'],['wide','寬鬆']]);
field('git','Diff 與衝突','git.diff','預設 Diff 檢視','select','split','可在單次檢視中另行切換。',[['split','並排'],['unified','同列']]);
field('git','Diff 與衝突','git.whitespace','顯示空白字元','toggle',false,'只影響顯示，不修改檔案。');
field('git','Diff 與衝突','git.openConflicts','偵測衝突時開啟解決頁','toggle',true,'關閉自動跳轉後，全域衝突提醒仍持續顯示。');
field('git','Diff 與衝突','git.showBase','顯示 Base 版本','toggle',true,'三方檢視的閱讀偏好；不略過未解決檢查。');
field('git','Diff 與衝突','git.nextConflict','儲存後前往下一個衝突檔','toggle',true,'全部解決後仍需明確點「繼續」。');
field('runtime','執行與排程','runtime.parallel','同時執行工作數','number',2,'正式版須依實際資源與工具限制排程。',[],{min:1,max:16});
field('runtime','執行與排程','runtime.timeout','工作逾時','number',600,'單位：秒；不等於取消後可完整回滾。',[],{min:10,max:86400});
field('runtime','執行與排程','runtime.autoRetry','失敗後自動重試讀取工作','toggle',false,'只對明確可重試的讀取工作；不盲目重試寫入。');
field('runtime','日誌','runtime.logRetention','保留執行日誌','number',7,'單位：天。',[],{min:1,max:90});
field('runtime','日誌','runtime.notifyFailure','工作失敗時通知','toggle',true,'通知內容不包含憑證與完整敏感輸出。');
field('shortcuts','快捷鍵','shortcut.save','儲存專案','text','Ctrl+S','支援 Ctrl／Alt／Shift／Meta 加一個按鍵；本頁不攔截系統快捷鍵。',[],{...personal,shortcut:true});
field('shortcuts','快捷鍵','shortcut.agent','開啟 Agent','text','Ctrl+Shift+A','不能與此頁其他快捷鍵重複。',[],{...personal,shortcut:true});
field('shortcuts','快捷鍵','shortcut.search','搜尋節點','text','Ctrl+K','正式版交由應用程式命令系統註冊。',[],{...personal,shortcut:true});
field('shortcuts','通知','notify.desktop','桌面通知','toggle',false,'本原型不會請求瀏覽器通知權限。',[],personal);
field('shortcuts','通知','notify.sound','通知音效','toggle',false,'正式版可播放完成與失敗提示。',[],personal);
field('shortcuts','通知','notify.agentDone','Agent 完成時提醒','toggle',true,'可搭配應用程式內通知。',[],personal);
field('advanced','執行模式','advanced.mode','工具執行模式','select','dryrun','正式版設計：模擬／實際執行。此 HTML 永遠不執行 CLI、MCP 或 Git。',[['dryrun','DryRun · 模擬'],['live','Live · 實際執行（Host 設定提案）']],{scopes:['session']});
field('advanced','診斷','advanced.logLevel','日誌詳細程度','select','normal','除錯資訊不應包含 token、私鑰或完整密碼。',[['error','僅錯誤'],['normal','一般'],['debug','除錯']]);
field('advanced','診斷','advanced.showDiagnostics','顯示進階診斷資訊','toggle',false,'開啟後才在右側顯示建議的 Host 介面與設定鍵。',[],personal);
field('advanced','診斷','advanced.redact','遮罩敏感日誌','toggle',true,'建議預設開啟；正式版須在 Host 端強制遮罩秘密。',[],{scopes:['personal']});

const clone=x=>JSON.parse(JSON.stringify(x)),SCOPES=['personal','project','session'],scopeNames={personal:'個人偏好',project:'目前專案',session:'本次工作階段'},KEY='EluSlot.Settings.DesktopMock.v1',byKey=Object.fromEntries(FIELDS.map(f=>[f.key,f]));
const paths={appearance:'M12 3a9 9 0 1 0 0 18h2a2 2 0 0 0 0-4h-1a2 2 0 0 1 0-4h3a5 5 0 0 0 5-5c0-3-5-5-9-5 M7 9h.01 M11 6h.01 M6 13h.01 M16 7h.01',folder:'M3 7V5h6l2 2h10v13H3Z',robot:'M9 3h6 M12 3v3 M5 6h14v14H5Z M2 10v6 M22 10v6 M9 11v3 M15 11v3',shield:'m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6Z M8 12l3 3 5-6',plug:'M8 3v5 M16 3v5 M6 8h12v4a6 6 0 0 1-12 0Z M12 18v4',nodes:'M3 3h6v6H3Z M15 3h6v6h-6Z M9 15h6v6H9Z M9 6h6 M6 9v9h3 M18 9v9h-3',git:'M6 3v12a4 4 0 0 0 4 4h4 M18 8v5a6 6 0 0 1-6 6 M3 3h6v5H3Z M15 3h6v5h-6Z M15 16h6v5h-6Z',tasks:'M9 5h12 M9 12h12 M9 19h12 M3 4l1 1 2-2 M3 11l1 1 2-2 M3 18l1 1 2-2',keyboard:'M2 5h20v14H2Z M6 9h.01 M10 9h.01 M14 9h.01 M18 9h.01 M6 13h.01 M10 13h.01 M14 13h.01 M18 13h.01 M7 16h10',sliders:'M4 3v7 M4 15v6 M12 3v12 M12 20v1 M20 3v2 M20 10v11 M1 10h6v5H1Z M9 15h6v5H9Z M17 5h6v5h-6Z'};
const icon=k=>`<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="${paths[k]||paths.sliders}"/></svg>`;
let saved={personal:{},project:{},session:{}},draft,category='general',scope='personal',selectedKey='ui.theme',search='',selectedServer='local-agent',lastTest={},timer,returnFocus,dialogAction=null,storageWarning='';
function supports(f,s=scope){return f.scopes.includes(s)}
function get(key,s=scope,obj=draft){const f=byKey[key];let v=clone(f.default);for(const layer of SCOPES.slice(0,SCOPES.indexOf(s)+1))if(supports(f,layer)&&Object.hasOwn(obj[layer],key))v=clone(obj[layer][key]);return v}
function origin(key,s=scope,obj=draft){for(const layer of SCOPES.slice(0,SCOPES.indexOf(s)+1).reverse())if(Object.hasOwn(obj[layer],key)&&supports(byKey[key],layer))return layer;return 'default'}
function diff(s=scope){return FIELDS.filter(f=>supports(f,s)&&JSON.stringify(saved[s][f.key])!==JSON.stringify(draft[s][f.key]))}
function canonicalShortcut(v){return String(v).trim().toLowerCase().split('+').map(x=>x.trim()).sort().join('+')}
function validate(f,v,s=scope,obj=draft){if(f.required&&!String(v).trim())return '此欄位不能空白。';if(f.type==='number'&&(!Number.isInteger(v)||v<f.min||v>f.max))return `請輸入 ${f.min}–${f.max} 的整數。`;if(f.email&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v))return '請輸入有效的 Email。';if(f.type==='select'&&!f.options.some(([x])=>x===v))return '請選擇有效選項。';if(['project.root','project.board','project.defaultFolder'].includes(f.key)&&/^[a-z]+:\/\//i.test(v))return '請填本機路徑，不接受 URL。';if(f.shortcut){if(!/^(?:(?:Ctrl|Alt|Shift|Meta)\+)+(?:[A-Za-z0-9]|F(?:[1-9]|1[0-2])|Enter|Space|Tab|Delete)$/i.test(v))return '請使用如 Ctrl+Shift+A 的格式。';if(FIELDS.some(other=>other.shortcut&&other.key!==f.key&&canonicalShortcut(get(other.key,s,obj))===canonicalShortcut(v)))return '這組快捷鍵已由其他動作使用。'}if(f.type==='servers'){if(!Array.isArray(v)||v.length>20)return '最多保留 20 組伺服器。';const names=new Set(),ids=new Set();for(const server of v){if(!server.name?.trim()||names.has(server.name.toLowerCase()))return '伺服器名稱不能空白或重複。';if(!server.id||ids.has(server.id))return '伺服器 ID 必須唯一。';ids.add(server.id);names.add(server.name.toLowerCase());if(server.transport==='stdio'&&!server.command.trim())return 'stdio 連線需要啟動命令。';if(server.transport==='http'&&!/^https?:\/\/[^\s/]+(?:\/[^\s]*)?$/.test(server.url))return 'HTTP 連線需要有效的 http(s) URL。';if(server.transport==='http'&&/@/.test(server.url))return 'URL 不可包含內嵌憑證。'}}return ''}
function errors(s=scope,obj=draft){return FIELDS.filter(f=>supports(f,s)).map(f=>({key:f.key,message:validate(f,get(f.key,s,obj),s,obj)})).filter(e=>e.message)}
function sanitizeConfig(data){if(data?.format!=='EluSlot.Settings'||data.version!==1||!data.profiles||typeof data.profiles!=='object')throw Error('無法辨識設定檔格式或版本。');const out={personal:{},project:{},session:{}};for(const s of ['personal','project']){const profile=data.profiles[s];if(profile!==undefined&&(!profile||typeof profile!=='object'||Array.isArray(profile)))throw Error('設定範圍格式不正確。');for(const [key,v]of Object.entries(profile||{})){const f=byKey[key];if(!Object.hasOwn(byKey,key)||!supports(f,s))throw Error('含有未知或不適用的設定：'+key);if(f.type==='servers'){if(!Array.isArray(v))throw Error('伺服器清單格式不正確。');out[s][key]=v.map(x=>{const allowed=['id','name','transport','command','args','url','credentialRef','enabled'];if(!x||Object.keys(x).some(k=>!allowed.includes(k)))throw Error('伺服器設定含有不支援欄位；不接受明文密鑰。');if(allowed.filter(k=>k!=='enabled').some(k=>typeof x[k]!=='string')||typeof x.enabled!=='boolean'||!['stdio','http'].includes(x.transport))throw Error('伺服器欄位型別不正確。');return clone(x)})}else if((f.type==='toggle'&&typeof v!=='boolean')||(f.type==='number'&&typeof v!=='number')||(!['toggle','number'].includes(f.type)&&typeof v!=='string'))throw Error('欄位型別不正確：'+key);else out[s][key]=v;}}for(const s of ['personal','project']){const e=errors(s,out);if(e.length)throw Error(e[0].message+'（'+e[0].key+'）')}return out}
function load(){try{const raw=localStorage.getItem(KEY);if(raw)saved=sanitizeConfig(JSON.parse(raw))}catch(e){storageWarning='本機設定無法載入，已使用預設值：'+e.message}draft=clone(saved)}
function toast(msg){const t=$('#settings-ux-toast');if(!t)return;t.textContent=msg;t.hidden=false;clearTimeout(timer);timer=setTimeout(()=>{t.hidden=true},4200)}
function show(title,body,foot=''){returnFocus=document.activeElement;const dialog=$('#settings-ux-dialog');const dt=$('#settings-ux-dialog-title');const db=$('#settings-ux-dialog-body');const df=$('#settings-ux-dialog-foot');if(dt)dt.textContent=title;if(db)db.innerHTML=body;if(df)df.innerHTML=foot||'<button type="button" data-close>關閉</button>';if(dialog&&!dialog.open)dialog.showModal()}
function close(){const dialog=$('#settings-ux-dialog');if(dialog&&dialog.open)dialog.close();dialogAction=null;if(returnFocus?.isConnected)returnFocus.focus()}
function display(f,v){if(f.type==='toggle')return v?'開啟':'關閉';if(f.type==='servers')return v.map(s=>s.name+' · '+s.transport).join('；')||'沒有伺服器';if(f.type==='select')return f.options.find(([x])=>x===v)?.[1]||v;return String(v||'（空白）')}
function preview(){const root=document.querySelector('#settings-ux-root');if(!root)return;const t=get('ui.theme','session'),a=get('ui.accent','session');root.dataset.theme=t;root.dataset.density=get('ui.density','session');const colors={lavender:t==='light'?'#7752b4':'#baa3f0',blue:t==='light'?'#3e65ae':'#9abdf5',mint:t==='light'?'#277960':'#8ed9bd'};document.documentElement.style.setProperty('--accent',colors[a]);document.documentElement.style.setProperty('--font',get('ui.fontSize','session')+'px')}
function paintNav(){$('#settings-ux-categories').innerHTML=CATEGORIES.map(c=>{const fields=FIELDS.filter(f=>f.cat===c.id&&supports(f)),d=diff().filter(f=>f.cat===c.id).length;return `<button class="category ${c.id===category&&!search?'active':''}" data-category="${c.id}" aria-current="${c.id===category&&!search?'page':'false'}">${icon(c.icon)}<span>${c.label}</span>${d?`<span class="navdirty">●</span>`:`<span class="catcount">${fields.length}</span>`}</button>`}).join('')}
function inheritedMeta(f){const own=Object.hasOwn(draft[scope],f.key),src=origin(f.key);return `<span class="${own?'override':''}">${own?'此範圍已設定':src==='default'?'使用預設值':'繼承自'+scopeNames[src]}</span>${own?`<button class="inherit" data-inherit="${f.key}">${scope==='personal'?'使用預設值':'移除覆寫'}</button>`:''}`}
function control(f){const v=get(f.key),disabled=f.depends&&!get(f.depends)||f.dependsValue&&get(f.dependsValue[0])!==f.dependsValue[1],error=validate(f,v),attrs=`data-key="${f.key}" id="f-${f.key}" aria-describedby="help-${f.key} error-${f.key}" ${disabled?'disabled':''} aria-invalid="${!!error}"`;if(f.type==='toggle')return `<div class="togglebox"><span class="toggletext">${v?'開啟':'關閉'}</span><button type="button" role="switch" class="toggle" ${attrs} aria-label="${esc(f.label)}" aria-checked="${v}"><i></i></button></div>`;if(f.type==='select')return `<select ${attrs}>${f.options.map(([a,b])=>`<option value="${esc(a)}" ${v===a?'selected':''}>${esc(b)}</option>`).join('')}</select>`;if(f.type==='textarea')return `<textarea ${attrs}>${esc(v)}</textarea>`;return `<input ${attrs} type="${f.type==='number'?'number':'text'}" ${f.type==='number'?`min="${f.min}" max="${f.max}" step="1"`:''} value="${esc(v)}" autocomplete="off">`}
function fieldRow(f){if(f.type==='servers')return serversUI(f);const error=validate(f,get(f.key));return `<div class="settingrow" data-setting="${f.key}"><div><div class="setting-label"><label for="f-${f.key}">${esc(f.label)}</label><button class="info" data-info="${f.key}" aria-label="${esc(f.label)}的說明">ⓘ</button></div><p id="help-${f.key}">${esc(f.help)}</p></div><div class="inputwrap">${control(f)}<div class="inputmeta" data-meta="${f.key}">${inheritedMeta(f)}</div><div class="err" id="error-${f.key}" ${error?'':'hidden'}>${esc(error)}</div></div></div>`}
function serversUI(f){const servers=get(f.key);if(!servers.some(s=>s.id===selectedServer))selectedServer=servers[0]?.id||'';const s=servers.find(s=>s.id===selectedServer);return `<div class="settingrow wide" data-setting="mcp.servers"><div class="setting-label"><strong style="font-size:13px">伺服器連線</strong><button class="info" data-info="mcp.servers" aria-label="MCP 連線的說明">ⓘ</button><span class="spacer"></span><small>${servers.length} / 20 組</small></div><div class="inputmeta" data-meta="mcp.servers">${inheritedMeta(f)}</div><div class="servernav"><select id="settings-ux-server-select" aria-label="選擇 MCP 伺服器">${servers.map(s=>`<option value="${esc(s.id)}" ${selectedServer===s.id?'selected':''}>${esc(s.name)}${s.enabled?'':'（停用）'}</option>`).join('')||'<option>沒有伺服器</option>'}</select><button data-action="addServer" ${servers.length>=20?'disabled':''}>＋ 新增</button></div>${s?`<div class="serverform"><div class="servergrid"><label class="serverfield">顯示名稱<input data-server="name" value="${esc(s.name)}"></label><label class="serverfield">傳輸方式<select data-server="transport"><option value="stdio" ${s.transport==='stdio'?'selected':''}>stdio · 本機程序</option><option value="http" ${s.transport==='http'?'selected':''}>HTTP · 服務端點</option></select></label>${s.transport==='stdio'?`<label class="serverfield full">啟動命令<input data-server="command" value="${esc(s.command)}"></label><label class="serverfield full">參數（每行一個 argv）<textarea data-server="args">${esc(s.args)}</textarea></label>`:`<label class="serverfield full">服務 URL<input data-server="url" value="${esc(s.url)}" placeholder="https://example.invalid/mcp"></label>`}<label class="serverfield full">系統憑證參照（可選）<input data-server="credentialRef" value="${esc(s.credentialRef)}" placeholder="例如 eluslot/mcp/team-server"><small>只存參照名稱；不在此輸入 token、密碼或私鑰。</small></label></div><div class="serveractions"><label class="row"><input type="checkbox" data-server="enabled" ${s.enabled?'checked':''}> 啟用此連線</label><span class="spacer"></span><button data-action="credentials">憑證管理說明</button><button data-action="deleteServer" class="danger">移除</button></div></div>`:'<p class="muted">新增一組工具伺服器開始設定。</p>'}<div id="error-mcp.servers" class="err" ${validate(f,servers)?'':'hidden'}>${esc(validate(f,servers))}</div></div>`}
function testPanel(type){const prev=lastTest[type];return `<div class="testpanel"><h3>${type==='cli'?'Agent 工具檢查':'MCP 連線與工具探測'}</h3><p class="muted" style="font-size:12px;margin:0 0 12px">測試 UI 回饋流程；此頁不啟動程序或建立網路連線。</p><div class="row"><label class="sr" for="test-${type}">模擬測試結果</label><select id="test-${type}" aria-label="${type==='cli'?'CLI':'MCP'} 模擬測試結果"><option value="success">模擬：成功</option><option value="missing">模擬：${type==='cli'?'找不到執行檔':'無法連線'}</option><option value="auth">模擬：驗證失敗</option><option value="timeout">模擬：逾時</option></select><button data-test="${type}">執行模擬測試</button>${type==='mcp'?'<button data-test="tools">模擬探測工具</button>':''}</div><div class="testresult" id="result-${type}" role="status">${prev||'<span class="muted">尚未測試</span>'}</div></div>`}
function advancedExtras(){return `<div class="group"><div class="grouphead"><h2>設定交換與維護</h2></div><div class="settingrow"><div><div class="setting-label">匯出與匯入</div><p>JSON 包含已儲存的個人／專案覆寫；排除工作階段與密鑰內容。</p></div><div class="row"><button data-action="export">匯出 JSON</button><button data-action="import">匯入 JSON</button></div></div><div class="settingrow"><div><div class="setting-label">還原目前範圍</div><p>清除此範圍的全部覆寫，先檢視再儲存；不清除其他範圍。</p></div><div><button data-action="resetScope" class="danger">清除此範圍覆寫</button></div></div><div class="settingrow"><div><div class="setting-label">原型驗證</div><p>檢查設定定義、預設值、作用範圍與驗證規則。不測試真實 Host。</p></div><div><button data-action="checks">執行結構檢查</button></div></div></div>`}
function render(){preview();paintNav();const cat=CATEGORIES.find(c=>c.id===category);$('#settings-ux-breadcrumb').textContent=search?'搜尋結果':cat.label;$('#settings-ux-title').textContent=search?'搜尋設定':cat.label;$('#settings-ux-description').textContent=search?'搜尋所有分類中，適用目前範圍的設定。':cat.description;$$('[data-scope]').forEach(el=>{el.classList.toggle('active',el.dataset.scope===scope);el.setAttribute('aria-pressed',el.dataset.scope===scope)});$('#settings-ux-scope-hint').textContent={personal:'保存在此瀏覽器；正式版為本機使用者偏好',project:'此示意專案的覆寫；可移除以繼承個人偏好',session:'本次頁面有效；重新開啟即清除'}[scope];let matching=FIELDS.filter(f=>supports(f)&&(search?`${f.label} ${f.help} ${f.group} ${f.key} ${CATEGORIES.find(c=>c.id===f.cat).label}`.toLowerCase().includes(search.toLowerCase()):f.cat===category));let html=`<div class="notice">${icon('shield')}<div><strong>離線互動原型</strong> · 儲存只影響此 HTML 在目前瀏覽器的設定。CLI、MCP、Git 與專案檔案皆未串接。${storageWarning?'<br>'+esc(storageWarning):''}</div></div>`;if(search)html+=`<div class="allsearch">「${esc(search)}」找到 ${matching.length} 個設定 · ${scopeNames[scope]}</div>`;if(!matching.length)html+=`<div class="empty"><h2>${search?'沒有符合的設定':'此分類不使用這個範圍'}</h2><p>${search?'請調整關鍵字或設定範圍。':'可切換「個人偏好」或「目前專案」，查看適用項目。'}</p></div>`;else{const groups=[...new Set(matching.map(f=>f.cat+'|'+f.group))];html+=groups.map(g=>{const[catId,title]=g.split('|');return `<section class="group"><div class="grouphead"><h2>${search?CATEGORIES.find(c=>c.id===catId).label+' / ':''}${esc(title)}</h2></div>${matching.filter(f=>f.cat===catId&&f.group===title).map(fieldRow).join('')}</section>`}).join('')}if(!search&&category==='agent')html+=testPanel('cli');if(!search&&category==='mcp')html+=testPanel('mcp');if(!search&&category==='advanced')html+=advancedExtras();$('#settings-ux-content').innerHTML=html;const current=matching.find(f=>f.key===selectedKey)||matching[0];if(current)selectedKey=current.key;updateFooter();paintInspector()}
function updateFooter(){const changed=diff(),other=SCOPES.filter(s=>s!==scope).reduce((n,s)=>n+diff(s).length,0),e=errors();$('#settings-ux-save-status').textContent=e.length?`${e.length} 個設定需要修正`:changed.length?`${changed.length} 項未儲存 · ${scopeNames[scope]}`:`${scopeNames[scope]} · 所有變更已儲存`;$('#settings-ux-save-status').className='status '+(e.length?'bad':'muted');$('#settings-ux-page-dirty').hidden=!changed.length;$('#settings-ux-page-dirty').textContent=changed.length+' 項未儲存'+(other?' · 其他範圍 '+other+' 項':'');$('#settings-ux-save').disabled=!changed.length||!!e.length;$('#settings-ux-reset-page').disabled=!!search||!FIELDS.some(f=>f.cat===category&&supports(f));$('#settings-ux-review').disabled=!changed.length;$('#settings-ux-revert').disabled=!changed.length;$('#settings-ux-save').textContent=scope==='session'?'套用至本次工作階段':'儲存設定'}
function editorPreview(){const depth=get('editor.expandDepth','session'),grid=get('editor.grid','session'),style=get('editor.connection','session'),d={curve:'M104 48 C150 48 124 111 188 111',elbow:'M104 48 H146 V111 H188',straight:'M104 48 L188 111'}[style];return `<div class="preview ${grid?'grid':''}"><svg viewBox="0 0 240 145" aria-hidden="true"><path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2"/></svg><div class="pnode a"><strong>Application</strong>${depth?'<div class="pslot">Slot · modules<br><small>▣ Agent</small></div>':'<div class="pslot">▸ Slot 已收合</div>'}</div><div class="pnode b">▣ Runtime<br><small>execution</small></div></div>`}
function gitPreview(){return `<div class="preview" style="height:auto"><div class="miniheader">Commit History · ${get('git.historyScope','session')==='all'?'全部分支':'目前分支'}</div><div class="mini-graph"><svg viewBox="0 0 36 98" aria-hidden="true"><path d="M9 3V88 M9 54C9 46 28 46 28 34V4" fill="none" stroke="var(--accent)" stroke-width="2"/><circle cx="9" cy="20" r="4" fill="var(--accent)"/><circle cx="28" cy="8" r="4" fill="#83cfc0"/><circle cx="9" cy="55" r="5" fill="var(--input)" stroke="var(--accent)" stroke-width="2"/><circle cx="9" cy="86" r="4" fill="var(--accent)"/></svg><div>Improve Git UI <span class="minitag">HEAD</span></div><div>Merge feature ${get('git.showRemotes','session')?'<span class="minitag">origin/main</span>':''}</div><div>Initial project ${get('git.showTags','session')?'<span class="minitag">v0.1</span>':''}</div></div></div>`}
function inspectorHTML(f){const source=origin(f.key),v=get(f.key),err=validate(f,v),diagnostics=get('advanced.showDiagnostics','session');return `<div class="inspectbox"><h2 class="inspect-title">${esc(f.label)}</h2><p>${esc(f.help)}</p><div class="kv"><span>目前範圍</span><span>${scopeNames[scope]}</span></div><div class="kv"><span>值的來源</span><span>${source==='default'?'產品預設':scopeNames[source]}</span></div><div class="kv"><span>目前值</span><span>${esc(display(f,v))}</span></div><div class="kv"><span>保存方式</span><span>${scope==='session'?'僅本次頁面記憶體':'瀏覽器本機儲存（原型）'}</span></div>${err?`<p class="bad">${esc(err)}</p>`:''}</div>${['editor','general'].includes(f.cat)?`<div class="inspectbox"><h3>畫布預覽</h3>${editorPreview()}<p>設定改變顯示偏好；不修改節點與 Slot 的專案結構。</p></div>`:f.cat==='git'?`<div class="inspectbox"><h3>版本紀錄預覽</h3>${gitPreview()}<p>衝突狀態與是否可繼續，由 Git 實際結果決定。</p></div>`:''}<div class="inspectbox"><h3>設定繼承</h3><p>個人偏好 → 目前專案 → 本次工作階段。較後範圍只覆寫適用的項目；移除覆寫後，會回到上一層的有效值。</p><p>未儲存變更切換分類或範圍後仍會保留。</p></div>${diagnostics?`<div class="inspectbox"><h3>串接提案</h3><pre>${esc(f.key)}\nSettingsService.prepare / save\nSettingsChanged(scope, keys)</pre><p>本機路徑與憑證參照，與可分享的專案設定分開保存。正式版透過 Host 檢查後才套用。</p></div>`:''}`}
function paintInspector(){const f=byKey[selectedKey];$('#settings-ux-inspector').innerHTML=f?inspectorHTML(f):'<p class="muted">選擇設定以查看說明。</p>'}
function updateField(key,v){draft[scope][key]=clone(v);lastTest={};$$('[id="settings-ux-result-cli"],[id="settings-ux-result-mcp"]').forEach(el=>el.innerHTML='<span class="muted">設定已變更，尚未重新測試</span>');preview();updateFooter();paintNav();selectedKey=key;paintInspector();for(const f of FIELDS.filter(f=>supports(f))){const error=validate(f,get(f.key)),el=document.getElementById('error-'+f.key),input=document.getElementById('f-'+f.key);if(el){el.hidden=!error;el.textContent=error}if(input)input.setAttribute('aria-invalid',!!error)}const meta=$(`[data-meta="${key}"]`);if(meta)meta.innerHTML=inheritedMeta(byKey[key])}
function reviews(s=scope){return diff(s).map(f=>`<div class="reviewitem"><strong>${esc(f.label)}</strong><p>原本：${esc(display(f,get(f.key,s,saved)))}<br>變更：${esc(display(f,get(f.key,s,draft)))}</p></div>`).join('')}
function showReview(){dialogAction=()=>save();show('檢視變更 · '+scopeNames[scope],`<p>只儲存目前範圍；其他範圍的未儲存變更會保留。</p><div class="reviewlist">${reviews()}</div>`,`<button data-close>返回編輯</button><button class="primary" data-confirm>確認儲存</button>`)}
function save(){const e=errors();if(e.length){toast('請先修正：'+e[0].message);return false}const next=clone(saved);next[scope]=clone(draft[scope]);try{if(scope!=='session')localStorage.setItem(KEY,JSON.stringify({format:'EluSlot.Settings',version:1,profiles:{personal:next.personal,project:next.project}}));saved=next;close();render();toast(scopeNames[scope]+(scope==='session'?'已套用；重新開啟即清除。':'已儲存至此瀏覽器。'));return true}catch(e){show('設定尚未儲存','<p>瀏覽器本機儲存不可用。變更仍保留在此頁；可檢查瀏覽器設定，或使用 JSON 匯出已儲存資料。</p><p class="bad">'+esc(e.message)+'</p>');return false}}
function confirmReset(all=false){const keys=FIELDS.filter(f=>supports(f)&&(all||f.cat===category)).map(f=>f.key),label=all?'此範圍所有分類':CATEGORIES.find(c=>c.id===category).label;dialogAction=()=>{keys.forEach(k=>delete draft[scope][k]);close();lastTest={};render();toast('已移除 '+label+' 的覆寫；請儲存後套用。')};show('還原設定 · '+scopeNames[scope],`<p>將移除「${esc(label)}」在${scopeNames[scope]}中的覆寫，回到繼承值或預設值。</p><p>其他範圍不會改變。這項變更仍需儲存。</p>`,`<button data-close>取消</button><button data-confirm class="danger">移除覆寫</button>`)}
function test(type){const kind=type==='tools'?'mcp':type,e=errors().find(e=>type==='cli'?e.key.startsWith('agent.'):e.key==='mcp.servers');if(e){toast('請先修正：'+e.message);return}let result;if(kind==='cli'){const provider=get('agent.provider'),path=get('agent.'+provider+'Path','session');result='工具：'+esc(provider)+' · 命令：<code>'+esc(path)+'</code>'}else{const s=get('mcp.servers').find(s=>s.id===selectedServer);if(!s||!s.enabled){toast('請先新增並啟用一組連線。');return}result='伺服器：'+esc(s.name)+' · '+esc(s.transport)}const sim=$('#settings-ux-test-'+kind).value;const messages={success:type==='tools'?'模擬探測完成：list_tools、read_project、inspect_node（示意能力）':'模擬檢查成功；未執行任何程序或連線。',missing:kind==='cli'?'模擬：找不到執行檔。請檢查路徑或 PATH。':'模擬：無法連線。請檢查啟動命令或 URL。',auth:'模擬：驗證失敗。請檢查系統憑證參照。',timeout:'模擬：等待逾時。正式版須核對程序與伺服器的實際狀態。'};lastTest[kind]=`<strong class="${sim==='success'?'good':'bad'}">${messages[sim]}</strong><br>${result}`;$('#settings-ux-result-'+kind).innerHTML=lastTest[kind];toast('已顯示模擬測試結果')}
function serverChange(key,v){const list=get('mcp.servers'),s=list.find(x=>x.id===selectedServer);if(!s)return;s[key]=v;updateField('mcp.servers',list)}
function addServer(){const list=get('mcp.servers');if(list.length>=20)return;const id='server-'+Date.now().toString(36)+'-'+Math.random().toString(36).slice(2,5);let n=2;while(list.some(s=>s.name==='New Server '+n))n++;list.push({id,name:'New Server '+n,transport:'stdio',command:'mcp-server',args:'',url:'',credentialRef:'',enabled:true});selectedServer=id;updateField('mcp.servers',list);render()}
function exportData(){return {format:'EluSlot.Settings',version:1,profiles:{personal:clone(saved.personal),project:clone(saved.project)}}}
function download(){const blob=new Blob([JSON.stringify(exportData(),null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='EluSlot_Settings.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('已匯出已儲存設定；不包含工作階段或密鑰。')}
function importText(text){let incoming;try{incoming=sanitizeConfig(JSON.parse(text))}catch(e){show('無法匯入設定','<p class="bad">'+esc(e.message)+'</p><p>目前設定與未儲存變更保持不變。</p>');return false}dialogAction=()=>{for(const s of ['personal','project'])draft[s]=clone(incoming[s]);lastTest={};close();render();toast('已載入為草稿。請切換各範圍檢查並分別儲存。')};show('匯入設定預覽',`<p>將以檔案內容取代個人與專案的草稿覆寫；本次工作階段保留。資料先載入草稿，尚未儲存。</p><p>個人：${Object.keys(incoming.personal).length} 項 · 專案：${Object.keys(incoming.project).length} 項</p>`,`<button data-close>取消</button><button data-confirm class="primary">載入為草稿</button>`);return true}
function runChecks(){const result=[],test=(name,ok)=>result.push({name,ok});test('設定鍵唯一',new Set(FIELDS.map(f=>f.key)).size===FIELDS.length);test('10 個分類都有設定',CATEGORIES.length===10&&CATEGORIES.every(c=>FIELDS.some(f=>f.cat===c.id)));test('所有預設值可通過驗證',SCOPES.every(s=>!errors(s,{personal:{},project:{},session:{}}).length));test('所有作用範圍合法',FIELDS.every(f=>f.scopes.length&&f.scopes.every(s=>SCOPES.includes(s))));test('所有條件依賴有效',FIELDS.every(f=>(!f.depends||byKey[f.depends])&&(!f.dependsValue||byKey[f.dependsValue[0]])));test('沒有密鑰輸入欄位',!FIELDS.some(f=>/token|password|secret/i.test(f.key)));test('匯出排除工作階段',!Object.hasOwn(exportData().profiles,'session'));show('原型結構檢查',result.map(r=>`<div class="testcheck ${r.ok?'good':'bad'}">${r.ok?'✓':'✕'} ${esc(r.name)}</div>`).join('')+'<p class="muted">這是文件與設定模型檢查，不代表已測試真實 CLI、MCP、Git 或桌面 Host。</p>');return result}
function action(id){if(id==='addServer')addServer();if(id==='deleteServer'){const s=get('mcp.servers').find(s=>s.id===selectedServer);if(!s)return;dialogAction=()=>{updateField('mcp.servers',get('mcp.servers').filter(s=>s.id!==selectedServer));close();render()};show('移除伺服器','<p>從目前範圍的連線清單移除「'+esc(s.name)+'」；不刪除系統憑證或伺服器。</p>','<button data-close>取消</button><button data-confirm class="danger">移除連線草稿</button>')}if(id==='credentials')show('系統憑證參照','<p>正式版交由桌面系統的 CredentialService 管理憑證。設定檔只保存參照名稱，秘密不傳入 UI、不寫入專案，也不出現在匯出 JSON。</p><p>此原型不提供密鑰輸入或憑證寫入。</p>');if(id==='resetScope')confirmReset(true);if(id==='export')download();if(id==='import')$('#settings-ux-import-file').click();if(id==='checks')runChecks()}


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
