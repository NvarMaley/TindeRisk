import { showIntro } from "./intro.js";
import { renderLibrary } from "./library.js";
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
  esc,
  fmt,
  pct,
  toast,
} from "./studio-core.js";
import { calculate, showMatches, showTracking } from "./portfolio.js";

let editing = null,
  calibrating = false;
const storeKey = "riskmatch-studio-dossier-v1";
function remember(token) {
  try {
    if (token) sessionStorage.setItem(storeKey, token);
    else sessionStorage.removeItem(storeKey);
  } catch {}
}
function field(label, name, attrs = "") {
  return (
    '<label class="field">' +
    label +
    '<input name="' +
    name +
    '" ' +
    attrs +
    "></label>"
  );
}
function intake() {
  shell(
    "intake",
    '<div class="intake-grid"><aside><p class="kicker">Investment brief</p><h1>Your money.<br>Your terms.</h1><p class="lede">Set aside what you need. We’ll use the rest to explore portfolios around your goal.</p><div class="intake-shot" role="img" aria-label="Miami waterfront at dusk"></div><div class="budget-line"><span>Protected cash</span><b id="reserve">—</b></div><div class="budget-line"><span>Investment sleeve</span><b id="sleeve">—</b></div><p class="muted" style="margin-top:12px">Fictional CHF account · research close 30 Oct 2026.</p></aside><form class="setup-form" id="brief"><div class="panel"><fieldset class="formset"><legend>Your budget</legend><div class="fields">' +
      field(
        "Total capital · CHF",
        "capital",
        'required type="number" min="1" max="1000000000" step=".01" placeholder="50,000"',
      ) +
      field(
        "Keep protected · CHF",
        "protected",
        'required type="number" min="0" step=".01" placeholder="15,000"',
      ) +
      field(
        "Loss you can afford · CHF",
        "loss",
        'required type="number" min="0" step=".01" placeholder="5,000"',
      ) +
      field(
        "Planned withdrawal · CHF",
        "expense",
        'type="number" min="0" step=".01" placeholder="0"',
      ) +
      '<label class="field wide" id="expenseWhen" hidden>Withdrawal date<input type="date" name="expense_date" min="2026-10-31"></label></div></fieldset></div><div class="panel"><fieldset class="formset"><legend>Your destination</legend><div class="fields">' +
      field(
        "Target wealth · CHF",
        "goal",
        'required type="number" min="1" step=".01" placeholder="60,000"',
      ) +
      field("Goal date", "due", 'required type="date" min="2026-10-31"') +
      field(
        "Desired annual return · % (optional)",
        "target",
        'type="number" step=".1" min="-99" max="200" placeholder="e.g. 5"',
      ) +
      '</div></fieldset></div><div class="panel"><fieldset class="formset"><legend>Your boundaries</legend><div class="fields"><label class="field wide">Environmental preference<select name="moral"><option value="none">No environmental preference</option><option value="low_emissions">Prefer lower measured emissions</option><option value="exclude_chevron">Require verified exclusion of Chevron exposure</option></select></label>' +
      '<label class="field wide">Investment universe<select name="universe"><option value="all">All eligible US instruments</option><option value="funds">ETFs only</option><option value="direct">Individual stocks and Treasuries only</option><option value="treasury">Treasuries and Treasury ETFs only</option></select></label>' +
      field(
        "Exclude US tickers (optional)",
        "exclusions",
        'placeholder="e.g. XOM, CVX" maxlength="500"',
      ) +
      field(
        "Other mandatory rule (optional)",
        "mandatory",
        'placeholder="Rule requiring verification" maxlength="280"',
      ) +
      '</div></fieldset></div><div class="error" role="alert"></div><button class="primary" type="submit">Start my calibration</button></form></div>',
  );
  const f = root.querySelector("#brief");
  for (const [k, v] of Object.entries(state.facts)) {
    if (f.elements[k]) f.elements[k].value = v;
  }
  const update = () => {
    const cap = f.capital.valueAsNumber,
      reserve = Math.max(
        f.protected.valueAsNumber || 0,
        f.expense.valueAsNumber || 0,
      );
    root.querySelector("#reserve").textContent = "CHF " + fmt(reserve);
    root.querySelector("#sleeve").textContent = isFinite(cap)
      ? "CHF " + fmt(Math.max(0, cap - reserve))
      : "—";
    const use = f.expense.valueAsNumber > 0;
    root.querySelector("#expenseWhen").style.display = use ? "grid" : "none";
    f.expense_date.required = use;
  };
  update();
  f.oninput = update;
  f.onsubmit = (e) => {
    e.preventDefault();
    run(f.querySelector("[type=submit]"), async () => {
      const raw = Object.fromEntries(new FormData(f));
      raw.expense = raw.expense || 0;
      await api("intake", { facts: raw });
      state.facts = raw;
      editing = null;
      await nextCard();
    });
  };
}
async function nextCard() {
  const data = await api("route", { answers: state.answers });
  state.cards = data.cards;
  state.answers = data.answers;
  const card =
    state.cards.find((c) => c.id === editing) ||
    state.cards.find((c) => !(c.id in state.answers));
  editing = null;
  if (!card) {
    await finishProfile();
    return;
  }
  const done = state.cards.filter((c) => c.id in state.answers).length;
  shell(
    "calibrate",
    '<div class="sweep"><div class="deck-head"><div><p class="kicker">Behavioural calibration</p><h2>Your move.</h2></div><span class="pill">' +
      done +
      ' answered</span></div><div class="meter"><span style="width:' +
      (100 * done) / state.cards.length +
      '%"></span></div><div class="swipepad"><article class="swipe-card" data-card-id="' +
      card.id +
      '" tabindex="0" aria-label="Swipe to agree or disagree"><div class="art ' +
      (done % 3 === 0 ? "a" : done % 3 === 1 ? "b" : "c") +
      '"></div><span class="swipe-mark" aria-hidden="true"></span><div class="card-body"><p class="kicker">' +
      esc(card.family) +
      '</p><h1 class="statement">' +
      esc(card.text) +
      '</h1><p class="lede">Swipe right if this sounds like you. Swipe left if it doesn’t.</p></div></article></div><div class="swipe-buttons"><button data-vote="no"><b aria-hidden="true">×</b> Not me</button><button class="like" data-vote="yes"><b aria-hidden="true">♥</b> Like me</button></div><div class="below"><button class="flat" id="back">Back</button><button class="flat" id="skip">Unsure</button></div></div>',
  );
  const answer = async (v) => {
    state.answers[card.id] = v;
    if (card.id === "T03" && v === "yes") editing = "T01";
    if (card.id === "L05" && v === "yes") editing = "L01";
    if (card.id === "G04" && v === "no") editing = "G01";
    await nextCard();
  };
  const stage = root.querySelector(".swipe-card");
  swipes(stage, answer);
  stage.focus({ preventScroll: true });
  bind("#skip", () => answer("skip"));
  bind("#back", async () => {
    const i = state.cards.indexOf(card);
    if (!i) {
      intake();
      return;
    }
    editing = state.cards[i - 1].id;
    await nextCard();
  });
}
async function finishProfile() {
  if (calibrating) return;
  calibrating = true;
  try {
    const result = await api("calibrate", {
      facts: state.facts,
      answers: state.answers,
    });
    Object.assign(state, result, { plans: [], kept: [], draft: null });
    remember(state.token);
    profile(true);
  } finally {
    calibrating = false;
  }
}
function profile(animate = false) {
  const p = state.profile;
  if (!p) {
    intake();
    return;
  }
  const f = p.facts;
  shell(
    "profile",
    '<div class="reveal ' +
      (animate ? "animated" : "") +
      '"><img src="assets/cherry.png" alt=""><p class="kicker">' +
      (animate ? "Calibration complete" : "Behavioural profile") +
      "</p><h1>" +
      esc(p.band) +
      '</h1><p class="lede">' +
      (p.score == null
        ? "The answers need another look before the model can estimate a risk range."
        : "Your choices suggest a " +
          (p.high == null
            ? pct(p.low) + " and above"
            : pct(p.low) + "–" + pct(p.high)) +
          " annual volatility range for your investment sleeve.") +
      "</p></div>" +
      tiles([
        [
          "Willingness score",
          p.score == null ? "Undetermined" : p.score + " / 100",
        ],
        ["Investment sleeve", "CHF " + fmt(f.capital_chf)],
        ["Protected cash", "CHF " + fmt(f.reserve_chf)],
        ["Horizon", p.horizon_years + " years"],
      ]) +
      '<div class="actions"><button class="primary" id="calculate" ' +
      (p.blocked_reason ? "disabled" : "") +
      '>Calculate my matches</button><button class="secondary" id="library">Explore the asset library</button><button class="flat" id="edit">Edit my brief</button></div>' +
      (p.blocked_reason
        ? '<p class="warning">' + esc(p.blocked_reason) + "</p>"
        : "") +
      '<div style="margin-top:32px"><p class="kicker">Behavioural evidence</p><h2>How you reacted.</h2><div class="tiles">' +
      p.readings
        .map(
          (c) =>
            '<div class="tile"><small>' +
            esc(c.name) +
            "</small><strong>" +
            esc(c.value) +
            "</strong><p>" +
            esc(c.detail) +
            "</p></div>",
        )
        .join("") +
      "</div></div>" +
      '<details class="info"><summary>How the score and risk range were estimated</summary><p class="lede">Three domains receive equal weight when interpretable. Higher scores indicate greater willingness to take risk. The thresholds are 20, 40, 60 and 80 out of 100. A like can indicate caution or risk tolerance depending on the proposition. These are theoretical tendencies from fictional decisions. A volatility range is a model estimate, not a maximum loss.</p>' +
      tiles(
        Object.entries(p.domains).map(([k, v]) => [
          k,
          v == null ? "Insufficient" : v + " / 100",
        ]),
      ) +
      '<p class="muted">' +
      esc(
        p.cap_note ||
          "Loss capacity, protected cash and mandatory constraints are checked separately for each actual portfolio.",
      ) +
      "</p></details>" +
      '<details class="info"><summary>My propositions and what they measure · ' +
      p.evidence.length +
      "</summary>" +
      p.evidence
        .map(
          (c) =>
            '<div class="listrow"><small>' +
            esc(c.family) +
            " · " +
            (c.answer === "yes"
              ? "Like me"
              : c.answer === "no"
                ? "Not me"
                : "Unsure") +
            "</small><strong>" +
            esc(c.text) +
            "</strong><small>" +
            esc(c.help) +
            '</small><button class="flat review" data-id="' +
            c.id +
            '">Revisit</button></div>',
        )
        .join("") +
      "</details>" +
      '<details class="info"><summary>My saved simulation</summary><div class="actions"><button id="export" class="flat">Export my dossier</button><button id="delete" class="danger">Delete my dossier</button></div></details><div class="error" role="alert"></div>',
  );
  bind("#calculate", calculate);
  bind("#library", library);
  bind("#edit", intake);
  root.querySelectorAll(".review").forEach(
    (b) =>
      (b.onclick = () =>
        run(b, async () => {
          editing = b.dataset.id;
          await nextCard();
        })),
  );
  bind("#export", async () => {
    const blob = new Blob([JSON.stringify(await api("export"), null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob),
      a = document.createElement("a");
    a.href = url;
    a.download = "riskmatch-fictional-dossier.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  });
  bind("#delete", async () => {
    if (!confirm("Delete this fictional dossier and its simulated holdings?"))
      return;
    await api("delete");
    remember("");
    location.reload();
  });
}
function library() {
  shell("library", '<div id="library-root"></div>');
  return renderLibrary(root.querySelector("#library-root"), {
    back: () => profile(),
  });
}
Object.assign(nav, {
  profile,
  intake,
  library,
  tracking: showTracking,
  matches: () => (state.plans.length ? showMatches() : calculate()),
});
showIntro(root, {
  prepare: async () => {
    await api("bootstrap");
    let token = "";
    try {
      token = sessionStorage.getItem(storeKey) || "";
    } catch {}
    if (token) {
      state.token = token;
      try {
        Object.assign(state, await api("resume"));
      } catch {
        remember("");
        state.token = "";
      }
    }
  },
  onDone: () => (state.profile ? profile() : intake()),
});
