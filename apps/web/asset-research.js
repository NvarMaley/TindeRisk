/* Asset-level research library and interval-aligned comparison, independent of portfolio shortlist. */
(() => {
  const $=id=>document.getElementById(id);
  const esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[c]);
  const tr=(en,fr)=>window.RM.language==="fr"?fr:en;
  const num=(v,d=4)=>Number.isFinite(v)?Number(v).toPrecision(d):"—";
  const pct=v=>Number.isFinite(v)?(100*v).toFixed(2)+"%":"—";
  let api,catalog,category="all",query="",page=0,mode="library",active=null,tray=[],result=null,revision=0;
  let cutoff, start,end,currency="USD",kind="total_return",error="";
  let forecastResult=null,forecastEstimate=null,forecastError="",forecastModel="",forecastRevision=0,forecastAdvanced=true;
  let riskResult=null,riskError="",riskModel="",riskRevision=0;
  let factorResult=null,factorError="",factorModel="",factorRevision=0,factorSelected="";
  let sentimentResult=null,sentimentError="",sentimentRevision=0;
  function clearSentiment(){sentimentRevision++;sentimentResult=null;sentimentError="";}
  function sentimentPanel(){if(mode!=="detail")return "";const r=sentimentResult;return `<article><h2>StockTwits · ${tr("Historical sentiment","Sentiment historique")}</h2><p>${tr("Course archive ends March 2020. No current sentiment signal is available.","L’archive du cours s’arrête en mars 2020. Aucun signal actuel de sentiment n’est disponible.")}</p><button id="sentiment-run" class="primary">${tr("View historical sentiment","Voir le sentiment historique")}</button><p role="status">${esc(sentimentError)}</p>${r?.series?`<p>${esc(r.first)} – ${esc(r.last)} · N=${r.observations} ${tr("months","mois")}</p>${lineChart(r.series.map(v=>[v.date,v.polarity]),tr("Bullish versus bearish polarity","Polarité haussière / baissière"),tr("(Bullish − bearish) / labelled messages; range −1 to +1.","(Haussiers − baissiers) / messages étiquetés ; entre −1 et +1."))}${lineChart(r.series.map(v=>[v.date,v.messages]),tr("Message volume","Volume de messages"),tr("Historical monthly message counts.","Nombre historique de messages par mois."))}${Object.keys(r.historical_model_comparison||{}).length?`<p>${tr("Historical pooled-model test on this asset","Test historique des modèles groupés sur cet actif")} · N=${r.test_count}. ${tr("Small sample, not a current forecast.","Petit échantillon, pas une prévision actuelle.")}</p><table><thead><tr><th>${tr("Model","Modèle")}</th><th>RMSE baseline</th><th>RMSE + sentiment</th></tr></thead><tbody>${Object.entries(r.historical_model_comparison).map(([k,v])=>`<tr><td>${esc(k)}</td><td>${pct(v.baseline.rmse)}</td><td>${pct(v.sentiment.rmse)}</td></tr>`).join("")}</tbody></table>`:""}`:r?`<p>${tr("No verified matching historical identity.","Aucune identité historique correspondante vérifiée.")}</p>`:""}</article>`;}
  async function runSentiment(){const token=++sentimentRevision;sentimentResult=null;sentimentError="";try{const r=await api("sentiment/asset",{as_of:cutoff,id:active.item.id});if(token!==sentimentRevision)return;sentimentResult=r;}catch(e){if(token!==sentimentRevision)return;sentimentError=e.message;}render();}
  const classes={all:["All assets","Tous les actifs"],stock:["US stocks","Actions américaines"],equity_etf:["Equity ETFs","ETF d’actions"],treasury_etf:["US Treasury ETFs","ETF du Trésor américain"],cash:["USD cash","Liquidités USD"]};
  const descriptions={
    mean:["Arithmetic mean","Moyenne arithmétique","Average observed return per period.","Moyenne des rendements observés par période."],
    geometric_mean:["Geometric mean","Moyenne géométrique","Constant compounded return per period.","Rendement constant équivalent après capitalisation."],
    median:["Median","Médiane","Half the observations lie below this value.","La moitié des observations se situent sous cette valeur."],
    variance:["Sample variance","Variance échantillon","Squared dispersion around the mean; denominator n−1.","Dispersion quadratique autour de la moyenne, dénominateur n−1."],
    volatility:["Sample volatility","Volatilité échantillon","Square root of sample variance, in return units.","Racine de la variance échantillon, en unités de rendement."],
    annualized_volatility:["Annualized volatility","Volatilité annualisée","Periodic volatility scaled by the square root of periods per year.","Volatilité périodique multipliée par la racine du nombre de périodes annuelles."],
    downside_deviation:["Downside deviation","Déviation baissière","Root mean square of returns below zero.","Racine de la moyenne des rendements négatifs au carré."],
    skewness:["Skewness","Asymétrie","Positive values indicate a longer right tail; negative values a longer left tail.","Une valeur positive indique une queue droite plus longue, une valeur négative une queue gauche plus longue."],
    excess_kurtosis:["Excess kurtosis","Kurtosis excédentaire","Positive excess suggests heavier tails than the normal reference.","Une valeur excédentaire positive suggère des queues plus épaisses que la normale."],
    jarque_bera:["Jarque–Bera","Jarque–Bera","Joint diagnostic of skewness and kurtosis against normality.","Test conjoint de l’asymétrie et de la kurtosis par rapport à la normalité."],
    jarque_bera_p:["Jarque–Bera p-value","Valeur p Jarque–Bera","Below 0.05 is evidence against normality under test assumptions.","Sous 0,05, les données s’écartent de la normalité sous les hypothèses du test."],
    q01:["1% quantile","Quantile 1%","Approximately one percent of returns lie below this level.","Environ 1 % des rendements se situent sous ce niveau."],
    q05:["5% quantile","Quantile 5%","Lower-tail reference, approximately five percent below.","Référence de queue gauche, environ 5 % en dessous."],
    q95:["95% quantile","Quantile 95%","Upper-tail reference, approximately five percent above.","Référence de queue droite, environ 5 % au-dessus."],
    q99:["99% quantile","Quantile 99%","Approximately one percent of returns lie above this level.","Environ 1 % des rendements se situent au-dessus."]
  };
  const groupLabels={
    listed_daily:["Listed products · 2026 daily","Produits cotés · journalier 2026"],
    etf_crsp_daily:["Listed products · CRSP history","Produits cotés · historique CRSP"],
    etf_crsp_monthly:["Listed products · CRSP monthly","Produits cotés · mensuel CRSP"],
    stock_monthly:["CRSP · monthly","CRSP · mensuel"],
    stock_ticker_reference:["DoltHub · daily","DoltHub · journalier"],
    treasury_marks:["US Treasury individual securities","Titres souverains américains individuels"],
    nominal_bond_scenario:["Nominal Treasury conditional scenario","Obligations nominales · scénario conditionnel"],
    bill_marks:["Treasury bills","Bons du Trésor"],btc:["Bitcoin","Bitcoin"],eth:["Ethereum","Ethereum"],
    cash_sofr_index:["USD cash · SOFR index","Liquidités USD · indice SOFR"],cash_sofr_accrual:["USD cash · SOFR accrual","Liquidités USD · intérêts SOFR"],
    benchmark_daily:["Market benchmark · daily","Indice de référence · journalier"],benchmark_monthly:["Market benchmark · monthly","Indice de référence · mensuel"]
  };
  function label(s){
    if(groupLabels[s])return tr(...groupLabels[s]);
    for(const suffix of ["_weekly","_monthly"])if(s.endsWith(suffix)){
      const base=s.slice(0,-suffix.length);
      if(groupLabels[base])return tr(...groupLabels[base])+" · "+(suffix==="_weekly"?tr("weekly","hebdomadaire"):tr("monthly","mensuel"));
    }
    return s;
  }
  function metric(k,value){
    const d=descriptions[k];
    const ratio=["mean","geometric_mean","median","volatility","annualized_volatility","downside_deviation","q01","q05","q95","q99"].includes(k);
    return `<div class="research-metric"><small>${tr(d[0],d[1])}</small><strong>${ratio?pct(value):num(value)}</strong><p>${tr(d[2],d[3])}</p></div>`;
  }
  function lineChart(points,title,explanation,format=num){
    points=(points||[]).map(([x,y])=>[typeof x==="string"?Date.parse(x):x,y]);
    const usable=points.filter(p=>Number.isFinite(p[0])&&Number.isFinite(p[1]));
    if(!usable.length)return `<figure class="research-chart"><figcaption>${esc(title)}</figcaption><p>${tr("No available observations.","Aucune observation disponible.")}</p><small>${esc(explanation)}</small></figure>`;
    const dated=points.some(p=>p[0]>1e10),xs=usable.map(p=>p[0]),ys=usable.map(p=>p[1]);
    const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
    const X=x=>50+570*(x-xmin)/(xmax-xmin||1),Y=y=>175-145*(y-ymin)/(ymax-ymin||1);
    let path="",newSegment=true;
    for(const [x,y] of points){if(!Number.isFinite(y)){newSegment=true;continue;}path+=(newSegment?"M":"L")+X(x).toFixed(2)+" "+Y(y).toFixed(2)+" ";newSegment=false;}
    const xfmt=x=>dated?new Date(x).toISOString().slice(0,10):num(x);
    const grid=[0,.5,1].map(t=>{const v=ymin+t*(ymax-ymin),y=Y(v);return `<line x1="50" x2="620" y1="${y}" y2="${y}" stroke="#507587" opacity=".4"/><text x="4" y="${y+4}" font-size="11" fill="currentColor">${esc(format(v))}</text>`;}).join("");
    return `<figure class="research-chart"><figcaption>${esc(title)}</figcaption><svg viewBox="0 0 650 205" role="img" aria-label="${esc(title)}">${grid}<path d="${path}" fill="none" stroke="#77c6d9" stroke-width="2"/><text x="50" y="195" font-size="11" fill="currentColor">${xfmt(xmin)}</text><text x="620" y="195" font-size="11" text-anchor="end" fill="currentColor">${xfmt(xmax)}</text></svg><small>${esc(explanation)}</small></figure>`;
  }
  function bars(values,title,explanation,format=pct){
    const valid=values.filter(x=>Number.isFinite(x[1])),max=Math.max(...valid.map(x=>Math.abs(x[1])),1e-12);
    return `<figure class="research-chart"><figcaption>${esc(title)}</figcaption>${values.map(([name,v])=>`<div class="research-bar-row"><span>${esc(name)}</span><div class="research-bar-track"><i style="width:${Number.isFinite(v)?100*Math.abs(v)/max:0}%;background:${v<0?"#ea8a92":"#77c6d9"}"></i></div><b>${format(v)}</b></div>`).join("")}<small>${esc(explanation)}</small></figure>`;
  }
  function histogram(a){
    const h=a.distribution.histogram;
    if(!h.length)return "";
    const max=Math.max(...h.map(r=>r[2]),1),w=570/h.length,s=a.statistics;
    const normal=h.map(([lo,hi])=>Number.isFinite(s.volatility)&&s.volatility>0?s.count*(hi-lo)*Math.exp(-.5*((.5*(lo+hi)-s.mean)/s.volatility)**2)/(s.volatility*Math.sqrt(2*Math.PI)):null);
    const scale=Math.max(max,...normal.filter(Number.isFinite));
    const curve=normal.every(Number.isFinite)?`<polyline points="${normal.map((v,i)=>`${50+w*(i+.5)},${175-145*v/scale}`).join(" ")}" stroke="#e1b86c" stroke-width="2" fill="none"/>`:"";
    return `<figure class="research-chart"><figcaption>${tr("Histogram and fitted normal","Histogramme et normale ajustée")}</figcaption><svg viewBox="0 0 650 205" role="img" aria-label="Histogram"><path d="M50 30 V175 H620" stroke="currentColor" fill="none"/>${h.map((r,i)=>`<rect x="${50+w*i}" y="${175-145*r[2]/scale}" width="${Math.max(0,w-1)}" height="${145*r[2]/scale}" fill="#77c6d9"><title>${pct(r[0])} – ${pct(r[1])}: ${r[2]}</title></rect>`).join("")}${curve}<text x="50" y="195" font-size="11" fill="currentColor">${pct(h[0][0])}</text><text x="620" y="195" text-anchor="end" font-size="11" fill="currentColor">${pct(h.at(-1)[1])}</text></svg><small>${tr("Bars are observed counts. Gold curve is the fitted normal reference; departures reveal skewness and heavy tails.","Les barres représentent les fréquences observées. La courbe dorée représente la normale ajustée ; les écarts illustrent l’asymétrie et les queues épaisses.")}</small></figure>`;
  }
  function box(a){
    const s=a.statistics,lo=s.min,hi=s.max;
    if(!Number.isFinite(lo)||!Number.isFinite(hi))return "";
    const X=v=>50+570*(v-lo)/(hi-lo||1);
    return `<figure class="research-chart"><figcaption>${tr("Quantiles and box plot","Quantiles et boîte à moustaches")}</figcaption><svg viewBox="0 0 650 140" role="img" aria-label="Quantiles"><line x1="${X(lo)}" x2="${X(hi)}" y1="50" y2="50" stroke="currentColor"/><rect x="${X(s.q25)}" y="28" width="${Math.max(1,X(s.q75)-X(s.q25))}" height="44" fill="#77c6d955" stroke="#77c6d9"/>${["min","q01","q05","q25","median","q75","q95","q99","max"].map(k=>`<line x1="${X(s[k])}" x2="${X(s[k])}" y1="22" y2="80" stroke="${k==="median"?"#e1b86c":"#77c6d9"}"><title>${k}: ${pct(s[k])}</title></line>`).join("")}<text x="50" y="105" font-size="11" fill="currentColor">${pct(lo)}</text><text x="620" y="105" text-anchor="end" font-size="11" fill="currentColor">${pct(hi)}</text></svg><small>${tr("The box contains the central 50%; the gold line is the median. Hover over marks for exact quantiles.","La boîte contient les 50 % centraux ; le trait doré représente la médiane. Survole les repères pour les valeurs exactes.")}</small></figure>`;
  }
  function assetDetail(a){
    const s=a.statistics,r=a.rolling||{},c=a.cross_section||{},serial=a.serial||{};
    return `<article class="research-detail"><h2>${esc(displayAsset(a))} · ${esc(label(a.source))}</h2><p>${tr("Observed / missing","Observations / manquantes")}: ${s.count} / ${s.missing} · ${esc(result.currency)} · ${esc(result.frequency)}</p><progress max="${s.count+s.missing||1}" value="${s.count}"></progress>
      <div class="research-charts">${lineChart(a.prices,tr("Observed price","Prix observé"),a.price_units||tr("No price series for this source.","Pas de série de prix pour cette source."))}${lineChart(a.history,tr("Return history","Historique des rendements"),tr("Each observation is a source-specific return interval; gaps remain missing.","Chaque observation correspond à un intervalle de rendement de la source ; les lacunes restent manquantes."),pct)}</div>
      <h3>${tr("Return and dispersion","Rendement et dispersion")}</h3><div class="research-metrics">${Object.keys(descriptions).map(k=>metric(k,s[k])).join("")}</div><div class="research-charts">${bars([["Mean",s.mean],["Median",s.median],["Geometric",s.geometric_mean]],tr("Central tendency","Tendance centrale"),tr("Periodic returns are comparable within the selected frequency.","Les rendements périodiques sont comparables à fréquence identique."))}${bars([[tr("Volatility","Volatilité"),s.volatility],[tr("Downside","Baissière"),s.downside_deviation]],tr("Dispersion","Dispersion"),tr("Both bars use the selected period; annualized volatility is shown separately.","Les deux barres utilisent la période sélectionnée ; la volatilité annualisée est affichée séparément."))}${box(a)}${histogram(a)}${lineChart(a.distribution.cdf,"ECDF",tr("Fraction of observations at or below a return.","Proportion des observations inférieures ou égales à un rendement."))}${lineChart(a.distribution.qq,"Normal QQ",tr("Normal quantiles on the horizontal axis; observed return quantiles on the vertical axis. Curvature indicates departure from normality.","Quantiles normaux en abscisse ; quantiles observés en ordonnée. La courbure indique un écart à la normalité."),pct)}</div>
      <div class="research-charts">${bars([[tr("Period","Période"),s.volatility],[tr("Annualized","Annualisée"),s.annualized_volatility]],tr("Volatility scaling","Annualisation de la volatilité"),tr("Annualized volatility depends on the number of periods per year.","La volatilité annualisée dépend du nombre de périodes par an."))}${bars([[tr("Variance","Variance"),s.variance],[tr("Volatility squared","Volatilité au carré"),s.volatility**2]],tr("Variance and volatility","Variance et volatilité"),tr("Both values are in squared decimal return units.","Les deux valeurs sont en unités de rendement décimal au carré."),num)}${bars([[tr("Skewness","Asymétrie"),s.skewness],[tr("Excess kurtosis","Kurtosis excédentaire"),s.excess_kurtosis]],tr("Moments against normal reference","Moments face à la normale"),tr("A normal distribution has zero skewness and zero excess kurtosis.","Une distribution normale a une asymétrie et une kurtosis excédentaire nulles."),num)}</div>
      <h3>${tr("Time dependence","Dépendance temporelle")}</h3><p>Ljung–Box Q: ${num(serial.ljung_box)} · p: ${num(serial.ljung_box_p)} · ADF(1): ${num(serial.adf_lag1_t)} · N: ${serial.observations??"—"}</p><p class="muted">${tr("Ljung–Box tests joint serial correlation; ADF is a stationarity diagnostic with nonstandard critical values. Calculations use the longest contiguous run.","Ljung–Box teste conjointement l’autocorrélation ; ADF est un diagnostic de stationnarité à valeurs critiques non standard. Calcul sur la plus longue séquence continue.")}</p><div class="research-charts">${lineChart(serial.acf?.map((v,i)=>[i,v]),"ACF",tr("Correlation with prior lags.","Corrélation avec les décalages précédents."))}${lineChart(serial.pacf?.map((v,i)=>[i,v]),"PACF",tr("Partial correlation after intermediate lags.","Corrélation partielle après contrôle des décalages intermédiaires."))}${bars([["Jarque–Bera",s.jarque_bera_p],["Ljung–Box",serial.ljung_box_p],[tr("5% reference","Référence 5 %"),.05]],tr("Test p-values","Valeurs p des tests"),tr("Below the 5% reference is evidence against the respective null hypothesis under its assumptions.","Sous la référence de 5 %, le test fournit un indice contre son hypothèse nulle sous ses hypothèses."),pct)}${bars([["ADF(1)",serial.adf_lag1_t]],tr("Stationarity diagnostic","Diagnostic de stationnarité"),tr("The statistic requires nonstandard critical values; zero is only the chart origin.","La statistique requiert des valeurs critiques non standard ; zéro est uniquement l’origine du graphique."),num)}</div>
      <h3>${tr("Time-varying risk and ranks","Risque dynamique et classement")}</h3><div class="research-charts">${lineChart(r.rolling_mean,tr("Rolling mean","Moyenne glissante"),tr("20 complete trailing periods.","20 périodes passées complètes."),pct)}${lineChart(r.annualized_volatility,tr("Rolling annualized volatility","Volatilité annualisée glissante"),tr("20 complete trailing periods scaled to one year.","20 périodes passées complètes annualisées."),pct)}${lineChart(r.rolling_beta,"Rolling beta",tr("Covariance with matching market benchmark divided by its variance.","Covariance avec l’indice de référence aligné divisée par sa variance."))}${lineChart(r.rolling_correlation,tr("Rolling correlation","Corrélation glissante"),tr("Correlation with a matching market benchmark.","Corrélation avec l’indice de référence aligné."))}${lineChart(c.cross_section_rank,tr("Cross-sectional rank","Rang transversal"),tr("Relative rank from 0 to 1 within matching source intervals.","Rang relatif de 0 à 1 au sein des intervalles correspondants."))}${lineChart(c.standardized_return,tr("Winsorized standardized return","Rendement standardisé winsorisé"),tr("Clipping and scaling fitted through 2019; shown only after training cutoff.","Écrêtage et échelle estimés jusqu’en 2019 ; affichage après la date d’entraînement."))}</div></article>`;
  }
  function matrixChart(matrix,assets,title,explanation){
    if(!matrix)return `<p>${esc(title)} · ${tr("Insufficient common intervals.","Intervalles communs insuffisants.")}</p>`;
    const scale=Math.max(...matrix.flat().filter(Number.isFinite).map(Math.abs),1e-12);
    return `<figure class="research-chart"><figcaption>${esc(title)}</figcaption><div class="universe-table-wrap"><table class="research-matrix"><thead><tr><th></th>${assets.map(a=>`<th>${esc(displayAsset(a))}</th>`).join("")}</tr></thead><tbody>${matrix.map((row,i)=>`<tr><th>${esc(displayAsset(assets[i]))}</th>${row.map(v=>`<td style="background:${Number.isFinite(v)?(v<0?"rgba(218,96,111,":"rgba(80,173,195,")+(Math.abs(v)/scale*.75+.08)+")":"transparent"}">${num(v)}</td>`).join("")}</tr>`).join("")}</tbody></table></div><small>${esc(explanation)}</small></figure>`;
  }
  function displayAsset(a){
    const choices=mode==="compare"?tray:active?[active]:[];
    return choices.find(c=>{const s=c.item.series[c.index];return s?.source===a.source&&s?.instrument===a.instrument;})?.item.ticker||a.instrument;
  }
  function renderResult(){
    if(!result)return "";
    const a=result.assets,m=result.matrix;
    return `${a.length>1?`<article><h2>${tr("Asset comparison","Comparaison des actifs")}</h2><p>${tr("Exact common intervals","Intervalles communs exacts")}: ${m.count} · PSD: ${m.psd??"—"}</p><div class="research-charts">${bars(a.map(x=>[displayAsset(x),x.statistics.mean]),tr("Mean return","Rendement moyen"),tr("Same selected frequency and currency.","Fréquence et devise sélectionnées identiques."))}${bars(a.map(x=>[displayAsset(x),x.statistics.volatility]),tr("Sample volatility","Volatilité échantillon"),tr("Same selected frequency; compare risk per period.","Fréquence sélectionnée identique ; comparaison du risque par période."))}</div>${matrixChart(m.covariance,a,"Covariance",tr("Joint movement in squared decimal return units; same complete intervals for every asset.","Variations conjointes en unités de rendement décimal au carré ; mêmes intervalles complets pour tous les actifs."))}${matrixChart(m.pearson,a,"Pearson",tr("Linear correlation between −1 and +1.","Corrélation linéaire entre −1 et +1."))}${matrixChart(m.spearman,a,"Spearman",tr("Rank correlation; useful for monotonic non-linear relationships.","Corrélation des rangs ; utile pour les relations monotones non linéaires."))}</article>`:""}${a.map(assetDetail).join("")}`;
  }
  function forecastPanel(){
    if(mode!=="detail"||!active?.item.series.length)return "";
    const f=forecastResult,m=f?.models[forecastModel];
    const names={historical:["Historical mean","Moyenne historique"],rolling:["Rolling mean","Moyenne mobile"],rolling_10:["Rolling mean (10 periods)","Moyenne mobile (10 périodes)"],ewma:["EWMA","EWMA"],zero_return:["Zero return","Rendement nul"],ols:["OLS","MCO"],ridge:["Ridge","Ridge"],lasso:["Lasso","Lasso"],elastic_net:["Elastic Net","Elastic Net"],ols_lag_only:["OLS: lag only","MCO : retard seul"],ols_clipped:["OLS: clipped training targets","MCO : cibles d'entraînement écrêtées"],random_forest:["Random Forest","Random Forest"],xgboost:["XGBoost","XGBoost"],neural_network:["Neural network","Réseau neuronal"]};
    const modelName=k=>names[k]?tr(...names[k]):k;
    const table=f?'<div class="universe-table-wrap"><table class="research-matrix"><thead><tr><th>'+tr("Model","Modèle")+'</th><th>MSE</th><th>MAE</th><th>'+tr("Direction","Direction")+'</th><th>'+tr("Coverage","Couverture")+'</th><th>'+tr("Net strategy mean","Moyenne stratégie nette")+'</th></tr></thead><tbody>'+Object.entries(f.models).map(([k,v])=>`<tr><th>${esc(modelName(k))}</th><td>${num(v.test.mse)}</td><td>${pct(v.test.mae)}</td><td>${pct(v.test.directional_accuracy)}</td><td>${pct(v.test.interval_coverage)}</td><td>${pct(v.test.net_strategy_mean)}</td></tr>`).join("")+'</tbody></table></div>':"";
    const c=f?.cash_reference;const cash=c?.status==="experimental"?`<h3>${tr("Aligned monthly USD cash reference","Référence cash USD mensuelle alignée")}</h3><p>MSE ${num(c.lagged_cash_mse)} · ${tr("Realized cash return","Rendement cash observé")} ${pct(c.cash_cumulative)} · ${tr("Mean excess return","Excès moyen")} ${pct(c.excess_mean)} · N=${c.test_count}</p><p class="muted">${tr("Historical RF release times unverified.","Dates historiques de publication du RF non vérifiées.")}</p>`:"";
    return `<article class="forecast-panel"><h2>${tr("Return forecasting — experimental","Prévision des rendements — expérimentale")}</h2><p>${tr("Research only. Forecasts are not reliable predictions or investment recommendations. One period at the selected frequency; a separate chronological test.","Recherche uniquement. Les prévisions ne sont ni fiables ni des recommandations d’investissement. Une période à la fréquence sélectionnée ; test chronologique séparé.")}</p><button id="forecast-run" class="primary">${tr("Run forecast research","Calculer les prévisions")}</button> <button id="forecast-batch">${tr("View saved universe run","Voir le calcul global")}</button> <label><input type="checkbox" id="forecast-advanced" ${forecastAdvanced?"checked":""}> ${tr("Include machine learning","Inclure les modèles de machine learning")}</label><p role="status">${esc(forecastError)}</p>${f&&m?`<p>${f.savedBatch?tr("Saved universe run","Calcul global enregistré")+" · ":""}${esc(f.frequency||"")} · ${esc(f.currency||"")} · ${esc(f.kind||"")} · ${esc(f.source||"")}</p><p>${tr("Train / validation / test","Entraînement / validation / test")}: ${f.split.train} / ${f.split.validation} / ${f.split.test} · ${tr("Last observation","Dernière observation")}: ${esc(f.last||f.split.test_end||"")} · ${tr("Validation-selected model","Modèle choisi sur validation")}: ${esc(modelName(f.selected_model))}</p><label>${tr("Inspect model","Examiner un modèle")}<select id="forecast-model">${Object.keys(f.models).map(k=>`<option value="${esc(k)}" ${k===forecastModel?"selected":""}>${esc(modelName(k))}</option>`).join("")}</select></label><div class="mandate-summary"><div><span>${tr("Next-period forecast","Prévision prochaine période")}</span><b>${pct(m.expected_return)}</b></div><div><span>${tr("90% empirical interval","Intervalle empirique à 90 %")}</span><b>${pct(m.interval[0])} – ${pct(m.interval[1])}</b></div></div><div class="research-charts">${lineChart(m.history.map(h=>[h[0],h[1]]),tr("Realized returns (test)","Rendements réalisés (test)"),tr("Held-out chronological test observations.","Observations du test chronologique séparé."),pct)}${lineChart(m.history.map(h=>[h[0],h[2]]),tr("Predicted returns (test)","Rendements prévus (test)"),tr("Forecasts made from prior observations only.","Prévisions à partir des seules observations antérieures."),pct)}${lineChart(m.history.map(h=>[h[0],h[3]]),tr("Lower interval bound","Borne inférieure"),tr("Calibrated on validation residuals.","Calibrée sur les résidus de validation."),pct)}${lineChart(m.history.map(h=>[h[0],h[4]]),tr("Upper interval bound","Borne supérieure"),tr("Not a guaranteed interval.","Intervalle non garanti."),pct)}</div>${table}${cash}<p>${tr("Unavailable / deferred","Indisponibles / reportés")}: ${esc(Object.keys(f.unavailable).join(", "))}</p>`:""}</article>`;
  }
  function riskPanel(){
    if(mode==="library"||mode==="detail"&&!active?.item.series.length||mode==="compare"&&tray.length<2)return "";
    const r=riskResult, m=r?.models?.[riskModel], matrix=mode==="compare";
    const label={historical:["Historical volatility","Volatilité historique"],rolling:["Rolling volatility","Volatilité glissante"],ewma:["EWMA","EWMA"],garch:["GARCH(1,1)","GARCH(1,1)"],egarch:["EGARCH","EGARCH"],gjr_garch:["GJR-GARCH","GJR-GARCH"],sample:["Sample covariance","Covariance échantillon"],ledoit_wolf:["Ledoit-Wolf","Ledoit-Wolf"],oas:["OAS","OAS"],pca_factor_diagonal:["PCA factor / diagonal residual","Facteurs PCA / résidus diagonaux"],pca_factor_full:["PCA factor / full residual","Facteurs PCA / résidus complets"]};
    const name=k=>label[k]?tr(...label[k]):k;
    const options=r?.models?`<label>${tr("Risk model","Modèle de risque")}<select id="risk-model">${Object.keys(r.models).map(k=>`<option value="${esc(k)}" ${riskModel===k?"selected":""}>${esc(name(k))}</option>`).join("")}</select></label>`:"";
    const table=r?.models?`<div class="universe-table-wrap"><table class="research-matrix"><thead><tr><th>${tr("Model","Modèle")}</th><th>${tr("Annualized volatility","Volatilité annualisée")}</th><th>QLIKE (test)</th><th>MSE (test)</th><th>${tr("Numerical guards","Gardes numériques")}</th></tr></thead><tbody>${Object.entries(r.models).map(([k,v])=>`<tr><th>${esc(name(k))}</th><td>${pct(matrix?v.equal_weight_annual_volatility:v.annualized_volatility)}</td><td>${num(v.test?.qlike)}</td><td>${num(v.test?.mse)}</td><td>${esc(v.numerical_guard_count??0)}</td></tr>`).join("")}</tbody></table></div>`:"";
    let charts="";
    if(m&&matrix){
      const assets=r.series||tray.map(a=>a.item.series[a.index]);
      const c=m.covariance, corr=c.map((row,i)=>row.map((v,j)=>c[i][i]>0&&c[j][j]>0?v/Math.sqrt(c[i][i]*c[j][j]):null));
      charts=matrixChart(m.annualized_covariance,assets,tr("Annualized covariance","Covariance annualisée"),tr("Training covariance; squared decimal returns per year.","Covariance d’entraînement ; rendements décimaux au carré par an."))+matrixChart(corr,assets,tr("Correlation","Corrélation"),tr("Common exact intervals.","Intervalles exacts communs."))+
        `<p>PSD: ${esc(m.diagnostics.before.psd)} · ${tr("Condition number","Conditionnement")}: ${num(m.diagnostics.before.condition_number)} · ${tr("Adjusted eigenvalues","Valeurs propres ajustées")}: ${m.diagnostics.eigenvalues_adjusted}</p>`+
        (r.dcc?matrixChart(r.dcc.next_correlation,assets,"DCC-GARCH",tr("Next conditional correlation.","Corrélation conditionnelle prochaine période."))+lineChart(r.dcc.test_correlations.map((c,i)=>[r.dcc.dates?.[i]||i,c[0][1]]),tr("DCC correlation, first two assets","Corrélation DCC, deux premiers actifs"),tr("Held-out conditional correlation.","Corrélation conditionnelle hors échantillon.")):r.dcc_unavailable?`<p>DCC: ${esc(r.dcc_unavailable)}</p>`:"");
    }else if(m){
      charts=`<div class="mandate-summary"><div><span>${tr("Next annualized volatility","Volatilité annualisée prévue")}</span><b>${pct(m.annualized_volatility)}</b></div><div><span>${tr("Persistence","Persistance")}</span><b>${num(m.persistence)}</b></div></div><div class="research-charts">${lineChart(m.history.map(h=>[h[0],h[1]]),tr("Conditional volatility (test)","Volatilité conditionnelle (test)"),tr("Annualized from causal one-step variance.","Annualisée à partir de la variance prédictive causale."),pct)}${lineChart(m.history.map(h=>[h[0],h[2]]),tr("Realized shock magnitude","Amplitude du choc réalisé"),tr("Annualized absolute return shock; noisy proxy.","Choc de rendement absolu annualisé ; mesure bruitée."),pct)}</div>`;
    }
    return `<article><h2>${tr("Volatility and covariance","Volatilité et covariance")}</h2><p>${tr("Experimental risk estimates, not approved portfolio inputs.","Estimations expérimentales du risque, non approuvées pour un portefeuille.")}</p><button id="risk-run" class="primary">${matrix?tr("Calculate covariance models","Calculer les modèles de covariance"):tr("Calculate volatility models","Calculer les modèles de volatilité")}</button>${matrix?"":` <button id="risk-saved">${tr("View saved risk run","Voir le calcul global du risque")}</button>`}<p role="status">${esc(riskError)}</p>${r?.status==="descriptive_only"?`<p>${tr("Descriptive interval volatility","Volatilité descriptive par intervalle")}: ${pct(r.interval_volatility)} · ${esc(r.frequency)} · ${esc(r.kind)} · ${tr("Observations","Observations")}: ${r.observations}. ${tr("No regular conditional model available.","Aucun modèle conditionnel régulier disponible.")}</p>`:""}${r?.models?`<p>${esc(r.frequency||"")} · ${esc(r.kind||"")} · ${esc(r.currency||"")} · ${esc(r.last||"")} · ${tr("Train / validation / test","Entraînement / validation / test")}: ${r.split.train} / ${r.split.validation} / ${r.split.test}</p>${options}${charts}${table}${Object.keys(r.unavailable||{}).length?`<p>${tr("Unavailable models","Modèles indisponibles")}: ${esc(Object.keys(r.unavailable).join(", "))}</p>`:""}`:""}</article>`;
  }
  function clearRisk(){riskRevision++;riskResult=null;riskError="";riskModel="";}
  let tailResult=null,tailError="",tailRevision=0;
  function clearTail(){tailRevision++;tailResult=null;tailError="";}
  function clearFactors(){factorRevision++;factorResult=null;factorError="";factorModel="";factorSelected="";clearTail();clearSentiment();}
  function tailPanel(){
    if(mode==="library")return "";
    const r=tailResult,t=r?.tail,compare=mode==="compare";
    const table=(models)=>`<div class="universe-table-wrap"><table><thead><tr><th>${tr("Confidence / model","Confiance / modèle")}</th><th>VaR</th><th>ES</th></tr></thead><tbody>${Object.entries(models).flatMap(([a,ms])=>Object.entries(ms).map(([k,v])=>`<tr><td>${esc(a)} · ${esc(k)}</td><td>${pct(v.var)}</td><td>${pct(v.es)}</td></tr>`)).join("")}</tbody></table></div>`;
    let content="";
    if(t){const d=t.drawdown;content=`<p>${esc(r.frequency)} · ${esc(r.currency)} · ${esc(r.kind)} · N=${t.observations} · ${esc(r.last)}</p>${table(t.models)}<p>${tr("Downside deviation","Déviation baissière")}: ${pct(t.downside_deviation)} · ${tr("Probability of loss","Probabilité de perte")}: ${pct(t.shortfall_probability)} · ${tr("Maximum drawdown","Perte maximale historique")}: ${pct(d.maximum)} · ${tr("Longest drawdown (periods)","Durée maximale (périodes)")}: ${d.longest_duration} · ${tr("Recovery (periods)","Récupération (périodes)")}: ${esc(d.recovery_periods??"—")}</p>${lineChart(d.dates.map((v,i)=>[v,d.underwater[i]]),tr("Underwater chart","Courbe de drawdown"),tr("Loss relative to prior peak.","Perte par rapport au sommet précédent."),pct)}${bars(t.loss_histogram.counts.map((v,i)=>[pct(t.loss_histogram.edges[i]),v]),tr("Loss distribution","Distribution des pertes"),tr("Observed interval loss counts.","Nombre de pertes par intervalle."),num)}<p>${tr("Backtest: exceptions / expected, Kupiec p, independence p","Backtest : exceptions / attendues, p de Kupiec, p d’indépendance")}</p>${Object.entries(t.validation).map(([a,v])=>v?`<p>${a}% · ${v.exceptions}/${num(v.expected)} · ${num(v.kupiec_p)} · ${num(v.independence_p)} · ${tr("realized tail mean","perte moyenne réalisée")} ${pct(v.realized_exception_mean)} ${v.low_power?tr("(low statistical power)","(faible puissance statistique)"):""}</p>`:"").join("")}${Object.entries(t.evt_sensitivity).map(([a,vs])=>Object.entries(vs).map(([k,v])=>`<p>EVT ${a}% · ${tr("threshold quantile","quantile seuil")} ${k} · VaR ${pct(v.var)} · ES ${pct(v.es)} · N=${v.exceedances} · ${tr("conditional interval","intervalle conditionnel")} ${v.conditional_var_interval.map(pct).join(" – ")}</p>`).join("")).join("")}`;}
    if(r?.simulated_risk){const models={};for(const [k,v] of Object.entries(r.simulated_risk))for(const [a,m] of Object.entries(v))(models[a]??={})[k]=m;content=table(models)+bars(r.es_contributions.contributions.map((v,i)=>[tray[i]?.item.ticker||String(i+1),v]),tr("ES contributions","Contributions à l’ES"),tr("Equal-weight historical scenarios.","Scénarios historiques équipondérés."),pct)+matrixChart(r.student_t_lower_upper_tail,r.series,tr("Student-t tail dependence","Dépendance de queue Student-t"),tr("Fixed five degrees of freedom.","Cinq degrés de liberté fixés."));}
    if(t?.models?.["95"]?.historical)content+=`<label>${tr("Illustrative loss budget per observed period (%)","Budget de perte illustratif par période observée (%)")}<input id="tail-limit" type="number" min="0" max="100" step="0.1"></label><p id="tail-limit-status" role="status"></p>`;
    return `<article><h2>${tr("Tail risk","Risques extrêmes")}</h2><p>${tr("VaR is not a maximum loss. All results are per observed period; estimates require sufficient tail observations.","La VaR n’est pas une perte maximale. Résultats par période observée ; les estimations exigent suffisamment d’observations de queue.")}</p><button id="tail-run" class="primary">${compare?tr("Compare tail dependence","Comparer les dépendances extrêmes"):tr("View tail risk","Voir les risques extrêmes")}</button><p role="status">${esc(tailError)}</p>${content}${r&&!t&&!r.simulated_risk?`<p>${tr("No compatible history","Historique compatible indisponible")}</p>`:""}</article>`;
  }
  async function runTail(){const token=++tailRevision;tailError="";tailResult=null;try{const payload={as_of:cutoff};let next;if(mode==="detail")next=await api("tail/universe/asset",{...payload,id:active.item.id});else next=await api("tail/matrix",{...payload,start,end,currency,kind,series:tray.map(a=>a.item.series[a.index])});if(token!==tailRevision)return;tailResult=next;}catch(e){if(token!==tailRevision)return;tailError=String(e.message||e);}render();}
  function factorPanel(){
    if(mode!=="detail")return "";
    const f=factorResult,m=f?.models?.[factorModel],ref=f?.reference;
    const labels={capm:"CAPM",ff3_subset:"Fama–French 3 (FF5 subset)",ff5:"Fama–French 5",ff6:"Fama–French 5 + Momentum",macro_sensitivity:tr("Macro sensitivities","Sensibilités macro"),internal_styles:tr("Internal style factors","Facteurs de style internes")};
    let contents="";
    if(m){
      const a=m.attribution;const keys=m.factor_names;
      const idx=Math.max(0,keys.indexOf(factorSelected));
      contents=`<p>${esc(f.frequency)} · ${esc(f.currency)} · ${esc(f.kind)} · ${esc(m.first)} – ${esc(m.last)} · N=${m.observations}</p><label>${tr("Model","Modèle")}<select id="factor-model">${Object.keys(f.models).map(k=>`<option value="${esc(k)}" ${k===factorModel?"selected":""}>${esc(labels[k]||k)}</option>`).join("")}</select></label>
      <div class="mandate-summary"><div><span>R² (${tr("training","entraînement")})</span><b>${num(m.r_squared)}</b></div><div><span>Alpha</span><b>${pct(m.alpha)}</b></div><div><span>${tr("Implied total return reference","Rendement total implicite de référence")}</span><b>${pct(m.implied_total_reference)}</b></div></div>
      <div class="research-charts">${bars(keys.map(k=>[k,m.beta[k]]),tr("Factor exposures","Expositions factorielles"),tr("OLS coefficients; macro units differ from traded-factor returns.","Coefficients MCO ; les unités macro diffèrent des rendements factoriels."),num)}${bars(Object.entries(a.mean_factor_contribution),tr("Mean factor attribution (test)","Attribution moyenne des facteurs (test)"),tr("Mean beta times realized factor, per period.","Moyenne du bêta multiplié par le facteur réalisé, par période."),pct)}</div>
      <label>${tr("Rolling exposure","Exposition glissante")}<select id="factor-exposure">${keys.map((k,i)=>`<option value="${esc(k)}" ${i===idx?"selected":""}>${esc(k)}</option>`).join("")}</select></label>${lineChart(m.rolling.map(r=>[r[0],r[idx+1]]),tr("Rolling beta","Bêta glissant"),tr("Trailing observations only; not a future return prediction.","Observations passées uniquement ; pas une prévision de rendement."))}
      <div class="universe-table-wrap"><table class="research-matrix"><thead><tr><th>Factor</th><th>Beta OLS</th><th>Beta Ridge</th><th>HAC SE</th><th>HAC p</th><th>VIF</th></tr></thead><tbody>${keys.map(k=>`<tr><th>${esc(k)}</th><td>${num(m.beta[k])}</td><td>${num(m.ridge.beta[k])}</td><td>${num(m.hac_se[k])}</td><td>${num(m.hac_p[k])}</td><td>${num(m.vif[k])}</td></tr>`).join("")}</tbody></table></div>
      <p>${tr("Held-out attribution reconciliation","Rapprochement de l’attribution hors échantillon")}: ${tr("alpha","alpha")} ${pct(a.alpha)} · ${tr("factors","facteurs")} ${pct(Object.values(a.mean_factor_contribution).reduce((s,v)=>s+v,0))} · ${tr("residual","résidu")} ${pct(a.mean_residual)} · ${tr("realized excess return","rendement excédentaire réalisé")} ${pct(a.mean_realized_excess)}</p>
      <p>${tr("Systematic variance","Variance systématique")}: ${num(m.factor_risk.systematic_variance)} · ${tr("Residual variance","Variance résiduelle")}: ${num(m.factor_risk.residual_variance)} · ${tr("Test RMSE","RMSE test")}: ${pct(Math.sqrt(m.test.mse))}</p>
      ${f.kind==="price_return"?`<p>${tr("Price-only target: not a total-return CAPM.","Rendement du prix uniquement : différent d’un CAPM sur rendement total.")}</p>`:""}${Object.keys(f.unavailable||{}).length?`<p>${tr("Unavailable specifications","Spécifications indisponibles")}: ${esc(Object.keys(f.unavailable).join(", "))}</p>`:""}`;
    }else if(ref){
      contents=`<p>${tr("Analytical reference only","Référence analytique uniquement")} · ${esc(ref.as_of)}</p>${ref.modified_duration!=null?`<p>${tr("Modified duration","Duration modifiée")}: ${num(ref.modified_duration)} · ${tr("Indicative yield","Rendement indicatif")}: ${pct(ref.yield)} · ${esc(ref.yield_type)}</p>`:`<p>SOFR: ${pct(ref.carry_rate)}</p>`}<p>${tr("No equity regression or empirical key-rate beta.","Aucune régression actions ni bêta empirique par taux clé.")}</p>`;
    }
    return `<article><h2>${tr("Factors and regressions","Facteurs et régressions")}</h2><p>${tr("Retrospective research exposures; published factors and proxies have different units. Not approved for investment.","Expositions de recherche rétrospectives ; les facteurs publiés et les proxys ont des unités différentes. Non approuvé pour l’investissement.")}</p><button class="primary" id="factor-run">${tr("View saved factor analysis","Voir l’analyse factorielle enregistrée")}</button><p role="status">${esc(factorError)}</p>${contents}</article>`;
  }
  async function runFactors(){
    if(!active||mode!=="detail")return;
    clearFactors();const own=factorRevision;factorError=tr("Loading…","Chargement…");render();
    try{
      const data=await api("factors/universe/asset",{as_of:cutoff,id:active.item.id});
      if(own!==factorRevision||mode!=="detail")return;
      factorResult=data;factorModel=Object.keys(data.models||{})[0]||"";
      factorSelected=data.models?.[factorModel]?.factor_names[0]||"";
      factorError=data.status==="unavailable"?tr("Insufficient matched factor data.","Données factorielles alignées insuffisantes."):"";render();
    }catch(e){if(own===factorRevision){factorError=e.message;render();}}
  }
  async function runRisk(saved=false){
    clearRisk();const own=riskRevision;
    riskError=tr("Calculating…","Calcul en cours…");render();
    try{
      let r;
      if(saved){
        const row=await api("risk/universe/asset",{as_of:cutoff,id:active.item.id});
        r=row.risk?{...row.risk,frequency:row.frequency,currency:row.currency,kind:row.kind,last:row.last}:row;
      }else{
        const series=(mode==="compare"?tray:[active]).map(a=>a.item.series[a.index]).map(({source,instrument})=>({source,instrument}));
        r=await api(mode==="compare"?"risk/matrix":"risk/asset",{as_of:cutoff,start,end,currency,kind,series,...series[0]});
      }
      if(own!==riskRevision)return;
      riskResult=r;riskModel=r.selected_model||Object.keys(r.models||{})[0];riskError=r.status==="unavailable"?tr("No result available.","Aucun résultat disponible."):"";render();
    }catch(e){if(own===riskRevision){riskError=e.message;render();}}
  }
  function estimateHtml(){
    const e=forecastEstimate;if(!e)return "";
    const label={indicative_ytm:["Indicative yield to maturity","Rendement actuariel indicatif"],real_ytm:["Real yield to maturity (TIPS)","Rendement actuariel réel (TIPS)"],sofr:["SOFR overnight rate","Taux SOFR au jour le jour"],short_history_mean:["Short-history mean","Moyenne sur historique court"]}[e.method]||[e.method,e.method];
    const disclaimer=e.method==="short_history_mean"?tr("Observed interval mean; gaps not filled and no held-out validation.","Moyenne observée, données manquantes non comblées et sans validation hors échantillon."):e.method==="sofr"?tr("Indicative annualized benchmark, not a guaranteed annual return.","Taux de référence annualisé indicatif, sans garantie de rendement annuel."):tr("Conditional clean-mark convention. Yield to maturity is not a one-period expected return.","Hypothèse de prix hors coupon couru. Le rendement actuariel n’est pas un rendement attendu sur une période.");
    return `<article><h3>${esc(tr(...label))}</h3><div class="mandate-summary"><div><span>${esc(e.units)}</span><b>${pct(e.value)}</b></div><div><span>${tr("Observation date","Date d’observation")}</span><b>${esc(e.as_of)}</b></div></div><p>${esc(e.source)} · ${esc(e.currency)}${e.observations?" · "+esc(e.observations)+" observations":""}</p><p>${esc(disclaimer)}</p></article>`;
  }
  async function runForecast(){
    if(!active||mode!=="detail")return;
    const own=++forecastRevision,s=active.item.series[active.index],advanced=$("forecast-advanced").checked;
    forecastAdvanced=advanced;
    forecastResult=null;forecastEstimate=null;forecastError=tr("Calculating…","Calcul en cours…");render();
    try{
      const f=await api("forecast",{source:s.source,instrument:s.instrument,as_of:cutoff,start,end,currency,kind,include_ml:advanced});
      if(own===forecastRevision&&mode==="detail"){forecastResult=f;forecastModel=f.selected_model;forecastError="";render();}
    }catch(e){if(own===forecastRevision){forecastError=e.message;render();}}
  }
  async function loadBatchForecast(){
    if(!active||mode!=="detail")return;
    const own=++forecastRevision;
    forecastResult=null;forecastEstimate=null;forecastError=tr("Loading saved research…","Chargement du calcul global…");render();
    try{
      const row=await api("forecast/universe/asset",{as_of:cutoff,id:active.item.id});
      if(own!==forecastRevision||mode!=="detail")return;
      if(row.forecast){
        forecastResult={...row.forecast,last:row.last,source:row.source,savedBatch:true};
        forecastModel=forecastResult.selected_model;
        forecastError="";
      }else if(row.estimate){
        forecastEstimate=row.estimate;forecastError="";
      }else{
        const reasons={no_series:["No return history","Aucun historique de rendement"],irregular_frequency:["Irregular return intervals","Intervalles irréguliers"],insufficient_contiguous_history:["Insufficient continuous history","Historique continu insuffisant"],asset_not_in_run:["Asset not in the saved run","Actif absent du calcul enregistré"]};
        forecastError=row.reason&&reasons[row.reason]?tr(...reasons[row.reason]):tr("No saved result available","Aucun résultat global disponible");
      }
      render();
    }catch(e){if(own===forecastRevision){forecastError=e.message;render();}}
  }
  function coverage(item){
    if(!item.matching_source)return "";
    const matchingSource=item.matching_source==="fama_french_rf"?"Fama–French RF":label(item.matching_source);
    const frequencies={daily:tr("Daily","Journalier"),weekly:tr("Weekly","Hebdomadaire"),monthly:tr("Monthly","Mensuel"),irregular:tr("Irregular intervals","Intervalles irréguliers")};
    const cleaning={
      stock:tr("Historical records are matched by permanent identifier. More recent public price series are kept separate.","L’historique repose sur un identifiant permanent. Les séries publiques de prix plus récentes restent séparées."),
      cash:tr("The monthly reference rate is aligned with the securities. SOFR series below are separate cash research references.","Le taux mensuel de référence est aligné avec les titres. Les séries SOFR ci-dessous sont des références de recherche distinctes."),
    };
    const etfCleaning=tr("The engine uses the reported monthly total return, which includes distributions. The project checks this history against compounded daily returns where both are available.","Le moteur utilise le rendement total mensuel déclaré, distributions comprises. Le projet le rapproche des rendements journaliers composés quand les deux séries existent.");
    return `<section class="asset-coverage" aria-label="${tr("Data coverage","Couverture des données")}">
      <h3>${tr("Data used for the portfolio","Données utilisées par le portefeuille")}</h3>
      <p>${esc(matchingSource)} · ${tr("USD monthly series","Série mensuelle USD")} · ${esc(catalog.matching_data_start)} – ${esc(catalog.matching_data_end)} · ${esc(catalog.matching_months)} ${tr("months","mois")}.</p>
      <p>${esc(cleaning[item.category]??etfCleaning)}</p>
      <h3>${tr("Series available on this page","Séries disponibles sur cette fiche")}</h3>
      <ul>${item.series.flatMap(series=>series.kinds.map(kind=>{
        const isTotal=kind==="total_return";
        const use=isTotal&&series.source===item.matching_source?tr("Source of portfolio total returns within the shared window","Source des rendements totaux du portefeuille dans la fenêtre commune"):tr("Asset research","Recherche par actif");
        const dates=series.kind_dates?.[kind]??series;
        return `<li><strong>${esc(label(series.source))}</strong> · ${esc(frequencies[series.frequency]??series.frequency)} · ${esc(isTotal?tr("Total return","Rendement total"):tr("Price return","Rendement de prix"))} · ${esc(dates.first)} – ${esc(dates.last)} · ${esc(use)}</li>`;
      })).join("")}</ul>
      <p class="muted">${tr("Dates indicate the observed span. Some series may have gaps. The analysis below uses the series and dates you select. Its forecasts, volatility models and other diagnostics are for asset research.","Les dates délimitent les observations. Certaines séries peuvent avoir des trous. Les analyses ci-dessous utilisent la série et les dates que tu sélectionnes. Les prévisions, modèles de volatilité et autres diagnostics servent à l’étude de l’actif.")}</p>
    </section>`;
  }
  function render(){
    const host=$("universe-statistics");if(!host)return;
    if(!catalog){host.textContent=tr("Loading catalogue…","Chargement du catalogue…");return;}
    const tabs=`<div class="research-tabs"><button id="research-library" class="${mode==="library"?"primary":""}">${tr("Catalogue","Catalogue")}</button><button id="research-compare" class="${mode==="compare"?"primary":""}">${tr("Compare assets","Comparer les actifs")} (${tray.length})</button></div>`;
    const list=catalog.items.filter(a=>(category==="all"||a.category===category)&&(!query||`${a.name} ${a.ticker}`.toLowerCase().includes(query.toLowerCase())));
    const per=24,shown=list.slice(page*per,(page+1)*per);
    const library=`${catalog.matching_data_end?'<p class="muted">'+esc(tr("Portfolio data through ","Données des portefeuilles arrêtées au ")+catalog.matching_data_end)+'</p><p>'+esc(tr(`${catalog.items.length} assets. Securities qualify with ${catalog.matching_months} consecutive monthly total returns. Some asset pages also show more recent research prices.`,`${catalog.items.length} actifs. Chaque titre doit avoir ${catalog.matching_months} mois consécutifs de rendement total. Certaines fiches présentent aussi des prix de recherche plus récents.`))+'</p>':""}<div class="mandate-grid universe-controls"><label>${tr("Asset class","Classe d’actifs")}<select id="research-category">${Object.entries(classes).map(([k,v])=>`<option value="${k}" ${category===k?"selected":""}>${tr(...v)}</option>`).join("")}</select></label><label>${tr("Search name or ticker","Rechercher un nom ou ticker")}<input id="research-search" type="search" placeholder="SPY, IEF…" value="${esc(query)}"></label></div><div class="research-asset-grid">${shown.map(a=>`<article class="catalog-card"><h3>${esc(a.name)}</h3><p class="catalog-ticker">${esc(a.ticker)}</p><p class="catalog-provider">${tr("Source","Source")} · ${esc(a.provider)}</p><button class="primary" data-research-open="${esc(a.id)}">${tr("Open statistics","Ouvrir la fiche")} →</button></article>`).join("")}</div>${!shown.length?`<p>${tr("No matching assets.","Aucun actif correspondant.")}</p>`:""}<div class="research-pagination"><button id="research-prev" ${page===0?"disabled":""}>←</button><span>${page+1} / ${Math.max(1,Math.ceil(list.length/per))}</span><button id="research-next" ${(page+1)*per>=list.length?"disabled":""}>→</button></div>`;
    const options=(a,idx)=>a.series.map((s,i)=>`<option value="${i}" ${idx===i?"selected":""}>${esc(label(s.source))} · ${esc(s.first)} – ${esc(s.last)}</option>`).join("");
    const controls=`<div class="mandate-grid universe-controls"><label>${tr("Start","Début")}<input id="research-start" type="date" value="${esc(start||"")}"></label><label>${tr("End","Fin")}<input id="research-end" type="date" value="${esc(end||"")}"></label><label>${tr("Currency","Devise")}<select id="research-currency"><option ${currency==="USD"?"selected":""}>USD</option><option ${currency==="CHF"?"selected":""}>CHF</option></select></label><label>${tr("Return kind","Type de rendement")}<select id="research-kind"><option value="total_return" ${kind==="total_return"?"selected":""}>${tr("Total return","Rendement total")}</option><option value="price_return" ${kind==="price_return"?"selected":""}>${tr("Price return","Rendement du prix")}</option></select></label></div>`;
    const detail=active?`<div class="catalog-detail-header"><button id="research-back">← ${tr("Back to catalogue","Retour au catalogue")}</button><small>${esc(active.item.ticker)}</small><h2>${esc(active.item.name)}</h2><p>${tr("Source","Source")} · ${esc(active.item.provider)}</p>${active.item.series.length?`<button id="research-add">${tray.some(a=>a.item.id===active.item.id)?tr("In comparison","Dans le comparateur"):tr("+ Add to comparison","+ Ajouter à la comparaison")}</button>`:""}</div>${coverage(active.item)}${active.item.series.length?`<div class="universe-controls"><label>${tr("Historical series / frequency","Historique / fréquence")}<select id="research-series">${options(active.item,active.index)}</select></label></div>${controls}<button class="primary" id="research-run">${tr("Update analysis","Actualiser la fiche")}</button>`:`<p>${tr("No usable statistical series is available for this asset at the selected date.","Aucune série statistique exploitable n’est disponible pour cet actif à la date sélectionnée.")}</p>`}`:"";
    const compare=`<h2>${tr("Asset comparison","Comparateur d’actifs")}</h2>${tray.length?tray.map((a,i)=>`<div class="catalog-tray-item"><b>${esc(a.item.name)} · ${esc(a.item.ticker)}</b><select aria-label="${tr("Series","Série")}" data-tray-series="${i}">${options(a.item,a.index)}</select><button data-research-remove="${i}">×</button></div>`).join("")+controls+`<button class="primary" id="research-run">${tr("Compare selected assets","Comparer les actifs")}</button>`:`<p>${tr("Open an asset profile and add it to the comparison.","Ouvre une fiche et ajoute l’actif au comparateur.")}</p>`}`;
    host.innerHTML=`<section class="research-hub">${tabs}${mode==="library"?library:mode==="detail"?detail:compare}<p role="status">${esc(error)}</p></section><div id="research-results">${forecastPanel()}${riskPanel()}${factorPanel()}${tailPanel()}${sentimentPanel()}${mode==="detail"?estimateHtml():""}${mode==="library"?"":renderResult()}</div>`;
    const on=(id,event,fn)=>{const el=$(id);if(el)el[event]=fn;};
    on("research-category","onchange",()=>{category=$("research-category").value;page=0;render();});
    on("research-search","oninput",()=>{query=$("research-search").value;page=0;render();$("research-search").focus();$("research-search").setSelectionRange(query.length,query.length);});
    on("research-prev","onclick",()=>{page--;render();});on("research-next","onclick",()=>{page++;render();});
    const go=next=>{revision++;forecastRevision++;forecastResult=null;forecastEstimate=null;forecastError="";clearRisk();clearFactors();mode=next;result=null;error="";if(next==="compare")setRange(tray);render();};
    on("research-library","onclick",()=>go("library"));on("research-back","onclick",()=>go("library"));
    on("research-compare","onclick",()=>go("compare"));
    on("research-series","onchange",()=>{active.index=Number($("research-series").value);setRange([active]);render();run();});
    on("research-add","onclick",add);
    on("research-run","onclick",run);
    on("forecast-run","onclick",runForecast);
    on("forecast-batch","onclick",loadBatchForecast);
    on("risk-run","onclick",()=>runRisk(false));
    on("risk-saved","onclick",()=>runRisk(true));
    on("risk-model","onchange",()=>{riskModel=$("risk-model").value;render();});
    on("factor-run","onclick",runFactors);
    on("tail-run","onclick",runTail);
    on("tail-limit","oninput",event=>{
      const value=event.target.value,limit=Number(value)/100,model=tailResult?.tail?.models?.["95"]?.historical;
      const status=$("tail-limit-status");
      if(!model||!status)return;
      status.textContent=value===""?"":!Number.isFinite(limit)||limit<0||limit>1?tr("Invalid loss budget","Budget de perte invalide"):
        tr("Historical 95% VaR / ES: ","VaR / ES historiques à 95 % : ")+pct(model.var)+" / "+pct(model.es)+" · "+
        (model.es>limit?tr("ES exceeds illustrative limit","ES supérieure au budget illustratif"):tr("ES within illustrative limit","ES dans le budget illustratif"))+
        " · "+tr("Not a guarantee or mandate approval.","Ni garantie ni validation du mandat.");
    });
    on("sentiment-run","onclick",runSentiment);
    on("factor-model","onchange",()=>{factorModel=$("factor-model").value;factorSelected=factorResult.models[factorModel].factor_names[0];render();});
    on("factor-exposure","onchange",()=>{factorSelected=$("factor-exposure").value;render();});
    on("forecast-model","onchange",()=>{forecastModel=$("forecast-model").value;render();});
    const clearForecast=()=>{forecastRevision++;forecastResult=null;forecastEstimate=null;forecastError="";clearRisk();clearFactors();render();};
    on("research-start","onchange",()=>{start=$("research-start").value;clearForecast();});
    on("research-end","onchange",()=>{end=$("research-end").value;clearForecast();});
    on("research-currency","onchange",()=>{currency=$("research-currency").value;clearForecast();});
    on("research-kind","onchange",()=>{kind=$("research-kind").value;clearForecast();});
    host.querySelectorAll("[data-research-open]").forEach(el=>el.onclick=()=>open(el.dataset.researchOpen));
    host.querySelectorAll("[data-research-remove]").forEach(el=>el.onclick=()=>{revision++;clearRisk();clearTail();tray.splice(Number(el.dataset.researchRemove),1);setRange(tray);result=null;render();});
    host.querySelectorAll("[data-tray-series]").forEach(el=>el.onchange=()=>{revision++;clearRisk();clearTail();tray[Number(el.dataset.traySeries)].index=Number(el.value);setRange(tray);result=null;render();});
  }
  function setRange(choices){
    const series=choices.map(a=>a.item.series[a.index]).filter(Boolean);
    if(!series.length)return;
    start=series.map(s=>s.first).sort().at(-1);
    end=series.map(s=>s.last).sort()[0];
    kind=series.every(s=>s.kinds.includes("total_return"))?"total_return":"price_return";
  }
  async function open(id){
    const item=catalog?.items.find(a=>a.id===id);
    if(!item)return;
    revision++;forecastRevision++;forecastResult=null;forecastEstimate=null;forecastError="";clearRisk();clearFactors();active={item,index:0};mode="detail";result=null;error="";setRange([active]);render();
    $("universe-statistics").scrollIntoView?.({block:"start"});
    if(item.series.length)await run();
  }
  function add(){
    if(!active||tray.some(a=>a.item.id===active.item.id))return;
    if(tray.length>=8){error=tr("Select at most eight assets.","Sélectionne au maximum huit actifs.");render();return;}
    tray.push({...active});render();
  }
  async function run(){
    forecastRevision++;forecastResult=null;forecastEstimate=null;forecastError="";clearRisk();clearFactors();
    const choices=mode==="compare"?tray:active?[active]:[];
    const series=choices.map(a=>a.item.series[a.index]).filter(Boolean);
    start=$("research-start").value;end=$("research-end").value;currency=$("research-currency").value;kind=$("research-kind").value;
    if(!series.length){error=tr("Select an asset first.","Sélectionne d’abord un actif.");render();return;}
    if(new Set(series.map(a=>a.frequency)).size>1){error=tr("Choose the same frequency for all assets.","Choisis la même fréquence pour tous les actifs.");render();return;}
    if(series.some(a=>a.kinds.length&&!a.kinds.includes(kind))){error=tr("The selected return kind is unavailable for one or more assets.","Le type de rendement est indisponible pour un ou plusieurs actifs.");render();return;}
    const own=++revision;error=tr("Calculating…","Calcul en cours…");result=null;render();
    try{const data=await api("statistics/compare",{as_of:cutoff,series:series.map(({source,instrument})=>({source,instrument})),start,end,currency,kind});
      if(own===revision){result=data;error="";render();}
    }catch(e){if(own===revision){error=e.message;render();}}
  }
  async function load(fetcher,asOf){api=fetcher;cutoff=asOf;const own=++revision;try{const next=await api("statistics/catalog",{as_of:cutoff,scope:"matching"});if(own===revision){catalog=next;mode="library";active=null;result=null;error="";render();}}catch(e){if(own===revision)$("universe-statistics").textContent=e.message;}}
  window.AssetResearch={load,render,open};
})();
