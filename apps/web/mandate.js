/* Client mandate v2: synthetic, local-only form. No financial calculations in the UI. */
(() => {
  const form = document.getElementById("form");
  const t = key => window.RM.t(key);
  const dateISO = d => d.toISOString().slice(0, 10);
  const today = () => dateISO(new Date());
  const tenYears = () => { const d = new Date(); d.setUTCFullYear(d.getUTCFullYear() + 10); return dateISO(d); };
  const obj = Array.from({length:11}, (_,i)=>`OBJ${String(i+1).padStart(2,"0")}`);
  const limits = ["stress_loss","loss_budget","volatility","max_asset_weight","max_issuer_weight","max_sector_weight","max_turnover","max_cost","min_liquidity","gross_limit","net_min","net_max"];
  const assets = ["equity","treasury","reit","cash","commodity_etp"];
  const editableLimits = ["volatility","max_asset_weight"];
  let legacyMandate = null;
  const knowledge = ["equity","treasury","futures","leverage","short"];
  const fields = ["capital","cash","investments","other_assets","debt","reserve","income_monthly","spending_monthly","contribution_monthly","withdrawal_monthly","loss_capacity_amount"];
  const help = key => `<details class="field-info"><summary aria-label="${t("fieldInfo")}" data-i18n-label="fieldInfo">i</summary><p data-i18n="field_${key}">${t("field_"+key)}</p></details>`;
  const label = (key, html, optional=false) => `<div class="mandate-field"><label><span data-i18n="${key}">${t(key)}</span>${optional?` <small class="field-optional" data-i18n="fieldOptional">${t("fieldOptional")}</small>`:""}${html}</label>${help(key)}</div>`;
  const numeric = (key, value="", required=true, min=0, max="") => label(key,`<input name="${key}" type="number" step="${key==="priority"?"1":"any"}" min="${min}" ${max!==""?`max="${max}"`:""} value="${value}" ${required?"required":""}>`,!required);
  const select = (name, keys) => `<select name="${name}">${keys.map(k=>`<option value="${k}" data-i18n="${k}">${t(k)}</option>`).join("")}</select>`;
  const check = (name, key, checked=false) => `<div class="mandate-field"><label class="mandate-check"><input type="checkbox" name="${name}" ${checked?"checked":""}><span data-i18n="${key}">${t(key)}</span></label>${help(key)}</div>`;
  const section = (number, key, content, desc) => `<fieldset class="mandate-panel" data-mandate-section="${number}"><legend><span data-i18n="${key}">${t(key)}</span></legend>${desc?`<p class="muted" data-i18n="${desc}">${t(desc)}</p>`:""}${content}</fieldset>`;
  const grid = content => `<div class="mandate-grid">${content}</div>`;
  form.innerHTML = `<div class="mandate-intro"><p data-i18n="mandateLocal">${t("mandateLocal")}</p><button type="button" id="mandate-example" data-i18n="loadExample">${t("loadExample")}</button></div>` +
    section("01","mandateCurrency",grid(`<input name="currency" type="hidden" value="USD">`+label("as_of",`<input name="as_of" type="date" value="${today()}" required>`)+label("horizon_date",`<input name="horizon_date" type="date" value="${tenYears()}" required>`)+`<div id="mandate-fx" hidden>${numeric("chf_per_usd","",false,0.000001)}</div>`+numeric("inflation",2,false,-99,100))+`<p id="mandate-currency-note" class="muted"></p>`,"currencyHelp")+
    section("02","mandateWealth",grid(fields.slice(0,6).map(f=>numeric(f,0,["capital","cash"].includes(f),f==="capital"?.01:0)).join("")),"wealthHelp")+
    section("03","mandateFlows",grid(fields.slice(6,10).map(f=>numeric(f,0,false)).join(""))+`<h3 data-i18n="datedFlows">${t("datedFlows")}</h3><div id="dated-flows"></div><button type="button" id="add-flow" data-i18n="addFlow">${t("addFlow")}</button>`,"flowHelp")+
    section("04","mandateGoals",`<p data-i18n="chooseGoals">${t("chooseGoals")}</p><div class="goal-picker">${obj.map(k=>`<button type="button" class="goal-choice" data-goal="${k}" aria-pressed="false" data-i18n="${k}">${t(k)}</button>`).join("")}</div><div id="goal-rows"></div><button type="button" id="add-goal" data-i18n="addGoal">${t("addGoal")}</button>`,"goalHelp")+
    section("05","mandateRisk",grid(numeric("loss_capacity_amount",0)+numeric("stress_loss",20,true,0,100)),"riskHelp")+
    section("07","mandateConstraints",`<h3 data-i18n="allowed_assets">${t("allowed_assets")}</h3>${grid(assets.map(f=>check(`asset_${f}`,f,f!=="commodity_etp")).join(""))}
      <div id="mandate-derivatives" hidden>${check("allow_derivatives","allow_derivatives")}
        <div id="mandate-derivatives-experience" hidden>${grid(label("derivativesKnowledge",select("knowledge_futures",["none","basic","advanced"]))+label("derivativesExperience",select("experience_futures",["none","limited","experienced"])))}</div>
      </div>
      <h3 data-i18n="optionalLimits">${t("optionalLimits")}</h3><div class="mandate-grid">${editableLimits.map(f=>`<div class="mandate-limit">${numeric(f,"",false,0,100)}${label("constraintMode",select(`${f}_mode`,["hard","soft"]))}</div>`).join("")}</div>`,"constraintsHelp")+
    `<div id="mandate-legacy" hidden><p class="muted" data-i18n="legacyMandateRestrictions">${t("legacyMandateRestrictions")}</p><button type="button" id="clear-legacy-mandate" data-i18n="clearLegacyMandate">${t("clearLegacyMandate")}</button></div>`+
    section("08","mandateReview",check("consent","mandateConsent")+`<button class="primary" type="submit" data-i18n="previewMandate">${t("previewMandate")}</button>`,"reviewHelp");
  const group = (root, name) => root.querySelector(`[name="${name}"]`);
  const read = (root, name) => group(root,name).value;
  const num = (root,name, optional=false) => { const value=read(root,name);return value===""?null:Number(value); };
  const checked = (root,name) => group(root,name).checked;
  const set = (root,name,value) => { const el=group(root,name); if(el.type==="checkbox")el.checked=Boolean(value);else el.value=value??""; };
  // Place investment objectives before flow details, and keep uncommon constraints expandable.
  const goalPanel=form.querySelector('[data-mandate-section="04"]');
  form.insertBefore(goalPanel,form.querySelector('[data-mandate-section="03"]'));
  for(const [number,key] of [["07","mandateConstraints"]]){
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
  function updateConditionalFields(){
    const goals=[...document.getElementById("goal-rows").children];
    const hasAmount=row=>num(row,"amount")!==null;
    for(const row of goals){
      const show=hasAmount(row);
      for(const name of ["currency","basis","shortfall_penalty"]){
        const field=group(row,name);
        field.closest(".mandate-field").hidden=!show;
        field.disabled=!show;
      }
    }
    const fxRequired=goals.some(row=>hasAmount(row)&&read(row,"currency")!==read(form,"currency"));
    document.getElementById("mandate-fx").hidden=!fxRequired;
    group(form,"chf_per_usd").required=fxRequired;
    group(form,"chf_per_usd").disabled=!fxRequired;
    const commodities=checked(form,"asset_commodity_etp");
    document.getElementById("mandate-derivatives").hidden=!commodities;
    document.getElementById("mandate-derivatives-experience").hidden=
      !commodities||!checked(form,"allow_derivatives");
  }
  function updateGoalPicker(){
    const selected=[...document.getElementById("goal-rows").children].map(r=>read(r,"objective_id"));
    form.querySelectorAll("[data-goal]").forEach(b=>b.setAttribute("aria-pressed",String(selected.includes(b.dataset.goal))));
  }
  function invalidate(){document.getElementById("mandate-report").hidden=true;}
  function addFlow(data={}){
    if(document.getElementById("dated-flows").children.length>=120)return;
    const row=document.createElement("div");row.className="mandate-row mandate-grid";
    row.innerHTML=label("flow_date",'<input name="date" type="date" required>')+label("flow_kind",select("kind",["contribution","withdrawal","liability"]))+numeric("flow_amount",0,true,0.01).replace('name="flow_amount"','name="amount"')+`<button type="button" data-i18n="removeRow">${t("removeRow")}</button>`;
    document.getElementById("dated-flows").append(row);
    set(row,"date",data.date||read(form,"horizon_date"));set(row,"kind",data.kind||"liability");set(row,"amount",data.amount??1000);
    row.querySelector("button").onclick=()=>{row.remove();invalidate();};updateDates();invalidate();
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
      amount.closest(".mandate-field").querySelector(".field-optional").hidden=amount.required;
      updateGoalPicker();
    };
    group(row,"objective_id").addEventListener("change",updateHelp);group(row,"funding").addEventListener("change",updateHelp);updateHelp();
    row.querySelector("button").onclick=()=>{row.remove();updateGoalPicker();updateConditionalFields();invalidate();};updateDates();updateConditionalFields();invalidate();
  }
  function updateDates(){
    const start=read(form,"as_of"),end=read(form,"horizon_date");
    if(!start||!end)return;
    const next=new Date(start+"T00:00:00Z");next.setUTCDate(next.getUTCDate()+1);
    const min=dateISO(next);
    group(form,"horizon_date").min=min;
    form.querySelectorAll('[name="due_date"],[name="date"]').forEach(input=>{input.min=min;input.max=end;});
  }
  function payload(){
    const values=Object.fromEntries(fields.map(k=>[k,num(form,k)??0]));
    const old=legacyMandate?.constraints;
    const value=num(form,"stress_loss");
    const stress=value===null?null:value/100;
    const unchangedStress=old && stress===Math.min(old.stress_loss.value,old.loss_budget.value);
    const constraints=Object.fromEntries(limits.map(k=>[k,old?.[k]||{value:null,mode:"hard"}]));
    constraints.stress_loss={value:unchangedStress?old.stress_loss.value:stress,mode:"hard"};
    constraints.loss_budget={value:unchangedStress?old.loss_budget.value:stress,mode:"hard"};
    for(const k of editableLimits){
      const value=num(form,k);
      constraints[k]={value:value===null?null:value/100,mode:read(form,`${k}_mode`)};
    }
    const allowedAssets=assets.filter(k=>checked(form,`asset_${k}`));
    if(old?.allowed_assets.includes("futures"))allowedAssets.push("futures");
    const derivatives=(allowedAssets.includes("commodity_etp")&&checked(form,"allow_derivatives"))||
      Boolean(old?.allowed_assets.includes("futures")&&old.allow_derivatives);
    Object.assign(constraints,{
      allow_short:old?.allow_short??false,allow_leverage:old?.allow_leverage??false,
      allow_derivatives:derivatives,allowed_assets:allowedAssets,esg_exclusions:old?.esg_exclusions??"",
      tax_assumption:old?.tax_assumption??"not_modeled",fx_hedge:old?.fx_hedge??"undecided",
    });
    const levels=kind=>Object.fromEntries(knowledge.map(k=>[k,
      k==="futures"&&derivatives?read(form,`${kind}_futures`):legacyMandate?.[kind]?.[k]??"none"
    ]));
    return {schema_version:"2.0.0",currency:read(form,"currency"),as_of:read(form,"as_of"),horizon_date:read(form,"horizon_date"),chf_per_usd:document.getElementById("mandate-fx").hidden?null:num(form,"chf_per_usd"),inflation:num(form,"inflation")===null?null:num(form,"inflation")/100,...values,
      dated_flows:[...document.getElementById("dated-flows").children].map(r=>({date:read(r,"date"),kind:read(r,"kind"),amount:num(r,"amount")})),
      goals:[...document.getElementById("goal-rows").children].map(r=>({objective_id:read(r,"objective_id"),due_date:read(r,"due_date"),amount:num(r,"amount"),currency:read(r,"currency"),basis:read(r,"basis"),priority:num(r,"priority"),shortfall_penalty:num(r,"amount")===null?1:num(r,"shortfall_penalty"),funding:checked(r,"funding")})),
      knowledge:levels("knowledge"),experience:levels("experience"),constraints,consent:checked(form,"consent")};
  }
  function reset(){legacyMandate=null;document.getElementById("mandate-legacy").hidden=true;form.reset();set(form,"currency","USD");document.getElementById("dated-flows").replaceChildren();document.getElementById("goal-rows").replaceChildren();updateGoalPicker();updateCurrency();updateDates();updateConditionalFields();invalidate();}
  function restore(m){
    reset();for(const k of [...fields,"currency","as_of","horizon_date","chf_per_usd","consent"])set(form,k,m[k]);
    set(form,"inflation",m.inflation===null?null:100*m.inflation);
    legacyMandate=m;
    const c=m.constraints;
    set(form,"stress_loss",100*Math.min(c.stress_loss.value,c.loss_budget.value));
    for(const k of editableLimits){
      const limit=c[k];
      set(form,k,limit.value===null?null:100*limit.value);
      set(form,`${k}_mode`,limit.mode);
    }
    for(const k of assets)set(form,`asset_${k}`,c.allowed_assets.includes(k));
    set(form,"allow_derivatives",c.allow_derivatives);
    set(form,"knowledge_futures",m.knowledge.futures);
    set(form,"experience_futures",m.experience.futures);
    document.getElementById("mandate-legacy").hidden=!(m.currency!=="USD"||c.allow_short||c.allow_leverage||
      c.allowed_assets.includes("futures")||c.esg_exclusions.trim()||c.tax_assumption==="after_tax_required"||
      ["partial","full"].includes(c.fx_hedge)||limits.slice(4).some(k=>c[k].value!==null));
    document.getElementById("dated-flows").replaceChildren();m.dated_flows.forEach(addFlow);
    document.getElementById("goal-rows").replaceChildren();m.goals.forEach(addGoal);updateCurrency();updateDates();updateConditionalFields();invalidate();
  }
  function example(){reset();const sample={capital:100000,cash:125000,investments:25000,other_assets:50000,debt:20000,reserve:20000,income_monthly:7000,spending_monthly:4500,contribution_monthly:1000,withdrawal_monthly:0,loss_capacity_amount:20000,currency:"USD",inflation:2};Object.entries(sample).forEach(([k,v])=>set(form,k,v));document.getElementById("goal-rows").replaceChildren();addGoal({objective_id:"OBJ10",amount:240000,currency:"USD",funding:true});invalidate();}
  form.addEventListener("input",()=>{updateConditionalFields();invalidate();});
  form.addEventListener("change",()=>{updateConditionalFields();invalidate();});
  document.getElementById("clear-legacy-mandate").onclick=()=>{
    if(read(form,"currency")!=="USD"){reset();return;}
    legacyMandate=null;
    document.getElementById("mandate-legacy").hidden=true;
    updateCurrency();updateConditionalFields();invalidate();
  };
  group(form,"as_of").addEventListener("change",updateDates);
  group(form,"horizon_date").addEventListener("change",()=>{
    updateDates();
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
