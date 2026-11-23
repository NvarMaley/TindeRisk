# Portefeuilles construits avec les 13 ETF

Le moteur examine SPY, IEF, GLD, TLT, XLK, XLF, XLE, XLV, XLY, XLP, XLI, XLB et XLU. Les 13 titres ont satisfait aux critères de cotation aux huit dates de décision. Le calcul utilise 732 à 744 rendements communs en CHF dans chacune des fenêtres de 756 séances. Les 13 moyennes, la matrice de covariance 13 × 13 et l'incertitude sur les moyennes sont estimées avant chaque décision. Le portefeuille de référence 60/40 conserve ses proportions SPY/IEF. [Protocole](PROTOCOL.md) · [Critères par titre et par date](results/frontier/eligibility.csv) · [Paramètres estimés](results/frontier/training.json)

## Ce que change le choix de l'univers

Rendement annuel net moyen du foyer sur sept cohortes financées séparément entre octobre 2019 et octobre 2026. Les quantités sont décidées avant l'exécution à la prochaine clôture admissible. Le retrait de 15 000 CHF, le capital de 50 000 CHF, la limite de 8 % sur la poche et les frais de 10 points de base sont identiques.

| Portefeuille conservé pendant un an | 3 candidats | 13 candidats |
|---|---:|---:|
| Mix fixe SPY/IEF | 2,96 % | 2,96 % |
| Optimisation classique | 4,36 % | 2,32 % |
| Optimisation robuste | 4,17 % | 2,43 % |

Le calcul comprend 462 cas pour le grand univers, huit décisions et 320 points de frontière. Deux des 320 points ont un statut de précision réduite du solveur. Le contrôle indépendant des contraintes les admet à la tolérance enregistrée. Les 1 485 portefeuilles de sensibilité satisfont aux contraintes de leurs propres estimations. Les intervalles sur le gain d'utilité de la robuste face au mix fixe et à la robuste à trois ETF englobent zéro aux deux niveaux d'aversion. Le catalogue conserve la sélection manuelle fictive. [Exécutions et retraits](results/execution/cohorts.csv) · [Scores appariés](results/client_value.csv) · [Dispersion](results/frontier/dispersion.csv)

## Exemple du 30 octobre 2026

La robuste investit 21 141,40 CHF sur les 35 000 CHF disponibles avant frais. Les positions dépassant un centime sont GLD (8 138,20 CHF), XLK (4 125,39), XLF (2 986,23), XLU (2 043,60), XLV (1 744,09), XLE (1 305,01) et XLP (798,88). Elle conserve 13 837,46 CHF en liquidités supplémentaires et paie 21,14 CHF à l'entrée. Les rendements annuels nets estimés sont de 12,40 % sur la poche et 8,68 % sur le foyer. Les volatilités estimées sont de 8,00 % et 5,60 %. La différence avec les performances historiques illustre l'incertitude des rendements attendus.

Les scénarios recalculés utilisent les 13 séries et le change conjointement. Avec une épargne de 100 CHF par mois, 84,0 % des 2 000 trajectoires robustes manquent le but réel de 65 000 CHF à huit ans. À 250 CHF par mois, la proportion tombe à 27,9 %. [Fiches client](results/options/options.csv) · [Scénarios de financement](results/options/goal_scenarios.csv) · [Choc et contraintes](results/options/reverse_stress.csv)

## Reproduire et essayer

Dans l'environnement du projet avec Python 3.12.6, installer les dépendances de recherche et d'application puis exécuter depuis la racine :

```sh
python -m pip install -r requirements-frontier.txt -r requirements-app.txt
OPENBLAS_NUM_THREADS=1 python research/universe/run.py
python -m streamlit run app/intake.py
```

**Portfolio options** ouvre le comparatif historique à 13. Une case affiche l'ancienne référence. Une fois le mandat renseigné, **Apply the 13-ETF model to my intake** utilise le montant investissable après la réserve, les exclusions de tickers, le plafond choisi et la dernière estimation archivée disponible au début du mandat. Une exclusion textuelle nécessitant la composition des fonds suspend le calcul. Les 2 000 trajectoires publiées concernent le foyer illustratif. Dans la démo portable, les 13 prix, les modèles de risque et les allocations sont fictifs. Le suivi de compte et la confirmation restent dans le périmètre du mandat fictif autorisé.

## Autres simplifications constatées lors de la revue

| Sujet | Périmètre réel et conséquence |
|---|---|
| Univers économique | Neuf des 13 fonds couvrent des secteurs actions américains, auxquels s'ajoute SPY. IEF et TLT représentent deux maturités du Trésor américain. GLD représente l'or. Les poids sectoriels peuvent se recouper avec SPY. Ces données permettent une comparaison américaine en CHF. Elles ne constituent pas une allocation mondiale complète. |
| Études d'origine | Les analyses descriptives individuelles couvrent déjà les 13 fonds. Le portefeuille détaillé du chapitre 4 et les expériences historiques H01/H02/H07 ont des références figées plus étroites. H03 étudie IEF, H04 étudie SPY, H06 teste une vue de sentiment. Leurs scores décrivent leurs univers respectifs. La version élargie réestime les sensibilités au choc conjoint pour chacun des 13 fonds. |
| Profil, devise et mandat | L'entretien repose sur des choix hypothétiques et un plafond de risque choisi explicitement. Le prototype estime le risque en CHF. Les préférences libres et les exclusions nécessitant les positions sous-jacentes ne sont pas traduites automatiquement. Le suivi persistant et le pitch restent des cas pédagogiques. |
| Validation | Les sept années de comparaison avaient déjà été étudiées. Les 462 lignes agrègent des variantes sur ces mêmes années. Les sept signaux n'ont aucune période prospective indépendante validée. H05 attend toujours les versions comptables disponibles aux dates de décision. |
| Frais et exécution | Frais, change, liquidité disponible et règlement sont modélisés. Le cash CHF rapporte zéro et les simulations omettent les impôts. Le registre utilise des clôtures et des unités fractionnaires. Les flux du suivi sont synthétiques. |
| Publication | Le ZIP exportable contient les ressources fictives. Les droits de redistribution des archives tierces du dépôt complet, la mise en ligne publique et la relecture humaine restent ouverts. |

[Audit détaillé](../../METHODOLOGY_AUDIT.md) · [Contrôles de publication](../release/README.md)
