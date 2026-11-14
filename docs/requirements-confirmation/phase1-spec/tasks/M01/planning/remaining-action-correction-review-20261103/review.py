import pathlib,json,hashlib,importlib.util,sys,copy,subprocess,datetime
sys.dont_write_bytecode=True
R=pathlib.Path.cwd(); H=R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning'; O=H/'remaining-action-correction-review-20261103'; C=H/'remaining-action-correction-20261103'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,x): (O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
spec=importlib.util.spec_from_file_location('candidate_check',C/'check.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
ps=read(C/'task-packets.json'); cards=read(C/'31-card-actions.json'); probes=[]
def probe(name,obj,fn,expected):
 try: fn(obj); observed='ACCEPT'
 except (AssertionError,KeyError,TypeError) as e: observed='REJECT'
 probes.append(dict(id=name,expected=expected,observed=observed,pass_=observed==expected))
p=copy.deepcopy(ps[0]);p['review_annotation']='legal extra metadata';probe('legal_extra_metadata',p,mod.validate,'ACCEPT')
for name,mutation in [('mixed_modules',lambda p:p.update(allowed_modules=['M02','M03'])),('empty_exactfiles',lambda p:p.update(allowed_files=[])),('missing_command',lambda p:p.update(commands=[])),('outside_scope',lambda p:p['allowed_files'].__setitem__(0,'apps/sgenaxis-desktop/candidate.json')),('missing_source',lambda p:p['source_refs'].append('missing-not-present.json')),('wrong_authorization',lambda p:p.update(authority='Approved production implementation and release authorized')),('non_executable_command',lambda p:p.update(commands=['echo check.py --packet M03']))]:
 p=copy.deepcopy(ps[0]);mutation(p);probe(name,p,mod.validate,'REJECT')
r=copy.deepcopy(cards['cards'][0]);r.pop('provider');probe('delete_provider',r,mod.io_validate,'REJECT')
r=copy.deepcopy(cards['cards'][0]);r['provider']='Windows11 fixture provider; No new Owner adoption required; native reparse and 8.3 fixture';probe('provider_wording_variant',r,mod.io_validate,'ACCEPT')
seal=read(C/'seal.json');sealcheck={n:sha(C/n)==v for n,v in seal['payload'].items()}
sources=read(C/'source-hashes.json');drift={n:{'expected':v,'actual':sha(R/n)} for n,v in sources['sources'].items() if sha(R/n)!=v}
authority=read(H/'s2-green/source-current.json');product=[n for n,v in authority['source_hashes'].items() if not (R/n).is_file() or sha(R/n)!=v]
original=read(H/'remaining-action-dispatch-20261103/31-card-actions.json');diff=[]
for a,b in zip(original['cards'],cards['cards']):
 for key in set(a)|set(b):
  if a.get(key)!=b.get(key):diff.append({'id':a.get('id'),'field':key,'before':a.get(key),'after':b.get(key)})
commands=[]
for p in ps:
 cmd=p['commands'][0];r=subprocess.run(cmd.split(),cwd=R,capture_output=True,text=True);commands.append({'command':cmd,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
# Current document checks only. Deliverable commands deliberately not run: outputs not authored in this review.
results={'reviewer':'/root/remaining_action_correction_review','author':'/root/remaining_action_correction_packet','layer':'INDEPENDENT_BOUNDED_DOCUMENT_REVIEW','head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'candidate_seal':sealcheck,'source_drift':drift,'product_authority_count':len(authority['source_hashes']),'product_hash_mismatches':product,'card_differences':diff,'commands':commands,'product_native_build_valid_red':'NOT RUN; valid RED N/A','owner_adoption':'NOT GRANTED','timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat()}
write('probes.json',probes);write('results.json',results)
print(json.dumps({'failed_probes':[p for p in probes if not p['pass_']],'seal_ok':all(sealcheck.values()),'source_drift':drift,'product_count':len(authority['source_hashes']),'product_mismatches':len(product),'card_differences':diff,'commands':[(x['exit']) for x in commands]},ensure_ascii=False,indent=2))
