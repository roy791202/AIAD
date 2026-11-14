import copy,hashlib,json,pathlib,sys
OUT=pathlib.Path(__file__).resolve().parent
ROOT=OUT.parents[6]
def load(p):return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def ptr(obj,p):
 for k in p.split('/')[1:]:
  k=k.replace('~1','/').replace('~0','~');obj=obj[int(k)] if isinstance(obj,list) else obj[k]
 return obj
def leaves(v,p=''):
 if isinstance(v,dict):
  for k,x in v.items():yield from leaves(x,p+'/'+str(k).replace('~','~0').replace('/','~1'))
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from leaves(x,p+'/'+str(i))
 else:yield p,v
 if isinstance(v,(dict,list)) and not v:yield p,v
def validate(r):
 errors=[]
 def require(ok,msg):
  if not ok:errors.append(msg)
 old=load('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/exact-disposition-register-20261103/register.json')
 require(len(r['cards'])==31,'31 card coverage')
 bindings=json.loads((OUT/'source-hashes.json').read_text(encoding='utf8'))['sources']
 for p,h in bindings.items():require(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'protected/source drift '+p)
 authority=load(r['authority']['path'])['source_hashes']
 for p,h in authority.items():require(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,'product hash drift '+p)
 require(r['counts']==old['counts'],'light counts preserved')
 for a,b in zip(r['cards'],old['cards']):
  for k in ['id','light','action','provider','missing_conditions','selected']:
   require(a.get(k)==b.get(k),'routing preserved '+b['id']+' '+k)
 require(r['cards'][0]['owner_adoption_required'] is False,'IO no new Owner adoption')
 require(r['cards'][3]['media_decisions']==old['cards'][3]['media_decisions'],'M03 eight dimensions preserved')
 for c in r['cards'][1:8]:
  source=load(c['pending_candidate']['path'])
  keys=[k for k in source if any(s in k for s in ['choice','decision','option'])]
  if not keys:keys=[k for k in ['contracts','contract','boundary','mapping','guards','before','after','scope','next_action'] if k in source]
  expected={(c['pending_candidate']['path'],p):v for k in keys for p,v in leaves(source[k],'/'+k)}
  actual={(x['source']['path'],x['source']['pointer']):x['source']['value'] for x in c['exact_pending']['fields']}
  require(expected==actual,'exact pending field coverage '+c['id'])
  for x in c['exact_pending']['fields']:require(x['status']=='PENDING_NOT_ADOPTED','wrong adopted status '+c['id'])
  require(c['exact_pending']['selected'] is None,'pending selection stays null')
  if not c.get('existing_adoption_records'):
   require(c['exact_adopted']['status']=='OPEN_NO_EXPLICIT_ADOPTION_LEDGER_IN_REGISTER' and c['exact_adopted']['fields']==[],'unknown adoption must remain OPEN')
  for x in c['exact_adopted']['fields']:
   require(x['status'] in ['ADOPTION_LEDGER_FACT','ADOPTED_DECISION_DEFINITION','OPEN_REVISION_MISMATCH'],'invalid adopted projection status')
 def walk(o):
  if isinstance(o,dict):
   if 'selected' in o:require(o['selected'] is None,'all selected null')
   if set(['path','sha256','pointer','value'])<=set(o):
    try:
     require(bool(o['pointer']),'nonempty exact field pointer')
     require(hashlib.sha256((ROOT/o['path']).read_bytes()).hexdigest()==o['sha256'],'source hash '+o['path'])
     require(ptr(load(o['path']),o['pointer'])==o['value'],'source value '+o['pointer'])
    except Exception as e:errors.append('unresolved pointer '+str(e))
   for v in o.values():walk(v)
  elif isinstance(o,list):
   for v in o:walk(v)
 walk(r)
 require(r['next_packet']['state']=='PROPOSAL_NOT_DISPATCHABLE','false dispatchability')
 require(len(r['next_packet']['missing_conditions'])==4,'explicit missing prerequisites')
 require(bool(r['next_packet']['missing_value_evidence']),'actual null evidence')
 require(r['authority_count']==796 and r['authority_drift']==[],'source authority unchanged')
 return errors
r=json.loads((OUT/'register.json').read_text(encoding='utf8'));base=validate(r)
results={'layer':'AUTHOR_DOCUMENT_CHECKS_ONLY','valid_RED':'N/A','baseline_errors':base,'negative_probes':[]}
for name,mutate in [
 ('missing_exact_pointer',lambda x:x['cards'][1]['exact_pending']['fields'].pop()),
 ('wrong_adopted_status',lambda x:x['cards'][1]['exact_pending']['fields'][0].update(status='ADOPTED_DECISION_DEFINITION')),
 ('false_dispatchability',lambda x:x['next_packet'].update(state='READY_FOR_DISPATCH'))]:
 x=copy.deepcopy(r);mutate(x);errors=validate(x);results['negative_probes'].append({'name':name,'detected':bool(errors),'errors':errors})
results['PASS']=not base and all(x['detected'] for x in results['negative_probes'])
print(json.dumps(results,indent=2))
if '--record' in sys.argv:(OUT/'checks.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
sys.exit(0 if results['PASS'] else 1)
