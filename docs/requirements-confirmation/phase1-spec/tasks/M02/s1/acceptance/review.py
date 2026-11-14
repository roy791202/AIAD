import pathlib,json,hashlib,re,subprocess,html,collections
from datetime import datetime,timezone,timedelta
from tools.board.board_core.snapshot_safe import load_snapshot_dict,mutate_snapshot_file,shell_halves
from tools.board.board_core.json_store import FileLock
ROOT=pathlib.Path.cwd();P=pathlib.Path(__file__).resolve().parent;S1=P.parent;DESIGN=S1.parent/'planning'/'exact-design'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,d):(P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base=read(S1/'source-baseline.json');delivery=read(S1/'verification.json');adoption=read(S1/'adoption.json');spec=read(DESIGN/'module-spec.json');runs=read(P/'commands.json')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip();assert head==base['head'] and branch==base['branch']
for p,h in adoption['approved_artifact_hashes'].items():assert sha(ROOT/p)==h
for p,h in delivery['scope'].items():assert sha(ROOT/p)==h
drift=[r['path'] for r in base['source_files']if not (ROOT/r['path']).exists() or sha(ROOT/r['path'])!=r['sha256']]
lib='apps/sgenaxis-desktop/crates/sgenaxis-work/src/lib.rs';assert drift==[lib]
before=(S1/'lib-before.rs.txt').read_text(encoding='utf-8');assert before.replace('pub mod document_edit;','pub mod document_edit;\npub mod generation_plan;')==(ROOT/lib).read_text(encoding='utf-8')
visible=subprocess.check_output(['rg','--files','apps/sgenaxis-desktop'],text=True).splitlines();known={r['path'] for r in base['source_files']};new=sorted(x.replace('\\','/')for x in visible if x.replace('\\','/')not in known)
assert set(new)==set(adoption['scope'])-{lib}
source=(ROOT/new[0]).read_text(encoding='utf-8');testpath=next(x for x in new if '/tests/'in x);test=(ROOT/testpath).read_text(encoding='utf-8');domainpath=next(x for x in new if '/src/'in x);source=(ROOT/domainpath).read_text(encoding='utf-8')
assert source.count('unimplemented!')==2 and len(re.findall(r'^pub fn ',source,re.M))==2
assert all(x not in source for x in ['std::fs','std::env','std::time','serde','sgenaxis_spec','sgenaxis_adapters'])
assert '#[ignore]' not in test and '#[should_panic]'not in test
assert {r['suite']:r['exit_code'] for r in runs}=={'compile':0,'red':101,'work-regression':0,'host-adjacent':0}
red=(P/'red.txt').read_text(encoding='utf-8');assert '2 passed; 65 failed; 0 ignored' in red and red.count('M02_S1_SKELETON_NOT_IMPLEMENTED:')==65
names=re.findall(r'^test (m02_\S+) \.\.\. FAILED$',red,re.M);assert len(names)==65
reg=(P/'work-regression.txt').read_text(encoding='utf-8');summaries=re.findall(r'test result: ok\. (\d+) passed; (\d+) failed; (\d+) ignored',reg);assert sum(int(x[0])for x in summaries)==73 and all(x[1:]==('0','0')for x in summaries)
assert '9 passed; 0 failed; 0 ignored' in (P/'host-adjacent.txt').read_text(encoding='utf-8')
def line(fragment):return next(i for i,l in enumerate(test.splitlines(),1)if fragment in l)
counterexample=['topology'];generic_pass=bool(counterexample) and all(a<b for a,b in zip(counterexample,counterexample[1:]))
assert generic_pass
findings=[
 {'id':'M02-S1-F1','priority':'P2','severity':'major','category':'missing tests / contract oracle','location':testpath,'line':line('fn missing('),'related_lines':[line('macro_rules! save_only'),line('missing(&d, &t, &c);'),line('m02_t03_unverified_approval_is_not_authority')],
 'approved_contract':'DX1 pure_C_contract.order/requirements requires the actual missing completeness, requirement and approval decisions to be reported, sorted and deduplicated. M02-T02/T03 explicitly require missing decision/approval explanation.',
 'observed':'missing() checks only nonempty + sorted unique. save_only! discards returned fields. Except one topology scenario, no assertion binds the missing list to the deliberately missing field or verifies that confirmed fields are not falsely reported.',
 'counterexample':'A missing-decision response containing only [topology] satisfies the helper for missing acceptance, tentative requirements, empty toolchain and absent verified approval even when topology is confirmed. This is an assertion-logic counterexample, not an executed product mutation.',
 'impact':'A future implementation may pass these cases while reporting incorrect decisions; the 65-marker RED count cannot establish a complete behavioral oracle.',
 'required_correction':'Strengthen existing cases to assert each approved missing cause (and combined sorted/deduplicated completeness), including approval-specific reason. Preserve all existing cases and behavioral intent. Record field-path spelling using existing M01 FieldPath vocabulary; do not invent approval authentication in WORK.',
 'acceptance_blocker':True},
 {'id':'M02-S1-F2','priority':'P2','severity':'major','category':'missing tests / validation precedence','location':testpath,'line':line('macro_rules! reject'),
 'approved_contract':'DX1 pure_C_contract.order: invalid identity/duplicate IDs/invalid template or path are rejected before incomplete decisions become SaveDefinitionOnly.',
 'observed':'All malformed-path/identity/duplicate rejection fixtures retain complete decisions and valid approval context. All save-only fixtures retain valid structure. There is no mixed invalid-structure + missing-decision case.',
 'counterexample':'A future policy that returns SaveDefinitionOnly immediately whenever approval/topology is missing, without validating malicious artifact paths or duplicate identities, is not rejected by these existing 65 cases.',
 'required_correction':'Add mixed cases for unsafe artifact path + missing approval, invalid project identity + missing topology, and duplicate target identity + incomplete requirement. Assert the existing typed structural rejection takes precedence; no IO or new error variant required.',
 'acceptance_blocker':True}]
dx=[{'id':'DX1','verdict':'PARTIAL / CHANGES_REQUIRED','basis':'Public models and two signatures match; F1/F2 weaken behavioral test constraints.'},
 {'id':'DX2','verdict':'PASS_SCOPE_ONLY','basis':'Immutable version layout is approved but intentionally not implemented in S1; no directory/pointer mutation.'},
 {'id':'DX3','verdict':'PASS_SCOPE_ONLY','basis':'No generation-store Port or native read/writer implementation added. Future S3 remains out of scope.'},
 {'id':'DX4','verdict':'PARTIAL_FOR_S1','basis':'Typed inputs, path/digest/count boundary tests are present; validation precedence F2 missing. Four JSON codecs remain future S2, not falsely claimed tested.'},
 {'id':'DX5','verdict':'PASS_SCOPE_ONLY','basis':'Immutable borrowed inputs and no IO preserve S1 no-write boundary. Runtime activation/cancel/rollback NOT RUN by design.'},
 {'id':'DX6','verdict':'PASS_SCOPE_ONLY','basis':'Compatible target data is represented. Two-artifact pure fixture exercises approved min-count boundaries; it is not claimed to be the shipped 14-file template.'},
 {'id':'DX7','verdict':'PASS_SCOPE','basis':'Exactly three product/test paths changed; only Skeleton/RED. No S2-S4, no dependencies or implementation bodies.'}]
report={'module':'M02','slice':'M02-S1','reviewed_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'review_mode':'Independent acceptance procedure against locked approved artifacts and fresh test runs. Same assistant in a later read-only review turn; no separately delegated reviewer. Prior delivery verdict was not used as the acceptance verdict.',
 'verdict':'CHANGES_REQUIRED_TEST_CONTRACT_COVERAGE','stage_acceptance':'NOT PASS','valid_RED':'CONFIRMED: 65 intended failures at missing behavior boundaries','fixture_checks':'2 PASS','regression':'WORK 73 PASS; selected HOST project_new 9 PASS (75 unrelated tests filtered)','branch':branch,'head':head,
 'scope':{'approved_product_test_paths':adoption['scope'],'actual_existing_delta':[lib],'actual_new_files':new,'preexisting_lib_delta':'one module declaration','other_baseline_files_unchanged':785,'source_hashes':delivery['scope'],'product_or_test_changes_this_review':0,'manifests_lockfiles_ports_host_UI_unchanged':True},
 'DX1_DX7':dx,'findings':findings,
 'quality_dimensions':{'correctness':'Skeleton shape matches approved C; behavior deliberately absent. F1 prevents complete future correctness proof.','boundary':'Count/path boundaries present, but F2 validation-order combinations absent.','error_handling':'Approved typed errors materialized; no success/error fallback implementation. Missing-decision error oracle needs F1.','complexity':'No manager/service/global/cache added; DTO + two body seams only.','coupling':'Only existing M01 types imported; no FS/OS/framework/codec dependency.'},
 'design_smells':'No blocking structural smell found; do not opportunistically refactor the approved Skeleton.',
 'suggested_refactors':'None. Required work is test-oracle strengthening and additional contract cases, not architectural refactoring or product implementation.',
 'risk':{'runtime':'NOT IMPLEMENTED; do not release or wire up the panicking Skeleton. This is expected for RED-only scope.','maintenance':'Medium until F1/F2 corrected: test counts could hide inaccurate missing decisions or wrong validation order.','input_safety':'Future structural precedence must be constrained before implementation; no actual import/write behavior exists here.'},
 'tests_and_logs':runs,'not_run':['Product GREEN','Full system regression','Native publication/IO','Template build/package','Separate-agent review'],
 'next':'Correct F1/F2 within a specifically authorized test/documentation scope, rerun compile/all intended RED/fixture guards and regressions, then reaccept. No architecture change or new owner decision about DX1-DX7 is requested.',
 'module_complete':False,'board_action':'Keep yellow; no doneAt or stage green.'}
write('review.json',report)
write('correction-plan.json',{'authority':'Recommendation only; this acceptance turn does not modify product or test files','existing_test_path':testpath,'protected':['generation_plan.rs body behavior','all other product source/tests','approved contracts/BDD/error variants','all dependencies and manifests'],'F1':'Strengthen missing()/save_only expectations per missing cause without deleting/weakening the existing 65 cases. Field aliases require consistency with existing M01 vocabulary.','F2':['unsafe path + missing approval','invalid identity + missing topology','duplicate target + unresolved requirement'],'expected_gate':'Existing 65 remain intended RED; added cases increase the count (at least 68). Compile and fixture guards must pass; all actual RED failures must remain missing approved behavior. No GREEN implementation.'})
def render(v):
 if isinstance(v,dict):return '<dl>'+''.join('<dt>'+html.escape(str(k))+'</dt><dd>'+render(x)+'</dd>'for k,x in v.items())+'</dl>'
 if isinstance(v,list):return '<ul>'+''.join('<li>'+render(x)+'</li>'for x in v)+'</ul>'
 return html.escape(str(v))
page='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M02-S1 acceptance: changes required</title><style>body{font:16px/1.65 system-ui;max-width:1150px;margin:30px auto;padding:24px;color:#193143;background:#eef3f6}section,header{background:white;padding:24px;margin:18px 0}dt{font-weight:650;margin-top:18px}dd{margin-left:18px}li{margin:8px 0}.warn{border-left:6px solid #bb7331;padding:18px;background:#fff3dc}a{color:#006e91}</style><header><h1>M02-S1 \u7368\u7acb\u9a57\u6536\u7d50\u679c</h1><p class="warn">\u9a57\u6536\u5c1a\u672a\u901a\u904e\uff1a2 \u9805\u6e2c\u8a66\u5951\u7d04\u7f3a\u53e3\u3002\u65b0\u8f2a\u91cd\u73fe 65 \u9805\u6709\u6548 RED\uff0c2 \u9805 fixture \u8207 82 \u9805\u65e2\u6709\uff0f\u76f8\u9130\u56de\u6b78\u901a\u904e\u3002\u67b6\u69cb\u8207\u4e09\u6a94\u7bc4\u570d\u76f8\u7b26\uff1b\u672c\u8f2a\u672a\u4fee\u6539\u7522\u54c1\u6216\u6e2c\u8a66\u3002</p><p>Read-only acceptance turn by the same assistant; no separately delegated reviewer. Stage and module remain incomplete.</p><a href="review.json">Structured review</a> | <a href="correction-plan.json">F1/F2 correction plan</a> | <a href="../index.html">Original delivery</a> | <a href="compile.txt">Compile</a> | <a href="red.txt">Fresh RED</a> | <a href="work-regression.txt">WORK</a> | <a href="host-adjacent.txt">HOST</a></header><section><h2>Findings</h2>'+render(findings)+'</section><section><h2>Contract, architecture, scope and evidence</h2>'+render(report)+'</section><script type="application/json" id="module-spec">'+json.dumps(report,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(page,encoding='utf-8');assert all((P/x).exists()for x in re.findall('href="([^"]+)"',page))
board=ROOT/'docs/PROJECT-BOARD.html';before=board.read_text(encoding='utf-8');old=load_snapshot_dict(before);own='PD-P1-M02-PREP-01'
def mutate(d):
 t=next(x for x in d['tasks']if x['id']==own);t['note']='[M02-S1 acceptance: CHANGES_REQUIRED] Fresh compile PASS; 65 valid RED + 2 fixture PASS; WORK73/HOST9 PASS; approved three-file scope and architecture conform. Blocking test gaps F1: missing decisions not bound to actual cause; F2: structural-invalid + incomplete-decision precedence cases absent. No product/test changes by reviewer. Keep yellow; no doneAt or full-module completion. Evidence: docs/requirements-confirmation/phase1-spec/tasks/M02/s1/acceptance/index.html\n--- original trace ---\n'+t.get('note','');t['m02S1']['status']=report['verdict'];t['m02S1']['acceptance']={'verdict':'CHANGES_REQUIRED','report':'docs/requirements-confirmation/phase1-spec/tasks/M02/s1/acceptance/index.html','findings':['M02-S1-F1','M02-S1-F2'],'date':report['reviewed_at']};t['m02S1']['independent_acceptance']='CHANGES_REQUIRED (separate read-only procedure; same assistant)'
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
after=board.read_text(encoding='utf-8');newboard=load_snapshot_dict(after)
assert shell_halves(before)==shell_halves(after);assert [x for x in old['tasks']if x['id']!=own]==[x for x in newboard['tasks']if x['id']!=own];assert {k:v for k,v in old.items()if k!='tasks'}=={k:v for k,v in newboard.items()if k!='tasks'}
counts=lambda d:dict(collections.Counter(x['zone']for x in d['tasks']));assert counts(old)==counts(newboard)
for p,h in delivery['scope'].items():assert sha(ROOT/p)==h
write('delivery-evidence.json',{'before':counts(old),'after':counts(newboard),'other_cards_metadata_shell_preserved':True,'product_and_test_hashes_unchanged_by_review':True,'verdict':report['verdict'],'JSON_HTML_links':'PASS static'})
print(json.dumps({'verdict':report['verdict'],'findings':2,'counts':counts(newboard)}))
