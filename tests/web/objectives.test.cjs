const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
test('Goal research is mounted on the current confirmed save and rejects stale responses',async()=>{
  const host={innerHTML:''},button={};let release;
  const context={document:{getElementById:id=>id==='objectives-panel'?host:button},window:{RM:{language:'fr',t:k=>k}},Intl};
  vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,'../../apps/web/objectives.js'),'utf8'),context);
  const view=context.window.GoalsView;view.mount(null,()=>{});assert.match(host.innerHTML,/Confirmez d’abord/);
  view.mount({currency:'CHF',capital:100},()=>new Promise(r=>release=r));assert.match(host.innerHTML,/Simuler les objectifs confirmés/);
  const request=button.onclick();view.clear();release({references:[],required_returns:[],currency:'CHF'});await request;
  assert.match(host.innerHTML,/Confirmez d’abord/);assert.doesNotMatch(host.innerHTML,/Mêmes allocations/);
  view.mount({currency:'USD'},async()=>({references:[],required_returns:[],currency:'USD',first:'2007-01-01',last:'2025-12-31',training_count:178,test_count:45,paths:2000}));await button.onclick();assert.match(host.innerHTML,/2[0-9]{3} trajectoires/);assert.match(host.innerHTML,/Mêmes allocations/);
  context.window.RM.language='en';view.render();assert.match(host.innerHTML,/Same candidates, same scenarios/);
});
