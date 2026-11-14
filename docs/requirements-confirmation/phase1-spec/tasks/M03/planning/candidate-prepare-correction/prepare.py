"""Additive planning correction. No product behavior or Owner decision is changed."""
import ast, copy, hashlib, html, json, pathlib, re, shutil, subprocess, sys
sys.dont_write_bytecode = True
P = pathlib.Path(__file__).resolve().parent
OLD = P.parent / 'candidate-prepare-integration'
ROOT = next(x for x in P.parents if (x / '.git').exists())
def read(p): return json.loads(p.read_text(encoding='utf8'))
def write(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def walk(x,path=''):
 if isinstance(x,dict):
  yield path,x
  for k,v in x.items(): yield from walk(v,path+'/'+k.replace('~','~0').replace('/','~1'))
 elif isinstance(x,list):
  for i,v in enumerate(x): yield from walk(v,path+'/'+str(i))
def stripped(x):
 if isinstance(x,dict): return {k:stripped(v) for k,v in x.items() if k!='pattern'}
 if isinstance(x,list): return [stripped(v) for v in x]
 return x
def kind(pattern):
 if '[0-9a-f]{8}' in pattern:return 'UUID-v4-lowercase'
 if '{64}' in pattern:return 'Digest-lowercase'
 return 'U64Decimal'
def sample(s):
 if 'pattern' in s:return {'UUID-v4-lowercase':'abcdef01-abcd-4abc-8abc-abcdef012345','Digest-lowercase':'abcdef01'*8,'U64Decimal':'7'}[kind(s['pattern'])]
 if 'const' in s:return copy.deepcopy(s['const'])
 if 'enum' in s:return s['enum'][0]
 t=s.get('type');t=t[0] if isinstance(t,list) else t
 return {'string':'x','boolean':False,'null':None,'array':[]}.get(t)
def resolve(root,ref):
 x=root
 for k in ref[2:].split('/'):x=x[k]
 return x
def witness(root,s,forced):
 if '$ref'in s:return witness(root,resolve(root,s['$ref']),forced)
 if 'oneOf'in s:return witness(root,s['oneOf'][forced.pop(0) if forced else 0],forced)
 if s.get('type')=='object':return {k:witness(root,v,forced) for k,v in s.get('properties',{}).items() if k in s.get('required',[])}
 return sample(s)
def routes(root,s,sp='',ip=(),branches=(),refs=()):
 if '$ref'in s:
  if s['$ref'] in refs:raise AssertionError('cycle')
  yield from routes(root,resolve(root,s['$ref']),s['$ref'][1:],ip,branches,refs+(s['$ref'],));return
 if 'pattern'in s:yield dict(schema_pointer=sp+'/pattern',instance_path=list(ip),branches=list(branches),ref_chain=list(refs),kind=kind(s['pattern']))
 for i,b in enumerate(s.get('oneOf',[])):yield from routes(root,b,sp+'/oneOf/'+str(i),ip,branches+(i,),refs)
 for k,b in s.get('properties',{}).items():yield from routes(root,b,sp+'/properties/'+k,ip+(k,),branches,refs)
 if 'items'in s:yield from routes(root,s['items'],sp+'/items',ip+('*',),branches,refs)
def setpath(x,path,value):
 for k in path[:-1]:x=x[k]
 x[path[-1]]=value
def main():
 preserved=['fixtures.json','new-policy-choices.json','trusted-fixture-authority.json','schema_subset.py','check_documents.py','module.feature','step-definition-stubs.json','steps.py','pending-automation.json']
 for n in preserved:shutil.copyfile(OLD/n,P/n)
 shutil.copyfile(OLD/'module-spec.json',P/'module-spec.json')
 before={};audit=[];roots={};trace=[];cases=[]
 for n in ['request.schema.json','response.schema.json']:
  old=read(OLD/n);new=copy.deepcopy(old);before[n]=sha(OLD/n)
  for pointer,node in walk(new):
   if 'pattern' not in node:continue
   raw=node['pattern'];assert raw.startswith('^')
   # Only existing anchored lexical grammars are corrected. No free-text rule added.
   if raw.endswith('$'):body=raw[:-1]
   else:
    assert raw.endswith(r'(?![\s\S])'),repr(raw)
    body=raw[:-len(r'(?![\s\S])')]
   node['pattern']=body+r'(?![\s\S])'
   probe_value=sample(node)
   audit.append(dict(schema=n,pointer=pointer+'/pattern',kind=kind(raw),before=raw,after=node['pattern'],changed=raw!=node['pattern'],before_tail_codepoints=list(map(ord,raw[-12:])),before_accepts_LF=re.search(raw,probe_value+'\n') is not None,after_accepts_LF=re.search(node['pattern'],probe_value+'\n') is not None,case_policy='unchanged original lowercase where applicable',body_unchanged=True))
  assert stripped(old)==stripped(new)
  write(n,new);roots[n]=new
  for route in routes(new,new):
   route['schema']=n;route['id']=str(len(trace));trace.append(route)
   base=witness(new,new,route['branches'].copy());path=route['instance_path'];assert '*'not in path
   v=base
   for k in path:v=v[k]
   values=[('canonical',v,True)]
   values += [(label,pre+v+post,False) for label,pre,post in [('prefix','x',''),('suffix','','x'),('LF','','\n'),('CR','','\r'),('CRLF','','\r\n'),('NUL','','\x00'),('TAB','','\t'),('NEL','','\x85'),('LS','','\u2028'),('PS','','\u2029'),('leadingLF','\n','')]]
   values += [('empty','',False),('nonstring',7,False)]
   if route['kind']=='U64Decimal':values += [(str(z),z,ok) for z,ok in [('0',True),('1',True),('9007199254740993',True),('18446744073709551615',True),('18446744073709551616',False),('01',False),('-1',False),('1.0',False),('1e0',False)]]
   else:values += [('uppercase',v.upper(),False),('wrong-version',v.replace('-4','-5',1),False)]
   for label,value,expected in values:
    b=copy.deepcopy(base);setpath(b,path,value)
    cases.append(dict(id=route['id']+':'+label,route=route['id'],schema=n,instance=b,expected_accept=expected))
 for entry in audit:
  entry['root_routes']=[r['id'] for r in trace if r['schema']==entry['schema'] and r['schema_pointer']==entry['pointer']]
  entry['reachability']='ROOT_REACHABLE' if entry['root_routes'] else 'UNREACHABLE_SHARED_DEF; definition regex probes only, no invented root field'
 write('lexical-audit.json',audit);write('root-occurrence-trace.json',trace);write('lexical-fixtures.json',cases)
 sys.path.insert(0,str(P));from schema_subset import Draft202012Validator
 results=[]
 for c in cases:
  try:Draft202012Validator(roots[c['schema']]).validate(c['instance']);actual=True
  except AssertionError:actual=False
  assert actual==c['expected_accept'],c['id']
  results.append(dict(id=c['id'],expected=c['expected_accept'],actual=actual))
 # Probe every physical pattern, even unreachable shared definitions, in both engines.
 pattern_cases=[]
 for a in audit:
  s=next(v for p,v in walk(roots[a['schema']]) if p+'/pattern'==a['pointer']);v=sample(s)
  vals=[('canonical',v,True),('empty','',False),('prefix','x'+v,False),('suffix',v+'x',False)]
  vals += [(repr(z),v+z,False) for z in ['\n','\r','\r\n','\0','\t','\x85','\u2028','\u2029']]
  if a['kind']!='U64Decimal':vals += [('uppercase',v.upper(),False),('short',v[:-1],False),('long',v+'0',False)]
  if a['kind']=='U64Decimal':vals += [(z,z,ok) for z,ok in [('0',True),('18446744073709551615',True),('18446744073709551616',False),('01',False),('-1',False)]]
  for label,value,expected in vals:
   actual=re.search(s['pattern'],value)is not None;assert actual==expected
   pattern_cases.append(dict(schema=a['schema'],pointer=a['pointer'],pattern=s['pattern'],label=label,value=value,expected=expected))
 write('pattern-fixtures.json',pattern_cases)
 write('before-after.json',{'changes':audit,'non_pattern_schema_canonical_equivalent':True,'checker_byte_identical':sha(P/'schema_subset.py')==sha(OLD/'schema_subset.py'),'checker_AST_identical':ast.dump(ast.parse((P/'schema_subset.py').read_text()))==ast.dump(ast.parse((OLD/'schema_subset.py').read_text())),'semantic_model_AST_identical':ast.dump(ast.parse((P/'check_documents.py').read_text()))==ast.dump(ast.parse((OLD/'check_documents.py').read_text())),'preserved':{n:{'before':sha(OLD/n),'after':sha(P/n),'byte_identical':sha(OLD/n)==sha(P/n)} for n in preserved}})
 string_inventory=[]
 for n,root in roots.items():
  for ptr,s in walk(root):
   if s.get('type')=='string' or isinstance(s.get('type'),list) and 'string'in s['type']:
    string_inventory.append({'schema':n,'pointer':ptr,'constraints':{k:s[k] for k in ['type','pattern','minLength','maxLength','enum','const','format'] if k in s},'policy':'existing pattern corrected or preserved' if 'pattern'in s else 'No new lexical grammar imposed; existing minLength/free text semantics preserved'})
 write('all-string-constraints.json',string_inventory)
 node=json.loads(subprocess.check_output(['node',str(P/'probe.cjs')],cwd=ROOT,text=True));assert node['mismatches']==[]
 authority=read(P.parent.parent.parent/'M01/planning/s2-green/source-current.json');hashes=authority['source_hashes']
 current={p:sha(ROOT/p) if (ROOT/p).is_file() else None for p in hashes};drift=[p for p in hashes if hashes[p]!=current[p]]
 write('source-current.json',{'branch':subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),'HEAD':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'historical_authority_HEAD':authority['head'],'authority_path':str((P.parent.parent.parent/'M01/planning/s2-green/source-current.json').relative_to(ROOT)).replace('\\','/'),'authority_count':len(hashes),'current_hashes':current,'drift':drift,'M01_S2':'Green authority preserved, not new M03 runtime evidence'})
 verification={'status':'AUTHOR_LEXICAL_DOCUMENT_CHECKED_PENDING_INDEPENDENT_REVIEW','author':'/root/m03_prepare_lexical_correction','independent_acceptance':'PENDING','pattern_occurrences':len(audit),'root_routes':len(trace),'new_python_root_probes':len(results),'new_python_definition_probes':len(pattern_cases),'node':node,'results':results,'original_96':'NOT RERUN','review_88':'NOT RERUN','fullDraft':'NOT RUN','product':'NOT RUN','native':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','build':'NOT RUN','Owner':'NOT ADOPTED','module_complete':False}
 write('verification.json',verification)
 spec=read(P/'module-spec.json');spec['correction']={'scope':'Anchored lexical end only, all physical patterns audited; all original lowercase/body/ranges unchanged','findings':['CP-R1','CP-R2'],'independent_acceptance':'PENDING','command':'python -B '+str((P/'check_correction.py').relative_to(ROOT)),'generator':'python -B '+str((P/'prepare.py').relative_to(ROOT)),'root_trace':'root-occurrence-trace.json','new_tests':'lexical-fixtures.json','Owner':'NOT ADOPTED','OPEN_OWNER':'Original CP-P4 unchanged','acceptance_criteria':['Both UUID actual-LF complete requests rejected by schema directly','Every physical pattern classified changed/already strict and root reachable/unreachable','Every reachable occurrence has complete-root positive, boundary, malformed and control-character probes in Python and Node','Non-pattern schema canonical equality; original model/checker AST equality; fixture and policy byte identity','796 source hashes compared against M01 s2-green authority with current hashes and drift listed','No product/old package/board/current-state writes; separate reviewer required']};write('module-spec.json',spec)
 (P/'lexical.feature').write_text('''Feature: Exact candidate preparation lexical identity
  Background:
    Given the original candidate preparation policies remain proposed
  Rule: Existing anchored lexical grammars reject additional characters
    Scenario: CP-R1 binding reference with an actual line feed
      Given a complete otherwise valid preparation request
      When its binding reference has a trailing line feed
      Then the document schema rejects the request
    Scenario: CP-R2 request identity with an actual line feed
      Given a complete otherwise valid preparation request
      When its request identity has a trailing line feed
      Then the document schema rejects the request
    Scenario: Audit every reachable lexical occurrence
      Given complete request and response branches and the original lexical ranges and case rules
      When canonical boundary values and malformed lexical values are checked
      Then Python and JavaScript agree with the preserved contracts
''',encoding='utf8')
 (P/'lexical_steps.py').write_text('''"""Pending native BDD automation; these are not product tests."""
def given_complete_native_request(context):
    raise NotImplementedError("Owner envelope and native Skeleton pending")
def when_trailing_line_feed(context):
    raise NotImplementedError("Native command not authorized")
def then_rejected_without_state_change(context):
    raise NotImplementedError("Independent runtime verification pending")
''',encoding='utf8')
 write('lesson.json',{'root_cause':'Prior command review identified two UUID fields; complete audit also checks Digest definitions. U64 already has correct strict end and is byte-preserved; initial escaped-display suspicion was withdrawn after decoded codepoint and executable probes.','prevention':'For each command audit every pattern through nested/inline defs; preserve body/case/range; trace full-root reachability; run positive/negative boundary/control probes in Python and ECMA; separately label unreachable definitions. Never diagnose escaping from rendered repr alone.','scope':'Planning lesson only; no global lessons or production edits.'})
 sections=['<h1>M03 Candidate Prepare — lexical correction candidate</h1><p>黃 PD-P1-M03-PREP-01 · PLANNING · 未獨立驗收 · Owner NOT ADOPTED</p><p>Only anchored lexical end changes. Existing prepare slot/replay/ReadResolved/C1 premises remain unchanged. NoChange is not introduced: prepare is candidate-only, not an edit mutation. OPEN_OWNER CP-P4 remains open.</p><pre>UI → Tauri admission → H2 prepare → C1 / ESS / M04 read / M05 prepare\nM04 owns content/history; H2 owns ephemeral slot; no content mutation or formal IO/ACK.</pre><pre>Input port → H2 facade → output ports ← providers\nPrepare: validate → temporary parse/project → read evidence → late authority check → slot publish</pre>']
 for n in ['module-spec.json','lexical.feature','lexical_steps.py','lexical-audit.json','all-string-constraints.json','root-occurrence-trace.json','lexical-fixtures.json','pattern-fixtures.json','before-after.json','verification.json','lesson.json']:
  sections.append('<details><summary>'+html.escape(n)+'</summary><pre>'+html.escape((P/n).read_text(encoding='utf8'))+'</pre></details>')
 sections.append('<h2>Preserved semantic package and checker</h2><p>Byte identity and canonical non-pattern schema equality are in before-after.json. Full Draft validation, native/product/RED/build/install and Owner adoption remain NOT RUN. Old 96/88 are NOT RERUN, not new progress.</p>')
 for n in ['schema_subset.py','check_documents.py','check_correction.py','probe.cjs','fixtures.json','new-policy-choices.json','trusted-fixture-authority.json','source-current.json']:
  sections.append('<details><summary>'+n+'</summary><pre>'+html.escape((P/n).read_text(encoding='utf8'))+'</pre></details>')
 sections.append('<script type="application/json" id="module-spec">'+json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')+'</script>')
 (P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M03 Prepare Lexical Correction</title><style>body{max-width:1100px;margin:2rem auto;font:16px system-ui;background:#101823;color:#e4ebf3}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#192638;padding:1rem}summary{padding:1rem;color:#ffd886}details{border:1px solid #314457;margin:1rem 0}</style>'+''.join(sections),encoding='utf8')
 write('artifact-hashes.json',{'path_base':'this directory','files':{p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name!='artifact-hashes.json'}})
 print(json.dumps({k:verification[k] for k in ['status','pattern_occurrences','root_routes','new_python_root_probes','new_python_definition_probes']}))
if __name__=='__main__': main()
