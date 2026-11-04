"""Author DOCUMENT checks only. No product/native acceptance and no valid RED."""
import pathlib,json,copy,hashlib,importlib.util
P=pathlib.Path(__file__).resolve().parent;ROOT=P.parents[6]
def read(name):return json.loads((P/name).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('oracle',P/'oracle.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
for group,name in [('original-eight','fixtures.json'),('exact-18-closure','closure-fixtures.json'),('targeted','targeted-fixtures.json')]:
 for case in read(name):
  before=copy.deepcopy(case['fixture']);observed=m.observe(case['fixture'])
  assert observed['result']==case['expected'],(group,case['id'],case['name'],case['expected'],observed)
  assert before==case['fixture'],case['id']
  assert all(observed['state_calls'][k]==0 for k in ['CAS','native_IO','model_mutation','retry','cleanup'])
  results.append({'group':group,'id':case['id'],'name':case['name'],'expected':case['expected'],'before':case.get('before'),'after':observed,'input_unchanged':True})
source=read('source-bindings.json');inventory=json.loads((ROOT/source['authority_inventory']).read_text(encoding='utf8'));bad=[name for name,h in inventory['source_hashes'].items() if sha(ROOT/name)!=h];assert len(inventory['source_hashes'])==796 and not bad,bad
bad=[name for name,h in source['source_hashes'].items() if sha(ROOT/name)!=h];assert not bad,bad
module=read('module-spec.json');embedded=(P/'index.html').read_text(encoding='utf8').split('id="module-spec">')[1].split('</script>')[0];assert json.loads(embedded)==module
report={'status':'PASS_DOCUMENT_CHECK_ONLY','author':'/root/m01_copy_ready_correction','counts':{g:sum(x['group']==g for x in results) for g in ['original-eight','exact-18-closure','targeted']},'cases':results,'authority_product_hashes':796,'source_bindings':len(source['source_hashes']),'schema':'candidate.schema.json; all objects recursively closed; no access before validation','no_input_mutation':True,'verification':dict.fromkeys(['independent','native','build','product','valid_RED','full_Draft'],'NOT RUN'),'module_pass':False,'skeleton':'NOT AUTHORIZED'}
(P/'document-check.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='cases'},indent=2))
