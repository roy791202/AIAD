"""Project authoritative cards and agent reports into the existing static preview."""
from pathlib import Path
import html
import json
import shutil
import sys
import re
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools' / 'board'))
from board_core.snapshot_safe import split_snapshot

data = json.loads(split_snapshot((ROOT / 'docs/PROJECT-BOARD.html').read_text(encoding='utf-8'))[1])
tasks = [t for t in data['tasks'] if t['id'].startswith('PD-RUST-')]
out = ROOT / 'apps/sgenaxis-desktop/ui'
reports = []
report_root = ROOT / 'reports/rust-improvements'
shutil.copytree(report_root, out / 'review-results', dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
for path in sorted((ROOT / 'reports/rust-improvements').glob('**/*.html')):
    name = '-'.join(path.relative_to(ROOT / 'reports/rust-improvements').parts)
    target = out / 'review-results' / name
    target.parent.mkdir(parents=True, exist_ok=True)
    def linked_artifact(match):
        value = match.group(1)
        if ':' in value or value.startswith(('/', '#')):
            return match.group(0)
        linked = (path.parent / value.split('#', 1)[0]).resolve()
        if linked.is_file() and linked.is_relative_to(report_root.resolve()):
            fragment = '#' + value.split('#', 1)[1] if '#' in value else ''
            return 'href="/review-results/' + linked.relative_to(report_root).as_posix() + fragment + '"'
        return match.group(0)
    target.write_text(re.sub(r'href="([^"]+)"', linked_artifact,
                            path.read_text(encoding='utf-8')), encoding='utf-8')
    reports.append((str(path.relative_to(ROOT)), 'review-results/' + name))
esc = html.escape
rows = ''.join('<tr><td>'+esc(t['id'])+'</td><td>'+esc(t['title'])+'</td><td>'+esc(t['zone'])+'</td><td><details><summary>Scope / evidence</summary><pre>'+esc(t['note'])+'</pre></details></td></tr>' for t in tasks)
links = ''.join('<li><a href="'+esc(url)+'">'+esc(label)+'</a></li>' for label, url in reports)
payload = json.dumps({'source':'docs/PROJECT-BOARD.html#board-snapshot','generatedAt':datetime.now(timezone(timedelta(hours=8))).isoformat(),'tasks':tasks,'reports':reports},ensure_ascii=False).replace('<','\\u003c')
document = '''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Rust 正式工作檔改善批次</title><style>body{margin:32px;background:#111820;color:#e4edf7;font:16px/1.6 system-ui}a{color:#8dc5ff}table{border-collapse:collapse;width:100%}th,td{border:1px solid #455264;padding:10px;text-align:left;vertical-align:top}pre{white-space:pre-wrap;max-width:650px}header{max-width:1000px}</style><header><h1>Rust 正式工作檔改善批次</h1><p>唯讀工程投影。任務來源：docs/PROJECT-BOARD.html 的 board-snapshot。8770 是靜態預覽，沒有 Tauri IPC；此頁不代表產品已正式派工、驗收或發布。</p><p>狀態：黃燈為執行／待獨立驗證；紅燈為待決策；灰燈為待辦。架構變更仍須 owner 核准。禁止以測試通過替代真實 MCP 證據。</p></header><h2>本批工項</h2><table><thead><tr><th>ID</th><th>任務</th><th>看板狀態</th><th>範圍與證據</th></tr></thead><tbody>'''+rows+'''</tbody></table><h2>模組報告</h2><ul>'''+links+'''</ul><script id="review-batch" type="application/json">'''+payload+'''</script></html>'''
(out / 'rust-improvements.html').write_text(document,encoding='utf-8')
print('Generated rust-improvements.html:',len(tasks),'tasks;',len(reports),'module reports')
