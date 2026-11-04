"""Read-only production-source inventory; writes this proposal package only."""
from pathlib import Path
import hashlib, json, subprocess, datetime, html, re

ROOT = Path(__file__).resolve().parents[7]
OUT = Path(__file__).resolve().parent
BASE = 'docs/requirements-confirmation/phase1-spec/tasks/'
def sha(b): return hashlib.sha256(b).hexdigest()
def read(p): return (ROOT/p).read_bytes()
def load(p): return json.loads(read(p))
def write(name, obj): (OUT/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def git(*args): return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()

assert (ROOT/'AGENTS.md').exists(), ROOT
authority_path = BASE+'M01/planning/s2-green/source-current.json'
authority = load(authority_path)['source_hashes']
drift = [p for p,h in authority.items() if not (ROOT/p).exists() or sha(read(p)) != h]
assert len(authority)==796 and not drift
port='apps/sgenaxis-desktop/crates/sgenaxis-ports/src/file_commit.rs'
adapter='apps/sgenaxis-desktop/crates/sgenaxis-adapters/src/file_commit.rs'
host='apps/sgenaxis-desktop/crates/sgenaxis-host/src/project_definition.rs'
spans=[]
for ident,p,a,b,meaning in [
 ('S1',port,22,30,'CommitReceipt exports only target path, previous digest, committed digest, transaction ID.'),
 ('S2',port,58,74,'FileCommitPort and FileWriteLease expose acquire/read/replace, no issuer lookup or lease-proof getter.'),
 ('S3',adapter,18,53,'StdFileCommit acquires a boxed lease; native sidecar handle is private and owned by lease.'),
 ('S4',adapter,236,250,'regular_identity calls GetFileInformationByHandle and checks attributes/link count; returns unit, not volume/file identity evidence.'),
 ('S5',adapter,411,445,'Acquire uses sidecar share_mode(0), validates sidecar, reads target, inspects journal, retains handle.'),
 ('S6',adapter,895,925,'CAS compares previous digest; journal records target/digests/transaction/state, not Ready issuer context.'),
 ('S7',adapter,955,993,'Publish rechecks prior digest, verifies bytes, commits journal, constructs the four-field receipt.'),
 ('S8',host,1632,1655,'HOST checks target/prior/new digest and 32 lowercase-hex transaction ID, not native lease provenance.'),
 ('S9',host,1789,1796,'HOST obtains lease and reads current contents locally.'),
 ('S10',host,1851,1867,'Lease scope closes before result proof construction; returned commit receipt is not evidence of a continuing held lease.')]:
 lines=read(p).decode('utf-8').splitlines();assert b<=len(lines)
 spans.append({'id':ident,'path':p,'sha256':sha(read(p)),'start':a,'end':b,'text':'\n'.join(lines[a-1:b]),'meaning':meaning,'layer':'STATIC_SOURCE_ONLY'})

decisions=load(BASE+'M01/planning/copy-ready-correction/owner-decisions.json')
request_fields=load(BASE+'M01/planning/copy-ready-correction/field-binding.json')
rows=[
 {'id':'P1','responsibility':'Native held lease authority (CR-D1)','exists':'Private StdFileWriteLease owns a sidecar OS handle; acquire uses exclusive sharing.','not_proven':'No public native_lease_id, native volume/file identity tuple, issuer record, marker-path binding or continuing lease proof in this Port/receipt.','sources':['S1','S2','S3','S4','S5','S10'],'required_provider':'IO/native provider architect + independent Windows 11 verifier','next_original_scope':'Prepare proposed native-provider schema/lifecycle options bound to this actual Port gap; do not extend Port until architecture approval.','classification':'ARCHITECTURE_GAP_FOR_PROPOSED_COPY_READY','selected':None},
 {'id':'P2','responsibility':'Durable Ready issuance / restart lookup (CR-D2)','exists':'Single-file journal and HOST commit-evidence checks exist.','not_proven':'Single-file journal is not a durable Ready issuer table: it lacks whole-request/context/provider/copy/catalog proof bindings. No restart Ready issuer lookup was located by the scoped token inventory.','sources':['S1','S2','S6','S7','S8'],'required_provider':'M01 Ready authority architect; M05 catalog and M06 copy evidence providers; independent restart verifier','next_original_scope':'Design durable record/lookup/retention and crash-window comparison as pending proposals; do not treat fixture dictionary lookup as native restart proof.','classification':'MISSING_ADMITTED_PROVIDER_EVIDENCE','selected':None},
 {'id':'P3','responsibility':'Returned receipt authority boundary','exists':'HOST validates receipt path/digests/transaction shape against the request.','not_proven':'Field equality does not authenticate issuer, grant a lease lifetime, or admit a new publish representation.','sources':['S1','S8','S10'],'required_provider':'M01 contract owner with IO evidence provider','next_original_scope':'Keep current four-field receipt and proposed copy-Ready shape separately reviewed; exact migration remains CR-D3.','classification':'EXISTING_RECEIPT_NOT_COPY_READY_AUTHORITY','selected':None}
]
product_files=sorted(ROOT/p for p in authority if p.startswith('apps/sgenaxis-desktop/') and p.endswith('.rs'))
tokens=['native_lease_id','ready_proof_id','provider_proof_id','target_native_identity','issuer_records','ReadyIssuer']
inventory=[]
for token in tokens:
 hits=[]
 for p in product_files:
  for n,line in enumerate(p.read_text(encoding='utf-8').splitlines(),1):
   if token in line: hits.append({'path':p.relative_to(ROOT).as_posix(),'line':n,'text':line})
 inventory.append({'token':token,'scope':'Rust files in admitted authority796 under apps/sgenaxis-desktop only','files_scanned':len(product_files),'hits':hits,'limit':'Literal token search only; absence is not semantic proof that no differently named provider exists.'})

coverage=[]
for field,bindings in request_fields.items():
 if field=='final_canonical_path': state='RELATED_EXISTING_FIELD_NOT_EQUIVALENT'; refs=['S1','S5','S8']
 else: state='NO_EXACT_PUBLIC_FIELD_IN_COMMIT_RECEIPT'; refs=['S1','S2']
 coverage.append({'proposed_copy_ready_field':field,'current_commit_receipt_mapping':state,'sources':refs,'proposed_fixture_bindings':bindings,'adoption':None})

actions=load(BASE+'M01/planning/current-action-blockers-20261103/actions.json')['cards']
yellow=[]
for c in actions:
 if c.get('light')=='Yellow' and c['id']!='PD-P1-M02-PREP-01':
  yellow.append({k:c[k] for k in ['id','action','missing_conditions','provider'] if k in c})
for c in yellow:
 c['this_round']='M01 new actual Port/adapter/HOST source map delivered' if c['id']=='PD-P1-M01-PREP-01' else 'Remaining requested inputs retained; no historical PASS rerun or product implementation.'
 c['scope_note']='Historical blocker register projection, not a claim all future preparation is exhausted.'

tests=[
 {'id':'DOC-P1','given':'Current CommitReceipt definition','when':'Extract public fields','then':'Exactly four legacy fields; native lease authority is not inferred.','actual':re.findall(r'pub (\w+):',spans[0]['text']),'expected':['target_path','previous_digest','committed_digest','transaction_id']},
 {'id':'DOC-P2','given':'regular_identity source','when':'Inspect returned representation','then':'Unit Result and no returned native identity tuple.','actual':'-> std::io::Result<()>' in spans[3]['text'],'expected':True},
 {'id':'DOC-P3','given':'Proposed copy-Ready fields','when':'Compare with current receipt','then':'Every proposed field has explicit non-equivalence and no adoption.','actual':all(x['adoption'] is None for x in coverage),'expected':True},
 {'id':'DOC-P4','given':'Private native sidecar lock','when':'Inspect lifetime and HOST scope','then':'Do not reinterpret private held handle as returned issuer proof.','actual':'_lock_handle' in spans[2]['text'] and 'let receipt = {' in spans[8]['text'] and '};' in spans[9]['text'],'expected':True},
 {'id':'DOC-P5','given':'Authority796','when':'Hash all entries','then':'Zero product drift; live HEAD separately recorded.','actual':len(drift),'expected':0}
]
assert all(t['actual']==t['expected'] for t in tests), tests
result={'author':'/root/yellow_scope_next','status':'AUTHOR_DOCUMENT_PREPARATION_ONLY_PENDING_INDEPENDENT_REVIEW','generated_at':datetime.datetime.now().astimezone().isoformat(),'task':'PD-P1-M01-PREP-01','branch':git('branch','--show-current'),'live_head':git('rev-parse','HEAD'),'historical_product_head':'31babe87a7ef1e40a0d4bedc523077e7a45d63ab','authority_count':len(authority),'authority_drift':drift,'scope':'New static source mapping only; no architecture/schema/Port adoption or production change.','rows':rows,'field_coverage':coverage,'owner_decisions':decisions,'other_yellow_actions':yellow,'product_native_runtime':'NOT RUN','historical_pass_rerun':False,'selected':None}
write('module-spec.json',result);write('source-spans.json',spans);write('token-inventory.json',inventory);write('author-checks.json',tests)
sources=[authority_path,BASE+'PD-P1-M01-PREP-01.json',BASE+'M01/planning/copy-ready-correction/owner-decisions.json',BASE+'M01/planning/copy-ready-correction/field-binding.json',BASE+'M01/planning/current-action-blockers-20261103/actions.json',port,adapter,host,'AGENTS.md']
write('source-hashes.json',{p:sha(read(p)) for p in sources})
body='<h1>M01 真實 provider／receipt 邊界對照</h1><p>新增來源調查；只限文件準備，未採納，產品／native NOT RUN。不是重跑歷史 PASS。</p><p>目前 IO 確實有私有 native handle，但它不是呼叫方可攜回的 Ready issuer 證據。regular_identity 只回傳 unit；四欄 receipt 不含 lease authority。新提案所需的 durable Ready issuer 不可用現有單檔 journal 冒充。</p>'
body+='<p>HEAD '+html.escape(result['live_head'])+'；authority 796 零漂移；歷史產品 SHA 另列，不能宣稱 same HEAD。</p>'
for row in rows:
 body+='<section id="'+row['id']+'"><h2>'+html.escape(row['responsibility'])+'</h2><dl>'+''.join('<dt>'+html.escape(k)+'</dt><dd>'+html.escape(str(row[k]))+'</dd>' for k in ['exists','not_proven','required_provider','next_original_scope','classification'])+'</dl></section>'
body+='<h2>需要產品決策，未代選</h2><p>CR-D1：provider schema／lease lifecycle／平台驗證。CR-D2：durable issuance／lookup／restart／diagnostics。CR-D3：完整 publish shape／byte representation／migration。建議先補工程方案後逐項確認；本報告不批准新 Port。</p>'
body+='<h2>精確來源片段</h2>'
for s in spans: body+='<details><summary>'+s['id']+' '+html.escape(s['path'])+':'+str(s['start'])+'–'+str(s['end'])+'</summary><p>'+html.escape(s['meaning'])+'</p><pre>'+html.escape(s['text'])+'</pre></details>'
body+='<h2>欄位與其他黃卡</h2><p>參見 <a href="module-spec.json">module-spec.json</a>：'+str(len(coverage))+' 個提案欄位逐一標示，'+str(len(yellow))+' 張其他/本模組黃卡沿用其缺件與責任人；M02 另由 Golden14 作者處理。</p><p><a href="token-inventory.json">限定 Rust token 搜尋</a> 不能證明全系統不存在其他命名 provider。<a href="author-checks.json">5 項新文件自檢</a> 不是獨立驗收。</p>'
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M01 provider source map</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto;line-height:1.6}dt{font-weight:bold}pre{white-space:pre-wrap;background:#eee;padding:15px}section{border-top:1px solid #aaa}</style>'+body,encoding='utf-8')
write('seal.json',{'author':'/root/yellow_scope_next','state':'SEALED_AUTHOR_DOCUMENT_ONLY','files':{p.name:sha(p.read_bytes()) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}})
print(json.dumps({'output':str(OUT),'rows':len(rows),'spans':len(spans),'coverage':len(coverage),'yellow':len(yellow),'checks':len(tests),'source_drift':len(drift)}))
