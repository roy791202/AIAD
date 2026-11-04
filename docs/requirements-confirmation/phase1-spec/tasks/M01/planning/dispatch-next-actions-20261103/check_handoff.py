"""Document/source integrity only. Does not execute any accepted checker."""
import hashlib, json
from pathlib import Path
out=Path(__file__).resolve().parent
root=out.parents[6]
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
a=read(out/'action-matrix.json')
assert len(a['yellow'])==8 and len(a['gray_red'])==23
assert len({x['id'] for x in a['yellow']+a['gray_red']})==31
assert len(a['feature_evidence'])==12
assert all(x.get('action_attempt_this_round') for x in a['yellow']+a['gray_red'])
assert sum(x['live_light']=='Gray' for x in a['gray_red'])==18
assert sum(x['live_light']=='Red' for x in a['gray_red'])==5
assert a['same_head'] is False
for name,h in read(out/'seal.json')['files'].items(): assert sha(out/name)==h, name
for name,h in read(out/'source-hashes.json')['sources'].items(): assert sha(root/name)==h, name
model=(out/'index.html').read_text(encoding='utf-8').split('<script id="module-spec" type="application/json">',1)[1].split('</script>',1)[0]
assert json.loads(model)==a
assert all(not (root/'docs/requirements-confirmation/phase1-spec/tasks/decisions'/f'G{i:02}').exists() for i in range(1,5))
print('PASS author document integrity only: 31 actions, 12 reviewed traces, source hashes, seal, embedded model. Independent acceptance/native/product NOT RUN.')
