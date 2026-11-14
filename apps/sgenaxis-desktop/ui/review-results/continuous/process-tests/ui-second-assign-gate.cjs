const {chromium}=require('C:/Users/g6812/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs');const path=require('path');const assert=require('assert');const {pathToFileURL}=require('url');
const out=__dirname;const root=path.resolve(__dirname,'../../../..');
(async()=>{const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe'});const results=[];
for(const mode of ['second-assign']){const page=await browser.newPage({viewport:{width:1440,height:1000}});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
await page.addInitScript(({mode})=>{
 const board=(active)=>({tasks:[{id:'dispatch-demo',title:'Process fixture',zone:active==null?'yellow':'blue'}],active_run_id:active,gray:0,yellow:active==null?1:0,blue:active==null?0:1,red:0,green:0});
 window.__proc={calls:[],pending:[],cancelFinished:false,mode};
 window.__TAURI__={core:{invoke:async(cmd,args)=>{window.__proc.calls.push({cmd,args});
 if(cmd==='host_get_settings')return {project_root:'D:/process-fixture',board_path:'board.html',agent_active:false,run_mode:'dry_run',provider:'cli'};
 if(cmd==='load_local_board')return {board:board(null),status:'ok',write_back:false,path:'board.html'};
 if(cmd==='get_board')return board(null);
 if(cmd==='get_evidence_summary')return {provider_terminal:'NotRun',ready_for_green:false};
 if(cmd==='start_run'){const count=window.__proc.calls.filter(x=>x.cmd==='start_run').length;if(count>1&&!window.__proc.completed)throw Error('busy: existing lease and active run');const id=count>1?102:101;return {run_id:id,provider:'cli',dry_run:true,board:board(id)};}
 if(cmd==='poll_chunks')return new Promise(resolve=>window.__proc.pending.push(resolve));
 if(cmd==='cancel_run'){window.__proc.cancelFinished=true;if(mode==='cancel-request-error')throw Error('controlled cancel request failure');return board(101);}
 return {};
 }}};
 window.__proc.release=(chunks,done=false)=>{window.__proc.completed=done;const resolve=window.__proc.pending.shift();if(!resolve)throw Error('HARNESS: no pending poll');resolve({run_id:101,chunks,board:board(done?null:101)});};
},{mode});
try{
 await page.goto(pathToFileURL(path.join(root,'apps/sgenaxis-desktop/ui/index.html')).href);
 await page.waitForFunction(()=>document.getElementById('app-splash')==null);
 await page.locator('#nav-tasks').click();await page.locator('#nav-agent').click();await page.locator('#btn-dry-run').click();
 await page.waitForFunction(()=>window.__proc.pending.length===1);
 assert.equal(await page.locator('#run-class-badge').getAttribute('data-class'),'running');
 if(mode==='empty'){
  await page.evaluate(()=>window.__proc.release([]));
  await page.waitForFunction(()=>window.__proc.pending.length===1||document.getElementById('run-class-badge').dataset.class==='failed');
  assert.equal(await page.locator('#run-class-badge').getAttribute('data-class'),'running','empty poll must preserve running UI');
  await page.evaluate(()=>window.__proc.release([]));
  await page.waitForFunction(()=>window.__proc.pending.length===1||document.getElementById('run-class-badge').dataset.class==='failed');
  assert.equal(await page.locator('#run-class-badge').getAttribute('data-class'),'running');
 }else{
  await page.locator('#btn-cancel-run').click();await page.waitForFunction(()=>window.__proc.cancelFinished);
  // Let the invoked cancel continuation settle through actual browser event loop.
  await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(await page.locator('#run-class-badge').getAttribute('data-class'),'running','cancel acknowledgment/request-error must not finish UI');
  if(mode!=='cancel-request-error')assert.match(await page.locator('#run-status-line').textContent(),/取消中/);
  else assert.match(await page.locator('#run-status-line').textContent(),/controlled cancel request failure/);
  assert.doesNotMatch(await page.locator('#run-status-line').textContent(),/租約已釋放/);
  await page.locator('#btn-dry-run').click();await page.evaluate(()=>new Promise(requestAnimationFrame));
  assert.equal(await page.locator('#run-class-badge').getAttribute('data-class'),'running','second assign while cancellation drains must not detach existing poll');
  assert.equal(await page.evaluate(()=>window.__proc.calls.filter(x=>x.cmd==='start_run').length),1,'pending run must block second dispatch before IPC');
 }
 const terminal=mode==='cancel-failed'?{kind:'failed',run_id:101,message:'incomplete output timeout 2000ms'}:{kind:'exited',run_id:101,classification:mode==='empty'||mode==='cancel-request-error'?'success':'cancelled',exit_code:mode==='empty'||mode==='cancel-request-error'?0:-1};
 await page.evaluate(({terminal})=>window.__proc.release([{kind:'chunk',run_id:101,stream:'stdout',text:'CONTROLLED_FINAL_TAIL'},terminal],true),{terminal});
 const expected=mode==='cancel-failed'?'failed':mode==='empty'||mode==='cancel-request-error'?'ok':'cancelled';
 await page.waitForFunction(expected=>document.getElementById('run-class-badge').dataset.class===expected,expected,{timeout:5000});
 const log=await page.locator('#agent-log').textContent();assert.equal((log.match(/CONTROLLED_FINAL_TAIL/g)||[]).length,1,'tail must appear once');assert(log.indexOf('CONTROLLED_FINAL_TAIL')<Math.max(log.indexOf('[exited]'),log.indexOf('[failed]')));
 assert(await page.locator('#btn-cancel-run').isDisabled());assert.equal(errors.length,0,errors.join('\n'));
 await page.locator('#btn-dry-run').click();await page.waitForFunction(()=>window.__proc.pending.length===1);
 assert.equal(await page.evaluate(()=>window.__proc.calls.filter(x=>x.cmd==='start_run').length),2,'terminal completion must permit later dispatch');
 assert.equal(await page.locator('#run-class-badge').getAttribute('data-class'),'running');
 await page.evaluate(()=>window.__proc.release([{kind:'chunk',run_id:102,stream:'stdout',text:'SECOND_RUN_TAIL'},{kind:'exited',run_id:102,classification:'success',exit_code:0}],true));
 await page.waitForFunction(()=>document.getElementById('run-class-badge').dataset.class==='ok');
 assert.equal(((await page.locator('#agent-log').textContent()).match(/SECOND_RUN_TAIL/g)||[]).length,1);assert(await page.locator('#btn-cancel-run').isDisabled());
 await page.screenshot({path:path.join(out,'ui-'+mode+'-green.png'),fullPage:false});results.push({mode,status:'PASS',url:page.url(),title:await page.title(),meaningfulBody:(await page.locator('body').innerText()).length>100,errors,calls:await page.evaluate(()=>window.__proc.calls.map(x=>x.cmd))});
}catch(e){await page.screenshot({path:path.join(out,'ui-'+mode+'-failure.png'),fullPage:false});results.push({mode,status:'FAIL',error:String(e),errors,dom:{classification:await page.locator('#run-class-badge').getAttribute('data-class'),status:await page.locator('#run-status-line').textContent(),log:await page.locator('#agent-log').textContent()}});}await page.close();}
await browser.close();fs.writeFileSync(path.join(out,process.env.UI_GATE_RESULT||'ui-second-assign-results.json'),JSON.stringify({browser:'Installed Chrome via bundled Playwright; Browser plugin not available',surface:'Actual index.html/app.js file://, mocked IPC only; no native Tauri or Agent proof',results},null,2));console.log(JSON.stringify(results.map(x=>({mode:x.mode,status:x.status,error:x.error})),null,2));if(results.some(x=>x.status!=='PASS'))process.exitCode=1;
})();
