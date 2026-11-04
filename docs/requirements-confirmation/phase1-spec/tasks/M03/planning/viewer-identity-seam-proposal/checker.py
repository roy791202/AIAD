"""Author-only bounded document checks. Run python -B checker.py. No acceptance."""
import copy, hashlib, json, pathlib, subprocess
import document_model as m
P=pathlib.Path(__file__).resolve().parent
def read(n):return json.loads((P/n).read_text(encoding='utf-8'))
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checks=[]
def check(name,ok):
 checks.append({'id':name,'pass':bool(ok)})
 assert ok,name
f=read('fixtures.json');a=f['authority'];projection=f['projection'];original=copy.deepcopy(a)
candidate_schema=read('observation.schema.json')
check('candidate-schema-keyword-audit',m.EVAL.audit(candidate_schema) is None)
check('candidate-closed-observation',m.EVAL.valid(candidate_schema,f['native_observation']['capture']))
for row in read('identity-mapping.json'):
 for kind in ('source_pointer','delivery_source_pointer'):
  file,pointer=row[kind].split('#');value=read(file)
  for key in pointer.strip('/').split('/'):value=value[key]
  check('mapping:'+row['command']+':'+row['field']+':'+kind,value is not None)
check('bounded-revision',m.REFRESH.u64(a['revision']) and a['revision']=='9007199254740993')
b=m.begin_case(a,projection)
br,bs,bc=m.BEGIN.begin(b,m.schema('preview-begin-correction','request.schema.json'))
check('begin-full-response',m.schema('preview-begin-correction','response.schema.json')(br) and br['ok'])
entry=m.from_projection(a,br['value']);old=entry['handle']
observed=m.identity(a,old)
check('all-full-root-fields',set(observed)==set(m.FIELDS)|{'native_live','revoked'} and m.CLOSE.identity(observed))
check('same-root-positive',m.admit(a,entry,observed,observed) is None)
mutations=[]
for phase in ('capture','delivery'):
 for k in m.FIELDS+('native_live','revoked'):
  c=copy.deepcopy(observed);d=copy.deepcopy(observed);o=c if phase=='capture' else d
  if k in ('native_live','revoked'):o[k]=not o[k]
  elif k=='generation':o[k]='4'
  elif k in ('project_uuid','document_uuid','session_uuid','preview_session'):o[k]='99999999-9999-4999-8999-999999999999'
  else:o[k]+='-changed'
  code=m.admit(a,entry,c,d);check('reject-'+phase+'-'+k,code is not None)
  mutations.append({'phase':phase,'field':k,'capture':c,'delivery':d,'expected_error':code})
for label,bad in [('unknown',{**observed,'unknown':True}),('missing',{k:v for k,v in observed.items() if k!='root_instance'}),('typed',{**observed,'native_live':'true'}),('generation-range',{**observed,'generation':'18446744073709551616'})]:
 check('reject-'+label,m.admit(a,entry,bad,observed)=='DependencyNotReady')
new_projection=copy.deepcopy(projection);new_projection['preview_session']=f['replacement_handle']
rc=m.refresh_case(a,entry,new_projection,observed,observed)
rr,rs,rcalls=m.REFRESH.refresh(rc,m.schema('viewer-refresh-integration','request.schema.json'),lambda x:m.schema('viewer-refresh-integration','response.schema.json')({'ok':True,'value':x,'replayed':False}),lambda e:True)
check('refresh-full-response',m.schema('viewer-refresh-integration','response.schema.json')(rr) and rr['ok'])
check('refresh-one-slot-replacement',rs['preview_count']==1 and rs['retired']==[old] and rs['sequence']=='1')
new_entry=m.from_projection(a,rr['value'])
old_case=m.intent_case(a,new_entry,old);old_response,old_state,old_calls=m.INTENT.intent(old_case)
check('old-intent-closed',old_response['error']['code']=='PreviewClosed' and old_state==old_case['before'])
new_case=m.intent_case(a,new_entry,new_entry['handle']);ir,is_,ic=m.INTENT.intent(new_case)
check('new-intent-full-response',m.schema('viewer-action-typed-correction','response.schema.json')(ir) and ir['ok'] and is_['sequence']=='2')
new_entry.update(sequence=is_['sequence'],mock=is_['mock'])
new_obs=m.identity(a,new_entry['handle']);cc=m.close_case(a,new_entry,new_obs,new_obs)
cr=m.CLOSE.close(cc,m.schema('viewer-close-integration','request.schema.json'),lambda e:True)
check('close-full-response',m.schema('viewer-close-integration','response.schema.json')(cr['response']) and cr['response']['ok'] and cr['delivered'])
check('close-slot-and-mock',cr['state']['slots']==0 and not cr['state']['preview_active'] and cr['state']['mock']=={} and cr['state']['capabilities']==[])
rollback=copy.deepcopy(rc);rollback['provider']['outcome']={'code':'DependencyNotReady','details':{'dependency':'C1_CODEC'}}
er,es,ec=m.REFRESH.refresh(rollback,m.schema('viewer-refresh-integration','request.schema.json'),lambda x:True,lambda e:True)
check('refresh-beforecommit-preserves-old',not er['ok'] and es['preview_session']==old and es['preview_count']==1 and es['retired']==[] and es['can_act'] is False)
unknown=copy.deepcopy(cc);unknown['provider']['outcome']='ResponseLostAfterCommit'
ur=m.CLOSE.close(unknown,m.schema('viewer-close-integration','request.schema.json'),lambda e:True)
check('unknown-close-no-false-rollback',not ur['response']['ok'] and ur['state']['slots']==0 and not ur['delivered'] and ur['ui']=='CloseUncertain' and not ur['automatic_retry'])
late=copy.deepcopy(cc);late['provider']['delivery']['runtime_epoch']='new-epoch'
lr=m.CLOSE.close(late,m.schema('viewer-close-integration','request.schema.json'),lambda e:True)
check('late-delivery-no-ui-install',lr['response']['error']['code']=='MissingBinding' and lr['state']['slots']==0 and not lr['delivered'])
check('authority-unchanged',a==original)
for n,c in [('begin',b),('refresh',rc),('intent',new_case)]:
 state=bs if n=='begin' else rs if n=='refresh' else is_
 for k in ('content','history','dirty','saved_baseline','owner_sessions','content_hash','saved_hash'):
  if k in c['before']:check(n+'-preserves-'+k,state[k]==c['before'][k])
for k in ('content','history','dirty','saved_baseline','owner_sessions','content_hash','saved_hash'):
 if k in cc['before']:check('close-preserves-'+k,cr['state'][k]==cc['before'][k])
write('sequence-witness.json',{'layer':'NEW AUTHOR DOCUMENT COMPOSITION ONLY','mapper':'document_model.py','authority':a,'begin':{'input':b,'response':br,'state':bs,'calls':bc},'refresh':{'input':rc,'response':rr,'state':rs,'calls':rcalls},'old_intent':{'input':old_case,'response':old_response,'state':old_state,'calls':old_calls},'new_intent':{'input':new_case,'response':ir,'state':is_,'calls':ic},'close':{'input':cc,'result':cr},'refresh_rollback':{'input':rollback,'response':er,'state':es,'calls':ec},'unknown_close':{'input':unknown,'result':ur},'late_close':{'input':late,'result':lr}})
write('negative-fixtures.json',mutations)
for path,digest in read('preserved-inputs.json').items():check('preserved:'+path,hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest)
for path,digest in read('source-current.json')['source_hashes'].items():check('product:'+path,hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()==digest)
write('verification.json',{'author':'/root/m03_viewer_identity_seam_packet','status':'PASS_AUTHOR_DOCUMENT_CHECKS_ONLY','checks':len(checks),'passed':len(checks),'negative_identity_cases':len(mutations),'composition_branches':8,'independent_review':'NOT RUN','native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft2020':'NOT RUN','checks_detail':checks})
print(json.dumps({'checks':len(checks),'negative_identity_cases':len(mutations),'status':'PASS_AUTHOR_DOCUMENT_CHECKS_ONLY'}))
