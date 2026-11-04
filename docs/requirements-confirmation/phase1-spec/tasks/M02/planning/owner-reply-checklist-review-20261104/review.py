import json,hashlib,re,copy,subprocess,html
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7]
BASE=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning'
OUT=Path(__file__).parent
ORIG=BASE/'owner-reply-checklist-20261104'
CAN=BASE/'owner-reply-checklist-correction-20261104'
checks=[]
def ck(name,value):checks.append({'name':name,'pass':bool(value)})
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def seals(p):
 s=json.loads((p/'seal.json').read_text(encoding='utf-8'));return all(sha(p/k)==v for k,v in s['files'].items())
before={str(p.relative_to(ROOT)):sha(p) for dr in [ORIG,CAN] for p in dr.iterdir() if p.is_file()}
for dr in [ORIG,CAN]:ck('sealed:'+dr.name,seals(dr))
d=json.loads((CAN/'checklist.json').read_text(encoding='utf-8'));s=(CAN/'index.html').read_text(encoding='utf-8');embed=json.loads(re.search(r'<script type="application/json" id="reply-checklist">(.*?)</script>',s,re.S).group(1));ck('embedded parity',embed==d)
for b in d['source_bindings']:ck('source:'+b['path'],sha(ROOT/b['path'])==b['sha256'])
for x in d['items']:
 ck('null:'+x['id'],x['selected'] is None)
 ck('visible:'+x['id'],('id="'+x['id']+'"') in s and html.escape(x['question']) in s and html.escape(x['actual_candidate']) in s)
 for f in x['evidence']:ck('evidence exists:'+f,(ROOT/f).exists())
for href in re.findall(r'href="([^"]+)"',s):
 if not href.startswith(('http','#')):ck('HTML link:'+href,(CAN/href).exists())
items={x['id']:x for x in d['items']}
ck('first four order',[x['id'] for x in d['items'][:4]]==['GT-D1','GT-D2','GT-D3','GT-D4'])
ck('GT3 exempt',not items['GT-D3']['requires_owner_reply'] and items['GT-D3']['options']=={})
ck('GT2 example and policy','0.1.0' in items['GT-D2']['question'] and 'proposal fixture' in items['GT-D2']['actual_candidate'])
ck('GT4 independent options',set(items['GT-D4']['options'])=={'GT-D4a.A','GT-D4a.B','GT-D4b.A','GT-D4b.B'})
ledger=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/s1/adoption.json').read_text(encoding='utf-8'))
for k,v in ledger['approved_artifact_hashes'].items():ck('adopted hash:'+k,sha(ROOT/k)==v)
ck('DX1..7 adopted',ledger['adopted']==['M02-DX'+str(i) for i in range(1,8)])
raw=(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/exact-design/module-spec.json').read_text(encoding='utf-8');ck('adopted target assumption',all(v in raw for v in ['Windows11 x64','Rust＋Vanilla UI','Tauri2','has_ui=true']))
for f in ['tauri.conf.json','Cargo.toml','rust-toolchain.toml']:
 txt=(BASE/'golden14-candidate-20261104/expected/program/src-tauri'/f).read_text(encoding='utf-8');ck('actual candidate embedded:'+f,html.escape(txt.strip()) in s)
m=items['DEC-M03-01']['actual_candidate'];ck('M03 corrected families',all('MM0'+str(i) in m for i in range(1,9)) and '影片' in m and '文字、' not in m)
ck('five other decisions',set(items)-{'GT-D1','GT-D2','GT-D3','GT-D4'}=={'DEC-M02-01','DEC-M03-01','DEC-M04-01','DEC-M05-01','DEC-M07-01'})
ck('BDD19 retained',any('BDD19' in x['item'] and '繼續有效' in x['work'] for x in d['engineering_not_owner_questions']))
h=json.loads((ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))['source_hashes'];ck('796',len(h)==796 and all(sha(ROOT/k)==v for k,v in h.items()))
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();ck('live HEAD',head==d['live_head'] and head!=d['historical_head'])
def valid(z):
 a={x['id']:x for x in z['items']}
 return z['selected'] is None and not z['product_pass'] and all(x['selected'] is None for x in z['items']) and not a['GT-D3']['requires_owner_reply'] and not a['GT-D3']['options'] and all('MM0'+str(i) in a['DEC-M03-01']['actual_candidate'] for i in range(1,9)) and '影片' in a['DEC-M03-01']['actual_candidate'] and 'proposal fixture' in a['GT-D2']['actual_candidate'] and 'GT-D4a.A' in a['GT-D4']['options'] and 'GT-D4b.A' in a['GT-D4']['options']
probes=[]
def probe(name,fn):
 z=copy.deepcopy(d);fn(z);probes.append({'name':name,'rejected':not valid(z)})
probe('auto selection',lambda z:z.update(selected='A'))
probe('product pass inflation',lambda z:z.update(product_pass=True))
probe('item adoption',lambda z:z['items'][0].update(selected='A'))
probe('reask GT3',lambda z:z['items'][2].update(requires_owner_reply=True))
probe('invent GT3 options',lambda z:z['items'][2].update(options={'A':'approve toolchain'}))
probe('omit video',lambda z:z['items'][5].update(actual_candidate=z['items'][5]['actual_candidate'].replace('影片','文字')))
probe('fixture identity formal',lambda z:z['items'][1].update(actual_candidate='formal production identity'))
probe('collapse independent GT4',lambda z:z['items'][3].update(options={'A':'all'}))
ck('new rejection probes',all(p['rejected'] for p in probes))
ck('candidate unchanged',before=={str(p.relative_to(ROOT)):sha(p) for dr in [ORIG,CAN] for p in dr.iterdir() if p.is_file()})
result={'reviewer':'/root/owner_reply_independent_review','author':d['author'],'verdict':'BOUNDED_DOCUMENT_REVIEW_PASS' if all(c['pass'] for c in checks) else 'CHANGES_REQUESTED','checks':checks,'probes':probes,'findings':[c for c in checks if not c['pass']],'original_defect':'Original M03 shorthand omitted video and introduced text; canonical correction retains exact MM01..08. Original sealed unchanged.','limits':['Product/native/build/acceptance NOT RUN','No product adoption','No historical PASS rerun'],'live_head':head}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Owner reply independent review</title><h1>'+result['verdict']+'</h1><p>作者 '+d['author']+'；獨立審查 /root/owner_reply_independent_review。'+str(len(checks))+' 檢查，'+str(len(probes))+' 新負向 probes。</p><p>GT-D3 已採納目標免回覆；其他選項未代選。M03 原清單維度錯誤已由另包補正，MM01–MM08 確認；原封存保留。</p><p>產品/native/build/驗收 NOT RUN；不重跑歷史 PASS。</p><a href="../owner-reply-checklist-correction-20261104/index.html">補正後可回覆清單</a><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre></html>',encoding='utf-8')
(OUT/'seal.json').write_text(json.dumps({'reviewer':result['reviewer'],'files':{f:sha(OUT/f) for f in ['review.py','results.json','index.html']}},indent=2)+'\n',encoding='utf-8')
print(result['verdict'],len(checks),len(probes),result['findings'])
