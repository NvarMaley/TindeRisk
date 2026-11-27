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
  await button("Minimize historical volatility").onclick();
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

test("full mandate rejects a legacy deck even when HTTP succeeds",async()=>{
  const el={addEventListener(){},classList:{toggle(){}}};
  const ctx={document:{getElementById:()=>el,querySelectorAll:()=>[],addEventListener(){}},
    window:{RM:{t:k=>k}},fetch:async url=>({ok:true,json:async()=>url.endsWith("health")
      ?{matching_engine:"personalized-v3"}:[{version:"historical-usd-v1"}]})};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname,"../../apps/web/app.js"),"utf8"),ctx);
  await assert.rejects(vm.runInContext('fetchDeck({schema_version:"2.0.0"})',ctx),/serverOutdated/);
});

test("Explore explains the method, source and mandate fit for each returned card",()=>{
  const ids=new Map();
  const get=id=>{
    if(!ids.has(id))ids.set(id,{addEventListener(){},classList:{toggle(){}}});
    return ids.get(id);
  };
  const ctx={document:{getElementById:get,querySelectorAll:()=>[],addEventListener(){}},
    window:{RM:{language:"fr",t:k=>k}}};
  vm.createContext(ctx);
  for(const script of ["strategy-methods.js","app.js"]){
    vm.runInContext(fs.readFileSync(path.join(__dirname,"../../apps/web",script),"utf8"),ctx);
  }
  vm.runInContext(`
    mandate={capital:10000,max_stress_loss:.2};
    fullMandate={as_of:"2026-11-27"};
    portfolios=[
      {name:"minimum_variance", personalized:true, model_as_of:"2025-12-31", fit_risk_weight:.6,
        stress_loss:.08, stress_usd:800, weights:{SPY:1}, metrics:{cagr:.04}},
      {name:"factor_value", personalized:true, stress_loss:.1, stress_usd:1000, weights:{SPY:1}, metrics:{cagr:.05}},
    ];
    showPortfolio();
  `,ctx);
  let html=get("portfolio").innerHTML;
  assert.match(html,/Comment ça marche et pourquoi cette carte/);
  assert.match(html,/min wᵀΣw/);
  assert.match(html,/Départ du mandat simulé · <strong>2026-11-27/);
  assert.match(html,/Dernières données utilisées pour les poids · <strong>2025-12-31/);
  assert.match(html,/Effet de la date des données · Estimations du risque/);
  assert.match(html,/8\.0% pour une limite de 20\.0%/);
  assert.match(html,/Stratégies proposées pour ce mandat/);
  assert.match(html,/Factor Value/);
  vm.runInContext('window.RM.language="en"; swipes=["skip"]; showPortfolio()',ctx);
  html=get("portfolio").innerHTML;
  assert.match(html,/high book equity relative to market value/);
  assert.match(html,/Dated stock factor scores/);
  assert.doesNotMatch(html,/min wᵀΣw/);
});

test("portfolio result separates nominal, simulated net gain, present value and uncertainty",()=>{
  const ctx={window:{}};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(__dirname,"../../apps/web/portfolio-result.js"),"utf8"),ctx);
  const report={paths:1000,training_months:60,data_end:"2025-12-31",
    matched:{terminal_quantiles:[55,100,180],net_gain_quantiles:[-20,15,50],mean_net_gain:20,
      present_value:{rate:.03,terminal_quantiles:[48,85,125],net_gain_quantiles:[-24,8,35]},
      funded_goal_schedule:[{objective_id:"home",date:"2031-11-25",median_paid:80}],
      wealth_path:{dates:["2026-11-25","2031-11-25"],bands:[[90,90,90],[55,100,180]]},
      goals:[{objective_id:"home",due_date:"2031-11-25",target:80,probability:.78,expected_deficit:5}]},
    reference:{goals:[{probability:.62}]}};
  const html=ctx.window.PortfolioResult.projection(report,()=>"Apartment <home>",false);
  assert.match(html,/Median remaining balance/);
  assert.match(html,/Mean simulated net gain/);
  assert.match(html,/Median balance in present value/);
  assert.match(html,/Central 90% of scenarios/);
  assert.match(html,/Goal payment/);
  assert.match(html,/2025-12-31/);
  assert.match(html,/Apartment &lt;home&gt;/);
  assert.doesNotMatch(html,/>Apartment <home>/);
});
