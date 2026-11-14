import pathlib,json,hashlib,re,subprocess
O=pathlib.Path(__file__).resolve().parent
R=next(p for p in O.parents if (p/'apps/sgenaxis-desktop/Cargo.toml').is_file())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((O/'trace.json').read_text(encoding='utf-8')); failures=[]
def ck(ok,m):
 if not ok: failures.append(m)
ck(d['feature']=='F02' and d['feature_count']==1,'one feature')
ck(d['head']=='5b709343a890503ebbe24a802e43cda5647df124','current HEAD authority')
ck(subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()==d['head'],'HEAD drift')
ck(d['board_zone']=='gray' and d['state']=='PLANNING_ONLY','Gray planning boundary')
ck(len(d['trace'])==3 and len(d['recipes'])==3,'three exact AC02 clauses and recipes')
ck({b for r in d['trace'] for b in r['original_bdd']}=={'BDD-03','BDD-04'},'original BDD retained')
original=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F02-DELIVERY-01.json').read_text(encoding='utf-8'))
ck(d['original_acceptance']==original['acceptance'],'original AC unchanged')
for p,h in d['sources'].items(): ck((R/p).is_file() and sha(R/p)==h,'source hash '+p)
inv=json.loads((R/d['inventory_authority']).read_text(encoding='utf-8'))['source_hashes']
ck(len(inv)==796 and d['inventory_count']==796,'796 inventory authority')
for p,h in inv.items(): ck((R/p).is_file() and sha(R/p)==h,'product inventory '+p)
for t in d['tests']:
 lines=(R/t['source']).read_text(encoding='utf-8').splitlines()
 ck(lines[t['line']-1].startswith('fn '+t['name']+'('),'exact test pointer '+t['name'])
 ck(t['executed_this_run'] is False,'not currently executed')
for r in d['recipes']: ck(r['status']=='PLANNED_NOT_RUN' and r['valid_red'] and r['fixture_recipe'],'planned recipe integrity')
page=(O/'index.html').read_text(encoding='utf-8')
ck(json.loads(re.search(r'<script type="application/json" id="feature-trace">(.*?)</script>',page,re.S).group(1))==d,'embedded trace equality')
for link in re.findall(r'href="([^"]+)"',page):
 if link!='check-result.json': ck((O/link).resolve().is_file(),'local link '+link)
seal=json.loads((O/'seal.json').read_text(encoding='utf-8'))
for p,h in seal['files'].items(): ck(sha(O/p)==h,'output seal '+p)
result={'status':'PASS' if not failures else 'FAIL','scope':'STATIC_DOCUMENT_INTEGRITY_ONLY_NOT_FEATURE_PASS','failures':failures,'counts':seal['counts'],'board':'UNCHANGED_GRAY_RETAINED','product_tests':'NOT RUN','build':'NOT RUN','native_UI':'NOT RUN','valid_RED':'NOT RUN','independent_acceptance':'NOT RUN','full_Draft':'NOT RUN'}
(O/'check-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False)); raise SystemExit(bool(failures))
