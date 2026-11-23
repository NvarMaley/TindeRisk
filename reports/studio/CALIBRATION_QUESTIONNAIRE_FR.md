# Audit et proposition de calibration du questionnaire

Je recommande **18 cartes dans la banque pilote**, avec **8 cartes communes** et des relances ciblées. Un parcours où la compréhension est établie contient **14 à 18 cartes**. S’il reste impossible d’établir la compréhension, le parcours contient **9 à 11 cartes** et la tolérance globale reste indéterminée. Le pilote se trouve dans le code de recherche. Le studio continue d’appliquer la version actuelle pendant cette phase de calibration.

## Diagnostic du questionnaire actuel

Les 26 cartes actuelles ont une bonne structure de départ. Elles distinguent délibérément le discours, la décision sous incertitude et la réaction à une baisse. La validation de compréhension, le droit de répondre « incertain » et le contrôle des contradictions sont à conserver. Le problème principal vient de la **quantité d’information par carte**. Certaines relances recueillent une intention de revoir sa réponse sans résoudre le désaccord. D’autres demandent déjà au client comment afficher ou comparer un portefeuille avant de connaître son profil.

| Ce que dit le code actuel | Effet possible | Choix pour le pilote |
|---|---|---|
| T01 donne directement 0 ou 100. T02 peut supprimer tout le domaine sans établir le sens du changement. | Une réponse peut peser sur un tiers du score global. Précision faible sur les situations intermédiaires. | Deux propositions concrètes, dont une orientée vers la stabilité. Elles donnent 0, 50 ou 100 sur deux réponses binaires. |
| G00 demande si le client peut mettre 1 000 CHF de côté malgré le caractère fictif du scénario. | Un refus peut relever du budget ou du choix de la mise. Il rend ensuite le score impossible. | La mise est explicitement fictive. Le formulaire financier évalue séparément le capital et la capacité de perte. |
| G01–G03 utilisent le même pari à trois prix. Le nombre de choix risqués alimente le score. | Bon contrôle de cohérence, mais les choix aux extrêmes rendent parfois la troisième question redondante. | Deux prix encadrent le choix. Un troisième apparaît lorsque les réponses diffèrent ou qu’une réponse est incertaine. |
| Un refus de vendre en D01 suffit à obtenir 100 pour le maintien. Un oui en D01 ouvre surtout des questions de motif. | À partir d’un seul seuil, on distingue mal quelqu’un qui tient à −10 % mais envisage de vendre à −20 %. | Deux niveaux de baisse dans la même situation. Une relance précise l’inconfort lorsque le maintien est incertain. |
| Deux paires de cadrage répètent le même mécanisme à des mises proportionnelles. L05 demande de revoir. | Bonne idée expérimentale, mais la répétition attire potentiellement l’attention sur l’objet du test. | Garder une paire de cadrage. Utiliser deux cartes distinctes pour observer la réticence aux pertes dans un pari mixte. |
| D05 et S03 demandent si le client souhaiterait une option ou une présentation particulière. | Réponses utiles pour une interface après le résultat. Peu d’information supplémentaire sur la volonté de prendre du risque. | Garder une préférence de suivi au départ. Reporter la vue par stratégie et la comparaison avec protection à l’étape des portefeuilles. |

Deux distinctions évitent de surinterpréter le résultat. Premièrement, hésiter face à un pari mélange perception du risque, préférence pour la certitude et sensibilité aux pertes. Deuxièmement, une différence entre deux formulations est une **observation ponctuelle**. Les paris du pilote sont hypothétiques. Une meilleure couverture de situations améliore la lisibilité du profil et les contrôles internes. La précision psychométrique demande des données de participants, une mesure répétée et une validation sur des décisions pertinentes. [Holt et Laury, rôle des montants et des incitations](https://pubs.aeaweb.org/doi/10.1257/000282802762024700) · [CFA Institute, profil financier et comportemental](https://rpc.cfainstitute.org/research/reports/investment-risk-profiling)

La [grille complète des 26 cartes actuellement en service](ETUDE_QUESTIONNAIRE_FR.md) détaille déjà leurs énoncés, branchements, réponses et effets. Le tableau qui suit donne l’équivalent complet pour le **pilote**.

## Énoncés et réponses du pilote

**Like** signifie que la proposition correspond au client. **Pass** indique qu’elle ne lui correspond pas. **Incertain** indique une réponse non déterminée et reste disponible sur chaque carte. Les codes ci-dessous appartiennent à la banque pilote. Les énoncés sont appliqués dans l’ordre du tableau.

| Catégorie · Carte · Proposition | Affichage | Like · sens et effet | Pass · sens et effet |
|---|---|---|---|
| **Compréhension · C01** · Même avec une pièce équilibrée, je peux perdre au prochain lancer. | Tronc commun | Reconnaît une issue défavorable. Compréhension 100, ouvre les exercices hypothétiques. | Ouvre C02. La compréhension attend cette relance. |
| **Compréhension · C02** · Après trois victoires, la manche suivante peut encore être perdue si le tirage est indépendant. | C01 Pass ou Incertain | Reconnaît l’indépendance. Compréhension 100 et ouvre les exercices. | Aucun oui de compréhension. Deux Pass donnent 0. Si une réponse était incertaine, la catégorie reste indéterminée. |
| **Tolérance · T01** · J’accepterais des fluctuations importantes si je n’avais pas besoin de cet argent pendant cinq ans. | Tronc commun | Accepte la fluctuation dans cette situation. 100 à cet item. | Hésite ou privilégie davantage de stabilité. 0 à cet item. |
| **Tolérance · T02** · Je choisirais un placement plus régulier même si son rendement espéré était plus faible. | Tronc commun | Accepte le coût de la stabilité. 0 à cet item de tolérance. | Ne choisit pas cette contrepartie pour la stabilité. 100 à cet item. |
| **Arbitrage · G01** · Sur une mise fictive de 1 000 CHF, je préfère recevoir 1 020 CHF avec certitude plutôt qu’une chance sur deux de recevoir 900 CHF ou 1 200 CHF. | Compréhension établie | Préfère la certitude à 2 %. 0 à l’item. | Choisit le pari selon le codage. 100 à l’item. |
| **Arbitrage · G02** · Sur la même mise, je préfère recevoir 1 040 CHF avec certitude plutôt que tenter le même pari, 900 CHF ou 1 200 CHF à chances égales. | Compréhension établie | Préfère la certitude à 4 %. 0. | Choisit le pari. 100. |
| **Arbitrage · G03** · Sur la même mise, je préfère recevoir 1 030 CHF avec certitude plutôt que tenter le même pari, 900 CHF ou 1 200 CHF à chances égales. | G01 et G02 diffèrent, ou l’une des deux est incertaine | Préfère la certitude à 3 %. 0. | Choisit le pari. 100. |
| **Maintien · D01** · Après une baisse de 10 %, je garderais le portefeuille jusqu’à la prochaine revue si mes dépenses et mon objectif restent couverts. | Tronc commun | Disposé à tenir jusqu’à la revue à −10 %. 100. | Refuse cette proposition de maintien. 0 et relance D03. |
| **Maintien · D02** · Dans la même situation, après une baisse de 20 %, je garderais le portefeuille jusqu’à la prochaine revue. | Tronc commun | Maintien déclaré à −20 %. 100. Si D01 vaut Pass, le domaine demande une relecture. | Maintien refusé à −20 %. 0 et relance D03. |
| **Maintien · D03** · Même si une revue confirme que mon objectif reste finançable, la baisse me donnerait envie de réduire le risque. | Sauf si D01 et D02 valent Like | Signale un inconfort après revue. Commentaire de profil, sans ajouter une voix au score. | Ne confirme pas ce motif de réduction. La réponse n’annule pas les choix D01 et D02. |
| **Pertes mixtes · L01** · Avec de l’argent fictif, j’accepterais une chance sur deux de perdre 100 CHF et une chance sur deux de gagner 150 CHF. | Compréhension établie | Accepte le pari mixte à +150 CHF. Réticence 0 sur cet item. | Refuse le pari. Réticence 100 sur cet item. |
| **Pertes mixtes · L02** · Avec de l’argent fictif, j’accepterais une chance sur deux de perdre 100 CHF et une chance sur deux de gagner 200 CHF. | Compréhension établie | Accepte le pari à +200 CHF. Réticence 0. | Refuse le pari. Réticence 100. Si L01 vaut Like, la catégorie est indéterminée. |
| **Cadrage · F01** · Sur une mise de 1 000 CHF, je préfère finir à 1 000 CHF avec certitude plutôt qu’avoir une chance sur deux de finir à 900 CHF ou 1 100 CHF. | Compréhension établie | Certitude en solde final. À comparer avec F02. | Pari en solde final. À comparer avec F02. |
| **Cadrage · F02** · Sur la même mise, je préfère que mon argent reste inchangé plutôt qu’avoir une chance sur deux de perdre ou gagner 100 CHF. | Compréhension établie | Certitude en gains et pertes. Concordance 100 si F01 Like et 0 si F01 Pass. | Pari en gains et pertes. Concordance 100 si F01 Pass et 0 si F01 Like. |
| **Souplesse · H01** · Si mon objectif était difficile à atteindre, je pourrais repousser la date. | Tronc commun | Peut envisager un horizon plus long. 100 sur cet item de souplesse. | Garde la date comme priorité. 0 de souplesse sur cet item. |
| **Souplesse · H02** · Si mon objectif était difficile à atteindre, je pourrais réduire le montant visé. | Tronc commun | Peut envisager de revoir le montant. 100 de souplesse. | Garde le montant comme priorité. 0 de souplesse. |
| **Suivi · S01** · J’aime vérifier souvent la valeur de mes placements. | Tronc commun | Préférence de suivi fréquent 100. Ouvre S02. | Préférence de suivi fréquent 0, S02 est omise. |
| **Suivi · S02** · Entre deux revues prévues, une alerte de risque me suffirait. | S01 Like | Une alerte peut suffire. Information qualitative à confirmer lors du suivi. | Une alerte seule ne suffit pas selon la réponse. Aucun point. |

Incertain n’entre dans aucune moyenne. Pour C01, il ouvre C02. Pour G, il peut ouvrir le troisième prix. Pour D, il peut ouvrir la relance sur l’inconfort. Pour F, il rend la paire indéterminée. À C02, l’absence de Like garde les exercices hypothétiques masqués. Dans H, un seul choix binaire produit un indicateur fondé sur un seul item, ce qui doit rester visible. Dans S, « incertain » n’ouvre pas S02.

## Algorithme et lecture du profil

Le [module pilote](../../src/riskmatch_v2/questionnaire_pilot.py) calcule les **huit catégories**, la couverture des réponses et la volonté globale. Une catégorie reçoit un score sur 100 lorsqu’elle a des données exploitables. Le profil affiche **Indéterminé** si les données manquent ou si les réponses se contredisent directement. La proportion de réponses exploitables n’est pas une probabilité que le résultat soit correct.

- **Volonté globale** = moyenne arrondie de **Tolérance**, **Arbitrage** et **Maintien**, après la fin du parcours. Il faut deux réponses binaires en tolérance, deux en arbitrage, deux en maintien et une compréhension établie. Un arbitrage incohérent ou une tenue déclarée à −20 % avec refus de tenir à −10 % rend le domaine concerné indéterminé.
- **Cohérence des arbitrages.** À pari identique, choisir un montant sûr plus faible tout en refusant un montant sûr plus élevé déclenche un signal à revoir. Les nombres de points sont des résumés de réponses, sans estimation de l’aversion absolue ou du coefficient d’utilité.
- **Écart entre dimensions.** Un écart d’au moins 67 points entre les trois domaines conserve le score descriptif et signale « à confirmer ». Par exemple, aimer l’idée du risque et rejeter les deux scénarios de baisse mérite une explication explicite. Le seuil est une convention du pilote.
- **Pertes mixtes et cadrage.** La réticence et la concordance ont chacune leur score. Un score de 100 signifie respectivement plus de réticence ou plus de concordance. Elles enrichissent le commentaire et gardent leur propre échelle. Elles n’entrent pas dans la moyenne globale.
- **Souplesse et suivi.** La souplesse résume H01–H02. Le suivi fréquent vient de S01. La préférence pour les alertes est affichée à part. Ces indications guident l’explication et la présentation.

Deux réponses binaires ne suffisent pas à distinguer 51 de 52 sur un trait psychologique. Le résultat doit être lu comme une synthèse d’observations, avec les réponses et les incohérences visibles. Le pilote ne transforme aucun point en tranche de volatilité à ce stade. Les seuils de traduction en contrainte d’allocation devront être justifiés et comparés à ceux de la version actuelle avant intégration au studio.

## Utilisation avec les actifs et les portefeuilles

| Signal | Utilisation prévue | Limite |
|---|---|---|
| Maintien faible ou inconfort persistant | Mettre au premier plan le scénario de baisse, la baisse historique maximale et la perte en CHF des portefeuilles compatibles. | Une baisse passée ou simulée ne borne pas la prochaine perte. |
| Écart entre tolérance déclarée et réaction | Comparer deux portefeuilles compatibles avec des profils de baisse différents et inviter à confirmer la préférence. | Cela ne justifie pas de proposer un actif risqué à partir du seul résultat d’une carte. |
| Volonté élevée et capacité de perte faible | Appliquer d’abord les limites financières et expliquer pourquoi certaines stratégies disparaissent. | La réserve en CHF, l’horizon et les exclusions proviennent du formulaire. |
| Souplesse sur la date ou le montant | Mettre en évidence l’option correspondante si le comparatif révèle un écart avec l’objectif. | Le client confirme tout changement. |
| Préférence de suivi | Adapter l’ordre de présentation du suivi ou la vue à ouvrir. | Aucun changement de poids ou de score de risque. |

Les effets se lisent au niveau du **portefeuille et de ses expositions en CHF**, avec la volatilité, les pertes de scénarios, les corrélations et les frais déjà calculés. Chaque actif conserve ses caractéristiques et sa disponibilité. Les paramètres financiers du client déterminent les contraintes. Le comparatif objectif et profil garde sa fonction d’explication. [Méthode d’allocation](ALLOCATION.md)

## Trois premiers cas rejoués

| Cas | Confort / Arbitrage / Maintien | Résultat | Avis à restituer |
|---|---|---|---|
| Compréhension récupérée à C02, pari choisi au taux certain le plus bas, maintien à −10 % seulement | 50 / 33 / 50 | 44/100, interprétable | Tolérance intermédiaire dans ces exercices. Comparer les baisses des portefeuilles compatibles et vérifier si l’inconfort apparaît surtout dans les scénarios sévères. |
| Tolérance et goût du pari élevés, refus de tenir aux deux baisses | 100 / 100 / 0 | 67/100, à confirmer | Le score moyen masque un écart important. Explorer la réaction aux baisses avant de se servir du score pour classer des stratégies. |
| Choix certains à prix inversés et maintien incohérent entre −10 % et −20 % | 50 / indéterminé / indéterminé | Score global indéterminé | Revoir les réponses G et D. Les préférences de suivi et de souplesse peuvent déjà être décrites. |

[Tests des cas pilotes](../../tests/test_questionnaire_pilot.py)

Deux vérifications empiriques restent particulièrement utiles. Alterner l’ordre des deux formulations de cadrage permet d’estimer l’effet de répétition. Comparer le score des deux premières cartes G avec le score incluant G03 permet de vérifier que la relance améliore l’interprétation sans changer le classement pour des raisons de parcours. Les scénarios fictifs servent à tester ces règles. Il faudra observer les réponses d’utilisateurs pour estimer leur stabilité.

## Combien de simulations préparer

Le module dénombre **56 629 125 séquences de réponses terminales au premier passage**, avec Like, Pass et Incertain, en tenant compte des branchements et en excluant les retours sur une carte. Ce nombre décrit l’espace théorique. La fréquence réelle des parcours devra être mesurée.

| Cartes affichées | Séquences terminales |
|---:|---:|
| 9 | 648 |
| 10 | 16 524 |
| 11 | 23 328 |
| 14 | 26 244 |
| 15 | 997 272 |
| 16 | 9 861 183 |
| 17 | 25 863 462 |
| 18 | 19 840 464 |

Pour la phase suivante, l’unité d’analyse est le **profil distinct**, défini par ses scores, son état et ses signaux. On couvre toutes les réponses en combinant les blocs du parcours, puis on regroupe les séquences qui produisent les mêmes sorties. Pour chaque groupe, on produit un avis traçable avec ce que les réponses permettent de conclure, ce qu’il faut confirmer et ce que cela change dans le comparatif. Les simulations de portefeuilles utilisent ensuite des mandats financiers représentatifs et des cas limites, dont capacité de perte nulle, objectif hors d’atteinte, faible liquidité et exclusions. Un dénombrement combinatoire ne valide ni le questionnaire ni les rendements.
