import { esc, fmt, pct } from "./studio-core.js";

const categories = [
  ["Very cautious", "Prefers stability and accepts limited fluctuations."],
  ["Cautious", "Accepts modest fluctuations for the chance of higher returns."],
  ["Moderate", "Balances potential gains with the ability to withstand losses."],
  ["Growth-oriented", "Accepts wider fluctuations in pursuit of growth."],
  ["Aggressive", "Shows strong willingness to accept fluctuations for higher potential returns."],
];

const descriptions = {
  comprehension: "Higher means the probability and the wider range were identified correctly.",
  tradeoff: "Higher means you chose the wider portfolio more often.",
  loss: "Higher means you needed more potential gain to accept the same possible loss.",
  drawdown: "Higher means you were more inclined to hold after the simulated 15% fall.",
  ambiguity: "Higher means greater willingness to choose an offer with an unknown probability.",
};

const blockRules = {
  comprehension: "A correct answer on probability and amplitude gives 100. An unresolved amplitude error gives 50. Two probability errors give 0.",
  tradeoff: "Each choice for the wider portfolio gives 50 points. Contradictory choices leave the block undetermined.",
  loss: "Taking both chances gives 0. Choosing only the CHF 250 gain scenario gives 50. Refusing both gives 100.",
  drawdown: "Holding gives 100, reviewing the plan gives 50 and reducing exposure gives 0. Follow-up answers describe your reasons.",
  ambiguity: "Known probability gives 0, no preference gives 50 and unknown probability gives 100.",
};

function evidenceRows(evidence) {
  return evidence.map(card => {
    const answer = card.choices?.find(([id]) => id === card.answer)?.[1] ??
      ({yes: "Like me", no: "Not me", skip: "Unsure"}[card.answer] ?? card.answer);
    return `<li><span>${esc(card.text)}</span><strong>${esc(answer)}</strong></li>`;
  }).join("");
}

function blockRows(blocks, evidence) {
  return blocks.map(block => {
    const { score, id, label, cards } = block;
    const responses = evidence.filter(card => cards.includes(card.id));
    return `<section class="profile-block">
      <div class="profile-block-body">
        <h3>${esc(label)}</h3>
        <p>${esc(descriptions[id])}</p>
        ${score == null ? "" : `<meter min="0" max="100" value="${score}" aria-label="${esc(label)}"></meter>`}
        ${responses.length ? `<details class="profile-answers">
          <summary>Questions and your answers</summary><p class="profile-note">${esc(blockRules[id])}</p><ul>${evidenceRows(responses)}</ul>
        </details>` : ""}
      </div>
      <strong class="profile-block-score">${score == null ? "Undetermined" : score + " / 100"}</strong>
    </section>`;
  }).join("");
}

export function profileView(profile, saveName, animate) {
  const { evidence, score, band, facts, volatility_zone: zone, aversion } = profile;
  const blocks = profile.behaviour_blocks;
  const category = categories.find(([label]) => label === band);
  const zoneText = zone?.low != null && zone?.high != null
    ? zone.high === 0 ? "0.0% · CHF cash" : pct(zone.low) === pct(zone.high)
      ? pct(zone.high) : pct(zone.low) + "–" + pct(zone.high)
    : !zone && profile.low != null
      ? profile.high == null ? pct(profile.low) + "+" : pct(profile.low) + "–" + pct(profile.high)
      : "Undetermined";
  const otherAnswers = blocks ? evidence.filter(card => !blocks.some(block => block.cards.includes(card.id))) : evidence;
  const downside = profile.readings.find(reading => reading.name === "Downside response");
  const gamma = aversion?.state === "estimated"
    ? aversion.gamma_high == null ? "γ ≥ " + aversion.gamma_low.toFixed(2)
      : "γ " + aversion.gamma_low.toFixed(2) + "–" + aversion.gamma_high.toFixed(2)
    : "";
  return `<div class="profile-layout">
    <header class="profile-hero ${animate ? "profile-reveal" : ""}">
      <div>
        <p class="kicker">Behavioural profile</p>
        ${saveName ? `<p class="profile-name" data-untranslated>${esc(saveName)}</p>` : ""}
        <h1>${esc(band)}</h1><p class="profile-definition">${esc(category?.[1] || "More answers are needed to assign a profile.")}</p>
      </div>
      <div class="profile-ring" style="--score: ${score ?? 0}%">
        <span>${score ?? "—"}<small>/ 100</small></span>
        <span class="profile-ring-label">Profile score</span>
      </div>
    </header>
    <ol class="profile-categories" aria-label="Risk profile categories">
      ${categories.map(([label, meaning]) => `<li ${label === band ? 'aria-current="true"' : ""} title="${esc(meaning)}">${esc(label)}</li>`).join("")}
    </ol>
    <details class="profile-answers profile-category-guide"><summary>What the categories mean</summary><dl>
      ${categories.map(([label, meaning]) => `<dt>${esc(label)}</dt><dd>${esc(meaning)}</dd>`).join("")}
    </dl></details>
    ${blocks ? `<div class="profile-results"><h2>Your results by block</h2>${blockRows(blocks, evidence)}</div>`
      : '<p class="profile-note">Restart the questionnaire to obtain the five block scores.</p>'}
    <div class="profile-facts">
      <div><span>Estimated annual volatility</span><strong>${esc(zoneText)}</strong></div>
      <div><span>Investment sleeve</span><strong>CHF ${fmt(facts.capital_chf)}</strong></div>
      <div><span>Horizon</span><strong>${profile.horizon_years} years</strong></div>
    </div>
    ${gamma ? `<p class="profile-note">Risk aversion · ${esc(gamma)}</p>` : ""}
    ${zone?.state === "needs_confirmation" ? '<p class="warning">The answers need another look before the model can estimate a risk range.</p>' : ""}
    ${zone?.high > aversion?.highest_tested_volatility ? '<p class="warning">The estimated range goes beyond the volatility covered by your answers.</p>' : ""}
    ${profile.stress_conflict ? '<p class="warning">Compare a calmer match and its modeled loss in CHF.</p>' : ""}
    ${profile.blocked_reason ? `<p class="warning">${esc(profile.blocked_reason)}</p>` : ""}
    <div class="actions profile-actions">
      <button class="primary" id="calculate" ${profile.blocked_reason ? "disabled" : ""}>Calculate my matches</button>
      <button class="secondary" id="restart-questionnaire">Restart questionnaire</button>
      <button class="flat" id="library">Explore the asset library</button>
      <button class="flat" id="edit">Edit my brief</button>
    </div>
    ${downside ? `<div class="profile-downside"><h3>Downside response</h3><p>${esc(downside.value)}</p><p class="profile-note">${esc(downside.detail)}</p></div>` : ""}
    <details class="profile-answers profile-method">
      <summary>Calculation method</summary>
      ${blocks ? `<p>The overall score uses 70% return–risk trade-off, 20% reaction after a decline and 10% willingness to accept a loss. Willingness to accept a loss is 100 minus loss sensitivity. Missing secondary scores are omitted and the remaining weights are rescaled.</p>
      <p class="profile-formula"><code>S = (7A + 2R + P) / 10</code></p>
      <p>A is the return–risk score, R is the reaction after a decline and P is willingness to accept a loss. The formula shown uses all three scores.</p>
      <p>A profile category requires a correct perception check, two interpretable portfolio choices and at least one secondary score. The category thresholds are 20, 40, 60 and 80. Comprehension and ambiguity do not contribute points.</p>
      <p>The block scores are indicative readings of a short simulation. Loss sensitivity can also reflect a preference for certainty. The ambiguity score comes from one optional choice.</p>`
      : '<p>This saved profile uses the previous scoring method. Restart to use the five-block method.</p>'}
      <p>The risk model compares expected return μ and variance σ². At the indifference point between A and B:</p>
      <p class="profile-formula"><code>γ* = 2(μB − μA) / (σB² − σA²)</code></p>
      <p>Choosing the steadier portfolio gives a lower bound on γ. Choosing the wider portfolio gives an upper bound. The model checks the resulting portfolios against the financial constraints to estimate volatility.</p>
    </details>
    ${otherAnswers.length ? `<details class="profile-answers">
      <summary>${blocks ? "Other questionnaire answers" : "Questions and your answers"}</summary><ul>${evidenceRows(otherAnswers)}</ul>
    </details>` : ""}
    <details class="profile-answers"><summary>My saved simulation</summary><button id="export" class="flat">Export my dossier</button></details>
    <div class="error" role="alert"></div>
  </div>`;
}
