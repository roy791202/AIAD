import json,pathlib,copy,hashlib,re
# Local interpreter for the schema vocabulary used here; not a general JSON Schema engine.
class Draft202012Validator:
 def __init__(self,s):self.s=s
 @staticmethod
 def check_schema(s):assert s.get('$schema')=='https://json-schema.org/draft/2020-12/schema'
 def validate(self,x):
  def v(s,x):
   if '$ref' in s:
    t=self.s
    for k in s['$ref'][2:].split('/'):t=t[k]
    return v(t,x)
   if 'oneOf' in s:return sum(v(z,x) for z in s['oneOf'])==1
   if 'const' in s and (type(x)!=type(s['const']) or x!=s['const']):return False
   if 'enum' in s and x not in s['enum']:return False
   kinds={'object':type(x)is dict,'array':type(x)is list,'string':type(x)is str,'boolean':type(x)is bool,'null':x is None}
   t=s.get('type')
   if t and not any(kinds.get(k,False) for k in (t if isinstance(t,list) else [t])):return False
   if type(x)is str:
    if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**9):return False
    if 'pattern'in s and re.search(s['pattern'],x)is None:return False
   if type(x)is dict:
    if any(k not in x for k in s.get('required',[])):return False
    if s.get('additionalProperties')is False and any(k not in s.get('properties',{}) for k in x):return False
    if any(k in x and not v(z,x[k]) for k,z in s.get('properties',{}).items()):return False
   if type(x)is list and 'items'in s and any(not v(s['items'],z) for z in x):return False
   return True
  assert v(self.s,x),'schema rejection'

P=pathlib.Path(__file__).parent

def read(n):return json.loads((P/n).read_text(encoding='utf8'))
def strict(value):
 if isinstance(value,dict):
  for k,v in value.items():
   if k in {'expected_revision','expected_generation','before_revision','after_revision','history_depth','revision','owner_generation'}:
    assert type(v) is str and re.fullmatch(r'0|[1-9][0-9]*',v) and int(v)<=18446744073709551615,'U64'
   strict(v)
 elif isinstance(value,list):
  for v in value:strict(v)
def validate(req,res):
 Draft202012Validator(read('request.schema.json')).validate(req);Draft202012Validator(read('response.schema.json')).validate(res);strict(req);strict(res)
 if not res['ok'] and res['error']['code']=='DomainRejected':
  assert any(res==e['wire'] for e in read('work-error-map.json')),'exact WORK diagnostic mapping'
 if res['ok']:
  v=res['value'];assert v['replayed']==res['replayed'],'replay contradiction'
  if v['outcome']!='NoChange':
   assert v['projection']['revision']==v['after_revision'],'projection revision'
   assert int(v['after_revision'])==int(v['before_revision'])+1,'Undo revision increment'
   assert v['before_revision']==req['expected_revision'],'capture revision'

def proofcheck(p):
 c=p['capture'];m=p['mutation_receipt'];e=p['pin_evidence'];versions=p['root_version_set']
 assert m['before_revision']==c['expected_revision']
 assert int(m['after_revision'])==int(m['before_revision'])+1
 assert int(m['history_after'])==int(m['history_before'])-1
 assert int(m['redo_after'])==int(m['redo_before'])+1
 assert m['pin_id']==e['pin_id']
 assert e['actual_state']=='Held' and e['evidence_receipt_id']
 assert versions['scope']==c['document_uuid']+'/'+c['session_uuid']
 assert versions['provider_id']=='provider-a' and versions['epoch']=='6' and versions['completeness']=='Complete'
 assert set(versions['before'])==set(versions['after'])=={'LiveDocuments','UndoHistory','RedoHistory','RecoverySnapshots','InFlightTransactions'}
 for kind in versions['before']:
  assert int(versions['after'][kind])==int(versions['before'][kind])+(kind in {'LiveDocuments','UndoHistory','RedoHistory'})
 assert p['io']['FileCommit']=='NOT CALLED'
results=[]
for case in read('fixtures.json'):
 try:validate(case['request'],case['response']);accepted=True
 except Exception:accepted=False
 assert accepted==case['valid'],case['id'];results.append({'case':case['id'],'PASS':True,'kind':'document-positive' if accepted else 'document-negative'})
p=read('proof-model.json');proofcheck(p)
for path,bad in [('mutation_receipt.after_revision','9'),('mutation_receipt.history_after','2'),('mutation_receipt.redo_after','0'),('pin_evidence.pin_id','forged'),('pin_evidence.actual_state','Unknown'),('root_version_set.epoch','7'),('root_version_set.completeness','Unknown'),('root_version_set.after.RedoHistory','6'),('capture.expected_revision','6')]:
 q=copy.deepcopy(p);x=q
 for k in path.split('.')[:-1]:x=x[k]
 x[path.split('.')[-1]]=bad
 try:proofcheck(q);rejected=False
 except AssertionError:rejected=True
 assert rejected,path;results.append({'case':'proof-'+path,'PASS':True,'kind':'document-negative'})
# Canonical range limits, not float based.
for value,expected in [('0',True),('18446744073709551615',True),('18446744073709551616',False),('99999999999999999999',False),('-1',False),('1e3',False),('01',False),('',False),(True,False)]:
 try:strict({'revision':value});ok=True
 except AssertionError:ok=False
 assert ok==expected;results.append({'case':'u64-'+str(value),'PASS':True,'kind':'document-range'})
for name in ['request.schema.json','response.schema.json']:
 s=read(name);Draft202012Validator.check_schema(s)
 def refs(v):
  if isinstance(v,dict):
   if '$ref' in v:
    assert v['$ref'].startswith('#/');target=s
    for part in v['$ref'][2:].split('/'):target=target[part]
   for z in v.values():refs(z)
  elif isinstance(v,list):
   for z in v:refs(z)
 refs(s)
for vector in read('replay-lifecycle-vectors.json'):
 assert vector['expected'] and vector['capture_revision']=='7'
 results.append({'case':vector['id'],'PASS':True,'kind':'document-lifecycle-oracle-presence-only'})
source=read('source-current.json');assert source['authority_count']==796 and not source['authority_drift']
R=pathlib.Path.cwd()
for file,h in source['sources'].items():assert hashlib.sha256((R/file).read_bytes()).hexdigest()==h,file
text=(P/'index.html').read_text(encoding='utf8');embedded=re.search(r'<script id="module-spec" type="application/json">(.*?)</script>',text,re.S);assert json.loads(embedded[1])==read('module-spec.json')
result={'status':'PASS_DOCUMENT_SELF_CHECK_ONLY','author':'m03_next_command_packet','independent_review':'NOT RUN','product_tests':'NOT RUN','product_RED':'NOT RUN','product_GREEN':'NOT RUN','fullDraft':'MISSING','cases':len(results),'results':results,'authority_entries':796,'authority_drift':0,'save181_rerun':False}
(P/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k!='results'}))
