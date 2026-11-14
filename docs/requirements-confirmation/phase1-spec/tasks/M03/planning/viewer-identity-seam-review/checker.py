"""Independent bounded document probes. python -B checker.py; no product execution."""
import copy, hashlib, html, importlib.util, json, pathlib, subprocess, sys
sys.dont_write_bytecode=True
P=pathlib.Path(__file__).resolve().parent
S=P.parent/'viewer-identity-seam-proposal'
ROOT=P.parents[6]
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,x): (P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
 spec=importlib.util.spec_from_file_location('independent_candidate',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load(S/'document_model.py')
checks=[];probes=[];trace=[]
def ck(i,b,detail=None): checks.append({'id':i,'pass':bool(b),'detail':detail})
f=read(S/'fixtures.json');a=copy.deepcopy(f['authority'])
# Fresh independent identity and exact u64 authority, not author's sequence witness.
a.update(consumer='review-native',window_instance='review-window',root_instance='review-root',runtime_epoch='review-epoch',generation='17',revision='18446744073709551614')
projection=copy.deepcopy(f['projection']);projection.update(source_revision=a['revision'],preview_session='44444444-4444-4444-8444-444444444444')
entry=m.from_projection(a,projection);obs=m.identity(a,entry['handle']);schema=read(S/'observation.schema.json')
seed={'authority':a,'projection':projection,'capture':obs,'delivery':copy.deepcopy(obs)}
write('new-fixtures.json',seed)
ck('reviewer-distinct',read(S/'module-spec.json')['author']=='/root/m03_viewer_identity_seam_packet')
ck('full-tuple-control',m.admit(a,entry,obs,obs) is None)
mapping=read(S/'identity-mapping.json');ck('48-distinct-rows',len(mapping)==48 and len({(r['command'],r['field']) for r in mapping})==48)
def ptr(doc,p):
 for k in p.strip('/').split('/'): doc=doc[k]
 return doc
for r in mapping:
 values=[]
 for kind in ('source_pointer','delivery_source_pointer'):
  fn,pointer=r[kind].split('#');value=ptr(read(S/fn),pointer);values.append(value)
  ck('lookup:'+r['command']+':'+r['field']+':'+kind,type(value) is (bool if r['field'] in ('native_live','revoked') else str))
 ck('authority-revision:'+r['command']+':'+r['field'],r['source_pointer']=='fixtures.json#/authority/revision' if r['field']=='revision' else '/native_observation/capture/'+r['field'] in r['source_pointer'])
 before=P.parent/r['before']['file']
 symbols=['provider_fault','original.intent'] if r['command']=='design_viewer_intent' else [symbol.strip() for symbol in r['before']['symbol'].split(',')]
 ck('source-symbol:'+r['command']+':'+r['field'],before.is_file() and all(symbol in before.read_text(encoding='utf-8') for symbol in symbols))
 trace.append({'command':r['command'],'field':r['field'],'source':r['source_pointer'],'delivery':r['delivery_source_pointer'],'source_sha256':digest(S/r['source_pointer'].split('#')[0]),'schema_pointer':('/properties/'+r['field']) if r['field']!='revision' else 'authority revision: separate owner u64 text, absent observation schema','before':r['before'],'after':r['after'],'status':'PROPOSED_PENDING_OWNER','lookup_types':[type(v).__name__ for v in values]})
# Every identity field is challenged at each phase with distinct invalid types and
# wrong-but-well-typed authority values. Revision is NOT silently added to tuple.
for phase in ('capture','delivery'):
 for field in obs:
  for label,value in [('type',1),('missing',None),('mismatch',not obs[field] if type(obs[field]) is bool else ('18' if field=='generation' else '55555555-5555-4555-8555-555555555555' if field.endswith('uuid') or field=='preview_session' else obs[field]+'-other'))]:
   c=copy.deepcopy(obs);d=copy.deepcopy(obs);target=c if phase=='capture' else d
   if label=='missing':target.pop(field)
   else:target[field]=value
   result=m.admit(a,entry,c,d)
   probes.append({'id':phase+':'+field+':'+label,'capture':c,'delivery':d,'error':result})
   ck('guard:'+phase+':'+field+':'+label,result is not None)
# New differential counterexamples: schema claims a different accepted language
# from the guard. These are document precision findings, not product defects.
counterexamples=[]
for field,value in [('generation','18446744073709551616'),('generation','17\n'),('project_uuid','not-a-uuid'),('document_uuid','not-a-uuid'),('session_uuid','not-a-uuid'),('preview_session','not-a-uuid')]:
 bad={**obs,field:value};schema_ok=m.EVAL.valid(schema,bad);guard=m.admit(a,entry,bad,obs)
 counterexamples.append({'field':field,'value':value,'schema_accepts':schema_ok,'guard_error':guard,'schema_pointer':'/properties/'+field,'guard_pointer':'document_model.py:admit -> viewer-close-integration/document_model.py:identity'})
 ck('counterexample-reproduced:'+field+':'+repr(value),schema_ok and guard=='DependencyNotReady')
def req(pkg):return m.schema(pkg,'request.schema.json')
def response(pkg):return m.schema(pkg,'response.schema.json')
def refresh(c):return m.REFRESH.refresh(c,req('viewer-refresh-integration'),lambda x:response('viewer-refresh-integration')({'ok':True,'value':x,'replayed':False}),lambda e:True)
b=m.begin_case(a,projection);br,bs,bc=m.BEGIN.begin(b,req('preview-begin-correction'))
ck('begin-new-authority-root',br['ok'] and response('preview-begin-correction')(br))
entry=m.from_projection(a,br['value']);old=entry['handle'];obs=m.identity(a,old)
new_projection=copy.deepcopy(projection);new_projection['preview_session']='66666666-6666-4666-8666-666666666666'
rc=m.refresh_case(a,entry,new_projection,obs,obs)
# Force nontrivial previous sequence and occupancy, testing reset and exchange.
rc['before'].update(sequence='93',preview_count=4)
rr,rs,calls=refresh(rc)
ck('capacity-four-one-slot-exchange',rr['ok'] and rs['preview_count']==4 and rs['sequence']=='1' and rs['retired']==[old])
ck('refresh-response-root',response('viewer-refresh-integration')(rr))
new=m.from_projection(a,rr['value'])
oc=m.intent_case(a,new,old);orr,oss,ocs=m.INTENT.intent(oc)
ck('old-handle-fenced',not orr['ok'] and orr['error']['code']=='PreviewClosed' and oss==oc['before'])
nc=m.intent_case(a,new,new['handle']);nr,ns,ncalls=m.INTENT.intent(nc)
ck('new-handle-typed-intent',nr['ok'] and response('viewer-action-typed-correction')(nr) and ns['sequence']=='2')
new.update(sequence=ns['sequence'],mock=ns['mock']);no=m.identity(a,new['handle']);cc=m.close_case(a,new,no,no)
cr=m.CLOSE.close(cc,req('viewer-close-integration'),lambda e:True)
ck('close-retirement',cr['delivered'] and cr['state']['slots']==0 and cr['state']['mock']=={} and response('viewer-close-integration')(cr['response']))
failure=copy.deepcopy(rc);failure['provider']['outcome']={'code':'DependencyNotReady','details':{'dependency':'C1_CODEC'}}
fr,fs,fc=refresh(failure)
ck('rollback-no-false-exchange',not fr['ok'] and fs['preview_session']==old and fs['retired']==[] and fs['preview_count']==4 and fs['can_act'] is False and 'preview.atomic.replace' not in fc)
unknown=copy.deepcopy(cc);unknown['provider']['outcome']='ResponseLostAfterCommit';ur=m.CLOSE.close(unknown,req('viewer-close-integration'),lambda e:True)
ck('lost-close-no-false-closed-or-rollback',not ur['delivered'] and not ur['response']['ok'] and ur['ui']=='CloseUncertain' and ur['state']['slots']==0 and not ur['automatic_retry'])
late=copy.deepcopy(cc);late['provider']['delivery']['runtime_epoch']='review-new-epoch';lr=m.CLOSE.close(late,req('viewer-close-integration'),lambda e:True)
ck('late-close-retired-no-delivery',not lr['delivered'] and lr['state']['slots']==0 and lr['response']['error']['code']=='MissingBinding')
for name,case,state in [('begin',b,bs),('refresh',rc,rs),('intent',nc,ns),('close',cc,cr['state']),('rollback',failure,fs),('unknown',unknown,ur['state']),('late',late,lr['state'])]:
 for key in ('content','history','dirty','saved_baseline','owner_sessions','content_hash','saved_hash'):
  if key in case['before']:ck('preserved:'+name+':'+key,state[key]==case['before'][key])
# Explicit mapping limitation, never interpret correlated fixture snapshots as
# real delivery-time owner observation or native atomicity proof.
owner_ahead={**a,'revision':'18446744073709551615'}
stale_case=m.refresh_case(a,entry,new_projection,obs,obs)
stale_result=refresh(stale_case)
ck('revision-observation-prerequisite-exposed',stale_result[0]['ok'] and owner_ahead['revision']!=stale_case['provider']['delivery']['revision'])
write('sequence-results.json',{'layer':'INDEPENDENT DOCUMENT COMPOSITION ONLY','begin':{'response':br,'calls':bc},'refresh':{'input':rc,'response':rr,'state':rs,'calls':calls},'old_intent':orr,'new_intent':nr,'close':cr,'rollback':{'response':fr,'state':fs,'calls':fc},'unknown_close':ur,'late_close':lr,'revision_capture_limitation':{'external_owner_delivery':owner_ahead,'mapper_delivery':stale_case['provider']['delivery'],'response':stale_result[0],'meaning':'Synthetic unchanged authority snapshot cannot establish delivery revision re-observation. VIS-D2/D3 remain pending; no runtime closure claimed.'}})
preserved=read(S/'preserved-inputs.json');preservation=[]
for path,expected in preserved.items():
 actual=digest(pathlib.Path(path));classification='MATCH' if actual==expected else 'BOARD_MANAGEMENT_DIFF' if path=='docs/board.json' else 'UNEXPECTED_DRIFT'
 preservation.append({'path':path,'expected':expected,'actual':actual,'classification':classification})
 ck('frozen:'+path,classification!='UNEXPECTED_DRIFT')
authority=P.parent.parent.parent/'M01/planning/s2-green/source-current.json'
authority=pathlib.Path('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
product=read(authority)['source_hashes'];ck('authority-796',len(product)==796)
for path,expected in product.items():ck('product:'+path,digest(pathlib.Path(path))==expected)
ck('preserved-513',len(preserved)==513)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
ck('current-head',head=='5b709343a890503ebbe24a802e43cda5647df124')
ck('historical-distinct',read(authority)['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab' and head!=read(authority)['head'])
decisions=read(S/'module-spec.json');ck('five-pending-decisions',{d['id'] for d in decisions['decisions']}=={'VIS-D'+str(i) for i in range(1,6)} and decisions['Owner']=='PENDING' and decisions['architecture_approval']=='NOT APPROVED')
findings=[{'id':'VIS-RF1','priority':'P2','status':'CHANGES_REQUIRED_DOCUMENT_SCHEMA_PRECISION_ONLY','title':'Candidate observation schema overaccepts values rejected by full-tuple guard','source':'viewer-identity-seam-proposal/observation.schema.json#/properties','required_action':'Align UUID grammar and exact bounded u64 generation (including strict end-of-string) with CLOSE.identity, or explicitly define schema as a permissive transport shape and add a separately named mandatory semantic contract with differential tests. Keep rejection semantics and public command schemas unchanged.','counterexamples':counterexamples}]
results={'reviewer':'/root/m03_identity_seam_review','author':decisions['author'],'status':'CHANGES_REQUIRED_DOCUMENT_SCHEMA_PRECISION_ONLY','state':'REPLAN_REQUIRED','task':'PD-P1-M03-PREP-01','head':head,'historical_head':read(authority)['head'],'checks':len(checks),'passed':sum(x['pass'] for x in checks),'failed':sum(not x['pass'] for x in checks),'fresh_guard_cases':len(probes),'mapping_rows':len(mapping),'differential_counterexamples':len(counterexamples),'preserved_inputs':len(preserved),'product_inputs':len(product),'findings':findings,'owner_decisions':[{**d,'approval':'PENDING'} for d in decisions['decisions']],'recommendation':'VIS-D1 option A: sole M04 document authority and M03 derived ephemeral preview; no second document registry. Exact observer/fence signature and lock ordering remain Owner decisions.','remaining_gates':['Correct VIS-RF1 and independently re-review bounded correction','Owner confirms VIS-D1..D5','Approve revised Skeleton and demonstrate valid product RED','Separate implementation and independent native/module/system acceptance'],'B058_B059_B060':'SEPARATE; no coverage or closure claimed','native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft2020':'NOT RUN','full_module_Draft':'NOT RUN','author_1464_rerun':False,'checks_detail':checks}
write('results.json',results);write('traceability.json',trace);write('negative-fixtures.json',probes);write('preservation.json',preservation)
sources={str(p):digest(p) for p in S.iterdir() if p.is_file()}
for folder in ['preview-begin-correction','viewer-action-typed-correction','viewer-action-integration','viewer-refresh-integration','viewer-close-integration','command-integration-correction-review']:
 for p in (P.parent/folder).iterdir():
  if p.is_file() and p.suffix in ('.py','.json','.html'):sources[str(p)]=digest(p)
write('source-hashes.json',sources)
summary='CHANGES_REQUIRED: VIS-RF1 candidate observation schema and mandatory guard accept different languages. Six fresh counterexamples. This is document precision, not a product defect. '
body='<h1>M03 Viewer identity seam independent document review</h1><p>'+summary+'</p><p>Yellow remains. REPLAN_REQUIRED; Owner VIS-D1..D5 pending. Recommend sole M04 document authority, M03 derived preview only; no second document registry. B058–B060 remain separate.</p><p>New fixture authority, capacity-four exchange, old/new handle fence, typed intent, close retirement, rollback, lost close, and late delivery probes pass. Source→mapper→preserved reducer composition is synthetic document evidence only. Delivery revision capture/fence/native trust are prerequisites, not runtime proof.</p><p>Native/build/product/valid RED/full Draft/module acceptance: NOT RUN. Author 1464 checker was not rerun.</p><h2>Review results and exact trace</h2><pre>'+html.escape(json.dumps({k:v for k,v in results.items() if k!='checks_detail'},ensure_ascii=False,indent=2))+'</pre><h2>48 mapping rows</h2><pre>'+html.escape(json.dumps(trace,ensure_ascii=False,indent=2))+'</pre>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 independent identity seam review</title><style>body{max-width:1100px;margin:40px auto;background:#101720;color:#e0e9f2;font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1b2733;padding:20px}h1,h2{color:#f2cb79}</style>'+body+'<script type="application/json" id="module-review">'+json.dumps({k:v for k,v in results.items() if k!='checks_detail'},ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
manifest={p.name:digest(p) for p in P.iterdir() if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')}
write('artifact-hashes.json',manifest)
write('seal.json',{'reviewer':results['reviewer'],'status':results['status'],'artifact_count':len(manifest),'manifest_sha256':digest(P/'artifact-hashes.json'),'counts':{k:results[k] for k in ('checks','passed','failed','fresh_guard_cases','mapping_rows','differential_counterexamples','preserved_inputs','product_inputs')},'next_action':'Correct VIS-RF1 in a new bounded candidate; independently re-review; Owner VIS-D1..D5 remains pending. No production or original edits.','native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft2020':'NOT RUN'})
print(json.dumps({k:results[k] for k in ('status','checks','passed','failed','fresh_guard_cases','mapping_rows','differential_counterexamples')}))
if any(not x['pass'] for x in checks):raise SystemExit(1)
