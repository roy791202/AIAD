from pathlib import Path
import json, hashlib, re, subprocess, html
ROOT=Path(__file__).resolve().parents[6]
OUT=Path(__file__).resolve().parent
BASE=Path('docs/requirements-confirmation/phase1-spec')
def read(p): return (ROOT/p).read_text(encoding='utf-8-sig')
def load(p): return json.loads(read(p))
def write(n,v): (OUT/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
original=read(BASE/'index.html')
embedded=json.loads(re.search(r'<script[^>]*type="application/json"[^>]*>(.*?)</script>',original,re.S).group(1))
packet=load(BASE/'tasks/PD-P1-F10-DELIVERY-01.json')
feature=next(x for x in embedded['features'] if x.get('id')=='F10')
text=read(BASE/'phase1.feature')
scenarios={}
for sid in ['07','08','19','20','21','26','31']:
 m=re.search(r'  @BDD-'+sid+r'\b.*?(?=\n  @BDD-|\Z)',text,re.S)
 scenarios['BDD-'+sid]=m.group(0).rstrip()
write('original-authority.json',{'feature':feature,'task':packet,'requirements':[x for x in embedded['requirement_traceability'] if 'F10' in x['feature']],'scenarios':scenarios,'original_result':'PLANNED_NOT_RUN'})
sources=[Path('AGENTS.md'),Path('docs/board.json'),BASE/'index.html',BASE/'phase1.feature',BASE/'fixtures.json',BASE/'tasks/PD-P1-F10-DELIVERY-01.json',BASE/'tasks/M04/planning/current-state.json',BASE/'tasks/M04/planning/exact-design/module-spec.json',BASE/'tasks/M04/planning/exact-design/s1-green/verification.json',BASE/'tasks/M04/planning/exact-design/independent-review/review.json',BASE/'tasks/M06/planning/exchange-exact-design/module-spec.json',BASE/'tasks/M06/planning/merge-record-consistency-review/review.json',BASE/'tasks/M06/planning/merge-retention-review/review.json',BASE/'tasks/M03/planning/undo-correction-review/review.json',BASE/'tasks/M03/planning/undo-response-correction/module-spec.json',BASE/'tasks/M04/planning/save-retention-observation-review/review.json',BASE/'tasks/M01/planning/s2-green/source-current.json',Path('apps/sgenaxis-desktop/crates/sgenaxis-work/src/document_edit.rs'),Path('apps/sgenaxis-desktop/crates/sgenaxis-work/tests/phase1_document_history.rs'),Path('apps/sgenaxis-desktop/ui/app.js')]
bindings=[]
for p in sources:
 if not (ROOT/p).exists(): raise RuntimeError(str(p))
 lines=read(p).splitlines()
 hits=[{'line':i,'text':line[:280]} for i,line in enumerate(lines,1) if any(k.lower() in line.lower() for k in ['clear','undo','222','pending','form','rollback'])][:40]
 bindings.append({'path':p.as_posix(),'sha256':sha(ROOT/p),'pointers':hits})
write('sources.json',bindings)
authority=load(BASE/'tasks/M01/planning/s2-green/source-current.json')
drift=[p for p,h in authority['source_hashes'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
write('source-integrity.json',{'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'inventory_head':authority['head'],'authority':'M01/planning/s2-green/source-current.json','entries':len(authority['source_hashes']),'drift':drift,'interpretation':'Current 796-file byte comparison only; historical 31babe inventory HEAD is not current HEAD or runtime evidence.'})
rows=[
 ('F10-T01','REQ-15','BDD-20','exact scenario equivalence','clear then one Undo restores full content, hierarchy, relations and references; only this operation undone','m04_ex01_clear_commit_creates_one_complete_history_entry; m04_ex01_undo_restores_content_refs_bindings_and_restrictions','Pure S1 source and historical logs only. UI confirmation, full Form restoration and native linked projection not proved.'),
 ('F10-T02','REQ-15/16','BDD-21','exact scenario equivalence','successful single-document merge with pending binding then one Undo restores all changes and binding restrictions; source/shared materials preserved','DocumentSession pure restoration is reusable component evidence, not successful M06 merge admission','Latest M06 MR-F1 document correction does not supply native merge/Undo history or real asset roots.'),
 ('F10-T03','REQ-15','BDD-19','shared regression, not BDD-20 equivalence','any merge commit stage failure returns full prior document/material state, source unchanged, zero new Undo','X04/X06 failure injection pending','No rollback weakening: all commit stages must be enumerated by approved transaction; not only selected model cases.'),
 ('F10-T04','REQ-16','BDD-31','shared roots regression, not clear scenario','do not reclaim still-referenced material','M05 roots and M03/M06 documentary handoffs','Provider identity, root freshness/fence and lifecycle outcomes remain proposals/premises; no physical cleanup authorization.'),
 ('F10-T05','REQ-07','BDD-07/08','contextual lifecycle regression only','save-failure switch protection and cancel-close preservation','X04','These original scenarios do not describe clear cancellation or compound Undo; cannot claim equivalence.'),
 ('F10-T06','REQ-20','BDD-26','cross-module regression only','capture waits until clear/merge/Undo completes or fully rolls back','M07 stable capture planning','No scheduling/native integration run.'),
 ('F10-T07','REQ-15','none','prospective AC10 recipe; no invented BDD ID','clear and merge Undo cause snapshot content re-evaluation; source package unchanged','proposed F10-AC10-SNAPSHOT','Original AC10 obligation exceeds exact BDD-20/21 text. Requires approved test seam, no new timer/provider semantics.'),
 ('F10-T08','REQ-15','none','prospective original-feature/UI recipe; no invented BDD ID','preview clear scope then confirm or cancel; one operation history; restore Form and linked state','proposed F10-UI-CONFIRM','Current design-only local UI handler is source observation, not complete M04 feature or native proof.')]
trace=[dict(zip(['id','requirement','bdd','mapping','oracle','existing_test_or_recipe','gap'],r),acceptance='AC10',status='PLANNED_NOT_RUN') for r in rows]
recipes=[]
for r in trace:
 recipes.append({'id':r['id'],'status':'PLANNED_NOT_RUN','fixture':'isolated current-session document A with Form root/children, architecture hierarchy/relations, task content, pending bindings and blocked capabilities; document B sharing material V; read-only source BIN; operation-new material N; earlier history entry H0; before/after semantic manifest and source byte hashes','action':r['oracle'],'oracle':r['oracle']+'; compare whole canonical payload, Form hierarchy, linked-state projections, references/bindings/restrictions, exact history delta, source/shared hashes and unaffected B','negative_control':'deliberately omit one restored linked field / preserve an unwanted history entry / mutate shared material; oracle must reject','next_command':'PENDING_OWNER_ENVELOPE_AND_APPROVED_SKELETON: bind actual runner and test file before adding product test; do not guess cargo target','existing_read_only_candidate':'cargo test --manifest-path apps/sgenaxis-desktop/Cargo.toml -p sgenaxis-work --test phase1_document_history (NOT RUN; existing pure component suite only)','valid_red':'Only after approved envelope/Skeleton: runner builds and test fails at intended missing F10 behavior assertion. Compile/environment/fixture/model failure is not valid RED. Existing GREEN or historical RED is not new F10 RED.'})
write('pending-recipes.json',recipes)
data={'feature':'F10','primary_module':'M04','state':'PLANNED_NOT_RUN','zone':'gray','dependencies':packet['dependencies'],'original_acceptance':packet['acceptance'],'trace':trace,'authority_boundary':'Original feature/REQ/BDD/AC remain unchanged. No new Redo/Undo/provider semantics; no softened partial-failure rollback. D11 proposal is not blanket approval.','evidence_limits':['Historical S1 24 focused / 73 work tests and independent review are pure component evidence; historical 222/model results cannot prove native full UI clear+Undo. No suites rerun.','Current UI app.js cmdUidesignRecoveryPreview/Confirm/Undo uses local design recovery and existing Redo; observing it adds no Redo requirement or authority.','M06 merge-record-consistency-review closes documentary MR-F1 only, MH1–MH6 pending Owner. Earlier merge-retention findings preserved in provenance, not treated as current unresolved MR-F1.','M03 undo-correction-review closes declared documentary corrections only; full Draft missing, Owner not adopted, Skeleton not created.','M04 save retention observation is separate deferred documentation/gates; it does not authorize F10 retained-history/provider implementation.'],'not_run':['new product tests','valid RED','build','native UI','independent acceptance','full Draft','full module regression'],'next_action':'Owner/exact envelope and cross-module transaction/retention decisions → approved Skeleton/test seams → actual fixtures and compile-valid RED → bounded implementation → independent verification. Gray retained; no Done, no module/feature PASS.'}
write('trace.json',data)
links=''.join('<li><a href="../../../../../../'+html.escape(s['path'])+'">'+html.escape(s['path'])+'</a> SHA256 '+s['sha256']+'</li>' for s in bindings)
body='<h1>F10 清空與複合 Undo｜original-scope preparation</h1><p>Gray retained · PLANNED_NOT_RUN · static packet only</p><p>'+html.escape(data['next_action'])+'</p>'
for k,v in data.items(): body+='<section><h2>'+html.escape(k)+'</h2><pre>'+html.escape(json.dumps(v,ensure_ascii=False,indent=2))+'</pre></section>'
body+='<h2>原始功能與情境（逐字）</h2><pre>'+html.escape(json.dumps({'feature':feature,'scenarios':scenarios},ensure_ascii=False,indent=2))+'</pre><h2>可執行前的 fixtures / oracle recipes</h2><pre>'+html.escape(json.dumps(recipes,ensure_ascii=False,indent=2))+'</pre><h2>Source hash links</h2><ul>'+links+'</ul>'
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>F10 trace preparation</title><style>body{font:16px/1.6 system-ui;max-width:1100px;margin:32px auto;padding:20px;background:#f5f6f8}section{background:white;padding:16px;margin:16px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}a{color:#24598a}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
print('Generated bounded F10 packet')


