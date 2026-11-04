import json,hashlib,subprocess,copy,html
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from tools.board.board_core.snapshot_safe import split_snapshot,mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
O=Path(__file__).parent;P=O.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
baseline=load('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');assert all(sha(p)==h for p,h in baseline['source_hashes'].items());assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==baseline['head'];assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()==baseline['branch']
original=load(P/'pure-preflight-design/module-spec.json');review=load(P/'preflight-document-review/review.json');now=datetime.now(timezone.utc).isoformat();B=Path('docs/PROJECT-BOARD.html');bp=split_snapshot(B.read_text(encoding='utf-8'));before=json.loads(bp[1])
base={'report':{'source_digest':'sha256:'+'a'*64,'target_document_id':'doc-A','target_revision':0,'blockers':[],'missing_external_dependencies':[],'requires_other_document_change':False},'context':{'expected_source_digest':'sha256:'+'a'*64,'target_document_id':'doc-A','target_revision':0},'choice':'NotConfirmed'}
order=['UnsupportedFormat','UnsupportedVersion','Integrity','MissingInternalPayload','UnsafePath','AmbiguousEntry']
policy={'status':'PROPOSED_PENDING_OWNER_NOT_APPROVED','error_contract':{'InvalidInput':{'field':'RFC6901 JSON pointer, rooted at /report, /context or /choice; indices decimal zero-based','reason':['Empty','ContainsNul','TooLongUtf8','TooManyItems','InvalidDigest','InvalidRevision','InvalidChoice','InvalidBlockerKind']},'StaleSource':'unit','StaleTarget':'unit','CrossDocumentChangeRequired':'unit'},'validation_order':['/report/source_digest','/context/expected_source_digest','/report/target_document_id','/context/target_document_id','/report/target_revision','/context/target_revision','/report/blockers count','each /report/blockers/i: kind, subject, reason in ascending index','/report/missing_external_dependencies count','each missing ID ascending index','/choice'],
 'string_validation':'No trim/normalization. Check Empty -> ContainsNul -> TooLongUtf8. Whitespace-only nonempty IDs/diagnostics remain literal data in this pure slice; HOST must apply authoritative identity rules. UTF-8 bytes, not scalar count. Digest syntax exact sha256:+64 lowercase hexadecimal; any mismatch InvalidDigest.',
 'semantic_precedence':['after ALL structural input validation, nonempty blockers -> Blocked before freshness or cross-document checks','no blockers: source digest mismatch -> StaleSource','then target ID or revision mismatch -> StaleTarget','then requires_other_document_change -> CrossDocumentChangeRequired','then empty missing list -> AllowedComplete regardless of choice','then NotConfirmed -> NeedsDependencyConfirmation','then ExplicitlyAcceptMissingExternal -> AllowedIncomplete with dependent_capabilities_blocked=true'],
 'blocker_order':order,'blocker_duplicate_policy':'Keep identical blockers, including exact duplicates. Sort stable by kind ordinal then subject UTF-8 bytes then reason UTF-8 bytes; every supplied valid reason remains represented. Missing dependency IDs alone sort/deduplicate by UTF-8 bytes. No locale sorting/casefold.',
 'typed_boundary':'Actual Rust report/context revisions are u64 and enum values are closed. InvalidRevision/InvalidChoice/InvalidBlockerKind are reserved future decoding oracle errors, NOT constructible L0 Rust values. No serde/decoder added to this slice. Do not count impossible enum/out-of-range construction as executable domain RED.',
 'bounds':original['limits_proposed_not_confirmed'],'authority':'Clarifies unapproved M06-R1-R4 proposal; not adopted product behavior. Full archive/schema/extract/Undo remains separate.'}
cases=[]
def add(name,mutations,expected,category='boundary'):
 data=copy.deepcopy(base)
 for path,value in mutations:
  parts=path.strip('/').split('/');d=data
  for k in parts[:-1]:d=d[int(k)] if isinstance(d,list) else d[k]
  if isinstance(d,list):d[int(parts[-1])]=value
  else:d[parts[-1]]=value
 cases.append({'id':f'M06-PC-{len(cases)+1:03d}','name':name,'category':category,'input':data,'expected':expected,'status':'PLANNED_NOT_RUN'})
def err(path,reason):return {'Err':{'InvalidInput':{'field':path,'reason':reason}}}
def blocker(kind='Integrity',subject='entry-a',reason='checksum mismatch'):return {'kind':kind,'subject':subject,'reason':reason}
add('valid complete',[],{'Ok':'AllowedComplete'},'success')
for kind in order:add(kind+' cannot be accepted away',[('/report/blockers',[blocker(kind)]),('/report/missing_external_dependencies',['dep-z']),('/choice','ExplicitlyAcceptMissingExternal')],{'Ok':{'Blocked':{'problems':[blocker(kind)]}}},'hard-block')
add('missing without confirmation',[('/report/missing_external_dependencies',['dep-z','dep-a','dep-z'])],{'Ok':{'NeedsDependencyConfirmation':{'missing':['dep-a','dep-z']}}},'choice')
add('explicit missing acceptance',[('/report/missing_external_dependencies',['dep-z','dep-a','dep-z']),('/choice','ExplicitlyAcceptMissingExternal')],{'Ok':{'AllowedIncomplete':{'pending_bindings':['dep-a','dep-z'],'dependent_capabilities_blocked':True}}},'choice')
add('accepted choice does not invent incomplete',[('/choice','ExplicitlyAcceptMissingExternal')],{'Ok':'AllowedComplete'},'choice')
add('stale source',[('/context/expected_source_digest','sha256:'+'b'*64)],{'Err':'StaleSource'},'freshness')
add('target ID mismatch',[('/context/target_document_id','doc-B')],{'Err':'StaleTarget'},'freshness')
add('target revision mismatch',[('/context/target_revision',1)],{'Err':'StaleTarget'},'freshness')
add('cross-document change',[('/report/requires_other_document_change',True)],{'Err':'CrossDocumentChangeRequired'},'cross-module')
add('blocker before stale source',[('/report/blockers',[blocker()]),('/context/expected_source_digest','sha256:'+'b'*64)],{'Ok':{'Blocked':{'problems':[blocker()]}}},'precedence')
add('malformed blocker before stale source',[('/report/blockers',[blocker(subject='')]),('/context/expected_source_digest','sha256:'+'b'*64)],err('/report/blockers/0/subject','Empty'),'precedence')
add('invalid digest before blocker',[('/report/source_digest','SHA256:'+'a'*64),('/report/blockers',[blocker()])],err('/report/source_digest','InvalidDigest'),'precedence')
add('invalid missing ID before blocker',[('/report/blockers',[blocker()]),('/report/missing_external_dependencies',[''])],err('/report/missing_external_dependencies/0','Empty'),'precedence')
add('source before stale target and cross',[('/context/expected_source_digest','sha256:'+'b'*64),('/context/target_revision',1),('/report/requires_other_document_change',True)],{'Err':'StaleSource'},'precedence')
add('target before cross',[('/context/target_revision',1),('/report/requires_other_document_change',True)],{'Err':'StaleTarget'},'precedence')
add('cross before missing acceptance',[('/report/requires_other_document_change',True),('/report/missing_external_dependencies',['dep-a']),('/choice','ExplicitlyAcceptMissingExternal')],{'Err':'CrossDocumentChangeRequired'},'precedence')
bs=[blocker('UnsafePath','z','r'),blocker('Integrity','a','z'),blocker('Integrity','a','a'),blocker('Integrity','a','a'),blocker('UnsupportedFormat','b','r')]
expected=[bs[4],bs[2],bs[3],bs[1],bs[0]]
add('exact blocker order with duplicates retained',[('/report/blockers',bs)],{'Ok':{'Blocked':{'problems':expected}}},'ordering')
add('missing UTF8 byte order',[('/report/missing_external_dependencies',['é','a','Z','a'])],{'Ok':{'NeedsDependencyConfirmation':{'missing':['Z','a','é']}}},'ordering')
for path,maximum,seed in [('/report/target_document_id',256,'x'),('/context/target_document_id',256,'x')]:
 for size in [0,1,maximum,maximum+1]:
  value=seed*size;expected=err(path,'Empty') if size==0 else err(path,'TooLongUtf8') if size>maximum else {'Ok':'AllowedComplete'}
  mut=[(path,value)]
  if size>0 and size<=maximum:mut=[('/report/target_document_id',value),('/context/target_document_id',value)]
  add(path+' bytes '+str(size),mut,expected)
 add(path+' NUL',[(path,'x\0')],err(path,'ContainsNul'))
for field,maximum in [('subject',1024),('reason',4096)]:
 for size in [0,1,maximum,maximum+1]:
  v=blocker();v[field]='x'*size
  expected=err('/report/blockers/0/'+field,'Empty') if size==0 else err('/report/blockers/0/'+field,'TooLongUtf8') if size>maximum else {'Ok':{'Blocked':{'problems':[v]}}}
  add(field+' bytes '+str(size),[('/report/blockers',[v])],expected)
 v=blocker();v[field]='\0';add(field+' NUL',[('/report/blockers',[v])],err('/report/blockers/0/'+field,'ContainsNul'))
for size in [0,1,256,257]:
 add('missing ID bytes '+str(size),[('/report/missing_external_dependencies',['x'*size])],err('/report/missing_external_dependencies/0','Empty') if size==0 else err('/report/missing_external_dependencies/0','TooLongUtf8') if size>256 else {'Ok':{'NeedsDependencyConfirmation':{'missing':['x'*size]}}})
add('missing ID NUL',[('/report/missing_external_dependencies',['x\0'])],err('/report/missing_external_dependencies/0','ContainsNul'))
for text,expect in [('é'*128,{'Ok':'AllowedComplete'}),('é'*128+'x',err('/report/target_document_id','TooLongUtf8'))]:add('multibyte ID '+str(len(text.encode('utf-8'))),[('/report/target_document_id',text),('/context/target_document_id',text)],expect)
for n in [256,257]:add('blocker count '+str(n),[('/report/blockers',[blocker() for _ in range(n)])],{'Ok':{'Blocked':{'problems':[blocker() for _ in range(n)]}}} if n==256 else err('/report/blockers','TooManyItems'))
for n in [4096,4097]:add('missing count '+str(n),[('/report/missing_external_dependencies',['dep-a']*n)],{'Ok':{'NeedsDependencyConfirmation':{'missing':['dep-a']}}} if n==4096 else err('/report/missing_external_dependencies','TooManyItems'))
for path in ['/report/source_digest','/context/expected_source_digest']:
 for v in ['', 'sha256:'+'A'*64,'sha256:'+'a'*63,'sha256:'+'a'*65]:add('digest '+path+' length '+str(len(v)),[(path,v)],err(path,'InvalidDigest'))
add('u64 max valid equal',[('/report/target_revision',18446744073709551615),('/context/target_revision',18446744073709551615)],{'Ok':'AllowedComplete'})
add('u64 max mismatch',[('/report/target_revision',18446744073709551615),('/context/target_revision',0)],{'Err':'StaleTarget'})
put('base-fixture.json',base);put('contract-correction.json',policy);put('cases.json',cases)
put('decoder-only-pending.json',{'status':'OUT_OF_PURE_TYPED_BOUNDARY_NOT_RUN','cases':[{'input':'target_revision=18446744073709551616','expected':'InvalidInput InvalidRevision at matching report/context path'},{'input':'choice=unknown','expected':'InvalidInput InvalidChoice /choice'},{'input':'blocker kind=unknown','expected':'InvalidInput InvalidBlockerKind /report/blockers/0/kind'}],'warning':'These require a future approved decoder; never add serde solely to exercise impossible Rust enum/u64 values.'})
spec={'module':'M06','slice':'pure preflight precision proposal','status':'CORRECTION_PROPOSAL_DELIVERED_PENDING_DOCUMENT_REACCEPTANCE','at':now,'addresses':['F1','F2','F3'],'source_review':'../preflight-document-review/review.json','historical_proposal':'../pure-preflight-design/module-spec.json','source_sha256':sha(P/'pure-preflight-design/module-spec.json'),'contract':policy,'case_count':len(cases),'decisions':['M06-R1 normalized trusted report/no mutation','M06-R2 hard-block and explicit incomplete semantics including proposed exact precedence','M06-R3 source/target freshness and single-document guard','M06-R4 input bounds, blocker duplicate retention/sort order and original three-file envelope'],'architecture':original['architecture'],'envelope':original['file_envelope_proposed'],'approval':'All corrections remain proposed; no test or product Skeleton. Does not self-close full M06 PREP or claim reacceptance PASS.','results':{'product_tests':'NOT RUN','RED':'NOT RUN','build':'NOT RUN','native':'NOT RUN','source_unchanged':796},'next':'Read-only document reacceptance of F1-F3 fixture/oracle coverage; then consolidate R1-R4 Owner adoption. Other M06 archive/merge scope remains separately planned.'}
put('module-spec.json',spec)
feature='Feature: M06 pure import preflight\n  Background:\n    Given validation report and target context are immutable input values\n'
for c in cases:feature+='\n  Scenario: '+c['id']+' '+c['name']+'\n    Given the complete fixture '+c['id']+' from cases.json\n    When import preflight is evaluated\n    Then result equals its exact recorded oracle\n    And source and target values remain unchanged\n'
(O/'module.feature').write_text(feature,encoding='utf-8')
body='<h1>M06 Preflight F1～F3 精確補正提案</h1><p>補正交付待文件複驗；不是驗收 PASS，也未批准 R1～R4。</p><h2>意圖／架構</h2><pre>'+html.escape(original['architecture']['hexagonal']+'\n'+original['architecture']['dependencies'])+'</pre><p>'+html.escape(original['architecture']['ownership'])+'</p><h2>精確差額補齊</h2><p>F1：完整結構檢查先於語意，明列 error reason／JSON pointer／多錯誤優先序。F2：列出六種 ordinal；建議保留重複 blocker，僅 missing IDs 去重。F3：完整 base/context/choice 與逐案例完整輸入，UTF-8 bytes、NUL、count 與 u64 邊界。</p><h2>語意優先序</h2><ol>'+''.join('<li>'+html.escape(x)+'</li>' for x in policy['semantic_precedence'])+'</ol><p>'+html.escape(policy['typed_boundary'])+'</p><h2>BDD／TDD</h2><p>'+str(len(cases))+' 組完整 fixture/oracle，全部 PLANNED／NOT RUN。<a href="cases.json">完整資料</a>，<a href="contract-correction.json">精確契約</a>。</p><table>'+''.join('<tr><td>'+c['id']+'</td><td>'+html.escape(c['name'])+'</td><td>'+html.escape(json.dumps(c['expected'],ensure_ascii=False)[:180])+'</td></tr>' for c in cases)+'</table><h2>Envelope／驗證／下一步</h2><p>候選仍僅 WORK lib.rs、merge_plan.rs、phase1_import_preflight.rs 三檔；未建立任何 code/test Skeleton。文件只寫本模組 planning 與自身卡證據。796 檔產品來源／branch／HEAD 未變，runtime/native/build/RED 均 NOT RUN。先文件複驗，再一次確認 R1～R4；M06 整張 PREP 維持黃燈。</p>'
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M06 precision correction</title><style>body{max-width:1100px;margin:40px auto;font:16px system-ui;line-height:1.6}pre{white-space:pre-wrap}td{border:1px solid #ccc;padding:7px}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(spec,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
assert len({c['id'] for c in cases})==len(cases);assert len(('é'*128).encode())==256;assert len(('é'*128+'x').encode())==257
for f in O.glob('*.json'):load(f)
put('verification.json',{'status':'STATIC_DOCUMENT_CHECKS_ONLY','checks':['JSON parse','unique case IDs','UTF8 boundary arithmetic','full fixture per case','original proposal preserved'],'case_count':len(cases),'source_unchanged':796,'product_tests':'NOT RUN','build':'NOT RUN','native':'NOT RUN','review_acceptance':'PENDING'})
state=load(P/'current-state.json');state.update({'state':spec['status'],'report':'preflight-precision-correction/index.html','next_step':spec['next'],'product_source_inventory':'../../M01/planning/s2-green/source-current.json'});(P/'current-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def mutate(s):
 t=next(t for t in s['tasks'] if t['id']=='PD-P1-M06-PREP-01');t['preflightPrecisionCorrection']={'status':spec['status'],'report':str(O/'index.html').replace('\\','/'),'cases':len(cases),'at':now};t['nextStep']=spec['next'];t['remainingGap']='F1-F3 precision correction delivered pending document reacceptance and R1-R4 adoption; complete archive/merge preparation remains separate.';t['notes']=t.get('notes','')+'\n['+now+'] M06 F1-F3 proposed correction: exact validation/semantic precedence, blocker ordering/duplicate retention and '+str(len(cases))+' full fixtures/oracles. Product unchanged; not reacceptance PASS. '+str(O/'index.html').replace('\\','/')
mutate_snapshot_file(B,mutate,lock_factory=FileLock)
ap=split_snapshot(B.read_text(encoding='utf-8'));after=json.loads(ap[1]);assert bp[0]==ap[0] and bp[2]==ap[2];assert {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'};assert [t for t in before['tasks'] if t['id']!='PD-P1-M06-PREP-01']==[t for t in after['tasks'] if t['id']!='PD-P1-M06-PREP-01'];assert all(sha(f)==h for f,h in baseline['source_hashes'].items())
put('board-evidence.json',{'before':dict(Counter(t['zone'] for t in before['tasks'])),'after':dict(Counter(t['zone'] for t in after['tasks'])),'other_cards_root_shell_preserved':True});put('artifact-hashes.json',{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({'cases':len(cases),'counts':dict(Counter(t['zone'] for t in after['tasks']))}))
