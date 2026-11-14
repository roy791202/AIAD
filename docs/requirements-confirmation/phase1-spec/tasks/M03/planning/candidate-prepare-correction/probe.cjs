// Limited schema subset, no field-name rules or custom lexical hooks.
const fs = require('fs'), path = require('path');
const read = n => JSON.parse(fs.readFileSync(path.join(__dirname,n),'utf8'));
function valid(root,s,x) {
 if(s.$ref) {let t=root;for(const k of s.$ref.slice(2).split('/'))t=t[k];return valid(root,t,x);}
 if(s.oneOf)return s.oneOf.filter(z=>valid(root,z,x)).length===1;
 if('const' in s && JSON.stringify(x)!==JSON.stringify(s.const))return false;
 if(s.enum&&!s.enum.includes(x))return false;
 const kinds={object:x!==null&&typeof x==='object'&&!Array.isArray(x),array:Array.isArray(x),string:typeof x==='string',boolean:typeof x==='boolean',null:x===null};
 if(s.type&&!(Array.isArray(s.type)?s.type:[s.type]).some(t=>kinds[t]))return false;
 if(typeof x==='string') {if(x.length<(s.minLength||0)||x.length>(s.maxLength??1e9))return false;if(s.pattern&&!new RegExp(s.pattern).test(x))return false;}
 if(kinds.object) {if((s.required||[]).some(k=>!(k in x)))return false;if(s.additionalProperties===false&&Object.keys(x).some(k=>!(k in (s.properties||{}))))return false;if(Object.entries(s.properties||{}).some(([k,z])=>k in x&&!valid(root,z,x[k])))return false;}
 if(kinds.array&&s.items&&x.some(z=>!valid(root,s.items,z)))return false;
 return true;
}
const roots=Object.fromEntries(['request.schema.json','response.schema.json'].map(n=>[n,read(n)]));
let results=read('lexical-fixtures.json').map(c=>({id:c.id,expected:c.expected_accept,actual:valid(roots[c.schema],roots[c.schema],c.instance)}));
let patterns=read('pattern-fixtures.json').map((c,i)=>({id:'physical-pattern-'+i,expected:c.expected,actual:new RegExp(c.pattern).test(c.value)}));
console.log(JSON.stringify({engine:process.version,root_probes:results.length,definition_probes:patterns.length,mismatches:[...results,...patterns].filter(r=>r.expected!==r.actual)}));
