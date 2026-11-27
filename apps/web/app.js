const $ = id => document.getElementById(id);
const t = key => window.RM.t(key);
let mandate = null, cards = [], answers = {}, index = 0, portfolios = [], swipes = [], shortlist = [];
let fullMandate = null, mandateReport = null, pendingMandate = null, pendingReport = null;
let discoverySeed=null, discoveryVersion=null, discoveryCurrency="USD", discoveryConsent=false, responseLocales={}, discoveryConfidence=null;
let activePage = "saves", lastSimulationPage = "home", scoreReport = null, errorKey = "";
let sessionUnlocked = false, sessionEpoch = 0;
function setSaveSession(open) {
  sessionEpoch++;
  sessionUnlocked=Boolean(open);
  if(!open)window.GoalsView?.clear();
  if(!open)window.BaselinesView?.clear();
  if(!open)window.MeanVarianceView?.clear();
  if(!open)window.BlackLittermanView?.clear();
  if(!open)window.HierarchicalView?.clear();
  if(!open)window.DownsideView?.clear();
  if(!open)window.AdvancedView?.clear();
  if(!open)window.LongOnlyView?.clear();
  if(!open)window.AlternativeView?.clear();
  if(!open)window.TreasuryView?.clear();
  if(!open)window.FuturesView?.clear();
  if(!open)window.WalkForwardView?.clear();
  if(!open)window.StressMCView?.clear();
  document.body.dataset.session=sessionUnlocked?"unlocked":"locked";
  $("studio-nav").hidden=!sessionUnlocked;
}
function changed(){if(sessionUnlocked)document.dispatchEvent(new Event("riskmatch:changed"));}
const confirmed = new Set();
const pct = x => (100*x).toFixed(1) + "%";
const esc = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
async function api(path, data) {
  const epoch=sessionEpoch;
  let response;
  try { response = await fetch('/api/'+path, data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}); }
  catch { throw Error("networkError"); }
  const result = await response.json().catch(() => { throw Error("networkError"); });
  if(epoch!==sessionEpoch)throw Error("sessionChanged");
  if (!response.ok) {
    if(result.error==="Not found"&&!["cards","score","candidates"].includes(path))throw Error("serverOutdated");
    throw Error(result.error||"networkError");
  }
  return result;
}
const handle = fn => async (...args) => {
  try { errorKey = ""; $("error").textContent = ""; await fn(...args); }
  catch (e) { if(e.message==="sessionChanged")return; errorKey = e.message; $("error").textContent = diagnostic(errorKey); }
};
function page(name) {
  if(!sessionUnlocked && name!=="saves")name="saves";
  activePage = name;
  if(name!=="matches")window.PaperTracking?.unmount();
  if(name!=="saves")lastSimulationPage=name;
  document.querySelectorAll(".page").forEach(x => x.hidden = x.id!==name);
  document.querySelectorAll("[data-page]").forEach(x => x.classList.toggle("active", x.dataset.page===name));
  if (name==="matches") compare();
  if(name==="explore"&&!portfolios.length)$("portfolio").textContent=t("matchingLoading");
  if (name==="saves") document.dispatchEvent(new Event("riskmatch:saves"));
  changed();
}
const canMatch = report => report?.personalized_eligible ?? report?.demo_eligible;
document.querySelectorAll("[data-page]").forEach(button => button.onclick = handle(async () => {
  if(!sessionUnlocked)throw Error("saveRequired");
  if (button.dataset.page==="explore" && !mandate) throw Error("mandateRequired");
  if (button.dataset.page==="explore" && fullMandate && !canMatch(mandateReport)) throw Error("demoUnavailable");
  if(button.dataset.page==="explore"&&!pendingDeck&&!portfolios.length&&(!cards.length||index<cards.length)){
    page("discovery");await showCard();return;
  }
  if(button.dataset.page==="explore"&&cards.length&&index===cards.length&&!scoreReport)scoreReport=await discoveryScore();
  page(button.dataset.page);
  if (activePage==="explore" || (activePage==="matches"&&pendingDeck)) {
    await loadPortfolios();
    if(activePage==="matches")compare();
  }
  if (activePage==="universe") await window.UniverseView.load(api);
  if (activePage==="sources") await window.SourcesView.load(api);
  if (activePage==="discovery") {
    await showCard();
  }
}));
$("form").onsubmit = handle(async event => {
  event.preventDefault();
  if(!sessionUnlocked)throw Error("saveRequired");
  const payload=window.MandateForm.payload();
  if(Array.isArray(payload.goals)&&!payload.goals.length){
    document.querySelector?.(".goal-picker")?.scrollIntoView({behavior:"smooth",block:"center"});
    throw Error("chooseGoalsRequired");
  }
  const report=await api("mandate/preview",payload);
  if(JSON.stringify(payload)!==JSON.stringify(window.MandateForm.payload()))return;
  pendingMandate=payload;pendingReport=report;renderMandateReport();
  $("mandate-report").scrollIntoView({behavior:"smooth",block:"start"});
});
const diagnostic=key=>{const [head,...tail]=key.split(":");return t(head)+(tail.length?": "+t(tail.join(":")):"");};
const money=(amount,currency)=>amount===null||amount===undefined?t("noValue"):new Intl.NumberFormat(window.RM.language==="fr"?"fr-CH":"en-US",{style:"currency",currency,maximumFractionDigits:0}).format(amount);
function mandateTrace(p,r){
  if(!p?.constraints||!r)return "";
  const fr=window.RM.language==="fr", c=p.constraints, cash=v=>money(v,p.currency);
  const list=rows=>`<dl>${rows.map(([key,val])=>`<div><dt>${esc(t(key))}</dt><dd>${esc(val)}</dd></div>`).join("")}</dl>`;
  const amounts=keys=>keys.map(k=>[k,cash(p[k])]);
  const construction=new Set(["stress_loss","loss_budget","volatility","max_asset_weight"]);
  const exposure=new Set(["gross_limit","net_min","net_max"]);
  const limits=Object.entries(c).filter(([k,v])=>v&&typeof v==="object"&&v.value!=null&&(k!=="loss_budget"||v.value!==c.stress_loss?.value)).map(([k,v])=>{
    let effect=fr?"Bloque le calcul personnalisé":"Blocks personalized calculation";
    if(v.mode==="soft"){
      effect=["volatility","max_asset_weight"].includes(k)
        ? (fr?"Agit sur le classement":"Affects ranking")
        : (fr?"Sans effet sur les cartes":"Does not affect cards");
    }else if(construction.has(k)){
      effect=fr?"Construction et vérification des poids":"Construction and weight checks";
    }else if(exposure.has(k)){
      effect=fr?"Vérifié sur une exposition fixe de 100 %":"Checked against fixed 100% exposure";
    }
    return [k,pct(v.value)+" · "+t(v.mode)+" · "+effect];
  });
  const goals=p.goals.map(g=>`<p><strong>${esc(t(g.objective_id))}</strong> · ${esc(g.due_date)} · ${g.amount==null?esc(t("noValue")):esc(money(g.amount,g.currency))} · ${esc(t(g.basis))} · ${esc(t("priority"))} ${g.priority}/5 · ${esc(t("shortfall_penalty"))} ${g.shortfall_penalty} · ${g.funding?(fr?"À financer":"Funded obligation"):(fr?"Préférence":"Preference")}</p>`).join("");
  return `<details class="mandate-trace"><summary>${fr?"Comment mon mandat a été pris en compte":"How my mandate was used"}</summary>
    <h3>${fr?"Construction et contrôle du risque":"Construction and risk checks"}</h3>${list([...amounts(["capital","loss_capacity_amount"]),["currency",p.currency],["as_of",p.as_of],["horizon_date",p.horizon_date],["effectiveStress",pct(r.effective_stress_limit)],["allowed_assets",c.allowed_assets.map(k=>t(({equity:"matchingEquities",treasury:"matchingTreasuries"})[k]||k)).join(", ")],...limits])}
    <h3>${fr?"Objectifs et projection":"Goals and projection"}</h3>${goals}${list([...amounts(["contribution_monthly","withdrawal_monthly"]),["inflation",p.inflation==null?t("noValue"):pct(p.inflation)],["chf_per_usd",p.chf_per_usd??t("noValue")]])}
    ${p.dated_flows.map(f=>`<p>${esc(f.date)} · ${esc(t(f.kind))} · ${esc(cash(f.amount))}</p>`).join("")}
    <h3>${fr?"Contrôle de la situation financière":"Financial feasibility checks"}</h3>${list([...amounts(["cash","investments","other_assets","debt","reserve","income_monthly","spending_monthly"]),["netWorth",cash(r.net_worth)],["investableWealth",cash(r.investable_wealth)],["monthlySurplus",cash(r.monthly_surplus)]])}
    <h3>${fr?"Expérience et restrictions déclarées":"Declared experience and restrictions"}</h3>${list([...[["short","allow_short"],["leverage","allow_leverage"],["futures","allow_derivatives"]].filter(([,key])=>c[key]).map(([k,key])=>[key,t(p.knowledge[k])+" / "+t(p.experience[k])]),["tax_assumption",t(c.tax_assumption)],["fx_hedge",t(c.fx_hedge)],["esg_exclusions",c.esg_exclusions||"—"]])}
    <p class="muted">${fr?"Le patrimoine, les dettes et le budget servent à vérifier le financement et la capacité de perte. Le taux de change saisi sert aux objectifs en devise étrangère ; la date du mandat détermine l’accès à l’archive locale.":"Assets, debts and budget are used to assess funding and loss capacity. The entered exchange rate is used for goals in a different currency; the mandate date determines access to the local archive."}</p></details>`;
}
function renderMandateReport(){
  if(!pendingReport)return;
  const r=pendingReport, p=pendingMandate, area=$("mandate-report");
  const cash=v=>money(v,r.currency), result=x=>x?.annual_return===null||x?.annual_return===undefined?t(x?.status||"noValue"):pct(x.annual_return);
  const stats=[["netWorth",cash(r.net_worth)],["investableWealth",cash(r.investable_wealth)],["monthlySurplus",cash(r.monthly_surplus)],["nextWithdrawal",r.next_withdrawal||t("noValue")],["loss_capacity_amount",cash(r.loss_capacity_amount)],["nearTermCushion",cash(r.near_term_liquidity_cushion)],["effectiveStress",pct(r.effective_stress_limit)],["zeroReturnBalance",cash(r.zero_return_min_balance)],["combinedReturn",result(r.combined_required_return)]];
  let comparison="";
  if(mandateReport)comparison=`<h3>${esc(t("compareBefore"))}</h3><p>${esc(t("effectiveStress"))}: ${pct(mandateReport.effective_stress_limit)} → ${pct(r.effective_stress_limit)} · ${esc(t("goalCount"))}: ${mandateReport.goals.length} → ${r.goals.length} · ${esc(t("capital"))}: ${esc(money(fullMandate.capital,fullMandate.currency))} → ${esc(cash(p.capital))}</p><p>${esc(t("mandateGoals"))}: ${esc(mandateReport.goals.map(g=>`${t(g.objective_id)} (${g.due_date}, ${money(g.target_nominal_base,mandateReport.currency)})`).join(" · "))} → ${esc(r.goals.map(g=>`${t(g.objective_id)} (${g.due_date}, ${cash(g.target_nominal_base)})`).join(" · "))}</p>`;
  const messages=(items,cls)=>items.map(k=>`<p class="${cls}">• ${esc(diagnostic(k))}</p>`).join("");
  area.innerHTML=`<article><h2>${esc(t("mandateReport"))}</h2><p class="mandate-status ${r.conflicts.length?"mandate-conflict":""}">${esc(t(r.conflicts.length?"structuralConflicts":"structuralValid"))}</p><div class="mandate-summary">${stats.map(([k,v])=>`<div><span>${esc(t(k))}</span><b>${esc(v)}</b></div>`).join("")}</div>${comparison}<h3>${esc(t("mandateGoals"))}</h3>${r.goals.map(g=>`<div class="mandate-row mandate-goal"><b>${esc(t(g.objective_id))} · ${esc(g.due_date)}</b><p>${esc(t("goal_amount"))}: ${esc(cash(g.target_nominal_base))} · ${esc(t("requiredReturn"))}: ${esc(result(g.required_return))} · ${esc(t("zeroReturnGap"))}: ${esc(cash(g.zero_return_gap))}</p></div>`).join("")}${messages(r.conflicts,"mandate-conflict")}${messages(r.warnings,"muted")}<div class="matching-readiness ${canMatch(r)&&p.as_of>="2026-11-25"?"":"mandate-conflict"}"><strong>${esc(t(canMatch(r)&&p.as_of>="2026-11-25"?"matchingReady":"matchingLimited"))}</strong>${messages(r.personalized_reasons??r.demo_reasons,"muted")}${p.as_of<"2026-11-25"?`<p>${esc(t("matchingDateUnavailable"))}</p>`:""}</div><p class="muted">${esc(t("riskNotMeasured"))}</p><button id="confirm-mandate" class="primary" ${r.conflicts.length?"disabled":""}>${esc(t("confirmMandate"))}</button></article>`;
  if(r.personalized_eligible && r.dynamic_overlay_available===false)
    area.insertAdjacentHTML("beforeend","<p>"+esc(t("dynamicUnavailableMandate"))+"</p>");
  area.innerHTML+=mandateTrace(p,r);
  area.hidden=false;
  $("confirm-mandate").onclick=handle(confirmMandate);
}
async function confirmMandate(){
  if(!sessionUnlocked||!pendingReport||pendingReport.status!=="structurally_valid"||$("mandate-report").hidden)throw Error("mandateRequired");
  if(JSON.stringify(pendingMandate)!==JSON.stringify(window.MandateForm.payload()))throw Error("mandateRequired");
  const keepDiscovery=Boolean(fullMandate&&fullMandate.currency===pendingMandate.currency&&cards.length);
  fullMandate=pendingMandate;mandateReport=pendingReport;pendingMandate=null;pendingReport=null;
  mandate={capital:fullMandate.capital,years:mandateReport.horizon_years,max_stress_loss:mandateReport.effective_stress_limit,currency:fullMandate.currency};
  historicalDeck=true;savedBlend=null;paperTracking=null;deckAversion=null;deckStyle="000";pendingDeck=null;deckRequest=null;portfolios=[]; swipes=[]; shortlist=[]; confirmed.clear(); if(!keepDiscovery)resetDiscovery();
  $("mandate-report").hidden=true;
  changed();page("discovery");await showCard();changed();
  if(canMatch(mandateReport)&&fullMandate.as_of>="2026-11-25"){
    // Load the common market inputs while the user answers Discovery.
    api("matching/prepare",{mandate:fullMandate}).catch(e=>{
      if(e.message==="serverOutdated"&&sessionUnlocked){errorKey=e.message;$("error").textContent=diagnostic(errorKey);}
    });
  }
}
const discoveryQuestionnaireVersion="discovery-v3.0.0";
function resetDiscovery(){cards=[];answers={};index=0;scoreReport=null;discoverySeed=null;discoveryVersion=null;discoveryConsent=false;responseLocales={};discoveryConfidence=null;discoveryCurrency=mandate?.currency||"USD";$("discovery-consent-check").checked=false;}
$("discovery-start").onclick=handle(async()=>{
  if(!sessionUnlocked||!mandate)throw Error("mandateRequired");
  if(!$("discovery-consent-check").checked)throw Error("discoveryConsentRequired");
  const seed=crypto.getRandomValues(new Uint32Array(1))[0], currency=mandate.currency;
  const session=await api("discovery/session",{seed,currency});
  if(session.version!==discoveryQuestionnaireVersion)throw Error("serverOutdated");
  discoverySeed=seed;discoveryCurrency=currency;discoveryVersion=session.version;discoveryConsent=true;cards=session.cards;answers={};responseLocales={};index=0;scoreReport=null;discoveryConfidence=null;
  changed();await showCard();
});
$("discovery-reset").onclick=handle(async()=>{if(!sessionUnlocked||!discoveryConsent)return;if(!window.confirm(t("withdrawDiscoveryConfirm")))return;resetDiscovery();changed();await showCard();});
async function discoveryScore(){return discoveryVersion?api("discovery/score",{seed:discoverySeed,currency:discoveryCurrency,answers,confidence:discoveryConfidence,locales:responseLocales}):api("score",answers);}
const discoveryArt = {
  mixed:"balance", gains:"allocation", losses:"hedge",
  rare:"factors", trajectory:"trend", checks:"calm",
};
function discoveryGainThresholds(rows){
  if(!rows?.length)return "";
  const format=amount=>money(amount,discoveryCurrency);
  const summary=rows.map(row=>{
    const loss=t("discoveryThresholdLoss").replace("{loss}",()=>format(row.loss));
    const threshold=t("discoveryThreshold_"+row.status)
      .replace("{lower}",()=>format(row.max_refused_gain))
      .replace("{upper}",()=>format(row.min_accepted_gain));
    const coverage=t("discoveryThresholdResponses")
      .replace("{answered}",()=>row.answered).replace("{total}",()=>row.total);
    return `<div><dt>${esc(loss)}</dt><dd>${esc(threshold)}<small>${esc(coverage)}</small></dd></div>`;
  }).join("");
  return `<section aria-labelledby="discovery-gain-thresholds"><h3 id="discovery-gain-thresholds">${esc(t("discoveryThresholdTitle"))}</h3>
    <p>${esc(t("discoveryThresholdContext"))}</p><dl class="discovery-thresholds">${summary}</dl></section>`;
}
function discoveryLossUtility(rows){
  if(!rows?.length)return "";
  const number=new Intl.NumberFormat(window.RM.language==="fr"?"fr-CH":"en-US",{maximumFractionDigits:2,minimumFractionDigits:2});
  const loss=esc(t("discoveryUtilityLossSymbol"));
  const scenarios=[
    ["discoveryUtilityLinear",1,50,50],
    ["discoveryUtilityCurved",.8,50,50],
    ["discoveryUtilityLossWeighted",1,45,55],
    ["discoveryUtilityGainWeighted",1,55,45],
  ];
  const coefficient=(row,alpha,gainWeight,lossWeight)=>{
    const format=gain=>number.format(gainWeight/lossWeight*(gain/row.loss)**alpha);
    return t("discoveryThreshold_"+row.status)
      .replace("{lower}",()=>format(row.max_refused_gain))
      .replace("{upper}",()=>format(row.min_accepted_gain));
  };
  const columns=rows.map(row=>`<th scope="col">${esc(t("discoveryThresholdLoss").replace("{loss}",()=>money(row.loss,discoveryCurrency)))}</th>`).join("");
  const results=scenarios.map(([key,alpha,gainWeight,lossWeight])=>`<tr>
    <th scope="row">${esc(t(key))}<small>α = ${number.format(alpha)} · ${gainWeight} / ${lossWeight}</small></th>
    ${rows.map(row=>`<td>${esc(coefficient(row,alpha,gainWeight,lossWeight))}</td>`).join("")}
    </tr>`).join("");
  return `<details class="discovery-utility">
    <summary>${esc(t("discoveryUtilityTitle"))}</summary>
    <p>${esc(t("discoveryUtilityIntro"))}</p>
    <div class="discovery-utility-equation" dir="ltr">V(G, L) = w<sub>gain</sub> × G<sup>α</sup> − w<sub>${loss}</sub> × λ<sub>${loss}</sub> × L<sup>α</sup></div>
    <p>${esc(t("discoveryUtilityVariables"))}</p>
    <p>${esc(t("discoveryUtilityBalance"))} <span dir="ltr">λ<sub>${loss}</sub> = (w<sub>gain</sub> / w<sub>${loss}</sub>) × (G / L)<sup>α</sup></span></p>
    <div class="backtest-table discovery-utility-table"><table><caption>${esc(t("discoveryUtilityCaption"))}</caption>
    <thead><tr><th scope="col">${esc(t("discoveryUtilityAssumption"))}</th>${columns}</tr></thead>
    <tbody>${results}</tbody></table></div>
    <p>${esc(t("discoveryUtilityExample"))}</p>
    <p class="muted">${esc(t("discoveryUtilityStatus"))}</p></details>`;
}
async function showCard() {
  $("discovery-consent").hidden=!mandate||discoveryConsent||cards.length>0;
  $("discovery-question").hidden=!cards[index];
  $("back").hidden=!cards.length;
  $("discovery-reset").hidden=!cards.length;
  const card = cards[index];
  $("actions").hidden=!card; $("back").disabled=index===0; $("result").replaceChildren();
  if(!mandate){
    $("card").replaceChildren();
    $("discovery-question").hidden=true;
    $("actions").hidden=true;
    $("back").hidden=true;
    $("discovery-reset").hidden=true;
    $("result").innerHTML='<article><h2>'+esc(t("mandateRequired"))+'</h2><button id="discovery-go-mandate" class="primary">'+esc(t("navMandate"))+' →</button></article>';
    $("discovery-go-mandate").onclick=()=>page("mandate");
    return;
  }
  if (!card) {
    $("card").replaceChildren();
    if (!cards.length) return;
    if (!scoreReport) scoreReport=await discoveryScore();
    const r=scoreReport;
    const dimensions=r.dimensions?`<div class="mandate-summary discovery-summary">${Object.entries(r.dimensions).map(([key,v])=>`<div><b>${esc(t(key))}</b><p>${v.canonical_b_fraction===null?esc(t("noValue")):pct(v.canonical_b_fraction)} · ${v.answered}/${v.total}</p><small>${esc(t(key+"_explain"))}</small></div>`).join("")}</div>`:"";
    const confidence=r.dimensions?`<label><span>${esc(t("confidenceOptional"))}</span><select id="discovery-confidence"><option value="">${esc(t("noValue"))}</option>${[1,2,3,4,5].map(v=>`<option value="${v}" ${v===discoveryConfidence?"selected":""}>${v}/5</option>`).join("")}</select></label>`:"";
    const audit=r.dimensions?`<p>${esc(t("coverage"))}: ${r.answered}/${r.total_scored} · ${esc(t("unsure"))}: ${r.counts.unsure} · ${esc(t("skip"))}: ${r.counts.skip} · ${esc(t("inconsistencies"))}: ${r.inconsistencies.length}/${r.pairs_checked} · ${esc(t("discoveryUnderstanding"))}: ${esc(t(r.comprehension_correct==null?"noValue":r.comprehension_correct?"discoveryUnderstood":"discoveryToReview"))}</p><p class="muted">${esc(t("scoreMethod"))}</p>`:"";
    const blocked=fullMandate&&(!canMatch(mandateReport)||fullMandate.as_of<"2026-11-25");
    const blocker=blocked?`<p class="mandate-conflict">${esc(t(!canMatch(mandateReport)?"demoUnavailable":"matchingDateUnavailable"))}</p>`:"";
    const scoreTitle=r.score===null?esc(t("scoreUnavailable")):`${esc(t("prudenceIndex"))} · <span>${esc(r.score)} / 30</span>`;
    $("result").innerHTML=`<article><div class="discovery-results"><section><h2>${scoreTitle}</h2>
      <p>${esc(t("scoreExplanation"))} ${esc(t("coverage"))}: ${pct(r.coverage)}. ${esc(t("sensitivity"))}: ${r.sensitivity.join("–")}. ${esc(t("scoreLimit"))}</p></section>
      ${discoveryGainThresholds(r.mixed_gain_thresholds)}</div>
      ${discoveryLossUtility(r.mixed_gain_thresholds)}
      <details><summary>${esc(t("profileDetails"))}</summary>${audit}${dimensions}${confidence}</details>
      <p class="muted">${esc(t("discoverySeparate"))}</p>${blocker}<button class="primary" id="next">${esc(t(blocked?"reviseMandate":"exploreAllocations"))}</button></article>`;
    if(r.dimensions)$("discovery-confidence").onchange=handle(async event=>{discoveryConfidence=event.target.value?Number(event.target.value):null;scoreReport=null;changed();await showCard();});
    $("next").onclick=handle(async()=>{if(!mandate)throw Error("mandateRequired");if(blocked){page("mandate");return;}page("explore");await loadPortfolios();});
    return;
  }
  $("discovery-question").hidden=false;
  const c=window.RM.language==="fr"?card.fr:card;
  const statementKey=card.block_id==="trajectory"?"discoveryPathStatement":
    card.dimension==="comprehension"?"discoveryComprehensionStatement":"discoveryStatement";
  const context=card.block_id==="trajectory"?t("discoveryPathContext"):
    card.reference_wealth?t("discoveryWealthContext").replace("{wealth}",()=>`${card.reference_wealth} ${card.currency}`):"";
  const statement=t(statementKey).split(/(\{[ab]\})/).map(part=>{
    if(part==="{a}")return `<strong>${esc(c.a)}</strong>`;
    if(part==="{b}")return `<strong>${esc(c.b)}</strong>`;
    return esc(part);
  }).join("");
  $("card").innerHTML=`
    <div class="discovery-deck-progress">
      <span>${esc(c.block)}</span><span>${index+1} / ${cards.length}</span>
      <progress max="${cards.length}" value="${index}" aria-label="${esc(t("discoveryProgress"))}"></progress>
    </div>
    <div class="discovery-card-backing" aria-hidden="true"></div>
    <div class="discovery-cherry-layer" aria-hidden="true"></div>
    <article class="card discovery-swipe-card" data-art="${discoveryArt[card.block_id]||"balance"}" aria-labelledby="discovery-statement">
      <div class="discovery-card-image" aria-hidden="true"></div>
      <div class="discovery-card-body">
        <h2 id="discovery-statement" class="discovery-proposal">${statement}</h2>
        ${context?`<p class="discovery-card-context">${esc(context)}</p>`:""}
      </div>
      <span class="discovery-stamp" aria-hidden="true"></span>
    </article>`;
}
let discoveryTransition=false;
let discoveryDrag=null;
const cardStage=$("card");
const cardMotion=(element, frames, duration)=>element.animate(frames,{duration,easing:"ease-out",fill:"forwards"}).finished.catch(()=>{});
function markChoice(card, choice){
  const stamp=card.querySelector(".discovery-stamp");
  stamp.textContent=choice==="like"?"♥":"✕";
  stamp.dataset.swipeDirection=choice;
}
async function animateDiscoveryChoice(choice){
  const card=cardStage.querySelector?.(".discovery-swipe-card");
  if(!card?.animate)return;
  markChoice(card,choice);
  const direction=choice==="like"?1:-1;
  const reduced=window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  await cardMotion(card,[{transform:card.style.transform||"none",opacity:1},
    {transform:reduced?"none":`translateX(${direction*54}%) rotate(${direction*11}deg)`,opacity:0}],reduced?140:260);
  if(!card.isConnected)return;
  const cherry=document.createElement("img");
  cherry.src="./assets/cherry.png";cherry.alt="";cherry.className="discovery-cherry";
  cardStage.querySelector(".discovery-cherry-layer").append(cherry);
  try{
    const frames=reduced?[{opacity:1},{opacity:1}]:[
      {opacity:0,transform:"scale(.76)"},
      {opacity:1,transform:"scale(1.12)",offset:.32},
      {opacity:1,transform:"scale(1)",offset:.76},
      {opacity:0,transform:"scale(.96)"}];
    await cardMotion(cherry,frames,reduced?130:420);
  }finally{cherry.remove();}
}
document.querySelectorAll("[data-choice]").forEach(button=>button.onclick=handle(async()=>{
  const card=cards[index];
  if(!sessionUnlocked||!card||discoveryTransition)return;
  const choice=button.dataset.choice, locale=window.RM.language, epoch=sessionEpoch;
  discoveryTransition=true;
  try{
    const isSwipe=choice==="like"||choice==="dislike";
    if(isSwipe)await animateDiscoveryChoice(choice);
    if(epoch!==sessionEpoch||cards[index]!==card)return;
    answers[card.id]=choice;responseLocales[card.id]=locale;index++;scoreReport=null;changed();
    await showCard();
  }finally{discoveryTransition=false;}
}));
$("back").onclick=handle(async()=>{if(sessionUnlocked&&index&&!discoveryTransition){const id=cards[--index].id;delete answers[id];delete responseLocales[id];scoreReport=null;discoveryConfidence=null;changed();await showCard();}});
document.addEventListener("keydown",e=>{if(!sessionUnlocked||activePage!=="discovery"||index>=cards.length||!cards.length||e.ctrlKey||e.metaKey||e.altKey||["INPUT","SELECT","TEXTAREA"].includes(e.target?.tagName))return;const choice={ArrowLeft:"dislike",ArrowRight:"like",u:"unsure",s:"skip"}[e.key];if(choice){e.preventDefault();document.querySelector(`[data-choice="${choice}"]`).click();}});
cardStage.addEventListener("pointerdown",event=>{
  const card=event.target.closest(".discovery-swipe-card");
  if(!card||!event.isPrimary||event.button!==0||discoveryTransition)return;
  discoveryDrag={card,pointer:event.pointerId,x:event.clientX};
  card.setPointerCapture(event.pointerId);
});
cardStage.addEventListener("pointermove",event=>{
  if(discoveryDrag?.pointer!==event.pointerId)return;
  const {card,x}=discoveryDrag;
  const dx=event.clientX-x;
  card.style.transform=`translateX(${dx}px) rotate(${Math.max(-14,Math.min(14,dx/12))}deg)`;
  if(Math.abs(dx)>24)markChoice(card,dx>0?"like":"dislike");
  else card.querySelector(".discovery-stamp").textContent="";
});
function finishDiscoveryDrag(event,send){
  if(discoveryDrag?.pointer!==event.pointerId)return;
  const {card,x}=discoveryDrag;
  const dx=event.clientX-x;
  discoveryDrag=null;
  if(send&&Math.abs(dx)>=Math.min(85,card.offsetWidth*.24)){
    document.querySelector(`[data-choice="${dx>0?"like":"dislike"}"]`).click();
  }else{
    card.style.transform="";
    card.querySelector(".discovery-stamp").textContent="";
  }
}
cardStage.addEventListener("pointerup",event=>finishDiscoveryDrag(event,true));
cardStage.addEventListener("pointercancel",event=>finishDiscoveryDrag(event,false));
cardStage.addEventListener("lostpointercapture",event=>finishDiscoveryDrag(event,false));
let deckStyle="000";
let historicalDeck=true, savedBlend=null,deckAversion=null,showFullDeck=false,pendingDeck=null;
let paperTracking=null;
async function fetchDeck(raw){
  try{
    if(raw.schema_version==="2.0.0"){
      const health=await api("health");
      if(health.matching_engine!=="personalized-v3")throw Error("serverOutdated");
      const comparison=await api("matching/cards",{mandate:raw,aversion:deckAversion,style:deckStyle,include_comparison:true});
      const deck=comparison?.cards;
      if(!Array.isArray(deck)||deck.some(c=>!c.personalized||!c.version?.startsWith("personalized-v3:")))throw Error("serverOutdated");
      deck.comparison={methods:comparison.methods,market_reference:comparison.market_reference};
      return deck;
    }
    return await (historicalDeck ? api("matching/cards",{mandate:raw,aversion:deckAversion,style:deckStyle}) : api("candidates",raw));
  }
  catch(e){if(historicalDeck&&e.message==="Not found")throw Error("serverOutdated");throw e;}
}
let deckRequest=null;
async function loadPortfolios(){
  if(deckRequest)return deckRequest;
  $("portfolio").textContent=t("matchingLoading");
  $("portfolio").setAttribute?.("aria-busy","true");
  for(const id of ["like","reject","skip","undo"])$(id).disabled=true;
  let clock;
  if(window.Journey && activePage==="explore"&&!portfolios.length){
    $("portfolio").innerHTML=window.Journey.loader();
    const display=$("portfolio").querySelector("[data-elapsed]"),start=Date.now();
    clock=setInterval(()=>{if(display.isConnected)display.textContent=Math.floor((Date.now()-start)/1000)+" s";},1000);
  }
  const task=loadPortfoliosInternal();
  deckRequest=task;
  try{await task;}
  catch(e){
    if(e.message!=="sessionChanged"&&deckRequest===task&&sessionUnlocked){
      $("portfolio").replaceChildren();
      const text=document.createElement("p");text.textContent=diagnostic(e.message);
      const retry=document.createElement("button");retry.textContent=window.RM.language==="fr"?"Réessayer":"Retry";
      retry.onclick=handle(loadPortfolios);$("portfolio").append(text,retry);
    }
    throw e;
  }finally{
    if(clock)clearInterval(clock);
    if(deckRequest===task)deckRequest=null;
    if(!deckRequest)$("portfolio").setAttribute?.("aria-busy","false");
  }
}
async function loadPortfoliosInternal(){
  if(fullMandate&&!canMatch(mandateReport))throw Error("demoUnavailable");
  if(fullMandate&&mandateReport?.personalized_eligible===true&&(scoreReport?.score===null||(!scoreReport&&deckAversion===null)))throw Error("scoreUnavailable");
  if(fullMandate&&fullMandate.as_of<"2026-11-25")throw Error("matchingDateUnavailable");
  const signature=JSON.stringify(fullMandate||mandate),epoch=sessionEpoch;
  const current=()=>sessionEpoch===epoch&&signature===JSON.stringify(fullMandate||mandate);
  if(pendingDeck){
    const restored=await fetchDeck(fullMandate||mandate);
    if(!current())throw Error("sessionChanged");
    if(pendingDeck.swipes.length&&JSON.stringify(pendingDeck.deckIds)!==JSON.stringify(restored.map(p=>[p.name,p.version])))throw Error("deckChanged");
    portfolios=restored;swipes=pendingDeck.swipes.slice();shortlist=portfolios.filter((_,i)=>swipes[i]==="like");savedBlend=pendingDeck.savedBlend;pendingDeck=null;changed();
    showPortfolio();return;
  }
  if(!portfolios.length || (scoreReport&&(deckAversion!==scoreReport.score||deckStyle!==(scoreReport.style_profile||"000")))){
    if(scoreReport){deckAversion=scoreReport.score;deckStyle=scoreReport.style_profile||"000";}
    const deck=await fetchDeck(fullMandate||mandate);
    if(!current())throw Error("sessionChanged");
    portfolios=deck;
    swipes=[];shortlist=[];savedBlend=null;showFullDeck=false;confirmed.clear();changed();
  }
  showPortfolio();
}
function strategyName(name){
  const translated=t(name);
  if(translated!==name||!name.includes("_"))return translated;
  return name.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
}
function strategyDescription(name){
  const lang=window.RM.language==="fr"?1:0;
  return window.StrategyMethods?.methods[name]?.[lang] || window.Journey?.method(name) || "";
}
function strategyExplanation(p){
  const fr=window.RM.language==="fr", lang=fr?1:0;
  const catalog=window.StrategyMethods, method=catalog?.methods[p.name];
  const limit=mandate?.max_stress_loss;
  const historical=Number.isFinite(p.fit_risk_weight);
  const stress=Number.isFinite(limit)&&Number.isFinite(p.stress_loss)
    ? (fr?"Pire perte parmi les chocs testés ":"Worst loss across the tested shocks ")+pct(p.stress_loss)
      +(fr?" pour une limite de ":" against a limit of ")+pct(limit)+"."
    : "";
  const fit=p.personalized
    ? (fr?"Les poids tiennent compte des actifs autorisés et des plafonds du mandat. Le classement combine sécurité, rendement estimé et projections de tes objectifs quand elles sont mesurables. Tes préférences de simplicité et d’activité peuvent aussi intervenir.":"Weights account for permitted assets and position caps. Ranking combines safety, estimated return and projections for goals that can be measured. Your preferences for simplicity and activity can also affect the ranking.")
    : historical
      ? (fr?"Cette allocation historique passe le filtre de perte en stress. Son classement utilise la perte simulée et le rendement de la période de développement.":"This historical allocation passes the stress-loss filter. Its ranking uses simulated loss and the return from the development period.")
      : (fr?"Cette allocation de démonstration passe le filtre de perte sur un choc prédéfini.":"This demo allocation passes the loss filter on a predefined shock.");
  const scenario=p.worst_scenario
    ? (fr?"Choc le plus défavorable ":"Worst shock ")+t(p.worst_scenario)+".":"";
  const riskWeight=historical?(fr?"Poids de la sécurité dans le compromis de base ":"Safety weight in the base tradeoff ")+pct(p.fit_risk_weight)+".":"";
  const softPenalty=p.soft_constraint_penalty>0
    ? (fr?"Un dépassement de préférence de volatilité ou de poids réduit le score.":"Exceeding a volatility or position-weight preference reduces the score."):"";
  const source=method?catalog.sources[method[3]||"returns"][lang]:"";
  const cutoff=p.model_as_of?(fr?" Dernière observation du panel ":" Last observation in the panel ")+p.model_as_of+".":"";
  const formula=method?.[2];
  const formulaGuide=fr
    ?"Dans les formules, w désigne les poids, r le rendement mensuel, R le rendement estimé, Rf le taux de référence des liquidités, σ la volatilité Σ la matrice des mouvements communs (covariances) et λ le coefficient de pénalisation du risque."
    :"In the formulas, w denotes weights, r monthly return, R estimated return, Rf the cash-rate proxy, σ volatility Σ the covariance matrix and λ the risk penalty coefficient.";
  return `<details class="strategy-method"><summary>${fr?"Comment ça marche et pourquoi cette carte ?":"How does it work and why am I seeing this card?"}</summary>
    ${method?`<h3>${fr?"Règle de construction":"Construction rule"}</h3><p>${esc(method[lang])}</p>`:""}
    ${formula?`<p><strong>${fr?"Formule de la règle":"Rule in formula form"}</strong><br><code>${esc(formula)}</code></p>`:""}
    ${formula&&/[Σσλ]/.test(formula)?`<p class="muted">${formulaGuide}</p>`:""}
    ${source?`<h3>${fr?"Données utilisées":"Data used"}</h3><p>${esc(source+cutoff)}</p>`:""}
    ${p.personalized&&window.StrategyMethods?.dependency?.[p.name]?`<p><strong>${fr?"Effet de la date des données":"Effect of the data cutoff"} · ${esc(window.StrategyMethods.dependency[p.name][lang])}</strong> ${esc(window.StrategyMethods.dependency[p.name][lang+2])}</p>`:""}
    ${p.personalized?`<p>${fr?"Le moteur peut rapprocher les poids de l’allocation défensive pour respecter le mandat. Les poids affichés sont les poids finaux après ces vérifications.":"The engine can move weights toward the defensive allocation to satisfy the mandate. The displayed weights are the final weights after these checks."}</p>`:""}
    <h3>${fr?"Pourquoi elle apparaît":"Why it appears"}</h3><p>${esc([stress,scenario,fit,riskWeight,softPenalty].filter(Boolean).join(" "))}</p>
  </details>`;
}
function strategyDeckList(fr){
  const comparison=portfolios.comparison;
  if(!comparison)return `<details class="strategy-deck-list"><summary>${fr?"Stratégies proposées pour ce mandat":"Strategies offered for this mandate"} (${portfolios.length})</summary>
    <ol>${portfolios.map(p=>`<li>${esc(strategyName(p.name))}</li>`).join("")}</ol></details>`;
  const fmt=new Intl.NumberFormat(fr?"fr":"en",{maximumFractionDigits:2});
  const percent=new Intl.NumberFormat(fr?"fr":"en",{style:"percent",maximumFractionDigits:2,minimumFractionDigits:2});
  const metricCells=m=>`<td>${percent.format(m.cagr)}</td><td>${percent.format(m.vol)}</td><td>${Number.isFinite(m.sharpe)?fmt.format(m.sharpe):"—"}</td>`;
  const statuses=fr?{unavailable:"Incompatible pour ce mandat",backtest_incomplete:"Backtest incomplet",research:"Référence de recherche"}:
    {unavailable:"Unavailable for this mandate",backtest_incomplete:"Incomplete backtest",research:"Research reference"};
  const reasons=(comparison.methods||[]).filter(m=>m.status!=="available").map(m=>{
    const stamp=/^\d{4}-\d{2}-\d{2}/.exec(m.reason||"")?.[0];
    const gap=/missing observed return for a held security through (\d{4}-\d{2}-\d{2}) \((.+)\)$/.exec(m.reason||"");
    const tie=m.name==="passive_index";
    const message=m.status==="research"
      ? tie?(fr?"Le plafond du moteur est de 65 % par ETF.":"The engine caps each ETF at 65%.")
        :(fr?"Le ratio peut devenir indéfini sur une fenêtre sans pertes.":"The ratio can be undefined in a window without losses.")
      : gap?(fr?`Rendement manquant à la clôture du ${gap[1]} (${gap[2]}).`:`Missing realized return at the ${gap[1]} close (${gap[2]}).`)
      : m.reason?.includes("missing observed return")?(fr?"Rendement réalisé manquant sur un titre détenu.":"Missing realized return for a holding.")
      : m.reason?.includes("mandatory exit conflicts")?(fr?"Une sortie obligatoire contredit la limite de cash.":"A mandatory exit conflicts with the cash limit.")
      : m.reason||"";
    return `<li><strong>${esc(strategyName(m.name))}</strong> · ${esc(statuses[m.status])}${stamp?` · ${esc(stamp)}`:""}<br>${esc(message)}</li>`;
  }).join("");
  const rows=portfolios.map(card=>`<tr><th scope="row">${esc(strategyName(card.name))}${card.featured?`<small>${fr?"Sélection pour ton mandat":"Featured for your mandate"}</small>`:""}
    ${card.equivalent_methods?.length?`<small>${fr?"Poids proches":"Similar weights"} · ${card.equivalent_methods.map(name=>esc(strategyName(name))).join(", ")}</small>`:""}</th>${metricCells(card.metrics)}</tr>`).join("");
  const market=comparison.market_reference;
  const reference=market?`<tr><th scope="row">${fr?"SPY · référence de marché":"SPY · market benchmark"}</th>${metricCells(market)}</tr>`:"";
  return `<details class="strategy-deck-list"><summary>${fr?"Comparer toutes les stratégies compatibles":"Compare all compatible strategies"} (${portfolios.length})</summary>
    <p>${fr?"Même période de test et même taux de frais simulés. La référence SPY achète une fois au début du test. Quand des méthodes sont regroupées, les chiffres sont ceux de la carte affichée.":"Same test period and simulated fee rate. The SPY benchmark buys once at the start of the test. For grouped methods, the figures represent the displayed card."}</p>
    <div class="backtest-table"><table><thead><tr><th>${fr?"Stratégie":"Strategy"}</th><th>CAGR</th><th>${fr?"Volatilité":"Volatility"}</th><th>Sharpe</th></tr></thead>
    <tbody>${rows}${reference}</tbody></table></div>
    ${reasons?`<details><summary>${fr?"Disponibilité des autres méthodes":"Availability of other methods"}</summary><ul>${reasons}</ul></details>`:""}</details>`;
}
function featuredLimit(){
  return portfolios.comparison ? portfolios.filter(card=>card.featured).length : 12;
}
function showRemainingStrategies(){
  showFullDeck=true;
  showPortfolio();
}
function wealthChart(nav){
  if(!Array.isArray(nav)||nav.length<2||nav.some(x=>!Number.isFinite(x)))return "";
  const fr=window.RM.language==="fr",lo=Math.min(...nav),hi=Math.max(...nav),span=Math.max(hi-lo,.001);
  const xy=nav.map((v,i)=>[24+552*i/(nav.length-1),152-128*(v-lo)/span]);
  const path=xy.map(([x,y],i)=>(i?"L":"M")+x.toFixed(2)+" "+y.toFixed(2)).join(" ");
  const title=fr?"Évolution historique, capital de départ = 100":"Historical performance, starting value = 100";
  return `<figure class="wealth-chart"><figcaption>${esc(title)}</figcaption><svg viewBox="0 0 600 180" role="img" aria-label="${esc(title)}"><path d="M24 152H576 M24 88H576 M24 24H576" stroke="currentColor" opacity=".18" fill="none"/><path d="${path}" fill="none" stroke="#95e8df" stroke-width="3" stroke-linejoin="round"/><circle cx="${xy.at(-1)[0]}" cy="${xy.at(-1)[1]}" r="4" fill="#ff97c1"/></svg><div><span>100</span><strong>${(100*nav.at(-1)).toFixed(1)}</strong></div></figure>`;
}
function strategyMetrics(p, fr){
  const {cagr,vol,sharpe,drawdown}=p.metrics;
  const percentage=new Intl.NumberFormat(fr?"fr":"en",{style:"percent",maximumFractionDigits:2,minimumFractionDigits:2});
  const decimal=new Intl.NumberFormat(fr?"fr":"en",{maximumFractionDigits:2,minimumFractionDigits:2});
  const readings=[
    ["cagr",fr?"Rendement annualisé":"Annualized return",cagr,percentage,fr?"Croissance annuelle composée du capital simulé sur la période testée.":"Compound annual growth of the simulated portfolio over the test period."],
    ["vol",fr?"Volatilité annualisée":"Annualized volatility",vol,percentage,fr?"Amplitude des fluctuations mensuelles, ramenée à une année.":"Magnitude of monthly fluctuations, expressed on an annual scale."],
    ["sharpe",fr?"Ratio de Sharpe":"Sharpe ratio",sharpe,decimal,fr?"Rendement mensuel moyen au-dessus des liquidités USD, divisé par la volatilité de cet écart et annualisé. Le ratio est indéfini si cet écart ne varie pas.":"Mean monthly return above USD cash divided by the volatility of that excess return, annualized. The ratio is undefined when the excess return has no variation."],
    ["drawdown",fr?"Baisse maximale":"Maximum drawdown",Number.isFinite(drawdown)?Math.abs(drawdown):null,percentage,fr?"Plus grand recul du portefeuille entre un sommet et un creux ultérieur sur la période testée.":"Largest portfolio decline from a peak to a subsequent low over the test period."],
    ["stress",fr?"Perte en scénario de stress":"Loss in stress scenario",p.stress_loss,percentage,fr?"Perte simulée dans le choc le plus sévère testé.":"Simulated loss under the most severe hypothetical shock tested."],
  ];
  return readings.map(([key,label,value,format,description])=>({key,label,value:Number.isFinite(value)?format.format(value):"—",description}));
}
function backtestDetails(p,fr){
  if(!p.backtest)return "";
  const {test,development,replay,annual_returns,development_annual_returns,worst_12_months:worst,reference}=p.backtest;
  const percent=new Intl.NumberFormat(fr?"fr":"en",{style:"percent",maximumFractionDigits:2,minimumFractionDigits:2});
  const dates=new Intl.DateTimeFormat(fr?"fr-CH":"en-GB",{dateStyle:"short",timeZone:"UTC"});
  const format=x=>Number.isFinite(x)?percent.format(x):"—";
  const period=row=>`${dates.format(new Date(row.start))} – ${dates.format(new Date(row.end))}`;
  const months=n=>`${n} ${fr?"mois":n===1?"month":"months"}`;
  const table=(title,rowLabel,headers,rows)=>`<div class="backtest-table"><table>
    <caption>${title}</caption><thead><tr><th scope="col">${rowLabel}</th>${headers.map(h=>`<th scope="col">${h}</th>`).join("")}</tr></thead>
    <tbody>${rows.map(([label,...cells])=>`<tr><th scope="row">${label}</th>${cells.map(cell=>`<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody>
    </table></div>`;
  const annual=(title,rows)=>table(title,fr?"Année":"Year",[fr?"Couverture":"Coverage",fr?"Rendement":"Return"],
    rows.map(row=>[row.year,`${months(row.months)}${row.months<12?(fr?" · partielle":" · partial"):""}`,format(row.return)]));
  const performanceHeaders=fr?["Rendement cumulé","Rendement annualisé","Volatilité annualisée","Baisse maximale"]:
    ["Cumulative return","Annualized return","Annualized volatility","Maximum drawdown"];
  const performance=(label,row)=>[label,format(row.cumulative),format(row.cagr),format(row.vol),format(row.drawdown)];
  const dated=(label,row)=>`${label}<small>${period(row)} · ${months(row.months)}</small>`;
  const testLabel=fr?"Test hors échantillon":"Out-of-sample test";
  const comparison=reference&&reference.name!==p.name?
    table(fr?"Comparaison sur les mêmes mois":"Comparison over the same months",fr?"Portefeuille":"Portfolio",performanceHeaders,[
      performance(fr?"Cette stratégie":"This strategy",test),
      performance(esc(strategyName(reference.name)),reference),
    ]):
    `<p class="muted">${reference?(fr?"Cette stratégie sert de référence pour ce mandat.":"This strategy is the reference for this mandate."):
      (fr?"Aucune référence simple compatible n’est disponible sur cette période.":"A compatible simple reference is unavailable for this period.")}</p>`;
  return `<section class="backtest-detail">
    <h3>${testLabel}</h3><p class="muted">${period(test)} · ${months(test.months)} · USD</p>
    <dl class="backtest-highlights">
      <div><dt>${fr?"Rendement cumulé":"Cumulative return"}</dt><dd>${format(test.cumulative)}</dd></div>
      <div><dt>${fr?"Pire rendement sur 12 mois glissants":"Worst rolling 12-month return"}</dt>
        <dd>${worst?format(worst.return):"—"}${worst?`<small>${period(worst)}</small>`:""}</dd></div>
    </dl>
    ${annual(fr?"Rendements par année civile":"Returns by calendar year",annual_returns)}
    ${comparison}
    <details class="backtest-longer"><summary>${fr?"Rejeu historique complet":"Full historical replay"} · ${months(replay.months)}</summary>
      <p>${fr?"La période de développement sert à l’analyse préalable. Le rejeu complet réunit le développement et le test hors échantillon.":"The development period supports preliminary analysis. The full replay combines development and out-of-sample testing."}</p>
      ${table(fr?"Résultats par période":"Results by period",fr?"Période":"Period",performanceHeaders,[
        ...(development?[performance(dated(fr?"Développement":"Development",development),development)]:[]),
        performance(dated(testLabel,test),test),
        performance(dated(fr?"Rejeu complet":"Full replay",replay),replay),
      ])}
      ${development?annual(fr?"Rendements annuels pendant le développement":"Calendar returns during development",development_annual_returns):""}
    </details>
  </section>`;
}
function detail(p, explain=true){
  const fr=window.RM.language==="fr";
  const metrics=strategyMetrics(p,fr).filter(({key})=>key!=="sharpe"||Object.hasOwn(p.metrics,"sharpe"));
  const positions=Object.entries(p.weights).filter(([,v])=>Math.abs(v)>1e-7).sort((a,b)=>b[1]-a[1]);
  const holdingRows=rows=>rows.map(([k,v])=>`<div><p><span>${esc(t(k))}</span><strong>${pct(v)}</strong></p><div class="bar"><i style="width:${Math.max(0,Math.min(100,100*v))}%"></i></div></div>`).join("");
  return `<div class="strategy-title"><h2>${esc(strategyName(p.name))}</h2><span class="simulation-tag">${p.personalized?(fr?"Construit pour ton mandat":"Built for your mandate"):(fr?"Simulation historique":"Historical simulation")}</span></div>
  ${p.personalized&&p.model_as_of?`<p class="strategy-dates">${fullMandate?.as_of?`${fr?"Départ du mandat simulé":"Simulated mandate start"} · <strong>${esc(fullMandate.as_of)}</strong><br>`:""}${fr?"Dernières données utilisées pour les poids":"Last data used for the weights"} · <strong>${esc(p.model_as_of)}</strong>${p.estimation_months?` · ${esc(p.estimation_months)} ${fr?"mois d’estimation":"months of estimation"}`:""}<br><span class="muted">${fr?"Estimations sur une archive figée pour reproduire la simulation.":"Estimates use a frozen archive so the simulation can be reproduced."}</span></p>`:""}
  ${explain?strategyExplanation(p):""}
  <p>${fr?"Dans le scénario de perte le plus sévère testé, ton capital baisse de":"In the worst loss scenario tested, your capital falls by"} <strong>${money(p.stress_usd,"USD")}</strong> (${pct(p.stress_loss)}).</p>
  ${backtestDetails(p,fr)}
  ${window.Journey?.timeline(p.metrics.nav)||wealthChart(p.metrics.nav)}
  ${window.Journey?.composition(p)||""}
  ${window.Journey?.goals(p.goal_projection)||""}
  <details><summary>${fr?"Comment lire les chiffres ?":"How do I read the numbers?"}</summary><dl>${metrics.map(({label,value,description})=>`<dt>${label} · ${value}</dt><dd>${description}</dd>`).join("")}</dl><p>${fr?"Perte moyenne pendant les 5 % de mois les plus défavorables":"Average loss across the worst 5% of months"} · ${pct(p.metrics.es95_monthly)}</p></details>
  <details><summary>${fr?"Voir les placements":"View holdings"} (${positions.length})</summary><div class="holdings-list">${holdingRows(positions)}</div></details>
  ${p.sensitivity_ranks?`<p>${fr?"Rang selon la priorité donnée à la sécurité":"Rank by emphasis on safety"} · ${p.sensitivity_ranks.join(" / ")}. ${fr?"Comparaison entre moins de poids, ton réglage et plus de poids pour la sécurité (±10 points).":"Less emphasis, your setting, and more emphasis (±10 percentage points)."}</p>`:""}
  ${p.income_preference_unmeasured?`<p>${fr?"Les versements de revenu ne sont pas mesurés.":"Income distributions are unmeasured."}</p>`:""}
  ${p.equivalent_methods?.length?`<details><summary>${fr?"Méthodes aux poids actuels proches · la courbe représente uniquement la méthode affichée":"Similar current holdings · the chart represents the displayed method only"}</summary>${p.equivalent_methods.map(n=>esc(strategyName(n))).join(", ")}</details>`:""}
  ${p.personalized?`<p class="muted">${fr?"Univers admissible":"Eligible universe"} : ${p.eligible_assets}/${p.universe_size} · ${fr?"Rendement estimé":"Estimated return"} : ${pct(p.expected_return)} · ${fr?"Volatilité estimée":"Estimated volatility"} : ${pct(p.estimated_volatility)}</p>
  ${p.goal_projection?`<details><summary>${fr?"Projection de tes objectifs":"Your goal projections"}</summary><p class="muted">${p.goal_projection_paths} ${fr?"trajectoires conditionnelles":"conditional paths"} · ${p.development_months} ${fr?"mois de données rééchantillonnés":"months of resampled history"}</p>${p.goal_projection.map(g=>`<p>${esc(t(g.objective_id))} · ${fr?"Probabilité simulée":"Simulated probability"}: ${g.probability===null?"—":pct(g.probability)} · ${fr?"Déficit attendu":"Expected shortfall"}: ${money(g.expected_deficit,"USD")}${g.window_probabilities?.every(Number.isFinite)?` · ${fr?"Probabilité sur chacune des deux moitiés de l’historique":"Probability using each half of the history"} ${g.window_probabilities.map(pct).join(" / ")}`:""}</p>`).join("")}</details>`:""}
  <p class="muted">${fr?"La courbe suit cette méthode réestimée chaque trimestre, avec un mois de délai. Les actions sont sélectionnées à chaque date. La liste des ETF est rétrospective et les dates de publication des rendements sont incomplètes.":"The curve re-estimates this method quarterly with a one-month lag. Stock membership is dated, the ETF list is retrospective, and return publication dates are incomplete."}</p>`:""}
  <details class="strategy-method"><summary>${fr?"Période et hypothèses":"Period and assumptions"}</summary><p class="muted">${esc(t(p.period))} · ${esc(t(p.costs))}</p></details>`;
}
const strategyArt = {
  calm:["Cash","Conservative","Fixed income","defensive_reference","minimum_variance","inverse_variance","minimum_cvar","minimum_cdar"],
  balance:["risk_parity","hrp","herc","maximum_diversification","mean_variance_utility","constrained_utility","entropy_utility","resampled_utility","maximum_sortino","fractional_kelly"],
  trend:["Growth","active_long_only","cross_sectional_momentum","time_series_momentum","mean_reversion","tactical_allocation","ewma_utility","regime_switching","global_macro","maximum_sharpe","maximum_omega","kelly"],
  factors:["smart_beta_factor","smart_beta_fundamental","factor_investing","black_litterman","capm_utility"],
  hedge:["tail_hedge_proxy","volatility_target","tracking_error","robust_utility","wasserstein_utility"],
  allocation:["equal_weight","passive_index","passive_etfs","smart_beta_equal","core_satellite","all_weather","multi_strategy","60/40","1/N"],
};
function strategyCover(name) {
  if(name.startsWith("factor_"))return "factors";
  return Object.keys(strategyArt).find(art=>strategyArt[art].includes(name))||"balance";
}
function showPortfolio(){
  const p=portfolios[swipes.length],fr=window.RM.language==="fr";
  $("reject").textContent=fr?"✕ Pas de match":"✕ No match";$("like").textContent="♥ Match";
  for(const id of ["like","reject","skip"])$(id).disabled=!p;
  $("undo").disabled=!swipes.length;
  if(historicalDeck&&p&&swipes.length>=featuredLimit()&&!showFullDeck){
    for(const id of ["like","reject","skip"])$(id).disabled=true;
    $("portfolio").replaceChildren();
    const more=document.createElement("button");
    more.textContent=fr?"Voir les autres stratégies compatibles":"View remaining compatible strategies";
    more.onclick=showRemainingStrategies;$("portfolio").append(more);
    $("portfolio").insertAdjacentHTML("beforeend",strategyDeckList(fr));return;
  }
  if(!p){
    $("portfolio").innerHTML=(portfolios.length?"<article>"+esc(t("end"))+": "+shortlist.length+"</article>":"<article>"+esc(t("matchingEmpty"))+"</article>")+strategyDeckList(fr);
    return;
  }
  const count=swipes.length+1,model=strategyName(p.name);
  const title=esc(model);
  const narrative=strategyDescription(p.name);
  const metrics=strategyMetrics(p,fr);
  const period=p.period?esc(t(p.period)):"";
  const synthetic=p.version==="synthetic-v1";
  const history=synthetic?(fr?"Simulation sur données synthétiques":"Simulation on synthetic data"):(fr?"Simulation sur données historiques":"Simulation on historical data");
  const selection=p.personalized? `<p class="muted">${p.featured?
    (fr?"Sélection pour ton mandat · adéquation aux objectifs, au risque et diversité des allocations.":"Featured for your mandate · goal fit, risk fit and allocation diversity.") :
    (fr?"Toutes les stratégies compatibles":"All compatible strategies")}
    ${!showFullDeck&&portfolios.length>featuredLimit()?`<button type="button" id="show-full-deck">${fr?"Parcourir toutes les cartes":"Browse all cards"}</button>`:""}</p>`:"";
  $("portfolio").innerHTML=`${selection}<article class="voyage-card">
    <div class="voyage-cover" data-art="${strategyCover(p.name)}"><span>${fr?"Stratégie":"Strategy"} ${count} / ${portfolios.length}</span></div>
    <div class="voyage-face"><h2>${title}</h2>${narrative?`<p>${esc(narrative)}</p>`:""}
    <small>${history}${period?` · ${period}`:""}</small>
    <dl class="strategy-card-metrics">${metrics.map(({key,label,value})=>`<div><dt>${label}</dt><dd>${value}${key==="stress"&&Number.isFinite(p.stress_usd)?`<small>${money(p.stress_usd,"USD")}</small>`:""}</dd></div>`).join("")}</dl></div>
    <div class="voyage-reveal strategy-explanation">${strategyExplanation(p)}</div>
    <details class="voyage-reveal"><summary>${fr?"Explorer la composition et les résultats":"Explore holdings and results"}</summary>${detail(p,false)}</details></article>${strategyDeckList(fr)}`;
  const all=$("show-full-deck");
  if(all)all.onclick=showRemainingStrategies;
}
function strategyVerdict(choice, portfolio){
  const dialog=$("strategy-verdict");
  if(typeof dialog?.showModal!=="function")return;
  const fr=window.RM.language==="fr",matched=choice==="like";
  dialog.dataset.matched=String(matched);
  $("verdict-title").textContent=matched?"MATCH !":fr?"PAS DE MATCH":"NO MATCH";
  $("verdict-strategy").textContent=strategyName(portfolio.name);
  $("verdict-next").textContent=fr?"Continuer":"Continue";
  $("verdict-next").onclick=()=>dialog.close();
  dialog.showModal();
}
function swipe(choice){if($("strategy-verdict")?.open||!sessionUnlocked||(historicalDeck&&swipes.length>=featuredLimit()&&!showFullDeck))return;const p=portfolios[swipes.length];if(!p)return;swipes.push(choice);if(choice==="like"){shortlist.push(p);savedBlend=null;}showPortfolio();changed();if(choice==="like"||choice==="dislike")strategyVerdict(choice,p);}
let strategyDrag=null;
const deckSurface=$("portfolio");
deckSurface.addEventListener("pointerdown",event=>{
  if(event.button!==0||!event.isPrimary||activePage!=="explore"||event.target.closest("button,summary,details,input,select,label,a"))return;
  const article=event.target.closest("article");
  if(!article||$("like").disabled)return;
  strategyDrag={article,id:event.pointerId,x:event.clientX,y:event.clientY};
});
deckSurface.addEventListener("pointermove",event=>{
  if(strategyDrag?.id!==event.pointerId)return;
  const {article,x,y}=strategyDrag,dx=event.clientX-x;
  if(Math.abs(event.clientY-y)>Math.abs(dx)+15){article.style.transform="";delete article.dataset.drag;strategyDrag=null;return;}
  if(Math.abs(dx)>12){
    deckSurface.setPointerCapture(event.pointerId);
    article.dataset.drag=dx>0?"like":"pass";
    article.dataset.verdict=dx>0?"♥ Match":window.RM.language==="fr"?"✕ Passer":"✕ Pass";
    if(!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches)
      article.style.transform=`translateX(${Math.max(-130,Math.min(130,dx*.48))}px) rotate(${Math.max(-8,Math.min(8,dx/18))}deg)`;
  }else{delete article.dataset.drag;article.style.transform="";}
});
function finishStrategyDrag(event){
  if(strategyDrag?.id!==event.pointerId)return;
  const {article,x,y}=strategyDrag;strategyDrag=null;article.style.transform="";delete article.dataset.drag;
  const dx=event.clientX-x;
  if(event.type==="pointerup"&&Math.abs(dx)>65&&Math.abs(dx)>1.4*Math.abs(event.clientY-y)&&article.isConnected)swipe(dx>0?"like":"dislike");
}
for(const event of ["pointerup","pointercancel","lostpointercapture"])deckSurface.addEventListener(event,finishStrategyDrag);
$("like").onclick=()=>swipe("like");$("reject").onclick=()=>swipe("dislike");$("skip").onclick=()=>swipe("skip");
$("undo").onclick=()=>{if(!sessionUnlocked||pendingDeck)return;if(swipes.pop()==="like"){const undone=shortlist.pop();confirmed.delete(undone.name);}showPortfolio();changed();};
function startPaperTracking(host, allocation){
  if(!host||!/^(personalized-v3:|historical-usd-v1-)/.test(allocation.version))return false;
  const next=window.PaperTracking.capture(allocation.weights,mandate.capital,paperTracking);
  if(!next)return false;
  paperTracking=next;
  window.PaperTracking.mount(host,paperTracking,api,changed);
  return true;
}
function portfolioProjection(report,fr){
  const m=report.matched, curve=m.wealth_path;
  const model=fr?"1 000 trajectoires · blocs communs de six mois · poids des titres rééquilibrés chaque mois":
    "1,000 paths · shared six-month blocks · monthly asset rebalancing";
  const label=fr?"Capital simulé après flux":"Simulated balance after cash flows";
  let chart="";
  if(curve?.bands?.length>1){
    const scale=Math.max(1,...curve.bands.map(row=>row[2]));
    const path=(q)=>curve.bands.map((row,i)=>[36+528*i/(curve.bands.length-1),158-136*row[q]/scale]);
    const band=[...path(0),...path(2).reverse()].map(p=>p.map(x=>x.toFixed(1)).join(",")).join(" ");
    const mid=path(1).map(p=>p.map(x=>x.toFixed(1)).join(",")).join(" ");
    chart=`<figure class="wealth-chart"><figcaption>${label} · ${fr?"bande P5–P95, trait médian":"P5–P95 band, median line"}</figcaption>
      <svg viewBox="0 0 600 180" role="img" aria-label="${label}"><path d="M36 22v136h528" stroke="currentColor" fill="none"/>
      <polygon points="${band}" fill="currentColor" opacity=".2"/><polyline points="${mid}" fill="none" stroke="currentColor" stroke-width="2.5"/></svg>
      <div><span>${esc(curve.dates[0])}</span><span>${esc(curve.dates.at(-1))}</span></div></figure>`;
  }
  const summary=m.market_cagr_quantiles?`<p><strong>${fr?"Rendement annualisé simulé hors flux":"Simulated annualized return excluding cash flows"}</strong> · P5 ${pct(m.market_cagr_quantiles[0])} · ${fr?"médiane":"median"} ${pct(m.market_cagr_quantiles[1])} · P95 ${pct(m.market_cagr_quantiles[2])}</p>
    <p>${fr?"Trajectoires en perte hors flux à l’horizon":"Paths ending in a loss excluding cash flows"} · ${pct(m.market_loss_probability)}</p>
    <p>${fr?"Trajectoires dont le recul hors flux dépasse le seuil de perte du mandat":"Paths whose drawdown excluding cash flows exceeds the mandate loss threshold"} (${pct(m.drawdown_threshold)}) · ${pct(m.drawdown_breach_probability)}</p>`:"";
  return `<p>${report.method==="joint_asset_blocks"?model:(fr?"Projection de recherche par poches":"Research projection by sleeve")} · ${report.training_months} ${fr?"mois de données":"months of data"}</p>
    ${chart}${summary}<p>${fr?"Capital restant à l’horizon, après apports, retraits et objectifs payés":"Remaining capital at horizon after contributions, withdrawals and funded goals"} ·
    P5 ${money(m.terminal_quantiles[0],"USD")} · ${fr?"médiane":"median"} ${money(m.terminal_quantiles[1],"USD")} · P95 ${money(m.terminal_quantiles[2],"USD")} · ${fr?"moyenne":"mean"} ${money(m.mean_terminal_wealth,"USD")}</p>
    <p class="muted">${fr?"P5 et P95 encadrent les 90 % centraux des trajectoires simulées. La projection est conditionnelle aux données figées et aux poids confirmés. Le benchmark des objectifs est le cash USD pour le moteur personnalisé.":"P5 and P95 frame the central 90% of simulated paths. The projection is conditional on the frozen inputs and confirmed weights. For personalized matches the goal benchmark is USD cash."}</p>`;
}
function compare(){
  const area=$("match-allocation");area.replaceChildren();
  const fr=window.RM.language==="fr";
  const resultView=window.PortfolioResult;
  let hasAdvancedSection=false;
  const trackingHost=activePage==="matches"&&window.PaperTracking?document.createElement("div"):null;
  if(trackingHost){
    trackingHost.className="matches-live";
    trackingHost.innerHTML=`<header><h2>${fr?"Suivi en direct":"Live tracking"}</h2><p class="muted">${fr?"Portefeuille simulé · disponibilité selon le flux de cotation.":"Paper portfolio · availability depends on the quote feed."}</p></header>`;
    const trackingBody=document.createElement("div");
    trackingBody.className="matches-live-body";
    trackingHost.append(trackingBody);
    if(!resultView)area.append(trackingHost);
    if(paperTracking){
      window.PaperTracking.mount(trackingBody,paperTracking,api,changed);
    }else{
      trackingBody.innerHTML=`<article>
        <h2>${fr?"Suivi du portefeuille simulé":"Paper portfolio tracking"}</h2>
        <p>${fr?"Pour démarrer, sélectionne une stratégie, calcule ton allocation et confirme-la ci-dessous. Le suivi des positions utilise les derniers cours disponibles si le serveur dispose d’un flux de marché.":"To get started, select a strategy, evaluate your allocation and confirm it below. Position tracking uses the latest available prices when the server has a market data feed."}</p>
      </article>`;
    }
  }
  if(!shortlist.length){
    const empty=document.createElement("article");empty.innerHTML=`<h2>${esc(t("empty"))}</h2><p>${fr?"Sélectionne les stratégies qui te correspondent pour construire ton allocation.":"Choose the strategies that suit you to build your allocation."}</p>`;
    if(activePage==="matches"){
      const button=document.createElement("button");button.className="primary";button.textContent=t("navExplore");
      button.onclick=handle(async()=>{if(!mandate){page("mandate");return;}if(!cards.length||index<cards.length){page("discovery");await showCard();return;}page("explore");await loadPortfolios();});empty.append(button);
    }
    area.append(empty);
    if(resultView&&trackingHost&&paperTracking){
      trackingHost.querySelector("header h2").textContent=fr?"Suivi de ta précédente simulation":"Tracking your previous simulation";
      area.append(trackingHost);
    }
    return;
  }
  if(activePage==="matches" && !resultView && window.Journey && shortlist.length>1){
    const landscape=document.createElement("div");
    landscape.innerHTML=window.Journey.map(shortlist.map(p=>({...p,title:strategyName(p.name)})));area.append(landscape);
  }
  const allocation=document.createElement("article");
  const trackingBody=trackingHost?.querySelector(".matches-live-body");
  const signature=JSON.stringify([fullMandate||mandate,shortlist[0].version,shortlist.map(p=>p.name)]);
  const stored=savedBlend?.signature===signature?savedBlend:null;
  const confirmationStatus=document.createElement("p");
  confirmationStatus.className="allocation-confirmation";
  confirmationStatus.setAttribute?.("role","status");
  const updateConfirmation=()=>{
    const isConfirmed=Boolean(savedBlend?.paperConfirmed&&savedBlend.signature===signature);
    allocation.classList?.toggle("voyage-confirmed",isConfirmed);
    confirmationStatus.hidden=!isConfirmed;
    confirmationStatus.textContent=isConfirmed?(fr?"Allocation confirmée en simulation":"Confirmed paper allocation"):"";
    if(trackingHost){
      trackingHost.querySelector("header h2").textContent=paperTracking&&!isConfirmed
        ? (fr?"Suivi de ta précédente simulation":"Tracking your previous simulation")
        : (fr?"Suivi du portefeuille simulé":"Paper portfolio tracking");
    }
  };
  if(trackingHost&&!paperTracking&&stored?.paperConfirmed&&/^(personalized-v3:|historical-usd-v1-)/.test(shortlist[0].version)){
    const activate=document.createElement("button");
    activate.type="button";
    activate.textContent=fr?"Activer le suivi de mon allocation confirmée":"Start tracking my confirmed allocation";
    activate.onclick=handle(async()=>{
      activate.disabled=true;
      try{
        const evaluated=await api("match-allocations/evaluate",{
          mandate:fullMandate||mandate,names:Object.keys(stored.budgets),
          budgets:Object.values(stored.budgets),version:shortlist[0].version,
        });
        if(!activate.isConnected||savedBlend!==stored)return;
        if(!startPaperTracking(trackingBody,evaluated)){
          throw Error(fr?"Cette allocation ne peut pas être suivie.":"This allocation cannot be tracked.");
        }
        changed();
      }finally{activate.disabled=false;}
    });
    trackingHost.querySelector("article").append(activate);
  }
  allocation.className=resultView?"rm-match-controls":"";
  allocation.id="match-result";
  allocation.innerHTML=resultView
    ? `<h2>${fr?"Ton allocation finale":"Your final allocation"}</h2><p class="rm-result-progress">${fr?"Répartis 100 % entre les stratégies retenues. Calcule ton allocation, puis confirme-la pour voir la projection du mandat.":"Split 100% among your selected strategies. Calculate your allocation, then confirm it to see your mandate projection."}</p>${historicalDeck&&fullMandate?`<nav class="rm-result-jump"><a href="#match-forecast">${fr?"Projection":"Projection"}</a><a href="#match-advanced">${fr?"Analyses complémentaires":"Additional analysis"}</a></nav>`:""}`
    : `<h2>${fr?"Mes Matches":"My Matches"}</h2><p>${historicalDeck?(fr?"Simulation sur rendements historiques en USD.":"USD historical return simulation."):(fr?"Simulation illustrative.":"Illustrative simulation.")}</p>`+mandateTrace(fullMandate,mandateReport);
  updateConfirmation();
  allocation.append(confirmationStatus);
  const inputs=shortlist.map(p=>{
    const label=document.createElement("label");label.className="allocation-row";label.textContent=strategyName(p.name)+" (%) ";
    const input=document.createElement("input");input.type="number";input.min="0";input.max="100";input.step="any";input.value=100/shortlist.length;
    if(stored?.budgets?.[p.name]!=null)input.value=100*stored.budgets[p.name];
    label.append(input);allocation.append(label);return input;
  });
  const total=document.createElement("p");total.className="allocation-total";
  const updateTotal=()=>{const sum=inputs.reduce((acc,input)=>acc+Number(input.value),0);total.textContent=(fr?"Budget réparti":"Total allocated")+" · "+sum.toFixed(2)+" %";total.classList?.toggle("mandate-conflict",Math.abs(sum-100)>1e-6);};
  updateTotal();allocation.append(total);
  const output=document.createElement("div");
  const renderAllocation=result=>{
    if(resultView&&result.personalized){
      output.innerHTML=resultView.allocation(result,fullMandate,mandateReport,strategyName,fr)+mandateTrace(fullMandate,mandateReport);
      return;
    }
    output.innerHTML=detail({...result,name:fr?"Portefeuille combiné":"Combined portfolio",period:result.period||"36 synthetic out-of-calibration months"})+`<h3>${fr?"Contributions au risque":"Risk contributions"}</h3>`+Object.entries(result.risk_contributions).map(([name,value])=>`<p>${esc(t(name))}: ${pct(value)}</p>`).join("");
  };
  let revision=0;
  let refreshProjection=null, clearAnalysis=()=>{};
  for(const optimized of (shortlist[0].personalized?[false,true,"return","goal"]:[false,true])){
    const button=document.createElement("button");button.textContent=optimized==="goal"?(fr?"Comparer selon mon objectif prioritaire":"Compare for my priority goal"):optimized==="return"?(fr?"Maximiser le rendement estimé":"Maximize estimated return"):optimized?(fr?"Minimiser les fluctuations historiques":"Minimize historical volatility"):(fr?"Calculer mon allocation":"Evaluate allocation");
    button.onclick=handle(async()=>{
      const requestRevision=++revision;
      output.replaceChildren();
      if(!optimized&&inputs.some(input=>String(input.value).trim()===""||!input.validity.valid))throw Error(fr?"Allocation invalide":"Invalid allocation");
      if(!optimized&&Math.abs(inputs.reduce((s,i)=>s+Number(i.value),0)-100)>1e-6)throw Error(fr?"Les allocations doivent totaliser 100 %.":"Allocations must total 100%.");
      output.textContent=t("allocationLoading");
      let result;
      try{result=await api("match-allocations/"+(optimized==="goal"?"goal":optimized==="return"?"return":optimized?"optimize":"evaluate"),{mandate:fullMandate||mandate,names:shortlist.map(p=>p.name),budgets:inputs.map(i=>Number(i.value)/100),version:shortlist[0].version});}
      catch(e){if(allocation.isConnected&&revision===requestRevision)output.textContent=diagnostic(e.message);throw e;}
      if(!allocation.isConnected||revision!==requestRevision)return;
      if(optimized)inputs.forEach((input,i)=>{input.value=result.budgets[shortlist[i].name]*100;});
      updateTotal();
      savedBlend={signature,budgets:result.budgets};updateConfirmation();clearAnalysis();changed();
      renderAllocation(result);
      if(!resultView&&Number.isFinite(result.historical_annual_mean))output.insertAdjacentHTML("beforeend",`<p>${fr?"Moyenne arithmétique historique annualisée":"Annualized historical arithmetic mean"} · ${pct(result.historical_annual_mean)}</p>`);
      if(optimized==="return")output.insertAdjacentHTML("beforeend",`<p class="muted">${fr?"Maximiser le rendement estimé seul concentre le budget sur la stratégie retenue ayant l’estimation la plus élevée. La diversification éventuelle vient des titres de cette stratégie.":"Maximizing estimated return alone concentrates the budget on the retained strategy with the highest estimate. Any diversification comes from that strategy’s holdings."}</p>`);
      if(result.comparison){
        const labels=fr?["Mon choix","Variance minimale","Objectif prioritaire"]:["My choice","Minimum variance","Priority goal"];
        output.insertAdjacentHTML("beforeend",`<h3>${fr?"Comparaison des répartitions":"Allocation comparison"}</h3><p>${result.tested_budgets} ${fr?"répartitions testées":"allocations tested"}</p><div class="match-table-scroll"><table><thead><tr><th></th>${labels.map(label=>`<th>${label}</th>`).join("")}</tr></thead><tbody>${shortlist.map(p=>`<tr><th>${esc(strategyName(p.name))}</th>${Object.values(result.comparison).map(row=>`<td>${pct(row.budgets[p.name])}</td>`).join("")}</tr>`).join("")}<tr><th>Stress</th>${Object.values(result.comparison).map(row=>`<td>${pct(row.stress_loss)}</td>`).join("")}</tr>${result.comparison.goal.goals.map((g,i)=>`<tr><th>${esc(t(g.objective_id))} · ${fr?"Probabilité / déficit":"Probability / deficit"}</th>${Object.values(result.comparison).map(row=>`<td>${row.goals[i].probability==null?"—":pct(row.goals[i].probability)} / ${money(row.goals[i].expected_deficit,"USD")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      }
      if(!resultView&&result.reference_metrics)output.insertAdjacentHTML("beforeend",`<p>${result.benchmark?esc(strategyName(result.benchmark)):"60/40"} · CAGR ${pct(result.reference_metrics.cagr)} · ${esc(t("vol"))} ${pct(result.reference_metrics.vol)}</p>`);
      if(result.overlap?.length)output.insertAdjacentHTML("beforeend",`<details><summary>${fr?"Positions communes aux stratégies":"Holdings shared by strategies"} (${result.overlap.length})</summary><p>${result.overlap.map(esc).join(", ")}</p></details>`);
      if(Number.isFinite(result.additional_transfer_fee_fraction))output.insertAdjacentHTML("beforeend",`<details><summary>${fr?"Frais simulés et mouvements":"Modeled fees and turnover"}</summary><p>${fr?"Somme des frais de transfert supplémentaires rapportés aux valeurs mensuelles":"Sum of extra transfer fees relative to monthly NAV"} · ${pct(result.additional_transfer_fee_fraction)} · ${fr?"Turnover annualisé":"Annualized turnover"} ${pct(result.additional_transfer_turnover)}</p></details>`);
      if(result.correlations&&shortlist.length>1){
        const pairs=shortlist.flatMap((p,i)=>shortlist.slice(i+1).map((q,j)=>
          `<p>${esc(strategyName(p.name))} / ${esc(strategyName(q.name))} · ${Number.isFinite(result.correlations[i]?.[i+j+1])?result.correlations[i][i+j+1].toFixed(2):"—"}</p>`));
        output.insertAdjacentHTML("beforeend",`<details><summary>${fr?"Corrélations":"Correlations"}</summary>${pairs.join("")}</details>`);
      }
      const confirm=document.createElement("button");
      confirm.className="primary";
      confirm.textContent=fr?"Confirmer cette simulation":"Confirm paper allocation";
      confirm.onclick=handle(async()=>{
        if(confirm.disabled)return;
        confirm.disabled=true;
        let evaluated;
        try{evaluated=await api("match-allocations/evaluate",{mandate:fullMandate||mandate,names:Object.keys(result.budgets),budgets:Object.values(result.budgets),version:result.version});}
        catch(error){if(confirm.isConnected)confirm.disabled=false;throw error;}
        if(!confirm.isConnected||requestRevision!==revision)return;
        savedBlend={signature,budgets:result.budgets,paperConfirmed:true};
        startPaperTracking(trackingBody,evaluated);
        updateConfirmation();
        changed();
        confirm.textContent=fr?"Simulation confirmée":"Paper allocation confirmed";
        await refreshProjection?.();
        if(resultView&&confirm.isConnected)document.getElementById("match-forecast")?.scrollIntoView?.({behavior:"smooth",block:"start"});
      });
      (resultView&&output.querySelector?.(".rm-result-lead")||output).append(confirm);
    });allocation.append(button);
  }
  inputs.forEach(input=>input.oninput=()=>{revision++;savedBlend=null;updateConfirmation();clearAnalysis();updateTotal();changed();output.replaceChildren();});
  allocation.append(output);if(activePage==="matches")area.append(allocation);
  if(resultView&&stored?.paperConfirmed){
    void handle(async()=>{
      const saved=stored, rev=revision;
      const result=await api("match-allocations/evaluate",{
        mandate:fullMandate||mandate,names:Object.keys(saved.budgets),budgets:Object.values(saved.budgets),version:shortlist[0].version
      });
      if(allocation.isConnected&&revision===rev&&savedBlend===saved)renderAllocation(result);
    })();
  }
  if(activePage==="matches"&&historicalDeck&&fullMandate){
    const goals=document.createElement("article"),goalButton=document.createElement("button"),goalOutput=document.createElement("div");
    goals.id="match-forecast";goals.className="rm-projection";
    goals.innerHTML=`<h2>${fr?"Projection sur ton horizon":"Projection over your horizon"}</h2>`;
    goalButton.textContent=fr?"Actualiser la projection":"Refresh projection";
    const controls=document.createElement("div"),rateLabel=document.createElement("label"),rateInput=document.createElement("input"),rateNote=document.createElement("p");
    controls.className="rm-discount-controls";rateNote.className="rm-note";
    rateLabel.textContent=fr?"Taux d’actualisation annuel (%)":"Annual discount rate (%)";
    rateInput.type="number";rateInput.min="-5";rateInput.max="30";rateInput.step="any";
    if(stored?.discountRate!=null)rateInput.value=100*stored.discountRate;
    rateLabel.append(rateInput);controls.append(rateLabel,goalButton);
    rateNote.textContent=fr?"Vide, RiskMatch utilise le rendement composé du cash USD sur sa fenêtre historique. Le taux modifie les valeurs actuelles.":"Left blank, RiskMatch uses the compound USD cash return over its historical window. The rate changes present values.";
    const pending=fr?"Confirme ton allocation pour lancer la projection.":"Confirm your allocation to start the projection.";
    goalOutput.textContent=pending;goalButton.disabled=!stored?.paperConfirmed;
    clearAnalysis=()=>{goalOutput.replaceChildren();goalOutput.textContent=pending;goalButton.disabled=true;};
    let projectionRequest=0;
    refreshProjection=handle(async()=>{
      if(!savedBlend?.paperConfirmed||savedBlend.signature!==signature)throw Error(fr?"Confirmez d’abord votre allocation.":"Confirm your paper allocation first.");
      const rate=String(rateInput.value??"").trim()===""?null:Number(rateInput.value)/100;
      if(rate!==null&&(!Number.isFinite(rate)||rate<-.05||rate>.30))throw Error(fr?"Entre un taux entre −5 % et 30 %.":"Enter a rate between −5% and 30%.");
      const rev=revision, seq=++projectionRequest;
      goalButton.disabled=true;
      goalOutput.textContent=fr?"Simulation des objectifs en cours…":"Simulating your goals…";
      let r;
      try{r=await api("matching/goals",{mandate:fullMandate,names:Object.keys(savedBlend.budgets),budgets:Object.values(savedBlend.budgets),version:shortlist[0].version,discount_rate:rate});}
      catch(e){if(goals.isConnected&&rev===revision&&seq===projectionRequest)goalOutput.textContent=diagnostic(e.message);throw e;}
      finally{if(goals.isConnected&&rev===revision&&seq===projectionRequest)goalButton.disabled=false;}
      if(!goals.isConnected||rev!==revision||seq!==projectionRequest)return;
      if(savedBlend.discountRate!==rate){savedBlend.discountRate=rate;changed();}
      if(resultView){goalOutput.innerHTML=resultView.projection(r,t,fr);return;}
      const moneyValue=v=>v==null?"—":Number(v).toFixed(0);
      const probability=v=>v==null?"—":pct(v);
      goalOutput.innerHTML=portfolioProjection(r,fr)+(window.Journey?.goals(r.matched.goals)||"")+(window.Journey?r.matched.goals.map(window.Journey.range).join(""):"")+`<div class="match-table-scroll"><table><thead><tr><th>${fr?"Objectif":"Objective"}</th><th>${fr?"Probabilité":"Probability"}</th><th>${fr?"Déficit attendu USD":"Expected deficit USD"}</th><th>${fr?"Prob. référence":"Reference probability"}</th></tr></thead><tbody>${r.matched.goals.map((g,i)=>`<tr><td>${esc(t(g.objective_id))} · ${esc(g.due_date)}</td><td>${probability(g.probability)}</td><td>${moneyValue(g.expected_deficit)}</td><td>${probability(r.reference.goals[i]?.probability)}</td></tr>`).join("")}</tbody></table></div>`;
    });goalButton.onclick=refreshProjection;goals.append(controls,rateNote,goalOutput);area.append(goals);
    if(stored?.paperConfirmed)void refreshProjection();
  }
  if(activePage==="matches"&&historicalDeck&&fullMandate&&mandateReport?.dynamic_overlay_available===false){
    const disabled=document.createElement("p");
    disabled.textContent=t("dynamicUnavailableMandate");
    area.append(disabled);
  }else if(activePage==="matches"&&historicalDeck){
    const dynamic=document.createElement("article");
    dynamic.innerHTML=`<p>${fr?"Compare 10 règles de gestion et 2 références sur les mêmes mois historiques. Ces règles ajustent la part investie et la réserve en cash.":"Compare 10 management rules and 2 benchmarks over the same historical months. These rules adjust invested exposure and cash reserves."}</p>`;
    const run=document.createElement("button"), result=document.createElement("div");
    const clearProjection=clearAnalysis;
    clearAnalysis=()=>{clearProjection();result.replaceChildren();};
    const costLabel=document.createElement("label"),costInput=document.createElement("input");
    costLabel.textContent=fr?"Frais par transfert (pb) ":"Transfer fee (bp) ";
    costInput.type="number";costInput.min="0";costInput.max="100";costInput.value=10;costLabel.append(costInput);
    const frequency=document.createElement("select");
    for(const [value,label] of [[1,fr?"Mensuel":"Monthly"],[3,fr?"Trimestriel":"Quarterly"]]){
      const option=document.createElement("option");option.value=value;option.textContent=label;frequency.append(option);
    }
    frequency.value="1";
    run.textContent=fr?"Simuler les politiques":"Simulate policies";
    run.onclick=handle(async()=>{
      if(!savedBlend?.paperConfirmed||savedBlend.signature!==signature)throw Error(fr?"Confirmez d’abord votre allocation.":"Confirm your paper allocation first.");
      const revisionAtStart=revision;
      result.textContent=fr?"Calcul en cours…":"Calculating…";
      const cost=Number(costInput.value);
      const frequencyAtStart=Number(frequency.value);
      if(costInput.value===""||!Number.isFinite(cost)||cost<0||cost>100)throw Error(fr?"Frais invalides.":"Invalid fee.");
      let r;
      try{r=await api("dynamic",{mandate:fullMandate||mandate,names:Object.keys(savedBlend.budgets),budgets:Object.values(savedBlend.budgets),version:shortlist[0].version,cost_bps:cost,frequency:frequencyAtStart});}
      catch(e){if(dynamic.isConnected&&revision===revisionAtStart)result.textContent=diagnostic(e.message);throw e;}
      if(!dynamic.isConnected||revision!==revisionAtStart)return;
      result.innerHTML=`<p>${fr?"Simulation historique USD · frais supplémentaires par transfert.":"Historical USD simulation · additional transfer fees."} · ${cost} bp</p><div class="match-table-scroll"><table><thead><tr><th>${fr?"Politique":"Policy"}</th><th>CAGR</th><th>${fr?"Volatilité":"Volatility"}</th><th>Drawdown</th><th>ES 95%</th><th>Turnover</th><th>${fr?"Frais USD":"Fees USD"}</th></tr></thead><tbody>${Object.entries(r.policies).map(([name,v])=>`<tr><td>${esc(name.replaceAll("_"," "))}</td>${v.status==="computed"?`<td>${pct(v.cagr)}</td><td>${pct(v.volatility)}</td><td>${pct(v.drawdown)}</td><td>${pct(v.expected_shortfall)}</td><td>${pct(v.annual_turnover)}</td><td>${v.fees.toFixed(2)}</td>`:`<td colspan="6">${esc(v.status)}</td>`}</tr>`).join("")}</tbody></table></div>`;
      const select=document.createElement("select"),ledger=document.createElement("div");
      ledger.className="match-table-scroll";
      for(const name of Object.keys(r.policies)){const option=document.createElement("option");option.value=name;option.textContent=name.replaceAll("_"," ");select.append(option);}
      const refresh=()=>{const v=r.policies[select.value];if(!v)return;ledger.innerHTML=`<table><thead><tr><th>Date</th><th>${fr?"Capital USD":"Capital USD"}</th><th>${fr?"Investi":"Invested"}</th><th>Stress</th><th>${fr?"Vol. estimée":"Est. vol."}</th><th>${fr?"Frais":"Fees"}</th></tr></thead><tbody>${(v.ledger||[]).map(row=>`<tr><td>${esc(row.date)}</td><td>${row.ending.toFixed(2)}</td><td>${pct(row.fraction)}</td><td>${pct(row.stress_estimate)}</td><td>${pct(row.annual_volatility)}</td><td>${row.fee.toFixed(2)}</td></tr>`).join("")}</tbody></table>`;};
      select.onchange=refresh;result.append(select,ledger);select.value="static";refresh();
      const download=document.createElement("button");
      download.textContent=fr?"Exporter le rapport de simulation ZIP":"Export paper simulation ZIP";
      download.onclick=handle(async()=>{
        if(!savedBlend?.paperConfirmed||savedBlend.signature!==signature||revision!==revisionAtStart)throw Error(fr?"Recalculez la simulation.":"Recalculate the simulation.");
        const archive=await api("paper/export",{mandate:fullMandate||mandate,names:Object.keys(savedBlend.budgets),budgets:Object.values(savedBlend.budgets),version:shortlist[0].version,cost_bps:cost,frequency:frequencyAtStart,policy:select.value});
        if(!dynamic.isConnected||revision!==revisionAtStart)return;
        const bytes=Uint8Array.from(atob(archive.archive),c=>c.charCodeAt(0));
        const url=URL.createObjectURL(new Blob([bytes],{type:"application/zip"}));
        const link=document.createElement("a");link.href=url;link.download=archive.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
      });result.append(download);
    });
    dynamic.append(costLabel,frequency,run,result);
    if(resultView){
      const advanced=document.createElement("details"), summary=document.createElement("summary");
      advanced.id="match-advanced";advanced.className="rm-optional-report";
      summary.textContent=fr?"Gestion dynamique · comparaison historique":"Dynamic management · historical comparison";
      advanced.append(summary,dynamic);area.append(advanced);
      hasAdvancedSection=true;
    }else area.append(dynamic);
  }
  if(activePage==="matches"){
    const details=document.createElement("details");details.className="matched-strategies";
    const summary=document.createElement("summary");summary.textContent=fr?"Détail de mes stratégies sélectionnées":"Details of my selected strategies";details.append(summary);
    shortlist.forEach(p=>{const article=document.createElement("article");article.innerHTML=detail(p);details.append(article);});
    if(!hasAdvancedSection)details.id="match-advanced";
    details.className+=" rm-optional-report";
    area.append(details);
    if(resultView&&trackingHost)area.append(trackingHost);
    return;
  }
  shortlist.forEach(p=>{
    const article=document.createElement("article");article.innerHTML=detail(p);
    const button=document.createElement("button");
    function update(){button.disabled=confirmed.has(p.name);button.textContent=t(button.disabled?"selected":"select");}
    button.onclick=()=>{if(sessionUnlocked){confirmed.add(p.name);update();changed();}};update();article.append(button);area.append(article);
  });
}
document.addEventListener("riskmatch:language",()=>{
  $("error").textContent=errorKey?diagnostic(errorKey):"";
  if(activePage==="discovery")showCard().catch(e=>{$("error").textContent=t(e.message);});
  if(activePage==="explore"&&portfolios.length)showPortfolio();
  if(activePage==="matches")compare();
  if(activePage==="universe")window.UniverseView.render();
  if(activePage==="sources")window.SourcesView.render();
  if(activePage==="mandate"&&!$("mandate-report").hidden)renderMandateReport();
});

// Store simulation and tracking results in the encrypted local save.
function simulationSnapshot() {
  return {version:1,mandate,fullMandate,answers,index,swipes:pendingDeck?.swipes??swipes,historicalDeck,savedBlend:pendingDeck?.savedBlend??savedBlend,paperTracking,deckAversion,deckStyle,deckIds:pendingDeck?.deckIds??portfolios.map(p=>[p.name,p.version]),activePage:lastSimulationPage,discoverySeed,discoveryVersion,discoveryCurrency,discoveryConsent,responseLocales,discoveryConfidence};
}
function clearSimulation(){
  window.PaperTracking?.unmount();
  paperTracking=null;
  historicalDeck=true;savedBlend=null;paperTracking=null;deckAversion=null;showFullDeck=false;pendingDeck=null;deckRequest=null;
  window.GoalsView?.clear();
  window.BaselinesView?.clear();
  window.MeanVarianceView?.clear();
  window.BlackLittermanView?.clear();
  window.HierarchicalView?.clear();
  window.DownsideView?.clear();
  window.AdvancedView?.clear();
  window.LongOnlyView?.clear();
  window.AlternativeView?.clear();
  window.TreasuryView?.clear();
  window.FuturesView?.clear();
  window.WalkForwardView?.clear();
  window.StressMCView?.clear();
  mandate=null;resetDiscovery();portfolios=[];swipes=[];shortlist=[];confirmed.clear();scoreReport=null;
  fullMandate=null;mandateReport=null;pendingMandate=null;pendingReport=null;
  lastSimulationPage="home";
  window.MandateForm.reset();$("card").replaceChildren();$("result").replaceChildren();$("portfolio").replaceChildren();
}
async function restoreSimulation(snapshot){
  if(snapshot?.version!==1 || !snapshot.answers || !Array.isArray(snapshot.swipes))throw Error("saveError");
  if(!snapshot.mandate){clearSimulation();return "home";}
  if(snapshot.fullMandate){
    fullMandate=snapshot.fullMandate;mandateReport=await api("mandate/preview",fullMandate);
    if(mandateReport.status!=="structurally_valid")throw Error("saveError");
  }
  const m=snapshot.mandate;
  const nextMandate=fullMandate?{capital:fullMandate.capital,years:mandateReport.horizon_years,max_stress_loss:mandateReport.effective_stress_limit,currency:fullMandate.currency}:{capital:Number(m.capital),years:Number(m.years),max_stress_loss:Number(m.max_stress_loss),currency:"USD"};
  if(!Number.isFinite(nextMandate.capital)||nextMandate.capital<=0||!Number.isFinite(nextMandate.years)||nextMandate.years<=0||!Number.isFinite(nextMandate.max_stress_loss)||nextMandate.max_stress_loss<0||nextMandate.max_stress_loss>1)throw Error("saveError");
  const currentQuestionnaire=snapshot.discoveryVersion===discoveryQuestionnaireVersion;
  const nextIndex=currentQuestionnaire?Number(snapshot.index):0;
  let nextCards=[];
  if(currentQuestionnaire){
    const restored=await api("discovery/session",{seed:snapshot.discoverySeed,currency:snapshot.discoveryCurrency});
    if(restored.version!==snapshot.discoveryVersion||restored.currency!==nextMandate.currency)throw Error("saveError");
    nextCards=restored.cards;discoverySeed=restored.seed;discoveryVersion=restored.version;discoveryCurrency=restored.currency;discoveryConsent=true;
  }
  historicalDeck=snapshot.historicalDeck??!snapshot.swipes.length;
  deckStyle=snapshot.deckStyle||"000";
  deckAversion=snapshot.deckAversion??null;
  const needDeck=snapshot.swipes.length||["explore","compare","matches"].includes(snapshot.activePage);
  let nextPortfolios=[];
  if(needDeck&&(!fullMandate||(canMatch(mandateReport)&&(deckAversion!==null||mandateReport.personalized_eligible===undefined)))){
    try{nextPortfolios=await fetchDeck(fullMandate||nextMandate);}
    catch(e){
      if(!historicalDeck||!["serverOutdated","networkError"].includes(e.message))throw e;
      if(snapshot.swipes.some(v=>!["like","dislike","skip"].includes(v)))throw Error("saveError");
      pendingDeck={swipes:snapshot.swipes.slice(),deckIds:snapshot.deckIds||[],savedBlend:snapshot.savedBlend||null};
    }
  }
  if(!Number.isInteger(nextIndex)||nextIndex<0||nextIndex>nextCards.length)throw Error("saveError");
  const choices=new Set(["like","dislike","unsure","skip"]);
  const nextAnswers={};
  for(const c of nextCards.slice(0,nextIndex)){
    if(!choices.has(snapshot.answers[c.id]))throw Error("saveError");
    nextAnswers[c.id]=snapshot.answers[c.id];
  }
  const stale=historicalDeck&&snapshot.swipes.length&&JSON.stringify(snapshot.deckIds)!==JSON.stringify(nextPortfolios.map(p=>[p.name,p.version]));
  const nextSwipes=stale?[]:snapshot.swipes;
  savedBlend=stale?null:snapshot.savedBlend||null;
  paperTracking=stale&&!pendingDeck?null:snapshot.paperTracking||null;
  if(nextSwipes.length>nextPortfolios.length||nextSwipes.some(v=>!["like","dislike","skip"].includes(v)))throw Error("saveError");
  mandate=nextMandate;cards=nextCards;answers=nextAnswers;index=nextIndex;
  responseLocales=Object.fromEntries(Object.keys(nextAnswers).filter(id=>["en","fr"].includes(snapshot.responseLocales?.[id])).map(id=>[id,snapshot.responseLocales[id]]));
  discoveryConfidence=currentQuestionnaire&&[1,2,3,4,5].includes(snapshot.discoveryConfidence)?snapshot.discoveryConfidence:null;
  portfolios=nextPortfolios;swipes=nextSwipes.slice();shortlist=portfolios.filter((_,i)=>swipes[i]==="like");confirmed.clear();scoreReport=null;
  if(fullMandate)window.MandateForm.restore(fullMandate);
  else{window.MandateForm.reset();const f=$("form");f.querySelector('[name="currency"]').value="USD";f.elements.capital.value=mandate.capital;f.elements.cash.value=mandate.capital;f.elements.loss_capacity_amount.value=mandate.capital*mandate.max_stress_loss;f.elements.stress_loss.value=mandate.max_stress_loss*100;}
  const savedPage=snapshot.activePage==="compare"?"matches":snapshot.activePage;
  const target=["home","mandate","discovery","universe","sources","explore","matches","strategy-catalogue","methodology"].includes(savedPage)?savedPage:"home";
  if(pendingDeck)return "home";
  if(fullMandate&&mandateReport?.personalized_eligible===true&&deckAversion===null&&["explore","matches"].includes(target))return "discovery";
  return fullMandate&&!canMatch(mandateReport)&&["explore","matches"].includes(target)?"mandate":target;
}
async function enterSavedStudio(target){
  setSaveSession(true);
  page(target);
  if(pendingDeck){errorKey="serverOutdated";$("error").textContent=diagnostic(errorKey);}
  if(target==="discovery")await showCard();
  if(target==="explore")showPortfolio();
  if(target==="universe")await window.UniverseView.load(api);
  if(target==="sources")await window.SourcesView.load(api);
}
