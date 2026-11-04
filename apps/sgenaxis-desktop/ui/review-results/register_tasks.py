"""Register the authorized review batch without changing the board HTML shell."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'board'))
from board_core import domain, snapshot_safe

NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
PARENT = 'PD-RUST-IMPROVE-20261025'
ROWS = [
    (PARENT, 'Rust 正式工作檔改善與獨立驗證', 'epic', 'yellow', 'integration', 'Module tasks own their contracts; no release or architecture approval implied.'),
    ('PD-RUST-PATH-SAFE-01', 'HOST：阻擋 Windows 磁碟前綴路徑逃逸', 'task', 'yellow', 'HOST', 'Allowed: uidesign_doc.rs, scene_doc.rs, reports/rust-improvements/path-safety/. Preserve API and project-scoped contract. Prove behavioral RED before minimal fix.'),
    ('PD-RUST-REPORT-ISO-01', 'REPORT：隔離並行報告輸出', 'task', 'yellow', 'REPORT', 'Allowed: src-tauri/src/pd_report_call.rs, reports/rust-improvements/report-isolation/. Preserve DTO and report semantics. Reproduce shared-output collision before fix.'),
    ('PD-RUST-EXEC-PLAN-01', 'EXEC：Guard/MCP 實作邊界重規劃', 'task', 'yellow', 'EXEC', 'Analysis only. Allowed: reports/rust-improvements/exec-envelope/. No production changes. Deliver architecture views, contracts, BDD and test plan.'),
    ('PD-RUST-ADAPTER-PLAN-01', 'ADAPTERS：輸出生命週期與原子寫檔規劃', 'task', 'yellow', 'ADAPTERS', 'Analysis only in reports/rust-improvements/exec-envelope/. No std_process.rs/std_fs.rs edits; identify lifecycle and transaction decisions.'),
    ('PD-RUST-EXEC-DEC-01', '決策：核准 Guard/MCP 與 Adapter 新骨架', 'decision', 'red', 'EXEC', 'REPLAN_REQUIRED. 待決策事項: Guard enforcement scope and authoritative approval source; real MCP transport versus NOT RUN; EOF/cancel lifecycle; concurrent file-write guarantees. Dependent production implementation remains blocked pending owner approval.'),
    ('PD-RUST-TDD-GATE-01', '獨立 TDD Gate：Rust 改善批次', 'task', 'gray', 'verification', 'Read-only independent tests after implementation handoff. Review two fixes and planning packets. Never alter production/tests or promote board green.'),
    ('PD-RUST-GIT-HYGIENE-01', '正式 Rust 原始碼版本管理與 target 忽略範圍', 'task', 'gray', 'repository', 'Follow-up only; no git add/commit/push authorized by this batch. Confirm desired tracked files and generated-output exclusion.'),
]

def mutate(data):
    existing = {t['id'] for t in data.get('tasks', [])}
    added = []
    for ident, title, kind, zone, module, scope in ROWS:
        if ident in existing:
            continue
        fields = dict(id=ident, ref=ident, title=title, kind=kind, zone=zone,
            bdd='Given approved existing module boundaries, when this slice executes, then evidence matches observable behavior and failures remain explicit.',
            tdd='Behavioral RED -> focused GREEN -> module regression -> independent review. Planning-only tasks: implementation NOT RUN.',
            note=f'Parent: {PARENT}\nPrimary Module: {module}\nUser authorized parallel execution 2026-10-25.\n{scope}\nAC: preserve contracts, no weakened assertions, report evidence and risks in module HTML. No commit/push/release; no self-green. Protected: all files outside declared scope. Dependencies: independent gate after fix reports.\nPreview: http://127.0.0.1:8770/index.html?v=treeactions is static HTTP, not Tauri IPC.\n本批已建卡: '+', '.join(r[0] for r in ROWS))
        data.setdefault('tasks', []).append(domain.new_task(fields, 'agent', NOW))
        added.append(ident)
    data['asOf'] = NOW
    return added

if __name__ == '__main__':
    board = ROOT / 'docs' / 'PROJECT-BOARD.html'
    result = snapshot_safe.mutate_snapshot_file(board, mutate)
    snapshot_safe.assert_shell_intact(board.read_text(encoding='utf-8'))
    print(result)
