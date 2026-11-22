# Guide de lecture des 60 cartes RiskMatch

Banque v2.2.0. Les affirmations en anglais sont celles de l’application. Les explications en français servent à préparer le rapport et l’oral. **Oui** approuve l’affirmation affichée, **non** la rejette et **passer** laisse la réponse ouverte. Le profil décrit des choix hypothétiques à un an. Les interprétations proposées sont des hypothèses.

## Comment les réponses comptent

| Cartes disponibles | Nombre | Contribution |
|---|---:|---|
| C03–C07, arbitrages communs, et T01–T20, précisions adaptatives | 25 | Chaque choix compris entre placement garanti et placement incertain impose au plus une borne sur l’aversion φ. Cinq arbitrages communs et au plus deux précisions peuvent compter dans un parcours. |
| C01 et P01, compréhension | 2 | Déterminent si le moteur peut interpréter les arbitrages. |
| C02 et C08–C15, autres cartes communes | 9 | Décrivent un choix, une préférence ou une action envisagée. Peuvent rendre une relance pertinente. |
| B01–B24, relances qualitatives | 24 | Précisent le motif, un fait à vérifier ou une préférence. Aucune borne numérique. |

**Le calcul utilise des bornes.** Pour chaque offre, on cherche la valeur de φ pour laquelle le montant garanti et le placement incertain sont équivalents. Dans le modèle, la valeur du placement incertain est son rendement moyen diminué de φ × variance / 2. Un φ élevé donne davantage de poids aux fluctuations. Avec des rendements exprimés en décimales, le seuil vaut **2 × (rendement moyen incertain − rendement garanti) / variance**.

Sur C03, le pari a un rendement moyen de 5 % et une variance de 0,0225. La garantie rapporte 2 %. Le seuil vaut donc environ **2,67**. Choisir la garantie donne une borne basse, choisir le pari donne une borne haute. Le moteur retient **la plus haute des bornes basses** (avec un minimum de zéro) et **la plus basse des bornes hautes**. Répéter un choix identique ne lui donne aucun poids supplémentaire. Une réponse passée laisse les bornes en place. Les valeurs ci-dessous sont arrondies pour la lecture.

**Déroulement.** Le parcours commence par C01 et présente 15 cartes communes si la compréhension est établie et si l’entretien se poursuit. Les relances éligibles dépendent des réponses, de leur priorité et de la place disponible. Le parcours s’arrête au plus tard à 25 cartes actives. Corriger un choix rouvre la suite du parcours. [Banque des cartes](profile_v1.json) · [Règles de calcul et de sélection](../src/riskmatch/interview.py)

## Compréhension et déclaration

La compréhension des montants conditionne le calcul. La déclaration de confort apporte le point de vue du client sur lui-même. Un écart entre sa déclaration et son choix d’un paiement garanti peut tenir au montant ou à l’objectif précis.

| Carte · catégorie | Situation et affirmation | Oui | Non | Passer |
|---|---|---|---|---|
| C01 · Compréhension | In one year an investment ends at CHF 900 or CHF 1,200. Both are equally likely. **The smallest possible balance is CHF 900.** | Identifie le minimum de CHF 900. Le parcours continue. | Reçoit une explication, puis P01. | Reçoit aussi l’explication et P01. |
| P01 · Compréhension | In one year the possible balances are CHF 800 and CHF 1,100, each with a 50% chance. **The smallest possible balance is CHF 1,100.** | Minimum mal identifié. Le parcours se termine avec une tolérance indéterminée. | Identifie correctement que CHF 1 100 ne peut pas être le minimum. Le parcours reprend. | Compréhension indéterminée. Le parcours se termine. |
| C02 · Confort déclaré | Think about money you could leave invested for a year. **I feel comfortable taking financial risk.** | Se dit à l’aise avec le risque financier sur un an. | Ne se dit pas à l’aise dans ce contexte. | Confort non précisé. B18 devient possible. |

## Arbitrages chiffrés

Pour **chacune** des 25 offres ci-dessous, le scénario part de **CHF 1 000**, sur **un an**, avec une chance sur deux de finir à **CHF 900** et une chance sur deux de finir à **CHF 1 200** si l’on choisit le pari. Seuls le montant garanti et l’option que l’affirmation approuve varient. Les proposer à plusieurs niveaux aide à situer le prix que le client accorde à la certitude. Un choix près du seuil peut aussi refléter une quasi-indifférence.

Les T deviennent possibles après les cartes communes si au moins un arbitrage a été compris et renseigné, si l’intervalle est cohérent, s’il laisse les deux exemples du modèle possibles et si le nouveau seuil tombe à l’intérieur. Le moteur en propose au plus deux. Dans chaque ligne, **passer** laisse l’offre sans borne.

### Arbitrages communs

| Carte | Garantie (CHF) | Affirmation affichée | Oui | Non |
|---|---|---|---|---|
| C03 | 1 020 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 2,67 | Pari · φ ≤ 2,67 |
| C04 | 1 000 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 4,44 | Garantie · φ ≥ 4,44 |
| C05 | 1 040 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 0,89 | Pari · φ ≤ 0,89 |
| C06 | 980 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 6,22 | Garantie · φ ≥ 6,22 |
| C07 | 1 030 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 1,78 | Pari · φ ≤ 1,78 |

### Précisions adaptatives

| Carte | Garantie (CHF) | Affirmation affichée | Oui | Non |
|---|---|---|---|---|
| T01 | 925 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 11,11 | Garantie · φ ≥ 11,11 |
| T02 | 930 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 10,67 | Pari · φ ≤ 10,67 |
| T03 | 935 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 10,22 | Garantie · φ ≥ 10,22 |
| T04 | 940 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 9,78 | Pari · φ ≤ 9,78 |
| T05 | 945 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 9,33 | Garantie · φ ≥ 9,33 |
| T06 | 950 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 8,89 | Pari · φ ≤ 8,89 |
| T07 | 955 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 8,44 | Garantie · φ ≥ 8,44 |
| T08 | 960 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 8,00 | Pari · φ ≤ 8,00 |
| T09 | 965 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 7,56 | Garantie · φ ≥ 7,56 |
| T10 | 970 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 7,11 | Pari · φ ≤ 7,11 |
| T11 | 975 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 6,67 | Garantie · φ ≥ 6,67 |
| T12 | 985 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 5,78 | Pari · φ ≤ 5,78 |
| T13 | 990 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 5,33 | Garantie · φ ≥ 5,33 |
| T14 | 995 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 4,89 | Pari · φ ≤ 4,89 |
| T15 | 1 005 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 4,00 | Garantie · φ ≥ 4,00 |
| T16 | 1 010 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 3,56 | Pari · φ ≤ 3,56 |
| T17 | 1 015 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 3,11 | Garantie · φ ≥ 3,11 |
| T18 | 1 025 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 2,22 | Pari · φ ≤ 2,22 |
| T19 | 1 035 | Of these two investments, I choose the uncertain payment. | Pari · φ ≤ 1,33 | Garantie · φ ≥ 1,33 |
| T20 | 1 045 | Of these two investments, I choose the guaranteed payment. | Garantie · φ ≥ 0,44 | Pari · φ ≤ 0,44 |

## Comparaisons autour du capital de départ

Pour les quatre cartes, le capital initial est de CHF 1 000 sur un an. L’affirmation est **“I choose the guaranteed payment.”** Il y a deux issues équiprobables. La comparaison porte sur le choix effectué lorsque le pire solde atteint le capital de départ, puis lorsqu’il passe en dessous.

| Carte | Carte associée | Oui | Non | Passer |
|---|---|---|---|---|
| C08 | C10 | Garantie de 1 080 CHF | Pari · 1 000 ou 1 200 CHF | Comparaison incomplète |
| C09 | C11 | Garantie de 1 150 CHF | Pari · 1 000 ou 1 400 CHF | Comparaison incomplète |
| C10 | C08 | Garantie de 980 CHF | Pari · 900 ou 1 100 CHF | Comparaison incomplète |
| C11 | C09 | Garantie de 1 000 CHF | Pari · 850 ou 1 250 CHF | Comparaison incomplète |

Si le choix passe du pari à la garantie dans **les deux paires**, ou de la garantie au pari dans les deux, B14 devient éligible. Un seul changement ne suffit pas. Un oui à B14 confirme que finir sous la mise comptait dans ces comparaisons. Le niveau de richesse finale change lui aussi entre les cartes. Le moteur conserve la description de cette sensibilité sans lui attribuer de coefficient d’aversion aux pertes.

## Vente, flexibilité et suivi

Les cartes suivantes explorent une action envisagée. C12 et C13 font varier la baisse et le contexte. Une différence entre leurs réponses peut donc avoir plusieurs causes.

| Carte · catégorie | Situation et affirmation | Oui | Non | Passer |
|---|---|---|---|---|
| C12 · Réaction à une baisse | The investment is down 15%. You planned to hold it for eight more years. **Today I would sell some of it.** | Envisage une vente. B01–B03 peuvent en préciser la raison. | N’envisage pas cette vente. La raison de conserver reste ouverte. | Décision ouverte. B16 peut préciser si des informations sur les dépenses manquent. |
| C13 · Réaction à une baisse | An investment falls 8% in a month. Your next planned expense is five years away. **I would reduce my exposure this month.** | Envisage de réduire son exposition ce mois-ci. B01–B03 deviennent possibles. | Ne prévoit pas cette réduction dans ce scénario. | Décision ouverte. B17 peut préciser si davantage de temps serait utile. |
| C14 · Souplesse de l’objectif | Your current savings plan may fall short of your goal. **I could move the goal date later.** | Un report pourrait convenir. B11 peut explorer le compromis entre date et montant. | Le report ne convient pas ici. B09 et B10 explorent le montant et les versements. | Flexibilité inconnue. B19 peut préciser si la date doit être vérifiée. |
| C15 · Suivi | Your investment has moved away from your chosen allocation. **I would like a notification when this happens.** | Souhaite un avis de dérive. B12 peut préciser son contenu. | Décline cet avis. B13 explore un rendez-vous périodique. | Préférence ouverte. B20 peut proposer de se prononcer après un exemple. |

## Les 24 relances qualitatives

Les conditions d’accès figurent sous chaque identifiant. « C12 oui ou C13 oui » indique que l’une des deux réponses suffit pour rendre la relance possible. Les raisons peuvent se cumuler. Chaque ligne indique l’interprétation possible, même lorsque l’application se limite à enregistrer la réponse dans l’historique. **Passer** laisse précisément le motif de la ligne indéterminé, sans défaire les réponses déjà données. Toutes ces relances ont une contribution numérique nulle à φ.

### Pourquoi vendre, et quel fait vérifier ?

| Carte · catégorie et condition | Affirmation affichée | Oui | Non |
|---|---|---|---|
| B01 · Besoin de liquidités<br>C12 oui ou C13 oui | Thinking about your decision to sell, I may need this money for a payment within twelve months. | Un paiement sous douze mois pourrait expliquer la vente. Ouvre la revue de trésorerie et rend B04–B06 possibles. | Aucun besoin proche signalé par cette réponse. Inconfort et anticipation restent possibles. |
| B02 · Inconfort<br>C12 oui ou C13 oui | Even with expenses covered, I would want an investment with smaller fluctuations. | Souhaite moins de fluctuations même avec les dépenses couvertes. Le profil le mentionne. B07 devient possible. | Ce motif de stabilité n’est pas approuvé ici. |
| B03 · Anticipation de marché<br>C12 oui ou C13 oui | My decision to sell reflects an expectation of further losses. | Attribue la vente à une baisse attendue. Le profil enregistre cette anticipation. B08 devient possible. | N’attribue pas la vente à cette anticipation. |
| B04 · Financement<br>B01 oui | There is a payment missing from the schedule I entered. | Signale un paiement oublié. Revoir son montant et sa date. B21 devient possible. | Aucune omission signalée. Une dépense connue pourrait néanmoins être avancée. |
| B05 · Financement<br>B01 oui | A payment I listed might have to be made earlier. | Signale une échéance potentiellement plus proche. Vérifier la date. B22 devient possible. | Aucune avance de date signalée. |
| B06 · Financement<br>B01 oui | Some money earmarked for the payment might arrive late. | Signale un risque de versement tardif. Vérifier la date de disponibilité. B23 devient possible. | Aucun retard signalé par cette réponse. |
| B07 · Inconfort<br>B02 oui | Seeing a temporary loss would make it difficult for me to follow my plan. | Une perte temporaire pourrait rendre le plan difficile à maintenir. | La personne ne déclare pas cette difficulté malgré son souhait de stabilité. |
| B08 · Anticipation de marché<br>B03 oui | I would reconsider selling if my outlook for this investment changed. | La décision de vendre pourrait changer avec les anticipations. | La personne ne s’engage pas à reconsidérer la vente si ses anticipations changent. |
| B16 · Réaction à une baisse<br>C12 passée | To answer the 15% decline scenario, I would need to know more about upcoming expenses. | Des précisions sur les dépenses aideraient à répondre. Aucune dépense chiffrée n’est confirmée. | Le manque d’informations sur les dépenses n’est pas le motif déclaré du passage. |
| B17 · Réaction à une baisse<br>C13 passée | To answer the one-month decline scenario, I would need more time to consider the choice. | Souhaite davantage de temps pour réfléchir au scénario de baisse mensuelle. | Le besoin de temps n’est pas le motif déclaré du passage. |
| B21 · Financement<br>B04 oui | I want to review the amount of the missing payment. | Souhaite vérifier le montant de la dépense manquante dans le formulaire. | Ne demande pas cette vérification ici. Le signal de paiement manquant reste présent. |
| B22 · Financement<br>B05 oui | I want to review the earliest possible payment date. | Souhaite vérifier la première date de paiement possible. | Ne demande pas cette vérification ici. L’incertitude sur la date déjà déclarée demeure. |
| B23 · Financement<br>B06 oui | I want to review which funding sources are confirmed. | Souhaite revoir les sources de financement confirmées. | Ne demande pas cette vérification ici. Le risque de retard déjà déclaré demeure. |

### Que clarifier sur le risque, l’objectif ou le suivi ?

| Carte · catégorie et condition | Affirmation affichée | Oui | Non |
|---|---|---|---|
| B09 · Souplesse de l’objectif<br>C14 non | I could reduce the amount I plan to spend on my goal. | Une réduction du montant cible est envisageable. B24 peut proposer de comparer deux montants. | La personne ne propose pas de réduire la cible. |
| B10 · Souplesse de l’objectif<br>C14 non | I could increase my future contributions to keep the goal date. | Des contributions plus élevées seraient envisageables. Vérifier les montants, dates et leur confirmation. | La personne ne se dit pas prête à augmenter ses contributions. |
| B11 · Souplesse de l’objectif<br>C14 oui | I would want to compare a later date with a smaller goal amount. | Souhaite comparer report de date et réduction de cible avant de choisir. | Ne demande pas cette comparaison. Le report précédemment envisagé reste possible. |
| B12 · Suivi<br>C15 oui | I would want to see the estimated trading cost in an allocation alert. | Souhaite voir les frais de transaction estimés dans l’alerte. Le profil l’indique. | Aucune demande de détail sur les frais. L’alerte déjà souhaitée reste enregistrée. |
| B13 · Suivi<br>C15 non | I would prefer to review my investments at a scheduled meeting. | Préfère un rendez-vous périodique. Le profil l’indique. | Aucune préférence déclarée pour un rendez-vous. |
| B14 · Point de référence<br>Deux inversions de même sens | In those comparisons, the chance of ending below the starting amount mattered to me. | Confirme que le risque de finir sous le montant initial a compté. | Le changement répété demeure observable. Cette explication n’est pas confirmée. |
| B15 · Indifférence possible<br>Résultat sensible à une carte ou conflit | For at least one of the one-year choices, both alternatives would work about equally well for me. | Signale qu’au moins une offre paraissait presque équivalente. Le profil invite à la revoir. | Aucune quasi-indifférence déclarée. Un conflit éventuel reste à examiner. |
| B18 · Confort déclaré<br>C02 passée | My comfort with risk depends on which financial goal I have in mind. | Le confort déclaré dépendrait de l’objectif financier considéré. | La dépendance à l’objectif n’est pas approuvée. Le confort initial reste inconnu. |
| B19 · Souplesse de l’objectif<br>C14 passée | I would need to check the goal date before deciding whether it can move. | Souhaite vérifier la date avant de se prononcer sur un report. | Aucun besoin de vérifier la date n’est déclaré. Sa flexibilité reste inconnue. |
| B20 · Suivi<br>C15 passée | I would like to choose notification settings after seeing an example. | Un exemple aiderait à choisir les notifications. | Aucun exemple demandé. La préférence de notification reste inconnue. |
| B24 · Souplesse de l’objectif<br>B09 oui | I would want to compare two goal amounts before choosing one. | Souhaite examiner deux cibles chiffrées avant de choisir. | Ne demande pas cette comparaison. Aucun nouveau montant cible n’est établi. |

## Les faits qui déterminent les contraintes du client

Les quatre écrans précédant les cartes recueillent les faits nécessaires pour savoir combien le client peut exposer. Un montant peut être exact, donné sous forme de fourchette, inconnu, refusé ou laissé en attente. Un zéro explicite est une information. [Formulaire](../app/intake.py) · [Calcul du financement](../src/riskmatch/intake.py)

| Écran et informations demandées | Comment une réponse change les possibilités |
|---|---|
| **Objectif** · projet financé, devise de dépense et code si « Other », début du plan, date et flexibilité de l’objectif, montant cible, valeur future ou pouvoir d’achat actuel, inflation si nécessaire | La date et le montant définissent la cible. Une cible en pouvoir d’achat actuel est convertie à l’échéance. Un report envisagé sur C14 demande une modification explicite du mandat avant tout nouveau calcul. |
| **Ressources** · capital disponible aujourd’hui, versements prévus pour l’objectif, montants, dates, confirmation et état du calendrier | Le capital de départ est immédiatement disponible. Un versement futur destiné à l’objectif entre à sa date dans le calcul du rendement nécessaire lorsqu’il est confirmé. |
| **Argent à protéger** · réserve d’urgence, retraits et dates, financements externes affectés aux paiements, montants, dates de disponibilité, confirmation et état du calendrier | Le besoin de réserve est le coussin d’urgence plus le déficit cumulé maximal des paiements après financements confirmés et disponibles à temps. Une fourchette produit deux scénarios. En cas d’insuffisance, l’application affiche le manque et la première date concernée. Un calendrier de paiements incomplet laisse la capacité indéterminée. |
| **Attentes et limites** · rendement annuel nominal souhaité, investissements à exclure et préférences | Le rendement souhaité permet une comparaison avec le rendement nécessaire, calculé séparément. Une exclusion exprimée délimite les investissements admissibles pour une future allocation. Une préférence sert à départager les possibilités. Le profil actuel restitue les limites déclarées. |

## Quelles possibilités selon les réponses ?

Le profil illustre deux placements fictifs sur un an. L’exemple plus stable a un rendement moyen de 3 % et une volatilité de 5 %. L’exemple plus variable a un rendement moyen de 5 % et une volatilité de 15 %. Leurs valeurs selon le modèle sont égales à **φ = 2**. En dessous, le modèle privilégie l’exemple plus variable. Au-dessus, il privilégie le plus stable. Si 2 appartient à l’intervalle, les deux restent possibles. Le moteur retire aussi chaque réponse chiffrée à tour de rôle. S’il suffit d’en retirer une pour changer les exemples compatibles, le classement personnel reste indéterminé.

Les cas suivants supposent la compréhension vérifiée, avec uniquement les arbitrages chiffrés indiqués. Les bornes sont arrondies. Chaque cas part du même mandat fictif de **CHF 50 000**, avec un paiement de **CHF 15 000**, aucun financement externe et aucune autre réserve.

| Réponses | Conclusion sur la préférence | Possibilité financière |
|---|---|---|
| Oui à C03, non à C04, oui à C06 | Garantie à CHF 1 020 et à CHF 1 000, pari face à la garantie de CHF 980. Intervalle de 4,44 à 6,22. L’exemple plus stable reste compatible même en retirant une réponse. | CHF 15 000 protégés, CHF 35 000 investissables. |
| Non à C05 et à C07 | Deux paris face à des garanties de CHF 1 040 et CHF 1 030. Intervalle de 0 à 0,89. L’exemple plus variable reste compatible même en retirant une réponse. | Même réserve, même capital investissable. |
| Oui à C04 et C05 | Le pari face à CHF 1 000 et la garantie de CHF 1 040 donnent un intervalle de 0,89 à 4,44. Les deux exemples sont possibles. | CHF 35 000 investissables. Le montant disponible ne détermine pas la préférence. |
| Oui à C03 seulement | φ ≥ 2,67. Retirer ce seul choix rouvre les deux possibilités. Le classement demeure sensible. | La réserve reste calculable indépendamment. |
| Oui à C03 et non à C05 | Exigerait à la fois φ ≥ 2,67 et φ ≤ 0,89. Le profil signale un conflit et permet de revoir les réponses. | Les CHF 15 000 restent protégés. |
| Toutes les offres chiffrées sont passées, ou la seconde pratique échoue | Tolérance indéterminée. La personne peut consulter ses réponses et corriger un geste. | La capacité reste calculable si les faits sont complets. |

**Même préférence, autre contrainte.** Si CHF 5 000 de financement dédié se règlent avant le paiement de CHF 15 000, la réserve nécessaire descend à CHF 10 000 et le capital investissable monte à CHF 40 000. Si ces CHF 5 000 arrivent après l’échéance, il faut à nouveau protéger CHF 15 000. Cocher B01, B04, B05 ou B06 signale un fait à revoir. Seules les modifications confirmées du calendrier changent les montants. Les exemples de stabilité et de variabilité illustrent un classement sous hypothèses. Ils ne déclenchent aucun ordre.

## Les quatre questions réservées à la simulation

Ces choix sont présentés ici pour que le lecteur puisse retrouver toutes les questions du projet. Ils restent hors des 60 cartes du profil. L’invite commune est **“Which ending balance would you choose for this investment after one year?”**. Choisir la garantie ou le pari fournit une réponse de comparaison pour la simulation. « Unsure » laisse le résultat non vérifié. Aucune des trois réponses ne change φ, la réserve ou le parcours. [Fichier des quatre choix](pilot_holdout_v1.json)

| Question et catégorie | Mise (CHF) | Garantie (CHF) | Soldes possibles du pari (CHF) |
|---|---|---|---|
| V01 · probabilités inégales | 1 000 | 1 020 | 800 (25 %), 1 120 (75 %) |
| V02 · trois soldes possibles | 1 000 | 1 010 | 800 (25 %), 1 000 (50 %), 1 300 (25 %) |
| V03 · mise plus importante et risque de perte | 10 000 | 10 150 | 8 500 (40 %), 11 500 (60 %) |
| V04 · gain asymétrique | 2 000 | 2 040 | 1 900 (75 %), 2 500 (25 %) |

Les choix de conception et les explications concurrentes sont documentés par famille dans la [justification théorique](QUESTIONNAIRE_DESIGN.md#research-behind-the-design). La simulation vérifie le fonctionnement de ces règles. La fréquence des comportements chez de vrais investisseurs reste inconnue.
