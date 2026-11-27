(() => {
  const sectorLabels = {
    11:["Agriculture","Agriculture"],21:["Mines, pétrole et gaz","Mining, oil and gas"],
    22:["Services publics","Utilities"],23:["Construction","Construction"],
    31:["Industrie manufacturière","Manufacturing"],42:["Commerce de gros","Wholesale trade"],
    44:["Commerce de détail","Retail trade"],48:["Transport et entreposage","Transport and warehousing"],
    51:["Information et communication","Information"],52:["Finance et assurances","Finance and insurance"],
    53:["Immobilier et location","Real estate and rental"],54:["Services professionnels et techniques","Professional and technical services"],
    55:["Gestion de sociétés","Company management"],56:["Services administratifs et déchets","Administrative and waste services"],
    61:["Éducation","Education"],62:["Santé et action sociale","Health and social care"],
    71:["Arts, loisirs et spectacles","Arts and recreation"],72:["Hôtellerie et restauration","Accommodation and food"],
    81:["Autres services","Other services"],92:["Administration publique","Public administration"]
  };
  const typeLabels = {
    stock:["Actions en direct","Individual stocks"],equity_etf:["ETF d’actions","Equity ETFs"],
    treasury_etf:["ETF du Trésor US","US Treasury ETFs"],cash:["Liquidités USD","USD cash"]
  };
  const colors=["#80dfc5","#71b9f3","#cab5fc","#f9cc8d"];
  const e = value => String(value).replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const pct = (value, fr) => Number.isFinite(value) ? new Intl.NumberFormat(fr?"fr-CH":"en-US",{style:"percent",maximumFractionDigits:2}).format(value) : "—";
  const usd = (value, fr) => Number.isFinite(value) ? new Intl.NumberFormat(fr?"fr-CH":"en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(value) : "—";
  const formatDate = (value,fr,full=false) => {
    const date=new Date(value+"T12:00:00Z");
    return Number.isFinite(date.getTime()) ? new Intl.DateTimeFormat(fr?"fr-CH":"en-US",{month:full?"long":"short",year:"numeric",timeZone:"UTC",...(full?{day:"numeric"}:{})}).format(date) : "—";
  };
  const shortDate = (value,fr) => formatDate(value,fr);
  const language = fr => fr?0:1;
  const sector = (key,fr) => sectorLabels[key]?.[language(fr)] || (fr?"Secteur non renseigné":"Sector unavailable");
  const type = (key,fr) => typeLabels[key]?.[language(fr)] || key;
  const card=(label,value,note="")=>`<div class="rm-stat"><span>${e(label)}</span><strong>${e(value)}</strong>${note?`<small>${e(note)}</small>`:""}</div>`;
  const row=(label,value)=>`<div><dt>${e(label)}</dt><dd>${e(value)}</dd></div>`;
  function allocation(result, mandate, report, strategyName, fr) {
    const pick=(frText,en)=>fr?frText:en;
    const m=result.metrics||{}, c=result.composition;
    const money=n=>usd(n,fr), percent=n=>pct(n,fr);
    const variance=c?c.volatility**2:0;
    const groups=c?Object.entries(c.allocation):[];
    const budgets=Object.entries(result.budgets||{}).filter(([,w])=>w>1e-8);
    const budgetRows=budgets.map(([k,v])=>row(strategyName(k),percent(v))).join("");
    const stacks=groups.map(([key,weight],i)=>weight>0?`<span style="width:${Math.max(0,weight)*100}%;--slice:${colors[i]}"></span>`:"").join("");
    const allPositions=c?.positions||[];
    const positionRows=rows=>rows.map(p=>`<tr><th scope="row">${e(p.name)}</th><td>${e(type(p.type,fr))}</td><td>${p.sector?e(sector(p.sector,fr)):"—"}</td><td>${percent(p.weight)}</td></tr>`).join("");
    const top=positionRows(allPositions.slice(0,6));
    const table=(body)=>`<div class="match-table-scroll"><table class="rm-positions"><thead><tr><th>${pick("Position","Holding")}</th><th>${pick("Type","Type")}</th><th>${pick("Secteur NAICS","NAICS sector")}</th><th>${pick("Poids","Weight")}</th></tr></thead><tbody>${body}</tbody></table></div>`;
    const constraints=mandate?.constraints||{};
    const covered=(c?.allocation.stock||0)-(c?.stock_sectors.unknown||0);
    const avoidedSectors=(constraints.excluded_sectors||[]).map(k=>sector(k,fr));
    const excluded=[...(constraints.excluded_companies||[]),...avoidedSectors];
    const trace=mandate&&report?`<h4>${pick("Mandat appliqué","Mandate applied")}</h4><dl class="rm-labeled">${[
      row(pick("Capital de départ","Starting capital"),money(mandate.capital)),
      row(pick("Date cible","Target date"),formatDate(mandate.horizon_date,fr,true)),
      ...(mandate.contribution_monthly>0?[row(pick("Apport mensuel","Monthly contribution"),money(mandate.contribution_monthly))]:[]),
      ...(mandate.withdrawal_monthly>0?[row(pick("Retrait mensuel","Monthly withdrawal"),money(mandate.withdrawal_monthly))]:[]),
      row(pick("Plafond de perte en stress","Stress-loss limit"),percent(report.effective_stress_limit)),
      row(pick("Classes demandées","Requested asset classes"),constraints.allowed_assets.map(k=>({equity:pick("Actions","Equities"),treasury:pick("Trésor US","US Treasuries"),cash:pick("Cash USD","USD cash")})[k]||k).join(" · ")),
      ...(constraints.max_asset_weight?.value!=null?[row(pick("Poids maximal par ligne","Holding cap"),percent(constraints.max_asset_weight.value)+(constraints.max_asset_weight.mode==="soft"?pick(" · préférence de classement"," · ranking preference"):""))]:[]),
      ...(constraints.volatility?.value!=null?[row(pick("Plafond de volatilité","Volatility limit"),percent(constraints.volatility.value)+(constraints.volatility.mode==="soft"?pick(" · préférence de classement"," · ranking preference"):""))]:[]),
      ...(excluded.length?[row(pick("Exclusions actives","Active exclusions"),excluded.join(" · ")),row(pick("Conséquence des exclusions","Effect of exclusions"),pick("ETF d’actions écartés faute de composition historique vérifiable","Equity ETFs excluded because historical holdings cannot be verified"))]:[]),
      ...(constraints.prefer_diversification?[row(pick("Diversification","Diversification"),pick("Les cartes moins concentrées sont favorisées au classement","Lower concentration is favored in card ranking"))]:[]),
    ].join("")}</dl>`:"";
    const observation=c?`<article class="rm-subpanel"><h4>${pick("Composition","Composition")}</h4>
      <div class="rm-stack" aria-hidden="true">${stacks}</div>
      <dl class="rm-labeled">${groups.map(([key,value],i)=>`<div><dt><i style="--slice:${colors[i]}"></i>${e(type(key,fr))}</dt><dd>${percent(value)}</dd></div>`).join("")}</dl>
      <p class="rm-note">${allPositions.length} ${pick("positions détenues","holdings")} · ${c.effective_positions.toFixed(1)} ${pick("positions équivalentes à poids égaux","equal-weight equivalent holdings")}</p>
      ${top?table(top):""}
      ${allPositions.length>6?`<details><summary>${pick("Autres positions","Remaining holdings")} (${allPositions.length-6})</summary>${table(positionRows(allPositions.slice(6)))}</details>`:""}
    </article><article class="rm-subpanel"><h4>${pick("Diversification et risque","Diversification and risk")}</h4>
      <dl class="rm-labeled">${row(pick("Volatilité du portefeuille","Portfolio volatility"),percent(c.volatility))}
      ${row(pick("Si les titres fluctuaient tous ensemble","If all holdings moved together"),percent(c.weighted_standalone_volatility))}
      ${variance>1e-12?row(pick("Part de la variance liée aux mouvements communs","Share of variance from co-movements"),percent(c.cross_covariance/variance)):""}</dl>
      <p class="rm-note">${pick("Les covariances mesurent dans quelle mesure les titres évoluent ensemble. Une part signée négative signale ici que les interactions réduisent la variance.","Covariances measure how holdings move together. A negative signed share means their interactions reduce variance here.")}</p>
      ${c.variance_shares?`<details><summary>${pick("Contribution au risque par classe","Risk contributions by asset class")}</summary><dl class="rm-labeled">${Object.entries(c.variance_shares).map(([k,v])=>row(type(k,fr),percent(v))).join("")}</dl><p class="rm-note">${pick("Variance annuelle wᵀΣw","Annual variance wᵀΣw")} · ${variance.toFixed(6)}. ${pick("Terme des covariances entre titres","Cross-holding covariance term")} · ${c.cross_covariance.toFixed(6)}.</p></details>`:""}
      ${c.allocation.stock>0?`<details><summary>${pick("Secteurs des actions détenues en direct","Sectors of directly held stocks")}</summary><p class="rm-note">${percent(covered)} ${pick("du portefeuille classés. Le détail sectoriel interne des ETF reste indisponible.","of the portfolio classified. ETF look-through sector weights are unavailable.")}</p><dl class="rm-labeled">${Object.entries(c.stock_sectors).sort((a,b)=>b[1]-a[1]).map(([k,v])=>row(sector(k,fr),percent(v))).join("")}</dl></details>`:c.allocation.equity_etf>0?`<p class="rm-note">${pick("L’exposition actions vient des ETF. Leur détail sectoriel interne reste indisponible.","Equity exposure comes from ETFs. ETF look-through sector weights are unavailable.")}</p>`:""}
    </article>`:"";
    return `<section class="rm-result"><div class="rm-result-lead"><span class="rm-eyebrow">${pick("Allocation consolidée","Consolidated allocation")}</span>
      <h3>${pick("Ton portefeuille en un coup d’œil","Your portfolio at a glance")}</h3>
      <p>${pick("Les positions communes aux stratégies sont additionnées. Les poids ci-dessous décrivent le portefeuille entier.","Shared holdings are consolidated. The weights below describe the entire portfolio.")}</p>
      <div class="rm-kpis">${card(pick("Rendement estimé","Estimated return"),percent(result.expected_return),pick("Estimations annuelles des actifs, pondérées par leurs poids","Annual asset estimates weighted by portfolio weights"))}
      ${card(pick("Volatilité estimée","Estimated volatility"),percent(result.estimated_volatility),pick("Amplitude des fluctuations annuelles","Scale of annual fluctuations"))}
      ${card(pick("Perte en stress","Stress loss"),percent(result.stress_loss),money(result.stress_usd)+" · "+pick("pire scénario testé","worst scenario tested"))}</div></div>
      <div class="rm-result-grid"><article class="rm-subpanel"><h4>${pick("Répartition entre stratégies","Strategy budgets")}</h4><dl class="rm-labeled">${budgetRows}</dl>${trace}</article>
      <article class="rm-subpanel"><h4>${pick("Résultat du backtest","Backtest results")}</h4><p class="rm-note">${e(result.period||"")}</p><dl class="rm-labeled">${[
        row(pick("Rendement composé annuel","Compound annual return"),percent(m.cagr)),
        row(pick("Volatilité historique","Historical volatility"),percent(m.vol)),
        row(pick("Plus forte baisse","Maximum drawdown"),percent(Number.isFinite(m.drawdown)?Math.abs(m.drawdown):null)),
        row(pick("Sharpe au-dessus du cash","Sharpe above cash"),Number.isFinite(m.sharpe)?m.sharpe.toFixed(2):"—"),
        ...(result.reference_metrics?[row(pick("Rendement de la référence","Benchmark return")+
          " · "+(result.benchmark?strategyName(result.benchmark):"60/40"),percent(result.reference_metrics.cagr))]:[])
      ].join("")}</dl><p class="rm-note">${pick("Le Sharpe rapporte l’excédent de rendement au-dessus du cash à la volatilité. Le backtest simule le passé avec frais modélisés.","Sharpe scales excess return above cash by volatility. The backtest replays history with modeled fees.")}</p></article>
      ${observation}</div></section>`;
  }

  function fanChart(curve,goals,title,fr) {
    if (!curve?.bands?.length || curve.bands.length<2) return "";
    const unit=fr?"k USD":"k USD";
    const high=Math.max(1,...curve.bands.map(b=>b[2]));
    const step=10**Math.floor(Math.log10(high/4));
    const max=Math.ceil(high/step)*step;
    const x=i=>82+530*i/(curve.bands.length-1);
    const y=v=>224-188*v/max;
    const coords=q=>curve.bands.map((b,i)=>[x(i),y(b[q])]);
    const points=rows=>rows.map(pair=>pair.map(p=>p.toFixed(1)).join(",")).join(" ");
    const tick=new Intl.NumberFormat(fr?"fr-CH":"en-US",{maximumFractionDigits:1});
    const grid=Array.from({length:5},(_,i)=>{
      const value=max*i/4, line=y(value);
      return `<path class="rm-axis" d="M82 ${line}h530"/><text x="75" y="${line+4}" text-anchor="end">${tick.format(value/1000)}</text>`;
    }).join("");
    const label=fr?"Capital restant après flux et objectifs payés":"Balance remaining after flows and funded goals";
    const events=goals.filter(g=>g.median_paid>0);
    const markers=[...new Set(events.map(g=>g.date))].map(date=>{
      const i=curve.dates.findIndex(day=>day>=date);
      if(i<1)return "";
      const [left,right]=curve.dates.slice(i-1,i+1).map(Date.parse);
      const position=x(i-1+(Date.parse(date)-left)/(right-left));
      return `<path class="rm-funding-marker" d="M${position} 36V224"/>`;
    }).join("");
    return `<figure class="rm-fan"><figcaption>${label} <span>${fr?"USD nominaux":"Nominal USD"}</span></figcaption>
      <svg viewBox="0 0 635 252" role="img" aria-label="${label}"><text x="8" y="17">${unit}</text>${grid}
      <polygon points="${points([...coords(0),...coords(2).reverse()])}" class="rm-fan-band"/>
      <polyline points="${points(coords(1))}" class="rm-fan-mid"/>${markers}</svg>
      <div class="rm-chart-dates"><span>${shortDate(curve.dates[0],fr)}</span>${curve.dates.length>5?`<span>${shortDate(curve.dates[Math.round((curve.dates.length-1)/2)],fr)}</span>`:""}<span>${shortDate(curve.dates.at(-1),fr)}</span></div>
      <div class="rm-chart-legend"><span class="rm-legend-mid">${fr?"Médiane":"Median"}</span><span class="rm-legend-band">${fr?"90 % centraux des scénarios":"Central 90% of scenarios"}</span>${markers?`<span class="rm-legend-funding">${fr?"Paiement d’un objectif":"Goal payment"}</span>`:""}</div>
      ${events.length?`<ul class="rm-chart-events">${events.map(g=>`<li>${e(shortDate(g.date,fr))} · ${e(title(g.objective_id))} · ${fr?"paiement médian simulé":"median simulated payment"} ${e(usd(g.median_paid,fr))}</li>`).join("")}</ul>`:""}
    </figure>`;
  }

  function projection(response, title, fr) {
    const pick=(a,b)=>fr?a:b;
    const m=response.matched, rate=m.present_value, horizon=m.wealth_path?.dates?.at(-1);
    const money=n=>usd(n,fr), percent=n=>pct(n,fr);
    const band=a=>a?.length?`${money(a[0])} — ${money(a[2])}`:"—";
    const cap=m.terminal_quantiles, gain=m.net_gain_quantiles;
    const pv=rate?.terminal_quantiles;
    const benchmark=response.benchmark==="USD cash"?pick("cash USD","USD cash"):(response.benchmark||pick("référence","benchmark"));
    const qualitative=m.goals.some(g=>g.probability==null);
    const dataRows=m.goals.map((g,i)=>`<tr><th scope="row">${e(title(g.objective_id))}<small>${e(formatDate(g.due_date,fr,true))}</small></th>
      <td>${money(g.target)}</td><td>${percent(g.probability)}${Number.isFinite(g.probability)?`<span class="rm-probability" aria-hidden="true"><i style="width:${100*g.probability}%"></i></span>`:""}</td><td>${money(g.expected_deficit)}</td><td>${percent(response.reference.goals[i]?.probability)}</td></tr>`).join("");
    return `<div class="rm-result-lead rm-forecast"><span class="rm-eyebrow">${pick("Scénarios sur ton horizon","Scenarios over your horizon")}</span>
      <h3>${horizon?pick("À l’horizon du","At the horizon on")+" "+e(formatDate(horizon,fr,true)):pick("Dans le futur","At your horizon")}</h3>
      <div class="rm-kpis">
        ${card(pick("Capital restant médian","Median remaining balance"),money(cap?.[1]),pick("Après les flux et objectifs payés","After flows and funded goals"))}
        ${card(pick("Gain net simulé moyen","Mean simulated net gain"),money(m.mean_net_gain),pick("Capital restant + sommes versées − capital et apports","Remaining balance + payments − capital and contributions"))}
        ${card(pick("Capital médian en valeur actuelle","Median balance in present value"),money(pv?.[1]),pick("Taux d’actualisation annuel ","Annual discount rate ")+percent(rate?.rate))}
      </div></div>
      ${fanChart(m.wealth_path,m.funded_goal_schedule||[],title,fr)}
      <div class="rm-result-grid"><article class="rm-subpanel"><h4>${pick("Montants à l’horizon","Amounts at the horizon")}</h4><dl class="rm-labeled">${[
        row(pick("Fourchette du capital restant","Remaining balance range"),band(cap)),
        row(pick("Gain net médian en USD futurs","Median net gain in future USD"),money(gain?.[1])),
        row(pick("Gain net médian en valeur actuelle","Median net gain in present value"),money(rate?.net_gain_quantiles?.[1])),
        ...(response.reference.terminal_quantiles?[row(pick("Solde médian avec la référence","Median balance with the benchmark")+" · "+benchmark,money(response.reference.terminal_quantiles[1]))]:[]),
        ...(m.purchasing_power?[row(pick("Capital médian en pouvoir d’achat de départ","Median balance in starting-date purchasing power"),money(m.purchasing_power.terminal_quantiles[1]))]:[]),
        ...(m.purchasing_power?[row(pick("Inflation annuelle du mandat","Annual mandate inflation"),percent(m.purchasing_power.inflation))]:[]),
      ].join("")}</dl><p class="rm-note">${pick("Le gain net additionne le capital restant et les retraits, dettes et objectifs effectivement payés, puis déduit le capital initial et les apports. La valeur actuelle applique le taux à chaque flux à sa date.","Net gain adds the remaining balance and actual withdrawals, liabilities and funded goals, then subtracts starting capital and contributions. Present value discounts each cash flow on its date.")}</p></article>
      <article class="rm-subpanel"><h4>${pick("Performance du placement hors flux","Investment performance excluding flows")}</h4><dl class="rm-labeled">${[
        row(pick("Rendement composé annuel moyen","Mean compound annual return"),percent(m.mean_market_cagr)),
        ...(m.purchasing_power?[row(pick("Rendement annuel médian après inflation","Median annual return after inflation"),percent(m.purchasing_power.market_cagr_quantiles[1]))]:[]),
        row(pick("Fourchette du rendement annuel","Annual return range"),m.market_cagr_quantiles?.length?percent(m.market_cagr_quantiles[0])+" — "+percent(m.market_cagr_quantiles[2]):"—"),
        row(pick("Fréquence des pertes à l’horizon","Frequency of terminal investment losses"),percent(m.market_loss_probability)),
        row(pick("Fréquence de recul au-delà du seuil du mandat","Frequency of drawdown beyond the mandate threshold"),percent(m.drawdown_breach_probability))
      ].join("")}</dl><p class="rm-note">${response.paths} ${pick("trajectoires, construites à partir de","paths built from")} ${response.training_months} ${pick("mois d’historique","months of history")}${response.data_end?" · "+pick("archive arrêtée au ","archive cutoff ")+e(response.data_end):""}. ${pick("Les rendements passés sont réutilisés en blocs de six mois. Frais de rééquilibrage modélisés, fiscalité hors simulation.","Historical returns are reused in six-month blocks. Rebalancing costs are modeled. Taxes are outside the simulation.")}</p></article></div>
      ${dataRows?`<article class="rm-subpanel"><h4>${pick("Financement des objectifs","Funding your goals")}</h4><div class="match-table-scroll"><table class="rm-positions"><thead><tr><th>${pick("Objectif et date","Goal and date")}</th><th>${pick("Montant cible","Target amount")}</th><th>${pick("Probabilité","Probability")}</th><th>${pick("Déficit moyen","Mean shortfall")}</th><th>${pick("Probabilité · référence","Probability · benchmark")} (${e(benchmark)})</th></tr></thead><tbody>${dataRows}</tbody></table></div><p class="rm-note">${pick("Les probabilités sont des fréquences dans les scénarios simulés. Le déficit moyen est calculé sur tous les scénarios, avec zéro si la cible est atteinte.","Probabilities are frequencies across the simulated paths. Mean shortfall includes zero for paths that reach the target.")} ${qualitative?pick("Un tiret signale un objectif dont la réussite n’est pas chiffrable avec les paramètres du mandat.","A dash marks a goal whose success cannot be quantified with the mandate inputs."):""}</p></article>`:""}
      <details class="rm-limitations"><summary>${pick("Comment lire ces scénarios","How to read these scenarios")}</summary><p class="rm-note">${pick("L’archive courte peut sous-représenter les crises rares. La bande mesure la dispersion des scénarios sous les hypothèses retenues. Au-delà des cinq années d’archive, les blocs sont réutilisés.","The short archive may underrepresent rare crises. The band shows the spread of scenarios under the model assumptions. Blocks are reused beyond the five years of source data.")}</p></details>`;
  }
  window.PortfolioResult={allocation,projection,sectorLabels,sector};
})();
