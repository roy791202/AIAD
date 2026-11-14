"""Snapshot formal desktop sources without third-party dependencies."""
import hashlib
import html
import json
import pathlib
import subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = pathlib.Path(__file__).resolve().parent
DESKTOP = ROOT / 'apps/sgenaxis-desktop'
EXCLUDE = {'target', 'node_modules', 'dist', 'gen', '__pycache__', '.git', 'review-results'}
EXCLUDE_FILES = {'ui/rust-improvements.html'}


def git(*args):
    result = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return result.stdout.rstrip()


def snapshot():
    files = []
    # Prune output directories before descent; avoid scanning Cargo artifacts.
    import os
    for directory, folders, names in os.walk(DESKTOP):
        folders[:] = sorted(name for name in folders if name not in EXCLUDE)
        for name in sorted(names):
            path = pathlib.Path(directory) / name
            if path.relative_to(DESKTOP).as_posix() in EXCLUDE_FILES:
                continue
            if path.suffix.lower() in {'.log', '.pyc'} or name == '.DS_Store':
                continue
            files.append({'path': path.relative_to(ROOT).as_posix(),
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    files.sort(key=lambda item: item['path'])
    locks = [item for item in files if item['path'] in {
        'apps/sgenaxis-desktop/Cargo.lock', 'apps/sgenaxis-desktop/src-tauri/Cargo.lock'}]
    if len(locks) != 2:
        raise RuntimeError('Both effective lockfiles are required')
    return {
        'module': 'rust-baseline', 'task': 'PD-RUST-BASELINE-CI-01',
        'status': 'REVIEW_PENDING', 'generated_at': datetime.now(timezone.utc).isoformat(),
        'head': git('rev-parse', 'HEAD'), 'branch': git('branch', '--show-current'),
        'git_status': git('status', '--short', '--untracked-files=all'),
        'files': files, 'effective_locks': locks,
        'excluded_output_directories': sorted(EXCLUDE),
        'excluded_output_files': sorted(EXCLUDE_FILES),
        'limitations': ['Sources include untracked and modified working files',
                        'No owner-approved source baseline commit',
                        'No clean checkout or remote CI proof',
                        'No packaging, install, DCC or live Agent verification'],
    }


if __name__ == '__main__':
    data = snapshot()
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    (OUT / 'source-manifest.json').write_text(payload + '\n', encoding='utf-8')
    rows = ''.join('<tr><td>' + html.escape(item['path']) + '</td><td><code>' +
                   item['sha256'] + '</code></td></tr>' for item in data['effective_locks'])
    document = '''<!doctype html><html lang="en"><meta charset="utf-8">
<title>Rust baseline proposal</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:20px}td{padding:8px;border:1px solid #ccc}code{overflow-wrap:anywhere}</style>
<h1>Rust baseline proposal</h1><p>Status: REVIEW_PENDING. Owner acceptance remains pending.</p>
<h2>Purpose and architecture</h2><p>Reproducible source inventory and independent Windows CI gates for the formal Rust desktop. No production boundaries, ports, state ownership or transaction semantics change.</p>
<h2>Contract and scope</h2><p>Preserve source and effective lock visibility; hide nested Cargo outputs. Existing CI, tests and production remain protected.</p>
<h2>Behavior and acceptance</h2><p>Git ignores Cargo outputs, preserves sources and locks. CI runs all three locked Cargo gates and fails on command failure. Independent acceptance tests map these requirements to executable checks.</p>
<h2>Effective locks</h2><table>''' + rows + '''</table>
<h2>Verification and traceability</h2><p>Locked acceptance: tests/test_rust_baseline_gate.py and baseline-tests/acceptance.json. Recorded RED: baseline-tests/red.txt. Focused implementation test output is recorded separately in focused-tests.txt; this document does not independently declare GREEN.</p>
<h2>Current tasks and results</h2><p>PD-RUST-BASELINE-CI-01: implementation submitted for independent review. Source manifest records SHA256 and Git/tree state. No staging, commit or push performed.</p>
<h2>Regression and risks</h2><p>Remote CI, clean checkout, build/package/install, DCC and live Agent checks: NOT RUN. Source baseline requires an owner-approved commit. Rust stable floats; resolved versions are recorded in CI. No MSRV claim.</p>
<h2>Deferred work and decisions</h2><p>Owner source selection, baseline commit and eventual remote run are deferred. Existing architecture is preserved; no new product behavior is authorized by this report.</p>
<h2>Module health</h2><p>PARTIAL: local acceptance evidence requires independent review; reproducible committed baseline is not established.</p>
<script type="application/json" id="module-spec">''' + payload.replace('<', '\\u003c') + '</script></html>'
    (OUT / 'module.html').write_text(document, encoding='utf-8')
    print(f"Recorded {len(data['files'])} files and {len(data['effective_locks'])} effective locks")
