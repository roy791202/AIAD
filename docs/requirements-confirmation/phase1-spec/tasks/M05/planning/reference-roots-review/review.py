import pathlib,json,hashlib,subprocess,html,collections
from datetime import datetime,timezone
from tools.board.board_core.snapshot_safe import load_snapshot_dict,mutate_snapshot_file,shell_halves
from tools.board.board_core.json_store import FileLock
ROOT=pathlib.Path.cwd(); P=pathlib.Path(__file__).resolve().parent; OLD=P.parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def write(n,d): (P/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
baseline=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/exact-design/authorization-and-baseline.json')
assert head==baseline['head'] and branch==baseline['branch']
assert all(hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in baseline['source_files'])
inv=read(OLD/'inventory.json'); drift=[]
for r in inv['files']:
 path=ROOT/r['path']
 if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=r['sha256']: drift.append(r['path'])
plan=read(OLD/'test-plan.json'); env=read(OLD/'envelope.json')
rows=[
 ('R01','active document','candidate referenced by the current document','retain with document reason','B1/B6'),
 ('R02','other document','candidate referenced only by another project document','retain; current-document scan is insufficient','B6/B10'),
 ('R03','Undo history','candidate absent from live document but retained in Undo','retain until owning history explicitly releases it','B8/B10'),
 ('R04','Redo history','undo moves candidate into redo-only reachability','retain; do not treat Undo as permanent disposal','B8/B12'),
 ('R05','recovery snapshot','candidate referenced by a retained recovery version','retain even after formal save or Undo','B6/B10'),
 ('R06','unprocessed snapshot','snapshot is unresolved and retention threshold exceeded','retain; numeric retention defaults do not authorize deletion','B2/B8'),
 ('R07','in-flight transaction','candidate staged for import or single-document merge','retain while transaction ownership exists','B5/B7'),
 ('R08','unknown provider','root provider unavailable or schema unsupported','retain with root-incomplete warning','B3/B4'),
 ('R09','empty versus missing','complete root set is empty versus a provider omitted','only complete empty set permits eligibility; omitted provider retains','B2/B3'),
 ('R10','stale evaluation','reference revision changes after cleanup preview','reject stale evaluation; recollect before destructive action','B6/B7'),
 ('R11','owned orphan','this transaction created a verified orphan and every root is complete','eligible for later authorized cleanup; planning itself deletes nothing','B1/B7'),
 ('R12','shared material','candidate has another logical or physical owner','retain; no deleting shared bytes after Undo','B6/B10'),
 ('R13','identity mismatch','same asset id points to an unresolved differing version','retain and surface conflict; no name guessing','B3/B11'),
 ('R14','catalog corruption','catalog cannot prove content identity or path ownership','retain and report integrity failure','B3/B9'),
 ('R15','replacement failure','new bytes staged but document commit fails','old references and old bytes preserved; classify new owned orphan','B5/B9'),
 ('R16','deletion failure','an eligible file cannot be removed','report retained cleanup debt; no false success or dropped catalog entry','B4/B9'),
 ('R17','restart','session history closes but retained snapshot remains','release history root only; snapshot root remains','B8/B11'),
 ('R18','single-document boundary','cleanup would require changing another document','do not mutate it; retain asset and report dependency','B7/B10')]
cases=[{'id':'M05-ROOT-'+i,'fixture':{'root_condition':g,'case':name},'given':g,'when':'evaluate cleanup for a named immutable asset version','then':t,'coverage':b,'result':'PLANNED_NOT_RUN','valid_red':'Only after approved Skeleton: target compiles, fixture setup succeeds and intended public-boundary assertion fails for missing behavior. No compile/setup failure counts.'} for i,name,g,t,b in rows]
report={
 'module':'M05','task':'PD-P1-M05-PREP-01','state':'PREPARATION_GAPS_IDENTIFIED_NOT_IMPLEMENTATION_READY','generated_at':datetime.now(timezone.utc).isoformat(),'head':head,'branch':branch,
 'authority':'Read-only source audit plus own planning deliverables/board note. User-provided AGENTS rules apply; repository-root AGENTS.md was absent. No product changes.',
 'confirmed_baseline':['Single-document merge plus necessary asset/reference changes only','Undo cannot delete material still used elsewhere','Recovery contains necessary unsaved assets','Formal save retains recovery versions until an approved retention policy cleans them','M02 C+B pending precision does not block this independent M05 preparation review'],
 'current_source_evidence':{'old_inventory_hash_drift':drift,'fresh_baseline_files_verified':len(baseline['source_files']),'filesystem_port':'Seven generic methods. No reference-root completeness, lease, revision fence or catalog transaction contract. Presence of remove_file does not authorize GC.','old_test_plan_cases':len(plan['cases']),'old_envelope':'11 candidate files are listed, but exact new types, output port and transaction seam are not approved.'},
 'findings':[
 {'id':'GAP-M05-01','severity':'P0','finding':'Unknown roots must be distinguished from a complete empty reference set. Existing three test rows do not encode all root providers or completeness.','disposition':'Add explicit conservative root evaluation plan; do not implement deletion.'},
 {'id':'GAP-M05-02','severity':'P1','finding':'Reference scan then remove_file has an unprotected time-of-check/time-of-use window. Generic FS API is not proof of safe physical deletion.','disposition':'Require approved root snapshot revision/fence and exclusive cleanup transaction capability before a physical cleanup slice.'},
 {'id':'GAP-M05-03','severity':'P1','finding':'Old B1-B12 rows all say Applicable but do not map to executable per-category cases; source-file targets alone do not establish module coverage.','disposition':'18 proposed cases below map all twelve categories; target/fixtures are still not created.'},
 {'id':'GAP-M05-04','severity':'P2','finding':'Old source inventory has drifted where listed. It cannot be reused as current acceptance evidence.','disposition':'Fresh source hashes verified against current 786-file baseline; preserve old report as historical.'}],
 'architecture_proposal':{
 'hexagonal_view':'UI/Test -> Input port -> HOST collect/evaluate -> WORK pure eligibility policy; HOST -> explicit root-provider and mutation capabilities <- owning modules/adapters.',
 'dependency_view':'M04 history projection + all document owners + M07 retained snapshots + in-flight transaction owner -> immutable completeness/revision projection -> M05 evaluator. M05 must not mutate providers.',
 'state_ownership':'Documents own references; M04 owns history; M07 owns recovery index; transaction owner owns temporary claims; M05 owns immutable asset identity/catalog only. Collected roots are derived projections, not an independent SSOT.',
 'mutation_boundary':'Evaluation is read-only. Later physical cleanup requires separately approved application transaction, complete root set and freshness fence. No direct UI-to-FS.',
 'transaction_boundary':'Collect complete roots -> evaluate bound candidate -> preview -> revalidate under approved exclusion -> delete only eligible owned bytes -> update catalog consistently. Missing seam means REPLAN_REQUIRED, not best-effort deletion.',
 'candidate_first_slice':'Pure evaluator only: immutable candidate identity/ownership plus root observations -> Retain(reasons), Ineligible(reason) or EligibleForCleanup. Eligibility is not deletion authority. No persistence/OS/clock/new output Port in this first slice.',
 'protected':'No product file or executable test may be changed by this review. Existing M05 envelope remains proposed, not silently expanded.'},
 'candidate_scope_for_future_confirmation':{'existing':['apps/sgenaxis-desktop/crates/sgenaxis-work/src/lib.rs'],'new':['apps/sgenaxis-desktop/crates/sgenaxis-work/src/asset_reference.rs'],'test':['apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_asset_roots.rs'],'status':'PROPOSED_NOT_APPROVED; exact signatures and input bounds still required before Skeleton','future_command':'cargo test -p sgenaxis-work --test phase1_asset_roots (cwd apps/sgenaxis-desktop; target NOT CREATED)'},
 'cases':cases,
 'acceptance_for_preparation':['All root types and unknown/completeness distinctions explicitly represented','BDD/TDD coverage maps B1-B12, with fixture conditions and valid-RED criteria','Current branch/HEAD/source evidence checked; stale source claims classified','Exact-signature, provider lifecycle and native deletion seam gaps remain visible; no readiness or module-completion claim'],
 'consolidated_next_design_work':['Freeze pure evaluator types, bounded input model and deterministic reason ordering for one future design review','Specify root-provider completeness/revision and history/snapshot release lifecycle with M04/M07 owners','Propose cleanup fence/transaction Port and durable catalog semantics separately; no destructive cleanup until approved','Keep format/media codec matrix outside this root-evaluator slice; G04 preview/media decision remains separate'],
 'verification':{'source_changes_this_round':0,'product_tests':'NOT RUN','RED':'NOT RUN','build_runtime':'NOT RUN','independent_acceptance':'NOT RUN','json_static':'PASS'},
 'owner_request_now':'None: this review identifies preparation work, not a new urgent owner decision. Consolidate exact proposals after further module preparation.'}
write('module-review.json',report)
write('test-plan.json',{'module':'M05','status':'PROPOSED_NOT_RUN','cases':cases,'levels':['pure policy','module contract through fake root providers','real adapter transaction later','M04/M07 adjacent regression'],'note':'These are planning records, not executable fixtures or valid RED.'})
feature=['@proposal_only','Feature: Referenced materials survive cleanup','  Background:','    Given a local project contains immutable material versions','  Rule: Cleanup cannot destroy retained work','']
for c in cases: feature+=['    @'+c['id'],'    Scenario: '+c['id'],'      Given '+c['given'],'      When '+c['when'],'      Then '+c['then'],'']
(P/'module.feature').write_text('\n'.join(feature),encoding='utf-8')
def render(v):
 if isinstance(v,dict):return '<dl>'+''.join('<dt>'+html.escape(k)+'</dt><dd>'+render(x)+'</dd>' for k,x in v.items())+'</dl>'
 if isinstance(v,list):return '<ul>'+''.join('<li>'+render(x)+'</li>' for x in v)+'</ul>'
 return html.escape(str(v))
page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M05 reference-root preparation review</title><style>body{font:16px/1.65 system-ui;max-width:1080px;margin:32px auto;padding:24px;color:#193143;background:#f2f5f7}dt{font-weight:bold;margin-top:20px}dd{margin-left:18px}li{margin:10px 0}h1{line-height:1.25}section{background:white;padding:24px}a{color:#006e91}</style><h1>M05 reference roots: preparation review</h1><p>Direction-level adoption is preserved. Exact design remains proposed. No product implementation or destructive cleanup is authorized.</p><p><a href="../architecture-and-ui.html">Historical planning</a> | <a href="module-review.json">Structured review</a> | <a href="test-plan.json">18 planned cases</a> | <a href="module.feature">BDD</a></p><section>'+render(report)+'</section><script type="application/json" id="module-spec">'+json.dumps(report,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(page,encoding='utf-8')
board=ROOT/'docs/PROJECT-BOARD.html';before=board.read_text(encoding='utf-8');old=load_snapshot_dict(before);own='PD-P1-M05-PREP-01'
def mutate(d):
 t=next(x for x in d['tasks'] if x['id']==own)
 t['note']='[M05 root completeness review delivered] Independent preparation continued while M02 exact design is pending. Current source baseline verified; 18 root/failure/lifecycle cases added to planning, not executable tests. Physical GC remains blocked on explicit completeness/freshness/transaction capability. Pure evaluation candidate isolated for future exact design. Product source/tests unchanged; no full-card PASS, keep yellow. Evidence: docs/requirements-confirmation/phase1-spec/tasks/M05/planning/reference-roots-review/index.html\n--- original trace ---\n'+t.get('note','')
 t['referenceRootsReview']={'status':report['state'],'report':'docs/requirements-confirmation/phase1-spec/tasks/M05/planning/reference-roots-review/index.html','generatedAt':report['generated_at']}
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
after=board.read_text(encoding='utf-8');new=load_snapshot_dict(after)
assert shell_halves(before)==shell_halves(after)
assert {k:v for k,v in old.items() if k!='tasks'}=={k:v for k,v in new.items() if k!='tasks'}
assert [x for x in old['tasks'] if x['id']!=own]==[x for x in new['tasks'] if x['id']!=own]
counts=lambda d:dict(collections.Counter(x['zone'] for x in d['tasks']))
assert counts(old)==counts(new)
write('delivery-evidence.json',{'before':counts(old),'after':counts(new),'board_shell_and_other_cards_preserved':True,'source_files_verified':len(baseline['source_files']),'old_inventory_drift':drift,'product_tests':'NOT RUN','source_changes_this_round':0})
print(json.dumps({'status':report['state'],'cases':len(cases),'old_inventory_drift':drift,'counts':counts(new)}))
