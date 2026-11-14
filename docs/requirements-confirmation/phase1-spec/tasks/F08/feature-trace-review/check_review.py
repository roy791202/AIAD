"""Independent F08 document semantic probes. No product execution or source writes."""
import copy,hashlib,html,json,pathlib,re,subprocess
O=pathlib.Path(__file__).resolve().parent; R=O.parents[5]; B=R/'docs/requirements-confirmation/phase1-spec'; P=O.parent/'feature-trace-preparation'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=read(P/'feature-trace.json'); bindings=read(P/'source-bindings.json'); seal=read(P/'seal.json'); inv=read(B/'tasks/M01/planning/s2-green/source-current.json')
expected=[('REQ-06','BDD-09','EXACT_ORIGINAL_SCENARIO'),('REQ-06','BDD-10','EXACT_ORIGINAL_SCENARIO'),('REQ-13','BDD-13','EXACT_ORIGINAL_SCENARIO'),('REQ-13','BDD-14','EXACT_ORIGINAL_SCENARIO'),('REQ-10','BDD-09/BDD-13','CONTEXTUAL_NOT_EQUIVALENT'),('REQ-10','NONE','PROSPECTIVE_AC_RECIPE_NOT_ORIGINAL_BDD'),('REQ-10 / REQ-08 contextual','BDD-02','CONTEXTUAL_NOT_EQUIVALENT'),('REQ-10 / AC08','NONE','PROSPECTIVE_AC_RECIPE_NOT_ORIGINAL_BDD'),('REQ-13 / AC08','NONE','PROSPECTIVE_AC_RECIPE_NOT_ORIGINAL_BDD'),('REQ-10 / AC08','NONE','PROSPECTIVE_AC_RECIPE_NOT_ORIGINAL_BDD')]
def evaluate(s,bs):
 errors=[]
 if len(s['trace'])!=10:errors.append('row count')
 for i,(row,want) in enumerate(zip(s['trace'],expected)):
  if (row['requirement'],row['bdd'],row['equivalence'])!=want:errors.append('semantic relation '+str(i+1))
  if row['acceptance']!='AC08':errors.append('wrong acceptance')
  if row['status']!='PLANNED_NOT_RUN':errors.append('unearned execution')
 if any(s[k] for k in ['feature_pass','module_pass','done']) or set(s['verification'].values())!={'NOT RUN'}:errors.append('product claim')
 if s['zone']!='gray' or s['dependencies_unchanged']!=['PD-P1-M06-PREP-01','PD-P1-G01-DEC-01','PD-P1-G02-DEC-01']:errors.append('management authority')
 if 'pending' not in s['evidence']['source_context'] or 'not retroactively alter accepted S2' not in s['evidence']['source_context']:errors.append('historical staged rename authority')
 if 'zero CAS/native IO' not in s['evidence']['copy_correction'] or 'pending' not in s['evidence']['copy_correction']:errors.append('oracle native conflation')
 for p,h in bs.items():
  if p=='docs/board.json':continue # management snapshot drift reported separately
  if not (R/p).is_file() or sha(R/p)!=h:errors.append('source binding '+p)
 return errors
baseline=evaluate(spec,bindings); fixtures=[]
def probe(name,mutate):
 s=copy.deepcopy(spec); bs=copy.deepcopy(bindings); mutate(s,bs); errors=evaluate(s,bs); fixtures.append({'id':name,'expected':'REJECT','detected':bool(errors),'errors':errors})
probe('wrong-AC',lambda s,b:s['trace'][0].update(acceptance='AC09'))
probe('wrong-BDD',lambda s,b:s['trace'][0].update(bdd='BDD-18'))
probe('wrong-source',lambda s,b:b.update({'not-an-authority.json':'0'*64}))
probe('wrong-hash',lambda s,b:b.update({next(iter(b)):'0'*64}))
probe('context-as-exact',lambda s,b:s['trace'][4].update(equivalence='EXACT_ORIGINAL_SCENARIO'))
probe('prospective-as-exact',lambda s,b:s['trace'][8].update(equivalence='EXACT_ORIGINAL_SCENARIO'))
probe('old-staged-rename-approved',lambda s,b:s['evidence'].update(source_context='Approved staged rename is current Ready implementation authority'))
probe('noIO-model-as-native-PASS',lambda s,b:(s['verification'].update(native='PASS'),s['evidence'].update(copy_correction='Document oracle proves native copy')))
probe('recipe-as-executed',lambda s,b:s['trace'][9].update(status='GREEN'))
recipes=read(P/'fixture-recipes.json')['recipes']
recipe_match=all(r['id']==t['tdd'] and r['input']==t['fixture_recipe'] and r['oracle']==t['oracle'] and r['command']==t['command'] and r['valid_RED']==t['valid_RED'] for r,t in zip(recipes,spec['trace']))
author_page=(P/'index.html').read_text(encoding='utf-8')
embedded=json.loads(re.search(r'<script type="application/json" id="module-spec">(.*?)</script>',author_page,re.S)[1].replace('<\\/','</'))
original=(B/'phase1.feature').read_text(encoding='utf-8'); extracts={k:re.search(r'  @'+k+r'\b.*?(?=\n  @|\Z)',original,re.S)[0] for k in ['BDD-09','BDD-10','BDD-13','BDD-14']}
checks={'baseline_semantics':not baseline,'source_bindings_21_current_board_separate':len(bindings)==22 and not [p for p,h in bindings.items() if p!='docs/board.json' and sha(R/p)!=h], 'author_seal_9':seal['count']==9 and all(sha(P/p)==h for p,h in seal['files'].items()),'author_reviewer_distinct':spec['author']!='/root/f08_feature_trace_review','inventory_796':len(inv['source_hashes'])==796 and all(sha(R/p)==h for p,h in inv['source_hashes'].items()),'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()=='5b709343a890503ebbe24a802e43cda5647df124','mutations_detected':all(f['detected'] for f in fixtures)}
checks['fixture_recipes_10_match']=len(recipes)==10 and recipe_match
checks['author_html_embedded_matches']=embedded==spec
checks['author_html_links_resolve']=all((P/x).is_file() for x in re.findall(r'href="([^"]+)"',author_page))
report={'reviewer':'/root/f08_feature_trace_review','author':spec['author'],'verdict':'PASS_PREPARATION_DOCUMENT_TRACE_ONLY' if all(checks.values()) else 'FAIL','checks':checks,'baseline_errors':baseline,'counts':{'rows':10,'exact':4,'contextual':2,'prospective':4,'new_mutations':len(fixtures),'source_bindings':22,'author_seal':9,'product_inventory':796},'findings':[],'scope':'One F08 feature preparation only. No feature/module PASS, Skeleton authority or approved architecture. Gray retained; dependencies unchanged.','interpretation':['BDD09/10/13/14 faithfully map original observable outcomes; exact means scenario identity, never proof of complete native implementation.','New identity/provenance is proposed pending Owner identity policy; source unchanged/no content execution are confirmed constraints. ESS explicit replace is not project-directory overwrite authority.','Preview/cancel is planned read-only; source and target bytes/identity and portable references need real native fixtures.','Accepted S2 is definition create/open/save/codec evidence, not imported ESS/BIN/native copy/full Draft. S3 source inventory remains historical source context.','Pending CX/copy correction supersedes old staged-rename proposal only in that proposal context: final-path quarantine then sole M01 Ready CAS; accepted S2 not rewritten.','CR-D1..3, CX Owner adoption, immutable source/target held leases, native authenticity, M05 catalog/root/pin, M01 Ready providers remain unapproved. Document oracle zero CAS/native IO cannot prove copy.','X06 duplicate paths, case collision, traversal, links, bombs, unknown version, cancellation, space and unreadable source remain unmaterialized recipes. D10 2 GiB/10000 limits remain suggestions, no threshold approved.'],'verification':{k:'NOT RUN' for k in ['product_tests','build','native','valid_RED','full_Draft','feature_acceptance']},'inventory_authority':str((B/'tasks/M01/planning/s2-green/source-current.json').relative_to(R)).replace('\\','/'),'historical_inventory_head':inv['head'],'current_head':'5b709343a890503ebbe24a802e43cda5647df124'}
write('new-fixtures-and-results.json',fixtures);write('review.json',report);write('original-scenario-text.json',extracts);write('input-hashes.json',{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in [*(P/n for n in seal['files']),P/'seal.json',*(R/p for p in bindings)]})
write('management-diff.json',{'board_current_sha256':sha(R/'docs/board.json'),'author_bound_sha256':bindings['docs/board.json'],'separate_from_product_inventory':True,'changed':sha(R/'docs/board.json')!=bindings['docs/board.json'],'board_written':False})
page='<!doctype html><meta charset="utf-8"><title>F08 independent trace review</title><style>body{font:16px system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap}</style><h1>F08 independent trace review</h1><h2>'+report['verdict']+'</h2><p>Preparation document only. Gray retained. Product/native/build/valid RED/full Draft NOT RUN.</p><pre>'+html.escape(json.dumps(report,ensure_ascii=False,indent=2))+'</pre><h2>New semantic counterexamples</h2><pre>'+html.escape(json.dumps(fixtures,ensure_ascii=False,indent=2))+'</pre><script type="application/json" id="review-spec">'+json.dumps(report,ensure_ascii=False).replace('</','<\/')+'</script>'
(O/'index.html').write_text(page,encoding='utf-8');write('seal.json',{'algorithm':'SHA256','excludes':'seal.json only','files':{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='seal.json'},'count':len([p for p in O.iterdir() if p.is_file() and p.name!='seal.json'])});print(json.dumps({'verdict':report['verdict'],'checks':checks,'mutations':len(fixtures)}));raise SystemExit(0 if all(checks.values()) else 1)
