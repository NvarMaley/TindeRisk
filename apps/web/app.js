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
function renderJourneyRoute(){
  const route=$("journey-route");
  if(!route)return;
  const steps=[["mandate","navMandate"],["discovery","navDiscovery"],["explore","navExplore"],["matches","myMatches"]];
  route.hidden=!sessionUnlocked||!steps.some(([name])=>activePage===name);
  if(!route.hidden)route.innerHTML="<ol>"+steps.map(([name,key])=>`<li ${name===activePage?'aria-current="step"':""}>${esc(t(key))}</li>`).join("")+"</ol>";
}
document.addEventListener("riskmatch:language",renderJourneyRoute);
function page(name) {
  if(!sessionUnlocked && name!=="saves")name="saves";
  activePage = name;
  renderJourneyRoute();
  if(name!=="saves")lastSimulationPage=name;
  document.querySelectorAll(".page").forEach(x => x.hidden = x.id!==name);
  document.querySelectorAll("[data-page]").forEach(x => x.classList.toggle("active", x.dataset.page===name));
  if (name==="compare"||name==="matches") compare();
  if(name==="explore"&&!portfolios.length)$("portfolio").textContent=t("matchingLoading");
  if (name==="compare")window.BaselinesView?.mount(api,mandate?.currency);
  if (name==="compare")window.MeanVarianceView?.mount(api,fullMandate);
  if (name==="compare")window.BlackLittermanView?.mount(api,fullMandate);
  if (name==="compare")window.HierarchicalView?.mount(api,fullMandate);
  if (name==="compare")window.DownsideView?.mount(api,fullMandate);
  if (name==="compare")window.AdvancedView?.mount(api,fullMandate);
  if (name==="compare")window.LongOnlyView?.mount(api,fullMandate);
  if (name==="compare")window.AlternativeView?.mount(api,fullMandate);
  if (name==="compare")window.TreasuryView?.mount(api,fullMandate);
  if (name==="compare")window.FuturesView?.mount(api,fullMandate);
  if (name==="compare")window.WalkForwardView?.mount(api,fullMandate);
  if (name==="compare")window.StressMCView?.mount(api,fullMandate);
  if (name==="compare") window.GoalsView?.mount(fullMandate,api);
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
  if (activePage==="explore" || (["matches","compare"].includes(activePage)&&pendingDeck)) {
    await loadPortfolios();
    if(activePage==="matches"||activePage==="compare")compare();
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
  if(Array.isArray(payload.goals)&&!payload.goals.length)throw Error("chooseGoalsRequired");
  const report=await api("mandate/preview",payload);
  if(JSON.stringify(payload)!==JSON.stringify(window.MandateForm.payload()))return;
  pendingMandate=payload;pendingReport=report;renderMandateReport();
  $("mandate-report").scrollIntoView({behavior:"smooth",block:"start"});
});
const diagnostic=key=>{const [head,...tail]=key.split(":");return t(head)+(tail.length?": "+t(tail.join(":")):"");};
const money=(amount,currency)=>amount===null||amount===undefined?t("noValue"):new Intl.NumberFormat(window.RM.language==="fr"?"fr-CH":"en-US",{style:"currency",currency,maximumFractionDigits:0}).format(amount);
function renderMandateReport(){
  if(!pendingReport)return;
  const r=pendingReport, p=pendingMandate, area=$("mandate-report");
  const cash=v=>money(v,r.currency), result=x=>x?.annual_return===null||x?.annual_return===undefined?t(x?.status||"noValue"):pct(x.annual_return);
  const stats=[["netWorth",cash(r.net_worth)],["investableWealth",cash(r.investable_wealth)],["monthlySurplus",cash(r.monthly_surplus)],["nextWithdrawal",r.next_withdrawal||t("noValue")],["loss_capacity_amount",cash(r.loss_capacity_amount)],["nearTermCushion",cash(r.near_term_liquidity_cushion)],["effectiveStress",pct(r.effective_stress_limit)],["zeroReturnBalance",cash(r.zero_return_min_balance)],["combinedReturn",result(r.combined_required_return)]];
  let comparison="";
  if(mandateReport)comparison=`<h3>${esc(t("compareBefore"))}</h3><p>${esc(t("effectiveStress"))}: ${pct(mandateReport.effective_stress_limit)} → ${pct(r.effective_stress_limit)} · ${esc(t("goalCount"))}: ${mandateReport.goals.length} → ${r.goals.length} · ${esc(t("capital"))}: ${esc(money(fullMandate.capital,fullMandate.currency))} → ${esc(cash(p.capital))}</p><p>${esc(t("mandateGoals"))}: ${esc(mandateReport.goals.map(g=>`${t(g.objective_id)} (${g.due_date}, ${money(g.target_nominal_base,mandateReport.currency)})`).join(" · "))} → ${esc(r.goals.map(g=>`${t(g.objective_id)} (${g.due_date}, ${cash(g.target_nominal_base)})`).join(" · "))}</p>`;
  const messages=(items,cls)=>items.map(k=>`<p class="${cls}">• ${esc(diagnostic(k))}</p>`).join("");
  area.innerHTML=`<article><h2>${esc(t("mandateReport"))}</h2><p class="mandate-status ${r.conflicts.length?"mandate-conflict":""}">${esc(t(r.conflicts.length?"structuralConflicts":"structuralValid"))}</p><div class="mandate-summary">${stats.map(([k,v])=>`<div><span>${esc(t(k))}</span><b>${esc(v)}</b></div>`).join("")}</div>${comparison}<h3>${esc(t("mandateGoals"))}</h3>${r.goals.map(g=>`<div class="mandate-row mandate-goal"><b>${esc(t(g.objective_id))} · ${esc(g.due_date)}</b><p>${esc(t("goal_amount"))}: ${esc(cash(g.target_nominal_base))} · ${esc(t("requiredReturn"))}: ${esc(result(g.required_return))} · ${esc(t("zeroReturnGap"))}: ${esc(cash(g.zero_return_gap))}</p></div>`).join("")}${messages(r.conflicts,"mandate-conflict")}${messages(r.warnings,"muted")}<div class="matching-readiness ${canMatch(r)&&p.as_of>="2026-11-25"?"":"mandate-conflict"}"><strong>${esc(t(canMatch(r)&&p.as_of>="2026-11-25"?"matchingReady":"matchingLimited"))}</strong>${messages(r.personalized_reasons??r.demo_reasons,"muted")}${p.as_of<"2026-11-25"?`<p>${esc(t("matchingDateUnavailable"))}</p>`:""}</div><p class="muted">${esc(t("riskNotMeasured"))}</p><button id="confirm-mandate" class="primary" ${r.conflicts.length?"disabled":""}>${esc(t("confirmMandate"))}</button></article>`;
  area.hidden=false;
  $("confirm-mandate").onclick=handle(confirmMandate);
}
async function confirmMandate(){
  if(!sessionUnlocked||!pendingReport||pendingReport.status!=="structurally_valid"||$("mandate-report").hidden)throw Error("mandateRequired");
  if(JSON.stringify(pendingMandate)!==JSON.stringify(window.MandateForm.payload()))throw Error("mandateRequired");
  const keepDiscovery=Boolean(fullMandate&&fullMandate.currency===pendingMandate.currency&&cards.length);
  fullMandate=pendingMandate;mandateReport=pendingReport;pendingMandate=null;pendingReport=null;
  mandate={capital:fullMandate.capital,years:mandateReport.horizon_years,max_stress_loss:mandateReport.effective_stress_limit,currency:fullMandate.currency};
  historicalDeck=true;savedBlend=null;deckAversion=null;deckStyle="000";pendingDeck=null;deckRequest=null;portfolios=[]; swipes=[]; shortlist=[]; confirmed.clear(); if(!keepDiscovery)resetDiscovery();
  $("mandate-report").hidden=true;
  changed();page("discovery");await showCard();changed();
  if(canMatch(mandateReport)&&fullMandate.as_of>="2026-11-25"){
    // Load the common market inputs while the user answers Discovery.
    api("matching/prepare",{mandate:fullMandate}).catch(e=>{
      if(e.message==="serverOutdated"&&sessionUnlocked){errorKey=e.message;$("error").textContent=diagnostic(errorKey);}
    });
  }
}
function resetDiscovery(){cards=[];answers={};index=0;scoreReport=null;discoverySeed=null;discoveryVersion=null;discoveryConsent=false;responseLocales={};discoveryConfidence=null;discoveryCurrency=mandate?.currency||"USD";$("discovery-consent-check").checked=false;}
$("discovery-start").onclick=handle(async()=>{
  if(!sessionUnlocked||!mandate)throw Error("mandateRequired");
  if(!$("discovery-consent-check").checked)throw Error("discoveryConsentRequired");
  const seed=crypto.getRandomValues(new Uint32Array(1))[0], currency=mandate.currency;
  const session=await api("discovery/session",{seed,currency});
  discoverySeed=seed;discoveryCurrency=currency;discoveryVersion=session.version;discoveryConsent=true;cards=session.cards;answers={};responseLocales={};index=0;scoreReport=null;discoveryConfidence=null;
  changed();await showCard();
});
$("discovery-reset").onclick=handle(async()=>{if(!sessionUnlocked||!discoveryConsent)return;if(!window.confirm(t("withdrawDiscoveryConfirm")))return;resetDiscovery();changed();await showCard();});
async function discoveryScore(){return discoveryVersion?api("discovery/score",{seed:discoverySeed,currency:discoveryCurrency,answers,confidence:discoveryConfidence,locales:responseLocales}):api("score",answers);}
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
    const audit=r.dimensions?`<p>${esc(t("coverage"))}: ${r.answered}/${r.total_scored} · ${esc(t("unsure"))}: ${r.counts.unsure} · ${esc(t("skip"))}: ${r.counts.skip} · ${esc(t("inconsistencies"))}: ${r.inconsistencies.length}/${r.pairs_checked} · ${esc(t("framingDifferences"))}: ${r.framing_differences.length}/${r.framing_pairs_checked}</p><p class="muted">${esc(t("scoreMethod"))}</p>`:"<p>"+esc(t("inconsistencies"))+": "+r.inconsistencies.length+"</p>";
    const blocked=fullMandate&&(!canMatch(mandateReport)||fullMandate.as_of<"2026-11-25");
    const blocker=blocked?`<p class="mandate-conflict">${esc(t(!canMatch(mandateReport)?"demoUnavailable":"matchingDateUnavailable"))}</p>`:"";
    $("result").innerHTML='<article><h2>'+esc(r.score===null?t("scoreUnavailable"):r.score+" / 30")+'</h2><p>'+esc(t("scoreExplanation"))+' '+esc(t("coverage"))+': '+pct(r.coverage)+'. '+esc(t("sensitivity"))+': '+r.sensitivity.join("–")+'. '+esc(t("scoreLimit"))+'</p><details><summary>'+esc(t("profileDetails"))+'</summary>'+audit+dimensions+confidence+'</details><p class="muted">'+esc(t("discoverySeparate"))+'</p>'+blocker+'<button class="primary" id="next">'+esc(t(blocked?"reviseMandate":"exploreAllocations"))+'</button></article>';
    if(r.dimensions)$("discovery-confidence").onchange=handle(async event=>{discoveryConfidence=event.target.value?Number(event.target.value):null;scoreReport=null;changed();await showCard();});
    $("next").onclick=handle(async()=>{if(!mandate)throw Error("mandateRequired");if(blocked){page("mandate");return;}page("explore");await loadPortfolios();});
    return;
  }
  $("discovery-question").hidden=false;
  const c=window.RM.language==="fr"?card.fr:card;
  const hasStartingBalance=["lottery","framing","consistency"].includes(card.block_id)&&card.reference_wealth;
  const statementKey={
    trajectory:"discoveryPathStatement",style:"discoveryStyleStatement",
  }[card.block_id]||"discoveryStatement";
  const contextKey=card.block_id==="trajectory"?"discoveryPathContext":
    card.dimension==="ambiguity"?"discoveryChanceContext":null;
  const context=hasStartingBalance?
    t("discoveryWealthContext").replace("{wealth}",()=>`${card.reference_wealth} ${card.currency}`):
    contextKey?t(contextKey):"";
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
    <article class="card discovery-swipe-card" aria-labelledby="discovery-statement">
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
async function fetchDeck(raw){
  try{return await (historicalDeck ? api("matching/cards",{mandate:raw,aversion:deckAversion,style:deckStyle}) : api("candidates",raw));}
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
  const fr=window.RM.language==="fr";
  const descriptions={
    minimum_variance:["Seeks the lowest estimated portfolio volatility.","Recherche la volatilité estimée la plus faible."],
    risk_parity:["Balances the contribution of each asset to total risk.","Équilibre la contribution de chaque actif au risque global."],
    black_litterman:["Combines market equilibrium with investment views to construct an allocation.","Combine l’équilibre du marché et des anticipations pour construire une allocation."],
    mean_reversion:["Uses departures from historical averages to form contrarian positions.","Exploite les écarts aux moyennes historiques pour prendre des positions contrariennes."],
    cross_sectional_momentum:["Favors assets with stronger prior relative performance.","Favorise les actifs ayant les meilleures performances relatives passées."],
    time_series_momentum:["Adjusts exposure according to historical trends.","Adapte les expositions aux tendances historiques."],
    maximum_sharpe:["Seeks the best estimated excess return per unit of volatility.","Recherche le meilleur excès de rendement estimé par unité de volatilité."],
    mean_variance_utility:["Balances expected return against portfolio variance.","Arbitre entre rendement attendu et variance du portefeuille."],
    minimum_cvar:["Aims to reduce the average loss in adverse tail scenarios.","Vise à réduire la perte moyenne dans les scénarios extrêmes."],
    volatility_target:["Adjusts exposure toward a target volatility.","Ajuste l’exposition en fonction d’une volatilité cible."],
    equal_weight:["Allocates equal capital to eligible holdings.","Répartit le capital de manière égale entre les actifs admissibles."],
    all_weather:["Diversifies across asset exposures under different economic conditions.","Diversifie les expositions sous différentes conditions économiques."],
    robust_utility:["Accounts for uncertainty in model estimates.","Prend en compte l’incertitude des estimations du modèle."],
    core_satellite:["Combines a reference core allocation with active strategies.","Combine une allocation centrale de référence et des stratégies actives."]
  };
  return window.Journey?.method(name)||descriptions[name]?.[fr?1:0]||"";
}
function wealthChart(nav){
  if(!Array.isArray(nav)||nav.length<2||nav.some(x=>!Number.isFinite(x)))return "";
  const fr=window.RM.language==="fr",lo=Math.min(...nav),hi=Math.max(...nav),span=Math.max(hi-lo,.001);
  const xy=nav.map((v,i)=>[24+552*i/(nav.length-1),152-128*(v-lo)/span]);
  const path=xy.map(([x,y],i)=>(i?"L":"M")+x.toFixed(2)+" "+y.toFixed(2)).join(" ");
  const title=fr?"Évolution historique, capital de départ = 100":"Historical performance, starting value = 100";
  return `<figure class="wealth-chart"><figcaption>${esc(title)}</figcaption><svg viewBox="0 0 600 180" role="img" aria-label="${esc(title)}"><path d="M24 152H576 M24 88H576 M24 24H576" stroke="currentColor" opacity=".18" fill="none"/><path d="${path}" fill="none" stroke="#95e8df" stroke-width="3" stroke-linejoin="round"/><circle cx="${xy.at(-1)[0]}" cy="${xy.at(-1)[1]}" r="4" fill="#ff97c1"/></svg><div><span>100</span><strong>${(100*nav.at(-1)).toFixed(1)}</strong></div></figure>`;
}
function detail(p){
  const fr=window.RM.language==="fr";
  const metrics=[["cagr",p.metrics.cagr],["vol",p.metrics.vol],["drawdown",p.metrics.drawdown],["stress",p.stress_loss]];
  const positions=Object.entries(p.weights).filter(([,v])=>Math.abs(v)>1e-7).sort((a,b)=>b[1]-a[1]);
  const holdingRows=rows=>rows.map(([k,v])=>`<div><p><span>${esc(t(k))}</span><strong>${pct(v)}</strong></p><div class="bar"><i style="width:${Math.max(0,Math.min(100,100*v))}%"></i></div></div>`).join("");
  return `<div class="strategy-title"><h2>${esc(strategyName(p.name))}</h2><span class="simulation-tag">${p.personalized?(fr?"Construit pour ton mandat":"Built for your mandate"):(fr?"Simulation historique":"Historical simulation")}</span></div>
  ${strategyDescription(p.name)?`<p>${esc(strategyDescription(p.name))}</p>`:""}
  <p>${fr?"Dans le scénario de perte le plus sévère testé, ton capital baisse de":"In the worst loss scenario tested, your capital falls by"} <strong>${money(p.stress_usd,"USD")}</strong> (${pct(p.stress_loss)}).</p>
  ${window.Journey?.timeline(p.metrics.nav)||wealthChart(p.metrics.nav)}
  ${window.Journey?.composition(p)||""}
  ${window.Journey?.goals(p.goal_projection)||""}
  <details><summary>${fr?"Comment lire les chiffres ?":"How do I read the numbers?"}</summary><dl>${metrics.map(([key,value],i)=>`<dt>${esc(t(key))} · ${pct(value)}</dt><dd>${(fr?["Croissance annuelle moyenne composée sur la période testée.","Amplitude habituelle des fluctuations, ramenée à une année.","Plus grand recul entre un sommet et le point bas suivant.","Perte estimée dans le choc le plus défavorable testé."]:["Compound annual growth over the test period.","Typical fluctuations expressed on an annual scale.","Largest historical fall from a previous high.","Estimated loss under the worst shock tested."])[i]}</dd>`).join("")}</dl><p>${fr?"Perte moyenne pendant les 5 % de mois les plus défavorables":"Average loss across the worst 5% of months"} · ${pct(p.metrics.es95_monthly)}</p></details>
  <details><summary>${fr?"Voir les placements":"View holdings"} (${positions.length})</summary><div class="holdings-list">${holdingRows(positions)}</div></details>
  ${p.income_preference_unmeasured?`<p>${fr?"Les versements de revenu ne sont pas mesurés.":"Income distributions are unmeasured."}</p>`:""}
  ${p.equivalent_methods?.length?`<details><summary>${fr?"Autres méthodes proches":"Similar methods"}</summary>${p.equivalent_methods.map(n=>esc(strategyName(n))).join(", ")}</details>`:""}
  ${p.personalized?`<p class="muted">${fr?"Univers admissible":"Eligible universe"} : ${p.eligible_assets}/${p.universe_size} · ${fr?"Rendement estimé":"Estimated return"} : ${pct(p.expected_return)} · ${fr?"Volatilité estimée":"Estimated volatility"} : ${pct(p.estimated_volatility)}</p>
  ${p.goal_projection?`<details><summary>${fr?"Projection de tes objectifs":"Your goal projections"}</summary><p class="muted">${p.goal_projection_paths} ${fr?"trajectoires conditionnelles":"conditional paths"}</p>${p.goal_projection.map(g=>`<p>${esc(t(g.objective_id))} · ${fr?"Probabilité simulée":"Simulated probability"}: ${g.probability===null?"—":pct(g.probability)} · ${fr?"Déficit attendu":"Expected shortfall"}: ${money(g.expected_deficit,"USD")}</p>`).join("")}</details>`:""}
  <p class="muted">${fr?"Données de construction arrêtées au":"Construction data cutoff"} ${esc(p.model_as_of)}. ${fr?"La performance historique est calculée sur des pondérations estimées avant la période de test.":"Historical performance uses weights estimated before the test period."}</p>`:""}
  <details class="strategy-method"><summary>${fr?"Période et hypothèses":"Period and assumptions"}</summary><p class="muted">${esc(t(p.period))} · ${esc(t(p.costs))}</p></details>`;
}
function showPortfolio(){
  const p=portfolios[swipes.length],fr=window.RM.language==="fr";
  $("reject").textContent=fr?"✕ Pas de match":"✕ No match";$("like").textContent="♥ Match";
  for(const id of ["like","reject","skip"])$(id).disabled=!p;
  $("undo").disabled=!swipes.length;
  if(historicalDeck&&p&&swipes.length>=12&&!showFullDeck){
    for(const id of ["like","reject","skip"])$(id).disabled=true;
    $("portfolio").replaceChildren();
    const more=document.createElement("button");
    more.textContent=fr?"Voir les autres stratégies compatibles":"View remaining compatible strategies";
    more.onclick=()=>{showFullDeck=true;showPortfolio();};$("portfolio").append(more);return;
  }
  const fit=p?.worst_scenario?`<p>${fr?"Scénario le plus défavorable":"Worst scenario"} · ${esc(p.worst_scenario.replaceAll("_"," "))}. ${fr?"Perte simulée":"Simulated loss"} ${pct(p.stress_loss)} / ${pct(mandate.max_stress_loss)} ${fr?"autorisés":"limit"}.</p>`:"";
  $("portfolio").innerHTML=p?"<article>"+detail(p)+fit+`<p class="muted">${swipes.length+1} / ${portfolios.length} · ${shortlist.length} ${fr?"retenues":"retained"}</p></article>`:portfolios.length?"<article>"+esc(t("end"))+": "+shortlist.length+"</article>":"<article>"+esc(t("matchingEmpty"))+"</article>";
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
function swipe(choice){if($("strategy-verdict")?.open||!sessionUnlocked||(historicalDeck&&swipes.length>=12&&!showFullDeck))return;const p=portfolios[swipes.length];if(!p)return;swipes.push(choice);if(choice==="like"){shortlist.push(p);savedBlend=null;}showPortfolio();changed();if(choice==="like"||choice==="dislike")strategyVerdict(choice,p);}
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
  if(Math.abs(event.clientY-y)>Math.abs(dx)+15){article.style.transform="";strategyDrag=null;return;}
  if(Math.abs(dx)>12){deckSurface.setPointerCapture(event.pointerId);article.style.transform=`translateX(${dx*.35}px) rotate(${Math.max(-6,Math.min(6,dx/22))}deg)`;}
});
function finishStrategyDrag(event){
  if(strategyDrag?.id!==event.pointerId)return;
  const {article,x,y}=strategyDrag;strategyDrag=null;article.style.transform="";
  const dx=event.clientX-x;
  if(event.type==="pointerup"&&Math.abs(dx)>65&&Math.abs(dx)>1.4*Math.abs(event.clientY-y)&&article.isConnected)swipe(dx>0?"like":"dislike");
}
for(const event of ["pointerup","pointercancel","lostpointercapture"])deckSurface.addEventListener(event,finishStrategyDrag);
$("like").onclick=()=>swipe("like");$("reject").onclick=()=>swipe("dislike");$("skip").onclick=()=>swipe("skip");
$("undo").onclick=()=>{if(!sessionUnlocked||pendingDeck)return;if(swipes.pop()==="like"){const undone=shortlist.pop();confirmed.delete(undone.name);}showPortfolio();changed();};
function compare(){
  const area=$(activePage==="matches"?"match-allocation":"shortlist");area.replaceChildren();
  const fr=window.RM.language==="fr";
  const research=document.createElement("article");
  const researchButton=document.createElement("button");researchButton.textContent=fr?"Comparaison des stratégies":"Compare research strategies";
  const researchOutput=document.createElement("div");
  researchButton.onclick=handle(async()=>{
    const r=await api("matching/research",{});
    if(r.status!=="experimental"){researchOutput.textContent=r.reason;return;}
    researchOutput.innerHTML=(window.Journey?.map(r.strategies.map(s=>({title:strategyName(s.strategy),metrics:{vol:s.holdout_volatility,cagr:s.holdout_cagr}})))||"")+`<p>${fr?"Comparaison historique exploratoire, sans validation indépendante":"Exploratory historical comparison, without independent validation"} · ${esc(r.reference)} · ${r.holdout_months} ${fr?"mois":"months"}</p><table><thead><tr><th>${fr?"Stratégie":"Strategy"}</th><th>CAGR</th><th>${fr?"Volatilité":"Volatility"}</th><th>Drawdown</th><th>${fr?"Excès annualisé":"Annualized excess"}</th></tr></thead><tbody>${r.strategies.map(s=>`<tr><td>${esc(s.strategy)}</td><td>${pct(s.holdout_cagr)}</td><td>${pct(s.holdout_volatility)}</td><td>${pct(s.holdout_drawdown)}</td><td>${pct(s.holdout_excess_annual)}</td></tr>`).join("")}</tbody></table>`;
  });research.append(researchButton,researchOutput);if(activePage==="compare")area.append(research);
  const variants=document.createElement("button");
  variants.textContent=fr?"Comparer les variantes du modèle":"Compare model variants";
  variants.onclick=handle(async()=>{
    const r=await api("matching/improvements",{});
    researchOutput.innerHTML=`<p>${fr?"Variation du rendement moyen annualisé face au modèle de référence sur la période de test":"Change in annualized mean return versus the reference model on the test period"} · ${r.holdout_months} ${fr?"mois":"months"}</p>`+
      Object.entries(r.variants).map(([name,v])=>`<p>${esc(name)} · ${pct(v.paired_change_vs_model)}</p>`).join("");
  });research.append(variants);
  if(!shortlist.length){
    const empty=document.createElement("article");empty.innerHTML=`<h2>${esc(t("empty"))}</h2><p>${fr?"Sélectionne les stratégies qui te correspondent pour construire ton allocation.":"Choose the strategies that suit you to build your allocation."}</p>`;
    if(activePage==="matches"){
      const button=document.createElement("button");button.className="primary";button.textContent=t("navExplore");
      button.onclick=handle(async()=>{if(!mandate){page("mandate");return;}if(!cards.length||index<cards.length){page("discovery");await showCard();return;}page("explore");await loadPortfolios();});empty.append(button);
    }
    area.append(empty);return;
  }
  if(activePage==="matches" && window.Journey && shortlist.length>1){
    const landscape=document.createElement("div");
    landscape.innerHTML=window.Journey.map(shortlist.map(p=>({...p,title:strategyName(p.name)})));area.append(landscape);
  }
  const allocation=document.createElement("article");
  const signature=JSON.stringify([fullMandate||mandate,shortlist[0].version,shortlist.map(p=>p.name)]);
  const stored=savedBlend?.signature===signature?savedBlend:null;
  allocation.innerHTML=`<h2>${fr?"Mes Matches":"My Matches"}</h2><p>${historicalDeck?(fr?"Simulation sur rendements historiques en USD.":"USD historical return simulation."):(fr?"Simulation fictive.":"Synthetic simulation.")}</p>`;
  if(stored?.paperConfirmed){
    const status=document.createElement("p");status.textContent=fr?"Allocation confirmée en simulation":"Confirmed paper allocation";allocation.append(status);
  }
  const inputs=shortlist.map(p=>{
    const label=document.createElement("label");label.className="allocation-row";label.textContent=strategyName(p.name)+" (%) ";
    const input=document.createElement("input");input.type="number";input.min="0";input.max="100";input.step="any";input.value=100/shortlist.length;
    if(stored?.budgets?.[p.name]!=null)input.value=100*stored.budgets[p.name];
    label.append(input);allocation.append(label);return input;
  });
  const total=document.createElement("p");total.className="allocation-total";
  const updateTotal=()=>{const sum=inputs.reduce((acc,input)=>acc+Number(input.value),0);total.textContent=(fr?"Total investi":"Total allocated")+" : "+sum.toFixed(2)+" %";total.classList?.toggle("mandate-conflict",Math.abs(sum-100)>1e-6);};
  updateTotal();allocation.append(total);
  const output=document.createElement("div");
  let revision=0;
  for(const optimized of (shortlist[0].personalized?[false,true,"goal"]:[false,true])){
    const button=document.createElement("button");button.textContent=optimized==="goal"?(fr?"Comparer selon mon objectif prioritaire":"Compare for my priority goal"):optimized?(fr?"Optimiser le risque":"Optimize risk"):(fr?"Calculer mon allocation":"Evaluate allocation");
    button.onclick=handle(async()=>{
      const requestRevision=++revision;
      output.replaceChildren();
      if(!optimized&&inputs.some(input=>String(input.value).trim()===""||!input.validity.valid))throw Error(fr?"Allocation invalide":"Invalid allocation");
      if(!optimized&&Math.abs(inputs.reduce((s,i)=>s+Number(i.value),0)-100)>1e-6)throw Error(fr?"Les allocations doivent totaliser 100 %.":"Allocations must total 100%.");
      output.textContent=t("allocationLoading");
      let result;
      try{result=await api("match-allocations/"+(optimized==="goal"?"goal":optimized?"optimize":"evaluate"),{mandate:fullMandate||mandate,names:shortlist.map(p=>p.name),budgets:inputs.map(i=>Number(i.value)/100),version:shortlist[0].version});}
      catch(e){if(allocation.isConnected&&revision===requestRevision)output.textContent=diagnostic(e.message);throw e;}
      if(!allocation.isConnected||revision!==requestRevision)return;
      if(optimized)inputs.forEach((input,i)=>{input.value=result.budgets[shortlist[i].name]*100;});
      updateTotal();
      savedBlend={signature,budgets:result.budgets};changed();
      output.innerHTML=detail({...result,name:fr?"Portefeuille combiné":"Combined portfolio",period:result.period||"36 synthetic out-of-calibration months"})+`<h3>${fr?"Contributions au risque":"Risk contributions"}</h3>`+Object.entries(result.risk_contributions).map(([name,value])=>`<p>${esc(t(name))}: ${pct(value)}</p>`).join("");
      if(result.comparison){
        const labels=fr?["Mon choix","Variance minimale","Objectif prioritaire"]:["My choice","Minimum variance","Priority goal"];
        output.insertAdjacentHTML("beforeend",`<h3>${fr?"Comparaison des répartitions":"Allocation comparison"}</h3><p>${result.tested_budgets} ${fr?"répartitions testées":"allocations tested"}</p><table><thead><tr><th></th>${labels.map(label=>`<th>${label}</th>`).join("")}</tr></thead><tbody>${shortlist.map(p=>`<tr><th>${esc(strategyName(p.name))}</th>${Object.values(result.comparison).map(row=>`<td>${pct(row.budgets[p.name])}</td>`).join("")}</tr>`).join("")}<tr><th>Stress</th>${Object.values(result.comparison).map(row=>`<td>${pct(row.stress_loss)}</td>`).join("")}</tr>${result.comparison.goal.goals.map((g,i)=>`<tr><th>${esc(t(g.objective_id))} · ${fr?"Probabilité / déficit":"Probability / deficit"}</th>${Object.values(result.comparison).map(row=>`<td>${row.goals[i].probability==null?"—":pct(row.goals[i].probability)} / ${money(row.goals[i].expected_deficit,"USD")}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      }
      if(result.reference_metrics)output.insertAdjacentHTML("beforeend",`<p>${result.benchmark?esc(strategyName(result.benchmark)):"60/40"} · CAGR ${pct(result.reference_metrics.cagr)} · ${esc(t("vol"))} ${pct(result.reference_metrics.vol)}</p>`);
      if(result.overlap?.length)output.insertAdjacentHTML("beforeend",`<p>${fr?"Positions communes":"Shared holdings"} · ${result.overlap.map(esc).join(", ")}</p>`);
      if(Number.isFinite(result.additional_transfer_fee_fraction))output.insertAdjacentHTML("beforeend",`<p>${fr?"Somme des frais de transfert supplémentaires rapportés aux valeurs mensuelles":"Sum of extra transfer fees relative to monthly NAV"} · ${pct(result.additional_transfer_fee_fraction)} · ${fr?"Turnover annualisé":"Annualized turnover"} ${pct(result.additional_transfer_turnover)}</p>`);
      if(result.correlations&&shortlist.length>1){
        const pairs=shortlist.flatMap((p,i)=>shortlist.slice(i+1).map((q,j)=>
          `<p>${esc(p.name)} / ${esc(q.name)} · ${result.correlations[i][i+j+1].toFixed(2)}</p>`));
        output.insertAdjacentHTML("beforeend",`<details><summary>${fr?"Corrélations":"Correlations"}</summary>${pairs.join("")}</details>`);
      }
      const confirm=document.createElement("button");
      confirm.textContent=fr?"Confirmer cette simulation":"Confirm paper allocation";
      confirm.onclick=handle(async()=>{
        await api("match-allocations/evaluate",{mandate:fullMandate||mandate,names:Object.keys(result.budgets),budgets:Object.values(result.budgets),version:result.version});
        if(!confirm.isConnected||requestRevision!==revision)return;
        savedBlend={signature,budgets:result.budgets,paperConfirmed:true};changed();
        confirm.disabled=true;confirm.textContent=fr?"Simulation confirmée":"Paper allocation confirmed";
      });output.append(confirm);
    });allocation.append(button);
  }
  inputs.forEach(input=>input.oninput=()=>{revision++;savedBlend=null;updateTotal();changed();output.replaceChildren();});
  allocation.append(output);if(activePage==="matches")area.append(allocation);
  if(activePage==="matches"&&historicalDeck&&fullMandate){
    const goals=document.createElement("article"),goalButton=document.createElement("button"),goalOutput=document.createElement("div");
    goalButton.textContent=fr?"Évaluer mes objectifs financiers":"Evaluate my financial objectives";
    goalButton.onclick=handle(async()=>{
      if(!savedBlend?.paperConfirmed||savedBlend.signature!==signature)throw Error(fr?"Confirmez d’abord votre allocation.":"Confirm your paper allocation first.");
      const rev=revision;
      goalOutput.textContent=fr?"Simulation des objectifs en cours…":"Simulating your goals…";
      let r;
      try{r=await api("matching/goals",{mandate:fullMandate,names:Object.keys(savedBlend.budgets),budgets:Object.values(savedBlend.budgets),version:shortlist[0].version});}
      catch(e){if(goals.isConnected&&rev===revision)goalOutput.textContent=diagnostic(e.message);throw e;}
      if(!goals.isConnected||rev!==revision)return;
      const moneyValue=v=>v==null?"—":Number(v).toFixed(0);
      const probability=v=>v==null?"—":pct(v);
      goalOutput.innerHTML=(window.Journey?.goals(r.matched.goals)||"")+(window.Journey?r.matched.goals.map(window.Journey.range).join(""):"")+`<p>${fr?"Simulation conditionnelle · 1 000 trajectoires":"Conditional simulation · 1,000 paths"}</p><table><thead><tr><th>${fr?"Objectif":"Objective"}</th><th>${fr?"Probabilité":"Probability"}</th><th>${fr?"Déficit attendu USD":"Expected deficit USD"}</th><th>${fr?"Prob. référence":"Reference probability"}</th></tr></thead><tbody>${r.matched.goals.map((g,i)=>`<tr><td>${esc(t(g.objective_id))} · ${esc(g.due_date)}</td><td>${probability(g.probability)}</td><td>${moneyValue(g.expected_deficit)}</td><td>${probability(r.reference.goals[i]?.probability)}</td></tr>`).join("")}</tbody></table><p>${esc(strategyName(r.benchmark||"60/40"))} · ${r.training_months} ${fr?"mois historiques":"historical months"}</p><p class="muted">${esc(r.warning)}</p>`;
    });goals.append(goalButton,goalOutput);area.append(goals);
  }
  if(activePage==="matches"&&historicalDeck){
    const dynamic=document.createElement("article");
    dynamic.innerHTML=`<h2>${fr?"Gestion dynamique":"Dynamic management"}</h2><p>${fr?"Comparer 10 politiques sur les mêmes rendements historiques du portefeuille sélectionné.":"Compare 10 policies on the same historical returns of the selected portfolio."}</p>`;
    const run=document.createElement("button"), result=document.createElement("div");
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
      result.innerHTML=`<p>${fr?"Simulation historique USD · frais supplémentaires par transfert.":"Historical USD simulation · additional transfer fees."} · ${cost} bp</p><table><thead><tr><th>${fr?"Politique":"Policy"}</th><th>CAGR</th><th>${fr?"Volatilité":"Volatility"}</th><th>Drawdown</th><th>ES 95%</th><th>Turnover</th><th>${fr?"Frais USD":"Fees USD"}</th></tr></thead><tbody>${Object.entries(r.policies).map(([name,v])=>`<tr><td>${esc(name.replaceAll("_"," "))}</td>${v.status==="computed"?`<td>${pct(v.cagr)}</td><td>${pct(v.volatility)}</td><td>${pct(v.drawdown)}</td><td>${pct(v.expected_shortfall)}</td><td>${pct(v.annual_turnover)}</td><td>${v.fees.toFixed(2)}</td>`:`<td colspan="6">${esc(v.status)}</td>`}</tr>`).join("")}</tbody></table>`;
      const select=document.createElement("select"),ledger=document.createElement("div");
      for(const name of Object.keys(r.policies)){const option=document.createElement("option");option.value=name;option.textContent=name.replaceAll("_"," ");select.append(option);}
      const refresh=()=>{const v=r.policies[select.value];if(!v)return;ledger.innerHTML=`<table><thead><tr><th>Date</th><th>${fr?"Capital USD":"Capital USD"}</th><th>${fr?"Investi":"Invested"}</th><th>Stress</th><th>${fr?"Vol. estimée":"Est. vol."}</th><th>${fr?"Frais":"Fees"}</th></tr></thead><tbody>${v.ledger.map(row=>`<tr><td>${esc(row.date)}</td><td>${row.ending.toFixed(2)}</td><td>${pct(row.fraction)}</td><td>${pct(row.stress_estimate)}</td><td>${pct(row.annual_volatility)}</td><td>${row.fee.toFixed(2)}</td></tr>`).join("")}</tbody></table>`;};
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
    dynamic.append(costLabel,frequency,run,result);area.append(dynamic);
  }
  if(activePage==="matches"){
    const details=document.createElement("details");details.className="matched-strategies";
    const summary=document.createElement("summary");summary.textContent=fr?"Détail de mes stratégies sélectionnées":"Details of my selected strategies";details.append(summary);
    shortlist.forEach(p=>{const article=document.createElement("article");article.innerHTML=detail(p);details.append(article);});
    area.append(details);return;
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
  if(activePage==="compare"||activePage==="matches")compare();
  if(activePage==="compare")window.BaselinesView?.render();
  if(activePage==="compare")window.MeanVarianceView?.render();
  if(activePage==="compare")window.BlackLittermanView?.render();
  if(activePage==="compare")window.HierarchicalView?.render();
  if(activePage==="compare")window.DownsideView?.render();
  if(activePage==="compare")window.AdvancedView?.render();
  if(activePage==="compare")window.LongOnlyView?.render();
  if(activePage==="compare")window.AlternativeView?.render();
  if(activePage==="compare")window.TreasuryView?.render();
  if(activePage==="compare")window.FuturesView?.render();
  if(activePage==="compare")window.WalkForwardView?.render();
  if(activePage==="compare")window.StressMCView?.render();
  if(activePage==="universe")window.UniverseView.render();
  if(activePage==="sources")window.SourcesView.render();
  if(activePage==="mandate"&&!$("mandate-report").hidden)renderMandateReport();
  if(activePage==="compare")window.GoalsView?.render();
});

// Serialize only the synthetic simulation, not passwords or computed market data.
function simulationSnapshot() {
  return {version:1,mandate,fullMandate,answers,index,swipes:pendingDeck?.swipes??swipes,historicalDeck,savedBlend:pendingDeck?.savedBlend??savedBlend,deckAversion,deckStyle,deckIds:pendingDeck?.deckIds??portfolios.map(p=>[p.name,p.version]),activePage:lastSimulationPage,discoverySeed,discoveryVersion,discoveryCurrency,discoveryConsent,responseLocales,discoveryConfidence};
}
function clearSimulation(){
  historicalDeck=true;savedBlend=null;deckAversion=null;showFullDeck=false;pendingDeck=null;deckRequest=null;
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
  window.MandateForm.reset();$("card").replaceChildren();$("result").replaceChildren();$("portfolio").replaceChildren();$("shortlist").replaceChildren();
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
  const nextIndex=Number(snapshot.index);
  let nextCards=[];
  if(snapshot.discoveryVersion){
    const restored=await api("discovery/session",{seed:snapshot.discoverySeed,currency:snapshot.discoveryCurrency});
    if(restored.version!==snapshot.discoveryVersion||restored.currency!==nextMandate.currency)throw Error("saveError");
    nextCards=restored.cards;discoverySeed=restored.seed;discoveryVersion=restored.version;discoveryCurrency=restored.currency;discoveryConsent=true;
  }else if(nextIndex>0){nextCards=await api("cards");discoveryConsent=true;}
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
  if(nextSwipes.length>nextPortfolios.length||nextSwipes.some(v=>!["like","dislike","skip"].includes(v)))throw Error("saveError");
  mandate=nextMandate;cards=nextCards;answers=nextAnswers;index=nextIndex;
  responseLocales=Object.fromEntries(Object.keys(nextAnswers).filter(id=>["en","fr"].includes(snapshot.responseLocales?.[id])).map(id=>[id,snapshot.responseLocales[id]]));
  discoveryConfidence=[1,2,3,4,5].includes(snapshot.discoveryConfidence)?snapshot.discoveryConfidence:null;
  portfolios=nextPortfolios;swipes=nextSwipes.slice();shortlist=portfolios.filter((_,i)=>swipes[i]==="like");confirmed.clear();scoreReport=null;
  if(fullMandate)window.MandateForm.restore(fullMandate);
  else{window.MandateForm.reset();const f=$("form");f.querySelector('[name="currency"]').value="USD";f.elements.capital.value=mandate.capital;f.elements.cash.value=mandate.capital;f.elements.loss_capacity_amount.value=mandate.capital*mandate.max_stress_loss;f.elements.stress_loss.value=mandate.max_stress_loss*100;f.elements.loss_budget.value=mandate.max_stress_loss*100;}
  const target=["home","mandate","discovery","universe","sources","explore","compare","matches"].includes(snapshot.activePage)?snapshot.activePage:"home";
  if(pendingDeck)return "home";
  if(fullMandate&&mandateReport?.personalized_eligible===true&&deckAversion===null&&["explore","matches"].includes(target))return "discovery";
  return fullMandate&&!canMatch(mandateReport)&&["explore","compare","matches"].includes(target)?"mandate":target;
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
