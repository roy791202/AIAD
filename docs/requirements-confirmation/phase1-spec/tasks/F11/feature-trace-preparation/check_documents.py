import json,pathlib,hashlib,re
O=pathlib.Path(__file__).resolve().parent; R=next(p for p in O.parents if (p/'AGENTS.md').exists())
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(n):return json.loads((O/n).read_text(encoding='utf-8'))
t=load('bdd-tdd-trace.json'); src=load('source-inputs.json'); checks={}
checks['nine_original_scenarios']= [r['bdd_id'] for r in t['rows']]==[f'BDD-{i}' for i in range(22,31)]
checks['no_rewritten_original_bdd']=all(r['original_verbatim'] in (R/'docs/requirements-confirmation/phase1-spec/phase1.feature').read_text(encoding='utf-8') for r in t['rows'])
checks['feature_context_split']=all(r['f11_relation']==('contextual' if r['bdd_id'] in ['BDD-28','BDD-29'] else 'direct') for r in t['rows'])
checks['source_hashes_match']=all(digest(R/s['path'])==s['sha256'] for s in src['sources'])
checks['796_product_hashes_no_drift']=src['product_inventory_count']==796 and not src['product_hash_mismatches']
checks['all_recipes_pending']=load('pending-recipes.json')['status']=='PENDING_OWNER_NOT_EXECUTABLE'
checks['local_links_exist']=all((O/l).is_file() or l=='static-verification.json' for l in re.findall('href="([^"]+)"',(O/'index.html').read_text(encoding='utf-8')))
checks['no_claim_of_acceptance']=load('module-spec.json')['independent_acceptance'].startswith('NOT PERFORMED')
result={'status':'PASS_DOCUMENT_STATIC_ONLY' if all(checks.values()) else 'FAIL','author':'/root/f11_feature_trace_packet','checks':checks,'not_run':['product tests','behavioral RED/GREEN','real timer/capture/material pin/payload/index','native ACK','native UI','independent acceptance'],'scope':'Self-check of document structure/source consistency; not acceptance or product evidence'}
(O/'static-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
seal={p.name:digest(p) for p in sorted(O.iterdir()) if p.is_file() and p.name!='seal.json'}
(O/'seal.json').write_text(json.dumps({'algorithm':'sha256','scope':'all packet files except seal itself','files':seal},indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if all(checks.values()) else 1)
