import copy, hashlib, html, json, pathlib, re, subprocess
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[7]
OUT = pathlib.Path(__file__).resolve().parent
BASE = OUT.parent / 'input-admission-20261103'
REVIEW = OUT.parent / 'input-admission-review-20261103'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def put(name, obj): (OUT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
authority_path = ROOT/'docs/requirements-confirmation/phase1-spec/index.html'
authority = read(REVIEW/'authority-a-rows.json')
assert sha(authority_path) == authority['source_sha256']
source_html = authority_path.read_text(encoding='utf-8-sig')
cross = read(BASE/'native-case-crosswalk.json')
oldcross = copy.deepcopy(cross)
for i, row in enumerate(authority['rows']):
    assert row['raw_row'] in source_html
    cells = re.findall(r'<td>(.*?)</td>', row['raw_row'], re.S)
    cross['cases'][16+i] = {
        'id':row['id'], 'case_source':{'path':row['source'], 'pointer':row['selector'], 'sha256':authority['source_sha256']},
        'original_authority_raw_row':row['raw_row'], 'original_definition_verbatim':cells[0],
        'required_evidence_verbatim':cells[1], 'definition_availability':'AVAILABLE_AUTHORITY_BOUND',
        'mapping_status':'OPEN', 'reason':'Definition is available. Exact Feature/native equivalence and execution evidence have not been explicitly approved; topical overlap does not approve equivalence.',
        'required_input':'Owner-confirmed exact Feature/native correspondence and actual eligible runtime evidence',
        'provider':'Requirement/acceptance Owner and M08 planning owner', 'admission':'BLOCKED_NOT_RUN'}
cross['author']='/root/m08_admission_correction_packet'
cross['generated_at']=datetime.now(timezone.utc).isoformat()
cross['independent_document_review']='NOT RUN'
missing=read(BASE/'missing-inputs.json')
missing['author']=cross['author']; missing['generated_at']=cross['generated_at']
put('native-case-crosswalk.json',cross)
put('missing-inputs.json',missing)
# Feature trace/review and every other gate remain byte-identical.
(OUT/'feature-input-matrix.json').write_bytes((BASE/'feature-input-matrix.json').read_bytes())
invpath=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'
inv=read(invpath)
drift=[p for p,h in inv['source_hashes'].items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert len(inv['source_hashes'])==796 and not drift
assert head=='5b709343a890503ebbe24a802e43cda5647df124'
put('authority-check.json',{'live_HEAD':head,'historical_inventory_HEAD':inv['head'],'inventory_count':796,'product_drift':drift,'board_management':'Separate mutable management context; not product drift or acceptance authority','board_sha256':sha(ROOT/'docs/board.json')})

def validate(candidate):
    assert candidate['native']=='BLOCKED_NOT_RUN' and candidate['product_acceptance']=='NOT RUN'
    assert candidate['cases'][:16]==oldcross['cases'][:16]
    assert [x['id'] for x in candidate['cases'][16:]]==[x['id'] for x in authority['rows']]
    for got, expected in zip(candidate['cases'][16:],authority['rows']):
        assert got['case_source']['path']==expected['source']
        assert got['case_source']['sha256']==sha(authority_path)
        assert got['case_source']['pointer']==expected['selector']
        assert got['original_authority_raw_row']==expected['raw_row']
        assert got['mapping_status']=='OPEN' and got['admission']=='BLOCKED_NOT_RUN'
validate(cross)
results=[]
for label, mutate in [
    ('delete A01',lambda d:d['cases'].pop(16)),
    ('wrong authority source',lambda d:d['cases'][16]['case_source'].update(path='invented.html')),
    ('false product acceptance',lambda d:d.update(product_acceptance='PASS')),
    ('false mapping acceptance',lambda d:d['cases'][16].update(mapping_status='APPROVED')),
    ('alter original N',lambda d:d['cases'][0]['original_case_verbatim'].update(then='invented'))]:
    bad=copy.deepcopy(cross); mutate(bad)
    try: validate(bad)
    except AssertionError: results.append({'mutation':label,'result':'REJECTED'})
    else: raise AssertionError(label)
put('author-checks.json',{'role':'AUTHOR DEVELOPMENT STATIC CHECKS ONLY; not independent acceptance','positive':'PASS','new_negative_mutations':results,'independent_review':'NOT RUN','product_native':'BLOCKED_NOT_RUN'})
closure={'finding':'R1','status':'CORRECTION_DELIVERED_INDEPENDENT_REVIEW_PENDING','changes':'Replace only eight A entries with exact authority definitions/evidence/pointers/hash; remove eight incorrect unavailable-definition reasons. All A equivalence remains OPEN.', 'unchanged_missing_input_count':len(missing['items']),'missing_input_ids':[x['id'] for x in missing['items']],'missing_input_delta':0,'explanation':'Original missing-inputs.json contains 20 items, no standalone A definition item; only crosswalk reasons and HTML require correction. No arbitrary count target.', 'preserved':'16 N entries unchanged; 12 Feature trace/review unchanged; PD1..3 unapproved, Win11/artifact/provider/observability blocked; no PREP reopen; no native acceptance','independent_acceptance':'NOT RUN'}
put('closure-diff.json',closure)
rows=''.join('<tr><td>'+html.escape(x['id'])+'</td><td>'+html.escape(x['original_definition_verbatim'])+'</td><td>'+html.escape(x['required_evidence_verbatim'])+'</td><td>OPEN / BLOCKED_NOT_RUN</td></tr>' for x in cross['cases'][16:])
page='<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>M08 R1 correction</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.6}td,th{border:1px solid #aaa;padding:10px}table{border-collapse:collapse}pre{white-space:pre-wrap}</style><h1>M08 輸入盤點 R1 補正</h1><p>文件補正已交付；獨立驗收 NOT RUN。產品／原生驗收 BLOCKED_NOT_RUN。作者不可自驗收。</p><p>A01–A08 原始定義存在於 phase1-spec/index.html，已逐列保留原文、來源 pointer、SHA256 與證據欄。移除原候選「缺少定義」理由；Feature/native 精確等價仍 OPEN。</p><table><tr><th>ID</th><th>原始定義</th><th>原始必要證據</th><th>狀態</th></tr>'+rows+'</table><h2>差異與未決條件</h2><pre>'+html.escape(json.dumps(closure,ensure_ascii=False,indent=2))+'</pre><p>live HEAD '+head+'；796 產品來源 hash 無漂移。31babe87 為歷史 inventory HEAD；board 管理漂移分開記錄。</p><p>未改產品、測試、BDD、schema、threshold、runner、hooks、roles、board 或 accepted PREP。未 build/package/native/install/commit/push；未批准 PD1–3。</p><h2>完整人機可讀資料</h2><ul>'+''.join('<li><a href="'+n+'">'+n+'</a></li>' for n in ['native-case-crosswalk.json','feature-input-matrix.json','missing-inputs.json','closure-diff.json','authority-check.json','author-checks.json','source-hashes.json','seal.json'])+'</ul><p>本次新靜態檢查及五項負向 mutation 是作者開發證據；不能取代獨立 review 或產品證據。原候選與 review 保留不動。</p></html>'
(OUT/'index.html').write_text(page,encoding='utf-8')
sources=list(BASE.iterdir())+[REVIEW/'authority-a-rows.json',REVIEW/'findings.json',authority_path,invpath,ROOT/'docs/board.json',ROOT/'AGENTS.md',ROOT/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-M08-VERIFY-01.json',ROOT/'reports/rust-improvements/continuous/coordination/heartbeat-latest.json']
put('source-hashes.json',{'sources':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in sources if p.is_file()},'note':'Heartbeat and board hashes are snapshot context, not approval inferred from content fields.'})
put('seal.json',{'author':cross['author'],'status':'SEALED_FOR_INDEPENDENT_REVIEW','files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'output':str(OUT),'missing_count':len(missing['items']),'product_hashes':796,'drift':drift,'mutations':results}))
