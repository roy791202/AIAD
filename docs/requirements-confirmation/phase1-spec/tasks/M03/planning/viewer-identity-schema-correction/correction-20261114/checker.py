"""Verify LF hash correction only. Does not rewrite parent packet files. Not acceptance."""
import hashlib, json, pathlib, sys
P = pathlib.Path(__file__).resolve().parent
PKT = P.parent
REPO = PKT
while REPO != REPO.parent and not (REPO / '.git').exists():
    REPO = REPO.parent

def digest_path(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

fails = []
hashes = json.loads((P / 'corrected-artifact-hashes.json').read_text(encoding='utf-8'))
for name, expected in hashes.items():
    actual = digest_path(PKT / name)
    if actual != expected:
        fails.append('payload %s: %s != %s' % (name, actual, expected))
manifest_expected = json.loads((P / 'seal.json').read_text(encoding='utf-8'))['manifest_sha256']
if digest_path(P / 'corrected-artifact-hashes.json') != manifest_expected:
    fails.append('seal.manifest_sha256 does not match corrected-artifact-hashes.json LF bytes')
freeze = json.loads((P / 'preservation.json').read_text(encoding='utf-8'))
for row in freeze:
    path = REPO / row['path']
    if row['classification'] == 'BOARD_MANAGEMENT_DIFF':
        if not path.is_file():
            fails.append('board.json missing')
        continue
    if row['classification'] != 'MATCH':
        fails.append('freeze class %s %s' % (row['path'], row['classification']))
        continue
    if not path.is_file():
        fails.append('missing %s' % row['path'])
        continue
    actual = digest_path(path)
    if actual != row['actual'] or actual != row['expected']:
        fails.append('freeze hash %s' % row['path'])
results = json.loads((P / 'results.json').read_text(encoding='utf-8'))
for banned in ('native PASS', 'READY_FOR_IMPLEMENTATION', 'Done', 'blue'):
    if banned not in results['not_claimed']:
        fails.append('missing not_claimed %s' % banned)
if results.get('native') != 'NOT RUN':
    fails.append('native must remain NOT RUN')
print(json.dumps({'ok': not fails, 'failed': fails, 'payloads': len(hashes), 'preservation': len(freeze)}))
sys.exit(1 if fails else 0)
