import {
  root,
  state,
  nav,
  api,
  shell,
  run,
  bind,
  swipes,
  tiles,
  tileBar,
  esc,
  fmt,
  pct,
  chf,
  toast,
} from "./studio-core.js";

const names = () => Object.fromEntries(state.plans.map((p) => [p.id, p.name]));
const textList = (arr) =>
  "<ul>" + arr.map((s) => "<li>" + esc(s) + "</li>").join("") + "</ul>";
const rows = (values, format) =>
  Object.entries(values || {})
    .map(
      ([k, v]) =>
        '<div class="budget-line"><span>' +
        esc(k) +
        "</span><b>" +
        esc(format(v)) +
        "</b></div>",
    )
    .join("");
const section = (label, body) =>
  '<details class="info"><summary>' +
  esc(label) +
  "</summary>" +
  body +
  "</details>";
const riskBand = () =>
  state.profile.high == null
    ? pct(state.profile.low) + " and above"
    : pct(state.profile.low) + " – " + pct(state.profile.high);
function evidence(p) {
  const env = p.esg;
  const ranges = p.estimated_return_range.map(pct).join(" – ");
  return (
    '<div class="panel"><h3>What works for you</h3>' +
    textList(p.strengths) +
    "<h3>Where it can hurt</h3>" +
    textList(p.risks) +
    "</div>" +
    section(
      "Allocation & largest positions",
      tileBar(p.weights) +
        rows(
          Object.fromEntries(
            p.top.map((s) => [s.symbol + " · " + s.name, s.weight]),
          ),
          pct,
        ),
    ) +
    section(
      "Goal, model sensitivity & cost",
      tiles([
        ["Historical model range", ranges],
        ["Dated goal estimate", chf(p.goal_value_chf)],
        ["Goal shortfall", chf(p.goal_gap_chf)],
        ["One-time cost", chf(p.fee_chf)],
      ]),
    ) +
    section(
      "Correlations & shocks",
      rows(p.correlations, (v) => v.toFixed(2)) +
        rows(p.scenarios, chf) +
        '<p class="muted">Scenario changes in CHF. Each shock is a separate historical or conditional exercise.</p>',
    ) +
    section(
      "Environmental evidence",
      "<p>" +
        esc(env.label) +
        "</p>" +
        tiles([
          ["Covered share", pct(env.coverage)],
          [
            "Intensity",
            Number.isFinite(env.intensity)
              ? env.intensity.toFixed(2)
              : "Unavailable",
          ],
          ["Reviewed", env.as_of],
        ]) +
        "<small>" +
        esc(env.unit) +
        "</small>",
    ) +
    section(
      "Five signal readings",
      p.signals
        .map(
          (s) =>
            '<div class="listrow"><strong>' +
            esc(s.family) +
            "</strong><p>" +
            esc(s.reading) +
            "</p><small>Recommendation weight " +
            pct(s.weight) +
            "</small></div>",
        )
        .join(""),
    ) +
    section(
      "Comparison score",
      rows(p.subscores, (v) => v.toFixed(1) + " / 100") +
        "<small>" +
        esc(p.score_label) +
        "</small>",
    )
  );
}
let calculation = 0;
export async function calculate() {
  if (state.profile.blocked_reason) {
    nav.profile();
    toast(state.profile.blocked_reason);
    return;
  }
  const request = ++calculation;
  shell(
    "matches",
    '<div class="reveal" id="solving"><div class="pulse-heart">♥</div><h1>Finding your matches.</h1><p class="lede">Checking whole positions against your risk range, cash and loss budget.</p><div class="error" role="alert"></div></div>',
  );
  const surface = root.querySelector("#solving");
  const result = await api("candidates");
  if (request !== calculation || !surface.isConnected) return;
  Object.assign(state, {
    plans: result.plans,
    day: result.day,
    revision: result.revision,
    kept: [],
    seen: [],
    index: 0,
    draft: null,
    preview: null,
  });
  showMatches();
}
function shortList() {
  return (
    '<aside class="panel saved"><p class="kicker">Shortlist</p><h2>Your picks.</h2>' +
    (state.kept.length
      ? state.kept
          .map(
            (k) =>
              '<div class="budget-line"><span>' +
              esc(names()[k]) +
              '</span><button class="flat remove" data-key="' +
              esc(k) +
              '" aria-label="Remove ' +
              esc(names()[k]) +
              '">×</button></div>',
          )
          .join("")
      : '<p class="muted">Keep a card to add it here.</p>') +
    '<button class="primary" id="compose" ' +
    (state.kept.length ? "" : "disabled") +
    '>Compose my match</button><button class="flat" id="restart">Review all cards</button></aside>'
  );
}
function shortlistControls() {
  bind("#compose", compose);
  bind("#restart", () => {
    state.index = 0;
    state.seen = [];
    showMatches();
  });
  root.querySelectorAll(".remove").forEach(
    (b) =>
      (b.onclick = () => {
        state.kept = state.kept.filter((k) => k !== b.dataset.key);
        showMatches();
      }),
  );
}
export function showMatches() {
  const plans = state.plans;
  const i = state.index,
    p = plans[i];
  const tabs =
    '<div class="reel" aria-label="Choose a strategy">' +
    plans
      .map(
        (q, j) =>
          '<button class="flat" data-card="' +
          j +
          '" aria-pressed="' +
          (i === j) +
          '">' +
          esc(q.name) +
          (state.kept.includes(q.id) ? " ♥" : "") +
          "</button>",
      )
      .join("") +
    "</div>";
  const art = {
    return: "a",
    robust: "b",
    diversified: "c",
    defensive: "b",
    reference: "c",
    carbon: "a",
  };
  const card = p
    ? '<div class="swipepad"><article class="swipe-card candidate" tabindex="0" aria-label="' +
      esc(p.name) +
      '"><div class="art ' +
      (art[p.id] || "a") +
      '"></div><span class="swipe-mark" aria-hidden="true"></span><div class="card-body"><p class="kicker">Portfolio ' +
      (i + 1) +
      " / " +
      plans.length +
      " · " +
      esc(state.day) +
      "</p><h1>" +
      esc(p.name) +
      '</h1><p class="lede">' +
      esc(p.subtitle) +
      '</p><div class="chips"><span class="pill">' +
      (p.valid ? "Match score " + p.score + " / 100" : "Outside mandate") +
      '</span><span class="pill">' +
      fmt(p.positions) +
      " holdings</span></div></div></article></div>" +
      tiles([
        ["Modeled annual return, net", pct(p.net)],
        ["Modeled annual volatility", pct(p.vol)],
        ["Your inferred band", riskBand()],
      ]) +
      (p.valid ? "" : '<p class="warning">' + esc(p.reason) + "</p>") +
      '<div class="swipe-buttons"><button data-vote="no"><b>×</b> Pass</button><button data-vote="yes" class="like" ' +
      (p.valid ? "" : "disabled") +
      '><b>♥</b> Keep</button></div><p class="muted">Return and volatility are historical estimates. Swipe the card or use the buttons.</p>' +
      evidence(p)
    : '<div class="reveal"><p class="kicker">Deck complete</p><h1>' +
      (state.kept.length ? "Your shortlist is ready." : "No cards kept.") +
      '</h1><p class="lede">' +
      (state.kept.length
        ? "Choose how to combine your picks."
        : "Review the strategies or edit your brief in Profile.") +
      "</p></div>";
  shell(
    "matches",
    '<p class="kicker">Portfolio studio</p><h2>Your contenders.</h2>' +
      tabs +
      '<div class="match-grid"><div>' +
      card +
      "</div>" +
      shortList() +
      "</div>",
  );
  shortlistControls();
  root.querySelectorAll("[data-card]").forEach(
    (b) =>
      (b.onclick = () => {
        state.index = Number(b.dataset.card);
        showMatches();
      }),
  );
  if (p)
    swipes(root.querySelector(".candidate"), async (vote) => {
      if (vote === "yes" && !p.valid) {
        toast(p.reason);
        return;
      }
      state.kept = state.kept.filter((id) => id !== p.id);
      if (vote === "yes") state.kept.push(p.id);
      state.seen = [...new Set([...(state.seen || []), p.id])];
      const next = plans.findIndex(
        (q, j) => j > i && !state.seen.includes(q.id),
      );
      const first =
        next >= 0 ? next : plans.findIndex((q) => !state.seen.includes(q.id));
      state.index = first < 0 ? plans.length : first;
      showMatches();
    });
}
function compose() {
  const ids = [...state.kept],
    n = ids.length,
    even = Math.floor(100 / n);
  shell(
    "matches",
    '<div class="sweep"><p class="kicker">Your shortlist</p><h1>Mix your match.</h1><p class="lede">' +
      (n === 1
        ? "Your selected strategy will be checked once more before booking."
        : "Choose the percentages or let the model search for the highest net return per unit of risk on its 10% grid.") +
      '</p><div class="panel" id="parts">' +
      ids
        .map(
          (k, i) =>
            '<label class="mixrow"><span>' +
            esc(names()[k]) +
            '</span><input type="range" aria-label="' +
            esc(names()[k]) +
            ' slider" min="0" max="100" value="' +
            (i === n - 1 ? 100 - even * i : even) +
            '" ' +
            (n === 1 ? "disabled" : "") +
            '><input type="number" aria-label="' +
            esc(names()[k]) +
            ' percent" min="0" max="100" step="1" value="' +
            (i === n - 1 ? 100 - even * i : even) +
            '" ' +
            (n === 1 ? "readonly" : "") +
            "><b>%</b></label>",
        )
        .join("") +
      '<div class="budget-line"><span>Total</span><b id="total">100%</b></div></div><div class="actions"><button class="primary" id="manual">' +
      (n === 1 ? "Preview my match" : "Preview my weights") +
      "</button>" +
      (n > 1
        ? '<button class="secondary" id="auto">Suggest weights</button>'
        : "") +
      '<button class="flat" id="backdeck">Back to cards</button></div><div class="error" role="alert"></div><div id="mixpreview"></div></div>',
  );
  const controls = [...root.querySelectorAll(".mixrow")];
  const weights = () =>
    Object.fromEntries(
      controls.map((r, i) => [
        ids[i],
        r.querySelector("[type=number]").valueAsNumber / 100,
      ]),
    );
  let sequence = 0;
  function changed() {
    sequence++;
    root.querySelector("#mixpreview").innerHTML = "";
    root.querySelector("#total").textContent =
      Number(
        (Object.values(weights()).reduce((a, b) => a + b, 0) * 100).toFixed(4),
      ) + "%";
  }
  controls.forEach((r) => {
    const [a, b] = r.querySelectorAll("input");
    a.oninput = () => {
      b.value = a.value;
      changed();
    };
    b.oninput = () => {
      a.value = b.value;
      changed();
    };
  });
  async function preview(suggested) {
    const mine = ++sequence,
      w = suggested ? null : weights(),
      target = root.querySelector("#mixpreview");
    if (
      w &&
      (Object.values(w).some((x) => !Number.isFinite(x) || x < 0 || x > 1) ||
        Math.abs(Object.values(w).reduce((a, b) => a + b, 0) - 1) > 1e-8)
    )
      throw Error("Set percentages between 0 and 100 that add up to 100%.");
    const payload = { ids, weights: w, revision: state.revision },
      result = await api("blend", payload);
    if (mine !== sequence || !target.isConnected) return;
    const p = result.plan;
    if (suggested && p.valid) {
      controls.forEach((r, i) =>
        r
          .querySelectorAll("input")
          .forEach(
            (input) => (input.value = Math.round(100 * p.parts[ids[i]])),
          ),
      );
      root.querySelector("#total").textContent = "100%";
    }
    target.innerHTML =
      '<div class="panel"><h2>' +
      esc(p.valid ? "Your combined portfolio" : "Outside your mandate") +
      "</h2>" +
      rows(
        Object.fromEntries(ids.map((k) => [names()[k], p.parts[k] || 0])),
        pct,
      ) +
      tiles([
        ["Modeled annual return", pct(p.net)],
        ["Annual volatility", pct(p.vol)],
        ["Trading cost", chf(p.fee_chf)],
      ]) +
      (p.valid
        ? '<button class="primary" id="draft">Review this match</button>'
        : '<p class="warning">' + esc(p.reason) + "</p>") +
      "</div>" +
      evidence(p);
    bind("#draft", async () => {
      const d = await api("draft", payload);
      if (!d.draft) throw Error(d.plan.reason);
      state.revision = d.revision;
      review(d);
    });
    target.scrollIntoView({ block: "start" });
  }
  bind("#manual", () => preview(false));
  bind("#auto", () => preview(true));
  bind("#backdeck", showMatches);
}
function review(d) {
  shell(
    "matches",
    '<div class="sweep"><p class="kicker">Final review · simulation</p><h1>Make it a match?</h1><p class="lede">Confirm to book these whole positions and the trading cost in your fictional CHF account.</p>' +
      tiles([
        ["Investable sleeve", chf(d.plan.capital_chf)],
        ["One-time fee", chf(d.plan.fee_chf)],
        ["Positions", fmt(d.plan.positions)],
        ["Protected outside account", chf(d.plan.reserve_chf)],
      ]) +
      tileBar(d.plan.weights) +
      '<div class="actions"><button class="primary" id="confirm">♥ Confirm my match</button><button class="flat" id="cancel">Cancel draft</button></div><div class="error" role="alert"></div></div>',
  );
  bind("#cancel", async () => {
    await api("cancel", { draft: d.draft });
    compose();
  });
  bind("#confirm", async () => {
    const result = await api("confirm", { draft: d.draft });
    state.funded = true;
    state.plans = [];
    state.kept = [];
    shell(
      "tracking",
      '<div class="reveal animated"><div class="matchheart">♥</div><p class="kicker">Portfolio ' +
        result.version +
        ' · simulated</p><h1>It’s a match.</h1><p class="lede">' +
        fmt(result.tracking.positions) +
        " positions · " +
        chf(result.tracking.value) +
        '</p><button id="openbook" class="primary">View my portfolio</button></div>',
    );
    bind("#openbook", () => tracking(result.tracking));
  });
}
function chart(history, key, timeline = "by simulated close") {
  const data = history.map((h) => h[key]),
    format = key === "value" ? chf : pct;
  let lo = Math.min(...data),
    hi = Math.max(...data);
  const pad = (hi - lo) * 0.1 || Math.max(0.001, Math.abs(hi) * 0.005);
  lo -= pad;
  hi += pad;
  const pts = data.map((v, i) => [
    40 + (data.length > 1 ? (i / (data.length - 1)) * 515 : 0),
    132 - ((v - lo) / (hi - lo)) * 110,
  ]);
  return (
    '<svg role="img" aria-label="' +
    esc(
      (key === "value" ? "Account value" : "Flow-neutral return") +
        " " +
        timeline +
        ", " +
        format(data[0]) +
        " to " +
        format(data.at(-1)),
    ) +
    '" viewBox="0 0 600 162"><path d="M40 20 V136 H555" fill="none" stroke="#685474"/><polyline fill="none" stroke="#ff9bc5" stroke-width="4" points="' +
    pts.map((a) => a.join(",")).join(" ") +
    '"/>' +
    pts
      .map(
        ([x, y], i) =>
          '<circle cx="' +
          x +
          '" cy="' +
          y +
          '" r="5" fill="#9aeafd"><title>' +
          esc(history[i].day + " · " + format(data[i])) +
          "</title></circle>",
      )
      .join("") +
    '</svg><div class="spread"><small>' +
    esc(history[0].day) +
    "</small><small>" +
    esc(history.at(-1).day) +
    "</small></div>"
  );
}
function liveText(q, samples) {
  if (!q.live) {
    samples.length = 0;
    return (
      "<p>" +
      esc(q.reason) +
      "</p><small>Showing the simulated ledger at its dated close.</small>"
    );
  }
  const last = samples.at(-1);
  if (last && last.source !== q.source) samples.length = 0;
  if (!samples.length || samples.at(-1).at !== q.oldest_at) {
    samples.push({
      at: q.oldest_at,
      source: q.source,
      day: q.oldest_at.slice(11, 19) + " UTC",
      value: q.value,
    });
    if (samples.length > 240) samples.shift();
  } else {
    samples.at(-1).value = q.value;
  }
  const change =
    samples.length > 1 && samples[0].value > 0
      ? pct(q.value / samples[0].value - 1)
      : "Awaiting next quote";
  return (
    "<strong>" +
    chf(q.value) +
    "</strong><p>" +
    esc(q.source) +
    " · oldest contributing quote " +
    esc(q.oldest_at) +
    "</p>" +
    chart(samples, "value", "from observed live quotes") +
    "<small>Change over displayed observations · " +
    change +
    "</small>"
  );
}
export async function showTracking() {
  const a = await api("tracking");
  if (!a) {
    toast("Confirm a match to open the portfolio.");
    return;
  }
  tracking(a);
}
function tracking(a) {
  const last = a.history.at(-1);
  const samples = [];
  shell(
    "tracking",
    '<p class="kicker">Your match · simulated close ' +
      esc(a.day) +
      "</p><h1>Your portfolio.</h1>" +
      tiles([
        ["Invested account value", chf(a.value)],
        ["Flow-neutral return", pct(last.twr)],
        ["Drawdown", pct(last.drawdown)],
        ["Cash in account", chf(a.cash)],
      ]) +
      '<div class="match-grid"><div><div class="panel"><div class="spread"><h2>Performance.</h2><select id="series" aria-label="Chart series"><option value="value">Account value</option><option value="twr">Flow-neutral return</option></select></div><div id="chart">' +
      chart(a.history, "value") +
      "</div>" +
      section(
        "Values by close",
        a.history
          .map(
            (h) =>
              '<div class="listrow"><b>' +
              esc(h.day) +
              "</b><span>" +
              chf(h.value) +
              " · return " +
              pct(h.twr) +
              " · cash flow " +
              chf(h.flow_chf) +
              "</span></div>",
          )
          .join(""),
      ) +
      "</div>" +
      '<div class="panel"><h2>Positions.</h2>' +
      section(
        "All " + a.positions + " held securities",
        a.composition
          .map(
            (h) =>
              '<div class="budget-line"><span>' +
              esc(h.symbol) +
              " · " +
              fmt(h.units) +
              " units</span><b>" +
              chf(h.value) +
              " · " +
              pct(h.weight) +
              "</b></div>",
          )
          .join("") || "<p>CHF cash only</p>",
      ) +
      section(
        "Strategy shares at booking",
        rows(
          Object.fromEntries(
            Object.entries(a.parts).map(([k, v]) => [names()[k] || k, v]),
          ),
          pct,
        ),
      ) +
      "</div></div>" +
      '<aside><div class="panel"><p class="kicker">Market monitor</p><h2>Live valuation.</h2><div id="live">' +
      liveText(a.live_quote, samples) +
      '</div><small>Feed checked every 15 seconds while visible.</small></div><div class="panel"><h3>Account controls</h3><p class="muted">' +
      chf(a.reserve_chf) +
      ' held outside the account.</p><div class="actions">' +
      (a.next
        ? '<button class="secondary" id="advance">Simulate ' +
          esc(a.next) +
          "</button>"
        : '<span class="pill">Final recorded close</span>') +
      '<button class="flat" id="recalc">Recalculate strategies</button></div>' +
      section(
        "Record a simulated cash flow",
        '<form id="flow"><label class="field">Direction<select name="direction"><option value="deposit">Deposit</option><option value="withdrawal">Withdrawal</option></select></label><label class="field">Amount in CHF<input required name="amount" min=".01" step=".01" type="number"></label><button class="secondary">Record flow</button></form>',
      ) +
      '</div></aside></div><div class="error" role="alert"></div>',
  );
  root.querySelector("#series").onchange = (e) =>
    (root.querySelector("#chart").innerHTML = chart(a.history, e.target.value));
  bind("#advance", async () => {
    const result = await api("advance", { day: a.day });
    state.plans = [];
    tracking(result);
  });
  bind("#recalc", calculate);
  const f = root.querySelector("#flow");
  let event = crypto.randomUUID();
  f.oninput = () => {
    event = crypto.randomUUID();
  };
  f.onsubmit = (e) => {
    e.preventDefault();
    run(f.querySelector("button"), async () => {
      const result = await api("flow", {
        ...Object.fromEntries(new FormData(f)),
        event,
        day: a.day,
      });
      state.plans = [];
      tracking(result);
    });
  };
  const live = root.querySelector("#live");
  let busy = false;
  const timer = setInterval(async () => {
    if (!live.isConnected) {
      clearInterval(timer);
      return;
    }
    if (document.hidden || busy) return;
    busy = true;
    try {
      const fresh = await api("tracking");
      if (live.isConnected && fresh) {
        if (
          fresh.day !== a.day ||
          fresh.version !== a.version ||
          fresh.value !== a.value
        ) {
          state.plans = [];
          tracking(fresh);
        } else live.innerHTML = liveText(fresh.live_quote, samples);
      }
    } catch {
      if (live.isConnected) live.textContent = "Feed check unavailable.";
    } finally {
      busy = false;
    }
  }, 15000);
}
