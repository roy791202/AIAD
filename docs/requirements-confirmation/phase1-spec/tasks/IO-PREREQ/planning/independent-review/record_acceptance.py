from pathlib import Path
import json, sys, hashlib
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
PLAN = OUT.parent
sys.path.insert(0, str(ROOT))
from tools.board.board_core.snapshot_safe import load_snapshot_dict, mutate_snapshot_file, split_snapshot
from tools.board.board_core.json_store import FileLock

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

review = json.loads((OUT / 'review.json').read_text(encoding='utf-8'))
checks = json.loads((OUT / 'primary-checks.json').read_text(encoding='utf-8'))
assert review['verdict'] == 'PARTIAL'
for name, code in [('helper', 0), ('compile', 0), ('red', 101), ('regression', 0), ('work', 0)]:
    assert json.loads((OUT / (name + '.json')).read_text())['exit_code'] == code
verdict = {
    'date': '2026-11-01', 'task': 'PD-P1-IO-PREREQ-RED-01',
    'verdict': 'PARTIAL', 'execution_state': 'REPLAN_REQUIRED',
    'implementation_gate': 'NOT_READY_FOR_IMPLEMENTATION',
    'scope': 'Independent acceptance of Skeleton and RED only; product source and tests read-only',
    'source_head': checks['sha'], 'source_branch': checks['branch'],
    'source_manifest': '../skeleton-red/source-manifest.json',
    'gates': {'contract_type_skeleton': 'PASS', 'dependency_and_ownership_skeleton': 'PASS',
              'compile': 'PASS', 'observed_valid_red': '20/20 PASS', 'source_scope': 'PASS',
              'module_contract_branch_coverage': 'PARTIAL', 'private_protocol_freeze': 'ARCHITECTURE_GAP'},
    'executed_regressions': {'ports_adapters_library': '101 PASS', 'work': '73 PASS'},
    'not_run': ['IO product GREEN', 'Windows 11 acceptance', 'full system regression', 'packaging', 'release'],
    'independence': {'static_reviewer': '/root/io_independent_review', 'runtime_and_scope_reviewer': '/root',
                     'runtime_logs': ['helper.json', 'compile.json', 'red.json', 'regression.json', 'work.json']},
    'findings': [x['id'] for x in review['findings']],
    'required_next_steps': [
        'Planning only: freeze exact private journal/sidecar naming and binary layout/checksum/state/path-binding/limit handling; existing test encoding is candidate, not approved persistence SSOT.',
        'Then test-only: add missing existence, commit-record failure, restore verification, absent-target rollback, malformed/bounded journal and fresh-process/lifetime cases; harden fixture naming.',
        'Rerun compile-valid RED and independent coverage acceptance before any product implementation.'
    ],
    'prior_delivery_clarification': 'Earlier 18 scenarios / 20 valid RED means scenario-ID mapping and observed first assertions only; it does not establish complete module contract coverage.',
    'source_and_test_changes_this_review': 0,
    'review_tooling_note': 'Initial ad-hoc lib comparison used PowerShell Python default cp950 and failed decoding. Repeated explicitly with UTF-8 and passed; this was review tooling, never counted as RED.'
}
save(OUT / 'primary-adjudication.json', verdict)
overlay = {
    'module': 'file-commit', 'historical_spec': 'module-spec.json',
    'history_policy': 'Historical proposal/spec files preserved; this overlay supplies current lifecycle, not new architecture approval.',
    'owner_authority': ['Adopt IO-PREREQ exact design; Skeleton and valid RED only.',
                        'Independent acceptance of contract, architecture, tests and scope; do not implement product behavior.'],
    'approved_design_direction': 'IO-D1 through IO-D3 adopted; no request to reconfirm those directions.',
    'remaining_precision': 'Byte-level private protocol and exact path conventions were not frozen by the direction-only prose; candidate fixture choices must not silently extend approval.',
    'state': 'REPLAN_REQUIRED', 'acceptance': 'PARTIAL', 'product_implementation': 'NOT_AUTHORIZED',
    'evidence': 'independent-review/primary-adjudication.json', 'human_report': 'independent-review/index.html',
    'protected_production_files_unchanged': 780, 'allowed_source_files_unchanged_during_review': True,
    'recommended_followup': verdict['required_next_steps']
}
save(PLAN / 'current-state.json', overlay)

banner = '<aside style="padding:18px;border:2px solid #b27616;background:#fff3d5"><strong>2026-11-01 獨立驗收：PARTIAL / REPLAN_REQUIRED。</strong>骨架、六檔範圍、編譯及 20 項已觀察 RED 通過；完整契約分支及 journal 精確協定尚有差額，未取得產品實作入口。<a href="independent-review/index.html">獨立報告</a> · <a href="current-state.json">目前狀態資料</a>。下列原規劃狀態保留供追溯，不能作為目前狀態。</aside>'
path = PLAN / 'index.html'
text = path.read_text(encoding='utf-8')
text = text.replace('<h1>', banner + '<h1>', 1)
path.write_text(text, encoding='utf-8')
path = PLAN / 'skeleton-red/index.html'
text = path.read_text(encoding='utf-8')
note = '<aside style="padding:18px;background:#fff3d5"><strong>後續獨立驗收：PARTIAL。</strong>20 項第一失敗為有效 RED；不代表所有契約分支已覆蓋。實作入口為 REPLAN_REQUIRED。<a href="../independent-review/index.html">查看差額與獨立實測</a>。</aside>'
text = text.replace('<h1>', note + '<h1>', 1)
path.write_text(text, encoding='utf-8')

board = ROOT / 'docs/PROJECT-BOARD.html'
before = board.read_text(encoding='utf-8')
old = load_snapshot_dict(before)
ids = {'PD-P1-IO-PREREQ-PLAN-01', 'PD-P1-IO-PREREQ-RED-01'}
stamp = datetime.now(timezone.utc).isoformat()
def mutate(data):
    for task in data['tasks']:
        if task.get('id') not in ids:
            continue
        task['executionStatus'] = 'REPLAN_REQUIRED'
        task['zone'] = 'yellow'
        task['doneAt'] = None
        task['report'] = 'docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/planning/independent-review/index.html'
        task['note'] += f'\n[{stamp}] Independent acceptance PARTIAL: Skeleton contract/architecture/six-file scope PASS; fresh compile PASS; 20 observed valid RED; existing 101+73 PASS. NOT_READY_FOR_IMPLEMENTATION. IO-R1 exact private persistence protocol gap; IO-R2/R3 missing contract/parser branches; IO-R4 product lease lifecycle coverage; IO-R5 fixture uniqueness; IO-R6 current-state overlay supplied. Earlier 18/20 mapping is not full contract coverage. No product/test changes, no green/commit/push/dispatch. Windows11 NOT RUN. Evidence: {task["report"]}'
        task['updatedAt'] = stamp
        task['version'] = task.get('version', 0) + 1
mutate_snapshot_file(board, mutate, lock_factory=FileLock)
after = board.read_text(encoding='utf-8')
new = load_snapshot_dict(after)
assert (split_snapshot(before)[0], split_snapshot(before)[2]) == (split_snapshot(after)[0], split_snapshot(after)[2])
assert [x for x in old['tasks'] if x.get('id') not in ids] == [x for x in new['tasks'] if x.get('id') not in ids]
assert {k:v for k,v in old.items() if k!='tasks'} == {k:v for k,v in new.items() if k!='tasks'}
save(OUT / 'board-evidence.json', {'updated_ids': sorted(ids), 'shell_and_other_cards_and_root_fields_unchanged': True, 'zone': 'yellow', 'status': 'REPLAN_REQUIRED'})
print('PARTIAL acceptance recorded; only reports/current-state projection and own board cards updated')
