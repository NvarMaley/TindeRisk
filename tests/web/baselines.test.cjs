const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
test('Baseline comparison renders independently and clears on save switch',async()=>{
  const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',value:''});return nodes.get(id);};
  const ctx={document:{getElementById:$},window:{RM:{language:'fr'}}};vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,'../../apps/web/baselines.js'),'utf8'),ctx);
  const view=ctx.window.BaselinesView,m={cagr:.04,max_drawdown:.1,annual_volatility:.12,annual_excess_ratio:.3,drawdown:[-.1],worst_month:-.1,worst_12_months:null};
  const row={id:'equal_weight_monthly',method:'equal_weight',frequency:'monthly',gross:m,net:m,annual_one_way_turnover:.2,stress_loss:.1,target_weights:{SPY:1},end_weights:{SPY:1},gross_final_nav:110,net_final_nav:109,fees:1,initial_fee:.1,ledger:[{end:'2025-12-31',twr_index:1.09,closing_weights:[1],opening_nav:100,pre_trade_nav:110,fee:1,traded_notional:2,net_nav:109,rebalance:false}],historical_stress:{},cost_sensitivity_cagr:{10:.04}};
  const data={start:'2024-01-01',end:'2025-12-31',months:24,currency:'CHF',cost_bps:10,reference:'BIL CHF',reference_is_cash_proxy:true,tickers:['SPY'],shock:{SPY:-.3},variants:[row],broad_reference:{status:'unavailable',reason:'fixture'}};
  let release;view.mount(()=>new Promise(r=>release=r),'CHF');$('baseline-currency').value='CHF';$('baseline-start').value='2007-01-01';$('baseline-cost').value='10';const pending=$('baseline-run').onclick();view.clear();release(data);await pending;assert.doesNotMatch($('baselines-panel').innerHTML,/Registre mensuel/);
  view.mount(async()=>data,'CHF');$('baseline-currency').value='CHF';$('baseline-start').value='2007-01-01';$('baseline-cost').value='10';await $('baseline-run').onclick();assert.match($('baselines-panel').innerHTML,/Registre mensuel/);assert.match($('baselines-panel').innerHTML,/Excédent \/ proxy trésorerie/);assert.match($('baselines-panel').innerHTML,/Équipondéré/);
  ctx.window.RM.language='en';view.render();assert.match($('baselines-panel').innerHTML,/Reconciled monthly ledger/);
});
