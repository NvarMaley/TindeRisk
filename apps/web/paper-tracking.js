(() => {
  const CASH = "USD cash";
  const MINUTE = 60_000;
  const DAY = 24 * 60 * MINUTE;
  const symbolPattern = /^[A-Z0-9][A-Z0-9./-]{0,14}$/;
  let mounted = null;

  function capture(weights, capital, previous, now = new Date()) {
    const entries = Object.entries(weights || {}).filter(([,value]) => Number.isFinite(value) && value > 1e-8);
    const sum = entries.reduce((total,[,value]) => total + value, 0);
    if (!Number.isFinite(capital) || capital <= 0 || Math.abs(sum - 1) > 1e-5) return null;
    const target = Object.fromEntries(entries.sort(([a],[b])=>a.localeCompare(b)).map(([key,value])=>[key,value/sum]));
    if (previous?.capital === capital && JSON.stringify(previous.target) === JSON.stringify(target)) return previous;
    return {
      capital, target, confirmedAt:now.toISOString(), policy:"hold",
      quantities:null, baselineAt:null, lastRebalance:null, latest:null, history:[], journal:[],
    };
  }

  function quarterlyDue(iso) {
    const date = new Date(iso);
    const month = date.getUTCMonth()+3, day = date.getUTCDate();
    date.setUTCMonth(month,1);
    const lastDay = new Date(Date.UTC(date.getUTCFullYear(),date.getUTCMonth()+1,0)).getUTCDate();
    date.setUTCDate(Math.min(day,lastDay));
    return date.getTime();
  }

  function update(state, market, now = new Date()) {
    if (market.status !== "ok") return {status:market.status};
    const assets = Object.keys(state.target).filter(key=>key!==CASH);
    const stamps = assets.map(key=>Date.parse(market.quotes?.[key]?.as_of));
    const missing = assets.filter((key,i)=>{
      const price=market.quotes?.[key]?.price;
      return !Number.isFinite(price)||price<=0||!Number.isFinite(stamps[i])||stamps[i]>+now+2*MINUTE;
    });
    if (missing.length) return {status:"missing", missing};
    const oldest = assets.length ? Math.min(...stamps) : +now;
    const newest = assets.length ? Math.max(...stamps) : +now;
    if (!state.quantities && oldest < +now-7*DAY) return {status:"baseline_stale"};
    const price = key => key === CASH ? 1 : market.quotes[key].price;
    const mark = assets.map((key,i)=>[key,stamps[i],price(key)]);
    if (state.latest && JSON.stringify(state.latest.mark)===JSON.stringify(mark)) return {status:"ok"};
    if (state.latest?.mark?.some(([key,stamp],i)=>mark[i]?.[0]===key&&mark[i][1]<stamp)) return {status:"out_of_order"};
    const positions = (capital) => Object.fromEntries(Object.entries(state.target).map(([key,weight])=>[key,capital*weight/price(key)]));
    const iso = now.toISOString();
    const initializing = !state.quantities;
    if (initializing) {
      state.quantities = positions(state.capital);
      state.baselineAt = iso;
    }
    const values = () => Object.fromEntries(Object.entries(state.quantities).map(([key,qty])=>[key,qty*price(key)]));
    let byAsset = values();
    const value = Object.values(byAsset).reduce((sum,n)=>sum+n,0);
    const anchor = state.lastRebalance || state.baselineAt;
    const due = quarterlyDue(anchor);
    if (!initializing && assets.length && state.policy==="quarterly" && oldest>=due && oldest>=+now-30*MINUTE) {
      const updated = positions(value);
      const trades = Object.entries(updated).filter(([key])=>key!==CASH).map(([key,qty])=>
        ({symbol:key,quantity:qty-state.quantities[key],price:price(key)})).filter(row=>Math.abs(row.quantity*row.price)>.01);
      state.journal.push({at:iso,reason:"quarterly",trades});
      state.quantities = updated;
      state.lastRebalance = iso;
      byAsset = values();
    }
    const currentWeights = Object.fromEntries(Object.entries(byAsset).map(([key,amount])=>[key,amount/value]));
    state.latest = {
      value, currentWeights, mark, firstQuote:assets.length?new Date(oldest).toISOString():null,
      lastQuote:assets.length?new Date(newest).toISOString():null, source:market.source, feed:market.feed,
      updatedAt:iso,
    };
    state.history = [...state.history.slice(-119),{at:iso,value}];
    return {status:"ok", changed:true};
  }

  function unmount(){
    if(mounted)clearTimeout(mounted.timer);
    mounted=null;
  }

  function mount(host, state, api, onChange) {
    unmount();
    const view = {timer:null};
    mounted=view;
    const fr = window.RM.language==="fr";
    const tr = (en, french)=>fr?french:en;
    const currency = value=>new Intl.NumberFormat(fr?"fr-CH":"en-US",{style:"currency",currency:"USD"}).format(value);
    const percent = value=>new Intl.NumberFormat(fr?"fr-CH":"en-US",{style:"percent",maximumFractionDigits:2}).format(value);
    const time = iso=>new Date(iso).toLocaleString(fr?"fr-CH":"en-US");
    const symbols = Object.keys(state.target).filter(key=>key!==CASH);
    const unsupported = symbols.filter(key=>!symbolPattern.test(key));
    const article = document.createElement("article");
    article.innerHTML = `<h2>${tr("Paper portfolio tracking","Suivi du portefeuille simulé")}</h2>
      <p>${tr("Updates while My Matches is open. Prices may be delayed. Performance is based on price changes; dividends, corporate actions and transaction costs are excluded.","Actualisation quand Mes Matches est ouvert. Les cours peuvent être différés. La performance suit les variations de cours, hors dividendes, opérations sur titres et frais de transaction.")}</p>
      <label>${tr("Tracking rule","Règle de suivi")} <select>
        <option value="hold">${tr("Keep initial holdings","Conserver les positions")}</option>
        <option value="quarterly">${tr("Quarterly paper rebalancing","Rééquilibrage trimestriel simulé")}</option></select></label>
      <p class="muted">${tr("Quarterly rebalancing uses the first complete set of recent prices received after the due date and restores the target weights.","Le rééquilibrage trimestriel utilise le premier ensemble complet de cours récents reçu après l’échéance et rétablit les poids cibles.")}</p>`;
    const select=article.querySelector("select");
    select.value=state.policy;
    const refresh=document.createElement("button");
    refresh.type="button";
    refresh.textContent=tr("Refresh prices","Actualiser les cours");
    const status=document.createElement("p");
    status.setAttribute("role","status");
    const results=document.createElement("div");
    article.append(refresh,status,results);
    host.replaceChildren(article);

    function render() {
      const latest=state.latest;
      const subtitle=`<p>${tr("Confirmed","Confirmation")} · ${esc(time(state.confirmedAt))}${state.baselineAt?` · ${tr("Initial valuation","Valorisation de départ")} · ${esc(time(state.baselineAt))}`:""}</p>`;
      if (!latest) {
        results.innerHTML=subtitle+`<p>${tr("The first complete quote set establishes the initial positions.","Le premier ensemble complet de cours permet d’établir les positions initiales.")}</p>`;
        return;
      }
      const prices=new Map(latest.mark.map(([key,stamp,price])=>[key,{stamp,price}]));
      const quotes=latest.firstQuote?`<p>${esc(latest.source)} · ${esc(latest.feed)} · ${tr("Quote times","Horaires des cours")} · ${esc(time(latest.firstQuote))} → ${esc(time(latest.lastQuote))}</p>`:"";
      const older=latest.firstQuote&&Date.now()-Date.parse(latest.firstQuote)>30*MINUTE
        ? `<p>${tr("Some prices are older than 30 minutes, for example when the market is closed.","Certains cours datent de plus de 30 minutes, par exemple lorsque le marché est fermé.")}</p>`:"";
      const rows=Object.entries(latest.currentWeights).sort(([,a],[,b])=>b-a).map(([key,weight])=>
        `<tr><th>${esc(key===CASH?tr("USD cash","Liquidités USD"):key)}</th><td>${key===CASH?currency(state.quantities[key]):state.quantities[key].toFixed(5)}</td><td>${percent(state.target[key])}</td><td>${percent(weight)}</td><td>${((weight-state.target[key])*100).toFixed(2)} pp</td><td>${prices.has(key)?currency(prices.get(key).price)+" · "+esc(time(prices.get(key).stamp)):"—"}</td></tr>`).join("");
      let history="";
      if(state.history.length>1){
        history=`<details><summary>${tr("Recent valuations","Dernières valorisations")}</summary><ul>${state.history.slice(-20).reverse().map(row=>`<li>${esc(time(row.at))} · ${currency(row.value)}</li>`).join("")}</ul></details>`;
      }
      const journal=state.journal.length?`<details><summary>${tr("Rebalancing log","Journal des rééquilibrages")}</summary>
        ${state.journal.slice().reverse().map(row=>`<p>${esc(time(row.at))} · ${tr("Quarterly target weights","Retour trimestriel aux poids cibles")}</p><ul>${row.trades.map(trade=>`<li>${esc(trade.symbol)} · ${trade.quantity>0?"+":""}${trade.quantity.toFixed(5)} · ${currency(trade.price)}</li>`).join("")}</ul>`).join("")}</details>`:"";
      results.innerHTML=subtitle+`<p><strong>${currency(latest.value)}</strong> · ${tr("Since initial valuation","Depuis la valorisation de départ")} ${percent(latest.value/state.capital-1)}</p>
        ${quotes}${older}<div class="paper-tracking-table"><table><thead><tr><th>${tr("Holding","Actif")}</th><th>${tr("Quantity","Quantité")}</th><th>${tr("Target","Cible")}</th><th>${tr("Current","Actuel")}</th><th>${tr("Drift","Écart")}</th><th>${tr("Last price and time","Dernier cours et heure")}</th></tr></thead><tbody>${rows}</tbody></table></div>${history}${journal}`;
    }

    async function tick() {
      if(mounted!==view||refresh.disabled)return;
      clearTimeout(view.timer);
      refresh.disabled=true;
      const messages={
        not_configured:tr("Configure the Alpaca market-data credentials on the local server to start tracking.","Configure les identifiants Alpaca sur le serveur local pour activer le suivi."),
        provider_auth:tr("Alpaca refused access. Check the credentials and feed permissions.","Alpaca a refusé l’accès. Vérifie les identifiants et les droits sur le flux."),
        rate_limited:tr("The provider rate limit was reached. Try again in a minute.","La limite de requêtes du fournisseur est atteinte. Réessaie dans une minute."),
        provider_unavailable:tr("Quotes are temporarily unavailable.","Les cours sont temporairement indisponibles."),
        baseline_stale:tr("Some prices are too old to establish the starting portfolio.","Certains cours sont trop anciens pour établir le portefeuille de départ."),
        out_of_order:tr("The provider returned older quotes. The latest complete valuation was kept.","Le fournisseur a renvoyé des cours plus anciens. La dernière valorisation complète est conservée."),
      };
      try {
        if (unsupported.length) {
          status.textContent=tr("Unmapped holdings: ","Actifs sans symbole vérifié : ")+unsupported.join(", ");
          return;
        }
        const market=symbols.length?await api("paper/quotes",{symbols}):{status:"ok",quotes:{}};
        if(mounted!==view)return;
        const outcome=update(state,market);
        status.textContent=outcome.status==="ok"?"":outcome.status==="missing"
          ? tr("No usable price for: ","Cours exploitable indisponible pour : ")+outcome.missing.join(", ")
          : messages[outcome.status]||messages.provider_unavailable;
        if(outcome.changed){onChange();render();}
        if(symbols.length&&!["not_configured","provider_auth"].includes(outcome.status)){
          view.timer=setTimeout(tick,MINUTE);
        }
      } catch(error){
        if(mounted===view){
          status.textContent=error.message==="serverOutdated"
            ? tr("Restart the RiskMatch server to load the quote endpoint.","Relance le serveur RiskMatch pour activer l’API de cours.")
            : messages.provider_unavailable;
          if(error.message!=="serverOutdated")view.timer=setTimeout(tick,MINUTE);
        }
      } finally {
        refresh.disabled=false;
      }
    }

    select.onchange=()=>{state.policy=select.value;onChange();};
    refresh.onclick=tick;
    render();
    void tick();
  }

  window.PaperTracking={capture,update,mount,unmount};
})();
