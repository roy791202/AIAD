import pathlib,json,hashlib,re,subprocess
R=pathlib.Path.cwd(); O=pathlib.Path(__file__).resolve().parent
p=json.loads((O/'audit.json').read_text(encoding='utf-8')); failures=[]
def digest(q): return hashlib.sha256(q.read_bytes()).hexdigest()
for s,h in p['sources'].items():
 if not (R/s).exists() or digest(R/s)!=h: failures.append(s)
inv=json.loads((R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json').read_text(encoding='utf-8'))
for s,h in inv['source_hashes'].items():
 if not (R/s).exists() or digest(R/s)!=h: failures.append(s)
page=(O/'index.html').read_text(encoding='utf-8'); embedded=json.loads(re.search(r'id="module-spec">(.*?)</script>',page,re.S).group(1)); assert embedded==p
links=re.findall(r'href="([^"]+)"',page)
for link in links:
 if not (O/link).resolve().exists(): failures.append(link)
assert len(p['actions'])==8
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==p['required_head']
result={'status':'PASS_AUTHOR_LINK_HASH_CHECK' if not failures else 'FAIL','yellow_rows':8,'essential_source_hashes':len(p['sources']),'product_inventory_hashes':len(inv['source_hashes']),'html_links':len(links),'failures':failures,'independent_acceptance':'NOT RUN','product_native_build_RED':'NOT RUN'}
(O/'check-result.json').write_text(json.dumps(result,indent=2),encoding='utf-8'); print(json.dumps(result)); assert not failures
