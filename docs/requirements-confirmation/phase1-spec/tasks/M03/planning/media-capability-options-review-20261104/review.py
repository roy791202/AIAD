from pathlib import Path
import json, hashlib, re, tomllib, subprocess, copy, datetime, html
ROOT=Path('D:/AIAD')
OUT=Path(__file__).resolve().parent
C=OUT.parent/'media-capability-options-20261104'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def dump(n,o): (OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
before={p.name:sha(p) for p in C.iterdir() if p.is_file()}
s=read(C/'module-spec.json'); ev=read(C/'source-evidence.json'); findings=[]; checks=[]
def check(name,ok):
 checks.append({'name':name,'pass':bool(ok)})
 if not ok: findings.append(name)
seal=read(C/'seal.json')
check('candidate seal hashes',all(before.get(n)==h for n,h in seal['hashes'].items()))
check('source pointers live hashes',all(sha(ROOT/x['path'])==x['sha256'] for x in read(C/'source-bindings.json')))
for x in ev['evidence']:
 p=ROOT/x['path']; lines=p.read_text(encoding='utf-8-sig').splitlines()
 check('span '+x['path']+':'+str(x['start']),sha(p)==x['sha256'] and '\n'.join(lines[x['start']-1:x['end']])==x['snippet'])
check('assets and dependency hashes',all(sha(ROOT/x['path'])==x['sha256'] for x in ev['assets']+ev['dependency_inventory']+[ev['lock']]))
authority=read(ROOT/read(C/'source-bindings.json')[0]['path'])
check('796 authority entries unchanged',len(authority['source_hashes'])==796 and all(sha(ROOT/p)==h for p,h in authority['source_hashes'].items()))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
check('live versus authority HEAD separated',head==s['live_head']=='5b709343a890503ebbe24a802e43cda5647df124' and authority['head']==s['authority_head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(C/'index.html').read_text(encoding='utf-8'),re.S).group(1).replace('<\\/','</'))
check('HTML embedded model exact',embedded==s)
candidate=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M03/planning/preview-media-candidate-20261103/candidate.json')
check('eight dimensions retained',[(r['id'],r['family']) for r in s['rows']]==[(r['id'],r['family']) for r in candidate['rows']] and len(s['rows'])==8)
lock=tomllib.loads((ROOT/ev['lock']['path']).read_text(encoding='utf-8'))
actual=[dict(name=p['name'],version=p['version'],dependencies=p.get('dependencies',[])) for p in lock['package'] if p['name']=='png' or any(d=='png' or d.startswith('png ') for d in p.get('dependencies',[]))]
check('png consumer inventory exact',actual==ev['transitive_png_consumers'] and {p['name'] for p in actual}=={'png','ico','muda','tauri-codegen','tray-icon'})
check('shell XML IPC and filesystem boundaries',all(token in ev['evidence'][i]['snippet'] for i,token in [(2,'img.src = archKindIconSrc(kind)'),(3,'reader.readAsText(file, "UTF-8")'),(4,'await invoke("uidesign_build_preview"'),(5,'authorize("uidesign_build_preview")'),(7,'fs.write_atomic')]))
check('H2 materials bound proposal', 'No file/network/image loading as mock effect' in read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M03/planning/h2-exact-design/viewer-capability.json')['materials'] and 'proposed document behavior' in s['rows'][6]['source_observation'])
def semantics(m):
 return (all(r['imported_format_support']=='NOT_PROVEN' and r['native_decode_render']=='NOT RUN' and all(r[k] is None for k in ['owner_selection','format','sdk','thresholds']) for r in m['rows']) and all(o['decision'] is None for o in m['options']) and m['approval'] is None and m['module_complete'] is False and 'shell icon display' in m['rows'][1]['source_observation'] and 'not arbitrary imported SVG sanitization' in m['rows'][1]['source_observation'] and 'does not establish opaque imported-media preservation or decoding' in m['rows'][5]['source_observation'] and 'communication-only' in m['rows'][7]['source_observation'])
check('bounded semantic claims',semantics(s))
probes=[]
for name,mutate in [('dependency as decoder',lambda m:m['rows'][0].update(imported_format_support='SUPPORTED')),('native execution promotion',lambda m:m['rows'][1].update(native_decode_render='PASS')),('SDK adoption',lambda m:m['rows'][2].update(sdk='png')),('threshold adoption',lambda m:m['rows'][3].update(thresholds=4096)),('shell SVG as imported sanitizer',lambda m:m['rows'][1].update(source_observation='Imported SVG sanitized')),('XML as media decode',lambda m:m['rows'][5].update(source_observation='XML proves media decode')),('preview as product renderer',lambda m:m['rows'][7].update(source_observation='product renderer')),('approval promotion',lambda m:m.update(approval='approved')),('completion promotion',lambda m:m.update(module_complete=True))]:
 m=copy.deepcopy(s); mutate(m); rejected=not semantics(m); probes.append({'probe':name,'expected':'REJECT','observed':'REJECT' if rejected else 'ACCEPT'}); check('negative probe '+name,rejected)
after={p.name:sha(p) for p in C.iterdir() if p.is_file()}
check('candidate unchanged before after',before==after)
result={'result':'BOUNDED_PASS_DOCUMENT_REVIEW' if not findings else 'FINDINGS','reviewer':'/root/media_capability_options_review','author':s['author'],'independent':True,'live_head':head,'authority_head':authority['head'],'checks':checks,'candidate_hashes_before':before,'candidate_hashes_after':after,'historical_pass_rerun':False,'product_native_build_package_install_dcc_regression':'NOT RUN','limitations':['Static source/document review only; NOT_PROVEN does not mean unsupported.','png/ico/muda/tauri-codegen/tray-icon lock presence relates to desktop icon/menu/build consumers; no M03 imported decoder is established.','Command opens OS association directly; host writes via FileSystemPort. This review observes existing wiring and does not certify architecture conformance.','No Owner format, SDK, threshold, fixture acquisition or architecture approval.']}
dump('results.json',result); dump('probes.json',probes); dump('findings.json',{'findings':findings,'severity':'none' if not findings else 'review required'})
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 independent capability options review</title><h1>'+result['result']+'</h1><p>獨立文件審查 /root/media_capability_options_review；作者 /root/yellow_remaining_execute。</p><p>8 維 source comparison、796 authority hashes、live/source bindings、HTML embedded JSON、candidate seal 均已核對。9 個新增負向語意 probes；未重跑歷史 PASS。</p><p>PNG/ICO 依賴與 shell SVG 顯示不構成 imported-media decoder；XML readAsText 不構成 media decode。UI IPC、command authorization/root/open、host FileSystemPort write 的邊界維持事實描述。</p><p>所有 imported support NOT_PROVEN；native/build/package/install/DCC/regression NOT RUN。Owner 決策維持 null，模組未完成。</p><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in result['limitations'])+'</ul><a href="results.json">results</a> · <a href="probes.json">negative probes</a> · <a href="findings.json">findings</a>',encoding='utf-8')
dump('seal.json',{'status':'SEALED_STOP_WRITING','generated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'candidate_unchanged':before==after,'hashes':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'result':result['result'],'checks':len(checks),'findings':findings,'probes':len(probes)}))
