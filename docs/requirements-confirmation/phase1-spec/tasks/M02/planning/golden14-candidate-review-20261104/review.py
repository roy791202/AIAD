import pathlib,json,hashlib,shutil,subprocess,tomllib,ast,html,datetime
P=pathlib.Path(__file__).resolve().parent
C=P.parent/'golden14-candidate-20261104'
R=next(x for x in P.parents if (x/'AGENTS.md').exists())
h=lambda b:hashlib.sha256(b).hexdigest()
seal=json.loads((C/'seal.json').read_text(encoding='utf8'))['files']
checks=[]
def check(n,b):checks.append({'name':n,'pass':bool(b)})
check('candidate_seal_before',all(h((C/k).read_bytes())==v for k,v in seal.items()))
d=json.loads((C/'candidate.json').read_text(encoding='utf8'));inp=json.loads((C/'input.json').read_text(encoding='utf8'))
check('fourteen_paths',len(d['rows'])==14 and len({x['path'] for x in d['rows']})==14)
check('null_choices',d['selected'] is None and all(x['selected'] is None for x in d['decisions']))
for x in d['rows']:
 for typ in ['template','expected']:check(typ+':'+x['path'],h((C/x[typ]['path']).read_bytes())==x[typ]['sha256'])
# Independent read-only renderer consumes actual submitted templates and fixture.
vals={'PACKAGE':inp['package_name'],'TITLE':inp['project_name'],'IDENTIFIER':inp['identifier'],'DEFINITION':inp['definition_revision'],'DESIGN':inp['design_revision']}
def render(b):
 s=b.decode('utf8')
 for k,v in vals.items():s=s.replace('@@'+k+'@@',v)
 if '@@' in s:raise ValueError('unresolved')
 return s.encode('utf8')
for x in d['rows']:
 b=(C/x['template']['path']).read_bytes();check('independent_render:'+x['path'],render(b)==render(b)==(C/x['expected']['path']).read_bytes())
W=P/'isolated';shutil.copytree(C/'expected',W,dirs_exist_ok=True)
r=subprocess.run(['cargo','+stable','metadata','--offline','--locked','--no-deps','--format-version','1','--manifest-path',str(W/'program/src-tauri/Cargo.toml')],capture_output=True,timeout=55)
meta=json.loads(r.stdout) if r.returncode==0 else {}
check('independent_locked_metadata',r.returncode==0 and meta.get('workspace_root')==str(W/'program/src-tauri'))
lock=tomllib.loads((W/'program/src-tauri/Cargo.lock').read_text(encoding='utf8'));check('own_root_full_lock',len(lock['package'])==406 and any(x['name']=='golden14-candidate' for x in lock['package']))
# Extract only author render and fixtures: no execution of mutating build.py.
tree=ast.parse((C/'build.py').read_text(encoding='utf8'));fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='render');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'author_render','exec'),ns)
probes=[]
for kind in ['template','input','output','lock']:
 probes.append({'kind':kind,'observation':'No read-only candidate validation command exists; build.py regenerates and overwrites submitted artifacts before hash checks. Hash inequality check is not rejection.','result':'GAP_CONFIRMED_BY_SOURCE','source':'build.py resources/fixture definitions, write loops, tamper checks'})
try:ns['render']('@@UNKNOWN@@',vals);check('unknown_token_rejected',False)
except ValueError:check('unknown_token_rejected',True)
auth=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf8'))['source_hashes'];check('authority796',len(auth)==796 and all(h((R/k).read_bytes())==v for k,v in auth.items()))
check('candidate_seal_after',all(h((C/k).read_bytes())==v for k,v in seal.items()))
f=[{'id':'G14-R1','severity':'P2','scope':'candidate tooling only','finding':'No executable fail-closed renderer/checker consumes submitted input/templates and rejects drift. Author build.py regenerates all outputs from embedded constants, overwriting tampering; tamper assertions only prove hashes differ.','required_correction':'Add separate render/validate command consuming bound input.json and actual templates; validate source bindings and all expected outputs/lock hashes without rewriting candidate. Add rejection tests for input/template/output/lock edits and missing lock. Keep all proposals unadopted.'}]
result={'status':'CHANGES_REQUESTED_BOUNDED_CANDIDATE_TOOLING','reviewer':'/root/golden14_independent_review','author':d['author'],'checks':checks,'findings':f,'probes':probes,'metadata':{'exit':r.returncode,'stdout':r.stdout.decode('utf8','replace'),'stderr':r.stderr.decode('utf8','replace')},'limits':['Content14 and standalone lock resolution verified','No product build/native/adoption','No historical PASS rerun']}
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><h1>Golden14 independent review</h1><p>CHANGES_REQUESTED_BOUNDED_CANDIDATE_TOOLING</p><p>14 actual candidate template/output bytes and own 406-package lock verified. Independent locked offline metadata PASS. Proposed choices remain null; product build/native NOT RUN.</p><h2>G14-R1</h2><p>'+html.escape(f[0]['finding'])+'</p><p>'+html.escape(f[0]['required_correction'])+'</p><a href="results.json">Exact checks and evidence</a>',encoding='utf8')
(P/'seal.json').write_text(json.dumps({'sealed_at':datetime.datetime.now().astimezone().isoformat(),'files':{str(x.relative_to(P)).replace(chr(92),'/'):h(x.read_bytes()) for x in P.rglob('*') if x.is_file() and x.name!='seal.json'}},indent=2),encoding='utf8')
print(json.dumps({'status':result['status'],'checks':len(checks),'failed':[x for x in checks if not x['pass']]}))
