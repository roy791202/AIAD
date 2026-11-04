from pathlib import Path
import json,hashlib,subprocess,html
from model import evaluate
P=Path(__file__).resolve().parent
R=next(x for x in P.parents if (x/'AGENTS.md').exists())
def read(n): return json.loads((P/n).read_text(encoding='utf-8'))
def write(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=[]
for f in read('fixtures.json'):
 r=evaluate(f)
 assert r['outcome']==f['expected'],f['id']
 assert r['snapshot']==f['snapshot'] and r['live_revision']==f['live_revision']
 if 'mismatch' in f['id'] or f['id']=='receipt-empty-transaction': assert r['ack_calls']==0 and r['root_calls']==0
 if f['id']=='file-verified-root-deferred': assert r['file_verified'] and r['ack_calls']==0 and r['pin_state']=='Unverified'
 if f['id']=='saved-newer-live': assert r['formal_revision']==10 and r['formal_semantic']=='sem10' and r['dirty']
 if f['id']=='late-ack-newer-baseline': assert r['formal_revision']==11 and r['formal_semantic']=='sem11'
 if f['id']=='owner-replaced': assert not r['delivered'] and not r['ack_calls']
 rows.append({'id':f['id'],'result':r,'status':'PASS_DOCUMENT_MODEL'})
# Reproducible unsafe legacy shorthand counterexample, not a production defect assertion.
f=next(f for f in read('fixtures.json') if f['id']=='file-verified-root-deferred')
counter={'input':f['id'],'unsafe_receipt_then_ack':{'outcome':'Saved','ack_calls':1},'required_candidate':evaluate(f),'missing_mapping':'Four-field IO receipt has no material root attestation; receipt-only shortcut cannot establish Saved.'}
assert counter['unsafe_receipt_then_ack']['ack_calls']!=counter['required_candidate']['ack_calls']
inputs=read('inputs.json');drift=[x['path'] for x in inputs if hashlib.sha256((R/x['path']).read_bytes()).hexdigest()!=x['sha256']];assert not drift
source=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))
source_drift=[n for n,h in source['source_hashes'].items() if not (R/n).exists() or hashlib.sha256((R/n).read_bytes()).hexdigest()!=h]
assert len(source['source_hashes'])==796 and not source_drift
cx=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M04/planning/cx-revision-v3/module-spec.json').read_text(encoding='utf-8'))
found=[]
def walk(o,p=''):
 if isinstance(o,dict):
  for k,v in o.items(): walk(v,p+'/'+k)
 elif isinstance(o,list):
  for i,v in enumerate(o):walk(v,p+'/'+str(i))
 elif isinstance(o,str) and 'Save: capture' in o:found.append({'pointer':p,'value':o})
walk(cx)
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
e={'status':'PASS_BOUNDED_DOCUMENT_MODEL_ONLY','head':head,'historical_authority_head':source['head'],'authority_product_count':len(source['source_hashes']),'product_drift':source_drift,'input_drift':drift,'new_fixture_witnesses':len(rows),'new_counterexamples':1,'old_suite_reruns':0,'rows':rows,'counterexample':counter,'exact_old_pointers':found,'not_run':['independent review','native UI/IPC','product tests','build/package/install','valid RED/GREEN','full Draft 2020-12 validation'],'owner_gates':'G1-G4 pending; no architecture adoption; parent remains Yellow','next_ready_action':read('module-spec.json')['next_ready_action']}
write('verification.json',e)
s=read('module-spec.json');m=read('mapping.json')
body='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M04 Save handoff precision gap</title><style>body{font:16px system-ui;max-width:1080px;margin:36px auto;background:#101723;color:#e4ecf5}pre{white-space:pre-wrap;background:#1c2838;padding:18px}h1,h2{color:#ffd178}a{color:#9fd4ff}</style><h1>M04 保存回應交接精度缺口</h1><p>Yellow · PROPOSED_PENDING_OWNER · document/model only · NOT_READY_FOR_IMPLEMENTATION</p><p>M04 is sole DocumentOwner; M03 is facade. Verified file commit does not prove material retention or semantic ACK. Owner adoption remains pending.</p>'
for title,v in [('Architecture / ownership / transaction',s['architecture']),('Exact old → new gap',s['delta']),('Request and response mapping (pending owners)',m),('Contracts / model premises',s['premises']),('BDD → TDD document trace',read('trace.json')),('New positive and negative witnesses',e),('Owner gates and next action',{'gates':s['owner_gates'],'next':s['next_ready_action']}),('Pending automation / risks',s['pending_automation'])]:body+='<h2>'+html.escape(title)+'</h2><pre>'+html.escape(json.dumps(v,ensure_ascii=False,indent=2))+'</pre>'
body+='<script type="application/json" id="module-spec">'+json.dumps(s,ensure_ascii=False).replace('<','\u003c')+'</script></html>'
(P/'index.html').write_text(body,encoding='utf-8')
write('artifact-hashes.json',{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted(P.iterdir()) if x.is_file() and x.name!='artifact-hashes.json'})
print(json.dumps({k:e[k] for k in ['status','head','authority_product_count','new_fixture_witnesses','new_counterexamples','product_drift']}))
