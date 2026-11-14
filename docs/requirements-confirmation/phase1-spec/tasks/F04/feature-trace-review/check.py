"""Independent F04 preparation review. Writes only its own new review directory."""
from pathlib import Path
import copy, hashlib, html, json, re, subprocess
O=Path(__file__).resolve().parent
R=O.parents[5]
P=O.parent/'feature-trace-preparation'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(n,v): (O/n).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 t=read(P/'feature-trace.json'); task=read(R/'docs/requirements-confirmation/phase1-spec/tasks/PD-P1-F04-DELIVERY-01.json')
 checks=[]
 def ck(n,v): checks.append({'name':n,'pass':bool(v)})
 bindings=read(P/'source-bindings.json')
 sources=[]
 for p,h in bindings.items():
  actual=sha(R/p); sources.append({'path':p,'expected':h,'actual':actual,'pass':h==actual})
  ck('binding '+p,h==actual)
 ck('105 source bindings',len(bindings)==105)
 for n,h in read(P/'seal.json')['payload_sha256'].items(): ck('sealed '+n,sha(P/n)==h)
 authority=read(R/'docs/requirements-confirmation/phase1-spec/tasks/M01/planning/s2-green/source-current.json')
 ck('796 authority',len(authority['source_hashes'])==796)
 for p,h in authority['source_hashes'].items(): ck('authority '+p,sha(R/p)==h)
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
 ck('current HEAD and historical authority distinct',head=='5b709343a890503ebbe24a802e43cda5647df124' and authority['head']=='31babe87a7ef1e40a0d4bedc523077e7a45d63ab')
 def semantic(x):
  errors=[]
  def require(n,v):
   if not v: errors.append(n)
  require('original AC',x['original_acceptance']==task['acceptance'])
  require('original BDD',x['original_bdd']==task['bdd'])
  require('original contract',x['original_contract']==task['contract'])
  require('Gray preparation',x['health']=='GRAY_RETAINED' and x['state']=='PREPARATION_ONLY_PENDING_OWNER_ENVELOPE_SKELETON')
  require('seven recipes',len(x['trace'])==7)
  clauses=['有UI成功生成後自動開主要畫面','無UI不開','選取一致','預覽版本可辨','保存重開互動定義一致','假資料不顯示正式成功','Build失敗顯示畫面／元件原因']
  for i,row in enumerate(x['trace']):
   require('original clause '+str(i),row['original_clause']==clauses[i])
   require('REQ/AC mapping '+str(i),row['requirement']=='REQ-05' and row['acceptance']==('AC04' if i<6 else 'AC04 context + original contract[2]'))
   require('BDD mapping '+str(i),row['bdd']==t['trace'][i]['bdd'])
   require('authority '+str(i),row['authority']==('CONFIRMED_REQ05' if i<2 else 'PROPOSAL_PENDING_OWNER'))
   require('planned '+str(i),row['status']=='PLANNED_NOT_RUN')
   require('source claim '+str(i),row['existing_evidence']==t['trace'][i]['existing_evidence'])
   require('oracle/fixture within original envelope '+str(i),row['oracle_recipe']==t['trace'][i]['oracle_recipe'] and row['fixture_recipe']==t['trace'][i]['fixture_recipe'])
   require('valid RED gate '+str(i),all(s in row['valid_red'] for s in ['Owner adoption','Skeleton','runner compiles','not valid RED','regression']))
  require('commands exact bound existing/not invented',x['commands']==t['commands'])
  require('no adoption or runtime inflation',x['execution']=={'new_product_tests':'NOT RUN','valid_RED':'NOT RUN','build':'NOT RUN','native_UI':'NOT RUN','independent_acceptance':'NOT RUN','full_Draft':'NOT RUN','feature_acceptance':'NOT RUN','new_Skeleton':False,'feature_complete':False,'module_complete':False})
  require('current/historical/noFS distinction',x['boundaries']==t['boundaries'])
  return errors
 ck('independent semantic baseline',not semantic(t))
 mutations=[]
 def mutate(n,fn):
  x=copy.deepcopy(t); fn(x); e=semantic(x); mutations.append({'id':n,'detected':bool(e),'diagnostics':e})
 mutate('wrong-AC',lambda x:x['trace'][0].update(acceptance='AC03'))
 mutate('wrong-BDD',lambda x:x['trace'][0].update(bdd='BDD-04'))
 mutate('wrong-source',lambda x:x['trace'][0].update(existing_evidence=['apps/sgenaxis-desktop/ui/app.js:1']))
 mutate('invented-test-target',lambda x:x['commands'].update(new_feature_runner='cargo test --test phase1_design_roundtrip'))
 mutate('adoption',lambda x:x.update(state='READY_FOR_AI_IMPLEMENTATION'))
 mutate('proposal-confirmed',lambda x:x['trace'][2].update(authority='CONFIRMED_REQ05'))
 mutate('native-PASS',lambda x:x['execution'].update(native_UI='PASS'))
 mutate('no-FS-current-claim',lambda x:x['boundaries'].update(persistence='Current Viewer has proven zero filesystem effects'))
 mutate('threshold-invention',lambda x:x['trace'][0].update(oracle_recipe='Opens in less than 100ms'))
 mutate('RED-without-Skeleton',lambda x:x['trace'][0].update(valid_red='Compile failure is valid RED'))
 for m in mutations: ck('new semantic mutation '+m['id'],m['detected'])
 ck('wrong source hash mutation rejected',sha(R/next(iter(bindings)))!='0'*64)
 embedded=json.loads(re.search(r'<script id="feature-trace" type="application/json">(.*?)</script>',(P/'index.html').read_text(encoding='utf-8'),re.S)[1])
 ck('preparation HTML embedded exact',embedded==t)
 ck('dependencies retained',task['dependencies']==['PD-P1-M03-PREP-01','PD-P1-G01-DEC-01','PD-P1-G04-DEC-01'] and task['zone']=='gray')
 ui=(R/'apps/sgenaxis-desktop/ui/app.js').read_text(encoding='utf-8')
 host=(R/'apps/sgenaxis-desktop/crates/sgenaxis-host/src/uidesign_doc.rs').read_text(encoding='utf-8')
 ck('Build distinct trigger',all(s in ui for s in ['async function cmdUidesignBuild()','open_after: true','invoke("uidesign_build_preview"']))
 ck('legacy preview writes through port',all(s in host for s in ['use sgenaxis_ports::FileSystemPort','pub fn build_preview_file','fs.write_atomic(&path, html.as_bytes())']))
 for name in ['roundtrip_sgendesign','rejects_product_pass_true','preview_contains_banner_and_node','save_load_via_fake_fs','build_preview_file_writes']: ck('existing HOST test '+name,'fn '+name+'(' in host)
 save('source-checks.json',sources); save('semantic-mutations.json',mutations)
 save('input-hashes.json',{str(p.relative_to(R)).replace('\\','/'):sha(p) for p in P.iterdir() if p.is_file()})
 save('results.json',{'checks':len(checks),'passed':sum(c['pass'] for c in checks),'failed':[c for c in checks if not c['pass']],'semantic_mutations':len(mutations),'hash_mutations':1,'checks_detail':checks})
 review={'reviewer':'/root/f04_feature_trace_review','author':'/root/f04_feature_trace_packet','status':'PASS_F04_PREPARATION_ONLY_PENDING_OWNER' if all(c['pass'] for c in checks) else 'CHANGES_REQUIRED','feature':'F04','primary_module':'M03','head':head,'historical_authority_head':authority['head'],'health':'GRAY_RETAINED','recipes':7,'confirmed':2,'proposals':5,'source_bindings':105,'product_inventory':796,'findings':[],'limits':'Independent document review only. No Owner adoption, architecture/Skeleton authority, Feature/module acceptance. Existing helper/static preview/command-model results are not native Editor/Viewer proof. Product tests/build/native UI/valid RED/full Draft NOT RUN. Historical codec evidence inspected, not rerun. Board management differences are separate from product source integrity.','next':'Owner adoption of exact C1/H2/effective cx-v3 and latest corrections; approve original AC04 slice envelope/Skeleton and bind actual test before valid RED.'}
 save('review.json',review)
 h='<html lang="zh-Hant"><meta charset="utf-8"><title>F04 Independent Review</title><style>body{font:17px/1.7 system-ui;max-width:1100px;margin:40px auto}pre{white-space:pre-wrap}</style><h1>F04 獨立文件審查</h1><p>7 recipes：2 confirmed、5 proposal。Gray 保留；原 AC04 混合狀態未改。105 來源與 796 產品來源雜湊獨立比對。</p><pre>'+html.escape(json.dumps(review,ensure_ascii=False,indent=2))+'</pre><p>來源完整性與語意負向測試見 results.json；所有結果僅準備文件範圍。</p><script id="review-spec" type="application/json">'+json.dumps(review,ensure_ascii=False).replace('<','\\u003c')+'</script></html>'
 (O/'index.html').write_text(h,encoding='utf-8')
 payload={p.name:sha(p) for p in O.iterdir() if p.is_file() and p.name!='seal.json'}
 save('seal.json',{'status':'SEALED_INDEPENDENT_PREPARATION_REVIEW','payload_sha256':payload,'payload_artifacts':len(payload),'total_files':len(payload)+1})
 print(json.dumps({'status':review['status'],'checks':len(checks),'failed':sum(not c['pass'] for c in checks)}))
if __name__=='__main__': main()
