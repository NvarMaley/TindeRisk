// Keep the English source for each translated node so switching language never
// rebuilds a form, restarts an animation or changes a saved answer.
import { french } from "./translations.js";

const storageKey = "riskmatch-language";
let language = "en";
try {
  if (localStorage.getItem(storageKey) === "fr") language = "fr";
} catch {}

const textSources = new WeakMap();
const attributeSources = new WeakMap();
const attributes = ["aria-label", "placeholder", "title"];

function translate(text) {
  if (language !== "fr") return text;
  const source = text.trim();
  const translation = Object.hasOwn(french, source) ? french[source] : source.replace(/^([\d]+) answered$/, "$1 réponses")
      .replace(/^Portfolio ([AB]) ·/, "Portefeuille $1 ·").replace(/^(Portefeuille [AB] · .*%) or (.*%)$/, "$1 ou $2")
      .replace(/^On a fictional CHF (.+) investment for one year, which outcome would you choose\?$/, "Sur un placement fictif de CHF $1 pendant un an, quelle option choisiriez-vous ?")
      .replace(/^CHF (.+) guaranteed$/, "CHF $1 garantis")
      .replace(/^50\/50 chance of CHF (.+) or CHF (.+)$/, "CHF $1 ou CHF $2 · 50 % chacun")
      .replace(/^(\d+(?:\.\d+)?) years$/, "$1 ans")
      .replace(/^Match score (.+)$/, "Score de compatibilité $1")
      .replace(/^Goal comparison ·/, "Comparaison avec l’objectif ·")
      .replace(/^(Comparaison avec l’objectif · .+) needed ·/, "$1 requis ·")
      .replace(/^Simulate (\d{4}-\d{2}-\d{2})$/, "Simuler le $1")
      .replace(/^My propositions and what they measure · (\d+)$/, "Mes réponses et ce qu’elles mesurent · $1")
      .replace(/^([\d,.]+) holdings$/, "$1 positions")
      .replace(/^Risk aversion ·/, "Aversion au risque ·")
      .replace(/^(\d+) of (\d+) equivalent pairs agreed\.$/, "Les réponses concordent dans $1 paire(s) sur $2.")
      .replace(/^Reasons you selected: (.+)\.$/, (_, reasons) => {
        const labels = { "cash needs": "besoin de liquidités", discomfort: "inconfort", "expecting a further fall": "anticipation d’une nouvelle baisse" };
        return "Motifs retenus : " + reasons.split(", ").map(reason => labels[reason] || reason).join(", ") + ".";
      })
      .replace(/^The upper end exceeds the (.+) volatility covered by your answered comparisons\. Treat this part of the range as an extrapolation from historical model inputs\.$/, "La borne haute dépasse la volatilité de $1 couverte par vos réponses. Cette partie de la tranche est extrapolée à partir des données historiques du modèle.")
      .replace(/^The portfolio search uses up to (.+) modeled annual volatility, with calmer options included\.$/, "La recherche couvre une volatilité annuelle estimée allant jusqu’à $1. Des options plus prudentes sont proposées.")
      .replace(/^(Provisional questionnaire range: |Your choices suggest a )(.+) annual volatility range for your investment sleeve\.$/, (_, lead, range) => "Tranche indicative de volatilité annuelle pour le montant investi : " + range.replace(" and above", " et plus") + ".")
      .replace(/^Help with (.+)$/, (_, label) => "Aide · " + (french[label] || label))
      .replace(/^Derived from your portfolio choices and checked against your account constraints on (.+)\. Calmer options are available\.$/, "Calculé à partir de vos choix, avec les contraintes du compte au $1. Des options plus prudentes sont disponibles.");
  return source ? text.replace(source, () => translation) : text;
}

function update(node) {
  if (node.nodeType === Node.TEXT_NODE) {
    if (node.parentElement?.closest("script, style, [data-language], [data-untranslated], #save-form select option:not([value=new])")) return;
    let original = textSources.get(node);
    if (!original || node.data !== original.rendered) original = { source: node.data };
    original.rendered = translate(original.source);
    textSources.set(node, original);
    if (node.data !== original.rendered) node.data = original.rendered;
  } else if (node.nodeType === Node.ELEMENT_NODE && !node.closest("[data-language]")) {
    const sources = attributeSources.get(node) || {};
    for (const name of attributes) {
      const value = node.getAttribute(name);
      if (value === null) {
        delete sources[name];
        continue;
      }
      if (value !== sources[name]?.rendered) sources[name] = { source: value };
      sources[name].rendered = translate(sources[name].source);
      if (value !== sources[name].rendered) node.setAttribute(name, sources[name].rendered);
    }
    attributeSources.set(node, sources);
  }
}
function translateTree(node) {
  update(node);
  const walker = document.createTreeWalker(node, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_ELEMENT);
  while (walker.nextNode()) update(walker.currentNode);
}

export function installLanguage(root) {
  const control = document.createElement("select");
  control.dataset.language = "";
  control.setAttribute("aria-label", "Language / Langue");
  control.innerHTML = '<option value="en" lang="en">English</option><option value="fr" lang="fr">Français</option>';
  control.value = language;
  const mount = () => {
    const host = root.querySelector(".mast .nav") || root.querySelector(".rm-intro");
    if (host && control.parentElement !== host) host.append(control);
  };
  const notice = document.getElementById("notice");
  const observer = new MutationObserver(records => {
    mount();
    for (const record of records) {
      if (record.type !== "childList") update(record.target);
      else record.addedNodes.forEach(translateTree);
    }
  });
  const targets = [root, notice].filter(Boolean);
  for (const target of targets) {
    observer.observe(target, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: attributes });
  }
  const refresh = () => {
    document.documentElement.lang = language;
    targets.forEach(translateTree);
  };
  control.onchange = () => {
    language = control.value;
    try { localStorage.setItem(storageKey, language); } catch {}
    refresh();
  };
  refresh();
}
