"""F07 documentary preparation only. Run with python -B -X utf8."""
from pathlib import Path
import hashlib, json, html, subprocess

ROOT = Path(__file__).resolve().parents[6]
OUT = Path(__file__).resolve().parent
BASE = 'docs/requirements-confirmation/phase1-spec/'
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8-sig'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name, value): (OUT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
task=read(BASE+'tasks/PD-P1-F07-DELIVERY-01.json')
inventory=read(BASE+'tasks/M01/planning/s2-green/source-current.json')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
sources=['AGENTS.md','docs/board.json',BASE+'index.html',BASE+'phase1.feature',BASE+'fixtures.json',BASE+'tasks/PD-P1-F07-DELIVERY-01.json',BASE+'tasks/M01/planning/s2-green/source-current.json','apps/sgenaxis-desktop/ui/app.js','apps/sgenaxis-desktop/ui/index.html','tests/test_pd_scene_sgb_01.py','fixtures/sgenaxis-scene/sample.sgb','fixtures/sgenaxis-scene/sample.ess']
for directory,names in {
 'exchange-exact-design':['module-spec.json','test-plan.json','fixtures.json','envelope.json','module.feature','verification.json'],
 'cx-exchange-revision-v3':['module-spec.json','shared-contract.json'],
 'preflight-document-reacceptance':['review.json'],
 'merge-retention-review':['review.json'],
 'merge-record-consistency-review':['review.json'],
}.items():
 sources.extend(BASE+'tasks/M06/planning/'+directory+'/'+n for n in names)
put('inputs.json',{p:digest(ROOT/p) for p in sources})
rows=[]
def row(i,claim,bdd,kind,recipe,oracle,gap):
 rows.append(dict(id=i,requirement='REQ-09',acceptance='AC07',claim=claim,bdd=bdd,mapping_kind=kind,test_id='TDD-F07-PREP-'+i,fixture_recipe=recipe,oracle=oracle,gap=gap,status='PLANNED_NOT_RUN',command='BLOCKED_PENDING_OWNER_ENVELOPE_SKELETON_RUNNER',valid_red='Approved target compiles; controlled fixture reaches missing F07 behavior and fails the stated oracle. Compile/fixture/environment failures are invalid RED.'))
row('01','一般保存不自動輸出BIN',['BDD-11'],'EXACT_ORIGINAL_SCENARIO','Isolated established project, no package request; record destination tree and export invocation count; perform ordinary save once.','No BIN output or packaging invocation after ordinary save; native result and filesystem diff agree.','No current F07 runner/native fixture bound; source-only observations do not exercise this action.')
row('02','明確封裝含定義、ESS、UI及完整引用素材',['BDD-12'],'EXACT_ORIGINAL_SCENARIO','Project with definition+ESS+UI, two referenced immutable assets (including shared digest) and one unreferenced asset; capture revision; explicit package action.','Independent approved-format decoder compares actual payload bytes and reference closure with captured expected bytes; all required content present, list matches actual entries.','BIN-v1 proposed DocumentWithAssets framing must be reconciled with original full-project definition/ESS/UI scope; one document/payload is not assumed to satisfy all four categories.')
row('03','封裝前後來源hash不變',[],'PROSPECTIVE_AC_RECIPE_NOT_EXISTING_BDD','Immutable source copies and raw byte hash map for project definition, ESS, UI and assets; explicit export success and failure variants.','Before/after exact source file hashes equal; project/document semantic state unchanged; no silent save into source.','AC07 obligation not equivalent to BDD-09 (modify imported B copy) or BDD-18 (new-copy mapping); requires approved capture/read-only seams.')
row('04','內容清單與實際一致',['BDD-12'],'PARTIAL_BDD_PLUS_AC_RECIPE','After explicit export, independent decoder enumerates entries; compare manifest sizes/digests/content categories against fixed captured oracle.','Manifest entry set, decoded sizes and computed digests match actual bytes and original required categories; missing referenced asset cannot be advertised complete.','No independent BIN-v1 byte oracle or accepted format; legacy three-entry roundtrip is insufficient.')
row('05','取消不留下被誤認成功的包',[],'PROSPECTIVE_AC_RECIPE_NOT_EXISTING_BDD','Cancel before publication and at every approved export boundary; pre-existing destination A and fresh absent destination variants.','No success UI/result on cancel; no incomplete package presented as complete; source intact; destination replacement/cleanup policy pending exact Owner approval.','No original scenario explicitly tests export cancellation. BDD-19 merge rollback and BDD-08 close cancel are different actions, not substitutes.')
put('traceability.json',rows)
plan=read(BASE+'tasks/M06/planning/exchange-exact-design/test-plan.json')['cases']
related=[c for c in plan if any(w in c['title'].lower() for w in ['export','cancel','valid bin','asset','ess','source'])]
spec={
 'identity':{'feature':'F07','task':task['id'],'module':'M06','status':'PLANNING_ONLY_NOT_READY_FOR_IMPLEMENTATION','zone':'gray','dependencies_unchanged':task['dependencies'],'head':head,'historical_inventory_head':inventory['head']},
 'original_packet':task,
 'traceability':rows,
 'exact_scenario_equivalence':{'BDD-11':'ordinary save without package request → no automatic BIN','BDD-12':'explicit BIN package of project with UI+referenced assets → complete declared content'},
 'contextual_regression_only':{'BDD-09/10':'ESS independent-copy import and same-name choices; F08 action, not F07 export','BDD-13/14':'dangerous import/missing external dependency preflight; not export success','BDD-15/16/17/18/19':'single-document merge/identity/rollback; not F07 package proof'},
 'proposals_preserved':{'BIN_v1':'M06-X1..X7 and R1..R4 pending Owner. SGABIN1 LF framing and SGA-BIN-v1 manifest are proposals, not SGB1, not auto-approved ZIP. All proposed limits unchanged; none adopted here.','scope_gap':'Proposed DocumentWithAssets one-document archive cannot silently narrow original definition+ESS+UI+referenced-assets requirement. Owner must resolve project aggregate/profile mapping before Skeleton.','confirmed':'BIN content scope and on-demand output remain confirmed; exclude credentials/cache/machine settings and missing-asset/publication details retain original proposed status.'},
 'legacy_evidence':{'app':'app.js:321-324 SGB1/default.es/default.esml/default.esui; :359 pack; :377 unpack; :440 build three entries; :615 saveSceneBundleToProject sequential text saves; :650 downloadSceneSgb calls project save, not proved BIN download.','tests':'test_pd_scene_sgb_01.py:test_scene_sgb_ui_and_codec_hooks checks source strings; test_sample_sgb_fixture_roundtrip uses Python-local codec and writes sample.sgb. NOT RUN here to avoid fixture mutation. No JS execution/native export/parser proof.','fixtures':'sample.sgb legacy SGB1 bytes and sample.ess existing sample only; not proposed BIN-v1 oracle.'},
 'upstream_boundaries':{'preflight':'64/64 historical document-only acceptance; normalized report policy, not parser/export/native proof; R1-R4 pending.','merge':'Historical merge-retention MR-F1 nine documentary gaps followed by merge-record-consistency-review PASS_DOCUMENT_SCOPE_PENDING_OWNER 184/184 (160 new+24 reused), nine closures; trusted fixture authenticity remains assumed, MH1-MH6 pending. No merge behavior claimed as F07 proof.','asset':'M05 owns pin issuer/catalog integrity/root completeness and ArchiveExport purpose/proof. F07 consumes exact captured versions; must not mint pins or infer durable roots from resolution.','security':'M06 container/body integrity/security/path validation are module obligations; malformed containers/unsafe paths/missing internal payload cannot become external-dependency exceptions. Import preflight is adjacent regression, not packaging AC evidence.','ownership':'Domain/application use approved output Ports; UI→command→host→application→ports. Source owners M01/M04/M03/M05 retain state authority. No new Port or Skeleton approved by this packet.'},
 'existing_proposal_test_references':related,
 'next_action':'Owner/architect resolves full-project content versus DocumentWithAssets mapping, X1..X7/R1..R4 and exact cross-owner capture/export/pin/publication envelope. Then separately authorize Skeleton+runner+independent byte fixture; verify valid RED before production. Independent validation/review by different agents follows GREEN.',
 'not_run':['new product tests','independent review','build','package','native UI','valid RED','full Draft'],
 'static_pass_is_not':'Feature PASS, module PASS, approval, implementation permission, Done or board transition'
}
put('module-spec.json',spec)
put('pending-test-recipes.json',{'cases':rows,'pending_automation':['Bind exact approved test target after Skeleton; do not guess cargo target.','Create independent byte oracle for full-project approved BIN profile, not production encoder reused as decoder.','Isolated native UI/command export and cancel harness; no product runner added here.','Module contract + adjacent preflight/assets/path/body/integrity regressions then Windows native evidence.'],'assumptions':['No production envelope approved by this preparation.','Static existing source inspection cannot establish output transaction safety.'],'open_questions':['How does proposed one-document payload represent confirmed project definition+ESS+UI aggregate?','Which exact owner captures all four categories and immutable asset pin, and which export publication/cancel semantics are approved?']})
ptr=[]
for p,needles in [('apps/sgenaxis-desktop/ui/app.js',['const SGB_MAGIC','function packSgbBinary','function unpackSgbBinary','function buildSceneSgbBytes','async function saveSceneBundleToProject','async function downloadSceneSgb']),('tests/test_pd_scene_sgb_01.py',['def test_scene_sgb_ui_and_codec_hooks','def test_sample_sgb_fixture_roundtrip']) ,(BASE+'phase1.feature',['@BDD-11','@BDD-12','@BDD-09','@BDD-19'])]:
 lines=(ROOT/p).read_text(encoding='utf-8-sig').splitlines()
 for needle in needles:
  for n,line in enumerate(lines,1):
   if needle in line: ptr.append({'path':p,'line':n,'needle':needle,'sha256':digest(ROOT/p)}); break
put('source-pointers.json',ptr)
drift=[p for p,h in inventory['source_hashes'].items() if not (ROOT/p).is_file() or digest(ROOT/p)!=h]
put('source-integrity.json',{'authority':BASE+'tasks/M01/planning/s2-green/source-current.json','count':len(inventory['source_hashes']),'inventory_head':inventory['head'],'observed_head':head,'drift':drift,'claim':'Current hashes checked against historical authority; no claim of clean checkout.'})
body=html.escape(json.dumps(spec,ensure_ascii=False,indent=2))
links=''.join('<li><a href="../../../../../../'+html.escape(p)+'">'+html.escape(p)+'</a></li>' for p in sources)
embedded=json.dumps(spec,ensure_ascii=False).replace('</','<\\/')
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>F07 feature trace preparation</title><style>body{max-width:1100px;margin:35px auto;background:#101b2a;color:#e5edf8;font:16px system-ui}a{color:#83c5ff}pre{white-space:pre-wrap;line-height:1.5;background:#19283c;padding:20px}h1{color:#9cd6ff}</style><h1>F07 ESS交換與BIN按需封裝</h1><p>Gray retained · PLANNING ONLY · Feature / product / native / valid RED NOT RUN</p><p>原始要求不縮減。僅 BDD-11/12 為本功能原始情境；AC07 來源hash與取消為待批准測試配方，不能借用匯入或合併情境冒充等價。</p><h2>下一步</h2><p>'+html.escape(spec['next_action'])+'</p><h2>Architecture / behavior / verification / risks</h2><pre>'+body+'</pre><h2>Hash-bound sources</h2><ul>'+links+'</ul><script id="module-spec" type="application/json">'+embedded+'</script></html>',encoding='utf-8')
print('F07 preparation generated; source count',len(inventory['source_hashes']),'drift',len(drift),'trace rows',len(rows))
