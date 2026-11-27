# Audit de RiskMatch V3 du 26 novembre 2026

Ce document conserve les mesures et les incidents observés le 26 novembre. Pour le parcours actuellement servi et les vérifications de livraison, voir la [revue académique](PROFESSOR_REVIEW.md) et le [guide des résultats](PORTFOLIO_MATCHING.md).

## Contre-vérification après correction

Les tableaux ci-dessous conservent le diagnostic initial. Le moteur corrigé personalized-v3 a ensuite été testé par HTTP sur le port 3002. Résultats du mandat de référence : 35 cartes distinctes, 5 pour le mandat Treasury restreint et 1 pour le mandat cash. Budgets manuels, minimum de variance, comparaison par objectif et export papier du mandat de référence ont abouti. Les deux estimations de risque en queue concordent sur chaque carte des trois cas. Les projections affichent la sensibilité aux deux moitiés de la fenêtre de développement. Les contraintes incompatibles avec la simulation dynamique sont signalées dès le mandat. Le notebook historique complet passe les 83 cellules. La version servie sur le port 3000 doit être redémarrée pour y retrouver les sauvegardes et le moteur corrigé. Les limites liées aux publications, aux ETF, aux sorties sans prix et à la validation humaine subsistent.

## Diagnostic au moment de l’audit

Le code local réalise le parcours imaginé pour les mandats USD pris en charge. Le site actuellement ouvert sert un ancien moteur. Sur la même machine et pour le même mandat, les cartes et le classement divergent. Corriger cet écart avant une présentation. Les calculs du nouveau moteur sont reproductibles sur les archives locales. Leur valeur prédictive, la calibration comportementale et l’investissabilité historique demeurent ouvertes.

## Expérience

Mandat issu de configs/mandate-example.json avec date portée au 25 novembre pour le rendre admissible au moteur actuel. Capital de 100 000 USD, apport de 1 000 USD par mois, objectif de 240 000 USD en novembre 2036, enveloppe de stress de 20 %. Préférences de style neutres. Appels directs au serveur sur le port 3000 et au moteur Python du dossier courant. Aucune sauvegarde personnelle utilisée.

| Cas | Instruments admissibles hors cash | Règles ayant une trajectoire comparable | Cartes après regroupement |
|---|---:|---:|---:|
| Mandat de référence, aversion 15 | 570 | 48 | 45 |
| Même mandat, aversion 30 | 570 | 48 | 45 |
| Treasuries et cash, aversion 27, maximum de 25 % par ligne, volatilité de 7 %, stress de 8 % | 5 | 31 | 5 |
| Cash seul | 0 | 1 | 1 |

Pour chaque règle calculée des quatre cas, contrôle des poids finis, de leur somme, de leur signe, des plafonds par ligne et du stress. Pour chaque carte affichable, recalcul du rendement composé annualisé, de la volatilité annualisée, du drawdown et de l’ES selon la convention du code. Aucun écart sur ces contrôles. Le notebook vérifie en plus le plafond de volatilité du mandat Treasury. La conformité à une formule implémentée et la pertinence de la formule pour le client demandent deux jugements distincts.

Les archives locales ont permis de rejouer les 83 cellules de code en mode historique. Les routes du notebook utilisent le gestionnaire HTTP du dépôt en mémoire. Les campagnes volumineuses bénéficient de caches et de contrôles d’intégrité. Ce replay ne réentraîne pas chaque modèle ni ne compare chaque observation au fournisseur. Les 181 tests Python, 5 sous-tests et 36 tests JavaScript passent. Le contrôle du site en fonctionnement a porté sur ses réponses HTTP. Aucun test visuel exhaustif de navigation, ni certification externe des données ou du conseil.

## Écarts à traiter dans l’ordre

1. **Version du serveur.** Sur le port 3000, health indique client_flow 28, alors que apps/api/server.py déclare 29. Pour le mandat de référence, prepare annonce 37 et cards renvoie 21 cartes historical-usd-v1 avec Black–Litterman en tête. Le dépôt renvoie 45 cartes personalized-v2 avec la référence cash en tête. Le front accepte une réponse réussie de l’ancien moteur. Redémarrer sur le bon backend et vérifier la version du jeu de cartes avant affichage. Critère de réception sur ce jeu figé : mêmes noms, versions, poids et ordre entre l’API servie et le calcul de référence.
2. **Univers historique.** Le vecteur de prévisions de décembre 2025 définit les actifs, puis aligned intersecte les historiques complets. L’appartenance des actions est contrôlée aux dates de construction, mais un titre sorti avant la date finale peut déjà avoir disparu de la sélection. Les dates de disponibilité nulles sont admises et le filtre utilise la date de l’audit de données plutôt que chaque décision historique. Risque de biais de survie et d’information future, dont l’ampleur reste à mesurer. Reconstruire l’univers à chaque date, traiter les sorties et comparer au résultat actuel sous les mêmes coûts.
3. **Stratégie simulée et portefeuille recommandé.** Le chapitre 25 ajuste les cibles à trois dates, puis rééquilibre mensuellement vers des poids fixes sur chacune des deux périodes d’évaluation. Il ne rejoue donc pas chaque mois un signal de momentum ou de changement de régime. Les prévisions communes interviennent dans la cible finale, les cibles historiques utilisent des estimations antérieures simplifiées. L’historique affiché renseigne sur cette variante. Pour évaluer la règle proposée, archiver les prévisions à chaque date, respecter le délai d’exécution, réestimer au rythme annoncé et suivre les entrées/sorties de l’univers. Le chapitre 23 dispose déjà d’un registre et d’un moteur à exécution différée.
4. **Mesure de perte extrême.** prototype.metrics prend la moyenne des pires ceil(5 % × n) mois. analytics.tail_risk.empirical pondère la fraction du dernier mois pour atteindre exactement 5 %. Sur 25 mois, la carte donne le même poids aux deux pires mois, alors que le chapitre 11 attribue 80 % au pire et 20 % au deuxième. Unifier et tester les deux écrans sur la même série.
5. **Coût du cash.** Dans le chapitre 25, simulate emploie la dernière colonne comme une ligne négociée. Le financement initial et les transferts avec le cash entraînent des frais sur cette colonne. Le chapitre 23 exclut le cash du notionnel négocié. Fixer une convention commune et séparer explicitement frais d’entrée éventuels et frais de transaction. Vérifier le cash seul, un achat financé par cash et un transfert entre stratégies.
6. **Probabilités et classement.** Les cartes tirent 256 trajectoires à partir de seulement 35 rendements mensuels de développement et de blocs de six mois. L’allocation finale emploie 1 000 trajectoires sur la même histoire. Multiplier les tirages ne crée pas de nouveaux régimes économiques. L’évaluation finale contient 25 mois. Le score combine stress, rendement, objectifs et préférences avec des coefficients choisis. Le cash arrive premier dans les deux mandats larges testés. Calibrer les pondérations et vérifier si le classement se maintient sous d’autres fenêtres, coûts, régimes et priorités. Afficher la sensibilité du classement et des probabilités.
7. **Choix et suivi.** Une permission de vente à découvert ne crée pas de proposition de ce type. Les plafonds d’émetteur ou secteur exigés, le CHF, la couverture de change exigée ou certaines contraintes bloquent le matching. L’optimisation des budgets par défaut minimise la variance des rendements de développement. La variante par objectif compare une grille de budgets et se concentre sur la priorité la plus haute. Avec les deux premières cartes, le mix manuel 60/40 respecte le mandat et donne un stress modélisé de 1,165 %. L’optimisation minimum-variance choisit 100 % de la poche cash. Le suivi dynamique refuse notamment le plafond strict de 25 % du mandat Treasury testé, ainsi que les flux datés. Afficher dès le mandat quelles étapes seront disponibles.
8. **Traçabilité et couverture.** Les cartes proches sont regroupées sous 1 % de distance de rotation. Deux méthodes peuvent avoir des poids actuels proches et des trajectoires passées différentes. L’interface devrait expliquer quel historique sert à la carte. Dans le cas cash seul, constrained_utility n’est ni produite ni assortie d’une raison dans unavailable. Le fichier d’exemple daté du 24 novembre précède aussi la date minimale acceptée. Ajouter un diagnostic par méthode et un mandat d’exemple utilisable tel quel.

## Contrôle chapitre par chapitre

| N° | Élément vérifié | Appréciation et limite |
|---|---|---|
| 01 | Aperçu du mandat, flux, capacité de perte, contraintes bloquantes | Fonctionne sur les exemples USD. Une contrainte sectorielle stricte ne peut pas être certifiée. |
| 02 | Session, réponses, score, construction avec deux aversions | La personnalisation réagit. Le pilote humain, le test-retest et les différences FR/EN restent à valider. |
| 03 | Catalogue daté, classes admissibles et panel commun | 1 474 entrées au catalogue, 575 dans le panel. Le filtre rétrospectif limite l’interprétation. |
| 04 | Inventaire et provenance des sources | Traçabilité locale disponible. Droits de redistribution et justesse des observations originales à valider séparément. |
| 05 | Snapshot et contrôles d’intégrité | Relecture réussie. La date réelle de disponibilité de chaque donnée historique reste un point critique. |
| 06 | Séries de rendements, devises, alignement | Le panel utilisé en USD contient 57 500 rendements mensuels finis. Le matching CHF reste indisponible. |
| 07 | Catalogue statistique et comparaison SPY/IEF sur dates communes | Les fiches et la comparaison répondent. Couverture variable selon l’actif, la mesure et la fenêtre. |
| 08 | Archive des prévisions et exemple par actif | 1 008 calculées, 464 estimations de repli, 2 indisponibles. Les modèles complets ne couvrent donc pas chaque fiche. |
| 09 | Rapport de risque et matrice alignée | 574 calculs complets, 441 partiels, 457 descriptifs, 2 indisponibles. Le matching utilise une covariance régularisée. |
| 10 | Archive factorielle et régression par actif | 1 022 calculés, 445 références analytiques, 7 indisponibles. La présence d’un facteur ne prouve pas sa prime future. |
| 11 | Queues, dépendance et comparaison | 1 008 calculés, 463 descriptifs, 3 indisponibles. Convention ES différente sur les cartes. |
| 12 | Les onze types d’objectifs évalués individuellement | Les objectifs modifient l’évaluation. Revenu distribué, protection contractuelle et couverture des passifs restent approximés ou indisponibles. |
| 13 | Références, flux, frais, rapprochement des valeurs | Comptabilité testée. La convention cash change entre les moteurs. |
| 14 | Moyenne–variance, contraintes, Sharpe et utilité sur deux univers | Calculs disponibles. Maximum Sharpe indisponible sur le mandat Treasury testé. Les grands solveurs retiennent en général 64 instruments au plus dans ce cas. |
| 15 | Black–Litterman et poids résultants | Carte calculée sur le mandat de référence. Les vues et l’ancrage sont des hypothèses de recherche. |
| 16 | Parité de risque, HRP, HERC et diversification | Les méthodes produisent des poids contrôlés. Cible plafonnée ou ajustée vers le cash peut s’écarter de la règle théorique. |
| 17 | CVaR, CDaR, Omega et Sortino | CVaR et CDaR produisent des cartes. Omega et Sortino n’ont pas d’historique comparable sur les trois origines du mandat de référence. |
| 18 | Robuste, rééchantillonnage, Kelly et entropie | Règles calculées. Quatre tirages pour l’incertitude de certains optimiseurs du registre personnalisé ; stabilité à éprouver. |
| 19 | ETF passifs, facteurs et actions long-only | Indice à 100 % sur un ETF bloqué par le plafond. Certaines règles aboutissent à des poids proches ou utilisent un portefeuille de repli. |
| 20 | Alternatives et expositions signées en recherche | Momentum et plusieurs alternatives long-only sont proposées. Quatre règles signées restent hors cartes. |
| 21 | Bons et obligations du Trésor, coupons, duration et passifs | Module de recherche distinct. Le mandat Treasury investit ici via cinq ETF et du cash. |
| 22 | Contrats futures, roulement et marge | Simulations de recherche. Calendriers de livraison, liquidité et marges historiques insuffisamment certifiés pour les cartes. |
| 23 | Walk-forward, références, délais, coûts et sensibilité | Mécanismes utiles. Une période réexaminée et une cohorte finale ne constituent pas un nouvel échantillon indépendant. |
| 24 | Stress et Monte Carlo sur deux univers | Scénarios et sensibilités calculés. Une perte supérieure au pire scénario modélisé reste possible. |
| 25 | Matching, contraintes, budgets manuels, variance et objectifs | Le dépôt personnalise réellement. Le serveur ouvert renvoie l’ancien jeu. Voir les quatre expériences et la matrice ci-dessous. |
| 26 | Politiques dynamiques et sensibilité aux frais | Replay historique réussi sur le mandat supporté. Un mandat accepté pour les cartes peut ensuite être refusé au suivi. |
| 27 | Export papier, manifeste et empreintes | Export rapproché sur le cas historique. La reproductibilité du calcul local dépend des archives privées. |

## Statut de chaque règle du registre

Les colonnes indiquent le résultat de l’exécution locale pour chaque mandat. « Regroupée » signifie que la règle a produit des poids, puis a été rattachée à une carte voisine. « Hors cartes » désigne une règle réservée à la recherche. Les libellés d’échec détaillent la cause observée.

| Méthode | Référence | Aversion 30 | Treasury | Cash seul |
|---|---|---|---|---|
| active_long_only | carte | carte | regroupée | capacité datée insuffisante |
| all_weather | carte | carte | capacité insuffisante | capacité datée insuffisante |
| black_litterman | carte | carte | regroupée | capacité datée insuffisante |
| capm_utility | carte | carte | carte | capacité datée insuffisante |
| constrained_utility | carte | carte | regroupée | absente |
| core_satellite | carte | carte | regroupée | capacité datée insuffisante |
| cross_sectional_momentum | carte | carte | regroupée | capacité datée insuffisante |
| cta_etf_proxy | hors cartes | hors cartes | hors cartes | hors cartes |
| defensive_reference | carte | carte | regroupée | carte |
| entropy_utility | carte | carte | carte | capacité datée insuffisante |
| equal_weight | carte | carte | regroupée | capacité datée insuffisante |
| ewma_utility | carte | carte | regroupée | capacité datée insuffisante |
| factor_investing | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_investment | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_liquidity | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_low_volatility | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_momentum | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_profitability_proxy | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_quality | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_size | carte | carte | signal absent ou plat | capacité datée insuffisante |
| factor_value | carte | carte | signal absent ou plat | capacité datée insuffisante |
| fractional_kelly | carte | carte | regroupée | capacité datée insuffisante |
| global_macro | regroupée | regroupée | fourchette stratégique infaisable | capacité datée insuffisante |
| herc | carte | carte | regroupée | capacité datée insuffisante |
| hrp | carte | carte | carte | capacité datée insuffisante |
| inverse_variance | carte | carte | regroupée | capacité datée insuffisante |
| kelly | carte | carte | regroupée | capacité datée insuffisante |
| long_short | hors cartes | hors cartes | hors cartes | hors cartes |
| market_neutral | hors cartes | hors cartes | hors cartes | hors cartes |
| maximum_diversification | carte | carte | regroupée | capacité datée insuffisante |
| maximum_omega | historique non comparable | historique non comparable | regroupée | capacité datée insuffisante |
| maximum_sharpe | carte | carte | tangence positive infaisable | capacité datée insuffisante |
| maximum_sortino | historique non comparable | historique non comparable | regroupée | capacité datée insuffisante |
| mean_reversion | carte | carte | carte | capacité datée insuffisante |
| mean_variance_utility | carte | carte | regroupée | capacité datée insuffisante |
| minimum_cdar | carte | carte | regroupée | capacité datée insuffisante |
| minimum_cvar | carte | carte | regroupée | capacité datée insuffisante |
| minimum_variance | carte | carte | regroupée | capacité datée insuffisante |
| multi_strategy | carte | carte | capacité insuffisante | capacité datée insuffisante |
| passive_etfs | carte | carte | regroupée | capacité datée insuffisante |
| passive_index | ETF seul hors plafond | ETF seul hors plafond | ETF seul hors plafond | capacité datée insuffisante |
| regime_switching | carte | carte | fourchette stratégique infaisable | capacité datée insuffisante |
| resampled_utility | carte | carte | regroupée | capacité datée insuffisante |
| risk_parity | carte | carte | regroupée | capacité datée insuffisante |
| robust_utility | carte | carte | regroupée | capacité datée insuffisante |
| smart_beta_equal | regroupée | regroupée | regroupée | capacité datée insuffisante |
| smart_beta_factor | carte | carte | signal absent ou plat | capacité datée insuffisante |
| smart_beta_fundamental | carte | carte | capacité des cibles insuffisante | capacité datée insuffisante |
| statistical_arbitrage | hors cartes | hors cartes | hors cartes | hors cartes |
| tactical_allocation | carte | carte | fourchette stratégique infaisable | capacité datée insuffisante |
| tail_hedge_proxy | regroupée | carte | capacité insuffisante | capacité datée insuffisante |
| time_series_momentum | carte | carte | regroupée | capacité datée insuffisante |
| tracking_error | carte | carte | carte | capacité datée insuffisante |
| volatility_target | carte | regroupée | capacité insuffisante | capacité datée insuffisante |
| wasserstein_utility | carte | carte | regroupée | capacité datée insuffisante |

## Contre-calculs et preuves complémentaires

Dans la partition mensuelle actions, 335 000 lignes, 191 rendements totaux manquants, zéro doublon sur (instrument, début, fin), zéro rendement inférieur à −100 %. Pour la partition mensuelle ETF, respectivement 7 396 lignes, 27 manquants, zéro doublon et zéro rendement inférieur à −100 %. La colonne availability_time est vide sur **toutes** les lignes des deux partitions. Cela ne prouve pas que les rendements sont faux. Leur horodatage de publication ne permet pas ici de certifier leur disponibilité à l’instant historique de décision.

| Carte du mandat de référence | ES mensuelle 95 % de la carte | ES du chapitre 11, mêmes 25 mois |
|---|---:|---:|
| Équipondération | 1,929 % | 2,127 % |
| Maximum Sharpe | 1,306 % | 1,515 % |
| Référence cash | −0,315 % | −0,306 % |

La perte est signée dans cette comparaison. Sur 100 000 USD de capital intégralement affecté au cash et un tarif de 10 points de base, la fonction de transaction du chapitre 25 facture 99,90 USD dès l’ouverture. Ces écarts ont été reproduits numériquement.

Les archives walk-forward USD à 53 méthodes du chapitre 23 permettent aussi de distinguer le sort des quatre règles exclues des cartes. Sur la cohorte large, long/short et le proxy CTA sur ETF sont calculés, market neutral et arbitrage statistique sont indisponibles. Sur le noyau ETF, seul le proxy CTA est calculé parmi ces quatre règles. Le produit futures effectivement négocié exige des données différentes de ce proxy.

### Rejouer les contrôles standard depuis la racine du projet

```sh
.venv/bin/python -m pytest -q
node --test tests/web/*.test.cjs
PYTHONPATH=src .venv/bin/python scripts/execute_notebook.py --in-process --historical
curl -sS http://127.0.0.1:3000/api/health
```

Les origines de construction viennent de src/riskmatch/personalized_matches.py (construct et _run). La constitution du panel est dans optimization/mean_variance_report.py (aligned), le registre dans backtesting/walk_models.py (fit_models), les frais dans backtesting/baselines.py (trade), les deux conventions de risque dans prototype.py (metrics) et analytics/tail_risk.py (empirical). Le rééquilibrage entre stratégies est implémenté dans selection/sleeve_ledger.py. Les cas rejoués par chapitre sont explicités dans scripts/notebook_evidence.py. Les fichiers archivés proviennent de data/processed sur cette installation.
