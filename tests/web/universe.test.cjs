const test=require("node:test"),assert=require("node:assert/strict"),fs=require("node:fs"),vm=require("node:vm"),path=require("node:path");
test("Universe delegates to the client catalogue without rendering acquisition audits",async()=>{
  let loaded=false,rendered=false;
  const ctx={window:{AssetResearch:{async load(api,date){loaded=typeof api==="function"&&/^\d{4}-\d{2}-\d{2}$/.test(date);},render(){rendered=true;}}}};
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.resolve(__dirname,"../../apps/web/universe.js"),"utf8"),ctx);
  await ctx.window.UniverseView.load(async()=>({}));
  ctx.window.UniverseView.render();
  assert.ok(loaded);
  assert.ok(rendered);
});
