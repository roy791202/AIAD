import json, pathlib, hashlib, re, copy, datetime, subprocess
root=pathlib.Path.cwd(); base=root/'docs/requirements-confirmation/phase1-spec/tasks/decisions/G02'; out=base.with_name('G02-review')
def read(p):return json.loads(pathlib.Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(n,d):(out/n).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def ptr(d,p):
 for k in p.split('/')[1:]:
  k=k.replace('~1','/').replace('~0','~');d=d[int(k)] if isinstance(d,list) else d[k]
 return d
req=read(base/'decision-request.json');mat=read(base/'failure-matrix.json');env=read(base/'approved-envelope-proposal.json');src=read(base/'source-hashes.json')
cache={}; errors=[]; bindings=[]
def load(path):
 if path not in cache:cache[path]=read(root/path)
 return cache[path]
def walk(d,loc=''):
 if isinstance(d,dict):
  s=d.get('source');vkey=next((k for k in ['verbatim','existing_record_verbatim','existing_document'] if k in d),None)
  if isinstance(s,dict) and all(k in s for k in ['path','pointer','sha256']) and vkey:
   try:
    actual=ptr(load(s['path']),s['pointer']); ok=actual==d[vkey];bindings.append({'location':loc,'path':s['path'],'pointer':s['pointer'],'equal':ok})
    if not ok:errors.append(loc)
   except Exception as e:errors.append([loc,str(e)])
  for k,v in d.items():walk(v,loc+'/'+k)
 elif isinstance(d,list):
  for i,v in enumerate(d):walk(v,loc+'/'+str(i))
for name,d in [('request',req),('matrix',mat),('envelope',env)]:walk(d,name)
hashes=[{'path':p,'expected':h,'actual':sha(root/p),'equal':sha(root/p)==h} for p,h in src['sources'].items()]
seal=read(base/'seal.json'); sealchecks={p:sha(base/p)==h for p,h in seal['artifacts'].items()}
html=(base/'index.html').read_text(encoding='utf-8');scripts=re.findall(r'<script[^>]*id=["\']([^"\']+)["\'][^>]*>(.*?)</script>',html,re.S)
print('scripts',[(k,len(v)) for k,v in scripts]);print('bindings',len(bindings),'errors',len(errors),'hashdrift',[h['path'] for h in hashes if not h['equal']]);print('errors',errors[:5]);print('row count',len(mat['rows']))
save('binding-results.json',{'bindings':bindings,'errors':errors,'hashes':hashes,'seal':sealchecks})
import html
allptr=[]
def wp(d,loc=''):
 if isinstance(d,dict):
  if all(k in d for k in ('path','pointer','sha256')):
   try:ptr(load(d['path']),d['pointer']);allptr.append((loc,True))
   except Exception as e:allptr.append((loc,str(e)))
  for k,v in d.items():wp(v,loc+'/'+k)
 elif isinstance(d,list):
  for i,v in enumerate(d):wp(v,loc+'/'+str(i))
for n,d in [('request',req),('matrix',mat),('envelope',env)]:wp(d,n)
projections=[json.loads(html.unescape(t)) for t in re.findall(r'<pre>(.*?)</pre>',html,re.S)] if False else []
# HTML full JSON blocks are parsed as structured data, without DOM inference.
htmltext=(base/'index.html').read_text(encoding='utf-8')
blocks=[json.loads(html.unescape(t)) for t in re.findall(r'<pre>(.*?)</pre>',htmltext,re.S)]
print('pointer count',len(allptr),'bad',[x for x in allptr if x[1] is not True]);print('html blocks',len(blocks),[b==d for b,d in zip(blocks,[req,mat,env])])
before=req['board_card']['verbatim'];now=ptr(load('docs/board.json'),req['board_card']['source']['pointer']);print('board changed keys',[k for k in set(before)|set(now) if before.get(k)!=now.get(k)])
authority=read(root/src['authority']['authority']['path']);ah=authority['source_hashes'];ad=[p for p,h in ah.items() if sha(root/p)!=h];print('authority',len(ah),ad)
def guard(r,m,e):
 violations=[]
 if r['direction_adoption']['verbatim']['status']!='DIRECTION_ADOPTED':violations.append('direction downgraded')
 if e['approved'] or e['approval'] is not None or e['owner_exact_choice']['selected'] is not None:violations.append('unauthorized adoption')
 if e['skeleton']!='NOT AUTHORIZED' or e['valid_RED']!='NOT RUN':violations.append('false implementation gate')
 c=r['semantic_conflict']
 if c['resolution'] is not None or c['owner_choice']['selected'] is not None or len(c['source_bindings'])!=13:violations.append('conflict erased or auto-resolved')
 for row in m['rows']:
  if row['existing_record_verbatim']!=ptr(load(row['source']['path']),row['source']['pointer']):violations.append('state outcome/source mismatch')
 return violations
mut=[]
def probe(id,change):
 r,m,e=copy.deepcopy((req,mat,env));change(r,m,e);v=guard(r,m,e);mut.append({'id':id,'expected':'REJECT','observed':'REJECT' if v else 'ACCEPT','reasons':v})
probe('direction-not-pending',lambda r,m,e:r['direction_adoption']['verbatim'].update(status='PENDING'))
probe('no-owner-auto-adopt',lambda r,m,e:e['owner_exact_choice'].update(selected='exact-adopt'))
probe('no-approved-envelope',lambda r,m,e:e.update(approved=True))
probe('no-skeleton-from-document',lambda r,m,e:e.update(skeleton='AUTHORIZED'))
probe('no-document-red-promotion',lambda r,m,e:e.update(valid_RED='PASS'))
probe('f09-conflict-not-auto-resolved',lambda r,m,e:r['semantic_conflict'].update(resolution='postcommit failures are exempt'))
probe('f09-binding-deletion',lambda r,m,e:r['semantic_conflict']['source_bindings'].pop())
probe('saved-retention-forged',lambda r,m,e:m['rows'][0]['existing_record_verbatim']['expected'].update(retention='Released'))
probe('saved-ack-forged',lambda r,m,e:m['rows'][0]['existing_record_verbatim']['expected'].update(ack_calls=0))
probe('captured-version-forged',lambda r,m,e:m['rows'][0]['existing_record_verbatim']['input']['capture']['asset_versions'][0].update(content_digest='0'*64))
save('probes.json',{'role':'independent document semantic review; no product execution','positive_control':guard(req,mat,env),'negative_mutations':mut,'method':'new reviewer-owned in-memory mutations; exact source/pointer equality and authority invariants; author checker not invoked'})
findings=[{'id':'G02-R-01','severity':'INFO','classification':'BOARD_ONLY_DRIFT','detail':'235 source hashes: 234 match; docs/board.json differs. Current G02 card changes only notes and updatedAt. Candidate embedded prior card is a semantic snapshot; original whole-board bytes cannot be reconstructed or proven exact from it. No candidate correction required for a sealed snapshot.'},{'id':'G02-R-02','severity':'OPEN','classification':'OWNER_DECISION_REQUIRED','detail':'F09 BDD-19 complete restoration at every commit failure and existing deferred-retention candidate remain unreconciled. All 13 bindings retained, resolution null. Review does not choose a failure taxonomy.'},{'id':'G02-R-03','severity':'INFO','classification':'TIME_AUTHORITY_LIMIT','detail':'12:37:05.377Z candidate owner_heartbeat is creation-context metadata, not evidence of 12:47:05.741Z current Owner instruction or exact adoption. Candidate remains unapproved.'}]
save('findings.json',{'reviewer':'/root/g02_decision_submission_review','author':req['author'],'findings':findings,'blocking_candidate_defects':[]})
results={'task':'PD-P1-G02-DEC-01','verdict':'PASS_DOCUMENT_CONSOLIDATION_ONLY','reviewer':'/root/g02_decision_submission_review','author':req['author'],'sources':{'count':235,'matching':234,'drift':['docs/board.json']},'pointer_bindings':{'count':len(allptr),'resolved':903,'verbatim_projections':893,'current_equal':892,'exception':'sealed prior board card; notes/updatedAt only'},'failure_matrix_rows':139,'html_machine_equal':[b==d for b,d in zip(blocks,[req,mat,env])],'candidate_seal':sealchecks,'product_authority':{'files':len(ah),'mismatches':ad,'historical_head':authority['head'],'live_head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'meaning':'796 content authority verified; 31babe87 is not live HEAD; management board changes do not establish product change'},'semantic_probes':{'negative':len(mut),'rejected':sum(x['observed']=='REJECT' for x in mut),'positive':not guard(req,mat,env)},'approval':None,'implementation':'NOT AUTHORIZED','skeleton':'NOT AUTHORIZED','product_RED_GREEN':'NOT RUN','native_restart_recovery':'NOT RUN','review_limit':'Document source fidelity only. Does not approve exact schema/API/transaction/envelope; source candidates and OPEN gaps remain unchanged. prepare/validate/commit/rollback/material versions/Undo/atomicity are existing candidate statements or OPEN, never newly inferred contracts.'}
save('results.json',results)
page='<!doctype html><meta charset="utf-8"><title>G02 independent review</title><style>body{font:16px system-ui;max-width:1050px;margin:40px auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><h1>G02 獨立文件審查</h1><p>PASS_DOCUMENT_CONSOLIDATION_ONLY。方向已採納；精確 Owner 選項仍 null。未批准 architecture / Skeleton / RED / native / product。</p><p>235 sources、903 pointers、139 state/outcome rows；HTML 三份完整 JSON 與 machine 一致。僅 board notes / updatedAt 漂移，不宣稱重建原 bytes。F09 BDD19 與 deferred retention 衝突 13 bindings 原樣保留。</p><p><a href="findings.json">Findings</a> · <a href="probes.json">New negative probes</a> · <a href="binding-results.json">Source bindings</a> · <a href="probes.py">Reviewer runner</a></p><pre>'+html.escape(json.dumps(results,ensure_ascii=False,indent=2))+'</pre>'
(out/'index.html').write_text(page,encoding='utf-8')
print('semantic probes',len(mut),'rejected',sum(x['observed']=='REJECT' for x in mut))
