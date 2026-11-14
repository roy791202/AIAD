"""Author-only checks, no product imports or product writes. python -B checker.py."""
import hashlib,json,pathlib,subprocess
import re
from document_model import close
from schema_eval import audit,valid,sample
P=pathlib.Path(__file__).resolve().parent;ROOT=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
req=read(P/'request.schema.json');resp=read(P/'response.schema.json')
audit(req);audit(resp)
audit(read(P/'provider-observation.schema.json'))
error={'$defs':resp['$defs'],'$ref':'#/$defs/Error'}
cases=read(P/'fixtures.json');checks=0
for c in cases:
 actual=close(c,lambda x:valid(req,x),lambda x:valid(error,x))
 assert actual==c['expected'],(c['id'],c['name'],actual,c['expected']);checks+=1
 assert valid(resp,actual['response']),(c['id'],actual['response']);checks+=1
 protected=set(c['before'])-{'preview_active','mock','capabilities','slots'}
 assert all(actual['state'][k]==c['before'][k] for k in protected);checks+=1
 assert not any(any(word in call for word in ('detach','document.close','ACK','pin','formal','S1','material')) for call in actual['calls']);checks+=1
# Enumerate COMPLETE response roots, not just Close values.
roots=[sample(resp,resp['oneOf'][0])]
for branch in resp['$defs']['Error']['oneOf']:
 roots.append({'ok':False,'error':sample(resp,branch),'replayed':False})
root_probes=[]
for i,r in enumerate(roots):
 assert valid(resp,r),(i,r);root_probes.append({'label':str(i)+' valid','value':r,'valid':True})
 for key in r:
  bad=dict(r);del bad[key];assert not valid(resp,bad);root_probes.append({'label':str(i)+' missing '+key,'value':bad,'valid':False})
 bad=dict(r,extra=True);assert not valid(resp,bad);root_probes.append({'label':str(i)+' extra','value':bad,'valid':False})
 for key in ('ok','replayed'):
  bad=dict(r);bad[key]=int(r[key]);assert not valid(resp,bad);root_probes.append({'label':str(i)+' typed '+key,'value':bad,'valid':False})
for key in ('closed','content_changed'):
 for v in (None,0,1,'true',[],{}):
  r={'ok':True,'value':{'closed':True,'content_changed':False},'replayed':False};r['value'][key]=v
  assert not valid(resp,r);root_probes.append({'label':'typed Close '+key,'value':r,'valid':False})
assert not valid(req,{'preview_session':'abcdef01-abcd-4abc-8abc-abcdef012345\n'})
original=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/integration-contract-revision-v3'
for n in ('request','response'):
 old=read(original/('h2-design_viewer_close-'+n+'.schema.json'));new=read(P/(n+'.schema.json'))
 for d in read(P/'schema-before-after.json'):
  if d['schema']!=n:continue
  target=old
  for k in d['pointer'].split('/')[1:-1]:target=target[int(k)] if type(target)is list else target[k]
  assert target['pattern']==d['before'];target['pattern']=d['after']
 assert old==new,'unlisted schema change'
for name,digest in read(P/'preserved-inputs.json').items():assert sha(ROOT/name)==digest,name
authority=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
hashes=authority['source_hashes'];assert len(hashes)==796
for name,digest in hashes.items():assert sha(ROOT/name)==digest,name
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert head=='5b709343a890503ebbe24a802e43cda5647df124'
embedded=re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(P/'index.html').read_text(encoding='utf-8'),re.S)
assert embedded and json.loads(embedded.group(1))==read(P/'module-spec.json')
assert set(c['bdd'] for c in cases)=={'CLOSE-'+str(i).zfill(3) for i in range(1,9)}
trace=[{'case':c['id'],'bdd':c['bdd'],'contract':'CLOSE-1..5','test':'checker.py::'+c['id'],'expected':c['expected'],'status':'AUTHOR_DOCUMENT_PASS'} for c in cases]
(P/'traceability.json').write_text(json.dumps(trace,indent=2)+'\n',encoding='utf-8')
(P/'root-probes.json').write_text(json.dumps(root_probes,indent=2)+'\n',encoding='utf-8')
result={'status':'AUTHOR_DOCUMENT_CHECKS_PASS_PENDING_OWNER','fixtures':len(cases),'behavior_assertions':checks,'complete_root_probes':len(root_probes),'preserved_inputs':len(read(P/'preserved-inputs.json')),'product_authority_matched':len(hashes),'schema_delta_rows':len(read(P/'schema-before-after.json')),'head':head,'historical_head':authority['head'],'independent_review':'NOT RUN','native':'NOT RUN','build':'NOT RUN','product_tests':'NOT RUN','valid_RED':'NOT RUN','full_Draft_validator':'NOT RUN','module_complete':False,'parent_light':'Yellow'}
(P/'results.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
