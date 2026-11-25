const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

test("StockTwits research explicitly reports no current signal", async () => {
  const el={innerHTML:"",addEventListener(){}};
  const context={document:{getElementById:()=>el},window:{RM:{t:k=>k,language:"fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../../apps/web/sources.js"),"utf8"),context);
  await context.window.SourcesView.load(async key=>key==="sentiment"?{status:"historical_only",asset_count:753,eligible_count:1022,aligned_rows:61141,first:"2009-08-01",last:"2020-02-01",split:{test_start:"2018-03-29",test_end:"2020-04-30"},models:{ridge:{baseline:{rmse:.1},sentiment:{rmse:.099},rmse_improvement:.001,uncertainty:{conditional_block_interval:[-.01,.02]}}},factor:{test_months:26,mean_test_spread:-.004,mean_test_rank_ic:-.009}}:{rows:[]});
  assert.match(el.innerHTML,/StockTwits/);assert.match(el.innerHTML,/Aucun signal actuel/);assert.match(el.innerHTML,/Intervalle bootstrap/);
});

test("The Sources view shows audited evidence in the selected language", async () => {
  const report = { innerHTML: "", textContent: "" };
  const button = { addEventListener() {} };
  const context = {
    document: { getElementById: id => id === "sources-report" ? report : button },
    window: { RM: { t: key => key, language: "fr" } }
  };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, "../../apps/web/sources.js"), "utf8"), context);
  await context.window.SourcesView.load(async () => ({
    rows: [{ id: "FUTURES", name: "Futures", evidence: "Ten families", evidence_fr: "Dix familles" }]
  }));
  assert.match(report.innerHTML, /Dix familles/);
  context.window.RM.language = "en";
  context.window.SourcesView.render();
  assert.match(report.innerHTML, /Ten families/);
});

test("Local inventory counts and rights are shown in both languages", async () => {
  const el = {innerHTML: "", addEventListener() {}};
  const context = {document: {getElementById: () => el}, window: {RM: {t: k => k, language: "fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../apps/web/sources.js"), "utf8"), context);
  await context.window.SourcesView.load(async () => ({rows: [], inventory: {available: true, files: 11, providers: 3}}));
  assert.match(el.innerHTML, /11 versions de fichiers, 3 groupes/);
  assert.match(el.innerHTML, /droits WRDS/);
  context.window.RM.language = "en";
  context.window.SourcesView.render();
  assert.match(el.innerHTML, /11 file versions, 3 source groups/);
});

test("Point-in-time quality panel displays blocked historical approval", async () => {
  const el = {innerHTML: "", addEventListener() {}};
  const context = {document: {getElementById: () => el}, window: {RM: {t: k => k, language: "fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../apps/web/sources.js"), "utf8"), context);
  await context.window.SourcesView.load(async endpoint => endpoint === "snapshot" ?
    {approved: false, datasets: [{dataset:"fixture",rows:3,quality:{missing_return:1}}]} : {rows: []});
  assert.match(el.innerHTML, /Qualité et données historiques/);
  assert.match(el.innerHTML, /Rendement manquant: 1/);
  assert.match(el.innerHTML, /bloqués/);
  context.window.RM.language = "en";
  context.window.SourcesView.render();
  assert.match(el.innerHTML, /Missing return: 1/);
});

test("Return coverage distinguishes price and total returns", async () => {
  const el = {innerHTML: "", addEventListener() {}};
  const context = {document: {getElementById: () => el}, window: {RM: {t: k => k, language: "fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname, "../../apps/web/sources.js"), "utf8"), context);
  await context.window.SourcesView.load(async endpoint => endpoint === "returns" ?
    {approved:false,datasets:[{dataset:"fixture",rows:4,price_returns:3,total_returns:0,chf_price_returns:2,chf_total_returns:0}]} : {rows:[]});
  assert.match(el.innerHTML,/Rendements et devises/);
  assert.match(el.innerHTML,/3 \/ 0/);
  assert.match(el.innerHTML,/75%/);
  context.window.RM.language="en";
  context.window.SourcesView.render();
  assert.match(el.innerHTML,/Returns and FX/);
});

test("Forecast coverage distinguishes computed and unavailable catalogue assets",async()=>{
  const el={innerHTML:"",addEventListener(){}};
  const context={document:{getElementById:()=>el},window:{RM:{t:k=>k,language:"fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../../apps/web/sources.js"),"utf8"),context);
  await context.window.SourcesView.load(async endpoint=>endpoint==="forecast/universe"?
    {status:"complete",catalogue_count:2,statuses:{computed:1,unavailable:1},by_category:{stock:{computed:1,unavailable:1}}}:{rows:[]});
  assert.match(el.innerHTML,/Couverture des prévisions/);
  assert.match(el.innerHTML,/2 actifs examinés/);
  assert.match(el.innerHTML,/1 calculés avec les dix modèles/);
});

test("Risk coverage reports regular and descriptive profiles",async()=>{
  const el={innerHTML:"",addEventListener(){}},context={document:{getElementById:()=>el},window:{RM:{t:k=>k,language:"fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../../apps/web/sources.js"),"utf8"),context);
  await context.window.SourcesView.load(async endpoint=>endpoint==="risk/universe"?
    {status:"complete",catalogue_count:2,statuses:{computed:1,descriptive_only:1},cohorts:[]}:{rows:[]});
  assert.match(el.innerHTML,/Volatilité et covariance/);
  assert.match(el.innerHTML,/1 descriptifs uniquement/);
});

test("Factor coverage distinguishes empirical and analytical references",async()=>{
  const el={innerHTML:"",addEventListener(){}},context={document:{getElementById:()=>el},window:{RM:{t:k=>k,language:"fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../../apps/web/sources.js"),"utf8"),context);
  await context.window.SourcesView.load(async endpoint=>endpoint==="factors/universe"?
    {status:"complete",catalogue_count:2,statuses:{computed:1,analytical_reference:1},taxonomy:{market:"market"}}:{rows:[]});
  assert.match(el.innerHTML,/Facteurs et régressions/);
  assert.match(el.innerHTML,/1 références analytiques/);
});

test("Universe research renders the asset library and opens an explained statistical profile", async () => {
  const elements=new Map();
  let savedFallback=false;
  const defaults={"research-start":"2025-01-01","research-end":"2025-01-02","research-currency":"USD","research-kind":"total_return"};
  const get=id=>{if(!elements.has(id))elements.set(id,{innerHTML:"",value:defaults[id]||"",querySelectorAll(){return [];},scrollIntoView(){}});return elements.get(id);};
  const context={document:{getElementById:get},window:{RM:{t:k=>k,language:"fr"}}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"../../apps/web/asset-research.js"),"utf8"), context);
  await context.window.AssetResearch.load(async (endpoint, payload)=>{
    if(endpoint==="statistics/catalog")return {items:[{id:"asset-a",name:"Asset A",ticker:"A",category:"equity_etf",provider:"Fixture source",series:[{source:"listed_daily",instrument:"A",frequency:"daily",kinds:["total_return"],first:"2025-01-01",last:"2025-01-02"}]},{id:"asset-b",name:"Asset B",ticker:"B",category:"stock",provider:"Fixture source",series:[]}]};
    if(endpoint==="statistics/compare")return {assets:[{source:"listed_daily",instrument:"A",statistics:{count:2,missing:0,mean:.01},distribution:{histogram:[],cdf:[],qq:[]}}],matrix:{count:2,psd:true,covariance:[[.01]],pearson:[[1]],spearman:[[1]]},frequency:"daily",currency:"USD"};
    if(endpoint==="forecast"){
      assert.equal(payload.include_ml,true);
      return {selected_model:"historic",split:{train:60,validation:20,test:20},models:Object.fromEntries(["historic","random_forest","xgboost","neural_network"].map(name=>[name,{expected_return:.01,interval:[-.02,.03],history:[["2025-01-02",.02,.01,-.02,.03]],test:{mse:.0001,mae:.01,directional_accuracy:1,interval_coverage:1,net_strategy_mean:.019}}])),unavailable:{}};
    }
    if(endpoint==="forecast/universe/asset"){
      assert.equal(payload.id,"asset-a");
      if(savedFallback)return {status:"fallback",estimate:{method:"indicative_ytm",units:"annual yield",value:.04,as_of:"2025-01-02",source:"fixture",currency:"USD"}};
      return {status:"computed",source:"fixture",last:"2025-01-02",forecast:{selected_model:"historical",frequency:"monthly",currency:"USD",kind:"total_return",split:{train:60,validation:20,test:20},models:{historical:{expected_return:.01,interval:[-.02,.03],history:[["2025-01-02",.02,.01,-.02,.03]],test:{mse:.0001,mae:.01,directional_accuracy:1,interval_coverage:1,net_strategy_mean:.019}}},unavailable:{}}};
    }
    if(endpoint==="risk/universe/asset")return {status:"computed",frequency:"daily",kind:"total_return",currency:"USD",risk:{
      selected_model:"ewma",split:{train:60,validation:20,test:20},models:{ewma:{annualized_volatility:.2,
      test:{qlike:1,mse:.01},history:[["2025-01-02",.2,.1]]}},unavailable:{}}};
    if(endpoint==="factors/universe/asset")return {status:"computed",frequency:"monthly",currency:"USD",kind:"total_return",models:{capm:{
      factor_names:["Mkt-RF"],beta:{"Mkt-RF":1.2},ridge:{beta:{"Mkt-RF":1.1}},hac_se:{"Mkt-RF":.1},hac_p:{"Mkt-RF":.01},vif:{"Mkt-RF":1},
      first:"2020-01-01",last:"2025-01-01",observations:60,r_squared:.7,alpha:.001,implied_total_reference:.01,
      rolling:[["2025-01-01",1.2]],attribution:{alpha:.001,mean_factor_contribution:{"Mkt-RF":.01},mean_residual:0,mean_realized_excess:.011},
      factor_risk:{systematic_variance:.001,residual_variance:.0002},test:{mse:.001}}},unavailable:{}};
    return {rows:[]};
  },"2025-01-02");
  assert.match(get("universe-statistics").innerHTML,/Catalogue/);
  assert.match(get("universe-statistics").innerHTML,/Asset A/);
  assert.doesNotMatch(get("universe-statistics").innerHTML,/classement local|3'658/);
  await context.window.AssetResearch.open("asset-a");
  assert.match(get("universe-statistics").innerHTML,/Retour au catalogue/);
  assert.match(get("universe-statistics").innerHTML,/Moyenne arithmétique/);
  assert.match(get("universe-statistics").innerHTML,/1.00%/);
  assert.match(get("universe-statistics").innerHTML,/Dépendance temporelle/);
  assert.doesNotMatch(get("universe-statistics").innerHTML,/catalog-card/);
  assert.match(get("universe-statistics").innerHTML,/Calculer les prévisions/);
  assert.match(get("universe-statistics").innerHTML,/id="forecast-advanced" checked/);
  get("forecast-advanced").checked=true;
  await get("forecast-run").onclick();
  assert.match(get("universe-statistics").innerHTML,/Prévision prochaine période/);
  assert.match(get("universe-statistics").innerHTML,/Rendements réalisés \(test\)/);
  assert.match(get("universe-statistics").innerHTML,/Random Forest/);
  assert.match(get("universe-statistics").innerHTML,/XGBoost/);
  assert.match(get("universe-statistics").innerHTML,/Réseau neuronal/);
  await get("risk-saved").onclick();
  assert.match(get("universe-statistics").innerHTML,/Volatilité annualisée prévue/);
  await get("factor-run").onclick();
  assert.match(get("universe-statistics").innerHTML,/Expositions factorielles/);
  assert.match(get("universe-statistics").innerHTML,/Bêta glissant/);
  assert.match(get("universe-statistics").innerHTML,/20.00%/);
  await get("forecast-batch").onclick();
  assert.match(get("universe-statistics").innerHTML,/Calcul global enregistré/);
  savedFallback=true;
  await get("forecast-batch").onclick();
  assert.match(get("universe-statistics").innerHTML,/Rendement actuariel indicatif/);
  assert.match(get("universe-statistics").innerHTML,/4.00%/);
  await context.window.AssetResearch.open("asset-b");
  assert.match(get("universe-statistics").innerHTML,/Aucune série statistique exploitable/);
});
