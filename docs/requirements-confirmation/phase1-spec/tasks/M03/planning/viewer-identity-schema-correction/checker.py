"""Author-only bounded schema correction checks; python -B checker.py. No acceptance."""
import pathlib,json,copy,hashlib,importlib.util,subprocess,html,re
P=pathlib.Path(__file__).resolve().parent; S=P.parent/'viewer-identity-seam-proposal'; R=P.parent/'viewer-identity-seam-review'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(n,x):(P/n).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('preserved_mapper',S/'document_model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
schema=read(P/'observation.schema.json'); old=read(S/'observation.schema.json'); checks=[]
def ck(n,b):checks.append({'id':n,'pass':bool(b)});assert b,n
ck('bounded-keyword-audit',m.EVAL.audit(schema) is None)
f=read(S/'fixtures.json');a=f['authority'];entry=m.from_projection(a,f['projection']);base=m.identity(a,entry['handle']); original=copy.deepcopy(base)
rows=[]
def probe(label,x):
 before=copy.deepcopy(x); sv=m.EVAL.valid(schema,x); gv=m.CLOSE.identity(x)
 ck(label+':language',sv==gv)
 codes={}
 for phase in ('capture','delivery'):
  c=x if phase=='capture' else base;d=x if phase=='delivery' else base
  code=m.admit(a,entry,c,d);codes[phase]=code
  ck(label+':'+phase+':malformed', (code=='DependencyNotReady')== (not gv))
 ck(label+':no-mutation',x==before and base==original)
 rows.append({'id':label,'observation':x,'schema':sv,'identity':gv,'admission':codes})
review=read(R/'results.json');counter=[]
for i,v in enumerate(review['findings'][0]['counterexamples']):
 x={**base,v['field']:v['value']};ck('original-counterexample:'+str(i),m.EVAL.valid(old,x) and not m.CLOSE.identity(x));probe('VIS-RF1-'+str(i+1),x);counter.append(v)
vals=[None,False,True,0,1,[],{},'', '0','1','9','10','9007199254740993','18446744073709551614','18446744073709551615','18446744073709551616','99999999999999999999','100000000000000000000','00','01','-1','+1',' 1','1 ','1\n','1\r','1\r\n','١','１','1\u2028','1\u2029']
for i,v in enumerate(vals):probe('generation-'+str(i),{**base,'generation':v})
u='abcdef12-abcd-4abc-8abc-abcdef123456'
uvals=[None,False,0,[],{},'',u,u.upper(),u+'\n',u+'\r',u+'\r\n',u+'\u2028',u+'\u2029',' '+u,u+' ',u.replace('-',''),u.replace('4abc','5abc'),u.replace('8abc','7abc'),u.replace('8abc','babc'),u.replace('a','ａ'), 'not-a-uuid']
for k in ('project_uuid','document_uuid','session_uuid','preview_session'):
 for i,v in enumerate(uvals):probe(k+'-'+str(i),{**base,k:v})
for k in ('consumer','window_instance','root_instance','runtime_epoch'):
 for i,v in enumerate([None,False,0,[],{},'','x','x\n','λ']):probe(k+'-'+str(i),{**base,k:v})
for k in ('native_live','revoked'):
 for i,v in enumerate([None,0,1,'true',[],{},True,False]):probe(k+'-'+str(i),{**base,k:v})
for k in base:probe('missing-'+k,{a:b for a,b in base.items() if a!=k})
probe('extra',{**base,'extra':True})
for i,v in enumerate([None,False,[],0,'identity']):probe('root-type-'+str(i),v)
# Fresh range vectors on both sides of every decimal prefix of MAX, not fixture lookup.
maximum=18446744073709551615
for exponent in range(21):
 for delta in (-1,0,1):
  n=(maximum//(10**exponent))*(10**exponent)+delta
  if n>=0:probe('range-%s-%s'%(exponent,delta),{**base,'generation':str(n)})
# Audit all schema nodes and references; forbid hidden schema drift.
diffs=[]
for k in old['properties']:
 if old['properties'][k]!=schema['properties'][k]:diffs.append({'pointer':'/properties/'+k,'before':old['properties'][k],'after':schema['properties'][k]})
ck('only-five-property-domains',set(d['pointer'] for d in diffs)=={'/properties/'+k for k in ('generation','project_uuid','document_uuid','session_uuid','preview_session')})
rest=copy.deepcopy(schema)
for k in old['properties']:rest['properties'][k]=old['properties'][k]
ck('schema-rest-preserved',rest==old)
ck('strict-end-no-dollar',all('$' not in d['after']['pattern'] and d['after']['pattern'].endswith('(?![\\s\\S])') for d in diffs))
ck('no-schema-ref',not any('$ref' in json.dumps(v) for v in schema.values()))
source_schema=read(P.parent/'viewer-refresh-integration/request.schema.json')
def resolve(node):
 while '$ref' in node:
  dest=source_schema
  for key in node['$ref'][2:].split('/'):dest=dest[key]
  node=dest
 return node
for key in ('project_uuid','document_uuid','session_uuid','preview_session'):
 ck('reuse-resolved-uuid:'+key,schema['properties'][key]==resolve(source_schema['properties']['preview_session']))
ck('reuse-resolved-u64',schema['properties']['generation']==resolve(source_schema['properties']['expected_revision']))
for field,value,code in [('consumer','other-consumer','UnauthorizedCaller'),('root_instance','other-root','MissingBinding'),('generation','0','StaleOwner'),('preview_session','abcdef12-abcd-4abc-8abc-abcdef123456','PreviewClosed'),('native_live',False,'PreviewClosed'),('revoked',True,'PreviewClosed')]:
 x={**base,field:value};ck('semantic-schema-valid:'+field,m.EVAL.valid(schema,x))
 for phase in ('capture','delivery'):
  ck('semantic-code:'+field+':'+phase,m.admit(a,entry,x if phase=='capture' else base,x if phase=='delivery' else base)==code)
audit=[]
for folder in (S,R,P.parent/'viewer-close-integration',P.parent/'viewer-refresh-integration'):
 for file in folder.iterdir():
  if file.is_file() and file.suffix in ('.py','.json','.md','.feature'):
   for lineno,line in enumerate(file.read_text(encoding='utf-8-sig').splitlines(),1):
    if any(word in line for word in ('observation.schema','CLOSE.identity','def identity','def u64','18446744073709551615','project_uuid','document_uuid','session_uuid','preview_session','generation')):
     audit.append({'file':str(file),'line':lineno,'text':line[:1000],'classification':'UNCHANGED_SOURCE_REFERENCE; correction applies only candidate five property domains'})
write('definition-reference-audit.json',audit)
write('schema-diff.json',diffs);write('fixtures.json',rows)
preserved=[]
for path,expected in read(S/'preserved-inputs.json').items():
 actual=digest(pathlib.Path(path));cl='MATCH' if actual==expected else 'BOARD_MANAGEMENT_DIFF' if path=='docs/board.json' else 'UNEXPECTED_DRIFT';ck('frozen:'+path,cl!='UNEXPECTED_DRIFT');preserved.append({'path':path,'expected':expected,'actual':actual,'classification':cl})
authority=pathlib.Path('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');src=read(authority)
for path,expected in src['source_hashes'].items():ck('product:'+path,digest(pathlib.Path(path))==expected)
ck('796-authority',len(src['source_hashes'])==796);ck('513-frozen',len(preserved)==513)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();ck('actual-head',head=='5b709343a890503ebbe24a802e43cda5647df124');ck('historical-distinct',src['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab' and src['head']!=head)
model=read(S/'module-spec.json');ck('pending-owner',model['Owner']=='PENDING' and model['architecture_approval']=='NOT APPROVED')
write('preservation.json',preserved)
sourcehash={str(p):digest(p) for folder in (S,R,P.parent/'viewer-close-integration',P.parent/'viewer-refresh-integration') for p in folder.iterdir() if p.is_file()}
write('preserved-hashes.json',sourcehash)
trace={'finding':'VIS-RF1','scope':'five property domains only; original mapper loaded at original path bytewise, dependency paths unchanged','guard':'viewer-close-integration/document_model.py:identity/u64','schema_evaluator':'viewer-refresh-integration/schema_eval.py:valid uses re.search on actual parsed patterns','pattern_source':'viewer-refresh-integration/request.schema.json properties preview_session and expected_revision','definitions':'full observation root properties/required/additionalProperties audited; no refs or defs exist','diff':'schema-diff.json','fixtures':'fixtures.json','original_counterexamples':counter,'decisions':model['decisions'],'Owner':'PENDING','VIS-D1..D5':'UNCHANGED','admission_parity':'Schema validates tuple grammar only; well-typed mismatches/live/revoked still yield existing semantic admission errors; only malformed parity is claimed.'}
write('traceability.json',trace)
results={'author':'/root/m03_identity_schema_correction','status':'BOUNDED_AUTHOR_DOCUMENT_CHECKS_PASS_PENDING_INDEPENDENT_REVIEW','state':'REPLAN_REQUIRED','task':'PD-P1-M03-PREP-01','head':head,'historical_head':src['head'],'checks':len(checks),'passed':sum(x['pass'] for x in checks),'failed':0,'full_root_vectors':len(rows),'admission_phase_probes':2*len(rows),'original_counterexamples':len(counter),'property_domains_corrected':len(diffs),'preserved_inputs':len(preserved),'product_inputs':len(src['source_hashes']),'independent':'NOT RUN','native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft2020':'NOT RUN','module_acceptance':'NOT RUN','checks_detail':checks}
write('results.json',results)
module={'module':'M03','scope':'VIS-RF1 schema precision proposal only','architecture':'NOT APPROVED','Owner':'PENDING','decisions':model['decisions'],'source_architecture_reference':'../viewer-identity-seam-proposal/index.html','contracts':'CLOSE.identity unchanged; schemas align exact lowercase UUIDv4 and canonical unsigned 64-bit decimal string','bdd':[{'id':'SCHEMA-1','Given':'a complete identity observation','When':'schema and guard evaluate its shape','Then':'their tuple grammar decisions agree'},{'id':'SCHEMA-2','Given':'a well typed mismatching identity','When':'admission executes','Then':'existing rejection precedence is preserved'}],'tdd':{'runner':'python -B checker.py','layer':'bounded author document evaluator only','results':{k:v for k,v in results.items() if k!='checks_detail'}},'tasks':[{'id':'VIS-RF1','allowed':'new viewer-identity-schema-correction only','status':'PENDING_INDEPENDENT_REVIEW'}],'acceptance':['six historical discrepancies rejected','strict LF/CR/Unicode/range boundaries evaluated','no original or product mutation'],'risks':['No native provider contract adoption','No full Draft validator or product RED','VIS-D1..D5 pending; B058-B060 separate']}
write('module-spec.json',module)
body='<h1>M03 VIS-RF1 schema precision correction</h1><p>Yellow / REPLAN_REQUIRED. Author document proposal; independent review and Owner VIS-D1..D5 remain pending.</p><h2>Intent and boundaries</h2><p>Align five observation property domains with the unchanged admission guard. No native provider contract, public command schema, mapper, reducer, policy or ownership changes. Original models execute from their original paths.</p><h2>Exact before / after</h2><pre>'+html.escape(json.dumps(diffs,indent=2))+'</pre><h2>Verification</h2><p>Bounded subset evaluator: object, properties, required, additionalProperties, string, boolean, minLength and pattern. Actual parsed patterns use strict end assertions. Schema grammar parity does not mean all schema-valid observations pass semantic admission.</p><pre>'+html.escape(json.dumps({k:v for k,v in results.items() if k!='checks_detail'},indent=2))+'</pre><h2>Architecture, contracts, behavior and tasks</h2><p><a href="../viewer-identity-seam-proposal/index.html">Unchanged proposed architecture and pending decisions</a>. See traceability.json, schema-diff.json, fixtures.json, preservation.json and preserved-hashes.json. No new skeleton approval.</p><h2>Risk / next gate</h2><p>Independent bounded review, Owner approval, revised Skeleton and valid product RED are required before implementation. Native/build/product/full Draft/module acceptance NOT RUN.</p>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 schema correction</title><style>body{max-width:1100px;margin:40px auto;background:#111b25;color:#edf2f7;font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#203040;padding:18px}a{color:#9dd9ff}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(module).replace('</','<\\/')+'</script></html>',encoding='utf-8')
manifest={p.name:digest(p) for p in P.iterdir() if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')};write('artifact-hashes.json',manifest)
write('seal.json',{'author':results['author'],'status':results['status'],'artifact_count':len(manifest),'manifest_sha256':digest(P/'artifact-hashes.json'),'counts':{k:results[k] for k in ('checks','passed','failed','full_root_vectors','admission_phase_probes','original_counterexamples','preserved_inputs','product_inputs')},'next':'Independent bounded document review; Owner VIS-D1..D5 pending; Yellow unchanged'})
print(json.dumps({k:v for k,v in results.items() if k!='checks_detail'}))
