import pathlib,json,hashlib,re,subprocess
R=pathlib.Path.cwd();O=pathlib.Path(__file__).resolve().parent
d=json.loads((O/'audit.json').read_text(encoding='utf8')); failures=[]
for s,h in d['sources'].items():
 q=R/s
 if not q.exists() or hashlib.sha256(q.read_bytes()).hexdigest()!=h:failures.append(s)
page=(O/'index.html').read_text(encoding='utf8')
assert json.loads(re.search(r'id="module-spec">(.*?)</script>',page,re.S).group(1))==d
for s in re.findall(r'href="([^"]+)"',page):
 if not (O/s).resolve().exists():failures.append(s)
assert d['gray_count']==18 and d['red_count']==5 and len(d['rows'])==23
assert len({r['id'] for r in d['rows']})==23
assert len(d['executed_new_action'])==4
assert not d['inventory_mismatches'] and d['inventory_count']==796
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==d['required_head']
for w in d['executed_new_action']:
 for c in w['existing_module_candidates']:
  for k in ['candidate','review']:
   assert (R/c[k]).exists(),c[k]
assert not failures,failures
result={'status':'PASS_AUTHOR_DOCUMENT_HASH_LINK_CHECK','gray':18,'red':5,'witnesses':4,'source_hashes':len(d['sources']),'product_hashes':796,'independent_acceptance':'NOT RUN','native_build_product_RED':'NOT RUN'}
(O/'check-result.json').write_text(json.dumps(result,indent=2),encoding='utf8')
seal={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in O.iterdir() if p.is_file() and p.name!='seal.json'}
(O/'seal.json').write_text(json.dumps({'files':seal,'scope':'new folder only','author_check_only':True},indent=2),encoding='utf8')
print(json.dumps(result))
