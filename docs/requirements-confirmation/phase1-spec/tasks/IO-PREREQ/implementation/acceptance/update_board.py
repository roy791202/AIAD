import pathlib,json,copy,datetime,collections,sys
sys.path.insert(0,str(pathlib.Path.cwd()))
from tools.board.board_core.snapshot_safe import mutate_snapshot_file,split_snapshot,shell_halves
from tools.board.board_core.json_store import FileLock
R=pathlib.Path.cwd();A=R/'docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/implementation/acceptance';PL=A.parent.parent/'planning';now=datetime.datetime.now().astimezone().isoformat();report='docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/implementation/acceptance/index.html';card='PD-P1-IO-PREREQ-IMPL-01'
state_path=PL/'current-state.json';oldstate=json.loads(state_path.read_text(encoding='utf-8'));(A/'current-state.before.json').write_text(json.dumps(oldstate,ensure_ascii=False,indent=2),encoding='utf-8');state=copy.deepcopy(oldstate)
state.update({'state':'IMPLEMENTATION_ACCEPTED_CURRENT_HOST_PENDING_PLATFORM_GATES','acceptance':'PASS_IMPLEMENTED_SCOPE_ONLY_FULL_ACCEPTANCE_PARTIAL','evidence':'../implementation/acceptance/verification.json','human_report':'../implementation/acceptance/index.html','module_complete':False,'product_implementation_acceptance':{'verdict':'PASS_IMPLEMENTED_SCOPE_ONLY','overall':'PARTIAL_PENDING_WINDOWS11_AND_NATIVE_ALIAS_GATES','report':'../implementation/acceptance/index.html','fresh_IO_GREEN':220,'original_product_cases_retained':196,'regressions':'101+222+84 PASS','architecture':'PASS_WITHIN_APPROVED_ENVELOPE','source_unchanged_during_review':792,'reviewer':'same assistant, separate-turn read-only acceptance; no delegated reviewer','pending':['Windows11 x64 native acceptance','IO-A-F1 remaining reparse/8.3 native coverage']}})
state_path.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
board=R/'docs/PROJECT-BOARD.html';before=board.read_text(encoding='utf-8');s0=json.loads(split_snapshot(before)[1]);oldmap={t['id']:copy.deepcopy(t)for t in s0['tasks']}
def mutate(s):
 t=next(t for t in s['tasks']if t['id']==card);assert t['zone']=='yellow';t['executionStatus']='IMPLEMENTATION_ACCEPTED_CURRENT_HOST_PENDING_PLATFORM_GATES';t['report']=report;t['updatedAt']=now;t['version']=t.get('version',0)+1;t['updatedBy']='agent';t['moduleComplete']=False
 t['note']+='\n['+now+'] 產品實作獨立另輪唯讀驗收：PASS_IMPLEMENTED_SCOPE_ONLY。fresh IO220 GREEN、原196產品+19support逐byte保留且與已驗收test-alignment原檔SHA相符、Ports/Adapters101+WORK222+HOST84與build PASS；契約/架構/修改範圍PASS，本輪792產品檔未變。無新阻擋缺陷；同一助理，未另委派審查者。整體平台驗收仍PARTIAL：Windows11與reparse/8.3原生覆蓋維持待驗收，產品卡留黃、不填doneAt；不影響其他已就緒工項。報告：'+report
 t['implementationAcceptance']={'verdict':'PASS_IMPLEMENTED_SCOPE_ONLY','overall':'PARTIAL_PENDING_WINDOWS11_AND_NATIVE_ALIAS_GATES','report':report,'at':now,'source_test_changes':False,'pending_gates':['Windows11 x64','IO-A-F1 reparse/8.3']}
 t['evidence']['acceptance']='docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/implementation/acceptance/verification.json'
 t['remainingGap']='Only platform/native coverage gates remain for this product acceptance: Windows11 x64 and IO-A-F1 reparse/8.3 native tests. HOST integration remains separate future scope.'
 t['nextStep']='取得Windows11原生驗證與剩餘reparse/8.3覆蓋後再驗收完整平台gate；本次產品範圍驗收已PASS，不重跑相同已通過驗收充當進度；繼續其他就緒工項。'
 t.setdefault('log',[]).append({'t':now,'zone':'yellow','by':'agent','note':'Separate-turn read-only implementation acceptance PASS for implemented scope; platform/native alias gates still pending; no product/test edits.'})
mutate_snapshot_file(board,mutate,lock_factory=FileLock)
after=board.read_text(encoding='utf-8');s1=json.loads(split_snapshot(after)[1]);assert shell_halves(before)==shell_halves(after);assert {k:v for k,v in s0.items()if k!='tasks'}=={k:v for k,v in s1.items()if k!='tasks'}
for t in s1['tasks']:
 if t['id']!=card:assert t==oldmap[t['id']],t['id']
reviewed=next(t for t in s1['tasks']if t['id']==card);assert reviewed['zone']=='yellow' and reviewed.get('doneAt')==oldmap[card].get('doneAt')
c=lambda s:dict(collections.Counter(t['zone']for t in s['tasks']))
e={'at':now,'before':c(s0),'after':c(s1),'modified_card_only':card,'other_cards_unchanged':True,'root_metadata_unchanged':True,'html_shell_unchanged':True,'method':'mutate_snapshot_file + FileLock','pending_card_yellow':True,'doneAt_unchanged':True,'no_stage_false_closure':True};(A/'board-evidence.json').write_text(json.dumps(e,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(e,ensure_ascii=False))
