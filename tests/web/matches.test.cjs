const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");

test("liked cards feed manual and optimized budgets, confirmation and the local snapshot",async()=>{
  const ids=new Map(),requests=[],downloads=[];
  function element(tag){
    return {tag,children:[],dataset:{},validity:{valid:true},isConnected:true,innerHTML:"",textContent:"",
      classList:{toggle(){}},append(...nodes){this.children.push(...nodes);},
      replaceChildren(){this.children=[];},insertAdjacentHTML(_,html){this.innerHTML+=html;},addEventListener(){},click(){if(tag==="a")downloads.push(this.download);}};
  }
  const get=id=>{if(!ids.has(id))ids.set(id,element(id));return ids.get(id);};
  const doc={body:{dataset:{}},getElementById:get,createElement:element,addEventListener(){},dispatchEvent(){},querySelectorAll:()=>[]};
  const metrics={cagr:.02,vol:.03,drawdown:-.05,es95_monthly:.01};
  const cards=["AAA","BBB"].map(name=>({name,metrics,weights:{SPY:1},version:"historical-fixture",stress_loss:.1,stress_usd:100,period:"test",costs:"10 bp"}));
  const ctx={document:doc,window:{RM:{language:"en",t:k=>k}},Event:class{},Blob,Uint8Array,atob,
    URL:{createObjectURL:()=>"blob:fixture",revokeObjectURL(){}},setTimeout:fn=>fn(),fetch:async(url,opts)=>{
    const body=JSON.parse(opts.body);requests.push({url,body});
    const optimized=url.endsWith("optimize");
    const data=url.endsWith("/cards")?cards:url.endsWith("/dynamic")?{policies:{static:{status:"computed",cagr:.03,volatility:.02,drawdown:-.01,expected_shortfall:.01,annual_turnover:.1,fees:2,ledger:[]}}}:url.endsWith("/paper/export")?{archive:"UEs=",filename:"RiskMatch-fixture.zip"}:{...cards[0],budgets:{AAA:optimized?.3:.6,BBB:optimized?.7:.4},risk_contributions:{AAA:.01,BBB:.02}};
    return {ok:true,json:async()=>data};
  }};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,"../../apps/web/app.js"),"utf8"),ctx);
  const run=expr=>vm.runInContext(expr,ctx);
  run('setSaveSession(true);mandate={capital:1000,max_stress_loss:.2,currency:"USD",years:10}');
  await run("loadPortfolios()");
  run('swipe("like");swipe("like");page("matches")');
  const panel=get("match-allocation").children[0],labels=panel.children.filter(x=>x.tag==="label");
  labels[0].children[0].value="60";labels[1].children[0].value="40";
  const button=text=>panel.children.find(x=>x.textContent===text);
  await button("Evaluate allocation").onclick();
  assert.deepEqual(requests.at(-1).body.budgets,[.6,.4]);
  assert.equal(run("simulationSnapshot().savedBlend.budgets.AAA"),.6);
  await button("Optimize risk").onclick();
  assert.equal(labels[0].children[0].value,30);
  const output=panel.children.at(-1);await output.children.at(-1).onclick();
  assert.equal(requests.at(-1).url,"/api/match-allocations/evaluate");
  assert.equal(run("simulationSnapshot().savedBlend.paperConfirmed"),true);
  const dynamic=get("match-allocation").children[1];
  await dynamic.children.find(x=>x.textContent==="Simulate policies").onclick();
  assert.equal(requests.at(-1).url,"/api/dynamic");
  const dynamicResult=dynamic.children.at(-1);
  await dynamicResult.children.find(x=>x.textContent==="Export paper simulation ZIP").onclick();
  assert.equal(requests.at(-1).url,"/api/paper/export");
  assert.equal(requests.at(-1).body.policy,"static");
  assert.deepEqual(downloads,["RiskMatch-fixture.zip"]);
});

test("outdated matching server does not prevent restoring a save or erase its choices",async()=>{
  const ids=new Map();
  const get=id=>{
    if(!ids.has(id))ids.set(id,{children:[],dataset:{},classList:{toggle(){}},replaceChildren(){},append(){},addEventListener(){}});
    return ids.get(id);
  };
  let outdated=true;
  const deck=[{name:"A",version:"fixture",weights:{SPY:1},metrics:{cagr:0,vol:0,drawdown:0,es95_monthly:0},stress_loss:0,stress_usd:0}];
  const mandate={capital:1000,currency:"USD"};
  const ctx={window:{RM:{language:"fr",t:k=>k},MandateForm:{restore(){},reset(){}}},
    document:{getElementById:get,body:{dataset:{}},querySelectorAll:()=>[],addEventListener(){},dispatchEvent(){},createElement:()=>get("element")},
    Event:class{},fetch:async url=>{
      if(url.endsWith("mandate/preview"))return {ok:true,json:async()=>({status:"structurally_valid",demo_eligible:true,horizon_years:10,effective_stress_limit:.2})};
      return {ok:!outdated,json:async()=>outdated?{error:"Not found"}:deck};
    }};
  vm.createContext(ctx);vm.runInContext(fs.readFileSync(path.join(__dirname,"../../apps/web/app.js"),"utf8"),ctx);
  ctx.fixture={version:1,mandate:{capital:1000,years:10,max_stress_loss:.2},fullMandate:mandate,index:0,answers:{},swipes:["like"],historicalDeck:true,deckIds:[["A","fixture"]],activePage:"matches",savedBlend:{paperConfirmed:true}};
  assert.equal(await vm.runInContext("restoreSimulation(fixture)",ctx),"home");
  await vm.runInContext('enterSavedStudio("home")',ctx);
  assert.equal(vm.runInContext("sessionUnlocked",ctx),true);
  assert.equal(vm.runInContext("simulationSnapshot().swipes[0]",ctx),"like");
  assert.equal(vm.runInContext("simulationSnapshot().savedBlend.paperConfirmed",ctx),true);
  outdated=false;
  await vm.runInContext("loadPortfolios()",ctx);
  assert.equal(vm.runInContext("shortlist[0].name",ctx),"A");
  assert.equal(vm.runInContext("pendingDeck",ctx),null);
});
