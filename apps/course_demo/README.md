# Démonstration RiskMatch pour QARM II

La démo présente une stratégie de Markowitz sous contraintes et un cas client fictif. Elle utilise le solveur du projet, une série synthétique reproductible, deux limites de perte à comparer, un test sur 24 mois réservés et un mélange avec un portefeuille de variance minimale.

Les cinq actifs représentent des classes fictives. La démo illustre la démarche quantitative du dossier local et peut être ouverte sans les archives de recherche. Les cours de marché et les sauvegardes du dossier local ne sont pas utilisés.

## Démo en ligne

[Ouvrir la démo Streamlit](https://nvarmaley.github.io/TindeRisk/).

GitHub Pages charge Streamlit et Python dans le navigateur via Stlite. Les
fichiers publiés sont explicitement sélectionnés par `package_pages.py`.
Pour reconstruire le paquet, exécuter depuis la racine :

```bash
python apps/course_demo/package_pages.py /tmp/riskmatch-qarm-pages
```

## Lancer avec Streamlit

Depuis la racine du dépôt :

```bash
python -m pip install -r apps/course_demo/requirements.txt
python -m streamlit run apps/course_demo/streamlit_app.py
```

Pour héberger avec Streamlit Community Cloud, sélectionner le chemin d’entrée `apps/course_demo/streamlit_app.py`. L’application trouve les dépendances dans le fichier `requirements.txt` du même dossier. La version navigateur peut aussi être publiée sur GitHub Pages.
