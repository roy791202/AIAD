"""Planning artifact only. Never executes product tests or changes authoritative inputs."""
from pathlib import Path
import json, hashlib, re, html, subprocess

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[5]
BASE = 'docs/requirements-confirmation/phase1-spec/'
def read(p): return (ROOT / p).read_text(encoding='utf-8-sig')
def digest(p): return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
def dump(name, value): (OUT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

original = json.loads(read(BASE+'tasks/PD-P1-F05-DELIVERY-01.json'))
spec = json.loads(re.findall(r'<script[^>]*application/json[^>]*>(.*?)</script>', read(BASE+'index.html'), re.S)[0])
feature = next(x for x in spec['features'] if x['id']=='F05')
authority_path = BASE+'tasks/M01/planning/s2-green/source-current.json'
authority = json.loads(read(authority_path))
drift = [p for p,h in authority['source_hashes'].items() if not (ROOT/p).exists() or digest(p)!=h]
assert len(authority['source_hashes'])==796 and not drift
head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip()
assert head=='5b709343a890503ebbe24a802e43cda5647df124'
W='apps/sgenaxis-desktop/crates/sgenaxis-work/'
A='apps/sgenaxis-desktop/crates/sgenaxis-adapters/'
P=BASE+'tasks/'
sources=[BASE+'index.html', BASE+'phase1.feature',BASE+'fixtures.json',BASE+'tasks/PD-P1-F05-DELIVERY-01.json','docs/board.json',authority_path,
 W+'src/document_edit.rs',W+'tests/phase1_document_history.rs', A+'src/file_commit.rs',A+'tests/phase1_file_commit.rs',
 'apps/sgenaxis-desktop/crates/sgenaxis-ports/src/file_commit.rs','apps/sgenaxis-desktop/crates/sgenaxis-host/src/scene_doc.rs','apps/sgenaxis-desktop/ui/app.js',
 P+'M04/planning/exact-design/independent-review/primary-adjudication.json',P+'M04/planning/exact-design/independent-review/work.stdout.txt',
 P+'M04/planning/exact-design/s1-green/green.stdout.txt',P+'IO-PREREQ/implementation/acceptance/verification.json',P+'IO-PREREQ/implementation/acceptance/independent-tests.txt',
 P+'M04/planning/s2-readiness-review/verification.json',P+'M04/planning/cx-revision-v3/shared-contract.json',P+'M04/planning/save-response-review/review.json',
 P+'M04/planning/save-retention-observation-review/review.json',P+'M03/planning/preservation-contract/codec-contract.json']
for p in sources: assert (ROOT/p).is_file(),p
evidence=[
 {'id':'E-S1','kind':'HISTORICAL_ACCEPTED_PURE_DOMAIN','pointers':sources[13:16], 'meaning':'S1 capture, semantic baseline, revision and complete undo semantics only; historical WORK73 plus independent seven M04 probes. No filesystem, reopen, UI, owner handoff or full feature proof.'},
 {'id':'E-IO','kind':'HISTORICAL_ACCEPTED_WINDOWS_ADAPTER_SCOPE','pointers':sources[16:18], 'meaning':'220 IO cases and classified adjacent regressions are historical adapter evidence. Overall PARTIAL_PENDING_WINDOWS11_AND_NATIVE_ALIAS_GATES; not current execution and not F05 integration.'},
 {'id':'E-UI','kind':'CURRENT_SOURCE_INSPECTION_ONLY','pointers':['apps/sgenaxis-desktop/ui/app.js:512','apps/sgenaxis-desktop/ui/app.js:1090','apps/sgenaxis-desktop/crates/sgenaxis-host/src/scene_doc.rs:76'], 'meaning':'confirmLeaveSceneIfDirty uses two confirms; saveSceneSgsToProject encodes XML, invokes scene_save, persists draft then clears dirty. Existing scene host write_atomic is not proof of proposed capture/checked-receipt/root/semantic ACK path. file_save saves host settings, not this feature.'},
 {'id':'E-S2','kind':'PROPOSAL_REPLAN_REQUIRED','pointers':sources[18:22], 'meaning':'S2 readiness remains NOT_READY_FOR_IMPLEMENTATION. CXv3 typed identities/raw-vs-semantic and save response/root transfer are design inputs, not native implementation. Save-retention independent 704 model probes are document-only pending Owner G1-G4; no issuer authenticity/persistence/concurrency/full Draft validation.'},
 {'id':'E-CODEC','kind':'PROPOSED_NOT_APPROVED_NOT_RUN','pointers':[sources[22]], 'meaning':'M03 preservation proposal retains recognized fields, rejects unknown/duplicates and checks number representation. It is not ESS/M03 adopted codec or roundtrip feature proof.'}
]
cases=[
 ('F05-P01','REQ-07',['BDD-07'],'AC05 reopen equality','Save/edit/close/reopen','A and B projects with distinct hierarchy, relations, references, supported UI fields and versioned materials; edit A then save and reopen in fresh session. Independent canonical semantic projection and exact expected references compare equal; undo history absent after reopen.','E-S1,E-UI,E-CODEC','Native codec/owner/persistence path and complete semantic oracle absent.'),
 ('F05-P02','REQ-07',['BDD-07'],'AC05 failed save preserves old valid file and dirty','Fail each save/Save As/replace stage','Start valid raw A0 plus dirty semantic A1. Inject encode, reserve, precommit, replace and uncertain/postcommit outcomes at adopted seams. Precommit old bytes/model/dirty unchanged and no leave. For committed/uncertain outcomes preserve truthful byte-state evidence; never assert unchanged old file where commit is known/uncertain. No ACK on IO error or mismatch.','E-IO,E-S2,E-UI','Exact failure seam/response mapping and adopted transaction boundary pending; no blanket rollback claim.'),
 ('F05-P03','REQ-07',['BDD-07','BDD-08'],'AC05 save unsuccessful cannot close/switch','Save / discard / cancel leave choices','Dirty A, target B; cancel retains A open/content; failed save retains A and blocks close/switch; discard abandons only current changes and preserves recovery snapshots. Clean document follows approved no-prompt decision only after adoption.','E-UI,E-S1','Existing two-confirm source does not prove close lifecycle or snapshot preservation; native fixtures needed.'),
 ('F05-P04','REQ-07',['BDD-07'],'AC05 A/B isolation','Target and owner identity fencing','Trusted A/B contexts, same relative file names, distinct UUID/session/generation; capture A then switch/rebind owner before completion. Receipt target identity/path, expected previous raw, new raw and transaction must match exact capture; mismatched owner receives no ACK/delivery. Native Windows alias/Win11 gates remain separate and unproved.','E-S2,E-IO','Adopt trusted target/provider and owner generation seam; no UI-supplied trusted booleans.'),
 ('F05-P05','REQ-07',['BDD-07'],'AC05 successful saved content baseline','Raw receipt → root transfer → semantic ACK','Captured semantic R10 differs from encoded file raw digest. Edit R11 during save. Verify exact file receipt, release IO lease, verify durable issuer-bound root transfer, then ACK captured revision+semantic to same owner. R11 stays dirty; formal save does not reset snapshot baseline. Unknown/deferred root keeps Held and no ACK; committed file may be CommittedAckDeferred.','E-S1,E-S2','Root provider persistence/issuer verification and response mapping pending Owner G1-G4; model booleans not a native oracle.'),
 ('F05-R20','REQ-15',['BDD-20'],'Original shared M04 regression, not new F05 AC','Clear then one Undo','Complete hierarchy/relations/versioned refs; clear then undo exactly once restores all and only that operation. Existing m04_ex01_undo_restores_content_refs_bindings_and_restrictions is pure S1 evidence; execute actual UI/owner path only in approved regression scope.','E-S1','Shared regression retained; not F05 full save feature-owned integration.'),
 ('F05-R21','REQ-15',['BDD-21'],'Original shared M04 regression, not new F05 AC','Merge then one Undo','Successful single-document merge with pending binding; undo restores whole prior content/restrictions and never deletes shared/source material. Generic S1 history tests are adjacent, not real merge/retention integration evidence.','E-S1,E-S2','Merge/binding provider integration belongs declared adjacent scope; no expansion of F05 authority.')
]
trace=[]
for tid,req,bdd,ac,behavior,recipe,ev,gap in cases:
 trace.append(dict(test_id=tid,requirement=req,bdd=bdd,acceptance_clause=ac,behavior=behavior,fixture_and_oracle_recipe=recipe,evidence=ev.split(','),gap=gap,status='PLANNED_NOT_RUN',level='L2 module contract + L3 real adapter + L5 native where applicable',test_target='PENDING_OWNER_ENVELOPE_AND_SKELETON',valid_RED='After approved exact envelope/Skeleton: target compiles exit0, then fails intended observable assertion for missing approved behavior; compile/fixture/environment failure is invalid RED. No product test has been created or executed.'))
packet={'identity':{'task':original['id'],'primary_module':'M04','feature':'F05','state':'PLANNING','zone':'gray','feature_verdict':'NOT_PROVEN','original_status':original['status']},
 'authority':{'head':head,'historical_authority_head':authority['head'],'authority_file':authority_path,'source_count':796,'drift':drift,'note':'796-file historical content authority verified against current files; HEAD is distinct from 31babe. Board is management state outside product authority.'},
 'original_packet':original,'original_feature':feature,'original_requirement_traceability':[x for x in spec['requirement_traceability'] if x['requirement'] in ['REQ-07','REQ-15']],
 'original_scenarios':[x for x in spec['scenarios'] if 'BDD-'+x[0] in original['bdd']['scenario_ids']],
 'scope':'Only new F05/feature-trace-preparation documents. Original allowed-files path differs; this preparation does not revise that production envelope or original statuses. Yellow dependencies unchanged; no product Skeleton/tests/BDD changes.',
 'evidence':evidence,'trace':trace,
 'gates':['Owner adopts exact codec/schema/target identity/owner/persistence and root-transfer response decisions; M04 sole DocumentOwner, M03 facade, M05 issuer remain explicit.','Review exact architecture/contract/BDD including original confirmed-vs-proposed boundaries and exact permitted files. No new Port/owner or behavior approved by this packet.','Approve three Skeletons and executable fixture/oracle/test targets, demonstrate valid intended RED, then separately authorize implementation.','Independent validation and native Win11/alias coverage remain required; no current feature/module PASS, Done, dispatch or release.'],
 'next_commands':[
 {'command':'python -B docs/requirements-confirmation/phase1-spec/tasks/F05/feature-trace-preparation/check_packet.py','purpose':'Static packet hashes/links/source integrity only'},
 {'command':'cargo test -p sgenaxis-work --test phase1_document_history','cwd':'apps/sgenaxis-desktop','status':'NOT RUN; future adjacent S1 regression, not F05 acceptance'},
 {'command':'cargo test -p sgenaxis-adapters --test phase1_file_commit','cwd':'apps/sgenaxis-desktop','status':'NOT RUN; requires historical helper/env protocol; do not infer feature coverage'},
 {'command':'PENDING: exact F05 runner/target after Owner envelope and Skeleton approval','status':'No guessed cargo target or executable pending product stub'}],
 'not_run':['product tests','build/package/install','native/UI/IPC','valid RED/GREEN','independent acceptance of this packet','full Draft 2020-12 conformance'],
 'next_action':'Owner review F05 P01-P05 recipes and original AC05; resolve dependencies and exact envelope/Skeleton before adding product tests. R20/R21 remain explicitly shared regression obligations.'}
dump('module-spec.json',packet)
dump('source-inputs.json',{'sources':[{'path':p,'sha256':digest(p)} for p in sources]})
links=''.join('<li><a href="'+html.escape('../../../../../../'+p[len(BASE):] if p.startswith(BASE) else '../../../../../../../../'+p)+'">'+html.escape(p)+'</a> — '+digest(p)+'</li>' for p in sources)
# All links are relative to the artifact; use relpath rather than inferred traversal.
import os
links=''.join('<li><a href="'+html.escape(os.path.relpath(ROOT/p,OUT).replace('\\','/'))+'">'+html.escape(p)+'</a> <code>'+digest(p)+'</code></li>' for p in sources)
body='''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>F05 原始功能追溯準備</title><style>body{font:16px/1.7 system-ui;max-width:1160px;margin:32px auto;color:#243245;background:#f5f7fa}section,header{background:white;padding:22px;margin:16px 0;border:1px solid #ccd4de}pre{white-space:pre-wrap;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccd4de;padding:10px;text-align:left;vertical-align:top}code{overflow-wrap:anywhere;font-size:12px}</style><header><h1>F05 ESS 編輯、正式保存與專案切換</h1><p>Gray 保留 · PLANNED_NOT_RUN · 功能未證明。這是原始 AC05 的證據缺口與測試準備，不是 S1／IO／文件模型的功能驗收。</p><p>靜態核對 PASS 只代表此文件一致與來源未漂移；產品測試、有效 RED、native、獨立驗收、完整 Draft 驗證均 NOT RUN。</p></header>'''
body+='<section><h2>原始功能與批准界線</h2><pre>'+html.escape(json.dumps(feature,ensure_ascii=False,indent=2))+'</pre><p>'+html.escape(packet['scope'])+'</p></section>'
body+='<section><h2>REQ → BDD → AC → TDD → 證據與缺口</h2><table><tr><th>追溯</th><th>可觀察行為、fixture 與 oracle</th><th>證據界線／缺口</th></tr>'
for row in trace:
 body+='<tr><td>'+html.escape(row['test_id']+' / '+row['requirement']+' / '+','.join(row['bdd'])+' / '+row['acceptance_clause'])+'</td><td>'+html.escape(row['fixture_and_oracle_recipe'])+'</td><td>'+html.escape(row['status']+'; '+row['evidence'].__str__()+'; '+row['gap'])+'</td></tr>'
body+='</table></section><section><h2>現況證據分層</h2>'
for e in evidence: body+='<h3>'+e['id']+' '+e['kind']+'</h3><p>'+html.escape(e['meaning'])+'</p>'
body+='</section><section><h2>下一步與有效 RED</h2><pre>'+html.escape(json.dumps({'gates':packet['gates'],'commands':packet['next_commands'],'valid_RED':trace[0]['valid_RED']},ensure_ascii=False,indent=2))+'</pre></section><section><h2>原始來源與 SHA-256</h2><ul>'+links+'</ul></section>'
body+='<script type="application/json" id="module-spec">'+json.dumps(packet,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
(OUT/'index.html').write_text(body,encoding='utf-8')
dump('seal.json',{'artifacts':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name not in ['seal.json','static-verification.json']},'trace_rows':len(trace),'feature_owned_plans':5,'adjacent_regressions':2,'status':'SEALED_PLANNING_ONLY'})
print('Generated F05 planning packet: 7 trace rows; 796 protected source hashes unchanged.')


