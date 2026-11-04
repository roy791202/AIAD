import pathlib,json,hashlib,re,html,subprocess,copy,datetime
R=pathlib.Path('.'); P=R/'docs/requirements-confirmation/phase1-spec/tasks/M08/verification/input-admission-20261103'; O=P.with_name('input-admission-review-20261103')
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
checks=[]
def check(n,b,detail=None): checks.append(dict(name=n,passed=bool(b),detail=detail))
f=read(P/'feature-input-matrix.json'); c=read(P/'native-case-crosswalk.json'); m=read(P/'missing-inputs.json'); hs=read(P/'source-hashes.json'); seal=read(P/'seal.json')
for n,h in seal['files'].items():check('candidate seal '+n,sha(P/n)==h)
drift=[p for p,h in hs['sources'].items() if sha(p)!=h];check('129 source binding classification',len(hs['sources'])==129 and set(drift)<= {'docs/board.json','reports/rust-improvements/continuous/coordination/heartbeat-latest.json'},drift)
inv=read('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');check('796 product files unchanged',len(inv['source_hashes'])==796 and all(sha(p)==h for p,h in inv['source_hashes'].items()))
check('live HEAD',subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='5b709343a890503ebbe24a802e43cda5647df124')
original=read('docs/requirements-confirmation/phase1-spec/tasks/M08/planning/native-evidence-plan/case-matrix.json')['cases']
check('16 original N cases verbatim',[x['original_case_verbatim'] for x in c['cases'][:16]]==original)
for feat in f['features']:
 check(feat['feature']+' trace/review present',bool(feat['trace_sources']) and bool(feat['document_reviews']))
 for rec in feat['preserved_trace_and_recipe_records']:
  src=read(rec['source']['path']);check(feat['feature']+' preserved source exact '+rec['source']['path'],src==rec['source_data_verbatim'])
check('20 missing inputs',len(m['items'])==20)
pre=re.findall(r'<pre>(.*?)</pre>',(P/'index.html').read_text(encoding='utf8'),re.S)
embedded=[json.loads(html.unescape(x)) for x in pre]
check('HTML four embedded datasets equal JSON',embedded==[f,c,m,hs])
s=pathlib.Path('docs/requirements-confirmation/phase1-spec/index.html').read_text(encoding='utf8'); rows=[]
for ident in ['A%02d'%i for i in range(1,9)]:
 row=next((x for x in re.findall(r'<tr>(.*?)</tr>',s,re.S) if re.search(r'<td>'+ident+r'\s',x)),None);rows.append({'id':ident,'source':'docs/requirements-confirmation/phase1-spec/index.html','selector':'tr > td starts '+ident,'raw_row':row})
check('A01-A08 authority rows found',all(x['raw_row'] for x in rows))
put('authority-a-rows.json',{'source_sha256':sha('docs/requirements-confirmation/phase1-spec/index.html'),'rows':rows})
board=read('docs/board.json'); live=next(x for x in board['items'] if x['id']=='PD-P1-M08-VERIFY-01'); old=f['board_card_readonly_snapshot']; dif={k:{'snapshot':old.get(k),'current':live.get(k)} for k in set(old)|set(live) if old.get(k)!=live.get(k)};put('board-context.json',{'changed_card_fields':dif,'current_root_updatedAt':board['updatedAt'],'classification':'Current card metadata/append-only notes drift; scope/status/light/legacy acceptance compared below','unchanged_fields':[k for k in ['status','light','legacyTask','tdd','ci'] if old.get(k)==live.get(k)]})
# New review-only admission model probes: missing any required gate cannot become eligible.
gates=['product_acceptance','artifact_sha','version_build','win11','provider','observability','PD1','PD2','PD3']
def eligible(x):return all(x.get(g) is True for g in gates)
probes=[]
for g in gates:
 fixture={k:True for k in gates};fixture[g]=False;probes.append({'id':'ADMIT-MISSING-'+g,'fixture':fixture,'expected':'BLOCKED_NOT_RUN','actual':'ELIGIBLE' if eligible(fixture) else 'BLOCKED_NOT_RUN','passed':not eligible(fixture),'layer':'review semantic probe only, not product/harness test'})
probes += [{'id':'DOCUMENT-PASS-NOT-PRODUCT','fixture':{'document_review':'PASS','product_acceptance':False},'passed':not eligible({'document_review':'PASS','product_acceptance':False}),'actual':'BLOCKED_NOT_RUN'}, {'id':'A-DEFINITION-OMISSION','expected':'authority retained even when execution mapping OPEN','actual':'candidate says criteria unavailable although root table contains eight criteria','passed':False}]
put('probes.json',probes)
findings=[{'id':'R1','severity':'P2','status':'OPEN','title':'A01-A08 definitions incorrectly reported unavailable','source':'docs/requirements-confirmation/phase1-spec/index.html (eight table rows preserved in authority-a-rows.json)','candidate':'native-case-crosswalk.json#/cases/16..23','impact':'Input inventory omits available original acceptance criteria and incorrectly requests Owner to supply existing definitions. OPEN exact feature/native equivalence may remain, but definition availability must be distinguished from unresolved correspondence.','required_fix':'Copy/hash-bind exact eight source table criteria as original authority, retain source encoding condition without inventing repaired wording; re-evaluate deterministic requirement/case associations separately from Owner approval and keep uncertain exact mappings OPEN. Update missing inputs and HTML accordingly.'}]
put('findings.json',findings)
result={'verdict':'CHANGES_REQUIRED_DOCUMENT_INPUT_INVENTORY_ONLY','author':'/root/m08_input_admission_packet','reviewer':'/root/m08_input_admission_review','checks':checks,'findings':1,'native':'BLOCKED_NOT_RUN','product_acceptance':'NOT RUN','build':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','acceptance':'NOT RUN','limits':['No product, candidate, board, specification, tests or hooks changed; no commit.','PREP remains accepted within original document scope. PD1-PD3 still require Owner adoption.','24 OPEN mappings do not imply native failure; available acceptance definitions must still be inventoried.','Candidate generated_at 11:39:07Z is distinct from later Owner heartbeat review context. No retroactive future metadata required.']}
put('results.json',result)
(O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M08 independent input review</title><h1>CHANGES_REQUIRED — document input inventory only</h1><p>Independent reviewer: /root/m08_input_admission_review; author: /root/m08_input_admission_packet.</p><p>A01–A08 definitions exist in the original phase1 HTML acceptance table. Candidate must preserve them; uncertain exact Feature/native mappings may remain OPEN. No native/product/build/RED/GREEN acceptance was performed.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre><p><a href="findings.json">Findings</a> · <a href="probes.json">New semantic probes</a> · <a href="authority-a-rows.json">Original A authority rows</a></p>',encoding='utf8')
put('seal.json',{'scope':'independent bounded document review','files':{x.name:sha(x) for x in O.iterdir() if x.name!='seal.json'}})
print(json.dumps({'verdict':result['verdict'],'checks':len(checks),'failed_checks':[x for x in checks if not x['passed']],'source_drift':drift,'probes':len(probes)},ensure_ascii=True))
