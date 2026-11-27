# Ouvrir l’interface RiskMatch dans Streamlit

Cette page Streamlit affiche l’application RiskMatch existante avec
`st.iframe`. L’interface, les requêtes et les calculs restent ceux du serveur
RiskMatch. Elle utilise la même origine RiskMatch pour les sauvegardes
locales qu’en ouvrant directement l’adresse affichée dans le cadre.

## Sur la même machine

Lancer RiskMatch sur le port 3000 avec `START_WEB.command`, ou conserver le
serveur déjà en cours. Depuis la racine du dépôt :

```bash
python -m pip install -r apps/streamlit/requirements.txt
python -m streamlit run apps/streamlit/streamlit_app.py --server.address 127.0.0.1
```

Ouvrir http://127.0.0.1:8501/.

## Sur une autre machine

Définir `RISKMATCH_APP_URL` à l’adresse HTTPS à laquelle le navigateur du
professeur peut ouvrir le serveur RiskMatch. L’origine RiskMatch doit
autoriser son affichage par la page Streamlit. L’adresse doit aussi permettre
à l’utilisateur autorisé d’ouvrir une session depuis un cadre.

Déployer uniquement cette page sur Streamlit ne rend pas le serveur local
portant le moteur et ses archives accessible à distance. Si un accès à
distance est configuré, conserver l’accès aux archives de recherche dans
l’environnement autorisé.
