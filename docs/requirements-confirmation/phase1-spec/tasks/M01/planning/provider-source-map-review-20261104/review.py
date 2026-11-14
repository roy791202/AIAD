import json,hashlib,subprocess,copy,re,html
from pathlib import Path
ROOT=Path.cwd(); P=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/provider-source-map-20261104'; OUT=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding="utf-8"))
d=load(P/'module-spec.json'); spans=load(P/'source-spans.json'); seal=load(P/'seal.json'); before={k:sha(P/k) for k in seal['files']}; checks=[]
def check(n,b):checks.append({'name':n,'pass':bool(b)})
check('author seal hashes',before==seal['files'])
for s in spans:
 p=ROOT/s['path']; check('source '+s['id'],sha(p)==s['sha256'] and '\n'.join(p.read_text(encoding='utf-8').splitlines()[s['start']-1:s['end']])==s['text'])
for k,v in load(P/'source-hashes.json').items():check('binding '+k,sha(ROOT/k)==v)
a=load(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];check('authority796',len(a)==796 and all(sha(ROOT/k)==v for k,v in a.items()))
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(); check('distinct HEAD',head==d['live_head'] and head!=d['historical_product_head'])
port=(ROOT/spans[0]['path']).read_text(encoding='utf-8');adapter=(ROOT/spans[2]['path']).read_text(encoding='utf-8');host=(ROOT/spans[7]['path']).read_text(encoding='utf-8')
fields=re.findall(r'pub (\w+):',re.search(r'pub struct CommitReceipt \{(.*?)\n\}',port,re.S).group(1));check('receipt exactly four fields',fields==['target_path','previous_digest','committed_digest','transaction_id'])
check('native identity returns unit', 'fn regular_identity(file: &File) -> std::io::Result<()>' in adapter and 'GetFileInformationByHandle(file.as_raw_handle(), &mut info)' in adapter)
check('private lease owns handle','pub(crate) struct StdFileWriteLease' in adapter and '_lock_handle: std::fs::File' in adapter and '.share_mode(0)' in adapter)
check('lexical lease ends before returned proof','checked_receipt(r, &path, baseline_digest, &bytes, &p)?\n    };\n    let proof = DefinitionCommitProof' in host)
fb=load(ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/copy-ready-correction/field-binding.json');check('21 fields exact bindings',len(d['field_coverage'])==21 and all(x['proposed_copy_ready_field'] in fb and x['proposed_fixture_bindings']==fb[x['proposed_copy_ready_field']] and x['adoption'] is None for x in d['field_coverage']))
check('3 seams pending',len(d['rows'])==3 and all(x['selected'] is None for x in d['rows']))
check('no adoption native or rerun',d['selected'] is None and d['product_native_runtime']=='NOT RUN' and d['historical_pass_rerun'] is False and all(x['status']=='PROPOSED_PENDING_OWNER' for x in d['owner_decisions']))
check('7 actions provider condition present',len(d['other_yellow_actions'])==7 and all(x['provider'] and x['missing_conditions'] and 'Historical blocker register projection' in x['scope_note'] for x in d['other_yellow_actions']))
rs=[(ROOT/k, (ROOT/k).read_text(encoding='utf-8')) for k in a if k.startswith('apps/sgenaxis-desktop/') and k.endswith('.rs')]
for x in load(P/'token-inventory.json'):
 hits=[str(p.relative_to(ROOT)).replace('\\','/') for p,t in rs if x['token'] in t];check('limited token '+x['token'],len(rs)==x['files_scanned'] and hits==x['hits'] and 'not semantic proof' in x['limit'])
# Fresh negative probes; each tests review admission rules, without mutating sources/candidate.
probes=[]
def probe(n,b):probes.append({'name':n,'rejected':bool(b)})
s=copy.deepcopy(spans[0]);s['text']+=' forged';probe('forged source text',s['text']!='\n'.join((ROOT/s['path']).read_text(encoding='utf-8').splitlines()[s['start']-1:s['end']]))
probe('forged source digest','0'*64!=sha(ROOT/spans[0]['path']))
probe('receipt claims native_lease_id','native_lease_id' not in fields)
probe('receipt claims durable Ready','ready_proof_id' not in fields)
probe('identity claims volume tuple','Result<()>' in spans[3]['text'] and 'Ok(())' in spans[3]['text'])
probe('lease claims continuing proof',host.index('    let proof = DefinitionCommitProof',host.index('let receipt = {'))>host.index('checked_receipt(r, &path, baseline_digest, &bytes, &p)?',host.index('let receipt = {')))
x=copy.deepcopy(d);x['selected']='accepted';probe('fabricated adoption',x['selected'] is not None)
x=copy.deepcopy(d);x['product_native_runtime']='PASS';probe('fabricated native PASS',x['product_native_runtime']!='NOT RUN')
check('fresh negatives reject all',all(x['rejected'] for x in probes));check('candidate unchanged',before=={k:sha(P/k) for k in before})
result={'reviewer':'/root/provider_map_independent_review','author':d['author'],'status':'BOUNDED_DOCUMENT_REVIEW_PASS' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','checks':checks,'probes':probes,'findings':[],'limits':['Static source and document evidence only; no runtime race, provider authenticity, durable Ready/native capability proof.','Product/build/native/regression NOT RUN. Historical PASS not rerun.','No candidate/product/board writes.']}
(OUT/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M01 provider source map independent review</title><h1>'+result['status']+'</h1><p>Author '+d['author']+'; reviewer /root/provider_map_independent_review. Static source mapping only.</p><p>Four-field receipt has no native identity/lease issuer output. regular_identity validates attributes but returns unit; HOST lexical lease scope closes before proof construction. These source facts do not prove runtime race or native Ready behavior.</p><p>21 proposed field bindings, 3 seams, 7 historical action projections checked; adoption stays pending. No architecture change approved.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
(OUT/'seal.json').write_text(json.dumps({'reviewer':result['reviewer'],'state':'SEALED','files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='seal.json'}},indent=2),encoding='utf-8')
print(result['status'],len(checks),'checks',len(probes),'probes');print([x for x in checks if not x['pass']])
