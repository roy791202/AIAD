import json,pathlib,hashlib,re
O=pathlib.Path(__file__).resolve().parent; R=O.parents[6]
# Locate repo by known root marker, no filesystem mutation outside this folder.
R=next(p for p in O.parents if (p/'apps/sgenaxis-desktop/Cargo.toml').is_file())
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((O/'trace.json').read_text(encoding='utf-8')); failures=[]
def ck(ok,message):
 if not ok: failures.append(message)
ck(d['feature']=='F01' and d['feature_count']==1,'one original feature')
ck(len(d['trace'])==3 and {r['bdd'] for r in d['trace']}=={'BDD-01','BDD-02'},'original AC01 and BDD coverage counts')
ck(d['original_bdd_count']==2 and len(d['recipes'])==2,'sealed case/recipe counts')
ck(d['board_zone']=='gray' and d['state']=='PLANNING_ONLY','no completion inference')
ck(d['inventory_count']==796 and not d['inventory_current_drift'],'authority source inventory')
for p,h in d['sources'].items(): ck((R/p).is_file() and digest(R/p)==h,'source drift '+p)
for t in d['tests']:
 lines=(R/t['source']).read_text(encoding='utf-8').splitlines()
 ck(lines[t['line']-1].startswith('fn '+t['name']+'('),'test source pointer '+t['name'])
 ck(t['executed_this_run'] is False,'existing test not current execution')
for recipe in d['recipes']: ck(recipe['status']=='PLANNED_NOT_RUN' and recipe['oracle'] and recipe['valid_red'],'planned oracle/RED boundary')
page=(O/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'<script type="application/json" id="feature-trace">(.*?)</script>',page,re.S).group(1)); ck(embedded==d,'embedded trace equality')
for href in re.findall('href="([^"]+)"',page): ck((O/href).resolve().is_file(),'local link '+href)
seal=json.loads((O/'seal.json').read_text(encoding='utf-8'))
for name,expected in seal.get('files',{}).items():
 if name != 'check-result.json': ck(digest(O/name)==expected,'output seal drift '+name)
result={'scope':'STATIC_DOCUMENT_INTEGRITY_ONLY_NOT_FEATURE_PASS','status':'PASS' if not failures else 'FAIL','failures':failures,'feature_count':1,'original_bdd_count':2,'AC01_behavior_rows':3,'existing_test_pointers':len(d['tests']),'planned_recipes':2,'source_inventory':796,'source_drift':len(d['inventory_current_drift']),'product_tests':'NOT RUN','RED':'NOT RUN','native':'NOT RUN','build':'NOT RUN','independent_acceptance':'NOT RUN','board':'UNCHANGED_GRAY_RETAINED'}
(O/'check-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False)); raise SystemExit(bool(failures))
