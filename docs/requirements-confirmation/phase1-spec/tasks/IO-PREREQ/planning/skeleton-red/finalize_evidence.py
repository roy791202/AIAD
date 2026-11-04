from pathlib import Path
import json, hashlib, re, html, sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
assert (ROOT / 'apps/sgenaxis-desktop').is_dir(), ROOT
sys.path.insert(0, str(ROOT))
from tools.board.board_core.snapshot_safe import load_snapshot_dict, mutate_snapshot_file, split_snapshot
from tools.board.board_core.json_store import FileLock

def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))
def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

baseline = read('authorization-and-baseline.json')
allowed = set(baseline['allowed_source_files'])
unchanged = []
for item in baseline['protected_baseline']:
    if item['path'] not in allowed:
        assert digest(ROOT / item['path']) == item['sha256'], item['path']
        unchanged.append(item['path'])
ports = 'apps/sgenaxis-desktop/crates/sgenaxis-ports/src/lib.rs'
adapters = 'apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/lib.rs'
for path, old_name, additions in [
    (ports, 'sgenaxis-ports.lib.before.txt', ['pub mod file_commit;\n', 'pub use file_commit::{CommitError, CommitReceipt, CommitStage, FileCommitPort, FileWriteLease};\n']),
    (adapters, 'sgenaxis-adapters.lib.before.txt', ['\n// IO-PREREQ Skeleton only; Windows adapter is not connected to HOST or UI.\n#[cfg(all(windows, feature = "std-adapters"))]\npub mod file_commit;\n#[cfg(all(windows, feature = "std-adapters"))]\npub use file_commit::StdFileCommit;\n'])]:
    current = (ROOT / path).read_text(encoding='utf-8')
    for addition in additions:
        assert current.count(addition) == 1
        current = current.replace(addition, '', 1)
    assert current == (OUT / old_name).read_text(encoding='utf-8'), path

manifest = []
for n, path in enumerate(sorted(allowed), 1):
    archived = f'source-{n:02d}-{Path(path).name}.txt'
    (OUT / archived).write_bytes((ROOT / path).read_bytes())
    manifest.append({'path': path, 'sha256': digest(ROOT / path), 'archive': archived})
write('source-manifest.json', manifest)

red = read('red.json')
stderr = (OUT / 'red.stderr.txt').read_text(encoding='utf-8')
matches = list(re.finditer(r"thread '([^']+)'[^\n]*panicked at [^\n]*phase1_file_commit.rs:(\d+):\d+:\n", stderr))
assert len(matches) == 20
lines = (ROOT / 'apps/sgenaxis-desktop/crates/sgenaxis-adapters/tests/phase1_file_commit.rs').read_text(encoding='utf-8').splitlines()
reviews = []
for i, m in enumerate(matches):
    block = stderr[m.end():matches[i+1].start() if i+1 < len(matches) else len(stderr)]
    assert 'SKELETON_NOT_IMPLEMENTED' in block, m[1]
    assert lines[int(m[2])-1].strip().startswith('assert'), m[1]
    reviews.append({'test': m[1], 'assertion_line': int(m[2]), 'bdd': 'IO-' + re.search(r'io_(\d+)', m[1])[1] if re.search(r'io_(\d+)', m[1]) else 'IO-read-current (supplement)', 'verdict': 'VALID_RED_MISSING_BEHAVIOR'})
assert set(x['test'] for x in reviews) == set(red['failed_tests'])
red['classification'] = 'VALID_RED_MISSING_BEHAVIOR'
red['assertion_reviews'] = reviews
red['limit'] = 'Each case stops at its first failing assertion; downstream postconditions remain unverified. Fixture OS-handle preflight is not product locking proof.'
write('red.json', red)
for name in ['compile.json','helper-build.json','existing-ports-adapters.json','existing-work.json']:
    assert read(name)['exit_code'] == 0
verification = {'status': 'SKELETON_RED_DELIVERED_STOPPED_PER_OWNER_SCOPE', 'source_sha': baseline['sha'], 'scope': {'allowed_files': sorted(allowed), 'protected_existing_files_unchanged': len(unchanged), 'existing_lib_changes': 'Only declared module registrations/re-exports'}, 'compile': 'PASS', 'red': {'cases': 20, 'bdd_scenarios': 18, 'valid_red': 20, 'ignored': 0}, 'regression': {'ports_adapters_library': 101, 'work': 73, 'failures': 0}, 'architecture': 'Port types remain infrastructure-free; Windows adapter Skeleton depends on Ports; test-only constructor/checkpoints do not expand shipping API; HOST/UI not wired', 'product_behavior': 'NOT IMPLEMENTED', 'windows11_acceptance': 'NOT RUN (actual host Windows 10 build 19045)', 'system_regression': 'NOT RUN', 'independent_acceptance': 'NOT RUN for IO-PREREQ', 'warnings': 'Nonblocking dead-code warnings: existing conpty fixture and new Skeleton/controlled test-copy scaffolding', 'remaining': ['Implement only after separate authorization', 'OS lease, atomic publish, digest recheck, journal parsing, rollback and cleanup remain absent', 'Green, full-system, Windows 11, packaging and release gates remain outstanding']}
write('verification.json', verification)
rows = ''.join(f'<tr><td>{html.escape(r["bdd"])}</td><td>{html.escape(r["test"])}</td><td>{r["assertion_line"]}</td><td>有效 RED</td></tr>' for r in reviews)
files = ''.join(f'<li><a href="{x["archive"]}">{html.escape(x["path"])}</a> — <code>{x["sha256"]}</code></li>' for x in manifest)
page = f'''<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>IO-PREREQ Skeleton / RED</title><style>body{{font:16px/1.6 system-ui;max-width:1200px;margin:40px auto;padding:0 24px;color:#202632}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccd3df;padding:8px;text-align:left}}code{{overflow-wrap:anywhere}}.status{{padding:18px;background:#fff1d1}}a{{color:#185aa8}}</style>
<h1>IO-PREREQ：骨架與有效 RED</h1><p class="status">已採納精確設計；只交付 Skeleton / RED，未實作產品功能。看板維持黃燈。2026-11-01</p>
<p>模組責任：透過 FileCommitPort / FileWriteLease 表達獨占建立、寫入租約、讀取及有條件提交；正式 IO 行為仍缺失。此頁是既有規格及實測證據的投影，原始契約與架構見<a href="../index.html">精確設計</a>。</p>
<h2>架構與範圍</h2><pre>未接入的 HOST / UI → FileCommitPort → Windows StdFileCommit Skeleton\nFileWriteLease → 私有 handle / journal / fault-checkpoint 接縫\n整合測試 → Ports 邊界 + test-only controlled lease\n隔離子程序 → 測試 fixture OS handle（不等於產品鎖）</pre>
<p>權威狀態、交易與失敗語意沿用已核准設計；未新增 recovery API。Ports 公開資料不攜帶檔案或 OS 型別。產品 adapter 各操作明確回報 SKELETON_NOT_IMPLEMENTED；未接入 HOST、UI 或既有 StdFS。固定六個來源檔，其他 {len(unchanged)} 個既有受保護檔雜湊一致；兩個 lib 僅新增註冊／匯出。</p>
<h2>測試結果與證據邊界</h2><ul><li>Helper build PASS；測試編譯 PASS。</li><li>18 個 BDD 情境對應 20 項測試，20 有效 RED、0 略過；exit 101 為預期行為缺失。</li><li>Ports / Adapters 既有 library：101 PASS；WORK 完整既有測試：73 PASS。</li><li>每項第一個失敗均為行為 assertion 且含 Skeleton 標記；沒有將編譯、fixture 或逾時錯誤算入 RED。第一個 assertion 後的條件尚未驗證。</li><li>實際主機 Windows 10 / 19045。Windows 11 相容驗收、IO 獨立驗收、全系統回歸、打包與發布：NOT RUN。</li></ul>
<h2>BDD → TDD → RED 追溯</h2><table><tr><th>BDD</th><th>測試</th><th>第一失敗行</th><th>結果</th></tr>{rows}</table>
<h2>Fixture、失敗注入與交易接縫</h2><p>子程序預檢確認測試持有的原生 handle 排他及正常／異常結束釋放；產品 acquire 仍為 Skeleton。lease 測試預先持有真實 fixture handle，故能把 replace/read 缺失與 acquire 缺失分開。故障 checkpoint 測試要求真的到達注入點，不能讓一般 Storage 錯誤冒充回復成功。</p><p>未完成 journal fixture 使用 ELUCOMMIT、v1、小端長度、六個長度前綴欄位、Prepared 狀態與 SHA-256；只存在於測試產生器，產品尚無編解碼。最大 65536 journal bytes / 4096 path bytes 仍依精確設計。暫存資料只在擁有標記且 canonical 邊界通過時清理。</p>
<h2>重跑</h2><pre>cd D:/AIAD/apps/sgenaxis-desktop\ncargo build -p sgenaxis-adapters --example file_commit_probe --locked\n$env:FILE_COMMIT_PROBE_PATH = (Resolve-Path target/debug/examples/file_commit_probe.exe).Path\ncargo test -p sgenaxis-adapters --test phase1_file_commit --no-run --locked\ncargo test -p sgenaxis-adapters --test phase1_file_commit --locked -- --nocapture\ncargo test -p sgenaxis-ports -p sgenaxis-adapters --lib --locked\ncargo test -p sgenaxis-work --locked</pre>
<h2>原始證據</h2><p><a href="verification.json">驗證摘要</a> · <a href="red.json">逐項 RED 審查</a> · <a href="red.stdout.txt">RED stdout</a> · <a href="red.stderr.txt">RED stderr</a> · <a href="compile.json">編譯</a> · <a href="helper-preflight.json">Helper 預檢</a> · <a href="existing-ports-adapters.json">Ports / Adapters 回歸</a> · <a href="existing-work.json">WORK 回歸</a> · <a href="source-manifest.json">來源雜湊</a></p><ul>{files}</ul>
<h2>模組健康與後續</h2><p>Skeleton / RED 交付完成；產品能力尚不可用。獨占鎖、正式提交、journal 檢查、rollback、清理的 GREEN 證據仍待後續授權實作。不得將此頁視為 IO 功能、模組或版本驗收通過。未 commit、push、dispatch 或發版。</p></html>'''
(OUT / 'index.html').write_text(page, encoding='utf-8')

board = ROOT / 'docs/PROJECT-BOARD.html'
before = board.read_text(encoding='utf-8')
old = load_snapshot_dict(before)
ids = {'PD-P1-IO-PREREQ-PLAN-01', 'PD-P1-IO-PREREQ-RED-01'}
stamp = datetime.now(timezone.utc).isoformat()
def mutate(data):
    for task in data['tasks']:
        if task.get('id') not in ids:
            continue
        task['zone'] = 'yellow'
        task['doneAt'] = None
        task['executionStatus'] = 'SKELETON_RED_DELIVERED_STOPPED_PER_OWNER_SCOPE' if task['id'].endswith('RED-01') else 'EXACT_DESIGN_ADOPTED_SKELETON_RED_DELIVERED'
        task['note'] += f'\n[{stamp}] Skeleton/RED delivered: compile PASS; 18 scenarios / 20 VALID RED / 0 ignored. Existing Ports+Adapters lib 101 PASS; WORK 73 PASS. Source envelope verified. Windows10 host; Windows11 acceptance NOT RUN. No product behavior implementation, no green/commit/push/dispatch. Evidence: docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/planning/skeleton-red/index.html'
        task['updatedAt'] = stamp
        task['version'] = task.get('version',0) + 1
mutate_snapshot_file(board, mutate, lock_factory=FileLock)
after = board.read_text(encoding='utf-8')
assert (split_snapshot(before)[0], split_snapshot(before)[2]) == (split_snapshot(after)[0], split_snapshot(after)[2])
new = load_snapshot_dict(after)
assert [t for t in old['tasks'] if t.get('id') not in ids] == [t for t in new['tasks'] if t.get('id') not in ids]
write('board-update.json', {'shell_unchanged': True, 'other_cards_unchanged': True, 'updated_ids': sorted(ids), 'zone': 'yellow'})
print(json.dumps(verification, ensure_ascii=True))
