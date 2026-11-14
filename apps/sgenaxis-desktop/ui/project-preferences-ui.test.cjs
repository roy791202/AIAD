const {test}=require('node:test');const assert=require('node:assert/strict');
const {toDraft}=require('./project-preferences-ui.js');
const form=()=>({modelIds:'A, B',preferred:'B',input:'',output:'100',seconds:'60',tasks:'4',concurrent:'2'});
test('project controls produce exact v1 draft without credentials',()=>{
 const p=toDraft(form());assert.equal(p.format,'sgenaxis.project-preferences');assert.equal(p.presetId,'custom');
 assert.deepEqual(p.modelPolicy,{allowedModelIds:['A','B'],preferredModelId:'B'});
 assert.deepEqual(p.budget,{maxInputTokens:null,maxOutputTokens:100,maxWallTimeSeconds:60});assert.equal(p.batch.mode,'suggest');assert.equal(p.batch.onLimit,'block');assert.equal(p.workflow.confirmBeforeRun,true);
});
test('blank model budget remains unconfigured',()=>{const f=form();f.modelIds='';f.preferred='';f.output='';f.seconds='';const p=toDraft(f);assert.deepEqual(p.modelPolicy.allowedModelIds,[]);assert.equal(p.modelPolicy.preferredModelId,null);assert.equal(p.budget.maxOutputTokens,null);});
test('invalid numbers and unsafe JS integers cannot silently round',()=>{for(const input of ['-1','0','1.5','abc','9007199254740992']){assert.throws(()=>toDraft({...form(),input}));}});
test('concurrency and membership rejected before command',()=>{assert.throws(()=>toDraft({...form(),concurrent:'5'}));assert.throws(()=>toDraft({...form(),preferred:'C'}));assert.throws(()=>toDraft({...form(),modelIds:'A,A'}));});
