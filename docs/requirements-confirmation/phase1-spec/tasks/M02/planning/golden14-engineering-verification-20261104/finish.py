from pathlib import Path
import json,hashlib,html,datetime
P=Path(__file__).resolve().parent
r=json.loads((P/'results.json').read_text(encoding='utf-8'))
resume=json.loads((P/'stable-check-resume.json').read_text(encoding='utf-8'));r['commands'].append(resume)
r['status']='PARTIAL_ENGINEERING_VERIFICATION'
r['classification']=[{'id':'ENGINEERING-TOOLCHAIN-ALIAS','status':'BLOCKED_ENVIRONMENT','fact':'Named 1.99.1 toolchain absent; installed stable alias reports same rustc/cargo 1.99.1. Exact candidate invocation fails before compile. No global install or candidate change performed.','provider':'Build/toolchain engineer','owner_decision_required':False},{'id':'ENGINEERING-COMPILE-DIAGNOSTIC','status':'TIMEOUT' if resume['timeout'] else ('PASS' if resume['exit']==0 else 'FAIL_CANDIDATE_RESOURCE_MISSING'),'fact':'Explicit +stable diagnostic result is separate from exact named channel proof; cold initial compile timed out after 50 seconds, one resume reached tauri-build and failed exit101 because icons/icon.ico is missing. This is a candidate resource/fixture gap, not an intended behavioral RED and not absent dependency download evidence.','provider':'Build/toolchain engineer','owner_decision_required':False},{'id':'ENGINEERING-JS-PARSE','status':'PASS','fact':'node --check actual candidate app.js exited0; no browser/runtime claim','owner_decision_required':False}]
r['owner_questions']=[{'id':'GT-D1','selected':None,'meaning':'Empty shell versus specified business controls'},{'id':'GT-D2','selected':None,'meaning':'Generated project identity/version policy; example values are fixture only'},{'id':'GT-D3','selected':None,'meaning':'Supported target/version policy only; installation, hashes, lock and compile diagnosis assigned engineering'},{'id':'GT-D4','selected':None,'meaning':'Window/CSP/bundle/UI policy'}]
r['script_setup_issue']='Initial ROOT ancestor off by one corrected before measurements/seal; no source mutation.'
(P/'results.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
body='<h1>Golden14 工程條件驗證</h1><p>PARTIAL：實際候選的指定版本名稱尚未安裝；stable alias 為同版本，另列診斷結果。這不是 Owner 產品語意決策。</p><h2>工程角色自行處理</h2>'
for x in r['classification']:body+='<p>'+html.escape(str(x))+'</p>'
body+='<h2>實際命令與結果</h2>'
for x in r['commands']:body+='<details><summary>'+html.escape(x['id'])+' exit='+str(x.get('exit'))+'</summary><pre>'+html.escape(json.dumps(x,ensure_ascii=False,indent=2))+'</pre></details>'
body+='<h2>Owner 仍待決</h2><pre>'+html.escape(json.dumps(r['owner_questions'],ensure_ascii=False,indent=2))+'</pre><p>7項結構與保存檢查PASS；796來源零漂移，原候選hash未變。Node parse不證明Tauri runtime，+stable不是指定channel已入場。無採納、產品/native驗收。</p>'
(P/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Golden14 engineering verification</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{margin:12px}</style>'+body+'</html>',encoding='utf-8')
files={str(f.relative_to(P)):hashlib.sha256(f.read_bytes()).hexdigest() for f in P.rglob('*') if f.is_file() and 'target' not in f.relative_to(P).parts and f.name!='seal.json'}
(P/'seal.json').write_text(json.dumps({'author':'/root/golden_engineering_evidence','sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':files,'excluded':'target/** compiler cache, non-evidence'},indent=2),encoding='utf-8')
print(r['classification'])
