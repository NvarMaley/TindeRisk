# 8.1 · Suivi fictif en CHF

Dans **Portfolio options**, sauvegarder une allocation, ouvrir **Portfolio monitor** et confirmer séparément le stockage sur l'hôte. La sélection conserve la version du mandat et du modèle, la date simulée, les unités, les frais, la réserve et les liquidités. La clé aléatoire permet de reprendre ou de supprimer le dossier. Seule son empreinte est enregistrée. Le journal SQLite est local, transactionnel et séparé du dépôt. La démonstration conserve des paramètres fictifs. Les réponses détaillées à l'entretien et l'identité du client restent hors du journal.

Le flux de clôtures et de changes a été créé pour ce projet. Le bouton reçoit un événement daté à la fois. Le calendrier explicite distingue fermeture et séance attendue. Une clôture absente, un change ancien ou une correction tardive laisse une trace. La dernière marque fiable reste visible. Les valeurs initialement reçues et les révisions restent consultables avec leur provenance. Les dates de la démonstration sont simulées. Aucun accès à un flux commercial en temps réel n'est établi.

La performance est chaînée après retrait des flux externes de fin de période. Le rapprochement distingue variation du prix local, effet de change sur la valeur locale finale, frais et flux externes. Le retrait vient de la réserve et une modification du prix pendant un flux de début de période requiert une sous-période supplémentaire. L'indicateur de progression compare l'avoir investissable à la cible nominale du scénario.

**Contrôle indépendant.** En tout-cash, le graphique part de 50 000 CHF, reçoit 100 et verse 15 000. Il termine à 35 100 CHF avec un rendement temporel de zéro. [Flux et versions](../../data/demo/monitor_feed.json) · [Vérifications](../../tests/test_monitor_ledger.py)
