"""Seal only this new folder; rerun checker first, python -B seal.py."""
import hashlib,json,pathlib
P=pathlib.Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inventory={p.name:sha(p) for p in sorted(P.iterdir()) if p.is_file() and p.name not in ('artifact-hashes.json','seal.json')}
(P/'artifact-hashes.json').write_text(json.dumps(inventory,indent=2)+'\n',encoding='utf-8')
result=json.loads((P/'results.json').read_text(encoding='utf-8'))
seal={'status':'SEALED_AUTHOR_DOCUMENT_ONLY_PENDING_INDEPENDENT_REVIEW_OWNER','artifacts':len(inventory),'inventory_sha256':sha(P/'artifact-hashes.json'),'final_counts':result,'scope':'new viewer-close-integration only','native_authenticity_atomicity':'UNPROVED_PREMISES','no_original_product_board_writes':True}
(P/'seal.json').write_text(json.dumps(seal,indent=2)+'\n',encoding='utf-8')
assert all(sha(P/name)==digest for name,digest in inventory.items())
print(json.dumps({'sealed_artifacts':len(inventory),'fixtures':result['fixtures'],'behavior_assertions':result['behavior_assertions'],'root_probes':result['complete_root_probes']}))
