const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function app(){
 const nodes=new Map(),callbacks={},requests=[];
 const node=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',textContent:'',value:'',dataset:{},open:false,disabled:false,classList:{toggle(){},add(){},remove(){}},setAttribute(){},focus(){},showModal(){this.open=true},close(){this.open=false}});return nodes.get(id)};
 const document={hidden:false,getElementById:node,querySelectorAll:()=>[],querySelector:()=>null,
  addEventListener:(event,callback)=>callbacks[event]=callback,
  createElement:()=>({textContent:'',get innerHTML(){return this.textContent}})};
 const context=vm.createContext({document,console,setTimeout(){},clearTimeout(){},setInterval:callback=>callbacks.poll=callback});
 vm.runInContext(fs.readFileSync(__dirname+'/app.js','utf8').replace(/load\(\);\s*$/,''),context);
 context.request=(action,data)=>new Promise((resolve,reject)=>requests.push({action,data,resolve,reject}));
 vm.runInContext('api=request',context);
 return {context,document,node,callbacks,requests,run:code=>vm.runInContext(code,context)};
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('an uncached tab displays its heading and loading state before data arrives',async()=>{
 const a=app();const pending=a.run("switchView('users')");
 assert.match(a.node('content').innerHTML,/<h2>Kasutajad<\/h2>/);
 assert.match(a.node('content').innerHTML,/laadimine/);
 assert.match(a.node('content').innerHTML,/Lisa kasutaja/);
 a.requests[0].resolve({items:[]});await flush();
 assert.match(a.node('content').innerHTML,/Kirjeid pole/);
});
test('late response cannot render data in another tab and remains reusable in its own tab',async()=>{
 const a=app();const old=a.run("view='users';load()");const current=a.run("view='groups';load()");
 a.requests[1].resolve({items:[{name:'CurrentGroup'}]});await current;
 a.requests[0].resolve({items:[{name:'OldUser'}]});await old;
 assert.match(a.node('content').innerHTML,/CurrentGroup/);assert.doesNotMatch(a.node('content').innerHTML,/OldUser/);
 a.run("switchView('users')");assert.match(a.node('content').innerHTML,/OldUser/);assert.equal(a.requests.length,2);
});
test('late error does not replace current tab',async()=>{
 const a=app();const old=a.run("view='users';load()");const current=a.run("view='groups';load()");
 a.requests[1].resolve({items:[]});await current;const html=a.node('content').innerHTML;
 a.requests[0].reject(Error('old request failed'));await old;assert.equal(a.node('content').innerHTML,html);
});
test('cached data stays visible while a forced refresh is pending',async()=>{
 const a=app();let pending=a.run("view='users';load()");a.requests[0].resolve({items:[{name:'Alice'}]});await pending;
 pending=a.run('load(true)');assert.match(a.node('content').innerHTML,/Alice/);
 a.requests[1].resolve({items:[{name:'Bob'}]});await pending;assert.match(a.node('content').innerHTML,/Bob/);
});
test('duplicate tab opens reuse the same in-flight request',async()=>{
 const a=app();const first=a.run("view='users';load()");const second=a.run('load()');
 assert.equal(a.requests.length,1);a.requests[0].resolve({items:[]});await Promise.all([first,second]);
});
test('a replaced request cannot overwrite a newer refresh',async()=>{
 const a=app();const first=a.run("view='users';load()");const second=a.run('load(true)');
 a.requests[1].resolve({items:[{name:'New'}]});await second;a.requests[0].resolve({items:[{name:'Old'}]});await first;
 assert.match(a.node('content').innerHTML,/New/);assert.doesNotMatch(a.node('content').innerHTML,/>Old</);
});
test('overview sections render independently when domain RPC is slow',async()=>{
 const a=app();const pending=a.run("view='overview';load()");assert.equal(a.requests.length,4);
 a.requests.find(r=>r.data.section==='counts').resolve({counts:{users:7,disabled:0,groups:3,computers:2,zones:1}});await flush();
 assert.match(a.node('content').innerHTML,/Kasutajaid/);assert.match(a.node('content').innerHTML,/>7</);
 assert.match(a.node('content').innerHTML,/FSMO rollid laadimine/);
 a.requests.find(r=>r.data.section==='identity').resolve({domain:{realm:'EXAMPLE',dc:'DC1'},service:{active:true}});
 a.requests.find(r=>r.data.section==='replication').resolve({replication:{healthy:true,partitions:5,failures:0}});
 a.requests.find(r=>r.data.section==='roles').reject(Error('RPC timeout'));await pending;
 assert.match(a.node('content').innerHTML,/EXAMPLE/);assert.match(a.node('content').innerHTML,/RPC timeout/);assert.match(a.node('content').innerHTML,/data-retry="roles"/);
});
test('retry reloads only the failed section',async()=>{
 const a=app();const pending=a.run("view='replication';load()");
 a.requests[0].resolve({healthy:true,partitions:5,failures:0});a.requests[1].reject(Error('SSH failed'));await pending;
 const retry=a.run("load(true,false,'sysvol')");assert.equal(a.requests.length,3);assert.equal(a.requests[2].data.section,'sysvol');
 a.requests[2].resolve({sysvol:{configured:false}});await retry;assert.match(a.node('content').innerHTML,/AD andmebaas korras/);
});
test('maintenance renders the real schema and hides backup diagnostics by default',()=>{
 const a=app();a.context.data={backups:[],audit:[],logs:'',backup_status:{time:'2026-11-14T13:00:00Z',ok:true,output:'backup log'}};
 a.run("view='operations';states.operations={summary:{ready:true},logs:{ready:true}};renderOperations(data)");const html=a.node('content').innerHTML;
 assert.match(html,/<details class="card" id="backup-diagnostics">/);assert.doesNotMatch(html,/<details[^>]*\bopen\b/);assert.ok(html.indexOf('backup-diagnostics')>html.indexOf('Viimased Samba logid'));
});
test('replication polling skips hidden pages, other tabs, dialogs and overlapping requests',async()=>{
 const a=app();a.callbacks.poll();assert.equal(a.requests.length,0);
 a.run("view='replication'");a.document.hidden=true;a.callbacks.poll();assert.equal(a.requests.length,0);
 a.document.hidden=false;a.document.querySelector=()=>({});a.callbacks.poll();assert.equal(a.requests.length,0);
 a.document.querySelector=()=>null;const pending=a.callbacks.poll();a.callbacks.poll();assert.equal(a.requests.length,2);
 a.requests[0].resolve({});a.requests[1].resolve({sysvol:{configured:false}});await pending;
});
test('a failed poll replaces stale AD health but keeps the independent SYSVOL result',async()=>{
 const a=app();let pending=a.run("view='replication';load()");
 a.requests[0].resolve({healthy:true,partitions:5,failures:0});a.requests[1].resolve({sysvol:{configured:false}});await pending;
 pending=a.callbacks.poll();a.requests[2].reject(Error('offline'));a.requests[3].resolve({sysvol:{configured:false}});await pending;
 assert.match(a.node('content').innerHTML,/offline/);assert.doesNotMatch(a.node('content').innerHTML,/AD andmebaas korras/);assert.match(a.node('content').innerHTML,/SYSVOL-i sünkroonimine/);
});
test('detail dialogs open immediately and a closed dialog is not reopened by a late response',async()=>{
 const a=app();const pending=a.run("view='users';details('Alice')");assert.equal(a.node('detail-dialog').open,true);assert.match(a.node('detail-content').innerHTML,/Laen/);
 a.node('detail-dialog').close();a.requests[0].resolve({attributes:{name:'Alice'}});await pending;assert.equal(a.node('detail-dialog').open,false);
});
test('follower page shows coordinator automation and local role',()=>{
 const a=app();a.context.data={sysvol:{configured:true,healthy:true,local:{role:'peer',hostname:'dc2',acl:{ok:true}},peer:{hostname:'dc1',acl:{ok:true}},coordinator:{hostname:'dc1',automatic:true,last_sync:{}}}};
 const html=a.run('renderSysvol(data)');assert.match(html,/partner \(timer koordinaatoris\)/);assert.match(html,/Sees/);assert.match(html,/konkreetse kasutaja ligipääs/);
});
