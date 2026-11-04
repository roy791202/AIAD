"""Static documentary checker only; never feature validation."""
from pathlib import Path
import json, hashlib, re
P=Path(__file__).resolve().parent
R=P.parents[5]
def read(n): return json.loads((P/n).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
s=read('module-spec.json'); rows=read('traceability.json')
assert len(rows)==5 and len({x['test_id'] for x in rows})==5
assert s['original_packet']==json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F07-DELIVERY-01.json').read_text(encoding='utf-8-sig'))
assert set(s['exact_scenario_equivalence'])=={'BDD-11','BDD-12'}
assert rows[2]['bdd']==[] and rows[4]['bdd']==[]
assert all(x['status']=='PLANNED_NOT_RUN' for x in rows)
assert all(x['command']=='BLOCKED_PENDING_OWNER_ENVELOPE_SKELETON_RUNNER' for x in rows)
for path,h in read('inputs.json').items(): assert sha(R/path)==h,path
i=read('source-integrity.json'); assert i['count']==796 and not i['drift']
authority=json.loads((R/i['authority']).read_text(encoding='utf-8-sig'))
assert len(authority['source_hashes'])==796
for path,hsh in authority['source_hashes'].items(): assert sha(R/path)==hsh,path
h=(P/'index.html').read_text(encoding='utf-8')
assert json.loads(re.search(r'<script id="module-spec" type="application/json">(.*?)</script>',h,re.S)[1])==s
for link in re.findall(r'href="([^"]+)"',h): assert (P/link).resolve().is_file(),link
assert s['identity']['zone']=='gray'
result={'status':'PASS_STATIC_DOCUMENT_SCOPE_ONLY','trace_rows':len(rows),'exact_original_scenarios':2,'product_inventory':796,'product_tests':'NOT RUN','independent_review':'NOT RUN','build':'NOT RUN','native':'NOT RUN','valid_RED':'NOT RUN','full_Draft':'NOT RUN','feature_PASS':False,'module_PASS':False,'Done':False,'next_action':s['next_action']}
(P/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
