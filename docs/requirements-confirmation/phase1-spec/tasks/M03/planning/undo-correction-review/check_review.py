import ast, copy, hashlib, json, pathlib, re, uuid, subprocess
P=pathlib.Path(__file__).parent
C=P.parent/'undo-response-correction'
def read(n): return json.loads((C/n).read_text(encoding='utf8'))
ns={'copy':copy,'hashlib':hashlib,'json':json,'pathlib':pathlib,'re':re,'uuid':uuid,'P':C}
def load_defs(path,names):
 tree=ast.parse(path.read_text(encoding='utf8'))
 nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),ns)
load_defs(P.parent/'undo-response-integration/check_documents.py',{'Draft202012Validator'})
load_defs(C/'check_documents.py',{'read','strict','validate','proofcheck','lifecycle','evidence_decision'})
f=read('fixtures.json'); out=[]
def probe(id,fn,expected=True,kind='independent property'):
 try: fn(); accepted=True
 except (AssertionError,KeyError,TypeError,ValueError): accepted=False
 assert accepted==expected,(id,accepted,expected)
 out.append({'id':id,'kind':kind,'observed':accepted,'expected':expected,'status':'PASS'})
# Author fixture suite replayed through extracted definitions only; no author main/import writes.
for row in f['wire']: probe('AUTHOR-'+row['id'],lambda row=row:ns['validate'](row['request'],row['response']),row['valid'],'author regression, not new coverage')
base=f['presented_proof']; trust=f['trusted_fixture_records']
probe('INDEP-BASE',lambda:ns['proofcheck'](base,trust))
# Independent property permutations preserve fixed issuer lookup. All must fail closed.
for role in base['roots']['before']:
 q=copy.deepcopy(base); q['roots']['before'][role]['material_versions']=[]
 if q==base: q['roots']['before'][role]['provider']='wrong-role-provider'
 probe('INDEP-ROOT-'+role,lambda q=q:ns['proofcheck'](q,trust),False)
for part in ['mutation','pin','roots']:
 q=copy.deepcopy(base); q[part]['context']['request_id']='unrelated-request'
 probe('INDEP-CONTEXT-'+part,lambda q=q:ns['proofcheck'](q,trust),False)
for io in base['io']:
 q=copy.deepcopy(base); q['io'][io]='CALLED'
 probe('INDEP-NOIO-'+io,lambda q=q:ns['proofcheck'](q,trust),False)
# Cross-product: all seven exact diagnostic bodies, both initial/replayed envelopes,
# and independent native authority revocation/late owner states.
errors=read('work-error-map.json'); req=f['wire'][0]['request']
for i,row in enumerate(errors):
 for replay in [False,True]:
  response=copy.deepcopy(row['wire']); response['replayed']=replay
  probe('INDEP-DIAGNOSTIC-%s-%s'%(i,replay),lambda response=response:ns['validate'](req,response))
  wrong=copy.deepcopy(response); wrong['error']['details']['fields']['injected']='x'
  probe('INDEP-DIAGNOSTIC-ALTERED-%s-%s'%(i,replay),lambda wrong=wrong:ns['validate'](req,wrong),False)
 case=copy.deepcopy(f['lifecycle'][0]); case['state']['retained_terminal']=copy.deepcopy(row['wire']); case['state']['M04_commit_established']=True
 for gate in ['authorized','closed','sender','generation']:
  x=copy.deepcopy(case)
  if gate=='authorized': x['state']['authorized']=False
  elif gate=='closed': x['state']['closed']=True
  elif gate=='sender': x['event']['sender']='replacement'
  else: x['event']['generation']='999'
  actual=ns['lifecycle'](x)
  assert not actual['deliver'] and not actual['render'] and 'terminal' not in actual
  out.append({'id':'INDEP-ERROR-REVOKE-%s-%s'%(i,gate),'status':'PASS'})
for live in ['8','9','11','18446744073709551615']:
 case=copy.deepcopy(f['lifecycle'][0]); case['state'].update(authorized=True,closed=False,inflight=False,M04_commit_established=True,live_revision=live,retained_terminal={'outcome':'Applied','revision':'8','replayed':False},pin_state='Unknown')
 case['event']['sender']=case['state']['owner_sender']; case['event']['generation']=case['state']['owner_generation']; case['event']['capture']=copy.deepcopy(case['state']['immutable_capture'])
 a=ns['lifecycle'](case)
 assert a['deliver'] and a['live_revision']==live and a['undo_calls']==0 and a['render']==(live=='8') and not a['release'] and a['pin_state']=='Unknown'
 case['state']['M04_commit_established']=False
 b=ns['lifecycle'](case); assert b['outcome']=='Indeterminate' and not b['deliver']
 out.append({'id':'INDEP-REPLAY-LIVE-'+live,'status':'PASS'})
# Measure semantic coverage directly from unchanged trusted input, not invented trusted seals.
# The following are static missing edges, NOT accepted forged-proof counterexamples.
proof=next(n for n in ast.parse((C/'check_documents.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='proofcheck')
assertions=[ast.unparse(n.test) for n in ast.walk(proof) if isinstance(n,ast.Assert)]
(P/'proof-assertions.json').write_text(json.dumps(assertions,indent=2)+'\n')
source=read('source-current.json'); authority=json.loads(pathlib.Path(source['authority_manifest']).read_text())['source_hashes']
drift=[str(n) for n,h in authority.items() if not pathlib.Path(n).exists() or hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()!=h]
assert len(authority)==796 and not drift
for n,h in source['sources'].items(): assert hashlib.sha256(pathlib.Path(n).read_bytes()).hexdigest()==h,n
hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [C,P.parent/'undo-response-integration',P.parent/'undo-response-review'] for p in folder.iterdir() if p.is_file()}
(P/'reviewed-hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
(P/'new-probes.json').write_text(json.dumps(out,indent=2)+'\n')
v={'status':'PASS_INDEPENDENT_DOCUMENT_PROBES_ONLY','reviewer':'/root/m03_undo_correction_review','head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'authority_entries':796,'authority_drift':drift,'author_cases_reused':sum(r.get('kind','').startswith('author') for r in out),'independent_probes':sum(not r.get('kind','').startswith('author') for r in out),'author_main_executed':False,'product_tests':'NOT RUN','native_runtime':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','BUILD':'NOT RUN','fullDraft':'MISSING','Owner_adoption':'NOT ADOPTED','module_complete':False}
(P/'verification.json').write_text(json.dumps(v,indent=2)+'\n')
print(json.dumps(v))
# Reproduce remaining author correction vectors without executing author main.
extra=[]
for row in read('mutation-matrix.json'):
 q=copy.deepcopy(base)
 for mutation in row['changes']:
  obj=q; parts=mutation['path'].split('.')
  for part in parts[:-1]: obj=obj[int(part)] if isinstance(obj,list) else obj[part]
  obj[int(parts[-1]) if isinstance(obj,list) else parts[-1]]=mutation['value']
 try: ns['proofcheck'](q,trust); accepted=True
 except (AssertionError,KeyError,TypeError,ValueError): accepted=False
 assert not accepted,row['id']
 assert ns['evidence_decision'](q,trust,trust['M04_record'])==row['expected_confirmed_commit_effect']
 extra.append({'id':row['id'],'status':'PASS','kind':'author correction regression'})
for row in f['lifecycle']:
 assert ns['lifecycle'](row)==row['expected'],row['id']
 extra.append({'id':row['id'],'status':'PASS','kind':'author correction regression'})
for value,expected in f['u64']:
 try: ns['strict']({'revision':value}); actual=True
 except AssertionError: actual=False
 assert actual==expected
 extra.append({'id':'AUTHOR-U64-'+repr(value),'status':'PASS','kind':'author correction regression'})
(P/'author-regression.json').write_text(json.dumps(extra,indent=2)+'\n')
v['additional_author_vectors']=len(extra)
(P/'verification.json').write_text(json.dumps(v,indent=2)+'\n')
print('Additional author vectors:',len(extra))
for row in f['wire']:
 if 'schema_valid' in row:
  try: ns['Draft202012Validator'](read('response.schema.json')).validate(row['response']); actual=True
  except AssertionError: actual=False
  assert actual==row['schema_valid']
  extra.append({'id':row['id']+'-schema','status':'PASS'})
ns['proofcheck'](base,trust)
extra.append({'id':'CORR-PROOF-BASE','status':'PASS'})
for lookup in [None,trust['M05_pin_record']]:
 assert ns['evidence_decision'](base,trust,lookup)=={'outcome':'Indeterminate','actual_revision':None,'rollback':False,'release':False}
 extra.append({'id':'CORR-UNVERIFIED-M04-'+str(lookup is None),'status':'PASS'})
v['author_correction_vectors']=33+len(extra)
assert v['author_correction_vectors']==255
(P/'author-regression.json').write_text(json.dumps(extra,indent=2)+'\n')
(P/'verification.json').write_text(json.dumps(v,indent=2)+'\n')
