import json,hashlib,subprocess,copy,html
from pathlib import Path
from datetime import datetime
R=Path('D:/AIAD');P=Path(__file__).resolve().parent;B=P.parent;C=B/'golden14-resource-correction-20261104';O=B/'golden14-candidate-20261104'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def ck(n,v):checks.append({'id':n,'pass':bool(v)})
before={k:sha(C/k) for k in read(C/'seal.json')['files']};ob={k:sha(O/k) for k in read(O/'seal.json')['files']};d=read(C/'results.json')
for k,v in read(C/'seal.json')['files'].items():ck('seal:'+k,sha(C/k)==v)
for k,v in read(O/'seal.json')['files'].items():ck('original:'+k,sha(O/k)==v)
src=R/d['resource']['source'];dst=C/'scratch/program/src-tauri/icons/icon.ico'
ck('icon-three-way-hash',sha(src)==sha(dst)==d['resource']['sha256']==d['resource']['copy_sha256']);ck('icon-size',src.stat().st_size==26964==d['resource']['bytes'])
for f in (O/'expected').rglob('*'):
 if f.is_file():ck('scratch-preserved:'+str(f.relative_to(O/'expected')),sha(f)==sha(C/'scratch'/f.relative_to(O/'expected')))
ck('outside14','OUTSIDE_GOLDEN14_REPLAN_REQUIRED' in d['resource']['admission']);ck('license-boundary','no external distribution license asserted' in d['resource']['role'])
cs=[x for x in d['commands'] if x['id'].startswith('resource-check')]
ck('two-segments',len(cs)==2)
for x in cs:
 ck(x['id']+':argv',x['argv']==['cargo','+stable','check','--offline','--locked']);ck(x['id']+':timeout',x['timeout'] and x['exit'] is None and 59<=x['seconds']<65);ck(x['id']+':log-parity',read(C/(x['id']+'.json'))==x)
ck('finished-output-not-exitproof','Finished `dev` profile' in cs[-1]['stderr'] and cs[-1]['exit'] is None)
ck('namedchannel-not-listed','1.99.1' not in read(C/'installed-toolchains.json')['stdout']);ck('stable-only','stable-x86_64-pc-windows-msvc' in read(C/'installed-toolchains.json')['stdout'])
ck('author-not-adopted',d['selected'] is None and d['adoption'] is None and d['product_pass'] is False);ck('partial-classification',d['status']=='PARTIAL_TIMEOUT')
a=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];drift=[k for k,v in a.items() if not (R/k).exists() or sha(R/k)!=v];ck('authority796',len(a)==796 and not drift)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip();ck('live-head',head==read(C/'head.json')['stdout'].strip())
proc=subprocess.check_output(['powershell','-NoProfile','-Command',"Get-CimInstance Win32_Process | Where-Object { $_.Name -in @('cargo.exe','rustc.exe','rustup.exe') } | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"],text=True).strip();ck('no-active-rust-process',not proc)
def valid(x):return x['status']=='PARTIAL_TIMEOUT' and not x['product_pass'] and x['selected'] is None and x['adoption'] is None and 'REPLAN_REQUIRED' in x['resource']['admission'] and all(z['timeout'] and z['exit'] is None and z['argv']==['cargo','+stable','check','--offline','--locked'] for z in x['commands'] if z['id'].startswith('resource-check'))
probes=[]
for name,mut in [('false-pass',lambda x:x.update(status='PASS')),('product-pass',lambda x:x.update(product_pass=True)),('adopted',lambda x:x.update(adoption='yes')),('selected',lambda x:x.update(selected='A')),('admission',lambda x:x['resource'].update(admission='ADMITTED')),('exit-invention',lambda x:next(z for z in x['commands'] if z['id']=='resource-check-2').update(exit=0)),('toolchain-conflation',lambda x:next(z for z in x['commands'] if z['id']=='resource-check-2').update(argv=['cargo','check','--offline','--locked'])),('timeout-as-fail',lambda x:x.update(status='FAIL'))]:
 q=copy.deepcopy(d);mut(q);probes.append({'id':name,'pass':not valid(q)})
ck('fresh-negative-probes',all(x['pass'] for x in probes));ck('candidate-unchanged',before=={k:sha(C/k) for k in before});ck('original-unchanged',ob=={k:sha(O/k) for k in ob})
out={'reviewer':'/root/golden_resource_review','author':d['author'],'status':'BOUNDED_RESOURCE_EVIDENCE_REVIEW_PASS' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','checks':checks,'probes':probes,'findings':[],'head':head,'authority_count':len(a),'authority_drift':drift,'process_snapshot':proc,'limits':['Second log includes Finished dev but timeout wrapper has no exit0; no complete compile verdict claimed.','Additional icon is isolated diagnostic resource; formal14-path envelope revision remains required.','No distribution license verified; existing repository provenance only.','Product/native/runtime NOT RUN; no cold compile rerun or historical PASS rerun.']}
(P/'results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8');(P/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Golden14 resource independent review</title><h1>'+out['status']+'</h1><p>既有 icon 的來源與複本雜湊一致；第15項資源尚待 envelope 重規劃。兩次60秒診斷均無退出碼；第二次雖輸出 Finished，仍只能列 PARTIAL_TIMEOUT，不宣稱編譯通過或失敗。</p><pre>'+html.escape(json.dumps(out,ensure_ascii=False,indent=2))+'</pre></html>',encoding='utf-8');files={f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name!='seal.json'};(P/'seal.json').write_text(json.dumps({'reviewer':out['reviewer'],'sealed_at':datetime.now().astimezone().isoformat(),'files':files},indent=2),encoding='utf-8');print(out['status'],len(checks),len(probes),[x['id'] for x in checks if not x['pass']])
