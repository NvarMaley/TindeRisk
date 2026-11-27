# Des cartes au bilan du portefeuille

## Construction et choix

Le [moteur personnalisé](PERSONALIZED_MATCHING.md) utilise le mandat USD, les 60 mois de rendements et les listes d’actions datées. Il applique les classes autorisées, les exclusions facultatives et les limites calculables. Les contraintes fermes requérant des données indisponibles rendent le mandat inéligible à la construction. Le classement de convenance utilise les objectifs, le risque modélisé et les préférences, à partir de la fenêtre de développement. Le rendement de la période de test reste une mesure de comparaison.

Jusqu’à six cartes sont mises en avant. Deux cartes mises en avant doivent déplacer au moins 5 % du capital entre titres. Les cibles finales à moins de 1 % de distance sont regroupées à l’écran. Chaque méthode garde son propre chemin historique dans l’[audit](AUDIT_STRATEGIES_ET_PORTEFEUILLE.md).

## Dans Mes matchs

Le client choisit une ou plusieurs stratégies, puis répartit 100 % de son budget entre elles. Le mode manuel utilise ses poids. Le mode variance minimale utilise la covariance des rendements des stratégies sur les 35 mois de développement, avant les frais supplémentaires de transfert. Le mode rendement estimé maximal donne le budget à la stratégie retenue ayant le rendement estimé le plus élevé. Le mode objectif prioritaire compare un ensemble déterministe de répartitions sur les mêmes scénarios et retient la meilleure parmi celles testées.

Le moteur additionne les positions en commun. La volatilité estimée tient compte des covariances des actifs. La concentration est résumée par le nombre de positions et leur équivalent à poids égaux, calculé par `1/Σw²`. Le détail sectoriel couvre les actions directes classables. Un ETF apporte une exposition à plusieurs titres, dont les positions internes ne peuvent être filtrées sur toute l’archive.

Le bilan sépare les quantités suivantes.

| Résultat | Données et interprétation |
|---|---|
| Rendement estimé, volatilité et stress | Estimations des poids consolidés au 31 décembre 2025. Le stress est la plus forte perte parmi les scénarios testés. |
| Backtest | Règles appliquées dans le passé, en USD, avec coûts de transactions modélisés. Le combiné applique des frais supplémentaires de 10 points de base sur les transferts entre stratégies. |
| Projection du portefeuille confirmé | 1 000 trajectoires construites avec des blocs communs de six mois, tirés des 60 mois des actifs détenus. Les poids cibles sont rétablis mensuellement, avec frais modélisés. La référence de cette projection est le cash USD. |
| Solde et gain à l’horizon | Le solde restant tient compte des retraits, des dettes et des objectifs payés. Le gain réintègre ces paiements et déduit le capital de départ et les apports. La valeur actuelle actualise chaque flux à sa date selon le taux renseigné. |
| Objectifs | Fréquence de réussite parmi les scénarios simulés et déficit moyen sur tous les scénarios. Un tiret indique que la réussite ne peut pas être chiffrée avec les paramètres du mandat. |

Les études historiques héritées utilisent un replay de stratégies et, selon le cas, une référence 60/40. Le bilan personnalisé utilise les poids des actifs consolidés. Le suivi de cours et les politiques de gestion dynamique constituent des analyses séparées. [Audit des hypothèses](AUDIT_STRATEGIES_ET_PORTEFEUILLE.md)
