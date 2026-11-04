"""Verify final packet content hashes without generating cache files."""
from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text(encoding='utf-8'))
actual={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in P.iterdir() if p.is_file() and p.name!='seal.json'}
assert actual==s['sha256']
assert len(actual)==s['file_count']
print('PASS_DOCUMENT_SEAL',len(actual))
