"""Materialize approved codec vectors; fixtures never call the production codec."""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
PACKET = Path(__file__).resolve().parent.parent / 's2-exact-design'
BASE = json.loads((PACKET / 'fixtures.json').read_text(encoding='utf-8'))['defaults']['wire_definition']
TARGET = ROOT / 'apps/sgenaxis-desktop/crates/sgenaxis-host/tests/phase1_project_definition_codec.rs'

def q(s):
    return json.dumps(s, ensure_ascii=False).replace('\\u0000', '\\0')

def owned(s):
    return q(s) + '.into()'

def vec(xs, f=owned):
    return 'vec![' + ','.join(f(x) for x in xs) + ']'

def state(v):
    return 'FieldState::' + {'unresolved': 'Unresolved', 'tentative': 'Tentative', 'confirmed': 'Confirmed'}[v['state']] + ('' if v['state'] == 'unresolved' else '(' + owned(v['value']) + ')')

def extension(v):
    if v is None: return 'ExtensionValue::Null'
    if isinstance(v, bool): return 'ExtensionValue::Bool(' + str(v).lower() + ')'
    if isinstance(v, str): return 'ExtensionValue::String(' + owned(v) + ')'
    if isinstance(v, list): return 'ExtensionValue::Array(' + vec(v, extension) + ')'
    if isinstance(v, dict): return 'ExtensionValue::Object([' + ','.join('(' + owned(k) + ',' + extension(x) + ')' for k, x in sorted(v.items())) + '].into_iter().collect())'
    return 'ExtensionValue::Number(' + owned(str(v)) + ')'

def domain(w):
    targets = []
    for t in w['deliveryTargets']:
        fields = ['id:' + owned(t['id'])]
        for wire, rust in [('form','form'),('platform','platform'),('host','host'),('hostVersion','host_version'),('language','language'),('framework','framework')]:
            fields.append(rust + ':' + state(t[wire]))
        fields += ['toolchain:' + vec(t['toolchain']), 'has_ui:' + ('None' if t['hasUi'] is None else 'Some(' + str(t['hasUi']).lower() + ')')]
        targets.append('DeliveryTarget{' + ','.join(fields) + '}')
    reqs = ['DefinitionRequirement{id:' + owned(r['id']) + ',intent:' + owned(r['intent']) + ',acceptance:' + vec(r['acceptance']) + ',state:RequirementState::' + r['state'].title() + '}' for r in w['requirements']]
    t = w['template']
    template = 'None' if t is None else 'Some(TemplateReference{id:' + owned(t['id']) + ',version:' + owned(t['version']) + ',source_digest:' + owned(t['sourceDigest']) + '})'
    return ('ProjectDefinition{project_uuid:PersistentProjectId::candidate(' + q(w['projectUuid']) + '),definition_revision:DefinitionRevision(' + w['definitionRevision'] + '),mode:DefinitionMode::' + w['mode'].title() + ',approval_refs:' + vec(w['approvalRefs']) + ',legacy_root_keys:' + vec(w['legacyRootKeys']) + ',draft:DefinitionDraft{name:' + owned(w['name']) + ',purpose:' + owned(w['purpose']) + ',last_saved_step:WizardStep::' + ''.join(x.title() for x in w['lastSavedStep'].split('_')) + ',delivery_targets:vec![' + ','.join(targets) + '],topology:' + state(w['topology']) + ',requirements:vec![' + ','.join(reqs) + '],preference_source:PreferenceSource::' + {'skip':'Skip','preset':'Preset','imported-copy':'ImportedCopy'}[w['preferenceSource']] + ',template:' + template + ',open_decisions:' + vec(w['openDecisions']) + ',extensions:match ' + extension(w['extensions']) + '{ExtensionValue::Object(o)=>o,_=>unreachable!()}}}')

def target():
    t = {k: {'state':'unresolved','value':None} for k in ['form','platform','host','hostVersion','language','framework']}
    t.update(id=BASE['projectUuid'], toolchain=[], hasUi=None)
    return t

parts = ['''//! Approved M01-S2 codec behavior, isolated from filesystem and production parsing.
use sgenaxis_host::project_definition::*;
use sgenaxis_work::project_definition::*;
fn base() -> ProjectDefinition { BASE_DOMAIN }
fn wire() -> serde_json::Value { serde_json::from_str(BASE_WIRE).expect("fixture JSON") }
fn raw(v: &serde_json::Value) -> Vec<u8> { serde_json::to_vec(v).expect("fixture serialization") }
fn invalid(pointer: &str, code: CodecFieldCode) -> DefinitionStoreError {
    DefinitionStoreError::Codec { issue: CodecIssue::InvalidField { pointer:pointer.into(), code } }
}
fn check_decode(bytes: &[u8], expected: DefinitionStoreError) {
    assert_eq!(decode_definition(bytes), Err(expected), "product result must match the exact approved error");
}
fn roundtrip(expected: ProjectDefinition, bytes: &[u8]) {
    let before = expected.clone();
    assert_eq!(decode_definition(bytes), Ok(expected.clone()), "decode exact independent domain oracle");
    let encoded = encode_definition(&expected);
    assert!(encoded.is_ok(), "encoding valid domain: {encoded:?}");
    let encoded = encoded.unwrap();
    assert_eq!(decode_definition(&encoded), Ok(before.clone()));
    assert_eq!(encode_definition(&before), Ok(encoded.clone()), "deterministic");
    assert_eq!(expected, before, "input untouched");
    assert!(encoded.ends_with(b"\\n"));
    assert!(!encoded.starts_with(&[239,187,191]));
}
'''.replace('BASE_DOMAIN', domain(BASE)).replace('BASE_WIRE', q(json.dumps(BASE, ensure_ascii=False)))]
manifest = []
def test(n, suffix, body):
    name = f't{n:03}_{suffix}'
    parts.append(f'\n#[test]\nfn {name}() {{\n{body}\n}}\n')
    manifest.append({'test':name, 'plan':f'M01-S2-T{n:03}', 'target':'phase1_project_definition_codec'})

for step in ['basics','delivery','topology','requirements','technology_ui','preview']:
    w=copy.deepcopy(BASE); w['lastSavedStep']=step
    test(1, step, 'roundtrip('+domain(w)+','+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
for n,mode in [(2,'draft'),(3,'defined')]:
    w=copy.deepcopy(BASE);w['mode']=mode
    test(n,mode,'let d='+domain(w)+'; assert!(!missing_generation_requirements(&d).is_empty()); roundtrip(d,'+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
for n,r in [(4,'0'),(5,str(2**64-1))]:
    w=copy.deepcopy(BASE);w['definitionRevision']=r
    test(n,'revision','roundtrip('+domain(w)+','+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
for n,r in enumerate(['01','+1','-1',str(2**64),1],6):
    test(n,'invalid_revision','let mut v=wire(); v["definitionRevision"]=serde_json::json!('+q(r) if isinstance(r,str) else 'let mut v=wire(); v["definitionRevision"]=serde_json::json!(1')
    # Complete expression separately to keep numeric-vs-string fixture distinction.
    parts[-1]=parts[-1].replace('\n}\n',');check_decode(&raw(&v),invalid("/definitionRevision",CodecFieldCode::InvalidRevision));\n}\n')
for n,(st,val) in enumerate([('unresolved',None),('tentative',''),('confirmed','')],11):
    w=copy.deepcopy(BASE);w['topology']={'state':st,'value':val}
    test(n,'field_state','roundtrip('+domain(w)+','+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
for n,(st,val) in enumerate([('unresolved','data'),('tentative',None),('confirmed',None)],14):
    test(n,'inconsistent','let mut v=wire();v["topology"]=serde_json::json!('+json.dumps({'state':st,'value':val})+');check_decode(&raw(&v),invalid("/topology",CodecFieldCode::InconsistentFieldState));')
for suffix,ui in [('null',None),('false',False)]:
    w=copy.deepcopy(BASE);t=target();t['hasUi']=ui;w['deliveryTargets']=[t]
    test(17,suffix,'roundtrip('+domain(w)+','+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
w=copy.deepcopy(BASE);w['approvalRefs']=['approval-data-only'];w['template']={'id':'base','version':'1','sourceDigest':'sha256:'+'a'*64};w['legacyRootKeys']=['opaque-id']
test(18,'references','roundtrip('+domain(w)+','+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
for n,token in enumerate(['-0','1.00','1E+03','18446744073709551616','0.123456789012345678901234567890'],19):
    wire=json.dumps(BASE,ensure_ascii=False).replace('"extensions": {}','"extensions": {"number":'+token+'}')
    test(n,'number','let mut d=base();d.draft.extensions.insert("number".into(),ExtensionValue::Number('+owned(token)+'));roundtrip(d.clone(),'+q(wire)+'.as_bytes());let b=encode_definition(&d).unwrap();assert!(String::from_utf8(b).unwrap().contains('+q(token)+'));')
w=copy.deepcopy(BASE);w['extensions']={'$serde_json::private::Number':'ordinary','z':[True,None,{'x':'維持順序'}],'a':{'y':False}}
test(24,'tree','roundtrip('+domain(w)+','+q(json.dumps(w,ensure_ascii=False))+'.as_bytes());')
for n,loc,ptr in [(25,'root','/futureRoot'),(26,'target','/deliveryTargets/0/future'),(27,'template','/template/future')]:
    w=copy.deepcopy(BASE)
    if loc=='root':w['futureRoot']=True
    elif loc=='target':t=target();t['future']=True;w['deliveryTargets']=[t]
    else:w['template']={'id':'base','version':'1','sourceDigest':'sha256:'+'a'*64,'future':True}
    test(n,loc,'check_decode('+q(json.dumps(w,ensure_ascii=False))+'.as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::UnknownField{pointer:'+owned(ptr)+'}});')
schema=json.loads((PACKET/'schema.json').read_text(encoding='utf-8'))
w=copy.deepcopy(BASE);w['deliveryTargets']=[target()];w['requirements']=[{'id':'r','intent':'','acceptance':[],'state':'unresolved'}];w['template']={'id':'base','version':'1','sourceDigest':'sha256:'+'a'*64}
def required(s,v,path=''):
    if s.get('type')=='array':
        if v:yield from required(s['items'],v[0],path+'/0')
    elif isinstance(v,dict):
        for k in s.get('required',[]): yield path+'/'+k
        for k,sub in s.get('properties',{}).items():
            if k in v:yield from required(sub,v[k],path+'/'+k)
for i,ptr in enumerate(required(schema,w)):
    mut=copy.deepcopy(w);loc=mut;segs=ptr.strip('/').split('/')
    for seg in segs[:-1]:loc=loc[int(seg)] if isinstance(loc,list) else loc[seg]
    del loc[segs[-1]]
    test(28,str(i),'check_decode('+q(json.dumps(mut,ensure_ascii=False))+'.as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::MissingField{pointer:'+owned(ptr)+'}});')
test(29,'utf8','let mut b=vec![255];b.extend(raw(&wire()));check_decode(&b,DefinitionStoreError::Codec{issue:CodecIssue::InvalidUtf8});')
test(30,'bom','let mut b=vec![239,187,191];b.extend(raw(&wire()));check_decode(&b,DefinitionStoreError::Codec{issue:CodecIssue::BomNotAllowed});')
test(31,'grammar','let mut b=raw(&wire());b.pop();assert!(matches!(decode_definition(&b),Err(DefinitionStoreError::Codec{issue:CodecIssue::InvalidJson{..}})),"exact grammar classification");')
for n,rawtext,ptr in [(32,json.dumps(BASE,ensure_ascii=False)[:-1]+',"name":"second"}','/name'),(33,json.dumps(BASE,ensure_ascii=False).replace('"extensions": {}','"extensions":{"plugin":1,"plugin":2}'),'/extensions/plugin')]:
    test(n,'duplicate','check_decode('+q(rawtext)+'.as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::DuplicateKey{pointer:'+owned(ptr)+'}});')
for n,mut,sch,ver in [(34,{'schemaVersion':2},BASE['schema'],'2'),(35,{'schema':'other.project-definition'},'other.project-definition','1')]:
    w=copy.deepcopy(BASE);w.update(mut)
    test(n,'schema','check_decode('+q(json.dumps(w,ensure_ascii=False))+'.as_bytes(),DefinitionStoreError::UnsupportedSchema{schema:'+owned(sch)+',version:'+owned(ver)+'});')
w=copy.deepcopy(BASE);w['schemaVersion']=2;w['futureRoot']=True
test(36,'version_unknown','check_decode('+q(json.dumps(w,ensure_ascii=False))+'.as_bytes(),DefinitionStoreError::UnsupportedSchema{schema:'+owned(BASE['schema'])+',version:"2".into()});')
test(36,'version_duplicate','check_decode('+q(json.dumps(w,ensure_ascii=False)[:-1]+',"name":"second"}')+'.as_bytes(),DefinitionStoreError::Codec{issue:CodecIssue::DuplicateKey{pointer:"/name".into()}});')
parts.append('''
fn nodes(v:&serde_json::Value)->usize {1+match v {serde_json::Value::Object(o)=>o.values().map(nodes).sum(),serde_json::Value::Array(a)=>a.iter().map(nodes).sum(),_=>0}}
fn depth(v:&serde_json::Value)->usize {match v {serde_json::Value::Object(o)=>o.values().map(depth).max().map_or(0,|x|x+1),serde_json::Value::Array(a)=>a.iter().map(depth).max().map_or(0,|x|x+1),_=>0}}
fn resource(b:&[u8], r:CodecResource) {assert!(matches!(decode_definition(b),Err(DefinitionStoreError::Codec{issue:CodecIssue::ResourceLimit{resource,..}}) if resource==r),"resource guard, not parser/environment failure");}
''')
for size in [1,120,121]:
    test(37,str(size),f'let mut v=wire();v["name"]=serde_json::json!("設".repeat({size}));let b=raw(&v);'+('assert!(decode_definition(&b).is_ok());' if size<=120 else 'check_decode(&b,DefinitionStoreError::InvalidInput{field:"name".into(),code:DefinitionInputCode::DomainInvalid});'))
for size in [16777215,16777216,16777217]:
    test(38,str(size),f'let mut b=raw(&wire());b.resize({size},b\' \');assert_eq!(b.len(),{size});assert!(serde_json::from_slice::<serde_json::Value>(&b).is_ok());'+('assert!(decode_definition(&b).is_ok());' if size<=16777216 else f'check_decode(&b,DefinitionStoreError::Codec{{issue:CodecIssue::InputTooLarge{{actual_bytes:{size},limit_bytes:16777216}}}});'))
for size in [63,64,65,129]:
    # Unvalidated raw nesting avoids serde's default recursion limit at 128.
    test(39,str(size),f'let b=String::from_utf8(raw(&wire())).unwrap().replace("\\"extensions\\":{{}}",&format!("{{}}", ""));let _=b; let mut v=wire();v["extensions"]=serde_json::json!({{"nest":"MARKER"}});let raw=String::from_utf8(raw(&v)).unwrap().replace("\\"MARKER\\"",&format!("{{}}{{}}{{}}","[".repeat({size}-2),"null","]".repeat({size}-2)));'+('assert!(decode_definition(raw.as_bytes()).is_ok());' if size<=64 else 'resource(raw.as_bytes(),CodecResource::Depth);'))
    # Drop an unnecessary draft construction so the source remains straightforward.
    parts[-1]=parts[-1].replace('let b=String::from_utf8(raw(&wire())).unwrap().replace("\\"extensions\\":{}",&format!("{}", ""));let _=b; ','')
for size in [99999,100000,100001]:
    test(40,str(size),f'let mut v=wire();v["extensions"]=serde_json::json!({{"nodes":[]}});let extra={size}-nodes(&v);v["extensions"]["nodes"]=serde_json::json!(vec![serde_json::Value::Null;extra]);assert_eq!(nodes(&v),{size});assert!(depth(&v)<64);let b=raw(&v);'+('assert!(decode_definition(&b).is_ok());' if size<=100000 else 'resource(&b,CodecResource::Nodes);'))
for size in [1048575,1048576,1048577]:
    test(41,str(size),f'let mut v=wire();let text=format!("{{}}x","界".repeat(({size}-1)/3));let text=format!("{{}}{{}}",text,"x".repeat({size}-text.len()));assert_eq!(text.len(),{size});v["purpose"]=serde_json::json!(text);let b=raw(&v);'+('assert!(decode_definition(&b).is_ok());' if size<=1048576 else 'resource(&b,CodecResource::StringBytes);'))
for size in [4095,4096,4097]:
    test(42,str(size),f'let mut v=wire();v["extensions"]=serde_json::json!({{"number":"MARKER"}});let token="7".repeat({size});assert_eq!(token.len(),{size});assert!(token.bytes().all(|x|x==b\'7\'));let b=String::from_utf8(raw(&v)).unwrap().replace("\\"MARKER\\"",&token);'+('assert!(decode_definition(b.as_bytes()).is_ok());' if size<=4096 else 'resource(b.as_bytes(),CodecResource::NumberBytes);'))
# A schema-ordered reference pretty fixture, not production output, sizes output guards.
for size in [16777216,16777217]:
    w=copy.deepcopy(BASE);w['extensions']={f'k{i:02}':'' for i in range(16)}
    overhead=len((json.dumps(w,ensure_ascii=False,indent=2)+'\n').encode())
    full=(size-overhead)//1048576;last=(size-overhead)%1048576
    body='let mut d=base();'
    for i in range(16):
        count=1048576 if i<full else last if i==full else 0
        body+=f'd.draft.extensions.insert("k{i:02}".into(),ExtensionValue::String("x".repeat({count})));'
    body+=f'let result=encode_definition(&d);'+(f'assert_eq!(result.as_ref().map(Vec::len),Ok({size}));' if size==16777216 else f'assert_eq!(result,Err(DefinitionStoreError::Codec{{issue:CodecIssue::OutputTooLarge{{actual_bytes:{size},limit_bytes:16777216}}}}));')
    test(43,str(size),body)
mutations=[(44,'d.draft.name="   ".into();','DefinitionStoreError::InvalidInput{field:"name".into(),code:DefinitionInputCode::DomainInvalid}'),(45,'d.project_uuid=PersistentProjectId::candidate("bad");','invalid("/projectUuid",CodecFieldCode::InvalidUuid)'),(46,'let t='+domain(dict(BASE,deliveryTargets=[target()]))+'.draft.delivery_targets.remove(0);d.draft.delivery_targets=vec![t.clone(),t];','DefinitionStoreError::InvalidInput{field:"deliveryTargets[1].id".into(),code:DefinitionInputCode::DomainInvalid}'),(47,'d.draft.requirements=vec![DefinitionRequirement{id:" ".into(),intent:"".into(),acceptance:vec![],state:RequirementState::Unresolved}];','DefinitionStoreError::InvalidInput{field:"requirements[0].id".into(),code:DefinitionInputCode::DomainInvalid}'),(48,'d.draft.template=Some(TemplateReference{id:"base".into(),version:"1".into(),source_digest:"sha256:bad".into()});','invalid("/template/sourceDigest",CodecFieldCode::InvalidDigest)'),(49,'d.legacy_root_keys=vec!["C:\\\\private\\\\old-root".into()];','invalid("/legacyRootKeys/0",CodecFieldCode::InvalidPortableAlias)'),(50,'d.draft.extensions.insert("number".into(),ExtensionValue::Number("01".into()));','invalid("/extensions/number",CodecFieldCode::InvalidNumberToken)')]
for n,mutation,expected in mutations:test(n,'encode_reject','let mut d=base();'+mutation+'let before=d.clone();assert_eq!(encode_definition(&d),Err('+expected+'));assert_eq!(d,before);')
parts.append('''
#[test] fn fixture_health() {
 let v=wire();assert_eq!(v["schema"],"eluslot.project-definition");assert_eq!(v["definitionRevision"],"0");
 assert_eq!(validate_definition(&base().draft),Ok(()));assert!(nodes(&v)<100000);assert!(depth(&v)<64);
}
''')
TARGET.write_text(''.join(parts),encoding='utf-8')
(Path(__file__).parent/'codec-test-map.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(f'Generated {len(manifest)} codec behavior cases plus fixture health: {TARGET}')

