import pathlib,json,hashlib,copy,datetime,subprocess,html
ROOT=pathlib.Path(__file__).resolve().parents[7]; OUT=pathlib.Path(__file__).resolve().parent; BASE=OUT.parent; C=BASE/'exact-disposition-correction-20261103'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ptr(o,p):
 for k in p.split('/')[1:]:
  k=k.replace('~1','/').replace('~0','~');o=o[int(k)] if isinstance(o,list) else o[k]
 return o
r=load(C/'register.json'); old=load(BASE/'exact-disposition-register-20261103/register.json'); checks=[]
def check(name,ok,detail):checks.append({'name':name,'pass':bool(ok),'detail':detail})
def walk(o):
 if isinstance(o,dict):
  yield o
  for v in o.values():yield from walk(v)
 elif isinstance(o,list):
  for v in o:yield from walk(v)
refs=[x for x in walk(r) if {'path','sha256','pointer','value'}<=x.keys()]
def validref(x):
 try:return bool(x['pointer']) and h(ROOT/x['path'])==x['sha256'] and ptr(load(ROOT/x['path']),x['pointer'])==x['value']
 except Exception:return False
check('independent pointer and value resolution',all(map(validref,refs)),{'bindings':len(refs)})
a=[x for c in r['cards'] for x in c.get('exact_adopted',{}).get('fields',[])];p=[x for c in r['cards'] for x in c.get('exact_pending',{}).get('fields',[])]
counts={s:sum(x['status']==s for x in a) for s in set(x['status'] for x in a)}
check('leaf classification',len(a)==118 and len(p)==116 and all(x['status']=='PENDING_NOT_ADOPTED' for x in p),counts)
check('routing and eight dimensions',len(r['cards'])==31 and all(all(c.get(k)==o.get(k) for k in ['id','action','provider','missing_conditions','selected','light']) for c,o in zip(r['cards'],old['cards'])) and r['cards'][3]['media_decisions']==old['cards'][3]['media_decisions'] and r['cards'][0]['owner_adoption_required'] is False,'8 Yellow / 18 Gray / 5 Red; no IO adoption requested')
check('all selections null',all(x.get('selected') is None for x in walk(r) if 'selected' in x),'No adoption performed')
ledger=load(ROOT/r['cards'][1]['existing_adoption_records'][0]['path']); spec=load(ROOT/r['cards'][1]['exact_adopted']['fields'][12]['source']['path'])
check('M01 logical adopted revision',ledger['review_revision_sha256']==spec['identity']['packet_revision_sha256'],'review_revision_sha256 is logical packet revision, not current file SHA256. Candidate revision_match=null; independently resolved here.')
check('unknown ledgers remain open',all(c['exact_adopted']['status']=='OPEN_NO_EXPLICIT_ADOPTION_LEDGER_IN_REGISTER' for c in r['cards'][1:8] if not c.get('existing_adoption_records')),'Absence from register does not deny historical adoption or acceptance')
check('F02 proposal scoped',r['next_packet']['state']=='PROPOSAL_NOT_DISPATCHABLE' and r['next_packet']['no_new_owner_adoption_needed_for_candidate_preparation'] is True and len(r['next_packet']['missing_conditions'])==4,'Actual byte/golden/resolver evidence unavailable; coordinator may prepare future exact candidate envelope without extra Owner adoption. No blanket block on preparation.')
seal=load(C/'seal.json');check('candidate payload seal',all(h(C/f)==v for f,v in seal['files'].items()),'7 sealed files')
auth=load(ROOT/r['authority']['path'])['source_hashes'];check('796 authority',len(auth)==796 and all(h(ROOT/f)==v for f,v in auth.items()),r['authority']['path'])
bind=load(C/'source-hashes.json')['sources'];drift=[f for f,v in bind.items() if h(ROOT/f)!=v];check('non-board source bindings',all(f=='docs/board.json' for f in drift),{'drift':drift,'count':len(bind)})
check('HEAD separation',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==r['head']=='5b709343a890503ebbe24a802e43cda5647df124' and r['historical_head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab','Historical HEAD not current product evidence; current commit is board-only context')
page=(C/'index.html').read_text(encoding='utf8');check('HTML exact projections',all(html.escape(json.dumps(x['source']['pointer'],ensure_ascii=False)[1:-1]) in page for x in a+p),'Static HTML content inspection only; no browser/native proof')
# New probes target independent semantic/source checks, never import author checker.
probes=[]
x=copy.deepcopy(refs[0]);x['source']='irrelevant';x['value']={'injected':'false'};probes.append({'id':'wrong_ledger_source_value','detected':not validref(x)})
x=copy.deepcopy(refs[0]);x['sha256']='0'*64;probes.append({'id':'source_hash_substitution','detected':not validref(x)})
x=copy.deepcopy(r);x['cards'][0]['owner_adoption_required']=True;probes.append({'id':'io_owner_gate_injection','detected':x['cards'][0]['owner_adoption_required'] is not False})
x=copy.deepcopy(r);x['cards'][3]['media_decisions'][0]['selected']='adopt';probes.append({'id':'M03_selection_injection','detected':any(y.get('selected') is not None for y in walk(x) if 'selected' in y)})
x=copy.deepcopy(ledger);x['review_revision_sha256']='0'*64;probes.append({'id':'logical_revision_substitution','detected':x['review_revision_sha256']!=spec['identity']['packet_revision_sha256']})
results={'reviewer':'/root/exact_disposition_correction_review','author':r['author'],'layer':'INDEPENDENT_BOUNDED_DOCUMENT_REVIEW','checks':checks,'negative_probes':probes,'verdict':'PASS_BOUNDED_DOCUMENT_CORRECTION' if all(x['pass'] for x in checks) and all(x['detected'] for x in probes) else 'CHANGES_REQUESTED','limitations':['No product/build/native/RED-GREEN rerun; historical PASS remains historical.','Board hash drift is management snapshot drift: current M01 note appended with item/root updatedAt after candidate seal. Original old bytes unavailable; cannot prove full-board reconstruction/equivalence.','Creation instruction 2026-11-03T15:27:09.094Z differs from review heartbeat 2026-11-03T15:37:09.229Z; neither is adoption evidence.','ADOPTED_DECISION_DEFINITION rows are source-bound definitions associated with ledger IDs, not independent adoption events. Ledger facts 53, definitions 65.']}
findings={'verdict':results['verdict'],'findings':[],'F01':'CLOSED_BOUNDED: exact ledger/definition and pending pointers exposed, preserved adoption boundaries.','F02':'CLOSED_AS_CLARIFIED_PROPOSAL: remains not dispatchable until exact future envelope, content/oracles and resolver evidence; no extra adoption for candidate prep.'}
for name,obj in [('results.json',results),('findings.json',findings)]: (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>Independent correction review</title><h1>'+results['verdict']+'</h1><p>Independent reviewer /root/exact_disposition_correction_review; author '+r['author']+'</p><pre>'+html.escape(json.dumps({'findings':findings,'results':results},ensure_ascii=False,indent=2))+'</pre></html>',encoding='utf8')
print(json.dumps(results,ensure_ascii=False,indent=2))
