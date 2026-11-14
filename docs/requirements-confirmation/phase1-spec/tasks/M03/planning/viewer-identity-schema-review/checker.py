"""Independent bounded document review. Run python -B checker.py; no production writes."""
import pathlib, json, hashlib, copy, importlib.util, re, subprocess, html
P=pathlib.Path(__file__).resolve().parent
B=P.parent; S=B/'viewer-identity-seam-proposal'; C=B/'viewer-identity-schema-correction'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
checks=[]
def ck(name,value):
 checks.append({'id':name,'pass':bool(value)})
 if not value: raise AssertionError(name)
def load(p):
 spec=importlib.util.spec_from_file_location('independent_review_model',p)
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
# Separate evaluator: only the actual keyword set is supported; fail closed otherwise.
KEYS={'$schema','type','properties','required','additionalProperties','minLength','maxLength','pattern'}
def audit(s):
 ck('keywords:'+str(len(checks)),set(s)<=KEYS)
 for child in s.get('properties',{}).values(): audit(child)
def valid(s,v):
 t=s.get('type')
 if t=='object':
  if type(v)!=dict:return False
  if any(k not in v for k in s.get('required',[])):return False
  if s.get('additionalProperties') is False and set(v)-set(s.get('properties',{})):return False
  return all(valid(s['properties'][k],x) for k,x in v.items() if k in s.get('properties',{}))
 if t=='boolean':return type(v)==bool
 if t=='string':
  return type(v)==str and len(v)>=s.get('minLength',0) and len(v)<=s.get('maxLength',10**9) and ('pattern' not in s or re.search(s['pattern'],v) is not None)
 raise ValueError('unsupported schema type')
schema=read(C/'observation.schema.json');old=read(S/'observation.schema.json')
audit(schema);audit(old)
srcdirs=[S,C,B/'viewer-identity-seam-review',B/'viewer-close-integration',B/'viewer-refresh-integration',B/'preview-begin-correction',B/'viewer-action-typed-correction']
before={str(p):sha(p) for d in srcdirs for p in d.rglob('*') if p.is_file()}
for name,h in read(C/'artifact-hashes.json').items():ck('candidate-seal:'+name,sha(C/name)==h)
ck('candidate-manifest-seal',sha(C/'artifact-hashes.json')==read(C/'seal.json')['manifest_sha256'])
m=load(S/'document_model.py');f=read(S/'fixtures.json');authority=f['authority'];entry=m.from_projection(authority,f['projection']);base=m.identity(authority,entry['handle'])
UUID_FIELDS=('project_uuid','document_uuid','session_uuid','preview_session')
MAX='18446744073709551615'
def uuid(v):
 if type(v)!=str or len(v)!=36:return False
 return all(c=='-' if i in (8,13,18,23) else c in '0123456789abcdef' for i,c in enumerate(v)) and v[14]=='4' and v[19] in '89ab'
def u64(v):
 return type(v)==str and 1<=len(v)<=20 and all(c in '0123456789' for c in v) and (len(v)==1 or v[0]!='0') and (len(v)<20 or v<=MAX)
def shape(v):
 return type(v)==dict and set(v)==set(base) and all(type(v[k])==str and len(v[k])>0 for k in ('consumer','window_instance','root_instance','runtime_epoch')) and all(uuid(v[k]) for k in UUID_FIELDS) and u64(v['generation']) and all(type(v[k])==bool for k in ('native_live','revoked'))
def expected(v):
 if not shape(v):return 'DependencyNotReady'
 if not v['native_live'] or v['revoked']:return 'PreviewClosed'
 if any(v[k]!=base[k] for k in ('consumer','window_instance')):return 'UnauthorizedCaller'
 if any(v[k]!=base[k] for k in ('project_uuid','root_instance','runtime_epoch','document_uuid','session_uuid')):return 'MissingBinding'
 if v['generation']!=base['generation']:return 'StaleOwner'
 if v['preview_session']!=base['preview_session']:return 'PreviewClosed'
 return None
rows=[]
def probe(label,v):
 original=copy.deepcopy(v);s=valid(schema,v);g=m.CLOSE.identity(v);want=shape(v)
 ck(label+':schema-oracle',s==want);ck(label+':guard-oracle',g==want)
 codes={phase:m.admit(authority,entry,v if phase=='capture' else base,v if phase=='delivery' else base) for phase in ('capture','delivery')}
 for phase,code in codes.items():ck(label+':'+phase,code==expected(v))
 ck(label+':immutable',v==original)
 rows.append({'id':label,'observation':v,'expected_shape':want,'schema':s,'guard':g,'expected_code':expected(v),'codes':codes})
probe('baseline',base)
values=[None,False,True,0,1,-1,1.5,[],{},'', '0','1',MAX,str(int(MAX)-1),str(int(MAX)+1),'00','01','-0','-1','+0','+1','1e0','1E1','1.0',' 0','0 ','\t1','1\t','1\n','1\r','1\r\n','1\u2028','1\u2029','١','１','1\u00a0','1\x00']
# Every digit of the maximum is varied, with both all-zero and all-nine suffixes.
for pos in range(20):
 for digit in '0123456789':
  for tail in ('0','9'): values.append(MAX[:pos]+digit+tail*(19-pos))
for power in range(22):
 for offset in (-1,0,1):
  if 10**power+offset>=0:values.append(str(10**power+offset))
for i,v in enumerate(values):probe('u64-'+str(i),{**base,'generation':v})
u='a1b2c3d4-e5f6-4abc-8def-0123456789ab'
uv=[None,False,True,0,1,[],{},'',u,u.upper(),u+'\n',u+'\r',u+'\r\n','\n'+u,u+'\u2028',u+'\u2029',u+'\x00',u+' ', ' '+u,u.replace('a','ａ'),u.replace('-','−')]
for pos in (14,19):
 for ch in '0123456789abcdefABCDEF':uv.append(u[:pos]+ch+u[pos+1:])
for pos in range(36):
 for ch in ('g','A','\n','λ'):uv.append(u[:pos]+ch+u[pos+1:])
for field in UUID_FIELDS:
 for i,v in enumerate(uv):probe(field+'-'+str(i),{**base,field:v})
for field in ('consumer','window_instance','root_instance','runtime_epoch'):
 for i,v in enumerate([None,False,True,0,[],{},'','valid','\n','\r','λ','\u2028']):probe(field+'-'+str(i),{**base,field:v})
for field in ('native_live','revoked'):
 for i,v in enumerate([None,0,1,'false',[],{},False,True]):probe(field+'-'+str(i),{**base,field:v})
for field in base:probe('missing-'+field,{k:v for k,v in base.items() if k!=field})
for i,v in enumerate([None,False,0,[],str(base),{**base,'extra':0}]):probe('root-'+str(i),v)
# Preserve rejection priority under multiple simultaneous valid mismatches.
probe('multi-semantic-priority',{**base,'consumer':'different','generation':'0','revoked':True})
probe('malformed-before-dead',{**base,'generation':'+1','native_live':False})
closure=[]
for i,counter in enumerate(read(B/'viewer-identity-seam-review/results.json')['findings'][0]['counterexamples']):
 v={**base,counter['field']:counter['value']}
 ck('RF1-original-'+str(i),valid(old,v) and not valid(schema,v) and m.admit(authority,entry,v,base)=='DependencyNotReady' and m.admit(authority,entry,base,v)=='DependencyNotReady')
 closure.append({**counter,'corrected_schema_accepts':valid(schema,v),'status':'CLOSED_DOCUMENT_CORRECTION_ONLY'})
# Native ECMAScript checks same full-root inputs and actual patterns; no fullmatch wrapper.
js="""const fs=require('fs'); const d=JSON.parse(fs.readFileSync(0,'utf8'));function v(s,x){if(s.type==='object'){return x!==null&&typeof x==='object'&&!Array.isArray(x)&&s.required.every(k=>Object.hasOwn(x,k))&&Object.keys(x).every(k=>Object.hasOwn(s.properties,k))&&Object.keys(x).every(k=>v(s.properties[k],x[k]));}if(s.type==='boolean')return typeof x==='boolean';if(s.type==='string')return typeof x==='string'&&[...x].length>=(s.minLength||0)&&[...x].length<=(s.maxLength||1e9)&&(!s.pattern||new RegExp(s.pattern).test(x));throw Error('unsupported');}process.stdout.write(JSON.stringify(d.rows.map(r=>v(d.schema,r.observation))));"""
node=json.loads(subprocess.check_output(['node','-e',js],input=json.dumps({'schema':schema,'rows':rows}),text=True))
for r,n in zip(rows,node):ck(r['id']+':ECMAScript',n==r['expected_shape']);r['ECMAScript']=n
changed=[k for k in old['properties'] if old['properties'][k]!=schema['properties'][k]]
ck('exact-five-property-diff',set(changed)==set(UUID_FIELDS)|{'generation'})
rest=copy.deepcopy(schema);rest['properties']=old['properties'];ck('root-and-other-keywords-preserved',rest==old)
refresh=read(B/'viewer-refresh-integration/request.schema.json')
audits=[]
for field in changed:
 ref=refresh['properties']['expected_revision' if field=='generation' else 'preview_session']['$ref'];resolved=refresh
 for part in ref[2:].split('/'):resolved=resolved[part]
 ck('definition-ref-'+field,schema['properties'][field]==resolved)
 audits.append({'candidate_pointer':'/properties/'+field,'source':'../viewer-refresh-integration/request.schema.json','ref':ref,'resolved':resolved,'match':True})
ck('no-candidate-defs-or-refs','$defs' not in schema and '$ref' not in json.dumps(schema))
source_lines=[]
for file in [C/'observation.schema.json',B/'viewer-refresh-integration/request.schema.json',S/'document_model.py',B/'viewer-close-integration/document_model.py']:
 for line,text in enumerate(file.read_text(encoding='utf-8-sig').splitlines(),1):
  if any(s in text for s in ('pattern','def identity','def admit','def u64','$ref','UUID','U64Decimal')):source_lines.append({'path':str(file),'line':line,'text':text})
preservation=[]
for path,h in read(S/'preserved-inputs.json').items():
 actual=sha(pathlib.Path(path));kind='MATCH' if actual==h else 'BOARD_MANAGEMENT_DIFF' if path=='docs/board.json' else 'UNEXPECTED_DRIFT'
 ck('513:'+path,kind!='UNEXPECTED_DRIFT');preservation.append({'path':path,'expected':h,'actual':actual,'classification':kind})
authority_file=pathlib.Path('docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json');a=read(authority_file)
for path,h in a['source_hashes'].items():ck('796:'+path,sha(pathlib.Path(path))==h)
ck('796-count',len(a['source_hashes'])==796);ck('513-count',len(preservation)==513)
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip();ck('actual-head',head=='5b709343a890503ebbe24a802e43cda5647df124');ck('historical-distinct',a['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab' and a['head']!=head)
board=read(pathlib.Path('docs/board.json'));card=next(x for x in board['items'] if x['id']=='PD-P1-M03-PREP-01');ck('yellow-preserved',card['light']=='Yellow')
write('board-context.json',{'id':card['id'],'status':card['status'],'light':card['light'],'latest_notes':card['notes'][-3:]})
ck('all-source-bytes-preserved',all(sha(pathlib.Path(p))==h for p,h in before.items()))
write('source-hashes.json',before);write('preservation.json',preservation);write('new-fixtures.json',rows);write('definition-reference-audit.json',{'five_definitions':audits,'source_lines':source_lines,'candidate_defs':[],'candidate_refs':[]});write('rf1-closure.json',closure)
trace={'reviewer':'/root/m03_identity_schema_review','author':'/root/m03_identity_schema_correction','finding':'VIS-RF1','closure':'rf1-closure.json','new_vectors':'new-fixtures.json','source_refs':'definition-reference-audit.json','source_authority':str(authority_file),'actual_head':head,'historical_head':a['head'],'mapper_reducers_policies':'original paths imported; source-hashes.json byte preserved; no candidate model replacement','Owner':'PENDING','VIS-D1..D5':'PENDING_UNCHANGED','CIH-G1':'OWNER_PENDING_UNRESOLVED','schema_evaluator':'Independent bounded Python re.search + ECMAScript RegExp.test against actual parsed pattern; independent character/lexical oracle. No fullmatch around schema regex.','scope':'Schema tuple grammar parity; semantic authorization remains separate with unchanged error precedence.'}
write('traceability.json',trace)
result={'status':'PASS_VIS_RF1_SCHEMA_DOCUMENT_CORRECTION_ONLY_PENDING_OWNER','reviewer':trace['reviewer'],'author':trace['author'],'checks':len(checks),'passed':sum(c['pass'] for c in checks),'failed':0,'fresh_full_root_vectors':len(rows),'capture_delivery_probes':2*len(rows),'ECMAScript_full_root_probes':len(node),'original_counterexamples_closed':len(closure),'property_definitions_audited':len(audits),'preserved_inputs':len(preservation),'product_inputs':len(a['source_hashes']),'source_files_byte_preserved':len(before),'head':head,'historical_head':a['head'],'findings':[],'state':'REPLAN_REQUIRED','Owner':'PENDING','VIS-D1..D5':'PENDING','CIH-G1':'OWNER_PENDING','native':'NOT RUN','build':'NOT RUN','product':'NOT RUN','valid_RED':'NOT RUN','full_Draft2020':'NOT RUN','module_acceptance':'NOT RUN','author_2356_rerun':'NOT RUN','checks_detail':checks}
write('results.json',result)
summary={k:v for k,v in result.items() if k!='checks_detail'}
module={'module':'M03','review':summary,'scope':'Independent document correction review only','traceability':trace,'acceptance':['Six original VIS-RF1 counterexamples closed','Five property definitions and related refs match parsed source','Fresh positive/negative complete observation roots agree with lexical oracle, existing guard and both admission phases','Original mapper/reducers/policies/source bytes preserved'],'risks':['Owner VIS-D1..D5 and CIH-G1 remain pending','No native atomicity, provider authenticity, runtime or product approval','Bounded keyword/regex evaluation only; no full Draft2020 claim']}
body='<h1>M03 independent VIS-RF1 schema correction review</h1><p>PASS for the bounded document correction only. Yellow / REPLAN_REQUIRED remains; Owner decisions remain pending.</p><h2>Intent and independence</h2><p>Reviewer /root/m03_identity_schema_review is distinct from correction author /root/m03_identity_schema_correction. Only this new review folder was written. No author checker rerun substitutes for review.</p><h2>Architecture and contract boundary</h2><p><a href="../viewer-identity-seam-proposal/index.html">Original proposed architecture</a> and <a href="../viewer-identity-schema-correction/index.html">sealed correction</a>. Original mapper, reducers and policies loaded at original paths and byte preserved. No new architecture, provider or native fence adoption. Grammar-valid identity mismatches retain UnauthorizedCaller, MissingBinding, StaleOwner and PreviewClosed; malformed tuples retain DependencyNotReady.</p><h2>Behavior and verification</h2><p>Fresh complete roots cover UUID v4 lower-case/version/variant/case/type/LF/CR/Unicode, canonical u64 min/max/overflow/each maximum digit/leading zero/sign/exponent/whitespace, missing and unknown fields, booleans and both capture/delivery. Independent lexical oracle plus bounded Python re.search and ECMAScript RegExp.test use the actual parsed schema pattern. No fullmatch masks regex ends.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre><h2>Definition and reference audit</h2><pre>'+html.escape(json.dumps(audits,indent=2))+'</pre><h2>Evidence navigation</h2><p><a href="new-fixtures.json">Fresh root fixtures/results</a> · <a href="rf1-closure.json">six counterexamples</a> · <a href="definition-reference-audit.json">exact source refs</a> · <a href="preservation.json">513 frozen inputs</a> · <a href="source-hashes.json">unchanged sources</a> · <a href="traceability.json">traceability</a> · <a href="checker.py">reproducible checker</a></p><h2>Risks and remaining gates</h2><p>VIS-D1..D5 / CIH-G1 remain Owner pending. No native atomicity/runtime approval; native, build, product, valid RED, full Draft2020 and module acceptance NOT RUN. Approval requires a separate Owner decision, adopted skeleton and valid product RED. This review closes only VIS-RF1 document precision.</p>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 independent schema review</title><style>body{max-width:1100px;margin:40px auto;background:#101a25;color:#edf3f7;font:16px system-ui}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#203246;padding:18px}a{color:#a5dfff}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(module).replace('</','<\\/')+'</script></html>',encoding='utf-8')
manifest={p.name:sha(p) for p in P.iterdir() if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')};write('artifact-hashes.json',manifest)
write('seal.json',{'reviewer':trace['reviewer'],'author':trace['author'],'status':result['status'],'artifact_count':len(manifest),'manifest_sha256':sha(P/'artifact-hashes.json'),'counts':{k:result[k] for k in ('checks','passed','failed','fresh_full_root_vectors','capture_delivery_probes','ECMAScript_full_root_probes','original_counterexamples_closed','preserved_inputs','product_inputs')},'bounds':'document correction only; Owner pending; native/build/product/valid_RED/full_Draft NOT RUN'})
print(json.dumps(summary))
