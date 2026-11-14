import sys,json,hashlib,copy,random,re,subprocess,importlib.util,html
from pathlib import Path
sys.dont_write_bytecode=True
D=Path(__file__).resolve().parent; W=Path.cwd(); C=D.parent/'save-proof-correction'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x): (D/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('candidate',C/'check_documents.py'); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
original={str(p.relative_to(W)):sha(p) for p in C.iterdir() if p.is_file()}
s=read(C/'module-spec.json'); frozen=[p for p,h in s['frozen_inputs'].items() if sha(W/p)!=h]
baseline=read(W/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json'); drift=[p for p,h in baseline['source_hashes'].items() if sha(W/p)!=h]
base=read(C/'lifecycle-vectors.json')[0]['input']; probes=[]
def probe(name,x,expected):
 observed=list(m.model(x)); probes.append(dict(id=name,expected=expected,observed=observed,passed=observed==expected))
for section in ['root_receipt','ack','file_receipt','current']:
 keys=list(base[section])
 for k in keys:
  x=copy.deepcopy(base);del x[section][k]
  expected=['UnverifiedOutcome',0,'CommitOutcomeUnknown'] if section=='file_receipt' else ['CommittedAckDeferred',0,'AckRejected' if section=='ack' else 'ProofMismatch' if section=='root_receipt' else 'Detached' if k=='attached' else 'OwnerChanged']
  if section=='current' and k=='live_revision': expected=['Saved',1,None]
  probe('independent-delete-'+section+'-'+k,x,expected)
for key in sorted(m.CAPTURE_KEYS):
 x=copy.deepcopy(base)
 value=[] if key=='asset_versions' else 'independent-substitution'
 for section in ['capture','file_receipt','root_receipt','ack','current']:
  if key in x[section]:x[section][key]=value
 probe('all-downstream-substitution-'+key,x,['UnverifiedOutcome',0,'IssuerEvidenceMissing'])
# New distinct versions of one asset are a set of pairs, not a map keyed only by asset.
x=copy.deepcopy(base)
pairs=[{'asset_id':'same','content_digest':'1'*64},{'asset_id':'same','content_digest':'2'*64}]
for section in ['capture','root_receipt','ack']:x[section]['asset_versions']=copy.deepcopy(pairs)
x['issuer_record']['sealed_capture']['asset_versions']=copy.deepcopy(pairs)
x['ack']['asset_versions'].reverse();probe('same-asset-distinct-versions-reordered',x,['Saved',1,None])
x['root_receipt']['asset_versions'].pop();probe('same-asset-one-version-lost',x,['CommittedAckDeferred',0,'ProofMismatch'])
for section in ['root_receipt','ack']:
 x=copy.deepcopy(base);x[section]['asset_versions'][0]['extra']=True
 probe('material-extra-field-'+section,x,['CommittedAckDeferred',0,'ProofMismatch' if section=='root_receipt' else 'AckRejected'])
# Compare actual schema constraint to independent arithmetic lexical oracle.
rng=random.Random(3103);tokens=[str(n) for n in [0,1,2**64-2,2**64-1,2**64,2**64+1]]
tokens += [str(rng.randrange(0,10**21)) for _ in range(512)]
tokens += [str(10**n+d) for n in range(1,21) for d in [-1,0,1]]
tokens += ['','00','01','+1','-1',' 1','1 ','1x','1\x00','1\n','1\r','1\r\n','1\u2028','1\u2029','１','١']
regex=[]
for name in ['request','response']:
 root=read(C/(name+'.schema.json'));u=root['$defs']['U64Decimal'];bad=[]
 for token in tokens:
  expected=bool(re.fullmatch('0|[1-9][0-9]*',token)) and int(token)<=2**64-1
  observed=bool(re.search(u['pattern'],token)) and u['minLength']<=len(token)<=u['maxLength']
  if observed!=expected:bad.append(token)
 regex.append(dict(schema=name,cases=len(tokens),mismatches=bad,pattern_tail_codepoints=list(map(ord,u['pattern'][-10:]))))
# ECMAScript engine consumes the same actual patterns and independent token/oracle outcomes.
js='const fs=require("fs");const x=JSON.parse(fs.readFileSync(0,"utf8"));console.log(JSON.stringify(x.patterns.map(p=>x.tokens.map(t=>new RegExp(p).test(t)))));'
jres=json.loads(subprocess.check_output(['node','-e',js],input=json.dumps({'patterns':[read(C/(n+'.schema.json'))['$defs']['U64Decimal']['pattern'] for n in ['request','response']],'tokens':tokens}),text=True))
jsbad=[]
for i,results in enumerate(jres):
 for t,got in zip(tokens,results):
  expected=bool(re.fullmatch('0|[1-9][0-9]*',t)) and int(t)<=2**64-1
  if got!=expected:jsbad.append([i,t,got,expected])
# Policy copies are byte-identical; no accidental change to defensive error mapping.
policy={n:sha(C/n)==sha(D.parent/'save-response-correction'/n) for n in ['material-outcome-matrix.json','io-outcome-map.json','response.schema.json']}
policy['response.schema.json']='U64-only schema change reviewed separately; not expected byte-identical'
changed=[p for p,h in original.items() if sha(W/p)!=h]
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip()
result=dict(new_model_probes=probes,python_regex_property=regex,ecmascript_mismatches=jsbad,policy_comparison=policy,frozen_drift=frozen,product_files=len(baseline['source_hashes']),product_drift=drift,reviewed_input_hashes=original,reviewed_input_changes=changed,current_head=head,historical_candidate_head=s['head'],branch=branch,full_draft_validator='NOT RUN',product_tests_build_RED_GREEN_native='NOT RUN')
write('verification.json',result)
assert not frozen and not drift and not changed and not jsbad and all(not r['mismatches'] for r in regex)
assert all(p['passed'] for p in probes),[p for p in probes if not p['passed']]
print(json.dumps(dict(model_probes=len(probes),regex_cases_per_engine=sum(r['cases'] for r in regex),product_files=len(baseline['source_hashes']),drift=len(drift),head=head)))
