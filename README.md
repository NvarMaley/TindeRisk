# RiskMatch V3

RiskMatch est une application de simulation de portefeuille réalisée pour **QARM II**. À partir d’un mandat fictif, elle construit des allocations sous contraintes, puis permet de comparer leurs performances historiques, leur risque et le financement des objectifs du client.

## Présentation au professeur

| Support | Ce qu’il permet de vérifier |
|---|---|
| **Application complète** | Le parcours Mandat → Profil de risque → Stratégies → Mes matchs. Elle utilise les archives autorisées sur l’ordinateur qui héberge RiskMatch. Le partage individuel peut passer par le [cadre Streamlit](apps/streamlit/README.md). |
| **Démo Streamlit publique** | Un cas Markowitz reproductible qui compare deux limites de perte sur des rendements synthétiques. [Ouvrir la démo](https://nvarmaley.github.io/TindeRisk/) |
| **Notebook portable** | Les calculs et contrôles des 27 chapitres, avec exemples numériques synthétiques. [Ouvrir le notebook](notebooks/RiskMatch_V3.ipynb) |
| **Revue académique** | Les résultats vérifiés, la correspondance avec les chapitres et les limites de la démonstration. [Revue et guide de présentation](docs/PROFESSOR_REVIEW.md) |

Pour voir les effets du moteur, charge **l’exemple** du mandat, réponds aux 30 cartes de Discovery, sélectionne deux stratégies et calcule une répartition dans **Mes matchs**. Change les budgets ou le taux d’actualisation pour comparer le résultat. La confirmation enregistre un portefeuille simulé.

## Ce qui est calculé dans la version complète

- **Univers et période.** Le catalogue client comprend **642 actions US, 15 ETF d’actions, 5 ETF du Trésor et une poche de cash USD**. Les poids affichés utilisent 60 rendements mensuels de janvier 2021 à décembre 2025. Le backtest reconstitue les choix à leurs dates et compare les méthodes sur 25 mois, de décembre 2023 à décembre 2025. Les chapitres de recherche conservent leurs propres univers et périodes. [Données et biais](docs/UNIVERS_DONNEES_STRATEGIES.md)
- **Mandat et sélection.** Classes autorisées, risque et plafonds influencent les poids. Les exclusions facultatives utilisent l’émetteur et le secteur des actions directes. Elles écartent les ETF d’actions dont les positions historiques ne peuvent être filtrées. Le moteur met en avant jusqu’à six cartes compatibles et distinctes et laisse le reste du catalogue accessible. [Mandat](docs/CLIENT_MANDATE.md) · [Audit des 50 méthodes](docs/AUDIT_STRATEGIES_ET_PORTEFEUILLE.md)
- **Résultat.** Le bilan distingue les poids, le backtest et la projection. Il consolide les positions communes, mesure la concentration et le risque lié aux covariances. Il simule 1 000 trajectoires à partir de blocs historiques communs aux actifs, applique les apports et les dépenses du mandat, et affiche un capital restant, un gain net et une valeur actuelle au taux choisi. [Explication des résultats](docs/PORTFOLIO_MATCHING.md)
- **Suivi.** Le volet Gestion dynamique compare des règles sur les mêmes mois historiques. Le suivi simulé des cours nécessite un flux Alpaca configuré sur le serveur. [Architecture et suivi](docs/CLIENT_FLOW.md) · [Configuration locale](.env.example)

Les résultats dépendent d’une archive courte avec certaines dates de publication indisponibles. Le registre d’ETF est établi rétrospectivement et les positions internes des ETF d’actions ne sont pas filtrables sur toute la période. La projection décrit des résultats conditionnels à ces données et hypothèses.

## Lancer et vérifier

Sur Mac, installer **Python 3.12**, exécuter `./INSTALL.command`, puis `./START.command`. L’application est disponible sur [le serveur local](http://127.0.0.1:3000/) et Jupyter sur [le port 8888](http://127.0.0.1:8888/lab). Les services écoutent sur l’adresse de boucle locale. `./STOP.command` arrête les services du projet.

```bash
.venv/bin/python -m pytest -q
node --test tests/web/*.test.cjs
.venv/bin/python scripts/check_notebooks.py
.venv/bin/python scripts/execute_notebook.py
```

Sur l’ordinateur qui détient les archives, `.venv/bin/python scripts/execute_notebook.py --historical --save-outputs` régénère la copie historique dans `data/reports/`. Les droits de redistribution s’appliquent à cette copie et aux données sources. Le dépôt public contient le code, le notebook portable et la documentation. [Reproduction](notebooks/README.md) · [Données et sécurité](docs/DATA_SECURITY.md)

Pour approfondir, voir l’[architecture](docs/ARCHITECTURE.md), le [guide quantitatif](docs/QUANT_GUIDE_A_Z.md), les [questions Discovery](docs/RISKMATCH_BEHAVIORAL.md), les [expériences](docs/EXPERIMENT_REGISTRY.md) et la [liste de travail](CHECKLIST_A_Z.md).
