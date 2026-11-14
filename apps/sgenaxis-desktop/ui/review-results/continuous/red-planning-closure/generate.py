import json, html, hashlib
from pathlib import Path

p=Path(__file__).parent
refs={
 'historical_exec':'reports/rust-improvements/exec-envelope/exec-dispatch.html',
 'historical_fs':'reports/rust-improvements/exec-envelope/filesystem-adapter.html',
 'historical_proc':'reports/rust-improvements/exec-envelope/process-adapter.html',
 'historical_review':'reports/rust-improvements/architecture-review/module.html',
 'guard':'reports/rust-improvements/continuous/guard-authority-planning/module.json',
 'fs':'reports/rust-improvements/continuous/filesystem-persistence/module.json',
 'proc':'reports/rust-improvements/continuous/process-lifecycle/module.json',
 'mcp':'reports/rust-improvements/mcp-notrun/module.html',
 'fs_review':'reports/rust-improvements/continuous/filesystem-persistence-review/module.json',
 'proc_review':'reports/rust-improvements/continuous/process-review/module.json',
 'mcp_review':'reports/rust-improvements/mcp-notrun-review/module.html',
 'fresh_gate':'reports/dispatch-pd/fresh-fs-proc/summary.json'}
matrix={
 'A1-A14':'Current guard.architecture_A1_A14, fs.architecture, proc.architecture_A1_A14 plus report-only coordination supplement below. Historical umbrella is not implementation authority.',
 'two_views':'Historical exec-envelope/review boundary and dependency views; current FS/PROC/Guard concrete views; coordination views below.',
 'contracts':'FS-C1..6; INV-PROC01..08; MCP explicit NOT RUN; Guard proposed trust/binding/lifecycle contracts.',
 'BDD':'Existing child BDD; Guard BDD_test_plan_PROPOSED; coordination scenarios below.',
 'test_plan':'Existing frozen child tests and exact evidence; Guard proposed failure matrix. No tests rerun for planning audit.',
 'AC':'Measurable child acceptance and report-only planning criteria below; owner acceptance separate.',
 'owner_inputs':'FS/PROC/MCP minimal decisions approved; Guard authority/producer/native confirmation/one-shot policy remain unapproved.'}
coord={
 'A1':'Context: coordinate bounded child modules; no runtime subsystem.',
 'A2':'Owner input -> planning/review -> report projection; child production boundaries separate.',
 'A3':'Coordinator reads child specs/evidence; reports never grant authority.',
 'A4':'Owner approves; child implements; independent agent tests/reviews; coordinator reconciles.',
 'A5':'Input: existing owner messages and board task scopes, no new API.',
 'A6':'Output: existing structured reports/HTML and proposed parent disposition, no new port.',
 'A7':'Driving: owner/chat and existing board read surface.',
 'A8':'Driven: report filesystem only; parent board writes use existing snapshot_safe.',
 'A9':'Dependencies: authoritative specs/evidence -> derived coordination views.',
 'A10':'Board owns task state; specs own semantics; report is projection only.',
 'A11':'Mutation: this audit report files only; child approved file scopes remain fixed.',
 'A12':'Transaction: bind task/artifact revisions, reconcile, publish; drift means stale. No new runtime transaction.',
 'A13':'External: no Agent/provider/native control execution.',
 'A14':'Forbidden: production edits, new Manager/port/dependency, silent schema/API/approval, weaker tests, self-green, commit/push.'}
guard_inputs=[
 'Owner approve/reject session-only native confirmation/caller trust boundary and one-shot consume/spawn-failure/revoke lifecycle.',
 'Name trusted current fingerprint producer and qualified behavioral RED producer/classifier.',
 'Approve exact caller capability/nativecallback separation, task-intent ownership and artifact manifest/current-source/serialization seams before Guard skeleton.']
cards=[
 {'id':'PD-RUST-EXEC-PLAN-01','status':'PLAN_COMPLETE_REVIEW_PASS','references':['historical_exec','historical_review','mcp','mcp_review','guard'],'disposition':'Historical EXEC umbrella planning superseded by completed approved MCP NOTRUN slice and refined Guard proposal. Do not redispatch umbrella as production.','subproposal':'PROPOSAL_NEEDS_OWNER: Guard','missing':'No further generic umbrella planning needed. Exact authority/producer decisions remain owner inputs, not missing implementation to invent.'},
 {'id':'PD-RUST-ADAPTER-PLAN-01','status':'PLAN_COMPLETE_REVIEW_PASS','references':['historical_fs','historical_proc','fs','proc','fs_review','proc_review','fresh_gate'],'disposition':'Historical FS/PROC alternatives superseded by separately approved bounded child packets and independent implementation gates. No duplicate adapter work.','subproposal':'Completed approved slices await owner acceptance.','missing':'None for original planning AC. Stronger Unicode, process-tree/buffering or crash durability are separate future requirements, not promised here.'},
 {'id':'PD-RUST-ARCH-REVIEW-01','status':'PLAN_COMPLETE_REVIEW_PASS','references':['historical_review','guard','fs_review','proc_review','mcp_review'],'disposition':'Historical independent review delivered four exact decisions. FS/PROC/MCP resolved through later owner-approved slices; Guard refined but still needs owner choices. Preserve dated historical report.','subproposal':'PROPOSAL_NEEDS_OWNER: Guard; review deliverable complete.','missing':'No new architecture review merely to rewrite history. This report supplies current decision disposition links.'},
 {'id':'PD-RUST-CONTINUOUS-01','status':'PLAN_COMPLETE_REVIEW_PASS','references':['guard','fs','proc','fresh_gate'],'disposition':'Coordinator folder had heartbeat projection only; minimal A1-A14, two views, contract/BDD/testplan/AC now supplied here. No new coordination framework.','subproposal':'Child decision gates remain independent.','missing':'Previous consolidated report-envelope gap closed by this report-only supplement; owner must select unresolved child proposals.'}]
s={'module':'red-planning-closure','phase':'PLANNING_COMPLETENESS_REVIEW','date':'2026-10-26 Asia/Taipei','status':'PLAN_COMPLETE_REVIEW_PASS for four planning/review deliverables; Guard PROPOSAL_NEEDS_OWNER','runtime':'This is NOT TDD_PASS or architecture approval. Real MCP transport remains unapproved; completed MCP NOTRUN composition is a separate bounded slice. No tests rerun. Source presence is not runtime proof; historical child evidence cited only. No original report rewritten.','references':refs,'artifact_sha256':{k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in refs.items()},'completeness_matrix':matrix,'coordination_a1_a14':coord,'diagram_A':'Owner intent/approval -> bounded planning input -> Codex report/review -> owner decision\nSeparately approved child skeleton+RED -> bounded execution -> independent tests/review -> owner acceptance\nReports never grant execution permission.','diagram_B':'Architecture/contract/BDD + frozen tests/result hashes + board task scope\n  -> child module report -> coordination projection -> owner\nFS/PROC/MCP child owners remain separate. Guard unresolved authority has no approval backedge.\nParent alone applies authorized snapshot_safe board disposition.','contracts':['CO-C1: unresolved child decision permits planning only, no production.','CO-C2: one primary module, exact allowed/protected files, frozen tests and independent gate per child.','CO-C3: report distinguishes proposal/approval/implementation/test/acceptance and preserves historical facts.','CO-C4: artifact drift invalidates reconciliation; no self-approval/green/commit/push.'],'bdd':[{'given':'Unresolved child architecture decision','when':'Coordinator chooses next work','then':'Advance concrete planning only; no production.'},{'given':'Approved skeleton and verified RED','when':'Bounded implementation is dispatched','then':'Child scope/contracts/tests stay fixed.'},{'given':'Independent GREEN and review evidence','when':'Status is reported','then':'Cite exact hashes and leave acceptance to owner.'},{'given':'Historical umbrella superseded by specific approved slices','when':'Planning is reviewed','then':'Close planning deliverable without duplicate implementation; unresolved choices remain explicit.'}],'test_plan':['Read-only task/ref/hash reconciliation; no orphan dispatch.','Check scope/role separation and frozen evidence; disclose prior FS authorship.','Verify historical states do not erase later approvals or authorize future changes.','Report-only audit needs no fake behavioral RED or new runtime test framework.'],'AC':['All four cards map A1-A14/two views/contracts/BDD/testplan/AC to specific references or coordination supplement.','Each historical option mapped to approved child or exact owner input.','Concrete next decisions replace generic blocked-only report.','No source/test/board changes or new framework/runtime PASS claim.','Parent may accept planning without approving Guard.'],'cards':cards,'remaining_owner_inputs':guard_inputs,'implementation_authorized':False,'source_test_board_changes':False,'commit_push':False}
(p/'module.json').write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
b='<h1>Red planning completeness closure</h1><p>Four planning/review deliverables complete. Guard remains PROPOSAL_NEEDS_OWNER. No self-approval or runtime acceptance.</p>'
b+='<table border="1" cellpadding="8"><tr><th>Card</th><th>Planning verdict</th><th>Current disposition</th><th>Remaining</th></tr>'+''.join('<tr><td>'+r['id']+'</td><td>'+r['status']+'</td><td>'+html.escape(r['disposition'])+'</td><td>'+html.escape(r['subproposal'])+'</td></tr>' for r in cards)+'</table>'
for k,v in s.items(): b+='<h2>'+html.escape(k)+'</h2><pre>'+html.escape(v if isinstance(v,str) else json.dumps(v,ensure_ascii=False,indent=2))+'</pre>'
(p/'module.html').write_text('<!doctype html><html><meta charset="utf-8"><title>Planning closure</title><style>body{font:16px system-ui;max-width:1100px;margin:32px auto;line-height:1.6}pre{white-space:pre-wrap;background:#eef2f7;padding:16px}</style>'+b+'<script type="application/json" id="module-spec">'+json.dumps(s,ensure_ascii=False).replace('<','\\u003c')+'</script></html>',encoding='utf8')
for r in cards:
 (p/(r['id']+'-PLAN-REVIEW.json')).write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
 (p/(r['id']+'-PLAN-REVIEW.md')).write_text('# '+r['id']+'\n\n**'+r['status']+'** (planning only).\n\n'+r['disposition']+'\n\n## Completeness\n\n'+'\n'.join('- '+k+': '+v for k,v in matrix.items())+'\n\n## Remaining concrete gap\n\n'+r['missing']+'\n\n'+r['subproposal']+'\n\n'+('\n'.join(guard_inputs) if 'EXEC' in r['id'] or 'ARCH' in r['id'] else 'Owner acceptance/child decision selection remains separate.')+'\n\nSee [canonical report](module.json) / [human view](module.html) for exact source references/hashes. No tests rerun, original report rewrite, source/test/board edits or commit/push.\n',encoding='utf8')
print('Four planning closure cards written; Guard requires owner decisions.')
