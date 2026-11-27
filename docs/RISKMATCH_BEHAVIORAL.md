# Questionnaire Discovery de RiskMatch

Version `discovery-v3.0.0`. Le questionnaire actif contient 30 cartes fixes, dans le même ordre et avec la même position des options pour tous les participants d’une même version. La graine de session ne change plus les questions. Les mêmes montants nominaux sont présentés dans la devise du mandat, en français ou en anglais. Le questionnaire porte sur des choix simulés.

## Six blocs

| Bloc | Cartes | Ce qu’il explore |
|---|---:|---|
| Gains et pertes possibles | 8 | Comparaison avec un solde inchangé. Deux tailles de perte (100 ou 500) et quatre ratios gain/perte par taille, avec probabilités de 50 %. |
| Risque face aux gains | 6 | Gain garanti ou gain incertain. La probabilité et l’écart de gain moyen varient. |
| Risque face aux pertes | 6 | Perte certaine ou risque de perdre davantage avec une possibilité de ne rien perdre. |
| Événements rares | 4 | Deux gains et deux pertes, de probabilité 1 % ou 5 %, comparés à un montant certain de même valeur espérée. |
| Baisses temporaires | 4 | Deux chemins depuis un indice de 100, mêmes résultats finaux à un an, mêmes probabilités et mêmes frais. Le creux en cours de route varie. |
| Vérification des choix | 2 | Comprendre une probabilité de 1 % et répondre de nouveau à la première situation avec les options inversées. |

## Les 30 cartes dans l’ordre affiché

Les formulations ci-dessous prennent le CHF comme exemple. « Non » garde l’option actuelle et « Oui » accepte l’alternative. Les cartes monétaires indiquent un solde fictif de 10 000. Pour les trajectoires, les deux résultats à un an sont équiprobables et les frais sont identiques. La carte CT01 demande combien de fois un événement de probabilité 1 % se produirait **en moyenne** sur 100 essais. La colonne finale indique la réponse comptée comme prudente pour l’indice de prudence provisoire.

| Ordre | ID | Bloc | Option actuelle (Non) | Alternative (Oui) | Indice de prudence |
|---:|---|---|---|---|---|
| 1 | GN01 | Risque face aux gains | gagner 100 CHF à coup sûr | accepter 50 % de chances de gagner 200 CHF, avec un solde inchangé sinon | Non |
| 2 | MX01 | Gains et pertes possibles | garder ton solde inchangé | accepter 50 % de chances de gagner 150 CHF et 50 % de risques de perdre 100 CHF | Diagnostic |
| 3 | TR01 | Baisses temporaires | 97 à 3 mois, 95 à 6 mois, puis 95 ou 112 à 1 an | 94 à 3 mois, 85 à 6 mois, puis 95 ou 112 à 1 an | Non |
| 4 | LS01 | Risque face aux pertes | perdre 100 CHF à coup sûr | accepter 50 % de chances de perdre 200 CHF, avec un solde inchangé sinon | Non |
| 5 | RR01 | Événements rares | perdre 10 CHF à coup sûr | accepter 1 % de chances de perdre 1000 CHF, avec un solde inchangé sinon | Non |
| 6 | CT01 | Vérification des choix | répondre « 10 fois en moyenne » | répondre « 1 fois en moyenne » | Diagnostic |
| 7 | GN02 | Risque face aux gains | accepter 25 % de chances de gagner 400 CHF, avec un solde inchangé sinon | gagner 80 CHF à coup sûr | Oui |
| 8 | MX02 | Gains et pertes possibles | garder ton solde inchangé | accepter 50 % de chances de gagner 500 CHF et 50 % de risques de perdre 500 CHF | Diagnostic |
| 9 | TR02 | Baisses temporaires | 83 à 3 mois, 91 à 6 mois, puis 100 ou 116 à 1 an | 94 à 3 mois, 97 à 6 mois, puis 100 ou 116 à 1 an | Oui |
| 10 | LS02 | Risque face aux pertes | accepter 75 % de chances de perdre 160 CHF, avec un solde inchangé sinon | perdre 100 CHF à coup sûr | Oui |
| 11 | RR02 | Événements rares | accepter 1 % de chances de gagner 1000 CHF, avec un solde inchangé sinon | gagner 10 CHF à coup sûr | Oui |
| 12 | GN03 | Risque face aux gains | gagner 120 CHF à coup sûr | accepter 75 % de chances de gagner 160 CHF, avec un solde inchangé sinon | Non |
| 13 | MX03 | Gains et pertes possibles | accepter 50 % de chances de gagner 100 CHF et 50 % de risques de perdre 100 CHF | garder ton solde inchangé | Diagnostic |
| 14 | TR03 | Baisses temporaires | 93 à 3 mois, 93 à 6 mois, puis 90 ou 120 à 1 an | 93 à 3 mois, 82 à 6 mois, puis 90 ou 120 à 1 an | Non |
| 15 | LS03 | Risque face aux pertes | perdre 100 CHF à coup sûr | accepter 25 % de chances de perdre 400 CHF, avec un solde inchangé sinon | Non |
| 16 | RR03 | Événements rares | accepter 5 % de chances de perdre 1000 CHF, avec un solde inchangé sinon | perdre 50 CHF à coup sûr | Oui |
| 17 | GN04 | Risque face aux gains | accepter 50 % de chances de gagner 600 CHF, avec un solde inchangé sinon | gagner 240 CHF à coup sûr | Oui |
| 18 | MX04 | Gains et pertes possibles | accepter 50 % de chances de gagner 1000 CHF et 50 % de risques de perdre 500 CHF | garder ton solde inchangé | Diagnostic |
| 19 | TR04 | Baisses temporaires | 80 à 3 mois, 85 à 6 mois, puis 98 ou 108 à 1 an | 90 à 3 mois, 97 à 6 mois, puis 98 ou 108 à 1 an | Oui |
| 20 | LS04 | Risque face aux pertes | accepter 50 % de chances de perdre 600 CHF, avec un solde inchangé sinon | perdre 320 CHF à coup sûr | Oui |
| 21 | RR04 | Événements rares | gagner 50 CHF à coup sûr | accepter 5 % de chances de gagner 1000 CHF, avec un solde inchangé sinon | Non |
| 22 | GN05 | Risque face aux gains | gagner 220 CHF à coup sûr | accepter 25 % de chances de gagner 800 CHF, avec un solde inchangé sinon | Non |
| 23 | MX05 | Gains et pertes possibles | garder ton solde inchangé | accepter 50 % de chances de gagner 200 CHF et 50 % de risques de perdre 100 CHF | Diagnostic |
| 24 | LS05 | Risque face aux pertes | perdre 180 CHF à coup sûr | accepter 25 % de chances de perdre 800 CHF, avec un solde inchangé sinon | Non |
| 25 | GN06 | Risque face aux gains | accepter 75 % de chances de gagner 400 CHF, avec un solde inchangé sinon | gagner 330 CHF à coup sûr | Oui |
| 26 | MX06 | Gains et pertes possibles | garder ton solde inchangé | accepter 50 % de chances de gagner 625 CHF et 50 % de risques de perdre 500 CHF | Diagnostic |
| 27 | LS06 | Risque face aux pertes | accepter 75 % de chances de perdre 400 CHF, avec un solde inchangé sinon | perdre 330 CHF à coup sûr | Oui |
| 28 | MX07 | Gains et pertes possibles | accepter 50 % de chances de gagner 125 CHF et 50 % de risques de perdre 100 CHF | garder ton solde inchangé | Diagnostic |
| 29 | MX08 | Gains et pertes possibles | accepter 50 % de chances de gagner 750 CHF et 50 % de risques de perdre 500 CHF | garder ton solde inchangé | Diagnostic |
| 30 | CT02 | Vérification des choix | accepter 50 % de chances de gagner 200 CHF, avec un solde inchangé sinon | gagner 100 CHF à coup sûr | Diagnostic |

## Indice de prudence et sauvegardes

L’indice de prudence provisoire utilise 20 cartes, à poids égal, réparties entre gains, pertes, événements rares et baisses temporaires. Avec au moins 14 réponses tranchées, le résultat est l’arrondi de 1 + 29 × la proportion de réponses prudentes parmi ces réponses. « Incertain » et « Passer » n’entrent pas dans ce calcul. Les huit choix mixtes, la vérification de probabilité et le choix répété sont descriptifs. La version actuelle du questionnaire ne collecte plus de choix de style et utilise le code neutre pour les nouveaux résultats.

Le moteur ramène l’indice S entre 0 et 1 par (S − 1) / 29, puis le combine avec les priorités des objectifs et l’horizon du mandat. Cela donne le poids de sécurité q. Pour les stratégies qui utilisent une utilité moyenne-variance, le moteur fixe λ = 1 + 13,3 × q² et maximise le rendement attendu diminué de λ/2 fois la variance. Une hausse de λ renforce la pénalité des fluctuations dans les deux sens. Les huit choix mixtes ne servent pas à estimer un coefficient individuel qui donnerait davantage de poids aux pertes qu’aux gains.

Le facteur 13,3 est un réglage expérimental qui donne λ ≈ 4,33 à q = 0,50. Il s’appuie sur un étalonnage par rapport au portefeuille de référence 60 % actions américaines et 40 % obligations du Trésor américain. Sa stabilité reste à vérifier sur plusieurs périodes et mandats. [Portefeuilles de référence](BASELINES.md)

À la fin du questionnaire, les seuils de gain sont affichés à côté de l’indice. Pour chaque perte possible, le plus grand gain refusé et le plus petit gain accepté encadrent le seuil. Si les deux se croisent, l’app affiche « Pas de seuil clair ». Avec des réponses dans un seul sens, elle affiche seulement la borne correspondante. Le nombre de réponses tranchées est indiqué pour chacune des deux séries.

Le détail expérimental « Aversion aux pertes dans l’utilité » calcule les bornes de `λ_perte` compatibles avec chaque série. Le modèle suppose que le pari est accepté si `V(G,L) = w_gain × G^α − w_perte × λ_perte × L^α ≥ 0`, avec `G` et `L` exprimés en montant positif. À `V = 0`, on obtient `λ_perte = (w_gain / w_perte) × (G / L)^α`. Un refus donne une borne inférieure stricte et une acceptation donne une borne supérieure inclusive. Le tableau compare quatre hypothèses fixées pour la simulation, avec les couples `(α, poids du gain/poids de la perte)` `(1, 50/50)`, `(0,8, 50/50)`, `(1, 45/55)` et `(1, 55/45)`. La probabilité objective des cartes reste 50/50. Les huit cartes ne permettent pas de distinguer à elles seules l’effet de la courbure, du poids des probabilités et du coefficient de perte. Le classement des portefeuilles continue d’utiliser sa pénalité de variance.

Les réponses issues d’un questionnaire retiré ne sont pas converties en réponses aux nouvelles cartes. Lors de la restauration, le mandat et les résultats déjà sauvegardés peuvent rester accessibles, tandis que Discovery s’ouvre sur le questionnaire actuel. La répartition et l’indice restent expérimentaux. Un refus de jouer un scénario du bloc mixte donne une observation de préférence, sans estimer à lui seul un coefficient individuel d’aversion aux pertes.

La source bilingue du questionnaire et du rapport est [discovery.py](../src/riskmatch/behavioral/discovery.py). Les routes actives sont `/api/discovery/session` et `/api/discovery/score`. Voir aussi le [protocole de test pilote](BEHAVIORAL_PILOT.md).
