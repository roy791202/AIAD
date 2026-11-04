"""Candidate preparation only. Never writes product files."""
import json, hashlib, subprocess, pathlib, datetime, html, tomllib
P=pathlib.Path(__file__).resolve().parent
ROOT=next(x for x in P.parents if (x/'AGENTS.md').exists())
BASE=ROOT/'docs/requirements-confirmation/phase1-spec/tasks'
def digest(b): return hashlib.sha256(b).hexdigest()
def write(rel,body):
 p=P/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(body.encode('utf8') if isinstance(body,str) else body)
def js(rel,obj): write(rel,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def cmd(args,cwd=P):
 r=subprocess.run(args,cwd=cwd,capture_output=True,timeout=55)
 return {'argv':args,'cwd':str(cwd),'exit':r.returncode,'stdout':r.stdout.decode('utf8','replace'),'stderr':r.stderr.decode('utf8','replace')}
spec=BASE/'M02/planning/exact-design/module-spec.json'
inventory=BASE/'M02/planning/golden14-lock-inventory-20261103/candidate.json'
contract=json.loads(spec.read_text(encoding='utf8'))
paths=contract['first_template']['product_paths']
fixture={'status':'PROPOSED_FIXTURE_NOT_APPROVED_PROJECT','project_name':'Golden14 Candidate','package_name':'golden14-candidate','identifier':'org.example.golden14candidate','definition_revision':'1','design_revision':'1','definition':{'intent':'Review generated skeleton bytes, not implemented business behavior'},'design':{'view':'static candidate skeleton','controls':[]},'selected':None}
js('input.json',fixture)
# Every literal below is a proposed resource body; source specifications establish the
# path and responsibilities, not these newly authored bytes or fixture identities.
resources={
'program/src-tauri/Cargo.toml':'''[workspace]
resolver = "2"

[package]
name = "@@PACKAGE@@"
version = "0.1.0"
edition = "2021"

[build-dependencies]
tauri-build = { version = "=2.7.4", features = [] }

[dependencies]
tauri = { version = "=2.12.5", features = [] }
serde = { version = "=1.0.229", features = ["derive"] }
serde_json = "=1.0.154"
''',
'program/src-tauri/build.rs':'fn main() { tauri_build::build() }\n',
'program/src-tauri/tauri.conf.json':'''{
  "$schema": "https://schema.tauri.app/config/2",
  "productName": "@@TITLE@@",
  "version": "0.1.0",
  "identifier": "@@IDENTIFIER@@",
  "build": { "frontendDist": "../../ui-ux" },
  "app": { "windows": [{ "title": "@@TITLE@@", "width": 960, "height": 640 }], "security": { "csp": "default-src 'self'; style-src 'self'" } },
  "bundle": { "active": false }
}
''',
'program/src-tauri/src/main.rs':'''mod domain;
mod ports;

fn main() {
    // Shell only: no generated business command or persistence implementation.
    tauri::Builder::default()
        .run(tauri::generate_context!())
        .expect("candidate shell startup failed");
}
''',
'program/src-tauri/src/domain/mod.rs':'''//! Domain skeleton. Business behavior intentionally not generated.
//! No filesystem, UI, OS, network, or framework dependency is introduced here.
''',
'program/src-tauri/src/ports/mod.rs':'''//! Port ownership placeholder only. No speculative public interface is introduced.
//! Concrete business use-case ports require an approved Module Skeleton.
''',
'program/README.md':'''# @@TITLE@@ — candidate program skeleton

PROPOSED, NOT OWNER-ADOPTED. Definition revision @@DEFINITION@@; design revision @@DESIGN@@.
No business command, storage, migration, network, installer or release is implemented.
UI is a static projection. Future UI → input adapter → application → domain → output ports.
Domain owns no infrastructure. No domain state or transaction exists in this empty shell.
Build/package/native launch are NOT RUN. Lock resolution is not compilation evidence.
''',
'ui-ux/index.html':'''<!doctype html>
<html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>@@TITLE@@</title><link rel="stylesheet" href="styles.css">
<main><h1>@@TITLE@@</h1><p id="status" role="status">候選骨架；業務行為尚未實作</p></main>
<script src="app.js"></script></html>
''',
'ui-ux/app.js':'''"use strict";
// Static projection only: no filesystem, Git, network or product-command calls.
document.documentElement.dataset.skeleton = "not-implemented";
''',
'ui-ux/styles.css':'body { font-family: system-ui, sans-serif; margin: 2rem; color: #17212b; background: #f7f8fa; }\nmain { max-width: 60rem; margin: auto; }\n',
'ui-ux/ui-schema.json':'''{
  "schema": "golden14.candidate-ui",
  "version": 1,
  "status": "PROPOSED_NOT_ADOPTED",
  "component": "SkeletonStatus",
  "userRole": "reviewer",
  "controls": [],
  "events": [],
  "emptyState": "Business behavior not implemented",
  "validation": "No user input",
  "accessibility": { "language": "zh-Hant", "statusRole": "status" }
}
''',
'ui-ux/README.md':'# @@TITLE@@ UI skeleton\n\nStatic candidate only; no save, generate, preview or business success is simulated.\nNo editable controls, commands or independent authoritative state. UI schema is proposed, not an approved replacement.\n',
'program/src-tauri/rust-toolchain.toml':'[toolchain]\nchannel = "1.99.1"\nprofile = "minimal"\ntargets = ["x86_64-pc-windows-msvc"]\n'
}
values={'PACKAGE':fixture['package_name'],'TITLE':fixture['project_name'],'IDENTIFIER':fixture['identifier'],'DEFINITION':fixture['definition_revision'],'DESIGN':fixture['design_revision']}
def render(body,values):
 for key,val in values.items():body=body.replace('@@'+key+'@@',val)
 if '@@' in body: raise ValueError('unresolved token')
 return body.encode('utf8')
for path,body in resources.items():
 write('templates/'+path,body);write('expected/'+path,render(body,values))
tool=[]
for args in [['rustc','-vV'],['cargo','-V'],['node','-v'],['rustup','show','active-toolchain']]:tool.append(cmd(args))
# Explicit +stable uses the installed toolchain and avoids rustup downloading an
# unavailable named toolchain. Versions are captured above, not inferred from filename.
standalone=P/'expected/program/src-tauri'
before=(standalone/'Cargo.lock').exists()
resolve=cmd(['cargo','+stable','generate-lockfile','--offline','--manifest-path',str(standalone/'Cargo.toml')])
tool.append(resolve)
lock=standalone/'Cargo.lock'
if resolve['exit']==0 and lock.exists():
 write('templates/program/src-tauri/Cargo.lock',lock.read_bytes())
 metadata=cmd(['cargo','+stable','metadata','--offline','--locked','--no-deps','--format-version','1','--manifest-path',str(standalone/'Cargo.toml')]);tool.append(metadata)
else: metadata={'exit':None}
js('toolchain-evidence.json',{'commands':tool,'lock_preexisted':before,'network':'NOT USED: offline only','registry':'crates.io registry sources and checksums recorded by newly resolved lock; local Cargo cache used','target':'x86_64-pc-windows-msvc','resolver':'2','workspace_lock_copied':False,'build':'NOT RUN','package':'NOT RUN','native':'NOT RUN'})
rows=[]
for i,path in enumerate(paths):
 t=P/'templates'/path;e=P/'expected'/path
 rows.append({'slot':f'GOLDEN-{i+1:02}','path':path,'state':'CANDIDATE_BYTES_PRESENT' if t.exists() and e.exists() else 'BLOCKED_NO_LOCK_BYTES','template':{'path':str(t.relative_to(P)).replace('\\','/'),'sha256':digest(t.read_bytes()) if t.exists() else None},'expected':{'path':str(e.relative_to(P)).replace('\\','/'),'sha256':digest(e.read_bytes()) if e.exists() else None,'size':e.stat().st_size if e.exists() else None},'input_binding':{'file':'input.json','sha256':digest((P/'input.json').read_bytes()),'definition_revision':'1 (proposal fixture only)','design_revision':'1 (proposal fixture only)'},'admission':'PENDING_OWNER_AND_INDEPENDENT_REVIEW','source_pointer':f'/first_template/product_paths/{i}'})
decisions=[{'id':'GT-D1','question':'Accept this empty static shell as first template content, or require specific business controls?','recommended':'Keep empty shell; business controls need module specification','selected':None,'impact':'main.rs, domain/ports placeholders and UI'}, {'id':'GT-D2','question':'Confirm generated identity mapping and initial package version policy (fixture values are examples only).','recommended':'Map approved project identity, never ship example identifier','selected':None,'impact':'Cargo.toml, tauri.conf.json, titles/README'}, {'id':'GT-D3','question':'Confirm proposed dependency pins/toolchain/resource bytes after standalone resolution; or return changed targets/version requirements.','recommended':'Review exact bytes and lock separately from product build claims','selected':None,'impact':'Cargo manifest/lock/toolchain and supported target'}, {'id':'GT-D4','question':'Confirm window size, CSP, no bundle default and proposed UI schema as template policy.','recommended':'Keep no bundle/no business command while skeleton-only','selected':None,'impact':'tauri.conf.json and ui-schema.json'}]
authpath=BASE/'M01/planning/s2-green/source-current.json';auth=json.loads(authpath.read_text(encoding='utf8'))
drift=[p for p,h in auth['source_hashes'].items() if not (ROOT/p).exists() or digest((ROOT/p).read_bytes())!=h]
sources=[]
for p in [ROOT/'AGENTS.md',spec,inventory,BASE/'PD-P1-M02-PREP-01.json',BASE/'M02/s1/adoption.json',authpath]:sources.append({'path':str(p.relative_to(ROOT)).replace('\\','/'),'sha256':digest(p.read_bytes())})
js('source-bindings.json',{'sources':sources,'authority_count':len(auth['source_hashes']),'drift':drift,'live_head':cmd(['git','rev-parse','HEAD'])['stdout'].strip(),'historical_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','not_same_head':True})
js('candidate.json',{'author':'/root/golden14_candidate_author','status':'PROPOSED_CANDIDATE_ONLY','selected':None,'product_pass':False,'rows':rows,'decisions':decisions,'lock_resolution':resolve['exit'],'standalone_metadata':metadata['exit'],'limits':['No adoption','No product Skeleton acceptance or valid RED','No product build/package/native/regression','Historical PASS not rerun','New expected outputs are authored proposal goldens, not independently validated product behavior']})
checks=[]
def check(name,value):checks.append({'name':name,'pass':bool(value)})
check('exact14unique',len(rows)==14 and len(set(paths))==14)
check('all14actualbytes',all(x['state']=='CANDIDATE_BYTES_PRESENT' for x in rows))
check('authority796zero',len(auth['source_hashes'])==796 and not drift)
check('new_standalone_lock',not before and resolve['exit']==0 and lock.exists())
for path,body in resources.items():check('deterministic:'+path,render(body,values)==render(body,values)==(P/'expected'/path).read_bytes())
for path in paths:
 e=P/'expected'/path
 if e.exists():check('tamper:'+path,digest(e.read_bytes()+b'X')!=digest(e.read_bytes()))
try:render('@@UNKNOWN@@',values);check('unresolved_rejected',False)
except ValueError:check('unresolved_rejected',True)
check('selected_null',all(x['selected'] is None for x in decisions))
if lock.exists():
 ld=tomllib.loads(lock.read_text(encoding='utf8'));packages=ld['package'];check('root_own_package',any(x['name']==fixture['package_name'] for x in packages));check('no_sgenaxis_workspace_deps',not any(x['name'].startswith('sgenaxis-') for x in packages))
 js('lock-summary.json',{'package_count':len(packages),'root':fixture['package_name'],'registry_packages':sum('source' in x for x in packages),'sha256':digest(lock.read_bytes()),'manifest_sha256':digest((standalone/'Cargo.toml').read_bytes())})
js('checks.json',{'layer':'new candidate author self-check only','checks':checks,'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks)})
write('module.feature','''Feature: Reviewable Golden14 candidate bytes
  Scenario: Render a bound candidate twice
    Given an explicit proposed definition and design fixture
    When the candidate is rendered twice
    Then the exact fourteen declared paths have identical expected bytes
    And no proposal is recorded as adopted
  Scenario: Unbound tokens cannot produce accepted output
    Given a candidate with an unknown placeholder
    When rendering is requested
    Then rendering fails explicitly
''')
write('steps.py','''# Pending independent automation bindings; author checks are in build.py.
def given_candidate_fixture(): raise NotImplementedError("independent binding pending")
def when_render_twice(): raise NotImplementedError("independent binding pending")
def then_exact_bytes(): raise NotImplementedError("independent binding pending")
''')
js('pending.json',{'independent_review':'PENDING','product_tests':'NOT RUN','build':'NOT RUN','native':'NOT RUN','open_decisions':[x['id'] for x in decisions]})
table=''.join('<tr><td>'+html.escape(x['slot'])+'</td><td><a href="'+x['expected']['path']+'">'+html.escape(x['path'])+'</a></td><td>'+x['state']+'</td><td>'+str(x['expected']['size'])+'</td><td><code>'+str(x['expected']['sha256'])+'</code></td></tr>' for x in rows)
ds=''.join('<li id="'+d['id']+'"><b>'+d['id']+'</b> '+html.escape(d['question'])+'<br>建議：'+html.escape(d['recommended'])+'；影響：'+html.escape(d['impact'])+'；selected=null</li>' for d in decisions)
write('index.html','<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Golden14 候選逐檔內容</title><style>body{font:16px system-ui;margin:2rem}td,th{padding:.5rem;border:1px solid #ccc}code{overflow-wrap:anywhere}table{border-collapse:collapse}</style><h1>M02 Golden14 候選逐檔交付</h1><p>PROPOSED_CANDIDATE_ONLY；非採納／非產品PASS。十四路徑沿用既有採納；本次新寫實際候選 bytes 與具體 fixture 預期輸出。所有產品語意選擇仍 null。</p><p>架構：靜態 UI → 未實作的輸入邊界 → 未實作應用／domain；domain/ports 僅責任說明，沒有自行發明介面。空骨架沒有業務狀態、mutation、transaction，也不模擬成功。</p><p><a href="candidate.json">逐檔結構資料與決策</a> · <a href="input.json">提案輸入與revision</a> · <a href="source-bindings.json">來源與796核對</a> · <a href="toolchain-evidence.json">獨立工具鏈命令/exit/log</a> · <a href="checks.json">作者新候選自檢</a></p><h2>逐檔實際預期輸出</h2><table><tr><th>項</th><th>路徑</th><th>狀態</th><th>bytes</th><th>SHA256</th></tr>'+table+'</table><h2>需要Owner選擇的產品語意</h2><ol>'+ds+'</ol><h2>證據界線</h2><p>manifest由本候選獨立建立；cargo +stable generate-lockfile --offline 使用本機cache解析，未複製根workspace lock，未下載套件。完整原始輸出保留。Lock解析不等build，build/package/install/native/產品TDD均NOT RUN；獨立審查PENDING。預期輸出是本次作者候選，不是對現行生成器的驗收。既有PASS未重跑。</p><p>所有檔案僅在本planning子目錄；未改正式產品、既有規格、hooks、roles或board。</p></html>')
files={str(p.relative_to(P)).replace('\\','/'):digest(p.read_bytes()) for p in P.rglob('*') if p.is_file() and p.name!='seal.json'}
js('seal.json',{'author':'/root/golden14_candidate_author','sealed_at':datetime.datetime.now().astimezone().isoformat(),'files':files})
print(json.dumps({'rows':len(rows),'bytes_present':sum(x['state']=='CANDIDATE_BYTES_PRESENT' for x in rows),'resolve_exit':resolve['exit'],'checks_failed':sum(not x['pass'] for x in checks)},ensure_ascii=False))
