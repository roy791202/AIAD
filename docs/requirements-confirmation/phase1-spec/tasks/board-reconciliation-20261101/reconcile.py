"""Owner-authorized, evidence-bound reconciliation of exactly 14 yellow cards.

Documentation/board only. Reruns refuse once these cards cease being yellow.
"""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib
import html
import json
import sys

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
TASKS = OUT.parent
sys.path.insert(0, str(ROOT))
from tools.board.board_core.snapshot_safe import load_snapshot_dict, mutate_snapshot_file, split_snapshot
from tools.board.board_core.json_store import FileLock

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

board = ROOT / 'docs/PROJECT-BOARD.html'
before_html = board.read_text(encoding='utf-8')
before = load_snapshot_dict(before_html)
cards = [t for t in before['tasks'] if t.get('zone') == 'yellow']
assert len(cards) == 14, 'Require original 14-card inventory; no silent rerun'
save(OUT / 'cards-before.json', cards)
source_baseline = read(TASKS / 'IO-PREREQ/planning/acceptance-a/review-baseline.json')
for f in source_baseline['source_files']:
    assert sha(ROOT / f['path']) == f['sha256'], f['path']

evidence_checks = []
for module in ['M01', 'M04']:
    exact = TASKS / module / 'planning/exact-design'
    acceptance = read(exact / 'independent-review/primary-adjudication.json')
    review = read(exact / 'independent-review/review.json')
    assert acceptance['verdict'] == 'ACCEPTED_FOR_PURE_S1_ONLY'
    assert review['verdict'] == 'PASS' and review['blocking_findings'] == 0
    for f in acceptance['source_files']:
        assert sha(ROOT / f['path']) == f['sha256'], f['path']
    red = read(exact / 's1-red/verification.json')
    assert red['compile_exit'] == 0 and red['red_exit'] == 101 and red['skipped'] == 0
    for filename, digest in red['log_hashes'].items():
        assert sha(exact / 's1-red' / filename) == digest, filename
    original = read(exact / 's1-red/source-manifest.json')
    for f in original['files']:
        path = Path(f['path'])
        archive = exact / 's1-green/historical-skeleton' / (path.name + '.txt')
        if path.name == 'lib.rs':
            assert sha(ROOT / f['path']) == f['sha256']
        else:
            assert sha(archive) == f['sha256'], archive
    evidence_checks.append({'module': module, 'pure_s1_independent_acceptance': 'PASS',
                            'live_accepted_source_hashes': 'PASS',
                            'historical_red_log_and_reconstruction_hashes': 'PASS',
                            'historical_red_failures': red['intentional_failures'],
                            'limit': 'Accept historical Skeleton/RED and pure S1 implementation stages only; no full module/UI/HOST/IO acceptance'})
io = TASKS / 'IO-PREREQ/planning'
io_review = read(io / 'acceptance-a/primary-adjudication.json')
assert io_review['verdict'] == 'PARTIAL'
assert io_review['gates']['journal_protocol_A'] == 'PASS'
assert io_review['gates']['architecture_dependency_and_ownership'] == 'PASS_FOR_SKELETON'
assert sha(io / 'gap-resolution/proposal-v2-a.json') == source_baseline['protocol_sha256']
evidence_checks.append({'module': 'file-commit', 'precise_protocol_A_planning_stage': 'PASS',
                        'skeleton_red_full_preparation_acceptance': 'PARTIAL',
                        'findings': ['IO-A-R1', 'IO-A-R2', 'IO-A-R3'],
                        'limit': 'Close design-only card; leave RED/preparation card yellow'})

# Each PREP card owns preparation review, never the full product module.
# Missing product behavior is context, not the reason to withhold PREP closure.
prep = {
 'M01': ('專案定義與新建',
         'S1 純領域已獨立通過；完整準備包尚缺非 S1 範圍的全項驗收證據。',
         '既有獨立 PASS 僅涵蓋 S1，不能外推六步精靈／持久保存／HOST／UI 的準備與整合；IO 前置準備仍 PARTIAL。',
         '沿已採納精確設計逐項審查其餘切片之契約、精確檔案範圍與 BDD/TDD 任務包；先處理 IO 三項測試對齊問題。',
         '後續功能範圍：六步精靈、保存未完成定義、重開續填、新建衝突保護與生成門檻整合。'),
 'M02': ('模板與雙骨架',
         '初步盤點與設計已交付；精確模板 manifest／生成計畫、版本與 golden fixture 的準備驗收未完成。',
         'D1～D7 方向已採納，但不是各 DTO／artifact schema／再生成衝突策略及精確 envelope 的全項驗收；尚無本卡獨立 PASS。',
         '按已採納 Vanilla UI＋Tauri 2 方向凍結模板 manifest、雙骨架輸出與 regeneration diff 測例，再驗收準備卡。',
         '後續功能範圍：條件足夠才生成程式/UI UX 雙骨架，條件不足只保存並明示差額。'),
 'M03': ('架構與 UI 設計',
         '初步盤點已交付；完整 metadata roundtrip、事件/預覽 schema、ID 綁定與多視窗 revision 協定仍需精確化與驗收。',
         '尚無本卡全範圍獨立 PASS；方向採納不能替代 schema、ownership 與 runtime 隔離的精確驗收。',
         '完成欄位保全 roundtrip fixture、Editor/Viewer 邊界、跨視圖定位與失敗流程的準備審查，不直接改 UI。',
         '後續功能範圍：UI 設計窗、互動預覽、跨視圖定位與權威狀態同步。'),
 'M04': ('文件與單文件歷史',
         'S1 單文件領域切片已獨立通過；完整準備包的 codec、正式保存、素材 pin 與 HOST 整合範圍未獲全項驗收。',
         'S1 PASS 不涵蓋實體檔案交易、ESS parser/serializer、實體素材或 UI dirty 提示；IO 前置 RED 準備仍 PARTIAL。',
         '先完成 IO 測試契約對齊；再對其餘已設計切片逐項核對失敗不變、兩基準、素材引用及精確 envelope。',
         '後續功能範圍：正式 ESS 保存、清空/合併各一筆 Undo、未保存提示與素材 pin 協調。'),
 'M05': ('素材管理',
         '初步盤點已交付；AssetID／immutable 版本、反向引用、媒體限制與 GC roots 的精確準備包尚待驗收。',
         '尚無本卡全範圍獨立 PASS；文件、Undo、快照及未完成交易的引用保留／回收契約需一致。',
         '精確列出版本/引用/pin/GC 的責任與失敗矩陣，媒體格式及限制依已採納方向分切片列測例，送準備驗收。',
         '後續功能範圍：素材匯入與引用、完整復原所需素材、避免刪除共用素材。'),
 'M06': ('交換與合併',
         '初步盤點已交付；BIN archive schema、格式/路徑限制、ID 衝突及單文件套用計畫仍缺精確準備驗收。',
         '尚無本卡全範圍獨立 PASS；方向採納不是 archive codec/依賴選型與交易 envelope 核准；需與 M04/M05 對齊。',
         '分別完成輸出、還原為新專案、合併單文件的規格與 BDD/TDD 包；檢查錯誤回復、ID 衝突及素材引用邊界。',
         '後續功能範圍：BIN 獨立輸出、ESS/BIN 安全驗證、不完整待綁定、單文件合併與一次 Undo。'),
 'M07': ('復原與最近檔案',
         '初步盤點已交付；stable capture、快照/index、late completion、復原與保留清理的精確準備包仍待驗收。',
         '尚無本卡全範圍獨立 PASS；M04 S1 capture 不是磁碟快照功能；仍需跨 M04/M05/IO 的精確持久化與引用契約。',
         '依已確認60秒檢查／相較上次成功快照有變更才保存，精確定義失敗重試、session切換、索引與清理測例；待決保留細節集中列出。',
         '後續功能範圍：LOCALAPPDATA 復原、歷史獨立標示、無效原路徑、復原開啟仍未保存。'),
 'M08': ('Windows 驗收整合',
         '整合盤點已交付；完整驗收包之環境、artifact lock、案例與依賴就緒條件尚缺全項審查。',
         '尚無本卡準備範圍獨立 PASS；實測 host 為 Windows10，Windows11 x64/WebView2、portable 新 artifact 與系統驗收仍 NOT RUN。',
         '先明定環境與 artifact 識別、跨模組矩陣、可重跑命令及證據門檻以完成準備驗收；實際 build/package/native 測試屬後續授權工作。',
         '後續功能範圍：Windows11 原生、移動 portable、唯讀/離線/多程序/異常中斷與完整回歸。'),
}

rows = []
for card in cards:
    cid = card['id']
    report = card.get('report')
    assert report and (ROOT / report).is_file(), cid
    row = {'id': cid, 'original_title': card['title'], 'old_zone': 'yellow',
           'previous_status': card.get('executionStatus'), 'module_complete': False,
           'evidence': [report], 'scope': '', 'gap': '', 'blockers': '', 'next_step': '',
           'product_implementation_authorized': False}
    if '-PREP-' in cid:
        module = cid.split('-')[2]
        name, gap, blockers, next_step, context = prep[module]
        packet = TASKS / (cid + '.json')
        original = read(packet)
        spec_path = TASKS / module / 'planning/module-spec.json'
        doc = read(spec_path)
        assert doc['module'] == module and original['module'] == module
        for filename in ['architecture-and-ui.html', 'module-spec.json', 'test-plan.json', 'module.feature', 'fixtures.json']:
            assert (TASKS / module / 'planning' / filename).is_file(), (module, filename)
        row.update({'module': module, 'name': name + '：完整準備卡', 'scope': '需求差額／架構／精確 envelope／BDD-TDD 準備包；不是模組產品完成卡',
                    'new_zone': 'yellow', 'status': 'PREPARATION_ACCEPTANCE_PENDING_FULL_CARD_SCOPE',
                    'acceptance': '尚無本卡全部準備範圍的驗收 PASS；M01/M04 僅 S1 PASS',
                    'gap': gap, 'blockers': blockers, 'next_step': next_step,
                    'future_product_context': context,
                    'closure_rule': '準備交付全項驗收後即可結案，不要求先實作整個模組；產品未實作本身不是本卡保留黃燈理由。',
                    'evidence': [packet.relative_to(ROOT).as_posix(), spec_path.relative_to(ROOT).as_posix(), report]})
    elif '-S1-' in cid:
        module = cid.split('-')[2]
        red_stage = '-RED-' in cid
        exact = TASKS / module / 'planning/exact-design'
        row.update({'module': module, 'name': module + '-S1 ' + ('Skeleton／有效 RED 階段' if red_stage else '純領域實作階段'),
                    'scope': module + '-S1 純領域切片，僅本卡原定階段',
                    'new_zone': 'green', 'status': 'STAGE_ACCEPTED_CLOSED',
                    'acceptance': ('原始編譯、行為 RED、log 雜湊與歷史來源重建已核對；後續同一 S1 獨立驗收 PASS，源碼已進入 GREEN。' if red_stage else '同一 S1 獨立驗收 PASS；目前原始碼與驗收 manifest 相符，既有 WORK73 PASS 證據有效。'),
                    'gap': '本階段無未完成差額；整個模組與 HOST/UI/IO 不在本卡完成範圍。',
                    'blockers': '本階段無；不得把 S1 結案外推 M01/M04 模組完成。',
                    'next_step': '保留歷史 RED／GREEN 與獨立驗收證據；剩餘準備與切片由本模組 PREP 卡追蹤，不重開已完成 S1。',
                    'evidence': [(exact / 'independent-review/primary-adjudication.json').relative_to(ROOT).as_posix(),
                                 (exact / 'independent-review/review.json').relative_to(ROOT).as_posix(),
                                 (exact / 's1-red/verification.json').relative_to(ROOT).as_posix(),
                                 (exact / 's1-green/historical-source-check.json').relative_to(ROOT).as_posix()]})
    elif cid == 'PD-P1-IO-PREREQ-PLAN-01':
        row.update({'module': 'file-commit', 'name': 'IO-PREREQ 精確設計階段',
                    'scope': 'FileCommit 契約、架構、journal 方案 A 與測試準備設計；不包含 RED 套件全項通過或產品行為',
                    'new_zone': 'green', 'status': 'DESIGN_STAGE_ACCEPTED_CLOSED',
                    'acceptance': 'G1～G6／方案 A 已獲採納；最新獨立驗收明示 journal、public contract Skeleton 及架構 PASS。',
                    'gap': '本設計階段無未完成差額；補測試交付有三項 P2，保留在 IO-PREREQ-RED-01。',
                    'blockers': '無本設計階段阻擋；不得把規劃轉綠視為檔案交易已實作。',
                    'next_step': '沿用已確認協定，在 RED 卡修正 IO-A-R1～R3，再驗收測試準備；不重問方案 A。',
                    'evidence': [(io / 'gap-red-a/approval.json').relative_to(ROOT).as_posix(),
                                 (io / 'gap-resolution/proposal-v2-a.json').relative_to(ROOT).as_posix(),
                                 (io / 'acceptance-a/primary-adjudication.json').relative_to(ROOT).as_posix()]})
    elif cid == 'PD-P1-IO-PREREQ-RED-01':
        row.update({'module': 'file-commit', 'name': 'IO-PREREQ Skeleton／RED 準備',
                    'scope': '補測試與有效 RED 套件的完整契約對齊，未含產品功能',
                    'new_zone': 'yellow', 'status': 'INDEPENDENT_ACCEPTANCE_PARTIAL_TEST_ALIGNMENT_REQUIRED',
                    'acceptance': '獨立驗收 PARTIAL；194 項第一 assertion RED、12 support 與既有174回歸通過，不代表後置條件正確。',
                    'gap': 'IO-A-R1：回傳後不應強制保留已可安全清理的 journal；R2：generic cleanup 不應強制保留冗餘 old.bin；R3：未解析紀錄須明確驗證 old/new 診斷 None。',
                    'blockers': '三項 P2 測試契約對齊尚未完成，不能進入產品實作；Windows11 原生驗收仍 NOT RUN。',
                    'next_step': '後續僅在測試修正範圍保留終態觀測與唯一 preimage 保護，修正三項 assertion；重跑 compile／support／有效 RED／回歸，重新獨立驗收。本輪不改測試。',
                    'follow_up': 'IO-A-F1：alias/reparse/hard-link 原生拒絕案例另列後續覆蓋，不默默擴大這張卡。',
                    'evidence': [(io / 'acceptance-a/primary-adjudication.json').relative_to(ROOT).as_posix(),
                                 (io / 'acceptance-a/review.json').relative_to(ROOT).as_posix()]})
    else:
        raise AssertionError('Unclassified yellow card ' + cid)
    rows.append(row)

assert len(rows) == 14
assert sum(r['new_zone'] == 'green' for r in rows) == 5
assert sum(r['new_zone'] == 'yellow' for r in rows) == 9
for row in rows:
    for path in row['evidence']:
        assert (ROOT / path).is_file(), path
save(OUT / 'evidence-checks.json', evidence_checks)
record = {'date': '2026-11-01', 'authority': 'Owner explicitly authorized green closure only for completed and accepted stages among these 14 cards; no product implementation.',
          'rule': 'Each card judged against original scope. Preparation closure is not product completion; S1 closure is not module completion. Prior no-auto-green policy is superseded only for these owner-authorized accepted stages.',
          'before_yellow': 14, 'closed_green': 5, 'remaining_yellow': 9,
          'product_tests_this_round': 'NOT RUN; reused live-hash-matched S1 acceptance and freshly recorded WORK73/IO acceptance evidence, no behavior change',
          'product_or_test_changes': 0, 'module_completion_claims': 0, 'cards': rows}
save(OUT / 'reconciliation.json', record)

stamp = datetime.now(timezone(timedelta(hours=8))).isoformat()
by_id = {row['id']: row for row in rows}
def mutate(snapshot):
    for task in snapshot['tasks']:
        row = by_id.get(task.get('id'))
        if not row:
            continue
        assert task['zone'] == 'yellow'
        task['zone'] = row['new_zone']
        task['executionStatus'] = row['status']
        task['doneAt'] = stamp if row['new_zone'] == 'green' else None
        task['updatedAt'] = stamp
        task['updatedBy'] = 'agent'
        task['version'] = task.get('version', 0) + 1
        task['stageReview'] = row
        task['closureScope'] = row['scope']
        task['remainingGap'] = row['gap']
        task['blockers'] = row['blockers']
        task['nextStep'] = row['next_step']
        task['moduleComplete'] = False
        task['report'] = 'docs/requirements-confirmation/phase1-spec/tasks/board-reconciliation-20261101/index.html'
        current = f'【2026-11-01 逐卡核對】{row["status"]}\n範圍：{row["scope"]}\n驗收：{row["acceptance"]}\n差額：{row["gap"]}\n阻擋：{row["blockers"]}\n下一步：{row["next_step"]}\n本次僅依Owner授權結案已驗收階段，非整個模組完成、非產品實作授權。逐卡證據：docs/requirements-confirmation/phase1-spec/tasks/board-reconciliation-20261101/index.html#{row["id"]}\n--- 原始追溯 ---\n'
        task['note'] = current + task.get('note', '')
        task.setdefault('log', []).append({'t': stamp, 'zone': row['new_zone'], 'by': 'agent',
                                          'note': 'Owner-authorized stage reconciliation; ' + row['status'] + '; moduleComplete=false'})

mutate_snapshot_file(board, mutate, lock_factory=FileLock)
after_html = board.read_text(encoding='utf-8')
after = load_snapshot_dict(after_html)
assert (split_snapshot(before_html)[0], split_snapshot(before_html)[2]) == (split_snapshot(after_html)[0], split_snapshot(after_html)[2])
assert [t for t in before['tasks'] if t.get('id') not in by_id] == [t for t in after['tasks'] if t.get('id') not in by_id]
assert {k:v for k,v in before.items() if k!='tasks'} == {k:v for k,v in after.items() if k!='tasks'}
assert len([t for t in after['tasks'] if t.get('zone')=='yellow']) == 9
for f in source_baseline['source_files']:
    assert sha(ROOT / f['path']) == f['sha256']
save(OUT / 'verification.json', {'result': 'PASS_BOARD_RECONCILIATION', 'reviewed_cards': 14,
                                'green_closed': [r['id'] for r in rows if r['new_zone']=='green'],
                                'yellow_remaining': [r['id'] for r in rows if r['new_zone']=='yellow'],
                                'source_files_unchanged': len(source_baseline['source_files']),
                                'shell_and_other_cards_root_metadata_unchanged': True,
                                'no_dispatch_commit_push_or_product_work': True})

esc = lambda x: html.escape(str(x))
def link(path):
    import os
    target = Path(path)
    return Path(os.path.relpath(ROOT / target, OUT)).as_posix()
page = '<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>14 張黃燈逐卡核對與階段結案</title><style>body{font:16px/1.7 system-ui;color:#24344a;max-width:1200px;margin:30px auto;padding:24px}section{padding:20px;border:1px solid #ccd5df;margin:20px 0}table{border-collapse:collapse;width:100%}th,td{border:1px solid #ccd5df;padding:9px;text-align:left;vertical-align:top}.green{color:#12643a}.yellow{color:#8a6112}a{color:#195ba5}code{overflow-wrap:anywhere}.summary{padding:18px;background:#eef3f8}</style><h1>14 張黃燈逐卡核對</h1><p class="summary">2026-11-01：5 張已驗收階段卡轉綠結案，9 張保留黃燈。8 張模組 PREP 均未標成整個模組完成；準備卡保留黃燈的原因是全範圍準備驗收仍欠缺，不是要求先把產品全部實作。本輪沒有修改產品或測試、沒有新增測試執行、沒有啟動派工。</p><p><a href="../../../../PROJECT-BOARD.html">工項看板</a> · <a href="reconciliation.json">逐卡結構資料</a> · <a href="verification.json">範圍與結案檢查</a> · <a href="evidence-checks.json">驗收證據核對</a></p><table><tr><th>工項</th><th>處理</th><th>本卡驗收</th></tr>'
for row in rows:
    page += '<tr><td><a href="#'+row['id']+'">'+esc(row['id'])+'</a><br>'+esc(row['name'])+'</td><td class="'+row['new_zone']+'">'+('轉綠結案' if row['new_zone']=='green' else '保留黃燈')+'</td><td>'+esc(row['acceptance'])+'</td></tr>'
page += '</table>'
for row in rows:
    page += '<section id="'+row['id']+'"><h2>'+esc(row['name'])+'</h2><p><code>'+row['id']+'</code> — '+esc(row['status'])+'</p>'
    for key,label in [('scope','原定範圍'),('acceptance','驗收核對'),('gap','剩餘差額'),('blockers','阻擋'),('next_step','下一步'),('closure_rule','準備卡結案門檻'),('future_product_context','未來功能上下文（不作本卡產品完成要求）'),('follow_up','另列追蹤')]:
        if key in row: page += '<p><strong>'+label+'：</strong>'+esc(row[key])+'</p>'
    page += '<p>來源證據：'+' · '.join('<a href="'+link(p)+'">'+esc(Path(p).name)+'</a>' for p in row['evidence'])+'</p></section>'
page += '<script type="application/json" id="reconciliation">'+json.dumps(record,ensure_ascii=False).replace('</','<\\/')+'</script></html>'
(OUT / 'index.html').write_text(page, encoding='utf-8')
import re
for target in re.findall(r'href="([^"]+)"',page):
    if not target.startswith('#'):assert (OUT / target).is_file(), target
print(json.dumps({'reviewed':14,'green_closed':5,'yellow_remaining':9,'source_unchanged':len(source_baseline['source_files'])}))
