"""Read-only candidate consumer. Binding manifest is a separate sealed trust input."""
import argparse, hashlib, json, pathlib, sys
def sha(b): return hashlib.sha256(b).hexdigest()
def consume(candidate, manifest, output=None):
 bindings=json.loads(manifest.read_text(encoding='utf8'))
 if sha(pathlib.Path(__file__).read_bytes())!=bindings['consumer_sha256']: raise ValueError('consumer code binding mismatch')
 # No generation/repair is attempted when an input differs from the reviewed snapshot.
 for rel, expected in bindings['files'].items():
  p=candidate/rel
  if not p.is_file() or sha(p.read_bytes())!=expected: raise ValueError('binding mismatch: '+rel)
 rows=json.loads((candidate/'candidate.json').read_text(encoding='utf8'))['rows']
 paths=[x['path'] for x in rows]
 if paths!=bindings['paths'] or len(paths)!=14 or len(set(paths))!=14: raise ValueError('declared path set mismatch')
 for folder in ['templates','expected']:
  actual={str(p.relative_to(candidate/folder)).replace('\\','/') for p in (candidate/folder).rglob('*') if p.is_file()}
  if actual!=set(paths): raise ValueError('actual path set mismatch: '+folder)
 data=json.loads((candidate/'input.json').read_text(encoding='utf8'))
 values={'PACKAGE':data['package_name'],'TITLE':data['project_name'],'IDENTIFIER':data['identifier'],'DEFINITION':data['definition_revision'],'DESIGN':data['design_revision']}
 rendered={}
 for row in rows:
  path=row['path'];raw=(candidate/'templates'/path).read_bytes()
  if path.endswith('/Cargo.lock'): result=raw
  else:
   body=raw.decode('utf8')
   for key,value in values.items():body=body.replace('@@'+key+'@@',value)
   if '@@' in body: raise ValueError('unresolved token: '+path)
   result=body.encode('utf8')
  if result!=(candidate/'expected'/path).read_bytes(): raise ValueError('render differs from independent expected bytes: '+path)
  if sha(raw)!=row['template']['sha256'] or sha(result)!=row['expected']['sha256']: raise ValueError('row digest mismatch: '+path)
  rendered[path]=result
 if output is not None:
  if output.exists() and any(output.iterdir()): raise ValueError('output must be absent or empty')
  # output cannot overlap either candidate or trusted correction package.
  out=output.resolve(); c=candidate.resolve(); m=manifest.parent.resolve()
  if out==c or c in out.parents or out==m or m in out.parents: raise ValueError('protected output location')
  for path,body in rendered.items():
   target=output/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
 return {path:sha(body) for path,body in rendered.items()}
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--candidate',required=True,type=pathlib.Path);a.add_argument('--manifest',type=pathlib.Path,default=pathlib.Path(__file__).with_name('bindings.json'));a.add_argument('--output',type=pathlib.Path);v=a.parse_args()
 try: print(json.dumps({'status':'PASS_CANDIDATE_BYTES_ONLY','files':consume(v.candidate,v.manifest,v.output)}))
 except (ValueError,KeyError,OSError,UnicodeError) as ex: print(json.dumps({'status':'FAIL_CLOSED','error':str(ex)}));sys.exit(1)
