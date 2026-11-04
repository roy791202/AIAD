from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8'))
assert set(s['files'])=={p.name for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
for n,h in s['files'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
r=json.loads((P/'review.json').read_text(encoding='utf-8'))
e=re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',(P/'index.html').read_text(encoding='utf-8'),re.S)
assert json.loads(e[1])==r
assert r['passed']==len(json.loads((P/'trace.json').read_text(encoding='utf-8')))==171
print('PASS bounded one-transition seal:',len(s['files']),'files; 171 probes; HTML matches review')
