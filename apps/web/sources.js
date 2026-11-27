/* Local source readiness view; no download or allocation is triggered by opening this page. */
(() => {
  const $=id=>document.getElementById(id),t=k=>window.RM.t(k);
  const esc=x=>String(x??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const fr={CRYPTO_SPOT:"Vérifier les jours manquants, les frais, la conservation et le mandat client.",ETF_DAILY:"Rapprocher les volumes et rendements WRDS par titre et date. Vérifier les indicateurs de qualité et compléter 2026.",ETF_MONTHLY:"Actualiser 2026 et réconcilier les distributions / delistings.",EQUITY_MASTER:"Valider la classification et les dates de cotation; conserver les titres radiés.",ETF_HOLDINGS:"Télécharger N-PORT et demander les historiques de détentions WRDS si disponibles, surtout avant 2019.",FUNDAMENTALS:"Vérifier les dates de publication, les RDQ manquantes et les révisions.",LINKS:"Actualiser CCM et valider les intervalles de liaison.",TREASURY_MASTER:"Réconcilier les pages d'adjudications historiques et récentes; exclure FRN/STRIPS.",TREASURY_DAILY:"Demander les prix secondaires individuels CRSP Treasury, coupons et intérêts courus.",RATES_FX:"Vérifier unités, calendrier et délai de publication; ne pas confondre taux et rendement.",MACRO_VINTAGES:"Compléter les vintages ALFRED et dates de publication.",FACTORS:"Actualiser si nécessaire auprès des producteurs officiels; vérifier unités et licences.",BENCHMARKS:"Demander rendements totaux et historiques de composition lorsque licenciés.",FUTURES:"Compléter les échéances et vérifier cours de compensation, volumes, positions ouvertes, ticks et marges auprès de la bourse.",COSTS_LIQUIDITY:"Rapprocher les volumes et les prix, puis vérifier les frais et les encours datés.",SENTIMENT:"Facultatif; vérifier les droits du cours et la disponibilité historique."};
  let report=null, matching=null, snapshot=null, returns=null, forecasts=null, risk=null, factors=null, tail=null, sentiment=null, api=null;
  function sentimentHtml(fr){if(sentiment?.status!=="historical_only")return "";const r=sentiment,p=v=>Number.isFinite(v)?(100*v).toFixed(3)+"%":"—";return `<article><h2>StockTwits · ${fr?"Recherche historique":"Historical research"}</h2><p>${r.asset_count} / ${r.eligible_count} ${fr?"actifs mensuels appariés":"matched monthly assets"} · ${r.aligned_rows} ${fr?"observations":"observations"} · ${esc(r.first)} – ${esc(r.last)}. ${fr?"Aucun signal actuel : archive terminée en mars 2020.":"No current signal: archive ends March 2020."}</p><p>${fr?"Test chronologique, mêmes lignes, variables de sentiment retardées d’un mois complet.":"Chronological test, same rows, sentiment lagged by one full month."} ${esc(r.split.test_start)} – ${esc(r.split.test_end)}</p><table><thead><tr><th>${fr?"Modèle":"Model"}</th><th>RMSE baseline</th><th>RMSE + sentiment</th><th>${fr?"Amélioration":"Improvement"}</th><th>${fr?"Intervalle bootstrap par mois":"Monthly block interval"}</th></tr></thead><tbody>${Object.entries(r.models).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${p(v.baseline?.rmse)}</td><td>${p(v.sentiment?.rmse)}</td><td>${p(v.rmse_improvement)}</td><td>${v.uncertainty?.conditional_block_interval?.map(p).join(" – ")||"—"}</td></tr>`).join("")}</tbody></table><p>${fr?"Références simples (sans sentiment)":"Simple references (without sentiment)"}: ${Object.entries(r.reference_models||{}).map(([k,v])=>`${esc(k)} RMSE ${p(v.rmse)}`).join(" · ")}</p><p>${fr?"Facteur long-short historique (grossier, non investi)":"Historical long-short factor (gross, not invested)"}: ${r.factor.test_months} ${fr?"mois":"months"} · ${fr?"écart moyen":"mean spread"} ${p(r.factor.mean_test_spread)} · rank IC ${Number.isFinite(r.factor.mean_test_rank_ic)?r.factor.mean_test_rank_ic.toFixed(3):"—"}</p>${r.black_litterman_diagnostic?.months?`<p>Black–Litterman (${fr?"illustration scalaire historique uniquement":"historical scalar illustration only"}): RMSE ${p(r.black_litterman_diagnostic.prior.rmse)} → ${p(r.black_litterman_diagnostic.view_posterior.rmse)}. ${fr?"Aucune vue actuelle activée.":"No current view enabled."}</p>`:""}</article>`;}
  function tailHtml(fr){if(tail?.status!=="complete")return "";return `<article><h2>${fr?"Risques extrêmes":"Tail risk"}</h2><p>${esc(tail.catalogue_count)} ${fr?"actifs examinés":"assets reviewed"} · ${esc(tail.statuses.computed||0)} ${fr?"estimations":"estimates"} · ${esc(tail.statuses.descriptive_only||0)} ${fr?"descriptifs uniquement":"descriptive only"} · ${esc(tail.statuses.unavailable||0)} ${fr?"indisponibles":"unavailable"}</p><table><tbody>${Object.entries(tail.by_model).map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("")}</tbody></table></article>`;}
  function factorHtml(french){
    if(factors?.status!=="complete")return "";
    const s=factors.statuses||{},models=Object.entries(factors.by_model||{}).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
    const portfolio=Object.entries(factors.portfolio_summary||{}).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v.periods)}</td><td>${esc(v.valid_gross)}</td><td>${Number.isFinite(v.test_mean_rank_ic)?v.test_mean_rank_ic.toFixed(3):"—"}</td><td>${Number.isFinite(v.test_mean_net)?(v.test_mean_net*100).toFixed(2)+"%":"—"}</td></tr>`).join("");
    const taxonomy=Object.entries(factors.taxonomy||{}).map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("");
    const pca=(factors.pca?.explained_variance_ratio||[]).map((v,i)=>`<p>PC${i+1} <progress max="1" value="${esc(v)}"></progress> ${(100*v).toFixed(1)}%</p>`).join("");
    const scores=Object.entries(factors.score_coverage||{}).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join("");
    return `<article><h2>${french?"Facteurs et régressions":"Factors and regressions"}</h2><p>${esc(factors.catalogue_count)} ${french?"actifs examinés":"assets examined"} · ${esc(s.computed||0)} ${french?"régressions":"regressions"} · ${esc(s.analytical_reference||0)} ${french?"références analytiques":"analytical references"} · ${esc(s.unavailable||0)} ${french?"indisponibles":"unavailable"}</p><p>${french?"Facteurs publiés et proxys distincts ; les portefeuilles de recherche ne sont pas exécutables.":"Published factors and proxies remain distinct; research factor portfolios are not executable."}</p><table><thead><tr><th>${french?"Modèle":"Model"}</th><th>${french?"Actifs":"Assets"}</th></tr></thead><tbody>${models}</tbody></table>${factors.common_factor_covariance?`<p>${french?"Covariance factorielle alignée":"Aligned factor covariance"}: ${esc(factors.common_factor_covariance.assets)} · ${esc(factors.common_factor_covariance.observations)} ${french?"intervalles":"intervals"} · PSD: ${esc(factors.common_factor_covariance.diagonal_diagnostics.psd)}</p>`:""}<h3>${french?"Portefeuilles factoriels expérimentaux":"Experimental factor portfolios"}</h3><div class="universe-table-wrap"><table><thead><tr><th>Factor</th><th>N</th><th>${french?"Valides":"Valid"}</th><th>Rank IC (test)</th><th>${french?"Moyenne nette":"Net mean"} (test)</th></tr></thead><tbody>${portfolio}</tbody></table></div>${factors.portfolio_common_test?`<p>${french?"Test commun":"Common test"}: ${esc(factors.portfolio_common_test.periods)} · ${esc(factors.portfolio_common_test.complete_net_periods)} ${french?"périodes nettes complètes":"complete net periods"}</p>`:""}<h3>PCA</h3>${pca}<h3>${french?"Couverture des scores":"Score coverage"}</h3><table><tbody>${scores}</tbody></table><h3>13 ${french?"facteurs":"factors"}</h3><table><tbody>${taxonomy}</tbody></table></article>`;
  }
  function riskHtml(french){
    if(risk?.status!=="complete")return "";
    const s=risk.statuses||{};
    const rows=(risk.cohorts||[]).map(c=>`<tr><td>${esc(c.frequency)} · ${esc(c.kind)}</td><td>${esc(c.last)}</td><td>${esc(c.assets)}</td><td>${esc(c.observations)}</td><td>${esc(c.status)}</td><td>${c.dcc?"DCC":""}</td></tr>`).join("");
    return `<article><h2>${french?"Volatilité et covariance":"Volatility and covariance"}</h2><p>${esc(risk.catalogue_count)} ${french?"actifs examinés":"assets examined"} · ${esc((s.computed||0)+(s.partial||0))} ${french?"modèles réguliers":"regular-model profiles"} · ${esc(s.descriptive_only||0)} ${french?"descriptifs uniquement":"descriptive only"} · ${esc(s.unavailable||0)} ${french?"indisponibles":"unavailable"}</p><p>${french?"Les covariances sont calculées uniquement entre rendements comparables ; aucune matrice globale artificielle.":"Covariances use comparable returns only; no artificial global matrix."}</p><div class="universe-table-wrap"><table><thead><tr>${(french?["Fréquence / rendement","Date","Actifs","Intervalles","Statut","DCC"]:["Frequency / return","Date","Assets","Intervals","Status","DCC"]).map(x=>`<th>${x}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></article>`;
  }
  function forecastHtml(french){
    if(forecasts?.status!=="complete")return "";
    const s=forecasts.statuses||{};
    const rows=Object.entries(forecasts.by_category||{}).map(([name,v])=>`<tr><td>${esc(name)}</td><td>${esc(v.computed||0)}</td><td>${esc(v.fallback||0)}</td><td>${esc(v.partial||0)}</td><td>${esc(v.unavailable||0)}</td><td>${esc(v.error||0)}</td></tr>`).join("");
    return `<article><h2>${french?"Couverture des prévisions":"Forecast coverage"}</h2><p>${esc(forecasts.as_of)} · ${esc(forecasts.catalogue_count)} ${french?"actifs examinés":"assets examined"} · ${esc(s.computed||0)} ${french?"calculés avec les dix modèles":"computed with all ten models"} · ${esc(s.fallback||0)} ${french?"estimations spécifiques":"specific estimates"}</p>${forecasts.common_monthly?`<p>${french?"Cohorte mensuelle comparable, rendement total USD":"Comparable monthly cohort, USD total return"}: ${esc(forecasts.common_monthly.count)} · ${esc(forecasts.common_monthly.as_of)}</p>`:""}<p>${french?"Recherche expérimentale. Les dates, fréquences et types de rendement diffèrent; ces résultats ne sont pas un vecteur directement optimisable.":"Experimental research. Dates, frequencies and return kinds differ; these results are not an optimization-ready vector."}</p><div class="universe-table-wrap"><table><thead><tr>${(french?["Classe","Calculés","Estimation spécifique","Partiels","Indisponibles","Erreurs"]:["Class","Computed","Specific estimate","Partial","Unavailable","Errors"]).map(x=>`<th>${x}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></article>`;
  }
  function returnsHtml(french){
    if(!Array.isArray(returns?.datasets))return "";
    const rows=returns.datasets.map(r=>{
      const valid=r.total_returns || r.price_returns || r.real_returns || r.annualized_means || r.matched || 0;
      const pct=r.rows?Math.round(100*valid/r.rows):0;
      const kind=r.total_returns? "Total" : r.price_returns? (french?"Prix":"Price") : r.real_returns? (french?"Réel":"Real") : r.annualized_means? (french?"Annualisé":"Annualized") : (french?"Rapprochement":"Reconciliation");
      return `<tr><td><b>${esc(r.dataset)}</b><small>${esc(r.method)}</small></td><td>${esc(r.frequency)} · ${esc(r.base_currency)} · ${esc(r.units)}</td><td>${esc(r.rows)}</td><td>${esc(r.price_returns??"—")} / ${esc(r.total_returns??"—")}</td><td>${esc(r.chf_price_returns??"—")} / ${esc(r.chf_total_returns??"—")}</td><td>${esc(kind)} <progress max="100" value="${pct}" aria-label="${esc(french?"Couverture":"Coverage")}"></progress> ${pct}%</td></tr>`;
    }).join("");
    const total=returns.datasets.reduce((sum,r)=>sum+r.rows,0);
    return `<article><h2>${french?"Rendements et devises":"Returns and FX"}</h2><p>${french?"Résultats de recherche. Les scénarios obligataires et les données historiques nécessitent une validation avant tout backtest.":"Research results. Bond scenarios and historical data require validation before backtesting."}</p><p>${returns.datasets.length} ${french?"tables":"partitions"} · ${esc(total.toLocaleString(french?"fr-CH":"en-US"))} ${french?"lignes":"rows"}</p><div class="universe-table-wrap"><table><thead><tr>${(french?["Table","Fréquence / devise / unités","Lignes","Prix / total USD","Prix / total CHF","Couverture"]:["Table","Frequency / currency / units","Rows","Price / total USD","Price / total CHF","Coverage"]).map(x=>`<th>${x}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></article>`;
  }
  function snapshotHtml(french){
    if (!snapshot) return "";
    const quality = r => Object.entries(r.quality || {}).map(([k,v]) => {
      const labels = {unchanged_close:["Unchanged close","Clôture identique"],large_price_change:["Large price change","Forte variation"],missing_return:["Missing return","Rendement manquant"],expected_sessions:["Expected observations","Observations attendues"],missing_sessions:["Missing observations","Observations manquantes"]};
      return `${esc(labels[k]?.[french?1:0] || k)}: ${esc(v)}`;
    }).join(" · ");
    const rows = snapshot.datasets.map(r => `<tr><td>${esc(r.dataset)}</td><td>${esc(r.rows)}</td><td>${esc(r.first)} – ${esc(r.last)}</td><td>${esc(r.invalid)} / ${esc(r.duplicates)} / ${esc(r.conflicts)}</td><td>${quality(r)}</td></tr>`).join("");
    const total = snapshot.datasets.reduce((sum,r)=>sum+(Number(r.rows)||0),0);
    return `<article><h2>${french?"Qualité et données historiques":"Point-in-time data quality"}</h2><p>${french?"Les usages qui exigent une disponibilité historique certifiée restent bloqués. Le replay du mandat reste une simulation rétrospective.":"Uses requiring certified historical availability remain blocked. The mandate replay is a retrospective simulation."}</p><p>${esc(snapshot.built_at || "")} · ${snapshot.datasets.length} ${french?"tables":"partitions"} · ${esc(total.toLocaleString(french?"fr-CH":"en-US"))} ${french?"lignes normalisées":"normalized rows"}</p><div class="universe-table-wrap"><table><thead><tr>${(french?["Table","Lignes","Période","Invalides / doublons / conflits","Qualité"]:["Table","Rows","Period","Invalid / duplicate / conflict","Quality"]).map(x=>`<th>${x}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></article>`;
  }
  const gaps = [
    ["Missing months and delisting proceeds", "Mois manquants et produits de liquidation",
      "A missing return excludes a security at that decision. A missing realized return for a holding can invalidate the strategy’s path. Five years of coverage favor older, well-documented securities.",
      "Un mois manquant écarte le titre à cette date. Un rendement réalisé absent sur une position peut invalider la trajectoire de la stratégie. Les cinq ans exigés favorisent les titres anciens et bien documentés."],
    ["Unverified publication times", "Dates de publication non vérifiées",
      "Original publication times are missing for the monthly CRSP and Fama–French RF series. Dated membership, data vintages and the execution lag reduce timing bias. The replay remains retrospective.",
      "Les dates de publication d’origine manquent dans les séries mensuelles CRSP et Fama–French RF. Les listes datées, les versions des données et le délai d’exécution réduisent le biais temporel. Le replay reste rétrospectif."],
    ["Survivorship and fund selection", "Biais de survie et sélection des ETF",
      "Stock membership changes by date. The ETF registry is retrospective and some historical closing proceeds are unknown.",
      "La liste d’actions change à chaque date. Le registre d’ETF a été constitué après coup et certains produits de liquidation historiques restent inconnus."],
    ["Older archive, short test, model choices", "Archive ancienne, test court et choix de modèle",
      "The test has 25 monthly returns, with limited evidence on rare losses. The equity-heavy median can raise the estimated return of a Treasury ETF. The current ranking also uses end-2025 estimates.",
      "Le test comporte 25 mois, ce qui donne peu de recul sur les pertes rares. La médiane d’un univers dominé par les actions peut relever le rendement estimé d’un ETF du Trésor. Le classement actuel utilise aussi les estimations de fin 2025."],
    ["Recent prices and quote coverage", "Prix récents et couverture des cotations",
      "Public 2026 prices remain separate from the frozen return series. Position monitoring requires a configured quote feed and coverage for the holdings.",
      "Les prix publics de 2026 restent séparés des rendements figés. Le suivi des positions dépend d’un flux configuré et de la couverture des titres détenus."],
  ];
  function matchingHtml(french){
    const groups = ["stock","equity_etf","treasury_etf","cash"];
    const labels = french ? ["actions US","ETF d’actions","ETF du Trésor","poche de cash USD"] :
      ["US stocks","equity ETFs","Treasury ETFs","USD cash allocation"];
    const counts = matching?.items ? groups.map((category,i)=>
      `${matching.items.filter(row=>row.category===category).length} ${labels[i]}`).join(" · ") : "";
    const window = counts ?
      `<p><strong>${esc(counts)}</strong></p><p>${esc(matching.matching_data_start)} → ${esc(matching.matching_data_end)} · ${esc(matching.matching_months)} ${french?"mois de rendements":"monthly returns"}</p>` :
      `<p>${french?"Vérification du catalogue local en cours ou données locales indisponibles.":"Checking local catalogue or local data unavailable."}</p>`;
    return `<article><h2>${french?"Données utilisées par le portefeuille":"Portfolio inputs"}</h2>${window}
      <p>${french?"Les rendements totaux mensuels CRSP sont alignés sur le calendrier de SPY. Les distributions sont incluses. Les actions proviennent du top 1 000 daté et le cash suit Fama–French RF.":"Monthly CRSP total returns are aligned to SPY’s calendar and include distributions. Stocks are selected from the dated top 1,000 and cash follows Fama–French RF."}</p>
      <h3>${french?"Données manquantes et biais":"Missing data and biases"}</h3>
      <dl>${gaps.map(row=>`<dt><strong>${esc(row[french?1:0])}</strong></dt><dd>${esc(row[french?3:2])}</dd>`).join("")}</dl></article>`;
  }
  let auditError=false;
  function render(){
    const french=window.RM.language==="fr";
    if(!report){
      const label=auditError ? (french?"Audits locaux indisponibles.":"Local audits unavailable.") :
        (french?"Lecture des audits locaux…":"Reading local audits…");
      $("sources-report").innerHTML=matchingHtml(french)+`<p role="status">${esc(label)}</p>`;
      return;
    }
    const rows=report.rows.map(r=>`<tr><td><b>${esc(r.name)}</b><small>${esc(r.provider)} · ${esc(r.frequency)}</small></td><td><b>${esc(t(r.status))}</b><small>${esc(french?(r.evidence_fr||r.evidence):r.evidence)}</small></td><td>${esc(r.acquisition)}<small>${esc(french?(fr[r.id]||r.action):r.action)}</small></td><td><small>${esc(r.required_fields)}</small><small>${esc(r.rights)}</small></td><td>${String(r.url).startsWith("https://")?`<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">${esc(t("universeSource"))}</a>`:""}</td></tr>`).join("");
    const inv = report.inventory;
    const inventory = inv?.available ? (french ? `Inventaire local : ${inv.files} versions de fichiers, ${inv.providers} groupes de sources.` : `Local inventory: ${inv.files} file versions, ${inv.providers} source groups.`) : (french ? "Inventaire local indisponible." : "Local inventory unavailable.");
    const rights = french ? "Les droits WRDS pour le stockage local, les transformations et le partage restent à confirmer. Aucune diffusion de données aux testeurs." : "WRDS rights for local storage, transformation and sharing await confirmation. Data distribution to testers is on hold.";
    $("sources-report").innerHTML=`${matchingHtml(french)}<details class="research-module"><summary>${french?"Audits et archives de recherche":"Research archives and audits"}</summary><article><p>${esc(inventory)}</p><p>${esc(rights)}</p><p>${esc(report.version)} · ${esc(report.as_of)}</p><div class="universe-table-wrap"><table><thead><tr>${["sourcesProvider","sourcesStatus","sourcesAction","sourcesFields","universeSource"].map(k=>`<th>${esc(t(k))}</th>`).join("")}</tr></thead><tbody>${rows}</tbody></table></div></article>${snapshotHtml(french)}${returnsHtml(french)}${forecastHtml(french)}${riskHtml(french)}${factorHtml(french)}${tailHtml(french)}${sentimentHtml(french)}</details>`;
  }
  let loadRevision=0;
  async function load(fetcher){
    api=fetcher;const revision=++loadRevision,cutoff={as_of:new Date().toISOString().slice(0,10)};
    auditError=false;
    render();
    const matchingLoad=api("statistics/catalog",{...cutoff,scope:"matching"}).catch(()=>null).then(value=>{
      if(revision!==loadRevision)return;
      matching=Array.isArray(value?.items)?value:null;
      render();
    });
    try{
      const sourceReport=await api("sources",cutoff);
      if(revision!==loadRevision)return;
      report=sourceReport;
      render();
      const jobs=[["snapshot",v=>{snapshot=Array.isArray(v?.datasets)?v:null;}],["returns",v=>{returns=v;}],
        ["forecast/universe",v=>{forecasts=v;}],["risk/universe",v=>{risk=v;}],["factors/universe",v=>{factors=v;}],
        ["tail/universe",v=>{tail=v;}],["sentiment",v=>{sentiment=v;}]];
      for(const [route,apply] of jobs){
        const value=await api(route,cutoff).catch(()=>null);
        if(revision!==loadRevision)return;
        apply(value);
      }
      render();
    }catch(e){if(revision===loadRevision&&e.message!=="sessionChanged"){auditError=true;render();}}
    await matchingLoad;
  }
  $("sources-refresh").addEventListener("click",()=>{if(api)load(api);});window.SourcesView={load,render};
})();
