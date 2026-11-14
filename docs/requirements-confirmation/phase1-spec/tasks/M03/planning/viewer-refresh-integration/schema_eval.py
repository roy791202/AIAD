"""Bounded keyword evaluator, NOT full Draft2020."""
import re
KEYWORDS={'$schema','$id','$defs','$ref','type','properties','required','additionalProperties','oneOf','const','enum','minLength','maxLength','pattern','items'}
def audit(s):
    assert not (set(s)-KEYWORDS),set(s)-KEYWORDS
    for key in ['properties','$defs']:
        for item in s.get(key,{}).values():audit(item)
    for item in s.get('oneOf',[]):audit(item)
    if 'items'in s:audit(s['items'])
def valid(root,x):
    def v(s,x):
        if '$ref'in s:
            dest=root
            for k in s['$ref'][2:].split('/'):dest=dest[k]
            return v(dest,x)
        if 'oneOf'in s:return sum(v(a,x) for a in s['oneOf'])==1
        if 'const'in s and (type(x)!=type(s['const']) or x!=s['const']):return False
        if 'enum'in s and not any(type(x)==type(a) and x==a for a in s['enum']):return False
        types={'object':type(x)is dict,'array':type(x)is list,'string':type(x)is str,'boolean':type(x)is bool,'null':x is None}
        t=s.get('type')
        if t and not any(types.get(k,False) for k in (t if isinstance(t,list) else [t])):return False
        if isinstance(x,str):
            if not s.get('minLength',0)<=len(x)<=s.get('maxLength',10**9):return False
            if 'pattern'in s and re.search(s['pattern'],x)is None:return False
        if type(x)is dict:
            if any(k not in x for k in s.get('required',[])):return False
            if s.get('additionalProperties')is False and set(x)-set(s.get('properties',{})):return False
            if any(k in x and not v(a,x[k]) for k,a in s.get('properties',{}).items()):return False
        if type(x)is list and 'items'in s and not all(v(s['items'],a) for a in x):return False
        return True
    return v(root,x)
