"""Independent document-only reviewer. Run python -B checker.py. Writes only this review directory."""
import copy,hashlib,html,importlib.util,json,pathlib,re,subprocess
P=pathlib.Path(__file__).resolve().parent;B=P.parent;H=B/'command-integration-handoff';ROOT=P.parents[6]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(n,d):(P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def ptr(d,p):
 for k in p.strip('/').split('/') if p else []:d=d[int(k)] if isinstance(d,list) else d[k.replace('~1','/').replace('~0','~')]
 return d
checks=[]
def check(name,ok,detail=None):
 checks.append({'id':name,'pass':bool(ok),'detail':detail});assert ok,name
rows=read(H/'command-coverage.json');tr=read(H/'original-62-trace.json');cats=read(H/'bdd-categories.json')
inputs=read(H/'source-input-hashes.json');baseline={k:sha(ROOT/k) for k in inputs};drift=[k for k,v in inputs.items() if baseline[k]!=v]
check('sealed-input-preservation',not drift,{'inputs':len(inputs),'drift':drift})
manifest=read(H/'artifact-hashes.json');check('handoff-manifest',all(sha(H/k)==v for k,v in manifest.items()));check('handoff-seal',sha(H/'artifact-hashes.json')==read(H/'seal.json')['manifest_sha256'])
authority=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');check('product-796',len(authority['source_hashes'])==796 and all(sha(ROOT/k)==v for k,v in authority['source_hashes'].items()))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();check('head-current',head=='5b709343a890503ebbe24a802e43cda5647df124')
original=read(B/'h2-exact-design/dto-errors.json')['requests'];check('exact-command-order',list(original)==[r['command'] for r in rows])
rootissues=[];roottrace=[]
for r in rows:
 cand=B/r['effective_candidate'];cmd=r['command'];s=cand/'response.schema.json'
 if not s.exists():s=cand/('h2-'+cmd+'-response.schema.json')
 req=cand/'request.schema.json'
 if not req.exists():req=cand/('h2-'+cmd+'-request.schema.json')
 actual=read(s);decl=B/r['response_root_source'];bad=[]
 for c in r['response_root_constants']:
  check(cmd+':constant:'+c['pointer'],ptr(actual,c['pointer'])==c['value'])
  try:valid=ptr(read(decl),c['pointer'])==c['value']
  except (FileNotFoundError,KeyError,IndexError,TypeError,ValueError):valid=False
  if not valid:bad.append(c['pointer'])
 if bad:rootissues.append({'command':cmd,'declared':r['response_root_source'],'exists':decl.exists(),'actual':str(s.relative_to(B)),'unresolved_pointers':len(bad),'first_pointer':bad[0]})
 for ev in r['candidate_evidence']+r['review_evidence']:
  check(cmd+':evidence:'+ev['file'],sha(B/ev['file'])==ev['sha256'])
  for claim in ev['claims']:check(cmd+':claim:'+claim['pointer'],ptr(read(B/ev['file']),claim['pointer'])==claim['value'])
 check(cmd+':unadopted',r['adoption']=='PROPOSED_PENDING_OWNER' and r['module_verification']=='NOT RUN')
 roottrace.append({'command':cmd,'candidate':r['effective_candidate'],'review':r['independent_scoped_review'],'request_schema':str(req.relative_to(B)),'response_schema':str(s.relative_to(B)),'request_sha256':sha(req),'response_sha256':sha(s),'request_root_keys':list(read(req)),'response_root_keys':list(actual),'dynamic_function_root_claim':'NOT CLAIMED: these are actual schema roots; selected reducer call roots independently tested below'})
check('pointer-counterexample-all13',len(rootissues)==13)
feature=(B/'h2-exact-design/module.feature').read_text(encoding='utf-8');origrows=read(B/'h2-exact-design/traceability.json')['rows']
check('62-original-records',len(tr)==62 and [r['original'] for r in tr]==origrows)
for row in tr:
 bid=row['original']['bdd'];block=next(x for x in feature.split('  Rule: ') if x.startswith(bid)).strip();check(bid+':exact-behavior',block==row['original_behavior'])
 for link in row['candidate_behavior_links']:check(bid+':candidate-exists:' + link['command'],(B/link['candidate_pointer']).exists() and link['link_kind']=='MANUAL_BEHAVIOR_RECONCILIATION_NOT_PROOF')
check('legacy-gap-exact',[r['original']['bdd'] for r in tr if not r['candidate_behavior_links']]==['M03-H2-B058','M03-H2-B059','M03-H2-B060'])
check('categories12',len(cats)==12 and {c['id'] for c in cats}=={'B'+str(n) for n in range(1,13)} and all(c['applicability']=='Applicable' and c['module_status']=='DEFERRED' and c['reason'] for c in cats))
# New negative trace probes: no textual matching can grant executable evidence.
def trace_gate(t):return len(t)==62 and {r['original']['bdd'] for r in t}=={'M03-H2-B%03d'%n for n in range(1,63)} and all((B/l['candidate_pointer']).is_file() for r in t for l in r['candidate_behavior_links'])
negative=[]
x=copy.deepcopy(tr);x.pop();negative.append({'id':'NEG-TRACE-MISSING-B062','rejected':not trace_gate(x)})
x=copy.deepcopy(tr);x[0]['candidate_behavior_links'][0]['candidate_pointer']='missing-no-such-sealed-candidate.json';negative.append({'id':'NEG-TRACE-BROKEN-CANDIDATE','rejected':not trace_gate(x)})
check('negative-trace-probes',all(n['rejected'] for n in negative))
# Independently reproduce calls using the schema roots that the functions actually receive.
refresh=load('independent_refresh',B/'viewer-refresh-integration/document_model.py');sc=load('independent_schema',B/'viewer-refresh-integration/schema_eval.py');close=load('independent_close',B/'viewer-close-integration/document_model.py')
w=read(H/'new-sequence-witness.json');case=copy.deepcopy(w['fixture']);rq=read(B/'viewer-refresh-integration/request.schema.json');rs=read(B/'viewer-refresh-integration/response.schema.json')
validators=[lambda x:sc.valid(rq,x),lambda x:sc.valid({'$defs':rs['$defs'],'$ref':'#/$defs/Preview'},x),lambda x:sc.valid({'$defs':rs['$defs'],'$ref':'#/$defs/Error'},x)]
out,after,calls=refresh.refresh(case,*validators);check('sequence-refresh',out==w['steps'][0]['response'] and after==w['steps'][0]['after'] and calls==w['steps'][0]['calls'])
old=copy.deepcopy(case);old['before']=after;out2,after2,calls2=refresh.refresh(old,*validators);check('sequence-retired-handle',out2==w['steps'][1]['response'] and after2==w['steps'][1]['after'] and calls2==w['steps'][1]['calls'])
closecase={'before':after,'request':{'preview_session':after['preview_session']},'provider':case['provider']};res=close.close(closecase,lambda x:True,lambda x:True);check('sequence-close-original-branch',res==w['steps'][2]['result'])
# Important sequential distinction: author's close uses step1 state, not the intervening old-handle step2 state.
sequential=copy.deepcopy(closecase);sequential['before']=after2;seqres=close.close(sequential,lambda x:True,lambda x:True);check('sequence-close-after-step2',seqres['response']==res['response'] and seqres['state']==after2)
# New provider isolation: root shape fails even before request callback, regardless of state bytes.
probe=close.close({'before':{},'request':None,'provider':copy.deepcopy(case['provider'])},lambda x:(_ for _ in ()).throw(AssertionError('request validator reached')),lambda x:False)
check('new-provider-shape-before-request',probe['calls']==['native.caller.observe'] and probe['response']['error']['code']=='DependencyNotReady')
# Compatible close fixture proves no inference that close is universally broken.
closefixtures=read(B/'viewer-close-integration/fixtures.json');compatible=next(c for c in closefixtures if c['provider'].get('outcome')=='Closed');cq=read(B/'viewer-close-integration/request.schema.json');cr=read(B/'viewer-close-integration/response.schema.json')
ctrl=close.close(copy.deepcopy(compatible),lambda x:sc.valid(cq,x),lambda x:sc.valid({'$defs':cr['$defs'],'$ref':'#/$defs/Error'},x));check('compatible-close-control',ctrl['response']['ok'] and ctrl['delivered'])
# New dynamic boundary probes: valid schema failure is observable at actual public function callback.
for key,val in [('preview_session',None),('expected_revision',9007199254740993)]:
 c=copy.deepcopy(case);c['request'][key]=val;o,s,cl=refresh.refresh(c,*validators);check('new-refresh-request-root:'+key,o['error']['code']=='InvalidRequest' and cl==[])
# Full protected inputs checked after all imported reducers; no old checker/build invocation.
check('post-input-preservation',all(sha(ROOT/k)==v for k,v in baseline.items()))
put('root-trace.json',roottrace);put('negative-probes.json',negative);put('sequence-results.json',{'refresh':out,'old_handle':out2,'author_close':res,'strict_sequential_close':seqres,'provider_shape_isolation':probe,'compatible_close_control':ctrl,'scope':'Document models only. Trusted identity, UUID uniqueness, revocation, registry consistency and atomicity are supplied fixture premises, not verified native capabilities.'})
findings=[{'id':'CIHR-F1','priority':'P2','title':'All 13 response root source links identify wrong files','evidence':rootissues,'cause':'build_handoff.py reuses f for outcome-file loop before recording response_root_source; actual constants are response schema values.','required_change':'Retain separate response_schema_path, emit request/response schema paths and dynamic function callback root references; add pointer-resolution negative test and reseal.'}]
review={'verdict':'CHANGES_REQUIRED_SCOPED_DOCUMENT_HANDOFF_ONLY','author':'/root/m03_command_coverage_handoff','reviewer':'/root/m03_command_handoff_review','findings':findings,'nonblocking_notes':[{'id':'CIHR-N1','text':'Author labels ordered 3-step witness but close uses step1 after state, bypassing old-handle after2 stale/can_act changes. Strict sequential recomposition independently returns same DependencyNotReady, preserving seam conclusion. Label close as branch or use after2.'},{'id':'CIHR-N2','text':'CIH-G1 demonstrates incompatible document provider/state records only. No actual runtime architecture defect proved. Port/registry/error proposals remain Owner decisions; no bijection from wire output grants authority.'},{'id':'CIHR-N3','text':'B1-B12 are evaluated Applicable/Deferred; thematic 59 links are not executable closure. B058-B060 are exact legacy ingress gaps. No full module PASS inherited.'}],'next_ready_action':'Separate author corrects 13 response_root_source links and strengthens root-resolution checks, labels branch/strict sequence, reseals a bounded correction; new independent document review before Owner chooses CIH-G1 seam. No Skeleton/product RED before exact adoption.','health':'Yellow / REPLAN_REQUIRED','owner':'PENDING / NOT ADOPTED','module_complete':False,'native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft':'NOT RUN','full_module_acceptance':'NOT RUN','head':head,'historical_head': '31babe87a7ef1e40a0d4bedc523077e7a45d63ab','product_hashes_preserved':796,'input_hashes_preserved':len(inputs),'board_drift':'Management-only: docs/board.json not product authority; review does not mutate board. Source-input set checked separately.','checks':len(checks),'commands':13,'original_BDD':62,'categories':12,'finding_count':len(findings),'new_negative_trace_probes':2,'new_dynamic_probes':5}
put('review.json',review);put('results.json',{'status':'PASS_REVIEW_CHECKER_FINDING_REPRODUCED','checks':checks,'findings':len(findings),'old_suites_rerun':False});put('input-hashes.json',baseline)
data=json.dumps(review,ensure_ascii=False).replace('</','<\\/');body='<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 independent command handoff review</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;background:#14202a;color:#eaf0f5}h1,h2{color:#ffd277}a{color:#90d4ff}pre{white-space:pre-wrap;background:#1e303e;padding:18px}</style><h1>M03 independent document review</h1><p>CHANGES_REQUIRED · Yellow · no module acceptance or Owner adoption</p><p>13 commands / 62 original BDD / B1–B12 evaluated. All 796 product hashes preserved.</p><h2>Finding CIHR-F1</h2><p>Every response root source points to work-error-map.json while constants originate in the response schema. Correct the source paths and validate every pointer before resealing.</p><h2>Architecture and composition boundary</h2><pre>UI → Tauri input adapter → M03 → M04 / C1 / M05 ports\nWire DTO never confers native authority.\nRefresh full tuple ≠ close full tuple. No automatic union adoption.</pre><p>Refresh succeeds; retired old handle is refused. Close rejects incompatible provider shape before request validation. Strict sequential state reproduces the same refusal. A compatible close fixture succeeds. This is a document seam, not proof of a runtime architecture flaw.</p><h2>Behavior and verification</h2><p>59 thematic reconciliation rows remain partial; B058–B060 are legacy ingress gaps. All categories are explicitly deferred. Native/product/build/valid RED/full Draft NOT RUN.</p><p><a href="root-trace.json">13 actual schema roots and hashes</a> · <a href="sequence-results.json">Independent dynamic composition and controls</a> · <a href="negative-probes.json">Negative trace probes</a> · <a href="results.json">Checker evidence</a></p><h2>Next ready action</h2><p>'+html.escape(review['next_ready_action'])+'</p><script type="application/json" id="module-spec">'+data+'</script></html>'
(P/'index.html').write_text(body,encoding='utf-8')
files={f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name not in ('artifact-hashes.json','seal.json')};put('artifact-hashes.json',files);put('seal.json',{'status':'SEALED_INDEPENDENT_REVIEW_CHANGES_REQUIRED','manifest_sha256':sha(P/'artifact-hashes.json'),'artifacts':len(files),'counts':{k:review[k] for k in ('checks','commands','original_BDD','categories','finding_count','new_negative_trace_probes','new_dynamic_probes')},'module_complete':False})
print(json.dumps({k:review[k] for k in ('verdict','checks','commands','original_BDD','categories','finding_count','product_hashes_preserved','input_hashes_preserved')}))

