const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
function app(){
 const nodes=new Map(),requests=[];
 function node(id){if(!nodes.has(id))nodes.set(id,{value:'',innerHTML:'',textContent:'',dataset:{},classList:{add(){},remove(){},toggle(){}},setAttribute(){}});return nodes.get(id)}
 const context=vm.createContext({document:{getElementById:node,querySelectorAll:()=>[],addEventListener(){},createElement:()=>({textContent:'',get innerHTML(){return this.textContent}})},localStorage:{getItem:()=>'',setItem(){}},setInterval(){},clearInterval(){},setTimeout(){},clearTimeout(){}});
 vm.runInContext(fs.readFileSync(__dirname+'/app.js','utf8').replace(/load\(\);\s*$/,''),context);
 context.request=action=>new Promise((resolve,reject)=>requests.push({action,resolve,reject}));
 vm.runInContext('api=request',context);
 return {node,requests,run:code=>vm.runInContext(code,context)};
}
test('tabs are usable before the first PM2 snapshot is ready',()=>{
 const a=app();a.run("view='apps';render()");assert.match(a.node('content').innerHTML,/Rakendused/);assert.match(a.node('content').innerHTML,/Andmed laaditakse/);
});
test('changing user clears previous user actions before awaiting a new snapshot',async()=>{
 const a=app();a.run("selectedUser='alice';snapshot={summary:{total:1}};load=()=>{};");
 a.node('user-select').value='bob';a.node('user-select').onchange();
 assert.equal(a.run('selectedUser'),'bob');assert.equal(a.run('snapshot.summary'),undefined);
});
test('a late poll from another user cannot replace the current snapshot',async()=>{
 const a=app();const pending=a.run("selectedUser='alice';refreshSnapshot()");
 a.run("selectedUser='bob';snapshot={marker:'bob'}");a.requests[0].resolve({marker:'alice'});await pending;
 assert.equal(a.run('snapshot.marker'),'bob');
});
test('log responses are ignored after switching the log target',async()=>{
 const a=app();const pending=a.run("selectedUser='alice';view='logs';logTarget='1';refreshLogs()");
 a.run("logTarget='2';logText='current log'");a.requests[0].resolve({log:'old log'});await pending;
 assert.equal(a.run('logText'),'current log');
});
