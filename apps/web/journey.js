// Client charts use the same portfolio objects as the detailed research tables.
(() => {
  const text=(en,fr)=>window.RM.language==="fr"?fr:en;
  const escape=s=>String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const number=(n,digits=1)=>n.toLocaleString(window.RM.language,{maximumFractionDigits:digits});
  const percent=n=>number(100*n)+" %";
  const palette=["#98eee0","#ff96b0","#ffce82","#a3abff","#84c8fa","#dab7f8","#e9e6d7"];
  const classes={equity:["Shares","Actions"],treasury:["US government bonds","Dette publique américaine"],cash:["Cash","Liquidités"],reit:["Listed real estate","Immobilier coté"],commodity_etp:["Commodities","Matières premières"]};
  const label=k=>classes[k]?text(...classes[k]):k;
  function composition(p){
    const entries=Object.entries(p.exposures||p.weights||{}).filter(([,v])=>Number.isFinite(v)&&v>0).sort((a,b)=>b[1]-a[1]);
    if(!entries.length)return "";
    const parts=entries.slice(0,6);
    if(entries.length>6)parts.push([text("Other holdings","Autres positions"),entries.slice(6).reduce((sum,x)=>sum+x[1],0)]);
    let angle=0;
    const slices=parts.map(([k,v],i)=>{
      const start=angle;angle+=v*360;
      return palette[i]+" "+start+"deg "+angle+"deg";
    });
    const items=parts.map(([k,v],i)=>`<button type="button" aria-pressed="${i===0}" data-slice="${escape(label(k))}" data-value="${escape(percent(v))}"><i style="background:${palette[i]}"></i>${escape(label(k))}<b>${percent(v)}</b></button>`).join("");
    return `<figure class="j-composition"><figcaption>${text("Where does your money go?","Où va ton argent ?")}</figcaption><div class="j-ring" style="background:conic-gradient(${slices.join(",")})"><output><strong>${percent(parts[0][1])}</strong><small>${escape(label(parts[0][0]))}</small></output></div><div class="j-legend">${items}</div></figure>`;
  }
  function timeline(nav){
    if(!Array.isArray(nav)||nav.length<2||!nav.every(Number.isFinite)||nav.some(x=>x<=0))return "";
    return `<figure class="j-timeline" data-nav="${nav.join(",")}"><figcaption>${text("Follow 100 USD through time","Suis 100 USD dans le temps")}</figcaption><div class="j-switch"><button type="button" data-trace="wealth" aria-pressed="true">Capital</button><button type="button" data-trace="dip" aria-pressed="false">${text("Fall from peak","Recul depuis le sommet")}</button></div><div class="j-plot"></div><label><span>${text("Explore by month","Explore mois par mois")}</span><input type="range" min="0" max="${nav.length-1}" value="${nav.length-1}"></label><output></output></figure>`;
  }
  function draw(figure){
    const nav=figure.dataset.nav.split(",").map(Number),dip=figure.dataset.trace==="dip";
    let peak=nav[0];
    const values=nav.map(v=>{peak=Math.max(v,peak);return dip?100*(v/peak-1):100*v/nav[0];});
    const low=Math.min(...values),high=Math.max(...values),span=high-low||1;
    const y=v=>96-76*(v-low)/span,x=i=>9+282*i/(values.length-1);
    const idx=Number(figure.querySelector("input").value);
    const path=values.map((v,i)=>(i?"L":"M")+x(i).toFixed(2)+" "+y(v).toFixed(2)).join(" ");
    figure.querySelector(".j-plot").innerHTML=`<svg viewBox="0 0 300 110" aria-hidden="true"><path d="M9 20H291 M9 58H291 M9 96H291" stroke="currentColor" opacity=".14"/><path d="${path} L291 99 H9Z" fill="${dip?"#fa85a3":"#72e2d2"}" opacity=".15"/><path d="${path}" fill="none" stroke="${dip?"#fa85a3":"#72e2d2"}" stroke-width="2"/><path d="M${x(idx)} 12V99" stroke="currentColor" stroke-dasharray="2 3"/><circle cx="${x(idx)}" cy="${y(values[idx])}" r="3.8" fill="#ffeece"/></svg>`;
    figure.querySelector("output").textContent=text("Month ","Mois ")+idx+" · "+number(values[idx])+(dip?" %":" USD");
  }
  function goals(rows){
    return (rows||[]).filter(g=>Number.isFinite(g.probability)).map(g=>{
      const n=Math.round(100*g.probability);
      return `<figure class="j-goal"><figcaption>${escape(window.RM.t(g.objective_id))}</figcaption><div class="j-dots" aria-hidden="true">${Array.from({length:100},(_,i)=>`<i class="${i<n?"hit":""}"></i>`).join("")}</div><div><strong>${n} / 100</strong><p>${text("simulated paths reach the target, rounded to 100 paths.","trajectoires simulées atteignent la cible, ramenées à 100 et arrondies.")}</p></div></figure>`;
    }).join("");
  }
  function map(rows){
    const points=rows.filter(p=>Number.isFinite(p.metrics?.vol)&&Number.isFinite(p.metrics?.cagr));
    if(points.length<2)return "";
    const vs=points.map(p=>p.metrics.vol),rs=points.map(p=>p.metrics.cagr);
    const maxV=Math.max(...vs,.001),lo=Math.min(0,...rs),hi=Math.max(0,...rs);
    const options=points.map((p,i)=>`<option value="${i}">${escape(p.title||p.name)}</option>`).join("");
    const circles=points.map((p,i)=>`<circle data-dot="${i}" cx="${15+265*p.metrics.vol/maxV}" cy="${97-79*(p.metrics.cagr-lo)/(hi-lo||1)}" r="4" fill="${palette[i%palette.length]}"><title>${escape(p.title||p.name)}</title></circle>`).join("");
    const labels=points.map(p=>percent(p.metrics.vol)+" · "+percent(p.metrics.cagr));
    return `<figure class="j-map" data-values="${escape(JSON.stringify(labels))}"><figcaption>${text("Compare the journeys","Compare les trajectoires")}</figcaption><p>${text("Further right means larger historical swings. Higher means faster annual growth over the test period.","Plus à droite, le capital a davantage fluctué. Plus haut, il a progressé plus vite par an sur la période testée.")}</p><svg viewBox="0 0 300 110" aria-hidden="true"><path d="M12 8V100H290" fill="none" stroke="currentColor" opacity=".5"/>${circles}</svg><label>${text("Strategy","Stratégie")} <select>${options}</select></label><output>${escape(labels[0])}</output><small>${text("Annual swings · Annual growth","Fluctuations annuelles · Croissance annuelle")}</small></figure>`;
  }
  function range(goal){
    const q=goal.wealth_quantiles;
    if(!Array.isArray(q)||q.length!==3||!q.every(Number.isFinite))return "";
    const target=Number.isFinite(goal.target)?goal.target:null;
    const hi=Math.max(q[2],target||0,1),x=v=>12+272*v/hi;
    const tick=target===null?"":`<path d="M${x(target)} 4V46" stroke="#ff99b8" stroke-width="2" stroke-dasharray="3 2"/>`;
    return `<figure class="j-range"><figcaption>${escape(window.RM.t(goal.objective_id))} · ${escape(goal.due_date)}</figcaption><svg viewBox="0 0 300 50" aria-hidden="true"><path d="M12 25H284" stroke="currentColor" opacity=".35"/><path d="M${x(q[0])} 25H${x(q[2])}" stroke="#91decf" stroke-width="10" stroke-linecap="round"/>${tick}<circle cx="${x(q[1])}" cy="25" r="7" fill="#fff5da"/></svg><p>${text("In the middle 90% of scenarios, available wealth ranges from","Dans les 90 % de scénarios centraux, le capital disponible va de")} ${number(q[0],0)} ${text("to","à")} ${number(q[2],0)} USD. ${text("Median","Médiane")} · ${number(q[1],0)} USD.${target===null?"":" "+text("Target","Cible")+" · "+number(target,0)+" USD."}</p></figure>`;
  }
  function method(name){
    const groups=[
      [["hrp","herc"],"Groups investments that tend to move together, then spreads risk across those groups.","Regroupe les placements qui évoluent ensemble, puis répartit le risque entre ces groupes."],
      [["maximum_sharpe","maximum_sortino","maximum_omega"],"Seeks a balance between potential gains and the risk taken to obtain them.","Cherche un équilibre entre les gains possibles et le risque pris pour les obtenir."],
      [["minimum_cvar","minimum_cdar","tail_hedge_proxy","defensive_reference"],"Gives particular attention to losses in difficult market conditions.","Accorde une attention particulière aux pertes dans les périodes de marché difficiles."],
      [["constrained_utility","mean_variance_utility","capm_utility","ewma_utility"],"Weighs estimated growth against fluctuations and your tolerance for losses.","Met en balance la croissance estimée, les fluctuations et ta tolérance aux pertes."],
      [["resampled_utility","robust_utility","wasserstein_utility"],"Accounts for uncertainty in the estimates before deciding how to invest.","Tient compte de l’incertitude des estimations avant de répartir l’argent."],
      [["tracking_error"],"Tries to move in step with a reference investment.","Cherche à évoluer au même rythme qu’un placement de référence."],
      [["kelly","fractional_kelly"],"Seeks to grow capital over repeated investment periods.","Cherche à faire croître le capital sur des périodes d’investissement successives."],
      [["cross_sectional_momentum","time_series_momentum"],"Uses recent price trends to choose exposures.","S’appuie sur les tendances récentes des prix pour choisir les placements."],
      [["inverse_variance","volatility_target"],"Adjusts exposure according to the size of observed price swings.","Adapte la répartition à l’ampleur des fluctuations observées."]];
    const g=groups.find(([keys])=>keys.includes(name));
    return g?text(g[1],g[2]):"";
  }
  function loader(){
    return `<div class="j-loader" role="status"><div class="j-orbit"><i></i><i></i><img src="./assets/cherry.png" alt=""></div><h2>${text("Building your portfolios","Tes portefeuilles prennent forme")}</h2><p>${text("We use your goals, risk limits and available assets to calculate the cards.","Tes objectifs, tes limites de perte et les actifs disponibles servent à calculer tes cartes.")}</p><output data-elapsed></output></div>`;
  }
  function selectPoint(fig,i){
    fig.querySelector("select").selectedIndex=i;
    fig.querySelector("output").textContent=JSON.parse(fig.dataset.values)[i];
    fig.querySelectorAll("circle").forEach((dot,j)=>dot.setAttribute("r",i===j?7:4));
  }
  document.addEventListener("click",e=>{
    const b=e.target.closest?.("[data-slice],[data-trace],[data-dot]");if(!b)return;
    const fig=b.closest("figure");
    if(b.hasAttribute("data-dot")){selectPoint(fig,Number(b.dataset.dot));return;}
    fig.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));
    if(b.hasAttribute("data-slice")){
      fig.querySelector("strong").textContent=b.dataset.value;fig.querySelector("small").textContent=b.dataset.slice;
    }else{fig.dataset.trace=b.dataset.trace;draw(fig);}
  });
  document.addEventListener("input",e=>{
    if(e.target.matches?.(".j-timeline input"))draw(e.target.closest("figure"));
    if(e.target.matches?.(".j-map select"))selectPoint(e.target.closest("figure"),e.target.selectedIndex);
  });
  new MutationObserver(records=>{for(const r of records)for(const el of r.addedNodes){
    if(el.nodeType!==1)continue;
    if(el.matches(".j-timeline"))draw(el);
    el.querySelectorAll(".j-timeline").forEach(draw);
  }}).observe(document.body,{childList:true,subtree:true});
  window.Journey={composition,timeline,goals,map,loader,range,method};
})();
