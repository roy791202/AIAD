"""Independent document-oracle audit only; not a product preflight implementation/test."""
import json,re,hashlib,subprocess,html
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
O=Path(__file__).parent;P=O.parent;C=P/'preflight-precision-correction'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
inputs={str(p):sha(p) for p in C.iterdir() if p.is_file()}
policy=read(C/'contract-correction.json');cases=read(C/'cases.json');spec=read(C/'module-spec.json');old=read(P/'pure-preflight-design/module-spec.json')
base=read('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
assert all(sha(p)==h for p,h in base['source_hashes'].items())
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==base['head']
assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()==base['branch']
assert all(sha(C/f)==h for f,h in read(C/'artifact-hashes.json').items())
assert sha(P/'pure-preflight-design/module-spec.json')==spec['source_sha256']
assert len(cases)==64 and len({c['id'] for c in cases})==64
# Derive expected results anew from the written policy; do not import/run producer.
def error(field,reason):return {'Err':{'InvalidInput':{'field':field,'reason':reason}}}
def string_error(value,path,limit):
 if value=='':return error(path,'Empty')
 if '\0' in value:return error(path,'ContainsNul')
 if len(value.encode('utf-8'))>limit:return error(path,'TooLongUtf8')
def assess(x):
 r=x['report'];c=x['context']
 for value,path in [(r['source_digest'],'/report/source_digest'),(c['expected_source_digest'],'/context/expected_source_digest')]:
  if not re.fullmatch(r'sha256:[0-9a-f]{64}',value):return error(path,'InvalidDigest')
 for value,path in [(r['target_document_id'],'/report/target_document_id'),(c['target_document_id'],'/context/target_document_id')]:
  e=string_error(value,path,256)
  if e:return e
 for value,path in [(r['target_revision'],'/report/target_revision'),(c['target_revision'],'/context/target_revision')]:
  if type(value)!=int or not 0<=value<=18446744073709551615:return error(path,'InvalidRevision')
 if len(r['blockers'])>256:return error('/report/blockers','TooManyItems')
 for i,b in enumerate(r['blockers']):
  if b['kind'] not in policy['blocker_order']:return error(f'/report/blockers/{i}/kind','InvalidBlockerKind')
  for field,limit in [('subject',1024),('reason',4096)]:
   e=string_error(b[field],f'/report/blockers/{i}/{field}',limit)
   if e:return e
 if len(r['missing_external_dependencies'])>4096:return error('/report/missing_external_dependencies','TooManyItems')
 for i,value in enumerate(r['missing_external_dependencies']):
  e=string_error(value,f'/report/missing_external_dependencies/{i}',256)
  if e:return e
 if x['choice'] not in ['NotConfirmed','ExplicitlyAcceptMissingExternal']:return error('/choice','InvalidChoice')
 if r['blockers']:
  problems=sorted(r['blockers'],key=lambda b:(policy['blocker_order'].index(b['kind']),b['subject'].encode('utf-8'),b['reason'].encode('utf-8')))
  return {'Ok':{'Blocked':{'problems':problems}}}
 if r['source_digest']!=c['expected_source_digest']:return {'Err':'StaleSource'}
 if (r['target_document_id'],r['target_revision'])!=(c['target_document_id'],c['target_revision']):return {'Err':'StaleTarget'}
 if r['requires_other_document_change']:return {'Err':'CrossDocumentChangeRequired'}
 missing=sorted(set(r['missing_external_dependencies']),key=lambda s:s.encode('utf-8'))
 if not missing:return {'Ok':'AllowedComplete'}
 if x['choice']=='NotConfirmed':return {'Ok':{'NeedsDependencyConfirmation':{'missing':missing}}}
 return {'Ok':{'AllowedIncomplete':{'pending_bindings':missing,'dependent_capabilities_blocked':True}}}
results=[]
for c in cases:
 snapshot=json.dumps(c['input'],sort_keys=True,ensure_ascii=False)
 derived=assess(c['input']);results.append({'id':c['id'],'name':c['name'],'status':'PASS' if derived==c['expected'] else 'FAIL','derived':derived,'declared':c['expected']})
 assert snapshot==json.dumps(c['input'],sort_keys=True,ensure_ascii=False)
failures=[r for r in results if r['status']=='FAIL']
assert not failures, failures
byname={c['name']:c for c in cases}
assert len(byname['exact blocker order with duplicates retained']['expected']['Ok']['Blocked']['problems'])==5
assert byname['exact blocker order with duplicates retained']['expected']['Ok']['Blocked']['problems'][1:3]==[{'kind':'Integrity','subject':'a','reason':'a'}]*2
assert spec['envelope']==old['file_envelope_proposed']
assert set(spec['envelope'])==set(old['file_envelope_proposed'])
assert len(spec['envelope']['existing'])+len(spec['envelope']['new'])+len(spec['envelope']['test'])==3
assert read(C/'decoder-only-pending.json')['status']=='OUT_OF_PURE_TYPED_BOUNDARY_NOT_RUN'
assert (C/'module.feature').read_text(encoding='utf-8').count('  Scenario: ')==64
now=datetime.now(timezone.utc).isoformat()
review={'module':'M06','status':'PASS_DOCUMENT_CORRECTION_SCOPE_ONLY','at':now,'scope':'F1-F3 correction proposal document consistency/oracle audit only; not architecture adoption, executable product RED or full M06 PREP acceptance','reviewer':'same assistant in separate read-only review phase; no separately delegated reviewer','findings_closed':[
 {'id':'F1','status':'PASS_DOCUMENT_SCOPE','evidence':'Explicit first-error JSON pointer/reason and all-input-structural-validation precedence; cases 015-021 independently re-derived and matched.'},
 {'id':'F2','status':'PASS_DOCUMENT_SCOPE','evidence':'Six-kind fixed ordinal; byte-order secondary keys; exact duplicate blockers retained, missing IDs deduplicated. Cases 022/023 matched complete expected lists.'},
 {'id':'F3','status':'PASS_DOCUMENT_SCOPE','evidence':'64 full report/context/choice inputs, min/max/max+1 counts/strings, UTF8 256/257, NUL/digest and equal/mismatched u64 max; every declared oracle independently re-derived.'}],
 'verification':{'document_oracles':'64/64 PASS','product_tests':'NOT RUN','compile':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','native':'NOT RUN','build':'NOT RUN','source_files_unchanged':796,'original_proposal_hash':'PASS','correction_artifact_hashes':'PASS','correction_files_read_only':'PASS','three_file_candidate_envelope_unchanged':'PASS','branch':base['branch'],'head':base['head']},
 'limitations':['Document checker is review-local Python, not product behavior or a Skeleton; product entry remains absent/unapproved.','Reserved decoder-only invalid enum/u64-overflow examples are not counted as typed Rust RED.','R1-R4 and proposed whitespace/duplicate/precedence semantics remain pending Owner adoption.','Full M06 archive format/export/restore/single-document apply/rollback/Undo preparation is outside this limited review; parent PREP stays yellow.','Coverage is accepted for this correction, not an exhaustive proof of all combined values or native/container validity.'],
 'next':'F1-F3 document correction closed. Consolidate current R1-R4 precise proposal for one Owner adoption; do not request product implementation permission or create Skeleton before architecture adoption. Continue other unblocked preparation.'}
put('review.json',review);put('case-results.json',results);put('reviewed-input-hashes.json',inputs)
body='<h1>M06 F1～F3 精確補正：文件複驗</h1><p>PASS_DOCUMENT_CORRECTION_SCOPE_ONLY</p><p>同一助理以另輪唯讀程序審查；未另委派獨立 reviewer。未執行補正產生器，未修改被驗收提案。</p><h2>結論</h2><ul>'+''.join('<li><b>'+x['id']+'</b> '+html.escape(x['evidence'])+'</li>' for x in review['findings_closed'])+'</ul><h2>64 組完整 fixture／oracle</h2><p>另寫文件審查用 oracle checker，依書面契約重新推導結果，逐組完整比較，64/64 一致；輸入未被修改。</p><table>'+''.join('<tr><td>'+r['id']+'</td><td>'+html.escape(r['name'])+'</td><td>'+r['status']+'</td></tr>' for r in results)+'</table><h2>範圍與證據</h2><p>原提案與補正包 hash 保持不變；796 檔產品來源、branch、HEAD 核對一致。候選 envelope 仍為原三檔。所有產品測試、compile、RED、GREEN、build、native 均 NOT RUN。</p><h2>保留界線</h2><ul>'+''.join('<li>'+html.escape(x)+'</li>' for x in review['limitations'])+'</ul><p>M06 父準備卡維持黃燈、不填 doneAt。F1～F3 文件修正結案，不代表 R1～R4 已採納或模組完成。</p>'
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M06 correction document acceptance</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6}td{border:1px solid #ccc;padding:7px}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(review,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
assert all(sha(f)==h for f,h in inputs.items())
from tools.board.board_core.snapshot_safe import split_snapshot,mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
B=Path('docs/PROJECT-BOARD.html');bp=split_snapshot(B.read_text(encoding='utf-8'));before=json.loads(bp[1])
state=read(P/'current-state.json');state['state']=review['status'];state['report']='preflight-document-reacceptance/index.html';state['correction_report']='preflight-precision-correction/index.html';state['next_step']=review['next'];state['f1_f3']='CLOSED_DOCUMENT_SCOPE_ONLY';(P/'current-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def mutate(s):
 t=next(t for t in s['tasks'] if t['id']=='PD-P1-M06-PREP-01');t['preflightCorrectionAcceptance']={'status':review['status'],'report':str(O/'index.html').replace('\\','/'),'at':now,'document_oracles_pass':64};t['remainingGap']='F1-F3 document correction accepted; R1-R4 exact architecture adoption and full archive/merge preparation remain separate. No product/Skeleton authorization from this review.';t['nextStep']=review['next'];t['notes']=t.get('notes','')+'\n['+now+'] F1-F3 independent document reacceptance PASS scope only, 64/64 separately derived oracle matches. Same assistant separate read-only phase; no delegated reviewer. Correction/source unchanged; product tests/RED/build/native NOT RUN. '+str(O/'index.html').replace('\\','/')
mutate_snapshot_file(B,mutate,lock_factory=FileLock)
ap=split_snapshot(B.read_text(encoding='utf-8'));after=json.loads(ap[1]);assert bp[0]==ap[0] and bp[2]==ap[2];assert {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'};assert [t for t in before['tasks'] if t['id']!='PD-P1-M06-PREP-01']==[t for t in after['tasks'] if t['id']!='PD-P1-M06-PREP-01'];assert all(sha(p)==h for p,h in base['source_hashes'].items());assert all(sha(f)==h for f,h in inputs.items())
put('board-evidence.json',{'before':dict(Counter(t['zone'] for t in before['tasks'])),'after':dict(Counter(t['zone'] for t in after['tasks'])),'other_cards_root_shell_preserved':True});put('artifact-hashes.json',{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({'status':review['status'],'oracles':len(results),'counts':dict(Counter(t['zone'] for t in after['tasks']))}))
