import json,pathlib,hashlib,copy,subprocess,html
ROOT=pathlib.Path(__file__).resolve().parents[7]
OUT=pathlib.Path(__file__).resolve().parent
BASE='docs/requirements-confirmation/phase1-spec/tasks/'
REG=BASE+'M01/planning/exact-disposition-register-20261103/register.json'
SOURCES={}
def digest(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def read(p):
 SOURCES[p]=digest(p);return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def esc(k):return str(k).replace('~','~0').replace('/','~1')
def leaves(v,p=''):
 if isinstance(v,dict):
  for k,x in v.items():yield from leaves(x,p+'/'+esc(k))
 elif isinstance(v,list):
  for i,x in enumerate(v):yield from leaves(x,p+'/'+str(i))
 else:yield p,v
 # Empty arrays/objects have semantic value and need explicit projection.
 if isinstance(v,(dict,list)) and not v:yield p,v
def ref(p,ptr,value):return {'path':p,'sha256':SOURCES[p],'pointer':ptr,'value':value}
def project(p,v,pointer='',status='PENDING_NOT_ADOPTED'):
 return [{'source':ref(p,q,x),'status':status,'selected':None} for q,x in leaves(v,pointer)]
def write(p,v): (OUT/p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
d=read(REG); r=copy.deepcopy(d)
r.update(author='/root/exact_disposition_correction',owner_instruction_at='2026-11-03T15:27:09.094Z',layer='DOCUMENT_CORRECTION_ONLY',independent_review='NOT RUN',document_RED='N/A: documentary projection checker; not product behavior TDD',head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
# Retain routing verbatim. Fine-grained dispositions are additional projections, never approvals.
for card in r['cards'][1:8]:
 module=card['id'].split('-')[2]; pending=card['pending_candidate']['path']; obj=read(pending)
 adopted=[]
 for ar in card.get('existing_adoption_records',[]):
  p=ar['path']; a=read(p); adopted+=project(p,a,status='ADOPTION_LEDGER_FACT')
  # Locate the exact decision definitions tied to the adoption revision, preserving old labels as source values.
  candidates=[]
  if module=='M01':candidates=[BASE+'M01/planning/s2-exact-design/module-spec.json']
  if module=='M02':candidates=[BASE+'M02/planning/exact-design/module-spec.json']
  if 'design_path' in a:candidates=[a['design_path'].replace('\\','/')]
  ids=set(a.get('decisions',a.get('adopted',[])))
  for q in candidates:
   spec=read(q); expected=a.get('design_sha256') or a.get('approved_artifact_hashes',{}).get(q.replace('/','\\'))
   revision_match=(expected==SOURCES[q]) if expected else None
   for ptr,val in leaves(spec):
    if isinstance(val,str) and val in ids:
     parts=ptr.rsplit('/',1); parent=spec
     for key in parts[0].split('/')[1:]:parent=parent[int(key)] if isinstance(parent,list) else parent[key.replace('~1','/').replace('~0','~')]
     rows=project(q,parent,parts[0],status='ADOPTED_DECISION_DEFINITION' if revision_match is not False else 'OPEN_REVISION_MISMATCH')
     for row in rows:row['revision_match']=revision_match;row['adoption_ledger']=ar;row['scope_limit']='Only the recorded adopted slice; source historical pending labels are superseded only by the ledger. No new product authority.'
     adopted+=rows
 current=card['adopted_current_status']['path']; curr=read(current)
 facts=[]
 for key in ['stage','scope','architecture_status','Skeleton_RED','product_implementation','remaining','module_complete','preflight_acceptance_preserved','f1_f3','sliceDoneAt']:
  if key in curr:facts+=project(current,curr[key],'/'+key,status='CURRENT_RECORDED_FACT_NOT_NEW_ADOPTION')
 # S1 acceptance is evidence, not fabricated Owner adoption.
 if module=='M04':
  q=BASE+'M04/planning/exact-design/independent-review/primary-adjudication.json';accepted=read(q);facts+=project(q,accepted,status='HISTORICAL_S1_ACCEPTANCE_ONLY')
 card['exact_adopted']={'status':'SOURCE_LEDGER_PROJECTED' if adopted else 'OPEN_NO_EXPLICIT_ADOPTION_LEDGER_IN_REGISTER','fields':adopted,'current_recorded_facts':facts,'unknown':'OPEN: do not infer adoption from current navigation, document PASS, or pending labels' if not adopted else None}
 keys=[k for k in obj if any(w in k for w in ['choice','decision','option'])]
 # M03 latest candidate intentionally has no choice array: project its precise retained contract, not generic whole-document adoption.
 if not keys:keys=[k for k in ['contracts','contract','boundary','mapping','guards','before','after','scope','next_action'] if k in obj]
 fields=[]
 for key in keys:fields+=project(pending,obj[key],'/'+key)
 card['exact_pending']={'source_revision_sha256':SOURCES[pending],'fields':fields,'effect':'Disposition only these source-bound proposed values. Return names exact pointer and replacement value; defer names exact pointer and reason. No existing accepted S1/S2 readoption.','selected':None,'unresolved_external_values':'OPEN; source proposals remain proposals and provider authenticity/native outcomes are not supplied by this projection.'}
 card.pop('decision',None)
# Actual new template bytes cannot be invented from an inventory.
inventory=r['next_packet']['input']['path']; inv=read(inventory)
r['next_packet']={'id':'M02-GOLDEN14-PROVIDER-INPUT-NEXT','primary_module':'M02','state':'PROPOSAL_NOT_DISPATCHABLE','selected':None,'input':d['next_packet']['input'],'provider':d['next_packet']['provider'],'no_new_owner_adoption_needed_for_candidate_preparation':True,'missing_conditions':[
 {'condition':'Exact template contents for each of fourteen resource paths','provider':'M02 template-content Owner / template author','source':ref(inventory,'/rows/0/submitted_resource/bytes',None),'missing':'Inventory identifies paths but does not prescribe actual bytes. Resource bytes and expected rendered output remain null; writing them would author a new template.'},
 {'condition':'Exact definition/design revisions and deterministic rendering expectations per resource','provider':'M01 definition and M03/M04 design/projector providers + M02 template-content Owner','missing':'Concrete admitted fixture inputs, full expected rendered bytes and output SHA256 are not present in inventory; no guessed golden output permitted.'},
 {'condition':'Standalone manifest + independent lock + resolver/toolchain provenance','provider':'Build/toolchain provider and independent resolver-evidence verifier','missing':'Exact dependency constraints/template Cargo.toml and Cargo.lock bytes, resolver result, toolchain/target/registry configuration and successful isolated resolver evidence are unavailable. Workspace-root lock is not replacement evidence.'},
 {'condition':'Exact writable candidate-only M02 subdirectory and approved deliverable/check envelope','provider':'Coordinator after template-content prerequisites are identified','missing':'No M02 files authorized by this M01 correction. Do not create a nominal packet lacking defined expected bytes. A future task must name every file, fixtures, runnable checker, GWT, acceptance and protected paths.'}],
 'blocked_portion':'Actual golden14 byte authorship and native/generated build evidence; no fabricated golden, native output, schema, or executable packet.',
 'available_now':'This M01 correction projects exact source facts and missing providers. Existing inventory is historical input, never a new deliverable or rerun-as-progress.',
 'document_RED':'N/A: no product/Skeleton implementation; new documentary negative checks only.','product_tests':'NOT RUN','native':'NOT RUN','cannot_authorize':d['next_packet']['cannot_authorize']}
# bind the actual missing source leafs without copying the inventory payload
r['next_packet']['missing_value_evidence']=[ref(inventory,p,v) for p,v in leaves(inv) if v is None]
auth=read(r['authority']['path']); hashes=auth['source_hashes']; drift=[p for p,h in hashes.items() if not (ROOT/p).is_file() or digest(p)!=h]
r['authority_count']=len(hashes);r['authority_drift']=drift
# An owner request is session authority only, not a fabricated disk adoption record.
r['correction_scope']={'allowed':[str(OUT.relative_to(ROOT)).replace('\\','/')+'/**'],'protected':['original candidate/review','board','product','tests','spec','hooks','roles'],'status':'CANDIDATE_PENDING_INDEPENDENT_REVIEW','owner_adoptions_made':0}
write('register.json',r)
write('closure-diff.json',{'F01':{'status':'CORRECTED_CANDIDATE_PENDING_INDEPENDENT_REVIEW','before':'whole-document generic disposition','after':'source-bound exact adopted ledger/decision definitions plus pending leaf pointer/value projections; missing adoption remains OPEN; M03 MM01..MM08 retained unchanged'},'F02':{'status':'CLARIFIED_NOT_DISPATCHABLE','before':d['next_packet']['state'],'after':'PROPOSAL_NOT_DISPATCHABLE; unknown template bytes/expected outputs and external resolver prerequisites named without inventing content'},'preserved':{'cards':31,'counts':r['counts'],'selected':'all null','IO_owner_adoption_required':False,'product_hashes':len(hashes),'historical_head':r['historical_head'],'live_head':r['head']}})
# Source bindings are hashes only, not large cached copies.
read(BASE+'M01/planning/exact-disposition-review-20261103/findings.json')
read('docs/board.json')
for dirname in ['exact-disposition-register-20261103','exact-disposition-review-20261103']:
 for protected in (ROOT/(BASE+'M01/planning/'+dirname)).rglob('*'):
  if protected.is_file():
   key=protected.relative_to(ROOT).as_posix();SOURCES[key]=digest(key)
write('source-hashes.json',{'sources':SOURCES,'board_semantics':'current management snapshot only; originals retain old board hashes','authority_drift':drift})
body=['<!doctype html><html lang="en"><meta charset="utf-8"><title>Exact disposition correction</title><style>body{font:15px system-ui;max-width:1250px;margin:30px auto;color:#203040}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f3f5f7;padding:14px}details{margin:15px 0}h2{border-bottom:1px solid #ccc} .warn{color:#8a4c00}</style><h1>Exact disposition correction · M01 planning</h1><p class="warn">Candidate only. No Owner adoption, product authority, native proof, module PASS or independent acceptance. Owner instruction 2026-11-03T15:27:09.094Z.</p><p>31 card action/provider routing retained. Existing S1/S2 slices are not reopened. Unknowns remain OPEN; every selection stays null. 796 protected source hashes checked against s2-green/source-current.json; live and historical HEAD remain distinct.</p>']
for c in r['cards']:
 body+=['<h2>'+html.escape(c['id'])+'</h2><p>'+html.escape(c['action'])+'</p><p>Provider: '+html.escape(c['provider'])+'</p>']
 for key in ['exact_adopted','exact_pending','media_decisions']:
  if key in c:body+=['<details open><summary>'+key+'</summary><pre>'+html.escape(json.dumps(c[key],ensure_ascii=False,indent=2))+'</pre></details>']
body+=['<p><a href="checks.json">Author checker results</a> · <a href="closure-diff.json">Closure diff</a> · <a href="source-hashes.json">Source hashes</a> · <a href="register.json">Structured register</a></p><h2>F02: actual golden14 prerequisites</h2><pre>'+html.escape(json.dumps(r['next_packet'],ensure_ascii=False,indent=2))+'</pre><p>Checks: python docs/requirements-confirmation/phase1-spec/tasks/M01/planning/exact-disposition-correction-20261103/check.py</p><p>Author documentary checks only. Product RED/GREEN/build/native/independent review NOT RUN. No commit.</p></html>']
(OUT/'index.html').write_text(''.join(body),encoding='utf8')
print(json.dumps({'cards':len(r['cards']),'pending_fields':sum(len(c.get('exact_pending',{}).get('fields',[])) for c in r['cards']),'authority':len(hashes),'drift':drift,'sources':len(SOURCES)}))
