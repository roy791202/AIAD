"""Build correction-only document fixtures. Never writes source or earlier packages."""
import copy
import datetime
import hashlib
import html
import json
import pathlib
import subprocess
import uuid

P = pathlib.Path(__file__).parent
OLD = P.parent/'undo-response-integration'
ROOT = pathlib.Path.cwd()
STATUS = 'PROPOSED_PENDING_REACCEPTANCE_AND_OWNER'


def read(path):
    return json.loads(path.read_text(encoding='utf8'))


def write(name, value):
    (P/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf8')


for name in ['request.schema.json', 'response.schema.json', 'work-error-map.json', 'command-contract.json']:
    write(name, read(OLD/name))
old_source = read(OLD/'source-current.json')
source = copy.deepcopy(old_source)
source['historical_candidate'] = {'branch': old_source['branch'], 'head': old_source['head'], 'authority_entries':796}
source['captured_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
source['branch'] = subprocess.check_output(['git','branch','--show-current'],text=True).strip()
source['head'] = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
for folder in ['undo-response-integration','undo-response-review']:
    for file in sorted((P.parent/folder).iterdir()):
        if file.is_file():
            source['sources'][file.as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
source['sources'] = {name:hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest() for name in source['sources']}
authority = read(pathlib.Path(old_source['authority_manifest']))
# Historical 796 inventory is independently re-compared; current sources above are not its replacement.
authority_map = authority['source_hashes']
assert len(authority_map) == 796
source['authority_comparison_keys'] = list(authority.keys())
source['authority_drift_current'] = [name for name,h in authority_map.items() if not pathlib.Path(name).exists() or hashlib.sha256(pathlib.Path(name).read_bytes()).hexdigest()!=h]
source['authority_count_currently_compared'] = len(authority_map)
source['authority_manifest_sha256'] = hashlib.sha256(pathlib.Path(old_source['authority_manifest']).read_bytes()).hexdigest()
write('source-current.json', source)

old_cases = read(OLD/'fixtures.json')
request = old_cases[0]['request']
wire = []
for i,row in enumerate(read(OLD/'work-error-map.json')):
    for replay in [False, True]:
        res = copy.deepcopy(row['wire']);res['replayed']=replay
        wire.append({'id':f'CORR-F1-{i}-replay-{replay}', 'request':request,'response':res,'valid':True,
                     'premise':'wire diagnostic validity only; delivery additionally requires lifecycle authority'})
        wrong=copy.deepcopy(res);wrong['error']['details']['fields']['extra']='not-allowed'
        wire.append({'id':f'CORR-F1-{i}-extra-{replay}', 'request':request,'response':wrong,'valid':False})
nochange = read(P.parent/'undo-response-review/counterexamples.json')[2]['input']
wire.append({'id':'CORR-F2-schema-valid-command-invalid-NoChange','request':request,'response':nochange,'valid':False,'schema_valid':True})
success = next(copy.deepcopy(row['response']) for row in old_cases if row['valid'] and row['response']['ok'] and row['response']['value']['outcome']!='NoChange')
wire.append({'id':'CORR-success-closed-root','request':request,'response':success,'valid':True})
for name, change in [('extra-root',lambda r:r.update(extra=True)), ('missing-ok',lambda r:r.pop('ok')),('bad-success-replay',lambda r:r.update(replayed=True))]:
    res=copy.deepcopy(success);change(res)
    wire.append({'id':'CORR-'+name,'request':request,'response':res,'valid':False})

c = copy.deepcopy(read(OLD/'proof-model.json')['capture'])
c.update(project_uuid='project-a', owner_handle='existing-M04-owner-a', sender='native-editor-window-a')
A=['asset-A','a'*64];B=['asset-B','b'*64];C=['asset-C','c'*64];D=['asset-D','d'*64]
mutation={'issuer':'M04','receipt_id':'m04-undo-7-8','kind':'DocumentMutation','context':c,
          'operation_role':'undo','ordinal':'0','operation_id':str(uuid.uuid5(uuid.UUID(c['workflow_id']),'undo/0')),
          'before_revision':'7','after_revision':'8','history_before':'2','history_after':'1',
          'redo_before':'0','redo_after':'1','before_semantic_digest':'sha256:'+'a'*64,
          'after_semantic_digest':'sha256:'+'b'*64,'history_entry_id':'entry-2',
          'history_content_digest':'b'*64,'pin_id':'pin-undo-7',
          'outgoing_versions':[A],'restored_versions':[B],'surviving_history_versions':[C]}
pin={'issuer':'M05','receipt_id':'m05-held-undo-7','context':c,'operation_role':'undo','ordinal':'0',
     'transition_role':'pin','purpose':'Undo','operation_id':str(uuid.uuid5(uuid.UUID(c['workflow_id']),'pin/0')),'pin_id':'pin-undo-7','actual_state':'Held',
     'store_identity':'trusted-native-store-a','catalog_generation':'12','material_versions':[A,B],
     'source_receipt_ids':['resolution-a'],'request_digest':'e'*64}
before_values={'LiveDocuments':[A], 'UndoHistory':[B,C], 'RedoHistory':[], 'RecoverySnapshots':[D], 'InFlightTransactions':[A,B]}
after_values={'LiveDocuments':[B], 'UndoHistory':[C], 'RedoHistory':[A], 'RecoverySnapshots':[D], 'InFlightTransactions':[A,B]}
roots={'issuer':'M05','receipt_id':'m05-roots-undo-7-8','context':c,'pin_id':pin['pin_id'],
       'scope':c['document_uuid']+'/'+c['session_uuid'],'epoch':'6','completeness':'Complete','fenced':True,
       'source_receipt_ids':[mutation['receipt_id'],pin['receipt_id']], 'store_identity':'trusted-native-store-a',
       'before':{},'after':{}}
versions={'LiveDocuments':40,'UndoHistory':18,'RedoHistory':4,'RecoverySnapshots':9,'InFlightTransactions':11}
for kind,n in versions.items():
    for side,values in [('before',before_values),('after',after_values)]:
        roots[side][kind]={'provider':'registered-'+kind,'epoch':'6','complete':True,
                           'version':str(n+(side=='after' and kind in {'LiveDocuments','UndoHistory','RedoHistory'})),
                           'material_versions':values[kind],
                           'coverage':'complete project inventory including closed formal documents' if kind=='LiveDocuments' else 'all registered providers aggregated'}
proof=copy.deepcopy({'capture':c,'mutation':mutation,'pin':pin,'roots':roots,
                    'io':{'FileCommit':'NOT CALLED','formal_save_ack':'NOT CALLED','formal_root_transfer':'NOT CALLED'}})
trusted=copy.deepcopy({'capture':c,'M04_record':mutation,'M05_pin_record':pin,'M05_root_record':roots})
matrix=[]
def negative(name,path,value):
    matrix.append({'id':'CORR-PROOF-'+name,'changes':[{'path':path,'value':value}],
                   'expected':'REJECT_DOCUMENT_PROOF; never infer actual rollback; postcommit retention issue deferred, uncertain M04 indeterminate'})
for group,obj in [('capture',c),('mutation',mutation),('pin',pin),('roots',roots)]:
    def leaves(node,prefix):
        if isinstance(node,dict):
            for k,v in node.items():leaves(v,prefix+'.'+k)
        elif isinstance(node,list):
            if not node:negative(prefix,prefix,[['asset-forged','f'*64]])
            else:
                for i,v in enumerate(node):leaves(v,prefix+'.'+str(i))
        else:
            value = (not node) if type(node)is bool else ('99' if isinstance(node,str) and node.isdigit() else 'forged-'+str(node))
            negative(prefix,prefix,value)
    leaves(obj,group)
for k in proof['io']:negative('io-'+k,'io.'+k,'CALLED')
# Coherent cross-evidence forgery: internal equality alone would pass; immutable issuer lookup must reject.
for name,paths,value in [
 ('coherent-other-request',['capture.request_id','mutation.context.request_id','pin.context.request_id','roots.context.request_id'],'99999999-9999-4999-8999-999999999999'),
 ('coherent-other-operation',['capture.operation','mutation.context.operation','pin.context.operation','roots.context.operation'],'design_document_save'),
 ('coherent-other-pin',['mutation.pin_id','pin.pin_id','roots.pin_id'],'forged-pin'),
 ('coherent-wrong-material',['mutation.restored_versions.0.1','pin.material_versions.1.1','roots.after.LiveDocuments.material_versions.0.1'],'f'*64),
 ('mixed-epoch',['roots.after.RedoHistory.epoch'],'7'),
 ('missing-recovery-provider',['roots.after.RecoverySnapshots.complete'],False)]:
    matrix.append({'id':'CORR-X-'+name,'changes':[{'path':p,'value':value} for p in paths],'expected':'REJECT_DOCUMENT_PROOF'})
negative('unknown-pin-not-Held','pin.actual_state','Unknown')
for row in matrix:
    row['expected_confirmed_commit_effect']={'outcome':'AppliedRetentionDeferred','actual_revision':'8','rollback':False,'release':False}
    row['premise']='Independent existing M04 owner fixture lookup established actual R8 commit. Without that fact use Indeterminate, not this effect. Mismatched presented attestation never authorizes rollback.'

state={'live_revision':'11','authorized':True,'closed':False,'owner_sender':c['sender'],
       'owner_generation':'3','immutable_capture':c,'inflight':False,'M04_commit_established':True,
       'retention_verified':True,'retained_terminal':{'outcome':'Applied','revision':'8','replayed':False},'pin_state':'Held'}
event={'sender':c['sender'],'generation':'3','capture':c}
base_result={'live_revision':'11','undo_calls':0,'retained':True,'deliver':False,'render':False,'pin_state':'Held','release':False}
life=[]
def lc(name,changes,outcome,extra=None,event_changes=None):
    s=copy.deepcopy(state);s.update(changes);e=copy.deepcopy(event);e.update(event_changes or {})
    result=copy.deepcopy(base_result);result['pin_state']=s['pin_state'];result['outcome']=outcome;result.update(extra or {})
    life.append({'id':'CORR-LIFE-'+name,'state':s,'event':e,'expected':result})
lc('changed-live-replay-no-rollback',{},'RetainedReplay',{'deliver':True,'terminal':{'outcome':'Applied','revision':'8','replayed':True}})
lc('matching-live-render',{'live_revision':'8'},'RetainedReplay',{'live_revision':'8','deliver':True,'render':True,'terminal':{'outcome':'Applied','revision':'8','replayed':True}})
for i,row in enumerate(read(OLD/'work-error-map.json')):
    terminal=copy.deepcopy(row['wire']);replayed=copy.deepcopy(terminal);replayed['replayed']=True
    lc('terminal-error-'+str(i),{'retained_terminal':terminal},'RetainedReplay',{'deliver':True,'terminal':replayed})
    lc('revoked-terminal-error-'+str(i),{'retained_terminal':terminal,'authorized':False},'UnauthorizedCaller')
lc('close',{'closed':True},'UnauthorizedCaller')
lc('replacement-owner',{'owner_generation':'4'},'UnauthorizedCaller')
lc('forged-native-sender',{},'UnauthorizedCaller',event_changes={'sender':'replacement-window'})
lc('inflight',{'inflight':True},'InProgress')
lc('uncertain-before-cached-result',{'M04_commit_established':False,'pin_state':'Unknown'},'Indeterminate')
lc('confirmed-retention-failure-unknown-pin',{'retained_terminal':None,'retention_verified':False,'pin_state':'Unknown'},'AppliedRetentionDeferred',{'deliver':True})
lc('confirmed-retention-failure-held-pin',{'retained_terminal':None,'retention_verified':False},'AppliedRetentionDeferred',{'deliver':True})
changed=copy.deepcopy(c);changed['expected_revision']='8'
lc('changed-capture-replay',{},'ReplayConflict',event_changes={'capture':changed})
lc('revoked-uncertain-precedence',{'authorized':False,'M04_commit_established':False},'UnauthorizedCaller')
fixtures={'trusted_fixture_records':trusted,'presented_proof':proof,'wire':wire,'lifecycle':life,
          'u64':[['0',True],['18446744073709551615',True],['18446744073709551616',False],['01',False],['-1',False],['1e3',False],['',False],[True,False],[7,False],['7\n',False]]}
write('fixtures.json',fixtures);write('mutation-matrix.json',matrix)
decisions=[
 {'id':'UNDO-CORR-F1','before':'Whole envelope equality incorrectly rejects replayed=true terminal rejection','after':'Exact closed error diagnostic equality independent of replay flag; delivery still requires native sender/owner/generation and immutable capture gate'},
 {'id':'UNDO-CORR-F2','before':'Shared NoChange bypasses Undo revision checks','after':'Shared wire root unchanged, Undo-specific semantic validator always rejects NoChange; empty history remains typed NoUndo'},
 {'id':'UNDO-CORR-PROOF','before':'Receipt IDs/counters presence; no issuer/context/root-member verification','after':'Document fixture resolves existing M04 owner record and M05 issuer evidence separately, exact entire immutable-record match plus context, semantic, revision/history/redo, pin/material and five-provider old/new set checks'},
 {'id':'UNDO-CORR-LIFECYCLE','before':'Narrative expected text only','after':'Executable fixture reducer compares exact output including live revision, calls, delivery, render, retention and actual Unknown pin; uncertainty before cached-result use; native authority checked before disclosure'}]
for d in decisions:d['status']=STATUS
write('decisions-before-after.json',decisions)
write('pending-automation.json',{'status':STATUS,'pending':['Independent read-only correction acceptance','Owner adoption of choices and exact issuer evidence seam','Real native sender/capability authority and late-owner asynchronous race tests','M04 runtime immutable MutationReceipt and M05 durable catalog/fence/retention verification','Complete FullDraft command/root integration','Accepted Skeleton then compilable valid RED; implementation and module regression afterward'],'not_authorized':['Skeleton','product changes','board/current-state changes','physical release/GC','new manager/second registry','formal file commit or ACK']})
spec={'identity':{'module':'M03','task':'PD-P1-M03-PREP-01','revision':'undo-response-correction-v1','status':STATUS,'author':'/root/m03_undo_correction'},
 'intent':'Correct F1/F2 and make the formerly narrative proof/lifecycle requirements executable as document oracles only.',
 'architecture':{'hexagonal':'UI projection → Tauri command → M03 facade → existing M04 single DocumentOwner → WORK. M04 → M05 retention through proposed output seam; no UI authority or second document registry.',
                 'dependency_view':'M03 command boundary → M04 DocumentOwner (content/revision/history SSOT) → WORK; M05 issuer owns pin and five root manifests; native sender adapter supplies trusted authority.',
                 'ownership':'M03 displays/provides facade only; M04 owns mutation, immutable runtime receipt and replay capture. M05 owns actual pin/root evidence. Fixture lookup maps are not product registries.',
                 'transaction':'Precommit known rejection unchanged. Confirmed 7→8 stays 8 even on roots failure; deferred retention preserves old/new union. Uncertain M04 never claims unchanged or success. No formal persistence/ACK.',
                 'diagrams_status':'PROPOSED views derived from cited v3 sources, not architecture approval'},
 'decisions':decisions,
 'trust_premises':['All issuer lookups here are immutable trusted DOCUMENT FIXTURES. No runtime issuer authenticity, native store identity, durable receipt inclusion or fence enforcement proved.',
                   'Fixture sender/authorization is out-of-band model input. Boolean true is not a product security implementation; real native capability gate remains pending.',
                   'Existing M04 unique owner is required, not a new proof manager/global registry. M05 receipt alone never establishes M04 commit.',
                   'M04 commit established includes a verified precommit terminal rejection as well as verified mutation; Unknown means neither fact established.',
                   'Unknown actual pin stays Unknown; conservative retention means no automatic release, not a fabricated Held attestation.',
                   'Material pairs and provider coverage below are illustrative concrete document data; production project-wide closed-document inventories remain unproved.'],
 'root_sets':{'before':roots['before'],'after':roots['after'],'retention_on_uncertainty':'Keep union of each old/new material set plus all unresolved pins; do not release or prune. Complete requires every registered provider and fence; omitted RecoverySnapshots or closed formal documents means Unknown.'},
 'command':read(P/'command-contract.json'),
 'coverage':{'BDD-F1':'7 typed terminal diagnostics first/replay; revoked error replay no disclosure','BDD-F2':'NoChange wire accepted but command rejected','BDD-PROOF':'Each immutable leaf mutation plus coherent cross-evidence forgery and concrete material/old-new roots','BDD-LIFECYCLE':'changed-live replay, render gate, owner replacement/close/revoke, in-flight, unknown outcome, retention failure','B1-B12':{'B1':'terminal/success','B2':'strict U64','B3':'closed root/fields invalid','B4':'M05 mismatch','B5':'confirmed commit retention deferred','B6':'live revision/history/redo and exact semantic roots','B7':'M04 commit fact vs retention','B8':'close/revoke/inflight','B9':'Unknown retained no release','B10':'M03/M04/M05 evidence binding','B11':'shared v3 roots unchanged; Undo stricter','B12':'F1/F2 counterexamples'}},
 'tests':{'command':'python docs/requirements-confirmation/phase1-spec/tasks/M03/planning/undo-response-correction/check_documents.py','layer':'DOCUMENT AUTHOR SELF CHECK ONLY','old_suites':'save181 and undo58 NOT rerun; not progress','product_RED':'NOT RUN; document negative fixtures are not product RED'},
 'scope':{'allowed':[P.as_posix()+'/**'],'protected':['all earlier packages','product/tests','board','current-state'],'primary_module':'M03','skeleton':'NOT CREATED'},
 'acceptance':['Independent reviewer must rerun new correction cases and challenge fixture authority premises','F1 authorized retained error replay accepted; revoked/late owner denied before disclosure','F2 schema-valid NoChange rejected by command semantics','Every context/proof/pin/root leaf mismatch and coherent cross-evidence forgery rejected','New material B restored Live, C survives Undo, A outgoing Redo; D Recovery unchanged; no mixing epoch/version sets','Changed-live replay delivers old result without live rollback or second Undo','Unknown M04 outcome blocks cached success; unknown pin remains Unknown; no auto release','No product/board/current-state change; no module completion or approval implied'],
 'health':{'fullDraft':'MISSING','product_tests':'NOT RUN','native_runtime':'NOT RUN','RED':'NOT RUN','GREEN':'NOT RUN','BUILD':'NOT RUN','Owner_adoption':'NOT ADOPTED','independent_acceptance':'NOT RUN','module_complete':False}}
write('module-spec.json',spec)
feature='''Feature: M03 Undo document correction oracle
  Background:
    Given an immutable authorized Undo capture and separate trusted issuer document fixtures
  Rule: Terminal replays preserve diagnostics and require current authority
    Scenario: BDD-F1 Retained rejection replay
      Given a retained typed NoUndo rejection and an authorized matching caller
      When the same Undo request is repeated
      Then the same typed rejection is returned with replay indicated
    Scenario: BDD-F1R Revoked caller cannot receive terminal evidence
      Given a retained rejection and a revoked caller
      When the Undo request is repeated
      Then evidence delivery is denied and retained server evidence is preserved
  Rule: Undo has no successful empty-history outcome
    Scenario: BDD-F2 Empty history
      Given a document with empty Undo history
      When Undo is requested
      Then a typed NoUndo rejection is required and NoChange success is invalid
  Rule: Evidence is bound to the whole operation
    Scenario: BDD-PROOF Coherent forged material evidence
      Given an immutable issuer record restoring material version B
      When presented evidence consistently substitutes another material version
      Then the document oracle rejects the substituted evidence
  Rule: Replay and uncertainty preserve current state
    Scenario: BDD-LIFECYCLE Changed live revision
      Given retained revision 8 and current live revision 11
      When the authorized original request is repeated
      Then revision 8 is delivered as a replay without replacing live revision 11
    Scenario: BDD-UNKNOWN Uncertain commit and pin
      Given commit evidence and actual pin state are unknown
      When an Undo terminal result is considered
      Then the outcome is indeterminate and no release or synthetic Held claim occurs
'''
(P/'module.feature').write_text(feature,encoding='utf8')
write('step-definition-stubs.json',[{'scenario':name,'fixture':'fixtures.json','document_automation':'check_documents.py','product_step_status':'PENDING_NOT_IMPLEMENTED','product_stub':'raise NotImplementedError("requires adopted envelope, accepted Skeleton, valid RED and independent verification")'} for name in ['BDD-F1','BDD-F1R','BDD-F2','BDD-PROOF','BDD-LIFECYCLE','BDD-UNKNOWN']])
body='<h1>M03 Undo correction</h1><p class="status">PROPOSED_PENDING_REACCEPTANCE_AND_OWNER</p><p>F1 terminal rejection replay and F2 forbidden Undo NoChange corrected in a new document oracle. Evidence binding and lifecycle cases are now executable fixture comparisons. No product verification or acceptance is claimed.</p>'
body+='<h2>Proposed architecture views</h2><pre>UI → Tauri → M03 facade → M04 single DocumentOwner → WORK\n                              ↓ declared retention seam\n                         M05 pin + five root providers\n\nMutation: capture → precommit checks → one M04 Undo → roots transition\nFailure: before commit unchanged | confirmed commit retained | uncertain fail closed</pre>'
for key,value in spec.items():
    body+='<section><h2>'+html.escape(key)+'</h2><pre>'+html.escape(json.dumps(value,ensure_ascii=False,indent=2))+'</pre></section>'
for name in ['module.feature','step-definition-stubs.json','fixtures.json','mutation-matrix.json','decisions-before-after.json','source-current.json','pending-automation.json']:
    body+='<details><summary>'+name+'</summary><pre>'+html.escape((P/name).read_text(encoding='utf8'))+'</pre></details>'
body+='<details><summary>Executable document checker</summary><pre>'+html.escape((P/'check_documents.py').read_text(encoding='utf8'))+'</pre></details>'
body+='<p>Verification: see <a href="verification.json">author document self-check</a>. Independent acceptance NOT RUN. Product tests/native/RED/GREEN/BUILD NOT RUN. FullDraft MISSING. <a href="artifact-hashes.json">Artifact hashes</a>.</p>'
(P/'index.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><title>M03 Undo correction</title><style>body{max-width:1150px;margin:40px auto;padding:20px;background:#101721;color:#dae4ef;font:16px system-ui}h1,h2,summary{color:#efc36c}section,details{border:1px solid #425467;padding:16px;margin:12px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere}.status{color:#f2cc60}a{color:#9bd8ff}</style>'+body+'<script id="module-spec" type="application/json">'+json.dumps(spec,ensure_ascii=False).replace('<','\\u003c')+'</script></html>',encoding='utf8')
print('Correction document fixtures generated; run new checker separately.')
