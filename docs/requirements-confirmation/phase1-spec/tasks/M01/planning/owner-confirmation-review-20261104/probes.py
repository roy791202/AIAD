import json, hashlib, re, html, subprocess
from pathlib import Path
from html.parser import HTMLParser
ROOT=Path('D:/AIAD'); OUT=Path(__file__).resolve().parent; C=OUT.parent/'owner-confirmation-checklist-20261104'
def load(p): return json.loads(p.read_text(encoding='utf8'))
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
d=load(C/'checklist.json'); checks=[]
def ck(name,ok,detail): checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail))
cache={}; hashes={}
def src(path):
 if path not in cache:
  p=ROOT/path; raw=p.read_bytes(); hashes[path]=hashlib.sha256(raw).hexdigest(); cache[path]=json.loads(raw)
 return cache[path]
def pointer(obj,p):
 for k in p.split('/')[1:] if p else []:
  k=k.replace('~1','/').replace('~0','~'); obj=obj[int(k)] if isinstance(obj,list) else obj[k]
 return obj
bindings=[]
def walk(x):
 if isinstance(x,dict):
  if {'path','sha256','pointer','value'}<=x.keys():
   try:
    val=pointer(src(x['path']),x['pointer']); ok=hashes[x['path']]==x['sha256'] and val==x['value']; bindings.append(dict(path=x['path'],pointer=x['pointer'],status='PASS' if ok else 'FAIL'))
   except Exception as e: bindings.append(dict(path=x['path'],pointer=x['pointer'],status='FAIL',error=str(e)))
  for v in x.values(): walk(v)
 elif isinstance(x,list):
  for v in x: walk(v)
walk(d)
ck('recursive_exact_bindings',all(x['status']=='PASS' for x in bindings),dict(bindings=len(bindings),unique_sources=len(cache)))
sh=load(C/'source-hashes.json'); cachechecks=[]
for s in sh:
 src(s['path']); cachechecks.append(hashes[s['path']]==s['sha256']==digest(C/s['cache']))
ck('source_cache_live_binding',all(cachechecks),len(cachechecks))
seal=load(C/'seal.json'); ck('candidate_seal',all(digest(C/p)==h for p,h in seal['files'].items()),len(seal['files']))
h=(C/'index.html').read_text(encoding='utf8'); emb=re.search(r'<script type="application/json" id="checklist-data">(.*?)</script>',h,re.S).group(1)
ck('embedded_json_parity',json.loads(emb)==d,'exact full data equality')
class P(HTMLParser):
 def __init__(self): super().__init__(); self.articles={}; self.current=None; self.radios=[]
 def handle_starttag(self,t,a):
  a=dict(a)
  if t=='article': self.current=a.get('id'); self.articles[self.current]=''
  if t=='input': self.radios.append(a)
 def handle_endtag(self,t):
  if t=='article': self.current=None
 def handle_data(self,s):
  if self.current: self.articles[self.current]+=s
p=P();p.feed(h)
ck('12_questions_visible_parity',len(d['items'])==12 and len(p.articles)==12 and all(all(s in p.articles[x['id']] for s in [x['question'],x['recommendation'],x['unlock']]+x['options']) for x in d['items']),'questions/options/recommendations/impact match rendered articles')
ck('unselected_no_authority',d['selected'] is None and all(x['selected'] is None for x in d['items']) and all('checked' not in x for x in p.radios),'JSON null; no checked radios')
items={x['id']:x for x in d['items']};gold=items['SUP-M02-01']['exact_candidates'][0]['value']; declared=src('docs/requirements-confirmation/phase1-spec/tasks/M02/planning/exact-design/module-spec.json')['first_template']['product_paths']
ck('golden14_exact_paths_missing_providers',len(gold)==14 and [x['declared_product_path'] for x in gold]==declared and all(x['submitted_resource']['status']=='MISSING' and x['golden']['status']=='MISSING' and x['lock_provider_evidence']['status']=='MISSING' and x['submitted_resource']['provider']=='M02 template author' for x in gold),'all 14 paths exact; actual bytes/golden/lock absent; author + independent reviewer duties retained')
authority=src(d['authority']['path']); ck('authority_796_manifest_binding',len(authority['source_hashes'])==796 and authority['head']==d['historical_head'] and hashes[d['authority']['path']]==d['authority']['sha256'],'Manifest identity and 796 entries verified; historical individual source bytes not revalidated')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();ck('head_authority_distinction',d['live_head']==head and d['historical_head']!=head and d['authority_count']==796,'live='+head+'; historical='+d['historical_head'])
ck('io_not_adoption',items['SUP-IO-01']['exact_candidates'][0]['value']['owner_adoption_required'] is False,'environment supply only')
ck('M06_BDD19_not_silently_changed','BEHAVIOR_CHANGE' in items['DEC-M06-02']['options'][1] and 'BDD-19' in items['DEC-M06-02']['options'][0],'preserve full rollback or explicit spec revision; no selection')
ra=items['DEC-M07-02'];ck('M07_no_invented_formula',[x['value']['id'] for x in ra['exact_candidates']]==['RA-C-O1','RA-C-O2'] and 'illustrative /0' in ra['question'],'existing candidates only; /0 explicitly not adopted formula')
ck('adopted_not_reasked',len(d['already_confirmed'])==7 and all(not any(y['value'].get('id','').startswith(('DX','M01-S2-D')) for y in x['exact_candidates'] if isinstance(y['value'],dict)) for x in d['items']),'ledger facts and decision definition statuses retained; existing adoption is not a new selection')
findings=[]
results=dict(reviewer='/root/owner_checklist_review',author=d['author'],verdict='BOUNDED_DOCUMENT_REVIEW_PASS' if all(x['status']=='PASS' for x in checks) else 'REQUEST_CHANGES',checks=checks,scope='Document semantic/source projection only; no production, native, UI execution, BDD/TDD RED/GREEN or acceptance claims',historical_pass='Not rerun or promoted',findings=findings)
(OUT/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n',encoding='utf8');(OUT/'source-probes.json').write_text(json.dumps(bindings,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps(results,ensure_ascii=True,indent=2))

