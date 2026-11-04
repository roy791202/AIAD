import sys,json,hashlib,subprocess,copy,html,importlib.util
sys.dont_write_bytecode=True
from pathlib import Path
P=Path(__file__).resolve().parent;R=Path.cwd();B=R/'docs/requirements-confirmation/phase1-spec/tasks/M07/planning';C=B/'provider-source-map-correction-20261104';O=B/'provider-source-map-20261104'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
checks=[]
def ck(n,v):checks.append({'name':n,'pass':bool(v)})
before={}
for pack in [O,C]:
 se=read(pack/'seal.json');before[pack.name]={f:sha(pack/f) for f in se['files']}
 for f,h in se['files'].items():ck(pack.name+':'+f,sha(pack/f)==h)
rows=read(C/'source-spans.json');spec=importlib.util.spec_from_file_location('candidate_validator',C/'validate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ck('candidate_validator_actual_corrected_rows',m.validate(rows));ck('ten_rows',len(rows)==10)
for x in rows:
 ls=(R/x['path']).read_text(encoding='utf-8').splitlines();ck(x['id']+':exact_range',1<=x['start']<=x['end']<=len(ls) and bool(x['text'].strip()) and '\n'.join(ls[x['start']-1:x['end']])==x['text']);ck(x['id']+':source_hash',sha(R/x['path'])==x['sha256']);ck(x['id']+':anchors',all(a in x['text'] for a in m.ANCHORS[x['id']]))
by={x['id']:x for x in rows}
for id,bounds in [('RS04',(115,145)),('RS05',(157,174)),('RS06',(212,216))]:ck(id+':corrected_bounds',(by[id]['start'],by[id]['end'])==bounds)
probes=[]
def reject(n,rs):
 try:m.validate(rs);ok=False
 except (ValueError,KeyError,TypeError,OSError):ok=True
 probes.append({'name':n,'rejected':ok})
for n,fn in [('empty_text',lambda a:a[0].update(text='')),('out_of_range',lambda a:a[0].update(end=9999)),('reversed_bounds',lambda a:a[0].update(start=12,end=1)),('source_hash',lambda a:a[0].update(sha256='0'*64)),('literal_text',lambda a:a[0].update(text=a[0]['text']+'x')),('anchor_list_missing',lambda a:a[0].pop('required_anchors')),('invented_anchor',lambda a:a[0].update(required_anchors=['unrelated'])),('missing_row',lambda a:a.pop()),('duplicate_id',lambda a:a[1].update(id=a[0]['id']))]:
 a=copy.deepcopy(rows);fn(a);reject(n,a)
old=read(O/'source-spans.json')
for ident in ['RS05','RS06']:
 a=copy.deepcopy(rows);i=next(i for i,r in enumerate(a) if r['id']==ident);bad=next(r for r in old if r['id']==ident);bad['required_anchors']=a[i]['required_anchors'];a[i]=bad;reject('original_defective_'+ident,a)
ck('all_fresh_rejection_probes',all(p['rejected'] for p in probes))
d=read(C/'module-spec.json');ck('MP1_to4_pending',len(d['bridges'])==4 and all(x['selected'] is None for x in d['bridges']));ck('six_earlier_yellow_attempts',len(d['earlier_yellow_attempts'])==6);ck('no_adoption_or_product_pass',d['selected'] is None and d['product_pass'] is False);ck('RA_options_pending',all('PENDING' in x['status'] for x in d['proposal_binding']['pointers']['/owner_options']))
a=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')['source_hashes'];ck('authority796_zero_drift',len(a)==796 and all((R/k).exists() and sha(R/k)==v for k,v in a.items()))
for pack in [O,C]:ck(pack.name+':unchanged',before[pack.name]=={f:sha(pack/f) for f in read(pack/'seal.json')['files']})
result={'status':'PASS_BOUNDED_M07_SOURCE_BINDING_CORRECTION' if all(x['pass'] for x in checks) else 'CHANGES_REQUESTED','reviewer':'/root/m07_provider_review','author':d['author'],'checks':checks,'probes':probes,'findings':[],'closed':['M07-PM-R1','M07-PM-R2','RS04 threshold binding'],'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'limits':['New static binding correction review only; no historical PASS rerun','Original erroneous report preserved, corrected sibling is active evidence','No protocol or ordinal adoption','Product/native/build/regression NOT RUN']}
(P/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');(P/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>M07 correction independent review</title><h1>'+result['status']+'</h1><p>R1/R2 corrected and RS04 threshold source included. Source-level evidence only; no product/native acceptance.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre>',encoding='utf-8');(P/'seal.json').write_text(json.dumps({'status':'SEALED','reviewer':result['reviewer'],'files':{f.name:sha(f) for f in P.iterdir() if f.is_file() and f.name!='seal.json'}},indent=2),encoding='utf-8');print(result['status'],len(checks),len(probes))
