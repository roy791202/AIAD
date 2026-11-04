import json, hashlib, subprocess, html
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter
from tools.board.board_core.snapshot_safe import split_snapshot, mutate_snapshot_file
from tools.board.board_core.json_store import FileLock

ROOT=Path.cwd(); OUT=Path(__file__).parent
def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(name,obj): (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base=read('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
assert all(sha(p)==h for p,h in base['source_hashes'].items())
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==base['head']
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()==base['branch']
board=Path('docs/PROJECT-BOARD.html'); before_parts=split_snapshot(board.read_text(encoding='utf-8')); before=json.loads(before_parts[1])
now=datetime.now(timezone.utc).isoformat(); card='PD-P1-M01-PREP-01'
routes=[{'command':c,'handler_line':n,'source':'apps/sgenaxis-desktop/src-tauri/src/commands.rs','current':v} for c,n,v in [
 ('host_new_project_directory',1165,'native save-file picker then deprecated HOST root creator; cancellation exits; no wizard'),
 ('host_create_project_directory',1208,'UI raw parent/name then deprecated HOST under-parent creator; no selection capability'),
 ('host_create_project_with_preferences',1259,'UI raw parent/name/preferences then DispatchHost project_policy_create; S2 returns WizardRequired')]]
gaps=[
 {'id':'S3-G1','gap':'Native selection authority is not a UI path string or UUID shape. Existing request schema names selection IDs without defining trusted issuer/storage/revocation.','next':'Specify actual Tauri sender/window authentication, parent selection creation, session binding and cancellation/revocation lifetime; do not reuse raw path as authority.'},
 {'id':'S3-G2','gap':'Draft owner lifecycle across close/reopen/window/session changes is not an exact approved runtime contract.','next':'Define owner key and every transition, stale ownership outcomes, retained draft reopen and project switch guards; no hidden global owner.'},
 {'id':'S3-G3','gap':'request_id shape alone does not specify idempotency.','next':'Define request fingerprint, same-ID same/different payload, in-flight replay, terminal retention and restart semantics, bounded lifetime and exact errors.'},
 {'id':'S3-G4','gap':'Successful persistence does not alone authorize late UI current-project binding. Existing UI calls bindPickedProjectRoot after legacy create.','next':'Define captured owner/request/revision correlation, committed-but-detached response and no rollback of committed bytes; stale completion must not switch project.'},
 {'id':'S3-G5','gap':'Six-step schema exists as proposed packet, but no complete S3 response/error/permission/caller migration contract locked.','next':'Reconcile with adopted S2 typed outcomes including Partial/RecoveryRequired and commit evidence; define command registration/permissions and UI state projection before Skeleton.'}]
cases=[('cancel','native picker cancelled','begin requested','no draft persistence or current-project switch'),('forged','raw path or another window selection','begin requested','explicit rejection and zero store calls'),('owner','draft belongs to another session','update requested','owner rejection and unchanged revision'),('revision','captured revision is stale','save requested','conflict without store call'),('replay','same request ID and identical payload','save repeated','one commit and same correlated terminal result'),('collision','same request ID and different payload','save requested','explicit request conflict and no second commit'),('late','owner changes while commit is pending','old completion arrives','persisted proof retained and current project unchanged'),('partial','store returns Partial or RecoveryRequired','save completes','structured non-success result and no current-project switch'),('legacy','each of three old entry routes','user starts creation','wizard route only; no deprecated direct-create bypass'),('steps','unfinished decisions exist','user saves draft at any of six steps','draft resumable without falsely finalizing or generating')]
model={'module':'M01','slice':'S3 entry/lifecycle preparation','status':'READINESS_HANDOFF_DELIVERED_NOT_READY_FOR_IMPLEMENTATION','at':now,'authority':'Original M01 planning envelope only; S2 D1-D7 remains adopted and accepted','routes':routes,'ui_evidence':{'source':'apps/sgenaxis-desktop/ui/app.js','lines':[1269,1289,1309,1318],'behavior':'prompt name, pick parent raw path, choose preferences, deprecated create, bind result'},'gaps':gaps,'planned_tests':[{'id':'S3-ENTRY-%02d'%(i+1),'fixture':k,'given':g,'when':w,'then':t,'result':'PLANNED / NOT RUN'} for i,(k,g,w,t) in enumerate(cases)],'scope':{'allowed':['M01/planning/s3-entry-review/**','M01/planning/current-state.json','own board evidence'],'protected':'All product/test source; other module artifacts; accepted S1/S2 contracts','candidate_product_envelope':'../exact-design/envelope.json S3 remains candidate, not newly approved'},'acceptance':'Planning handoff only; full PREP acceptance and S3 architecture approval still pending','verification':{'source_files_unchanged':len(base['source_hashes']),'branch':base['branch'],'head':base['head'],'product_tests':'NOT RUN','build':'NOT RUN','native':'NOT RUN','RED':'NOT RUN','review':'Source inspection by same assistant; no independent delegated reviewer'},'next':'Complete one precise S3 owner/selection/idempotency/response/permission/UI packet, fixtures and BDD/TDD before asking Owner once; do not build speculative Skeleton.'}
put('module-spec.json',model)
feature='Feature: M01 wizard entry and lifecycle preparation\n  # PLANNED: not executable RED and not an approved new S3 contract\n'
for i,(_,g,w,t) in enumerate(cases): feature+=f'\n  Scenario: S3-ENTRY-{i+1:02d}\n    Given {g}\n    When {w}\n    Then {t}\n'
(OUT/'module.feature').write_text(feature,encoding='utf-8')
body='<h1>M01-S3 入口與生命週期銜接盤點</h1><p>準備交付；尚未核准 S3 Skeleton。S2 已完成，不重開其驗收。</p><h2>現況與差額</h2>'
body+='<p>三個舊入口仍存在；S2 HOST 已 fail-closed。現有 UI 仍以 parent path 建立後綁定，尚未遷移六步精靈。此為來源檢查，不是 native 行為證明。</p>'
body+='<h2>架構定位</h2><pre>UI → Tauri authenticated command → DispatchHost owner/use case → adopted S1/S2 → declared IO Port\nNative picker → trusted selection capability → owner-bound request\nDomain owns definition; HOST authorizes session; UI renders projection. Proposed S3 seams remain unapproved.</pre>'
body+='<h2>待精確化契約</h2>'+''.join('<p><b>'+x['id']+'</b> '+html.escape(x['gap'])+'<br>下一步：'+html.escape(x['next'])+'</p>' for x in gaps)
body+='<h2>BDD／TDD</h2><p>10 個規劃情境，全部 NOT RUN；fixture 名稱是規劃標籤，尚非可執行測試資料。有效 RED 必須可編譯且因對應缺失行為失敗，不接受 fixture／環境錯誤。</p><table>'+''.join('<tr><td>'+x['id']+'</td><td>'+html.escape(x['then'])+'</td><td>NOT RUN</td></tr>' for x in model['planned_tests'])+'</table>'
body+='<h2>範圍與驗證</h2><p>僅文件與本卡證據；796 檔來源 SHA、branch、HEAD 核對一致。產品／測試程式碼零修改。build、native、RED、GREEN 均未重跑。</p><h2>模組狀態</h2><p>M01 父準備卡維持黃燈；本次不是完整 PREP 驗收。下一步補齊精確契約整包，再一次確認；其他模組不受此阻擋。</p>'
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M01 S3 entry review</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.7}td{padding:8px;border:1px solid #ccc}pre{white-space:pre-wrap}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
statepath=OUT.parent/'current-state.json'; state=read(statepath);state['s3_preparation']={'status':model['status'],'report':'s3-entry-review/index.html','gaps':[g['id'] for g in gaps],'product_implementation':'NOT AUTHORIZED FOR UNAPPROVED S3 SKELETON'};state['next_step']=model['next'];put('verification.json',model['verification']);statepath.write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report=str((OUT/'index.html').relative_to(ROOT)).replace('\\','/')
def mutate(s):
 t=next(t for t in s['tasks'] if t['id']==card)
 t['s3EntryReview']={'status':model['status'],'report':report,'at':now,'productSourceChanges':0}
 t['remainingGap']='S3 exact trusted selection/owner lifecycle/idempotency/late completion/response and permission packet remains incomplete; S1/S2 accepted scope preserved.'
 t['nextStep']=model['next']; t['notes']=t.get('notes','')+'\n['+now+'] S3 entry/lifecycle source review delivered: 3 legacy handlers and UI call chain mapped; 5 precise planning gaps, 10 PLANNED/NOT RUN behavior cases. No product changes. '+report
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
afterparts=split_snapshot(board.read_text(encoding='utf-8'));after=json.loads(afterparts[1])
assert before_parts[0]==afterparts[0] and before_parts[2]==afterparts[2]
assert {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'}
assert [t for t in before['tasks'] if t['id']!=card]==[t for t in after['tasks'] if t['id']!=card]
assert all(sha(p)==h for p,h in base['source_hashes'].items())
put('board-evidence.json',{'before':dict(Counter(t['zone'] for t in before['tasks'])),'after':dict(Counter(t['zone'] for t in after['tasks'])),'other_cards_root_shell_preserved':True})
put('artifact-hashes.json',{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({'report':report,'counts':dict(Counter(t['zone'] for t in after['tasks'])),'source_unchanged':796}))
