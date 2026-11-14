"""Static documentation checker; not product tests, RED, schema conformance or acceptance."""
from pathlib import Path
import json,hashlib,re
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[5]
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
packet=load(OUT/'module-spec.json')
seal=load(OUT/'seal.json')
for name,h in seal['artifacts'].items(): assert sha(OUT/name)==h,name
for row in load(OUT/'source-inputs.json')['sources']: assert sha(ROOT/row['path'])==row['sha256'],row['path']
authority=load(ROOT/packet['authority']['authority_file'])
for name,h in authority['source_hashes'].items(): assert sha(ROOT/name)==h,name
page=(OUT/'index.html').read_text(encoding='utf-8')
embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',page,re.S).group(1))
assert embedded==packet
for href in re.findall(r'href="([^"]+)"',page): assert (OUT/href).resolve().is_file(),href
assert len(packet['trace'])==7 and all(x['status']=='PLANNED_NOT_RUN' for x in packet['trace'])
assert packet['identity']['zone']=='gray' and packet['identity']['feature_verdict']=='NOT_PROVEN'
result={'status':'PASS_STATIC_ONLY','feature':'NOT_PROVEN','protected_source_count':len(authority['source_hashes']),'sealed_artifacts':len(seal['artifacts']),'trace_rows':7,'feature_owned_plans':5,'adjacent_regressions':2,'product_tests':'NOT RUN','valid_RED':'NOT RUN','native':'NOT RUN','independent_acceptance':'NOT RUN','full_Draft_validation':'NOT RUN'}
(OUT/'static-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))

