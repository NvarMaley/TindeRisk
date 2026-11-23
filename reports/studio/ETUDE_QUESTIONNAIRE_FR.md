# Étude du questionnaire comportemental de RiskMatch

Le studio contient **23 cartes de calibration réparties en 7 catégories**, puis **2 comparaisons de portefeuilles et une relance conditionnelle**. **7 cartes forment le tronc commun** (C01, T01, L00, D01, H01, S01 et S03). Les **16 autres** sont conditionnelles. Une correction peut modifier le parcours et retirer les réponses aux cartes qui deviennent inactives. Le score comportemental conserve son barème. La version **studio-3** dérive la tranche indicative à partir des choix de portefeuille et des allocations calculées. La banque de recherche d’origine comprend aussi 15 cartes économiques. Le studio recueille ces informations dans un formulaire séparé et simplifié. [Code du studio](../../src/riskmatch_v2/studio_profile.py) · [Branchements](../../src/riskmatch_v2/interview.py) · [Banque de recherche](../02-questionnaire/CARDS.md)

La [proposition de calibration](CALIBRATION_QUESTIONNAIRE_FR.md) audite cette version et présente les 18 cartes du pilote de recherche.

Le bouton **Retour** efface la réponse à la carte précédente et toutes les réponses qui la suivent. Le parcours se recalcule à partir des réponses restantes. La croix sur un bouton indique un refus. **Je ne sais pas** conserve son rôle distinct. Dès que la compréhension est établie, les exercices G01 à G03 sont présentés à la suite. Les cartes G00, G04, T03 et L05 appartiennent au parcours historique. Les anciennes sauvegardes peuvent les afficher comme réponses passées.

## Pourquoi ces questions

- **Vérifier la compréhension avant l’interprétation.** Deux exemples de lancer indépendant permettent de vérifier qu’une mauvaise issue reste possible et que des victoires antérieures ne déterminent pas le prochain résultat. Une réponse incertaine appelle une relance.
- **Croiser plusieurs manifestations du risque.** Le confort déclaré, le choix d’un pari et la réaction envisagée face à une baisse de 15 % abordent des situations différentes. Quelqu’un peut accepter des fluctuations en général et vouloir vendre lorsqu’une perte devient concrète.
- **Faire varier un élément à la fois.** Les trois arbitrages G gardent le même pari et changent le montant certain. Les paires L présentent le même résultat économique en solde final puis en gains ou pertes. La première construction s’inspire du critère moyenne–variance. La seconde reprend l’idée d’un point de référence et l’effet possible de la présentation des résultats. [Markowitz, 1952](https://doi.org/10.1111/j.1540-6261.1952.tb01525.x) · [Kahneman et Tversky, 1979](https://www.jstor.org/stable/1914185)
- **Distinguer la volonté de prendre un risque de la capacité de le supporter.** Vendre pour payer une facture, à cause de l’inconfort ou par anticipation de nouvelles baisses peut relever de trois motifs différents. Le budget et la perte financièrement supportable sont recueillis dans le formulaire. La souplesse et les préférences de suivi aident à lire le profil. [CFA Institute, construction de portefeuille](https://www.cfainstitute.org/insights/professional-learning/refresher-readings/2026/basics-of-portfolio-planning-and-construction)

Les 26 cartes d’origine ont été reformulées pour le swipe. Le studio propose désormais aussi des choix explicites sur G01–G03 et D01, ainsi qu’une relance D06. **Oui** signifie que la proposition correspond au client. **Non** indique qu’elle ne lui correspond pas. **Incertain** permet de signaler qu’il ne souhaite pas trancher. Dans un arbitrage binaire entre un montant certain et un pari, le studio code non comme acceptation du pari. Les situations sont hypothétiques. Le barème et les bandes sont des hypothèses de conception sans validation psychométrique sur des participants.

## Choix explicites en service

| Carte | Proposition et choix affichés | Effet sur le profil |
|---|---|---|
| **G01, G02, G03** | Sur 1 000 CHF fictifs pendant un an, choisir le montant certain (1 020, 1 000 ou 1 040 CHF selon la carte) ou une chance sur deux de recevoir 900 CHF ou 1 200 CHF. | La certitude et le pari sont nommés directement. Les points et les bornes restent ceux de la grille ci-dessous. |
| **D01** | Le portefeuille perd 15 %. Choisir **Garder le portefeuille**, **Réduire le risque** ou **Revoir le plan avant d’agir**. | Garder donne 100 au domaine du maintien. Réduire ouvre les cartes D02–D04 sur le besoin de cash, l’inconfort et les perspectives. Revoir le plan ouvre D06 et laisse le domaine du maintien sans score. |
| **D06** | « Je reverrais le plan surtout pour vérifier si mon objectif reste atteignable. » Cette carte apparaît après le choix de revoir le plan. | Like identifie la vérification de l’objectif comme motif. Pass garde le motif ouvert. Incertain enregistre une absence de position nette. Aucun point de maintien. |

Le choix **Incertain** reste disponible. Les choix explicites sont conservés dans la sauvegarde. Les lignes historiques ci-dessous expliquent aussi le codage des réponses déjà enregistrées.

## Vérification sur des choix de portefeuille

Lorsque la compréhension de base est établie, les comparaisons terminent le parcours avant l’affichage du score. Le joueur peut aussi sélectionner « Aucun des deux, garder les CHF » ou « Incertain ». Les options représentent deux résultats fictifs en CHF sur un an, chacun à 50 %, avec les mêmes frais et le même accès aux fonds.

| Carte | Portefeuille A | Portefeuille B | Présentation | Seuil d’aversion γ |
|---|---|---|---|---:|
| **V01** | −2 % ou +6 % | −5 % ou +11 % | Comparaison de départ | 4,17 |
| **V02** | −2 % ou +6 % | −12 % ou +20 % | Deuxième comparaison | 1,67 |
| **V03** | −2 % ou +6 % | −4 % ou +12 % | Après deux A. B garde la volatilité de V01 et offre un rendement espéré plus élevé. | 8,33 |
| **V04** | −2 % ou +6 % | −13 % ou +19 % | Après deux B. B garde la volatilité de V02 et offre un rendement espéré plus faible. | 0,83 |

Chaque scénario fournit une moyenne μ et un écart-type σ. Avec deux résultats équiprobables, σ vaut la moitié de leur écart. On utilise les rendements en décimal. Dans le modèle moyenne–variance, l’utilité vaut `μ − γ × σ² / 2`. Le seuil `γ* = 2 × (μB − μA) / (σB² − σA²)` indique où A et B ont la même utilité. **A fixe une borne basse pour γ et B une borne haute.** Deux choix compatibles suffisent à estimer un intervalle, éventuellement ouvert vers le haut. B dans V01 et A dans V02 donnent par exemple **γ ∈ [1,67 ; 4,17]**. Des bornes incompatibles ou moins de deux choix A/B conduisent à « à confirmer » et la recherche se limite aux CHF. Un choix explicite de garder les CHF ou une capacité de perte à zéro oriente également vers les CHF.

Le moteur maximise ensuite cette même utilité aux bornes disponibles et sur une valeur intermédiaire de γ, avec les estimations annuelles du modèle CHF, les frais, la réserve, le budget de perte, les exclusions et les contraintes d’exécution. Quand γ n’a pas de borne haute, la solution à la limite est évaluée en CHF et le point de sensibilité utilise deux fois la borne basse. Chaque exemple est arrondi en positions entières et vérifié. Le minimum et le maximum des volatilités vérifiées forment la zone affichée. L’extrémité haute guide les autres stratégies et la recherche garde des options plus calmes. Le moteur recalcule avec le compte utilisé pour la comparaison et la composition.

Ces cartes apportent **zéro point** aux catégories. Le score global et ses composantes décrivent les réponses, et le profil signale si la personne choisit la fluctuation la plus large de V02 mais déclare qu’elle vendrait par inconfort après une baisse. Le dossier conserve les choix et les bornes. Les profils établis sous **studio-1** ou **studio-2** restent lisibles et une nouvelle calibration dans le studio applique la méthode actuelle.

La zone est une sensibilité au modèle sur des choix fictifs. Elle peut dépasser les scénarios montrés dans les cartes lorsque les estimations historiques de rendement poussent les allocations vers des actifs plus volatils. L’application signale cette extrapolation. Une validation sur des choix supplémentaires et des hypothèses de marché hors échantillon reste ouverte. [Code de calibration](../../src/riskmatch_v2/studio_profile.py) · [Moteur de portefeuille](../../src/riskmatch_v2/studio_allocation.py)

## Relecture bilingue du studio

Les cartes actives ont été relues avec leurs branchements. Les trois exemples indiquent directement qu’ils utilisent de l’argent fictif. Les cartes de cadrage distinguent explicitement « ni gain ni perte » du pari. Après une baisse, les relances reprennent le choix de réduire l’investissement et clarifient ses motifs. Les cartes de portefeuille précisent l’horizon d’un an. Le codage des réponses, les calculs et les seuils sont conservés. [Formulations anglaises du studio](../../src/riskmatch_v2/studio_profile.py) · [Traductions françaises](../../web/translations.js)

Le récapitulatif traduit séparément la catégorie et la réponse, y compris dans les anciens profils. Les motifs d’une réduction du risque et les commentaires sur la tranche s’affichent aussi en français lorsque cette langue est choisie.

## Grille des 26 cartes d’origine

Les énoncés ci-dessous traduisent les propositions d’origine. Les choix explicites actuels figurent plus haut. Pour les autres reformulations, les liens de la relecture bilingue donnent les libellés en service. Les cartes sont regroupées ici par catégorie. L’ordre de présentation complet est **C01, C02, T01, T02, G00, G01, G02, G03, G04, T03, L00, L01, L02, L03, L04, L05, D01, D02, D03, D04, D05, H01, H02, S01, S02, S03**.

### Compréhension de l’incertitude

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **C01** « Même à pile ou face avec une pièce équilibrée, je pourrais perdre cette manche. » | Comprendre qu’une issue défavorable reste possible. | Tronc commun | Compréhension validée. C02 est omise. | Déclenche la relance C02. |
| **C02** « Après trois victoires, je pourrais quand même perdre au prochain lancer indépendant. » | Comprendre l’indépendance du prochain lancer. | C01 non ou incertain | Rétablit la validation de la compréhension. | Compréhension non établie. Les arbitrages et les paires de cadrage restent masqués. |

### Tolérance déclarée

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **T01** « Si mes factures sont couvertes, j’accepterais de fortes fluctuations sur mes placements. » | Confort déclaré quand le besoin immédiat d’argent est mis à part. | Tronc commun | 100 points au confort déclaré, sous réserve de T02. | 0 point au confort déclaré, sous réserve de T02. |
| **T02** « Une perte temporaire de 2 000 CHF sur 10 000 CHF me ferait changer ma dernière réponse. » | Réaction à une baisse concrète de 20 %. | T01 oui ou non | Le confort déclaré devient indéterminé. Le sens du changement reste inconnu. | Le score de T01 est conservé. |
| **T03** « J’aimerais revoir ma réponse sur les fortes fluctuations. » | Réexaminer un décalage entre déclaration et décisions. | T01 oui avec au moins deux choix certains, ou T01 non avec au moins deux choix risqués | Le studio rouvre T01. Seule sa révision peut modifier le score. | La déclaration précédente est conservée. Le décalage seul ne bloque pas le score. |

### Arbitrages entre certitude et risque

La mise fictive est de **1 000 CHF pendant un an**. G01 à G03 utilisent le même pari (900 CHF ou 1 200 CHF, chacun à 50 %). Il offre un rendement moyen de 5 %. Les bornes φ sont arrondies ci-dessous.

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **G00** « Je peux mettre 1 000 CHF de côté pendant un an et comparer deux offres fictives. » | Acceptation de la mise et de l’horizon de l’exercice. | Tronc commun | Ouvre G01–G03 si la compréhension est validée. | Les arbitrages restent masqués. Le seuil de deux arbitrages répondus ne peut pas être atteint. |
| **G01** « Je choisirais 1 020 CHF garantis plutôt qu’une chance sur deux d’obtenir 900 CHF ou 1 200 CHF. » | Préférence face à une offre certaine de 2 %. | Compréhension validée et G00 oui | Certitude. 0 point et φ ≥ 2,67. | Pari. 100 points et φ ≤ 2,67. |
| **G02** « Je choisirais 1 000 CHF garantis plutôt qu’une chance sur deux d’obtenir 900 CHF ou 1 200 CHF. » | Préférence face à la restitution certaine de la mise. | Compréhension validée et G00 oui | Certitude. 0 point et φ ≥ 4,44. | Pari. 100 points et φ ≤ 4,44. |
| **G03** « Je choisirais 1 040 CHF garantis plutôt qu’une chance sur deux d’obtenir 900 CHF ou 1 200 CHF. » | Préférence face à une offre certaine de 4 %, proche du rendement moyen du pari. | Compréhension validée et G00 oui | Certitude. 0 point et φ ≥ 0,89. | Pari. 100 points et φ ≤ 0,89. |
| **G04** « Je maintiens mes choix, même s’ils vont dans des directions opposées. » | Permet de maintenir ou de revoir des arbitrages incompatibles dans le modèle. | Les bornes déduites des réponses G sont incompatibles | Le conflit reste inscrit et empêche le score tant que les arbitrages sont incompatibles. | Le studio rouvre G01. Le conflit disparaît si les arbitrages révisés deviennent compatibles. |

### Point de référence et cadrage

Les cartes L apportent **0 point au score de risque**. Le profil affiche le nombre de paires concordantes parmi celles où les deux réponses sont oui ou non.

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **L00** « Pour juger une perte, je pense d’abord au prix que j’ai payé. » | Repère déclaré pour juger un gain ou une perte. | Tronc commun | Le prix payé sert de repère déclaré. | Le prix d’achat n’est pas désigné comme premier repère. |
| **L01** « Je préférerais garder 1 000 CHF avec certitude plutôt qu’avoir une chance sur deux de finir à 900 CHF ou à 1 100 CHF. » | Choix sous la forme d’un solde final. À comparer avec L02. | Compréhension validée | Choisit le solde certain dans ce cadrage. | Accepte le pari dans ce cadrage. |
| **L02** « Je préférerais ne rien gagner plutôt qu’avoir une chance sur deux de perdre ou de gagner 100 CHF. » | Reformule L01 en gain ou perte autour de la mise. | Compréhension validée | Choisit la variation nulle. Concorde avec L01 oui. | Accepte le pari. Concorde avec L01 non. |
| **L03** « Je préférerais garder 2 000 CHF avec certitude plutôt qu’avoir une chance sur deux de finir à 1 800 CHF ou à 2 200 CHF. » | Répète le cadrage en solde final à une mise doublée, aux mêmes proportions. | Compréhension validée | Choisit le solde certain dans ce cadrage. | Accepte le pari dans ce cadrage. |
| **L04** « Je préférerais que le montant reste inchangé plutôt qu’avoir une chance sur deux de perdre ou de gagner 200 CHF. » | Reformule L03 en gain ou perte autour de la mise. | Compréhension validée | Choisit la variation nulle. Concorde avec L03 oui. | Accepte le pari. Concorde avec L03 non. |
| **L05** « J’aimerais revoir le même choix présenté de deux manières. » | Propose une relecture après deux inversions. | L01 et L02 s’opposent, et L03 et L04 s’opposent aussi | Le studio rouvre L01. Seule une réponse effectivement revue peut changer la concordance. | Les réponses sont conservées. |

### Réaction à une perte

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **D01** « Après une baisse de 15 %, j’envisagerais de vendre. » | Réaction envisagée face à une baisse concrète et intérêt de clarifier le motif. | Tronc commun | Ouvre D02, D03 et D04. Le score de maintien dépend alors de D03. | 100 points au maintien sous stress. Ouvre D05. |
| **D02** « Je vendrais après cette baisse pour payer une facture. » | Besoin de liquidités comme motif de vente. | D01 oui | Le motif figure dans les réponses. Aucune dépense ou réserve n’est ajoutée automatiquement. | La facture n’est pas citée comme motif. Aucun effet chiffré. |
| **D03** « Même si mes factures sont couvertes, l’inconfort me ferait vendre. » | Réaction émotionnelle quand les dépenses sont couvertes. | D01 oui | 0 point au maintien sous stress. Le profil mentionne l’inconfort comme motif. | 100 points. Le profil indique que l’inconfort seul n’est pas un motif de vente. |
| **D04** « Je vendrais parce que je pense que les cours vont continuer à baisser. » | Anticipation d’une nouvelle baisse comme motif. | D01 oui | Ouvre D05. L’opinion ne modifie pas les prévisions du moteur. | D05 reste masquée dans cette branche. Aucun effet chiffré. |
| **D05** « Je comparerais avec un portefeuille qui réduit explicitement l’exposition à un choc. » | Intérêt pour une comparaison avec une protection contre un choc. | D01 non ou D04 oui | Intérêt indiqué dans les réponses. Aucune contrainte d’allocation n’est ajoutée. | Pas d’intérêt affirmé. Aucun effet chiffré. |

### Souplesse de l’objectif

L’indicateur de souplesse fait la moyenne des réponses interprétables de H01 et H02. Il est distinct du score de risque. Le profil résume les réponses sur la date et sur le montant.

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **H01** « Je pourrais repousser la date de mon objectif si cela prenait plus de temps. » | Possibilité de revoir l’horizon. | Tronc commun | Ouvre H02. Compte 100 pour la souplesse. | Ouvre aussi H02. Compte 0 pour la souplesse. |
| **H02** « Je pourrais accepter un montant final plus faible. » | Possibilité de revoir le montant indépendamment de l’horizon. | H01 oui ou non | Compte 100 pour la souplesse. | Compte 0 pour la souplesse. |

### Préférences de suivi

Ces cartes apportent **0 point de risque**. Le résumé du profil utilise S01. S02 et S03 restent consultables dans le détail des réponses.

| Carte et énoncé | Ce qu’elle teste | Quand elle apparaît | Oui | Non |
|---|---|---|---|---|
| **S01** « J’aime vérifier souvent la valeur de mes placements. » | Fréquence de consultation souhaitée. | Tronc commun | Le profil indique un suivi fréquent. Ouvre S02. | Le profil indique un suivi moins fréquent. S02 reste masquée. |
| **S02** « Entre deux points de suivi programmés, une alerte de risque me suffirait. » | Acceptation d’un suivi par alerte entre des revues prévues. | S01 oui | Une alerte pourrait suffire. Aucun paramétrage n’est déclenché. | La formule proposée ne suffit pas selon la réponse. |
| **S03** « Dans un portefeuille combiné, je veux suivre chaque stratégie séparément. » | Intérêt pour une lecture par stratégie après combinaison. | Tronc commun | Intérêt déclaré pour le détail par stratégie. | Pas de préférence affirmée pour cette vue. |

### Effet d’une réponse incertaine

- **C01** incertain ouvre C02. **C02** incertain laisse la compréhension indéterminée.
- **T01** incertain rend le confort déclaré indéterminé et masque T02. **T02** incertain conserve le résultat de T01.
- **G00** incertain masque les arbitrages. Pour **G01–G03**, un choix incertain est retiré de la moyenne et des bornes φ.
- Pour **L01–L04**, une réponse incertaine retire la paire correspondante du calcul de concordance. L05 exige deux inversions explicites.
- **D01** incertain rend le maintien indéterminé et masque les relances. Si D01 vaut oui et **D03** incertain, le maintien reste indéterminé.
- **H01** incertain masque H02 et **S01** incertain masque S02. Les réponses incertaines à **G04**, **T03** et **L05** ne déclenchent aucune correction automatique. Les autres réponses incertaines restent consultables, sans ajouter de points.

## Comment RiskMatch construit le score

| Domaine | Calcul appliqué |
|---|---|
| **Confort déclaré** | T01 oui = 100 et T01 non = 0. T01 incertain ou T02 oui rend le domaine indéterminé. |
| **Choix sous incertitude** | Chaque G01–G03 vaut 0 pour le montant certain et 100 pour le pari. Le domaine est la moyenne arrondie des choix binaires disponibles. |
| **Maintien sous stress** | D01 non = 100. Si D01 oui, D03 non = 100 et D03 oui = 0. Dans les autres cas, le domaine est indéterminé. |

Le score final est la **moyenne arrondie des domaines interprétables, à poids égal**. Il faut que les cartes actives soient terminées, que la compréhension soit validée, que deux arbitrages G au minimum aient une réponse binaire, que deux domaines au minimum soient interprétables et que les bornes φ soient cohérentes. Une borne d’un seul côté suffit si ces autres conditions sont remplies. Le profil affiche **Indéterminé** quand les conditions échouent et le calcul des portefeuilles attend une révision. [Calcul du score](../../src/riskmatch_v2/studio_profile.py)

### Le rôle des bornes φ

Le modèle compare les choix par le critère moyenne–variance **U = rendement moyen − φ × variance / 2**. Le pari commun a un rendement moyen de 5 % et une variance de 0,0225 sur la mise de 1 000 CHF. Face à une offre certaine à 2 %, le seuil d’indifférence vaut **2 × (0,05 − 0,02) / 0,0225 ≈ 2,67**. Le choix certain donne une borne inférieure sur φ. Le pari donne une borne supérieure. Une borne inférieure supérieure à la borne supérieure signale une contradiction dans le modèle. φ sert à vérifier la cohérence. La valeur de φ n’entre pas directement dans la formule du score ou dans la bande de volatilité. [Moteur des bornes](../../src/riskmatch_v2/interview.py)

### Exemple vérifié

T01 oui et T02 non donnent **100**. G01 oui, G02 non et G03 oui donnent **33** et des bornes compatibles, de **2,67 à 4,44** environ. D01 oui et D03 oui donnent **0**. La moyenne arrondie de 100, 33 et 0 donne **44/100**. Le profil est **Modéré**, avec une volatilité annuelle estimée de **8 à 12 %** sur la poche investissable. Par ailleurs, G02 oui et G03 non imposeraient simultanément φ ≥ 4,44 et φ ≤ 0,89. Ce conflit empêche la production d’un score tant qu’il persiste. [Rejeu du studio](browser-check.json) · [Tests de calibration](../../tests/test_studio_profile.py)

| Score | Profil | Bande de volatilité annuelle de la poche investissable |
|---|---|---|
| 0–19 | Très prudent | 0–4 % |
| 20–39 | Prudent | 4–8 % |
| 40–59 | Modéré | 8–12 % |
| 60–79 | Orienté croissance | 12–20 % |
| 80–100 | Offensif | 20 % et plus |

La volatilité mesure les fluctuations estimées. La **capacité de perte** est un montant en CHF, comparé aux pertes dans les scénarios du moteur. Une capacité à zéro limite les propositions à la poche en espèces CHF lorsque le reste du dossier est interprétable. La réserve, les exclusions et les contraintes obligatoires peuvent modifier ou bloquer les propositions. Les réponses sur la souplesse ne changent jamais la date ou le montant de l’objectif automatiquement. [Paramètres des profils](../../src/riskmatch_v2/risk_review.py) · [Contrôles d’allocation](ALLOCATION.md)

## Champs du formulaire financier

Ces champs recueillent une donnée ou une préférence. Ils apportent **0 point au score comportemental**.

| Libellé du studio | Utilité |
|---|---|
| **Starting budget · CHF** | Capital total à répartir. |
| **Cash to set aside · CHF** | Réserve en CHF à garder hors de la poche investie. |
| **Loss you can afford · CHF** | Perte financièrement supportable utilisée comme contrainte lors des tests de scénarios. |
| **Target amount · CHF** | Montant total visé à l’échéance, réserve restante comprise. |
| **Target date** | Date qui fixe l’horizon et le taux nécessaire pour atteindre le montant cible. |
| **CHF savings rate · %** | Taux annuel facultatif sur la réserve. Le modèle suppose 0 % si le champ est vide. |
| **Annual return aim · %** | Rendement annuel souhaité sur la poche investie. Le taux nécessaire est calculé à partir de l’objectif et de l’échéance. |
| **Environmental preference** | Préférence facultative pour une intensité d’émissions mesurée plus faible. |
| **Companies to exclude** | Exclusions de titres détenus directement. Elles ne garantissent pas une exclusion indirecte par les ETF. |
| **Planned spending · CHF**, **Spending date**, **Saved asset filter**, **Saved mandatory rule** | Paramètres proposés à la révision lorsqu’un dossier précédent les utilise. L’exclusion dédiée de Chevron reste disponible pour les dossiers qui l’avaient choisie. |

[Formulaire du studio](../../web/app.js) · [Réserve et répartition finale](README.md)

## Limites de l’interprétation

Les réponses décrivent des choix hypothétiques dans le contexte présenté. Une perte réelle, une mise différente ou un autre horizon peuvent changer ces choix. Deux inversions sur les cartes L motivent une relecture, sans suffire à établir un biais durable. La fréquence de consultation ne mesure pas l’aversion au risque. Les tests vérifient les règles et les parcours sur des cas fictifs. Valider la mesure elle-même demanderait des réponses de participants, des mesures répétées et une comparaison avec des décisions observées.
