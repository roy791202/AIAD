const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');const vm=require('node:vm');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'app.js'),'utf8').split('// DOC-UI-02 controller begin')[1].split('// DOC-UI-02 controller end')[0];
const context={};vm.runInNewContext(source+'\nglobalThis.create=createDocumentIdentityController;',context);
function fixture(handler){let root='/A';const calls=[];const invoke=handler?async(c,a)=>{calls.push([c,a]);return handler(c,a);}:async(c,a)=>{calls.push([c,a]);return c==='project_document_prepare'?{project_id:'pA',project_root:root}:{outcome:'Adopted',document_id:'doc-A',revision_id:'rev'};};const ctrl=context.create({invoke,getRoot:()=>root,render:()=>{}});return{ctrl,calls,setRoot:r=>{root=r;ctrl.invalidate();}};}
const plain=x=>JSON.parse(JSON.stringify(x));

test('blocked preparation explains execution busy instead of asking to prepare again',()=>{
  const c=context.create({invoke:async()=>{},getRoot:()=>'/A',getBusy:()=>true,render:()=>{}});
  c.invalidate();
  assert.equal(c.view().canPrepare,false);
  assert.match(c.view().status,/執行中/);
  assert.doesNotMatch(c.view().status,/請重新準備/);
});

test('dialog prepare button dispatches through the actual UI event wiring',async()=>{
  const app=fs.readFileSync(path.join(__dirname,'app.js'),'utf8');
  const html=fs.readFileSync(path.join(__dirname,'index.html'),'utf8');
  const elements=new Map();
  for(const match of html.matchAll(/id="(document-identity-[^"]+)"/g)){
    const listeners=new Map();
    elements.set(match[1],{textContent:'',value:'',disabled:false,open:false,
      addEventListener(type,fn){listeners.set(type,fn);},
      showModal(){this.open=true;},
      async fire(type){if(type==='click'&&this.disabled)return;return listeners.get(type)?.({target:this});}
    });
  }
  const calls=[];
  const ctx={document:{getElementById:id=>elements.get(id)},cachedProjectRoot:'/A',activeRunId:null,hasIpc:true,
    invoke:async(cmd,args)=>{calls.push([cmd,args]);return{project_id:'pA',project_root:'/A'};}};
  const wiring=app.slice(app.indexOf('  function renderDocumentIdentity('),app.indexOf('  /** OS 獨立視窗'));
  vm.runInNewContext(source+'\n'+wiring+'\nopenDocumentIdentity();',ctx);
  const prepare=elements.get('document-identity-prepare');
  assert.equal(prepare.disabled,false);
  await prepare.fire('click');
  assert.equal(calls.length,1);
  assert.equal(calls[0][0],'project_document_prepare');
  assert.match(elements.get('document-identity-status').textContent,/專案已準備/);
});
test('explicit prepare then adopt sends only server identity and selected reference',async()=>{const{ctrl,calls}=fixture();ctrl.setReference('design/main.sgendesign');assert.equal(ctrl.view().canPrepare,true);assert.equal(ctrl.view().canAdopt,false);await ctrl.prepare();assert.equal(ctrl.view().canAdopt,true);await ctrl.adopt();assert.deepEqual(plain(calls),[['project_document_prepare',{args:{expected_project_root:'/A'}}],['project_document_adopt',{args:{expected_project_id:'pA',reference:'design/main.sgendesign'}}]]);assert.match(ctrl.view().status,/doc-A/);});
test('browser or unbound state never invokes',async()=>{for(const invoke of [null,async()=>{throw Error('must not invoke');}]){const c=context.create({invoke,getRoot:()=>'',render:()=>{}});assert.equal(c.view().canPrepare,false);await c.prepare();await c.adopt();}});
test('invalid or empty reference remains disabled without adoption request',async()=>{const{ctrl,calls}=fixture();await ctrl.prepare();for(const s of ['', '../a.ess','/a.ess','C:\\a.ess','a/../b.ess','file.txt','a:stream.ess']){ctrl.setReference(s);assert.equal(ctrl.view().canAdopt,false,s);await ctrl.adopt();}assert.equal(calls.length,1);});
test('late prepare result cannot bind another project',async()=>{let resolve;const{ctrl,setRoot}=fixture(()=>new Promise(r=>resolve=r));const pending=ctrl.prepare();assert.equal(ctrl.view().busy,true);setRoot('/B');resolve({project_id:'pA',project_root:'/A'});await pending;assert.equal(ctrl.view().context,null);assert.equal(ctrl.view().root,'/B');assert.equal(ctrl.view().canAdopt,false);});
test('duplicate prepare clicks produce one request and cancellation discards result',async()=>{let resolve;const{ctrl,calls}=fixture(()=>new Promise(r=>resolve=r));const p=ctrl.prepare();await ctrl.prepare();assert.equal(calls.length,1);ctrl.invalidate();resolve({project_id:'pA',project_root:'/A'});await p;assert.equal(ctrl.view().context,null);});
test('failed reprepare clears prior prepared context and displays typed error',async()=>{let fail=false;const{ctrl}=fixture(async()=>{if(fail)throw{code:'Busy'};return{project_id:'pA',project_root:'/A'};});await ctrl.prepare();fail=true;await ctrl.prepare();assert.equal(ctrl.view().context,null);assert.match(ctrl.view().status,/Busy/);});
test('late adoption response and double click cannot update B or replay request',async()=>{let resolve;const{ctrl,calls,setRoot}=fixture(async(c)=>c==='project_document_prepare'?{project_id:'pA',project_root:'/A'}:new Promise(r=>resolve=r));await ctrl.prepare();ctrl.setReference('scene/default.ess');const p=ctrl.adopt();await ctrl.adopt();assert.equal(calls.filter(x=>x[0]==='project_document_adopt').length,1,'adoption must dispatch once');setRoot('/B');resolve({outcome:'Adopted',document_id:'old-A'});await p;assert.equal(calls.filter(x=>x[0]==='project_document_adopt').length,1);assert.doesNotMatch(ctrl.view().status,/old-A/);assert.equal(ctrl.view().context,null);});

test('known execution busy disables preparation and adoption without an IPC attempt',async()=>{let executionBusy=false;const calls=[];const c=context.create({invoke:async(cmd,args)=>{calls.push([cmd,args]);return{project_id:'pA',project_root:'/A'};},getRoot:()=>'/A',getBusy:()=>executionBusy,render:()=>{}});await c.prepare();c.setReference('design/main.sgendesign');assert.equal(c.view().canAdopt,true);executionBusy=true;assert.equal(c.view().canPrepare,false);assert.equal(c.view().canAdopt,false);await c.prepare();await c.adopt();assert.equal(calls.length,1);});
