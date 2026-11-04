import pathlib,hashlib,json
P=pathlib.Path(__file__).resolve().parent
for name in ['source-hashes.json','artifact-hashes.json']:
 for path,h in json.loads((P/name).read_text(encoding='utf8')).items():
  assert hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==h,path
v=json.loads((P/'verification.json').read_text(encoding='utf8'))
assert v['new_probes']==88 and len(v['mismatches'])==2
assert all(x['id'] in ['binding_ref:trailing-newline','request_id:trailing-newline'] for x in v['mismatches'])
print('PASS review consistency and frozen hashes; document CHANGES_REQUIRED remains')
