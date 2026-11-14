import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[7]
OUT=Path(__file__).resolve().parent
ANCHORS={'RS01': ['pub struct CapturedAttempt', 'pub attempt_id', 'pub captured_fingerprint', 'pub asset_manifest_digest'], 'RS02': ['Published', 'Failed', 'Complete', 'attempt_id'], 'RS03': ['Published is a trusted HOST receipt', 'pub fn transition_recovery'], 'RS04': ['checked_sub(state.last_check_ms)', 'elapsed < 60000', 'RecoveryAction::RequestCapture'], 'RS05': ['.filter(|c| &c.attempt_id == attempt_id)', 'CompletionOutcome::Published', 'next.successful_fingerprint', 'RecoveryAction::BaselineAdvanced'], 'RS06': ['fn validate_capture', 'validate_id("attempt_id"', 'validate_fingerprint("captured_fingerprint"', 'validate_fingerprint("asset_manifest_digest"'], 'DE01': ['pub fn capture', 'self.state.content.clone()'], 'DE02': ['pub fn acknowledge_formal_save', 'self.state.formal_baseline =', 'pub fn acknowledge_recovery_save', 'self.state.snapshot_baseline ='], 'DE03': ['fn check_ack', 'captured.0 > self.state.content_revision.0', 'captured.0 < saved.revision.0'], 'IO01': ['pub struct CommitReceipt', 'pub transaction_id', 'pub target', 'pub committed_digest']}
def validate(rows):
 if len(rows)!=10 or {x['id'] for x in rows}!=set(ANCHORS):raise ValueError('exact ten span IDs required')
 for r in rows:
  p=ROOT/r['path'];raw=p.read_bytes();lines=raw.decode('utf-8').splitlines();a,b=r['start'],r['end']
  if not isinstance(a,int) or not isinstance(b,int) or not 1<=a<=b<=len(lines):raise ValueError('invalid/out-of-range span '+r['id'])
  text='\n'.join(lines[a-1:b])
  if not text.strip():raise ValueError('empty span '+r['id'])
  if hashlib.sha256(raw).hexdigest()!=r['sha256']:raise ValueError('source hash mismatch '+r['id'])
  if text!=r['text']:raise ValueError('source span text mismatch '+r['id'])
  if r.get('required_anchors')!=ANCHORS[r['id']] or any(x not in text for x in ANCHORS[r['id']]):raise ValueError('semantic anchors missing '+r['id'])
 return True
if __name__=='__main__':
 try:
  validate(json.loads(Path(sys.argv[1] if len(sys.argv)>1 else OUT/'source-spans.json').read_text(encoding='utf-8')))
  print('PASS_EXACT_STATIC_SOURCE_BINDINGS')
 except (ValueError,KeyError,TypeError,OSError) as e:print('FAIL '+str(e));sys.exit(1)
