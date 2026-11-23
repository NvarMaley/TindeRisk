// Portable research library. Asset history is loaded in blocks only on inspection.
const dataUrl = name => new URL("./data/" + name, import.meta.url);
const cache = new Map();
function load(name) {
  if (!cache.has(name)) {
    cache.set(name, fetch(dataUrl(name)).then(response => {
      if (!response.ok) throw new Error("Research file unavailable");
      return response.json();
    }).catch(error => { cache.delete(name); throw error; }));
  }
  return cache.get(name);
}
const node = (tag, cls, txt) => {
  const result = document.createElement(tag);
  if (cls) result.className = cls;
  if (txt !== undefined) result.textContent = txt;
  return result;
};
function button(label, action, cls = "lib-btn") {
  const b = node("button", cls, label);
  b.type = "button";
  b.addEventListener("click", action);
  return b;
}
function select(label, options, current, change) {
  const wrapper = node("label", "lib-field");
  wrapper.append(node("span", "", label));
  const element = node("select", "lib-input");
  for (const [val, title] of options) {
    const option = node("option", "", title);
    option.value = String(val);
    element.append(option);
  }
  element.value = String(current);
  element.onchange = () => change(element.value);
  wrapper.append(element);
  return wrapper;
}
function table(headers, rows) {
  const wrap = node("div", "lib-table-wrap");
  const table = node("table", "lib-table");
  const head = table.createTHead().insertRow();
  headers.forEach(title => {
    const th = node("th", "", title); th.scope = "col"; head.append(th);
  });
  const body = table.createTBody();
  for (const row of rows) {
    const tr = body.insertRow();
    row.forEach((data, i) => {
      const cell = node(i === 0 ? "th" : "td", "", data);
      if (i === 0) cell.scope = "row";
      tr.append(cell);
    });
  }
  wrap.append(table);
  return wrap;
}
const finite = Number.isFinite;
function fmt(x, digits = 1, signed = false) {
  if (!finite(x)) return "—";
  return (signed && x > 0 ? "+" : "") + new Intl.NumberFormat("en", {
    minimumFractionDigits: digits, maximumFractionDigits: digits
  }).format(x);
}
const percent = (x, signed = false) => finite(x) ? fmt(x, 1, signed) + "%" : "—";
const ratio = x => fmt(x, 2, true);
const small = msg => node("p", "lib-caption", msg);
function section(title, ...contents) {
  const area = node("section", "lib-block");
  area.append(node("h3", "", title), ...contents); return area;
}
function stat(name, value, hint) {
  const item = node("div", "lib-stat");
  item.append(node("span", "", name), node("strong", "", value), node("small", "", hint));
  return item;
}
const CLASSES = ["US stock", "Equity ETF", "Treasury ETF", "Gold ETF", "US Treasury"];
const FACTORS = [
  ["US equities", "SPY +1% in USD"], ["US dollar", "USD +1% in CHF"], ["Crude oil", "WTI +$10/barrel"],
  ["Long rates", "10-year yield +50 bp"], ["Yield curve", "10Y minus 2Y +25 bp"],
];
const SIGNALS = {vix:"VIX", curve:"Yield curve", unemployment:"US unemployment", gpr:"Geopolitical risk",
  tone:"Federal Reserve tone", realized:"Recent volatility", momentum:"Price momentum", liquidity:"Dollar volume"};
const LABELS = ["Return · 21 sessions", "Variance · 21 sessions", "Variance · 63 sessions"];
const periods = ["Latest year", "Prior year", "Full available history"];
const preferred = ["SPY", "AAPL", "IEF", "GLD", "XOM", "XLK"];
function plot(rows, cap = null) {
  const unbounded = Math.max(...rows.map(r => finite(r[1]) ? Math.abs(r[1]) : 0), .01);
  const maximum = cap || unbounded;
  const chart = node("div", "lib-bars");
  for (const [name, val, label] of rows) {
    const row = node("div", "lib-bar-row");
    const track = node("div", "lib-bar-track");
    track.setAttribute("aria-hidden", "true");
    if (finite(val)) {
      const bar = node("i", val < 0 ? "lib-bar-negative" : "lib-bar-positive");
      bar.style.width = Math.min(50, 50 * Math.abs(val) / maximum) + "%";
      track.append(bar);
    }
    row.append(node("span", "", name), track, node("b", "", label)); chart.append(row);
  }
  return chart;
}
function history(meta, row) {
  const cols = ["Window", "Months", "Mean/year", "Vol/year", "CAGR", "Worst drawdown"];
  const records = row.h.map((r,i) => [meta.years[i] + "Y", r ? r[0] + "/" + meta.years[i]*12 : "—",
    percent(r?.[1],true), percent(r?.[2]), percent(r?.[3],true), percent(r?.[4],true)]);
  return section("Returns across horizons",
    small("Monthly total returns in CHF to " + meta.date + ". The annual mean scales the arithmetic monthly mean by 12. CAGR measures compounded growth."),
    plot(row.h.map((r,i) => [meta.years[i] + " years · CAGR", r?.[3], percent(r?.[3],true)])), table(cols, records),
    small("Incomplete windows keep measured mean and volatility when available. CAGR and drawdown here require the complete series. A dash means unavailable."));
}
function relationships(meta, row) {
  const panel = node("div", "lib-stack");
  const results = node("div");
  const update = v => {
    const recent = Number(v) === 0;
    const values = row.f[Number(v)];
    results.replaceChildren(plot(values.map((r,i) => [FACTORS[i][1],r?.[0],percent(r?.[0],true)])),
      table(["Factor", "Shock impact", "95% interval", ...(recent ? ["Pearson", "Spearman"] : []), "Sessions"],
        values.map((r,i) => [FACTORS[i][0],percent(r?.[0],true),r ? percent(r[1],true) + " to " + percent(r[2],true) : "—",
          ...(recent ? [ratio(r?.[3]),ratio(r?.[4])] : []),r?.[5] ?? "—"])));
  };
  const factor = section("How this asset moved with the economy",
    small("Estimated change in the asset’s CHF return for each stated shock, holding the four other factors fixed. Confidence intervals reflect historical estimation uncertainty."),
    select("Estimation window", periods.map((name,i) => [i,name]),0,update),results,
    small("Latest and prior years use 252-session windows. Long history begins no earlier than October 2014. Five-lag Newey–West intervals are individual. Each estimate needs a sufficient joint history."));
  update(0);
  panel.append(factor, section("Correlation with reference assets",
    plot(row.p.map((r,i) => [meta.peers[i],r?.[0],ratio(r?.[0])]),1),
    table(["Reference", "Pearson", "Spearman", "Paired months"],row.p.map((r,i) =>
      [meta.peers[i],ratio(r?.[0]),ratio(r?.[1]),r?.[2] ?? "—"])),
    small("Three-year window in CHF, minimum 18 paired monthly returns. Pearson measures linear co-movement; Spearman compares ranks. SPY tracks US equities, IEF Treasury bonds and GLD gold.")));
  return panel;
}
function stress(meta, row) {
  const eventNames = Object.keys(meta.episodes);
  const crises = section("Historical crisis windows", small("Realized CHF returns across each dated event. Losses and recovery depend on the available daily path."),
    plot(row.c.map((r,i) => [eventNames[i],r?.[0],percent(r?.[0],true)])),
    table(["Event", "Window", "Total return", "Drawdown", "Recovery"],
      row.c.map((r,i) => [eventNames[i],meta.episodes[eventNames[i]].join(" to "),percent(r?.[0],true),percent(r?.[1],true),
        finite(r?.[2]) ? r[2] + " sessions" : r?.[3] || "—"])),
    small("Recovery is measured against the pre-event reference level with up to 252 follow-up sessions. A missing path stays unavailable."));
  const oil = section("Large daily moves in oil", small("Average CHF return on days when WTI moved at least $5 per barrel since 2020. The regime uses the prior 21 sessions of SPY volatility, with 20% annualized as the high-regime threshold."),
    table(["Prior regime", "WTI move", "Sessions", "Mean CHF return"],
      ["Normal", "Normal", "High", "High"].map((name,i) => [name,i%2 ? "Up ≥ $5" : "Down ≥ $5",row.tails?.[i]?.[0] ?? "—",percent(row.tails?.[i]?.[1],true)])),
    small("A mean requires five measured sessions. Historical conditional returns include all simultaneous market moves. Oil slope assessment across model variants · " + (row.oil || "Unestimated") + "."));
  const stack=node("div","lib-stack");stack.append(crises,oil);return stack;
}
function signals(meta, row) {
  const content = node("div");
  function update(v) {
    const target = Number(v);
    content.replaceChildren(table(["Signal", "Final paired windows", "Against reference"],
      row.s[target].map((r,i) => [SIGNALS[meta.signals[i]],r?.[0] ?? 0,
        !finite(r?.[1]) ? "Insufficient paired history" : r[1] > 0 ? "Lower error" : r[1] < 0 ? "Higher error" : "Equal within rounding"])));
  }
  update(0);
  const evidence = section("Signal evidence", small("Each signal was tested separately against this asset’s reference forecast on held-out periods. The label compares mean prediction error over at least eight final paired windows."),
    select("Prediction target",LABELS.map((name,i)=>[i,name]),0,update),content,
    small("All eight signals have zero allocation weight under the decision register. Historical error comparisons do not establish a current buy or sell signal."));
  const volatility=section("Volatility estimates at the study close",
    table(["Evaluation horizon", "Rolling 63-day estimate", "EWMA estimate", "Paired historical windows"],
      [21,63].map((days,i)=>[days+" sessions",percent(row.v?.[i]?.[0]),percent(row.v?.[i]?.[1]),row.v?.[i]?.[2]??"—"])),
    small("Both annualized estimates use the last 63 daily CHF returns, with ≥50 observations and the last session present. EWMA gives higher weight to recent moves (decay 0.94). Each horizon evaluates the same starting estimates against a different subsequent window."));
  const momentum=section("Momentum context",small(finite(row.z) ?
    "The 63-session USD momentum score was "+fmt(row.z,2,true)+" standard deviations relative to the preceding year. "+(row.z>=2?"It crossed the study’s +2 alert threshold.":"It stayed below the +2 alert threshold.")+" The threshold has no calibrated bubble probability." :
    "A momentum score requires a complete last 63 sessions and sufficient prior history; this case has no measured score."));
  const stack=node("div","lib-stack");stack.append(evidence,volatility,momentum);return stack;
}
function extra(meta, row) {
  const out = node("div", "lib-stack");
  if (row.bond) {
    const b = row.bond;
    out.append(section("Bond terms", table(["Measure", "Value"], [
      ["Annual coupon",percent(b.coupon_pct)],["Maturity",b.maturity],["Next coupon at study date",b.next_coupon || "—"],
      ["Modified duration",finite(b.duration) ? fmt(b.duration,2)+" years" : "—"],
      ["DV01 per USD 100 face", finite(b.dv01_per_100) ? "USD "+fmt(b.dv01_per_100,4) : "—"]])));
  }
  const env = row.env;
  out.append(section("Environmental coverage",
    small("Issuer and facility review dated " + meta.environmentDate + ". This is a later review than the market study."),
    table(["Measure","Value"],[
      ["Measured point-source exposure",percent(env?.measured)],["Unresolved issuer exposure",percent(env?.unknownIssuer)],
      ["Intensity of covered exposure",finite(env?.intensity)?fmt(env.intensity,1)+" tCO₂e / USD million revenue":"—"]]),
    small("US EPA point-source facilities are only a subset of company-wide emissions. Missing coverage cannot establish that an asset meets a green mandate.")));
  return out;
}

export async function renderLibrary(container, {back} = {}) {
  if (!document.querySelector('link[data-rm-library]')) {
    const css = document.createElement("link"); css.rel = "stylesheet"; css.dataset.rmLibrary = "";
    css.href = new URL("./library.css", import.meta.url); document.head.append(css);
  }
  const shell = node("main", "rm-library");
  container.replaceChildren(shell);
  const toolbar = node("nav","lib-nav");
  if (typeof back === "function") toolbar.append(button("Back to profile", back, "lib-back"));
  const status = node("span","lib-date","Loading library…"); toolbar.append(status);
  const body = node("div","lib-body");
  shell.append(toolbar, body);
  let meta;
  try { meta = await load("library.json"); }
  catch { body.append(node("h2","","Library unavailable"), button("Try again",()=>renderLibrary(container,{back})));return; }
  if (!container.contains(shell)) return;
  status.textContent = "Research close   /   " + meta.date;
  let query = "", group = "", scope = "", page = 0, current = -1;
  const pageSize = 20;
  const priority = i => { const k = preferred.indexOf(meta.assets[i][0]); return k < 0 ? 99 : k; };
  const all = meta.assets.map((_,i)=>i).sort((a,b)=>priority(a)-priority(b) || a-b);
  function listing() {
    current=-1; const top=node("header","lib-title");
    top.append(node("h1","","Asset library"),small("Explore the history, risk and macro exposure of " + meta.assets.length.toLocaleString("en") + " US instruments."));
    const filters=node("div","lib-filters");
    const search=node("label","lib-field lib-search"); search.append(node("span","","Search"));
    const input=node("input","lib-input");input.type="search";input.placeholder="Ticker, issuer or Treasury issue";input.value=query;
    function reset() {page=0;listRows();}
    input.addEventListener("input",()=>{query=input.value;reset();});search.append(input);
    filters.append(search,select("Asset class",[["","All classes"],...CLASSES.map((c,i)=>[i,c])],group,v=>{group=v;reset();}),
      select("Eligibility",[["","All instruments"],["eligible","Model eligible"],["blocked","Outside model"]],scope,v=>{scope=v;reset();}));
    const list=node("div","lib-results");
    function listRows() {
      const txt=query.toLowerCase().trim();
      const ids=all.filter(i=>{const a=meta.assets[i]; return (group==="" || Number(group)===a[2]) &&
        (scope==="" || a[3]===(scope==="eligible")) && (!txt || (a[0]+" "+a[1]).toLowerCase().includes(txt));});
      const start=page*pageSize;
      const bar=node("div","lib-result-line");
      bar.append(node("b","",ids.length.toLocaleString("en")+" instruments"),
        node("span","", ids.length ? (start+1)+"–"+Math.min(start+pageSize,ids.length) : "0 results"));
      list.replaceChildren(bar);
      if (!ids.length) {list.append(small("No matching assets. Try another ticker or adjust the filters."));return;}
      for (const i of ids.slice(start,start+pageSize)) {
        const a=meta.assets[i], ok=a[3], btn=button("",()=>detail(i),"lib-asset");
        btn.setAttribute("aria-label","Inspect " + a[0] + " · " + a[1]);
        const name=node("span","lib-asset-main");
        name.append(node("strong","lib-symbol",a[0]),node("span","lib-company",a[1]));
        const kind=node("span","lib-asset-detail");kind.append(node("span","",CLASSES[a[2]]),node("small","",ok?"Model eligible":"Outside model"));
        const values=node("span","lib-asset-detail lib-num");values.append(node("span","",percent(a[5])),node("small","","1Y volatility"));
        btn.append(name,kind,values); list.append(btn);
      }
      const pager=node("div","lib-pager");
      const prev=button("Previous",()=>{page--;listRows();list.scrollIntoView({block:"start"});});
      const next=button("Next",()=>{page++;listRows();list.scrollIntoView({block:"start"});});
      prev.disabled=page===0;next.disabled=start+pageSize>=ids.length;
      pager.append(prev,node("span","", "Page "+(page+1)+" of "+Math.ceil(ids.length/pageSize)),next);
      list.append(pager);
    }
    body.replaceChildren(top,filters,list);listRows();
  }
  async function detail(i) {
    current=i; const a=meta.assets[i];
    const backList=button("Back to assets",()=>{listing();},"lib-back");
    const top=node("header","lib-asset-title");
    top.append(node("span","lib-kind",CLASSES[a[2]]),node("h1","",a[0]),node("h2","",a[1]));
    const pane=node("div","lib-data-pane");pane.append(small("Opening asset sheet…"));
    body.replaceChildren(backList,top,pane);
    shell.scrollIntoView({block:"start"});
    let r;
    try {
      const chunk=await load("library-"+String(Math.floor(i/meta.batch)).padStart(2,"0")+".json");
      r=chunk[i%meta.batch]; if (!r) throw new Error("Missing asset");
    } catch {
      if (current===i) pane.replaceChildren(small("This asset sheet could not be loaded."),button("Retry",()=>detail(i)));
      return;
    }
    if (current!==i || !container.contains(shell)) return;
    const metrics=node("div","lib-stats");
    const h=r.h[0];
    metrics.append(stat("Annual mean return",percent(h?.[1],true),"1Y window · CHF"),
      stat("Annual volatility",percent(h?.[2]),"1Y window · CHF"),
      stat("Worst drawdown",percent(h?.[4],true),"1Y window · CHF"));
    const note=small((a[3]?"Eligible for the dated research model.":"Outside the dated research model · "+r.reason+".")+" Current broker availability and executable quotes are unverified.");
    const nav=node("div","lib-tabs");nav.setAttribute("aria-label","Asset sheet sections");
    const area=node("div","lib-sheet");
    const tabs=[["History",history],["Relationships",relationships],["Crises",stress],["Signals",signals],["Details",extra]];
    const activate=index=>{
      [...nav.children].forEach((b,k)=>b.setAttribute("aria-pressed",String(k===index)));
      area.replaceChildren(tabs[index][1](meta,r));
    };
    tabs.forEach(([label],k)=>nav.append(button(label,()=>activate(k),"lib-tab")));
    pane.replaceChildren(metrics,note,nav,area);activate(0);
  }
  listing();
}
