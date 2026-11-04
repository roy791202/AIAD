const fs=require('fs'),path=require('path');const read=n=>JSON.parse(fs.readFileSync(path.join(__dirname,n),'utf8').replace(/^\uFEFF/,''));
function validate(schema,x,root=schema){
 if(schema.$ref){let target=root;for(const key of schema.$ref.slice(2).split('/'))target=target[key];return validate(target,x,root)}
 if(schema.oneOf)return schema.oneOf.filter(s=>validate(s,x,root)).length===1;
 if('const'in schema&&JSON.stringify(schema.const)!==JSON.stringify(x))return false;
 if(schema.enum&&!schema.enum.some(v=>JSON.stringify(v)===JSON.stringify(x)))return false;
 const typ=x===null?'null':Array.isArray(x)?'array':typeof x;
 if(schema.type&&!(Array.isArray(schema.type)?schema.type:[schema.type]).includes(typ))return false;
 if(typ==='string'&&(x.length<(schema.minLength||0)||x.length>(schema.maxLength||Infinity)||schema.pattern&&!new RegExp(schema.pattern).test(x)))return false;
 if(typ==='object'){
  if((schema.required||[]).some(k=>!(k in x)))return false;
  if(schema.additionalProperties===false&&Object.keys(x).some(k=>!(k in (schema.properties||{}))))return false;
  for(const [k,v]of Object.entries(schema.properties||{}))if(k in x&&!validate(v,x[k],root))return false;
 }
 if(typ==='array'&&schema.items&&x.some(v=>!validate(schema.items,v,root)))return false;
 return true;
}
let count=0;for(const item of read('lexical-audit.json')){const r=new RegExp(item.pattern);if(!r.test(item.positive)||item.negative.some(x=>r.test(x)))throw Error(item.pointer);count++}
const roots=read('root-probes.json');for(const p of roots)if(validate(read(p.root),p.value)!==p.expected)throw Error(p.label);
process.stdout.write(JSON.stringify({status:'PASS_DOCUMENT_SUBSET_NOT_FULL_DRAFT202012',physical_patterns:count,root_cases:roots.length}));
