/* Client mandate v2: synthetic, local-only form. No financial calculations in the UI. */
(() => {
  const form = document.getElementById("form");
  const t = key => window.RM.t(key);
  const dateISO = d => d.toISOString().slice(0, 10);
  const today = () => dateISO(new Date());
  const tenYears = () => { const d = new Date(); d.setUTCFullYear(d.getUTCFullYear() + 10); return dateISO(d); };
  const obj = Array.from({length:11}, (_,i)=>`OBJ${String(i+1).padStart(2,"0")}`);
  const limits = ["stress_loss","loss_budget","volatility","max_asset_weight","max_issuer_weight","max_sector_weight","max_turnover","max_cost","min_liquidity","gross_limit","net_min","net_max"];
  const assets = ["equity","treasury","reit","cash","commodity_etp","futures"];
  const knowledge = ["equity","treasury","futures","leverage","short"];
  const fields = ["capital","cash","investments","other_assets","debt","reserve","income_monthly","spending_monthly","contribution_monthly","withdrawal_monthly","loss_capacity_amount"];
  const label = (key, html) => `<label><span data-i18n="${key}">${t(key)}</span>${html}</label>`;
  const numeric = (key, value="", required=true, min=0, max="") => label(key,`<input name="${key}" type="number" step="any" min="${min}" ${max!==""?`max="${max}"`:""} value="${value}" ${required?"required":""}>`);
  const select = (name, keys) => `<select name="${name}">${keys.map(k=>`<option value="${k}" data-i18n="${k}">${t(k)}</option>`).join("")}</select>`;
  const check = (name, key, checked=false) => `<label class="mandate-check"><input type="checkbox" name="${name}" ${checked?"checked":""}><span data-i18n="${key}">${t(key)}</span></label>`;
  const section = (number, key, content, desc) => `<fieldset class="mandate-panel" data-mandate-section="${number}"><legend><span data-i18n="${key}">${t(key)}</span></legend>${desc?`<p class="muted" data-i18n="${desc}">${t(desc)}</p>`:""}${content}</fieldset>`;
  const grid = content => `<div class="mandate-grid">${content}</div>`;
  form.innerHTML = `<div class="mandate-intro"><p data-i18n="mandateLocal">${t("mandateLocal")}</p><button type="button" id="mandate-example" data-i18n="loadExample">${t("loadExample")}</button></div>` +
    section("01","mandateCurrency",grid(label("currency",select("currency",["USD","CHF"]))+label("as_of",`<input name="as_of" type="date" value="${today()}" required>`)+label("horizon_date",`<input name="horizon_date" type="date" value="${tenYears()}" required>`)+numeric("chf_per_usd","",false,0.000001)+numeric("inflation",2,false,-99,100))+`<p id="mandate-currency-note" class="muted"></p>`,"currencyHelp")+
    section("02","mandateWealth",grid(fields.slice(0,6).map(f=>numeric(f,0)).join("")),"wealthHelp")+
    section("03","mandateFlows",grid(fields.slice(6,10).map(f=>numeric(f,0)).join(""))+`<h3 data-i18n="datedFlows">${t("datedFlows")}</h3><div id="dated-flows"></div><button type="button" id="add-flow" data-i18n="addFlow">${t("addFlow")}</button>`,"flowHelp")+
    section("04","mandateGoals",`<p data-i18n="chooseGoals">${t("chooseGoals")}</p><div class="goal-picker">${obj.map(k=>`<button type="button" class="goal-choice" data-goal="${k}" aria-pressed="false" data-i18n="${k}">${t(k)}</button>`).join("")}</div><div id="goal-rows"></div><button type="button" id="add-goal" data-i18n="addGoal">${t("addGoal")}</button>`,"goalHelp")+
    section("05","mandateRisk",grid(numeric("loss_capacity_amount",0)+numeric("stress_loss",20,true,0,100)+numeric("loss_budget",20,true,0,100)),"riskHelp")+
    section("06","mandateKnowledge",`<h3 data-i18n="knowledgeLevel">${t("knowledgeLevel")}</h3>${grid(knowledge.map(f=>label(f,select(`knowledge_${f}`,["none","basic","advanced"]))).join(""))}<h3 data-i18n="experienceLevel">${t("experienceLevel")}</h3>${grid(knowledge.map(f=>label(f,select(`experience_${f}`,["none","limited","experienced"]))).join(""))}`,"knowledgeHelp")+
    section("07","mandateConstraints",`<h3 data-i18n="allowed_assets">${t("allowed_assets")}</h3>${grid(assets.map(f=>check(`asset_${f}`,f,!["futures","commodity_etp"].includes(f))).join(""))}<h3 data-i18n="permissions">${t("permissions")}</h3>${grid(["allow_short","allow_leverage","allow_derivatives"].map(f=>check(f,f)).join(""))}<h3 data-i18n="optionalLimits">${t("optionalLimits")}</h3><div class="mandate-grid">${limits.slice(2).map(f=>`<div class="mandate-limit">${numeric(f,"",false,f==="net_min"?-1000:0, ["gross_limit","net_min","net_max","max_turnover"].includes(f)?1000:100)}${label("constraintMode",select(`${f}_mode`,["hard","soft"]))}</div>`).join("")}</div>${grid(label("esg_exclusions",'<input name="esg_exclusions" maxlength="240">')+label("tax_assumption",select("tax_assumption",["not_modeled","pre_tax","after_tax_required"]))+label("fx_hedge",select("fx_hedge",["undecided","none","partial","full"])))}`,"constraintsHelp")+
    section("08","mandateReview",check("consent","mandateConsent")+`<button class="primary" type="submit" data-i18n="previewMandate">${t("previewMandate")}</button>`,"reviewHelp");
  const group = (root, name) => root.querySelector(`[name="${name}"]`);
  const read = (root, name) => group(root,name).value;
  const num = (root,name, optional=false) => { const value=read(root,name);return value===""?null:Number(value); };
  const checked = (root,name) => group(root,name).checked;
  const set = (root,name,value) => { const el=group(root,name); if(el.type==="checkbox")el.checked=Boolean(value);else el.value=value??""; };
  // Place investment objectives before flow details, and keep uncommon constraints expandable.
  const goalPanel=form.querySelector('[data-mandate-section="04"]');
  form.insertBefore(goalPanel,form.querySelector('[data-mandate-section="03"]'));
  for(const [number,key] of [["06","mandateKnowledge"],["07","mandateConstraints"]]){
    const panel=form.querySelector(`[data-mandate-section="${number}"]`);
    const details=document.createElement("details");details.className="mandate-advanced";
    const summary=document.createElement("summary");summary.dataset.i18n=key;summary.textContent=t(key);
    panel.parentNode.insertBefore(details,panel);details.append(summary,panel);
  }
  function updateCurrency(){
    const note=document.getElementById("mandate-currency-note");
    note.dataset.i18n=read(form,"currency")==="USD"?"matchingUsdReady":"matchingChfLimited";
    note.textContent=t(note.dataset.i18n);
  }
  function updateGoalPicker(){
    const selected=[...document.getElementById("goal-rows").children].map(r=>read(r,"objective_id"));
    form.querySelectorAll("[data-goal]").forEach(b=>b.setAttribute("aria-pressed",String(selected.includes(b.dataset.goal))));
  }
  function invalidate(){document.getElementById("mandate-report").hidden=true;}
  function addFlow(data={}){
    const row=document.createElement("div");row.className="mandate-row mandate-grid";
    row.innerHTML=label("flow_date",'<input name="date" type="date" required>')+label("flow_kind",select("kind",["contribution","withdrawal","liability"]))+numeric("flow_amount",0,true,0.01).replace('name="flow_amount"','name="amount"')+`<button type="button" data-i18n="removeRow">${t("removeRow")}</button>`;
    document.getElementById("dated-flows").append(row);
    set(row,"date",data.date||read(form,"horizon_date"));set(row,"kind",data.kind||"liability");set(row,"amount",data.amount??1000);
    row.querySelector("button").onclick=()=>{row.remove();invalidate();};invalidate();
  }
  function addGoal(data={}){
    if(document.getElementById("goal-rows").children.length>=11)return;
    const row=document.createElement("div");row.className="mandate-row mandate-grid mandate-goal";
    row.innerHTML=label("objective_id",select("objective_id",obj))+label("goal_due_date",'<input name="due_date" type="date" required>')+numeric("goal_amount","",false,0.01).replace('name="goal_amount"','name="amount"')+label("goal_currency",select("currency",["CHF","USD"]))+label("goal_basis",select("basis",["nominal","real"]))+numeric("priority",3,true,1,5)+numeric("shortfall_penalty",1,true,0,1000)+check("funding","funding")+`<button type="button" data-i18n="removeRow">${t("removeRow")}</button><p class="muted goal-help"></p>`;
    document.getElementById("goal-rows").append(row);
    const defaults={objective_id:"OBJ05",due_date:read(form,"horizon_date"),amount:null,currency:read(form,"currency"),basis:"nominal",priority:3,shortfall_penalty:1,funding:false};
    Object.entries({...defaults,...data}).forEach(([k,v])=>set(row,k,v));
    const updateHelp=()=>{const el=row.querySelector(".goal-help"),id=read(row,"objective_id"),key=id+"_help";el.dataset.i18n=key;el.textContent=t(key);
      const funding=group(row,"funding"),amount=group(row,"amount");
      funding.disabled=id==="OBJ09"||id==="OBJ10"||id==="OBJ02";
      if(id==="OBJ09"||id==="OBJ10"){funding.checked=true;amount.required=true;}else if(id==="OBJ02"){funding.checked=false;amount.required=false;}else amount.required=funding.checked;
      updateGoalPicker();
    };
    group(row,"objective_id").addEventListener("change",updateHelp);group(row,"funding").addEventListener("change",updateHelp);updateHelp();
    row.querySelector("button").onclick=()=>{row.remove();updateGoalPicker();invalidate();};invalidate();
  }
  function payload(){
    const values=Object.fromEntries(fields.map(k=>[k,num(form,k)]));
    const constraints=Object.fromEntries(limits.map(k=>[k,{value:num(form,k)===null?null:num(form,k)/100,mode:["stress_loss","loss_budget"].includes(k)?"hard":read(form,`${k}_mode`)}]));
    Object.assign(constraints,Object.fromEntries(["allow_short","allow_leverage","allow_derivatives"].map(k=>[k,checked(form,k)])),{allowed_assets:assets.filter(k=>checked(form,`asset_${k}`)),esg_exclusions:read(form,"esg_exclusions"),tax_assumption:read(form,"tax_assumption"),fx_hedge:read(form,"fx_hedge")});
    return {schema_version:"2.0.0",currency:read(form,"currency"),as_of:read(form,"as_of"),horizon_date:read(form,"horizon_date"),chf_per_usd:num(form,"chf_per_usd"),inflation:num(form,"inflation")===null?null:num(form,"inflation")/100,...values,
      dated_flows:[...document.getElementById("dated-flows").children].map(r=>({date:read(r,"date"),kind:read(r,"kind"),amount:num(r,"amount")})),
      goals:[...document.getElementById("goal-rows").children].map(r=>({objective_id:read(r,"objective_id"),due_date:read(r,"due_date"),amount:num(r,"amount"),currency:read(r,"currency"),basis:read(r,"basis"),priority:num(r,"priority"),shortfall_penalty:num(r,"shortfall_penalty"),funding:checked(r,"funding")})),
      knowledge:Object.fromEntries(knowledge.map(k=>[k,read(form,`knowledge_${k}`)])),experience:Object.fromEntries(knowledge.map(k=>[k,read(form,`experience_${k}`)])),constraints,consent:checked(form,"consent")};
  }
  function reset(){form.reset();document.getElementById("dated-flows").replaceChildren();document.getElementById("goal-rows").replaceChildren();updateGoalPicker();updateCurrency();invalidate();}
  function restore(m){
    reset();for(const k of [...fields,"currency","as_of","horizon_date","chf_per_usd","consent"])set(form,k,m[k]);
    set(form,"inflation",m.inflation===null?null:100*m.inflation);
    for(const k of limits){const limit=m.constraints[k];set(form,k,limit.value===null?null:100*limit.value);if(!["stress_loss","loss_budget"].includes(k))set(form,`${k}_mode`,limit.mode);}
    for(const k of assets)set(form,`asset_${k}`,m.constraints.allowed_assets.includes(k));
    for(const k of ["allow_short","allow_leverage","allow_derivatives","esg_exclusions","tax_assumption","fx_hedge"])set(form,k,m.constraints[k]);
    for(const k of knowledge){set(form,`knowledge_${k}`,m.knowledge[k]);set(form,`experience_${k}`,m.experience[k]);}
    document.getElementById("dated-flows").replaceChildren();m.dated_flows.forEach(addFlow);
    document.getElementById("goal-rows").replaceChildren();m.goals.forEach(addGoal);updateCurrency();invalidate();
  }
  function example(){reset();const sample={capital:100000,cash:125000,investments:25000,other_assets:50000,debt:20000,reserve:20000,income_monthly:7000,spending_monthly:4500,contribution_monthly:1000,withdrawal_monthly:0,loss_capacity_amount:20000,currency:"USD",inflation:2};Object.entries(sample).forEach(([k,v])=>set(form,k,v));document.getElementById("goal-rows").replaceChildren();addGoal({objective_id:"OBJ10",amount:240000,currency:"USD",funding:true});invalidate();}
  form.addEventListener("input",invalidate);form.addEventListener("change",invalidate);
  group(form,"currency").addEventListener("change",updateCurrency);
  group(form,"horizon_date").addEventListener("change",()=>{
    const end=read(form,"horizon_date");
    for(const row of document.getElementById("goal-rows").children)if(read(row,"due_date")>end)set(row,"due_date",end);
  });
  form.querySelectorAll("[data-goal]").forEach(button=>button.onclick=()=>{
    const id=button.dataset.goal,existing=[...document.getElementById("goal-rows").children].find(r=>read(r,"objective_id")===id);
    if(existing){existing.scrollIntoView({behavior:"smooth",block:"nearest"});return;}
    addGoal({objective_id:id,funding:id==="OBJ09"||id==="OBJ10"});
  });
  form.addEventListener("invalid",event=>{const parent=event.target.closest("details");if(parent)parent.open=true;},true);
  document.getElementById("add-flow").onclick=()=>addFlow();document.getElementById("add-goal").onclick=()=>addGoal();document.getElementById("mandate-example").onclick=example;
  reset();
  window.MandateForm={payload,reset,restore,example,limits,assets,knowledge};
})();
