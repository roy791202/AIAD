import datetime, hashlib, html, json, pathlib
OUT=pathlib.Path(__file__).parent
ROOT=OUT.parents[6]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
# Preserve all prior sealed observations verbatim. Execute only the read-only oracle
# definitions, stopping before the old runner's writes and result generation.
source=(OUT/'review.py').read_text(encoding='utf-8-sig')
prefix=source.split('try: oracle(d);')[0]
prefix=prefix.replace("assert x['board_read_time_record']==byid[x['id']]", "assert all(x['board_read_time_record'].get(k)==byid[x['id']].get(k) for k in set(x['board_read_time_record'])|set(byid[x['id']]) if not (x['id']=='PD-P1-M01-PREP-01' and k in ('notes','updatedAt')))")
ns={'__file__':str(OUT/'review.py')}
exec(compile(prefix,'corrected-read-only-oracle','exec'),ns)
oracle=ns['oracle']; d=ns['d']; copy=ns['copy']
oracle(d)
mutation_source=source.split('mutations=')[1].split('\nprobes=[]')[0]
exec('mutations='+mutation_source,ns)
probes=[]
for name, mutate in ns['mutations']:
    v=copy.deepcopy(d); mutate(v)
    try: oracle(v); rejected=False
    except Exception: rejected=True
    probes.append({'name':name,'rejected':rejected,'baseline_positive_passed_before_mutation':True})
assert all(p['rejected'] for p in probes)
board=ns['board']; bi=ns['byid']
diff=[]
for card in d['cards']:
    old=card['board_read_time_record']; new=bi[card['id']]
    for k in set(old)|set(new):
        if old.get(k)!=new.get(k): diff.append({'id':card['id'],'field':k})
assert diff and all(x['id']=='PD-P1-M01-PREP-01' and x['field'] in ('notes','updatedAt') for x in diff)
old=next(x for x in d['cards'] if x['id']=='PD-P1-M01-PREP-01')['board_read_time_record']
new=bi['PD-P1-M01-PREP-01']
assert new['notes'][:len(old['notes'])]==old['notes']
hashes=load(ns['CAND']/'source-hashes.json')
drift=[p for p,h in hashes.items() if sha(ns['ROOT']/p)!=h]
assert drift==['docs/board.json']
before_seal=sha(OUT/'seal.json')
result={'reviewer':'/root/current_action_blockers_review','author':d['author'],'verdict':'PASS_BOUNDED_CURRENT_ACTION_DOCUMENT_WITH_SNAPSHOT_LIMITS','supersedes_verdict_only':'results.json FAIL_DOCUMENT_REVIEW; old files and seal remain byte-identical','correction_reason':'Expected parent management append is snapshot drift, not candidate defect. Corrected oracle permits only M01 notes/updatedAt current-record differences; all other 31-card fields still compare.','positive_baseline':'PASS','fresh_valid_negative_probes':len(probes),'old_14_probes':'INVALID_DUE_TO_BASELINE_REJECTION; not counted','management_snapshot_drift':diff,'observed_M01_notes_prefix_preserved':True,'source_hash_drift':drift,'limits':['No original full-board old bytes; root updatedAt and complete historical board delta NOT PROVEN; no reconstructed board.','Current snapshot only; no categorical future preparation impossibility.','No new unfilled source-bound original-scope output found in bounded review.','Product/native tests, valid RED/GREEN, historical PASS reruns, build/package/install/DCC and Owner adoption NOT RUN.'],'creation_heartbeat':d['heartbeat'],'review_heartbeat':'2026-11-03T15:57:09.327Z','corrected_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'preserved_original_seal_sha256':before_seal,'candidate_seal_pass':all(sha(ns['CAND']/p)==h for p,h in load(ns['CAND']/'seal.json')['files'].items()),'board_unchanged_during_correction':ns['board_before']==(ns['ROOT']/'docs/board.json').read_bytes()}
assert result['candidate_seal_pass'] and result['board_unchanged_during_correction']
for name,obj in [('correction-results.json',result),('correction-probes.json',probes),('correction-findings.json',[])]: (OUT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'correction-index.html').write_text('<!doctype html><html lang="zh-Hant"><meta charset="utf-8"><title>Corrected bounded review</title><h1>'+result['verdict']+'</h1><p>Original observations and seal preserved. Corrected positive baseline PASS; 14 fresh valid semantic/source negative probes. Earlier 14 invalid probes excluded.</p><pre>'+html.escape(json.dumps(result,ensure_ascii=False,indent=2))+'</pre></html>',encoding='utf-8')
seal={'sealed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'stop_writing_after_seal':True,'original_seal_preserved':before_seal,'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='correction-seal.json'}}
(OUT/'correction-seal.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
