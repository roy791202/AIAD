import pathlib,json,hashlib,re,html,subprocess,copy,datetime
R=pathlib.Path('.'); O=R/'docs/requirements-confirmation/phase1-spec/tasks/M08/verification/input-admission-correction-review-20261103'; C=O.with_name('input-admission-correction-20261103'); B=O.with_name('input-admission-20261103'); V=O.with_name('input-admission-review-20261103')
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def put(n,d):(O/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
checks=[]
def ck(n,b,d=None):checks.append(dict(name=n,passed=bool(b),detail=d))
c=read(C/'native-case-crosswalk.json'); old=read(B/'native-case-crosswalk.json'); a=read(V/'authority-a-rows.json'); f=read(C/'feature-input-matrix.json'); m=read(C/'missing-inputs.json'); source=R/'docs/requirements-confirmation/phase1-spec/index.html'; sh=source.read_text(encoding='utf-8-sig')
for name,h in read(C/'seal.json')['files'].items():ck('candidate seal '+name,sha(C/name)==h)
ck('Feature bytes unchanged',sha(C/'feature-input-matrix.json')==sha(B/'feature-input-matrix.json'))
ck('16 N entries unchanged',c['cases'][:16]==old['cases'][:16])
ck('20 missing gates unchanged',len(m['items'])==20 and m['items']==read(B/'missing-inputs.json')['items'])
ck('24 cases',len(c['cases'])==24)
def validate_A(row, expected):
 cells=re.findall(r'<td>(.*?)</td>',expected['raw_row'],re.S)
 return row['id']==expected['id'] and row['case_source']==dict(path=expected['source'],pointer=expected['selector'],sha256=sha(source)) and row['original_authority_raw_row']==expected['raw_row'] and row['original_definition_verbatim']==cells[0] and row['required_evidence_verbatim']==cells[1] and row['definition_availability']=='AVAILABLE_AUTHORITY_BOUND' and row['mapping_status']=='OPEN' and row['admission']=='BLOCKED_NOT_RUN' and 'Definition is available.' in row['reason']
for row,expected in zip(c['cases'][16:],a['rows']):
 independently=next(x for x in re.findall(r'<tr>(.*?)</tr>',sh,re.S) if re.search('<td>'+expected['id']+r'\s',x))
 ck(row['id']+' independent authority/definition/evidence/selector/hash',independently==expected['raw_row'] and validate_A(row,expected))
ck('false unavailable definitions removed',not re.search('unavailable|not located|缺少定義',json.dumps(c['cases'][16:],ensure_ascii=False),re.I))
page=(C/'index.html').read_text(encoding='utf8'); table=re.findall(r'<tr>(.*?)</tr>',page,re.S)[1:]
for row,tr in zip(c['cases'][16:],table):ck(row['id']+' visible HTML exact cells',re.findall(r'<td>(.*?)</td>',tr,re.S)==[row['id'],html.escape(row['original_definition_verbatim']),html.escape(row['required_evidence_verbatim']),'OPEN / BLOCKED_NOT_RUN'])
embedded=[json.loads(html.unescape(p)) for p in re.findall(r'<pre>(.*?)</pre>',page,re.S)]
ck('HTML embedded closure exact',embedded==[read(C/'closure-diff.json')]);ck('HTML JSON links resolve',all((C/n).is_file() for n in re.findall(r'href="([^"]+)"',page)))
# Correction HTML embeds closure only, other datasets are exact linked JSON rather than claimed embedded data.
source_drift=[]
for p,h in read(C/'source-hashes.json')['sources'].items():
 if sha(p)!=h:source_drift.append(p)
ck('candidate source binding drift classified',set(source_drift)<= {'docs/board.json','reports/rust-improvements/continuous/coordination/heartbeat-latest.json'},source_drift)
inv=read('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'); ck('796 authority hashes current',len(inv['source_hashes'])==796 and all(sha(p)==h for p,h in inv['source_hashes'].items()));ck('live HEAD correct',subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()=='5b709343a890503ebbe24a802e43cda5647df124',{'historical_inventory_head':inv['head'],'classification':'historical 31babe87 is not current product HEAD; board-management context separated'})
for feat in f['features']:
 ck(feat['feature']+' preserved records',all(read(r['source']['path'])==r['source_data_verbatim'] for r in feat['preserved_trace_and_recipe_records']))
ck('12 Features',len(f['features'])==12)
board=read('docs/board.json'); snap=f['board_card_readonly_snapshot']; card=next(x for x in board['items'] if x['id']==snap['id']); prior=read(V/'board-context.json'); before=copy.deepcopy(snap)
for k,v in prior['changed_card_fields'].items():before[k]=v['current']
delta={k:{'before':before.get(k),'now':card.get(k)} for k in set(before)|set(card) if before.get(k)!=card.get(k)}
ck('board since prior review append-note metadata only',set(delta)<= {'notes','updatedAt'} and card['notes'][:len(before['notes'])]==before['notes'],list(delta))
put('board-context.json',{'since_original_snapshot_changed_fields':[k for k in set(snap)|set(card) if snap.get(k)!=card.get(k)],'since_prior_review':delta,'root_updatedAt':board['updatedAt'],'classification':'M08 append-only notes and item/root updatedAt are management metadata; no status/light/TDD/CI/legacy scope authority granted','card_status':card.get('status'),'card_light':card.get('light')})
# New semantic mutations independently exercise split definition/evidence and anti-upgrade rules; no author validator imported.
probes=[]
for label,field,value in [('evidence omitted','required_evidence_verbatim',''),('definition swapped with evidence','original_definition_verbatim',c['cases'][16]['required_evidence_verbatim']),('selector points another criterion','case_source',dict(c['cases'][16]['case_source'],pointer='tr > td starts A02')),('available definition falsely unavailable','definition_availability','UNAVAILABLE'),('admission upgraded despite OPEN mapping','admission','PASS')]:
 bad=copy.deepcopy(c['cases'][16]);bad[field]=value;probes.append({'id':label,'expected':'REJECT','actual':'REJECT' if not validate_A(bad,a['rows'][0]) else 'ACCEPT','passed':not validate_A(bad,a['rows'][0]),'layer':'new independent document semantic mutation; not product test'})
# Operational admission cannot be inferred by full authority inventory or review PASS alone.
for gate in ['ARTIFACT-SHA','VERSION-BUILD','WIN11','PROVIDERS','OBSERVABILITY','M08-PD1','M08-PD2','M08-PD3']:
 item=next(x for x in m['items'] if x['id']==gate);probes.append({'id':'authority_available_does_not_override_'+gate,'expected':'BLOCKED_NOT_RUN','actual':item['status'],'passed':item['status']=='BLOCKED_NOT_RUN','layer':'gate preservation semantic probe'})
put('probes.json',probes)
findings=[] if all(x['passed'] for x in checks+probes) else [{'id':'CR1','status':'OPEN','failed':[x for x in checks+probes if not x['passed']]}]
put('findings.json',{'prior_R1':'CLOSED_DOCUMENT_CORRECTION' if not findings else 'NOT_CLOSED','new_findings':findings,'remaining_OPEN':'Exact Feature/native equivalence and actual execution evidence; not missing original definitions'})
result={'verdict':'PASS_BOUNDED_DOCUMENT_CORRECTION' if not findings else 'CHANGES_REQUIRED','author':'/root/m08_admission_correction_packet','reviewer':'/root/m08_admission_correction_review','review_context':'2026-11-03T12:07:05.043Z','author_creation_instruction_context':'2026-11-03T11:57Z; distinct from review context; no retroactive author metadata required','checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks':checks,'product_acceptance':'NOT RUN','native':'BLOCKED_NOT_RUN','build':'NOT RUN','RED_GREEN':'NOT RUN','Owner_adoption':'NOT RUN','limits':['Independent document review only, not product/native/Owner adoption.','Correction HTML embeds closure JSON and links full datasets; does not falsely claim all JSON embedded.','All 20 admission gates preserved; accepted PREP not reopened; PD1..3 not approved.','No candidate, board, product, spec, tests, hooks, roles edits; no commit.']}
put('results.json',result)
(O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M08 independent R1 correction review</title><h1>'+result['verdict']+'</h1><p>R1 original definitions correction independently reviewed. 8 authority criteria and evidence columns preserved; 12 Features, 16 N cases, 20 gates unchanged. Exact native equivalence stays OPEN.</p><p>Author: '+result['author']+'; independent reviewer: '+result['reviewer']+'. Product/native/build/Owner adoption NOT RUN; native admission BLOCKED_NOT_RUN.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre><a href="findings.json">Findings</a> <a href="probes.json">New semantic probes</a> <a href="board-context.json">Board drift classification</a>',encoding='utf8')
put('seal.json',{'status':'SEALED_STOP_WRITING','scope':'bounded independent document correction review','files':{x.name:sha(x) for x in O.iterdir() if x.is_file() and x.name!='seal.json'}})
print(json.dumps({'verdict':result['verdict'],'checks':len(checks),'probes':len(probes),'failed':[x for x in checks+probes if not x['passed']]},ensure_ascii=True))
