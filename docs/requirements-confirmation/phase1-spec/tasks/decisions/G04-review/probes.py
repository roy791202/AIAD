import pathlib,json,hashlib,re,html,copy,datetime,subprocess
R=pathlib.Path(__file__).resolve().parents[6]
D=R/'docs/requirements-confirmation/phase1-spec/tasks/decisions/G04'; O=D.parent/'G04-review'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=load(D/'decision-request.json');f=load(D/'failure-matrix.json');e=load(D/'approved-envelope-proposal.json');s=load(D/'seal.json');obs=load(O/'observations.json')
source=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M02/planning/exact-design/module-spec.json')
a=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M02/s1/adoption.json')
def valid(r,f,e):
 return (r['approval'] is None and r['owner_exact_selection'] is None and r['intent_items'][1]['status']=='ADOPTED_M02_TARGET_BASELINE' and r['intent_items'][3]['candidate']['status']=='OPEN' and all(r['intent_items'][3][k] is None for k in ['approved_media_formats','decoder_sdk','thresholds']) and all(e[k] is False for k in ['implementation_authority','skeleton_authority','RED_authority']) and e['adopted_pure_S1_file_scope']['files']==a['scope'] and len(f['rows'])==len(source['failure_matrix']) and all(x['at']==y['at'] and x['outcome_and_preservation']==y['result'] for x,y in zip(f['rows'],source['failure_matrix'])) and e['pending_gates']['golden14']=='MISSING' and e['pending_gates']['transitive_lock']=='MISSING' and 'no delegated independent reviewer' in r['pure_S1_current_acceptance']['reviewer_limitation'])
checks=[]
def check(n,b):checks.append({'name':n,'pass':bool(b)})
check('bounded semantic baseline',valid(r,f,e))
check('seal payload bytes',all(sha(D/n)==v for n,v in s['payload_sha256'].items()))
check('90 source hashes only board drift',len(obs)==90 and [x['path'] for x in obs if not x['match']]==['docs/board.json'])
projections=load(O/'pointer-projections.json');check('57 pointers resolve and source hashes match',len(projections)==57 and all(x.get('hash_match') and 'error' not in x for x in projections))
t=(D/'index.html').read_text(encoding='utf-8');blocks=[json.loads(html.unescape(x)) for x in re.findall(r'<pre>(.*?)</pre>',t,re.S)];check('HTML five intent projections exact',blocks==r['intent_items'])
inventory=load(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'); drift=[n for n,v in inventory['source_hashes'].items() if sha(R/n)!=v];check('796 authority product sources unchanged',len(inventory['source_hashes'])==796 and not drift)
check('current HEAD distinct from historical inventory',subprocess.check_output(['git','rev-parse','HEAD'],cwd=R).decode().strip()=='5b709343a890503ebbe24a802e43cda5647df124' and inventory['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
mutations=[]
for label,target,path,value in [('invent approval','r',['approval'],'APPROVED'),('reopen adopted baseline','r',['intent_items',1,'status'],'PENDING'),('invent media approval','r',['intent_items',3,'candidate','status'],'APPROVED'),('invent SDK','r',['intent_items',3,'decoder_sdk'],'imaginary'),('authorize product','e',['implementation_authority'],True),('authorize skeleton','e',['skeleton_authority'],True),('authorize RED','e',['RED_authority'],True),('hide golden gate','e',['pending_gates','golden14'],'PASS'),('hide lock gate','e',['pending_gates','transitive_lock'],'PASS'),('expand accepted scope','e',['adopted_pure_S1_file_scope','files'],['apps/other.rs']),('success recast as error','f',['rows',8,'outcome_and_preservation'],'Cancelled'),('invent rollback','f',['rows',5,'outcome_and_preservation'],'delete sealed version'),('remove failure row','f',['rows'],f['rows'][:-1]),('independent acceptance inflation','r',['pure_S1_current_acceptance','reviewer_limitation'],'Independent native acceptance')]:
 q={'r':copy.deepcopy(r),'f':copy.deepcopy(f),'e':copy.deepcopy(e)};v=q[target]
 for key in path[:-1]:v=v[key]
 v[path[-1]]=value;mutations.append({'mutation':label,'rejected':not valid(q['r'],q['f'],q['e'])})
check('14 fresh semantic negative probes rejected',all(x['rejected'] for x in mutations))
result={'reviewer':'/root/g04_decision_submission_review','author':r['author'],'verdict':'PASS_BOUNDED_DOCUMENT_REVIEW_PENDING_OWNER' if all(x['pass'] for x in checks) else 'CHANGES_REQUIRED','checks':checks,'mutations':mutations,'product_drift':drift,'not_run':['product tests','build','package','native publication/provider/consumer','valid RED','full Draft2020-12','Owner adoption','feature/module acceptance'],'limit':'Fixed bounded semantic oracles; not a generic natural-language proof and not author checker rerun.'}
(O/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result,ensure_ascii=False))

