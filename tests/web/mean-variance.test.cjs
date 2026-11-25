const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
test('Mean-variance result renders and cannot cross save sessions',async()=>{
 const nodes=new Map(),$=id=>{if(!nodes.has(id))nodes.set(id,{innerHTML:'',value:'',checked:false});return nodes.get(id);};const ctx={document:{getElementById:$},window:{RM:{language:'fr'}}};vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,'../../apps/web/mean-variance.js'),'utf8'),ctx);
 const view=ctx.window.MeanVarianceView;const form=()=>{for(const [id,v] of Object.entries({'mv-scope':'cohort','mv-currency':'USD','mv-cap':'5','mv-lambda':'3','mv-penalty':'.1','mv-cost':'10','mv-mean':'regularized'}))$(id).value=v;};
 let release;view.mount(()=>new Promise(r=>release=r),null);form();const pending=$('mv-run').onclick();view.clear();release({status:'infeasible',reason:'fixture'});await pending;assert.doesNotMatch($('mean-variance-panel').innerHTML,/fixture/);
 view.mount(async()=>({status:'infeasible',reason:'fixture'}),null);form();await $('mv-run').onclick();assert.match($('mean-variance-panel').innerHTML,/Contraintes irréalisables/);
 ctx.window.RM.language='en';view.render();assert.match($('mean-variance-panel').innerHTML,/Infeasible constraints/);
});
