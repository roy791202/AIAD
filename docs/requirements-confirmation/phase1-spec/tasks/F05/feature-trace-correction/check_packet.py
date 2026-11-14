import copy,json,re,subprocess
from build_packet import HERE,ROOT,BASE,read,write,sha,expected,validate

def run():
    model=read(HERE/'module-spec.json'); sources=read(HERE/'source-inputs.json')['sources']; errors=validate(model,sources)
    embedded=re.search(r'<script id="module-spec" type="application/json">(.*?)</script>',(HERE/'index.html').read_text(encoding='utf-8'),re.S)
    if not embedded or json.loads(embedded.group(1))!=model: errors.append('HTML embedded trace mismatch')
    fixtures=read(HERE/'mutation-fixtures.json'); outcomes=[]
    for f in fixtures['mutations']:
        mutant=copy.deepcopy(model); mutant['trace'][f['row']][f['field']]=f['value']; detected=bool(validate(mutant)); outcomes.append({'id':f['id'],'detected':detected})
    bad=copy.deepcopy(sources); bad[0]['sha256']='0'*64
    outcomes.append({'id':'source-hash-mismatch','detected':bool(validate(model,bad))})
    for label,mutate in [('original-failure-scenario-change',lambda m:m['original_scenarios'][0].__setitem__(6,'leave allowed')),('gray-promotion',lambda m:m['identity'].__setitem__('zone','green')),('gate-removal',lambda m:m.__setitem__('gates',[]))]:
        mutant=copy.deepcopy(model); mutate(mutant); outcomes.append({'id':label,'detected':bool(validate(mutant))})
    authority=read(ROOT/model['authority']['authority_file']); drift=[p for p,h in authority['source_hashes'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if len(authority['source_hashes'])!=796 or drift or head!=model['authority']['head']: errors.append('Authority inventory/current HEAD mismatch')
    if not all(o['detected'] for o in outcomes): errors.append('Mutation survived')
    seal_path=HERE/'seal.json'
    if seal_path.exists():
        for item in read(seal_path)['files']:
            target=HERE/item['path']
            if not target.is_file() or sha(target)!=item['sha256']: errors.append('Seal hash mismatch:'+item['path'])
    result={'scope':'Static trace correction self-check only; not independent acceptance','status':'STATIC_CHECK_PASS' if not errors else 'FAIL','counts':{'rows':7,'feature_plans':5,'adjacent_regressions':2,'mutations':len(outcomes),'detected':sum(o['detected'] for o in outcomes)},'errors':errors,'mutations':outcomes,'authority':{'head':head,'historical_head':authority['head'],'files':len(authority['source_hashes']),'drift':drift},'not_run':model['not_run'],'zone':'gray','feature_verdict':'NOT_PROVEN'}
    return result
if __name__=='__main__':
    result=run(); print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(bool(result['errors']))
