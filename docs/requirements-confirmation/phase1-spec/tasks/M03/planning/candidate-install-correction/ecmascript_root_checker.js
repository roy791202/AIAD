const fs=require('fs');const d=JSON.parse(fs.readFileSync(0,'utf8'));
function valid(root,s,x){if(s.$ref){let t=root;for(const k of s.$ref.slice(2).split('/'))t=t[k];return valid(root,t,x)}
if(s.oneOf)return s.oneOf.filter(z=>valid(root,z,x)).length===1;
if('const'in s&&JSON.stringify(x)!==JSON.stringify(s.const))return false;
if(s.enum&&!s.enum.includes(x))return false;
const kind=x===null?'null':Array.isArray(x)?'array':typeof x;
if(s.type&&!(Array.isArray(s.type)?s.type:[s.type]).includes(kind))return false;
if(typeof x==='string'){if(x.length<(s.minLength||0)||x.length>(s.maxLength||1e9))return false;if(s.pattern&&!new RegExp(s.pattern).test(x))return false}
if(kind==='object'){if((s.required||[]).some(k=>!(k in x)))return false;if(s.additionalProperties===false&&Object.keys(x).some(k=>!(k in(s.properties||{}))))return false;if(Object.entries(s.properties||{}).some(([k,z])=>k in x&&!valid(root,z,x[k])))return false}
if(kind==='array'&&s.items&&x.some(z=>!valid(root,s.items,z)))return false;return true}
process.stdout.write(JSON.stringify(d.cases.map(c=>({id:c.id,accepted:valid(d.roots[c.root],d.roots[c.root],c.instance),before:valid(d.old[c.root],d.old[c.root],c.instance)}))));