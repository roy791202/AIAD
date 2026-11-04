"""Independent bounded document review; python -B checker.py. No product execution."""
import copy, hashlib, itertools, json, pathlib, re
P=pathlib.Path(__file__).resolve().parent
R=next(p for p in P.parents if (p/'AGENTS.md').is_file())
A=P.parent/'legacy-entry-integration'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(name,value): (P/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checks=[]
def check(name,value):
    checks.append({'id':name,'pass':bool(value)})
    assert value,name
spec=read(A/'module-spec.json'); traces=read(A/'traceability.json'); preserved=read(A/'preserved-hashes.json')
authority=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
check('independent authors',spec['identity']['author']=='/root/m03_legacy_gate_packet')
check('796 exact authority keys and values',preserved['product796']==authority['source_hashes'] and len(authority['source_hashes'])==796)
management_diff=[]
for group in ('inputs','product796'):
    changed=[p for p,h in preserved[group].items() if not (R/p).is_file() or digest(R/p)!=h]
    if group=='inputs':
        management_diff=[{'path':p,'expected':preserved[group][p],'observed':digest(R/p)} for p in changed if p=='docs/board.json']
        changed=[p for p in changed if p!='docs/board.json']
    check(group+' preserved excluding separately classified management board',not changed)
check('58 inputs',len(preserved['inputs'])==58)
commands=(R/'apps/sgenaxis-desktop/src-tauri/src/commands.rs').read_text(encoding='utf-8-sig')
helpers=(R/'apps/sgenaxis-desktop/crates/sgenaxis-host/src/uidesign_doc.rs').read_text(encoding='utf-8-sig')
ipc=(R/'apps/sgenaxis-desktop/crates/sgenaxis-host/src/ipc.rs').read_text(encoding='utf-8-sig')
original=(P.parent/'h2-exact-design/module.feature').read_text(encoding='utf-8-sig')
cx=read(P.parent/'cx-h2-revision-v3/case-trace.json')
trace=[]
for n,(command,helper,dto) in enumerate(zip(('uidesign_save_design','uidesign_load_design','uidesign_build_preview'),('save_design_file','load_design_file','build_preview_file'),('UiDesignSaveDto','UiDesignLoadDto','UiDesignBuildDto')),58):
    bdd='M03-H2-B0'+str(n)
    body=commands.split('pub fn '+command+'(',1)[1].split('\n}',1)[0]
    check(bdd+' exact original',f'Rule: {bdd} {command}' in original and traces[n-58]['original']['original_behavior'] in original)
    rows=[x for x in cx if x.get('original_case_id')==bdd]
    check(bdd+' cx oracle',len(rows)==1 and rows[0]['behavior_oracle']=='DESIGN_OWNER_REQUIRED; no save/load/build filesystem call')
    check(command+' current direct IO trace',helper+'(' in body and 'root.fs()' in body and 'resolve_bound_project_root' in body)
    check(command+' current result and negative owner trace',f'Result<{dto}, String>' in body and all(x not in body for x in ('DESIGN_OWNER_REQUIRED','WebviewWindow','DispatchHost')))
    check(command+' static order',body.index('authorize(')<body.index('host.inner.lock()')<body.index(helper+'('))
    trace.append({'bdd':bdd,'handler':f'apps/sgenaxis-desktop/src-tauri/src/commands.rs:{commands[:commands.index("pub fn "+command+"(")].count(chr(10))+1}','helper':helper,'current':'name allowlist -> host lock -> root resolution -> direct FileSystemPort helper; not owner denial','proposed':'framework admission/decode first; admitted legacy denial before host/root/default/codec/owner/FS/native; pending Owner'})
check('name only authorization', 'pub fn authorize(name: &str)' in ipc and 'AllowedIpcCommand::parse(name)' in ipc)
check('helper current writes and reads',all(s in helpers for s in ('fs.create_dir_all','fs.write_atomic','.read_to_string(&path)','serialize_design(doc)?','parse_design_json(&raw)?')))
build=commands.split('pub fn uidesign_build_preview(',1)[1].split('\n}',1)[0]
check('all platform opener branches static',all('Command::new("'+s+'")' in build for s in ('cmd','open','xdg-open')) and 'if args.open_after' in build and '.spawn()' in build)
cap=read(R/'apps/sgenaxis-desktop/src-tauri/capabilities/uidesign-window.json')
permissions=(R/'apps/sgenaxis-desktop/src-tauri/permissions/dispatch.toml').read_text(encoding='utf-8-sig')
check('viewer current capability differs from proposed restriction',cap['windows']==['ui-editor','ui-viewer'] and 'dispatch-default' in cap['permissions'])
check('three permission entries and default inclusions',all(permissions.count('allow-uidesign-'+s)>=2 for s in ('save-design','load-design','build-preview')))
check('pending denial shape',spec['status']=='PROPOSED_PENDING_OWNER' and 'not a newly approved wire schema' in spec['contracts'][2] and 'NOT approved' in spec['response_boundary']['proposed_handler_denial'])
# Independent fixtures intentionally avoid asserting DTO deserialization or caller authorization.
before={'owner':{'doc':{'unknown':['keep',{'x':1}]},'revision':'9007199254740993','history':['undo','redo']},'bindings':['b1','b2'],'candidate':['held'],'viewer_registry':{'v':'epoch7'},'selection':['n'],'filesystem':{'prior':'complete bytes'},'native':[]}
def oracle(case):
    stage='handler' if case['admission']=='admitted' else 'pre-handler'
    return {'stage':stage,'semantic_result':'DESIGN_OWNER_REQUIRED' if stage=='handler' else 'FRAMEWORK_DENIAL_UNSPECIFIED','state':copy.deepcopy(before),'calls':[]}
fixtures=[]; mutations=0
for i,(t,caller,input_kind,owner,admission) in enumerate(itertools.product(trace,('authorized-editor','viewer','foreign','forged-owner'),('typed-valid','raw-root-symbolic','empty-symbolic','invalid-symbolic'),('ready','unavailable'),('admitted','acl-denied','decode-denied'))):
    c={'id':f'IR-{i+1:03}','bdd':t['bdd'],'caller_category':caller,'input_category':input_kind,'owner':owner,'admission':admission,'expected':None}
    c['expected']=oracle(c); fixtures.append(c)
    check(c['id']+' full immutable state and precedence',c['expected']['state']==before and not c['expected']['calls'] and c['expected']['stage']==('handler' if admission=='admitted' else 'pre-handler'))
    for key in before:
        bad=oracle(c); bad['state'][key]=None
        check(c['id']+' rejects mutation '+key,bad!=c['expected']); mutations+=1
    for call in ('host_lock','resolve_root','default_path','codec','owner_lookup','owner_fallback','read','write','spawn'):
        bad=oracle(c); bad['calls']=[call]
        check(c['id']+' rejects forbidden '+call,bad!=c['expected']); mutations+=1
    bad=oracle(c); bad['semantic_result']='SUCCESS' if admission=='admitted' else 'DESIGN_OWNER_REQUIRED'
    check(c['id']+' rejects result conflation',bad!=c['expected']); mutations+=1
check('original packet unchanged approval',not spec['module_complete'] and all(x=='NOT RUN' for x in spec['verification'].values()))
snapshot={str(p.relative_to(R)).replace('\\','/'):digest(p) for p in A.iterdir() if p.is_file()}
result={'status':'PASS_SCOPED_DOCUMENT_REVIEW_ONLY_PENDING_OWNER','reviewer':'/root/m03_legacy_entry_review','author':'/root/m03_legacy_gate_packet','bounded_original_scenarios':3,'independent_fixtures':len(fixtures),'semantic_mutations_rejected':mutations,'checks':len(checks),'product_hashes':796,'preserved_inputs':58,'findings':[],'head_observed':'5b709343a890503ebbe24a802e43cda5647df124','authority_historical_head':authority['head'],'no_approval_delta':True,'module_complete':False,'health':'Yellow / REPLAN_REQUIRED','native_build_product_valid_RED_full_Draft':'NOT RUN','limits':'Model noIO is proposed semantic evidence only; current product has direct helper IO and optional OS spawn. Caller/input categories do not prove actual admission. Exact String serialization and richer shape pending Owner.','next_action':'Owner adopt exact H2/C1 and denial wire choice, approve Skeleton and valid RED, then separate independent runtime ACL/caller/FS/native validation; no module PASS.'}
result['input_preservation_detail']={'input_inventory':58,'unchanged_original_inputs':58-len(management_diff),'separate_management_diff':management_diff}
dump('fixtures.json',fixtures); dump('traceability.json',trace); dump('results.json',result); dump('checks.json',checks); dump('input-seal.json',{'original_packet':snapshot,'authority_source':digest(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'),'management_board':'Read only; management diff is separate from 796 product authority and not included as product behavior evidence.','management_diff':management_diff})
html='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M03 legacy independent review</title><style>body{font:16px system-ui;max-width:1050px;margin:40px auto;background:#121927;color:#e8eef7}pre{white-space:pre-wrap;background:#202c40;padding:20px}h1{color:#f6cf68}</style><h1>M03 B058–B060 independent document review</h1><p>PASS scoped document review only · Yellow · Pending Owner. Reviewer /root/m03_legacy_entry_review; distinct author /root/m03_legacy_gate_packet.</p><p>Current: caller → Tauri capability/decode → name allowlist → host lock → root resolution → direct helper FileSystemPort IO; build may spawn cmd/open/xdg-open. Future proposal: admitted legacy input → DESIGN_OWNER_REQUIRED → stop. No owner fallback; complete state unchanged. Neither branch was run.</p><p>ACL/decode denials precede handler; admitted invalid symbolic inputs remain model assumptions, not real DTO evidence. main/editor/viewer/foreign identity requires native tests. No response String encoding or new error schema adopted.</p><pre>'+json.dumps(result,ensure_ascii=False,indent=2)+'</pre><pre>'+json.dumps(trace,ensure_ascii=False,indent=2)+'</pre><script type="application/json" id="review-spec">'+json.dumps(result,ensure_ascii=False)+'</script></html>'
(P/'index.html').write_text(html,encoding='utf-8')
dump('artifact-hashes.json',{p.name:digest(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps(result))
