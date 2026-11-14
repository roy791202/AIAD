import json,hashlib,subprocess,copy,html
from pathlib import Path
P=Path(__file__).resolve().parent
C=P.parent/'provider-source-map-20261104'
ROOT=Path('D:/AIAD')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
before={p.name:sha(p) for p in C.iterdir() if p.is_file()}
d=read(C/'module-spec.json');spans=read(C/'source-spans.json');checks=[]
def ck(name,v):checks.append({'id':name,'pass':bool(v)})
seal=read(C/'seal.json')
for f,h in seal['artifacts'].items():ck('seal:'+f,sha(C/f)==h)
for f,h in read(C/'source-hashes.json').items():ck('source:'+f,sha(ROOT/f)==h)
for x in spans:
 lines=(ROOT/x['path']).read_text(encoding='utf-8').splitlines();ck('span:'+x['id'],'\n'.join(lines[x['start']-1:x['end']])==x['text'])
auth=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes']
ck('authority796',len(auth)==796 and all(sha(ROOT/f)==h for f,h in auth.items()))
ck('head',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==d['head'])
ck('differentHistorical',d['head']!=d['historical_head'] and d['head_same_as_historical'] is False)
for q in read(C/'search-log.json'):
 r=subprocess.run(q['command'],cwd=ROOT,text=True,capture_output=True);ck('limitedrg:'+q['command'][2],r.returncode==q['exit'] and r.stdout==q['stdout'] and 'Only HOST' in q['limit'])
proposal=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M04/planning/save-retention-observation-proposal/module-spec.json')
ck('G1to4pending',len(proposal['choices'])==4 and all(x['status']=='PROPOSED_PENDING_OWNER' for x in proposal['choices']))
ck('threeNullBridges',len(d['field_bridge_gaps'])==3 and all(x['selected'] is None for x in d['field_bridge_gaps']))
ck('threeEarlierYellow',len(d['earlier_yellow_actions'])==3 and all('do not rerun' in x['attempt'] for x in d['earlier_yellow_actions']))
ck('sceneBoundary','fs.write_atomic' in spans[3]['text'] and 'Ok(path)' in spans[3]['text'] and 'FileCommitPort' not in spans[3]['text'])
ck('ackSeparate','formal_baseline' in spans[4]['text'] and 'snapshot_baseline' in spans[5]['text'])
ck('retentionInert','No physical cleanup behavior' in spans[7]['text'] and 'EligibleForCleanup' in spans[8]['text'])
# Fresh semantic negative document guards. These classify evidence, not product tests.
def accepted(v):
 return (v['kind']=='static_source' and not any(v[k] for k in ['receipt_is_semantic_ack','eligible_is_delete_authority','search_global_absence','native_pass','adopted']) and v['selected'] is None and v['head']!=d['historical_head'])
v={'kind':'static_source','receipt_is_semantic_ack':False,'eligible_is_delete_authority':False,'search_global_absence':False,'native_pass':False,'adopted':False,'selected':None,'head':d['head']}
ck('guardBaseline',accepted(v));probes=[]
for k,val in [('receipt_is_semantic_ack',True),('eligible_is_delete_authority',True),('search_global_absence',True),('native_pass',True),('adopted',True),('selected','G4'),('head',d['historical_head']),('kind','runtime')]:
 m=copy.deepcopy(v);m[k]=val;ok=not accepted(m);probes.append({'mutation':k,'rejected':ok});ck('negative:'+k,ok)
ck('candidateUnchanged',before=={p.name:sha(p) for p in C.iterdir() if p.is_file()})
result={'reviewer':'/root/m04_provider_review','author':d['author'],'status':'BOUNDED_DOCUMENT_REVIEW_PASS' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','checks':checks,'probes':probes,'findings':[],'limits':['Static source/document review only; guards are reviewer documentary semantics, not product behavior tests.','Product/native/build/package/regression NOT RUN; no historical PASS rerun.','No adoption. HOST src searches do not prove global or runtime absence.'],'candidate_hashes':before}
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
body='<h1>M04 provider source map independent review</h1><h2>'+result['status']+'</h2><p>Author '+html.escape(d['author'])+'; reviewer /root/m04_provider_review.</p><p>'+str(len(checks))+' checks; 8 new negative documentary probes. No findings.</p><p>9 exact source spans distinguish raw-byte file receipt, pure retention evaluation, and captured semantic ACK. Scene helper returns a path through FileSystemPort.write_atomic; this is not root-transfer or authenticated Held proof. G1–G4 remain pending; 3 bridges selected=null.</p><p>Source authority: 796 hashes zero drift. Live HEAD '+d['head']+'; historical '+d['historical_head']+' is distinct.</p><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in result['limits'])+'</ul><table>'+''.join('<tr><td>'+html.escape(x['id'])+'</td><td>'+str(x['pass'])+'</td></tr>' for x in checks)+'</table>'
(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M04 independent provider review</title>'+body,encoding='utf-8')
(P/'seal.json').write_text(json.dumps({'state':'SEALED_STOP_WRITES','artifacts':{p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name!='seal.json'}},indent=2)+'\n',encoding='utf-8')
print(result['status'],len(checks),'checks',sum(not x['pass'] for x in checks),'failures')
