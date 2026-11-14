from pathlib import Path
import json,hashlib,copy,uuid
P=Path(__file__).resolve().parent
R=P.parents[6]
T=R/'docs/requirements-confirmation/phase1-spec/tasks'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,v):(P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
def ident(n):return str(uuid.uuid5(uuid.NAMESPACE_URL,'m06-merge-document-fixture/'+n))
s=read(T/'M06/planning/cx-exchange-revision-v3/shared-contract.json')
write('transition-request.schema.json',s['request_hash_schema'])
write('effective-proof-contract.json',{k:s[k] for k in ['replay_protocol','proof_registry_record','mutation_wire_result','h2_error_lifecycle']})
c={'project_uuid':ident('project'),'document_uuid':ident('document'),'session_id':ident('session'),'owner_generation':'4','captured_revision':'10','workflow_id':ident('merge')}
store={'volume_id':'fixture-volume','file_id':'catalog-file','canonical_target':'fixture://catalog'}
asset={'asset_id':'asset-imported','digest':'a'*64,'size_bytes':'16'}
old={'asset_id':'asset-existing','digest':'b'*64,'size_bytes':'12'}
idmap=[{'source_id':'source-parent','target_id':'fresh-parent'},{'source_id':'source-child','target_id':'fresh-child'}]
before={'revision':'10','content':{'entities':[{'id':'existing','parent':None}],'edges':[],'assets':[old]},'undo':[],'redo':[],'formal_baseline':'formal-9','recovery_baseline':'recovery-8'}
after=copy.deepcopy(before);after['revision']='11';after['content']['entities'] += [{'id':'fresh-parent','parent':None},{'id':'fresh-child','parent':'fresh-parent'}];after['content']['edges']=[{'from':'fresh-parent','to':'fresh-child'}];after['content']['assets'].append(asset);after['undo']=[{'id':'history-merge','before':before['content'],'after':after['content']}]
undo=copy.deepcopy(after);undo['revision']='12';undo['content']=copy.deepcopy(before['content']);undo['undo']=[];undo['redo']=copy.deepcopy(after['undo'])
def ref(issuer,kind,n,ctx,evidence):return {'issuer':issuer,'receipt_id':ident(n),'kind':kind,'context_digest':digest(ctx),'evidence_digest':digest(evidence)}
source={'archive_digest':'c'*64,'entities':['source-parent','source-child'],'parent':{'source-child':'source-parent'},'edge':['source-parent','source-child'],'asset':asset}
sourceproof=ref('M06','VerifiedBundle','source-proof',c,source)
metadata={'asset_id':asset['asset_id'],'name':'imported','media_type':'application/octet-stream','original_filename':'fixture.bin','legacy_aliases':['original-asset']}
body={'mode':'VerifiedBundle','bundle':{'issuer_proof':sourceproof,'source_digest':source['archive_digest'],'entries':[{'asset':asset,'metadata':metadata}],'legacy_alias_mapping':[{'alias':'original-asset','asset_id':asset['asset_id'],'digest':asset['digest']}]},'purpose':'Import','store_identity':store,'expected_catalog_generation':'5'}
def req(role,body,ctx=c,issuer='M05',ordinal='0'):return {'protocol':'SGA-TRANSITION-v2','issuer':issuer,'role':role,'ordinal':ordinal,'context':ctx,'body':body}
imp=req('import',body)
mutation={'context':c,'target_identity':{'project_uuid':c['project_uuid'],'document_uuid':c['document_uuid'],'session_id':c['session_id'],'owner_generation':c['owner_generation']},'source_digest':source['archive_digest'],'mapping':idmap,'mapping_digest':digest(idmap),'candidate_digest':digest(after['content']),'before_digest':digest(before['content']),'before_revision':'10','after_revision':'11','pin_id':ident('import-pin'),'history_entry_id':'history-merge'}
mutproof=ref('M04','DocumentMutation','merge-proof',c,mutation)
uc=dict(c,captured_revision='11',workflow_id=ident('undo'))
umutation=dict(mutation,pin_id=ident('undo-pin'),context=uc,before_digest=digest(after['content']),candidate_digest=digest(before['content']),before_revision='11',after_revision='12')
undoproof=ref('M04','DocumentMutation','undo-proof',uc,umutation)
roots=[];transfers=[];publishes=[];uroots=[];utransfers=[];upublishes=[]
for phase,ctx,proof,rs,ts,ps,epoch in [('merge',c,mutproof,roots,transfers,publishes,'7'),('undo',uc,undoproof,uroots,utransfers,upublishes,'8')]:
 for i,kind in enumerate(['LiveDocuments','UndoHistory','RedoHistory']):
  assets=([old,asset] if phase=='merge' and kind in ['LiveDocuments','UndoHistory'] or phase=='undo' and kind=='RedoHistory' else [old] if kind=='LiveDocuments' else [])
  root={'manifest_id':ident(phase+kind),'provider_id':'M04-owner-provider','kind':kind,'epoch':epoch,'completeness':'Complete','assets':assets}
  rs.append(root);ts.append(req('transfer-live',{'pin_id':(mutation['pin_id'] if phase=='merge' else umutation['pin_id']),'store_identity':store,'root_manifest':root,'external_proof':proof,'expected_catalog_generation':str(6+i)},ctx,ordinal=str(i)))
  ps.append(req('publish',{'registration_id':'registered-'+kind,'provider_capability_id':'trusted-M04-provider','expected_epoch':epoch,'manifest':root,'expected_catalog_generation':str(6+i)},ctx,ordinal=str(i)))
def record(request,receipt,kind,pairs,rootids,external=None,sourceids=[]):
 return {'issuer':'M05','receipt_id':receipt,'workflow_id':request['context']['workflow_id'],'operation_id':str(uuid.uuid5(uuid.UUID(request['context']['workflow_id']),request['role']+'/'+request['ordinal'])),'role':request['role'],'ordinal':request['ordinal'],'request_digest':digest(request),'context':request['context'],'store_identity':store,'target_identity':store,'expected_generation':request['body']['expected_catalog_generation'],'committed_generation':str(int(request['body']['expected_catalog_generation'])+1),'source_receipt_ids':sourceids,'pin_id':request['body'].get('pin_id',mutation['pin_id']),'asset_pairs':[{k:a[k] for k in ['asset_id','digest']} for a in sorted(pairs,key=lambda a:(a['asset_id'],a['digest']))],'root_manifest_ids':sorted(rootids),'external_proof':external,'result':kind,'request_protocol':'SGA-TRANSITION-v2'}
irecord=record(imp,ident('import-receipt'),'Imported',[asset],[],sourceids=[sourceproof])
catalog={'premises':['Trusted immutable issuer fixture lookup; never caller assertion','Document commit and history change atomic inside M04 exclusive owner','Root providers registered and fenced at stated epoch; stale providers fail/defer','Catalog receipt and pin/root transition same CAS assumed, no native proof','M04 runtime mutation proof survives this modeled operation only; restart not proven'], 'source':source,'source_proof':sourceproof,'import_request':imp,'import_record':irecord,'held_pin':{'pin_id':mutation['pin_id'],'purpose':'Import','state':'Held','context':c,'versions':[asset]},'mutation':mutation,'mutation_proof':mutproof,'undo_mutation':umutation,'undo_proof':undoproof,'merge_publish':publishes,'merge_transfer':transfers,'undo_publish':upublishes,'undo_transfer':utransfers,'before':before,'after_merge':after,'after_undo':undo,'other_document':{'revision':'50','content':'unaffected'},'transfer_records':[]}
for requests in [transfers,utransfers]:
 for r in requests:
  proof=r['body']['external_proof']; external={k:proof[k] for k in ['issuer','receipt_id','kind','context_digest']};external.update(target_identity=mutation['target_identity'],raw_digest='d'*64,projection_digest=proof['evidence_digest'])
  catalog['transfer_records'].append(record(r,ident('receipt-'+r['context']['workflow_id']+r['ordinal']),'Transferred',r['body']['root_manifest']['assets'],[r['body']['root_manifest']['manifest_id']],external,[proof]))
write('immutable-issuer-fixture.json',catalog)
base={'import_request':imp,'import_receipt_ref':{'issuer':'M05','receipt_id':irecord['receipt_id']},'mutation':mutation,'mutation_proof':mutproof,'merge_publish':publishes,'merge_transfer':transfers,'undo_request':req('undo',{'owner_handle':'M04-exclusive-owner','binding_ref':'binding-current','history_entry_id':'history-merge','history_content_digest':digest(before['content']),'expected_revision':'11','expected_generation':'4','pin_receipt':ref('M05','Pin','undo-pin-receipt',uc,{'pin_id':umutation['pin_id'],'versions':[old,asset]})},uc,'M04'),'undo_mutation':umutation,'undo_proof':undoproof,'undo_publish':upublishes,'undo_transfer':utransfers,'commit_observation':'KnownNotAttempted','root_observation':'Failure','perform_undo':False,'undo_observation':'Applied','undo_root_observation':'Failure'}
catalog['undo_held_pin']={'pin_id':umutation['pin_id'],'purpose':'Undo','state':'Held','context':uc,'versions':[old,asset]};catalog['undo_request']=base['undo_request'];write('immutable-issuer-fixture.json',catalog)
cases=[]
def add(name,x,expected):cases.append({'id':name,'input':copy.deepcopy(x),'expected':expected})
add('known-precommit-failure',base,'RejectedBeforeMutation')
x=copy.deepcopy(base);x['commit_observation']='Applied';add('merge-root-failure',x,'MergeAppliedRetentionDeferred')
x['perform_undo']=True;add('undo-root-failure',x,'UndoAppliedRetentionDeferred')
x['root_observation']='Verified';x['undo_root_observation']='Verified';add('all-verified',x,'UndoApplied')
x=copy.deepcopy(base);x['commit_observation']='Unknown';add('unknown-commit',x,'UnverifiedOutcome')
for name,path,value in [('wrong-target',['mutation','target_identity','document_uuid'],ident('wrong')),('wrong-context',['import_request','context','workflow_id'],ident('wrong')),('wrong-digest',['merge_transfer',0,'body','external_proof','evidence_digest'],'e'*64),('wrong-import-map',['mutation','mapping',0,'target_id'],'fresh-WRONG'),('wrong-issuer',['mutation_proof','issuer'],'IO'),('formal-proof-is-not-mutation',['mutation_proof','kind'],'FormalFile'),('stale-provider',['merge_publish',0,'body','expected_epoch'],'6'),('import-receipt-wrong-issuer',['import_receipt_ref','issuer'],'UI'),('unknown-body-field',['import_request','body','unapproved'],'bad'),('wrong-source-bytes',['import_request','body','bundle','source_digest'],'f'*64)]:
 x=copy.deepcopy(base);x['commit_observation']='Applied';v=x
 for k in path[:-1]:v=v[k]
 v[path[-1]]=value;add(name,x,'ProofMismatch')
write('fixtures.json',cases)
write('fixture-input.schema.json',{'$schema':'https://json-schema.org/draft/2020-12/schema','description':'Bounded input closed at top; transition nested closure validated against exact central schema; mutation observations are candidate fixture fields, not adopted public DTO.','type':'object','properties':{k:({'enum':['KnownNotAttempted','Applied','Unknown']} if k=='commit_observation' else {'enum':['Failure','Verified','Stale','Unknown']} if k in ['root_observation','undo_root_observation'] else {'type':'boolean'} if k=='perform_undo' else {'enum':['Applied','Unknown']} if k=='undo_observation' else {'type':'array'} if type(v)==list else {'type':'object'}) for k,v in base.items()},'required':list(base),'additionalProperties':False})
write('before-after.json',{'before':before,'after_merge':after,'after_undo':undo,'pins_on_deferred':catalog['held_pin'],'formal_save_calls':0,'other_document':catalog['other_document']})

