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
  ];
  const stages = [
    [
      ["Set the investment mandate", "Définir le mandat"],
      ["The mandate starts today by default and sets the calendar for goals and cash flows. The cards use a frozen market archive to make the simulation reproducible. They show both the mandate start and the last market observation used to estimate the weights.",
        "Le mandat démarre par défaut aujourd’hui et fixe le calendrier des objectifs et des flux. Les cartes utilisent une archive de marché figée pour rendre la simulation reproductible. Elles affichent le départ du mandat et la dernière observation utilisée pour estimer les poids."],
    ],
    [
      ["Explore your risk preferences", "Explorer tes préférences de risque"],
      ["The 30 Discovery cards pose decisions about gains, losses and uncertainty. With enough usable answers, the app calculates a prudence index from 1 to 30. The engine combines that index with your horizon and goals to set the weight given to safety, within the mandate limits.",
        "Les 30 cartes du questionnaire proposent des choix sur les gains, les pertes et l’incertitude. Avec suffisamment de réponses exploitables, l’application calcule un indice de prudence de 1 à 30. Le moteur combine cet indice avec ton horizon et tes objectifs pour déterminer le poids donné à la sécurité, dans les limites du mandat."],
    ],
    [
      ["Select eligible holdings and data", "Sélectionner les actifs et les données admissibles"],
      ["Personalized matching uses US stocks, equity ETFs and US Treasury ETFs with 60 consecutive monthly total returns in USD, plus a cash account. The mandate filters the permitted holdings and applies position caps. Depending on the strategy, dated stock eligibility, company filings or macroeconomic signals may also help determine the weights.",
        "Le calcul personnalisé utilise des actions américaines, des ETF d’actions et des ETF du Trésor américain avec 60 mois consécutifs de rendement total en USD, ainsi qu’une poche de cash. Le mandat filtre les actifs autorisés et fixe les plafonds de position. Selon la stratégie, des publications d’entreprises ou des signaux macroéconomiques peuvent aussi intervenir."],
    ],
    [
      ["Check the data behind each asset", "Vérifier les données de chaque actif"],
      ["Universe lists the holdings whose series qualify for the shared portfolio panel. Each asset page gives the source, first and last observation, return type and role of its series. All strategies use the same calendar ending 31 December 2025. A missing month makes a security ineligible at that date. More recent prices remain available for research.",
        "Univers présente les placements retenus dans le panel du portefeuille. Chaque fiche donne la source, les dates, le type de rendement et le rôle des séries. Toutes les stratégies utilisent le même calendrier arrêté au 31 décembre 2025. Un mois manquant rend le titre inadmissible à cette date. Les prix plus récents restent disponibles dans Recherche."],
    ],
    [
      ["Build and check candidate portfolios", "Construire et vérifier les portefeuilles"],
      ["Each strategy applies its own rule to determine how much to invest in each holding. The engine checks that weights sum to 100% and tests concentration, stress losses and any firm volatility limit. It can move a portfolio toward a feasible defensive mix. A method can be left out if the inputs or constraints make it impracticable.",
        "Chaque stratégie applique sa propre règle pour répartir le capital. Le moteur vérifie que les poids totalisent 100 %, puis teste la concentration, les pertes en stress et le plafond ferme de volatilité s’il existe. Il peut rapprocher une allocation d’un portefeuille défensif compatible. Une méthode peut être écartée si les données ou les contraintes empêchent de la calculer."],
    ],
    [
      ["Distinguish asset research from portfolio inputs", "Distinguer les analyses par actif des données du moteur"],
      ["The asset pages compare historical and estimated returns, volatility models such as GARCH, factor exposures and downside risk. These diagnostics are indicative. The personalized engine rebuilds its own inputs, including historical means, covariance and dated factor or macro signals for the methods that require them. Recent-signal methods such as momentum and EWMA are especially sensitive to the archive cutoff.",
        "Les fiches comparent rendements observés et estimés, modèles de volatilité comme GARCH, expositions factorielles et risque de perte. Ces analyses sont indicatives. Le moteur reconstruit ses entrées, dont les moyennes historiques, les covariances et les signaux factoriels ou macro datés pour les méthodes qui en ont besoin. Momentum et EWMA sont particulièrement sensibles à la date de coupure."],
    ],
    [
      ["Replay the strategies on historical data", "Rejouer les stratégies dans le passé"],
      ["The engine recalculates each method quarterly using the same 60-month eligibility rule and the stock list at each decision. It applies new targets one month later and rebalances monthly. The replay models a charge of 0.10% on the value of securities traded. The comparable test runs from December 2023 through December 2025. The January 2021 to November 2023 development period supplies the goal projection blocks.",
        "Le moteur recalcule chaque méthode chaque trimestre avec la même règle des 60 mois et la liste d’actions connue à chaque décision. Il applique les nouvelles cibles un mois plus tard et rééquilibre chaque mois. Le test simule des frais de 0,10 % sur la valeur des titres échangés. Le test commun couvre décembre 2023 à décembre 2025. Les projections d’objectifs utilisent les mois de développement, de janvier 2021 à novembre 2023."],
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
    [
      ["Interpret the limitations of the results", "Interpréter les limites des résultats"],
      ["The replay uses dated stock membership. Missing original publication timestamps and the retrospective ETF registry limit real-time interpretation. Requiring five years favors older, well-covered assets. Rare losses are hard to assess with 25 test months. The common expected return shrinks each security’s historical mean halfway toward the median, which can raise Treasury ETF estimates in an equity-heavy universe.",
        "Le replay utilise les listes d’actions de l’époque. Les dates de publication manquantes et le registre rétrospectif des ETF limitent l’interprétation en temps réel. Exiger cinq ans favorise les titres anciens et bien couverts. Vingt-cinq mois de test donnent peu de recul sur les pertes rares. Le rendement estimé rapproche la moyenne de chaque titre à mi-chemin vers la médiane, ce qui peut relever les estimations des ETF du Trésor dans cet univers dominé par les actions."],
    ],
  ];
  function render() {
    const lang=window.RM.language==="fr"?1:0;
    const t=window.RM.t;
    const {methods,sources,dependency}=window.StrategyMethods;
    const catalogue=document.getElementById("strategy-library");
    catalogue.innerHTML=groups.map(([title,names])=>{
      const keys=Array.isArray(names)?names:names.split(" ");
      const entries=keys.map(key=>{
        const method=methods[key], source=sources[method[3]||"returns"];
        return `<details><summary>${esc(strategyName(key))}</summary>
          <p>${esc(method[lang])}</p>
          ${method[2]?`<p><code>${esc(method[2])}</code></p>`:""}
          <p class="muted"><strong>${esc(t("catalogueInputs"))}</strong> · ${esc(source[lang])}</p>
          <p><strong>${esc(lang?"Effet de la date des données":"Effect of the data cutoff")} · ${esc(dependency[key][lang])}</strong> ${esc(dependency[key][lang+2])}</p></details>`;
      }).join("");
      return `<section><h2>${esc(title[lang])}</h2>${entries}</section>`;
    }).join("");
    document.getElementById("methodology-stages").innerHTML=stages.map(([title,body])=>
      `<li><h2>${esc(title[lang])}</h2><p>${esc(body[lang])}</p></li>`).join("");
  }
  document.addEventListener("riskmatch:language",render);
  render();
})();
