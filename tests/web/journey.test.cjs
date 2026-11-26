const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
function charts(){
  const window={RM:{language:"fr",t:k=>k}};
  const document={body:{},addEventListener(){}};
  vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,"../../apps/web/journey.js"),"utf8"),
    {window,document,MutationObserver:class{observe(){}}});
  return window.Journey;
}
test("client charts use measured values and preserve unavailable projections",()=>{
  const c=charts();
  assert.equal(c.timeline([1,NaN]),"");
  assert.match(c.timeline([1,1.14,.97]),/max="2"/);
  assert.match(c.composition({weights:{"USD cash":.7,"A<B":.3}}),/A&lt;B/);
  assert.equal(c.goals([{probability:null}]),"");
  assert.equal((c.goals([{objective_id:"OBJ10",probability:.37}]).match(/class="hit"/g)||[]).length,37);
  assert.match(c.range({objective_id:"OBJ10",due_date:"2036",wealth_quantiles:[80,100,130],target:120}),/120 USD/);
  assert.equal(c.map([{metrics:{vol:0,cagr:-.1}}]),"");
});
