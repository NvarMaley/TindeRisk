(() => {
  const groups = [
    [["Weighting and diversification", "Pondération et diversification"],
      "equal_weight minimum_variance inverse_variance risk_parity hrp herc maximum_diversification"],
    [["Return and risk optimization", "Optimisation du rendement et du risque"],
      "maximum_sharpe mean_variance_utility tracking_error black_litterman capm_utility ewma_utility robust_utility resampled_utility wasserstein_utility kelly fractional_kelly entropy_utility constrained_utility"],
    [["Loss control and defensive allocations", "Maîtrise des pertes et allocations défensives"],
      "minimum_cvar minimum_cdar maximum_sortino maximum_omega volatility_target tail_hedge_proxy defensive_reference"],
    [["Passive, active and factor strategies", "Gestion passive, active et factorielle"],
      "passive_index passive_etfs active_long_only smart_beta_equal smart_beta_factor smart_beta_fundamental factor_investing core_satellite factor_size factor_value factor_momentum factor_low_volatility factor_liquidity factor_quality factor_profitability_proxy factor_investment"],
    [["Trends and economic conditions", "Tendances et conditions économiques"],
      "cross_sectional_momentum time_series_momentum mean_reversion tactical_allocation all_weather multi_strategy regime_switching global_macro"],
    [["Fixed demo allocations", "Allocations fixes de démonstration"],
      ["Cash", "Conservative", "60/40", "1/N", "Growth", "Fixed income"]],
  ];
  const stages = [
    [
      ["Set the investment mandate", "Définir le mandat"],
      ["Enter the capital you can invest, its intended use, the dates you will need it, and your deposits and withdrawals. RiskMatch checks funding and derives the working stress limit from the declared loss capacity and firm limits. For example, a 10% stress limit on USD 10,000 means the tested shocks must imply a loss of at most USD 1,000.",
        "Indique le capital que tu peux investir, à quoi il servira, quand tu en auras besoin et les versements ou retraits prévus. RiskMatch vérifie le financement et détermine la limite de stress à partir de ta capacité de perte déclarée et des limites fermes. Par exemple, une limite de 10 % sur 10 000 USD signifie que les chocs testés doivent impliquer une perte d’au plus 1 000 USD."],
    ],
    [
      ["Explore your risk preferences", "Explorer tes préférences de risque"],
      ["The 30 Discovery cards pose decisions about gains, losses and uncertainty. With enough usable answers, the app estimates a risk-aversion score from 1 to 30. The engine combines that score with your horizon and goals to set the weight given to safety, within the mandate limits.",
        "Les 30 cartes du questionnaire proposent des choix sur les gains, les pertes et l’incertitude. Avec suffisamment de réponses exploitables, l’application estime un score d’aversion au risque de 1 à 30. Le moteur combine ce score avec ton horizon et tes objectifs pour déterminer le poids donné à la sécurité, dans les limites du mandat."],
    ],
    [
      ["Select eligible holdings and data", "Sélectionner les actifs et les données admissibles"],
      ["Personalized matching uses a local archive of monthly total returns in USD. It starts from securities with a common return history, then filters by your permitted asset classes and applies position caps. Depending on the strategy, it also uses dated stock eligibility, company filings or macroeconomic data.",
        "Le calcul personnalisé utilise une archive locale de rendements totaux mensuels en USD. Il part d’actifs disposant d’un historique commun, filtre selon les catégories autorisées et applique les plafonds de poids. Selon la stratégie, il utilise aussi la liste des actions admissibles à chaque date, des publications d’entreprises ou des données macroéconomiques."],
    ],
    [
      ["Build and check candidate portfolios", "Construire et vérifier les portefeuilles"],
      ["Each strategy applies its own rule to determine how much to invest in each holding. The engine checks that weights sum to 100% and tests concentration, stress losses and any firm volatility limit. It can move a portfolio toward a feasible defensive mix. A method can be left out if the inputs or constraints make it impracticable.",
        "Chaque stratégie applique sa propre règle pour répartir le capital. Le moteur vérifie que les poids totalisent 100 %, puis teste la concentration, les pertes en stress et le plafond ferme de volatilité s’il existe. Il peut rapprocher une allocation d’un portefeuille défensif compatible. Une méthode peut être écartée si les données ou les contraintes empêchent de la calculer."],
    ],
    [
      ["Replay the strategies on historical data", "Rejouer les stratégies dans le passé"],
      ["The engine recalculates each method quarterly using returns preceding each decision, then applies the new weights one month later. The replay models a charge of 0.10% on the value of securities traded. A later test period shows how the rule behaved after the period used to develop and assess it.",
        "Le moteur recalcule chaque méthode chaque trimestre avec les rendements antérieurs à la décision, puis applique les nouveaux poids un mois plus tard. Le test simule des frais de 0,10 % sur la valeur des titres échangés. Une période de test plus récente montre comment la règle s’est comportée après la période utilisée pour la mettre au point et l’évaluer."],
    ],
    [
      ["Project goals and rank the cards", "Projeter les objectifs et classer les cartes"],
      ["For measurable goals, the engine builds 256 possible paths from six-month blocks of historical returns and applies your cash flows. Ranking combines stress losses, estimated return, goal outcomes and supported preferences. It brings different allocations forward and groups methods whose final weights are nearly identical.",
        "Pour les objectifs mesurables, le moteur construit 256 trajectoires à partir de blocs de six mois de rendements historiques et y applique tes flux. Le classement combine les pertes en stress, le rendement estimé, les résultats des objectifs et les préférences prises en charge. Il met en avant des allocations variées et regroupe les méthodes dont les poids finaux sont très proches."],
    ],
    [
      ["Compare and confirm an allocation", "Comparer et confirmer une allocation"],
      ["Keep the cards you want to compare. In My Matches, set your own split or test a lower-volatility or goal-focused split where available. RiskMatch combines the underlying holdings and recalculates the portfolio’s risk and results. Confirming saves a simulated choice. Results depend on the available history, costs and stress assumptions, and future losses can be larger.",
        "Garde les cartes que tu veux comparer. Dans Mes Matches, choisis ta répartition ou teste, selon les options disponibles, une répartition moins volatile ou orientée vers un objectif. RiskMatch combine les actifs détenus et recalcule le risque et les résultats du portefeuille. La confirmation enregistre un choix de simulation. Les résultats dépendent de l’historique disponible, des frais et des hypothèses de stress, et les pertes futures peuvent être plus importantes."],
    ],
    [
      ["Follow the portfolio after confirmation", "Suivre le portefeuille après confirmation"],
      ["With market quotes configured, My Matches values the simulated holdings from the first complete set of prices, then refreshes while the page is open. You can see performance and weight drift, keep the initial holdings or simulate a quarterly return to the target weights. Historical goal projections and management tests remain available.",
        "Avec une API de cours configurée, Mes Matches valorise les positions simulées à partir du premier ensemble complet de cours et les actualise tant que la page est ouverte. Tu peux voir la performance et l’écart aux poids cibles, conserver les positions ou simuler un retour trimestriel aux poids cibles. Les projections d’objectifs et les tests historiques restent disponibles."],
    ],
  ];
  const tools = {
    objectives: ["Estimate how often a savings or funding target is reached in simulated paths and how much may be missing.", "Estime combien de trajectoires simulées atteignent un objectif d’épargne ou de financement, et quel montant peut manquer."],
    baselines: ["Compare against simple reference portfolios such as cash, equal weights or a 60/40 mix.", "Compare avec des portefeuilles de référence simples, comme les liquidités, les poids égaux ou un portefeuille 60/40."],
    "mean-variance": ["Try allocations that seek a given return or minimize fluctuations, subject to weight limits.", "Teste des allocations qui visent un rendement donné ou minimisent les fluctuations, sous réserve des plafonds de poids."],
    "black-litterman": ["See how adding market assumptions changes estimated returns and portfolio weights.", "Observe comment des hypothèses de marché modifient les rendements estimés et les poids du portefeuille."],
    hierarchical: ["Compare ways to spread risk among assets or groups that move together.", "Compare des façons de répartir le risque entre des actifs ou des groupes qui évoluent ensemble."],
    downside: ["Compare methods that focus on the worst months and falls from a previous peak.", "Compare des méthodes qui se concentrent sur les pires mois et les reculs depuis un sommet."],
    advanced: ["Test how allocations change when estimates are uncertain or when the rule favors diversification or compound growth.", "Teste comment les allocations changent quand les estimations sont incertaines ou que la règle favorise la diversification ou la croissance composée."],
    "long-only": ["Compare strategies that buy assets, from passive funds to rules based on stock characteristics.", "Compare des stratégies qui achètent des actifs, des fonds passifs aux règles fondées sur les caractéristiques des actions."],
    alternative: ["Explore trend, macroeconomic and other signals, including experimental strategies that may use short positions.", "Explore les signaux de tendance, les signaux macroéconomiques et d’autres règles, y compris des stratégies expérimentales qui peuvent utiliser des positions vendeuses."],
    treasury: ["Explore US government bonds and how their values react to changes in interest rates.", "Explore les obligations d’État américaines et la réaction de leur valeur aux variations de taux."],
    futures: ["Explore how contracts behave when exposure is carried from one expiry to the next.", "Explore le comportement des contrats à terme quand une exposition est reportée d’une échéance à la suivante."],
    "walk-forward": ["Replay decisions in order and check how strategies behaved on later observations.", "Rejoue les décisions dans l’ordre et observe le comportement des stratégies sur des données ultérieures."],
    "stress-mc": ["Apply specified market shocks or generate simulated return paths to see how outcomes vary.", "Applique des chocs de marché définis ou génère des trajectoires simulées pour observer la diversité des résultats."],
  };

  function render() {
    const lang=window.RM.language==="fr"?1:0;
    const t=window.RM.t;
    const {methods,sources}=window.StrategyMethods;
    const catalogue=document.getElementById("strategy-library");
    catalogue.innerHTML=groups.map(([title,names])=>{
      const keys=Array.isArray(names)?names:names.split(" ");
      const entries=keys.map(key=>{
        const method=methods[key], source=sources[method[3]||"returns"];
        return `<details><summary>${esc(strategyName(key))}</summary>
          <p>${esc(method[lang])}</p>
          ${method[2]?`<p><code>${esc(method[2])}</code></p>`:""}
          <p class="muted"><strong>${esc(t("catalogueInputs"))}</strong> · ${esc(source[lang])}</p></details>`;
      }).join("");
      return `<section><h2>${esc(title[lang])}</h2>${entries}</section>`;
    }).join("");
    document.getElementById("methodology-stages").innerHTML=stages.map(([title,body])=>
      `<li><h2>${esc(title[lang])}</h2><p>${esc(body[lang])}</p></li>`).join("");
    document.querySelectorAll(".research-tool-help").forEach(node=>{
      node.textContent=tools[node.dataset.tool][lang];
    });
  }
  document.addEventListener("riskmatch:language",render);
  render();
})();
