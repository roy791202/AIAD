import json,hashlib,copy,html,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7];OUT=Path(__file__).resolve().parent;ORIG=OUT.parent/'provider-source-map-20261104'
H=lambda b:hashlib.sha256(b).hexdigest()
def write(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
rows=json.loads((ORIG/'source-spans.json').read_text(encoding='utf-8'))
anchors={'RS01':['pub struct CapturedAttempt','pub attempt_id','pub captured_fingerprint','pub asset_manifest_digest'],'RS02':['Published','Failed','Complete','attempt_id'],'RS03':['Published is a trusted HOST receipt','pub fn transition_recovery'],'RS04':['checked_sub(state.last_check_ms)','elapsed < 60000','RecoveryAction::RequestCapture'],'RS05':['.filter(|c| &c.attempt_id == attempt_id)','CompletionOutcome::Published','next.successful_fingerprint','RecoveryAction::BaselineAdvanced'],'RS06':['fn validate_capture','validate_id("attempt_id"','validate_fingerprint("captured_fingerprint"','validate_fingerprint("asset_manifest_digest"'],'DE01':['pub fn capture','self.state.content.clone()'],'DE02':['pub fn acknowledge_formal_save','self.state.formal_baseline =','pub fn acknowledge_recovery_save','self.state.snapshot_baseline ='],'DE03':['fn check_ack','captured.0 > self.state.content_revision.0','captured.0 < saved.revision.0'],'IO01':['pub struct CommitReceipt','pub transaction_id','pub target','pub committed_digest']}
# Exact corrective ranges, not inferred from stale authored spans.
bounds={'RS04':(115,145),'RS05':(157,174),'RS06':(212,216)}
for r in rows:
 if r['id'] in bounds:r['start'],r['end']=bounds[r['id']]
 l=(ROOT/r['path']).read_text(encoding='utf-8').splitlines();r['text']='\n'.join(l[r['start']-1:r['end']]);r['required_anchors']=anchors[r['id']]
write('source-spans.json',rows)
code=r"""import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
ANCHORS=ANCHOR_LITERAL
def validate(rows):
 if len(rows)!=10 or {x['id'] for x in rows}!=set(ANCHORS):raise ValueError('exact ten span IDs required')
 for r in rows:
  p=ROOT/r['path'];raw=p.read_bytes();lines=raw.decode('utf-8').splitlines();a,b=r['start'],r['end']
  if not isinstance(a,int) or not isinstance(b,int) or not 1<=a<=b<=len(lines):raise ValueError('invalid/out-of-range span '+r['id'])
  text='\n'.join(lines[a-1:b])
  if not text.strip():raise ValueError('empty span '+r['id'])
  if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('source hash mismatch '+r['id'])
  if text!=r['text']:raise ValueError('source span text mismatch '+r['id'])
  if r.get('required_anchors')!=ANCHORS[r['id']] or any(x not in text for x in ANCHORS[r['id']]):raise ValueError('semantic anchors missing '+r['id'])
 return True
if __name__=='__main__':
 try:
  validate(json.loads(Path(sys.argv[1] if len(sys.argv)>1 else OUT/'source-spans.json').read_text(encoding='utf-8')))
  print('PASS_EXACT_STATIC_SOURCE_BINDINGS')
 except (ValueError,KeyError,TypeError,OSError) as e:print('FAIL '+str(e));sys.exit(1)
""".replace('ANCHOR_LITERAL',repr(anchors))
(OUT/'validate.py').write_text(code,encoding='utf-8')
import importlib.util
sp=importlib.util.spec_from_file_location('v',OUT/'validate.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
probes=[]
def probe(name,rs,expected):
 try:actual=v.validate(rs)
 except (ValueError,KeyError,TypeError,OSError):actual=False
 probes.append(dict(id=name,expected_accept=expected,actual_accept=actual,passed=actual==expected))
probe('corrected_exact_sources',rows,True)
for name,rid,change in [('old_empty_RS06','RS06',lambda r:r.update(start=236,end=240,text='')),('old_wrong_RS05','RS05',lambda r:r.update(start=171,end=192,text='\n'.join((ROOT/r['path']).read_text().splitlines()[170:192]))),('empty_text','RS01',lambda r:r.update(text='')),('out_of_range','DE01',lambda r:r.update(end=999999)),('missing_anchor','RS05',lambda r:r.update(required_anchors=[])),('wrong_hash','IO01',lambda r:r.update(sha256='0'*64)),('wrong_text','DE02',lambda r:r.update(text=r['text']+'x'))]:
 rs=copy.deepcopy(rows);change(next(x for x in rs if x['id']==rid));probe(name,rs,False)
rs=copy.deepcopy(rows);rs.pop();probe('missing_span',rs,False)
auth=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))['source_hashes'];drift=[p for p,h in auth.items() if not (ROOT/p).exists() or H((ROOT/p).read_bytes())!=h]
spec=json.loads((ORIG/'module-spec.json').read_text(encoding='utf-8'));spec['author']='/root/yellow_m07_provider';spec['status']='CORRECTED_STATIC_PROVIDER_MAP_PENDING_INDEPENDENT_REVIEW';spec['correction']={'finding':'RS06 empty out-of-range, RS05 omitted Published branch; additionally RS04 expanded to cover elapsed threshold','corrected_ranges':bounds,'original_preserved':True,'validation':'Fixed semantic anchors, nonempty exact in-range source text/hash, exact ten IDs; rejects malformed bounds/text/hash/anchor set','trust_boundary':'Static documentary correspondence only, not code behavior or runtime/native proof'}
write('module-spec.json',spec);write('results.json',dict(layer='NEW_CORRECTION_DOCUMENT_CHECKS',probes=probes,passed=sum(p['passed'] for p in probes),failed=sum(not p['passed'] for p in probes),authority_count=len(auth),authority_drift=drift))
originalseal=json.loads((ORIG/'seal.json').read_text(encoding='utf-8'));unchanged=all(H((ORIG/n).read_bytes())==h for n,h in originalseal['files'].items());write('original-preservation.json',dict(original_seal_sha256=H((ORIG/'seal.json').read_bytes()),all_original_sealed_hashes_unchanged=unchanged))
body='<h1>M07 精確來源片段補正</h1><p>原封存包保留；RS06 改為212–216，RS05 改為157–174，RS04 擴為115–145。修正空片段與語意證據未涵蓋，未更改產品或待決選項。</p><p>產品/native/歷史PASS重跑：NOT RUN。MP1–4 selected=null。</p>'+''.join('<h2>'+r['id']+' '+str(r['start'])+'–'+str(r['end'])+'</h2><p>'+html.escape(r['meaning'])+'</p><pre>'+html.escape(r['text'])+'</pre>' for r in rows)+'<h2>新拒絕檢查</h2><pre>'+html.escape(json.dumps(probes,ensure_ascii=False,indent=2))+'</pre>'
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M07 source correction</title><style>body{font:16px system-ui;max-width:1050px;margin:40px auto}pre{white-space:pre-wrap;background:#eee;padding:15px}</style>'+body,encoding='utf-8')
assert all(p['passed'] for p in probes) and len(auth)==796 and not drift and unchanged
write('seal.json',dict(author=spec['author'],status='SEALED_AUTHOR_CORRECTION',files={p.name:H(p.read_bytes()) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}));print('SEALED correction',len(probes),'new probes pass')
