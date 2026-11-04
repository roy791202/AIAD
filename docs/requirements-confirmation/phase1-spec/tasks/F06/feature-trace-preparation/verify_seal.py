import pathlib,json,hashlib
P=pathlib.Path(__file__).resolve().parent
s=json.loads((P/'seal.json').read_text())['files']
assert all(hashlib.sha256((P/f).read_bytes()).hexdigest()==h for f,h in s.items())
assert {p.name for p in P.iterdir() if p.is_file() and p.name!='seal.json'}==set(s)
print('PASS_SEAL',len(s),'files; document only')
