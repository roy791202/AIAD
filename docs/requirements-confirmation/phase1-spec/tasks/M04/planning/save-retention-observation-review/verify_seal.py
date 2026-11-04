"""Read-only verification of review envelope, embedded review and frozen inputs."""
import hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
W=next(p for p in D.parents if (p/'apps/sgenaxis-desktop').exists())
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
s=read(D/'seal.json');i=read(D/'inputs.json')
assert all(sha(D/p)==h for p,h in s['artifacts'].items())
assert all(sha(W/p)==h for p,h in i['readonly_inputs'].items())
embedded=re.search(r'<script type="application/json" id="review">(.*?)</script>',(D/'index.html').read_text(encoding='utf-8'),re.S).group(1)
assert json.loads(embedded)==read(D/'review.json')
authority=read(W/i['source_authority'])
assert len(authority['source_hashes'])==796
assert all(sha(W/p)==h for p,h in authority['source_hashes'].items())
print(json.dumps({'seal':'PASS','sealed_files':len(s['artifacts']),'frozen_readonly_inputs':len(i['readonly_inputs']),'authority_files':796,'embedded_review':'PASS','management':'board hash separate; no assertion that management bytes equal historical proposal'}))
