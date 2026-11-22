# 6.2 · Comparer des portefeuilles et financer un objectif

**Un retrait couvert et un objectif final difficile à atteindre peuvent coexister.** Dans le cas illustratif de RiskMatch, 15 000 CHF sont réservés sur les 50 000 CHF initiaux pour le retrait dans un an. Les 35 000 CHF restants financent les placements, les liquidités supplémentaires et les frais. Pour tester un objectif de 65 000 CHF de pouvoir d'achat dans huit ans, nous avons supposé des versements de 100 CHF par mois et 2 % d'inflation annuelle. Aucun participant n'a fourni ces paramètres. [Hypothèses fixées avant calcul](PROTOCOL.md)

### Explorer l'exemple

Lancer l'application habituelle depuis la racine, puis ouvrir **Portfolio options** dans la barre latérale. Choisir un plafond de volatilité de 4 % ou 8 %, comparer les huit allocations admissibles et explorer l'effet d'une autre épargne, d'un autre horizon ou d'une autre cible. Le choix conservé dans la session concerne cet exemple daté. Les options utilisent le mandat de 6.1. Les données saisies dans le questionnaire personnel ont un autre contexte.

```sh
python -m pip install -r requirements-app.txt
python -m streamlit run app/intake.py
```

## Retrait, risque et rendement

| Indicateur sur l'allocation robuste, limite de 8 % sur la poche | Résultat |
|---|---:|
| Liquidités de la poche après achat, en plus de la réserve | 15 473 CHF |
| Frais d'entrée modélisés | 19,51 CHF |
| Moyenne des sept rendements annuels historiques du foyer | 4,14 % |
| Rendement annuel net et volatilité estimés du foyer au 30 octobre 2026 | 8,08 % et 5,60 % |
| Fourchette conditionnelle pour le mois suivant, sur les 50 000 CHF | −0,44 % à +2,06 % |
| Test de cette méthode sur les sept décisions antérieures | 6 résultats dans leur fourchette |
| Perte instantanée du scénario conjoint de 4.2 | 2 858 CHF |
| Pire mois historique appliqué aux positions du 30 octobre 2026 | 2 488 CHF, octobre 2008 |

La fourchette reprend les 10ᵉ et 90ᵉ percentiles des 36 mois complets antérieurs, positions courantes, CHF et coût d'entrée inclus. La vérification utilise chaque portefeuille de l'époque, sa première clôture d'exécution et la fin du premier mois. Les sept résultats annuels de 6.1 proviennent de cohortes financées séparément. Le choc simultané combine actions américaines −10 %, taux nominal américain +1 point, inflation anticipée +0,5 point et dollar −5 % face au CHF. La revalorisation du choc exclut les frais d'entrée déjà affichés. Aucun de ces résultats ne constitue une observation prospective indépendante. [Fiches de toutes les options](results/options.csv) · [Vérification des fourchettes](results/range_calibration.csv)

### Ce que les réponses aux cartes permettent de comparer

Pour l'exemple, C01 établit la compréhension. C03 et C04 donnent un intervalle d'aversion φ de **2,67 à 4,44**. En retirant l'un des deux arbitrages, une seule borne reste étayée. Les exemples sans compréhension, à borne unique ou contradictoires produisent un classement indéterminé. Une réponse passée peut laisser les options ouvertes. Les cartes utilisent une mise hypothétique de 1 000 CHF sur un an. Le transfert au patrimoine réel reste à vérifier.

Pour chaque paire, le score annuel est la moyenne nette moins φ fois la variance divisée par deux. L'écart entre scores est affine en φ. Tester les deux extrémités permet d'établir un ordre conditionnel ou de calculer le seuil auquel il bascule. Si le rendement excédentaire de la poche est mesuré sur 35 000 CHF, le rendement du foyer est multiplié par 0,7 et la variance par 0,49. L'équivalence de classement exige alors φ de la poche égal à 0,7 fois φ du foyer. Nous publions les deux bases avec le même intervalle pour vérifier la sensibilité à ce choix. Le Sharpe compare une moyenne annuelle nette à du cash CHF rémunéré à zéro. Il est indéfini pour le tout-cash.

Au plafond de 8 %, les estimations du 30 octobre placent la solution robuste devant l'équipondération pour tout l'intervalle de φ. Les sept rendements annuels effectivement observés inversent cet ordre. Avec ces mêmes observations, le classement du 60/40 et de la parité de risque change autour de **φ = 2,68**. Ce petit échantillon laisse le choix ouvert. Les égalités numériques appartiennent au calcul, et aucune marge d'équivalence pratique n'a été établie. [Paires et seuils](results/pairwise.csv) · [Comparaison historique à années identiques](results/ranking_history.csv) · [Variations des hypothèses](results/model_sensitivity.csv)

## Financer le but à huit ans

Les 2 000 trajectoires tirent des blocs communs de douze mois parmi 229 blocs disponibles entre octobre 2006 et septembre 2026. Chaque bloc garde les mouvements simultanés des trois ETF en USD et du change USD/CHF. Le modèle garde les titres pendant l'année, verse l'épargne en CHF à la fin de chaque mois, puis rééquilibre annuellement aux poids de départ sur la fortune investissable du moment. Les plafonds sont contrôlés sur l'allocation de référence aux dates de revue. Entre ces dates les poids peuvent dériver, et la simulation ne réestime pas le risque futur. Les achats, les ventes et la liquidation finale coûtent 0,10 % du montant échangé. Le retrait à douze mois est financé par la réserve séparée. Le montant disponible pour le but exclut cette réserve.

| Allocation robuste, plafond de 8 % | Cible nominale à l'échéance | Avoir médian après vente | Trajectoires en déficit |
|---|---:|---:|---:|
| 100 CHF/mois, huit ans, inflation 2 % | 76 158 CHF | 63 035 CHF | 91,30 % |
| 250 CHF/mois | 76 158 CHF | 80 244 CHF | 33,55 % |
| Dix ans, 100 CHF/mois | 79 235 CHF | 71 767 CHF | 72,60 % |
| Cible ramenée à 55 000 CHF de pouvoir d'achat | 64 441 CHF | 63 035 CHF | 55,00 % |
| Inflation nulle | 65 000 CHF | 63 035 CHF | 58,00 % |
| Inflation de 4 % | 88 957 CHF | 63 035 CHF | 99,60 % |

Dans le cas de base, il manque en moyenne **12 964 CHF** sur l'ensemble des trajectoires et **14 200 CHF** parmi celles en déficit. Inverser l'ordre des huit blocs annuels tirés donne 91,20 % de déficits. Avec une capacité abaissée à 4 %, la solution robuste manque la même cible sur les 2 000 trajectoires. Ces fréquences dépendent des hypothèses et du marché échantillonné. Elles ne quantifient pas les événements au-delà de l'historique.

**Vérification indépendante en CHF.** En tout-cash, après paiement par la réserve, 35 000 + 96 × 100 = 44 600 CHF à huit ans. La cible nominale est 65 000 × 1,02⁸ = 76 157,86 CHF. L'écart vaut 31 557,86 CHF. Pour le portefeuille robuste avec marché et change constants, frais compris, **429,55 CHF par mois** financent la cible à huit ans. Avec 100 CHF/mois, la cible finançable est **38 024 CHF** de pouvoir d'achat initial. Aucun horizon annuel de 1 à 50 ans ne comble le déficit dans ce scénario de marché constant à 2 % d'inflation. [Écarts par scénario](results/goal_scenarios.csv) · [Trajectoires annuelles](results/funding_path.csv) · [Ajustements à marché constant](results/goal_adjustments.csv)

### Que se passe-t-il si le paiement arrive plus tôt ?

La réserve couvre les 15 000 CHF même en cas de perte totale des ETF. Pour tester une facture de **22 000 CHF**, on garde les positions de départ, les versements et un marché constant avant un choc simultané identique sur la valeur CHF de tous les ETF. Pour la parité de risque au plafond de 8 %, le paiement à un an est juste couvert après une perte de **92,59 %** et devient déficitaire au-delà. Si la facture arrive juste après l'achat, avant les versements et avant le règlement de toute vente, il manque déjà **3 531,50 CHF**. La solution robuste dispose de suffisamment de cash dans les deux cas. Le seuil de perte décrit la frontière de financement de ce scénario et n'a pas de probabilité associée. Les données disponibles étayent des stress empiriques et déterministes. Elles ne permettent pas d'étalonner la fréquence d'une perte conjointe extrême. [Stress de retrait et ressources mobilisables](results/reverse_stress.csv)

### Reproduire

Avec les dépendances de 6.1 et les résultats des sections 3.2, 4.2 et 6.1 présents, exécuter `python research/options/run.py`. Le programme vérifie les empreintes des entrées et compare ses sorties aux fichiers archivés. `python tests/test_client_options.py` vérifie notamment la conversion de richesse, les limites du mandat, les données futures, les frais et l'égalité au seuil de paiement. Le test de page est `python tests/test_options_app.py` avec les dépendances de l'application. [Paramètres de l'exemple](results/design.json) · [Empreintes des résultats](results/manifest.json)
