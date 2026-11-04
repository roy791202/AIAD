from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8'))
actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
assert actual==s['files']
print('PASS_STATIC_SEAL_ONLY',len(actual),'files; no Feature PASS')
