# Audit des stratégies et du portefeuille final

Contrôle du 27 novembre 2026. L’audit couvre les 47 méthodes candidates, SPY comme benchmark et les deux ratios conservés en recherche. Les résultats décrivent le moteur local. Une règle calculable et un backtest complet permettent une démonstration, avec une validation limitée à l’archive et aux hypothèses testées.

## Protocole de contrôle

Le moteur construit chaque cible à partir des 60 mois précédant la décision. Il retient les rendements totaux mensuels en USD, le taux sans risque Fama–French et les listes d’actions datées. Les signaux comptables et macroéconomiques utilisent leurs propres dates et conditions de disponibilité. Le replay refait les cibles tous les trois mois, attend un mois pour les appliquer, rééquilibre chaque mois et simule 10 points de base sur les titres échangés. Il refuse de compléter un rendement réalisé manquant pour une position détenue.

La première anomalie de l’équipondération venait de la fusion d’Eaton Vance. Le rendement total de février 2021, déjà présent dans l’archive, comprend le rendement de radiation (indicateur CRSP `MthDelFlg=A`). Le moteur demandait pourtant un rendement de mars pour la même action. Le replay transfère désormais en cash la valeur finale des positions dont la fusion et le règlement final sont documentés pour cette fenêtre mensuelle. Il comptabilise le rendement terminal une fois et ne simule aucune vente de l’ancien titre. Pour une fusion réglée en titres, la valorisation des titres reçus est convertie en cash dans le modèle. Le cash est valorisé au taux du mois dès le début de cette période comptable, y compris lorsque le paiement effectif intervient quelques jours plus tard. Le modèle ne suit pas le titre de l’acquéreur. La date de règlement borne l’utilisation du rendement terminal dans les estimations. [Indicateurs de rendement CRSP CIZ](https://www.crsp.org/wp-content/uploads/appendix/FlagType_DE.html)

Deux mandats sont testés avec un indice de prudence de 18/30. Le mandat **standard** autorise les actions, les ETF du Trésor et le cash. Le mandat **Trésor + cash** impose aussi une perte en stress au plus de 8 %, une volatilité estimée au plus de 7 % et un poids par position au plus de 25 %. Pour chaque carte, le contrôle vérifie que les poids sont positifs ou nuls, totalisent 100 % et que le test contient les mêmes 25 mois. Pour le mandat restreint, il vérifie les classes autorisées et les trois limites supplémentaires.

## Corrections vérifiées

- **Sorties liées à une fusion.** Le traitement des règlements documentés a rétabli les 11 historiques interrompus dans le cas standard. Les rendements réellement manquants continuent à interrompre le replay.
- **Nº 24, défense contre les pertes extrêmes.** La valeur d’ouverture de la fenêtre de 12 mois entre désormais dans la recherche du sommet de SPY. Un test reproduit une baisse de 15 % dès le premier mois et vérifie le retour à la cible normale après un rebond suffisant.
- **Nº 45, multi-stratégies.** Les corrélations diagnostiques utilisent les volatilités observées des poches. Une poche constante donne une corrélation indéfinie. Le plancher de 2 % continue à s’appliquer dans le calcul des budgets.
- **Catalogue et fiches.** Les explications précisent le panier utilisé, le rôle des plafonds, les hypothèses de chaque méthode et les résultats individuels derrière les cartes regroupées.

## Lecture des résultats

- **Carte** indique une cible et un replay complet pour le mandat contrôlé. **Regroupée** signifie que l’interface présente une autre méthode ayant des poids finaux proches. Les trajectoires historiques des méthodes regroupées peuvent différer.
- **Incomplet** indique qu’un incident historique empêche une comparaison complète. **Indisponible** indique que le calcul actuel ne produit pas de cible faisable ou que son signal est indisponible. **Recherche** désigne les trois références hors sélection.
- Limites communes à toutes les cartes. Le registre d’ETF a été constitué rétrospectivement. Le filtre de cinq ans favorise les titres anciens et bien couverts. Certaines dates d’origine manquent. Les 25 mois de test donnent une information limitée sur la stabilité et les pertes rares. Les frais et la liquidité sont modélisés. Les poids actuels et le choix d’une carte utilisent des données allant jusqu’à la fin du test.
- Les solveurs matriciels partent généralement d’un sous-ensemble totalisant au plus 64 instruments. Ils retiennent les ETF admissibles et classent les actions par capitalisation datée. Les règles de classement qui parcourent un univers plus large et la référence défensive ont leurs propres restrictions. Le filtrage par capitalisation limite la portée des comparaisons entre familles.

## Résultat des deux replays

| Mandat | Méthodes calculées avec replay complet | Cartes distinctes | Méthodes écartées |
|---|---:|---:|---:|
| Standard · 18/30 | 47 | 45 | 0 |
| Trésor + cash · 18/30 | 28 | 8 | 19 indisponibles sous les contraintes du mandat |

Avant la correction, le mandat standard totalisait 36 méthodes avec un replay complet et 35 cartes. Les 11 méthodes dont l’historique était interrompu terminent désormais le replay standard.

Les quatre modes d’allocation ont passé les contrôles de poids et de faisabilité sur les deux mandats. La répartition manuelle 60/40 des deux premières cartes produit une projection de 120 mois, avec des quantiles ordonnés à chaque date. Les trois références restent hors classement.

## Vérification une par une

| Méthode | Entrées et contrôle de cohérence | Limite propre à la méthode | Standard | Trésor + cash |
|---|---|---|---|---|
| [1. Équipondération](#audit-1) `equal_weight` | Parts égales parmi les actifs autorisés, puis redistribution sous plafonds. | Le nombre d’actions domine la répartition par classe. Un panier large peut perdre son replay au premier rendement réalisé manquant. | Carte | Regroupée |
| [2. Variance minimale](#audit-2) `minimum_variance` | Minimise la variance Ledoit–Wolf des 60 derniers mois sous plafonds, sur les ETF admissibles et les actions retenues par capitalisation, jusqu’à 64 titres au total. Le moteur contrôle ensuite le risque sur la cible du mandat avec l’estimateur commun. | Le minimum vaut pour la covariance et les titres du solveur. L’ajustement défensif peut modifier la cible. Les poids peuvent se concentrer sur les ETF courts et changer si les corrélations évoluent. | Carte | Regroupée |
| [3. Variance inverse](#audit-3) `inverse_variance` | Prend l’inverse de chaque variance individuelle de la matrice Ledoit–Wolf estimée sur 60 mois. Utilise les ETF admissibles et les plus grandes actions admissibles jusqu’à 64 titres, applique les plafonds, puis vérifie le risque du portefeuille. | Les poids de départ ignorent les corrélations entre titres et peuvent cumuler des expositions similaires. La régularisation réduit les écarts de variance entre actifs. | Carte | Carte |
| [4. Parité des risques](#audit-4) `risk_parity` | Utilise la covariance Ledoit–Wolf sur 60 mois des ETF admissibles et des actions retenues par capitalisation, jusqu’à 64 titres. Le solveur vise une contribution égale par titre et tient compte des plafonds avant le contrôle du mandat. | L’égalité porte sur le risque par titre dans le modèle du solveur. Les plafonds, les différences d’estimateur et l’ajustement défensif peuvent déplacer les contributions finales. | Carte | Regroupée |
| [5. Parité hiérarchique HRP](#audit-5) `hrp` | Utilise la covariance Ledoit–Wolf sur 60 mois et jusqu’à 64 titres. Ordonne les titres via un regroupement à liaison moyenne, coupe la liste ordonnée en moitiés successives et répartit le capital entre elles selon l’inverse de leur variance estimée. | Chaque partage utilise la variance interne des deux moitiés. Leur covariance mutuelle intervient dans le contrôle du risque du portefeuille. Les groupes et les poids peuvent changer si l’ordre des titres change. | Carte | Regroupée |
| [6. Contributions hiérarchiques HERC](#audit-6) `herc` | Variante à deux niveaux. Coupe l’arbre des corrélations Ledoit–Wolf estimées sur 60 mois en trois groupes au plus, sur 64 titres au maximum. Vise une contribution égale au risque dans chaque groupe puis entre les portefeuilles des groupes. | Avec des plafonds actifs, le moteur ajuste les poids des groupes ou redistribue les excédents par titre si les poids internes sont incompatibles avec les plafonds. Les parités peuvent alors s’écarter de leurs cibles. Le nombre de groupes est un choix et un groupe de petite taille peut concentrer le capital. | Carte | Regroupée |
| [7. Diversification maximale](#audit-7) `maximum_diversification` | Maximise la volatilité moyenne pondérée rapportée à celle du portefeuille. | Sensible aux corrélations instables. Une bonne valeur du ratio ne garantit pas une perte faible. | Carte | Regroupée |
| [8. Sharpe maximal](#audit-8) `maximum_sharpe` | Utilise les rendements estimés par classe, le taux du cash et la covariance. | Très sensible aux erreurs de moyenne et au marché de référence. Le Sharpe d’estimation et le Sharpe du test mesurent des périodes différentes. | Carte | Indisponible |
| [9. Moyenne-variance](#audit-9) `mean_variance_utility` | Utilise les moyennes régularisées par classe et pénalise la covariance par le coefficient du profil. | Moyennes bruyantes et coefficient heuristique. La variance pénalise aussi les surprises positives. | Carte | Regroupée |
| [10. Erreur de suivi](#audit-10) `tracking_error` | Minimise la variance de l’écart à SPY, sous bornes d’investissement. | SPY est une référence actions US. Un écart élevé est attendu pour un mandat obligataire, même s’il répond bien au client. | Carte | Carte |
| [11. Black–Litterman](#audit-11) `black_litterman` | Prior à poids égaux plafonnés. Vues actions et Treasuries dérivées de la fenêtre commune. | Prior et vues utilisent une information partagée. Les coefficients de confiance et le choix du prior influencent le résultat. | Carte | Regroupée |
| [12. CAPM](#audit-12) `capm_utility` | Utilise les rendements en excès des titres et de SPY après déduction du même taux mensuel. Le bêta a été corrigé pour ce contrôle. | Un seul facteur actions explique mal certains risques de taux, d’inflation ou de duration. Bêta et prime changent selon la période. | Carte | Regroupée |
| [13. EWMA](#audit-13) `ewma_utility` | Donne davantage de poids aux mois récents avec une décroissance de 0,94. | La décroissance est fixée. Un choc récent peut dominer une estimation courte. | Carte | Regroupée |
| [14. Allocation robuste](#audit-14) `robust_utility` | Pénalise les moyennes et covariances à partir d’incertitudes obtenues par blocs. | Le moteur utilise quatre tirages pour cette estimation interne. La marge est sensible au tirage et ne certifie pas un pire cas réel. | Carte | Regroupée |
| [15. Rééchantillonnage](#audit-15) `resampled_utility` | Optimise sur des rééchantillonnages de la fenêtre et moyenne les poids obtenus. | Quatre tirages internes et une seule archive. Le rééchantillonnage réutilise l’information disponible. | Carte | Carte |
| [16. Wasserstein](#audit-16) `wasserstein_utility` | Applique une pénalité de norme aux poids avec un rayon issu des perturbations de l’estimation. | Le rayon repose sur une calibration courte et simplifiée. L’étiquette désigne ici une pénalisation approchée, dont le rayon n’a pas été validé hors échantillon. | Carte | Carte |
| [17. Kelly](#audit-17) `kelly` | Maximise le logarithme moyen du capital après les scénarios mensuels observés. | Sensible aux mois extrêmes absents et aux erreurs d’estimation. Les plafonds et le stress peuvent modifier le résultat théorique. | Carte | Carte |
| [18. Kelly fractionnaire](#audit-18) `fractional_kelly` | Combine 25 % de Kelly et 75 % de l’équipondération plafonnée parmi les titres du solveur. | La fraction est fixe. Elle réduit la concentration dans certains cas, sans garantir une amélioration universelle. | Carte | Carte |
| [19. Entropie](#audit-19) `entropy_utility` | Ajoute un terme favorisant la répartition à l’utilité moyenne-variance. | Le poids de l’entropie est un choix. Répartir davantage le capital peut quand même concentrer les facteurs de risque. | Carte | Regroupée |
| [20. Rendement-risque sous contraintes](#audit-20) `constrained_utility` | Utilise la moyenne par classe, la covariance commune et les chocs du mandat dans les contraintes. La volatilité est revalidée. | Le résultat dépend de l’estimateur, des chocs et du sous-ensemble. La perte réelle peut dépasser les chocs testés. | Carte | Regroupée |
| [21. CVaR minimale](#audit-21) `minimum_cvar` | Minimise l’ampleur des pertes dans les 5 % de mois les plus défavorables de la fenêtre. | Trois mois environ représentent la queue sur 60 observations. Dépend fortement des extrêmes observés. | Carte | Regroupée |
| [22. CDaR minimale](#audit-22) `minimum_cdar` | Optimise les plus forts reculs d’une courbe additive construite avec les rendements mensuels. | Le solveur utilise une courbe additive. Le drawdown affiché du portefeuille historique se mesure sur une courbe composée. | Carte | Regroupée |
| [23. Ciblage de volatilité](#audit-23) `volatility_target` | Part d’une cible actions–Treasuries 60/40 et réduit l’exposition si la volatilité sur 36 mois dépasse 10 %. | La réaction dépend d’une mesure passée et du cash autorisé. Les contraintes peuvent rendre le mélange de départ impossible. | Carte | Indisponible |
| [24. Défense contre les pertes extrêmes](#audit-24) `tail_hedge_proxy` | Bascule la cible actions de 60 % à 20 % si le recul de SPY dépasse 10 % sur sa trajectoire de 12 mois. | La règle réagit après le recul. Elle utilise actions et Treasuries et son efficacité dépend de leur corrélation en crise. | Regroupée | Indisponible |
| [25. Référence défensive](#audit-25) `defensive_reference` | Utilise le cash si possible, sinon cherche une combinaison à faible stress et vérifie sa faisabilité. | Le taux sans risque représente le cash théorique. Le panier de chocs ne représente qu’un ensemble de scénarios. | Carte | Regroupée |
| [26. ETF équipondérés](#audit-26) `passive_etfs` | Répartit parmi les ETF admissibles, avec plafonds. | Plusieurs ETF peuvent détenir des titres identiques. La diversité des fonds ne garantit pas celle des expositions. | Carte | Regroupée |
| [27. Gestion active long-only](#audit-27) `active_long_only` | Estime un alpha face à SPY sur 36 mois, favorise les rangs positifs et utilise l’équipondération si le signal manque. | Alpha bruité et sensible à SPY. Le retour à l’équipondération réduit parfois la différence avec une méthode passive. | Carte | Regroupée |
| [28. Smart beta multifactoriel](#audit-28) `smart_beta_factor` | Moyenne les scores standardisés disponibles avec au moins trois signaux par action. | La combinaison des facteurs varie selon les données disponibles par titre. Couverture et effets sectoriels peuvent influencer le classement. | Carte | Indisponible |
| [29. Pondération fondamentale](#audit-29) `smart_beta_fundamental` | Pondère les titres aux capitaux propres positifs issus des comptes publiés et reliés au titre. | Comparabilité des comptes, fonds propres négatifs et couverture des publications. | Carte | Indisponible |
| [30. Allocation à huit facteurs](#audit-30) `factor_investing` | Construit huit poches de scores datés, avec moyenne des poids. | Les poches peuvent détenir les mêmes sociétés. Un seul signal indisponible peut faire échouer le calcul. | Carte | Indisponible |
| [31. Cœur-satellite](#audit-31) `core_satellite` | Utilise 60 % d’ETF équipondérés et 40 % sélectionnés sur alpha historique. | Budget fixe. Expositions redondantes entre les poches et risque d’alpha instable. | Carte | Regroupée |
| [32. Facteur taille](#audit-32) `factor_size` | Privilégie la plus faible capitalisation parmi les actions admissibles. | Petit parmi le top 1 000. Le filtre 60 mois et les frais fixes limitent l’étude des petites valeurs récentes. | Carte | Indisponible |
| [33. Facteur valeur](#audit-33) `factor_value` | Privilégie un ratio élevé de capitaux propres publiés sur capitalisation. | Comptabilité, secteurs et faibles valeurs de marché peuvent accentuer les scores extrêmes. | Carte | Indisponible |
| [34. Facteur momentum](#audit-34) `factor_momentum` | Classe les actions sur le score factoriel daté 12–1. | Très sensible aux retournements et aux actions qui ont déjà suffisamment d’historique. | Carte | Indisponible |
| [35. Facteur faible volatilité](#audit-35) `factor_low_volatility` | Favorise les faibles fluctuations historiques dans le score daté. | Un historique calme peut masquer une rupture et la stratégie peut concentrer certains secteurs. | Carte | Indisponible |
| [36. Facteur liquidité](#audit-36) `factor_liquidity` | Utilise le volume régressé sur la taille comme indicateur relatif. | Volume et coût de négociation sont différents. Les conditions historiques de marché restent peu vérifiées. | Carte | Indisponible |
| [37. Facteur qualité](#audit-37) `factor_quality` | Utilise le bénéfice rapporté aux actifs et pénalise l’endettement relatif. | Définition partielle de la qualité et sensibilité à la comparabilité sectorielle. | Carte | Indisponible |
| [38. Facteur rentabilité](#audit-38) `factor_profitability_proxy` | Utilise le bénéfice net rapporté aux capitaux propres dans les publications datées. | Les capitaux propres faibles et les éléments exceptionnels peuvent gonfler le score. | Carte | Indisponible |
| [39. Facteur investissement](#audit-39) `factor_investment` | Utilise la croissance annuelle des actifs avec contrôle des exercices comparables. | Les acquisitions et changements de périmètre comptable peuvent dominer le score. | Carte | Indisponible |
| [40. Momentum transversal](#audit-40) `cross_sectional_momentum` | Privilégie le meilleur tiers des titres sur le rendement cumulé des 11 mois précédant le dernier mois. | Le rang est relatif aux titres admissibles. Les retournements et la couverture des sorties peuvent affecter le résultat. | Carte | Carte |
| [41. Suivi de tendance](#audit-41) `time_series_momentum` | Sélectionne les ETF à rendement positif sur 12 mois et pondère selon la volatilité sur 36 mois. | Retard de réaction et allers-retours autour de zéro. Le cash disponible peut modifier le poids final. | Carte | Carte |
| [42. Retour à la moyenne](#audit-42) `mean_reversion` | Compare le rendement sur trois mois à sa distribution historique et écarte les pertes d’au moins 15 % au dernier mois. | Dépend des seuils et du régime. Une baisse extrême peut refléter une dégradation durable. | Carte | Regroupée |
| [43. Allocation tactique](#audit-43) `tactical_allocation` | Compare les tendances de SPY et IEF pour déplacer la cible actions autour de 60 %. | SPY et IEF sont deux proxies. La bande 40–80 % limite la faisabilité d’un mandat très défensif. | Carte | Indisponible |
| [44. Tous régimes](#audit-44) `all_weather` | Pondère SPY, IEF, TIP et SHY selon l’inverse de leur volatilité historique sur 36 mois. | Le panier est limité à ces quatre ETF. Les régimes et les expositions inflation ou duration restent imparfaitement couverts. | Carte | Indisponible |
| [45. Multi-stratégies](#audit-45) `multi_strategy` | Combine momentum transversal, tendance et panier 60/40, avec budgets selon le risque des poches. | Utilise la volatilité de chaque poche pour ses budgets. L’effet des positions communes et des corrélations n’est pas annulé. | Carte | Indisponible |
| [46. Changement de régime](#audit-46) `regime_switching` | Filtre SPY avec deux états à paramètres fixés. Cible 20 % d’actions en régime défavorable, 70 % autrement. | Les paramètres et le seuil sont des choix de modélisation. Des régimes réels peuvent différer de ces deux états. | Carte | Indisponible |
| [47. Macro globale](#audit-47) `global_macro` | Utilise les versions antérieures de croissance et d’inflation et le rendement 12 mois de BIL. | Seuils fixes. Le rendement de BIL est un proxy du niveau des taux. Calendrier et révisions macro restent un enjeu. | Regroupée | Indisponible |
| [48. SPY seul](#audit-48) `passive_index` | Retient SPY à 100 % pour la comparaison de marché, avec un achat au début du test. | Concentration supérieure au plafond client et exposition actions US. Sert de repère même si le mandat exclut les actions. | Recherche | Recherche |
| [49. Sortino maximal](#audit-49) `maximum_sortino` | Optimise le rendement relativement à la dispersion sous le seuil de zéro. | Une fenêtre sans pertes peut donner un dénominateur nul. Le candidat est maintenu en recherche. | Recherche | Recherche |
| [50. Omega maximal](#audit-50) `maximum_omega` | Compare la somme des gains et la somme des pertes sous le seuil choisi. | Même problème de dénominateur nul et sensibilité au seuil et aux rares pertes. | Recherche | Recherche |

## Fiches détaillées dans l’ordre du catalogue

Les cas standard et Trésor + cash partagent la même archive, un score de prudence de 18/30 et les mêmes 25 mois hors estimation. Les 60 mois précédant chaque décision servent à construire les cibles. Les solveurs matriciels retiennent jusqu’à 64 titres en privilégiant les ETF admissibles puis les actions de plus grande capitalisation datée. Les règles de classement peuvent parcourir un panier plus large.

Les résultats de chaque fiche utilisent le replay propre à la méthode, y compris quand la web app rassemble deux cibles finales proches. Les estimations concernent les poids finaux arrêtés au 31 décembre 2025. Le stress est la pire perte dans les scénarios modélisés. Le test de décembre 2023 à décembre 2025 simule la règle qui a produit les poids au fil du temps. Les rendements et volatilités sont annualisés en USD. Le Sharpe historique est calculé au-dessus du cash. Le rendement estimé des cartes utilise la méthode commune par classe, même pour les stratégies qui font appel à une estimation différente en interne.

Les contrôles sur les deux mandats vérifient les poids finaux, les classes autorisées, la somme de 100 %, les limites de stress et la disponibilité des 25 mois. La volatilité et le poids par ligne ont aussi été contrôlés pour le mandat Trésor + cash. Les statuts s’appliquent aux deux exemples de ce contrôle.

Les règles de sélection, de stress, de repli défensif et de replay restent communes. [Construction personnalisée](../src/riskmatch/personalized_matches.py:271) · [Règles de calcul](../src/riskmatch/backtesting/walk_models.py:23) · [Replay](../src/riskmatch/backtesting/mandate_replay.py:122)

<a id="audit-1"></a>

### 1. Équipondération

**Entrées.** Univers admissible complet, à partir des 60 observations exigées et de la liste d’actions datée.

**Calcul et effet du mandat.** Attribue une part `1/N` à chaque titre admissible, puis répartit les excédents des lignes plafonnées. Les moyennes et corrélations n’interviennent que dans l’évaluation du portefeuille et l’adaptation au mandat.

**Résultat standard.** Actions 39,32 % · Trésor 0,30 % · cash 60,38 %. Principale position USD cash à 60,38 %. Estimations 6,94 % de rendement et 5,91 % de volatilité. Stress 13,66 %. Test 8,72 % de rendement composé, 4,48 % de volatilité et Sharpe 0,86.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 78,55 % · cash 21,45 %. Principale position BIL à 24,29 %. Estimations 1,65 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,83 % de rendement composé, 1,84 % de volatilité et Sharpe 0,04. Regroupée avec la nº 18 dans l’interface.

**Limite.** La classe qui fournit le plus de titres reçoit spontanément le plus de capital. L’équipondération est une référence transparente, avec une mise en œuvre exigeante en nombre de lignes.

<a id="audit-2"></a>

### 2. Variance minimale

**Entrées.** Covariance Ledoit–Wolf des rendements mensuels des titres du solveur.

**Calcul et effet du mandat.** Minimise `wᵀΣw` sous les plafonds et avec une somme de poids égale à un. Le solveur vérifie le budget, les bornes et l’écart d’optimalité. La carte mesure ensuite le risque avec l’estimateur commun.

**Résultat standard.** Actions 20,90 % · Trésor 79,10 % · cash 0,00 %. Principale position BIL à 28,16 %. Estimations 4,39 % de rendement et 3,49 % de volatilité. Stress 8,15 %. Test 6,56 % de rendement composé, 3,06 % de volatilité et Sharpe 0,57.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Le minimum vaut pour la covariance et les titres du solveur. Sur le mandat standard, le solveur mesure 5,62 % de volatilité, contre 3,49 % avec l’estimateur commun sur les mêmes poids. Les ETF courts peuvent concentrer le capital.

<a id="audit-3"></a>

### 3. Variance inverse

**Entrées.** Diagonale de la covariance Ledoit–Wolf du solveur.

**Calcul et effet du mandat.** Calcule `w_i = (1/σ_i²) / Σ_j(1/σ_j²)` puis applique les plafonds. Deux volatilités de 10 % et 20 % donnent 80 % et 20 % avant plafonds.

**Résultat standard.** Actions 46,59 % · Trésor 15,41 % · cash 38,00 %. Principale position USD cash à 38,00 %. Estimations 8,15 % de rendement et 6,26 % de volatilité. Stress 13,66 %. Test 10,95 % de rendement composé, 4,42 % de volatilité et Sharpe 1,34.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 81,28 % · cash 18,72 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,45 % de volatilité. Stress 5,46 %. Test 4,88 % de rendement composé, 1,84 % de volatilité et Sharpe 0,07.

**Limite.** Des ETF similaires peuvent recevoir ensemble un poids important. Le contrôle final utilise les covariances, tandis que les poids de départ répondent aux variances individuelles régularisées.

<a id="audit-4"></a>

### 4. Parité des risques

**Entrées.** Covariance Ledoit–Wolf du solveur.

**Calcul et effet du mandat.** Vise des parts de risque `w_i(Σw)_i/(wᵀΣw)=1/N`. Le solveur convexe réoptimise sous plafonds quand ils lient. Le mandat peut ensuite rapprocher la cible de l’allocation défensive.

**Résultat standard.** Actions 47,21 % · Trésor 18,40 % · cash 34,39 %. Principale position USD cash à 34,39 %. Estimations 8,85 % de rendement et 6,14 % de volatilité. Stress 13,66 %. Test 11,57 % de rendement composé, 4,47 % de volatilité et Sharpe 1,45.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 80,87 % · cash 19,13 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,87 % de rendement composé, 1,84 % de volatilité et Sharpe 0,06. Regroupée avec la nº 41 dans l’interface.

**Limite.** L’égalité par titre donne 59/64 du risque du solveur aux titres actions dans le mandat standard. Les parts de risque finales dépendent aussi de l’estimateur commun.

<a id="audit-5"></a>

### 5. Parité hiérarchique HRP

**Entrées.** Corrélations et covariances estimées sur les titres du solveur.

**Calcul et effet du mandat.** Construit un arbre à liaison moyenne et lit l’ordre de ses titres. Bissecte la liste et donne au groupe A la fraction `V_B/(V_A+V_B)`, avec des variances de poches provisoires à poids de variance inverse. Répète jusqu’au titre, puis applique les plafonds.

**Résultat standard.** Actions 44,18 % · Trésor 33,07 % · cash 22,75 %. Principale position USD cash à 22,75 %. Estimations 7,55 % de rendement et 6,10 % de volatilité. Stress 13,66 %. Test 10,25 % de rendement composé, 4,60 % de volatilité et Sharpe 1,14.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 81,28 % · cash 18,72 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,45 % de volatilité. Stress 5,46 %. Test 4,88 % de rendement composé, 1,84 % de volatilité et Sharpe 0,07. Regroupée avec la nº 3 dans l’interface.

**Limite.** L’ordre de l’arbre détermine les moitiés. Une petite variation des corrélations peut changer l’ordre et les poids. Le calcul entre deux moitiés utilise leurs variances internes.

<a id="audit-6"></a>

### 6. Contributions hiérarchiques HERC

**Entrées.** Arbre de corrélations et covariance du solveur.

**Calcul et effet du mandat.** Coupe l’arbre en trois groupes au plus. Résout une parité du risque dans chaque groupe, puis sur la covariance des portefeuilles de groupe. Un titre reçoit le poids de son groupe multiplié par son poids interne. En cas de plafond, essaie de réallouer entre groupes et redistribue par titre si nécessaire.

**Résultat standard.** Actions 27,78 % · Trésor 72,22 % · cash 0,00 %. Principale position BIL à 35,22 %. Estimations 5,62 % de rendement et 3,92 % de volatilité. Stress 9,29 %. Test 7,99 % de rendement composé, 2,40 % de volatilité et Sharpe 1,29.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 80,51 % · cash 19,49 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,86 % de rendement composé, 1,84 % de volatilité et Sharpe 0,05. Regroupée avec la nº 41 dans l’interface.

**Limite.** BIL et SHY sont chacun un groupe dans le cas standard, reçoivent un tiers du risque du solveur et totalisent près de 69 % du capital. Le nombre de groupes est un réglage du projet.

<a id="audit-7"></a>

### 7. Diversification maximale

**Entrées.** Volatilités individuelles et covariance Ledoit–Wolf du solveur.

**Calcul et effet du mandat.** Maximise `Σ_i w_i σ_i / √(wᵀΣw)`. Le numérateur représente les fluctuations si tous les titres évoluaient dans le même sens. Le dénominateur tient compte de la compensation entre titres. La tangence utilise les volatilités individuelles comme numérateur et teste les plafonds.

**Résultat standard.** Actions 50,90 % · Trésor 49,10 % · cash 0,00 %. Principale position BIL à 21,49 %. Estimations 10,32 % de rendement et 6,18 % de volatilité. Stress 12,47 %. Test 11,01 % de rendement composé, 4,96 % de volatilité et Sharpe 1,20.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 81,20 % · cash 18,80 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,45 % de volatilité. Stress 5,46 %. Test 4,89 % de rendement composé, 1,84 % de volatilité et Sharpe 0,07. Regroupée avec la nº 41 dans l’interface.

**Limite.** Un ratio élevé peut coexister avec une volatilité ou une perte élevée. Le rapport vise la réduction relative du risque et dépend des corrélations sur 60 mois.

<a id="audit-8"></a>

### 8. Sharpe maximal

**Entrées.** Moyennes historiques annualisées rapprochées de la médiane de leur classe, covariance du solveur et taux USD Fama–French.

**Calcul et effet du mandat.** Maximise `(μᵀw − r_f)/√(wᵀΣw)` sous plafonds. Le solveur vérifie une tangence à excès positif. La carte calcule séparément le Sharpe réalisé sur les mois de test.

**Résultat standard.** Actions 54,55 % · Trésor 4,36 % · cash 41,09 %. Principale position USD cash à 41,09 %. Estimations 12,42 % de rendement et 6,55 % de volatilité. Stress 13,66 %. Test 15,99 % de rendement composé, 5,18 % de volatilité et Sharpe 2,03.

**Résultat Trésor + cash.** Indisponible, car aucun portefeuille admissible ne dépasse le taux sans risque estimé dans la fenêtre de la cible finale.

**Limite.** Une moyenne trop optimiste peut dominer le choix. Si aucun portefeuille ne dépasse le taux sans risque sur la fenêtre, le moteur écarte la solution. Le seuil de faisabilité explique certaines indisponibilités.

<a id="audit-9"></a>

### 9. Utilité moyenne-variance

**Entrées.** Moyennes par classe, covariance et coefficient de profil `λ=1+13,3q²`.

**Calcul et effet du mandat.** Maximise `μᵀw − (λ/2)wᵀΣw` sous plafonds. Une hausse de λ pénalise davantage la variance. La construction finale teste aussi le stress et le seuil de volatilité du mandat.

**Résultat standard.** Actions 45,02 % · Trésor 0,00 % · cash 54,98 %. Principale position USD cash à 54,98 %. Estimations 11,72 % de rendement et 6,36 % de volatilité. Stress 13,66 %. Test 13,31 % de rendement composé, 4,52 % de volatilité et Sharpe 1,78.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Le coefficient de profil est calibré dans le projet et les deux premiers moments restent des estimations. Les variations favorables entrent aussi dans la variance.

<a id="audit-10"></a>

### 10. Minimisation de l’erreur de suivi

**Entrées.** Rendements des titres du solveur et rendement mensuel de SPY comme série de référence.

**Calcul et effet du mandat.** Forme `d_i = r_i − r_SPY` et minimise `wᵀCov_régularisée(d)w`. Comme la somme des poids de départ vaut un, l’expression correspond à la variance de l’écart entre le portefeuille initial et SPY.

**Résultat standard.** Actions 38,55 % · Trésor 1,66 % · cash 59,79 %. Principale position USD cash à 59,79 %. Estimations 7,87 % de rendement et 5,59 % de volatilité. Stress 13,66 %. Test 11,37 % de rendement composé, 4,00 % de volatilité et Sharpe 1,57.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 77,72 % · cash 22,28 %. Principale position TIP à 25,00 %. Estimations 1,67 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,81 % de rendement composé, 1,84 % de volatilité et Sharpe 0,03.

**Limite.** Une faible erreur de suivi mesure la stabilité de l’écart, avec possibilité de sous-performance constante. Le contrôle du mandat peut éloigner le portefeuille de cette référence. SPY demeure une référence actions pour un mandat Trésor.

<a id="audit-11"></a>

### 11. Black–Litterman

**Entrées.** Covariance, portefeuille de référence équipondéré plafonné, moyennes historiques, taux sans risque et vues de classes.

**Calcul et effet du mandat.** Construit le rendement en excès initial `π=δΣw_ref`, puis le met à jour à partir des vues actions, Trésor et de leur écart lorsqu’elles existent. Utilise τ=0,05, des confiances de 35 % pour les vues absolues et 25 % pour la relative, avec erreurs corrélées. Calibre δ à partir de la prime historique et de la variance du portefeuille de référence, avec un repli de 2,5 si le ratio est inutilisable. Optimise ensuite l’utilité avec la covariance prédictive.

**Résultat standard.** Actions 35,95 % · Trésor 0,00 % · cash 64,05 %. Principale position USD cash à 64,05 %. Estimations 8,66 % de rendement et 5,79 % de volatilité. Stress 13,66 %. Test 12,36 % de rendement composé, 3,93 % de volatilité et Sharpe 1,83.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Le point de départ équipondéré et les vues historiques sont des choix de recherche. Les données soutenant les vues se recoupent et les confiances sont fixées.

<a id="audit-12"></a>

### 12. CAPM

**Entrées.** Rendements des titres, de SPY et du cash mensuel sur la même fenêtre.

**Calcul et effet du mandat.** Calcule `β_i=Cov(r_i−r_f,r_SPY−r_f)/Var(r_SPY−r_f)`, puis `μ_i=r_f+β_i×prime_SPY`. La covariance Ledoit–Wolf sert au terme de risque de l’utilité.

**Résultat standard.** Actions 37,08 % · Trésor 0,00 % · cash 62,92 %. Principale position USD cash à 62,92 %. Estimations 7,75 % de rendement et 5,53 % de volatilité. Stress 13,66 %. Test 11,61 % de rendement composé, 4,09 % de volatilité et Sharpe 1,59.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 77,74 % · cash 22,26 %. Principale position TIP à 25,00 %. Estimations 1,67 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,81 % de rendement composé, 1,84 % de volatilité et Sharpe 0,03. Regroupée avec la nº 10 dans l’interface.

**Limite.** Un facteur actions unique explique mal les risques de taux et d’inflation. Le calcul en excès est la correction du bêta déjà appliquée dans le moteur du mandat.

<a id="audit-13"></a>

### 13. Utilité EWMA

**Entrées.** Rendements mensuels du panier du solveur, avec poids exponentiels.

**Calcul et effet du mandat.** Attribue à un mois d’âge k un poids proportionnel à `0,94^k`. Recalcule la moyenne et les covariances avec ces poids, annualise, puis optimise l’utilité avec λ. Le coefficient donne une demi-vie d’environ 11 mois.

**Résultat standard.** Actions 34,80 % · Trésor 0,00 % · cash 65,20 %. Principale position USD cash à 65,20 %. Estimations 9,98 % de rendement et 6,24 % de volatilité. Stress 13,66 %. Test 13,06 % de rendement composé, 5,07 % de volatilité et Sharpe 1,54.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Un choc récent pèse fortement. Le réglage 0,94 et la fenêtre de 60 mois imposent la vitesse d’adaptation et le risque peut varier selon le point de coupure.

<a id="audit-14"></a>

### 14. Allocation robuste

**Entrées.** Rendements du panier et 4 tirages de l’historique par blocs de trois mois, avec graine 24.

**Calcul et effet du mandat.** Estime une marge `h_i` par moyenne et un rayon `a` pour la covariance au quantile empirique 90 %. Optimise avec `μ−h` et `Σ+aI` dans l’utilité. Les positions positives rendent la borne basse des moyennes cohérente avec le modèle supposé.

**Résultat standard.** Actions 39,54 % · Trésor 1,82 % · cash 58,64 %. Principale position USD cash à 58,64 %. Estimations 10,00 % de rendement et 5,90 % de volatilité. Stress 13,66 %. Test 14,22 % de rendement composé, 4,29 % de volatilité et Sharpe 2,07.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Quatre tirages donnent une calibration fragile. Les chocs restent ceux de l’archive. Le mot robuste désigne l’incertitude explicitement modélisée.

<a id="audit-15"></a>

### 15. Allocation par rééchantillonnage

**Entrées.** Quatre historiques reconstruits par blocs contigus de trois mois.

**Calcul et effet du mandat.** Estime une moyenne et une covariance par tirage, optimise l’utilité sous les mêmes plafonds puis moyenne les quatre vecteurs. Le moteur écarte la stratégie si un tirage n’obtient pas une solution certifiée.

**Résultat standard.** Actions 39,22 % · Trésor 0,00 % · cash 60,78 %. Principale position USD cash à 60,78 %. Estimations 10,34 % de rendement et 6,08 % de volatilité. Stress 13,66 %. Test 12,56 % de rendement composé, 3,62 % de volatilité et Sharpe 2,03.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 80,12 % · cash 19,88 %. Principale position TIP à 25,00 %. Estimations 1,66 % de rendement et 2,45 % de volatilité. Stress 5,46 %. Test 4,91 % de rendement composé, 1,85 % de volatilité et Sharpe 0,08.

**Limite.** La moyenne de poids admissibles respecte les mêmes bornes. Le résultat dépend des blocs et de la graine et recycle l’information de départ.

<a id="audit-16"></a>

### 16. Allocation Wasserstein

**Entrées.** Covariance nominale, moyenne historique et dispersion des moyennes des blocs.

**Calcul et effet du mandat.** Ajoute `−ε||w||₂` à l’utilité, avec `ε=||h||₂` tiré des marges empiriques. La pénalité représente un rendement moyen défavorable dans une boule d’incertitude euclidienne. La covariance du terme de risque reste nominale.

**Résultat standard.** Actions 38,67 % · Trésor 0,57 % · cash 60,76 %. Principale position USD cash à 60,76 %. Estimations 10,09 % de rendement et 5,97 % de volatilité. Stress 13,66 %. Test 13,22 % de rendement composé, 4,12 % de volatilité et Sharpe 1,93.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 81,90 % · cash 18,10 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,45 % de volatilité. Stress 5,46 %. Test 4,92 % de rendement composé, 1,85 % de volatilité et Sharpe 0,09.

**Limite.** Le rayon dépend de quatre rééchantillonnages et reste une calibration expérimentale. Le stress de la carte est un calcul séparé.

<a id="audit-17"></a>

### 17. Kelly

**Entrées.** Les 60 rendements mensuels joints du panier, utilisés comme scénarios.

**Calcul et effet du mandat.** Maximise `(1/T)Σ_t log(1+r_tᵀw)` sous plafonds. Un scénario doit laisser au moins 1 % du capital de début de mois dans la formulation. Le logarithme pénalise fortement les trajectoires qui approchent de zéro.

**Résultat standard.** Actions 32,43 % · Trésor 0,00 % · cash 67,57 %. Principale position USD cash à 67,57 %. Estimations 9,82 % de rendement et 6,28 % de volatilité. Stress 13,66 %. Test 11,69 % de rendement composé, 4,99 % de volatilité et Sharpe 1,32.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09.

**Limite.** Les scénarios observés peuvent manquer des crises. Le calcul peut être concentré et l’adaptation ultérieure au mandat change le Kelly initial.

<a id="audit-18"></a>

### 18. Kelly fractionnaire

**Entrées.** Même historique et même cible Kelly, plus l’équipondération plafonnée du panier du solveur.

**Calcul et effet du mandat.** Combine `25 % × w_Kelly + 75 % × w_égal plafonné`. Le poids de 25 % règle l’intensité du signal Kelly. Les bornes de la cible initiale suivent de la combinaison des deux allocations admissibles.

**Résultat standard.** Actions 37,66 % · Trésor 2,34 % · cash 59,99 %. Principale position USD cash à 59,99 %. Estimations 8,92 % de rendement et 5,83 % de volatilité. Stress 13,66 %. Test 11,46 % de rendement composé, 4,16 % de volatilité et Sharpe 1,53.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 79,09 % · cash 20,91 %. Principale position BIL à 24,39 %. Estimations 1,65 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,84 % de rendement composé, 1,84 % de volatilité et Sharpe 0,05.

**Limite.** C’est la variante de RiskMatch, avec une référence équipondérée. Le niveau de risque final dépend aussi de la composition de cette référence.

<a id="audit-19"></a>

### 19. Utilité avec entropie

**Entrées.** Moyennes régularisées par classe, covariance du panier et coefficient λ du profil.

**Calcul et effet du mandat.** Maximise l’utilité moyenne-variance augmentée de `0,01 H(w)`, où `H(w)=−Σ_i w_i log(w_i)`. L’entropie récompense une répartition du capital plus étalée.

**Résultat standard.** Actions 44,53 % · Trésor 0,00 % · cash 55,47 %. Principale position USD cash à 55,47 %. Estimations 11,48 % de rendement et 6,22 % de volatilité. Stress 13,66 %. Test 14,30 % de rendement composé, 4,54 % de volatilité et Sharpe 1,97.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,36 % · cash 17,64 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,92 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Plus de lignes ne garantit pas plus de diversification économique. Le coefficient 0,01 fixe le compromis et reste un choix du projet.

<a id="audit-20"></a>

### 20. Rendement-risque sous contraintes

**Entrées.** Moyennes et covariance communes, cash, chocs de stress et plafonds du mandat.

**Calcul et effet du mandat.** Optimise l’utilité avec des limites de stress directement dans le problème. Utilise les ETF admissibles, les actions retenues par capitalisation, les positions nécessaires de la référence défensive et le cash autorisé. Vérifie ensuite la limite de volatilité et ajuste vers la référence si nécessaire.

**Résultat standard.** Actions 62,58 % · Trésor 0,00 % · cash 37,42 %. Principale position USD cash à 37,42 %. Estimations 14,43 % de rendement et 8,01 % de volatilité. Stress 13,66 %. Test 19,21 % de rendement composé, 6,03 % de volatilité et Sharpe 2,21.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 75,00 % · cash 25,00 %. Principale position BIL à 25,00 %. Estimations 1,89 % de rendement et 1,98 % de volatilité. Stress 4,21 %. Test 4,88 % de rendement composé, 1,39 % de volatilité et Sharpe 0,08. Regroupée avec la nº 40 dans l’interface.

**Limite.** La contrainte de volatilité est contrôlée après le premier solveur. Les pertes futures peuvent dépasser tous les chocs retenus.

<a id="audit-21"></a>

### 21. CVaR minimale

**Entrées.** Les 60 rendements mensuels joints, de même poids.

**Calcul et effet du mandat.** Définit la perte du mois par `L_t=−r_tᵀw`. Minimise `z + moyenne(max(L_t−z,0))/0,05` sous plafonds. Cette quantité mesure la perte moyenne dans les 5 % de scénarios les plus défavorables.

**Résultat standard.** Actions 2,36 % · Trésor 97,64 % · cash 0,00 %. Principale position BIL à 65,00 %. Estimations 2,29 % de rendement et 1,01 % de volatilité. Stress 2,85 %. Test 5,16 % de rendement composé, 0,76 % de volatilité et Sharpe 0,49.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** Avec 60 mois, la queue contient l’équivalent de trois observations. Elle peut donc changer fortement avec un mois extrême.

<a id="audit-22"></a>

### 22. CDaR minimale

**Entrées.** Les rendements mensuels du panier du solveur, dans leur ordre historique.

**Calcul et effet du mandat.** Construit une courbe additive `C_t=Σ_{j≤t}r_jᵀw` en partant de zéro. Mesure l’écart au sommet courant, puis minimise la moyenne des 5 % plus grands écarts via programmation linéaire.

**Résultat standard.** Actions 4,83 % · Trésor 95,17 % · cash 0,00 %. Principale position BIL à 65,00 %. Estimations 2,73 % de rendement et 1,16 % de volatilité. Stress 3,07 %. Test 5,93 % de rendement composé, 1,00 % de volatilité et Sharpe 1,12.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 82,47 % · cash 17,53 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,46 % de volatilité. Stress 5,46 %. Test 4,93 % de rendement composé, 1,84 % de volatilité et Sharpe 0,09. Regroupée avec la nº 17 dans l’interface.

**Limite.** La courbe de l’optimiseur est additive. Le drawdown de la carte est calculé sur la richesse composée du replay. Quelques épisodes peuvent dominer le résultat.

<a id="audit-23"></a>

### 23. Ciblage de volatilité

**Entrées.** Rendements d’un panier actions–Treasuries 60/40 sur 36 mois.

**Calcul et effet du mandat.** Construit une exposition 60/40, en privilégiant SPY et IEF si leurs plafonds le permettent. Multiplie ses poids par `min(1,0,10/σ_36)` et laisse le solde en cash si le mandat est compatible.

**Résultat standard.** Actions 33,18 % · Trésor 22,12 % · cash 44,71 %. Principale position USD cash à 44,71 %. Estimations 5,82 % de rendement et 5,99 % de volatilité. Stress 13,66 %. Test 10,76 % de rendement composé, 4,16 % de volatilité et Sharpe 1,37.

**Résultat Trésor + cash.** Indisponible, car le panier initial 60/40 exige une poche actions.

**Limite.** La volatilité réalisée peut dépasser la cible de 10 % après un choc. Le mélange initial exige une capacité dans chacune des deux classes.

<a id="audit-24"></a>

### 24. Défense contre les pertes extrêmes

**Entrées.** Richesse cumulée de SPY, initialisée à 1, sur les 12 mois avant la décision.

**Calcul et effet du mandat.** Mesure `richesse finale / sommet de la fenêtre − 1`. Une baisse strictement supérieure à 10 % en valeur absolue ramène la cible actions de 60 % à 20 %. Le reste va aux ETF du Trésor selon les plafonds.

**Résultat standard.** Actions 33,18 % · Trésor 22,12 % · cash 44,71 %. Principale position USD cash à 44,71 %. Estimations 5,82 % de rendement et 5,99 % de volatilité. Stress 13,66 %. Test 10,76 % de rendement composé, 4,16 % de volatilité et Sharpe 1,37. Regroupée avec la nº 23 dans l’interface.

**Résultat Trésor + cash.** Indisponible, car la règle prévoit au moins 20 % d’actions.

**Limite.** Le signal réagit après la baisse. La valeur des Treasuries peut aussi baisser simultanément. La correction inclut la valeur d’ouverture pour détecter une baisse dès le premier mois.

<a id="audit-25"></a>

### 25. Allocation défensive de référence

**Entrées.** Plafonds, cash, chocs communs, covariance et limite de volatilité.

**Calcul et effet du mandat.** Préfère 100 % cash uniquement lorsque c’est compatible. Sinon, minimise la pire perte parmi les scénarios sous les plafonds. Si nécessaire, cherche une cible de faible variance respectant les contraintes de stress.

**Résultat standard.** Actions 0,00 % · Trésor 0,00 % · cash 100,00 %. Principale position USD cash à 100,00 %. Estimations 3,11 % de rendement et 0,62 % de volatilité. Stress 0,00 %. Test 4,77 % de rendement composé, 0,17 % de volatilité et Sharpe indéfini.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 75,00 % · cash 25,00 %. Principale position BIL à 25,00 %. Estimations 1,89 % de rendement et 1,98 % de volatilité. Stress 4,21 %. Test 4,88 % de rendement composé, 1,39 % de volatilité et Sharpe 0,08. Regroupée avec la nº 40 dans l’interface.

**Limite.** Le cash est le taux sans risque Fama–French dans l’archive. Le choix défensif dépend des chocs du projet et des classes réellement autorisées.

<a id="audit-26"></a>

### 26. ETF équipondérés

**Entrées.** Liste des ETF admissibles et plafonds du mandat.

**Calcul et effet du mandat.** Attribue initialement `1/N` aux ETF, puis redistribue entre les fonds autorisés. Les actions détenues directement sont exclues de ce panier initial. Les contrôles de risque du mandat s’appliquent ensuite.

**Résultat standard.** Actions 42,21 % · Trésor 14,07 % · cash 43,72 %. Principale position USD cash à 43,72 %. Estimations 6,72 % de rendement et 6,19 % de volatilité. Stress 13,66 %. Test 10,12 % de rendement composé, 4,56 % de volatilité et Sharpe 1,13.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 78,55 % · cash 21,45 %. Principale position BIL à 24,29 %. Estimations 1,65 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,83 % de rendement composé, 1,84 % de volatilité et Sharpe 0,04. Regroupée avec la nº 18 dans l’interface.

**Limite.** Plusieurs fonds peuvent répliquer des expositions proches. L’égalité par fonds peut favoriser la classe contenant le plus de fonds.

<a id="audit-27"></a>

### 27. Gestion active long-only

**Entrées.** 36 mois de rendements de chaque titre admissible et de SPY.

**Calcul et effet du mandat.** Classe suivant l’ordonnée à l’origine annualisée de la régression sur SPY `12(ȓ_i−β_iȓ_SPY)`, avec rendements totaux. Favorise les rangs positifs, part du meilleur cinquième et élargit si les plafonds l’exigent. Suit une règle équipondérée si le signal positif manque ou ne peut financer le panier.

**Résultat standard.** Actions 37,43 % · Trésor 0,00 % · cash 62,57 %. Principale position USD cash à 62,57 %. Estimations 11,19 % de rendement et 6,57 % de volatilité. Stress 13,66 %. Test 11,27 % de rendement composé, 5,24 % de volatilité et Sharpe 1,19.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 78,55 % · cash 21,45 %. Principale position BIL à 24,29 %. Estimations 1,65 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,83 % de rendement composé, 1,84 % de volatilité et Sharpe 0,04. Regroupée avec la nº 18 dans l’interface.

**Limite.** Un alpha estimé sur 36 mois est sensible au bruit et à SPY. Les positions de repli peuvent ressembler à une stratégie passive.

<a id="audit-28"></a>

### 28. Smart beta multifactoriel

**Entrées.** Scores standardisés datés des huit facteurs, avec au moins trois scores disponibles par action.

**Calcul et effet du mandat.** Moyenne les scores disponibles titre par titre, classe les actions et utilise des poids décroissants par rang. Commence au meilleur 30 % et élargit selon la capacité sous plafonds.

**Résultat standard.** Actions 43,88 % · Trésor 0,00 % · cash 56,12 %. Principale position USD cash à 56,12 %. Estimations 6,45 % de rendement et 6,67 % de volatilité. Stress 13,66 %. Test 9,73 % de rendement composé, 4,77 % de volatilité et Sharpe 1,00.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** L’ensemble des facteurs peut différer d’une action à l’autre. Le score ne neutralise pas toutes les expositions sectorielles.

<a id="audit-29"></a>

### 29. Pondération fondamentale

**Entrées.** Capitaux propres positifs de comptes reliés via CCM et acceptés avant la décision, avec contrôles de couverture.

**Calcul et effet du mandat.** Attribue `w_i∝capitaux propres_i` aux titres couverts et applique les plafonds. Les entités aux fonds propres non positifs ou sans publication datée exploitable ne reçoivent pas de poids.

**Résultat standard.** Actions 39,37 % · Trésor 0,00 % · cash 60,63 %. Principale position USD cash à 60,63 %. Estimations 7,64 % de rendement et 5,84 % de volatilité. Stress 13,66 %. Test 11,48 % de rendement composé, 4,32 % de volatilité et Sharpe 1,48.

**Résultat Trésor + cash.** Indisponible, car la pondération sur capitaux propres requiert des actions admissibles.

**Limite.** Les capitaux propres sont une grandeur comptable et varient selon secteur et règles de déclaration. L’écart avec la valeur boursière est intentionnel.

<a id="audit-30"></a>

### 30. Allocation à huit facteurs

**Entrées.** Huit séries de scores datés sur les actions.

**Calcul et effet du mandat.** Construit une allocation de rangs pour chaque facteur, puis accorde 1/8 du capital à chacune. Les positions communes sont additionnées. La règle requiert une poche calculable pour chacun des huit facteurs.

**Résultat standard.** Actions 38,87 % · Trésor 0,00 % · cash 61,13 %. Principale position USD cash à 61,13 %. Estimations 6,68 % de rendement et 5,93 % de volatilité. Stress 13,66 %. Test 9,08 % de rendement composé, 4,53 % de volatilité et Sharpe 0,92.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Une même action peut remonter dans plusieurs poches. La couverture du facteur le moins renseigné peut empêcher le calcul de la stratégie complète.

<a id="audit-31"></a>

### 31. Cœur-satellite

**Entrées.** ETF admissibles pour le cœur et alpha sur 36 mois face à SPY pour le satellite.

**Calcul et effet du mandat.** Mélange `60 % × cœur ETF équipondéré + 40 % × gestion active`. Le satellite reprend les mêmes conditions de signal et de repli que la gestion active.

**Résultat standard.** Actions 40,29 % · Trésor 7,11 % · cash 52,59 %. Principale position USD cash à 52,59 %. Estimations 9,03 % de rendement et 6,07 % de volatilité. Stress 13,66 %. Test 10,64 % de rendement composé, 4,63 % de volatilité et Sharpe 1,21.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 78,55 % · cash 21,45 %. Principale position BIL à 24,29 %. Estimations 1,65 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,83 % de rendement composé, 1,84 % de volatilité et Sharpe 0,04. Regroupée avec la nº 18 dans l’interface.

**Limite.** Le 60/40 désigne ici les budgets de deux méthodes, avec recouvrement possible. L’allocation par classes en résulte et peut varier.

<a id="audit-32"></a>

### 32. Facteur taille

**Entrées.** Capitalisation observée des actions du classement daté.

**Calcul et effet du mandat.** Calcule `−ln(capitalisation)`, standardise, sélectionne les hauts rangs et répartit par rang sous plafonds. Les petites valeurs obtiennent un meilleur score parmi les actions filtrées.

**Résultat standard.** Actions 37,97 % · Trésor 0,00 % · cash 62,03 %. Principale position USD cash à 62,03 %. Estimations 5,39 % de rendement et 6,56 % de volatilité. Stress 13,66 %. Test 7,96 % de rendement composé, 5,05 % de volatilité et Sharpe 0,62.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** La sélection est petite à l’intérieur d’un top 1 000 et d’un historique admissible de cinq ans. Les micro-capitalisations restent hors champ.

<a id="audit-33"></a>

### 33. Facteur valeur

**Entrées.** Capitaux propres positifs publiés et capitalisation observée.

**Calcul et effet du mandat.** Classe à partir de `capitaux propres / capitalisation` sur une échelle commune de source. Les scores sont standardisés à chaque date, puis les meilleurs rangs sont pondérés sous plafonds.

**Résultat standard.** Actions 42,88 % · Trésor 0,00 % · cash 57,12 %. Principale position USD cash à 57,12 %. Estimations 6,51 % de rendement et 7,29 % de volatilité. Stress 13,66 %. Test 10,56 % de rendement composé, 5,59 % de volatilité et Sharpe 1,00.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Une valorisation basse peut refléter une entreprise fragilisée. Les niveaux comptables sont difficiles à comparer entre secteurs.

<a id="audit-34"></a>

### 34. Facteur momentum

**Entrées.** Rendements mensuels datés des actions, avec continuité contrôlée.

**Calcul et effet du mandat.** Compose les 11 mois précédant le dernier mois, `Π(1+r)−1`, puis standardise le signal dans la coupe actions et favorise le haut du classement.

**Résultat standard.** Actions 34,46 % · Trésor 0,00 % · cash 65,54 %. Principale position USD cash à 65,54 %. Estimations 8,28 % de rendement et 5,97 % de volatilité. Stress 13,66 %. Test 11,29 % de rendement composé, 5,24 % de volatilité et Sharpe 1,19.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Les leaders peuvent décrocher brutalement. Cette variante part des scores du classement actions, avec leur couverture, leur traitement et leurs poids de rang.

<a id="audit-35"></a>

### 35. Facteur faible volatilité

**Entrées.** Douze rendements mensuels consécutifs pour chaque action couverte.

**Calcul et effet du mandat.** Prend l’opposé de l’écart-type des 12 mois, standardise, puis favorise les hauts rangs sous plafonds.

**Résultat standard.** Actions 50,94 % · Trésor 0,00 % · cash 49,06 %. Principale position USD cash à 49,06 %. Estimations 7,55 % de rendement et 6,42 % de volatilité. Stress 13,66 %. Test 8,47 % de rendement composé, 4,97 % de volatilité et Sharpe 0,73.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Une volatilité individuelle faible peut masquer un risque commun de secteur ou une perte extrême. Le score regarde une année de données.

<a id="audit-36"></a>

### 36. Facteur liquidité

**Entrées.** Volume mensuel d’actions échangées et capitalisation du classement daté.

**Calcul et effet du mandat.** Régresse `ln(volume)` sur `ln(capitalisation)` par date. Le résidu standardisé indique quels titres échangent plus que ce que leur taille laisserait attendre. Favorise les rangs élevés.

**Résultat standard.** Actions 39,20 % · Trésor 0,00 % · cash 60,80 %. Principale position USD cash à 60,80 %. Estimations 6,15 % de rendement et 6,08 % de volatilité. Stress 13,66 %. Test 9,56 % de rendement composé, 4,35 % de volatilité et Sharpe 1,06.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Le résidu mesure l’activité relative. Le coût réel dépend aussi du spread, de la profondeur et de la taille de l’ordre.

<a id="audit-37"></a>

### 37. Facteur qualité

**Entrées.** Actifs, dettes et résultat net de comptes annuels acceptés avant la décision.

**Calcul et effet du mandat.** Calcule `résultat net / actifs − dettes / actifs`, standardise et favorise les hauts rangs sous plafonds.

**Résultat standard.** Actions 34,06 % · Trésor 0,00 % · cash 65,94 %. Principale position USD cash à 65,94 %. Estimations 6,50 % de rendement et 5,93 % de volatilité. Stress 13,66 %. Test 7,88 % de rendement composé, 4,64 % de volatilité et Sharpe 0,66.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** La mesure rassemble rentabilité et bilan avec une pondération fixe. Les particularités sectorielles et comptables peuvent peser fortement.

<a id="audit-38"></a>

### 38. Facteur rentabilité

**Entrées.** Résultat net annuel et capitaux propres positifs publiés.

**Calcul et effet du mandat.** Utilise `résultat net / capitaux propres` comme indicateur de rentabilité, avec standardisation et pondération par rang.

**Résultat standard.** Actions 38,31 % · Trésor 0,00 % · cash 61,69 %. Principale position USD cash à 61,69 %. Estimations 7,39 % de rendement et 5,74 % de volatilité. Stress 13,66 %. Test 8,27 % de rendement composé, 4,36 % de volatilité et Sharpe 0,79.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Des fonds propres très faibles peuvent gonfler le ratio et un résultat exceptionnel peut perturber le classement. L’écrêtage réduit l’influence des extrêmes.

<a id="audit-39"></a>

### 39. Facteur investissement

**Entrées.** Actifs positifs de deux exercices comparables, espacés de 9 à 15 mois.

**Calcul et effet du mandat.** Calcule `1−actifs actuels/actifs précédents` et favorise les scores les plus élevés après standardisation. Une croissance plus basse des actifs augmente le score.

**Résultat standard.** Actions 37,68 % · Trésor 0,00 % · cash 62,32 %. Principale position USD cash à 62,32 %. Estimations 5,77 % de rendement et 6,16 % de volatilité. Stress 13,66 %. Test 8,17 % de rendement composé, 4,55 % de volatilité et Sharpe 0,73.

**Résultat Trésor + cash.** Indisponible, car aucune action autorisée pour alimenter le signal.

**Limite.** Une acquisition, une cession ou un changement de périmètre peut dominer le signal. Des exercices comparables et datés sont requis.

<a id="audit-40"></a>

### 40. Momentum transversal

**Entrées.** Rendements 12–1 des titres admissibles, actions et ETF.

**Calcul et effet du mandat.** Classe selon `Π(1+r)−1` sur les 11 mois qui précèdent le dernier mois. Vise le meilleur tiers, le départage par l’ordre stable du panier et le pondère à égalité sous plafonds. Le reliquat reste en cash si la capacité manque et si le mandat est compatible.

**Résultat standard.** Actions 37,69 % · Trésor 0,00 % · cash 62,31 %. Principale position USD cash à 62,31 %. Estimations 8,10 % de rendement et 5,88 % de volatilité. Stress 13,66 %. Test 10,07 % de rendement composé, 4,85 % de volatilité et Sharpe 1,06.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 75,00 % · cash 25,00 %. Principale position USD cash à 25,00 %. Estimations 1,89 % de rendement et 1,98 % de volatilité. Stress 4,21 %. Test 4,88 % de rendement composé, 1,39 % de volatilité et Sharpe 0,08.

**Limite.** Le classement est relatif à l’univers. Le meilleur titre peut avoir baissé si tous les autres ont encore plus baissé. Les retournements pénalisent la règle.

<a id="audit-41"></a>

### 41. Suivi de tendance

**Entrées.** ETF, rendement composé sur 12 mois et volatilité sur 36 mois.

**Calcul et effet du mandat.** Retient les ETF à performance strictement positive et pondère par `1/max(σ_36,2 %)` sous plafonds. Si les titres en tendance positive n’absorbent pas tout le capital, la cible laisse un reliquat en cash.

**Résultat standard.** Actions 37,10 % · Trésor 52,87 % · cash 10,03 %. Principale position BIL à 18,61 %. Estimations 5,58 % de rendement et 5,82 % de volatilité. Stress 13,66 %. Test 9,12 % de rendement composé, 4,25 % de volatilité et Sharpe 0,99.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 80,78 % · cash 19,22 %. Principale position BIL à 25,00 %. Estimations 1,64 % de rendement et 2,44 % de volatilité. Stress 5,46 %. Test 4,68 % de rendement composé, 1,71 % de volatilité et Sharpe -0,05.

**Limite.** Le seuil zéro peut créer des allers-retours et le signal peut réagir lentement après un retournement.

<a id="audit-42"></a>

### 42. Retour à la moyenne

**Entrées.** Rendement composé des trois derniers mois et historique de rendements glissants sur trois mois qui précède ce signal.

**Calcul et effet du mandat.** Calcule `z=(rendement récent−moyenne)/écart-type`. Retient `−4<z≤−2` et une perte du dernier mois inférieure à 15 %. Favorise `−z` et laisse un reliquat en cash si le panier sous plafonds ne peut absorber le capital.

**Résultat standard.** Actions 44,53 % · Trésor 0,00 % · cash 55,47 %. Principale position USD cash à 55,47 %. Estimations 7,36 % de rendement et 6,82 % de volatilité. Stress 13,66 %. Test 9,47 % de rendement composé, 6,75 % de volatilité et Sharpe 0,69.

**Résultat Trésor + cash.** Actions 0,00 % · Trésor 75,00 % · cash 25,00 %. Principale position USD cash à 25,00 %. Estimations 1,89 % de rendement et 1,98 % de volatilité. Stress 4,21 %. Test 4,88 % de rendement composé, 1,39 % de volatilité et Sharpe 0,08. Regroupée avec la nº 40 dans l’interface.

**Limite.** Les fenêtres passées se recouvrent entre elles et les seuils sont fixes. Une baisse peut refléter une dégradation durable sans rebond.

<a id="audit-43"></a>

### 43. Allocation tactique

**Entrées.** Signaux de momentum 12–1 de SPY et IEF.

**Calcul et effet du mandat.** Calcule `60 %+20 points × signe(momentum_SPY−momentum_IEF)`. Ajuste la part dans la bande 40–80 % et selon la capacité des deux classes. Utilise les proxies de classe si les plafonds le permettent.

**Résultat standard.** Actions 40,19 % · Trésor 10,05 % · cash 49,76 %. Principale position USD cash à 49,76 %. Estimations 6,69 % de rendement et 6,43 % de volatilité. Stress 13,66 %. Test 9,01 % de rendement composé, 4,87 % de volatilité et Sharpe 0,85.

**Résultat Trésor + cash.** Indisponible, car la bande de poids actions exige une exposition interdite par le mandat.

**Limite.** Deux ETF déterminent le signal de classes. Exiger au moins 40 % d’actions rend cette règle incompatible avec certains mandats.

<a id="audit-44"></a>

### 44. Allocation tous régimes

**Entrées.** Rendements sur 36 mois de SPY, IEF, TIP et SHY.

**Calcul et effet du mandat.** Répartit le capital dans ce panier fixe selon `1/max(σ_i,2 %)` sous plafonds, puis applique les contrôles du mandat.

**Résultat standard.** Actions 8,93 % · Trésor 91,07 % · cash 0,00 %. Principale position SHY à 53,38 %. Estimations 2,14 % de rendement et 4,06 % de volatilité. Stress 10,35 %. Test 6,26 % de rendement composé, 2,88 % de volatilité et Sharpe 0,51.

**Résultat Trésor + cash.** Indisponible, car les trois ETF du Trésor du panier, plafonnés à 25 % chacun, ne peuvent absorber 100 % du capital.

**Limite.** Quatre ETF couvrent un ensemble limité de régimes. L’objectif ne vise pas une égalité mesurée des contributions au risque économique.

<a id="audit-45"></a>

### 45. Multi-stratégies

**Entrées.** Momentum transversal, suivi de tendance et poche stratégique actions–Treasuries 60/40.

**Calcul et effet du mandat.** Reconstitue les rendements des trois poches sur 36 mois et pondère par l’inverse de leur volatilité, avec un plancher de 2 % pour les budgets. Additionne les positions communes. Le diagnostic utilise désormais les volatilités réelles et renvoie une corrélation absente pour une poche constante.

**Résultat standard.** Actions 37,55 % · Trésor 26,86 % · cash 35,59 %. Principale position USD cash à 35,59 %. Estimations 6,60 % de rendement et 5,97 % de volatilité. Stress 13,66 %. Test 10,34 % de rendement composé, 4,52 % de volatilité et Sharpe 1,18.

**Résultat Trésor + cash.** Indisponible, car la poche stratégique 60/40 du modèle exige des actions.

**Limite.** Les poches peuvent détenir les mêmes actifs et une poche sans exposition peut attirer du capital par le plancher. La règle d’allocation est en inverse-volatilité, avec des corrélations utilisées dans l’analyse.

<a id="audit-46"></a>

### 46. Changement de régime

**Entrées.** Rendements de SPY et filtre gaussien à deux états, avec paramètres fixés.

**Calcul et effet du mandat.** Part de 20 % de probabilité du régime turbulent, applique des transitions mensuelles puis actualise les probabilités avec le rendement observé. Les volatilités mensuelles des états sont 3,5 % et 9 %. Vise 20 % d’actions si la probabilité turbulente dépasse 50 %, sinon 70 %, selon les capacités.

**Résultat standard.** Actions 36,94 % · Trésor 15,83 % · cash 47,23 %. Principale position USD cash à 47,23 %. Estimations 6,18 % de rendement et 6,20 % de volatilité. Stress 13,66 %. Test 8,62 % de rendement composé, 4,76 % de volatilité et Sharpe 0,79.

**Résultat Trésor + cash.** Indisponible, car la bande de poids actions exige une exposition interdite par le mandat.

**Limite.** Les états et transitions découlent de paramètres fixés. Une période de stress atypique ou un changement des marchés peut réduire la pertinence du signal.

<a id="audit-47"></a>

### 47. Macro globale

**Entrées.** Versions historiques datées de la croissance réelle et des prix, plus rendement 12 mois de BIL.

**Calcul et effet du mandat.** Attend que le mois du millésime macro soit terminé, puis prend les variations annuelles des informations utilisables. Vise 80 % actions si croissance > 2 %, inflation < 4 % et BIL < 5 %. Sinon vise 30 %, dans la bande faisable.

**Résultat standard.** Actions 40,19 % · Trésor 10,05 % · cash 49,76 %. Principale position USD cash à 49,76 %. Estimations 6,69 % de rendement et 6,43 % de volatilité. Stress 13,66 %. Test 8,90 % de rendement composé, 4,40 % de volatilité et Sharpe 0,91. Regroupée avec la nº 43 dans l’interface.

**Résultat Trésor + cash.** Indisponible, car la bande de poids actions exige une exposition interdite par le mandat.

**Limite.** BIL représente les taux à court terme par approximation. La fréquence, l’âge et les révisions des données peuvent influencer le classement du régime.

<a id="audit-48"></a>

### 48. SPY à 100 %

**Entrées.** Rendements mensuels totaux de SPY pendant le test commun.

**Calcul et effet du mandat.** Utilise 100 % SPY et applique les frais simulés de l’achat initial. Le Sharpe utilise le même taux sans risque que les cartes.

**Résultat de la référence sur les deux mandats.** Test 22,86 % de rendement composé, 10,58 % de volatilité et Sharpe 1,58.

**Limite.** Le benchmark représente surtout les grandes actions américaines. Un mandat Trésor peut s’y comparer, même si cette exposition serait incompatible avec son mandat.

<a id="audit-49"></a>

### 49. Sortino maximal

**Entrées.** Rendements mensuels et seuil de rendement minimal fixé à zéro dans le test de référence.

**Calcul et effet du mandat.** Divise le rendement moyen au-dessus du seuil par la racine de la moyenne des écarts négatifs au carré. Le code teste si un portefeuille peut garder un rendement positif sans mois sous le seuil.

**Résultat standard.** Cible calculable sur la fenêtre finale. Le replay exploratoire s’interrompt à la décision du 26 février 2021. Le moteur détecte une cible à rendement excédentaire positif sans mois sous le seuil, ce qui rend la maximisation du ratio indéfinie.

**Résultat Trésor + cash.** Cible calculable sur la fenêtre finale. Le replay exploratoire termine les 60 mois, dont les 25 mois du test commun. La référence reste en recherche dans le catalogue.

**Limite.** Le dénominateur vaut zéro si aucun mois du portefeuille ne passe sous le seuil, ce qui rend le ratio indéfini. La méthode reste en recherche et aucun backtest de carte ne lui est attribué.

<a id="audit-50"></a>

### 50. Omega maximal

**Entrées.** Rendements mensuels et seuil de rendement fixé à zéro dans le test de référence.

**Calcul et effet du mandat.** Calcule `Σ max(r_t,0)/Σ max(−r_t,0)`. Utilise une programmation linéaire homogène pour les cas à excès positif et traite séparément les cas de dénominateur nul.

**Résultat standard.** Cible calculable sur la fenêtre finale. Le replay exploratoire s’interrompt à la décision du 26 février 2021. Le moteur détecte une cible à rendement excédentaire positif sans mois sous le seuil, ce qui rend la maximisation du ratio indéfinie.

**Résultat Trésor + cash.** Cible calculable sur la fenêtre finale. Le replay exploratoire termine les 60 mois, dont les 25 mois du test commun. La référence reste en recherche dans le catalogue.

**Limite.** La valeur dépend fortement du seuil et de la présence de pertes. La méthode reste en recherche et aucun backtest de carte ne lui est attribué.

#### Variante testée pour Sortino et Omega

Une règle de départage conserve le seuil mensuel de 0 %. Le moteur maximise le ratio lorsque la solution est finie. Si un portefeuille admissible peut avoir un rendement moyen positif sans mois sous le seuil dans sa fenêtre d’estimation, il retient parmi ces portefeuilles celui dont le rendement moyen est le plus élevé. Le calcul de la cible utilise uniquement les mois antérieurs à la décision. Les plafonds s’appliquent pendant le départage, puis les contrôles habituels du mandat s’appliquent à la cible. Le ratio d’estimation reste indéfini à ces dates.

L’essai a rétabli les 60 mois de replay, dont les 25 mois de test, pour les deux modèles sur chacun des deux mandats. La règle de départage a été sollicitée sur le mandat standard aux décisions des 26 février, 28 mai et 31 août 2021. Le mandat Trésor + cash a terminé sans ce départage. Il s’agit d’un essai isolé. Les deux fiches du catalogue gardent leur statut de recherche pour le moteur courant.

Un deuxième essai a utilisé le cash USD de chaque mois comme seuil. Il termine lui aussi les deux replays sur les deux mandats. Dans cette formulation, un placement qui rapporte moins que le cash compte comme un manque à gagner, même si son rendement est positif. Le choix du seuil modifie alors le signal sur toutes les fenêtres.

## Du swipe au portefeuille

Le swipe ajoute une **méthode sélectionnée**. Les budgets des poches doivent totaliser 100 %. Les positions détenues en commun sont additionnées et les limites du mandat sont revérifiées. Le moteur propose quatre modes.

| Mode | Ce qui est effectivement calculé |
|---|---|
| Répartition manuelle | Les pourcentages saisis déterminent le budget de chaque méthode. |
| Variance minimale | Le moteur utilise la covariance des 35 mois de développement entre les poches sélectionnées. L’estimation est calculée sur les rendements des stratégies avant les frais supplémentaires de transfert entre poches. Le résultat historique affiché intègre ces frais. |
| Rendement estimé maximal | La moyenne estimée est linéaire dans les budgets. Sans plafond par stratégie, la meilleure allocation pour ce seul critère place 100 % du budget dans la poche retenue qui a l’estimation la plus élevée. Les plafonds par titre restent appliqués. |
| Objectif prioritaire | Le moteur compare un ensemble déterministe de répartitions, y compris les poches seules et certains mélanges, sur les mêmes trajectoires. Il retient celle qui obtient le meilleur score d’objectif dans cet ensemble. |

Le rapport distingue la moyenne arithmétique historique annualisée, le CAGR historique, le Sharpe historique au-dessus du cash, la volatilité et la baisse maximale du replay. Il affiche aussi le rendement estimé et la volatilité estimée des poids consolidés et le stress sur ces mêmes positions. Les risques des titres et stratégies ne s’additionnent pas comme des pourcentages de budget. L’analyse tient compte des expositions communes et des covariances.

La projection confirmée répète **1 000 trajectoires** sur l’horizon du client, tire des blocs de six mois communs à tous les titres parmi les **60 mois** de l’archive et rééquilibre les positions vers les poids consolidés mensuellement. Elle modélise les frais de rééquilibrage et utilise les flux du mandat. P5, P50 et P95 résument la dispersion. Le rendement simulé hors flux et le capital restant après paiement des objectifs répondent à deux questions différentes. La comparaison d’objectif utilise le cash comme référence. La projection garde les poids actuels comme cible. La simulation des règles dynamiques reste accessible séparément et utilise le replay historique des stratégies.

L’actualisation relance la projection avec la dernière allocation confirmée et l’archive figée. Le suivi en direct a son propre état et dépend des cours disponibles pour les titres. Une absence de cotation doit rester visible.

## Sources dans le projet

- [Règles, entrées et optimisations](../src/riskmatch/backtesting/walk_models.py), [filtres et sélection](../src/riskmatch/personalized_matches.py), [replay mensuel](../src/riskmatch/backtesting/mandate_replay.py).
- [Combinaison, rendement et variance](../src/riskmatch/historical_matches.py), [projection et choix par objectif](../src/riskmatch/selection/goals.py), [flux et objectifs](../src/riskmatch/analytics/objectives.py).
- [Données et limites du projet](UNIVERS_DONNEES_STRATEGIES.md).
