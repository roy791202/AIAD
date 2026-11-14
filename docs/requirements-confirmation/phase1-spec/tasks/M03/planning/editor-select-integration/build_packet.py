from pathlib import Path
import json,copy,hashlib,html
P=Path(__file__).parent;T=P.parents[2];R=Path.cwd()
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def put(n,v): (P/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base=T/'integration-contract-revision-v3'
for kind in ('request','response'):
 d=read(base/f'h2-design_editor_select-{kind}.schema.json');put(kind+'.schema.json',d)
from document_model import fresh,run,U
from schema_eval import valid,audit
req=read(P/'request.schema.json');resp=read(P/'response.schema.json')
# Preserve all original root choices; new InvalidRequest alternatives are explicitly proposals.
put('response.schema.json',resp)
s=fresh();r=dict(binding_ref=U,expected_generation='7',expected_revision='9',node_id='node-1');p=dict(capture=copy.deepcopy(s['identity']),delivery=copy.deepcopy(s['identity']),role='ui-editor',origin='tauri://localhost',native_live=True,ready=True,outcome='Selected')
def fixture(name,mut=None):
 c=dict(id=name,before=copy.deepcopy(s),request=copy.deepcopy(r),provider=copy.deepcopy(p))
 if mut:mut(c)
 c['expected']=run(c,lambda x:valid(req,x));return c
cases=[fixture('select'),fixture('clear',lambda c:c['request'].update(node_id=None)),fixture('repeat',lambda c:c['before'].update(selection='node-1'))]
for key,value in [('expected_revision','8'),('expected_generation','6'),('binding_ref','00000000-0000-4000-8000-000000000000'),('node_id','missing'),('node_id',''),('expected_revision','18446744073709551616'),('expected_revision',True),('expected_generation','09')]:cases.append(fixture('request-'+key+'-'+str(value),lambda c,k=key,v=value:c['request'].update({k:v})))
for key in r:cases.append(fixture('missing-'+key,lambda c,k=key:c['request'].pop(k)))
for key,value in [('role','ui-viewer'),('origin','https://evil.invalid'),('native_live',False),('native_live','true'),('ready',False),('ready','false'),('outcome','Rejected'),('outcome',{}),('capture',{}),('delivery',{})]:cases.append(fixture('provider-'+key+'-'+str(value),lambda c,k=key,v=value:c['provider'].update({k:v})))
for key in s['identity']:cases.append(fixture('foreign-'+key,lambda c,k=key:c['provider']['capture'].update({k:'foreign'})))
for key in s['identity']:cases.append(fixture('late-'+key,lambda c,k=key:c['provider']['delivery'].update({k:'replacement'})))
cases.extend([fixture('duplicate-node',lambda c:c['before']['nodes'].append(copy.deepcopy(c['before']['nodes'][0]))),fixture('foreign-node',lambda c:c['before']['nodes'][0].update(document_uuid='foreign')),fixture('bad-node-bool',lambda c:c['before']['nodes'][0].update(node_id=True)),fixture('unknown-request',lambda c:c['request'].update(label='node-1'))])
for value in [None,False,[],{},'',0]:cases.append(fixture('root-'+repr(value),lambda c,v=value:c.update(request=v)))
put('fixtures.json',cases)
probes=[]
for kind,root,good in [('request',req,r),('response',resp,cases[0]['expected']['response'])]:
 for value in [None,False,[],0,'x',{},dict(good,extra=True)]:probes.append(dict(kind=kind,value=value,valid=False))
 for k in good:
  x=copy.deepcopy(good);x.pop(k);probes.append(dict(kind=kind,value=x,valid=False))
 probes.append(dict(kind=kind,value=good,valid=True))
# All admitted error branches and nested closed shapes.
from schema_eval import sample
for branch in resp['$defs']['Error']['oneOf']:
 e=sample(resp,branch);v={'ok':False,'error':e,'replayed':False};probes.append(dict(kind='response',value=v,valid=True));bad=copy.deepcopy(v);bad['error']['details']['extra']=True;probes.append(dict(kind='response',value=bad,valid=False))
put('root-probes.json',probes)
policies=[('error mapping','Original broad Error union, no select-specific ordering','Validate request; exact native identity; generation; revision; typed node identity; owner outcome. Missing/foreign/duplicate node -> IdentityConflict.'),('selection lifecycle','Selection ephemeral; content unchanged','Select and clear and repeated selection retain revision/history/dirty/baseline/pins/ACK; replayed false, no replay cache.'),('delivery','No exact select response delivery fence','Only exact current native tuple may render; replacement or closed window discards, no automatic retry; selection may already have changed.'),('atomicity','No new provider implementation authorized','Trusted M04 observation and select performed atomically against captured revision are premises, not established by this reducer.'),('lexical bounds','Original regex anchors permit host-specific end semantics; runtime checked u64','Physical roots preserved; explicit semantic u64 check rejects overflow and noncanonical input. No full Draft certification.'),('invalid envelope','Original no explicit InvalidRequest alternatives','Original InvalidRequest field/reason branch retained; per-command reason values Type or OutOfRange proposed.')]
put('before-after.json',[dict(id='ES-P'+str(i+1),status='PROPOSED_PENDING_OWNER',aspect=a,before=b,after=c) for i,(a,b,c) in enumerate(policies)])
put('ui-schema.json',dict(component='Editor selection',role='native owning Editor',controls=[dict(name='node selection',value='stable node_id or null',action='design_editor_select',default=None,disabled='missing/stale binding')],validation='No labels; exact current projection membership',success='Highlight selection; no dirty/history/revision change',errors='Keep existing highlight on rejection; discard stale delivery',empty='Clear with null',accessibility='Keyboard focus and announced selection',status='PROPOSED_PENDING_OWNER'))
trace=[dict(bdd='ES-'+str(i+1),fixture=c['id'],contract='Ephemeral selection and exact identity',level='L2 document model only',status='AUTHOR_CHECK_ONLY') for i,c in enumerate(cases)];put('traceability.json',trace)
feature=['Feature: Ephemeral Editor selection','  Background:','    Given a current native Editor bound to its document','  Rule: Selection never changes document content']
for i,c in enumerate(cases):feature.extend(['',f'  Scenario: ES-{i+1} {c["id"]}','    Given the declared fixture state', '    When the author selects the declared node', '    Then the selection result and preserved document match the declared expectation'])
(P/'module.feature').write_text('\n'.join(feature)+'\n',encoding='utf-8')
(P/'steps.py').write_text('"""Pending native automation; never counts as executable BDD acceptance."""\ndef given_fixture(context, fixture_id):\n raise NotImplementedError("Native fixture runner pending")\ndef when_select(context):\n raise NotImplementedError("Native command adapter pending")\ndef then_expected(context):\n raise NotImplementedError("Independent native assertions pending")\n',encoding='utf-8')
put('pending-automation.json',dict(native='NOT RUN',independent='NOT RUN',build='NOT RUN',product_tests='NOT RUN',valid_RED='NOT RUN',full_Draft2020='NOT RUN',owner_adoption='PENDING',required=['native authenticity','atomic observation/select transaction','independent behavior execution','response delivery race proof']))
source=read(T/'M01/planning/s2-green/source-current.json');put('source-current.json',source)
paths=[R/'AGENTS.md',R/'docs/board.json',P.parent/'current-state.json',T/'M01/planning/s2-green/source-current.json',P.parent/'cx-h2-revision-v3/module-spec.json',P.parent/'h2-exact-design/module-spec.json',base/'h2-design_editor_select-request.schema.json',base/'h2-design_editor_select-response.schema.json']
put('preserved-inputs.json',{str(x.relative_to(R)):hashlib.sha256(x.read_bytes()).hexdigest() for x in paths})
spec=dict(module='M03',task='PD-P1-M03-PREP-01',command='design_editor_select',status='PROPOSED_PENDING_OWNER',scope='One bounded command, document-only planning. No product implementation.',authority='M01/planning/s2-green/source-current.json; current HEAD 5b709343a890503ebbe24a802e43cda5647df124; 31babe historical',architecture=dict(hexagonal='Native UI -> Tauri command/input port -> selection use case -> domain projection; application -> owner observation/select output port <- M04 adapter',dependency='UI -> command -> application -> domain; owner adapter implements port; no domain infrastructure',ownership='M04 owns document/revision/history. M03 owns ephemeral selection projection.',mutation='Only owner.select_ephemeral; no content mutation',transaction='Atomic native identity/current revision check plus ephemeral select is trusted provider premise',forbidden=['formal save','ACK','pin','history mutation','label lookup','arbitrary dispatch']),contracts=['content/history/revision/dirty/baseline/pins/ACK unchanged','exact native binding/document/session/project/root/epoch/window/generation and current projection identity','failure preserves selection'],bdd_categories={f'B{i}':('Applicable: fixtures' if i not in [11] else 'Deferred: native platform compatibility NOT RUN') for i in range(1,13)},cases=len(cases),acceptance=['All document fixture state/call/response expectations pass','Original/product hashes preserved','Independent native and Owner adoption remain pending'],risks=['Trusted fixture provider is not authenticity proof','Atomic observation/select not demonstrated','Delivery loss after select is uncertain; do not retry automatically'])
put('module-spec.json',spec)
body='<h1>M03 Editor selection planning</h1><p>PROPOSED_PENDING_OWNER · Yellow parent unchanged · no product acceptance</p>'
for title,value in [('Purpose and boundary',spec),('Hexagonal view','Native Editor → command → selection application → domain\nOwner adapter → implements observation/select port ← application'),('Dependency view','UI → Tauri → application → domain; M04 owns content, M03 ephemeral selection'),('Before / after Owner decisions',read(P/'before-after.json')),('UI schema',read(P/'ui-schema.json')),('BDD / TDD traceability',trace),('Results and deferred work',read(P/'pending-automation.json'))]:body+='<h2>'+title+'</h2><pre>'+html.escape(json.dumps(value,indent=2))+'</pre>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 Editor selection</title><style>body{max-width:1100px;margin:3rem auto;font:16px system-ui;background:#101827;color:#eee}pre{white-space:pre-wrap;padding:1rem;background:#1e293b}h2{color:#7dd3fc}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(spec).replace('<','\\u003c')+'</script></html>',encoding='utf-8')
print('generated',len(cases),'fixtures',len(probes),'root probes')

