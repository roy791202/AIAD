import pathlib,json,hashlib,subprocess,html,collections,re
from datetime import datetime,timezone
from tools.board.board_core.snapshot_safe import load_snapshot_dict,mutate_snapshot_file,shell_halves
from tools.board.board_core.json_store import FileLock
ROOT=pathlib.Path.cwd();P=pathlib.Path(__file__).resolve().parent;OLD=P.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
baseline=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/exact-design/authorization-and-baseline.json')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
assert head==baseline['head'] and branch==baseline['branch']
def check_sources():
 assert all((ROOT/r['path']).is_file() and hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()==r['sha256'] for r in baseline['source_files'])
check_sources()
inventory=read(OLD/'inventory.json');drift=[r['path'] for r in inventory['files'] if not (ROOT/r['path']).is_file() or hashlib.sha256((ROOT/r['path']).read_bytes()).hexdigest()!=r['sha256']]
plan=read(OLD/'test-plan.json')
rows=[
 ('01','59 seconds since last check','check deadline has not arrived','no capture','B2','none'),
 ('02','60 seconds reached; content equals successful snapshot','periodic check runs','no snapshot and no baseline change','B1/B2','none'),
 ('03','first check with unsaved content and no recovery baseline','periodic check runs','capture current complete content and required materials','B1/B8','none'),
 ('04','clear, merge or Undo mutation still in progress','check deadline arrives','defer capture until complete commit or full rollback','B7/B10','mutation barrier'),
 ('05','a snapshot is still being written','another check deadline arrives','no overlapping writer or queued timer burst','B5/B8','slow storage'),
 ('06','snapshot captured R; editor has changed to R+1','R finishes successfully','baseline acknowledges only R; R+1 remains pending','B6/B8','edit during write'),
 ('07','snapshot captured R; material bytes change before publication','publication is attempted','publish only immutable pinned bytes matching R or fail without advancing baseline','B6/B10','asset change'),
 ('08','payload or material write fails','snapshot attempt completes','retain previous valid snapshot and pending content','B4/B9','write failure'),
 ('09','payload durable but index publication fails','snapshot attempt completes','do not advance baseline or release previous snapshot roots','B5/B7','index failure'),
 ('10','snapshot R succeeded and current content is R+1','formal save succeeds','formal baseline alone changes; recovery baseline remains R','B6/B12','none'),
 ('11','snapshot R exists','formal save fails','retain recovery data and pending states','B4/B12','formal save failure'),
 ('12','only selection, hover or playback position changed','periodic check runs','no content-triggered snapshot','B3/B12','ephemeral state'),
 ('13','content was changed and then restored to last snapshot content','periodic check runs','skip equivalent content despite a higher editor revision','B2/B6','undo round trip'),
 ('14','two sessions edit same stable project identity','both reach a check deadline','separate session recovery namespaces and baselines','B8/B10','concurrent sessions'),
 ('15','old session closes while its snapshot write finishes','completion arrives in a new session','do not apply old completion to new session baseline; retain old recoverable data','B8/B11','late completion'),
 ('16','an attempt already completed','duplicate acknowledgement arrives','reject or harmlessly ignore without changing current baseline','B3/B8','duplicate completion'),
 ('17','original project drive is offline','complete recovery version is opened','open unsaved content with necessary assets and allow save to another location','B1/B9','offline project'),
 ('18','recovery root cannot be written','snapshot attempt fails','persistent visible warning, alternative-location action and no false saved claim','B4/B9','permission denied'),
 ('19','history item refers to retained recovery version','author removes history item','remove entry only; files and recovery roots remain','B8/B10','none'),
 ('20','a recovery index has unsupported schema or incomplete assets','recovery versions are enumerated','mark unavailable or incomplete with reason; do not silently activate or discard','B3/B11','integrity/version'),
 ('21','timer resumes after a long suspended interval','deadline is checked','one pending check, not one write per missed interval','B2/B8','clock jump'),
 ('22','captured bytes are durable but process dies before index success is known','application restarts','previous verified entry remains valid; inspect orphan candidate without treating it as a successful baseline','B5/B7/B9','process interruption')]
cases=[{'id':'M07-CAP-'+n,'given':g,'when':w,'then':t,'coverage':b.split('/'),'fault':f,'fixture':{'session':'S0 unless case specifies S1','project':'stable P0','baseline':'optional content fingerprint F0','captured':'immutable R0/F0 or R1/F1','current':'may advance to R2/F2','clock_ms':[59000,60000,61000,120000]},'result':'PLANNED_NOT_RUN','valid_red':'After approved Skeleton only: target compiles and reaches intended behavior assertion; compile/fixture/environment failure is invalid RED.'} for n,g,w,t,b,f in rows]
source_paths=['apps/sgenaxis-desktop/crates/sgenaxis-core/src/dirty.rs','apps/sgenaxis-desktop/crates/sgenaxis-host/src/scene_doc.rs','apps/sgenaxis-desktop/crates/sgenaxis-host/src/uidesign_doc.rs','apps/sgenaxis-desktop/crates/sgenaxis-ports/src/fs.rs']
report={
 'module':'M07','task':'PD-P1-M07-PREP-01','state':'PREPARATION_REVIEW_DELIVERED_EXACT_SEAMS_PENDING','generated_at':datetime.now(timezone.utc).isoformat(),'branch':branch,'head':head,
 'authority':'Own planning files and own board evidence only. User-supplied AGENTS workflow is applicable; no product changes, no new architecture approved.',
 'confirmed_baseline':['Every 60 seconds check content against last successfully saved recovery snapshot','No change: skip; no overlap; failed attempt retains baseline and retries next check','Do not capture intermediate clear/import/merge/Undo state','Changes during save remain pending after captured version succeeds','Formal-save and recovery baselines independent; formal save never clears retained snapshots','ProjectID/SessionID isolate recovery; original project path is location metadata','Recovery opens unsaved; removing history does not delete snapshots or files'],
 'source_evidence':{'old_inventory_drift':drift,'fresh_files_checked':len(baseline['source_files']),'files':[{'path':x,'sha256':hashlib.sha256((ROOT/x).read_bytes()).hexdigest()} for x in source_paths],
 'findings':['core DirtySet tracks property/projection reevaluation and clear(), not a recovery content fingerprint or formal/recovery dual baseline. Reusing clear() after formal save would violate confirmed recovery semantics.','scene_doc save_scene_text performs project-relative text persistence via FileSystemPort; it does not expose immutable multi-content capture with asset ownership.','DesignDoc has selection and timestamp metadata. Hashing raw serialization without an approved semantic projection would incorrectly trigger content snapshots on ephemeral changes.','Generic FileSystemPort has no durable multi-file snapshot-plus-index publication or material pin lifecycle. Accepted IO Skeleton is not implemented runtime publication.'],
 'existing_planned_cases':len(plan['cases'])},
 'findings':[
 {'id':'GAP-M07-01','severity':'P1','issue':'Atomic capture across document content and required material versions is not expressed by current generic interfaces.','disposition':'Freeze stable capture/projection ownership contract before HOST writer integration.'},
 {'id':'GAP-M07-02','severity':'P1','issue':'Completion acknowledgements need immutable attempt identity and session binding; current case R/R+1 alone does not cover stale/duplicate completion.','disposition':'Proposed attempt token and completion state machine below; no source API added.'},
 {'id':'GAP-M07-03','severity':'P1','issue':'Material root release cannot precede successful snapshot/index publication, and cannot depend on recent-history visibility.','disposition':'Coordinate with M05 root completeness; failure preserves previous and necessary candidate material.'},
 {'id':'GAP-M07-04','severity':'P2','issue':'Old inventory contains listed hash drift. Numeric cadence is confirmed, but scheduler/clock semantics and canonical fingerprint projection still require precision.','disposition':'New evidence is current static inspection; no full-card PASS.'}],
 'architecture_proposal':{
 'hexagonal_view':'UI/timer adapter -> authorized HOST recovery use case -> WORK recovery eligibility/state policy. HOST -> stable capture capability + recovery publisher capability + monotonic clock abstraction <- owning document/material/native adapters.',
 'dependency_view':'M04 committed immutable content + M05 pinned material versions -> M07 captured envelope -> recovery store payload -> single published index acknowledgement -> WORK baseline. Formal saver updates only its separate baseline.',
 'ownership':'Document owner owns current content and mutation barrier; M05 owns immutable material identity; M07 owns recovery baseline and attempt state per session. Captured envelopes and history items are projections, never document SSOT.',
 'mutation_boundary':'No UI/timer direct filesystem writes. Capture owner provides stable immutable semantic content. Recovery completion may advance only matching session attempt; it cannot overwrite the active document.',
 'transaction_boundary':'Acquire stable content + necessary asset claims -> release short capture barrier -> persist immutable payload/materials off UI -> publish durable index -> acknowledge captured fingerprint -> convert temporary material claims to retained snapshot roots. Failure before index acknowledgement never advances baseline.',
 'reader_boundary':'Enumerate and open only validated payload/index consistency. Uncertain/unsupported/incomplete entries remain visible with reason where safe, never automatically treated as successful capture.',
 'proposed_states':['Idle','DeferredMutation','Capturing','Writing(attempt)','WarningPendingRetry','Closed'],
 'attempt_binding':['project_id','session_id','attempt_id','captured_revision','captured_content_fingerprint','asset_manifest_digest'],
 'success_transition':'Writing(A) + durable index acknowledgement for A -> recovery baseline = A.captured_content_fingerprint; current fingerprint is reread independently. Never baseline=current merely because write finished.',
 'failure_transition':'Writing(A) + failure -> unchanged successful baseline; retain changed state and materials needed for recovery; next scheduled check retries after no operation overlaps.',
 'close_transition':'Closed session never accepts a completion into another session. Any already-published version retains original session identity; no destruction merely because editor closed.',
 'pure_slice_candidate':'Policy(state, monotonic check event, stable current fingerprint, mutation/inflight flags) -> Skip / Defer / RequestCapture. Completion(state, matching attempt outcome) -> new policy state. No FS, OS timer, hashing implementation or ownership migration in this slice.',
 'non_goals':['No adoption of M02 generation store protocol for recovery without its own review','No automatic retention limits or GC','No change to core DirtySet or existing selection Undo','No UI authority migration or blanket editing of app.js']},
 'proposed_defaults_not_confirmed':['Use monotonic elapsed time for checks; resume performs at most one catch-up check. No timer backlog writes.','A deferred check is eligible once stable state is available, but no concurrent attempt; event/timer integration must be frozen in exact design.','Compare semantic content fingerprints, not only increasing revisions; content restored to previous snapshot is equal. Canonical field list and hash profile remain pending.','Retain unprocessed snapshots and candidate artifacts conservatively; physical cleanup has separate approval and complete-root prerequisites.'],
 'candidate_scope_for_future_confirmation':{'existing':['apps/sgenaxis-desktop/crates/sgenaxis-work/src/lib.rs'],'new':['apps/sgenaxis-desktop/crates/sgenaxis-work/src/recovery_state.rs'],'test':['apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_recovery_policy.rs'],'status':'PROPOSED; exact public types/signatures and bounded inputs NOT YET FROZEN','future_command':'cargo test -p sgenaxis-work --test phase1_recovery_policy','cwd':'apps/sgenaxis-desktop','target':'NOT CREATED'},
 'cases':cases,'coverage':{b:[c['id'] for c in cases if b in c['coverage']] for b in ['B'+str(i) for i in range(1,13)]},
 'traceability':{'BDD-22':['M07-CAP-02','M07-CAP-12','M07-CAP-13'],'BDD-23':['M07-CAP-03'],'BDD-24':['M07-CAP-06','M07-CAP-07'],'BDD-25':['M07-CAP-05','M07-CAP-08','M07-CAP-09'],'BDD-26':['M07-CAP-04'],'BDD-27':['M07-CAP-10','M07-CAP-11'],'BDD-28':['M07-CAP-17','M07-CAP-20'],'BDD-29':['M07-CAP-19'],'BDD-30':['M07-CAP-14','M07-CAP-15']},
 'next_design_work':['Freeze pure policy types/signatures, fingerprints as opaque validated values and exact event ordering','Specify stable capture input/output capability, mutation barrier and unsaved-draft coverage with document owner','Define snapshot payload/index bytes, integrity/limits and M05 material claim transfer as one transaction proposal','Freeze monotonic timer/session close/late completion UI behavior and adjacent M04/M05 regression cases','Submit consolidated precision packet once ready; no additional owner question required for this audit'],
 'acceptance':['Every original BDD22-30 mapped to planned cases','B1-B12 each has a concrete planned case','Baseline/failure/session identity and root-release semantics explicitly distinguished','Source evidence current and product execution clearly NOT RUN'],
 'verification':{'product_tests':'NOT RUN','valid_RED':'NOT RUN','build_runtime':'NOT RUN','independent_acceptance':'NOT RUN','source_files_modified':0,'module_complete':False},
 'block_classification':'ARCHITECTURE_GAP for live stable-capture/publisher seam; NOT_READY_FOR_IMPLEMENTATION. Independent pure-policy design preparation remains actionable.'}
assert all(report['coverage'].values())
assert set(report['traceability'])=={'BDD-'+str(i) for i in range(22,31)}
write('module-review.json',report);write('test-plan.json',{'status':'PLANNED_NOT_RUN','cases':cases,'coverage':report['coverage'],'traceability':report['traceability']})
feature=['@proposal_only','Feature: Recovery saves complete stable editing content','  Background:','    Given an author is editing a local project','  Rule: Successful recovery never loses changes made during saving','']
for c in cases:feature+=['    @'+c['id'],'    Scenario: '+c['id'],'      Given '+c['given'],'      When '+c['when'],'      Then '+c['then'],'']
(P/'module.feature').write_text('\n'.join(feature),encoding='utf-8')
def render(v):
 if isinstance(v,dict):return '<dl>'+''.join('<dt>'+html.escape(k)+'</dt><dd>'+render(x)+'</dd>' for k,x in v.items())+'</dl>'
 if isinstance(v,list):return '<ul>'+''.join('<li>'+render(x)+'</li>' for x in v)+'</ul>'
 return html.escape(str(v))
page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M07 stable capture preparation review</title><style>body{font:16px/1.65 system-ui;max-width:1100px;margin:32px auto;padding:24px;background:#f2f5f7;color:#193143}dt{font-weight:650;margin-top:20px}dd{margin-left:18px}li{margin:10px 0}section{background:white;padding:24px}a{color:#006e91}</style><h1>M07 stable capture and completion review</h1><p>Confirmed: 60-second content checks, independent baselines and no overlapping snapshots. Exact capture/attempt/publication seams remain proposed; product implementation NOT RUN.</p><p><a href="../architecture-and-ui.html">Historical planning</a> | <a href="module-review.json">Structured review</a> | <a href="test-plan.json">22 planned cases</a> | <a href="module.feature">BDD</a></p><section>'+render(report)+'</section><script type="application/json" id="module-spec">'+json.dumps(report,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(P/'index.html').write_text(page,encoding='utf-8')
for f in P.glob('*.json'):read(f)
assert all((P/x).exists() for x in re.findall('href="([^"]+)"',page))
board=ROOT/'docs/PROJECT-BOARD.html';before=board.read_text(encoding='utf-8');old=load_snapshot_dict(before);own='PD-P1-M07-PREP-01'
def mutate(d):
 t=next(x for x in d['tasks'] if x['id']==own)
 t['note']='[M07 stable-capture preparation review delivered] 22 concrete planned cases map B1-B12 and BDD22-30. Reviewed stale/duplicate completion, session close, R/R+1, immutable material capture, payload/index failure and independent formal/recovery baselines. Stable capture/publisher seams remain architectural gaps; pure policy design can proceed independently of M02. Product code/tests untouched; no valid RED or full PREP PASS. Keep yellow. Evidence: docs/requirements-confirmation/phase1-spec/tasks/M07/planning/stable-capture-review/index.html\n--- original trace ---\n'+t.get('note','')
 t['stableCaptureReview']={'status':report['state'],'report':'docs/requirements-confirmation/phase1-spec/tasks/M07/planning/stable-capture-review/index.html','generatedAt':report['generated_at']}
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
after=board.read_text(encoding='utf-8');new=load_snapshot_dict(after)
assert shell_halves(before)==shell_halves(after)
assert {k:v for k,v in old.items() if k!='tasks'}=={k:v for k,v in new.items() if k!='tasks'}
assert [x for x in old['tasks'] if x['id']!=own]==[x for x in new['tasks'] if x['id']!=own]
counts=lambda d:dict(collections.Counter(x['zone'] for x in d['tasks']))
assert counts(old)==counts(new);check_sources()
write('delivery-evidence.json',{'before':counts(old),'after':counts(new),'board_shell_other_cards_and_root_metadata_preserved':True,'source_files_verified':len(baseline['source_files']),'old_inventory_drift':drift,'JSON_links_and_BDD_coverage':'PASS (static only)','product_tests':'NOT RUN','source_changes_this_round':0})
print(json.dumps({'status':report['state'],'cases':len(cases),'coverage_categories':len(report['coverage']),'old_inventory_drift':drift,'counts':counts(new)}))
