"""Planning-only exact semantic byte vectors; not a production codec or Skeleton."""
import json,hashlib,subprocess,re,html
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from tools.board.board_core.snapshot_safe import split_snapshot,mutate_snapshot_file
from tools.board.board_core.json_store import FileLock
O=Path(__file__).parent;P=O.parent;T=P.parent.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def put(n,v):(O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
base=load(T/'M01/planning/s2-green/source-current.json');assert all(sha(p)==h for p,h in base['source_hashes'].items());assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==base['head'];assert subprocess.check_output(['git','branch','--show-current'],text=True).strip()==base['branch']
h2=T/'M03/planning/h2-exact-design/review-request.json';r2=P/'s2-canonical-profile/module-spec.json';frozen={str(h2):sha(h2),str(r2):sha(r2)}
# Distinct planning value for raw decimal text; never binary floating-point equality.
class Num(str):pass
def number(token):
 m=re.fullmatch(r'(-?)(0|[1-9][0-9]*)(?:\.([0-9]+))?(?:[eE]([+-]?[0-9]+))?',token);assert m
 sign,integer,fraction,exponent=m.groups();fraction=fraction or '';digits=(integer+fraction).lstrip('0');power=int(exponent or '0')-len(fraction)
 if not digits:return ['n','0','0']
 while digits.endswith('0'):digits=digits[:-1];power+=1
 return ['n',('-' if sign else '')+digits,str(power)]
def typed(v):
 if isinstance(v,Num):return number(v)
 if v is None:return ['z']
 if type(v)==bool:return ['b',v]
 if isinstance(v,str):return ['s',v]
 if isinstance(v,list):return ['a',[typed(x) for x in v]]
 if isinstance(v,dict):return ['o',[[k,typed(v[k])] for k in sorted(v,key=lambda k:k.encode('utf-8'))]]
 raise AssertionError('No implicit numeric coercion in planning vectors')
def encode(v):return json.dumps(['SGA-DESIGN-SEM-v1',typed(v)],ensure_ascii=False,separators=(',',':')).encode('utf-8')
vectors=[]
values=[('zero','0'),('negative zero','-0'),('one','1'),('one decimal','1.00'),('one exponent','1e0'),('thousand','1000'),('thousand exponent','1E+03'),('tenth','0.1'),('tenth exponent','1e-1')]
for name,token in values:
 b=encode(Num(token));vectors.append({'id':f'M04-SEM-{len(vectors)+1:02d}','input_kind':'validated numeric token','input':token,'canonical_utf8_text':b.decode(),'sha256':'sha256:'+hashlib.sha256(b).hexdigest(),'status':'DOCUMENT_VECTOR_ONLY_PRODUCT_NOT_RUN'})
for name,value in [('key order',{'z':['x'], 'a':True}),('Unicode key',{'é':'字','a':'quote" and newline\n'}),('string numeric','1'),('empty',None)]:
 b=encode(value);vectors.append({'id':f'M04-SEM-{len(vectors)+1:02d}','input_kind':name,'input':value,'canonical_utf8_text':b.decode(),'sha256':'sha256:'+hashlib.sha256(b).hexdigest(),'status':'DOCUMENT_VECTOR_ONLY_PRODUCT_NOT_RUN'})
assert vectors[0]['sha256']==vectors[1]['sha256'];assert len({vectors[i]['sha256'] for i in [2,3,4]})==1;assert vectors[5]['sha256']==vectors[6]['sha256'];assert vectors[7]['sha256']==vectors[8]['sha256'];assert vectors[2]['sha256']!=vectors[11]['sha256']
policy={'status':'JOINT_PROPOSAL_PENDING_OWNER_NOT_ADOPTED','profile':'SGA-DESIGN-SEM-v1','domain':'DesignJsonV1 only; XML aggregate retains separate format-specific semantic profile, not interchangeable by subtree extraction','entry':'Only after adopted C1 guard has validated format/version/product_pass=false/duplicate/unknown/exact numeric representability; these vectors do not authorize unsupported input numbers.','exclusions':['/selection','/meta/updatedAt','/product_pass after false guard'],'projection':'Remove only exact paths in semantic projection; original canonical payload keeps compatibility fields. Never omit same key name at another path.','tagged_values':{'null':['z'],'bool':['b','boolean'],'string':['s','decoded string'],'number':['n','signed coefficient digits','base10 exponent decimal string'],'array':['a','ordered typed child list'],'object':['o','list of [decoded key,typed value] sorted key UTF8 bytes']},'decimal':'Exact base10 coefficient/exponent normalization: strip leading coefficient zeros, strip trailing zeros while increment exponent; zero canonical coefficient0/exponent0 including -0. No f64 proof or JS Number intermediate.','bytes':'UTF8 no BOM/newline, compact JSON separators, string escape only quote/backslash and controls: standard short escape b/f/n/r/t when defined, otherwise lowercase u00xx; other valid Unicode scalars encoded literally, no surrogate values. Outer array [profile,typed semantic projection].','digest':'sha256 of exact profile bytes, lowercase sha256:64hex. Raw file bytes/IO receipt digest remain separate.','migration':'Adoption would amend pending M03-H2-D2 semantic byte recipe and M04 DesignJsonV1 recipe together. Do not overwrite either original review packet/revision silently. Existing accepted S1 raw digest syntax/state APIs unchanged; no existing persisted semantic baseline auto-reinterpreted.','owner_choice':'Recommend this tagged shared profile to avoid serializer-specific number token spelling differences. Rejecting it requires another exact common byte profile before H2/M04 integration.','scope':'Only M04 planning and own card evidence; affected M03 exact packet frozen/read-only; no cross-module implementation authority inferred.'}
now=datetime.now(timezone.utc).isoformat();B=Path('docs/PROJECT-BOARD.html');bp=split_snapshot(B.read_text(encoding='utf-8'));before=json.loads(bp[1]);model={'module':'M04','affected_module':'M03-H2 pending proposal','status':'DESIGN_SEMANTIC_COMPATIBILITY_PROPOSAL_DELIVERED','at':now,'policy':policy,'vectors':vectors,'amendment_required':['M03-H2-D2','M04 R2 DesignJsonV1 semantic profile'],'frozen_inputs':frozen,'not_claimed':['approved shared schema','C1 implementation','product parser/hash integration PASS','M04/S1 changes','Skeleton'],'verification':{'document_vectors':len(vectors),'exact_decimal_equality_groups':'PASS document arithmetic only','source_unchanged':796,'product_tests':'NOT RUN','build':'NOT RUN','RED':'NOT RUN','native':'NOT RUN'},'next':'Include joint byte-profile choice in complete M04 S2 review; retain original M03 packet immutable until explicit coordinated revision/adoption. Continue exact R2 XML/resource/material fixtures.'}
put('module-spec.json',model);put('profile.json',policy);put('vectors.json',vectors)
body='<h1>M03-H2／M04 Design 語意指紋相容提案</h1><p>共同byte profile待採納；只M04 planning交付，不改M03已交付版本。</p><h2>精確規則</h2><pre>'+html.escape(json.dumps(policy,ensure_ascii=False,indent=2))+'</pre><h2>13個文件用精確bytes／hash vectors</h2><table>'+''.join('<tr><td>'+v['id']+'</td><td>'+html.escape(str(v['input']))+'</td><td>'+html.escape(v['canonical_utf8_text'])+'</td><td>'+v['sha256']+'</td></tr>' for v in vectors)+'</table><h2>界線</h2><p>1/1.00/1e0、1000/1E+03、0/-0等精確decimal分組已以文件算式檢查；不是產品codec測試或有效RED。C1輸入守門仍先行。原M03-H2待確認revision與M04原profile未變，796產品來源未變。需整包協調修訂與Owner採納，不自行換約或變更既有semantic baseline。</p>'
(O/'index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Design semantic compatibility proposal</title><style>body{max-width:1200px;margin:40px auto;font:16px system-ui;line-height:1.7}pre{white-space:pre-wrap}td{border:1px solid #ccc;padding:6px;word-break:break-all}</style>'+body+'<script type="application/json" id="module-spec">'+json.dumps(model,ensure_ascii=False).replace('</','<\\/')+'</script></html>',encoding='utf-8')
state=load(P/'current-state.json');state['design_semantic_compatibility']={'status':model['status'],'report':'design-semantic-compatibility/index.html'};state['next']=model['next'];(P/'current-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def mutate(s):
 t=next(t for t in s['tasks'] if t['id']=='PD-P1-M04-PREP-01');t['designSemanticCompatibility']={'status':model['status'],'report':str(O/'index.html').replace('\\','/'),'at':now};t['nextStep']=model['next'];t['notes']=t.get('notes','')+'\n['+now+'] M03-H2/M04 shared Design semantic byte-profile proposal with13 exact UTF8/hash vectors; original pending packets frozen, coordinated amendment/adoption required. No product/Skeleton. '+str(O/'index.html').replace('\\','/')
mutate_snapshot_file(B,mutate,lock_factory=FileLock)
ap=split_snapshot(B.read_text(encoding='utf-8'));after=json.loads(ap[1]);assert bp[0]==ap[0] and bp[2]==ap[2];assert {k:v for k,v in before.items() if k!='tasks'}=={k:v for k,v in after.items() if k!='tasks'};assert [t for t in before['tasks'] if t['id']!='PD-P1-M04-PREP-01']==[t for t in after['tasks'] if t['id']!='PD-P1-M04-PREP-01'];assert all(sha(p)==h for p,h in base['source_hashes'].items());assert all(sha(p)==h for p,h in frozen.items())
put('board-evidence.json',{'before':dict(Counter(t['zone'] for t in before['tasks'])),'after':dict(Counter(t['zone'] for t in after['tasks'])),'other_cards_root_shell_preserved':True});put('artifact-hashes.json',{p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='artifact-hashes.json'})
print(json.dumps({'status':model['status'],'vectors':len(vectors),'counts':dict(Counter(t['zone'] for t in after['tasks']))}))
