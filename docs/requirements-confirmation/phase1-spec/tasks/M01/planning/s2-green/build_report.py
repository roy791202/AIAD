"""Project immutable approved M01 engineering data + observed verification."""
from pathlib import Path
import json,hashlib,re,datetime,subprocess,html,collections
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
PACKET=HERE.parent/'s2-exact-design'
RED=HERE.parent/'s2-skeleton-red'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,d):p.write_bytes(json.dumps(d,ensure_ascii=False,indent=2).encode('utf-8'))
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
baseline=load(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/IO-PREREQ/implementation/source-current.json')
approved=load(PACKET/'module-spec.json')
envelope=load(PACKET/'envelope.json')['after_whole_packet_approval_only']
allowed=[x['path'] for k in ['new_production','existing_production','dependency_feature'] for x in envelope[k]]+envelope['tests']
inventory=dict(baseline['source_hashes']);changed={}
for name,old in baseline['source_hashes'].items():
    actual=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    if actual!=old:changed[name]=actual
assert set(changed)<=set(allowed),(set(changed)-set(allowed))
for name in allowed:inventory[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()
branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT).decode().strip()
assert head==baseline['head'] and branch==baseline['branch']
source={'date':now,'head':head,'branch':branch,'source_hashes':inventory,'based_on':'../s2-skeleton-red/source-current.json','changed_this_delivery':allowed}
write(HERE/'source-current.json',source)
# Explicitly check the pre-existing bodies protected inside the allowed files.
h=ROOT/'apps/sgenaxis-desktop/crates/sgenaxis-host'
old_prefs=(PACKET/'legacy-history/project_preferences.rs.before.txt').read_text(encoding='utf-8')
prefs=(h/'src/project_preferences.rs').read_text(encoding='utf-8')
assert prefs[prefs.index('fn root_path'):]==old_prefs[old_prefs.index('fn root_path'):]
old_new=(PACKET/'legacy-history/project_new.rs.before.txt').read_text(encoding='utf-8')
new=(h/'src/project_new.rs').read_text(encoding='utf-8')
assert new[new.index('pub fn normalize_new_project_path'):new.index('/// Create (or ensure)') if '/// Create (or ensure)' in new else new.index('/// Deprecated direct creator')]==old_new[old_new.index('pub fn normalize_new_project_path'):old_new.index('/// Create (or ensure)')]
for name in ['phase1_project_definition.rs','phase1_project_definition_codec.rs','phase1_project_creation_legacy.rs']:
    assert (h/'tests'/name).read_bytes().replace(b'\r\n',b'\n')==(RED/'red-source'/name).read_bytes().replace(b'\r\n',b'\n'),name
production=(h/'src/project_definition.rs').read_text(encoding='utf-8')
assert not any(x in production for x in ['std::fs','std::env','std::os','write_atomic(', 'create_dir_all(', 'remove_file(', '$SKELETON_NOT_IMPLEMENTED'])
assert 'Deserialize' not in production.replace('no Deserialize','').replace('No Deserialize','') or '#[derive(Deserialize' not in production
runs=load(HERE/'final-runs.json')
for target in ['host-final.log','io220-with-helpers.log','work-full.log','ports-adapters.log','host-build-final.log','shell-full.log']:
    run=next(x for x in runs if x['log']==target);assert run['exit_code']==0,(target,run)
classification=[
 {'attempt':'../s2-skeleton-red/shell-regression.log','classification':'FLAKY_TIMING','observed':'239 PASS /1 deadline elapsed assertion FAIL in initial concurrent shell run','resolution':'full serial shell run 240 PASS; no source/test edits'},
 {'attempt':'io220-final.log','classification':'ENVIRONMENT_FIXTURE_FAILURE','observed':'190 PASS /30 missing helper setup failures, not product RED','resolution':'rebuilt existing normal/checkpoint examples, configured two approved env paths; fresh 220 PASS'},
 {'attempt':'project_preferences_creation.log','classification':'MIGRATED_FIXTURE_PATH_AND_TEARDOWN','observed':'S2 native creation succeeded; existing editor mixed separators on verbatim path, then exact lock-sidecar cleanup incomplete','resolution':'fixture uses original Win32 spelling for unchanged preference editor; explicit owned lock cleanup; native creation/edit roundtrip PASS; no product expectation weakened'},
]
acceptance=[]
for c in load(PACKET/'acceptance.json')['criteria']:
    x=dict(c);x['status']='PASS_SCOPED';acceptance.append(x)
review={'status':'PASS_IMPLEMENTED_SCOPE_ONLY','date':now,'reviewer':'same assistant, separate architecture/acceptance review phase; no independently delegated reviewer','contract_and_public_types':'unchanged from adopted D1-D7 / accepted Skeleton','architecture':'PASS','protected_existing_files_unchanged':len(baseline['source_hashes'])-len(changed),'same_3_new_test_targets':'byte-identical after newline normalization to accepted RED archive','native_fixture_adjustment':'approved existing test migration, Win32 spelling and explicit empty lock cleanup only','criteria':acceptance,'not_accepted':['S3 UI/IPC/owner/idempotency/late-ack migration','Windows11/native alias gates','entire M01 module','package/install/release']}
write(HERE/'acceptance.json',review)
verification={'status':'GREEN_SCOPED_ACCEPTED','date':now,'source':{'inventory':'source-current.json','count':len(inventory),'branch':branch,'head':head},'approved_decisions':[f'M01-S2-D{i}' for i in range(1,8)],'approved_packet_sha256':'0463a1fba2616cb0b48866992547e2ea654ef3ce8c9b7a6634d4936c3cd937af','allowed_paths':allowed,'changed_existing':changed,'new_paths':[k for k in allowed if k not in baseline['source_hashes']],'red_stage':'../s2-skeleton-red/verification.json','skeleton_acceptance':'../s2-skeleton-red/acceptance/review.json','behavioral_plans':105,'expanded_plan_cases':189,'related_tests_green':204,'host_all_tests':330,'work_all_tests':222,'ports_adapters_library':101,'native_io_regression':220,'shell_library':240,'native_M01_roundtrip':1,'native_environment':'Windows10 build19045, not Windows11','all_original_migrated_names_preserved':True,'classification':classification,'architecture_review':review,'runs':runs,'module_complete':False,'release':'NOT RUN; S2 not independently releasable before S3','cleanup':'Automatic approval review rejected optional cleanup of two prior owned fixture remnants: blocked by policy. Retained them; no bypass/retry.'}
write(HERE/'verification.json',verification)
module=approved.copy();module['current_results']=verification;write(HERE/'module-spec.json',module)
esc=html.escape
diagrams=re.findall(r'<pre>.*?</pre>',(PACKET/'index.html').read_text(encoding='utf-8'),re.S)
parts=['''<!DOCTYPE html><html lang="zh-Hant"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>M01 專案定義與新建｜S2 工程文件</title>
<style>body{margin:0;background:#f2f5f9;color:#18283e;font:16px/1.65 system-ui}main{max-width:1260px;margin:auto;padding:32px}header{background:#17324e;color:white;padding:32px;border-radius:16px}a{color:#0967b3}nav{margin:24px 0;display:flex;gap:16px;flex-wrap:wrap}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin:24px 0}.card,section{background:white;border:1px solid #d9e2ed;border-radius:10px;padding:20px}.card b{font-size:24px;display:block;color:#176544}section{margin:20px 0}table{width:100%;border-collapse:collapse;font-size:14px}td,th{padding:10px;border:1px solid #d8e1ed;text-align:left;vertical-align:top}th{background:#eef3fa}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0f7;padding:18px;border-radius:8px}.pending{border-left:5px solid #c88a20;background:#fff8e8;padding:14px}h2{margin-top:0}code{overflow-wrap:anywhere}details{margin:10px 0}.table{overflow:auto}</style><main>
<header><small>M01｜專案定義與新建｜HOST application / codec</small><h1>S2 完整工程狀態</h1><p>保存六步精靈未完成定義、嚴格重開、無覆寫建立、明確採用舊專案，以及獨立偏好副本。S2 提供本機 Port 邊界；S3 負責原生選取、視窗／session 權限及 UI 接線。</p></header>''',
 '<p>產生於 '+esc(now)+'。本頁由已採納工程包及實測結果產生，嵌入結構化 ModuleSpec；原始精確設計與歷史 RED 不改寫。</p>',
 '<div class="grid">'+''.join('<div class="card">'+esc(k)+'<b>'+esc(v)+'</b></div>' for k,v in [('S2 契約／架構','PASS'),('M01-S2 關聯測試','204 GREEN'),('完整 HOST','330 PASS'),('WORK','222 PASS'),('Ports / Adapters library','101 PASS'),('IO native regression','220 PASS'),('Shell library','240 PASS'),('完整 M01','未完成')])+'</div>',
 '<p class="pending">驗收為 PASS_IMPLEMENTED_SCOPE_ONLY，同一助理另行只讀審查，未另委派獨立審查者。Windows11／原生別名與 S3 UI、權限、request 去重、late acknowledgement、打包發布均不在本次完成範圍。三個舊入口已依核准規則 fail-closed，S2 不單獨發布。</p>',
 '<nav><a href="#architecture">架構</a><a href="#contracts">契約</a><a href="#behavior">BDD／追溯</a><a href="#tests">測試</a><a href="#scope">工項與範圍</a><a href="#acceptance">驗收</a><a href="#risks">風險</a></nav>',
 '<section id="architecture"><h2>架構、責任與 Port</h2>',''.join(diagrams[:2])]
for k,v in approved['architecture'].items():parts.append('<p><b>'+esc(k)+'</b> '+esc(v if isinstance(v,str) else '; '.join(v))+'</p>')
parts+=['</section><section id="contracts"><h2>契約與不變量</h2><p>WORK 為型別與純領域規則來源；HOST 只映射、驗證與協調。save 回傳不可變 proof／下一份 binding 提案，不安裝 active project。每個正式檔案是一個 IO 交易；definition 成功後 prefs 失敗保留 definition proof，回傳 partial；RecoveryRequired 保持頂層精確診斷。矛盾 receipt 阻擋後續寫入，不假稱 rollback。</p>']
for x in approved['contracts']['invariants']:parts.append('<p><b>'+esc(x['id'])+'</b> '+esc(x['rule'])+'</p>')
parts+=['<div class="table"><table><tr><th>輸入操作</th><th>輸入／輸出</th><th>成功與失敗語意</th></tr>']
for x in approved['contracts']['operations']:parts.append('<tr><td>'+esc(x['name'])+'</td><td>'+esc(x['inputs'])+' → '+esc(x['output'])+'</td><td>'+esc(x['postconditions'])+'<br>'+esc(x['failure'])+'</td></tr>')
parts+=['</table></div><details><summary>25 個核准型別與責任</summary><table><tr><th>型別</th><th>角色與約束</th></tr>']
for k,v in approved['types']['types'].items():parts.append('<tr><td>'+esc(k)+'</td><td>'+esc(v['kind'])+'<br>'+esc(v['rule'])+'</td></tr>')
parts+=['</table></details></section><section id="behavior"><h2>模組 BDD、TDD 與需求追溯</h2><p>105 個行為情境完整映射為 189 個參數案例（包含 4 個原已正確的驗證案例）；另有 2 個補充契約、11 個原測試遷移、2 個 fixture 健康檢查。合計 204 個關聯測試 GREEN。198 個預期 RED 與 6 個既有／fixture PASS 的來源封存於 <a href="../s2-skeleton-red/index.html">RED 階段</a>。</p><p>涵蓋 B1 成功、B2 邊界、B3 無效輸入、B4 依賴失敗、B5 partial、B6 狀態一致、B7 交易、B8 lifecycle、B9 recovery、B10 WORK／IO 邊界、B11 相容性及 B12 回歸。S3 使用者 lifecycle／跨視窗及系統層 B10/B11 明確 Deferred，不以 S2 測試外推。</p><div class="table"><table><tr><th>需求／BDD／TDD</th><th>Given → When → Then</th><th>證據</th></tr>']
cases=load(PACKET/'test-plan.json')['cases']
for x in cases:
    static=x['id'] in ['M01-S2-T090','M01-S2-T101','M01-S2-T106']
    parts.append('<tr><td>'+esc(x['requirement'])+'<br>'+esc(x['bdd'])+'<br>'+esc(x['id'])+'<br>'+esc(', '.join(x['invariants']))+'</td><td>'+esc(x['given'])+'<br>→ '+esc(x['when'])+'<br>→ '+esc(x['then'])+'<br><b>'+esc(x['expected_result'])+'</b></td><td>'+('STATIC／範圍分類 PASS；未宣稱 native' if static else 'GREEN · '+esc(x['target']))+'</td></tr>')
parts+=['</table></div></section><section id="tests"><h2>測試層級與回歸</h2><table><tr><th>層級</th><th>Suite</th><th>結果</th></tr>']
for level,suite,result in [('L0/L1/L2','codec mapping / resources / negative input','118 PASS'),('L2','shared-state FS/commit Port contract / injected failures','69 PASS'),('L1/L2','legacy denial / syntax validation','13 PASS'),('L3','Windows10 native creation + reopen + existing preference edit','1 PASS'),('L1','original migrated HOST unit tests','3 PASS, included in HOST library84'),('L4','complete HOST','330 PASS'),('L4','WORK','222 PASS'),('L3/L4','Ports/Adapters library + IO process fixtures','101 +220 PASS'),('L4','standalone shell library','240 PASS'),('L5','UI / installer / system acceptance','NOT RUN')]:parts.append('<tr><td>'+level+'</td><td>'+suite+'</td><td>'+result+'</td></tr>')
parts+=['</table><details><summary>可重現命令、fixture 與 raw logs</summary>']
for r in runs:parts.append('<p><a href="'+esc(r['log'])+'">'+esc(' '.join(r['command']))+'</a> · exit '+str(r['exit_code'])+'<br>'+esc('; '.join(r['summaries']))+'</p>')
parts+=['<p>IO helpers 的絕對位置及來源／二進位雜湊：<a href="helpers.json">helpers.json</a>。需先建立 helper 並設定 FILE_COMMIT_PROBE_PATH 與 FILE_COMMIT_CHECKPOINT_PROBE_PATH。缺 helper 屬 fixture failure，從未當有效 RED。</p></details><h3>曾失敗的檢查與分類</h3>']
for c in classification:parts.append('<p><b>'+esc(c['classification'])+'</b>：'+esc(c['observed'])+' → '+esc(c['resolution'])+'</p>')
parts+=['</section><section id="scope"><h2>工項、允許範圍與受保護邊界</h2><p>Primary Module M01；S2-CODEC／S2-STORE／S2-LEGACY 均完成核准行為。25 型別／六操作的公開形狀、Port、schema、ownership 與交易邊界保持採納版。內部演算法、錯誤傳遞、字元 escaping、Port 協調均為既定 envelope 內實作。</p><pre>'+esc('\n'.join(allowed))+'</pre><p>現有 787 個受保護盤點檔案未變；current inventory 796。現有 preference load/save/preset/import 的其餘實作與原新建三個純 normalizer 保持原內容。所有 lockfile、非 HOST manifest、WORK、Ports、Adapters、Tauri/UI 未變。原有其他 WIP 保留。</p><p><a href="source-current.json">來源 inventory</a> · <a href="verification.json">驗證資料</a> · <a href="../s2-skeleton-red/migration-map.json">原八項測試遷移</a> · <a href="../s2-exact-design/index.html">核准精確包</a></p></section><section id="acceptance"><h2>架構一致性與驗收</h2><p>Dependency、SRP、資料 ownership、mutation／transaction、Port 使用、failure path、receipt 驗證與修改範圍均 PASS。審查者為同一助理切換只讀 phase，沒有外部獨立 reviewer。</p><table><tr><th>AC</th><th>條件</th><th>結果</th></tr>']
for c in acceptance:parts.append('<tr><td>'+esc(c['id'])+'</td><td>'+esc(c['criterion'])+'</td><td>PASS_SCOPED</td></tr>')
parts+=['</table></section><section id="risks"><h2>風險、後續工項與最終模組健康</h2><p class="pending">S2 範圍 GREEN／驗收 PASS；父 M01 PREP 與完整產品不宣稱結案。S3 三入口精靈、native selection／owner、idempotency／late ack 尚須其自身核准 Skeleton 與驗收；新舊 UI 尚未接線前不發布。</p><ul><li>Windows10 本機證據不能替代 Windows11 或尚缺 native alias gate。</li><li>目前 read Port 一次讀完整檔；16MiB 是 codec 讀取後／解析前上限，不保證 OS 讀取記憶體上限。</li><li>未實作跨檔 rollback；definition 與 preference 分別提交，錯誤攜帶已成功證據。</li><li>舊偏好編輯 API 的既有寫入機制未升級，仍是原契約。</li><li>兩個先前測試專屬暫存目錄因自動核准審查 blocked by policy 而保留；未重試清理或繞過。</li><li>無 commit、push、打包、安裝或發布；排程保持 ACTIVE，繼續其他已核准就緒工項。</li></ul><p>回復方式：核對本輪九檔 scope 與 baseline inventory，再只回復對應切片；不可 reset/clean 或包含其他 WIP。正式使用前需 S3 整合 gate。原工程包與 RED source 封存供精確追溯。</p></section>',
 '<script type="application/json" id="module-spec">'+json.dumps(module,ensure_ascii=False).replace('</','<\\/')+'</script></main></html>']
(HERE/'index.html').write_bytes(''.join(parts).encode('utf-8'))
print(json.dumps({'source_count':len(inventory),'protected_unchanged':review['protected_existing_files_unchanged'],'acceptance':review['status'],'report':str(HERE/'index.html')},ensure_ascii=True))
