"""Document-only verifier. No product import or runtime/native invocation. python -B checker.py."""
import copy,hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
R=next(p for p in P.parents if (p/'AGENTS.md').is_file())
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def model(case):
    # Caller/ACL/decode are supplied observations in a document fixture, never inferred real authorization.
    admitted=case['acl_admitted'] and case['decoded']
    return {'stage':'handler' if admitted else 'pre-handler','outcome':'DESIGN_OWNER_REQUIRED' if admitted else 'FRAMEWORK_DENIAL_UNSPECIFIED','after':copy.deepcopy(case['before']),'calls':[]}
def valid(case,observed):
    required=model(case)
    return observed==required
checks=[]
def check(name,ok):
    checks.append({'id':name,'pass':bool(ok)})
    if not ok: raise AssertionError(name)
fixtures=read(P/'fixtures.json'); spec=read(P/'module-spec.json'); traces=read(P/'traceability.json'); preserved=read(P/'preserved-hashes.json')
check('18 bounded document fixtures',len(fixtures)==18)
for c in fixtures: check(c['id'],valid(c,model(c)) and c['expected']==model(c))
base=fixtures[0]; mutations=[]
for field,value in [('outcome','SUCCESS'),('stage','owner-port')]:
    o=model(base); o[field]=value; mutations.append(o)
o=model(base); o['calls']=['read_to_string']; mutations.append(o)
o=model(base); o['after']['owner']['revision']='8'; mutations.append(o)
o=model(base); o['after']['filesystem']={}; mutations.append(o)
o=model(base); o['calls']=['native_open']; mutations.append(o)
for i,o in enumerate(mutations): check('negative semantic tamper '+str(i+1),not valid(base,o))
check('3 exact original IDs',[t['original']['original']['bdd'] for t in traces]==spec['bdd']['original_ids'])
original=(P.parent/'h2-exact-design/module.feature').read_text(encoding='utf-8-sig')
check('original 62 BDD retained',sum(1 for line in original.splitlines() if line.strip().startswith('Rule: M03-H2-B'))==62)
for t in traces:
    o=t['original']; check(o['original']['bdd']+' exact behavior',o['original_behavior'] in original)
check('796 authority entries',len(preserved['product796'])==796)
for group in ['inputs','product796']:
    changed=[p for p,h in preserved[group].items() if not (R/p).is_file() or sha(R/p)!=h]
    check(group+' hashes unchanged',not changed)
commands=(R/'apps/sgenaxis-desktop/src-tauri/src/commands.rs').read_text(encoding='utf-8-sig')
ipc=(R/'apps/sgenaxis-desktop/crates/sgenaxis-host/src/ipc.rs').read_text(encoding='utf-8-sig')
for t in traces:
    start=commands.index('pub fn '+t['command']+'('); end=commands.index('\n}',start)+2; body=commands[start:end]
    check(t['command']+' actual helper',t['current_static']['helper']+'(' in body)
    check(t['command']+' no DispatchHost/current caller window', 'DispatchHost' not in body and 'WebviewWindow' not in body)
check('authorize is name allowlist','pub fn authorize(name: &str)' in ipc and 'AllowedIpcCommand::parse(name)' in ipc)
check('source pending denial absent from current handler range','DESIGN_OWNER_REQUIRED' not in commands[commands.index('pub fn uidesign_save_design('):commands.index('pub fn uidesign_build_preview(')])
html=(P/'index.html').read_text(encoding='utf-8'); embedded=json.loads(html.split('<script type="application/json" id="module-spec">')[1].split('</script>')[0])
check('HTML embedded ModuleSpec identical',embedded==spec)
check('no inherited approval',not spec['module_complete'] and all(x=='NOT RUN' for x in spec['verification'].values()))
result={'status':'PASS_DOCUMENT_MODEL_ONLY','author':'/root/m03_legacy_gate_packet','independent_review':'NOT RUN','original_scenarios':3,'original_total':62,'document_fixture_count':18,'negative_tamper_count':6,'product_hashes':796,'preserved_input_count':len(preserved['inputs']),'checks':checks,'remaining_gates':spec['remaining_gates'],'product_native_build_RED_full_Draft':'NOT RUN','approval':'PROPOSED_PENDING_OWNER'}
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
manifest={p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'}
(P/'artifact-hashes.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='checks'})); print('checks='+str(len(checks))+'; payload='+str(len(manifest)))
