import pathlib,json,hashlib,re,html,subprocess,collections
from datetime import datetime,timezone,timedelta
from tools.board.board_core.snapshot_safe import load_snapshot_dict,mutate_snapshot_file,shell_halves
from tools.board.board_core.json_store import FileLock
ROOT=pathlib.Path.cwd();P=pathlib.Path(__file__).resolve().parent;PLAN=P.parent/'planning'/'exact-design'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
base=read(P/'source-baseline.json');head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
assert head==base['head'] and branch==base['branch']
lib='apps/sgenaxis-desktop/crates/sgenaxis-work/src/lib.rs';domain='apps/sgenaxis-desktop/crates/sgenaxis-work/src/generation_plan.rs';test='apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_generation_plan.rs'
allowed={lib,domain,test}
drift=[r['path'] for r in base['source_files'] if not (ROOT/r['path']).is_file() or sha(ROOT/r['path'])!=r['sha256']]
assert set(drift)=={lib},drift
assert (P/'lib-before.rs.txt').read_bytes().replace(b'pub mod document_edit;',b'pub mod document_edit;\npub mod generation_plan;')==(ROOT/lib).read_bytes() or (P/'lib-before.rs.txt').read_text(encoding='utf-8').replace('pub mod document_edit;','pub mod document_edit;\npub mod generation_plan;')==(ROOT/lib).read_text(encoding='utf-8')
code=(ROOT/domain).read_text(encoding='utf-8');tests=(ROOT/test).read_text(encoding='utf-8')
assert code.count('unimplemented!')==2
assert all(x not in code for x in ['std::fs','std::env','std::time','serde','sgenaxis_spec','sgenaxis_adapters'])
assert '#[ignore]' not in tests and '#[should_panic]' not in tests
assert len(re.findall(r'^pub fn ',code,re.M))==2
red=(P/'red.txt').read_text(encoding='utf-8');compilelog=(P/'compile.txt').read_text(encoding='utf-8');reg=(P/'regression.txt').read_text(encoding='utf-8');adj=(P/'adjacent.txt').read_text(encoding='utf-8');commands=read(P/'commands.json')
assert {r['name']:r['exit_code'] for r in commands}=={'compile':0,'red':101,'regression':0,'adjacent':0}
assert '2 passed; 65 failed; 0 ignored' in red
assert red.count('M02_S1_SKELETON_NOT_IMPLEMENTED:')==65
names=re.findall(r'^test (m02_\S+) \.\.\. FAILED$',red,re.M);assert len(names)==65 and len(set(names))==65
groups={f'M02-T{i:02}':[n for n in names if n.startswith(f'm02_t{i:02}_')] for i in range(1,11)};assert all(groups.values())
rows=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',reg);assert sum(int(r[0]) for r in rows)==73 and all(r[1:] == ('0','0') for r in rows)
assert '9 passed; 0 failed; 0 ignored' in adj
now=datetime.now(timezone(timedelta(hours=8))).isoformat()
adoption={'module':'M02','revision':'M02-EXACT-CB-v1','adopted':['M02-DX'+str(i) for i in range(1,8)],'authority':'Owner explicitly adopted DX1-DX7 and authorized M02-S1 Skeleton + valid RED only; no product behavior implementation.','recorded_at':now,'approved_artifact_hashes':{str(x.relative_to(ROOT)) if x.is_absolute() else str(x):sha(x) for x in [PLAN/'module-spec.json',PLAN/'envelope.json',PLAN/'test-plan.json',*sorted((PLAN/'schemas').glob('*.json'))]},'historical_pending_labels':'Superseded by this adoption ledger; original proposal remains unchanged for traceability.','scope':sorted(allowed),'future':'S2-S4 and GREEN require their separate gates; no automatic product authorization.'}
write('adoption.json',adoption)
source_hashes={p:sha(ROOT/p) for p in sorted(allowed)}
result={'module':'M02','slice':'M02-S1','state':'SKELETON_VALID_RED_DELIVERED_PENDING_INDEPENDENT_ACCEPTANCE','date':now,'branch':branch,'head':head,'dirty_worktree':'Pre-existing; no commit/push/release','scope':source_hashes,
 'architecture':'Approved C policy boundary materialized. Eight approved model roles plus the ArtifactProduct discriminant needed by ArtifactIntent. No new Port/adapter/service/dependency/SSOT/transaction/runtime wiring.',
 'contract':'Only immutable M01 input values. HOST remains approval authenticator. SaveDefinitionOnly is an action value, never actual save. Both function bodies stop at explicit unimplemented marker.',
 'compile':{'status':'PASS','exit_code':0},'RED':{'status':'VALID_RED','behavior_cases':65,'failed_at_missing_body_marker':65,'fixture_checks_passed':2,'ignored':0,'exit_code':101,'reason':'All target behavior failures occur at approved unimplemented policy boundaries, not compile/setup/environment. Exit 101 is expected for this stage, not GREEN.'},
 'regression':{'WORK_existing':'PASS: 73 tests across library + all five pre-existing integration targets','HOST_adjacent_project_new':'PASS: 9 tests, 75 unrelated host tests filtered; not full HOST regression','full_system':'NOT RUN'},
 'scope_review':{'baseline_files':len(base['source_files']),'preexisting_changed_only':[lib],'other_baseline_files_unchanged':len(base['source_files'])-1,'lib_delta':'one public module declaration','new_files':[domain,test],'cargo_manifests_lockfiles_ports_host_ui_changed':False,'domain_no_infrastructure':'PASS static inspection','unimplemented_bodies':2},
 'traceability':groups,'commands':commands,
 'remaining':['Independent acceptance NOT RUN','No product generation behavior implemented; GREEN not attempted','S2 codecs/render/HOST, S3 native version publishing and S4 UI/consumer not started','No build/package/native IO/real approval evidence verification claimed'],
 'acceptance':{'Skeleton reflects approved public model and function boundaries':'PASS','New target compiles':'PASS','65 actual behavioral RED failures classified':'PASS','Fixture assumptions checked separately':'PASS (2)','Existing WORK and selected adjacent regression':'PASS','Approved file scope preserved':'PASS','Independent acceptance':'NOT RUN'},
 'module_complete':False,'product_implementation':'NOT IMPLEMENTED'}
write('verification.json',result)
plans=read(PLAN/'test-plan.json')['cases'];selected=[r for r in plans if r['slice']=='M02-S1']
feature=['@M02_S1 @approved_DX1_DX7','Feature: Pure generation planning','  Background:','    Given an author has a local project definition and a verified template selection','  Rule: Planning preserves the definition and generates no files','']
business={1:('Complete approved definition','the required project decisions and approvals are complete','the author prepares a generation plan','the plan contains program and UI design artifact intents'),2:('Incomplete definition','required decisions are missing','the author prepares a generation plan','the missing decisions are listed in a stable unique order without generation'),3:('Approval required','approval names exist but approval has not been verified','the author prepares a generation plan','the plan cannot authorize generation'),4:('Exact selection binding','the selected template identity or version differs from the prepared selection','the author prepares a generation plan','the mismatch is reported without a plan'),5:('Supported targets only','the selected delivery target is unsupported','the author prepares a generation plan','unsupported target is reported without silently changing the selection'),6:('Safe unique artifact paths','an artifact path escapes the allowed grammar or conflicts with another','the author prepares a generation plan','the invalid or conflicting path is rejected'),7:('Stale plan','a binding value has changed since a plan was prepared','the author checks that plan','the changed binding field is reported'),8:('Bounded artifacts','an artifact list or path is at an approved boundary','the author prepares a generation plan','the exact limits and both required products are enforced'),9:('Stable identity','project identity or unique target identifiers are invalid','the author prepares a generation plan','the invalid identity is rejected without guessing by name'),10:('Deterministic plan','the same immutable definition and verified selection are available','the author prepares the plan repeatedly','the same ordered plan is returned without modifying the inputs')}
for i,(name,g,w,t) in business.items():feature+=['    @M02-T'+str(i).zfill(2),'    Scenario: '+name,'      Given '+g,'      When '+w,'      Then '+t,'']
(P/'module.feature').write_text('\n'.join(feature),encoding='utf-8')
write('test-traceability.json',{'approved_rows':selected,'executable_cases':groups,'fixture_tests':['fixture_complete_definition_satisfies_existing_m01_preconditions','fixture_boundary_vectors_have_the_declared_lengths_and_products'],'note':'Future S2-S4 rows M02-T11..T34 are not covered by S1 and remain NOT RUN.'})
def render(v):
 if isinstance(v,dict):return '<dl>'+''.join('<dt>'+html.escape(str(k))+'</dt><dd>'+render(x)+'</dd>' for k,x in v.items())+'</dl>'
 if isinstance(v,list):return '<ul>'+''.join('<li>'+render(x)+'</li>' for x in v)+'</ul>'
 return html.escape(str(v))
page='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M02-S1 Skeleton / valid RED</title><style>body{font:16px/1.6 system-ui;max-width:1120px;padding:28px;margin:auto;color:#1d3344;background:#edf2f6}section,header{background:white;padding:24px;margin:18px 0}dt{font-weight:650;margin-top:16px}dd{margin-left:18px}li{margin:8px 0}pre{white-space:pre-wrap;background:#183244;color:white;padding:20px}a{color:#066d98}.red{border-left:6px solid #bc4237;padding:14px;background:#fff0ed}</style><header><h1>M02-S1 Skeleton + \u6709\u6548 RED</h1><p>DX1\uff5eDX7 \u5df2\u63a1\u7d0d\u3002\u672c\u8f2a\u50c5\u4ea4\u4ed8 C \u7d14\u8a08\u756b\u9aa8\u67b6\u8207\u6e2c\u8a66\uff0c\u4e0d\u5be6\u4f5c\u7522\u54c1\u529f\u80fd\u3002</p><p class="red">Compile PASS | 65 valid behavioral RED | 2 fixture checks PASS | 73 WORK + 9 selected HOST regressions PASS | Independent acceptance NOT RUN</p><a href="../planning/exact-design/index.html">Approved design (historical proposal labels)</a> | <a href="adoption.json">Current approval ledger</a> | <a href="module.feature">BDD</a> | <a href="test-traceability.json">Traceability</a> | <a href="compile.txt">Compile</a> | <a href="red.txt">RED</a> | <a href="regression.txt">WORK regression</a> | <a href="adjacent.txt">Adjacent HOST</a></header><section><h2>Architecture and ownership</h2><pre>Driving tests -> WORK prepare_generation / validate_plan_binding\n                          |\n                          v\n               Immutable M01 values + approved C DTOs\n\nHOST (future) authenticates approval and byte digests.\nNo WORK -> filesystem / OS / codec / concrete adapter.\nDefinition remains M01 SSOT; GenerationPlan is derived.\nNo transaction/persistence/publication introduced by this slice.</pre><p>Only lib.rs module declaration and two approved new source/test files changed. Public function bodies remain explicitly unimplemented. Candidate data does not grant approval or write authority.</p></section><section><h2>Evidence and remaining scope</h2>'+render(result)+'</section><section><h2>Approved BDD to executable tests</h2>'+render(groups)+'</section><script type="application/json" id="module-spec">'+json.dumps({'adoption':adoption,'verification':result},ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(page,encoding='utf-8')
assert all((P/x).exists() for x in re.findall('href="([^"]+)"',page))
board=ROOT/'docs/PROJECT-BOARD.html';before=board.read_text(encoding='utf-8');old=load_snapshot_dict(before);ids={'PD-P1-M02-PREP-01','PD-P1-G04-DEC-01'}
def mutate(d):
 for t in d['tasks']:
  if t['id'] not in ids:continue
  note='[Owner adopted M02 DX1-DX7; M02-S1 Skeleton/valid RED delivered] Compile PASS; 65 intended RED at missing behavior bodies; 2 fixture checks PASS; WORK 73 and selected HOST 9 regression PASS. Only three approved product/test paths changed, no product behavior implemented. Independent acceptance NOT RUN. Evidence: docs/requirements-confirmation/phase1-spec/tasks/M02/s1/index.html. '
  if t['id']=='PD-P1-M02-PREP-01':note+='Keep module PREP yellow; S1 is not full M02 module completion. '
  else:note+='Only M02 precision adopted; M03 preview/media matrix still pending, keep red. '
  t['note']=note+'\n--- original trace retained ---\n'+t.get('note','')
  t['m02ExactDesign']={'direction':'C+B_ADOPTED','status':'DX1_DX7_ADOPTED','adoption':'docs/requirements-confirmation/phase1-spec/tasks/M02/s1/adoption.json','updatedAt':now}
  t['m02S1']={'status':result['state'],'report':'docs/requirements-confirmation/phase1-spec/tasks/M02/s1/index.html','behavior_RED':65,'fixture_PASS':2,'independent_acceptance':'NOT RUN','product_behavior':'NOT IMPLEMENTED'}
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
after=board.read_text(encoding='utf-8');new=load_snapshot_dict(after)
assert shell_halves(before)==shell_halves(after)
assert {k:v for k,v in old.items() if k!='tasks'}=={k:v for k,v in new.items() if k!='tasks'}
assert [x for x in old['tasks'] if x['id'] not in ids]==[x for x in new['tasks'] if x['id'] not in ids]
counts=lambda d:dict(collections.Counter(x['zone'] for x in d['tasks']))
assert counts(old)==counts(new)
write('delivery-evidence.json',{'before':counts(old),'after':counts(new),'board_shell_and_other_cards_preserved':True,'source_hashes':source_hashes,'scope_review':result['scope_review'],'review':'Self-check only, independent acceptance NOT RUN','scheduler':'aiad-10 ACTIVE every 10 minutes, prompt updated via automation_update for DX1-DX7 adoption and RED-only constraint'})
(P.parent/'planning'/'current-state.json').write_text(json.dumps({'direction':'C+B_ADOPTED','exact_design':'DX1_DX7_ADOPTED','adoption':'../s1/adoption.json','current_stage':result['state'],'report':'../s1/index.html','product_implementation_authorized':False},indent=2),encoding='utf-8')
print(json.dumps({'state':result['state'],'RED':65,'fixtures':2,'WORK_regression':73,'HOST_adjacent':9,'counts':counts(new)}))
