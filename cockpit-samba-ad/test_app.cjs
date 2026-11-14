const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function app(){
 const nodes=new Map(),callbacks={},requests=[];
 const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',classList:{toggle(){},add(){}}});return nodes.get(id)};
 const document={hidden:false,getElementById:node,querySelectorAll:()=>[],querySelector:()=>null,
  addEventListener:(event,callback)=>callbacks[event]=callback,
  createElement:()=>({textContent:'',get innerHTML(){return this.textContent}})};
 const context=vm.createContext({document,console,setTimeout(){},setInterval:callback=>callbacks.poll=callback});
 vm.runInContext(fs.readFileSync(__dirname+'/app.js','utf8').replace(/load\(\);\s*$/,''),context);
 context.request=action=>new Promise((resolve,reject)=>requests.push({action,resolve,reject}));
 vm.runInContext('api=request',context);
 return {context,document,node,callbacks,requests,run:code=>vm.runInContext(code,context)};
}
test('late response cannot render data in another tab',async()=>{
 const a=app(); a.context.received=[];a.run('render=r=>received.push(r)');
 const old=a.run("view='users';load()");const current=a.run("view='operations';load()");
 a.requests[1].resolve({backups:[],audit:[]});await current;
 a.requests[0].resolve({items:[]});await old;
 assert.equal(a.context.received.length,1);assert.ok(a.context.received[0].backups);
 assert.equal(a.run('cache.users'),undefined);
});
test('late error does not replace current tab',async()=>{
 const a=app();a.run('render=()=>{}');
 const old=a.run("view='users';load()");const current=a.run("view='operations';load()");
 a.requests[1].resolve({});await current;a.node('content').innerHTML='current page';
 a.requests[0].reject(Error('old request failed'));await old;
 assert.equal(a.node('content').innerHTML,'current page');
});
test('maintenance renders real schema and hides backup diagnostics by default',()=>{
 const a=app();a.context.data={backups:[],audit:[],logs:'',backup_status:{time:'2026-11-14T13:00:00Z',ok:true,output:'backup log'}};
 a.run('renderOperations(data)');const html=a.node('content').innerHTML;
 assert.match(html,/<details class="card" id="backup-diagnostics">/);
 assert.doesNotMatch(html,/<details[^>]*\bopen\b/);assert.ok(html.indexOf('backup-diagnostics')>html.indexOf('Viimased Samba logid'));
});
test('replication polling skips hidden pages, other tabs, dialogs and overlapping requests',async()=>{
 const a=app();a.run('render=()=>{}');a.callbacks.poll();assert.equal(a.requests.length,0);
 a.run("view='replication'");a.document.hidden=true;a.callbacks.poll();assert.equal(a.requests.length,0);
 a.document.hidden=false;a.document.querySelector=()=>({});a.callbacks.poll();assert.equal(a.requests.length,0);
 a.document.querySelector=()=>null;const pending=a.callbacks.poll();a.callbacks.poll();assert.equal(a.requests.length,1);
 a.requests[0].resolve({});await pending;
});
test('poll failure replaces stale health with unavailable state',async()=>{
 const a=app();a.run("view='replication'");a.node('content').innerHTML='green';const pending=a.callbacks.poll();
 a.requests[0].reject(Error('offline'));await pending;assert.match(a.node('content').innerHTML,/offline/);
 assert.doesNotMatch(a.node('content').innerHTML,/green/);
});
test('follower page shows coordinator automation and local role',()=>{
 const a=app();a.context.data={sysvol:{configured:true,healthy:true,local:{role:'peer',hostname:'dc2',acl:{ok:true}},peer:{hostname:'dc1',acl:{ok:true}},coordinator:{hostname:'dc1',automatic:true,last_sync:{}}}};
 const html=a.run('renderSysvol(data)');assert.match(html,/partner \(timer koordinaatoris\)/);assert.match(html,/Sees/);assert.match(html,/konkreetse kasutaja ligipääs/);
});
