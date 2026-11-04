"""Add the owner's IDE-style Agent hosting direction as a proposed module view."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import html, json, sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/board'))
from board_core import snapshot_safe, domain

spec = {
    'module':'embedded-agent-workbench', 'requirement':'REQ-AGENT-HOST-01',
    'intent':'EluSlot hosts interactive Claude Code and Codex sessions like an IDE, in addition to external Agent MCP access and Agent-hosted EluSlot UI.',
    'state':'PLANNING', 'architecture_status':'PROPOSED_NOT_APPROVED',
    'implementation':'NOT_STARTED', 'verification':'NOT RUN',
    'options':[
        {'id':'EA-A','name':'Integrated terminal','proposal':'Web terminal view -> Rust input port -> PTY adapter -> official Agent CLI. Requires stdin, resize, interruption and process/session cleanup; existing ProcessPort is not an interactive terminal port.'},
        {'id':'EA-B','name':'Native Agent panel','proposal':'EluSlot chat/session/approval/diff UI -> shared application session boundary -> provider adapter. Codex App Server is a documented integration path; Claude Code programmatic CLI/Agent SDK is a documented path, with exact runtime, auth and capability differences still to validate.'},
    ],
    'ui_schema':{'controls':['Agent selector (Claude Code/Codex)','Project/worktree context','Session list','Prompt composer','Streaming conversation','Permission and question cards','Diff/evidence view','Cancel/resume'], 'states':['unconfigured','auth required','idle','running','waiting for approval','disconnected','failed','completed'], 'rules':['no run without bound project','never auto-approve permission requests','Agent completion is not product acceptance','do not silently switch projects on existing session']},
    'ownership':{'provider':'provider conversation and tool execution','application':'task/run binding, authority, leases and acceptance','ui':'projection and explicit user actions only'},
    'ports':'Proposed session input/output ports must be approved before skeleton or production code. Keep provider-specific protocol outside Domain.',
    'acceptance':['Claude Code and Codex evaluated separately','interactive input and streamed output proven','approval/deny/cancel reaches correct session once','project/run isolation','restart/disconnect recovery specified and tested','CLI and embedded panel share task/evidence gates'],
    'sources':['https://learn.chatgpt.com/docs/app-server','https://code.claude.com/docs/en/headless','https://code.claude.com/docs/en/vs-code'],
    'limitations':['No claim that a VS Code extension can be installed directly into a Tauri webview','No PTY, SDK runtime or authentication choice approved','No live Agent started; no provider integration tested'],
}
out = ROOT/'reports/rust-improvements/embedded-agents'
out.mkdir(parents=True,exist_ok=True)
payload=json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')
doc='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>IDE-style embedded Agents</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:32px auto;padding:20px;background:#111820;color:#edf2f8}a{color:#9dccff}pre{white-space:pre-wrap}td,th{border:1px solid #567;padding:12px;text-align:left}table{border-collapse:collapse;width:100%}</style><body><h1>EluSlot 內嵌 Claude Code / Codex</h1><p>Owner direction recorded. PLANNING / PROPOSED_NOT_APPROVED. Production and live verification: NOT RUN.</p><p>方向一：EluSlot 啟動 Agent CLI。方向二：Agent 經 MCP 連入 EluSlot。方向三：Agent 視窗內嵌 EluSlot Web 工作台。此次新增：EluSlot 內嵌 Agent 的互動終端或原生聊天面板。</p><h2>兩個候選切片</h2><table><tr><th>整合</th><th>方式與界線</th></tr>'''
for option in spec['options']:
    doc+='<tr><td>'+html.escape(option['name'])+'</td><td>'+html.escape(option['proposal'])+'</td></tr>'
doc+='''</table><h2>Proposed dependency / ownership view</h2><pre>EluSlot Agent UI (projection only)
  -> Session input port (proposed)
  -> Application: task/run binding + permission routing + leases
  -> Provider output ports (proposed)
       -> Codex App Server adapter
       -> Claude Code CLI / Agent SDK adapter
       -> PTY adapter (terminal option)
  -> Existing task/evidence acceptance gates

Provider owns conversation execution; application owns task authority.
Session creation binds project/worktree before spawning.
Cancel/disconnect/finalization semantics require approval before implementation.</pre><h2>UI schema</h2><pre>'''+html.escape(json.dumps(spec['ui_schema'],ensure_ascii=False,indent=2))+'''</pre><h2>Acceptance and open decisions</h2><pre>'''+html.escape(json.dumps({'acceptance':spec['acceptance'],'limitations':spec['limitations']},ensure_ascii=False,indent=2))+'''</pre><h2>Official sources</h2><ul>'''
doc+=''.join('<li><a href="'+url+'">'+url+'</a></li>' for url in spec['sources'])
doc+='</ul><script id="module-spec" type="application/json">'+payload+'</script></body></html>'
(out/'module.html').write_text(doc,encoding='utf-8')
now=datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
def mutate(data):
    ident='PD-RUST-EMBEDDED-AGENT-PLAN-01'
    if not any(t['id']==ident for t in data['tasks']):
        data['tasks'].append(domain.new_task(dict(id=ident,title='IDE-style embedded Claude Code and Codex sessions',kind='planning',zone='gray',bdd='Interactive Agent sessions hosted inside EluSlot preserve project binding, permission prompts, cancellation and evidence gates.',tdd='NOT RUN; approve architecture/contracts/UI schema before executable RED and implementation.',note='Parent: PD-RUST-IMPROVE-20261025\nPrimary Module: embedded-agent-workbench\nOwner direction REQ-AGENT-HOST-01. Terminal PTY vs native chat panel options in reports/rust-improvements/embedded-agents/module.html. Codex App Server / Claude Code programmatic integration documented. Current ProcessPort lacks interactive stdin/resize. No direct VS Code extension embedding assumption. Production blocked pending approved session ports/lifecycle/auth design.'),'agent',now))
    for task in data['tasks']:
        if task['id']=='PD-RUST-DISPATCH-MODES-DEC-01':
            task['note']+='\n['+now+'] Owner added IDE-style Agent hosting inside EluSlot, including Claude Code and Codex. Requirement confirmed; PTY vs native session panel architecture remains proposed. See PD-RUST-EMBEDDED-AGENT-PLAN-01.'
            task['version']=int(task.get('version',1))+1
            task['updatedAt']=now;task['updatedBy']='agent'
    data['asOf']=now
snapshot_safe.mutate_snapshot_file(ROOT/'docs/PROJECT-BOARD.html',mutate)
print('Recorded embedded-Agent direction and planning card; no production changes')
