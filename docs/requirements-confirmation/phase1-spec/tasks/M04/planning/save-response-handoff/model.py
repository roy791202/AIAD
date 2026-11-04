"""Document-only orchestration oracle. No product/native implementation."""
def evaluate(f):
 r={'ack_calls':0,'root_calls':0,'formal_revision':f['formal_revision'],'formal_semantic':f['formal_semantic'],'snapshot':f['snapshot'],'live_revision':f['live_revision'],'retained':True,'unchanged_claim':False,'delivered':f['owner_current']}
 if f['io_error']:
  r['outcome']='SaveRejected' if f['io_error']=='Busy' else 'UnverifiedOutcome';return r
 if not (f['receipt_target']==f['target'] and f['receipt_previous']==f['previous'] and f['receipt_raw']==f['raw'] and bool(f['transaction'])):
  r['outcome']='UnverifiedOutcome';return r
 r['file_verified']=True
 if not f['owner_current']:
  r['outcome']='CommittedAckDeferred:OwnerChanged';return r
 r['root_calls']=1
 if f['root']!='verified' or f['root_capture']!=f['capture']:
  r['outcome']='CommittedAckDeferred:RootTransfer';r['pin_state']='Unverified';return r
 r['ack_calls']=1
 if f['revision']<f['formal_revision'] or (f['revision']==f['formal_revision'] and f['semantic']!=f['formal_semantic']):
  r['outcome']='CommittedAckDeferred:SemanticAck';return r
 r.update(outcome='Saved',formal_revision=f['revision'],formal_semantic=f['semantic'],dirty=f['live_semantic']!=f['semantic'])
 return r
