"""Append verifiable batch state; never promote owner-controlled green."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/board'))
from board_core import snapshot_safe, domain

NOW = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
notes = {
    'PD-RUST-IMPROVE-20261025': 'Parallel child agents dispatched. Two fixes ready; structural changes remain REPLAN_REQUIRED. Preview projection: http://127.0.0.1:8770/rust-improvements.html . Initial agents were launched before PM-AGENT ordering check; cards were subsequently registered, agents notified, and ordering deviation recorded. No green/commit/push.',
    'PD-RUST-PATH-SAFE-01': 'TDD_PASS yellow, owner acceptance pending. Independent HOST 74 unit + 3 integration PASS; Tauri full 74/74 PASS. reports/rust-improvements/independent-review/PD-RUST-PATH-SAFE-01-TDD-REVIEW.md . Junction/symlink containment NOT RUN. Historical RED is implementer-recorded, not independently replayed.',
    'PD-RUST-REPORT-ISO-01': 'TDD_PASS yellow, owner acceptance pending. Independent Tauri full 74/74 PASS and exact concurrency test 1/1 PASS. reports/rust-improvements/independent-review/PD-RUST-REPORT-ISO-01-TDD-REVIEW.md . Explicit same out_dir behavior unchanged; historical RED not independently replayed.',
    'PD-RUST-EXEC-PLAN-01': 'Planning packet delivered, production NOT RUN. reports/rust-improvements/exec-envelope/exec-dispatch.html . Owner approval pending PD-RUST-EXEC-DEC-01.',
    'PD-RUST-ADAPTER-PLAN-01': 'Planning packets delivered: process-adapter.html and filesystem-adapter.html in reports/rust-improvements/exec-envelope/. Existing ProcessPort allows lossy UTF-8; Unicode preservation is a contract clarification requiring approval, not proven violation. Production NOT RUN.',
    'PD-RUST-TDD-GATE-01': 'Independent gate TDD_PASS yellow. HOST 74+3, Tauri 74/74, concurrency exact 1/1 PASS. Two independent reviews and module.html delivered. No Port/API/ownership changes or weakened assertions found. Rust source currently untracked, so review uses actual content, not committed diff. No green transition.',
}

def mutate(data):
    for task in data['tasks']:
        ident = task['id']
        if ident not in notes:
            continue
        if ident == 'PD-RUST-TDD-GATE-01' and task['zone'] == 'gray':
            task.update(domain.apply_zone(task, 'yellow', 'agent', NOW))
        task['note'] += '\n[' + NOW + '] ' + notes[ident]
        task['version'] = int(task.get('version', 1)) + 1
        task['updatedAt'] = NOW
        task['updatedBy'] = 'agent'
    data['asOf'] = NOW

if __name__ == '__main__':
    snapshot_safe.mutate_snapshot_file(ROOT / 'docs/PROJECT-BOARD.html', mutate)
    print('Updated batch evidence notes; no green transitions')
