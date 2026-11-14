"""Bounded evaluator for enumerated physical schemas, NOT full JSON Schema Draft."""
import re
KEYWORDS={'$schema','$id','$defs','$ref','type','properties','required','additionalProperties','oneOf','const','enum','minLength','maxLength','pattern','items','description'}
def audit(s):
 assert type(s)is dict and not set(s)-KEYWORDS,set(s)-KEYWORDS
 if '$ref'in s:assert s['$ref'].startswith('#/')
 for key in ('properties','$defs'):
  for child in s.get(key,{}).values():audit(child)
 for child in s.get('oneOf',[]):audit(child)
 if 'items'in s:audit(s['items'])
def valid(root,value):
 def visit(s,x):
  if '$ref'in s:
   target=root
   for part in s['$ref'][2:].split('/'):target=target[part]
   return visit(target,x)
  if 'oneOf'in s:return sum(visit(a,x) for a in s['oneOf'])==1
  if 'const'in s and (type(x)is not type(s['const']) or x!=s['const']):return False
  if 'enum'in s and not any(type(x)is type(a) and x==a for a in s['enum']):return False
  types={'object':type(x)is dict,'array':type(x)is list,'string':type(x)is str,'boolean':type(x)is bool,'null':x is None}
  kinds=s.get('type',[]);kinds=[kinds] if type(kinds)is str else kinds
  if kinds and not any(types.get(k,False) for k in kinds):return False
  if type(x)is str:
   if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**9):return False
   if 'pattern'in s and re.search(s['pattern'],x)is None:return False
  if type(x)is dict:
   if not set(s.get('required',[]))<=set(x):return False
   if s.get('additionalProperties')is False and set(x)-set(s.get('properties',{})):return False
   if any(k in x and not visit(a,x[k]) for k,a in s.get('properties',{}).items()):return False
  if type(x)is list and 'items'in s and not all(visit(s['items'],a) for a in x):return False
  return True
 return visit(root,value)
def sample(root,s=None):
 s=root if s is None else s
 if '$ref'in s:
  target=root
  for part in s['$ref'][2:].split('/'):target=target[part]
  return sample(root,target)
 if 'oneOf'in s:return sample(root,s['oneOf'][0])
 if 'const'in s:return s['const']
 if 'enum'in s:return s['enum'][0]
 kind=s.get('type');kind=kind[0] if type(kind)is list else kind
 if kind=='object':return {k:sample(root,s['properties'][k]) for k in s.get('required',[])}
 if kind=='array':return []
 if kind=='boolean':return False
 if kind=='null':return None
 if kind=='string':
  pat=s.get('pattern','')
  return '0' if '[1-9]'in pat else ('a'*64 if '{64}'in pat else ('abcdef01-abcd-4abc-8abc-abcdef012345' if '{8}'in pat else 'x'))
 raise AssertionError(s)
