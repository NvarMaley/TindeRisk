# 9.1 · Démonstration et vérification

[Télécharger l'application fictive](RiskMatch-demo.zip) · [Pitch PowerPoint en anglais](RiskMatch-client-pitch.pptx) · [Déroulé de 15 minutes et questions client](PITCH.md)

Décompresser l'archive et suivre le README inclus. La démonstration protège un retrait de 15 000 CHF sur un capital de 50 000 CHF. Le client peut arrêter l'entretien avec une tolérance incertaine, comparer deux allocations fictives, autoriser le stockage local, puis revoir son choix après une nouvelle échéance. Les tableaux historiques des diapositives proviennent des sections 6 et 7. Les deux allocations du logiciel portable et ses observations de marché sont générées pour le cours.

## Résultats d'acceptation du 23 novembre 2026

| Contrôle | Résultat |
|---|---|
| Suite Python complète | 69 tests réussis avec CPython 3.12.6. Quatorze avertissements de dépendances. |
| Chromium, fenêtre de 1 200 × 850 et téléphone émulé de 390 × 850 | Six observations attendues sur chaque écran. Tolérance indéterminée, signal refusé et choix ouvert, paiement couvert, confirmation unique, change périmé et manque de 5 000 CHF. Les douze valeurs attendues et observées figurent dans le relevé. |
| Gestes et corrections | Les deux parcours supplémentaires ont réussi avec souris/clavier et écran tactile émulé. Glissement court ignoré, réponse, incertitude, arrêt, reprise et correction. |
| Deux contrefactuels séparés | Modifier la tolérance laisse les 15 000 CHF protégés. Avancer seulement la date d'une facture révisée déclenche une nouvelle comparaison et augmente le manque avant règlement. |
| Copie GitHub neuve et sélective, version 4b89e68 | Les exemples Python isolés, la signature du catalogue et la reconstruction de l'archive ont réussi. Le navigateur a parcouru l'export sans fichiers de recherche privés et avec les requêtes HTTP externes bloquées. |
| Données et secrets de l'export | 24 fichiers vérifiés par SHA-256, deux jeux de données fictifs, un catalogue de démonstration signé. Contrôle de noms et de motifs de clés privées, de jetons GitHub et de clés AWS. Identifiant d'accès généré uniquement à l'ouverture d'un compte. Suppression des écritures dépendantes testée. |
| Présentation | Sept diapositives, frais et financement recalculés depuis les tableaux d'origine. Narration synthétique mesurée à 5 min 28 s. Le déroulé réserve le reste des 15 minutes à la manipulation et aux questions. Relecture indépendante par une personne en attente. |

[Relevé des parcours](evidence/checks.json) · [Captures et temps mesurés](evidence/) · [Vérification des diapositives](verify_pitch.py) · [Tests indépendants de mandat](../../tests/test_release_acceptance.py)

Les premiers essais de développement ont identifié un préremplissage de formulaire perdu pendant le rafraîchissement Streamlit et des sélecteurs de test ambigus. Le formulaire met désormais à jour les widgets lors du clic. Les vérifications de publication portent sur une copie neuve. Les parcours automatisés utilisent des cas fictifs et l'émulation mobile. L'application a été exécutée sur un serveur local. Aucun hébergement public de l'application n'a été validé.

## Périmètre de distribution

| Contenu | Origine et vérification | Destination |
|---|---|---|
| Application, banque de questions, événements et cours de marché fictifs | Fichiers du projet recensés et empreintes vérifiées. L'archive contient les déclarations de dépendances. | Démo portable du cours. |
| Mandats et réponses | Le consentement au stockage est distinct de la sélection. Le serveur local conserve un résumé de profil fictif et le registre du compte. Les réponses carte par carte restent en session. Une clé aléatoire permet la reprise ou la suppression. | Base SQLite de l'hôte, hors de l'archive. |
| Données WRDS/CRSP/Compustat, historiques de tiers, matériel des laboratoires | Le dépôt GitHub complet est public et contient déjà des fichiers fournisseur, dont les fragments CRSP et les tables WRDS. Aucun justificatif de redistribution de ces archives n'a été retrouvé dans le projet. Le droit de redistribuer les historiques et les extraits dérivés reste à établir auprès des titulaires. | Absents du ZIP. La diffusion du dépôt complet reste un point ouvert. |
| Corpus local Theory | Aucun fichier de ce répertoire suivi dans Git. Les documents du projet peuvent le référencer. | Hors dépôt et hors archive. |
| Rapports agrégés, expériences et diapositives | Source, période, hypothèses et limites identifiées dans les chapitres correspondants. | Livrables du dépôt, distincts du ZIP applicatif. |

## Reproduction

Depuis la racine du dépôt, dans les environnements Python configurés pour le projet :

```sh
python -m pytest -q
python -I -S tests/check_course_examples.py
python -I -S research/check_source_fixture.py
python research/release/verify_package.py
python research/release/verify_pitch.py
python research/release/package.py /tmp/riskmatch-demo
python -m streamlit run /tmp/riskmatch-demo/app/intake.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Dans un environnement avec Playwright et Chromium installés, lancer dans un autre terminal :

```sh
python research/release/browser.py --url http://127.0.0.1:8501 --output /tmp/riskmatch-verification
RISK_MATCH_URL=http://127.0.0.1:8501 python tests/browser_interview.py
```

L'empreinte SHA-256 de RiskMatch-demo.zip est `9b2cf74dd32c4bb41a93f8057ec2c185f8f1a3c070b3c713ac90b91cb9dc2f43`. La reconstruction compare chaque entrée à son empreinte et vérifie l'identité complète du ZIP. [Manifeste](public_manifest.json) · [Instructions incluses](DEMO.md) · [Dépendances macOS vérifiées](demo-requirements.lock)
