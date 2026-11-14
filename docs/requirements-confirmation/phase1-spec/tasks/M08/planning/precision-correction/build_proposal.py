"""Documentation-only materialization of proposed M08 F1/F2/F3 corrections.

No validator, UI driver, native fixture, process, or product test is implemented.
Synthetic dictionaries below are test specifications, never actual run evidence.
"""
from pathlib import Path
import copy,json,hashlib,datetime,math,re,html,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
PLAN=HERE.parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(name,data):
    (HERE/name).write_bytes(json.dumps(data,ensure_ascii=False,indent=2).encode('utf-8'))
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
current=read(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==current['head']
assert subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip()==current['branch']
for path,digest in current['source_hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
for rel,digest in read(PLAN/'full-preparation-acceptance/review.json')['reviewed_document_hashes'].items():
    assert hashlib.sha256((PLAN/rel).read_bytes()).hexdigest()==digest,rel

STATUS='PROPOSED_NOT_APPROVED_NOT_RUN'
notice='ALL records and binding facts in this file are fictitious SCHEMA_UNIT vectors, NOT live evidence. Do not launch paths, use PIDs, access volumes, aggregate native PASS, or treat example flags/hashes as real attestations.'
exe=r'X:\__M08_SYNTHETIC_NOT_REAL__\artifact\EluSlot.exe'
sandbox=r'X:\__M08_SYNTHETIC_NOT_REAL__\sandbox'
project=sandbox+r'\Project-A'
base={
 'record_format':'m08.native-evidence.v1','run_id':'synthetic-unit-not-executed','recorded_at':'2026-01-01T00:00:30Z','module':'M08','case_id':'M08-N16',
 'source':{'branch':'fixture/not-a-real-checkout','head':'1'*40,'dirty_inventory_sha256':'2'*64,'approved_spec_revision':'fixture-spec-r1-not-owner-approval','build_manifest_ref':'SYNTHETIC-MANIFEST-NOT-A-FILE'},
 'artifact':{'eligibility':'ELIGIBLE','actual_path':exe,'actual_sha256':'3'*64,'build_manifest_sha256':'4'*64,'built_executable_sha256':'3'*64},
 'environment':{'OS_build':'10.0.22631','OS_arch':'x64','is_Windows11':True,'WebView2':'123.0.0.0','user_profile_mode':'DISPOSABLE_TEST_ACCOUNT'},
 'execution':{'state':'EXECUTED','pid':424242,'process_started_at':'2026-01-01T00:00:00Z','command_or_manual_steps':['SYNTHETIC ONLY: no executable is launched'],'selected_executable_path':exe},
 'fixture':{'sandbox_id':'synthetic-sandbox','canonical_sandbox_root':sandbox,'ownership_marker_sha256':'5'*64,'canonical_test_roots':[project],'all_roots_proven_within_disposable_scope':True,'original_source_hashes_before_after':{'fixture.ess':{'before':'6'*64,'after':'6'*64}}},
 'evidence':{'layer':'E3','logs':['synthetic-log-A'],'captures':['synthetic-capture-A'],'operation_result':{'description':'fictitious UI result'},'assertions_executed':True,'fixture_health_confirmed':True},
 'result':{'verdict':'PASS','reason':'Synthetic consistency vector only, never a real native result','unmet_prerequisites':[],'remaining_limits':[]},
 'illustrative_only':False,
}
bindings={
 'mode':'SCHEMA_UNIT','notice':notice,
 'expected_source':copy.deepcopy(base['source']),
 'expected_artifact':copy.deepcopy(base['artifact']),
 'expected_environment':copy.deepcopy(base['environment']),
 'expected_process':{'run_id':base['run_id'],'pid':424242,'process_started_at':base['execution']['process_started_at'],'selected_executable_path':exe,'executable_sha256':'3'*64},
 'root_proofs':{project:{'canonical_sandbox_root':sandbox,'sandbox_id':'synthetic-sandbox','ownership_marker_sha256':'5'*64,'resolved_ancestor_identity_matches':True,'no_reparse_escape':True}},
 'capture_bindings':{'synthetic-capture-A':{'run_id':base['run_id'],'pid':424242,'process_started_at':base['execution']['process_started_at'],'executable_sha256':'3'*64}},
}
policy={'case_id':'M08-N16','requires_Windows11_x64':True,'requires_native_layer':True,'requires_disposable_account':False,'required_modules':['M01-S3','M07-runtime'],'native_layer_values':['E3','E4']}
write('synthetic-base.json',{'status':STATUS,'fixture_kind':'SYNTHETIC_TEST_VECTOR_NOT_NATIVE_EVIDENCE','notice':notice,'record':base,'observed_bindings':bindings,'case_policy':policy,'flag_note':'record.illustrative_only=false deliberately exercises a purported genuine record; outer fixture_kind and SCHEMA_UNIT context always prevent it becoming live evidence. True illustrative PASS is a separate negative vector.'})

# This is a proposed pure test-harness checker, not a new product API or Port.
# Native collection/aggregation is deliberately absent from the first scope.
validation={
 'status':STATUS,'primary_module':'M08','subtask':'M08-H1-PURE-RECORD-CHECK',
 'proposed_file':'tests/test_p1_portable_acceptance.py','current_file_exists':(ROOT/'tests/test_p1_portable_acceptance.py').exists(),
 'entry_signature':'_validate_evidence_claim(record: Mapping[str, JSONValue], observed_bindings: Mapping[str, JSONValue], case_policy: Mapping[str, JSONValue]) -> EvidenceCheck',
 'local_types':{'JSONValue':'None | bool | int | str | list[JSONValue] | dict[str, JSONValue]; float not used for digests/PIDs/time samples','EvidenceIssue':'frozen dataclass(code: EvidenceCode, pointer: RFC6901 absolute string)','EvidenceCheck':'frozen dataclass(classification: Literal[SCHEMA_VALID, REJECTED], issue: EvidenceIssue | None, evidence_scope: Literal[SCHEMA_UNIT]); never returns PASS or native verdict'},
 'preconditions':['All three inputs borrowed read-only, no mutation or normalization','observed_bindings.mode must be SCHEMA_UNIT for this first pure slice; fixture facts are synthetic test doubles','No native collector, PID lookup, filesystem hashing, process launch, file write, network or live aggregation capability in this slice'],
 'postconditions':['SCHEMA_VALID iff all declared structural/cross-field checks pass against supplied facts; NOT proof those facts physically exist','REJECTED has exactly the first declared EvidenceIssue; stable priority below, no assertion weakening','Inputs remain deeply/canonically equal before and after both success and error','No native/system PASS can be produced by this return type or incorporated as actual evidence'],
 'priority_groups':[
  {'priority':0,'checks':['record format/module/case shape; RFC3339 timestamp includes timezone; hash/PID primitive syntax'], 'tie_break':'schema property order from existing record-fields.json, then RFC6901 index order'},
  {'priority':1,'checks':['PASS requires EXECUTED','assertions executed','fixture health','unmet prerequisites empty']},
  {'priority':2,'checks':['case-policy Windows11 x64','required nonempty valid source inventory hash','required build manifest source reference and manifest SHA','ELIGIBLE artifact','actual artifact SHA equals manifest executable SHA and supplied expected artifact binding']},
  {'priority':3,'checks':['exact source revision/inventory/spec binding','exact process run/PID/start/path/hash binding','canonical root ownership proof for each root, not caller boolean or path prefix','capture run/PID/start/hash binding']},
  {'priority':4,'checks':['illustrative native PASS rejected','E0/E1/E2 cannot satisfy native-layer required case','profile and source-preservation requirements from case policy']},
 ],
 'non_PASS_records':'NOT RUN/BLOCKED record may retain truthful read-only artifact identification, but cannot invent PID/start/result/capture. Validate present fields, shape and truthful missing prerequisite representation; do not require an executable or Win11 to validate its schema.',
 'timestamp_rule':'RFC3339 timezone Z or explicit offset required; date/time/offset validity checked, no locale parsing. Missing timezone has specific E_TIMESTAMP_OFFSET_REQUIRED.',
 'source_inventory_rule':'Missing, null or empty /source/dirty_inventory_sha256 receives E_SOURCE_INVENTORY_REQUIRED before generic digest-shape validation; present wrong-length/case token receives E_DIGEST_FORMAT.',
 'PID_rule':'EXECUTED requires type exactly int (bool is not int here), 1 <= pid <= 4294967295; reject0/negative/out-of-range without touching OS.',
 'source_truth_boundary':'Supplied bindings do not establish authenticity. A later separately designed/approved native runner must acquire actual observations and own aggregation. No untrusted record can grant itself authority by setting eligibility, root boolean, illustrative flag or PID.',
 'runtime_aggregation':'OUT_OF_SCOPE; no native PASS result type/function in H1',
}

def setptr(doc,path,value,remove=False):
    segs=[s.replace('~1','/').replace('~0','~') for s in path.strip('/').split('/')];node=doc
    for key in segs[:-1]:node=node[int(key)] if isinstance(node,list) else node[key]
    key=int(segs[-1]) if isinstance(node,list) else segs[-1]
    if remove:del node[key]
    else:node[key]=copy.deepcopy(value)

negative_specs=[
 ('01','M08-HR02',[('/environment/is_Windows11',False),('/environment/OS_build','10.0.19045')],'E_WIN11_REQUIRED','/environment/is_Windows11','Windows10 record claims Windows11 native PASS'),
 ('02','M08-HR03',[('/artifact/actual_sha256','7'*64)],'E_ARTIFACT_DIGEST_MISMATCH','/artifact/actual_sha256','actual binary hash differs from manifest executable hash'),
 ('03','M08-HR03',[('/source/dirty_inventory_sha256',None)],'E_SOURCE_INVENTORY_REQUIRED','/source/dirty_inventory_sha256','HEAD present but source inventory absent'),
 ('04','M08-HR05',[('/evidence/captures',['synthetic-unbound-capture'])],'E_CAPTURE_BINDING','/evidence/captures/0','screenshot without matching run/process binding'),
 ('05','M08-HR01',[('/execution/state','NOT RUN')],'E_EXECUTION_REQUIRED','/execution/state','NOT RUN claims PASS; execution error takes priority over leftover PID fields'),
 ('06','M08-HR03',[('/source/build_manifest_ref',None),('/artifact/build_manifest_sha256',None)],'E_BUILD_MANIFEST_REQUIRED','/source/build_manifest_ref','claimed ELIGIBLE, matching declared hash but no source-build provenance; historical identification cannot suffice'),
 ('07','M08-HR06',[('/fixture/canonical_test_roots',[sandbox+'-escape\\Project-A'])],'E_SANDBOX_OWNERSHIP','/fixture/canonical_test_roots/0','caller boolean remains true but supplied canonical ownership proof does not cover lookalike path'),
 ('08','M08-HR08',[('/execution/process_started_at','2026-01-01T00:00:01Z')],'E_PROCESS_BINDING','/execution/process_started_at','PID unchanged but start time differs from run-owned binding'),
 ('09','M08-HR10',[('/illustrative_only',True)],'E_ILLUSTRATIVE_NOT_RUNTIME','/illustrative_only','illustrative sample purports to be actual native PASS'),
 ('10','M08-HR01',[('/result/unmet_prerequisites',['M07-runtime'])],'E_UNMET_PREREQUISITES','/result/unmet_prerequisites','required runtime absent while verdict claims PASS'),
 ('11','required recorded_at shape',[('/recorded_at','2026-01-01T00:00:30')],'E_TIMESTAMP_OFFSET_REQUIRED','/recorded_at','timestamp lacks timezone'),
 ('12','M08-HR10',[('/evidence/layer','E1')],'E_EVIDENCE_LAYER_REQUIRED','/evidence/layer','library probe purports to satisfy portable UI native-layer gate'),
]
vectors=[]
for suffix,rule,mutations,code,path,meaning in negative_specs:
    record=copy.deepcopy(base)
    for ptr,value in mutations:setptr(record,ptr,value)
    vectors.append({'id':'M08-H-N'+suffix,'bdd':'BDD-M08-H-N'+suffix,'requirement':'REQ-01/REQ-23 evidence separation','invariant':rule,'test_name':'test_m08_claim_n'+suffix,'given':meaning,'base_ref':'synthetic-base.json#/record','mutations':[{'op':'replace','pointer':k,'value':v} for k,v in mutations],'input_record':record,'observed_bindings_ref':'synthetic-base.json#/observed_bindings','case_policy_ref':'synthetic-base.json#/case_policy','expected':{'classification':'REJECTED','issue':{'code':code,'pointer':path},'evidence_scope':'SCHEMA_UNIT'},'unchanged_input_assertion':'record, observed_bindings and case_policy deep equality and canonical JSON SHA unchanged after call','valid_RED':'After approved H1 Skeleton compiles, exact EvidenceCheck comparison fails only because validation behavior is absent; setup/import/dependency/fixture failure is invalid RED','result':'NOT RUN'})
write('validator-negative-vectors.json',{'status':STATUS,'notice':notice,'cases':vectors})

positives=[]
def positive(name,record=None,expected_context=None,expected=None):
    positives.append({'id':name,'test_name':'test_'+name.lower().replace('-','_'),'input_record':copy.deepcopy(record or base),'observed_bindings':copy.deepcopy(expected_context or bindings),'case_policy':copy.deepcopy(policy),'expected':expected or {'classification':'SCHEMA_VALID','issue':None,'evidence_scope':'SCHEMA_UNIT'},'result':'NOT RUN','notice':notice})
positive('M08-H-P01')
for suffix,timestamp in [('Z','2026-01-01T00:00:30Z'),('OFFSET','2026-01-01T08:00:30+08:00')]:
    v=copy.deepcopy(base);v['recorded_at']=timestamp;positive('M08-H-P02-'+suffix,v)
blocked=copy.deepcopy(base);blocked['artifact']['eligibility']='UNREVIEWED';blocked['source']['build_manifest_ref']=None;blocked['artifact']['build_manifest_sha256']=None;blocked['artifact']['built_executable_sha256']=None;blocked['environment'].update(is_Windows11=False,OS_build='10.0.19045',WebView2='NOT_CHECKED',user_profile_mode='NOT_CHECKED');blocked['execution'].update(state='NOT RUN',pid=None,process_started_at=None,selected_executable_path=None);blocked['fixture'].update(canonical_sandbox_root=None,ownership_marker_sha256=None,canonical_test_roots=[],all_roots_proven_within_disposable_scope=False,original_source_hashes_before_after={});blocked['evidence'].update(layer='E0',captures=[],operation_result=None,assertions_executed=False,fixture_health_confirmed=False);blocked['result'].update(verdict='BLOCKED',unmet_prerequisites=['eligible-artifact','Windows11','owned-fixture'],reason='Synthetic truthful NOT RUN representation');blocked['illustrative_only']=True
positive('M08-H-P03-BLOCKED',blocked)
for n in [1,4294967295]:
    v=copy.deepcopy(base);facts=copy.deepcopy(bindings);v['execution']['pid']=n;facts['expected_process']['pid']=n;facts['capture_bindings']['synthetic-capture-A']['pid']=n;positive('M08-H-P04-PID-'+str(n),v,facts)
v=copy.deepcopy(base);facts=copy.deepcopy(bindings);unicode_exe=r'X:\__M08_SYNTHETIC_NOT_REAL__\含 空白\EluSlot.exe';v['artifact']['actual_path']=unicode_exe;v['execution']['selected_executable_path']=unicode_exe;facts['expected_artifact']['actual_path']=unicode_exe;facts['expected_process']['selected_executable_path']=unicode_exe;positive('M08-H-P05-UNICODE',v,facts)
for size in [63,64,65]:
    v=copy.deepcopy(base);v['artifact']['actual_sha256']='3'*size
    positive('M08-H-B01-DIGEST-'+str(size),v,expected=None if size==64 else {'classification':'REJECTED','issue':{'code':'E_DIGEST_FORMAT','pointer':'/artifact/actual_sha256'},'evidence_scope':'SCHEMA_UNIT'})
for pid in [0,-1,4294967296,True]:
    v=copy.deepcopy(base);v['execution']['pid']=pid;positive('M08-H-B02-PID-'+str(pid),v,expected={'classification':'REJECTED','issue':{'code':'E_PID_INVALID','pointer':'/execution/pid'},'evidence_scope':'SCHEMA_UNIT'})
write('validator-positive-boundaries.json',{'status':STATUS,'notice':notice,'cases':positives})

codes={x['expected']['issue']['code'] for x in vectors}
codes.update(['E_UNEXECUTED_PROCESS_FIELDS','E_UNEXECUTED_CAPTURE','E_FIELD_REQUIRED','E_FIELD_TYPE','E_FIELD_ENUM','E_UNKNOWN_FIELD','E_TIMESTAMP_INVALID','E_CASE_BINDING','E_CONTEXT_MODE','E_DIGEST_FORMAT','E_PID_INVALID','E_RECORD_FORMAT','E_SOURCE_BINDING','E_ASSERTIONS_REQUIRED','E_FIXTURE_HEALTH_REQUIRED','E_ACCOUNT_REQUIRED','E_SOURCE_CONTENT_CHANGED'])
validation['error_codes']=sorted(codes)
validation['applicability']={'all_records':'mode guard, closed shape, required source identity syntax, timestamp and every present field type; output always SCHEMA_UNIT','PASS_records':'priority groups1-4 evaluate every eligibility/execution/binding/native-claim predicate','non_PASS_records':'may remain truthfully BLOCKED without Win11/eligible artifact/owned native fixture; NOT RUN state requires pid/start/selected path null, no operation_result or captures; surplus process fields use E_UNEXECUTED_PROCESS_FIELDS, captures use E_UNEXECUTED_CAPTURE','executed_failure_records':'retain actual provided process identity/evidence when known; require supplied binding consistency without treating it as a PASS; no facts invented for a missing prerequisite'}
validation['shape_policy']={'status':STATUS,'closed_objects':'top-level and each named source/artifact/environment/execution/fixture/evidence/result object reject unknown fields; operation_result is explicitly free JSON scalar/object/null, source-hash maps use fixture-relative IDs','required':'all original record-fields.json keys are required, except specifically nullable fields still require the key','error_mapping':{'missing_key':'E_FIELD_REQUIRED at exact missing pointer, with source inventory special case E_SOURCE_INVENTORY_REQUIRED','wrong_primitive_or_container':'E_FIELD_TYPE at field pointer','unknown_named_key':'E_UNKNOWN_FIELD at unexpected pointer','invalid_enumeration':'E_FIELD_ENUM at field pointer','bad_RFC3339_date_or_offset':'E_TIMESTAMP_INVALID; absent timezone specifically E_TIMESTAMP_OFFSET_REQUIRED','mismatched_case_policy':'E_CASE_BINDING /case_id','context_mode_not_SCHEMA_UNIT':'E_CONTEXT_MODE /observed_bindings/mode'},'specific_primitive_precedence':'format/PID/digest/source inventory/timestamp specialized errors precede generic type check at that same field; missing source inventory always uses E_SOURCE_INVENTORY_REQUIRED','maps_and_refs':'original_source_hashes_before_after requires per-fixture {before:64hex,after:64hex}; capture refs are opaque lookup keys resolved only against supplied capture_bindings, never file-opened','array_order':'record arrays retained; issues chosen by stable priority, then documented field/index order; no mutation/default-filling'}

validation['deterministic_order_note']='All vector fields not explicitly mutated retain valid base values. N05 execution-state priority precedes NOT RUN extraneous PID checks; N06 missing manifest precedes artifact/binding checks; N08 process identity precedes capture consistency. Return one stable first issue, never mask a higher-priority mismatch.'
validation['tests']={'negative':len(vectors),'positive_and_boundary':len(positives),'command':'python -m pytest tests/test_p1_portable_acceptance.py -k m08_claim -q','cwd':'D:/AIAD','target_status':'PROPOSED TARGET NOT CREATED; command NOT RUN','fixture_materialization':'After approval embed these exact synthetic vectors as private fixture dictionaries in the single permitted test file, or request explicit fixture-file scope before adding external test files; never load a mutable real run as the base.'}
write('validator-contract.json',validation)

responsiveness={
 'status':STATUS,'finding':'M08-PREP-F1','case':'M08-N08','requirement':'既有：快照寫入不應阻塞 UI 操作；下列數字是建議驗收預設，尚未採納為產品 SLA。',
 'proposed_default':{'events':30,'nominal_input_period_us':1000000,'observation_window_us':30000000,'minimum_inputs_inside_verified_write_interval':3,'p95_upper_bound_us':250000,'maximum_upper_bound_us':1000000,'maximum_timestamp_uncertainty_us':20000,'percentile':'nearest rank sorted[ceil(0.95*N)-1]; integers in monotonic microseconds; bounds inclusive'},
 'interaction':'Alternate selection between two pre-existing visible fixture objects through ordinary permitted native UI input. Expected acknowledgement is the visible selected-object identity/highlight matching that particular input. Selection must not count as content change; no destructive action or hidden UI evaluation.',
 'GWT':{'Given':'Eligible locked artifact, actual Windows11 x64, disposable owned project/account, native recording with calibrated monotonic event/frame mapping and an approved observable snapshot write interval','When':'Issue30 alternating selection inputs over30seconds while an actual permitted snapshot write overlaps at least3 inputs','Then':'Each input receives its matching acknowledgement; conservative p95 latency <=250ms and maximum <=1000ms; content/source hashes remain valid and no edit is silently marked captured'},
 'per_event_record':['sequence:int','issued_at_us:int monotonic','expected_object_id:string stable fixture ID','ack_object_id:string','ack_frame_start_us:int','ack_frame_end_us:int','write_interval_ref:string or null'],
 'latency':'ack_frame_end_us - issued_at_us, a conservative upper bound; use calibrated interval end, never subtract recorder uncertainty to turn a failure into PASS. Wrong object/missing acknowledgement by maximum deadline fails responsiveness; missing or invalid recording is not product RED.',
 'observation_health':['Run/PID/start/executable hash bind input trace, recording and write interval to the same session','All30 inputs and matching acknowledgements accounted for, unless a timed-out acknowledgement is the actual measured product failure','Monotonic ordering, calibration uncertainty <=20000us, no dropped/unbounded frames, exact native write interval start/end evidence','At least3 issued inputs are within a proven write interval; at least1 still-pending content edit is checked through approved M07 observation after capture without adding new hook'],
 'fixture_recipe':['Only approved disposable data and permitted material sizes; use current M05/M07 accepted limits, not an invented large-asset cap','Use an eligible real write and ordinary native input. If permitted workload finishes too quickly for3 overlaps, report BLOCKED_INSUFFICIENT_OVERLAP; do not stall product IO or add sleeps/hooks','If M07 cannot expose approved write/capture acknowledgement evidence, classify IMPLEMENTATION_BLOCKED/ARCHITECTURE_GAP for native execution and propose observability separately. Do not implement a test hook in this package','Record the actual permissible workload, hashes and native environment. Do not benchmark old historical binary or call a library timer/native probe full UI evidence'],
 'classification':{'measured_all_thresholds_and_health_met':'eligible native operator may report PASS only after separate native harness approval; this planning file is NOT RUN','valid_recording_with_wrong_ack_or_timeout_or_latency_limit_exceeded':'FAIL actual responsiveness observation','bad_calibration_or_wrong_process_or_missing_write_interval_or_insufficient_overlap':'BLOCKED_OBSERVATION; no native PASS/FAIL or valid RED inferred','synthetic_unit_metric_vector':'SCHEMA/METRIC ORACLE ONLY, never native responsiveness proof'},
 'forbidden':['new production UI control or runtime Port','private JS/DOM injection to simulate acknowledgement','unapproved sleep/fault/clock overrides','process-name kill or changing real user project/profile','deriving capture success from UI selection state'],
 'integration_boundary':'M08 records evidence; M03 owns UI/preview authority and M07 owns writer/capture/baselines. This proposal does not move ownership or alter60-second snapshot cadence.',
 'owner_decision':'M08-PD1: adopt or adjust the numeric responsiveness acceptance profile and native observation strategy as a whole; not yet approved.'
}
metric=[]
for name,values,health,expected in [
 ('at_both_limits',[100000]*28+[250000,1000000],{},'WITHIN_PROPOSED_PROFILE'),
 ('p95_plus_one',[100000]*28+[250001,1000000],{},'EXCEEDS_P95'),
 ('max_plus_one',[100000]*29+[1000001],{},'EXCEEDS_MAX'),
 ('p95_below',[100000]*28+[249999,999999],{},'WITHIN_PROPOSED_PROFILE'),
 ('missing_sample',[100000]*29,{},'BLOCKED_BAD_SAMPLE_COUNT'),
 ('insufficient_overlap',[100000]*30,{'overlap_inputs':2},'BLOCKED_INSUFFICIENT_OVERLAP'),
 ('clock_at_limit',[100000]*30,{'uncertainty_us':20000},'WITHIN_PROPOSED_PROFILE'),
 ('clock_over_limit',[100000]*30,{'uncertainty_us':20001},'BLOCKED_CALIBRATION'),
]:
    metric.append({'id':'M08-RESP-'+name,'latencies_upper_bound_us':values,'health':dict({'overlap_inputs':3,'uncertainty_us':1000,'run_binding_ok':True},**health),'expected':expected,'expected_p95_us':sorted(values)[math.ceil(.95*len(values))-1] if len(values)==30 else None,'expected_max_us':max(values),'execution':'NOT RUN; declarative oracle vector only'})
responsiveness['proposed_metric_signature']='_evaluate_responsiveness_profile(latencies_upper_bound_us: Sequence[int], observation_health: Mapping[str, JSONValue], profile: ResponseProfile) -> ResponsivenessCheck'
responsiveness['proposed_metric_output']='frozen ResponsivenessCheck(classification: declared metric-vector code, p95_us:int|None, maximum_us:int|None, evidence_scope:Literal[SCHEMA_UNIT]); never returns native PASS'
responsiveness['pure_metric_precedence']='Reject malformed samples/clock/run identity or count first, then insufficient overlap, then max over1000000us, then p95 over250000us, else WITHIN_PROPOSED_PROFILE. Wrong/missing native acknowledgement is a separate measured failure in the operator assertion, not silently removed from the30-event denominator.'
write('responsiveness-plan.json',responsiveness)
write('responsiveness-oracles.json',{'status':STATUS,'notice':'Synthetic integer examples, not recorded measurements. Only document arithmetic checked this delivery; proposed metric function/test not created.','cases':metric})

prereq=read(PLAN/'harness-contract/module-prerequisites.json')
prereq['checked_as_of']=now;prereq['current_state_projection_only']=True
for x in prereq['modules']:
    if x['module']=='M01':x.update(current='S1 accepted; Owner adopted S2-D1-D7; S2 scoped GREEN/acceptance PASS; S3 six-step UI/native selection/owner/idempotency/IPC incomplete',native_ready=False,evidence='../../../M01/planning/s2-green/verification.json')
prereq['source_inventory']='M01/planning/s2-green/source-current.json:796 files, verified this delivery'
prereq['supersedes']='M01 awaiting S2 confirmation in historical harness-contract prerequisite projection; historical source preserved'
write('current-prerequisites.json',prereq)

decisions=[{'id':'M08-PD1','status':'建議採用／未核准','proposal':'30 inputs/30seconds; p95 conservative upper-bound<=250ms; max<=1000ms; >=3 verified in-flight overlaps; <=20ms calibration uncertainty; insufficient observation BLOCKED, not fake product failure.','authority':'Quantitative acceptance detail proposed in original planning scope; no product SLA self-approval.'},{'id':'M08-PD2','status':'建議採用／未核准','proposal':'Single-file pure SCHEMA_UNIT evidence checker, frozen EvidenceCheck/EvidenceIssue, explicit first-error precedence,12 exact negative vectors and14 positive/boundary vectors. No live/native aggregation or authority inferred from record fields.','authority':'New precise test-only contract/error/defaults require one whole-package approval before Skeleton.'},{'id':'M08-PD3','status':'建議採用／未核准','proposal':'After approval first create only tests/test_p1_portable_acceptance.py Skeleton and valid RED for pure checker/metric oracles; native N01-N16 remain separate blocked until actual eligible artifact, Win11 and owner-authorized observability exist. No product/Port/schema/UI changes.','authority':'Existing automatic implementation authorization applies only AFTER approved envelope and accepted Skeleton/valid RED; this package does not approve itself.'}]
write('decisions.json',decisions)
envelope={'status':STATUS,'current_writes':['docs/requirements-confirmation/phase1-spec/tasks/M08/planning/**','own PD-P1-M08-PREP-01 evidence only through snapshot_safe + FileLock'],'after_explicit_whole_package_adoption_only':{'new_test_file':['tests/test_p1_portable_acceptance.py'],'production_files':[],'private_components':['EvidenceCode constants','frozen EvidenceIssue/EvidenceCheck','_validate_evidence_claim SCHEMA_UNIT checker','_evaluate_responsiveness_profile pure integer oracle','literal synthetic fixtures and pytest cases in this same file'],'dependencies':'Existing Python stdlib + existing pytest only, no additions/version changes'},'protected':['all product source/tests except the single later-approved new test target','all other module packages and historical M08 packages','all packaging/artifacts/manifests/locks','native profile/volume/ACL/process state','live evidence-collection/aggregation code and product observability hooks'],'boundary':'A pure checker test target passing cannot establish native artifact/Windows/UI evidence. Current package is planning only.'}
write('envelope.json',envelope)

gherkin=['Feature: M08 evidence consistency without claiming native execution','  Background:','    Given a synthetic evidence record and matching synthetic observation facts','    And the checker output is limited to schema-unit evidence','']
for x in vectors:
    gherkin += ['  Rule: '+x['invariant'],'  Scenario: '+x['bdd']+' '+x['given'],'    Given the base synthetic record with the declared field mutations','    When its evidence claim is checked','    Then it is rejected with code '+x['expected']['issue']['code'],'    And the issue points to '+x['expected']['issue']['pointer'],'    And the input records remain unchanged','    And no native PASS is produced','']
gherkin += ['Feature: Native snapshot responsiveness acceptance profile (proposed, not run)','  Scenario: BDD-M08-N08-PROPOSED responsive selection during an observed write','    Given an eligible locked artifact on actual Windows11 x64 in a disposable profile','    And timestamp uncertainty is at most20milliseconds','    And at least3 inputs overlap a verifiable snapshot write interval','    When30 ordinary selection inputs are issued over30seconds','    Then every acknowledgement matches its input object identity','    And conservative nearest-rank p95 latency is at most250milliseconds','    And maximum conservative latency is at most1000milliseconds','    And source content and pending-edit accounting remain consistent','','  Scenario: BDD-M08-N08-OBSERVATION missing write interval','    Given no verifiable snapshot write interval is available','    When responsiveness observations are evaluated','    Then the observation is classified as blocked','    And no native PASS or product failure is inferred from insufficient observation','']
feature_text='\n'.join(gherkin).replace('When30','When 30').replace('most20','most 20').replace('least3','least 3').replace('over30','over 30').replace('most250','most 250').replace('most1000','most 1000')
feature_main,feature_native=feature_text.split('Feature: Native snapshot responsiveness',1)
(HERE/'module.feature').write_bytes(feature_main.encode())
(HERE/'responsiveness.feature').write_bytes(('Feature: Native snapshot responsiveness'+feature_native).encode())
write('step-definition-stubs.json',{'status':'PLANNED_ONLY_NO_EXECUTABLE_TEST_CREATED','validator': [{'bdd':x['bdd'],'given':'PENDING load exact base/mutations/context from embedded literal fixture','when':'PENDING call _validate_evidence_claim once and snapshot inputs','then':'PENDING assert exact EvidenceCheck and immutable inputs','expected':x['expected']} for x in vectors],'responsiveness':{'given':'PENDING ordinary native operator/calibration/write-interval prerequisites; no test hook','when':'PENDING approved operator action/recording','then':'PENDING observed identity, timings, content/material hashes; pure metric checker is not native proof'},'pending_automation':['Owner whole-package adoption','create only named test Skeleton','compile/import and fixture-health check','demonstrate intended RED then accept stage','standing authorization may then implement pure test helper inside accepted scope','native driver/observability, artifact build linkage and Windows11 execution remain separate']})

# Static document checks, deliberately not executing proposed validator logic.
assert len(vectors)==12 and len({x['id'] for x in vectors})==12
assert len(positives)==14,len(positives)
for x in vectors:
    r=copy.deepcopy(base)
    for m in x['mutations']:setptr(r,m['pointer'],m['value'])
    assert r==x['input_record']
    assert x['expected']['classification']=='REJECTED'
    assert x['expected']['issue']['code'] in validation['error_codes']
    assert x['expected']['issue']['pointer'].startswith('/')
for x in metric:
    if x['expected_p95_us'] is not None:assert x['expected_p95_us']==sorted(x['latencies_upper_bound_us'])[28]
assert not (ROOT/'tests/test_p1_portable_acceptance.py').exists(),'Do not overwrite or claim ownership of unexpected test target'
for path,digest in current['source_hashes'].items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
delivery={'at':now,'status':'CORRECTION_PROPOSAL_DELIVERED_PENDING_DOCUMENT_REACCEPTANCE','findings':{'M08-PREP-F1':'measurable proposed profile, clock/overlap health and8 exact metric oracles delivered','M08-PREP-F2':'complete synthetic base + immutable observed bindings +12 exact mutations/error pointers +14 positive/boundary vectors +explicit helper return contract delivered','M08-PREP-F3':'current overlay says S2 adopted/scoped GREEN, S3 incomplete; native-ready remains false'},'owner_decisions':[x['id'] for x in decisions],'static_checks':'PASS_DOCUMENT_STRUCTURE_MUTATIONS_AND_ARITHMETIC_ONLY','validator_tests':'NOT RUN','metric_helper_tests':'NOT RUN','native_UI_tests':'NOT RUN','build_package_launch':'NOT RUN','product_changes':0,'source_unchanged':796,'head':current['head'],'branch':current['branch'],'preparation_reacceptance':'NOT RUN; must review new packet, not auto-PASS','module_complete':False}
write('verification.json',delivery)
model={'identity':{'module':'M08','task':'PD-P1-M08-PREP-01','stage':'F1-F3 proposed precise correction','status':STATUS},'canonical_policy':'Human review projection generated from this local structured package; historical packages immutable; no runtime or approval inference.','architecture':read(PLAN/'harness-contract/module-spec.json')['architecture'],'responsiveness':responsiveness,'validator':validation,'synthetic_fixture_notice':notice,'negative_cases':vectors,'positive_boundary_cases':positives,'metric_oracles':metric,'current_prerequisites':prereq,'decisions':decisions,'scope':envelope,'results':delivery}
write('module-spec.json',model)
esc=html.escape
diagrams=['Native operator / ordinary product UI\n             ↓ approved input boundaries\n    Module usecases/domain → Ports ← native adapters\n             ↓ read-only observed evidence\n       M08 evidence record/check/report\n\nM08 owns test evidence only; no M01-M07 business-state mutation.','Synthetic record + synthetic binding facts + case policy\n                        ↓\n       Proposed pure SCHEMA_UNIT checker (H1)\n                        ↓\n       SCHEMA_VALID / REJECTED + exact issue\n                        ≠\n       native PASS / product correctness / release approval']
parts=['<!DOCTYPE html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M08 F1-F3 精確補正提案</title><style>body{font:16px/1.6 system-ui;background:#f4f6fa;color:#20354b;max-width:1250px;margin:35px auto;padding:20px}header,section{background:white;border:1px solid #d7e0ec;padding:24px;border-radius:12px;margin:20px 0}header{background:#17344f;color:white}table{border-collapse:collapse;width:100%;font-size:14px}td,th{border:1px solid #ccd6e4;padding:10px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0f7;padding:18px}a{color:#126ab5}.pending{background:#fff3d6;padding:16px;border-left:5px solid #c58b22}</style><header><h1>M08｜F1～F3 精確補正提案</h1><p>Windows 驗收整合：量測標準、確定性 evidence checker 案例與目前依賴投影</p></header>',
 '<p class="pending">建議採用，尚未核准；補正交付待文件複驗。沒有產品／測試程式碼修改，沒有執行 validator、metric helper、原生 UI、build、package 或 launch。Owner 的既有自動實作授權不代表採納本次新精確契約。</p>',
 '<section><h2>用途、責任與架構</h2><p>讓人類可一次核對本機證據是否可追溯，並在未取得原生證據時保持 NOT RUN。M08 不擁有其他模組的文件、資產、快照、當前專案或 release 權限。</p>']
parts += ['<pre>'+esc(x)+'</pre>' for x in diagrams]
parts += ['<p>交易：綁定 source/spec/artifact/environment → 確認 disposable ownership → 執行核准操作 → 比對觀察／原始 hash → 保存證據 → 只清理明確屬該 run 的資料。此輪只交付規劃，未走原生執行交易。</p></section><section><h2>F1：可量測回應性預設</h2><p>既有需求是快照寫入不阻塞 UI。以下數字為建議驗收 profile，尚未成為產品 SLA。</p><ul><li>30 秒內30次普通選取操作；至少3次輸入在已證實的寫入區間內。</li><li>端到端保守上界延遲：p95 ≤250ms，最大值 ≤1000ms；兩者包含等號。</li><li>nearest-rank p95；整數 monotonic microseconds；事件／frame 時間校準不確定度 ≤20ms。</li><li>沒有可證明寫入區間、重疊不足或錄影失真時為 BLOCKED_OBSERVATION；不擅自增加 sleep／fault hook 或宣稱產品失敗。</li></ul><p>選取兩個既有 fixture 物件 A/B，確認各輸入對應的高亮／身份回應；選取本身不算內容變更。未提供 M07 核准觀察 seam 時，原生執行等待其架構提案，不能由 M08 私加接口。</p><p><a href="responsiveness-plan.json">完整量測／fixture／分類規則</a> · <a href="responsiveness-oracles.json">8個邊界 oracle（未執行）</a></p><table><tr><th>邊界例</th><th>預期 p95／max µs</th><th>預期分類</th></tr>']
for x in metric:parts.append('<tr><td>'+esc(x['id'])+'</td><td>'+esc(str(x['expected_p95_us'])+' / '+str(x['expected_max_us']))+'</td><td>'+esc(x['expected'])+' · NOT RUN</td></tr>')
parts += ['</table></section><section><h2>F2：精確 validator 契約與 fixture</h2><p>提議 H1 只做純資料檢查；輸出只有 SCHEMA_VALID／REJECTED 及精確 issue，證據等級固定 SCHEMA_UNIT。它不回傳 native PASS，也不驗證虛構檔案／PID實際存在。所有示例的 record 與 context 均為虛構 unit vectors，外層明示 SYNTHETIC；不得用來啟動程式或彙總原生驗收。</p><pre>'+esc(validation['entry_signature'])+'</pre><p>採 immutable input、固定第一錯誤優先序及 RFC6901 path。完整 base record、binding facts、case policy 可直接讓後續核准測試具體化，不再靠模糊文字猜預期。</p><p><a href="synthetic-base.json">完整 synthetic base/context/policy</a> · <a href="validator-contract.json">型別、優先序、error code、允許能力</a> · <a href="validator-positive-boundaries.json">14個正例／邊界向量</a></p><table><tr><th>BDD／TDD</th><th>精確 mutation</th><th>唯一第一錯誤 oracle</th></tr>']
for x in vectors:parts.append('<tr><td>'+esc(x['bdd'])+'<br>'+esc(x['test_name'])+'<br>'+esc(x['invariant'])+'</td><td>'+esc(json.dumps(x['mutations'],ensure_ascii=False))+'</td><td>'+esc(x['expected']['issue']['code'])+'<br>'+esc(x['expected']['issue']['pointer'])+'<br>輸入不變；NOT RUN</td></tr>')
parts += ['</table><p><a href="validator-negative-vectors.json">12個完整輸入／mutation／error向量</a> · <a href="module.feature">Gherkin</a> · <a href="step-definition-stubs.json">步驟與待自動化項目</a></p><p>後續命令：<code>python -m pytest tests/test_p1_portable_acceptance.py -k m08_claim -q</code>，cwd D:/AIAD。目標尚未建立，不能執行此命令充作 RED。需先整包核准，再建 Skeleton、fixture health、可編譯／可載入有效 RED，驗收後才按持續授權實作。</p></section><section><h2>F3：目前依賴與歷史追溯</h2><p>M01-S2 D1～D7已採納，核准範圍已 GREEN／驗收 PASS；S3六步精靈、native selection、owner/idempotency/IPC 仍未完成，所以 M01 native-ready=false。舊 awaiting confirmation 只是歷史，不重問已確認決策。</p><p><a href="current-prerequisites.json">目前依賴 overlay</a> · <a href="../../../M01/planning/s2-green/index.html">M01-S2 實測報告</a></p><p>其餘 M02-S1／M05-S1／M07-S1純領域完成不等於完整 native runtime；目前仍無 eligible current portable build／Windows11 native gate。這些不阻礙純準備文件複驗。</p></section><section><h2>集中一次審查的建議</h2><table><tr><th>建議項目</th><th>內容</th><th>狀態</th></tr>']
for x in decisions:parts.append('<tr><td>'+esc(x['id'])+'</td><td>'+esc(x['proposal'])+'</td><td>'+esc(x['status'])+'</td></tr>')
parts += ['</table><p>以上是新精確建議；沒有待重新確認的 M01-S2 決策。是否轉入 H1 Skeleton 需此包整體採納。文件複驗可先執行，不要求完成原生產品。</p></section><section><h2>範圍、驗收與模組狀態</h2><p>目前允許寫入僅 M08/planning 與本卡證據。採納後候選也只有單一 <code>tests/test_p1_portable_acceptance.py</code>；fixture literals／private helpers 同檔，額外 fixture路徑另需明列。沒有任何產品、Port、schema、UI、封裝或其他模組檔案範圍。</p><p>文件靜態結構、12個mutation的重現、14個正例／邊界資料、8個整數oracle算式已核對；這不是實際 validator/metric test PASS。完整準備卡補正待複驗，父卡保持黃燈；module_complete=false。</p><p>796來源雜湊、branch/HEAD一致。歷史 harness-contract/native-evidence-plan/full-preparation-acceptance 內容與hash保留。無commit/push／發布。</p><a href="verification.json">交付驗證</a> · <a href="envelope.json">候選範圍</a></section>',
 '<script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('</','<\\/')+'</script></html>']
(HERE/'index.html').write_bytes(''.join(parts).encode('utf-8'))
write('artifact-hashes.json',{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in HERE.iterdir() if f.is_file() and f.name!='artifact-hashes.json'})
print(json.dumps({'status':delivery['status'],'negative_vectors':len(vectors),'positive_boundary_vectors':len(positives),'metric_vectors':len(metric),'source_unchanged':796},ensure_ascii=True))
