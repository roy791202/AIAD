import copy, hashlib, html, json, subprocess
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
C=OUT.parent/'dispatch-next-actions-20261103'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=load(C/'action-matrix.json'); bindings=load(C/'source-hashes.json')['sources']; board=load(ROOT/'docs/board.json')
rows=a['yellow']+a['gray_red']; live={x['id']:x for x in board['items']}
checks=[]
def check(name,value,detail=None):
 checks.append({'name':name,'pass':bool(value),'detail':detail}); assert value,name
check('211 bound sources',len(bindings)==211)
drift=[p for p,h in bindings.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
check('Only live board changed after seal',drift==['docs/board.json'],drift)
for n,h in load(C/'seal.json')['files'].items(): check('candidate seal '+n,sha(C/n)==h)
authority=load(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes']
check('796 product sources unchanged',len(authority)==796 and all((ROOT/p).exists() and sha(ROOT/p)==h for p,h in authority.items()))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
check('Live HEAD distinct from historical inventory',head==a['live_head']=='5b709343a890503ebbe24a802e43cda5647df124' and head!=a['historical_inventory_head'])
check('31 current card identities/lights retained',len(rows)==31 and len({r['id'] for r in rows})==31 and all(live[r['id']]['light']==r['live_light'] for r in rows))
check('8 Yellow /18 Gray /5 Red',sum(r['live_light']=='Yellow' for r in rows)==8 and sum(r['live_light']=='Gray' for r in rows)==18 and sum(r['live_light']=='Red' for r in rows)==5)
check('All original actions and missing conditions retained',all(r.get('next_concrete_action') and r.get('exact_missing_gate') for r in a['yellow']) and all(r.get('next_action') and r.get('missing_condition') for r in a['gray_red']))
check('Six superseded cards remain suppressed',sum(r['classification']=='SUPERSEDED_NOT_REDISPATCH' for r in a['gray_red'])==6)
for r in rows:
 p=ROOT/r['original_source'].split('#')[0]; original=load(p)
 if p.name!='board.json':
  check(r['id']+' original dependencies',r['dependencies']==original['dependencies'])
  check(r['id']+' original acceptance',r.get('original_acceptance',r.get('acceptance'))==original['acceptance'])
for f in a['feature_evidence']:
 check(f['feature']+' latest trace and review consumed',bool(f['consumed_payloads']) and any('review' in p['path'] for p in f['consumed_payloads']) and all(sha(ROOT/p['path'])==p['sha256'] for p in f['consumed_payloads']))
 # Read actual evidence, not only its path or author checker result.
 for p in f['consumed_payloads']: load(ROOT/p['path'])
m=load(C/'next-m08-task.json'); g=load(C/'next-g01-task.json')
for packet,card in [(m,'PD-P1-M08-VERIFY-01'),(g,'PD-P1-G01-DEC-01')]:
 original=load(ROOT/packet['original_scope_source']); prefix=original['allowed_files'][0].replace('\\','/').removesuffix('**')
 check(card+' strict original file subset',all(p.startswith(prefix) for p in packet['allowed_files']))
 check(card+' distinct author/verifier',packet['role_separation']['author']!=packet['role_separation']['verifier'])
check('M08 all 24 cases named', 'A01..A08/N01..N16' in ' '.join(m['steps']))
check('G01 canonical deliverables unchanged',set(load(ROOT/g['original_scope_source'])['deliverables'])<=set(Path(p).name for p in g['allowed_files']))
check('G01 still absent; proposal not adoption',not (ROOT/'docs/requirements-confirmation/phase1-spec/tasks/decisions/G01').exists() and 'approval=null' in ' '.join(g['steps']))
def semantics(model,mp,gp):
 if any(r['product_ready'] for r in model['yellow']+model['gray_red']): return False
 if any(f['native_result']!='NOT RUN' for f in model['feature_evidence']): return False
 if any(p.startswith(('apps/','tests/')) for p in mp['allowed_files']+gp['allowed_files']): return False
 if 'not satisfied native dependencies' not in mp['dependency_semantics']: return False
 if 'approval=null' not in ' '.join(gp['steps']): return False
 if gp['role_separation']['author']==gp['role_separation']['verifier']: return False
 return all(r['classification']=='SUPERSEDED_NOT_REDISPATCH' for r in model['gray_red'] if '-ESS-' in r['id'])
check('Independent semantic baseline',semantics(a,m,g))
mutations=[]
for name in ['product-pass','native-pass','scope-escape','dependency-waiver','auto-adopt','self-verify','superseded-revive']:
 aa,mm,gg=copy.deepcopy(a),copy.deepcopy(m),copy.deepcopy(g)
 if name=='product-pass': aa['yellow'][0]['product_ready']=True
 if name=='native-pass': aa['feature_evidence'][0]['native_result']='PASS'
 if name=='scope-escape': mm['allowed_files'].append('tests/test_p1_portable_acceptance.py')
 if name=='dependency-waiver': mm['dependency_semantics']='document traces satisfy native dependencies'
 if name=='auto-adopt': gg['steps']=[s.replace('approval=null','approval=true') for s in gg['steps']]
 if name=='self-verify': gg['role_separation']['verifier']=gg['role_separation']['author']
 if name=='superseded-revive': aa['gray_red'][0]['classification']='DISPATCHABLE'
 rejected=not semantics(aa,mm,gg); check('Negative semantic mutation '+name,rejected); mutations.append({'mutation':name,'rejected':rejected})
# Reconstruct prior board bytes in memory only; never write authoritative board.
old=copy.deepcopy(board); item=next(x for x in old['items'] if x['id']=='PD-P1-M01-PREP-01'); appended=item['notes'].pop(); item['updatedAt']=item['notes'][-1]['at']; old['updatedAt']=a['board_snapshot_at']
target=bindings['docs/board.json']; matched=[]
for ascii_mode in [True,False]:
 for newline in ['\n','\r\n']:
  raw=(json.dumps(old,ensure_ascii=ascii_mode,indent=2)+'\n').replace('\n',newline).encode('utf8')
  if hashlib.sha256(raw).hexdigest()==target: matched.append({'ensure_ascii':ascii_mode,'newline':repr(newline)})
check('Exact prior board hash recovered by reversing only appended M01 note and two timestamps',bool(matched),matched)
result={'verdict':'PASS_DOCUMENT_DISPATCH_PREPARATION_ONLY','reviewer':'/root/dispatch_next_action_review','author':a['author'],'generated_at':datetime.now(timezone.utc).isoformat(),'checks':checks,'negative_probes':mutations,'board_drift':{'classification':'EXPECTED_COORDINATOR_APPEND_ONLY','fields':['root.updatedAt','M01.updatedAt','M01.notes append'],'appended_note':appended,'prior_hash':target,'current_hash':sha(ROOT/'docs/board.json'),'exact_reconstruction':matched},'heartbeat_context':{'candidate_creation_instruction':a['owner_heartbeat_context']['timestamp'],'review_instruction':'2026-11-03T11:27:04.369Z','meaning':'Original-scope preparation proceeds; envelope adoption remains gated. No retroactive candidate timestamp rewrite.'},'not_run':['Owner adoption','product RED/GREEN','native verification','build/package/install','release'],'findings':[]}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
(OUT/'findings.json').write_text(json.dumps({'blocking_findings':[],'scope':'Document dispatch readiness only','limitations':result['not_run']},indent=2)+'\n',encoding='utf8')
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Independent dispatch preparation review</title><h1>PASS — 文件派工準備</h1><p>作者與審查者獨立。8 Yellow、18 Gray、5 Red維持；6 superseded不重派。M08只盤點輸入，G01只產製三份canonical提案；Owner採納、產品及Native驗收未執行。</p><p>211來源：210完全相同，board僅協調者追加M01備註與兩個時間戳；反向重建精確吻合原SHA。796產品來源無漂移。</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf8')
(OUT/'seal.json').write_text(json.dumps({'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}},indent=2)+'\n',encoding='utf8')
print(json.dumps({'verdict':result['verdict'],'checks':len(checks),'negative_probes':len(mutations),'board_exact_reconstruction':matched}))
