import json,pathlib,hashlib,copy,datetime,subprocess,html
ROOT=pathlib.Path.cwd(); OUT=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/decisions/G03-review'; C=OUT.parent/'G03'; cache={}
def read(p):
 p=str(p).replace('\\','/')
 if p not in cache:
  raw=(ROOT/p).read_bytes();cache[p]=(hashlib.sha256(raw).hexdigest(),json.loads(raw.decode('utf-8-sig')) if p.endswith('.json') else raw.decode('utf-8-sig'))
 return cache[p]
def ptr(d,p):
 for k in p.split('/')[1:] if p else []: d=d[int(k)] if isinstance(d,list) else d[k.replace('~1','/').replace('~0','~')]
 return d
D=read(str((C/'decision-request.json').relative_to(ROOT)))[1]; E=read(str((C/'approved-envelope-proposal.json').relative_to(ROOT)))[1]; F=read(str((C/'failure-matrix.json').relative_to(ROOT)))[1]; S=read(str((C/'source-hashes.json').relative_to(ROOT)))[1]
hashes=[dict(x,actual_sha256=read(x['path'])[0],match=read(x['path'])[0]==x['sha256']) for x in S['sources']]
bindings=[]
for kind,rows in [('candidate',D['candidate_projections']),('envelope',E['source_projections']),('matrix',F['source_witness_matrices'])]:
 for i,row in enumerate(rows):
  s=row['source'];h,v=read(s['path']);bindings.append({'kind':kind,'index':i,'source':s,'hash_matches':h==s['sha256'],'projection_matches':ptr(v,s['pointer'])==row['verbatim']})
seal=json.loads((C/'seal.json').read_text(encoding='utf-8')); seal_checks={n:hashlib.sha256((C/n).read_bytes()).hexdigest()==h for n,h in seal['hashes'].items()}
# New semantic mutation probes, distinct from author checkers and historical suites.
def bounded(x):
 return x.get('approval') is None and x.get('exact_owner_selection') is None and all(t['selected_option'] is None and t['status']=='OPEN_PENDING_EXACT_OWNER' for t in x['decisions']) and x['direction_adoption']['verbatim']['exact_schema_api_envelope']=='PROPOSED_REVIEW_REQUIRED' and x['verification']['native']=='NOT PROVEN' and x['verification']['product_RED']=='NOT RUN'
probes=[]
for name,mutation in [('unauthorized-owner-selection',lambda x:x['decisions'][0].update(selected_option='A')),('direction-promoted-to-exact',lambda x:x['direction_adoption']['verbatim'].update(exact_schema_api_envelope='APPROVED')),('native-promoted-from-documents',lambda x:x['verification'].update(native='PASS')),('document-red-promoted',lambda x:x['verification'].update(product_RED='GREEN')),('approval-forged',lambda x:x.update(approval='APPROVED'))]:
 x=copy.deepcopy(D);mutation(x);probes.append({'id':name,'baseline_accepted':bounded(D),'mutant_rejected':not bounded(x),'level':'independent document semantic negative probe; no product execution'})
for name,kind in [('tampered-pointer','pointer'),('tampered-value','value'),('tampered-source-hash','hash')]:
 r=copy.deepcopy(E['source_projections'][0]);s=r['source'];h,v=read(s['path'])
 if kind=='pointer':s['pointer']='/nonexistent-review-negative-path'
 elif kind=='value':r['verbatim']={'unapproved':'replacement'}
 else:s['sha256']='0'*64
 try: accepted=h==s['sha256'] and ptr(v,s['pointer'])==r['verbatim']
 except (KeyError,IndexError,ValueError):accepted=False
 probes.append({'id':name,'mutant_rejected':not accepted,'level':'independent source binding negative probe'})
board=read('docs/board.json')[1];before=D['board_cards'][0]['verbatim'];after=next(x for x in board['items'] if x['id']==before['id']);fields=sorted(k for k in set(before)|set(after) if before.get(k)!=after.get(k));append=after['notes'][:len(before['notes'])]==before['notes']
inv=read(D['authority']['inventory_source']['path'])[1];head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
authority={'live_HEAD':head,'candidate_observed_HEAD':D['authority']['observed_HEAD'],'inventory_HEAD':inv['head'],'inventory_count':len(inv['source_hashes']),'candidate_count':D['authority']['inventory_count'],'note':'796 source inventory is referenced authority, not a fresh product-source verification. 31babe87 baseline differs from live 5b709343; board-only commit classification is separately checked with git.'}
changes=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r',head],text=True).splitlines();authority['live_commit_changed_paths']=changes
findings=[{'id':'G03-OBS-01','severity':'INFO','status':'CLASSIFIED','text':'Board hash differs after candidate seal. Embedded G03 card comparison changes only '+', '.join(fields)+'. Notes prefix preserved='+str(append)+'. Full prior board bytes unavailable: no claim of reconstructing or proving all-board historical delta.'},{'id':'G03-OPEN-01','severity':'INFO','status':'OPEN','text':'Exact Owner choices, ports, Skeleton, implementation RED remain unapproved. M07 RA-L1 ordinal / RA-L2 replay-baseline / RA-L3 authentic provider premise and PH-G2/G3/G4 remain OPEN; native authentication, replay and restart NOT PROVEN.'},{'id':'G03-TIME-01','severity':'INFO','status':'CLASSIFIED','text':'Candidate owner_heartbeat '+D['owner_heartbeat']+' is author-time context; does not stand in for this round Owner message at 2026-11-03T13:07:06.275Z. Neither timestamp grants exact adoption.'}]
checks={'source_count_67':len(hashes)==67,'source_nonboard_hashes_match':all(x['match'] for x in hashes if x['path']!='docs/board.json'),'candidate_54':len(D['candidate_projections'])==54,'envelope_58':len(E['source_projections'])==58,'matrices_8':len(F['source_witness_matrices'])==8,'all_120_bindings_match':all(x['hash_matches'] and x['projection_matches'] for x in bindings),'candidate_seal':all(seal_checks.values()),'null_exact_approval':bounded(D) and E['approval'] is None and E['approved_skeleton'] is None and E['approved_ports'] is None,'negative_probes':all(x['mutant_rejected'] for x in probes),'G03_board_metadata_only':fields==['notes','updatedAt'] and append,'authority_count_796':len(inv['source_hashes'])==796,'live_HEAD_matches_candidate':head==D['authority']['observed_HEAD']}
result={'task':'PD-P1-G03-DEC-01','reviewer':'/root/g03_decision_submission_review','author':D['author'],'verdict':'PASS' if all(checks.values()) else 'FAIL','acceptance_scope':'Independent static decision-consolidation document review only; no native/product/Owner exact adoption, Skeleton approval, valid RED, release or board completion','checks':checks,'authority':authority,'board_drift':{'fields':fields,'notes_append_only':append,'full_prior_board_available':False},'hashes':hashes,'bindings':bindings,'candidate_seal_checks':seal_checks,'product_tests':'NOT RUN','historical_suites':'NOT RUN'}
def write(n,d):(OUT/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
write('findings.json',findings);write('probes.json',probes);write('results.json',result)
(OUT/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>G03 independent document review</title><h1>G03 — '+result['verdict']+'</h1><p>'+html.escape(result['acceptance_scope'])+'</p><h2>Independent checks</h2><pre>'+html.escape(json.dumps(checks,ensure_ascii=False,indent=2))+'</pre><h2>Findings and retained gates</h2><pre>'+html.escape(json.dumps(findings,ensure_ascii=False,indent=2))+'</pre><p>54 candidate + 58 envelope source-pointer projections and 8 original witness matrices verified by cached source reads. Bounded review preserves editable SSOT revision, architecture/UI/material consistency, activeDoc/Undo/snapshot roots and conservative unknown-reference cleanup as existing proposals or OPEN choices. No new contract inferred.</p><p><a href="results.json">Results and source bindings</a> · <a href="probes.json">New negative probes</a> · <a href="findings.json">Findings</a></p>',encoding='utf-8')
print(json.dumps({'verdict':result['verdict'],'checks':checks,'authority':authority,'source_drift':[x for x in hashes if not x['match']]},ensure_ascii=False,indent=2))
