const assets = [
  { label: "US equities", color: "#f87eb8", expected: 8.6, volatility: 18 },
  { label: "US bonds", color: "#79ceff", expected: 3.2, volatility: 6 },
  { label: "Gold", color: "#bc9aff", expected: 4.8, volatility: 14 },
  { label: "CHF cash", color: "#716487", expected: 1, volatility: 0 },
];
const correlations = [
  [1, .15, .18, 0],
  [.15, 1, .05, 0],
  [.18, .05, 1, 0],
  [0, 0, 0, 1],
];
const portfolios = [
  { title: "Biscayne", tone: "cyan", style: "Stability", description: "A larger allocation to bonds and cash.", weights: [20, 55, 10, 15] },
  { title: "Ocean Drive", tone: "pink", style: "Balanced", description: "A mix of equities, bonds and gold.", weights: [47, 33, 15, 5] },
  { title: "Skyline", tone: "violet", style: "Growth", description: "Greater exposure to equities.", weights: [75, 15, 7, 3] },
];
const questions = [
  "I would accept temporary losses in pursuit of a higher return.",
  "I prefer to keep some of my investment available in the short term.",
  "Avoiding a large exposure to any one sector is important to me.",
];
const fee = .2;
const cashRate = 1;
const storage = "riskmatch-v2-demo-match";
const modal = document.querySelector("#modal");
const content = document.querySelector("#modal-content");
const profile = document.querySelector("#questionnaire");

function summary(weights) {
  const shares = weights.map(value => value / 100);
  const net = shares.reduce((sum, share, i) => sum + share * assets[i].expected, -fee);
  const variance = shares.reduce((sum, share, i) => sum + shares.reduce(
    (row, other, j) => row + share * other * assets[i].volatility * assets[j].volatility * correlations[i][j], 0,
  ), 0);
  const risk = Math.sqrt(variance);
  const riskBalance = Math.max(0, 100 - Math.abs(9 - risk) * 8);
  const diversification = Math.min(100, (1 - shares.reduce((sum, value) => sum + value ** 2, 0)) * 135);
  const returnPotential = Math.min(100, net * 14);
  const subscores = [riskBalance, diversification, returnPotential].map(Math.round);
  const score = Math.round(.45 * subscores[0] + .3 * subscores[1] + .25 * subscores[2]);
  return {net, risk, score, subscores, sharpe: risk > 1e-8 ? (net - cashRate) / risk : -Infinity};
}

function blendWeights(parts) {
  return assets.map((_, j) => parts.reduce((sum, part, i) => sum + part * portfolios[i].weights[j] / 100, 0));
}

function highestSharpe(indices) {
  let best = null;
  let bestRatio = -Infinity;
  for (let first = 0; first <= 100; first += 5) {
    for (let second = 0; second <= 100 - first; second += 5) {
      const parts = [first, second, 100 - first - second];
      const honoursChoice = parts.every((part, i) => indices.includes(i) ? part > 0 : part === 0);
      if (!honoursChoice) continue;
      const ratio = summary(blendWeights(parts)).sharpe;
      if (ratio > bestRatio) {
        bestRatio = ratio;
        best = parts;
      }
    }
  }
  return best;
}

const format = new Intl.NumberFormat("en-CH", {maximumFractionDigits: 1});
const percent = value => `${format.format(value)} %`;
const funds = new Intl.NumberFormat("en-CH", {style: "currency", currency: "CHF", maximumFractionDigits: 0});

function metrics(weights) {
  const {net, risk, score} = summary(weights);
  return `<dl class="metrics">
    <div><dt>Estimated return</dt><dd>${percent(net)}</dd></div>
    <div><dt>Volatility</dt><dd>${percent(risk)}</dd></div>
    <div><dt>Demo score</dt><dd><strong>${score}</strong> / 100</dd></div>
  </dl>`;
}

function allocation(weights) {
  let start = 0;
  const stops = assets.map((asset, i) => {
    const previous = start;
    start += weights[i];
    return `${asset.color} ${previous}% ${start}%`;
  });
  return `<div class="allocation">
    <div class="donut" aria-hidden="true" style="background:conic-gradient(${stops.join(",")})"></div>
    <ul class="legend">${assets.map((asset, i) =>
      `<li><span><i style="background:${asset.color}" aria-hidden="true"></i>${asset.label}</span><b>${percent(weights[i])}</b></li>`,
    ).join("")}</ul>
  </div>`;
}

function scoreBreakdown(weights) {
  const labels = ["Risk", "Diversification", "Return"];
  return summary(weights).subscores.map((value, i) => `<div class="score-row"><span>${labels[i]}</span><span class="bar" aria-hidden="true"><span style="width:${value}%"></span></span><b>${value}</b></div>`).join("");
}

function drawCards() {
  document.querySelector("#portfolio-cards").innerHTML = portfolios.map((portfolio, i) => `<article class="card" data-tone="${portfolio.tone}">
    <div class="card-top"><span class="card-index">${portfolio.style}</span><h3>${portfolio.title}</h3><p>${portfolio.description}</p></div>
    <div class="card-body">${metrics(portfolio.weights)}<button type="button" class="button outline" data-portfolio="${i}" aria-label="View ${portfolio.title}">View portfolio</button></div>
  </article>`).join("");
}

function showModal(markup) {
  content.innerHTML = markup;
  if (!modal.open) modal.showModal();
  modal.scrollTop = 0;
}

function showPortfolio(index) {
  const {title, description, weights, style} = portfolios[index];
  showModal(`<p class="eyebrow">${style.toUpperCase()}</p><h2 id="modal-title">${title}</h2><p>${description}</p>${metrics(weights)}
    <h3>Composition</h3>${allocation(weights)}<h3>Demo score breakdown</h3>${scoreBreakdown(weights)}
    <div class="actions"><button class="button primary" id="choose" type="button">Choose this portfolio</button>
      <button class="button outline" id="blend-this" type="button">Include in a blend</button></div>`);
  content.querySelector("#choose").addEventListener("click", () => confirmChoice(title, weights));
  content.querySelector("#blend-this").addEventListener("click", () => showComposer(index));
}

function showComposer(selected = 0) {
  const other = (selected + 1) % portfolios.length;
  const initial = portfolios.map((_, i) => i === selected ? 60 : i === other ? 40 : 0);
  showModal(`<p class="eyebrow">YOUR ALLOCATION</p><h2 id="modal-title">Build an allocation</h2>
    <p>Enter weights that add up to 100%. The blend is recalculated from the combined holdings.</p>
    ${portfolios.map((portfolio, i) => `<div class="weight" data-part="${i}"><label for="part-${i}">${portfolio.title}</label>
      <input type="range" min="0" max="100" value="${initial[i]}" aria-label="Weight of ${portfolio.title}">
      <input type="number" id="part-${i}" min="0" max="100" step="1" value="${initial[i]}" required></div>`).join("")}
    <div class="actions"><button type="button" class="button outline" id="suggest">Suggest a blend by Sharpe ratio</button></div>
    <p id="blend-status" aria-live="polite"></p><div id="blend-result"></div>
    <button class="button primary" type="button" id="choose-blend">Confirm this blend</button>`);
  const rows = [...content.querySelectorAll("[data-part]")];
  const read = () => rows.map(row => row.querySelector('input[type="number"]').valueAsNumber);
  const status = content.querySelector("#blend-status");
  const result = content.querySelector("#blend-result");
  const confirm = content.querySelector("#choose-blend");
  function update() {
    const parts = read();
    const total = parts.reduce((sum, part) => sum + part, 0);
    const valid = parts.every(part => Number.isInteger(part) && part >= 0 && part <= 100) && total === 100;
    status.textContent = Number.isFinite(total) ? `Total ${total} %${valid ? "" : " · Adjust the weights to total 100%."}` : "Enter a weight for each portfolio.";
    status.dataset.valid = String(valid);
    result.innerHTML = valid ? metrics(blendWeights(parts)) + allocation(blendWeights(parts)) : "";
    confirm.disabled = !valid;
  }
  rows.forEach(row => {
    const slider = row.querySelector('input[type="range"]');
    const field = row.querySelector('input[type="number"]');
    slider.addEventListener("input", () => { field.value = slider.value; update(); });
    field.addEventListener("input", () => { slider.value = field.value; update(); });
  });
  content.querySelector("#suggest").addEventListener("click", () => {
    const active = read().map((value, i) => value > 0 ? i : -1).filter(i => i >= 0);
    const best = highestSharpe(active.length > 1 ? active : [0, 1, 2]);
    rows.forEach((row, i) => row.querySelectorAll("input").forEach(input => { input.value = best[i]; }));
    update();
    status.textContent += " · Demo suggestion using five-percentage-point increments.";
  });
  confirm.addEventListener("click", () => confirmChoice("My blend", blendWeights(read()), read()));
  update();
}

let sessionChoice = null;
function savedChoice() {
  if (sessionChoice) return sessionChoice;
  try {
    const saved = JSON.parse(localStorage.getItem(storage));
    if (!saved || typeof saved.title !== "string" || !Array.isArray(saved.weights) || saved.weights.length !== assets.length ||
        !saved.weights.every(value => Number.isFinite(value) && value >= 0 && value <= 100) ||
        Math.abs(saved.weights.reduce((sum, value) => sum + value, 0) - 100) > 1e-6) return null;
    return saved;
  } catch {
    return null;
  }
}

function confirmChoice(title, weights, parts = null) {
  sessionChoice = {title, weights, parts};
  try {
    localStorage.setItem(storage, JSON.stringify(sessionChoice));
  } catch {
    // The demo can still show the choice in this tab.
  }
  showModal(`<div class="match-screen"><span class="match-heart" aria-hidden="true">♥</span>
    <h2 id="modal-title">Match confirmed</h2><p>${title} · Simulated selection</p>
    <button class="button primary" id="see-portfolio" type="button">View my portfolio</button></div>`);
  const follow = content.querySelector("#see-portfolio");
  follow.focus();
  follow.addEventListener("click", () => {
    modal.close();
    if (location.hash === "#suivi") renderPage();
    else location.hash = "suivi";
  });
}

function track() {
  const container = document.querySelector("#tracking");
  const choice = savedChoice();
  if (!choice) {
    container.innerHTML = '<h2>No match yet</h2><p>Choose a portfolio or build your allocation.</p><a class="button primary" href="#options">Explore portfolios</a>';
    return;
  }
  container.innerHTML = `<h2 id="saved-title"></h2><p>Illustrative capital · ${funds.format(35000)} · Simulated selection</p>
    ${metrics(choice.weights)}<h3>Confirmed holdings</h3>${allocation(choice.weights)}
    <a class="button outline" href="#options">Compare options</a>`;
  container.querySelector("#saved-title").textContent = choice.title;
}

const responses = [];
function renderQuestion() {
  const i = responses.length;
  if (i === questions.length) {
    profile.innerHTML = '<h2>Questionnaire complete</h2><p>These cards demonstrate the response format. The portfolios shown use fictional profiles.</p><div class="actions"><a href="#options" class="button primary">View portfolios</a><button type="button" class="button outline" data-back>Back</button></div>';
    return;
  }
  profile.innerHTML = `<div class="question-card"><p class="eyebrow">QUESTION ${i + 1} OF ${questions.length}</p><h2>${questions[i]}</h2></div>
    <div class="actions"><button type="button" class="button outline" data-answer="non">No</button><button type="button" class="button primary" data-answer="oui">Yes</button>
    <button type="button" class="button outline" data-answer="passer">Skip</button>${i > 0 ? '<button type="button" class="button outline" data-back>Back</button>' : ""}</div>`;
  const card = profile.querySelector(".question-card");
  let from = null;
  card.addEventListener("pointerdown", event => {
    from = event.clientX;
    card.setPointerCapture(event.pointerId);
  });
  card.addEventListener("pointercancel", () => { from = null; });
  card.addEventListener("pointerup", event => {
    if (from === null) return;
    const offset = event.clientX - from;
    from = null;
    if (Math.abs(offset) >= 52) answer(offset > 0 ? "oui" : "non");
  });
}

function answer(value) {
  if (responses.length >= questions.length) return;
  responses.push(value);
  renderQuestion();
}
function renderPage() {
  const target = location.hash.slice(1);
  const current = ["profil", "suivi"].includes(target) ? target : "explorer";
  document.querySelectorAll("[data-view]").forEach(view => { view.hidden = view.dataset.view !== current; });
  document.querySelectorAll("[data-nav]").forEach(link => {
    if (link.dataset.nav === current) link.setAttribute("aria-current", "page");
    else link.removeAttribute("aria-current");
  });
  if (current === "suivi") track();
  if (target === "options") requestAnimationFrame(() => document.getElementById(target).scrollIntoView());
  else window.scrollTo(0, 0);
}

drawCards();
renderQuestion();
renderPage();
window.addEventListener("hashchange", renderPage);
document.querySelector("#compose").addEventListener("click", () => showComposer());
document.querySelector(".close").addEventListener("click", () => modal.close());
document.querySelector("#portfolio-cards").addEventListener("click", event => {
  const button = event.target.closest("[data-portfolio]");
  if (button) showPortfolio(Number(button.dataset.portfolio));
});
profile.addEventListener("click", event => {
  const option = event.target.closest("[data-answer]");
  if (option) answer(option.dataset.answer);
  if (event.target.closest("[data-back]")) {
    responses.pop();
    renderQuestion();
  }
});
document.addEventListener("keydown", event => {
  if (document.querySelector("#profil").hidden || event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    event.preventDefault();
    answer(event.key === "ArrowRight" ? "oui" : "non");
  }
});
