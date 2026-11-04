import re
import copy
class Draft202012Validator:
 def __init__(self,s):self.s=s
 @staticmethod
 def check_schema(s):assert s.get('$schema')=='https://json-schema.org/draft/2020-12/schema'
 def validate(self,x):
  def v(s,x):
   if '$ref' in s:
    t=self.s
    for k in s['$ref'][2:].split('/'):t=t[k]
    return v(t,x)
   if 'oneOf' in s:return sum(v(z,x) for z in s['oneOf'])==1
   if 'const' in s and (type(x)!=type(s['const']) or x!=s['const']):return False
   if 'enum' in s and x not in s['enum']:return False
   kinds={'object':type(x)is dict,'array':type(x)is list,'string':type(x)is str,'boolean':type(x)is bool,'null':x is None}
   t=s.get('type')
   if t and not any(kinds.get(k,False) for k in (t if isinstance(t,list) else [t])):return False
   if type(x)is str:
    if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**9):return False
    if 'pattern'in s and re.search(s['pattern'],x)is None:return False
   if type(x)is dict:
    if any(k not in x for k in s.get('required',[])):return False
    if s.get('additionalProperties')is False and any(k not in s.get('properties',{}) for k in x):return False
    if any(k in x and not v(z,x[k]) for k,z in s.get('properties',{}).items()):return False
   if type(x)is list and 'items'in s and any(not v(s['items'],z) for z in x):return False
   return True
  assert v(self.s,x),'schema rejection'

