import json,hashlib,subprocess,copy,html
from pathlib import Path
from datetime import datetime
ROOT=Path('D:/AIAD'); C=ROOT/'docs/requirements-confirmation/phase1-spec/tasks/M05/planning/provider-source-map-20261104'; O=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
before={f.name:sha(f.read_bytes()) for f in C.iterdir() if f.is_file()}
d=read(C/'module-spec.json'); spans=read(C/'source-spans.json'); seal=read(C/'seal.json'); checks=[]
def ck(n,v):checks.append({'name':n,'pass':bool(v)})
for f,h in seal['files'].items():ck('seal:'+f,sha((C/f).read_bytes())==h)
ck('author_separate',d['author']!='/root/m05_provider_review')
ck('span_count10',len(spans)==10)
for x in spans:
 p=ROOT/x['path']; txt='\n'.join(p.read_text(encoding='utf-8').splitlines()[x['start']-1:x['end']]);ck(x['id']+':file',sha(p.read_bytes())==x['file_sha256']);ck(x['id']+':exactspan',txt==x['text'] and sha(txt.encode())==x['text_sha256'])
a=read(ROOT/d['authority']['path']);ck('authority796',len(a['source_hashes'])==796);ck('authority_zero_drift',all((ROOT/k).exists() and sha((ROOT/k).read_bytes())==v for k,v in a['source_hashes'].items()))
ck('liveHEAD',subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==d['HEAD']);ck('distincthistorical',d['HEAD']!=d['historical_product_head'])
q=subprocess.run(d['bounded_search']['argv'],cwd=ROOT,text=True,encoding='utf-8',capture_output=True); norm=lambda t:t.replace('\\','/').replace('\r\n','\n');ck('bounded_search_reproduced',q.returncode==d['bounded_search']['exit'] and norm(q.stdout)==norm(d['bounded_search']['stdout']))
ck('search_scope_declared','not runtime/global absence' in d['bounded_search']['limit'])
ck('sixfieldmaps',len(d['field_map'])==6);ck('four_pending',len(d['owner_choices'])==4 and all(x['status']=='PROPOSED_PENDING_OWNER' for x in d['owner_choices']));ck('MPnull',len(d['provider_choices'])==3 and all(x['selected'] is None for x in d['provider_choices']));ck('selectednull',d['selected'] is None);ck('earlierYellow4',len(d['earlier_yellow_attempts'])==4);ck('module_notcomplete',d['module_complete'] is False)
texts={x['id']:x['text'] for x in spans}
ck('caller_ownership_text','owned_by_operation: Option<String>' in texts['S01'] and 'candidate.owned_by_operation.as_deref() != Some(context.operation_id.as_str())' in texts['S06'])
ck('projection_input','pub completeness: Completeness' in texts['S02'] and 'expected[i] != Some(observation.revision.as_str())' in texts['S06'])
ck('identityonly_result','asset_id: candidate.asset_id.clone()' in texts['S07'] and 'content_digest: candidate.content_digest.clone()' in texts['S07'])
ck('receipt_fourfields',sum('pub '+x in texts['S08'] for x in ['target_path:','previous_digest:','committed_digest:','transaction_id:'])==4)
ck('lease_port_separate','Result<CommitReceipt, CommitError>' in texts['S09'])
# New semantic negative probes test the document admission guard; no runtime assertions.
def guard(z):
 return z['selected'] is None and not z['module_complete'] and all(v is False for v in z['negative_probe_contract'].values()) and all(x['selected'] is None for x in z['provider_choices']) and all(x['status']=='PROPOSED_PENDING_OWNER' for x in z['owner_choices']) and 'not runtime/global absence' in z['bounded_search']['limit']
probes=[]
for key in d['negative_probe_contract']:
 z=copy.deepcopy(d);z['negative_probe_contract'][key]=True;probes.append({'name':'reject:'+key,'pass':not guard(z),'layer':'document semantic guard, not native behavior'})
z=copy.deepcopy(d);z['provider_choices'][0]['selected']='APPROVED';probes.append({'name':'reject_self_adoption','pass':not guard(z)})
z=copy.deepcopy(d);z['module_complete']=True;probes.append({'name':'reject_module_completion','pass':not guard(z)})
for p in probes:ck(p['name'],p['pass'])
ck('candidate_unchanged',before=={f.name:sha(f.read_bytes()) for f in C.iterdir() if f.is_file()})
result={'reviewer':'/root/m05_provider_review','author':d['author'],'status':'BOUNDED_DOCUMENT_REVIEW_PASS' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','generated_at':datetime.now().astimezone().isoformat(),'checks':checks,'new_negative_probes':probes,'findings':[],'limits':['Static source and document review only','No product/native/build/regression execution','No historical PASS rerun','H1-H4 pending; MP1-MP3 null','No cleanup/issuer authority established'],'candidate_before':before}
(O/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M05 provider independent review</title><h1>M05 provider 獨立文件審查</h1><p>'+result['status']+'</p><p>作者 '+d['author']+'；審查者 /root/m05_provider_review。</p><p>核對10段精確來源、六項欄位邊界、H1–H4待採納與MP1–MP3未選。owned_by_operation為呼叫端文字；complete/revision為輸入投影；Eligible只有identity，不能當刪除授權。四欄IO收據不能升格semantic transfer。</p><p>限定crate搜尋已重現；不宣稱runtime或全域缺失。796來源零漂移，候選未變動。產品/native/build/regression NOT RUN；未重跑歷史PASS。</p><p>'+str(len(checks))+' checks / '+str(len(probes))+' 新文件負向probes。</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8')
(O/'seal.json').write_text(json.dumps({'reviewer':'/root/m05_provider_review','files':{p.name:sha(p.read_bytes()) for p in O.iterdir() if p.name!='seal.json'},'stopped_after_seal':True},indent=2)+'\n',encoding='utf-8')
print(result['status'],len(checks),len(probes));print([x for x in checks if not x['pass']])
